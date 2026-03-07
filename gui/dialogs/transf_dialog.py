"""
Diálogo para crear / editar transformaciones geométricas.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from gui.core.model_data import GeomTransf, TransfType


# Presets de vectores vecxz comunes
VECXZ_PRESETS: dict[str, tuple[float, float, float]] = {
    "Columnas (vertical Z)": (0.0, 0.0, 1.0),
    "Vigas en X": (0.0, 0.0, 1.0),
    "Vigas en Y": (0.0, 0.0, 1.0),
    "Columnas (plano XZ)": (1.0, 0.0, 0.0),
    "Personalizado": (0.0, 0.0, 1.0),
}


class TransfDialog(QDialog):
    """Diálogo modal para crear o editar una transformación geométrica."""

    def __init__(
        self,
        parent=None,
        transf: Optional[GeomTransf] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Editar transformación" if transf else "Nueva transformación"
        )
        self.setMinimumWidth(400)

        self._editing = transf

        layout = QVBoxLayout(self)

        # --- Información básica ---
        grp_info = QGroupBox("Información")
        form_info = QFormLayout()
        grp_info.setLayout(form_info)

        self._tag_edit = QLineEdit(str(transf.tag if transf else next_tag))
        self._tag_edit.setReadOnly(True)
        form_info.addRow("Tag:", self._tag_edit)

        self._type_combo = QComboBox()
        for tt in TransfType:
            self._type_combo.addItem(tt.value, tt)
        if transf:
            idx = self._type_combo.findData(transf.transf_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
        form_info.addRow("Tipo:", self._type_combo)

        layout.addWidget(grp_info)

        # --- Vector vecxz ---
        grp_vec = QGroupBox("Vector de orientación (vecxz)")
        vec_layout = QVBoxLayout()
        grp_vec.setLayout(vec_layout)

        # Preset selector
        self._preset_combo = QComboBox()
        for preset_name in VECXZ_PRESETS:
            self._preset_combo.addItem(preset_name)
        self._preset_combo.setCurrentIndex(len(VECXZ_PRESETS) - 1)  # "Personalizado"
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        vec_layout.addWidget(self._preset_combo)

        # Spinboxes para X, Y, Z
        vec_form = QFormLayout()

        default_vec = transf.vecxz if transf else (0.0, 0.0, 1.0)

        self._vec_x = QDoubleSpinBox()
        self._vec_x.setDecimals(4)
        self._vec_x.setRange(-100.0, 100.0)
        self._vec_x.setValue(default_vec[0])
        vec_form.addRow("X:", self._vec_x)

        self._vec_y = QDoubleSpinBox()
        self._vec_y.setDecimals(4)
        self._vec_y.setRange(-100.0, 100.0)
        self._vec_y.setValue(default_vec[1])
        vec_form.addRow("Y:", self._vec_y)

        self._vec_z = QDoubleSpinBox()
        self._vec_z.setDecimals(4)
        self._vec_z.setRange(-100.0, 100.0)
        self._vec_z.setValue(default_vec[2])
        vec_form.addRow("Z:", self._vec_z)

        vec_layout.addLayout(vec_form)

        # Nota explicativa
        note = QLabel(
            "El vector vecxz define el plano local xz del elemento.\n"
            "Para columnas, normalmente (0, 0, 1) o (1, 0, 0).\n"
            "Para vigas horizontales, normalmente (0, 0, 1)."
        )
        note.setStyleSheet("color: #757575; font-size: 11px; padding: 4px;")
        vec_layout.addWidget(note)

        layout.addWidget(grp_vec)

        # --- Botones ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---------------------------------------------------------------

    def _on_preset_changed(self, text: str) -> None:
        """Aplica un preset de vector vecxz."""
        vec = VECXZ_PRESETS.get(text)
        if vec and text != "Personalizado":
            self._vec_x.setValue(vec[0])
            self._vec_y.setValue(vec[1])
            self._vec_z.setValue(vec[2])

    def get_transf(self) -> GeomTransf:
        """Retorna la transformación configurada."""
        tag = int(self._tag_edit.text())
        transf_type: TransfType = self._type_combo.currentData()
        vecxz = (self._vec_x.value(), self._vec_y.value(), self._vec_z.value())
        return GeomTransf(tag=tag, transf_type=transf_type, vecxz=vecxz)
