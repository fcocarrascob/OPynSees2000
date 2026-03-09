# Configurable Snap System with Working Planes

**Branch:** `feature/configurable-snap-system`
**Description:** Adds configurable snap spacing/tolerance, working plane system (XY/XZ/YZ), visual plane feedback, and snap-to-points toggle

## Goal
Enhance the snap system to allow users to configure snap grid spacing, merge tolerance, and working planes (XY, XZ, YZ, or Free 3D). Provide visual feedback showing the active working plane in the viewport. Include a checkbox in properties panel during Frame/Shell drawing modes to enable/disable snapping to existing points. This improves precision control and workflow flexibility when creating structural models, especially for mixed 2D/3D modeling.

## Design Decisions (Final)

### Working Plane System
- **Four modes:** XY Plane, XZ Plane, YZ Plane, Free 3D
- **XY Plane:** Locks Z axis to elevation, free X/Y movement (horizontal floor plan)
- **XZ Plane:** Locks Y axis to elevation, free X/Z movement (front elevation)
- **YZ Plane:** Locks X axis to elevation, free Y/Z movement (side elevation)
- **Free 3D:** No restrictions, all axes free

### Configuration Storage
- **Per-project** (in `DrawingTemplate`): Different models have different grid needs
- Includes: spacing, tolerance, working plane mode, elevation, snap-to-points toggle

### Snap Behavior with Working Planes
- **Point snap priority:** When snapping to existing nodes, use their exact 3D coordinates (ignores working plane restriction)
- **Shift override:** Holding Shift temporarily enables Free 3D mode (ignores working plane for that click)
- **Grid snap:** Uses working plane restrictions when clicking on empty space

### Visual Feedback
- Semi-transparent grid plane rendered in viewport showing active working plane
- Grid lines at snap spacing intervals
- Plane elevation indicator
- Color-coded by plane type (XY=blue, XZ=green, YZ=red)

## Implementation Steps

### Step 1: Enhance SnapManager with Working Plane Support
**Files:** `gui/viewport/snap_manager.py`
**What:** Extend `SnapManager` to support working plane modes:
- Add `snap_with_plane()` method that accepts plane mode ("XY", "XZ", "YZ", "Free"), elevation, and spacing
- For XY: Lock Z to elevation, snap X/Y to grid
- For XZ: Lock Y to elevation, snap X/Z to grid  
- For YZ: Lock X to elevation, snap Y/Z to grid
- For Free: Snap all three axes to grid
- Keep existing `snap()` method for backward compatibility
**Testing:** Call `snap_with_plane()` with different modes and verify correct axis locking and grid snapping.

### Step 2: Extend DrawingTemplate with Snap Configuration Fields
**Files:** `gui/core/model_data.py`, `gui/core/project_io.py`
**What:** Add the following fields to `DrawingTemplate` dataclass:
```python
snap_spacing: float = 1.0
snap_tolerance: float = 0.15  
snap_to_points_enabled: bool = True
working_plane_mode: str = "XY"  # "XY", "XZ", "YZ", "Free"
working_plane_elevation: float = 0.0
```
Update `to_dict()` and `from_dict()` methods to serialize these new fields. Add validation for `working_plane_mode` to ensure only valid values are stored.
**Testing:** Save project with custom snap settings, close and reload, verify all settings persist correctly. Test with each plane mode.

### Step 3: Create Working Plane Visual Renderer
**Files:** `gui/viewport/vtk_widget.py` (or new file `gui/viewport/working_plane.py`)
**What:** Create VTK actors to render the working plane:
- Semi-transparent plane (vtkPlaneSource) at the configured elevation
- Grid lines at snap spacing intervals (vtkPolyData with lines)
- Plane boundary indicator
- Color scheme: XY=blue (0.3, 0.3, 0.8, 0.15), XZ=green (0.3, 0.8, 0.3, 0.15), YZ=red (0.8, 0.3, 0.3, 0.15)
- Plane size: 20x20 units centered at origin (or adapt to model bounds)
- Show/hide based on whether plane mode is active (hide in Free 3D mode)
- Update visualization when plane mode or elevation changes
**Testing:** Change working plane mode/elevation, verify plane appears at correct position and orientation with correct color. Verify hidden in Free 3D mode.

### Step 4: Add Snap Configuration UI in Properties Panel
**Files:** `gui/panels/properties_panel.py`
**What:** Create `show_snap_settings(model)` method displaying snap configuration as always-visible section:
- **QComboBox** for working plane mode: ["Free 3D", "XY Plane", "XZ Plane", "YZ Plane"]
- **QDoubleSpinBox** for plane elevation (range -100 to 100, step 0.1, label changes: "Z=" for XY, "Y=" for XZ, "X=" for YZ, hidden for Free)
- **QDoubleSpinBox** for grid spacing (range 0.01-10.0, default 1.0)
- **QDoubleSpinBox** for merge tolerance (range 0.01-1.0, default 0.15)
- **QCheckBox** for "Snap to Points" (shown only in DRAW_FRAME/DRAW_SHELL modes)
- Add tooltips: plane mode tooltip mentions Shift override
- Connect all controls to update `model.drawing_template` fields and trigger viewport refresh
**Testing:** Change each control, verify DrawingTemplate updates, visual plane updates in real-time, elevation input shows/hides correctly, snap-to-points checkbox appears only in drawing modes.

