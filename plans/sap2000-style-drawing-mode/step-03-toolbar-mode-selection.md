# Step 3: Toolbar Mode Selection UI

## Goal
Add mutually exclusive toolbar buttons for each interaction mode using `QActionGroup`. Create checkable actions for "Selección", "Dibujar Nodo", "Dibujar Frame", "Dibujar Shell". Connect toolbar actions to mode switching logic.

## Prerequisites
Steps 1–2 must be completed and committed.

---

### Step-by-Step Instructions

#### 3.1 — Add `QActionGroup` import

- [ ] Open `gui/main_window.py`
- [ ] Add `QActionGroup` to the existing `PySide6.QtGui` import line:

```python
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
```

#### 3.2 — Add mode toolbar in `_build_toolbar`

- [ ] In `_build_toolbar`, at the **very end** of the method (after the `Snap` button block), add:

```python
        # --- Separador de modos ---
        tb.addSeparator()

        # Grupo exclusivo de modos
        self._mode_group = QActionGroup(self)
        self._mode_group.setExclusive(True)

        self._act_mode_select = QAction("Selección", self)
        self._act_mode_select.setToolTip("Modo selección (Escape)")
        self._act_mode_select.setCheckable(True)
        self._act_mode_select.setChecked(True)
        self._act_mode_select.setData(InteractionMode.SELECT)
        self._mode_group.addAction(self._act_mode_select)
        tb.addAction(self._act_mode_select)

        self._act_mode_node = QAction("Dibujar Nodo", self)
        self._act_mode_node.setToolTip("Dibujar nodos en viewport (1 clic)")
        self._act_mode_node.setCheckable(True)
        self._act_mode_node.setData(InteractionMode.DRAW_NODE)
        self._mode_group.addAction(self._act_mode_node)
        tb.addAction(self._act_mode_node)

        self._act_mode_frame = QAction("Dibujar Frame", self)
        self._act_mode_frame.setToolTip("Dibujar frames en viewport (2 clics)")
        self._act_mode_frame.setCheckable(True)
        self._act_mode_frame.setData(InteractionMode.DRAW_FRAME)
        self._mode_group.addAction(self._act_mode_frame)
        tb.addAction(self._act_mode_frame)

        self._act_mode_shell = QAction("Dibujar Shell", self)
        self._act_mode_shell.setToolTip("Dibujar shells en viewport (4 clics)")
        self._act_mode_shell.setCheckable(True)
        self._act_mode_shell.setData(InteractionMode.DRAW_SHELL)
        self._mode_group.addAction(self._act_mode_shell)
        tb.addAction(self._act_mode_shell)

        self._mode_group.triggered.connect(self._on_mode_action_triggered)
```

#### 3.3 — Add mode action triggered slot

- [ ] Add this slot to the Mode switching section (after `_base_status_message`):

```python
    def _on_mode_action_triggered(self, action: QAction) -> None:
        """Slot cuando se selecciona un modo desde el toolbar."""
        mode = action.data()
        if mode is not None:
            self.set_mode(mode)
```

#### 3.4 — Update `set_mode` to sync toolbar buttons

- [ ] Modify the existing `set_mode` method to also sync the toolbar button state. Replace the full method with:

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
            self._update_statusbar()
        else:
            self._viewport.disable_picking()
            self._viewport.set_drawing_mode(True)
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

---

### Step 3 Verification Checklist
- [ ] No build errors — run `python -m gui.main` and verify the window opens
- [ ] Toolbar shows 4 new buttons: `Selección | Dibujar Nodo | Dibujar Frame | Dibujar Shell`
- [ ] `Selección` is checked by default
- [ ] Clicking any mode button checks only that button (mutually exclusive)
- [ ] Status bar updates to show current mode when in draw modes
- [ ] Status bar reverts to counts when in SELECT mode
- [ ] Console logs mode changes
- [ ] Pressing Escape returns to `Selección` mode (toolbar button syncs)
- [ ] Toggle between modes repeatedly — only one button is checked at any time

---

### Step 3 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
