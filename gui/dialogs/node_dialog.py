"""
Diálogo para crear nodos por coordenadas.

Soporta creación individual y en secuencia (botón "Agregar otro").
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from gui.core.model_data import Node


class NodeDialog(QDialog):
    """Diálogo modal para crear un nodo por coordenadas."""

    def __init__(
        self,
        parent=None,
        node: Optional[Node] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar nodo" if node else "Nuevo nodo")
        self.setMinimumWidth(380)

        self._editing = node
        self._created_nodes: list[Node] = []
        self._next_tag = next_tag

        layout = QVBoxLayout(self)

        # --- Coordenadas ---
        grp_coords = QGroupBox("Coordenadas")
        form = QFormLayout()
        grp_coords.setLayout(form)

        self._tag_edit = QLineEdit(str(node.tag if node else next_tag))
        self._tag_edit.setReadOnly(True)
        form.addRow("Tag:", self._tag_edit)

        self._x_spin = QDoubleSpinBox()
        self._x_spin.setDecimals(4)
        self._x_spin.setRange(-1e6, 1e6)
        self._x_spin.setValue(node.x if node else 0.0)
        self._x_spin.setSuffix(" m")
        form.addRow("X:", self._x_spin)

        self._y_spin = QDoubleSpinBox()
        self._y_spin.setDecimals(4)
        self._y_spin.setRange(-1e6, 1e6)
        self._y_spin.setValue(node.y if node else 0.0)
        self._y_spin.setSuffix(" m")
        form.addRow("Y:", self._y_spin)

        self._z_spin = QDoubleSpinBox()
        self._z_spin.setDecimals(4)
        self._z_spin.setRange(-1e6, 1e6)
        self._z_spin.setValue(node.z if node else 0.0)
        self._z_spin.setSuffix(" m")
        form.addRow("Z:", self._z_spin)

        layout.addWidget(grp_coords)

        # --- Info ---
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #388E3C; padding: 4px;")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label)

        # --- Botones ---
        if node:
            # Modo edición: solo OK/Cancel
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
        else:
            # Modo creación: Agregar otro + Cerrar
            btn_layout = QHBoxLayout()

            self._btn_add = QPushButton("Agregar nodo")
            self._btn_add.clicked.connect(self._on_add_node)
            btn_layout.addWidget(self._btn_add)

            self._btn_add_another = QPushButton("Agregar y continuar")
            self._btn_add_another.setProperty("flat", "true")
            self._btn_add_another.clicked.connect(self._on_add_and_continue)
            btn_layout.addWidget(self._btn_add_another)

            self._btn_close = QPushButton("Cerrar")
            self._btn_close.setProperty("flat", "true")
            self._btn_close.clicked.connect(self.reject)
            btn_layout.addWidget(self._btn_close)

            layout.addLayout(btn_layout)

    # ---------------------------------------------------------------

    def _on_add_node(self) -> None:
        """Agrega un nodo y cierra el diálogo."""
        self._store_current_node()
        self.accept()

    def _on_add_and_continue(self) -> None:
        """Agrega un nodo y prepara para el siguiente."""
        self._store_current_node()
        # Incrementar tag
        self._next_tag += 1
        self._tag_edit.setText(str(self._next_tag))
        # Limpiar coordenadas (mantener Z para comodidad)
        self._x_spin.setValue(0.0)
        self._y_spin.setValue(0.0)
        self._x_spin.setFocus()
        self._x_spin.selectAll()
        self._info_label.setText(
            f"✔ Nodo {self._next_tag - 1} agregado. "
            f"Total: {len(self._created_nodes)}"
        )

    def _store_current_node(self) -> None:
        """Almacena el nodo actual en la lista interna."""
        tag = int(self._tag_edit.text())
        node = Node(
            tag=tag,
            x=self._x_spin.value(),
            y=self._y_spin.value(),
            z=self._z_spin.value(),
        )
        self._created_nodes.append(node)

    # ---------------------------------------------------------------
    # Resultado
    # ---------------------------------------------------------------

    def get_node(self) -> Node:
        """Retorna el nodo editado (modo edición)."""
        tag = int(self._tag_edit.text())
        return Node(
            tag=tag,
            x=self._x_spin.value(),
            y=self._y_spin.value(),
            z=self._z_spin.value(),
            fixity=self._editing.fixity if self._editing else (),
            mass=self._editing.mass if self._editing else (),
        )

    def get_created_nodes(self) -> list[Node]:
        """Retorna todos los nodos creados (modo creación secuencial)."""
        return list(self._created_nodes)
