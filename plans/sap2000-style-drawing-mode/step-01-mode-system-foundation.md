# Step 1: Mode System Foundation

## Goal
Create an `InteractionMode` enum and add mode tracking to `MainWindow` and `VTKViewport`, establishing the foundation for all mode-based interactions (SELECT, DRAW_NODE, DRAW_FRAME, DRAW_SHELL).

## Prerequisites
Make sure you are currently on the `feature/sap2000-drawing-mode` branch before beginning implementation.
If not, switch to the correct branch. If the branch does not exist, create it from `main`.

---

### Step-by-Step Instructions

#### 1.1 — Add `InteractionMode` enum to `main_window.py`

- [x] Open `gui/main_window.py`
- [x] Add the following import at the top of the file, after the existing `from enum import ...` or after the `from __future__ import annotations` line:

```python
from enum import Enum, auto
```

- [x] Add the `InteractionMode` enum **before** the `MainWindow` class definition (after the `THEME_PATH` constant):

```python
class InteractionMode(Enum):
    """Modos de interacción del viewport."""
    SELECT = auto()
    DRAW_NODE = auto()
    DRAW_FRAME = auto()
    DRAW_SHELL = auto()
```

#### 1.2 — Add mode tracking state to `MainWindow.__init__`

- [x] In `MainWindow.__init__`, add the mode tracking attribute after the `self._undo_mgr` line and before `# Construcción de la interfaz`:

```python
        # Modo de interacción activo
        self._interaction_mode = InteractionMode.SELECT
```

#### 1.3 — Add `set_mode()` method to `MainWindow`

- [x] Add the following method to `MainWindow`, in a new section after the Status bar section and before the Slots section. Place it right before the `# Slots` comment block:

```python
    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def set_mode(self, mode: InteractionMode) -> None:
        """Cambia el modo de interacción activo."""
        old_mode = self._interaction_mode
        self._interaction_mode = mode

        if mode == InteractionMode.SELECT:
            self._viewport.enable_picking(self._model)
            self._viewport.set_drawing_mode(False)
            self.statusBar().showMessage(self._base_status_message())
        else:
            self._viewport.disable_picking()
            self._viewport.set_drawing_mode(True)
            mode_names = {
                InteractionMode.DRAW_NODE: "Dibujar Nodo",
                InteractionMode.DRAW_FRAME: "Dibujar Frame",
                InteractionMode.DRAW_SHELL: "Dibujar Shell",
            }
            mode_label = mode_names.get(mode, "")
            self.statusBar().showMessage(
                f"Modo: {mode_label}  |  Clic en viewport para crear  |  "
                f"Escape → Selección"
            )

        if old_mode != mode:
            self._console.log(f"Modo cambiado: {mode.name}")

    def _base_status_message(self) -> str:
        """Genera el mensaje de status bar base con conteos del modelo."""
        n = len(self._model.nodes)
        e = len(self._model.elements)
        m = len(self._model.materials)
        s = len(self._model.sections)
        return (
            f"Nodos: {n}  |  Elementos: {e}  |  Materiales: {m}  |  "
            f"Secciones: {s}  |  Unidades: kN, m, C"
        )
```

#### 1.4 — Update `_update_statusbar` to use `_base_status_message`

- [x] Replace the existing `_update_statusbar` method body to use the new helper:

```python
    def _update_statusbar(self) -> None:
        if self._interaction_mode == InteractionMode.SELECT:
            self.statusBar().showMessage(self._base_status_message())
```

#### 1.5 — Add `disable_picking`, `set_drawing_mode` to `VTKViewport`

- [x] Open `gui/viewport/vtk_widget.py`
- [x] Add a `_drawing_mode` attribute in `__init__`, after `self._selected_category`:

```python
        self._drawing_mode = False
```

- [x] Add these methods to `VTKViewport`, after the `enable_picking` method and before the `close` method:

```python
    def disable_picking(self) -> None:
        """Deshabilita el picking interactivo."""
        self.plotter.disable_picking()

    def set_drawing_mode(self, active: bool) -> None:
        """Establece si el viewport está en modo dibujo."""
        self._drawing_mode = active
```

#### 1.6 — Add Escape key handler for mode switching

- [x] In `MainWindow`, add a `keyPressEvent` override. Place it after the `closeEvent` method at the bottom of the class:

```python
    def keyPressEvent(self, event) -> None:
        """Maneja atajos de teclado globales."""
        if event.key() == Qt.Key.Key_Escape:
            if self._interaction_mode != InteractionMode.SELECT:
                self.set_mode(InteractionMode.SELECT)
                return
        super().keyPressEvent(event)
```

---

### Step 1 Verification Checklist
- [x] No build errors — run `python -m gui.main` and verify the window opens
- [ ] The application starts in `SELECT` mode (default)
- [ ] Status bar shows node/element counts as before
- [ ] Pressing Escape does nothing visually (already in SELECT mode)
- [ ] Verify in Python console or add a temporary `print(self._interaction_mode)` in `set_mode()` to confirm mode tracking works

---

### Step 1 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
