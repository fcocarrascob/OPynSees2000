# SAP2000-Style Drawing Mode

**Branch:** `feature/sap2000-drawing-mode`
**Description:** Implement interactive element drawing in viewport with SAP2000-like workflow (select tool, click to draw, snap to grid, relative offsets)

## Goal
Add SAP2000-style drawing functionality where users can select a drawing mode (node, beam, column, shell) from the toolbar and create elements by clicking directly in the 3D viewport. Includes intelligent grid snapping for precision and relative coordinate offsets for repetitive geometry. This dramatically improves modeling workflow by enabling fast, accurate visual element placement.

## Implementation Steps

### Step 1: Mode System Foundation
**Files:** 
- gui/main_window.py
- gui/viewport/vtk_widget.py

**What:** 
Create an `InteractionMode` enum (SELECT, DRAW_NODE, DRAW_FRAME, DRAW_SHELL) and add mode tracking to MainWindow. Add mode switching infrastructure that properly enables/disables viewport picking based on mode. This establishes the foundation for all mode-based interactions. DRAW_FRAME handles all 2-node linear elements (beams, columns, braces, etc.).

**Testing:** 
- Add print statements to verify mode changes
- Ensure only one mode active at a time
- Verify viewport picking is disabled in draw modes

---

### Step 2: Grid Snap System (Invisible/Minimalist)
**Files:**
- gui/viewport/vtk_widget.py
- gui/main_window.py

**What:**
Implement minimalist grid snapping system with no visual clutter. Create `SnapManager` class that rounds coordinates to grid spacing (1.0 units default). Add single toolbar button `[Snap]` (checkable, ON by default) to enable/disable snapping. Add keyboard shortcut `F9` for quick toggle. Display snap status in status bar: "[SNAP ON] | Grid: 1.0". When snap is active and mouse moves during drawing, show subtle snap indicator (small cross/point) at nearest grid intersection.

**Testing:**
- Toggle snap button ON/OFF, verify status bar updates
- In draw mode, move mouse and verify snap indicator appears at grid intersections
- Click to create node, verify coordinates are rounded (e.g., 3.0, 5.0 not 3.14, 4.89)
- Disable snap, verify coordinates are exact click positions
- Test F9 keyboard shortcut toggles snap

---

### Step 3: Toolbar Mode Selection UI
**Files:**
- gui/main_window.py

**What:**
Add mutually exclusive toolbar buttons for each interaction mode using `QActionGroup`. Create checkable actions for "Select", "Draw Node", "Draw Frame", "Draw Shell" representing 0-click selection, 1-node elements, 2-node elements, and 4-node elements respectively. Connect toolbar actions to mode switching logic. Update status bar to show current mode and context-specific controls (offset fields for DRAW_NODE, etc.).

**Testing:**
- Click each toolbar button and verify visual feedback (checked state)
- Ensure only one mode button is checked at a time
- Verify status bar displays current mode name
- Test switching between modes repeatedly
- Verify offset fields appear in status bar only for DRAW_NODE mode

---

### Step 4: Viewport Mouse Event Handling & Coordinate Conversion
**Files:**
- gui/viewport/vtk_widget.py
- gui/viewport/picking.py (new utilities)

**What:**
Override `QtInteractor.mousePressEvent()` and `mouseMoveEvent()` to capture raw clicks in the viewport. Implement screen-to-world coordinate conversion using VTK camera rays and PyVista's picking system. Add working plane projection to constrain points to Z=0 by default (configurable elevation). Integrate snap system: apply snap_to_grid() to clicked coordinates when snap is enabled. Emit signals for mouse clicks with world coordinates.

**Testing:**
- Click in viewport and print world coordinates
- Verify coordinates match expected position in 3D space
- Test in different camera views (XY, XZ, YZ, ISO)
- With snap ON, verify coordinates align to grid (multiples of 1.0)
- With snap OFF, verify exact click positions
- Verify working plane constraint at Z=0

---

### Step 5: Preview Geometry Rendering
**Files:**
- gui/viewport/vtk_widget.py

