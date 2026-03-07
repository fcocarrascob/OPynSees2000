# Sprint 4: Generación de Script + Ejecución de Análisis

## Goal
Generar scripts OpenSeesPy completos a partir del modelo GUI, ejecutar análisis estático y modal, capturar resultados (desplazamientos, reacciones, eigenvalores) y visualizar la deformada en el viewport.

## Prerequisites
Sprint 3 completado y commiteado. Branch `feat/gui-sap2000-workflow`.  
**Dependencia externa:** `openseespy` debe estar instalado para ejecutar análisis (`pip install openseespy`).

---

### Step-by-Step Instructions

---

#### Step 9: Generador de Script OpenSeesPy

- [x] Crear `gui/core/script_generator.py`
- [x] Crear `gui/dialogs/script_preview_dialog.py`
- [x] Modificar `gui/main_window.py` para habilitar Archivo → Exportar script...

##### 9A. Crear `gui/core/script_generator.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Generador de scripts OpenSeesPy.

Recorre el StructuralModel y produce un string con código Python
válido que usa openseespy.opensees para replicar el modelo completo.
"""

from __future__ import annotations

from textwrap import dedent

from gui.core.model_data import (
    ElementType,
    MaterialType,
    SectionType,
    StructuralModel,
    TransfType,
)


def generate_script(model: StructuralModel, include_analysis: bool = False) -> str:
    """
    Genera un script OpenSeesPy completo a partir del modelo.

    Parameters
    ----------
    model : StructuralModel
        Modelo a convertir.
    include_analysis : bool
        Si True, incluye comandos básicos de análisis estático al final.

    Returns
    -------
    str
        Código Python listo para ejecutar.
    """
    lines: list[str] = []

    # --- Header ---
    lines.append('"""')
    lines.append("Script generado por OPynSees2000")
    lines.append("Sistema de unidades: kN, m, s, °C")
    lines.append('"""')
    lines.append("")
    lines.append("import openseespy.opensees as ops")
    lines.append("")
    lines.append("# " + "=" * 58)
    lines.append("# INICIALIZACIÓN")
    lines.append("# " + "=" * 58)
    lines.append("ops.wipe()")
    lines.append(f"ops.model('basic', '-ndm', {model.ndm}, '-ndf', {model.ndf})")
    lines.append("")

    # --- Nodos ---
    if model.nodes:
        lines.append("# " + "=" * 58)
        lines.append("# NODOS")
        lines.append("# " + "=" * 58)
        for tag in sorted(model.nodes.keys()):
            node = model.nodes[tag]
            if model.ndm == 3:
                lines.append(
                    f"ops.node({tag}, {node.x}, {node.y}, {node.z})"
                )
            else:
                lines.append(
                    f"ops.node({tag}, {node.x}, {node.y})"
                )
        lines.append("")

    # --- Restricciones (fixity) ---
    fixed_nodes = [
        (tag, n) for tag, n in sorted(model.nodes.items()) if n.is_fixed
    ]
    if fixed_nodes:
        lines.append("# " + "=" * 58)
        lines.append("# RESTRICCIONES")
        lines.append("# " + "=" * 58)
        for tag, node in fixed_nodes:
            fix_args = ", ".join(str(f) for f in node.fixity)
            lines.append(f"ops.fix({tag}, {fix_args})")
        lines.append("")

    # --- Materiales ---
    if model.materials:
        lines.append("# " + "=" * 58)
        lines.append("# MATERIALES")
        lines.append("# " + "=" * 58)
        for tag in sorted(model.materials.keys()):
            mat = model.materials[tag]
            lines.append(f"# {mat.name}")
            lines.append(_material_command(tag, mat.mat_type, mat.params))
        lines.append("")

    # --- Secciones ---
    if model.sections:
        lines.append("# " + "=" * 58)
        lines.append("# SECCIONES")
        lines.append("# " + "=" * 58)
        for tag in sorted(model.sections.keys()):
            sec = model.sections[tag]
            lines.append(f"# {sec.name}")
            lines.append(_section_command(tag, sec.sec_type, sec.params))
        lines.append("")

    # --- Transformaciones geométricas ---
    if model.geom_transfs:
        lines.append("# " + "=" * 58)
        lines.append("# TRANSFORMACIONES GEOMÉTRICAS")
        lines.append("# " + "=" * 58)
        for tag in sorted(model.geom_transfs.keys()):
            transf = model.geom_transfs[tag]
            vx, vy, vz = transf.vecxz
            lines.append(
                f"ops.geomTransf('{transf.transf_type.value}', {tag}, "
                f"{vx}, {vy}, {vz})"
            )
        lines.append("")

    # --- Elementos ---
    if model.elements:
        lines.append("# " + "=" * 58)
        lines.append("# ELEMENTOS")
        lines.append("# " + "=" * 58)
        for tag in sorted(model.elements.keys()):
            elem = model.elements[tag]
            lines.append(_element_command(tag, elem, model))
        lines.append("")

    # --- Patrones de carga y cargas ---
    if model.load_patterns:
        lines.append("# " + "=" * 58)
        lines.append("# PATRONES DE CARGA")
        lines.append("# " + "=" * 58)
        for pat_tag in sorted(model.load_patterns.keys()):
            pat = model.load_patterns[pat_tag]
            ts_tag = pat_tag  # TimeSeries tag = pattern tag
            lines.append(f"# Patrón: {pat.name}")
            lines.append(
                f"ops.timeSeries('{pat.time_series_type}', {ts_tag})"
            )
            lines.append(f"ops.pattern('Plain', {pat_tag}, {ts_tag})")

            for load in pat.loads:
                args = (
                    f"{load.fx}, {load.fy}, {load.fz}, "
                    f"{load.mx}, {load.my}, {load.mz}"
                )
                lines.append(f"ops.load({load.node_tag}, {args})")
            lines.append("")

    # --- Análisis estático básico (opcional) ---
    if include_analysis:
        lines.append("# " + "=" * 58)
        lines.append("# ANÁLISIS ESTÁTICO")
        lines.append("# " + "=" * 58)
        lines.append("ops.system('BandSPD')")
        lines.append("ops.numberer('RCM')")
        lines.append("ops.constraints('Plain')")
        lines.append("ops.algorithm('Linear')")
        lines.append("ops.integrator('LoadControl', 1.0)")
        lines.append("ops.analysis('Static')")
        lines.append("ok = ops.analyze(1)")
        lines.append("print(f'Análisis completado: {\"OK\" if ok == 0 else \"ERROR\"}')")
        lines.append("")
        lines.append("# Desplazamientos de todos los nodos")
        lines.append("for tag in ops.getNodeTags():")
        lines.append("    disp = ops.nodeDisp(tag)")
        lines.append("    print(f'  Nodo {tag}: {disp}')")
        lines.append("")

    # --- Footer ---
    lines.append("print('Script ejecutado exitosamente.')")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------
