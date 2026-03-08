# Step 6: Draw Node Mode with Relative Offset

## Goal
Implement the complete DRAW_NODE mode: click in viewport to create nodes with optional relative coordinate offset (ΔX, ΔY, ΔZ). Includes status bar offset widgets, undo support via `DictChangeCommand`, offset preview line, and R key to reset offset.

## Prerequisites
Steps 1–5 must be completed and committed.

---

### Step-by-Step Instructions

#### 6.1 — Add `CompoundUndoCommand` to `undo_manager.py`

- [x] Open `gui/core/undo_manager.py`
- [x] Add the following class **after** `DictChangeCommand` and **before** `UndoManager`:

```python
class CompoundUndoCommand(UndoCommand):
    """Comando compuesto que agrupa múltiples sub-comandos como una sola operación."""

    def __init__(self, commands: list[UndoCommand], desc: str = "") -> None:
        self._commands = list(commands)
        self._desc = desc

    def redo(self) -> None:
        for cmd in self._commands:
            cmd.redo()

    def undo(self) -> None:
        for cmd in reversed(self._commands):
            cmd.undo()

    def description(self) -> str:
        return self._desc
```

#### 6.2 — Add offset widgets to status bar

- [x] Open `gui/main_window.py`
- [x] Add the import for `QDoubleSpinBox` and `QLabel` to the PySide6.QtWidgets import (if not already present):

```python
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
)
```

- [x] Add the import for `CompoundUndoCommand`:

```python
from gui.core.undo_manager import UndoManager, DictChangeCommand, CompoundUndoCommand
```

- [x] In `_build_statusbar`, replace the entire method with:

```python
    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)

        # Offset widgets (solo visibles en DRAW_NODE)
        self._offset_label = QLabel("  Offset:")
        self._offset_dx = QDoubleSpinBox()
        self._offset_dx.setPrefix("ΔX: ")
        self._offset_dx.setSuffix(" m")
        self._offset_dx.setDecimals(2)
        self._offset_dx.setRange(-1e6, 1e6)
        self._offset_dx.setValue(0.0)
        self._offset_dx.setFixedWidth(120)

        self._offset_dy = QDoubleSpinBox()
        self._offset_dy.setPrefix("ΔY: ")
        self._offset_dy.setSuffix(" m")
        self._offset_dy.setDecimals(2)
        self._offset_dy.setRange(-1e6, 1e6)
        self._offset_dy.setValue(0.0)
        self._offset_dy.setFixedWidth(120)

        self._offset_dz = QDoubleSpinBox()
        self._offset_dz.setPrefix("ΔZ: ")
        self._offset_dz.setSuffix(" m")
        self._offset_dz.setDecimals(2)
        self._offset_dz.setRange(-1e6, 1e6)
        self._offset_dz.setValue(0.0)
        self._offset_dz.setFixedWidth(120)

        sb.addPermanentWidget(self._offset_label)
        sb.addPermanentWidget(self._offset_dx)
        sb.addPermanentWidget(self._offset_dy)
        sb.addPermanentWidget(self._offset_dz)

        # Ocultar por defecto
        self._set_offset_widgets_visible(False)

        self._update_statusbar()

    def _set_offset_widgets_visible(self, visible: bool) -> None:
        """Muestra u oculta los widgets de offset en la status bar."""
        self._offset_label.setVisible(visible)
        self._offset_dx.setVisible(visible)
        self._offset_dy.setVisible(visible)
        self._offset_dz.setVisible(visible)

    def _get_offset(self) -> tuple[float, float, float]:
        """Retorna el offset actual (ΔX, ΔY, ΔZ)."""
        return (
            self._offset_dx.value(),
            self._offset_dy.value(),
            self._offset_dz.value(),
        )

    def _reset_offset(self) -> None:
        """Resetea el offset a (0, 0, 0)."""
        self._offset_dx.setValue(0.0)
        self._offset_dy.setValue(0.0)
        self._offset_dz.setValue(0.0)
```

#### 6.3 — Show/hide offset widgets based on mode

- [x] In `set_mode()`, update to show/hide offset widgets. Add these lines inside the method:
  - After the viewport mode setup for SELECT:
  
```python
            self._set_offset_widgets_visible(False)
```

  - In the `else` block (draw modes), add before the statusBar messages:
  
```python
            self._set_offset_widgets_visible(mode == InteractionMode.DRAW_NODE)
```

The full updated `set_mode` should be:

```python
    def set_mode(self, mode: InteractionMode) -> None:
        """Cambia el modo de interacción activo."""
        old_mode = self._interaction_mode
        self._interaction_mode = mode

        # Sincronizar toolbar buttons
        mode_actions = {
            InteractionMode.SELECT: self._act_mode_select,
            InteractionMode.DRAW_NODE: self._act_mode_node,
            InteractionMode.DRAW_FRAME: self._act_mode_frame,
            InteractionMode.DRAW_SHELL: self._act_mode_shell,
        }
        target_action = mode_actions.get(mode)
        if target_action and not target_action.isChecked():
            target_action.setChecked(True)

        if mode == InteractionMode.SELECT:
            self._viewport.enable_picking(self._model)
            self._viewport.set_drawing_mode(False)
            self._viewport.clear_all_previews()
            self._set_offset_widgets_visible(False)
            self._update_statusbar()
        else:
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
            self.statusBar().showMessage(
                f"Modo: {mode_label}  |  {snap}  |  "
                f"Clic en viewport para crear  |  Escape → Selección"
            )

        if old_mode != mode:
            self._console.log(f"Modo cambiado: {mode.name}")
```

#### 6.4 — Implement DRAW_NODE click handler

- [x] Replace the placeholder `_on_drawing_click` method in `MainWindow` with:

