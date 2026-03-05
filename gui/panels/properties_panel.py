"""
Panel de propiedades del ítem seleccionado.

Muestra los atributos del nodo, material, sección o elemento
seleccionado en el Model Tree, en modo solo-lectura (por ahora).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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


class PropertiesPanel(QWidget):
    """Panel lateral derecho con propiedades del ítem seleccionado."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setMaximumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        layout.addWidget(scroll)

        # Contenedor interior
        self._container = QWidget()
        self._form_layout = QVBoxLayout(self._container)
        self._form_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._container)

        # Placeholder
        self._placeholder = QLabel("Seleccione un ítem\nen el árbol de modelo")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #9E9E9E; padding: 24px;")
        self._form_layout.addWidget(self._placeholder)

    def show_item(self, model: StructuralModel, category: str, tag: int) -> None:
        """Muestra las propiedades de un ítem específico."""
        self._clear()

        item = None
        title = ""

        if category == "nodes":
            item = model.nodes.get(tag)
            title = f"Nodo {tag}"
        elif category == "materials":
            item = model.materials.get(tag)
            title = f"Material {tag}"
        elif category == "sections":
            item = model.sections.get(tag)
            title = f"Sección {tag}"
        elif category == "geom_transfs":
            item = model.geom_transfs.get(tag)
            title = f"Transformación {tag}"
        elif category == "elements":
            item = model.elements.get(tag)
            title = f"Elemento {tag}"
        elif category == "load_patterns":
            item = model.load_patterns.get(tag)
            title = f"Patrón de Carga {tag}"

        if item is None:
            return

        group = QGroupBox(title)
        form = QFormLayout()
        group.setLayout(form)

        # Agregar campos desde los atributos del dataclass
        for field_name, value in vars(item).items():
            if field_name.startswith("_"):
                continue

            display_value = self._format_value(value)
            line = QLineEdit(display_value)
            line.setReadOnly(True)
            form.addRow(self._human_label(field_name), line)

        # Si tiene params dict, expandir
        if hasattr(item, "params") and isinstance(item.params, dict):
            for key, val in item.params.items():
                line = QLineEdit(self._format_value(val))
                line.setReadOnly(True)
                form.addRow(f"  {key}:", line)

        self._form_layout.addWidget(group)

    def clear_selection(self) -> None:
        """Restaura el placeholder."""
        self._clear()
        self._placeholder = QLabel("Seleccione un ítem\nen el árbol de modelo")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #9E9E9E; padding: 24px;")
        self._form_layout.addWidget(self._placeholder)

    def _clear(self) -> None:
        """Limpia todos los widgets del panel."""
        while self._form_layout.count():
            child = self._form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    @staticmethod
    def _format_value(value) -> str:
        if isinstance(value, float):
            if abs(value) >= 1_000:
                return f"{value:,.2f}"
            return f"{value:.6g}"
        if isinstance(value, (tuple, list)):
            return ", ".join(str(v) for v in value)
        if hasattr(value, "value"):  # Enum
            return str(value.value)
        return str(value)

    @staticmethod
    def _human_label(field_name: str) -> str:
        """Convierte snake_case a label legible."""
        labels = {
            "tag": "Tag:",
            "x": "X:",
            "y": "Y:",
            "z": "Z:",
            "fixity": "Fijación:",
            "mass": "Masa:",
            "name": "Nombre:",
            "mat_type": "Tipo:",
            "sec_type": "Tipo:",
            "elem_type": "Tipo:",
            "node_i": "Nodo i:",
            "node_j": "Nodo j:",
            "section_tag": "Sección:",
            "transf_tag": "Transf.:",
            "transf_type": "Tipo:",
            "vecxz": "Vec XZ:",
            "params": "Params:",
            "time_series_type": "Serie:",
            "loads": "Cargas:",
        }
        return labels.get(field_name, f"{field_name}:")
