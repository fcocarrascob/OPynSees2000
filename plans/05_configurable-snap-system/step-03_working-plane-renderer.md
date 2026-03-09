# Step 3: Create Working Plane Visual Renderer

## Goal
Create a VTK-based working plane visualization that renders a semi-transparent colored grid plane at the configured elevation, with color coding by plane type.

## Prerequisites
Steps 1-2 must be completed and committed.

### Step-by-Step Instructions

#### Step 3.1: Create the working_plane.py module

- [ ] Create a new file `gui/viewport/working_plane.py`
- [ ] Paste the following complete code:

```python
"""
WorkingPlaneRenderer — Visualización del plano de trabajo activo.

Renderiza un plano semi-transparente con grilla en el viewport VTK,
usando colores codificados por tipo de plano:
  - XY: azul   (0.3, 0.3, 0.8)
  - XZ: verde  (0.3, 0.8, 0.3)
  - YZ: rojo   (0.8, 0.3, 0.3)
  - Free: oculto
"""

from __future__ import annotations

import numpy as np
import pyvista as pv


# Colores por plano (RGB 0-1)
PLANE_COLORS = {
    "XY": (0.3, 0.3, 0.8),
    "XZ": (0.3, 0.8, 0.3),
    "YZ": (0.8, 0.3, 0.3),
}

# Opacidad del plano
PLANE_OPACITY = 0.12
GRID_LINE_OPACITY = 0.25

# Nombres de actores
_ACTOR_PLANE = "_working_plane"
_ACTOR_GRID = "_working_plane_grid"

# Extensión del plano (unidades del modelo)
PLANE_HALF_SIZE = 15.0


class WorkingPlaneRenderer:
    """Gestiona la visualización del plano de trabajo en el viewport."""

    def __init__(self, plotter: pv.Plotter) -> None:
        self._plotter = plotter

    def update(
        self,
        plane_mode: str,
        elevation: float,
        spacing: float,
    ) -> None:
        """
        Actualiza la visualización del plano de trabajo.

        Parameters
        ----------
        plane_mode : str
            "XY", "XZ", "YZ" o "Free".
        elevation : float
            Elevación del eje bloqueado.
        spacing : float
            Espaciado de la grilla.
        """
        self.hide()

        if plane_mode == "Free" or plane_mode not in PLANE_COLORS:
            return

        color = PLANE_COLORS[plane_mode]
        half = PLANE_HALF_SIZE
        s = max(spacing, 0.1)  # mínimo 0.1 para evitar grillas excesivas
        n_lines = int(2 * half / s)
        # Limitar cantidad de líneas para rendimiento
        if n_lines > 200:
            n_lines = 200
            s = 2 * half / n_lines

        if plane_mode == "XY":
            self._draw_plane_xy(elevation, half, s, n_lines, color)
        elif plane_mode == "XZ":
            self._draw_plane_xz(elevation, half, s, n_lines, color)
        elif plane_mode == "YZ":
            self._draw_plane_yz(elevation, half, s, n_lines, color)

    def hide(self) -> None:
        """Oculta el plano de trabajo."""
        self._plotter.remove_actor(_ACTOR_PLANE, render=False)
        self._plotter.remove_actor(_ACTOR_GRID, render=False)

    def _draw_plane_xy(
        self, z: float, half: float, spacing: float, n_lines: int, color: tuple
    ) -> None:
        """Dibuja plano en XY a Z=z."""
        # Plano semi-transparente
        plane = pv.Plane(
            center=(0, 0, z),
            direction=(0, 0, 1),
            i_size=half * 2,
            j_size=half * 2,
            i_resolution=1,
            j_resolution=1,
        )
        self._plotter.add_mesh(
            plane,
            color=color,
            opacity=PLANE_OPACITY,
            name=_ACTOR_PLANE,
        )

        # Grilla de líneas
        points = []
        lines = []
        idx = 0

        # Líneas paralelas a X (variando Y)
        y_start = -half
        for i in range(n_lines + 1):
            y = y_start + i * spacing
            if y > half:
                break
            points.append([-half, y, z])
            points.append([half, y, z])
            lines.extend([2, idx, idx + 1])
            idx += 2

        # Líneas paralelas a Y (variando X)
        x_start = -half
        for i in range(n_lines + 1):
            x = x_start + i * spacing
            if x > half:
                break
            points.append([x, -half, z])
            points.append([x, half, z])
            lines.extend([2, idx, idx + 1])
            idx += 2

        if points:
            mesh = pv.PolyData(
                np.array(points, dtype=float),
                lines=np.array(lines),
            )
            self._plotter.add_mesh(
                mesh,
                color=color,
                line_width=1,
                opacity=GRID_LINE_OPACITY,
                name=_ACTOR_GRID,
            )

    def _draw_plane_xz(
        self, y: float, half: float, spacing: float, n_lines: int, color: tuple
    ) -> None:
        """Dibuja plano en XZ a Y=y."""
        plane = pv.Plane(
            center=(0, y, 0),
            direction=(0, 1, 0),
            i_size=half * 2,
            j_size=half * 2,
            i_resolution=1,
            j_resolution=1,
        )
        self._plotter.add_mesh(
            plane,
            color=color,
            opacity=PLANE_OPACITY,
            name=_ACTOR_PLANE,
        )

        points = []
        lines = []
        idx = 0

        # Líneas paralelas a X (variando Z)
        z_start = -half
        for i in range(n_lines + 1):
            z = z_start + i * spacing
            if z > half:
                break
            points.append([-half, y, z])
            points.append([half, y, z])
            lines.extend([2, idx, idx + 1])
            idx += 2

        # Líneas paralelas a Z (variando X)
        x_start = -half
        for i in range(n_lines + 1):
            x = x_start + i * spacing
            if x > half:
                break
            points.append([x, y, -half])
            points.append([x, y, half])
            lines.extend([2, idx, idx + 1])
            idx += 2

        if points:
            mesh = pv.PolyData(
                np.array(points, dtype=float),
                lines=np.array(lines),
            )
            self._plotter.add_mesh(
                mesh,
                color=color,
                line_width=1,
                opacity=GRID_LINE_OPACITY,
                name=_ACTOR_GRID,
            )

    def _draw_plane_yz(
        self, x: float, half: float, spacing: float, n_lines: int, color: tuple
    ) -> None:
        """Dibuja plano en YZ a X=x."""
        plane = pv.Plane(
            center=(x, 0, 0),
            direction=(1, 0, 0),
            i_size=half * 2,
            j_size=half * 2,
            i_resolution=1,
            j_resolution=1,
        )
        self._plotter.add_mesh(
            plane,
            color=color,
            opacity=PLANE_OPACITY,
            name=_ACTOR_PLANE,
        )

        points = []
        lines = []
        idx = 0

        # Líneas paralelas a Y (variando Z)
        z_start = -half
        for i in range(n_lines + 1):
            z = z_start + i * spacing
            if z > half:
                break
            points.append([x, -half, z])
            points.append([x, half, z])
            lines.extend([2, idx, idx + 1])
            idx += 2

        # Líneas paralelas a Z (variando Y)
        y_start = -half
        for i in range(n_lines + 1):
            yv = y_start + i * spacing
            if yv > half:
                break
            points.append([x, yv, -half])
            points.append([x, yv, half])
            lines.extend([2, idx, idx + 1])
            idx += 2

        if points:
            mesh = pv.PolyData(
                np.array(points, dtype=float),
                lines=np.array(lines),
            )
            self._plotter.add_mesh(
                mesh,
                color=color,
                line_width=1,
                opacity=GRID_LINE_OPACITY,
                name=_ACTOR_GRID,
            )
```