# Helpers — Comandos específicos por tipo
# ---------------------------------------------------------------

def _material_command(tag: int, mat_type: MaterialType, params: dict) -> str:
    """Genera el comando ops.uniaxialMaterial(...)."""
    if mat_type == MaterialType.ELASTIC:
        E = params.get("E", 200e6)
        return f"ops.uniaxialMaterial('Elastic', {tag}, {E})"
    elif mat_type == MaterialType.STEEL02:
        Fy = params.get("Fy", 420_000)
        E0 = params.get("E0", 200e6)
        b = params.get("b", 0.01)
        R0 = params.get("R0", 18.0)
        cR1 = params.get("cR1", 0.925)
        cR2 = params.get("cR2", 0.15)
        return (
            f"ops.uniaxialMaterial('Steel02', {tag}, "
            f"{Fy}, {E0}, {b}, {R0}, {cR1}, {cR2})"
        )
    elif mat_type == MaterialType.CONCRETE01:
        fpc = params.get("fpc", -28_000)
        epsc0 = params.get("epsc0", -0.002)
        fpcu = params.get("fpcu", -5_600)
        epsU = params.get("epsU", -0.005)
        return (
            f"ops.uniaxialMaterial('Concrete01', {tag}, "
            f"{fpc}, {epsc0}, {fpcu}, {epsU})"
        )
    elif mat_type == MaterialType.CONCRETE02:
        fpc = params.get("fpc", -28_000)
        epsc0 = params.get("epsc0", -0.002)
        fpcu = params.get("fpcu", -5_600)
        epsU = params.get("epsU", -0.005)
        lam = params.get("lambda_", 0.1)
        ft = params.get("ft", 2_800)
        Ets = params.get("Ets", 1_400_000)
        return (
            f"ops.uniaxialMaterial('Concrete02', {tag}, "
            f"{fpc}, {epsc0}, {fpcu}, {epsU}, {lam}, {ft}, {Ets})"
        )
    elif mat_type == MaterialType.ELASTIC_PP:
        E = params.get("E", 200e6)
        epsyP = params.get("epsyP", 0.002)
        return f"ops.uniaxialMaterial('ElasticPP', {tag}, {E}, {epsyP})"
    elif mat_type == MaterialType.HYSTERETIC:
        keys = ["s1p", "e1p", "s2p", "e2p", "s3p", "e3p",
                "s1n", "e1n", "s2n", "e2n", "s3n", "e3n",
                "pinchX", "pinchY", "damage1", "damage2", "beta"]
        args = ", ".join(str(params.get(k, 0.0)) for k in keys)
        return f"ops.uniaxialMaterial('Hysteretic', {tag}, {args})"
    return f"# Material tipo '{mat_type.value}' (tag={tag}) — no soportado"


