# Step 2: Grid Snap System (Invisible/Minimalist)

## Goal
Implement a minimalist grid snapping system with no visual clutter. A `SnapManager` class rounds coordinates to grid spacing. A toolbar button and F9 shortcut toggle snapping. Status bar shows snap status.

## Prerequisites
Step 1 (Mode System Foundation) must be completed and committed.

---

### Step-by-Step Instructions

#### 2.1 — Create `gui/viewport/snap_manager.py`

- [x] Create a new file `gui/viewport/snap_manager.py` with the following content:

```python
"""
SnapManager — Sistema minimalista de snap a grilla.

Redondea coordenadas al espaciado de grilla (invisiblemente).
Sin grilla visual; solo snap lógico + indicador sutil.
"""

from __future__ import annotations

import math


class SnapManager:
    """Gestor de snap a grilla invisible."""

    def __init__(self, spacing: float = 1.0, enabled: bool = True) -> None:
        self._spacing = spacing
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def spacing(self) -> float:
        return self._spacing

    @spacing.setter
    def spacing(self, value: float) -> None:
        if value > 0:
            self._spacing = value

    def snap(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        """
        Redondea coordenadas al múltiplo más cercano del espaciado.

        Si snap está deshabilitado, retorna las coordenadas sin cambiar.
        """
        if not self._enabled:
            return (x, y, z)
        s = self._spacing
        return (
            round(x / s) * s,
            round(y / s) * s,
            round(z / s) * s,
        )

    def snap_point(self, point: tuple[float, float, float]) -> tuple[float, float, float]:
        """Versión con tupla de entrada."""
        return self.snap(point[0], point[1], point[2])

    def status_text(self) -> str:
        """Texto para mostrar en status bar."""
        if self._enabled:
            return f"[SNAP ON] | Grilla: {self._spacing}"
        return "[SNAP OFF]"
```

#### 2.2 — Add snap toggle to `MainWindow` toolbar

- [x] Open `gui/main_window.py`
- [x] Add this import at the top, with the other imports:

```python
from gui.viewport.snap_manager import SnapManager
```

- [x] In `MainWindow.__init__`, after `self._interaction_mode = InteractionMode.SELECT`, add:

```python
        # Snap manager
        self._snap_mgr = SnapManager(spacing=1.0, enabled=True)
```

- [x] In `_build_toolbar`, at the **end** of the method (after the `self._act_loads` block), add:

```python
        tb.addSeparator()

        self._act_snap = QAction("Snap", self)
        self._act_snap.setToolTip("Activar/desactivar snap a grilla (F9)")
        self._act_snap.setCheckable(True)
        self._act_snap.setChecked(True)
        self._act_snap.toggled.connect(self._on_toggle_snap)
        tb.addAction(self._act_snap)
```

#### 2.3 — Add F9 shortcut and snap toggle slot

- [x] Add the F9 keyboard shortcut. In `_build_menubar`, at the end of the `Opciones` menu section (after `act_units`), add:

```python
        m_options.addSeparator()

        self._act_snap_menu = QAction("Snap a grilla", self)
        self._act_snap_menu.setShortcut(QKeySequence("F9"))
        self._act_snap_menu.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self._act_snap_menu.setCheckable(True)
        self._act_snap_menu.setChecked(True)
        self._act_snap_menu.toggled.connect(self._on_toggle_snap)
        m_options.addAction(self._act_snap_menu)
```

- [x] Add the toggle slot. In the Slots section, add this method:

```python
    def _on_toggle_snap(self, checked: bool) -> None:
        """Toggle snap a grilla."""
        self._snap_mgr.enabled = checked
        # Sincronizar toolbar y menú
        self._act_snap.blockSignals(True)
        self._act_snap.setChecked(checked)
        self._act_snap.blockSignals(False)
        self._act_snap_menu.blockSignals(True)
        self._act_snap_menu.setChecked(checked)
        self._act_snap_menu.blockSignals(False)
        state = "activado" if checked else "desactivado"
        self._console.log(f"Snap {state} (grilla: {self._snap_mgr.spacing})")
```

#### 2.4 — Update status bar to show snap info

- [x] Update `_base_status_message` to include snap status:

```python
    def _base_status_message(self) -> str:
        """Genera el mensaje de status bar base con conteos del modelo."""
        n = len(self._model.nodes)
        e = len(self._model.elements)
        m = len(self._model.materials)
        s = len(self._model.sections)
        snap = self._snap_mgr.status_text()
        return (
            f"Nodos: {n}  |  Elementos: {e}  |  Materiales: {m}  |  "
            f"Secciones: {s}  |  {snap}  |  Unidades: kN, m, C"
        )
```

#### 2.5 — Pass snap manager to viewport

- [x] In `MainWindow.__init__`, after creating `self._snap_mgr`, pass it to the viewport. Add after the snap manager creation:

```python
        self._viewport.set_snap_manager(self._snap_mgr)
```

- [x] In `gui/viewport/vtk_widget.py`, add a `_snap_mgr` attribute in `__init__`, after `self._drawing_mode`:

```python
        self._snap_mgr: "SnapManager | None" = None
```

- [x] Add a `set_snap_manager` method to `VTKViewport`, after `set_drawing_mode`:

```python
    def set_snap_manager(self, mgr) -> None:
        """Registra el snap manager para uso durante dibujo."""
        self._snap_mgr = mgr
```

---

### Step 2 Verification Checklist
- [x] No build errors — run `python -m gui.main` and verify the window opens
- [ ] Toolbar shows a "Snap" checkable button (checked by default)
- [ ] Clicking "Snap" button toggles it ON/OFF, console prints snap status
- [ ] Opciones menu has "Snap a grilla" with F9 shortcut
- [ ] Pressing F9 toggles snap (syncs toolbar button and menu item)
- [ ] Status bar shows `[SNAP ON] | Grilla: 1.0` when snap is active
- [ ] Status bar shows `[SNAP OFF]` when snap is disabled

---

### Step 2 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
