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
    QFileDialog,
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

        # Construcción de la interfaz
        self._build_menubar()
        self._build_toolbar()
        self._build_layout()
        self._build_statusbar()

        # Conexiones
        self._tree.item_selected.connect(self._on_tree_item_selected)
        self._tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self._viewport.item_picked.connect(self._on_viewport_pick)

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
        self._current_file = None
        self._update_title()
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
            dlg = SectionDialog(self, section=sec)
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
            self._model = load_project(Path(path))
            self._current_file = Path(path)
            self._refresh_all()
            self._update_title()
            self._console.log_success(f"Proyecto abierto: {path}")
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

    def _on_viewport_pick(self, category: str, tag: int) -> None:
        """Maneja la selección de un objeto en el viewport."""
        self._properties.show_item(self._model, category, tag)
        self._console.log(f"Seleccionado: {category} → tag {tag}")

    # ------------------------------------------------------------------
    # Override close
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._viewport.close()
        super().closeEvent(event)
