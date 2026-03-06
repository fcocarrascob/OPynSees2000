"""
Viewport 3D basado en PyVista / VTK embebido en Qt.

Renderiza el modelo estructural como:
  - Líneas para elementos (columnas azul oscuro, vigas azul claro)
  - Esferas para nodos (rojas)
  - Conos para apoyos empotrados (verdes)
  - Grilla de piso + ejes XYZ
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QVBoxLayout, QWidget

if TYPE_CHECKING:
    from gui.core.model_data import StructuralModel


# ---------------------------------------------------------------------------
# Colores (RGB 0-1)
# ---------------------------------------------------------------------------
COLOR_BG = "white"
COLOR_COLUMN = "#1565C0"       # azul oscuro
COLOR_BEAM = "#42A5F5"         # azul claro
COLOR_NODE = "#D32F2F"         # rojo
COLOR_SUPPORT = "#388E3C"      # verde
COLOR_GRID = "#E0E0E0"        # gris claro
COLOR_AXIS_X = "#D32F2F"
COLOR_AXIS_Y = "#388E3C"
COLOR_AXIS_Z = "#1976D2"


class VTKViewport(QWidget):
    """Widget con el viewport 3D de PyVista."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Crear el interactor de PyVista
        self.plotter = QtInteractor(self)
        self._layout.addWidget(self.plotter)

        # Configuración base del renderer
        self._setup_renderer()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_renderer(self) -> None:
        """Configura fondo, iluminación y cámara inicial."""
        self.plotter.set_background(COLOR_BG)

        # Iluminación suave
        self.plotter.enable_anti_aliasing("ssaa")

        # Cámara isométrica inicial
        self.plotter.camera_position = "iso"
        self.plotter.camera.zoom(0.85)

    # ------------------------------------------------------------------
    # Renderizado del modelo
    # ------------------------------------------------------------------

    def display_model(self, model: StructuralModel) -> None:
        """Renderiza el modelo completo en el viewport."""
        self.plotter.clear()

        if not model.nodes:
            self.plotter.reset_camera()
            return

        self._add_floor_grid(model)
        self._add_axes_widget()
        self._add_elements(model)
        self._add_shells(model)
        self._add_nodes(model)
        self._add_supports(model)

        self.plotter.reset_camera()
        self.plotter.camera_position = "iso"
        self.plotter.camera.zoom(0.85)

    # ------------------------------------------------------------------
    # Grilla de piso
    # ------------------------------------------------------------------

    def _add_floor_grid(self, model: StructuralModel) -> None:
        """Dibuja una grilla en el plano Z=0."""
        xs = [n.x for n in model.nodes.values()]
        ys = [n.y for n in model.nodes.values()]

        if not xs or not ys:
            return

        margin = 2.0
        x_min, x_max = min(xs) - margin, max(xs) + margin
        y_min, y_max = min(ys) - margin, max(ys) + margin

        x_range = x_max - x_min
        y_range = y_max - y_min
        n_cells_x = max(int(x_range), 4)
        n_cells_y = max(int(y_range), 4)

        grid = pv.Plane(
            center=((x_min + x_max) / 2, (y_min + y_max) / 2, 0.0),
            direction=(0, 0, 1),
            i_size=x_range,
            j_size=y_range,
            i_resolution=n_cells_x,
            j_resolution=n_cells_y,
        )

        self.plotter.add_mesh(
            grid,
            color=COLOR_GRID,
            style="wireframe",
            line_width=0.5,
            opacity=0.3,
            name="floor_grid",
        )

    # ------------------------------------------------------------------
    # Ejes XYZ
    # ------------------------------------------------------------------

    def _add_axes_widget(self) -> None:
        """Agrega un widget de ejes orientados."""
        self.plotter.add_axes(
            line_width=3,
            color="black",
            x_color=COLOR_AXIS_X,
            y_color=COLOR_AXIS_Y,
            z_color=COLOR_AXIS_Z,
            xlabel="X",
            ylabel="Y",
            zlabel="Z",
            labels_off=False,
        )

    # ------------------------------------------------------------------
    # Elementos
    # ------------------------------------------------------------------

    def _add_elements(self, model: StructuralModel) -> None:
        """Dibuja columnas y vigas como líneas."""
        col_points: list[list[float]] = []
        col_lines: list[list[int]] = []
        beam_points: list[list[float]] = []
        beam_lines: list[list[int]] = []

        col_idx = 0
        beam_idx = 0

        for elem in model.elements.values():
            if elem.is_shell:
                continue
            ni = model.nodes.get(elem.node_i)
            nj = model.nodes.get(elem.node_j)
            if ni is None or nj is None:
                continue

            p1 = [ni.x, ni.y, ni.z]
            p2 = [nj.x, nj.y, nj.z]

            # Determinar si es columna (vertical) o viga (horizontal)
            dz = abs(nj.z - ni.z)
            dh = ((nj.x - ni.x) ** 2 + (nj.y - ni.y) ** 2) ** 0.5
            is_column = dz > dh

            if is_column:
                col_points.extend([p1, p2])
                col_lines.append([2, col_idx, col_idx + 1])
                col_idx += 2
            else:
                beam_points.extend([p1, p2])
                beam_lines.append([2, beam_idx, beam_idx + 1])
                beam_idx += 2

        # Columnas
        if col_points:
            cells = np.hstack(col_lines)
            col_mesh = pv.PolyData(
                np.array(col_points, dtype=float),
                lines=cells,
            )
            self.plotter.add_mesh(
                col_mesh,
                color=COLOR_COLUMN,
                line_width=4,
                render_lines_as_tubes=True,
                name="columns",
            )

        # Vigas
        if beam_points:
            cells = np.hstack(beam_lines)
            beam_mesh = pv.PolyData(
                np.array(beam_points, dtype=float),
                lines=cells,
            )
            self.plotter.add_mesh(
                beam_mesh,
                color=COLOR_BEAM,
                line_width=3,
                render_lines_as_tubes=True,
                name="beams",
            )

    # ------------------------------------------------------------------
    # Shells
    # ------------------------------------------------------------------

    def _add_shells(self, model: StructuralModel) -> None:
        """Dibuja elementos shell como superficies cuadriláteras."""
        shell_points: list[list[float]] = []
        shell_faces: list[list[int]] = []
        idx = 0

        for elem in model.elements.values():
            if not elem.is_shell:
                continue
            nodes = []
            for nt in elem.node_tags:
                n = model.nodes.get(nt)
                if n is None:
                    break
                nodes.append(n)
            if len(nodes) != 4:
                continue

            for n in nodes:
                shell_points.append([n.x, n.y, n.z])
            shell_faces.append([4, idx, idx + 1, idx + 2, idx + 3])
            idx += 4

        if not shell_points:
            return

        faces = np.hstack(shell_faces)
        shell_mesh = pv.PolyData(
            np.array(shell_points, dtype=float),
            faces=faces,
        )
        self.plotter.add_mesh(
            shell_mesh,
            color="#80CBC4",        # teal claro
            opacity=0.5,
            show_edges=True,
            edge_color="#00695C",   # teal oscuro
            line_width=1,
            name="shells",
        )

    # ------------------------------------------------------------------
    # Nodos
    # ------------------------------------------------------------------

    def _add_nodes(self, model: StructuralModel) -> None:
        """Dibuja esferas en cada nodo libre (no empotrado)."""
        free_coords = [
            [n.x, n.y, n.z]
            for n in model.nodes.values()
            if not n.is_fully_fixed
        ]
        if not free_coords:
            return

        cloud = pv.PolyData(np.array(free_coords, dtype=float))
        glyphs = cloud.glyph(
            geom=pv.Sphere(radius=0.12),
            orient=False,
            scale=False,
        )
        self.plotter.add_mesh(
            glyphs,
            color=COLOR_NODE,
            name="nodes",
        )

    # ------------------------------------------------------------------
    # Apoyos (empotramientos)
    # ------------------------------------------------------------------

    def _add_supports(self, model: StructuralModel) -> None:
        """Dibuja conos invertidos en nodos empotrados."""
        fixed_coords = [
            [n.x, n.y, n.z]
            for n in model.nodes.values()
            if n.is_fully_fixed
        ]
        if not fixed_coords:
            return

        cloud = pv.PolyData(np.array(fixed_coords, dtype=float))
        cone = pv.Cone(
            center=(0, 0, -0.25),
            direction=(0, 0, 1),
            height=0.5,
            radius=0.2,
            resolution=16,
        )
        glyphs = cloud.glyph(
            geom=cone,
            orient=False,
            scale=False,
        )
        self.plotter.add_mesh(
            glyphs,
            color=COLOR_SUPPORT,
            name="supports",
        )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def reset_view(self) -> None:
        """Regresa la cámara a la posición isométrica."""
        self.plotter.camera_position = "iso"
        self.plotter.camera.zoom(0.85)
        self.plotter.reset_camera()

    def set_view_xy(self) -> None:
        self.plotter.view_xy()

    def set_view_xz(self) -> None:
        self.plotter.view_xz()

    def set_view_yz(self) -> None:
        self.plotter.view_yz()

    def close(self) -> None:
        self.plotter.close()
        super().close()
