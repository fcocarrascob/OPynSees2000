# Step 4: Add Snap Configuration UI in Properties Panel

## Goal
Add a persistent "Snap Configuration" section in the Properties Panel with controls for working plane mode, elevation, grid spacing, merge tolerance, and snap-to-points toggle.

## Prerequisites
Steps 1-3 must be completed and committed.

### Step-by-Step Instructions

#### Step 4.1: Add new imports to properties_panel.py

- [x] Open `gui/panels/properties_panel.py`
- [x] Find the existing imports block. After the line `from PySide6.QtWidgets import (`, find the closing `)` of that import block, and add `QCheckBox` to the imports. The full import should become:

```python
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
```

#### Step 4.2: Add the show_snap_settings method

- [x] In the `PropertiesPanel` class, add the following new method **right after** the `show_drawing_template()` method (after its last line before the `# Builders internos` comment):

```python
    def show_snap_settings(
        self,
        model: "StructuralModel",
        mode: str,
        on_setting_changed: "callable | None" = None,
    ) -> None:
        """Muestra la configuración de snap y plano de trabajo.

        Parameters
        ----------
        model : StructuralModel
            Modelo actual (contiene drawing_template).
        mode : str
            ``"frame"``, ``"shell"`` o ``"node"`` — para controlar visibilidad
            del checkbox snap-to-points.
        on_setting_changed : callable | None
            Callback invocado cuando un setting cambia: on_setting_changed(field_name, value).
        """
        template = model.drawing_template

        grp = QGroupBox("Configuración de Snap")
        form = QFormLayout()
        grp.setLayout(form)

        # ── Working Plane Mode ──
        combo_plane = QComboBox()
        plane_options = ["Free 3D", "XY Plane", "XZ Plane", "YZ Plane"]
        plane_values = ["Free", "XY", "XZ", "YZ"]
        for display, value in zip(plane_options, plane_values):
            combo_plane.addItem(display, value)
        current_plane_idx = plane_values.index(template.working_plane_mode) if template.working_plane_mode in plane_values else 0
        combo_plane.setCurrentIndex(current_plane_idx)
        combo_plane.setToolTip(
            "Plano de trabajo activo.\n"
            "XY: bloquea Z | XZ: bloquea Y | YZ: bloquea X\n"
            "Free 3D: sin restricción.\n"
            "Mantener Shift al hacer clic = Free 3D temporal."
        )

        # ── Elevation ──
        spin_elevation = QDoubleSpinBox()
        spin_elevation.setDecimals(2)
        spin_elevation.setRange(-1000.0, 1000.0)
        spin_elevation.setSingleStep(0.1)
        spin_elevation.setValue(template.working_plane_elevation)
        spin_elevation.setSuffix(" m")

        # Label dinámico para elevación
        elevation_label = QLabel(self._elevation_label_text(template.working_plane_mode))

        def _update_elevation_label(idx: int) -> None:
            plane_val = combo_plane.itemData(idx)
            elevation_label.setText(self._elevation_label_text(plane_val))
            # Mostrar/ocultar elevación según modo
            is_free = (plane_val == "Free")
            spin_elevation.setVisible(not is_free)
            elevation_label.setVisible(not is_free)

        # Ocultar elevación si es Free
        is_free = (template.working_plane_mode == "Free")
        spin_elevation.setVisible(not is_free)
        elevation_label.setVisible(not is_free)

        # ── Grid Spacing ──
        spin_spacing = QDoubleSpinBox()
        spin_spacing.setDecimals(2)
        spin_spacing.setRange(0.01, 100.0)
        spin_spacing.setSingleStep(0.1)
        spin_spacing.setValue(template.snap_spacing)
        spin_spacing.setSuffix(" m")
        spin_spacing.setToolTip("Espaciado de la grilla de snap")

        # ── Merge Tolerance ──
        spin_tolerance = QDoubleSpinBox()
        spin_tolerance.setDecimals(3)
        spin_tolerance.setRange(0.001, 10.0)
        spin_tolerance.setSingleStep(0.01)
        spin_tolerance.setValue(template.snap_tolerance)
        spin_tolerance.setSuffix(" m")
        spin_tolerance.setToolTip("Tolerancia para fusionar nodos cercanos")

        # ── Snap to Points ──
        chk_snap_points = QCheckBox("Snap a Puntos")
        chk_snap_points.setChecked(template.snap_to_points_enabled)
        chk_snap_points.setToolTip(
            "Cuando activo, el clic cerca de un nodo existente\n"
            "usa sus coordenadas exactas 3D (ignora plano).\n"
            "Shift+clic = Free 3D temporal."
        )
        # Solo mostrar en modos de dibujo frame/shell
        show_snap_to_points = mode in ("frame", "shell")
        chk_snap_points.setVisible(show_snap_to_points)

        # ── Conectar callbacks ──
        def _on_plane_changed(idx: int) -> None:
            value = combo_plane.itemData(idx)
            template.working_plane_mode = value
            _update_elevation_label(idx)
            if on_setting_changed:
                on_setting_changed("working_plane_mode", value)

        def _on_elevation_changed() -> None:
            template.working_plane_elevation = spin_elevation.value()
            if on_setting_changed:
                on_setting_changed("working_plane_elevation", spin_elevation.value())

        def _on_spacing_changed() -> None:
            template.snap_spacing = spin_spacing.value()
            if on_setting_changed:
                on_setting_changed("snap_spacing", spin_spacing.value())

        def _on_tolerance_changed() -> None:
            template.snap_tolerance = spin_tolerance.value()
            if on_setting_changed:
                on_setting_changed("snap_tolerance", spin_tolerance.value())

        def _on_snap_points_changed(state: int) -> None:
            template.snap_to_points_enabled = bool(state)
            if on_setting_changed:
                on_setting_changed("snap_to_points_enabled", bool(state))

        combo_plane.currentIndexChanged.connect(_on_plane_changed)
        spin_elevation.editingFinished.connect(_on_elevation_changed)
        spin_spacing.editingFinished.connect(_on_spacing_changed)
        spin_tolerance.editingFinished.connect(_on_tolerance_changed)
        chk_snap_points.stateChanged.connect(_on_snap_points_changed)

        # ── Agregar al formulario ──
        form.addRow("Plano de trabajo:", combo_plane)
        form.addRow(elevation_label, spin_elevation)
        form.addRow("Espaciado grilla:", spin_spacing)
        form.addRow("Tolerancia merge:", spin_tolerance)
        if show_snap_to_points:
            form.addRow(chk_snap_points)

        self._layout.addWidget(grp)

    @staticmethod
    def _elevation_label_text(plane_mode: str) -> str:
        """Retorna el texto de etiqueta de elevación según el plano."""
        if plane_mode == "XY":
            return "Elevación Z:"
        elif plane_mode == "XZ":
            return "Elevación Y:"
        elif plane_mode == "YZ":
            return "Elevación X:"
        return "Elevación:"
```

