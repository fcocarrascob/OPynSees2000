# Step 2: Extend DrawingTemplate with Snap Configuration Fields

## Goal
Add snap spacing, tolerance, working plane mode/elevation, and snap-to-points fields to `DrawingTemplate` with full serialization support.

## Prerequisites
Step 1 (SnapManager with working plane support) must be completed and committed.

### Step-by-Step Instructions

#### Step 2.1: Add new fields to DrawingTemplate dataclass

- [x] Open `gui/core/model_data.py`
- [x] Find the `DrawingTemplate` dataclass (around line 315)
- [x] Replace the **entire `DrawingTemplate` class** with the code below:

```python
@dataclass
class DrawingTemplate:
    """Plantilla de propiedades para nuevos elementos dibujados en viewport."""

    # Para Frames
    frame_section_tag: Optional[int] = None
    frame_transf_tag: Optional[int] = None
    frame_elem_type: ElementType = ElementType.ELASTIC_BEAM_COLUMN

    # Para Shells
    shell_section_tag: Optional[int] = None
    shell_thickness: float = 0.2  # metros

    # Para Loads (patrón de carga activo — futuro)
    active_load_pattern_tag: int = 1  # Default to DEAD

    # Snap & Working Plane Configuration
    snap_spacing: float = 1.0
    snap_tolerance: float = 0.15
    snap_to_points_enabled: bool = True
    working_plane_mode: str = "XY"  # "XY", "XZ", "YZ", "Free"
    working_plane_elevation: float = 0.0

    def to_dict(self) -> dict:
        return {
            "frame_section_tag": self.frame_section_tag,
            "frame_transf_tag": self.frame_transf_tag,
            "frame_elem_type": self.frame_elem_type.value if self.frame_elem_type else None,
            "shell_section_tag": self.shell_section_tag,
            "shell_thickness": self.shell_thickness,
            "active_load_pattern_tag": self.active_load_pattern_tag,
            "snap_spacing": self.snap_spacing,
            "snap_tolerance": self.snap_tolerance,
            "snap_to_points_enabled": self.snap_to_points_enabled,
            "working_plane_mode": self.working_plane_mode,
            "working_plane_elevation": self.working_plane_elevation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DrawingTemplate":
        elem_type_str = data.get("frame_elem_type")
        elem_type = ElementType(elem_type_str) if elem_type_str else ElementType.ELASTIC_BEAM_COLUMN

        # Validar working_plane_mode
        plane_mode = data.get("working_plane_mode", "XY")
        if plane_mode not in ("XY", "XZ", "YZ", "Free"):
            plane_mode = "XY"

        return cls(
            frame_section_tag=data.get("frame_section_tag"),
            frame_transf_tag=data.get("frame_transf_tag"),
            frame_elem_type=elem_type,
            shell_section_tag=data.get("shell_section_tag"),
            shell_thickness=data.get("shell_thickness", 0.2),
            active_load_pattern_tag=data.get("active_load_pattern_tag", 1),
            snap_spacing=data.get("snap_spacing", 1.0),
            snap_tolerance=data.get("snap_tolerance", 0.15),
            snap_to_points_enabled=data.get("snap_to_points_enabled", True),
            working_plane_mode=plane_mode,
            working_plane_elevation=data.get("working_plane_elevation", 0.0),
        )
```

##### Step 2 Verification Checklist
- [x] No import errors: run `python -c "from gui.core.model_data import DrawingTemplate"`
- [x] New fields exist with defaults:
  ```python
  python -c "
  from gui.core.model_data import DrawingTemplate
  dt = DrawingTemplate()
  assert dt.snap_spacing == 1.0
  assert dt.snap_tolerance == 0.15
  assert dt.snap_to_points_enabled is True
  assert dt.working_plane_mode == 'XY'
  assert dt.working_plane_elevation == 0.0
  print('All defaults OK')
  "
  ```
- [x] Serialization round-trip works:
  ```python
  python -c "
  from gui.core.model_data import DrawingTemplate
  dt = DrawingTemplate(
      snap_spacing=0.5,
      snap_tolerance=0.1,
      snap_to_points_enabled=False,
      working_plane_mode='XZ',
      working_plane_elevation=3.5,
  )
  d = dt.to_dict()
  dt2 = DrawingTemplate.from_dict(d)
  assert dt2.snap_spacing == 0.5
  assert dt2.snap_tolerance == 0.1
  assert dt2.snap_to_points_enabled is False
  assert dt2.working_plane_mode == 'XZ'
  assert dt2.working_plane_elevation == 3.5
  print('Round-trip OK')
  "
  ```
- [x] Backward compatibility — loading old data without new fields:
  ```python
  python -c "
  from gui.core.model_data import DrawingTemplate
  old_data = {
      'frame_section_tag': 1,
      'frame_transf_tag': 1,
      'frame_elem_type': 'elasticBeamColumn',
      'shell_section_tag': None,
      'shell_thickness': 0.2,
      'active_load_pattern_tag': 1,
  }
  dt = DrawingTemplate.from_dict(old_data)
  assert dt.snap_spacing == 1.0
  assert dt.working_plane_mode == 'XY'
  print('Backward compat OK')
  "
  ```
- [x] Invalid plane mode is corrected:
  ```python
  python -c "
  from gui.core.model_data import DrawingTemplate
  dt = DrawingTemplate.from_dict({'working_plane_mode': 'INVALID'})
  assert dt.working_plane_mode == 'XY', f'Got {dt.working_plane_mode}'
  print('Validation OK')
  "
  ```
- [x] Full model save/load works:
  ```python
  python -c "
  from gui.core.model_data import StructuralModel
  model = StructuralModel.create_demo()
  model.drawing_template.snap_spacing = 0.5
  model.drawing_template.working_plane_mode = 'YZ'
  model.drawing_template.working_plane_elevation = 2.0
  d = model.to_dict()
  model2 = StructuralModel.from_dict(d)
  assert model2.drawing_template.snap_spacing == 0.5
  assert model2.drawing_template.working_plane_mode == 'YZ'
  assert model2.drawing_template.working_plane_elevation == 2.0
  print('Full model round-trip OK')
  "
  ```
- [ ] Application still launches: `python -m gui`

#### Step 2 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
