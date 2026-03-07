"""
Diálogo para crear / editar elementos estructurales.

Soporta elementos frame (2 nodos), truss (2 nodos) y shell (4 nodos).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from gui.core.model_data import (
    Element,
    ElementType,
    StructuralModel,
)

# Tipos que requieren 4 nodos
SHELL_TYPES = {ElementType.SHELL_MITC4}

# Tipos que NO requieren transformación geométrica
NO_TRANSF_TYPES = {ElementType.TRUSS, ElementType.COROT_TRUSS, ElementType.SHELL_MITC4}


class ElementDialog(QDialog):
    """Diálogo modal para crear o editar un elemento."""

    def __init__(
        self,
        parent=None,
        model: Optional[StructuralModel] = None,
        element: Optional[Element] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar elemento" if element else "Nuevo elemento")
        self.setMinimumWidth(440)

        self._model = model or StructuralModel()
        self._editing = element

        layout = QVBoxLayout(self)

        # --- Tipo e info ---
        grp_info = QGroupBox("Tipo de elemento")
        form_type = QFormLayout()
        grp_info.setLayout(form_type)

        self._tag_edit = QLineEdit(str(element.tag if element else next_tag))
        self._tag_edit.setReadOnly(True)
        form_type.addRow("Tag:", self._tag_edit)

        self._type_combo = QComboBox()
        for et in ElementType:
            self._type_combo.addItem(et.value, et)
        if element:
            idx = self._type_combo.findData(element.elem_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form_type.addRow("Tipo:", self._type_combo)

        layout.addWidget(grp_info)

        # --- Conectividad ---
        grp_conn = QGroupBox("Conectividad (nodos)")
        self._conn_layout = QFormLayout()
        grp_conn.setLayout(self._conn_layout)

        self._node_i_spin = QSpinBox()
        self._node_i_spin.setRange(1, 999_999)
        self._node_i_spin.setValue(element.node_i if element else 1)
        self._conn_layout.addRow("Nodo I:", self._node_i_spin)

        self._node_j_spin = QSpinBox()
        self._node_j_spin.setRange(1, 999_999)
        self._node_j_spin.setValue(element.node_j if element else 2)
        self._conn_layout.addRow("Nodo J:", self._node_j_spin)

        # Nodos K y L para Shell
        self._node_k_spin = QSpinBox()
        self._node_k_spin.setRange(1, 999_999)
        self._node_k_spin.setValue(element.node_k if element and element.node_k else 3)
        self._lbl_k = QLabel("Nodo K:")

        self._node_l_spin = QSpinBox()
        self._node_l_spin.setRange(1, 999_999)
        self._node_l_spin.setValue(element.node_l if element and element.node_l else 4)
        self._lbl_l = QLabel("Nodo L:")

        self._conn_layout.addRow(self._lbl_k, self._node_k_spin)
        self._conn_layout.addRow(self._lbl_l, self._node_l_spin)

        layout.addWidget(grp_conn)

        # --- Propiedades ---
        grp_props = QGroupBox("Propiedades")
        self._props_layout = QFormLayout()
        grp_props.setLayout(self._props_layout)

        # Sección
        self._section_combo = QComboBox()
        self._section_combo.addItem("(ninguna)", None)
        for tag, sec in sorted(self._model.sections.items()):
            self._section_combo.addItem(
                f"{tag}: {sec.name} [{sec.sec_type.value}]", tag
            )
        if element and element.section_tag:
            idx = self._section_combo.findData(element.section_tag)
            if idx >= 0:
                self._section_combo.setCurrentIndex(idx)
        self._props_layout.addRow("Sección:", self._section_combo)

        # Transformación
        self._transf_combo = QComboBox()
        self._transf_combo.addItem("(ninguna)", None)
        for tag, transf in sorted(self._model.geom_transfs.items()):
            self._transf_combo.addItem(
                f"{tag}: {transf.transf_type.value}", tag
            )
        if element and element.transf_tag:
            idx = self._transf_combo.findData(element.transf_tag)
            if idx >= 0:
                self._transf_combo.setCurrentIndex(idx)
        self._lbl_transf = QLabel("Transformación:")
        self._props_layout.addRow(self._lbl_transf, self._transf_combo)

        layout.addWidget(grp_props)

        # --- Validación ---
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #D32F2F; padding: 4px;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._error_label)

        # --- Botones ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Mostrar/ocultar campos según tipo
        self._on_type_changed()

    # ---------------------------------------------------------------

    def _on_type_changed(self) -> None:
        """Muestra/oculta campos según el tipo de elemento."""
        elem_type: ElementType = self._type_combo.currentData()
        is_shell = elem_type in SHELL_TYPES
        needs_transf = elem_type not in NO_TRANSF_TYPES

        # Nodos K y L solo para Shell
        self._node_k_spin.setVisible(is_shell)
        self._lbl_k.setVisible(is_shell)
        self._node_l_spin.setVisible(is_shell)
        self._lbl_l.setVisible(is_shell)

        # Transformación no aplica a truss/shell
        self._transf_combo.setVisible(needs_transf)
        self._lbl_transf.setVisible(needs_transf)

    def _on_accept(self) -> None:
        """Valida y acepta."""
        elem_type: ElementType = self._type_combo.currentData()
        is_shell = elem_type in SHELL_TYPES

        # Validar que los nodos existen
        node_tags = [self._node_i_spin.value(), self._node_j_spin.value()]
        if is_shell:
            node_tags.extend([self._node_k_spin.value(), self._node_l_spin.value()])

        missing = [t for t in node_tags if t not in self._model.nodes]
        if missing:
            self._error_label.setText(
                f"❌ Nodos no encontrados: {', '.join(str(t) for t in missing)}"
            )
            return

        # Validar sección
        sec_tag = self._section_combo.currentData()
        if sec_tag is None:
            self._error_label.setText("❌ Debe seleccionar una sección.")
            return

        self._error_label.setText("")
        self.accept()

    def get_element(self) -> Element:
        """Retorna el elemento configurado."""
        tag = int(self._tag_edit.text())
        elem_type: ElementType = self._type_combo.currentData()
        is_shell = elem_type in SHELL_TYPES

        return Element(
            tag=tag,
            elem_type=elem_type,
            node_i=self._node_i_spin.value(),
            node_j=self._node_j_spin.value(),
            node_k=self._node_k_spin.value() if is_shell else None,
            node_l=self._node_l_spin.value() if is_shell else None,
            section_tag=self._section_combo.currentData(),
            transf_tag=self._transf_combo.currentData()
            if elem_type not in NO_TRANSF_TYPES
            else None,
        )
