# Step 5: Preview Geometry Rendering

## Goal
Add temporary geometry rendering in the viewport for visual feedback during drawing: snap indicator, preview nodes, preview lines for frames/shells, and offset preview lines. All previews update on mouse move and clear when exiting draw mode.

## Prerequisites
Steps 1–4 must be completed and committed.

---

### Step-by-Step Instructions

#### 5.1 — Add preview actor names as constants

- [ ] Open `gui/viewport/vtk_widget.py`
- [ ] Add these constants at the top of the file, after the existing color constants:

```python
# Nombres de actores de preview
_PREVIEW_NODE = "_preview_node"
_PREVIEW_SNAP = "_preview_snap"
_PREVIEW_LINE = "_preview_line"
_PREVIEW_OFFSET = "_preview_offset"
_PREVIEW_SHELL_LINES = "_preview_shell_lines"

COLOR_PREVIEW = "#FF9800"         # naranja — preview
COLOR_SNAP_INDICATOR = "#4CAF50"  # verde — snap indicator
COLOR_OFFSET_LINE = "#9E9E9E"    # gris — offset line
```

#### 5.2 — Add preview methods to `VTKViewport`

- [ ] Add these methods to `VTKViewport`, after the `_emit_throttled_move` method and before the `close` method:

```python
    # ------------------------------------------------------------------
    # Preview rendering (temporal geometry)
    # ------------------------------------------------------------------

    def show_preview_node(self, coords: tuple[float, float, float]) -> None:
        """Muestra una esfera semi-transparente en la posición indicada."""
        self.plotter.remove_actor(_PREVIEW_NODE, render=False)
        sphere = pv.Sphere(radius=0.15, center=coords)
        self.plotter.add_mesh(
            sphere,
            color=COLOR_PREVIEW,
            opacity=0.6,
            name=_PREVIEW_NODE,
        )
        self.plotter.render()

    def show_snap_indicator(self, coords: tuple[float, float, float]) -> None:
        """Muestra un indicador sutil (cruz) en el punto de snap."""
        self.plotter.remove_actor(_PREVIEW_SNAP, render=False)
        size = 0.15
        x, y, z = coords
        # Cruz: 3 líneas cortas en X, Y, Z
        points = np.array([
            [x - size, y, z], [x + size, y, z],
            [x, y - size, z], [x, y + size, z],
            [x, y, z - size], [x, y, z + size],
        ], dtype=float)
        lines = np.array([2, 0, 1, 2, 2, 3, 2, 4, 5])
        mesh = pv.PolyData(points, lines=lines)
        self.plotter.add_mesh(
            mesh,
            color=COLOR_SNAP_INDICATOR,
            line_width=2,
            name=_PREVIEW_SNAP,
        )
        self.plotter.render()

    def show_preview_line(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
    ) -> None:
        """Muestra una línea preview entre dos puntos (para frames)."""
        self.plotter.remove_actor(_PREVIEW_LINE, render=False)
        line = pv.Line(pointa=start, pointb=end)
        self.plotter.add_mesh(
            line,
            color=COLOR_PREVIEW,
            line_width=3,
            render_lines_as_tubes=True,
            opacity=0.7,
            name=_PREVIEW_LINE,
        )
        self.plotter.render()

    def show_preview_shell_lines(
        self, points: list[tuple[float, float, float]]
    ) -> None:
        """Muestra líneas preview progresivas para shell (1-4 puntos)."""
        self.plotter.remove_actor(_PREVIEW_SHELL_LINES, render=False)
        if len(points) < 2:
            self.plotter.render()
            return

        pts = np.array(points, dtype=float)
        n = len(pts)
        line_cells = []
        for i in range(n - 1):
            line_cells.extend([2, i, i + 1])
        # Cerrar si hay 4 puntos (quad completo)
        if n == 4:
            line_cells.extend([2, n - 1, 0])

        mesh = pv.PolyData(pts, lines=np.array(line_cells))
        self.plotter.add_mesh(
            mesh,
            color=COLOR_PREVIEW,
            line_width=3,
            render_lines_as_tubes=True,
            opacity=0.7,
            name=_PREVIEW_SHELL_LINES,
        )
        self.plotter.render()

    def show_offset_preview(
        self,
        base: tuple[float, float, float],
        final: tuple[float, float, float],
    ) -> None:
        """Muestra una línea punteada del punto base al punto con offset."""
        self.plotter.remove_actor(_PREVIEW_OFFSET, render=False)
        if base == final:
            return
        line = pv.Line(pointa=base, pointb=final)
        self.plotter.add_mesh(
            line,
            color=COLOR_OFFSET_LINE,
            line_width=1,
            style="wireframe",
            opacity=0.5,
            name=_PREVIEW_OFFSET,
        )
        self.plotter.render()

    def clear_all_previews(self) -> None:
        """Elimina todos los actores de preview."""
        for name in (
            _PREVIEW_NODE,
            _PREVIEW_SNAP,
            _PREVIEW_LINE,
            _PREVIEW_OFFSET,
            _PREVIEW_SHELL_LINES,
        ):
            self.plotter.remove_actor(name, render=False)
        self.plotter.render()
```

#### 5.3 — Clear previews when exiting draw mode

- [ ] In `MainWindow.set_mode()`, add a preview clear call when switching to SELECT mode. In the `if mode == InteractionMode.SELECT:` block, add after `self._viewport.set_drawing_mode(False)`:

```python
            self._viewport.clear_all_previews()
```

#### 5.4 — Update mouse move handler for preview

- [ ] Replace the placeholder `_on_drawing_mouse_move` in `MainWindow` with:

```python
    def _on_drawing_mouse_move(self, x: float, y: float, z: float) -> None:
        """Actualiza previews durante movimiento del mouse en modo dibujo."""
        if self._interaction_mode == InteractionMode.DRAW_NODE:
            # Mostrar snap indicator + preview node
            if self._snap_mgr and self._snap_mgr.enabled:
                self._viewport.show_snap_indicator((x, y, z))
            self._viewport.show_preview_node((x, y, z))

        elif self._interaction_mode == InteractionMode.DRAW_FRAME:
            if self._snap_mgr and self._snap_mgr.enabled:
                self._viewport.show_snap_indicator((x, y, z))
            # Preview line se maneja en Step 7 (después del primer clic)

        elif self._interaction_mode == InteractionMode.DRAW_SHELL:
            if self._snap_mgr and self._snap_mgr.enabled:
                self._viewport.show_snap_indicator((x, y, z))
            # Preview shell se maneja en Step 8 (después de clics previos)
```

---

### Step 5 Verification Checklist
- [ ] No build errors — run `python -m gui.main` and verify the window opens
- [ ] Enter "Dibujar Nodo" mode, move mouse in viewport:
  - [ ] Orange semi-transparent sphere follows the mouse
  - [ ] Green cross/snap indicator appears at grid intersections when snap is ON
- [ ] Enter "Dibujar Frame" mode, move mouse:
  - [ ] Green snap indicator appears when snap is ON
- [ ] Switch back to "Selección" mode:
  - [ ] All preview geometry disappears
- [ ] Preview rendering is smooth (throttled at 50ms, no flickering)
- [ ] Camera rotation/panning still works in draw modes

---

### Step 5 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
