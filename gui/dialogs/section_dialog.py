"""
Diálogo para crear / editar secciones transversales.

Campos dinámicos que cambian según el tipo de sección.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from gui.core.model_data import Section, SectionType


# ---------------------------------------------------------------------------
# Esquema de parámetros por tipo de sección
# ---------------------------------------------------------------------------

SECTION_PARAMS: dict[SectionType, list[tuple[str, str, float]]] = {
    SectionType.ELASTIC_2D: [
        ("A", "Área A [m²]", 0.16),
        ("E", "Módulo E [kN/m²]", 24_821_000.0),
        ("Iz", "Inercia Iz [m⁴]", 2.1333e-3),
    ],
    SectionType.ELASTIC_3D: [
        ("A", "Área A [m²]", 0.16),
        ("E", "Módulo E [kN/m²]", 24_821_000.0),
        ("Iz", "Inercia Iz [m⁴]", 2.1333e-3),
        ("Iy", "Inercia Iy [m⁴]", 2.1333e-3),
        ("G", "Módulo de corte G [kN/m²]", 10_342_000.0),
        ("J", "Constante de torsión J [m⁴]", 3.6053e-3),
    ],
    SectionType.FIBER: [],  # Secciones de fibra requieren manejo especial (futuro)
}


class SectionDialog(QDialog):
    """Diálogo modal para crear o editar una sección transversal."""

    def __init__(
        self,
        parent=None,
        section: Optional[Section] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar sección" if section else "Nueva sección")
        self.setMinimumWidth(440)

        self._editing = section
        self._param_widgets: dict[str, QDoubleSpinBox] = {}

        layout = QVBoxLayout(self)

        # --- Información básica ---
        grp_info = QGroupBox("Información")
        form_info = QFormLayout()
        grp_info.setLayout(form_info)

        self._tag_edit = QLineEdit(str(section.tag if section else next_tag))
        self._tag_edit.setReadOnly(True)
        form_info.addRow("Tag:", self._tag_edit)

        self._name_edit = QLineEdit(section.name if section else "")
        self._name_edit.setPlaceholderText("Ej: Columna 40×40, Viga 30×50")
        form_info.addRow("Nombre:", self._name_edit)

        self._type_combo = QComboBox()
        for st in SectionType:
            self._type_combo.addItem(st.value, st)
        if section:
            idx = self._type_combo.findData(section.sec_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
        self._type_combo.currentIndexChanged.connect(self._rebuild_params)
        form_info.addRow("Tipo:", self._type_combo)

        layout.addWidget(grp_info)

        # --- Parámetros (dinámico) ---
        self._params_group = QGroupBox("Parámetros")
        self._params_layout = QFormLayout()
        self._params_group.setLayout(self._params_layout)
        layout.addWidget(self._params_group)

        # --- Nota para tipo Fiber ---
        self._fiber_label = QLabel(
            "⚠ Las secciones de fibra requieren un editor\n"
            "especializado (disponible en versión futura)."
        )
        self._fiber_label.setStyleSheet("color: #FF8F00; padding: 8px;")
        self._fiber_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fiber_label.setVisible(False)
        layout.addWidget(self._fiber_label)

        # --- Botones ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Construir parámetros iniciales
        self._rebuild_params()

    # ---------------------------------------------------------------

    def _rebuild_params(self) -> None:
        """Reconstruye los campos según el tipo de sección."""
        while self._params_layout.count():
            child = self._params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._param_widgets.clear()

        sec_type: SectionType = self._type_combo.currentData()
        schema = SECTION_PARAMS.get(sec_type, [])

        # Mostrar/ocultar nota de fiber
        self._fiber_label.setVisible(sec_type == SectionType.FIBER)

        for key, label, default in schema:
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e15, 1e15)
            if (
                self._editing
                and self._editing.sec_type == sec_type
                and key in self._editing.params
            ):
                spin.setValue(self._editing.params[key])
            else:
                spin.setValue(default)
            self._param_widgets[key] = spin
            self._params_layout.addRow(label, spin)

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            self._name_edit.setStyleSheet("border: 1px solid #D32F2F;")
            return
        self._name_edit.setStyleSheet("")
        self.accept()

    def get_section(self) -> Section:
        """Retorna la sección configurada."""
        tag = int(self._tag_edit.text())
        name = self._name_edit.text().strip()
        sec_type: SectionType = self._type_combo.currentData()
        params = {k: w.value() for k, w in self._param_widgets.items()}
        return Section(tag=tag, name=name, sec_type=sec_type, params=params)
