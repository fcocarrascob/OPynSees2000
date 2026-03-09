# Multi-Selección y Filtros (Multi-Select and Selection Filters)

**Branch:** `feature/multi-select-filters`
**Description:** Implementar selección múltiple (box/fence), filtros de selección y operaciones bulk tipo SAP2000

## Goal
Transformar el flujo de trabajo de "uno a la vez" a "muchos a la vez" mediante herramientas de selección avanzadas. Similar a SAP2000: arrastrar ventana para seleccionar 50 nodos → Assign → Fixed (vs. 50 × [click → assign → click → assign...]).

**Impacto UX:** Operaciones en 100 elementos reducidas de 100 × 5 clicks = 500 a 10 clicks totales.

---

## Implementation Steps

### Step 1: Multi-Selection Data Structure
**Files:**
- `gui/viewport/vtk_widget.py`

**What:**
Reemplazar variables de selección única por conjuntos:
```python
# Cambiar de:
self.selected_node: Optional[int] = None
self.selected_element: Optional[int] = None

# A:
self.selected_nodes: Set[int] = set()
self.selected_elements: Set[int] = set()
```

Actualizar métodos:
- `highlight_selection()`: iterar sobre sets y crear múltiples actores amarillos
- `clear_selection()`: limpiar ambos sets
- Click behavior:
  - **Simple click**: Reemplazar selección (clear + add)
  - **Ctrl+Click**: Toggle (add/remove sin clear)
  - **Shift+Click**: Extender selección (add)

**Testing:**
- Click nodo N1 → solo N1 seleccionado
- Ctrl+Click N2 → N1 y N2 seleccionados (2 esferas amarillas)
- Click N3 → solo N3 seleccionado (N1, N2 deseleccionados)
- Shift+Click N4 → N3 y N4 seleccionados

---

### Step 2: Box Selection Tool
**Files:**
- `gui/viewport/vtk_widget.py`
- `gui/main_window.py` (toolbar button)

**What:**
Implementar modo "Box Select" (estilo CAD):
1. **Activación:** Botón toolbar "□ Box Select" o shortcut `B`
2. **Interacción:**
   - Click-drag en viewport → dibujar rectángulo en pantalla (overlay 2D)
   - Usar `vtkAreaPicker` o custom screen-space logic
   - Al soltar: seleccionar todos los nodos/elementos dentro del rectángulo
   - **Windowing rules** (SAP2000 style):
     - **Left-to-right drag** (azul): selecciona completamente dentro
     - **Right-to-left drag** (verde): selecciona tocando borde también
3. **Rendering:**
   - Dibujar rectángulo temporal usando `QRubberBand` o overlay actor
   - Color según dirección: azul (L→R) o verde (R→L)

**Algorithm:**
```python
def get_items_in_box(self, screen_rect, mode='inside'):
    # Convert all node/element positions to screen coordinates
    # Check if within screen_rect
    # mode='inside': only if fully inside
    # mode='crossing': if touches or inside
    selected = set()
    for tag, node in self.model.nodes.items():
        screen_pos = self.world_to_screen(node.x, node.y, node.z)
        if screen_rect.contains(screen_pos):  # (or intersects for crossing)
            selected.add(tag)
    return selected
```

**Testing:**
- Activar Box Select
- Arrastrar L→R sobre 5 nodos → verificar 5 seleccionados (esferas amarillas)
- Arrastrar R→L parcialmente sobre elementos → verificar crossing selection
- ESC → volver a modo Select normal

---

### Step 3: Selection Filters
**Files:**
- `gui/main_window.py` (nuevo panel/toolbar)

**What:**
Implementar sistema de filtros de selección (SAP2000 tiene "Select" menu con filtros):

**Toolbar "Filtros de Selección":**
- Checkboxes: `☑ Nodos` `☑ Elementos` (toggle qué puede seleccionarse)
- Dropdown: "Filtros Rápidos":
  - "Seleccionar todos los nodos"
  - "Seleccionar todos los elementos"
  - "Seleccionar nodos sin restricción" (fixity == (0,0,0,0,0,0))
  - "Seleccionar nodos empotrados" (fixity == (1,1,1,1,1,1))
  - "Seleccionar elementos sin sección asignada" (section_tag == None)
  - "Seleccionar por Z = ..." (dialog input)
  - "Invertir selección"

**Implementation:**
```python
def select_by_filter(self, filter_name):
    self.clear_selection()
    if filter_name == "Nodos sin restricción":
        for tag, node in self.model.nodes.items():
            if node.fixity == (0,0,0,0,0,0):
                self.selected_nodes.add(tag)
    elif filter_name == "Elementos sin sección":
        for tag, elem in self.model.elements.items():
            if elem.section_tag is None:
                self.selected_elements.add(tag)
    # ... más filtros
    self.highlight_selection()
```

