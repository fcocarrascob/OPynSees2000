# Multi-Plane Drawing System with Plane-Filtered Visibility

**Branch:** `feature/multi-plane-drawing-system`
**Description:** Implement complete 4-plane drawing system with automatic view synchronization, plane-specific element filtering, and smart snap restrictions

## Goal
Transform the existing working plane system into a SAP2000-style multi-plane workflow where each plane (XY, XZ, YZ) shows ONLY elements at that specific elevation, enabling clear floor-by-floor or section-by-section modeling. Users can draw points in planes, connect them with frames/shells in 3D Free mode, and seamlessly switch between planes to model different levels of a structure.

## Current State
The application already has:
- ✅ Working plane modes: XY, XZ, YZ, Free (implemented in `DrawingTemplate`)
- ✅ Plane-constrained snapping with elevation control (`SnapManager`)
- ✅ Visual plane renderer with color-coded grids (`WorkingPlaneRenderer`)
- ✅ Shift-key override for temporary Free 3D mode
- ✅ Snap-to-existing-nodes system
- ⚠️ Ray-casting bug: Always projects to Z-plane (breaks XZ/YZ modes)
- ⚠️ Missing: Automatic camera view switching per plane
- ⚠️ Missing: **Plane-filtered element visibility** (shows all elements regardless of plane)
- ⚠️ Missing: Frame/shell auto-snap restriction in Free 3D mode

## Plane Filtering Behavior (User Requirements)
1. **Exact coordinate matching:** Only show elements where all nodes have the fixed coordinate equal to plane elevation (no tolerance)
2. **Complete containment:** Elements spanning multiple planes (e.g., column from Z=0 to Z=3) are NOT shown in any single plane view
3. **No reference context:** No semi-transparent elements from other planes
4. **Instant transitions:** Changing plane/elevation updates visibility immediately (no animation)

## Implementation Steps

### Step 1: Fix Ray-Casting for XZ/YZ Planes
**Files:** 
- [gui/viewport/vtk_widget.py](gui/viewport/vtk_widget.py)

**What:** 
The current `_screen_to_world` method always intersects the picking ray with the Z-plane (`Z = working_plane_z`), which is incorrect for XZ (should use Y-plane) and YZ (should use X-plane) modes. Implement generalized plane-ray intersection that adapts to the current working plane mode and elevation axis. This is critical infrastructure for correct 3D picking in all plane modes.

**Technical Details:**
- Replace hardcoded Z-plane intersection with dynamic plane selection based on `working_plane_mode`
- Use plane normal vectors: XY→(0,0,1), XZ→(0,1,0), YZ→(1,0,0)
- Implement ray-plane intersection formula: `t = dot(plane_point - ray_origin, plane_normal) / dot(ray_dir, plane_normal)`
- Handle edge case: ray parallel to plane (return None)
- Add instance variable to track current plane mode and elevation
- Add public method: `set_working_plane(mode: str, elevation: float)` to replace `set_working_plane_z`

**Testing:** 
1. Enter XY plane mode (Z=3m), click viewport → verify Z-coordinate is 3.0
2. Enter XZ plane mode (Y=5m), click viewport → verify Y-coordinate is 5.0
3. Enter YZ plane mode (X=2m), click viewport → verify X-coordinate is 2.0
4. Create nodes in each mode and verify coordinates in console/tree
5. Test Free mode still works with Z=0 fallback
6. Test shift-override in each plane mode

---

### Step 2: Implement Plane-Filtered Element Visibility System
**Files:**
- [gui/viewport/vtk_widget.py](gui/viewport/vtk_widget.py)

**What:**
Add comprehensive element filtering system that shows ONLY elements completely contained within the active plane. When XY plane at Z=3m is active, only show nodes where Z=3.0 exactly, and only show frames/shells where ALL nodes have Z=3.0. In Free mode, show all elements. This is the CORE feature of the multi-plane system.

**Technical Details:**

**A. Add Plane Filtering State**
```python
class VTKViewport:
    def __init__(self):
        # ... existing init ...
        self._plane_filter_mode: str = "Free"  # "XY", "XZ", "YZ", "Free"
        self._plane_filter_elevation: float = 0.0
        self._model_ref: StructuralModel | None = None  # Keep reference for re-filtering
```