def _section_command(tag: int, sec_type: SectionType, params: dict) -> str:
    """Genera el comando ops.section(...)."""
    if sec_type == SectionType.ELASTIC_2D:
        A = params.get("A", 0.1)
        E = params.get("E", 200e6)
        Iz = params.get("Iz", 1e-4)
        return f"ops.section('Elastic', {tag}, {E}, {A}, {Iz})"
    elif sec_type == SectionType.ELASTIC_3D:
        A = params.get("A", 0.1)
        E = params.get("E", 200e6)
        Iz = params.get("Iz", 1e-4)
        Iy = params.get("Iy", 1e-4)
        G = params.get("G", 80e6)
        J = params.get("J", 1e-4)
        return (
            f"ops.section('Elastic', {tag}, {E}, {A}, {Iz}, {Iy}, {G}, {J})"
        )
    elif sec_type == SectionType.FIBER:
        return f"# Sección Fiber (tag={tag}) — definición manual requerida"
    return f"# Sección tipo '{sec_type.value}' (tag={tag}) — no soportada"


def _element_command(tag: int, elem, model: StructuralModel) -> str:
    """Genera el comando ops.element(...)."""
    et = elem.elem_type

    if et == ElementType.ELASTIC_BEAM_COLUMN:
        # elasticBeamColumn requiere parámetros de sección directos
        sec = model.sections.get(elem.section_tag) if elem.section_tag else None
        if sec and sec.sec_type == SectionType.ELASTIC_3D:
            p = sec.params
            return (
                f"ops.element('elasticBeamColumn', {tag}, "
                f"{elem.node_i}, {elem.node_j}, "
                f"{p.get('A', 0)}, {p.get('E', 0)}, {p.get('G', 0)}, "
                f"{p.get('J', 0)}, {p.get('Iy', 0)}, {p.get('Iz', 0)}, "
                f"{elem.transf_tag})"
            )
        elif sec and sec.sec_type == SectionType.ELASTIC_2D:
            p = sec.params
            return (
                f"ops.element('elasticBeamColumn', {tag}, "
                f"{elem.node_i}, {elem.node_j}, "
                f"{p.get('A', 0)}, {p.get('E', 0)}, {p.get('Iz', 0)}, "
                f"{elem.transf_tag})"
            )
        # Fallback: referencia a sección
        return (
            f"ops.element('elasticBeamColumn', {tag}, "
            f"{elem.node_i}, {elem.node_j}, "
            f"'-section', {elem.section_tag}, {elem.transf_tag})"
        )

    elif et in (ElementType.FORCE_BEAM_COLUMN, ElementType.DISP_BEAM_COLUMN):
        cmd_name = et.value
        return (
            f"ops.element('{cmd_name}', {tag}, "
            f"{elem.node_i}, {elem.node_j}, "
            f"{elem.transf_tag}, {elem.section_tag})"
        )

    elif et in (ElementType.TRUSS, ElementType.COROT_TRUSS):
        cmd_name = et.value
        sec = model.sections.get(elem.section_tag) if elem.section_tag else None
        A = sec.params.get("A", 0.01) if sec else 0.01
        mat_tag = 1  # default — truss necesita material, no sección
        return (
            f"ops.element('{cmd_name}', {tag}, "
            f"{elem.node_i}, {elem.node_j}, {A}, {mat_tag})"
        )

    elif et == ElementType.SHELL_MITC4:
        node_k = getattr(elem, "node_k", None) or 0
        node_l = getattr(elem, "node_l", None) or 0
        return (
            f"ops.element('ShellMITC4', {tag}, "
            f"{elem.node_i}, {elem.node_j}, {node_k}, {node_l}, "
            f"{elem.section_tag})"
        )

    return f"# Elemento tipo '{et.value}' (tag={tag}) — no soportado"
```

##### 9B. Crear `gui/dialogs/script_preview_dialog.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Diálogo de previsualización del script OpenSeesPy generado.

Muestra el código en un editor de texto de solo lectura con
opción de copiar al portapapeles o exportar a archivo .py.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from gui.core.model_data import StructuralModel
from gui.core.script_generator import generate_script


