# Step 5: Integrate Working Plane into Drawing Handlers

## Goal
Update click handling in MainWindow and VTKViewport to use working plane constraints, snap-to-points priority, Shift override for Free 3D, and visual plane feedback.

## Prerequisites
Steps 1-4 must be completed and committed.

### Step-by-Step Instructions

#### Step 5.1: Update VTKViewport to pass Shift modifier state in drawing signals

The VTK event filter in `vtk_widget.py` needs to detect whether Shift is held when a drawing click occurs and pass that info. We'll change the `drawing_click` signal to include the modifier state.

- [x] Open `gui/viewport/vtk_widget.py`
- [x] Find the signal declarations near the top of `VTKViewport`:

```python
    # Señales para modo dibujo
    drawing_click = Signal(float, float, float)       # clic con coords mundo (snapped)
    drawing_mouse_move = Signal(float, float, float)   # movimiento con coords mundo (snapped)
```

Replace with:

```python
    # Señales para modo dibujo
    drawing_click = Signal(float, float, float, bool)  # clic con coords mundo (snapped) + shift_pressed
    drawing_mouse_move = Signal(float, float, float)   # movimiento con coords mundo (snapped)
```

- [x] Find the `eventFilter` method (around line 883). In the mouse click handling branch, update to detect Shift and pass it. Replace the existing block:

```python
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    coords = self._screen_to_world(event.pos().x(), event.pos().y())
                    if coords is not None:
                        snapped = self._apply_snap(coords)
                        self.drawing_click.emit(snapped[0], snapped[1], snapped[2])
                    return True  # consumir: no propagar clic izquierdo al interactor VTK
```

With:

```python
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    coords = self._screen_to_world(event.pos().x(), event.pos().y())
                    if coords is not None:
                        snapped = self._apply_snap(coords)
                        shift_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                        self.drawing_click.emit(snapped[0], snapped[1], snapped[2], shift_pressed)
                    return True  # consumir: no propagar clic izquierdo al interactor VTK
```

- [x] Also find the `mousePressEvent` method. Update the same way. Replace:

```python
    def mousePressEvent(self, event) -> None:
        """Captura clics en modo dibujo; delega al plotter en modo selección."""
        if self._drawing_mode and event.button() == Qt.MouseButton.LeftButton:
            # Obtener posición del widget interior (plotter)
            pos = self.plotter.mapFromParent(event.pos())
            coords = self._screen_to_world(pos.x(), pos.y())
            if coords is not None:
                snapped = self._apply_snap(coords)
                self.drawing_click.emit(snapped[0], snapped[1], snapped[2])
            return  # No propagar al plotter
        super().mousePressEvent(event)
```

With:

```python
    def mousePressEvent(self, event) -> None:
        """Captura clics en modo dibujo; delega al plotter en modo selección."""
        if self._drawing_mode and event.button() == Qt.MouseButton.LeftButton:
            # Obtener posición del widget interior (plotter)
            pos = self.plotter.mapFromParent(event.pos())
            coords = self._screen_to_world(pos.x(), pos.y())
            if coords is not None:
                snapped = self._apply_snap(coords)
                shift_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                self.drawing_click.emit(snapped[0], snapped[1], snapped[2], shift_pressed)
            return  # No propagar al plotter
        super().mousePressEvent(event)
```

#### Step 5.2: Update MainWindow drawing_click connection

- [x] Open `gui/main_window.py`
- [x] Find the signal connection in `__init__`:

```python
        self._viewport.drawing_click.connect(self._on_drawing_click)
```

This stays the same — but we need to update the slot signature.

- [x] Find `_on_drawing_click` and replace:

```python
    def _on_drawing_click(self, x: float, y: float, z: float) -> None:
        """Maneja clic en modo dibujo."""
        if self._interaction_mode == InteractionMode.DRAW_NODE:
            self._handle_draw_node(x, y, z)
        elif self._interaction_mode == InteractionMode.DRAW_FRAME:
            self._handle_draw_frame(x, y, z)
        elif self._interaction_mode == InteractionMode.DRAW_SHELL:
            self._handle_draw_shell(x, y, z)
```

With:

```python
    def _on_drawing_click(self, x: float, y: float, z: float, shift_pressed: bool = False) -> None:
        """Maneja clic en modo dibujo con soporte de plano de trabajo."""
        template = self._model.drawing_template
        snap_coords = self._resolve_snap_point(x, y, z, shift_pressed)

        if self._interaction_mode == InteractionMode.DRAW_NODE:
            self._handle_draw_node(snap_coords[0], snap_coords[1], snap_coords[2])
        elif self._interaction_mode == InteractionMode.DRAW_FRAME:
            self._handle_draw_frame(snap_coords[0], snap_coords[1], snap_coords[2])
        elif self._interaction_mode == InteractionMode.DRAW_SHELL:
            self._handle_draw_shell(snap_coords[0], snap_coords[1], snap_coords[2])
```

