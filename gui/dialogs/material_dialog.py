"""
Diálogo para crear / editar materiales uniaxiales.

Campos dinámicos que cambian según el tipo de material seleccionado.
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
    QLineEdit,
    QVBoxLayout,
)

from gui.core.model_data import Material, MaterialType


# ---------------------------------------------------------------------------
# Esquema de parámetros por tipo de material
# Cada entrada: (clave_param, etiqueta_ui, valor_por_defecto)
# ---------------------------------------------------------------------------

MATERIAL_PARAMS: dict[MaterialType, list[tuple[str, str, float]]] = {
    MaterialType.ELASTIC: [
        ("E", "Módulo de elasticidad E [kN/m²]", 200_000_000.0),
    ],
    MaterialType.STEEL02: [
        ("Fy", "Esfuerzo de fluencia Fy [kN/m²]", 420_000.0),
        ("E0", "Módulo elástico E0 [kN/m²]", 200_000_000.0),
        ("b", "Razón de endurecimiento b", 0.01),
        ("R0", "Parámetro R0", 18.0),
        ("cR1", "Parámetro cR1", 0.925),
        ("cR2", "Parámetro cR2", 0.15),
    ],
    MaterialType.CONCRETE01: [
        ("fpc", "Resistencia pico f'c [kN/m²]", -28_000.0),
        ("epsc0", "Deformación en f'c", -0.002),
        ("fpcu", "Resistencia residual [kN/m²]", -5_600.0),
        ("epsU", "Deformación última", -0.005),
    ],
    MaterialType.CONCRETE02: [
        ("fpc", "Resistencia pico f'c [kN/m²]", -28_000.0),
        ("epsc0", "Deformación en f'c", -0.002),
        ("fpcu", "Resistencia residual [kN/m²]", -5_600.0),
        ("epsU", "Deformación última", -0.005),
        ("lam", "Factor de rigidez de descarga λ", 0.1),
        ("ft", "Resistencia a tracción ft [kN/m²]", 2_800.0),
        ("Ets", "Módulo de softening Ets [kN/m²]", 1_400_000.0),
    ],
    MaterialType.ELASTIC_PP: [
        ("E", "Módulo de elasticidad E [kN/m²]", 200_000_000.0),
        ("epsyP", "Deformación de fluencia (+)", 0.002),
    ],
    MaterialType.HYSTERETIC: [
        ("s1p", "Esfuerzo punto 1 (+) [kN/m²]", 420_000.0),
        ("e1p", "Deformación punto 1 (+)", 0.002),
        ("s2p", "Esfuerzo punto 2 (+) [kN/m²]", 500_000.0),
        ("e2p", "Deformación punto 2 (+)", 0.01),
        ("s3p", "Esfuerzo punto 3 (+) [kN/m²]", 420_000.0),
        ("e3p", "Deformación punto 3 (+)", 0.05),
        ("s1n", "Esfuerzo punto 1 (−) [kN/m²]", -420_000.0),
        ("e1n", "Deformación punto 1 (−)", -0.002),
        ("s2n", "Esfuerzo punto 2 (−) [kN/m²]", -500_000.0),
        ("e2n", "Deformación punto 2 (−)", -0.01),
        ("s3n", "Esfuerzo punto 3 (−) [kN/m²]", -420_000.0),
        ("e3n", "Deformación punto 3 (−)", -0.05),
        ("pinchX", "Factor pinchX", 0.8),
        ("pinchY", "Factor pinchY", 0.2),
        ("damage1", "Daño 1", 0.0),
        ("damage2", "Daño 2", 0.0),
        ("beta", "Beta (degradación rigidez)", 0.0),
    ],
}


class MaterialDialog(QDialog):
    """Diálogo modal para crear o editar un material uniaxial."""

    def __init__(
        self,
        parent=None,
        material: Optional[Material] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar material" if material else "Nuevo material")
        self.setMinimumWidth(440)

        self._editing = material
        self._param_widgets: dict[str, QDoubleSpinBox] = {}

        layout = QVBoxLayout(self)

        # --- Información básica ---
        grp_info = QGroupBox("Información")
        form_info = QFormLayout()
        grp_info.setLayout(form_info)

        self._tag_edit = QLineEdit(str(material.tag if material else next_tag))
        self._tag_edit.setReadOnly(True)
        form_info.addRow("Tag:", self._tag_edit)

        self._name_edit = QLineEdit(material.name if material else "")
        self._name_edit.setPlaceholderText("Ej: Acero A36, Concreto f'c=28 MPa")
        form_info.addRow("Nombre:", self._name_edit)

        self._type_combo = QComboBox()
        for mt in MaterialType:
            self._type_combo.addItem(mt.value, mt)
        if material:
            idx = self._type_combo.findData(material.mat_type)
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
    # Parámetros dinámicos
    # ---------------------------------------------------------------

    def _rebuild_params(self) -> None:
        """Reconstruye los campos de parámetros según el tipo seleccionado."""
        # Limpiar layout anterior
        while self._params_layout.count():
            child = self._params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._param_widgets.clear()

        mat_type: MaterialType = self._type_combo.currentData()
        schema = MATERIAL_PARAMS.get(mat_type, [])

        for key, label, default in schema:
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e15, 1e15)
            # Si estamos editando y el param existe, usar su valor
            if (
                self._editing
                and self._editing.mat_type == mat_type
                and key in self._editing.params
            ):
                spin.setValue(self._editing.params[key])
            else:
                spin.setValue(default)
            self._param_widgets[key] = spin
            self._params_layout.addRow(label, spin)

    # ---------------------------------------------------------------
    # Aceptar
    # ---------------------------------------------------------------

    def _on_accept(self) -> None:
        """Valida y acepta el diálogo."""
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            self._name_edit.setStyleSheet("border: 1px solid #D32F2F;")
            return
        self._name_edit.setStyleSheet("")
        self.accept()

    # ---------------------------------------------------------------
    # Resultado
    # ---------------------------------------------------------------

    def get_material(self) -> Material:
        """Retorna el material configurado con los valores del diálogo."""
        tag = int(self._tag_edit.text())
        name = self._name_edit.text().strip()
        mat_type: MaterialType = self._type_combo.currentData()
        params = {k: w.value() for k, w in self._param_widgets.items()}
        return Material(tag=tag, name=name, mat_type=mat_type, params=params)
