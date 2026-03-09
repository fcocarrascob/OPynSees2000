"""
Panel de propiedades — Inspector editable de objetos del modelo.

Muestra las propiedades del ítem seleccionado en el Model Tree
como campos de formulario editables. Al presionar Enter en un campo,
se genera un UndoCommand y se aplica el cambio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from gui.core.model_data import StructuralModel
    from gui.core.undo_manager import UndoManager

from gui.core.model_data import ElementType, SectionType


# Campos read-only que no se deben editar
READ_ONLY_FIELDS = {
    "tag",
    "elem_type",
    "mat_type",
    "sec_type",
    "transf_type",
    "time_series_type",
}

# Mapeo de nombres de campo a etiquetas legibles (español)
HUMAN_LABELS = {
    "tag": "Tag",
    "x": "Coord. X [m]",
    "y": "Coord. Y [m]",
    "z": "Coord. Z [m]",
    "name": "Nombre",
    "mat_type": "Tipo de material",
    "sec_type": "Tipo de sección",
    "elem_type": "Tipo de elemento",
    "transf_type": "Tipo de transformación",
    "node_i": "Nodo I",
    "node_j": "Nodo J",
    "node_k": "Nodo K",
    "node_l": "Nodo L",
    "section_tag": "Sección (tag)",
    "transf_tag": "Transformación (tag)",
    "fixity": "Restricciones",
    "mass": "Masa nodal",
    "vecxz": "Vector vecxz",
    "fx": "Fx [kN]",
    "fy": "Fy [kN]",
    "fz": "Fz [kN]",
    "mx": "Mx [kN·m]",
    "my": "My [kN·m]",
    "mz": "Mz [kN·m]",
    "time_series_type": "TimeSeries",
    "node_tag": "Nodo (tag)",
    "params": "Parámetros",
    "loads": "Cargas",
    "ndm": "NDM",
    "ndf": "NDF",
    "density": "Densidad [kg/m³]",
    "material_tag": "Material (tag)",
    "self_weight_multiplier": "Mult. peso propio",
}


class PropertiesPanel(QScrollArea):
    """Panel lateral derecho con propiedades editables."""

    # Señal emitida cuando se cambia una propiedad: (category, tag)
    property_changed = Signal(str, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setWidgetResizable(True)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self._container)

        self._current_item: Any = None
        self._current_category: str = ""
        self._current_tag: int = 0
        self._undo_manager: Optional["UndoManager"] = None
        self._field_widgets: dict[str, QWidget] = {}

        # Placeholder
        self._placeholder = QLabel("Seleccione un ítem\nen el Model Tree")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #9E9E9E; padding: 30px;")
        self._layout.addWidget(self._placeholder)

    def set_undo_manager(self, mgr: "UndoManager") -> None:
        """Conecta el UndoManager para operaciones de edición."""
        self._undo_manager = mgr

    def show_item(
        self,
        model: "StructuralModel",
        category: str,
        tag: int,
    ) -> None:
        """Muestra las propiedades del ítem seleccionado."""
        item = self._resolve_item(model, category, tag)
        if item is None:
            return

        self._current_item = item
        self._current_category = category
        self._current_tag = tag
        self._field_widgets.clear()

        # Limpiar layout
        self._clear_layout()

        # Título
        title = QLabel(f"{category.capitalize()} — Tag {tag}")
        title.setStyleSheet(
            "font-weight: bold; font-size: 13px; padding: 6px 0;"
        )
        self._layout.addWidget(title)

        # Campos
        grp = QGroupBox("Propiedades")
        form = QFormLayout()
        grp.setLayout(form)

        for field_name, value in vars(item).items():
            if field_name.startswith("_"):
                continue

            label = HUMAN_LABELS.get(field_name, field_name)
            is_readonly = field_name in READ_ONLY_FIELDS

            widget = self._create_field_widget(
                item, field_name, value, is_readonly
            )
            self._field_widgets[field_name] = widget
            form.addRow(label + ":", widget)

        # Mostrar params como sub-campos si es dict
        if hasattr(item, "params") and isinstance(item.params, dict):
            grp_params = QGroupBox("Parámetros detallados")
            params_form = QFormLayout()
            grp_params.setLayout(params_form)
            for key, val in item.params.items():
                w = self._create_param_widget(item, key, val)
                params_form.addRow(f"{key}:", w)
            self._layout.addWidget(grp_params)

        self._layout.addWidget(grp)
        self._layout.addStretch()

    def clear(self) -> None:
        """Limpia el panel y muestra el placeholder."""
        self._current_item = None
        self._current_category = ""
        self._current_tag = 0
        self._field_widgets.clear()
        self._clear_layout()
        self._placeholder = QLabel("Seleccione un ítem\nen el Model Tree")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #9E9E9E; padding: 30px;")
        self._layout.addWidget(self._placeholder)

    def show_drawing_template(
        self,
        model: "StructuralModel",
        mode: str,
    ) -> None:
        """Muestra propiedades editables para elementos a crear.

        Parameters
        ----------
        model : StructuralModel
            Modelo actual.
        mode : str
            ``"frame"`` o ``"shell"``.
        """
        template = model.drawing_template

        # Limpiar layout actual
        self._clear_layout()
        self._current_item = None
        self._current_category = ""
        self._current_tag = 0
        self._field_widgets.clear()

        # Título
        if mode == "frame":
            title_text = "Propiedades del Frame a Crear"
        else:
            title_text = "Propiedades del Shell a Crear"
        title = QLabel(title_text)
        title.setStyleSheet(
            "font-weight: bold; font-size: 13px; padding: 6px 0; color: #1976D2;"
        )
        self._layout.addWidget(title)

        # Info box
        info = QLabel("Los elementos dibujados usarán estas propiedades")
        info.setStyleSheet(
            "color: #757575; font-size: 11px; padding: 4px; "
            "background: #E3F2FD; border-radius: 3px;"
        )
        info.setWordWrap(True)
        self._layout.addWidget(info)

        # Formulario
        grp = QGroupBox("Configuración")
        form = QFormLayout()
        grp.setLayout(form)

        if mode == "frame":
            self._build_frame_template_form(form, model, template)
        elif mode == "shell":
            self._build_shell_template_form(form, model, template)

        self._layout.addWidget(grp)

        # Hint para crear secciones si no hay
        if not model.sections:
            hint = QLabel(
                "\u26a0\ufe0f No hay secciones definidas.\n"
                "Crea una en Definir \u2192 Sección"
            )
            hint.setStyleSheet(
                "color: #F57C00; padding: 10px; "
                "background: #FFF3E0; border-radius: 3px;"
            )
            hint.setWordWrap(True)
            self._layout.addWidget(hint)

        # Sección de configuración de snap
        self.show_snap_settings(model, mode)

        self._layout.addStretch()

    def show_snap_settings(
        self,
        model: "StructuralModel",
        mode: str,
        on_setting_changed: "callable | None" = None,
    ) -> None:
        """Muestra la configuración de snap y plano de trabajo.

        Parameters
        ----------
        model : StructuralModel
            Modelo actual (contiene drawing_template).
        mode : str
            ``"frame"``, ``"shell"`` o ``"node"`` — para controlar visibilidad
            del checkbox snap-to-points.
        on_setting_changed : callable | None
            Callback invocado cuando un setting cambia: on_setting_changed(field_name, value).
        """
        template = model.drawing_template

        grp = QGroupBox("Configuración de Snap")
        form = QFormLayout()
        grp.setLayout(form)

        # ── Working Plane Mode ──
        combo_plane = QComboBox()
        plane_options = ["Free 3D", "XY Plane", "XZ Plane", "YZ Plane"]
        plane_values = ["Free", "XY", "XZ", "YZ"]
        for display, value in zip(plane_options, plane_values):
            combo_plane.addItem(display, value)
        current_plane_idx = plane_values.index(template.working_plane_mode) if template.working_plane_mode in plane_values else 0
        combo_plane.setCurrentIndex(current_plane_idx)
        combo_plane.setToolTip(
            "Plano de trabajo activo.\n"
            "XY: bloquea Z | XZ: bloquea Y | YZ: bloquea X\n"
            "Free 3D: sin restricción.\n"
            "Mantener Shift al hacer clic = Free 3D temporal."
        )

        # ── Elevation ──
        spin_elevation = QDoubleSpinBox()
        spin_elevation.setDecimals(2)
        spin_elevation.setRange(-1000.0, 1000.0)
        spin_elevation.setSingleStep(0.1)
        spin_elevation.setValue(template.working_plane_elevation)
        spin_elevation.setSuffix(" m")

        # Label dinámico para elevación
        elevation_label = QLabel(self._elevation_label_text(template.working_plane_mode))

        def _update_elevation_label(idx: int) -> None:
            plane_val = combo_plane.itemData(idx)
            elevation_label.setText(self._elevation_label_text(plane_val))
            # Mostrar/ocultar elevación según modo
            is_free = (plane_val == "Free")
            spin_elevation.setVisible(not is_free)
            elevation_label.setVisible(not is_free)

        # Ocultar elevación si es Free
        is_free = (template.working_plane_mode == "Free")
        spin_elevation.setVisible(not is_free)
        elevation_label.setVisible(not is_free)

        # ── Grid Spacing ──
        spin_spacing = QDoubleSpinBox()
        spin_spacing.setDecimals(2)
        spin_spacing.setRange(0.01, 100.0)
        spin_spacing.setSingleStep(0.1)
        spin_spacing.setValue(template.snap_spacing)
        spin_spacing.setSuffix(" m")
        spin_spacing.setToolTip("Espaciado de la grilla de snap")

        # ── Merge Tolerance ──
        spin_tolerance = QDoubleSpinBox()
        spin_tolerance.setDecimals(3)
        spin_tolerance.setRange(0.001, 10.0)
        spin_tolerance.setSingleStep(0.01)
        spin_tolerance.setValue(template.snap_tolerance)
        spin_tolerance.setSuffix(" m")
        spin_tolerance.setToolTip("Tolerancia para fusionar nodos cercanos")

        # ── Snap to Points ──
        chk_snap_points = QCheckBox("Snap a Puntos")
        chk_snap_points.setChecked(template.snap_to_points_enabled)
        chk_snap_points.setToolTip(
            "Cuando activo, el clic cerca de un nodo existente\n"
            "usa sus coordenadas exactas 3D (ignora plano).\n"
            "Shift+clic = Free 3D temporal."
        )
        # Solo mostrar en modos de dibujo frame/shell
        show_snap_to_points = mode in ("frame", "shell")
        chk_snap_points.setVisible(show_snap_to_points)

        # ── Conectar callbacks ──
        def _on_plane_changed(idx: int) -> None:
            value = combo_plane.itemData(idx)
            template.working_plane_mode = value
            _update_elevation_label(idx)
            if on_setting_changed:
                on_setting_changed("working_plane_mode", value)

        def _on_elevation_changed() -> None:
            template.working_plane_elevation = spin_elevation.value()
            if on_setting_changed:
                on_setting_changed("working_plane_elevation", spin_elevation.value())

        def _on_spacing_changed() -> None:
            template.snap_spacing = spin_spacing.value()
            if on_setting_changed:
                on_setting_changed("snap_spacing", spin_spacing.value())

        def _on_tolerance_changed() -> None:
            template.snap_tolerance = spin_tolerance.value()
            if on_setting_changed:
                on_setting_changed("snap_tolerance", spin_tolerance.value())

        def _on_snap_points_changed(state: int) -> None:
            template.snap_to_points_enabled = bool(state)
            if on_setting_changed:
                on_setting_changed("snap_to_points_enabled", bool(state))

        combo_plane.currentIndexChanged.connect(_on_plane_changed)
        spin_elevation.editingFinished.connect(_on_elevation_changed)
        spin_spacing.editingFinished.connect(_on_spacing_changed)
        spin_tolerance.editingFinished.connect(_on_tolerance_changed)
        chk_snap_points.stateChanged.connect(_on_snap_points_changed)

        # ── Agregar al formulario ──
        form.addRow("Plano de trabajo:", combo_plane)
        form.addRow(elevation_label, spin_elevation)
        form.addRow("Espaciado grilla:", spin_spacing)
        form.addRow("Tolerancia merge:", spin_tolerance)
        if show_snap_to_points:
            form.addRow(chk_snap_points)

        self._layout.addWidget(grp)

    @staticmethod
    def _elevation_label_text(plane_mode: str) -> str:
        """Retorna el texto de etiqueta de elevación según el plano."""
        if plane_mode == "XY":
            return "Elevación Z:"
        elif plane_mode == "XZ":
            return "Elevación Y:"
        elif plane_mode == "YZ":
            return "Elevación X:"
        return "Elevación:"

    # ------------------------------------------------------------------
    # Builders internos para formularios de template
    # ------------------------------------------------------------------

    def _build_frame_template_form(
        self,
        form: QFormLayout,
        model: "StructuralModel",
        template: "DrawingTemplate",
    ) -> None:
        """Construye los campos del formulario para template de frame."""
        from gui.core.model_data import DrawingTemplate  # noqa: F811

        # Dropdown: Tipo de Elemento
        combo_type = QComboBox()
        for elem_type in [
            ElementType.ELASTIC_BEAM_COLUMN,
            ElementType.FORCE_BEAM_COLUMN,
            ElementType.DISP_BEAM_COLUMN,
            ElementType.TRUSS,
            ElementType.COROT_TRUSS,
        ]:
            combo_type.addItem(elem_type.value, elem_type)
        current_idx = combo_type.findData(template.frame_elem_type)
        if current_idx >= 0:
            combo_type.setCurrentIndex(current_idx)
        combo_type.currentIndexChanged.connect(
            lambda _idx, c=combo_type, t=template: self._on_template_type_changed(t, c)
        )
        form.addRow("Tipo de Elemento:", combo_type)

        # Dropdown: Sección (poblado dinámicamente)
        combo_section = QComboBox()
        combo_section.addItem("(Sin asignar)", None)
        for tag, section in model.sections.items():
            display = f"{section.name} [{section.sec_type.value}]"
            combo_section.addItem(display, tag)
        if template.frame_section_tag is not None:
            idx = combo_section.findData(template.frame_section_tag)
            if idx >= 0:
                combo_section.setCurrentIndex(idx)
        combo_section.currentIndexChanged.connect(
            lambda _idx, c=combo_section, t=template: self._on_template_section_changed(t, c)
        )
        form.addRow("Sección:", combo_section)

        # Dropdown: Transformación
        combo_transf = QComboBox()
        combo_transf.addItem("(Sin asignar)", None)
        for tag, transf in model.geom_transfs.items():
            display = f"Tag {tag} [{transf.transf_type.value}]"
            combo_transf.addItem(display, tag)
        if template.frame_transf_tag is not None:
            idx = combo_transf.findData(template.frame_transf_tag)
            if idx >= 0:
                combo_transf.setCurrentIndex(idx)
        combo_transf.currentIndexChanged.connect(
            lambda _idx, c=combo_transf, t=template: self._on_template_transf_changed(t, c)
        )
        form.addRow("Transformación:", combo_transf)

    def _build_shell_template_form(
        self,
        form: QFormLayout,
        model: "StructuralModel",
        template: "DrawingTemplate",
    ) -> None:
        """Construye los campos del formulario para template de shell."""
        from gui.core.model_data import DrawingTemplate  # noqa: F811

        # Dropdown: Sección (solo secciones compatibles con shells)
        combo_section = QComboBox()
        combo_section.addItem("(Sin asignar)", None)
        for tag, section in model.sections.items():
            display = f"{section.name} [{section.sec_type.value}]"
            combo_section.addItem(display, tag)
        if template.shell_section_tag is not None:
            idx = combo_section.findData(template.shell_section_tag)
            if idx >= 0:
                combo_section.setCurrentIndex(idx)
        combo_section.currentIndexChanged.connect(
            lambda _idx, c=combo_section, t=template: self._on_template_shell_section_changed(t, c)
        )
        form.addRow("Sección:", combo_section)

        # Espesor
        spin_thick = QDoubleSpinBox()
        spin_thick.setDecimals(3)
        spin_thick.setRange(0.001, 10.0)
        spin_thick.setValue(template.shell_thickness)
        spin_thick.setSuffix(" m")
        spin_thick.editingFinished.connect(
            lambda s=spin_thick, t=template: self._on_template_thickness_changed(t, s.value())
        )
        form.addRow("Espesor:", spin_thick)

    # ------------------------------------------------------------------
    # Callbacks de template
    # ------------------------------------------------------------------

    @staticmethod
    def _on_template_type_changed(template: "DrawingTemplate", combo: QComboBox) -> None:
        template.frame_elem_type = combo.currentData()

    @staticmethod
    def _on_template_section_changed(template: "DrawingTemplate", combo: QComboBox) -> None:
        template.frame_section_tag = combo.currentData()

    @staticmethod
    def _on_template_transf_changed(template: "DrawingTemplate", combo: QComboBox) -> None:
        template.frame_transf_tag = combo.currentData()

    @staticmethod
    def _on_template_shell_section_changed(template: "DrawingTemplate", combo: QComboBox) -> None:
        template.shell_section_tag = combo.currentData()

    @staticmethod
    def _on_template_thickness_changed(template: "DrawingTemplate", value: float) -> None:
        template.shell_thickness = value

    def _resolve_item(self, model, category, tag):
        """Busca el objeto dentro del modelo."""
        mapping = {
            "nodes": model.nodes,
            "materials": model.materials,
            "sections": model.sections,
            "geom_transfs": model.geom_transfs,
            "elements": model.elements,
            "load_patterns": model.load_patterns,
        }
        container = mapping.get(category)
        if container is None:
            return None
        return container.get(tag)

    def _create_field_widget(
        self, item: Any, field_name: str, value: Any, is_readonly: bool
    ) -> QWidget:
        """Crea el widget adecuado para un campo."""
        if is_readonly or isinstance(value, (tuple, list, dict)):
            # Solo lectura
            lbl = QLineEdit(self._format_value(value))
            lbl.setReadOnly(True)
            lbl.setStyleSheet("background: #F5F5F5; color: #616161;")
            return lbl

        if isinstance(value, float):
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e15, 1e15)
            spin.setValue(value)
            spin.editingFinished.connect(
                lambda fn=field_name, s=spin: self._on_field_edited(
                    item, fn, s.value()
                )
            )
            return spin

        if isinstance(value, int):
            spin = QDoubleSpinBox()
            spin.setDecimals(0)
            spin.setRange(-999_999, 999_999)
            spin.setValue(value)
            spin.editingFinished.connect(
                lambda fn=field_name, s=spin: self._on_field_edited(
                    item, fn, int(s.value())
                )
            )
            return spin

        if isinstance(value, str):
            edit = QLineEdit(value)
            edit.editingFinished.connect(
                lambda fn=field_name, e=edit: self._on_field_edited(
                    item, fn, e.text()
                )
            )
            return edit

        # Fallback read-only
        lbl = QLineEdit(self._format_value(value))
        lbl.setReadOnly(True)
        lbl.setStyleSheet("background: #F5F5F5; color: #616161;")
        return lbl

    def _create_param_widget(
        self, item: Any, key: str, value: Any
    ) -> QWidget:
        """Crea un widget editable para un parámetro del dict params."""
        if isinstance(value, (int, float)):
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e15, 1e15)
            spin.setValue(float(value))
            spin.editingFinished.connect(
                lambda k=key, s=spin: self._on_param_edited(
                    item, k, s.value()
                )
            )
            return spin

        edit = QLineEdit(str(value))
        edit.setReadOnly(True)
        return edit

    def _on_field_edited(self, item: Any, field_name: str, new_value: Any) -> None:
        """Llamado cuando un campo es editado."""
        old_value = getattr(item, field_name, None)
        if old_value == new_value:
            return

        if self._undo_manager:
            from gui.core.undo_manager import PropertyChangeCommand

            desc = f"Editar {field_name} de tag {self._current_tag}"
            cmd = PropertyChangeCommand(item, field_name, old_value, new_value, desc)
            self._undo_manager.execute(cmd)
        else:
            setattr(item, field_name, new_value)

        self.property_changed.emit(self._current_category, self._current_tag)

    def _on_param_edited(self, item: Any, key: str, new_value: float) -> None:
        """Llamado cuando un parámetro del dict params es editado."""
        old_value = item.params.get(key)
        if old_value == new_value:
            return

        if self._undo_manager:
            from gui.core.undo_manager import PropertyChangeCommand

            # Crear un wrapper para editar el dict
            class ParamTarget:
                def __init__(self, params, k):
                    self._params = params
                    self._key = k
                @property
                def value(self):
                    return self._params[self._key]
                @value.setter
                def value(self, v):
                    self._params[self._key] = v

            target = ParamTarget(item.params, key)
            desc = f"Editar param {key} de tag {self._current_tag}"
            cmd = PropertyChangeCommand(target, "value", old_value, new_value, desc)
            self._undo_manager.execute(cmd)
        else:
            item.params[key] = new_value

        self.property_changed.emit(self._current_category, self._current_tag)

    def _clear_layout(self) -> None:
        """Elimina todos los widgets del layout."""
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    @staticmethod
    def _format_value(value: Any) -> str:
        """Formatea un valor para display en campo read-only."""
        if isinstance(value, float):
            if abs(value) > 1e6 or (0 < abs(value) < 1e-3):
                return f"{value:.4e}"
            return f"{value:.4f}"
        if isinstance(value, tuple):
            return "(" + ", ".join(str(v) for v in value) + ")"
        if isinstance(value, list):
            return f"[{len(value)} ítems]"
        if isinstance(value, dict):
            return f"{{{len(value)} params}}"
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)
