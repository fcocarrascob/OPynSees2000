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
