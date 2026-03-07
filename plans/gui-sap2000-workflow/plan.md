# OPynSees2000 — GUI SAP2000-like Workflow

**Branch:** `feat/gui-sap2000-workflow`
**Description:** Implementación incremental de la pipeline completa Definir → Dibujar → Asignar → Analizar → Resultados, transformando la GUI actual (visor read-only) en una herramienta interactiva al estilo SAP2000.

## Goal

Convertir OPynSees2000 de un visor 3D de modelos demo a una interfaz funcional donde el usuario pueda crear modelos desde cero, definir propiedades, asignar condiciones, ejecutar análisis y visualizar resultados — siguiendo el flujo natural de SAP2000 pero con la potencia de OpenSeesPy detrás.

---

## Estado Actual (Baseline)

| Componente | Estado |
|------------|--------|
| Layout (menu, toolbar, splitters) | ✅ Funcional |
| Viewport 3D (PyVista) | ✅ Funcional (columnas, vigas, nodos, apoyos, grid) |
| Model Tree (read-only) | ✅ Funcional |
| Properties Panel (read-only) | ✅ Funcional |
| Consola de logs | ✅ Funcional |
| 13 acciones de menú | ❌ `setEnabled(False)` — placeholders |
| Persistencia (save/load) | ❌ No existe |
| Edición del modelo | ❌ No existe |
| Generación de scripts OpenSeesPy | ❌ No existe |
| Ejecución de análisis | ❌ No existe |

---

## Implementation Steps

---

### Step 1: Infraestructura — Serialización y Proyecto
**Files:**
- `gui/core/model_data.py` (agregar `to_dict()` / `from_dict()`)
- `gui/core/project_io.py` (nuevo — save/load JSON)
- `gui/main_window.py` (conectar Archivo → Guardar / Abrir)

**What:**
Implementar serialización JSON del `StructuralModel` completo para persistencia. Agregar acciones de menú "Guardar como..." (`Ctrl+S`), "Abrir..." (`Ctrl+O`) que lean/escriban archivos `.opss` (JSON). El modelo demo también se podrá guardar y recargar.

**Testing:**
1. Cargar demo → Guardar como `test.opss` → Nuevo modelo → Abrir `test.opss` → verificar que nodos/elementos/materiales coinciden.
2. Verificar que el JSON es legible y tiene estructura clara.

---

### Step 2: Diálogos de Definición — Materiales
**Files:**
- `gui/dialogs/material_dialog.py` (nuevo)
- `gui/main_window.py` (habilitar acción Materiales...)
- `gui/core/model_data.py` (posibles ajustes a los params por tipo)

**What:**
Diálogo modal para crear/editar materiales uniaxiales. ComboBox para seleccionar `MaterialType` (Elastic, Steel02, Concrete01, etc.) y campos dinámicos que aparecen según el tipo seleccionado. Botones Aceptar/Cancelar. Al aceptar, se agrega el material al `StructuralModel` y se refresca el tree.

**Testing:**
1. Menú Definir → Materiales → crear material Elastic con E=24821000 → verificar que aparece en el tree.
2. Cambiar tipo a Steel02 → verificar que aparecen campos Fy, E0, b, etc.
3. Doble-clic en tree sobre material existente → abre diálogo con valores precargados.

---

### Step 3: Diálogos de Definición — Secciones y Transformaciones
**Files:**
- `gui/dialogs/section_dialog.py` (nuevo)
- `gui/dialogs/transf_dialog.py` (nuevo)
- `gui/main_window.py` (habilitar acciones Secciones... y Transformaciones...)

**What:**
Dos diálogos modales similares al de materiales:
- **Secciones:** ComboBox con `SectionType`, campos dinámicos (A, E, Iz, Iy, G, J para Elastic3D; fibras para Fiber).
- **Transformaciones:** ComboBox con `TransfType` (Linear, PDelta, Corotational) y campos para `vecxz`.

**Testing:**
1. Crear sección Elastic3D con parámetros de columna → verificar en tree y properties.
2. Crear transformación PDelta → verificar vecxz en properties.

---

### Step 4: Dibujar — Nodos interactivos
**Files:**
- `gui/dialogs/node_dialog.py` (nuevo — diálogo de coordenadas)
- `gui/viewport/vtk_widget.py` (agregar picking/click-to-place)
- `gui/main_window.py` (habilitar acción Nodo..., modo de dibujo)
- `gui/core/model_data.py` (sin cambios esperados)

**What:**
Diálogo modal para agregar nodos: Menú Dibujar → Nodo → ingreso manual de coordenadas (X, Y, Z). Opción de agregar múltiples nodos en secuencia (botón "Agregar otro"). Tag auto-incremental. Al aceptar, el nodo se agrega al modelo, se refresca viewport y tree. El viewport muestra etiquetas de nodos (tag numérico).

> **Decisión:** Solo diálogo de coordenadas. El modo click-to-place interactivo se deja como mejora futura.