#### Step 5.3: Add the _resolve_snap_point method to MainWindow

- [x] Add the following method to `MainWindow`, right **before** `_on_drawing_click`:

```python
    def _resolve_snap_point(
        self, x: float, y: float, z: float, shift_pressed: bool = False,
    ) -> tuple[float, float, float]:
        """
        Resuelve el punto final de snap según el plano de trabajo activo.

        Prioridad:
        1. Snap a nodo existente (si snap_to_points_enabled y nodo cercano)
        2. Shift override → Free 3D snap
        3. Working plane snap
        """
        from gui.viewport.picking import find_closest_node

        template = self._model.drawing_template

        # Prioridad 1: Snap a nodo existente
        if template.snap_to_points_enabled:
            nearby = find_closest_node(
                self._model, (x, y, z), tolerance=template.snap_tolerance,
            )
            if nearby is not None:
                node = self._model.nodes[nearby]
                return node.coords

        # Prioridad 2: Shift override → Free 3D
        if shift_pressed:
            return self._snap_mgr.snap_with_plane(
                x, y, z, "Free", 0.0, template.snap_spacing,
            )

        # Prioridad 3: Working plane snap
        return self._snap_mgr.snap_with_plane(
            x, y, z,
            template.working_plane_mode,
            template.working_plane_elevation,
            template.snap_spacing,
        )
```

#### Step 5.4: Update _handle_draw_frame to use template tolerance

- [x] In `_handle_draw_frame`, find the **two** places where `tolerance=0.15` is used (for finding existing nodes). Replace them with `tolerance=template.snap_tolerance`.

Find this block in the **first click** section:

```python
            existing = find_closest_node(self._model, (x, y, z), tolerance=0.15)
```

Replace with:

```python
            template = self._model.drawing_template
            existing = find_closest_node(self._model, (x, y, z), tolerance=template.snap_tolerance)
```

Find this block in the **second click** section:

```python
            existing_j = find_closest_node(self._model, (x, y, z), tolerance=0.15)
```

Replace with:

```python
            existing_j = find_closest_node(self._model, (x, y, z), tolerance=template.snap_tolerance)
```

#### Step 5.5: Update _handle_draw_shell to use template tolerance

- [x] In `_handle_draw_shell`, find the line:

```python
        existing = find_closest_node(self._model, (x, y, z), tolerance=0.15)
```

Replace with:

```python
        template = self._model.drawing_template
        existing = find_closest_node(self._model, (x, y, z), tolerance=template.snap_tolerance)
```

#### Step 5.6: Add callback for snap settings changes and visual plane updates

- [x] In `MainWindow`, add this new method after `_resolve_snap_point`:

```python
    def _on_snap_setting_changed(self, field_name: str, value) -> None:
        """Callback cuando cambia un setting de snap en el Properties Panel."""
        template = self._model.drawing_template

        # Actualizar snap manager spacing
        if field_name == "snap_spacing":
            self._snap_mgr.spacing = value

        # Actualizar visual del plano de trabajo
        if field_name in ("working_plane_mode", "working_plane_elevation", "snap_spacing"):
            self._viewport.update_working_plane_visual(
                template.working_plane_mode,
                template.working_plane_elevation,
                template.snap_spacing,
            )

            # Actualizar plano Z de raycasting para proyección
            if template.working_plane_mode == "XY":
                self._viewport.set_working_plane_z(template.working_plane_elevation)
            elif template.working_plane_mode == "Free":
                self._viewport.set_working_plane_z(0.0)
            # Para XZ y YZ, el raycasting sigue proyectando a Z=working_plane_z
            # pero el snap_with_plane corregirá el eje apropiado

        # Actualizar status bar
        self._update_drawing_statusbar()
```

#### Step 5.7: Add _update_drawing_statusbar helper

- [x] Add this method to `MainWindow` after `_on_snap_setting_changed`:

