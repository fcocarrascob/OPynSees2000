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
