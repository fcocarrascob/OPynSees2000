"""
Diálogo «Acerca de» —  placeholder.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout


class AboutDialog(QDialog):
    """Ventana 'Acerca de OPynSees2000'."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Acerca de OPynSees2000")
        self.setFixedSize(380, 220)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("OPynSees2000")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1976D2;")
        layout.addWidget(title)

        desc = QLabel(
            "Interfaz gráfica para OpenSeesPy\n"
            "Generación interactiva de modelos estructurales\n\n"
            "Basado en PySide6 + PyVista/VTK"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #616161;")
        layout.addWidget(desc)

        version = QLabel("v0.1.0-dev")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        layout.addWidget(version)

        btn = QPushButton("Cerrar")
        btn.setFixedWidth(100)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