**What:**
Add temporary geometry rendering for visual feedback during drawing. Implement `show_preview_node(coords)` to display semi-transparent sphere at mouse position (shows final position after offset). Implement `show_snap_indicator(coords)` to show small cross/point at snap intersection. Implement `show_preview_line(start_coords, end_coords, style='dashed')` to show preview line for frames/shells. Implement `show_offset_preview(base, final)` to show dotted line from click point to offset point. Implement `clear_preview()` to remove all temporary actors. Preview updates on mouse move in draw modes.

**Testing:**
- Enter DRAW_NODE mode, move mouse, verify snap indicator appears at grid points when snap ON
- Verify preview sphere shows final node position (with offset applied)
- Enter DRAW_FRAME mode, click first node, verify preview line stretches to cursor
- Enter DRAW_SHELL mode, verify progressive preview (1 line → L-shape → triangle → quad)
- Set offset (2,0,3) in node mode, verify dotted line from click to final position
- Verify preview clears when exiting draw mode
- Test preview rendering in all camera views

---

### Step 6: Draw Node Mode with Relative Offset
**Files:**
- gui/main_window.py
- gui/viewport/vtk_widget.py

**What:**
Implement complete DRAW_NODE mode with relative coordinate offset capability. Add status bar widgets: 3 QDoubleSpinBox for offset (ΔX, ΔY, ΔZ) with defaults (0, 0, 0). On viewport click: get world coords → apply snap (if enabled) → apply offset → create node at final position. Node formula: `final = (click.x + offset_x, click.y + offset_y, click.z + offset_z)`. Add node to model using `DictChangeCommand` for undo support. Show preview with dotted line from click point to final point when offset ≠ (0,0,0). Keep mode active for continuous creation. Add Escape key handler to return to SELECT mode. Add 'R' key to reset offset to (0,0,0).

**Testing:**
- Click "Draw Node" button, click multiple locations in viewport
- Verify nodes created at exact click positions when offset = (0,0,0)
- Set offset to (2, 0, 3), click at (5, 3, 0), verify node created at (7, 3, 3)
- Verify preview shows dotted line from base to offset point
- Create multiple nodes with same offset (e.g., column tops at Z+3)
- Test with snap ON: click near (5.3, 3.2) → snaps to (5, 3) → applies offset → (7, 3, 3)
- Test undo/redo for node creation
- Press R key, verify offset resets to (0, 0, 0)
- Press Escape, verify return to SELECT mode
- Verify nodes persist after viewport refresh

---

### Step 7: Draw Frame Mode Implementation (2-Node Elements)
**Files:**
- gui/main_window.py
- gui/viewport/vtk_widget.py
- gui/dialogs/element_dialog.py (enhanced for property defaults)

**What:**
Implement two-click sequence for DRAW_FRAME mode to create 2-node linear elements (beams, columns, braces). First click: snap to existing node (within tolerance 0.15 units) OR create new node at clicked coordinates. Second click: snap to existing/create second node and create frame element. Element type defaults to 'elasticBeamColumn' or last-used type. Property assignment: use last-selected section/transformation if available, otherwise create with None (user assigns later via Properties panel). Store element with auto-incremented tag using compound undo command (creates nodes + element as single action). Show preview line during second click. Reset to first click state for continuous drawing. Add Escape to cancel current element and return to first click.

**Testing:**
- Enter DRAW_FRAME mode
- Click first node (existing), click second position (new node)
- Verify frame element created connecting the two nodes
- Verify element appears in model tree and viewport with correct type
- Test clicking two existing nodes (within snap tolerance)
- Test clicking two new positions (creates 2 nodes + 1 element)
- Click first node, press Escape, verify cancels and resets to first click
- Test undo (Ctrl+Z) - should undo entire operation (element + created nodes)
- Test redo (Ctrl+Shift+Z)
- Verify preview line during second click
- Test creating multiple frames continuously

---

### Step 8: Draw Shell Mode (4-Click Sequence)
**Files:**
- gui/main_window.py
- gui/viewport/vtk_widget.py

