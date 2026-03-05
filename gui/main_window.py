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

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
)

from gui.core.model_data import StructuralModel
from gui.dialogs.about_dialog import AboutDialog
from gui.panels.console_panel import ConsolePanel
from gui.panels.model_tree import ModelTree
from gui.panels.properties_panel import PropertiesPanel
from gui.viewport.vtk_widget import VTKViewport


THEME_PATH = Path(__file__).parent / "theme" / "light.qss"


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("OPynSees2000 — OpenSeesPy GUI")
        self.resize(1400, 900)

        # Modelo de datos
        self._model = StructuralModel.create_demo()

        # Widgets
        self._tree = ModelTree()
        self._viewport = VTKViewport()
        self._properties = PropertiesPanel()
        self._console = ConsolePanel()

        # Construcción de la interfaz
        self._build_menubar()
        self._build_toolbar()
        self._build_layout()
        self._build_statusbar()

        # Conexiones
        self._tree.item_selected.connect(self._on_tree_item_selected)

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

        act_demo = QAction("Cargar demo", self)
        act_demo.triggered.connect(self._on_load_demo)
        m_file.addAction(act_demo)

        m_file.addSeparator()

        act_exit = QAction("Salir", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        m_file.addAction(act_exit)

        # --- Definir ---
        m_define = mb.addMenu("&Definir")

        act_mat = QAction("Materiales...", self)
        act_mat.setToolTip("Definir materiales uniaxiales")
        act_mat.setEnabled(False)  # placeholder
        m_define.addAction(act_mat)

        act_sec = QAction("Secciones...", self)
        act_sec.setEnabled(False)
        m_define.addAction(act_sec)

        act_transf = QAction("Transformaciones...", self)
        act_transf.setEnabled(False)
        m_define.addAction(act_transf)

        act_pattern = QAction("Patrones de carga...", self)
        act_pattern.setEnabled(False)
        m_define.addAction(act_pattern)

        # --- Dibujar ---
        m_draw = mb.addMenu("Di&bujar")

        act_node = QAction("Nodo...", self)
        act_node.setEnabled(False)
        m_draw.addAction(act_node)

        act_elem = QAction("Elemento...", self)
        act_elem.setEnabled(False)
        m_draw.addAction(act_elem)

        # --- Asignar ---
        m_assign = mb.addMenu("&Asignar")

        act_fix = QAction("Restricciones...", self)
        act_fix.setEnabled(False)
        m_assign.addAction(act_fix)

        act_load = QAction("Cargas nodales...", self)
        act_load.setEnabled(False)
        m_assign.addAction(act_load)

        act_mass = QAction("Masas...", self)
        act_mass.setEnabled(False)
        m_assign.addAction(act_mass)

        # --- Analizar ---
        m_analyze = mb.addMenu("A&nalizar")

        act_static = QAction("Análisis estático...", self)
        act_static.setEnabled(False)
        m_analyze.addAction(act_static)

        act_modal = QAction("Análisis modal...", self)
        act_modal.setEnabled(False)
        m_analyze.addAction(act_modal)

        act_run = QAction("Ejecutar análisis", self)
        act_run.setShortcut(QKeySequence("F5"))
        act_run.setEnabled(False)
        m_analyze.addAction(act_run)

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

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._update_statusbar()

    def _update_statusbar(self) -> None:
        n = len(self._model.nodes)
        e = len(self._model.elements)
        m = len(self._model.materials)
        s = len(self._model.sections)
        self.statusBar().showMessage(
            f"Nodos: {n}  |  Elementos: {e}  |  Materiales: {m}  |  "
            f"Secciones: {s}  |  Unidades: kN, m, C"
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_new_model(self) -> None:
        self._model.clear()
        self._refresh_all()
        self._console.log("Modelo limpiado.")

    def _on_load_demo(self) -> None:
        self._model = StructuralModel.create_demo()
        self._refresh_all()
        self._console.log_success(
            f"Demo cargado: {len(self._model.nodes)} nodos, "
            f"{len(self._model.elements)} elementos"
        )

    def _on_tree_item_selected(self, category: str, tag: int) -> None:
        self._properties.show_item(self._model, category, tag)

    def _on_about(self) -> None:
        dlg = AboutDialog(self)
        dlg.exec()

    def _refresh_all(self) -> None:
        """Refresca tree, viewport y statusbar."""
        self._tree.refresh(self._model)
        self._viewport.display_model(self._model)
        self._update_statusbar()

    def _refresh_viewport(self) -> None:
        self._viewport.display_model(self._model)
        self._console.log("Viewport refrescado.")

    # ------------------------------------------------------------------
    # Override close
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._viewport.close()
        super().closeEvent(event)