#### Step 3.2: Integrate WorkingPlaneRenderer into VTKViewport

- [ ] Open `gui/viewport/vtk_widget.py`
- [ ] Add the following import near the top, after the existing `from gui.viewport.picking import ...` line:

```python
from gui.viewport.working_plane import WorkingPlaneRenderer
```

- [ ] In the `VTKViewport.__init__()` method, add the following line **after** `self._working_plane_z: float = 0.0`:

```python
        # Renderer del plano de trabajo visual
        self._working_plane_renderer: WorkingPlaneRenderer | None = None
```

- [ ] In the `_setup_renderer()` method, add the following line **at the end** of the method body (after `self.plotter.camera.zoom(0.85)`):

```python
        # Inicializar renderer de plano de trabajo
        self._working_plane_renderer = WorkingPlaneRenderer(self.plotter)
```

- [ ] Add the following **new method** to the `VTKViewport` class, right after the `set_working_plane_z()` method:

```python
    def update_working_plane_visual(
        self,
        plane_mode: str,
        elevation: float,
        spacing: float,
    ) -> None:
        """Actualiza la visualización del plano de trabajo."""
        if self._working_plane_renderer is not None:
            self._working_plane_renderer.update(plane_mode, elevation, spacing)
            self.plotter.render()

    def hide_working_plane_visual(self) -> None:
        """Oculta la visualización del plano de trabajo."""
        if self._working_plane_renderer is not None:
            self._working_plane_renderer.hide()
            self.plotter.render()
```

- [ ] In the `display_model()` method, add a call to re-render the working plane **before** the `self.plotter.reset_camera()` line. Find the line `self._add_supports(model)` and add after all the conditional blocks (`if self._show_labels...`, `if self._show_loads...`), but **before** `self.plotter.reset_camera()`:

```python
        # Re-dibujar plano de trabajo si hay renderer
        # (se redibuja después de clear para persistir entre refreshes)
```

> **Note:** The actual working plane display will be triggered from MainWindow in Step 5 when the full integration happens. For now, the renderer is ready to be called.

##### Step 3 Verification Checklist
- [ ] No import errors:
  ```python
  python -c "from gui.viewport.working_plane import WorkingPlaneRenderer; print('Import OK')"
  ```
- [ ] VTKViewport has the new methods:
  ```python
  python -c "
  from gui.viewport.vtk_widget import VTKViewport
  assert hasattr(VTKViewport, 'update_working_plane_visual')
  assert hasattr(VTKViewport, 'hide_working_plane_visual')
  print('Methods exist OK')
  "
  ```
- [ ] WorkingPlaneRenderer logic check:
  ```python
  python -c "
  from gui.viewport.working_plane import PLANE_COLORS, VALID_PLANES
  assert 'XY' in PLANE_COLORS
  assert 'XZ' in PLANE_COLORS
  assert 'YZ' in PLANE_COLORS
  assert 'Free' not in PLANE_COLORS
  print('Colors OK')
  "
  ```
  > Note: `VALID_PLANES` is defined in snap_manager.py, not working_plane.py. Adjust import if needed, or just check PLANE_COLORS.
- [ ] Application still launches: `python -m gui`

#### Step 3 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