### Step 5: Integrate Working Plane into Drawing Handlers
**Files:** `gui/main_window.py`, `gui/viewport/vtk_widget.py`
**What:** Update click handling logic to use working plane:
- Modify `_handle_draw_frame()` and `_handle_draw_shell()`:
  - Check if Shift key is pressed (detect modifier state from event)
  - Priority 1: If `snap_to_points_enabled` and node nearby (within `snap_tolerance`), use exact node coordinates (ignores plane restriction)
  - Priority 2: If Shift pressed, use Free 3D snap (ignores plane restriction)  
  - Priority 3: Apply working plane snap using `snap_manager.snap_with_plane(x, y, z, mode, elevation, spacing)`
  - Use `drawing_template.snap_tolerance` instead of hardcoded `0.15`
- Update status bar to show: "[SNAP ON] | Grilla: {spacing} | Plano: {mode} @ {elevation}"
- Initialize snap manager from template settings on model load/change
**Testing:** 
- Set XY plane @ Z=0, click in space, verify Z locked to 0
- Set XZ plane @ Y=3, click in space, verify Y locked to 3
- Shift+click in any plane mode, verify Free 3D behavior
- Click on existing node in any plane mode, verify exact node coordinates used
- Change spacing to 0.5, verify snapping at 0.5 intervals
- Disable snap-to-points, create node near existing one, verify duplicate created

### Step 6: Add Keyboard Shortcuts and Status Indicators
**Files:** `gui/main_window.py`
**What:** Add conveniences for working plane workflow:
- Keyboard shortcuts (optional but recommended):
  - `Ctrl+1`: Set XY Plane
  - `Ctrl+2`: Set XZ Plane  
  - `Ctrl+3`: Set YZ Plane
  - `Ctrl+0`: Set Free 3D
- Update status bar format: "[SNAP ON] | Grid: 1.0m | Plane: XY @ Z=0.0"
- Add tooltips to snap configuration controls explaining Shift override and point snap behavior
- Visual indicator when Shift is held (optional: temporary status message "Free 3D Override")
**Testing:** Press keyboard shortcuts, verify plane changes and UI updates. Verify status bar shows current configuration. Hold Shift during drawing, verify feedback.

---

## Technical Implementation Notes

### Working Plane Snap Logic (Pseudocode)
```python
def determine_snap_point(x, y, z, shift_pressed, model, nearby_node):
    template = model.drawing_template
    
    # Priority 1: Snap to existing point (ignores plane restriction)
    if template.snap_to_points_enabled and nearby_node:
        return nearby_node.coords  # Exact 3D coordinates
    
    # Priority 2: Shift override (Free 3D)
    if shift_pressed:
        return snap_manager.snap_with_plane(x, y, z, "Free", 0.0, template.snap_spacing)
    
    # Priority 3: Working plane snap
    return snap_manager.snap_with_plane(
        x, y, z,
        template.working_plane_mode,
        template.working_plane_elevation,
        template.snap_spacing
    )
```

### VTK Plane Visualization (Pseudocode)
```python
def update_working_plane_visual(mode, elevation):
    if mode == "Free":
        hide_plane()
        return
    
    # Configure plane orientation
    if mode == "XY":
        normal = (0, 0, 1); origin = (0, 0, elevation); color = (0.3, 0.3, 0.8)
    elif mode == "XZ":
        normal = (0, 1, 0); origin = (0, elevation, 0); color = (0.3, 0.8, 0.3)
    elif mode == "YZ":
        normal = (1, 0, 0); origin = (elevation, 0, 0); color = (0.8, 0.3, 0.3)
    
    # Create plane + grid
    plane_actor.SetPosition(origin)
    plane_actor.SetNormal(normal)
    plane_actor.GetProperty().SetColor(color)
    plane_actor.GetProperty().SetOpacity(0.15)
    
    show_plane()
```

### UI Layout (Properties Panel)
```
┌─ Snap Configuration ────────────────────┐
│ Working Plane: [XY Plane ▼]            │
│ Elevation Z:   [0.0     ] m            │
│ Grid Spacing:  [1.0     ] m            │
│ Merge Tolerance: [0.15  ] m            │
│                                         │
│ [When in drawing mode:]                │
│ ☑ Snap to Points                       │
│   (Ignores plane, Shift=Free 3D)       │
└─────────────────────────────────────────┘
```

---

## Expected User Workflows

### Workflow 1: 2D Frame in XY Plane
```
1. Set "XY Plane" mode, elevation Z=0
2. Enter DRAW_FRAME mode
3. Click points (0,0), (5,0), (5,3), (0,3) - all at Z=0 automatically
4. Frame created in 2D plane ✓
```

### Workflow 2: 3D Frame with Diagonal Brace
```  
1. Set "XY Plane", Z=0
2. Create base nodes at Z=0
3. Set "XY Plane", Z=3 (second floor)
4. Create top nodes at Z=3
5. Shift+Click from base to top → Diagonal brace in 3D ✓
```

### Workflow 3: Front Elevation (XZ Plane)
```
1. Set "XZ Plane", Y=0
2. Draw wall frame in X-Z view (height vs length)
3. All nodes locked to Y=0 front face ✓
```

This plan provides a comprehensive working plane system with visual feedback and intuitive controls following CAD software patterns! 🎯
