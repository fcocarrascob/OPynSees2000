"""
Ejecutor de análisis OpenSeesPy.

Genera el script completo, lo ejecuta en un subproceso Python,
y parsea la salida para obtener resultados.

Alternativa: ejecutar OpenSeesPy in-process (más rápido pero
menos aislado). Aquí usamos subproceso por seguridad.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from gui.core.model_data import AnalysisResult, StructuralModel
from gui.core.script_generator import generate_script


def run_static_analysis(
    model: StructuralModel,
    system: str = "BandSPD",
    algorithm: str = "Linear",
    python_exe: str | None = None,
) -> tuple[bool, AnalysisResult | None, str]:
    """
    Ejecuta un análisis estático lineal.

    Returns
    -------
    (success, result, log_output)
    """
    script = generate_script(model, include_analysis=False)

    # Agregar comandos de análisis + extracción de resultados
    script += _static_analysis_commands(model, system, algorithm)
    script += _result_extraction_commands(model)

    return _execute_script(script, "static", python_exe)


def run_modal_analysis(
    model: StructuralModel,
    n_modes: int = 6,
    system: str = "BandSPD",
    python_exe: str | None = None,
) -> tuple[bool, AnalysisResult | None, str]:
    """
    Ejecuta un análisis modal (eigenvalue).

    Returns
    -------
    (success, result, log_output)
    """
    script = generate_script(model, include_analysis=False)
    script += _modal_analysis_commands(model, n_modes, system)

    return _execute_script(script, "modal", python_exe)


# ---------------------------------------------------------------
# Generadores de comandos de análisis
# ---------------------------------------------------------------

def _static_analysis_commands(
    model: StructuralModel, system: str, algorithm: str
) -> str:
    lines = [
        "",
        "# " + "=" * 58,
        "# ANÁLISIS ESTÁTICO",
        "# " + "=" * 58,
        f"ops.system('{system}')",
        "ops.numberer('RCM')",
        "ops.constraints('Plain')",
        f"ops.algorithm('{algorithm}')",
        "ops.integrator('LoadControl', 1.0)",
        "ops.analysis('Static')",
        "analysis_ok = ops.analyze(1)",
        "",
    ]
    return "\n".join(lines)


def _modal_analysis_commands(
    model: StructuralModel, n_modes: int, system: str
) -> str:
    # Las masas se calculan automáticamente desde el patrón DEAD en script_generator.
    # La validación pre-análisis (Step 5) asegura que existe DEAD o masas explícitas.

    lines = [
        "",
        "# " + "=" * 58,
        "# ANÁLISIS MODAL",
        "# " + "=" * 58,
        f"ops.system('{system}')",
        "ops.numberer('RCM')",
        "ops.constraints('Plain')",
        f"eigenvalues = ops.eigen({n_modes})",
    ]
    lines.extend([
        "import math",
        "import json",
        "",
        "# Resultados",
        "result = {",
        '    "type": "modal",',
        "    \"eigenvalues\": eigenvalues,",
        "    \"periods\": [2 * math.pi / math.sqrt(ev) if ev > 0 else 0 for ev in eigenvalues],",
        "    \"frequencies\": [math.sqrt(ev) / (2 * math.pi) if ev > 0 else 0 for ev in eigenvalues],",
        "    \"mode_shapes\": {},",
        "}",
        "",
        "# Extraer formas modales",
        f"node_tags = {sorted(model.nodes.keys())}",
        f"for mode in range(1, {n_modes + 1}):",
        "    shapes = {}",
        "    for tag in node_tags:",
        "        try:",
        f"            disp = [ops.nodeEigenvector(tag, mode, dof) for dof in range(1, {model.ndf + 1})]",
        "            shapes[tag] = disp",
        "        except Exception:",
        "            pass",
        "    result['mode_shapes'][mode] = shapes",
        "",
        "print('__RESULT_JSON__')",
        "print(json.dumps(result))",
        "print('__END_RESULT__')",
    ])
    return "\n".join(lines)


def _result_extraction_commands(model: StructuralModel) -> str:
    """Genera comandos para extraer desplazamientos y reacciones."""
    node_tags = sorted(model.nodes.keys())
    fixed_tags = [t for t in node_tags if model.nodes[t].is_fixed]
    ndf = model.ndf

    lines = [
        "import json",
        "",
        "result = {",
        '    "type": "static",',
        "    \"displacements\": {},",
        "    \"reactions\": {},",
        '    "analysis_ok": analysis_ok,',
        "}",
        "",
        f"for tag in {node_tags}:",
        f"    disp = [ops.nodeDisp(tag, dof) for dof in range(1, {ndf + 1})]",
        "    result['displacements'][tag] = disp",
        "",
    ]

    if fixed_tags:
        lines.extend([
            "ops.reactions()",
            f"for tag in {fixed_tags}:",
            f"    rxn = [ops.nodeReaction(tag, dof) for dof in range(1, {ndf + 1})]",
            "    result['reactions'][tag] = rxn",
            "",
        ])

    lines.extend([
        "print('__RESULT_JSON__')",
        "print(json.dumps(result))",
        "print('__END_RESULT__')",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------
# Ejecución del script
# ---------------------------------------------------------------

def _execute_script(
    script: str,
    analysis_type: str,
    python_exe: str | None = None,
) -> tuple[bool, AnalysisResult | None, str]:
    """
    Escribe el script a un archivo temporal, lo ejecuta en subproceso,
    y parsea los resultados del stdout.
    """
    exe = python_exe or sys.executable

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        temp_path = f.name

    try:
        proc = subprocess.run(
            [exe, temp_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False, None, "ERROR: Timeout (120s) en la ejecución del análisis."
    except FileNotFoundError:
        return False, None, f"ERROR: Python no encontrado en '{exe}'."
    finally:
        Path(temp_path).unlink(missing_ok=True)

    output = proc.stdout + proc.stderr
    log = output

    # Buscar JSON de resultados en la salida
    result_json = _extract_result_json(proc.stdout)

    if proc.returncode != 0 or result_json is None:
        return False, None, log

    # Parsear resultado
    try:
        result = _parse_result(result_json, analysis_type)
        return True, result, log
    except Exception as e:
        return False, None, f"{log}\n\nError parseando resultados: {e}"


def _extract_result_json(stdout: str) -> Optional[dict]:
    """Extrae el JSON de resultados del stdout."""
    marker_start = "__RESULT_JSON__"
    marker_end = "__END_RESULT__"
    start = stdout.find(marker_start)
    end = stdout.find(marker_end)
    if start == -1 or end == -1:
        return None
    json_str = stdout[start + len(marker_start):end].strip()
    return json.loads(json_str)


def _parse_result(data: dict, analysis_type: str) -> AnalysisResult:
    """Convierte el dict de resultados en AnalysisResult."""
    if analysis_type == "static":
        result = AnalysisResult(analysis_type="static")
        for tag_str, disp in data.get("displacements", {}).items():
            result.node_displacements[int(tag_str)] = tuple(disp)
        for tag_str, rxn in data.get("reactions", {}).items():
            result.node_reactions[int(tag_str)] = tuple(rxn)
        return result
    elif analysis_type == "modal":
        result = AnalysisResult(analysis_type="modal")
        result.eigenvalues = data.get("eigenvalues", [])
        result.periods = data.get("periods", [])
        result.frequencies = data.get("frequencies", [])
        for mode_str, shapes in data.get("mode_shapes", {}).items():
            mode_num = int(mode_str)
            result.mode_shapes[mode_num] = {}
            for tag_str, disp in shapes.items():
                result.mode_shapes[mode_num][int(tag_str)] = tuple(disp)
        return result
    raise ValueError(f"Tipo de análisis desconocido: {analysis_type}")
