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