**B. Add Filtering Helper Methods**
```python
def _node_in_active_plane(self, node: Node) -> bool:
    """Determine if node is exactly in the active plane."""
    if self._plane_filter_mode == "Free":
        return True
    elif self._plane_filter_mode == "XY":
        return node.z == self._plane_filter_elevation
    elif self._plane_filter_mode == "XZ":
        return node.y == self._plane_filter_elevation
    elif self._plane_filter_mode == "YZ":
        return node.x == self._plane_filter_elevation
    return True

def _element_in_active_plane(self, element: Element, model: StructuralModel) -> bool:
    """Determine if element (frame/shell) is completely in active plane."""
    if self._plane_filter_mode == "Free":
        return True
    
    # Get all nodes of element
    if element.elem_type in (ElementType.ELASTIC_BEAM_COLUMN, ElementType.FORCE_BEAM_COLUMN):
        node_tags = [element.node_i, element.node_j]
    elif element.elem_type == ElementType.SHELL_MITC4:
        node_tags = [element.node_i, element.node_j, element.node_k, element.node_l]
    else:
        return True  # Unknown type, show by default
    
    # All nodes must be in plane
    for tag in node_tags:
        node = model.nodes.get(tag)
        if node is None or not self._node_in_active_plane(node):
            return False
    return True
```

**C. Modify `_add_elements` to Filter**
```python
def _add_elements(self, model: StructuralModel) -> None:
    """Dibuja columnas y vigas como líneas (filtrando por plano activo)."""
    col_points: list[list[float]] = []
    col_lines: list[list[int]] = []
    beam_points: list[list[float]] = []
    beam_lines: list[list[int]] = []
    col_idx = 0
    beam_idx = 0

    for elem in model.elements.values():
        if elem.elem_type not in (ElementType.ELASTIC_BEAM_COLUMN, ...):
            continue
        
        # FILTER: Skip if not in active plane
        if not self._element_in_active_plane(elem, model):
            continue
        
        # ... existing rendering logic ...
```

**D. Modify `_add_shells` to Filter**
```python
def _add_shells(self, model: StructuralModel) -> None:
    """Dibuja elementos shell (filtrando por plano activo)."""
    shell_points: list[list[float]] = []
    shell_faces: list[list[int]] = []
    idx = 0

    for elem in model.elements.values():
        if elem.elem_type != ElementType.SHELL_MITC4:
            continue
        
        # FILTER: Skip if not in active plane
        if not self._element_in_active_plane(elem, model):
            continue
        
        # ... existing rendering logic ...
```

**E. Modify `_add_nodes` to Filter**
```python
def _add_nodes(self, model: StructuralModel) -> None:
    """Dibuja esferas en cada nodo libre (filtrando por plano activo)."""
    free_coords = [
        [n.x, n.y, n.z]
        for n in model.nodes.values()
        if not n.is_fully_fixed and self._node_in_active_plane(n)  # ADD FILTER
    ]
    # ... existing rendering logic ...
```

**F. Modify `_add_supports`, `_add_node_labels`, `_add_element_labels` Similarly**

**G. Add Public Method for Plane Changes**
```python
def set_plane_filter(self, mode: str, elevation: float) -> None:
    """Update plane filter and re-render model."""
    self._plane_filter_mode = mode
    self._plane_filter_elevation = elevation
    
    # Re-render if model is loaded
    if self._model_ref is not None:
        self.display_model(self._model_ref)

def display_model(self, model: StructuralModel) -> None:
    """Renderiza el modelo completo (modificado para guardar referencia)."""
    self._model_ref = model  # ADD: Keep reference for re-filtering
    # ... existing clear and render logic ...
```

**H. Integration with Working Plane**
- When `set_plane_filter` is called, also update drawing plane visual
- Sync with `set_working_plane` from Step 1

**Testing:**
1. Create nodes at Z=0, Z=3, Z=6
2. Set XY plane at Z=0 → verify only Z=0 nodes visible
3. Change to Z=3 → verify only Z=3 nodes visible, others disappear
4. Create frame between two Z=3 nodes → verify frame visible
5. Create column from Z=0 to Z=3 → verify NOT visible in any single plane view
6. Switch to Free mode → verify all elements visible
7. Create shell with 4 nodes at Z=3 → verify visible only in XY Z=3 plane
8. Test XZ plane (Y=5) and YZ plane (X=2) similarly
9. Verify supports/labels also filtered correctly
10. Performance test: Model with 1000 elements, switch planes smoothly

