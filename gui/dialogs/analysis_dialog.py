"""
Diálogo de configuración y ejecución de análisis.

Permite seleccionar tipo de análisis (estático/modal),
configurar parámetros, ejecutar, y ver resultados.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui.core.analysis_runner import run_modal_analysis, run_static_analysis
from gui.core.model_data import AnalysisResult, StructuralModel


class AnalysisWorker(QThread):
    """Thread para ejecutar el análisis sin bloquear la GUI."""

    finished = Signal(bool, object, str)  # (ok, result, log)

    def __init__(
        self,
        model: StructuralModel,
        analysis_type: str,
        params: dict,
    ) -> None:
        super().__init__()
        self._model = model
        self._analysis_type = analysis_type
        self._params = params

    def run(self) -> None:
        try:
            if self._analysis_type == "static":
                ok, result, log = run_static_analysis(
                    self._model,
                    system=self._params.get("system", "BandSPD"),
                    algorithm=self._params.get("algorithm", "Linear"),
                )
            elif self._analysis_type == "modal":
                ok, result, log = run_modal_analysis(
                    self._model,
                    n_modes=self._params.get("n_modes", 6),
                    system=self._params.get("system", "BandSPD"),
                )
            else:
                ok, result, log = False, None, "Tipo de análisis no soportado."
            self.finished.emit(ok, result, log)
        except Exception as e:
            self.finished.emit(False, None, f"Error inesperado: {e}")


class AnalysisDialog(QDialog):
    """Diálogo para configurar y ejecutar análisis."""

    # Señal emitida cuando hay resultados disponibles
    analysis_complete = Signal(object)  # AnalysisResult

    def __init__(
        self,
        parent=None,
        model: Optional[StructuralModel] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ejecutar análisis")
        self.setMinimumSize(650, 500)

        self._model = model or StructuralModel()
        self._worker: Optional[AnalysisWorker] = None
        self._result: Optional[AnalysisResult] = None

        layout = QVBoxLayout(self)

        # --- Tabs ---
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Tab: Configuración
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)

        grp_type = QGroupBox("Tipo de análisis")
        type_form = QFormLayout()
        grp_type.setLayout(type_form)

        self._type_combo = QComboBox()
        self._type_combo.addItem("Estático lineal", "static")
        self._type_combo.addItem("Modal (eigenvalores)", "modal")
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_form.addRow("Tipo:", self._type_combo)

        config_layout.addWidget(grp_type)

        # Parámetros de análisis
        grp_params = QGroupBox("Parámetros")
        self._params_form = QFormLayout()
        grp_params.setLayout(self._params_form)

        self._system_combo = QComboBox()
        for sys_name in ("BandSPD", "BandGeneral", "ProfileSPD",
                         "UmfPack", "SparseSYM"):
            self._system_combo.addItem(sys_name)
        self._params_form.addRow("Sistema:", self._system_combo)

        self._algo_combo = QComboBox()
        for algo in ("Linear", "Newton", "ModifiedNewton", "KrylovNewton"):
            self._algo_combo.addItem(algo)
        self._algo_lbl = QLabel("Algoritmo:")
        self._params_form.addRow(self._algo_lbl, self._algo_combo)

        self._modes_spin = QSpinBox()
        self._modes_spin.setRange(1, 50)
        self._modes_spin.setValue(6)
        self._modes_lbl = QLabel("Nº de modos:")
        self._params_form.addRow(self._modes_lbl, self._modes_spin)

        config_layout.addWidget(grp_params)

        # Info del modelo
        grp_info = QGroupBox("Modelo")
        info_form = QFormLayout()
        grp_info.setLayout(info_form)
        info_form.addRow("Nodos:", QLabel(str(len(self._model.nodes))))
        info_form.addRow("Elementos:", QLabel(str(len(self._model.elements))))
        info_form.addRow("Materiales:", QLabel(str(len(self._model.materials))))
        info_form.addRow("Patrones:", QLabel(str(len(self._model.load_patterns))))
        config_layout.addWidget(grp_info)

        config_layout.addStretch()
        tabs.addTab(config_widget, "Configuración")

        # Tab: Resultados / Log
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)

        self._results_label = QLabel("Sin resultados. Ejecute un análisis.")
        self._results_label.setWordWrap(True)
        self._results_label.setStyleSheet("padding: 8px;")
        log_layout.addWidget(self._results_label)

        self._log_edit = QPlainTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setPlaceholderText("Log de ejecución...")
        log_layout.addWidget(self._log_edit)

        tabs.addTab(log_widget, "Resultados")

        # --- Progress + Botones ---
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminado
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        btn_layout = QHBoxLayout()
        self._btn_run = QPushButton("▶ Ejecutar análisis")
        self._btn_run.setStyleSheet(
            "font-weight: bold; padding: 8px 16px;"
        )
        self._btn_run.clicked.connect(self._on_run)
        btn_layout.addWidget(self._btn_run)

        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("flat", "true")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        # Configurar visibilidad inicial
        self._on_type_changed()

    # ---------------------------------------------------------------

    def _on_type_changed(self) -> None:
        """Ajusta campos según tipo de análisis."""
        is_static = self._type_combo.currentData() == "static"
        self._algo_combo.setVisible(is_static)
        self._algo_lbl.setVisible(is_static)
        self._modes_spin.setVisible(not is_static)
        self._modes_lbl.setVisible(not is_static)

    def _on_run(self) -> None:
        """Ejecuta el análisis en un thread."""
        analysis_type = self._type_combo.currentData()
        params = {
            "system": self._system_combo.currentText(),
            "algorithm": self._algo_combo.currentText(),
            "n_modes": self._modes_spin.value(),
        }

        self._btn_run.setEnabled(False)
        self._progress.setVisible(True)
        self._results_label.setText("Ejecutando análisis...")
        self._log_edit.clear()

        self._worker = AnalysisWorker(self._model, analysis_type, params)
        self._worker.finished.connect(self._on_analysis_finished)
        self._worker.start()

    def _on_analysis_finished(
        self, ok: bool, result: AnalysisResult | None, log: str
    ) -> None:
        """Callback cuando el análisis termina."""
        self._btn_run.setEnabled(True)
        self._progress.setVisible(False)
        self._log_edit.setPlainText(log)

        if ok and result:
            self._result = result
            self._show_results(result)
            self.analysis_complete.emit(result)
        else:
            self._results_label.setText(
                "❌ Error en el análisis. Revise el log para detalles."
            )
            self._results_label.setStyleSheet(
                "color: #D32F2F; padding: 8px; font-size: 13px;"
            )

    def _show_results(self, result: AnalysisResult) -> None:
        """Presenta los resultados en la pestaña."""
        lines = []

        if result.analysis_type == "static":
            lines.append("✔ ANÁLISIS ESTÁTICO COMPLETADO\n")
            lines.append("Desplazamientos nodales (primeros 20):")
            for i, (tag, disp) in enumerate(
                sorted(result.node_displacements.items())
            ):
                if i >= 20:
                    lines.append(f"  ... y {len(result.node_displacements) - 20} más")
                    break
                disp_str = ", ".join(f"{d:+.6f}" for d in disp[:3])
                lines.append(f"  Nodo {tag}: [{disp_str}] m")

            if result.node_reactions:
                lines.append("\nReacciones en apoyos:")
                for tag, rxn in sorted(result.node_reactions.items()):
                    rxn_str = ", ".join(f"{r:+.2f}" for r in rxn[:3])
                    lines.append(f"  Nodo {tag}: [{rxn_str}] kN")

        elif result.analysis_type == "modal":
            lines.append("✔ ANÁLISIS MODAL COMPLETADO\n")
            lines.append(
                f"{'Modo':>5} | {'Período [s]':>12} | "
                f"{'Frecuencia [Hz]':>15} | {'ω² (eigenval)':>15}"
            )
            lines.append("-" * 55)
            for i, (T, f, ev) in enumerate(
                zip(result.periods, result.frequencies, result.eigenvalues), 1
            ):
                lines.append(
                    f"{i:>5} | {T:>12.4f} | {f:>15.4f} | {ev:>15.4f}"
                )

        self._results_label.setText("\n".join(lines))
        self._results_label.setStyleSheet(
            "color: #212121; padding: 8px; font-family: Consolas; "
            "font-size: 12px; background: #FAFAFA;"
        )

    def get_result(self) -> Optional[AnalysisResult]:
        return self._result