**Testing:**
1. Dibujar → Nodo → ingresar (5, 0, 3.5) → verificar esfera roja nueva en viewport.
2. Verificar que el tag es auto-incremental.
3. Verificar etiqueta visible junto al nodo.

---

### Step 5: Dibujar — Elementos (conectar nodos)
**Files:**
- `gui/dialogs/element_dialog.py` (nuevo)
- `gui/viewport/vtk_widget.py` (agregar selección de nodos / highlight)
- `gui/main_window.py` (habilitar acción Elemento...)

**What:**
Diálogo para crear elementos frame/truss: seleccionar tipo (`ElementType`), nodo I, nodo J (por tag), sección y transformación desde ComboBox que lista las existentes. Validación: los nodos deben existir, la sección y transformación deben estar definidas.

Para **elementos Shell (ShellMITC4):** Diálogo separado que recibe 4 nodos (I, J, K, L) y una sección de shell. El viewport renderiza la superficie como un cuadrilátero con transparencia parcial.

> **Decisión:** Se incluyen frames, truss y Shell. Los shells se agregan como extensión en este mismo step.

**Testing:**
1. Crear elemento elasticBeamColumn entre nodo 1 y nodo 10 con sección 1 y transf 1 → verificar línea nueva en viewport.
2. Crear ShellMITC4 con 4 nodos → verificar superficie renderizada en viewport.
3. Intentar crear con nodo inexistente → error en consola.

---

### Step 6: Asignar — Restricciones (fixity)
**Files:**
- `gui/dialogs/fixity_dialog.py` (nuevo)
- `gui/main_window.py` (habilitar acción Restricciones...)

**What:**
Diálogo para asignar condiciones de borde a nodos. Selección de nodo(s) por tag, checkboxes para cada DOF (dx, dy, dz, rx, ry, rz), presets rápidos: Empotrado (1,1,1,1,1,1), Articulado (1,1,1,0,0,0), Libre (0,0,0,0,0,0). Aplicar actualiza `node.fixity` y refresca viewport (cono verde para fijos).

**Testing:**
1. Seleccionar nodo libre → asignar Empotrado → verificar cono verde en viewport.
2. Verificar en properties panel que fixity cambió.

---

### Step 7: Asignar — Cargas nodales y Patrones de carga
**Files:**
- `gui/dialogs/load_pattern_dialog.py` (nuevo)
- `gui/dialogs/nodal_load_dialog.py` (nuevo)
- `gui/viewport/vtk_widget.py` (agregar visualización de flechas de carga)
- `gui/main_window.py` (habilitar acciones Patrones de carga... y Cargas nodales...)

**What:**
1. **Patrón de carga:** Diálogo para crear `LoadPattern` (nombre, tipo de time series).
2. **Cargas nodales:** Diálogo para asignar fuerzas/momentos a nodos dentro de un patrón existente.
3. **Visualización:** Flechas 3D en los nodos cargados (color rojo para fuerzas, morado para momentos), con magnitud proporcional escalada.

**Testing:**
1. Crear patrón "Gravedad" → Asignar carga Fz=-100 kN al nodo 15 → verificar flecha en viewport.
2. Verificar que el tree muestra el patrón con sus cargas anidadas.

---

### Step 8: Viewport mejorado — Etiquetas, selección, visualización
**Files:**
- `gui/viewport/vtk_widget.py` (refactor mayor)
- `gui/viewport/picking.py` (nuevo — lógica de selección)
- `gui/main_window.py` (toolbar: toggle etiquetas, toggle cargas)

**What:**
Mejoras de visualización al estilo SAP2000:
- **Etiquetas:** Toggle para mostrar/ocultar tags de nodos y elementos.
- **Selección interactiva:** Click en nodo/elemento para seleccionarlo (highlight amarillo). La selección alimenta el properties panel.
- **Visualización de cargas:** Toggle para mostrar/ocultar flechas de carga.
- **Colores por tipo:** Columnas vs. vigas vs. arriostramientos con colores diferenciados.

**Testing:**
1. Activar etiquetas → verificar números visibles en nodos y elementos.
2. Click en un elemento → verificar highlight + properties panel actualizado.
3. Toggle cargas → verificar flechas visibles/ocultas.

---

### Step 9: Generación de script OpenSeesPy
**Files:**
- `gui/core/script_generator.py` (nuevo — genera código Python con OpenSeesPy)
- `gui/dialogs/script_preview_dialog.py` (nuevo — previsualización del script)
- `gui/main_window.py` (menú Archivo → Exportar script...)

**What:**
Recorre `StructuralModel` y genera un script Python válido que usa `openseespy.opensees` para replicar el modelo completo: `model()`, `node()`, `fix()`, `uniaxialMaterial()`, `section()`, `geomTransf()`, `element()`, `timeSeries()`, `pattern()`, `load()`. El script se puede previsualizar en un diálogo con syntax highlighting y exportar a `.py`.

**Testing:**
1. Cargar demo → Exportar script → Ejecutar script independientemente con `python script.py` → sin errores.
2. Comparar con ejemplos existentes en `ejemplos/` para validar sintaxis.

---