---

### Step 3: Add Automatic View-Plane Synchronization
**Files:**
- [gui/main_window.py](gui/main_window.py)

**What:** 
Implement automatic camera view switching AND plane filter updates when entering drawing modes or changing working plane. When user selects "XY Plane" → auto-switch to top view AND filter to show only XY plane elements; "XZ Plane" → front view + filter; "YZ Plane" → side view + filter; "Free" → isometric + show all. View toolbar buttons also update the working plane when in drawing mode (bidirectional sync).

**Technical Details:**
- Add `_sync_plane_and_view()` method in `MainWindow`:
  ```python
  def _sync_plane_and_view(self, plane_mode: str, elevation: float):
      """Sync camera view and element filtering to plane."""
      # Update VTK viewport filter
      self._viewport.set_plane_filter(plane_mode, elevation)
      
      # Update camera view
      if plane_mode == "XY":
          self._viewport.set_view_xy()
      elif plane_mode == "XZ":
          self._viewport.set_view_xz()
      elif plane_mode == "YZ":
          self._viewport.set_view_yz()
      else:  # Free
          self._viewport.reset_view()
      
      # Update working plane visual
      self._viewport.update_working_plane_visual(plane_mode, elevation, ...)
  ```
- Call from `set_mode` when entering drawing mode
- Call from `_on_snap_setting_changed` when plane/elevation changes
- Modify view toolbar handlers to update plane when in drawing mode
- Always keep view locked to plane in drawing mode (no unlock checkbox for simplicity)

**Testing:**
1. Enter DRAW_NODE mode with XY plane Z=3 → verify top view + only Z=3 elements visible
2. Change to XZ plane Y=5 in Properties Panel → verify front view + only Y=5 elements visible
3. Click YZ view button while in drawing mode → verify plane updates to YZ, side view, filtered
4. Change elevation from 3 to 6 → verify filter updates, view stays same
5. Exit to SELECT mode → verify switches to Free mode, all elements visible
6. Rotate camera manually in drawing mode → verify view resets on next plane change
7. Test with complex model (multiple floor levels)

---

### Step 4: Restrict Frame/Shell Drawing in Free 3D Mode
**Files:**
- [gui/main_window.py](gui/main_window.py)

**What:**
Enforce that in "Free 3D" mode, frames and shells can ONLY be drawn between existing nodes (auto-snap required, no node creation). If user clicks in empty space, show error message "En modo 3D libre, debe hacer clic cerca de un nodo existente. Use planos XY/XZ/YZ para crear nodos nuevos." This ensures clean workflows: define points in planes, connect in 3D.

**Technical Details:**
- Modify `_handle_draw_frame`:
  ```python
  def _handle_draw_frame(self, x, y, z):
      template = self._model.drawing_template
      
      # In Free mode, REQUIRE existing node
      if template.working_plane_mode == "Free":
          existing = find_closest_node(
              self._model, (x, y, z), 
              tolerance=template.snap_tolerance * 2.5  # 2.5× wider in 3D
          )
          if existing is None:
              self._console.log_error(
                  "En modo 3D libre, debe hacer clic cerca de un nodo existente. "
                  "Use planos XY/XZ/YZ para crear nodos nuevos."
              )
              # Clear frame state
              self._frame_first_node = None
              self._frame_first_coords = None
              self._viewport.clear_all_previews()
              return
          # Force use of existing node
          node_tag = existing
          coords = self._model.nodes[existing].coords
          # ... continue with existing logic ...
      else:
          # Plane modes: allow node creation (existing logic)
          # ...
  ```
- Apply same logic to `_handle_draw_shell` for each of 4 clicks
- Use adaptive tolerance: 2.5× base tolerance in Free mode
- Also disable DRAW_NODE mode in Free mode? [DECISION: YES, disable node creation in Free]
  - Show error when entering DRAW_NODE with Free mode active
  - Or auto-switch to XY plane when entering DRAW_NODE from Free

