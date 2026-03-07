# Step 7: Remover Lógica de Auto-Mass Silenciosa en analysis_runner.py

## Goal
Eliminar el código que automáticamente asigna masa unitaria (1.0) a nodos sin masa en `run_modal_analysis()`. Con el nuevo sistema DEAD + densidad, la masa se calcula desde el peso propio vía `script_generator.py`.

## Prerequisites
Steps 1–6 completados y commiteados. Estás en la branch `fix/sap2000-load-pattern-validation`.

---

### Step-by-Step Instructions

#### 7.1 — Modificar `_modal_analysis_commands` en `analysis_runner.py`

- [ ] Abrir `gui/core/analysis_runner.py`
- [ ] Localizar la función `_modal_analysis_commands` (línea ~75) y reemplazar **completa** con:

**Buscar:**
```python
def _modal_analysis_commands(
    model: StructuralModel, n_modes: int, system: str
) -> str:
    # Nodes without mass that are not fully fixed
    nodes_needing_mass = [
        tag for tag, node in model.nodes.items()
        if not node.is_fixed and not node.mass
    ]

    # Mass pattern: translational DOFs = 1.0, rotational = 0
    if model.ndf == 6:
        mass_str = "1.0, 1.0, 1.0, 1e-9, 1e-9, 1e-9"
    elif model.ndf == 3:
        mass_str = "1.0, 1.0, 1e-9"
    else:
        mass_str = ", ".join(["1.0"] * model.ndf)

    lines = [
        "",
        "# " + "=" * 58,
        "# ANÁLISIS MODAL",
        "# " + "=" * 58,
    ]

    # Auto-assign unit mass if no masses defined
    if nodes_needing_mass:
        lines.append("# Masas unitarias automáticas (nodos sin masa definida)")
        for tag in nodes_needing_mass:
            lines.append(f"ops.mass({tag}, {mass_str})")
        lines.append("")

    lines.extend([
        f"ops.system('{system}')",
        "ops.numberer('RCM')",
        "ops.constraints('Plain')",
        f"eigenvalues = ops.eigen({n_modes})",
    ])
```

**Reemplazar con:**
```python
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
```

**NOTA:** El resto de la función (extracción de resultados con mode_shapes, eigenvalues, etc.) **no cambia**. Solo se elimina el bloque de asignación de masas unitarias automáticas.

---

### Step 7 Verification Checklist
- [ ] No hay errores de import al ejecutar `python -c "from gui.core.analysis_runner import run_modal_analysis"`
- [ ] **Modelo demo (DEAD + densidad):** Ejecutar análisis modal → completado exitosamente con períodos realistas
- [ ] **Modelo sin DEAD ni masas:** Ejecutar análisis modal → bloqueado por validación (Step 5), nunca llega a `analysis_runner`
- [ ] Verificar que el log de análisis **NO** muestra "Masas unitarias automáticas"
- [ ] Los períodos modales del modelo demo ahora reflejan masas realistas (no unitarias)
- [ ] Resultados modal: T₁ debe estar en rango razonable para pórtico 3D de concreto (ej: 0.1–1.0 s)

---

### Step 7 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Mensaje de commit sugerido:
```
fix(analysis): remove silent auto-mass assignment in modal analysis

- Remove automatic unit mass (1.0) assignment to nodes without mass
- Masses are now calculated from DEAD pattern via script_generator
- Pre-analysis validation ensures mass exists before running modal
```

---

## Final Integration Testing

Después de completar todos los steps, realizar estas pruebas de integración:

### Test 1: Workflow Completo - Modelo Nuevo
1. Archivo → Nuevo modelo
2. Verificar DEAD existe en árbol (tag=1, mult=1.0)
3. Definir material con densidad 2400 kg/m³
4. Definir sección con material_tag=1
5. Crear nodos (con restricciones en base)
6. Crear elementos
7. Exportar script → verificar masas y cargas gravitacionales
8. Ejecutar análisis modal → períodos coherentes
9. Guardar como .opss
10. Cerrar y reabrir → todo persiste correctamente

### Test 2: Compatibilidad Backward
1. Abrir archivo .opss versión 1 (anterior a cambios)
2. Verificar notificación "sin patrón DEAD" en consola
3. Verificar que patrones existentes tienen mult=0.0
4. Verificar que materiales tienen density=0.0
5. Verificar que secciones tienen material_tag=None

### Test 3: Protecciones
1. Intentar eliminar DEAD → error
2. Intentar editar multiplicador de DEAD → bloqueado
3. Intentar análisis sin nodos → error descriptivo
4. Intentar análisis modal sin masa → error descriptivo