### Step 10: Ejecución de análisis y resultados
**Files:**
- `gui/core/analysis_runner.py` (nuevo — ejecuta OpenSeesPy en subprocess o in-process)
- `gui/dialogs/analysis_dialog.py` (nuevo — configuración de análisis)
- `gui/core/model_data.py` (agregar `AnalysisResult` dataclass)
- `gui/viewport/vtk_widget.py` (visualización de deformada)
- `gui/main_window.py` (habilitar menú Analizar)

**What:**
1. **Diálogo de análisis:** Selección de tipo (estático lineal o modal), parámetros (sistema, algoritmo, integrador, número de pasos/modos).
2. **Ejecución:** Genera script + comandos de análisis, ejecuta en subprocess Python con OpenSeesPy, captura resultados (desplazamientos, reacciones, eigenvalores).
3. **Resultados estáticos:** Deformada (malla desplazada escalada), reacciones en la consola.
4. **Resultados modales:** Períodos y frecuencias, formas modales visualizadas como deformada escalada por modo.

> **Decisión:** Se incluye análisis estático + modal. El espectro de respuesta se deja para un step posterior.

**Testing:**
1. Modelo demo → Ejecutar análisis estático con carga demo → verificar desplazamientos razonables.
2. Ejecutar análisis modal → verificar que muestra períodos y formas modales animadas.
3. F5 como atajo rápido.

---

### Step 11: Properties Panel editable + Undo/Redo
**Files:**
- `gui/panels/properties_panel.py` (refactor: campos editables)
- `gui/core/undo_manager.py` (nuevo — command pattern)
- `gui/main_window.py` (Ctrl+Z / Ctrl+Y, menú Editar)

**What:**
Convertir el properties panel de read-only a editable: al cambiar un valor y presionar Enter, se actualiza el modelo y se registra el cambio en el undo stack. El sistema de undo usa el patrón Command para almacenar operaciones reversibles (agregar/eliminar/modificar nodos, elementos, etc.).

**Testing:**
1. Seleccionar nodo → cambiar coordenada X → Enter → viewport actualizado.
2. Ctrl+Z → coordenada restaurada.
3. Ctrl+Y → re-apply.

---

### Step 12: Configuración de proyecto y dependencias
**Files:**
- `pyproject.toml` (nuevo — metadata del proyecto + dependencias)
- `requirements.txt` (nuevo — lock de dependencias)
- `.gitignore` (actualizar si necesario)
- `README.md` (actualizar con instrucciones de instalación)

**What:**
Crear `pyproject.toml` con metadata (nombre, versión, descripción, dependencias: PySide6, pyvista, pyvistaqt, numpy, openseespy). Generar `requirements.txt` desde el venv actual. Actualizar README con instrucciones de setup.

**Testing:**
1. `pip install -e .` desde un venv limpio → la app se instala y ejecuta.
2. `python -m gui` funciona tras la instalación.

---

## Diagrama de Dependencias entre Steps

```
Step 1 (Save/Load) ──────────────────────────────────────────┐
                                                              │
Step 2 (Materiales) ─────┐                                   │
                          ├── Step 3 (Secciones + Transf) ──┐│
Step 4 (Nodos) ──────────┤                                  ││
                          ├── Step 5 (Elementos) ───────────┤│
Step 6 (Restricciones) ──┘                                  ││
                                                             ├─── Step 9 (Script Gen)
Step 7 (Cargas) ─────────────────────────────────────────────┤    │
                                                             │    Step 10 (Análisis)
Step 8 (Viewport mejorado) ─────────────────────────────────┘         │
                                                                      │
Step 11 (Properties editable + Undo) ─── independiente ──────────────┘
Step 12 (pyproject.toml) ─── independiente
```

**Steps 1-7** son secuenciales y forman la pipeline core.
**Step 8** puede desarrollarse en paralelo con Steps 5-7.
**Steps 9-10** requieren Steps 1-7 completados.
**Steps 11-12** son independientes y pueden hacerse en cualquier momento.

---

## Prioridades sugeridas por sprint

| Sprint | Steps | Entregable |
|--------|-------|------------|
| Sprint 1 | 1, 2, 3 | Persistencia + Definición de propiedades |
| Sprint 2 | 4, 5, 6 | Dibujo de geometría + Restricciones |
| Sprint 3 | 7, 8 | Cargas + Viewport mejorado |
| Sprint 4 | 9, 10 | Script gen + Análisis |
| Sprint 5 | 11, 12 | Editing avanzado + Packaging |

---

## Puntos que necesitan clarificación

Todas las preguntas han sido resueltas:

1. **[Step 4] Nodos:** Solo diálogo de coordenadas. Click interactivo queda como mejora futura.
2. **[Step 10] Análisis:** Estático lineal + Modal. Espectro de respuesta queda para un step posterior.
3. **[General] Idioma:** Solo español. Sin i18n por ahora.
4. **[General] Elementos:** Se incluyen frames (beamColumn), truss y Shell (ShellMITC4). Los shells requieren un Step 5b adicional para el diálogo de mallado de áreas.