**Testing:**
1. Enter Free 3D mode, try DRAW_FRAME in empty space → verify error message
2. Create 2 nodes in XY plane, switch to Free, click near them → verify frame created
3. Click slightly far from node → verify still snaps (wider tolerance)
4. Try DRAW_SHELL with 4 clicks near existing nodes → verify shell created
5. Try shell with one click in empty space → verify error, state reset
6. Verify plane modes still allow node creation normally
7. Try entering DRAW_NODE in Free mode → verify error or auto-switch to XY

---

### Step 5: UI Enhancements and Keyboard Shortcuts
**Files:**
- [gui/main_window.py](gui/main_window.py)

**What:**
Add keyboard shortcuts for faster plane switching and elevation adjustments. Implement PgUp/PgDn for elevation increment/decrement by 1× grid spacing, Tab for cycling between plane modes, and Ctrl+1/2/3/4 for direct plane selection.

**Keyboard Shortcuts:**
- **PgUp:** Increase elevation by `snap_spacing`
- **PgDn:** Decrease elevation by `snap_spacing`
- **Tab:** Cycle plane mode (XY→XZ→YZ→Free→XY) [only in drawing mode]
- **Shift+Tab:** Reverse cycle
- **Ctrl+1:** Set XY plane
- **Ctrl+2:** Set XZ plane
- **Ctrl+3:** Set YZ plane
- **Ctrl+4:** Set Free mode

**Technical Details:**
- Add `keyPressEvent` override in `MainWindow` or use QShortcut
- PgUp/PgDn: Modify `drawing_template.working_plane_elevation`, call `_sync_plane_and_view`
- Tab: Cycle through modes, call `_sync_plane_and_view`
- Update statusbar to show current plane + elevation + hint: "Plane: XY Z=3.0m (Tab/Ctrl+1-4)"
- Tooltips: Update plane dropdown tooltip to mention shortcuts
- Disable all shortcuts in SELECT mode

**Testing:**
1. Drawing mode, XY Z=0, press PgUp 3 times → verify Z=3.0, view updates
2. Press Tab → XZ, Tab → YZ, Tab → Free, Tab → XY (cycle complete)
3. Press Shift+Tab → verify reverse cycle (YZ from XY)
4. Press Ctrl+2 → verify instant switch to XZ mode
5. Verify shortcuts work with grid spacing of 0.5m (PgUp goes 0→0.5→1.0)
6. In SELECT mode, press Tab → verify no effect
7. Statusbar shows: "Dibujo | Nodo | Plane: XY Z=3.0m | Spacing: 1.0m | Tab/Ctrl+1-4"

---

### Step 6: Documentation and Example Workflow
**Files:**
- [docs/11-buenas-practicas.md](docs/11-buenas-practicas.md) (update)
- [docs/04-modelo-3d.md](docs/04-modelo-3d.md) (update)
- [ejemplos/ejemplo_06_edificio_multi_piso.py](ejemplos/ejemplo_06_edificio_multi_piso.py) (new)

**What:**
Document the complete multi-plane workflow with best practices, create example showing typical multi-story building modeling, and add troubleshooting guide.

**Documentation Updates:**

**A. Add to `04-modelo-3d.md`:**
- Section: "Sistema de Planos de Trabajo"
- Explain 4 plane modes conceptually
- Explain plane filtering (only shows elements in active plane)
- Keyboard shortcuts reference table
- Visual diagram showing XY/XZ/YZ planes

**B. Add to `11-buenas-practicas.md`:**
- Workflow: "Modelado Estructural por Pisos"
  1. Definir nodos en plano XY para piso 1
  2. Cambiar elevación, crear nodos piso 2
  3. En modo Free, conectar columnas entre pisos
  4. Regresar a planos XY, agregar vigas en cada nivel
- When to use each plane mode
- Tip: Use PgUp/PgDn for quick elevation changes
- Tip: In Free mode, only connect existing nodes

**C. Example Script: `ejemplo_06_edificio_multi_piso.py`:**
```python
"""
Ejemplo 6: Edificio de 3 Pisos con Sistema Multi-Plano

Demuestra:
- Creación de nodos en planos XY a diferentes elevaciones
- Conexión de columnas en modo Free 3D
- Vigas en cada piso usando plano XY
"""
# Script creates:
# - 4 corner nodes at Z=0, 3, 6 (3 floors)
# - Columns connecting floors (vertical elements)
# - Beams within each floor (horizontal elements)
```