```python
    def _update_drawing_statusbar(self) -> None:
        """Actualiza la status bar con info del modo de dibujo actual."""
        if self._interaction_mode == InteractionMode.SELECT:
            self._update_statusbar()
            return

        template = self._model.drawing_template
        mode_names = {
            InteractionMode.DRAW_NODE: "Dibujar Nodo",
            InteractionMode.DRAW_FRAME: "Dibujar Frame",
            InteractionMode.DRAW_SHELL: "Dibujar Shell",
        }
        mode_label = mode_names.get(self._interaction_mode, "")
        snap = self._snap_mgr.status_text()

        # Info de plano
        plane = template.working_plane_mode
        if plane == "Free":
            plane_info = "Plano: Free 3D"
        elif plane == "XY":
            plane_info = f"Plano: XY @ Z={template.working_plane_elevation:.1f}"
        elif plane == "XZ":
            plane_info = f"Plano: XZ @ Y={template.working_plane_elevation:.1f}"
        elif plane == "YZ":
            plane_info = f"Plano: YZ @ X={template.working_plane_elevation:.1f}"
        else:
            plane_info = f"Plano: {plane}"

        # Info de propiedades activas
        props_info = ""
        if self._interaction_mode == InteractionMode.DRAW_FRAME:
            section_name = "(sin asignar)"
            if template.frame_section_tag:
                sec = self._model.sections.get(template.frame_section_tag)
                if sec:
                    section_name = sec.name
            props_info = f"  |  Sección: {section_name}"
        elif self._interaction_mode == InteractionMode.DRAW_SHELL:
            section_name = "(sin asignar)"
            if template.shell_section_tag:
                sec = self._model.sections.get(template.shell_section_tag)
                if sec:
                    section_name = sec.name
            props_info = f"  |  Sección: {section_name}"

        self.statusBar().showMessage(
            f"Modo: {mode_label}  |  {snap}  |  Grid: {template.snap_spacing}m  |  "
            f"{plane_info}{props_info}  |  Escape → Selección"
        )
```

#### Step 5.8: Update set_mode to use new statusbar and show working plane

- [x] In the `set_mode()` method, find the `else:` branch (for drawing modes). Replace the entire block starting from `self._viewport.disable_picking()` down to and including the `self.statusBar().showMessage(...)` call. The new code should be:

Find and replace this section (inside `set_mode`, the `else:` branch):

```python
            self._viewport.disable_picking()
            self._viewport.set_drawing_mode(True)
            self._set_offset_widgets_visible(mode == InteractionMode.DRAW_NODE)
            mode_names = {
                InteractionMode.DRAW_NODE: "Dibujar Nodo",
                InteractionMode.DRAW_FRAME: "Dibujar Frame",
                InteractionMode.DRAW_SHELL: "Dibujar Shell",
            }
            mode_label = mode_names.get(mode, "")
            snap = self._snap_mgr.status_text()

            # Construir info de propiedades activas para status bar
            props_info = ""
            if mode == InteractionMode.DRAW_FRAME:
                template = self._model.drawing_template
                section_name = "(sin asignar)"
                if template.frame_section_tag:
                    sec = self._model.sections.get(template.frame_section_tag)
                    if sec:
                        section_name = sec.name
                transf_name = "(sin asignar)"
                if template.frame_transf_tag:
                    transf_name = f"Tag {template.frame_transf_tag}"
                props_info = f"  |  Sección: {section_name}  |  Transf: {transf_name}"
            elif mode == InteractionMode.DRAW_SHELL:
                template = self._model.drawing_template
                section_name = "(sin asignar)"
                if template.shell_section_tag:
                    sec = self._model.sections.get(template.shell_section_tag)
                    if sec:
                        section_name = sec.name
                props_info = f"  |  Sección: {section_name}"

            self.statusBar().showMessage(
                f"Modo: {mode_label}  |  {snap}{props_info}  |  "
                f"Clic en viewport para crear  |  Escape → Selección"
            )
```

Replace with:

```python
            self._viewport.disable_picking()
            self._viewport.set_drawing_mode(True)
            self._set_offset_widgets_visible(mode == InteractionMode.DRAW_NODE)

            # Sincronizar snap manager con template
            template = self._model.drawing_template
            self._snap_mgr.spacing = template.snap_spacing

            # Mostrar plano de trabajo visual
            self._viewport.update_working_plane_visual(
                template.working_plane_mode,
                template.working_plane_elevation,
                template.snap_spacing,
            )

            # Actualizar status bar con info del plano
            self._update_drawing_statusbar()
```

#### Step 5.9: Update show_drawing_template calls to pass callback

- [x] In `set_mode()`, find the two calls to `self._properties.show_drawing_template(...)` at the bottom of the method. They currently look like:

```python
            # Actualizar Properties Panel según modo de dibujo
            if mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(self._model, "frame")
            elif mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(self._model, "shell")
```

These remain unchanged. But the `show_snap_settings` inside `show_drawing_template` needs the callback. Update the `show_drawing_template` method in `properties_panel.py` to accept and pass the callback.

- [x] Open `gui/panels/properties_panel.py`
- [x] Update the `show_drawing_template` method signature to accept an optional callback:

Find:

```python
    def show_drawing_template(
        self,
        model: "StructuralModel",
        mode: str,
    ) -> None:
```

Replace with:

