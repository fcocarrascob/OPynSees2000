# Step 5: UI Enhancements and Keyboard Shortcuts

## Goal
Add keyboard shortcuts for faster plane switching and elevation adjustments: PgUp/PgDn for elevation increment/decrement, Tab for cycling plane modes, and Ctrl+1/2/3/4 for direct plane selection. Update the statusbar to show plane info with shortcut hints.

## Prerequisites
Steps 1–4 must be completed and committed.

---

### Step-by-Step Instructions

#### 5.1 — Add keyboard shortcuts to `keyPressEvent`

- [ ] Open `gui/main_window.py`
- [ ] Find the `keyPressEvent` method. It currently handles Escape and R. Replace the ENTIRE method with this expanded version:

```python
    def keyPressEvent(self, event) -> None:
        """Maneja atajos de teclado globales."""
        key = event.key()
        modifiers = event.modifiers()
        in_drawing = self._interaction_mode != InteractionMode.SELECT

        # ── Escape ──
        if key == Qt.Key.Key_Escape:
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

        # ── R: Reset offset (only in DRAW_NODE) ──
        elif key == Qt.Key.Key_R:
            if self._interaction_mode == InteractionMode.DRAW_NODE:
                self._reset_offset()
                self._console.log("Offset reseteado a (0, 0, 0)")
                return

        # ── Ctrl+1/2/3/4: Direct plane selection (only in drawing mode) ──
        elif modifiers & Qt.KeyboardModifier.ControlModifier and in_drawing:
            template = self._model.drawing_template
            if key == Qt.Key.Key_1:
                template.working_plane_mode = "XY"
                self._sync_plane_and_view("XY", template.working_plane_elevation)
                self._refresh_drawing_properties()
                self._console.log("Plano XY seleccionado (Ctrl+1)")
                event.accept()
                return
            elif key == Qt.Key.Key_2:
                template.working_plane_mode = "XZ"
                self._sync_plane_and_view("XZ", template.working_plane_elevation)
                self._refresh_drawing_properties()
                self._console.log("Plano XZ seleccionado (Ctrl+2)")
                event.accept()
                return
            elif key == Qt.Key.Key_3:
                template.working_plane_mode = "YZ"
                self._sync_plane_and_view("YZ", template.working_plane_elevation)
                self._refresh_drawing_properties()
                self._console.log("Plano YZ seleccionado (Ctrl+3)")
                event.accept()
                return
            elif key == Qt.Key.Key_4:
                template.working_plane_mode = "Free"
                self._sync_plane_and_view("Free", template.working_plane_elevation)
                self._refresh_drawing_properties()
                self._console.log("Modo Free 3D seleccionado (Ctrl+4)")
                event.accept()
                return

        # ── Tab: Cycle plane mode (only in drawing mode) ──
        elif key == Qt.Key.Key_Tab and in_drawing:
            template = self._model.drawing_template
            cycle = ["XY", "XZ", "YZ", "Free"]
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                cycle = list(reversed(cycle))
            current_idx = cycle.index(template.working_plane_mode) if template.working_plane_mode in cycle else 0
            next_idx = (current_idx + 1) % len(cycle)
            new_mode = cycle[next_idx]
            template.working_plane_mode = new_mode
            self._sync_plane_and_view(new_mode, template.working_plane_elevation)
            self._refresh_drawing_properties()
            self._console.log(f"Plano cambiado: {new_mode} (Tab)")
            event.accept()
            return

        # ── PgUp/PgDn: Elevation change (only in drawing mode) ──
        elif key == Qt.Key.Key_PageUp and in_drawing:
            template = self._model.drawing_template
            template.working_plane_elevation += template.snap_spacing
            self._sync_plane_and_view(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
            self._refresh_drawing_properties()
            self._console.log(
                f"Elevación: {template.working_plane_elevation:.2f}m (PgUp)"
            )
            event.accept()
            return

        elif key == Qt.Key.Key_PageDown and in_drawing:
            template = self._model.drawing_template
            template.working_plane_elevation -= template.snap_spacing
            self._sync_plane_and_view(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
            self._refresh_drawing_properties()
            self._console.log(
                f"Elevación: {template.working_plane_elevation:.2f}m (PgDn)"
            )
            event.accept()
            return

        super().keyPressEvent(event)
```

---

#### 5.2 — Update `_update_drawing_statusbar` with shortcut hints

- [ ] Find the `_update_drawing_statusbar` method and replace it entirely:

```python
    def _update_drawing_statusbar(self) -> None:
        """Actualiza la status bar con info del modo de dibujo actual."""
        if self._interaction_mode == InteractionMode.SELECT:
            self._update_statusbar()
            return

        template = self._model.drawing_template
        mode_names = {
            InteractionMode.DRAW_NODE: "Nodo",
            InteractionMode.DRAW_FRAME: "Frame",
            InteractionMode.DRAW_SHELL: "Shell",
        }
        mode_label = mode_names.get(self._interaction_mode, "")

        # Info de plano
        plane = template.working_plane_mode
        if plane == "Free":
            plane_info = "Plano: Free 3D"
        elif plane == "XY":
            plane_info = f"Plano: XY Z={template.working_plane_elevation:.1f}m"
        elif plane == "XZ":
            plane_info = f"Plano: XZ Y={template.working_plane_elevation:.1f}m"
        elif plane == "YZ":
            plane_info = f"Plano: YZ X={template.working_plane_elevation:.1f}m"
        else:
            plane_info = f"Plano: {plane}"

        snap_state = "ON" if self._snap_mgr.enabled else "OFF"

        self.statusBar().showMessage(
            f"Dibujo | {mode_label} | {plane_info} | "
            f"Grid: {template.snap_spacing}m | Snap: {snap_state} | "
            f"Tab/Ctrl+1-4: plano | PgUp/PgDn: elev | Esc: salir"
        )
```

---

### Step 5 Verification Checklist

- [ ] No import or syntax errors
- [ ] Enter drawing mode (DRAW_FRAME), verify statusbar shows: "Dibujo | Frame | Plano: XY Z=0.0m | Grid: 1.0m | Snap: ON | Tab/Ctrl+1-4: plano | PgUp/PgDn: elev | Esc: salir"
- [ ] Press PgUp 3 times with spacing=1.0 → verify elevation goes 0→1→2→3, statusbar updates
- [ ] Press PgDn once → verify elevation goes 3→2, statusbar updates
- [ ] Press Tab → verify cycle XY→XZ, camera changes to front view
- [ ] Press Tab again → XZ→YZ, side view
- [ ] Press Tab → YZ→Free, isometric view
- [ ] Press Tab → Free→XY, top view (cycle complete)
- [ ] Press Shift+Tab → verify reverse cycle (XY→Free→YZ→XZ→XY)
- [ ] Press Ctrl+2 → verify instant switch to XZ mode
- [ ] Press Ctrl+4 → verify instant switch to Free mode
- [ ] Press Ctrl+1 → verify instant switch to XY mode
- [ ] Press Ctrl+3 → verify instant switch to YZ mode
- [ ] Verify PgUp/PgDn work with spacing=0.5m (goes 0→0.5→1.0)
- [ ] In SELECT mode, press Tab → verify no effect (shortcut disabled)
- [ ] In SELECT mode, press PgUp → verify no effect
- [ ] Verify Ctrl+1-4 don't interfere in SELECT mode
- [ ] Verify Escape still works to cancel frame/shell operations and exit drawing mode

---

#### Step 5 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