class ScriptPreviewDialog(QDialog):
    """Diálogo para previsualizar y exportar el script OpenSeesPy."""

    def __init__(
        self,
        parent=None,
        model: StructuralModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Script OpenSeesPy — Previsualización")
        self.setMinimumSize(700, 550)

        self._model = model or StructuralModel()

        layout = QVBoxLayout(self)

        # Opciones
        self._chk_analysis = QCheckBox("Incluir análisis estático básico")
        self._chk_analysis.setChecked(False)
        self._chk_analysis.stateChanged.connect(self._regenerate)
        layout.addWidget(self._chk_analysis)

        # Editor de texto (solo lectura)
        self._editor = QPlainTextEdit()
        self._editor.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(font)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._editor)

        # Info de líneas
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #757575; padding: 2px;")
        layout.addWidget(self._info_label)

        # Botones
        btn_layout = QHBoxLayout()

        btn_copy = QPushButton("Copiar al portapapeles")
        btn_copy.clicked.connect(self._on_copy)
        btn_layout.addWidget(btn_copy)

        btn_export = QPushButton("Exportar a .py")
        btn_export.clicked.connect(self._on_export)
        btn_layout.addWidget(btn_export)

        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("flat", "true")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        # Generar script inicial
        self._regenerate()

    def _regenerate(self) -> None:
        """Regenera el script y actualiza el editor."""
        include = self._chk_analysis.isChecked()
        self._script = generate_script(self._model, include_analysis=include)
        self._editor.setPlainText(self._script)
        n_lines = self._script.count("\n") + 1
        self._info_label.setText(f"{n_lines} líneas generadas")

    def _on_copy(self) -> None:
        """Copia el script al portapapeles."""
        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self._script)
        self._info_label.setText("✔ Copiado al portapapeles")
        self._info_label.setStyleSheet("color: #388E3C; padding: 2px;")

    def _on_export(self) -> None:
        """Exporta el script a un archivo .py."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar script OpenSeesPy",
            "",
            "Python (*.py);;Todos los archivos (*.*)",
        )
        if not path:
            return
        Path(path).write_text(self._script, encoding="utf-8")
        self._info_label.setText(f"✔ Exportado: {Path(path).name}")
        self._info_label.setStyleSheet("color: #388E3C; padding: 2px;")

    def get_script(self) -> str:
        """Retorna el script generado actual."""
        return self._script
```

##### 9C. Modificar `gui/main_window.py` — Exportar script

- [x] Agregar import:

```python
from gui.dialogs.script_preview_dialog import ScriptPreviewDialog
```

- [x] En `_build_menubar`, en el menú Archivo, agregar antes del separador previo a "Salir":

Agregar estas líneas antes de `m_file.addSeparator()` (el que precede a Salir):

```python
        m_file.addSeparator()

        act_export = QAction("Exportar script OpenSeesPy...", self)
        act_export.setShortcut(QKeySequence("Ctrl+E"))
        act_export.setToolTip("Generar y previsualizar script OpenSeesPy")
        act_export.triggered.connect(self._on_export_script)
        m_file.addAction(act_export)
```

- [x] Agregar slot:

```python
    def _on_export_script(self) -> None:
        """Abre el diálogo de previsualización del script."""
        dlg = ScriptPreviewDialog(self, model=self._model)
        dlg.exec()
```

##### Step 9 Verification Checklist

- [ ] Cargar demo → Archivo → Exportar script OpenSeesPy... → se abre diálogo de previsualización
- [ ] Verificar que el script contiene: `ops.wipe()`, `ops.model()`, `ops.node()`, `ops.fix()`, `ops.section()`, `ops.geomTransf()`, `ops.element()`
- [ ] Marcar checkbox "Incluir análisis estático" → script se regenera con `ops.analyze(1)`
- [ ] "Copiar al portapapeles" → pegar en editor → script válido
- [ ] "Exportar a .py" → guardar como `test_script.py` → ejecutar con `python test_script.py` desde un entorno con openseespy → sin errores
- [ ] Modelo nuevo con Shell → el script genera `ops.element('ShellMITC4', ...)`
- [ ] Modelo con cargas → script genera `ops.timeSeries()`, `ops.pattern()`, `ops.load()`

#### Step 9 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: add OpenSeesPy script generator with preview

- Create script_generator.py covering all model objects
- Support all material types, section types, element types
- ScriptPreviewDialog with syntax preview, copy, and export
- Optional static analysis commands
- Add Archivo > Exportar script (Ctrl+E)"
```

---

#### Step 10: Ejecución de Análisis y Resultados

- [x] Crear `gui/core/analysis_runner.py`
- [x] Crear `gui/dialogs/analysis_dialog.py`
- [x] Modificar `gui/core/model_data.py` para agregar `AnalysisResult`
- [x] Modificar `gui/viewport/vtk_widget.py` para visualizar deformada
- [x] Modificar `gui/main_window.py` para habilitar menú Analizar

##### 10A. Modificar `gui/core/model_data.py` — AnalysisResult

- [x] Agregar al final del archivo (antes de `StructuralModel`), la siguiente dataclass:

```python
@dataclass
class AnalysisResult:
    """Resultado de un análisis."""
    analysis_type: str  # "static" o "modal"

    # Estático
    node_displacements: dict[int, tuple[float, ...]] = field(default_factory=dict)
    node_reactions: dict[int, tuple[float, ...]] = field(default_factory=dict)

    # Modal
    eigenvalues: list[float] = field(default_factory=list)
    periods: list[float] = field(default_factory=list)
    frequencies: list[float] = field(default_factory=list)
    mode_shapes: dict[int, dict[int, tuple[float, ...]]] = field(default_factory=dict)
    # mode_shapes[mode_num][node_tag] = (dx, dy, dz, rx, ry, rz)

    @property
    def n_modes(self) -> int:
        return len(self.eigenvalues)
```

##### 10B. Crear `gui/core/analysis_runner.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
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
    lines = [
        "",
        "# " + "=" * 58,
        "# ANÁLISIS MODAL",
        "# " + "=" * 58,
        f"ops.system('{system}')",
        "ops.numberer('RCM')",
        "ops.constraints('Plain')",
        f"eigenvalues = ops.eigen({n_modes})",
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
    ]
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
```

##### 10C. Crear `gui/dialogs/analysis_dialog.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Diálogo de configuración y ejecución de análisis.

Permite seleccionar tipo de análisis (estático/modal),
configurar parámetros, ejecutar, y ver resultados.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.core.analysis_runner import run_modal_analysis, run_static_analysis
from gui.core.model_data import AnalysisResult, StructuralModel


class AnalysisWorker(QThread):
    """Thread para ejecutar el análisis sin bloquear la GUI."""

    finished = Signal(bool, object, str)  # (ok, result, log)

    def __init__(
        self,
        model: StructuralModel,
        analysis_type: str,
        params: dict,
    ) -> None:
        super().__init__()
        self._model = model
        self._analysis_type = analysis_type
        self._params = params

    def run(self) -> None:
        try:
            if self._analysis_type == "static":
                ok, result, log = run_static_analysis(
                    self._model,
                    system=self._params.get("system", "BandSPD"),
                    algorithm=self._params.get("algorithm", "Linear"),
                )
            elif self._analysis_type == "modal":
                ok, result, log = run_modal_analysis(
                    self._model,
                    n_modes=self._params.get("n_modes", 6),
                    system=self._params.get("system", "BandSPD"),
                )
            else:
                ok, result, log = False, None, "Tipo de análisis no soportado."
            self.finished.emit(ok, result, log)
        except Exception as e:
            self.finished.emit(False, None, f"Error inesperado: {e}")


class AnalysisDialog(QDialog):
    """Diálogo para configurar y ejecutar análisis."""

    # Señal emitida cuando hay resultados disponibles
    analysis_complete = Signal(object)  # AnalysisResult

    def __init__(
        self,
        parent=None,
        model: Optional[StructuralModel] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ejecutar análisis")
        self.setMinimumSize(650, 500)

        self._model = model or StructuralModel()
        self._worker: Optional[AnalysisWorker] = None
        self._result: Optional[AnalysisResult] = None

        layout = QVBoxLayout(self)

        # --- Tabs ---
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Tab: Configuración
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)

        grp_type = QGroupBox("Tipo de análisis")
        type_form = QFormLayout()
        grp_type.setLayout(type_form)

        self._type_combo = QComboBox()
        self._type_combo.addItem("Estático lineal", "static")
        self._type_combo.addItem("Modal (eigenvalores)", "modal")
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_form.addRow("Tipo:", self._type_combo)

        config_layout.addWidget(grp_type)

        # Parámetros de análisis
        grp_params = QGroupBox("Parámetros")
        self._params_form = QFormLayout()
        grp_params.setLayout(self._params_form)

        self._system_combo = QComboBox()
        for sys_name in ("BandSPD", "BandGeneral", "ProfileSPD",
                         "UmfPack", "SparseSYM"):
            self._system_combo.addItem(sys_name)
        self._params_form.addRow("Sistema:", self._system_combo)

        self._algo_combo = QComboBox()
        for algo in ("Linear", "Newton", "ModifiedNewton", "KrylovNewton"):
            self._algo_combo.addItem(algo)
        self._algo_lbl = QLabel("Algoritmo:")
        self._params_form.addRow(self._algo_lbl, self._algo_combo)

        self._modes_spin = QSpinBox()
        self._modes_spin.setRange(1, 50)
        self._modes_spin.setValue(6)
        self._modes_lbl = QLabel("Nº de modos:")
        self._params_form.addRow(self._modes_lbl, self._modes_spin)

        config_layout.addWidget(grp_params)

        # Info del modelo
        grp_info = QGroupBox("Modelo")
        info_form = QFormLayout()
        grp_info.setLayout(info_form)
        info_form.addRow("Nodos:", QLabel(str(len(self._model.nodes))))
        info_form.addRow("Elementos:", QLabel(str(len(self._model.elements))))
        info_form.addRow("Materiales:", QLabel(str(len(self._model.materials))))
        info_form.addRow("Patrones:", QLabel(str(len(self._model.load_patterns))))
        config_layout.addWidget(grp_info)

        config_layout.addStretch()
        tabs.addTab(config_widget, "Configuración")

        # Tab: Resultados / Log
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)

        self._results_label = QLabel("Sin resultados. Ejecute un análisis.")
        self._results_label.setWordWrap(True)
        self._results_label.setStyleSheet("padding: 8px;")
        log_layout.addWidget(self._results_label)

        self._log_edit = QPlainTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setPlaceholderText("Log de ejecución...")
        log_layout.addWidget(self._log_edit)

        tabs.addTab(log_widget, "Resultados")

        # --- Progress + Botones ---
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminado
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        btn_layout = QHBoxLayout()
        self._btn_run = QPushButton("▶ Ejecutar análisis")
        self._btn_run.setStyleSheet(
            "font-weight: bold; padding: 8px 16px;"
        )
        self._btn_run.clicked.connect(self._on_run)
        btn_layout.addWidget(self._btn_run)

        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("flat", "true")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        # Configurar visibilidad inicial
        self._on_type_changed()

    # ---------------------------------------------------------------

    def _on_type_changed(self) -> None:
        """Ajusta campos según tipo de análisis."""
        is_static = self._type_combo.currentData() == "static"
        self._algo_combo.setVisible(is_static)
        self._algo_lbl.setVisible(is_static)
        self._modes_spin.setVisible(not is_static)
        self._modes_lbl.setVisible(not is_static)

    def _on_run(self) -> None:
        """Ejecuta el análisis en un thread."""
        analysis_type = self._type_combo.currentData()
        params = {
            "system": self._system_combo.currentText(),
            "algorithm": self._algo_combo.currentText(),
            "n_modes": self._modes_spin.value(),
        }

        self._btn_run.setEnabled(False)
        self._progress.setVisible(True)
        self._results_label.setText("Ejecutando análisis...")
        self._log_edit.clear()

        self._worker = AnalysisWorker(self._model, analysis_type, params)
        self._worker.finished.connect(self._on_analysis_finished)
        self._worker.start()

    def _on_analysis_finished(
        self, ok: bool, result: AnalysisResult | None, log: str
    ) -> None:
        """Callback cuando el análisis termina."""
        self._btn_run.setEnabled(True)
        self._progress.setVisible(False)
        self._log_edit.setPlainText(log)

        if ok and result:
            self._result = result
            self._show_results(result)
            self.analysis_complete.emit(result)
        else:
            self._results_label.setText(
                "❌ Error en el análisis. Revise el log para detalles."
            )
            self._results_label.setStyleSheet(
                "color: #D32F2F; padding: 8px; font-size: 13px;"
            )

    def _show_results(self, result: AnalysisResult) -> None:
        """Presenta los resultados en la pestaña."""
        lines = []

        if result.analysis_type == "static":
            lines.append("✔ ANÁLISIS ESTÁTICO COMPLETADO\n")
            lines.append("Desplazamientos nodales (primeros 20):")
            for i, (tag, disp) in enumerate(
                sorted(result.node_displacements.items())
            ):
                if i >= 20:
                    lines.append(f"  ... y {len(result.node_displacements) - 20} más")
                    break
                disp_str = ", ".join(f"{d:+.6f}" for d in disp[:3])
                lines.append(f"  Nodo {tag}: [{disp_str}] m")

            if result.node_reactions:
                lines.append("\nReacciones en apoyos:")
                for tag, rxn in sorted(result.node_reactions.items()):
                    rxn_str = ", ".join(f"{r:+.2f}" for r in rxn[:3])
                    lines.append(f"  Nodo {tag}: [{rxn_str}] kN")

        elif result.analysis_type == "modal":
            lines.append("✔ ANÁLISIS MODAL COMPLETADO\n")
            lines.append(
                f"{'Modo':>5} | {'Período [s]':>12} | "
                f"{'Frecuencia [Hz]':>15} | {'ω² (eigenval)':>15}"
            )
            lines.append("-" * 55)
            for i, (T, f, ev) in enumerate(
                zip(result.periods, result.frequencies, result.eigenvalues), 1
            ):
                lines.append(
                    f"{i:>5} | {T:>12.4f} | {f:>15.4f} | {ev:>15.4f}"
                )

        self._results_label.setText("\n".join(lines))
        self._results_label.setStyleSheet(
            "color: #212121; padding: 8px; font-family: Consolas; "
            "font-size: 12px; background: #FAFAFA;"
        )

    def get_result(self) -> Optional[AnalysisResult]:
        return self._result
```

##### 10D. Modificar `gui/viewport/vtk_widget.py` — Visualizar Deformada

- [x] Agregar un import de AnalysisResult. Después de los imports existentes, agregar dentro del bloque `if TYPE_CHECKING`:

```python
    from gui.core.model_data import AnalysisResult
```

- [x] Agregar método `display_deformed` a la clase `VTKViewport`:

```python
    def display_deformed(
        self,
        model: StructuralModel,
        result: "AnalysisResult",
        scale: float = 50.0,
        mode: int | None = None,
    ) -> None:
        """
        Muestra la deformada del modelo.

        Parameters
        ----------
        model : StructuralModel
        result : AnalysisResult
        scale : float
            Factor de amplificación de desplazamientos.
        mode : int | None
            Número de modo (para análisis modal). None = estático.
        """
        # Obtener desplazamientos según tipo
        if mode is not None and result.mode_shapes:
            disps = result.mode_shapes.get(mode, {})
        else:
            disps = result.node_displacements

        if not disps:
            return

        # Construir coordenadas deformadas
        deformed_points: list[list[float]] = []
        deformed_lines: list[list[int]] = []
        idx = 0

        for elem in model.elements.values():
            ni = model.nodes.get(elem.node_i)
            nj = model.nodes.get(elem.node_j)
            if not ni or not nj:
                continue

            # Desplazamientos
            di = disps.get(elem.node_i, (0, 0, 0, 0, 0, 0))
            dj = disps.get(elem.node_j, (0, 0, 0, 0, 0, 0))

            p1 = [ni.x + di[0] * scale, ni.y + di[1] * scale, ni.z + di[2] * scale]
            p2 = [nj.x + dj[0] * scale, nj.y + dj[1] * scale, nj.z + dj[2] * scale]

            deformed_points.extend([p1, p2])
            deformed_lines.append([2, idx, idx + 1])
            idx += 2

        if deformed_points:
            cells = np.hstack(deformed_lines)
            mesh = pv.PolyData(
                np.array(deformed_points, dtype=float),
                lines=cells,
            )
            self.plotter.add_mesh(
                mesh,
                color="#FF6F00",   # ámbar oscuro
                line_width=3,
                render_lines_as_tubes=True,
                opacity=0.9,
                name="deformed",
            )

        # Esferas en nodos deformados
        node_pts = []
        for tag, node in model.nodes.items():
            d = disps.get(tag, (0, 0, 0))
            node_pts.append([
                node.x + d[0] * scale,
                node.y + d[1] * scale,
                node.z + d[2] * scale,
            ])
        if node_pts:
            cloud = pv.PolyData(np.array(node_pts, dtype=float))
            glyphs = cloud.glyph(
                geom=pv.Sphere(radius=0.08),
                orient=False,
                scale=False,
            )
            self.plotter.add_mesh(
                glyphs,
                color="#FF6F00",
                opacity=0.8,
                name="deformed_nodes",
            )
```

- [ ] Agregar método `clear_deformed`:

```python
    def clear_deformed(self) -> None:
        """Elimina la visualización de deformada."""
        self.plotter.remove_actor("deformed", render=False)
        self.plotter.remove_actor("deformed_nodes", render=False)
```

##### 10E. Modificar `gui/main_window.py` — Habilitar Menú Analizar

- [x] Agregar imports:

```python
from gui.dialogs.analysis_dialog import AnalysisDialog
from gui.core.model_data import AnalysisResult
```

- [x] Agregar atributo al `__init__`:

```python
        self._analysis_result: AnalysisResult | None = None
```

- [x] En `_build_menubar`, reemplazar los tres bloques del menú Analizar.

Reemplazar:
```python
        act_static = QAction("Análisis estático...", self)
        act_static.setEnabled(False)
        m_analyze.addAction(act_static)

        act_modal = QAction("Análisis modal...", self)
        act_modal.setEnabled(False)
        m_analyze.addAction(act_modal)

        act_run = QAction("Ejecutar análisis", self)
        act_run.setShortcut(QKeySequence("F5"))
        act_run.setEnabled(False)
        m_analyze.addAction(act_run)
```
Con:
```python
        act_analysis = QAction("Configurar y ejecutar...", self)
        act_analysis.setShortcut(QKeySequence("F5"))
        act_analysis.setToolTip("Abrir diálogo de análisis (F5)")
        act_analysis.triggered.connect(self._on_open_analysis)
        m_analyze.addAction(act_analysis)

        m_analyze.addSeparator()

        self._act_show_deformed = QAction("Mostrar deformada", self)
        self._act_show_deformed.setCheckable(True)
        self._act_show_deformed.setEnabled(False)
        self._act_show_deformed.toggled.connect(self._on_toggle_deformed)
        m_analyze.addAction(self._act_show_deformed)
```

- [x] Agregar slots de análisis:

```python
    def _on_open_analysis(self) -> None:
        """Abre el diálogo de análisis."""
        if not self._model.nodes:
            self._console.log_error("El modelo está vacío.")
            return
        dlg = AnalysisDialog(self, model=self._model)
        dlg.analysis_complete.connect(self._on_analysis_result)
        dlg.exec()

    def _on_analysis_result(self, result: AnalysisResult) -> None:
        """Callback cuando hay resultados de análisis."""
        self._analysis_result = result
        self._act_show_deformed.setEnabled(True)
        self._act_show_deformed.setChecked(True)

        if result.analysis_type == "static":
            n_disp = len(result.node_displacements)
            self._console.log_success(
                f"Análisis estático completado: {n_disp} nodos con desplazamientos."
            )
        elif result.analysis_type == "modal":
            self._console.log_success(
                f"Análisis modal completado: {result.n_modes} modos."
            )
            if result.periods:
                T1 = result.periods[0]
                self._console.log(f"  Período fundamental T₁ = {T1:.4f} s")

    def _on_toggle_deformed(self, checked: bool) -> None:
        """Toggle de visualización de deformada."""
        if checked and self._analysis_result:
            self._viewport.display_model(self._model)
            self._viewport.display_deformed(self._model, self._analysis_result)
            self._console.log("Deformada mostrada (escala 50x).")
        else:
            self._viewport.clear_deformed()
            self._viewport.display_model(self._model)
            self._console.log("Deformada ocultada.")
```

##### Step 10 Verification Checklist

- [ ] Cargar demo → F5 (Analizar → Configurar y ejecutar...) → tipo "Estático lineal" → Ejecutar
- [ ] Verificar que el progress bar se muestra durante la ejecución
- [ ] Verificar que la pestaña "Resultados" muestra desplazamientos nodales y reacciones
- [ ] Verificar que la deformada (líneas ámbar) aparece superpuesta al modelo original
- [ ] Cambiar a tipo "Modal" → 6 modos → Ejecutar → verificar períodos y frecuencias
- [ ] Toggle "Mostrar deformada" → ON/OFF → deformada aparece/desaparece
- [ ] Ejecutar desde modelo vacío → error "El modelo está vacío."
- [ ] Si openseespy no está instalado → error claro en el log
- [ ] Verificar que la GUI no se congela durante la ejecución (thread separado)

#### Step 10 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: add analysis execution with results visualization

- Create analysis_runner.py for subprocess-based analysis
- AnalysisDialog with static/modal configuration tabs
- Thread-based execution to keep GUI responsive
- Display deformed shape (amber overlay, scale 50x)
- Parse displacements, reactions, eigenvalues, and mode shapes
- Add F5 shortcut for quick analysis access
- AnalysisResult dataclass for structured results storage"
```

---

## Sprint 4 Complete

Al finalizar Sprint 4, la GUI ES FUNCIONAL de extremo a extremo:

| Feature | Estado |
|---------|--------|
| Exportar script OpenSeesPy | ✅ Preview + copiar + exportar .py |
| Análisis estático lineal | ✅ En subprocess, resultados en GUI |
| Análisis modal (eigenvalores) | ✅ Períodos, frecuencias, formas modales |
| Visualización de deformada | ✅ Toggle, overlay ámbar 50x |
| Thread seguro | ✅ GUI no se congela |

**Pipeline COMPLETA:**
```
Definir → Dibujar → Asignar → Analizar → Resultados
```

**Archivos nuevos creados:** 4
- `gui/core/script_generator.py`
- `gui/core/analysis_runner.py`
- `gui/dialogs/script_preview_dialog.py`
- `gui/dialogs/analysis_dialog.py`

**Archivos modificados:** 3
- `gui/core/model_data.py` (AnalysisResult dataclass)
- `gui/viewport/vtk_widget.py` (display_deformed, clear_deformed)
- `gui/main_window.py` (menú Analizar funcional + F5 + deformada toggle)