#### Step 4.3: Integrate snap settings into show_drawing_template

- [x] In the `show_drawing_template()` method, find the line `self._layout.addStretch()` at the end of the method
- [x] **Insert the following code before** that `self._layout.addStretch()` line:

```python
        # Sección de configuración de snap
        self.show_snap_settings(model, mode)
```

The end of `show_drawing_template()` should now look like:

```python
        # ...existing hint code...

        # Sección de configuración de snap
        self.show_snap_settings(model, mode)

        self._layout.addStretch()
```

##### Step 4 Verification Checklist
- [x] No import errors:
  ```python
  python -c "from gui.panels.properties_panel import PropertiesPanel; print('Import OK')"
  ```
- [x] PropertiesPanel has the new methods:
  ```python
  python -c "
  from gui.panels.properties_panel import PropertiesPanel
  assert hasattr(PropertiesPanel, 'show_snap_settings')
  assert hasattr(PropertiesPanel, '_elevation_label_text')
  print('Methods OK')
  "
  ```
- [x] Elevation label text is correct:
  ```python
  python -c "
  from gui.panels.properties_panel import PropertiesPanel
  assert PropertiesPanel._elevation_label_text('XY') == 'Elevación Z:'
  assert PropertiesPanel._elevation_label_text('XZ') == 'Elevación Y:'
  assert PropertiesPanel._elevation_label_text('YZ') == 'Elevación X:'
  assert PropertiesPanel._elevation_label_text('Free') == 'Elevación:'
  print('Labels OK')
  "
  ```
- [ ] Application launches and shows snap settings in drawing mode:
  1. Run `python -m gui`
  2. Click "Dibujar Frame" in the toolbar
  3. Verify the Properties Panel shows:
     - "Propiedades del Frame a Crear" title (blue)
     - Frame configuration (type, section, transformation)
     - **"Configuración de Snap"** group box with:
       - Working Plane dropdown (default: "XY Plane")
       - Elevation Z spinner (default: 0.0 m)
       - Grid spacing spinner (default: 1.0 m)
       - Merge tolerance spinner (default: 0.15 m)
       - "Snap a Puntos" checkbox (checked)
  4. Change plane to "Free 3D" → verify elevation spinner hides
  5. Change plane to "XZ Plane" → verify label changes to "Elevación Y:"
  6. Change plane to "YZ Plane" → verify label changes to "Elevación X:"
  7. Switch to "Dibujar Shell" → verify snap settings also appear
  8. Switch to "Selección" → verify snap settings disappear

#### Step 4 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
