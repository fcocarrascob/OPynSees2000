"""
Diálogo de previsualización del script OpenSeesPy generado.

Muestra el código en un editor de texto de solo lectura con
opción de copiar al portapapeles o exportar a archivo .py.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from gui.core.model_data import StructuralModel
from gui.core.script_generator import generate_script


class ScriptPreviewDialog(QDialog):
    """Diálogo para previsualizar y exportar el script OpenSeesPy."""

    def __init__(
        self,
        parent=None,
        model: StructuralModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Script OpenSeesPy — Previsualización")
        self.setMinimumSize(700, 550)

        self._model = model or StructuralModel()

        layout = QVBoxLayout(self)

        # Opciones
        self._chk_analysis = QCheckBox("Incluir análisis estático básico")
        self._chk_analysis.setChecked(False)
        self._chk_analysis.stateChanged.connect(self._regenerate)
        layout.addWidget(self._chk_analysis)

        # Editor de texto (solo lectura)
        self._editor = QPlainTextEdit()
        self._editor.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(font)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._editor)

        # Info de líneas
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #757575; padding: 2px;")
        layout.addWidget(self._info_label)

        # Botones
        btn_layout = QHBoxLayout()

        btn_copy = QPushButton("Copiar al portapapeles")
        btn_copy.clicked.connect(self._on_copy)
        btn_layout.addWidget(btn_copy)

        btn_export = QPushButton("Exportar a .py")
        btn_export.clicked.connect(self._on_export)
        btn_layout.addWidget(btn_export)

        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("flat", "true")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        # Generar script inicial
        self._regenerate()

    def _regenerate(self) -> None:
        """Regenera el script y actualiza el editor."""
        include = self._chk_analysis.isChecked()
        self._script = generate_script(self._model, include_analysis=include)
        self._editor.setPlainText(self._script)
        n_lines = self._script.count("\n") + 1
        self._info_label.setText(f"{n_lines} líneas generadas")

    def _on_copy(self) -> None:
        """Copia el script al portapapeles."""
        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self._script)
        self._info_label.setText("✔ Copiado al portapapeles")
        self._info_label.setStyleSheet("color: #388E3C; padding: 2px;")

    def _on_export(self) -> None:
        """Exporta el script a un archivo .py."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar script OpenSeesPy",
            "",
            "Python (*.py);;Todos los archivos (*.*)",
        )
        if not path:
            return
        Path(path).write_text(self._script, encoding="utf-8")
        self._info_label.setText(f"✔ Exportado: {Path(path).name}")
        self._info_label.setStyleSheet("color: #388E3C; padding: 2px;")

    def get_script(self) -> str:
        """Retorna el script generado actual."""
        return self._script