**Testing:**
- Crear modelo con 10 nodos (5 empotrados, 5 libres)
- Menú → "Seleccionar nodos empotrados" → verificar 5 conos verdes resaltados
- Menú → "Invertir selección" → verificar 5 esferas rojas resaltadas
- Crear elementos sin sección → Select filter → verificar que destacan

---

### Step 4: Bulk Operations on Selection
**Files:**
- `gui/viewport/vtk_widget.py`
- `gui/dialogs/fixity_dialog.py`, `nodal_load_dialog.py`

**What:**
Modificar diálogos existentes para operar sobre selección múltiple:

**FixityDialog:**
- Al abrir, pre-seleccionar checkboxes para nodos en `self.viewport.selected_nodes`
- Label informativo: "Aplicando a 15 nodos seleccionados"
- Botón "Deseleccionar todos" / "Seleccionar todos"

**NodalLoadDialog:**
- Similar: pre-populate con nodos seleccionados
- Al aplicar, iterar sobre todos → crear `NodalLoad` para cada uno

**Context Menu Enhancement:**
- "Asignar Restricción" → si múltiples nodos seleccionados, aplicar a todos
- "Cambiar Sección" → si múltiples elementos seleccionados, aplicar a todos

**Undo Handling:**
```python
# Usar CompoundUndoCommand para bulk ops
commands = []
for node_tag in selected_nodes:
    cmd = DictChangeCommand(...)
    commands.append(cmd)
compound = CompoundUndoCommand(commands, description="Bulk fixity assignment")
undo_manager.execute(compound)
```

**Testing:**
- Box select 20 nodos
- Right-click → "Empotrado" → verificar que TODOS se empotraron
- Undo → verificar que TODOS volvieron a estado anterior (single undo)
- Select 10 elementos → Change section → verificar bulk update

---

### Step 5: Selection Info Panel
**Files:**
- `gui/main_window.py`

**What:**
Agregar panel informativo para selección múltiple (SAP2000 tiene "Selection Information" en statusbar):

**Status Bar Widget:**
```
Seleccionados: 15 nodos, 8 elementos | Total: 150 nodos, 240 elementos
```

**Optional: Detailed Panel (dockable):**
- Lista de tags seleccionados
- Botón "Deseleccionar todos"
- Botón "Seleccionar similares" (misma sección, mismo material, etc.)
- Estadísticas: min/max Z, centro de gravedad de selección

**Testing:**
- Seleccionar 5 nodos → ver "Seleccionados: 5 nodos, 0 elementos"
- Ctrl+Click 3 elementos → ver "Seleccionados: 5 nodos, 3 elementos"
- Clear selection → ver "Seleccionados: 0 nodos, 0 elementos"

---

### Step 6: Advanced Selection Modes
**Files:**
- `gui/viewport/vtk_widget.py`
- `gui/main_window.py` (toolbar)

**What:**
Implementar modos de selección adicionales:

**1. Fence Select (Polyline):**
- Click puntos para dibujar polígono
- Double-click para cerrar
- Seleccionar items dentro del polígono (2D screen space)

**2. Select by Plane:**
- "Seleccionar todo en Z = 3.5m" (tolerance ±0.1m)
- Útil para seleccionar todos nodos de un piso

**3. Grow Selection:**
- Botón "Crecer Selección" → expandir a nodos/elementos conectados
- Iterativo: presionar múltiples veces para crecer en niveles

**4. Select Connected:**
- Select elemento → "Seleccionar conectados" → todos elementos que comparten nodos

**Testing:**
- Fence select: dibujar polígono alrededor de región → verificar selección
- Select Z=0 → verificar solo nodos de base seleccionados
- Select elemento E1 → Grow → verificar elementos conectados resaltados

---

## Impact Summary
**Antes:**
- Asignar 50 nodos como empotrados: 50 × [Click → Menú → Dialog → Check → OK] = 250 clicks
- Cambiar sección de 30 elementos: 30 × 6 clicks = 180 clicks

**Después:**
- Box select región → Right-click → Empotrado (3 clicks para 50 nodos)
- Filter "Sin sección" → Select all → Right-click → Section → IPE300 (5 clicks para 100 elementos)

**UX similar a SAP2000:** ✅ Box/fence select, ✅ Selection filters, ✅ Bulk operations, ✅ Visual feedback

---

## Additional Notes
**Compatibility:**
- Mantener compatibilidad con single-click selection (current behavior)
- Multi-select es ADDITIVE al workflow existente, no breaking change

**Performance:**
- Para modelos grandes (1000+ nodos), optimizar highlight rendering:
  - Usar single merged PolyData para todos highlights
  - Throttle selection updates (debounce 50ms)

**Future Enhancement:**
- Selection sets (named groups): "Columnas Piso 1", "Vigas Principales", etc.
- Save in project file for reuse
