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
from PySide6.QtCore import Signal, Qt, QTimer, QEvent
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from gui.core.model_data import StructuralModel, AnalysisResult

from gui.viewport.picking import find_closest_node, find_closest_element
from gui.viewport.working_plane import WorkingPlaneRenderer


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
COLOR_LOAD_FORCE = "#D32F2F"      # rojo — fuerzas
COLOR_LOAD_MOMENT = "#7B1FA2"     # morado — momentos
COLOR_HIGHLIGHT = "#FFD600"       # amarillo — selección
COLOR_LABEL = "#212121"           # negro/gris oscuro

# Nombres de actores de preview
_PREVIEW_SNAP = "_preview_snap"
_PREVIEW_NODE = "_preview_node"
_PREVIEW_OFFSET = "_preview_offset"
_PREVIEW_LINE = "_preview_line"
_PREVIEW_SHELL_LINES = "_preview_shell_lines"

COLOR_SNAP_INDICATOR = "#4CAF50"  # verde — snap indicator
COLOR_PREVIEW_NODE = "#FF9800"    # naranja — nodo preview
COLOR_PREVIEW_OFFSET = "#9E9E9E"  # gris — línea de offset
COLOR_PREVIEW = "#FF9800"         # naranja — preview líneas/shells


class VTKViewport(QWidget):
    """Widget con el viewport 3D de PyVista."""

    # Señal emitida al hacer clic en un nodo/elemento: (category, tag)
    item_picked = Signal(str, int)

    # Señales para modo dibujo
    drawing_click = Signal(float, float, float, bool)  # clic con coords mundo (snapped) + shift_pressed
    drawing_mouse_move = Signal(float, float, float)   # movimiento con coords mundo (snapped)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Crear el interactor de PyVista
        self.plotter = QtInteractor(self)
        self._layout.addWidget(self.plotter)

        # Interceptar eventos del plotter para modo dibujo
        self.plotter.installEventFilter(self)

        # Configuración base del renderer
        self._setup_renderer()

        # Estado de toggles
        self._show_labels = False
        self._show_loads = False
        self._selected_tag: int | None = None
        self._selected_category: str | None = None
        self._drawing_mode = False
        self._snap_mgr: "SnapManager | None" = None

        # Working plane Z para proyección de rayos
        self._working_plane_z: float = 0.0

        # Renderer del plano de trabajo visual
        self._working_plane_renderer: WorkingPlaneRenderer | None = None

        # Throttle para mouse move (50ms)
        self._move_timer = QTimer(self)
        self._move_timer.setSingleShot(True)
        self._move_timer.setInterval(50)
        self._move_timer.timeout.connect(self._emit_throttled_move)
        self._pending_move_coords: tuple[float, float, float] | None = None

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

        # Inicializar renderer de plano de trabajo
        self._working_plane_renderer = WorkingPlaneRenderer(self.plotter)

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

        if self._show_labels:
            self._add_node_labels(model)
            self._add_element_labels(model)
        if self._show_loads:
            self._add_load_arrows(model)

        # Re-dibujar plano de trabajo si hay renderer
        # (se redibuja después de clear para persistir entre refreshes)

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

    def toggle_labels(self, show: bool) -> None:
        """Activa/desactiva etiquetas de nodos y elementos."""
        self._show_labels = show

    def toggle_loads(self, show: bool) -> None:
        """Activa/desactiva visualización de flechas de carga."""
        self._show_loads = show

    # ------------------------------------------------------------------
    # Etiquetas
    # ------------------------------------------------------------------

    def _add_node_labels(self, model: StructuralModel) -> None:
        """Muestra etiquetas numéricas en cada nodo."""
        if not model.nodes:
            return

        points = []
        labels = []
        for tag, node in model.nodes.items():
            points.append([node.x, node.y, node.z])
            labels.append(str(tag))

        cloud = pv.PolyData(np.array(points, dtype=float))
        cloud["labels"] = labels

        self.plotter.add_point_labels(
            cloud,
            "labels",
            font_size=10,
            text_color=COLOR_LABEL,
            point_size=0,
            shape=None,
            render_points_as_spheres=False,
            always_visible=True,
            name="node_labels",
        )

    def _add_element_labels(self, model: StructuralModel) -> None:
        """Muestra etiquetas numéricas en el punto medio de cada elemento."""
        points = []
        labels = []

        for tag, elem in model.elements.items():
            ni = model.nodes.get(elem.node_i)
            nj = model.nodes.get(elem.node_j)
            if ni is None or nj is None:
                continue
            mid = [(ni.x + nj.x) / 2, (ni.y + nj.y) / 2, (ni.z + nj.z) / 2]
            points.append(mid)
            labels.append(str(tag))

        if not points:
            return

        cloud = pv.PolyData(np.array(points, dtype=float))
        cloud["labels"] = labels

        self.plotter.add_point_labels(
            cloud,
            "labels",
            font_size=9,
            text_color="#1565C0",
            point_size=0,
            shape=None,
            render_points_as_spheres=False,
            always_visible=True,
            name="element_labels",
        )

    # ------------------------------------------------------------------
    # Flechas de carga
    # ------------------------------------------------------------------

    def _add_load_arrows(self, model: StructuralModel) -> None:
        """Dibuja flechas 3D representando las cargas nodales."""
        force_origins: list[list[float]] = []
        force_dirs: list[list[float]] = []
        moment_origins: list[list[float]] = []
        moment_dirs: list[list[float]] = []

        # Recopilar todas las cargas de todos los patrones
        for pattern in model.load_patterns.values():
            for load in pattern.loads:
                node = model.nodes.get(load.node_tag)
                if node is None:
                    continue
                origin = [node.x, node.y, node.z]

                # Fuerzas
                for comp, axis in [(load.fx, [1, 0, 0]),
                                   (load.fy, [0, 1, 0]),
                                   (load.fz, [0, 0, 1])]:
                    if abs(comp) > 1e-6:
                        sign = 1.0 if comp > 0 else -1.0
                        force_origins.append(origin)
                        force_dirs.append([a * sign for a in axis])

                # Momentos
                for comp, axis in [(load.mx, [1, 0, 0]),
                                   (load.my, [0, 1, 0]),
                                   (load.mz, [0, 0, 1])]:
                    if abs(comp) > 1e-6:
                        sign = 1.0 if comp > 0 else -1.0
                        moment_origins.append(origin)
                        moment_dirs.append([a * sign for a in axis])

        # Escala de flechas (longitud fija para visibilidad)
        arrow_scale = 0.8

        # Dibujar flechas de fuerzas
        if force_origins:
            origins = np.array(force_origins, dtype=float)
            dirs = np.array(force_dirs, dtype=float)
            arrows = pv.PolyData(origins)
            arrows["vectors"] = dirs * arrow_scale
            arrows.set_active_vectors("vectors")
            glyphs = arrows.glyph(
                orient="vectors",
                scale=False,
                factor=arrow_scale,
                geom=pv.Arrow(
                    start=(0, 0, 0),
                    direction=(1, 0, 0),
                    tip_length=0.3,
                    tip_radius=0.1,
                    shaft_radius=0.03,
                    shaft_resolution=12,
                ),
            )
            self.plotter.add_mesh(
                glyphs,
                color=COLOR_LOAD_FORCE,
                name="load_force_arrows",
            )

        # Dibujar flechas de momentos (más delgadas, color distinto)
        if moment_origins:
            origins = np.array(moment_origins, dtype=float)
            dirs = np.array(moment_dirs, dtype=float)
            arrows = pv.PolyData(origins)
            arrows["vectors"] = dirs * arrow_scale * 0.7
            arrows.set_active_vectors("vectors")
            glyphs = arrows.glyph(
                orient="vectors",
                scale=False,
                factor=arrow_scale * 0.7,
                geom=pv.Arrow(
                    start=(0, 0, 0),
                    direction=(1, 0, 0),
                    tip_length=0.35,
                    tip_radius=0.08,
                    shaft_radius=0.02,
                    shaft_resolution=12,
                ),
            )
            self.plotter.add_mesh(
                glyphs,
                color=COLOR_LOAD_MOMENT,
                name="load_moment_arrows",
            )

    # ------------------------------------------------------------------
    # Highlight y Picking
    # ------------------------------------------------------------------

    def highlight_node(self, model: StructuralModel, tag: int) -> None:
        """Resalta un nodo con color amarillo."""
        self.plotter.remove_actor("highlight", render=False)
        node = model.nodes.get(tag)
        if not node:
            return
        sphere = pv.Sphere(radius=0.2, center=(node.x, node.y, node.z))
        self.plotter.add_mesh(
            sphere,
            color=COLOR_HIGHLIGHT,
            opacity=0.8,
            name="highlight",
        )

    def highlight_element(self, model: StructuralModel, tag: int) -> None:
        """Resalta un elemento con color amarillo."""
        self.plotter.remove_actor("highlight", render=False)
        elem = model.elements.get(tag)
        if not elem:
            return
        ni = model.nodes.get(elem.node_i)
        nj = model.nodes.get(elem.node_j)
        if not ni or not nj:
            return
        line = pv.Line(
            pointa=(ni.x, ni.y, ni.z),
            pointb=(nj.x, nj.y, nj.z),
        )
        self.plotter.add_mesh(
            line,
            color=COLOR_HIGHLIGHT,
            line_width=8,
            render_lines_as_tubes=True,
            name="highlight",
        )

    def clear_highlight(self) -> None:
        """Elimina cualquier resaltado activo."""
        self.plotter.remove_actor("highlight", render=False)

    def enable_picking(self, model: StructuralModel) -> None:
        """Habilita picking interactivo en el viewport."""
        self._pick_model = model

        def _on_pick(point):
            if point is None:
                return
            p = (point[0], point[1], point[2])
            # Primero intentar nodo, luego elemento
            node_tag = find_closest_node(self._pick_model, p, tolerance=0.5)
            if node_tag is not None:
                self.highlight_node(self._pick_model, node_tag)
                self.item_picked.emit("nodes", node_tag)
                return
            elem_tag = find_closest_element(self._pick_model, p, tolerance=0.5)
            if elem_tag is not None:
                self.highlight_element(self._pick_model, elem_tag)
                self.item_picked.emit("elements", elem_tag)

        self.plotter.disable_picking()
        self.plotter.enable_point_picking(
            callback=_on_pick,
            show_message=False,
            show_point=False,
            use_picker=True,
            picker="cell",
            tolerance=0.025,
        )

    def disable_picking(self) -> None:
        """Deshabilita el picking interactivo."""
        self.plotter.disable_picking()

    def set_drawing_mode(self, active: bool) -> None:
        """Establece si el viewport está en modo dibujo."""
        self._drawing_mode = active

    def set_snap_manager(self, mgr) -> None:
        """Registra el snap manager para uso durante dibujo."""
        self._snap_mgr = mgr

    def set_working_plane_z(self, z: float) -> None:
        """Establece la elevación del plano de trabajo para proyección."""
        self._working_plane_z = z

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

    def _screen_to_world(self, screen_x: int, screen_y: int) -> tuple[float, float, float] | None:
        """
        Convierte coordenadas de pantalla a coordenadas del mundo 3D,
        proyectando el rayo de la cámara sobre el plano Z = _working_plane_z.

        Retorna None si el rayo es paralelo al plano.
        """
        renderer = self.plotter.renderer

        # Obtener dimensiones del viewport
        size = self.plotter.window_size
        if size[0] == 0 or size[1] == 0:
            return None

        # Normalizar coordenadas de pantalla [0, 1]
        # Qt da Y desde arriba; VTK espera Y desde abajo
        display_x = screen_x
        display_y = size[1] - screen_y

        # Usar VTK picker para obtener el punto en el plano de trabajo
        # Crear un WorldPointPicker
        picker = self.plotter.renderer.GetRenderWindow().GetInteractor()
        if picker is None:
            return None

        # Método alternativo: ray casting manual
        # Obtener posición y dirección del rayo de la cámara
        camera = renderer.GetActiveCamera()
        if camera is None:
            return None

        # Coordenadas normalizadas del viewport
        vp = renderer.GetViewport()
        vp_width = size[0] * (vp[2] - vp[0])
        vp_height = size[1] * (vp[3] - vp[1])

        if vp_width == 0 or vp_height == 0:
            return None

        # Display to normalized viewport
        norm_x = (display_x - size[0] * vp[0]) / vp_width
        norm_y = (display_y - size[1] * vp[1]) / vp_height

        # Usar el coordinate converter de VTK
        coord = renderer.GetActiveCamera().GetPosition()
        focal = renderer.GetActiveCamera().GetFocalPoint()

        import vtk
        # Convertir display coords a world coords en near/far planes
        renderer.SetDisplayPoint(display_x, display_y, 0.0)
        renderer.DisplayToWorld()
        near_point = list(renderer.GetWorldPoint()[:3])

        renderer.SetDisplayPoint(display_x, display_y, 1.0)
        renderer.DisplayToWorld()
        wp = renderer.GetWorldPoint()
        if wp[3] != 0:
            far_point = [wp[i] / wp[3] for i in range(3)]
        else:
            far_point = list(wp[:3])

        # Ray direction
        ray_dir = [far_point[i] - near_point[i] for i in range(3)]

        # Intersect with Z = _working_plane_z
        # near_point + t * ray_dir = (x, y, _working_plane_z)
        # near_point[2] + t * ray_dir[2] = _working_plane_z
        if abs(ray_dir[2]) < 1e-12:
            return None  # Rayo paralelo al plano

        t = (self._working_plane_z - near_point[2]) / ray_dir[2]
        world_x = near_point[0] + t * ray_dir[0]
        world_y = near_point[1] + t * ray_dir[1]
        world_z = self._working_plane_z

        return (world_x, world_y, world_z)

    def _apply_snap(self, coords: tuple[float, float, float]) -> tuple[float, float, float]:
        """Aplica snap si está habilitado."""
        if self._snap_mgr and self._snap_mgr.enabled:
            return self._snap_mgr.snap_point(coords)
        return coords

    def mousePressEvent(self, event) -> None:
        """Captura clics en modo dibujo; delega al plotter en modo selección."""
        if self._drawing_mode and event.button() == Qt.MouseButton.LeftButton:
            # Obtener posición del widget interior (plotter)
            pos = self.plotter.mapFromParent(event.pos())
            coords = self._screen_to_world(pos.x(), pos.y())
            if coords is not None:
                snapped = self._apply_snap(coords)
                shift_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                self.drawing_click.emit(snapped[0], snapped[1], snapped[2], shift_pressed)
            return  # No propagar al plotter
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Captura movimiento en modo dibujo para preview."""
        if self._drawing_mode:
            pos = self.plotter.mapFromParent(event.pos())
            coords = self._screen_to_world(pos.x(), pos.y())
            if coords is not None:
                snapped = self._apply_snap(coords)
                self._pending_move_coords = snapped
                if not self._move_timer.isActive():
                    self._move_timer.start()
            return
        super().mouseMoveEvent(event)

    def _emit_throttled_move(self) -> None:
        """Emite la señal de movimiento con throttle de 50ms."""
        if self._pending_move_coords is not None:
            x, y, z = self._pending_move_coords
            self.drawing_mouse_move.emit(x, y, z)
            self._pending_move_coords = None

    # ------------------------------------------------------------------
    # Preview rendering (snap indicator)
    # ------------------------------------------------------------------

    def show_snap_indicator(self, coords: tuple[float, float, float]) -> None:
        """Muestra un indicador (cruz) en el punto de snap."""
        self.plotter.remove_actor(_PREVIEW_SNAP, render=False)
        size = 0.15
        x, y, z = coords
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

    def clear_snap_indicator(self) -> None:
        """Elimina el actor de snap indicator."""
        self.plotter.remove_actor(_PREVIEW_SNAP, render=False)
        self.plotter.render()

    def show_preview_node(self, coords: tuple[float, float, float]) -> None:
        """Muestra una esfera naranja preview en la posición dada."""
        self.plotter.remove_actor(_PREVIEW_NODE, render=False)
        x, y, z = coords
        sphere = pv.Sphere(radius=0.12, center=(x, y, z))
        self.plotter.add_mesh(
            sphere,
            color=COLOR_PREVIEW_NODE,
            opacity=0.85,
            name=_PREVIEW_NODE,
        )
        self.plotter.render()

    def show_offset_preview(
        self,
        base: tuple[float, float, float],
        final: tuple[float, float, float],
    ) -> None:
        """Muestra una línea gris desde base hasta final (offset preview)."""
        self.plotter.remove_actor(_PREVIEW_OFFSET, render=False)
        if base == final:
            return
        points = np.array([list(base), list(final)], dtype=float)
        lines = np.array([2, 0, 1])
        mesh = pv.PolyData(points, lines=lines)
        self.plotter.add_mesh(
            mesh,
            color=COLOR_PREVIEW_OFFSET,
            line_width=2,
            opacity=0.7,
            name=_PREVIEW_OFFSET,
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

    def clear_all_previews(self) -> None:
        """Elimina todos los actores de preview."""
        for name in (
            _PREVIEW_SNAP,
            _PREVIEW_NODE,
            _PREVIEW_OFFSET,
            _PREVIEW_LINE,
            _PREVIEW_SHELL_LINES,
        ):
            self.plotter.remove_actor(name, render=False)
        self.plotter.render()

    def eventFilter(self, obj, event) -> bool:
        """Intercepta eventos del plotter para capturar clics en modo dibujo."""
        if obj is self.plotter and self._drawing_mode:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    coords = self._screen_to_world(event.pos().x(), event.pos().y())
                    if coords is not None:
                        snapped = self._apply_snap(coords)
                        shift_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                        self.drawing_click.emit(snapped[0], snapped[1], snapped[2], shift_pressed)
                    return True  # consumir: no propagar clic izquierdo al interactor VTK
            elif event.type() == QEvent.Type.MouseMove:
                coords = self._screen_to_world(event.pos().x(), event.pos().y())
                if coords is not None:
                    snapped = self._apply_snap(coords)
                    self._pending_move_coords = snapped
                    if not self._move_timer.isActive():
                        self._move_timer.start()
                return False  # no consumir: permite rotación/pan con botón derecho
        return super().eventFilter(obj, event)

    def close(self) -> None:
        self.plotter.close()
        super().close()

    # ------------------------------------------------------------------
    # Deformada
    # ------------------------------------------------------------------

    def display_deformed(
        self,
        model: "StructuralModel",
        result: "AnalysisResult",
        scale: float = 50.0,
        mode: int | None = None,
    ) -> None:
        """
        Muestra la deformada del modelo.

        Parameters
        ----------
        model : StructuralModel
        result : AnalysisResult
        scale : float
            Factor de amplificación de desplazamientos.
        mode : int | None
            Número de modo (para análisis modal). None = estático.
        """
        # Obtener desplazamientos según tipo
        if mode is not None and result.mode_shapes:
            disps = result.mode_shapes.get(mode, {})
        else:
            disps = result.node_displacements

        if not disps:
            return

        # Construir coordenadas deformadas
        deformed_points: list[list[float]] = []
        deformed_lines: list[list[int]] = []
        idx = 0

        for elem in model.elements.values():
            ni = model.nodes.get(elem.node_i)
            nj = model.nodes.get(elem.node_j)
            if not ni or not nj:
                continue

            # Desplazamientos
            di = disps.get(elem.node_i, (0, 0, 0, 0, 0, 0))
            dj = disps.get(elem.node_j, (0, 0, 0, 0, 0, 0))

            p1 = [ni.x + di[0] * scale, ni.y + di[1] * scale, ni.z + di[2] * scale]
            p2 = [nj.x + dj[0] * scale, nj.y + dj[1] * scale, nj.z + dj[2] * scale]

            deformed_points.extend([p1, p2])
            deformed_lines.append([2, idx, idx + 1])
            idx += 2

        if deformed_points:
            cells = np.hstack(deformed_lines)
            mesh = pv.PolyData(
                np.array(deformed_points, dtype=float),
                lines=cells,
            )
            self.plotter.add_mesh(
                mesh,
                color="#FF6F00",   # ámbar oscuro
                line_width=3,
                render_lines_as_tubes=True,
                opacity=0.9,
                name="deformed",
            )

        # Esferas en nodos deformados
        node_pts = []
        for tag, node in model.nodes.items():
            d = disps.get(tag, (0, 0, 0))
            node_pts.append([
                node.x + d[0] * scale,
                node.y + d[1] * scale,
                node.z + d[2] * scale,
            ])
        if node_pts:
            cloud = pv.PolyData(np.array(node_pts, dtype=float))
            glyphs = cloud.glyph(
                geom=pv.Sphere(radius=0.08),
                orient=False,
                scale=False,
            )
            self.plotter.add_mesh(
                glyphs,
                color="#FF6F00",
                opacity=0.8,
                name="deformed_nodes",
            )

    def clear_deformed(self) -> None:
        """Elimina la visualización de deformada."""
        self.plotter.remove_actor("deformed", render=False)
        self.plotter.remove_actor("deformed_nodes", render=False)
