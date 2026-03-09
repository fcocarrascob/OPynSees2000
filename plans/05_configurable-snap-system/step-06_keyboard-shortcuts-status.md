# Step 6: Add Keyboard Shortcuts and Status Indicators

## Goal
Add keyboard shortcuts (Ctrl+1/2/3/0) for quick plane switching and a visual Shift indicator in the status bar during drawing modes.

## Prerequisites
Steps 1-5 must be completed and committed.

### Step-by-Step Instructions

#### Step 6.1: Add keyboard shortcuts for plane switching in keyPressEvent

- [ ] Open `gui/main_window.py`
- [ ] Find the `keyPressEvent` method. It currently handles Escape and R keys. Add plane switching shortcuts **before** the `super().keyPressEvent(event)` call at the end.

Find the existing method:

```python
    def keyPressEvent(self, event) -> None:
        """Maneja atajos de teclado globales."""
        if event.key() == Qt.Key.Key_Escape:
            if self._interaction_mode == InteractionMode.DRAW_FRAME and self._frame_first_node is not None:
                self._frame_first_node = None
                self._frame_first_coords = None
                self._viewport.clear_all_previews()
                self._console.log("Frame cancelado — esperando primer nodo.")
                return
            if self._interaction_mode == InteractionMode.DRAW_SHELL and self._shell_nodes:
                self._shell_nodes.clear()
                self._shell_coords.clear()
                self._viewport.clear_all_previews()
                self._console.log("Shell cancelado — esperando primer nodo.")
                return
            if self._interaction_mode != InteractionMode.SELECT:
                self.set_mode(InteractionMode.SELECT)
                return
        elif event.key() == Qt.Key.Key_R:
            if self._interaction_mode == InteractionMode.DRAW_NODE:
                self._reset_offset()
                self._console.log("Offset reseteado a (0, 0, 0)")
                return
        super().keyPressEvent(event)
```

Replace the **entire method** with:

```python
    def keyPressEvent(self, event) -> None:
        """Maneja atajos de teclado globales."""
        if event.key() == Qt.Key.Key_Escape:
            if self._interaction_mode == InteractionMode.DRAW_FRAME and self._frame_first_node is not None:
                self._frame_first_node = None
                self._frame_first_coords = None
                self._viewport.clear_all_previews()
                self._console.log("Frame cancelado — esperando primer nodo.")
                return
            if self._interaction_mode == InteractionMode.DRAW_SHELL and self._shell_nodes:
                self._shell_nodes.clear()
                self._shell_coords.clear()
                self._viewport.clear_all_previews()
                self._console.log("Shell cancelado — esperando primer nodo.")
                return
            if self._interaction_mode != InteractionMode.SELECT:
                self.set_mode(InteractionMode.SELECT)
                return
        elif event.key() == Qt.Key.Key_R:
            if self._interaction_mode == InteractionMode.DRAW_NODE:
                self._reset_offset()
                self._console.log("Offset reseteado a (0, 0, 0)")
                return

        # Atajos de plano de trabajo (Ctrl+0/1/2/3)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            plane_map = {
                Qt.Key.Key_1: "XY",
                Qt.Key.Key_2: "XZ",
                Qt.Key.Key_3: "YZ",
                Qt.Key.Key_0: "Free",
            }
            plane = plane_map.get(event.key())
            if plane is not None:
                self._set_working_plane(plane)
                return

        super().keyPressEvent(event)
```

#### Step 6.2: Add _set_working_plane helper method

- [ ] Add this method to `MainWindow`, after `_on_snap_setting_changed`:

```python
    def _set_working_plane(self, plane_mode: str) -> None:
        """Cambia el plano de trabajo activo desde atajo de teclado."""
        template = self._model.drawing_template
        template.working_plane_mode = plane_mode

        # Actualizar visual
        self._viewport.update_working_plane_visual(
            template.working_plane_mode,
            template.working_plane_elevation,
            template.snap_spacing,
        )

        # Actualizar raycasting Z
        if plane_mode == "XY":
            self._viewport.set_working_plane_z(template.working_plane_elevation)
        elif plane_mode == "Free":
            self._viewport.set_working_plane_z(0.0)

        # Actualizar status bar
        self._update_drawing_statusbar()

        # Refrescar properties panel si estamos en modo dibujo
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

        plane_names = {"XY": "XY Plane", "XZ": "XZ Plane", "YZ": "YZ Plane", "Free": "Free 3D"}
        self._console.log(f"Plano de trabajo: {plane_names.get(plane_mode, plane_mode)}")
```

#### Step 6.3: Add Shift key visual indicator

- [ ] Add a `keyReleaseEvent` handler to show/hide a Shift indicator. Add after `keyPressEvent`:

```python
    def keyReleaseEvent(self, event) -> None:
        """Maneja liberación de teclas."""
        if event.key() == Qt.Key.Key_Shift:
            if self._interaction_mode in (
                InteractionMode.DRAW_FRAME,
                InteractionMode.DRAW_SHELL,
                InteractionMode.DRAW_NODE,
            ):
                self._update_drawing_statusbar()
        super().keyReleaseEvent(event)
```

- [ ] Also update `keyPressEvent` to show the Shift indicator. Add after the `elif event.key() == Qt.Key.Key_R:` block, **before** the Ctrl plane shortcuts:

Find in the new `keyPressEvent` (from Step 6.1):

```python
        # Atajos de plano de trabajo (Ctrl+0/1/2/3)
```

Insert before that line:

```python
        # Indicador visual de Shift (Free 3D temporal)
        if event.key() == Qt.Key.Key_Shift:
            if self._interaction_mode in (
                InteractionMode.DRAW_FRAME,
                InteractionMode.DRAW_SHELL,
                InteractionMode.DRAW_NODE,
            ):
                self.statusBar().showMessage(
                    "🔓 Free 3D Override (Shift) — Clic ignora restricción de plano"
                )
                return

```

The final `keyPressEvent` should be:

```python
    def keyPressEvent(self, event) -> None:
        """Maneja atajos de teclado globales."""
        if event.key() == Qt.Key.Key_Escape:
            if self._interaction_mode == InteractionMode.DRAW_FRAME and self._frame_first_node is not None:
                self._frame_first_node = None
                self._frame_first_coords = None
                self._viewport.clear_all_previews()
                self._console.log("Frame cancelado — esperando primer nodo.")
                return
            if self._interaction_mode == InteractionMode.DRAW_SHELL and self._shell_nodes:
                self._shell_nodes.clear()
                self._shell_coords.clear()
                self._viewport.clear_all_previews()
                self._console.log("Shell cancelado — esperando primer nodo.")
                return
            if self._interaction_mode != InteractionMode.SELECT:
                self.set_mode(InteractionMode.SELECT)
                return
        elif event.key() == Qt.Key.Key_R:
            if self._interaction_mode == InteractionMode.DRAW_NODE:
                self._reset_offset()
                self._console.log("Offset reseteado a (0, 0, 0)")
                return

        # Indicador visual de Shift (Free 3D temporal)
        if event.key() == Qt.Key.Key_Shift:
            if self._interaction_mode in (
                InteractionMode.DRAW_FRAME,
                InteractionMode.DRAW_SHELL,
                InteractionMode.DRAW_NODE,
            ):
                self.statusBar().showMessage(
                    "🔓 Free 3D Override (Shift) — Clic ignora restricción de plano"
                )
                return

        # Atajos de plano de trabajo (Ctrl+0/1/2/3)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            plane_map = {
                Qt.Key.Key_1: "XY",
                Qt.Key.Key_2: "XZ",
                Qt.Key.Key_3: "YZ",
                Qt.Key.Key_0: "Free",
            }
            plane = plane_map.get(event.key())
            if plane is not None:
                self._set_working_plane(plane)
                return

        super().keyPressEvent(event)
```

#### Step 6.4: Add tooltips to toolbar mode actions

- [ ] In `_build_toolbar()`, update the tooltips for mode actions. Find:

```python
        self._act_mode_frame = QAction("Dibujar Frame", self)
        self._act_mode_frame.setToolTip("Dibujar frames en viewport (2 clics)")
```

Replace with:

```python
        self._act_mode_frame = QAction("Dibujar Frame", self)
        self._act_mode_frame.setToolTip(
            "Dibujar frames en viewport (2 clics)\n"
            "Ctrl+1=XY | Ctrl+2=XZ | Ctrl+3=YZ | Ctrl+0=Free\n"
            "Shift+clic = Free 3D temporal"
        )
```

- [ ] Find:

```python
        self._act_mode_shell = QAction("Dibujar Shell", self)
        self._act_mode_shell.setToolTip("Dibujar shells en viewport (4 clics)")
```

Replace with:

```python
        self._act_mode_shell = QAction("Dibujar Shell", self)
        self._act_mode_shell.setToolTip(
            "Dibujar shells en viewport (4 clics)\n"
            "Ctrl+1=XY | Ctrl+2=XZ | Ctrl+3=YZ | Ctrl+0=Free\n"
            "Shift+clic = Free 3D temporal"
        )
```

##### Step 6 Verification Checklist
- [ ] Application launches: `python -m gui`
- [ ] **Keyboard shortcuts test:**
  1. Enter "Dibujar Frame" mode
  2. Press `Ctrl+1` → Verify console shows "Plano de trabajo: XY Plane" and Properties Panel updates to "XY Plane"
  3. Press `Ctrl+2` → Verify switches to "XZ Plane" with green grid
  4. Press `Ctrl+3` → Verify switches to "YZ Plane" with red grid
  5. Press `Ctrl+0` → Verify switches to "Free 3D" and grid disappears
- [ ] **Shift indicator test:**
  1. In drawing mode, press and hold Shift
  2. Verify status bar shows "🔓 Free 3D Override (Shift) — Clic ignora restricción de plano"
  3. Release Shift → status bar returns to normal drawing mode info
- [ ] **Tooltip test:**
  1. Hover over "Dibujar Frame" button → verify tooltip mentions Ctrl shortcuts and Shift override
  2. Hover over "Dibujar Shell" button → same
- [ ] **Full workflow test: 2D frame in XY plane:**
  1. Set XY Plane, Z=0
  2. Create frames at (0,0), (5,0), (5,3), (0,3) → all at Z=0
  3. Verify all nodes have Z=0.0
- [ ] **Full workflow test: 3D frame with elevation change:**
  1. Create base nodes at Z=0 (XY Plane, Z=0)
  2. Change elevation to Z=3.5
  3. Create top nodes at Z=3.5
  4. Shift+click from base to top → connect across elevations
- [ ] **Full workflow test: XZ plane front elevation:**
  1. Press Ctrl+2 (XZ Plane), set Y=0
  2. Draw wall frame in X-Z view
  3. Verify all nodes have Y=0.0
- [ ] **Save/Load persistence test:**
  1. Change snap settings (spacing=0.5, plane=XZ, elevation=2.0)
  2. Save project (.opss)
  3. Close and reopen
  4. Enter drawing mode → verify settings are preserved

#### Step 6 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