**What:**
Implement four-click sequence for DRAW_SHELL mode similar to beam logic but with 4 nodes (I, J, K, L). First click: establish node I. Second click: establish node J, show preview line I→J. Third click: establish node K, show preview lines forming L-shape (I→J, J→K). Fourth click: establish node L, create shell element. Show progressive preview with dashed lines. Each click snaps to existing nodes or creates new ones. Use compound undo command for entire shell + all created nodes. Reset to first click for continuous drawing.

**Testing:**
- Enter DRAW_SHELL mode
- Click 4 positions in order, verify preview updates at each stage
- Verify shell element created with all 4 nodes (I, J, K, L)
- Test with mix of existing and new nodes
- Test Escape at each stage (cancels and returns to first click)
- Test undo/redo (should undo entire shell + created nodes)
- Verify shell renders correctly in viewport
- Test with snap ON for aligned quadrilateral grids

---

## Design Decisions (Finalized)

1. **Element Types**: Three drawing modes for complete workflow:
   - **Draw Node**: 1-node elements (supports, masses, constraints)
   - **Draw Frame**: 2-node linear elements (beams, columns, braces, links)
   - **Draw Shell**: 4-node area elements (walls, slabs, plates)

2. **Working Plane**: 
   - Default Z=0 
   - Configurable elevation for multi-story structures (future enhancement)
   - No visual plane rendering (minimalist approach)

3. **Grid Snapping**:
   - ✅ Included with minimalist design (invisible snap, no visual grid clutter)
   - Default spacing: 1.0 units
   - Toggle: toolbar button + F9 keyboard shortcut
   - Visual feedback: small snap indicator only when drawing

4. **Property Assignment Strategy**:
   - **Chosen**: Deferred assignment (create with None, assign later)
   - Frames/shells created with default element type, properties assigned via Properties panel
   - Frame default type: 'elasticBeamColumn'
   - Shell default type: 'ShellMITC4' 
   - Future enhancement: remember last-used section/transformation

5. **Coordinate Input**:
   - ✅ Relative offset system in status bar for DRAW_NODE mode
   - Offset fields: ΔX, ΔY, ΔZ with default (0, 0, 0)
   - Applied after snap: `final = snap(click) + offset`
   - No direct coordinate typing (keeps UI simple)

6. **Node Snapping Behavior**:
   - Snap to existing node within 0.15 units tolerance
   - Prevents duplicate near-coincident nodes
   - SAP2000-style intelligent merging

7. **Toolbar Organization**:
   - Four mode buttons: [Select] [Draw Node] [Draw Frame] [Draw Shell]
   - Individual top-level checkable buttons, mutually exclusive via QActionGroup
   - Simple, clear naming: Node (1-node), Frame (2-node), Shell (4-node)
   - No icons required (text labels sufficient for MVP)

## Dependencies & Risks

**Dependencies:**
- PyVista/VTK coordinate conversion (ray casting to plane)
- Qt event system for mouse handling (mousePressEvent, mouseMoveEvent)
- Existing undo system integration with compound commands
- Status bar widget containers for mode-specific controls

**Risks:**
- VTK mouse move events may have performance impact if preview updates every pixel
- Coordinate conversion accuracy in different camera modes needs testing
- Undo system needs to handle compound operations (create 2 nodes + 1 element as single action)
- Relative offset + snap interaction needs careful order of operations

**Mitigation:**
- Throttle mouse move preview updates (every 50ms instead of every event)
- Extensive testing in all camera views (XY, XZ, YZ, ISO)
- Create `CompoundUndoCommand` for multi-entity operations
- Clear operation order: screen → world → snap → offset → create

## Future Enhancements (Out of Scope for This PR)

- Visual grid overlay (toggle with Ctrl+G)
- Multi-level working planes ("Stories" like SAP2000)
- Copy/paste elements
- Array drawing (linear, radial patterns)
- Polyline mode (continuous beams)
- Dimension annotations during drawing
- Smart inference (perpendicular, parallel, midpoint snaps)
- Direct coordinate typing in status bar
- "Last used properties" for element creation
- Customizable grid spacing via preferences
- Import from CAD (DXF)
- Mirror/rotate during drawing