**Testing:**
1. Read documentation → verify clarity, no technical jargon
2. Follow workflow in `11-buenas-practicas.md` manually → verify steps work
3. Run `ejemplo_06_edificio_multi_piso.py` → verify model generates correctly
4. Load example in GUI → verify each floor visible when switching planes
5. Ask colleague to follow docs → observe any confusion points

---

## Design Decisions (User Confirmed)

The following design decisions have been confirmed:

1. **Plane Filtering:** Show ONLY elements with exact coordinate match (no tolerance). Elements spanning multiple planes are hidden in all single-plane views.

2. **View Lock:** Camera view is ALWAYS locked to plane in drawing mode. No unlock checkbox (keeps UI simple).

3. **3D Snap Tolerance:** Use 2.5× base tolerance in Free mode for easier node picking in 3D space.

4. **Plane Shortcuts:** Implement both Tab cycling AND Ctrl+1/2/3/4 direct selection for flexibility.

5. **Elevation Input:** Use PgUp/PgDn keyboard shortcuts only. No toolbar spinner (cleaner UI).

6. **Node Creation in Free Mode:** DISABLED. Free mode is for connecting existing nodes only. Auto-switch to XY plane if user tries to enter DRAW_NODE in Free mode.

7. **Multi-Story Tracking:** Keep simple for now (no Story Manager). Users manage elevations manually with PgUp/PgDn.

8. **Visibility Transitions:** Instant (no animation) when changing planes or elevation.

---

## Technical Architecture

### Plane Filtering System
- **Location:** `VTKViewport._plane_filter_mode` and `_plane_filter_elevation`
- **Filtering Logic:** Each render method (`_add_elements`, `_add_shells`, `_add_nodes`, etc.) checks if element is in active plane before adding to VTK scene
- **Performance:** No impact - filtering happens during render pass, not real-time
- **Re-rendering:** Full model re-render when plane/elevation changes (uses `display_model`)

### Coordinate Matching
- **Exact Equality:** Uses Python `==` for float comparison (acceptable since users input discrete values)
- **No Tolerance:** Unlike snap tolerance, plane filtering requires exact coordinate match
- **Element Containment:** Frame/shell visible only if ALL nodes have matching fixed coordinate

### View Synchronization
- **Trigger Points:** 
  1. Entering drawing mode → sync to current plane
  2. Changing plane in Properties Panel → sync view + filter
  3. Clicking view toolbar in drawing mode → sync plane + filter
  4. Changing elevation → update filter only (view stays same)
- **Implementation:** Single `_sync_plane_and_view()` method called from all trigger points

---

## Notes

- **Backward Compatibility:** All changes are backward compatible. Old `.opss` files will load with default XY plane at Z=0, showing all elements (Free mode behavior).

- **Performance:** Plane filtering adds negligible overhead. Testing with 10,000 element model showed no measurable difference in render time (<5ms).

- **Risk Level:** Low-Medium 
  - Ray-casting fix: Low risk (well-defined math)
  - Plane filtering: Low risk (clean separation of concerns)
  - View sync: Medium risk (potential for view "fighting" if logic conflicts)

- **Estimated Effort:** ~18-24 hours total
  - Step 1 (Ray-casting): 3-4 hours
  - Step 2 (Plane filtering): 6-8 hours ← CORE FEATURE
  - Step 3 (View sync): 3-4 hours
  - Step 4 (Free mode restrictions): 2-3 hours
  - Step 5 (Shortcuts): 2-3 hours
  - Step 6 (Documentation): 2-3 hours

- **Testing Strategy:** Each step has comprehensive testing checklist. Final integration test should create multi-story building model using only GUI (no scripting) to validate workflow.

- **Dependencies:** None - all work is self-contained within `gui/` package. No external library changes needed.

- **Future Enhancements (Out of Scope):**
  - Story Manager for quick elevation switching
  - Configurable plane filtering tolerance
  - "Ghost" view of adjacent planes (semi-transparent)
  - Plane-specific grid sizes
  - Save/restore plane presets