```python
    def show_drawing_template(
        self,
        model: "StructuralModel",
        mode: str,
        on_snap_setting_changed: "callable | None" = None,
    ) -> None:
```

- [x] Update the `show_snap_settings` call inside `show_drawing_template` (that was added in Step 4.3). Find:

```python
        # Sección de configuración de snap
        self.show_snap_settings(model, mode)
```

Replace with:

```python
        # Sección de configuración de snap
        self.show_snap_settings(model, mode, on_setting_changed=on_snap_setting_changed)
```

- [x] Back in `gui/main_window.py`, update the `show_drawing_template` calls in `set_mode()` to pass the callback:

Find:

```python
            # Actualizar Properties Panel según modo de dibujo
            if mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(self._model, "frame")
            elif mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(self._model, "shell")
```

Replace with:

```python
            # Actualizar Properties Panel según modo de dibujo
            if mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(
                    self._model, "frame",
                    on_snap_setting_changed=self._on_snap_setting_changed,
                )
            elif mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(
                    self._model, "shell",
                    on_snap_setting_changed=self._on_snap_setting_changed,
                )
```

#### Step 5.10: Hide working plane when returning to SELECT mode

- [x] In `set_mode()`, find the `if mode == InteractionMode.SELECT:` branch. After the line `self._viewport.clear_all_previews()`, add:

```python
            self._viewport.hide_working_plane_visual()
```

The SELECT branch should now look like:

```python
        if mode == InteractionMode.SELECT:
            self._viewport.enable_picking(self._model)
            self._viewport.set_drawing_mode(False)
            self._viewport.clear_all_previews()
            self._viewport.hide_working_plane_visual()
            self._set_offset_widgets_visible(False)
            self._properties.clear()
            self._update_statusbar()
```

#### Step 5.11: Also update the _on_define_section and _on_define_transf refreshes

- [x] Find in `_on_define_section()` these lines at the bottom:

```python
            # Refrescar panel si estamos en modo dibujo
            if self._interaction_mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(self._model, "frame")
            elif self._interaction_mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(self._model, "shell")
```

Replace with:

```python
            # Refrescar panel si estamos en modo dibujo
            if self._interaction_mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(
                    self._model, "frame",
                    on_snap_setting_changed=self._on_snap_setting_changed,
                )
            elif self._interaction_mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(
                    self._model, "shell",
                    on_snap_setting_changed=self._on_snap_setting_changed,
                )
```

- [x] Find in `_on_define_transf()` the line:

```python
            # Refrescar panel si estamos en modo dibujo frame
            if self._interaction_mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(self._model, "frame")
```

Replace with:

```python
            # Refrescar panel si estamos en modo dibujo frame
            if self._interaction_mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(
                    self._model, "frame",
                    on_snap_setting_changed=self._on_snap_setting_changed,
                )
```

##### Step 5 Verification Checklist
- [x] No import errors: `python -c "from gui.main_window import MainWindow; print('OK')"`
- [ ] Application launches: `python -m gui`
- [ ] **Working Plane XY test:**
  1. Enter "Dibujar Frame" mode
  2. Set plane to "XY Plane", elevation Z=0.0
  3. Click two points in the viewport
  4. Verify both nodes have Z=0.0 (check in Model Tree → node properties)
  5. Change elevation to Z=3.0 and create another frame
  6. Verify new nodes have Z=3.0
- [ ] **Working Plane XZ test:**
  1. Set plane to "XZ Plane", elevation Y=0.0
  2. Create a frame
  3. Verify nodes have Y=0.0
- [ ] **Shift override test:**
  1. Set plane to "XY Plane", Z=0.0
  2. Hold Shift + click → should create node with Free 3D coordinates (Z not locked)
- [ ] **Snap to Points test:**
  1. Ensure "Snap a Puntos" is checked
  2. Click near an existing node → should use its exact coords
  3. Uncheck "Snap a Puntos"
  4. Click near an existing node → should create a new node (not snap to existing)
- [ ] **Visual plane feedback:**
  1. In "Dibujar Frame" mode, verify semi-transparent blue grid appears at Z=0
  2. Change to "XZ Plane" → verify green grid appears
  3. Change to "YZ Plane" → verify red grid appears
  4. Change to "Free 3D" → verify grid disappears
  5. Press Escape → verify grid disappears
- [ ] **Status bar shows plane info:**
  1. In drawing mode, verify status bar shows: `Grid: 1.0m | Plano: XY @ Z=0.0`
  2. Change plane/elevation, verify status updates
- [ ] **Tolerance customization:**
  1. Change merge tolerance to 0.5m
  2. Click at a distance between 0.15-0.5m from existing node
  3. Verify it snaps to the existing node (with "Snap a Puntos" enabled)

#### Step 5 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
