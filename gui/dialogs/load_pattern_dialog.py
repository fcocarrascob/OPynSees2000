"""
Diálogo para crear / editar patrones de carga.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QVBoxLayout,
)

from gui.core.model_data import LoadPattern

# Tipos de TimeSeries disponibles
TIME_SERIES_TYPES = ["Constant", "Linear", "Path"]


class LoadPatternDialog(QDialog):
    """Diálogo modal para crear o editar un patrón de carga."""

    def __init__(
        self,
        parent=None,
        pattern: Optional[LoadPattern] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar patrón" if pattern else "Nuevo patrón de carga")
        self.setMinimumWidth(380)

        self._editing = pattern

        layout = QVBoxLayout(self)

        grp = QGroupBox("Patrón de carga")
        form = QFormLayout()
        grp.setLayout(form)

        self._tag_edit = QLineEdit(str(pattern.tag if pattern else next_tag))
        self._tag_edit.setReadOnly(True)
        form.addRow("Tag:", self._tag_edit)

        self._name_edit = QLineEdit(pattern.name if pattern else "")
        self._name_edit.setPlaceholderText("Ej: Carga muerta, Carga viva, Sismo X")
        form.addRow("Nombre:", self._name_edit)

        self._ts_combo = QComboBox()
        for ts in TIME_SERIES_TYPES:
            self._ts_combo.addItem(ts)
        if pattern:
            idx = self._ts_combo.findText(pattern.time_series_type)
            if idx >= 0:
                self._ts_combo.setCurrentIndex(idx)
        form.addRow("Time Series:", self._ts_combo)

        layout.addWidget(grp)

        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self.accept()

    def get_pattern(self) -> LoadPattern:
        """Retorna el patrón configurado."""
        tag = int(self._tag_edit.text())
        return LoadPattern(
            tag=tag,
            name=self._name_edit.text().strip(),
            time_series_type=self._ts_combo.currentText(),
            loads=self._editing.loads if self._editing else [],
        )