```python
    def _on_drawing_click(self, x: float, y: float, z: float) -> None:
        """Maneja clic en modo dibujo."""
        if self._interaction_mode == InteractionMode.DRAW_NODE:
            self._handle_draw_node(x, y, z)
        elif self._interaction_mode == InteractionMode.DRAW_FRAME:
            self._handle_draw_frame(x, y, z)
        elif self._interaction_mode == InteractionMode.DRAW_SHELL:
            self._handle_draw_shell(x, y, z)

    def _handle_draw_node(self, x: float, y: float, z: float) -> None:
        """Crea un nodo en la posición clickeada + offset."""
        dx, dy, dz = self._get_offset()
        final_x = x + dx
        final_y = y + dy
        final_z = z + dz

        tag = self._model.next_node_tag()
        from gui.core.model_data import Node
        node = Node(tag=tag, x=final_x, y=final_y, z=final_z)

        cmd = DictChangeCommand(
            target_dict=self._model.nodes,
            key=tag,
            old_value=None,
            new_value=node,
            desc=f"Crear nodo {tag} ({final_x:.2f}, {final_y:.2f}, {final_z:.2f})",
        )
        self._undo_mgr.execute(cmd)
        self._refresh_all()
        self._console.log_success(
            f"Nodo {tag} creado: ({final_x:.2f}, {final_y:.2f}, {final_z:.2f})"
        )

    def _handle_draw_frame(self, x: float, y: float, z: float) -> None:
        """Placeholder — implementado en Step 7."""
        pass

    def _handle_draw_shell(self, x: float, y: float, z: float) -> None:
        """Placeholder — implementado en Step 8."""
        pass
```

#### 6.5 — Update mouse move preview for offset

- [x] Replace the `_on_drawing_mouse_move` method with:

```python
    def _on_drawing_mouse_move(self, x: float, y: float, z: float) -> None:
        """Actualiza previews durante movimiento del mouse en modo dibujo."""
        if self._interaction_mode == InteractionMode.DRAW_NODE:
            # Snap indicator en la posición del cursor
            if self._snap_mgr and self._snap_mgr.enabled:
                self._viewport.show_snap_indicator((x, y, z))

            # Calcular posición final con offset
            dx, dy, dz = self._get_offset()
            final = (x + dx, y + dy, z + dz)

            # Preview node en posición final
            self._viewport.show_preview_node(final)

            # Si hay offset, mostrar línea punteada desde click a final
            if dx != 0 or dy != 0 or dz != 0:
                self._viewport.show_offset_preview((x, y, z), final)
            else:
                self.plotter_clear_actor("_preview_offset")

        elif self._interaction_mode == InteractionMode.DRAW_FRAME:
            if self._snap_mgr and self._snap_mgr.enabled:
                self._viewport.show_snap_indicator((x, y, z))
            self._update_frame_preview(x, y, z)

        elif self._interaction_mode == InteractionMode.DRAW_SHELL:
            if self._snap_mgr and self._snap_mgr.enabled:
                self._viewport.show_snap_indicator((x, y, z))
            self._update_shell_preview(x, y, z)

    def _update_frame_preview(self, x: float, y: float, z: float) -> None:
        """Actualiza preview de frame — implementado en Step 7."""
        pass

    def _update_shell_preview(self, x: float, y: float, z: float) -> None:
        """Actualiza preview de shell — implementado en Step 8."""
        pass
```

**Note:** The `self.plotter_clear_actor(...)` line won't exist. Replace that block with a direct viewport call. The corrected code for clearing offset preview when there's no offset:

```python
            # Si hay offset, mostrar línea punteada desde click a final
            if dx != 0 or dy != 0 or dz != 0:
                self._viewport.show_offset_preview((x, y, z), final)
```

(The offset preview will simply not be drawn when offset is (0,0,0) — `show_offset_preview` already handles `base == final`.)

#### 6.6 — Add R key handler for offset reset

- [x] Update the `keyPressEvent` override in `MainWindow`:

```python
    def keyPressEvent(self, event) -> None:
        """Maneja atajos de teclado globales."""
        if event.key() == Qt.Key.Key_Escape:
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

#### 6.7 — Re-enable picking after refresh in draw mode

- [x] Update `_refresh_all` to respect the current mode. Replace:

```python
    def _refresh_all(self) -> None:
        """Refresca tree, viewport y statusbar."""
        self._tree.refresh(self._model)
        self._viewport.display_model(self._model)
        if self._interaction_mode == InteractionMode.SELECT:
            self._viewport.enable_picking(self._model)
        self._update_statusbar()
```

---

### Step 6 Verification Checklist
- [ ] No build errors — run `python -m gui.main` and verify the window opens
- [ ] Switch to "Dibujar Nodo" mode:
  - [ ] Offset widgets (ΔX, ΔY, ΔZ) appear in the status bar
  - [ ] Default offset is (0, 0, 0)
- [ ] Click in viewport with offset (0, 0, 0):
  - [ ] Node created at exact click position (snapped)
  - [ ] Console prints "Nodo X creado: (x, y, z)"
  - [ ] Node appears in viewport and model tree
- [ ] Set offset to ΔX=2, ΔZ=3, click at (5, 3, 0):
  - [ ] Node created at (7, 3, 3)
  - [ ] Preview shows orange sphere at (7, 3, 3) and grey offset line from (5, 3, 0) to (7, 3, 3)
- [ ] Create multiple nodes — each gets sequential tag
- [ ] Press R key — offset resets to (0, 0, 0)
- [ ] Press Ctrl+Z — last node is undone (removed)
- [ ] Press Ctrl+Shift+Z — node is redone (restored)
- [ ] Press Escape — returns to SELECT mode, offset widgets hidden
- [ ] Switch back to SELECT — picking works as before

---

### Step 6 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
