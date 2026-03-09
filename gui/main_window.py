"""
MainWindow — Ventana principal de OPynSees2000.

Layout:
  ┌────────────────────────────────────────────────────────┐
  │  Menú Bar                                              │
  ├────────────────────────────────────────────────────────┤
  │  Toolbar                                               │
  ├──────────┬──────────────────────────┬──────────────────┤
  │ Model    │                          │ Properties       │
  │ Tree     │     VTK Viewport         │ Panel            │
  │          │                          │                  │
  ├──────────┴──────────────────────────┴──────────────────┤
  │  Console                                               │
  ├────────────────────────────────────────────────────────┤
  │  Status Bar                                            │
  └────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QEvent, QObject
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
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

from gui.core.model_data import StructuralModel
from gui.core.undo_manager import UndoManager, DictChangeCommand, CompoundUndoCommand
from gui.dialogs.about_dialog import AboutDialog
from gui.panels.console_panel import ConsolePanel
from gui.panels.model_tree import ModelTree
from gui.panels.properties_panel import PropertiesPanel
from gui.viewport.vtk_widget import VTKViewport
from gui.viewport.snap_manager import SnapManager
from gui.core.project_io import save_project, load_project, FILE_FILTER
from gui.dialogs.element_dialog import ElementDialog
from gui.dialogs.fixity_dialog import FixityDialog
from gui.dialogs.load_pattern_dialog import LoadPatternDialog
from gui.dialogs.material_dialog import MaterialDialog
from gui.dialogs.node_dialog import NodeDialog
from gui.dialogs.nodal_load_dialog import NodalLoadDialog
from gui.dialogs.section_dialog import SectionDialog
from gui.dialogs.transf_dialog import TransfDialog
from gui.dialogs.script_preview_dialog import ScriptPreviewDialog
from gui.dialogs.analysis_dialog import AnalysisDialog
from gui.core.model_data import AnalysisResult


THEME_PATH = Path(__file__).parent / "theme" / "light.qss"


class InteractionMode(Enum):
    """Modos de interacción del viewport."""
    SELECT = auto()
    DRAW_NODE = auto()
    DRAW_FRAME = auto()
    DRAW_SHELL = auto()


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("OPynSees2000 — OpenSeesPy GUI")
        self.resize(1400, 900)

        # Modelo de datos
        self._model = StructuralModel.create_demo()
        self._current_file: Path | None = None
        self._analysis_result: AnalysisResult | None = None

        # Widgets
        self._tree = ModelTree()
        self._viewport = VTKViewport()
        self._properties = PropertiesPanel()
        self._console = ConsolePanel()

        self._undo_mgr = UndoManager(max_stack=100)
        self._properties.set_undo_manager(self._undo_mgr)

        # Modo de interacción activo
        self._interaction_mode = InteractionMode.SELECT

        # Snap manager
        self._snap_mgr = SnapManager(spacing=1.0, enabled=True)

        # Estado de dibujo de frames (2 clics)
        self._frame_first_node: int | None = None  # tag del primer nodo (None = esperando 1er clic)
        self._frame_first_coords: tuple[float, float, float] | None = None

        # Construcción de la interfaz
        self._build_menubar()
        self._build_toolbar()
        self._build_layout()
        self._build_statusbar()

        self._viewport.set_snap_manager(self._snap_mgr)

        # Conexiones
        self._tree.item_selected.connect(self._on_tree_item_selected)
        self._tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self._viewport.item_picked.connect(self._on_viewport_pick)
        self._properties.property_changed.connect(self._on_property_changed)
        self._undo_mgr.state_changed.connect(self._update_undo_actions)

        self._viewport.drawing_click.connect(self._on_drawing_click)
        self._viewport.drawing_mouse_move.connect(self._on_drawing_mouse_move)

        # Capturar teclado del viewport VTK (para Escape, etc.)
        self._viewport.plotter.installEventFilter(self)

        # Carga inicial
        self._refresh_all()
        self._console.log(
            f"Modelo demo cargado: {len(self._model.nodes)} nodos, "
            f"{len(self._model.elements)} elementos"
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        """Construye el layout con splitters."""
        # Splitter horizontal: tree | viewport | properties
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.addWidget(self._tree)
        h_splitter.addWidget(self._viewport)
        h_splitter.addWidget(self._properties)
        h_splitter.setStretchFactor(0, 0)   # tree: fijo
        h_splitter.setStretchFactor(1, 1)   # viewport: expansible
        h_splitter.setStretchFactor(2, 0)   # properties: fijo
        h_splitter.setSizes([240, 800, 260])

        # Splitter vertical: [h_splitter] | console
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.addWidget(h_splitter)
        v_splitter.addWidget(self._console)
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 0)
        v_splitter.setSizes([680, 160])

        self.setCentralWidget(v_splitter)

    # ------------------------------------------------------------------
    # Menu Bar
    # ------------------------------------------------------------------

    def _build_menubar(self) -> None:
        mb = self.menuBar()

        # --- Archivo ---
        m_file = mb.addMenu("&Archivo")

        act_new = QAction("Nuevo modelo", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._on_new_model)
        m_file.addAction(act_new)

        act_open = QAction("Abrir...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._on_open)
        m_file.addAction(act_open)

        act_save = QAction("Guardar como...", self)
        act_save.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save.triggered.connect(self._on_save_as)
        m_file.addAction(act_save)

        m_file.addSeparator()

        act_demo = QAction("Cargar demo", self)
        act_demo.triggered.connect(self._on_load_demo)
        m_file.addAction(act_demo)

        m_file.addSeparator()

        act_export = QAction("Exportar script OpenSeesPy...", self)
        act_export.setShortcut(QKeySequence("Ctrl+E"))
        act_export.setToolTip("Generar y previsualizar script OpenSeesPy")
        act_export.triggered.connect(self._on_export_script)
        m_file.addAction(act_export)

        m_file.addSeparator()

        act_exit = QAction("Salir", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        m_file.addAction(act_exit)

        # --- Editar ---
        m_edit = mb.addMenu("&Editar")

        self._act_undo = QAction("Deshacer", self)
        self._act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._act_undo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self._act_undo.setEnabled(False)
        self._act_undo.triggered.connect(self._on_undo)
        m_edit.addAction(self._act_undo)

        self._act_redo = QAction("Rehacer", self)
        self._act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._act_redo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self._act_redo.setEnabled(False)
        self._act_redo.triggered.connect(self._on_redo)
        m_edit.addAction(self._act_redo)

        m_edit.addSeparator()

        act_delete = QAction("Eliminar selección", self)
        act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        act_delete.setEnabled(True)
        act_delete.triggered.connect(self._on_delete_selected)
        m_edit.addAction(act_delete)
        self._act_delete = act_delete

        # --- Definir ---
        m_define = mb.addMenu("&Definir")

        act_mat = QAction("Materiales...", self)
        act_mat.setToolTip("Definir materiales uniaxiales")
        act_mat.triggered.connect(self._on_define_material)
        m_define.addAction(act_mat)

        act_sec = QAction("Secciones...", self)
        act_sec.setToolTip("Definir secciones transversales")
        act_sec.triggered.connect(self._on_define_section)
        m_define.addAction(act_sec)

        act_transf = QAction("Transformaciones...", self)
        act_transf.setToolTip("Definir transformaciones geométricas")
        act_transf.triggered.connect(self._on_define_transf)
        m_define.addAction(act_transf)

        act_pattern = QAction("Patrones de carga...", self)
        act_pattern.setToolTip("Definir patrones de carga (TimeSeries)")
        act_pattern.triggered.connect(self._on_define_pattern)
        m_define.addAction(act_pattern)

        # --- Dibujar ---
        m_draw = mb.addMenu("Di&bujar")

        act_node = QAction("Nodo...", self)
        act_node.setToolTip("Agregar nodos al modelo")
        act_node.triggered.connect(self._on_draw_node)
        m_draw.addAction(act_node)

        act_elem = QAction("Elemento...", self)
        act_elem.setToolTip("Agregar elementos al modelo")
        act_elem.triggered.connect(self._on_draw_element)
        m_draw.addAction(act_elem)

        # --- Asignar ---
        m_assign = mb.addMenu("&Asignar")

        act_fix = QAction("Restricciones...", self)
        act_fix.setToolTip("Asignar condiciones de borde a nodos")
        act_fix.triggered.connect(self._on_assign_fixity)
        m_assign.addAction(act_fix)

        act_load = QAction("Cargas nodales...", self)
        act_load.setToolTip("Asignar fuerzas y momentos a nodos")
        act_load.triggered.connect(self._on_assign_nodal_loads)
        m_assign.addAction(act_load)

        act_mass = QAction("Masas...", self)
        act_mass.setEnabled(False)
        m_assign.addAction(act_mass)

        # --- Analizar ---
        m_analyze = mb.addMenu("A&nalizar")

        act_analysis = QAction("Configurar y ejecutar...", self)
        act_analysis.setShortcut(QKeySequence("F5"))
        act_analysis.setToolTip("Abrir diálogo de análisis (F5)")
        act_analysis.triggered.connect(self._on_open_analysis)
        m_analyze.addAction(act_analysis)

        m_analyze.addSeparator()

        self._act_show_deformed = QAction("Mostrar deformada", self)
        self._act_show_deformed.setCheckable(True)
        self._act_show_deformed.setEnabled(False)
        self._act_show_deformed.toggled.connect(self._on_toggle_deformed)
        m_analyze.addAction(self._act_show_deformed)

        # --- Mostrar ---
        m_display = mb.addMenu("M&ostrar")

        act_iso = QAction("Vista isométrica", self)
        act_iso.setShortcut(QKeySequence("0"))
        act_iso.triggered.connect(self._viewport.reset_view)
        m_display.addAction(act_iso)

        act_xy = QAction("Vista XY (planta)", self)
        act_xy.setShortcut(QKeySequence("7"))
        act_xy.triggered.connect(self._viewport.set_view_xy)
        m_display.addAction(act_xy)

        act_xz = QAction("Vista XZ (frontal)", self)
        act_xz.setShortcut(QKeySequence("1"))
        act_xz.triggered.connect(self._viewport.set_view_xz)
        m_display.addAction(act_xz)

        act_yz = QAction("Vista YZ (lateral)", self)
        act_yz.setShortcut(QKeySequence("3"))
        act_yz.triggered.connect(self._viewport.set_view_yz)
        m_display.addAction(act_yz)

        m_display.addSeparator()

        act_refresh = QAction("Refrescar viewport", self)
        act_refresh.setShortcut(QKeySequence("F6"))
        act_refresh.triggered.connect(self._refresh_viewport)
        m_display.addAction(act_refresh)

        # --- Opciones ---
        m_options = mb.addMenu("&Opciones")

        act_units = QAction("Unidades: kN, m, s, °C", self)
        act_units.setEnabled(False)
        m_options.addAction(act_units)

        m_options.addSeparator()

        self._act_snap_menu = QAction("Snap a grilla", self)
        self._act_snap_menu.setShortcut(QKeySequence("F9"))
        self._act_snap_menu.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self._act_snap_menu.setCheckable(True)
        self._act_snap_menu.setChecked(True)
        self._act_snap_menu.toggled.connect(self._on_toggle_snap)
        m_options.addAction(self._act_snap_menu)

        # --- Ayuda ---
        m_help = mb.addMenu("A&yuda")

        act_about = QAction("Acerca de...", self)
        act_about.triggered.connect(self._on_about)
        m_help.addAction(act_about)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        tb = QToolBar("Principal")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        self.addToolBar(tb)

        # Acciones con texto (sin íconos por ahora — minimalista)
        act_new = QAction("Nuevo", self)
        act_new.setToolTip("Nuevo modelo vacío (Ctrl+N)")
        act_new.triggered.connect(self._on_new_model)
        tb.addAction(act_new)

        act_demo = QAction("Demo", self)
        act_demo.setToolTip("Cargar pórtico demo")
        act_demo.triggered.connect(self._on_load_demo)
        tb.addAction(act_demo)

        act_open_tb = QAction("Abrir", self)
        act_open_tb.setToolTip("Abrir proyecto (Ctrl+O)")
        act_open_tb.triggered.connect(self._on_open)
        tb.addAction(act_open_tb)

        act_save_tb = QAction("Guardar", self)
        act_save_tb.setToolTip("Guardar como... (Ctrl+Shift+S)")
        act_save_tb.triggered.connect(self._on_save_as)
        tb.addAction(act_save_tb)

        tb.addSeparator()

        act_iso = QAction("3D", self)
        act_iso.setToolTip("Vista isométrica (0)")
        act_iso.triggered.connect(self._viewport.reset_view)
        tb.addAction(act_iso)

        act_xy = QAction("XY", self)
        act_xy.setToolTip("Vista planta (7)")
        act_xy.triggered.connect(self._viewport.set_view_xy)
        tb.addAction(act_xy)

        act_xz = QAction("XZ", self)
        act_xz.setToolTip("Vista frontal (1)")
        act_xz.triggered.connect(self._viewport.set_view_xz)
        tb.addAction(act_xz)

        act_yz = QAction("YZ", self)
        act_yz.setToolTip("Vista lateral (3)")
        act_yz.triggered.connect(self._viewport.set_view_yz)
        tb.addAction(act_yz)

        tb.addSeparator()

        act_refresh = QAction("Refrescar", self)
        act_refresh.setToolTip("Refrescar viewport (F6)")
        act_refresh.triggered.connect(self._refresh_viewport)
        tb.addAction(act_refresh)

        tb.addSeparator()

        self._act_labels = QAction("Etiquetas", self)
        self._act_labels.setToolTip("Mostrar/ocultar etiquetas de nodos y elementos")
        self._act_labels.setCheckable(True)
        self._act_labels.setChecked(False)
        self._act_labels.toggled.connect(self._on_toggle_labels)
        tb.addAction(self._act_labels)

        self._act_loads = QAction("Cargas", self)
        self._act_loads.setToolTip("Mostrar/ocultar flechas de carga")
        self._act_loads.setCheckable(True)
        self._act_loads.setChecked(False)
        self._act_loads.toggled.connect(self._on_toggle_loads)
        tb.addAction(self._act_loads)

        tb.addSeparator()

        self._act_snap = QAction("Snap", self)
        self._act_snap.setToolTip("Activar/desactivar snap a grilla (F9)")
        self._act_snap.setCheckable(True)
        self._act_snap.setChecked(True)
        self._act_snap.toggled.connect(self._on_toggle_snap)
        tb.addAction(self._act_snap)

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

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

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

    def _update_statusbar(self) -> None:
        if self._interaction_mode == InteractionMode.SELECT:
            self.statusBar().showMessage(self._base_status_message())

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def _find_or_create_node(
        self, x: float, y: float, z: float, tolerance: float = 0.15
    ) -> tuple[int, bool]:
        """
        Busca un nodo existente cercano o crea uno nuevo.

        Returns:
            (tag, was_created) — tag del nodo y si fue creado nuevo.
        """
        from gui.viewport.picking import find_closest_node
        existing = find_closest_node(self._model, (x, y, z), tolerance=tolerance)
        if existing is not None:
            return (existing, False)

        tag = self._model.next_node_tag()
        from gui.core.model_data import Node
        node = Node(tag=tag, x=x, y=y, z=z)
        return (tag, True)

    def _on_mode_action_triggered(self, action: QAction) -> None:
        """Slot cuando se selecciona un modo desde el toolbar."""
        mode = action.data()
        if mode is not None:
            self.set_mode(mode)

    def set_mode(self, mode: InteractionMode) -> None:
        """Cambia el modo de interacción activo."""
        old_mode = self._interaction_mode
        self._interaction_mode = mode

        # Reset frame drawing state
        self._frame_first_node = None
        self._frame_first_coords = None

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
                f"Clic en viewport para crear  |  Escape \u2192 Selecci\u00f3n"
            )

        if old_mode != mode:
            self._console.log(f"Modo cambiado: {mode.name}")

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

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

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
        """Maneja clics en modo DRAW_FRAME (secuencia de 2 clics)."""
        from gui.viewport.picking import find_closest_node
        from gui.core.model_data import Node, Element, ElementType

        if self._frame_first_node is None:
            # === PRIMER CLIC: establecer nodo I ===
            existing = find_closest_node(self._model, (x, y, z), tolerance=0.15)
            if existing is not None:
                self._frame_first_node = existing
                node = self._model.nodes[existing]
                self._frame_first_coords = (node.x, node.y, node.z)
                self._console.log(
                    f"Frame: nodo I = {existing} (existente)"
                )
            else:
                # Crear nodo nuevo como primer nodo
                tag = self._model.next_node_tag()
                node = Node(tag=tag, x=x, y=y, z=z)
                cmd = DictChangeCommand(
                    target_dict=self._model.nodes,
                    key=tag,
                    old_value=None,
                    new_value=node,
                    desc=f"Crear nodo {tag} para frame",
                )
                self._undo_mgr.execute(cmd)
                self._frame_first_node = tag
                self._frame_first_coords = (x, y, z)
                self._refresh_all()
                self._console.log(
                    f"Frame: nodo I = {tag} (nuevo: {x:.2f}, {y:.2f}, {z:.2f})"
                )
        else:
            # === SEGUNDO CLIC: establecer nodo J y crear frame ===
            commands: list = []

            # Resolver nodo J
            existing_j = find_closest_node(self._model, (x, y, z), tolerance=0.15)
            if existing_j is not None:
                node_j_tag = existing_j
                self._console.log(f"Frame: nodo J = {existing_j} (existente)")
            else:
                node_j_tag = self._model.next_node_tag()
                node_j = Node(tag=node_j_tag, x=x, y=y, z=z)
                commands.append(DictChangeCommand(
                    target_dict=self._model.nodes,
                    key=node_j_tag,
                    old_value=None,
                    new_value=node_j,
                    desc=f"Crear nodo {node_j_tag} para frame",
                ))
                self._console.log(
                    f"Frame: nodo J = {node_j_tag} (nuevo: {x:.2f}, {y:.2f}, {z:.2f})"
                )

            # Prevenir frame de un nodo a sí mismo
            if node_j_tag == self._frame_first_node:
                self._console.log_error("Frame: nodos I y J no pueden ser iguales.")
                return

            # Crear elemento frame
            elem_tag = self._model.next_element_tag()
            element = Element(
                tag=elem_tag,
                elem_type=ElementType.ELASTIC_BEAM_COLUMN,
                node_i=self._frame_first_node,
                node_j=node_j_tag,
                section_tag=None,
                transf_tag=None,
            )
            commands.append(DictChangeCommand(
                target_dict=self._model.elements,
                key=elem_tag,
                old_value=None,
                new_value=element,
                desc=f"Crear elemento {elem_tag}",
            ))

            # Ejecutar como comando compuesto
            if len(commands) == 1:
                self._undo_mgr.execute(commands[0])
            else:
                compound = CompoundUndoCommand(
                    commands,
                    desc=f"Crear frame {elem_tag} [{self._frame_first_node}\u2192{node_j_tag}]",
                )
                self._undo_mgr.execute(compound)

            self._refresh_all()
            self._console.log_success(
                f"Frame {elem_tag} creado: [{self._frame_first_node}\u2192{node_j_tag}] "
                f"elasticBeamColumn"
            )

            # Reset para siguiente frame (continuo)
            self._frame_first_node = None
            self._frame_first_coords = None
            self._viewport.clear_all_previews()

    def _handle_draw_shell(self, x: float, y: float, z: float) -> None:
        """Placeholder — implementado en Step 8."""
        pass

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

        elif self._interaction_mode == InteractionMode.DRAW_FRAME:
            if self._snap_mgr and self._snap_mgr.enabled:
                self._viewport.show_snap_indicator((x, y, z))
            self._update_frame_preview(x, y, z)

        elif self._interaction_mode == InteractionMode.DRAW_SHELL:
            if self._snap_mgr and self._snap_mgr.enabled:
                self._viewport.show_snap_indicator((x, y, z))
            self._update_shell_preview(x, y, z)

    def _update_frame_preview(self, x: float, y: float, z: float) -> None:
        """Actualiza preview de línea durante el segundo clic del frame."""
        if self._frame_first_coords is not None:
            # Mostrar preview line desde primer nodo hasta cursor
            self._viewport.show_preview_line(self._frame_first_coords, (x, y, z))
            self._viewport.show_preview_node((x, y, z))
        else:
            # Antes del primer clic, solo mostrar preview node
            self._viewport.show_preview_node((x, y, z))

    def _update_shell_preview(self, x: float, y: float, z: float) -> None:
        """Actualiza preview de shell — implementado en Step 8."""
        pass

    def _on_new_model(self) -> None:
        self._model.clear()
        self._current_file = None
        self._update_title()
        self._refresh_all()
        self._console.log("Modelo limpiado.")
        self._undo_mgr.clear()

    def _on_load_demo(self) -> None:
        self._model = StructuralModel.create_demo()
        self._refresh_all()
        self._console.log_success(
            f"Demo cargado: {len(self._model.nodes)} nodos, "
            f"{len(self._model.elements)} elementos"
        )

    def _on_tree_item_selected(self, category: str, tag: int) -> None:
        self._properties.show_item(self._model, category, tag)

    def _on_tree_item_double_clicked(self, item, column) -> None:
        """Abre diálogo de edición al hacer doble-clic en un ítem del tree."""
        category = item.data(0, 100)
        tag = item.data(0, 101)
        if tag is None:
            return

        if category == "materials":
            mat = self._model.materials.get(tag)
            if not mat:
                return
            dlg = MaterialDialog(self, material=mat)
            if dlg.exec():
                edited = dlg.get_material()
                self._model.materials[tag] = edited
                self._refresh_all()
                self._console.log(f"Material {tag} editado: {edited.name}")

        elif category == "sections":
            sec = self._model.sections.get(tag)
            if not sec:
                return
            dlg = SectionDialog(self, section=sec, model=self._model)
            if dlg.exec():
                edited = dlg.get_section()
                self._model.sections[tag] = edited
                self._refresh_all()
                self._console.log(f"Sección {tag} editada: {edited.name}")

        elif category == "geom_transfs":
            transf = self._model.geom_transfs.get(tag)
            if not transf:
                return
            dlg = TransfDialog(self, transf=transf)
            if dlg.exec():
                edited = dlg.get_transf()
                self._model.geom_transfs[tag] = edited
                self._refresh_all()
                self._console.log(
                    f"Transformación {tag} editada: {edited.transf_type.value}"
                )

        elif category == "nodes":
            node = self._model.nodes.get(tag)
            if not node:
                return
            dlg = NodeDialog(self, node=node)
            if dlg.exec():
                edited = dlg.get_node()
                self._model.nodes[tag] = edited
                self._refresh_all()
                self._console.log(
                    f"Nodo {tag} editado: ({edited.x}, {edited.y}, {edited.z})"
                )

        elif category == "elements":
            elem = self._model.elements.get(tag)
            if not elem:
                return
            dlg = ElementDialog(self, model=self._model, element=elem)
            if dlg.exec():
                edited = dlg.get_element()
                self._model.elements[tag] = edited
                self._refresh_all()
                self._console.log(
                    f"Elemento {tag} editado: {edited.elem_type.value}"
                )

        elif category == "load_patterns":
            pat = self._model.load_patterns.get(tag)
            if not pat:
                return
            dlg = LoadPatternDialog(self, pattern=pat)
            if dlg.exec():
                edited = dlg.get_pattern()
                self._model.load_patterns[tag] = edited
                self._refresh_all()
                self._console.log(f"Patrón {tag} editado: {edited.name}")

    def _on_about(self) -> None:
        dlg = AboutDialog(self)
        dlg.exec()

    def _on_open(self) -> None:
        """Abre un archivo .opss."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir proyecto", "", FILE_FILTER,
        )
        if not path:
            return
        try:
            self._model, notification = load_project(Path(path))
            self._current_file = Path(path)
            self._refresh_all()
            self._update_title()
            self._console.log_success(f"Proyecto abierto: {path}")
            if notification:
                self._console.log(notification)
        except Exception as exc:
            self._console.log_error(f"Error al abrir: {exc}")

    def _on_save_as(self) -> None:
        """Guarda el modelo como archivo .opss."""
        default_name = str(self._current_file) if self._current_file else ""
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar proyecto como", default_name, FILE_FILTER,
        )
        if not path:
            return
        if not path.endswith(".opss"):
            path += ".opss"
        try:
            save_project(self._model, Path(path))
            self._current_file = Path(path)
            self._update_title()
            self._console.log_success(f"Proyecto guardado: {path}")
        except Exception as exc:
            self._console.log_error(f"Error al guardar: {exc}")

    def _on_draw_node(self) -> None:
        """Abre el diálogo para crear nodos."""
        dlg = NodeDialog(
            self,
            next_tag=self._model.next_node_tag(),
        )
        result = dlg.exec()
        nodes = dlg.get_created_nodes()
        if nodes:
            for node in nodes:
                self._model.nodes[node.tag] = node
            self._refresh_all()
            self._console.log_success(
                f"{len(nodes)} nodo(s) creado(s): "
                + ", ".join(str(n.tag) for n in nodes)
            )

    def _on_draw_element(self) -> None:
        """Abre el diálogo para crear un elemento."""
        dlg = ElementDialog(
            self,
            model=self._model,
            next_tag=self._model.next_element_tag(),
        )
        if dlg.exec():
            elem = dlg.get_element()
            self._model.elements[elem.tag] = elem
            self._refresh_all()
            self._console.log_success(
                f"Elemento creado: {elem.tag} — {elem.elem_type.value} "
                f"[{elem.node_i}→{elem.node_j}]"
            )

    def _on_assign_fixity(self) -> None:
        """Abre el diálogo para asignar restricciones."""
        if not self._model.nodes:
            self._console.log_error("No hay nodos en el modelo.")
            return
        dlg = FixityDialog(self, model=self._model)
        dlg.exec()
        if dlg.was_applied:
            self._refresh_all()
            self._console.log_success("Restricciones aplicadas.")

    def _on_define_material(self) -> None:
        """Abre el diálogo para crear un nuevo material."""
        dlg = MaterialDialog(
            self,
            next_tag=self._model.next_material_tag(),
        )
        if dlg.exec():
            mat = dlg.get_material()
            self._model.materials[mat.tag] = mat
            self._refresh_all()
            self._console.log_success(
                f"Material creado: {mat.tag} — {mat.name} [{mat.mat_type.value}]"
            )

    def _on_define_section(self) -> None:
        """Abre el diálogo para crear una nueva sección."""
        dlg = SectionDialog(
            self,
            next_tag=self._model.next_section_tag(),
            model=self._model,
        )
        if dlg.exec():
            sec = dlg.get_section()
            self._model.sections[sec.tag] = sec
            self._refresh_all()
            self._console.log_success(
                f"Sección creada: {sec.tag} — {sec.name} [{sec.sec_type.value}]"
            )

    def _on_define_transf(self) -> None:
        """Abre el diálogo para crear una nueva transformación."""
        dlg = TransfDialog(
            self,
            next_tag=self._model.next_transf_tag(),
        )
        if dlg.exec():
            transf = dlg.get_transf()
            self._model.geom_transfs[transf.tag] = transf
            self._refresh_all()
            self._console.log_success(
                f"Transformación creada: {transf.tag} — {transf.transf_type.value}"
            )

    def _on_define_pattern(self) -> None:
        """Abre el diálogo para crear un patrón de carga."""
        dlg = LoadPatternDialog(
            self,
            next_tag=self._model.next_pattern_tag(),
        )
        if dlg.exec():
            pat = dlg.get_pattern()
            self._model.load_patterns[pat.tag] = pat
            self._refresh_all()
            self._console.log_success(
                f"Patrón de carga creado: {pat.tag} — {pat.name}"
            )

    def _on_export_script(self) -> None:
        """Abre el diálogo de previsualización del script."""
        dlg = ScriptPreviewDialog(self, model=self._model)
        dlg.exec()

    def _on_open_analysis(self) -> None:
        """Abre el diálogo de análisis."""
        if not self._model.nodes:
            self._console.log_error("El modelo está vacío.")
            return
        dlg = AnalysisDialog(self, model=self._model)
        dlg.analysis_complete.connect(self._on_analysis_result)
        dlg.exec()

    def _on_analysis_result(self, result: AnalysisResult) -> None:
        """Callback cuando hay resultados de análisis."""
        self._analysis_result = result
        self._act_show_deformed.setEnabled(True)
        self._act_show_deformed.setChecked(True)

        if result.analysis_type == "static":
            n_disp = len(result.node_displacements)
            self._console.log_success(
                f"Análisis estático completado: {n_disp} nodos con desplazamientos."
            )
        elif result.analysis_type == "modal":
            self._console.log_success(
                f"Análisis modal completado: {result.n_modes} modos."
            )
            if result.periods:
                T1 = result.periods[0]
                self._console.log(f"  Período fundamental T₁ = {T1:.4f} s")

    def _on_toggle_deformed(self, checked: bool) -> None:
        """Toggle de visualización de deformada."""
        if checked and self._analysis_result:
            self._viewport.display_model(self._model)
            self._viewport.display_deformed(self._model, self._analysis_result)
            self._console.log("Deformada mostrada (escala 50x).")
        else:
            self._viewport.clear_deformed()
            self._viewport.display_model(self._model)
            self._console.log("Deformada ocultada.")

    def _on_assign_nodal_loads(self) -> None:
        """Abre el diálogo para asignar cargas nodales."""
        if not self._model.load_patterns:
            self._console.log_error(
                "Primero debe crear un patrón de carga (Definir → Patrones de carga...)."
            )
            return
        if not self._model.nodes:
            self._console.log_error("No hay nodos en el modelo.")
            return
        dlg = NodalLoadDialog(self, model=self._model)
        dlg.exec()
        if dlg.was_applied:
            self._refresh_all()
            self._console.log_success("Cargas nodales asignadas.")

    def _update_title(self) -> None:
        """Actualiza el título de la ventana con el nombre del archivo."""
        base = "OPynSees2000 — OpenSeesPy GUI"
        if self._current_file:
            base = f"{self._current_file.stem} — {base}"
        self.setWindowTitle(base)

    def _refresh_all(self) -> None:
        """Refresca tree, viewport y statusbar."""
        self._tree.refresh(self._model)
        self._viewport.display_model(self._model)
        if self._interaction_mode == InteractionMode.SELECT:
            self._viewport.enable_picking(self._model)
        self._update_statusbar()

    def _refresh_viewport(self) -> None:
        self._viewport.display_model(self._model)
        self._console.log("Viewport refrescado.")

    def _on_toggle_labels(self, checked: bool) -> None:
        """Toggle de etiquetas de nodos/elementos."""
        self._viewport.toggle_labels(checked)
        self._viewport.display_model(self._model)
        state = "activadas" if checked else "desactivadas"
        self._console.log(f"Etiquetas {state}.")

    def _on_toggle_loads(self, checked: bool) -> None:
        """Toggle de visualización de cargas."""
        self._viewport.toggle_loads(checked)
        self._viewport.display_model(self._model)
        state = "activadas" if checked else "desactivadas"
        self._console.log(f"Flechas de carga {state}.")

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

    def _on_viewport_pick(self, category: str, tag: int) -> None:
        """Maneja la selección de un objeto en el viewport."""
        self._properties.show_item(self._model, category, tag)
        self._console.log(f"Seleccionado: {category} → tag {tag}")

    def _on_undo(self) -> None:
        desc = self._undo_mgr.undo()
        if desc:
            self._refresh_all()
            self._console.log(f"↩ Deshacer: {desc}")

    def _on_redo(self) -> None:
        desc = self._undo_mgr.redo()
        if desc:
            self._refresh_all()
            self._console.log(f"↪ Rehacer: {desc}")

    def _update_undo_actions(self) -> None:
        self._act_undo.setEnabled(self._undo_mgr.can_undo())
        self._act_redo.setEnabled(self._undo_mgr.can_redo())
        if self._undo_mgr.can_undo():
            self._act_undo.setToolTip(
                f"Deshacer: {self._undo_mgr.undo_description()}"
            )
        if self._undo_mgr.can_redo():
            self._act_redo.setToolTip(
                f"Rehacer: {self._undo_mgr.redo_description()}"
            )

    def _on_property_changed(self, category: str, tag: int) -> None:
        """Llamado cuando el properties panel edita una propiedad."""
        self._refresh_all()

    def _on_delete_selected(self) -> None:
        """Elimina el ítem seleccionado en el árbol."""
        current = self._tree.currentItem()
        if current is None:
            return
        category = current.data(0, 100)
        tag = current.data(0, 101)
        if category is None or tag is None:
            return

        # Prevenir eliminación del patrón DEAD
        if category == "load_patterns" and tag == 1:
            self._console.log_error(
                "El patrón DEAD (tag=1) es obligatorio y no puede eliminarse."
            )
            return

        mapping = {
            "nodes": self._model.nodes,
            "materials": self._model.materials,
            "sections": self._model.sections,
            "geom_transfs": self._model.geom_transfs,
            "elements": self._model.elements,
            "load_patterns": self._model.load_patterns,
        }
        container = mapping.get(category)
        if container is None or tag not in container:
            return

        container.pop(tag)
        self._refresh_all()
        self._console.log(f"Eliminado: {category} → tag {tag}")

    # ------------------------------------------------------------------
    # Override close
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._viewport.close()
        super().closeEvent(event)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Intercepta eventos del viewport VTK para capturar teclas globales."""
        if event.type() == QEvent.Type.KeyPress:
            self.keyPressEvent(event)
            if event.isAccepted():
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:
        """Maneja atajos de teclado globales."""
        if event.key() == Qt.Key.Key_Escape:
            if self._interaction_mode == InteractionMode.DRAW_FRAME and self._frame_first_node is not None:
                # Cancelar frame en progreso, volver al primer clic
                self._frame_first_node = None
                self._frame_first_coords = None
                self._viewport.clear_all_previews()
                self._console.log("Frame cancelado \u2014 esperando primer nodo.")
                return
            if self._interaction_mode != InteractionMode.SELECT:
                self.set_mode(InteractionMode.SELECT)
                return
        elif event.key() == Qt.Key.Key_R:
            if self._interaction_mode == InteractionMode.DRAW_NODE:
                self._reset_offset()
                self._console.log("Offset reseteado a (0, 0, 0)")
                return
        super().keyPressEvent(event)
