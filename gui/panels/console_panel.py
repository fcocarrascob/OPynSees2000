"""
Panel de consola de salida / preview de script.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QPlainTextEdit


class ConsolePanel(QPlainTextEdit):
    """Consola de salida en la parte inferior de la ventana."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)  # límite de líneas
        self.setMinimumHeight(100)
        self.setPlaceholderText("Consola de salida...")

        # Mensaje inicial
        self.log("OPynSees2000 — Interfaz gráfica para OpenSeesPy")
        self.log("Listo.")

    def log(self, message: str) -> None:
        """Agrega un mensaje con timestamp."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.appendPlainText(f"[{ts}] {message}")

    def log_separator(self) -> None:
        self.appendPlainText("─" * 60)

    def log_error(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.appendPlainText(f"[{ts}] ❌ ERROR: {message}")

    def log_success(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.appendPlainText(f"[{ts}] ✔ {message}")
