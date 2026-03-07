"""
Diálogo para asignar cargas nodales dentro de un patrón de carga.

Permite seleccionar nodo, ingresar fuerzas Fx/Fy/Fz y momentos Mx/My/Mz,
y agregar múltiples cargas en secuencia.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from gui.core.model_data import LoadPattern, NodalLoad, StructuralModel


class NodalLoadDialog(QDialog):
    """Diálogo modal para asignar cargas nodales a un patrón."""

    def __init__(
        self,
        parent=None,
        model: Optional[StructuralModel] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Asignar cargas nodales")
        self.setMinimumWidth(500)
        self.setMinimumHeight(580)

        self._model = model or StructuralModel()
        self._applied = False

        layout = QVBoxLayout(self)

        # --- Selección de patrón ---
        grp_pattern = QGroupBox("Patrón de carga")
        pat_layout = QFormLayout()
        grp_pattern.setLayout(pat_layout)

        self._pattern_combo = QComboBox()
        if not self._model.load_patterns:
            self._pattern_combo.addItem("(sin patrones definidos)", None)
        else:
            for tag, pat in sorted(self._model.load_patterns.items()):
                self._pattern_combo.addItem(
                    f"{tag}: {pat.name} [{pat.time_series_type}]", tag
                )
        pat_layout.addRow("Patrón:", self._pattern_combo)
        layout.addWidget(grp_pattern)

        # --- Selección de nodo ---
        grp_load = QGroupBox("Carga nodal")
        load_form = QFormLayout()
        grp_load.setLayout(load_form)

        self._node_spin = QSpinBox()
        self._node_spin.setRange(1, 999_999)
        self._node_spin.setValue(1)
        load_form.addRow("Nodo:", self._node_spin)

        # Fuerzas
        self._fx_spin = QDoubleSpinBox()
        self._fx_spin.setDecimals(2)
        self._fx_spin.setRange(-1e10, 1e10)
        self._fx_spin.setSuffix(" kN")
        load_form.addRow("Fx:", self._fx_spin)

        self._fy_spin = QDoubleSpinBox()
        self._fy_spin.setDecimals(2)
        self._fy_spin.setRange(-1e10, 1e10)
        self._fy_spin.setSuffix(" kN")
        load_form.addRow("Fy:", self._fy_spin)

        self._fz_spin = QDoubleSpinBox()
        self._fz_spin.setDecimals(2)
        self._fz_spin.setRange(-1e10, 1e10)
        self._fz_spin.setSuffix(" kN")
        load_form.addRow("Fz:", self._fz_spin)

        # Momentos
        self._mx_spin = QDoubleSpinBox()
        self._mx_spin.setDecimals(2)
        self._mx_spin.setRange(-1e10, 1e10)
        self._mx_spin.setSuffix(" kN·m")
        load_form.addRow("Mx:", self._mx_spin)

        self._my_spin = QDoubleSpinBox()
        self._my_spin.setDecimals(2)
        self._my_spin.setRange(-1e10, 1e10)
        self._my_spin.setSuffix(" kN·m")
        load_form.addRow("My:", self._my_spin)

        self._mz_spin = QDoubleSpinBox()
        self._mz_spin.setDecimals(2)
        self._mz_spin.setRange(-1e10, 1e10)
        self._mz_spin.setSuffix(" kN·m")
        load_form.addRow("Mz:", self._mz_spin)

        layout.addWidget(grp_load)

        # --- Lista de cargas añadidas ---
        grp_list = QGroupBox("Cargas asignadas en esta sesión")
        list_layout = QVBoxLayout()
        grp_list.setLayout(list_layout)

        self._load_list = QListWidget()
        self._load_list.setMaximumHeight(120)
        list_layout.addWidget(self._load_list)

        layout.addWidget(grp_list)

        # --- Info ---
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #388E3C; padding: 4px;")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label)

        # --- Botones ---
        btn_layout = QHBoxLayout()

        self._btn_add = QPushButton("Agregar carga")
        self._btn_add.clicked.connect(self._on_add_load)
        btn_layout.addWidget(self._btn_add)

        self._btn_close = QPushButton("Cerrar")
        self._btn_close.setProperty("flat", "true")
        self._btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_close)

        layout.addLayout(btn_layout)

    # ---------------------------------------------------------------

    def _on_add_load(self) -> None:
        """Agrega la carga nodal al patrón seleccionado."""
        pat_tag = self._pattern_combo.currentData()
        if pat_tag is None:
            self._info_label.setText("⚠ No hay patrones de carga definidos.")
            self._info_label.setStyleSheet("color: #FF8F00; padding: 4px;")
            return

        node_tag = self._node_spin.value()
        if node_tag not in self._model.nodes:
            self._info_label.setText(f"❌ Nodo {node_tag} no existe.")
            self._info_label.setStyleSheet("color: #D32F2F; padding: 4px;")
            return

        load = NodalLoad(
            node_tag=node_tag,
            fx=self._fx_spin.value(),
            fy=self._fy_spin.value(),
            fz=self._fz_spin.value(),
            mx=self._mx_spin.value(),
            my=self._my_spin.value(),
            mz=self._mz_spin.value(),
        )

        # Agregar al patrón
        pattern = self._model.load_patterns.get(pat_tag)
        if pattern:
            pattern.loads.append(load)
            self._applied = True

        # Mostrar en lista
        forces = []
        if load.fx != 0:
            forces.append(f"Fx={load.fx}")
        if load.fy != 0:
            forces.append(f"Fy={load.fy}")
        if load.fz != 0:
            forces.append(f"Fz={load.fz}")
        if load.mx != 0:
            forces.append(f"Mx={load.mx}")
        if load.my != 0:
            forces.append(f"My={load.my}")
        if load.mz != 0:
            forces.append(f"Mz={load.mz}")
        desc = ", ".join(forces) if forces else "(sin cargas)"
        self._load_list.addItem(
            f"Nodo {node_tag}: {desc}"
        )

        self._info_label.setText(
            f"✔ Carga añadida al nodo {node_tag} (patrón {pat_tag})."
        )
        self._info_label.setStyleSheet("color: #388E3C; padding: 4px;")

        # Reset fuerzas para la siguiente carga
        for spin in (self._fx_spin, self._fy_spin, self._fz_spin,
                     self._mx_spin, self._my_spin, self._mz_spin):
            spin.setValue(0.0)
        self._node_spin.setValue(self._node_spin.value())
        self._node_spin.setFocus()

    @property
    def was_applied(self) -> bool:
        return self._applied
