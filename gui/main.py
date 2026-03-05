"""
OPynSees2000 — Entry point.

Ejecutar con:
    python -m gui.main
    o
    python gui/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que el paquete raíz esté en sys.path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def load_stylesheet(app: QApplication) -> None:
    """Carga el tema claro desde el archivo .qss."""
    qss_path = Path(__file__).parent / "theme" / "light.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("OPynSees2000")
    app.setOrganizationName("OPynSees2000")

    load_stylesheet(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
