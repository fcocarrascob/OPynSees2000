"""
Diálogo para asignar condiciones de borde a nodos.

Presets: Empotrado, Articulado, Libre.
Selección individual de DOFs con checkboxes.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from gui.core.model_data import Node, StructuralModel


# Presets de condiciones de borde (6 DOF: dx, dy, dz, rx, ry, rz)
FIXITY_PRESETS: dict[str, tuple[int, ...]] = {
    "Libre": (0, 0, 0, 0, 0, 0),
    "Empotrado": (1, 1, 1, 1, 1, 1),
    "Articulado (pin)": (1, 1, 1, 0, 0, 0),
    "Rodillo X (libre en X)": (0, 1, 1, 0, 0, 0),
    "Rodillo Y (libre en Y)": (1, 0, 1, 0, 0, 0),
    "Rodillo Z (libre en Z)": (1, 1, 0, 0, 0, 0),
    "Personalizado": (),
}

DOF_LABELS = ["dx (traslación X)", "dy (traslación Y)", "dz (traslación Z)",
              "rx (rotación X)", "ry (rotación Y)", "rz (rotación Z)"]


class FixityDialog(QDialog):
    """Diálogo modal para asignar restricciones a nodos seleccionados."""

    def __init__(
        self,
        parent=None,
        model: Optional[StructuralModel] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Asignar restricciones")
        self.setMinimumWidth(460)
        self.setMinimumHeight(500)

        self._model = model or StructuralModel()

        layout = QVBoxLayout(self)

        # --- Selección de nodos ---
        grp_nodes = QGroupBox("Seleccionar nodos")
        nodes_layout = QVBoxLayout()
        grp_nodes.setLayout(nodes_layout)

        # Botones de selección rápida
        btn_row = QHBoxLayout()
        btn_all = QPushButton("Seleccionar todos")
        btn_all.setProperty("flat", "true")
        btn_all.clicked.connect(self._select_all)
        btn_row.addWidget(btn_all)

        btn_none = QPushButton("Deseleccionar todos")
        btn_none.setProperty("flat", "true")
        btn_none.clicked.connect(self._deselect_all)
        btn_row.addWidget(btn_none)

        btn_free = QPushButton("Solo libres")
        btn_free.setProperty("flat", "true")
        btn_free.clicked.connect(self._select_free_only)
        btn_row.addWidget(btn_free)

        nodes_layout.addLayout(btn_row)

        # Lista de nodos con checkboxes
        self._node_list = QListWidget()
        self._node_list.setMaximumHeight(180)
        for tag, node in sorted(self._model.nodes.items()):
            fix_str = " [EMP]" if node.is_fully_fixed else ""
            item = QListWidgetItem(
                f"Nodo {tag}: ({node.x:.1f}, {node.y:.1f}, {node.z:.1f}){fix_str}"
            )
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self._node_list.addItem(item)

        nodes_layout.addWidget(self._node_list)
        layout.addWidget(grp_nodes)

        # --- Condición de borde ---
        grp_fix = QGroupBox("Condición de borde")
        fix_layout = QVBoxLayout()
        grp_fix.setLayout(fix_layout)

        # Preset combo
        self._preset_combo = QComboBox()
        for name in FIXITY_PRESETS:
            self._preset_combo.addItem(name)
        self._preset_combo.setCurrentText("Empotrado")
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        fix_layout.addWidget(self._preset_combo)

        # DOF checkboxes
        self._dof_checks: list[QCheckBox] = []
        dof_form = QFormLayout()
        for i, label in enumerate(DOF_LABELS):
            cb = QCheckBox()
            cb.stateChanged.connect(self._on_dof_changed)
            self._dof_checks.append(cb)
            dof_form.addRow(label + ":", cb)
        fix_layout.addLayout(dof_form)

        layout.addWidget(grp_fix)

        # Info
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #757575; padding: 4px;")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label)

        # --- Botones ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Close
        )
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._on_apply
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Aplicar preset inicial
        self._on_preset_changed("Empotrado")

    # ---------------------------------------------------------------

    def _select_all(self) -> None:
        for i in range(self._node_list.count()):
            self._node_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        for i in range(self._node_list.count()):
            self._node_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _select_free_only(self) -> None:
        """Selecciona solo nodos sin restricciones."""
        for i in range(self._node_list.count()):
            item = self._node_list.item(i)
            tag = item.data(Qt.ItemDataRole.UserRole)
            node = self._model.nodes.get(tag)
            if node and not node.is_fixed:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _on_preset_changed(self, text: str) -> None:
        """Aplica un preset de fixity."""
        fixity = FIXITY_PRESETS.get(text, ())
        if not fixity:
            return  # Personalizado: no cambiar nada
        for i, val in enumerate(fixity):
            self._dof_checks[i].setChecked(val == 1)

    def _on_dof_changed(self) -> None:
        """Actualiza el preset combo si los DOFs no coinciden."""
        current = tuple(1 if cb.isChecked() else 0 for cb in self._dof_checks)
        for name, preset in FIXITY_PRESETS.items():
            if preset == current:
                self._preset_combo.blockSignals(True)
                self._preset_combo.setCurrentText(name)
                self._preset_combo.blockSignals(False)
                return
        self._preset_combo.blockSignals(True)
        self._preset_combo.setCurrentText("Personalizado")
        self._preset_combo.blockSignals(False)

    def _on_apply(self) -> None:
        """Aplica las restricciones a los nodos seleccionados."""
        fixity = tuple(1 if cb.isChecked() else 0 for cb in self._dof_checks)
        selected_tags = self._get_selected_tags()

        if not selected_tags:
            self._info_label.setText("⚠ No hay nodos seleccionados.")
            self._info_label.setStyleSheet("color: #FF8F00; padding: 4px;")
            return

        for tag in selected_tags:
            node = self._model.nodes.get(tag)
            if node:
                # Reemplazar fixity (dataclass inmutable → crear nuevo)
                self._model.nodes[tag] = Node(
                    tag=node.tag, x=node.x, y=node.y, z=node.z,
                    fixity=fixity, mass=node.mass,
                )

        self._applied = True
        self._info_label.setText(
            f"✔ Restricciones aplicadas a {len(selected_tags)} nodo(s)."
        )
        self._info_label.setStyleSheet("color: #388E3C; padding: 4px;")

        # Actualizar la lista para reflejar cambios
        self._refresh_node_list()

    def _get_selected_tags(self) -> list[int]:
        """Retorna los tags de nodos seleccionados."""
        tags = []
        for i in range(self._node_list.count()):
            item = self._node_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                tags.append(item.data(Qt.ItemDataRole.UserRole))
        return tags

    def _refresh_node_list(self) -> None:
        """Actualiza el texto de los ítems despues de aplicar."""
        for i in range(self._node_list.count()):
            item = self._node_list.item(i)
            tag = item.data(Qt.ItemDataRole.UserRole)
            node = self._model.nodes.get(tag)
            if node:
                fix_str = " [EMP]" if node.is_fully_fixed else (
                    " [FIX]" if node.is_fixed else ""
                )
                item.setText(
                    f"Nodo {tag}: ({node.x:.1f}, {node.y:.1f}, {node.z:.1f}){fix_str}"
                )

    # ---------------------------------------------------------------

    @property
    def was_applied(self) -> bool:
        """True si se aplicaron cambios."""
        return getattr(self, "_applied", False)
