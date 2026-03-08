# Step 5: Implementar Validación Pre-Análisis

## Goal
Crear validación pre-análisis en `analysis_dialog.py` que verifique el modelo antes de ejecutar, bloqueando análisis con errores descriptivos para modelos estáticos sin cargas/apoyos y modelos modales sin masa.

## Prerequisites
Steps 1–4 completados y commiteados. Estás en la branch `fix/sap2000-load-pattern-validation`.

---

### Step-by-Step Instructions

#### 5.1 — Agregar método `_validate_model` y modificar `_on_run` en `analysis_dialog.py`

- [x] Abrir `gui/dialogs/analysis_dialog.py`
- [x] Localizar el método `_on_run` (línea ~162) y reemplazar con la siguiente versión que incluye validación:

**Buscar:**
```python
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
```

**Reemplazar con:**
```python
    def _validate_model(self, analysis_type: str) -> tuple[bool, str]:
        """
        Valida el modelo antes de ejecutar análisis.

        Returns
        -------
        tuple[bool, str]
            (es_válido, mensaje_error). Si es_válido=True, mensaje está vacío.
        """
        if not self._model.nodes:
            return False, "El modelo no tiene nodos definidos."

        if not self._model.elements:
            return False, "El modelo no tiene elementos definidos."

        # Validar conectividad de elementos
        for elem_tag, elem in self._model.elements.items():
            if elem.node_i not in self._model.nodes:
                return False, (
                    f"Elemento {elem_tag} referencia nodo inexistente {elem.node_i}."
                )
            if elem.node_j not in self._model.nodes:
                return False, (
                    f"Elemento {elem_tag} referencia nodo inexistente {elem.node_j}."
                )
            if elem.node_k is not None and elem.node_k not in self._model.nodes:
                return False, (
                    f"Elemento {elem_tag} referencia nodo inexistente {elem.node_k}."
                )
            if elem.node_l is not None and elem.node_l not in self._model.nodes:
                return False, (
                    f"Elemento {elem_tag} referencia nodo inexistente {elem.node_l}."
                )

        if analysis_type == "static":
            if not self._model.load_patterns:
                return False, "Análisis estático requiere al menos un patrón de carga."

            has_support = any(n.is_fixed for n in self._model.nodes.values())
            if not has_support:
                return False, (
                    "El modelo no tiene nodos restringidos (apoyos).\n"
                    "Asigne restricciones desde: Asignar → Restricciones..."
                )

        elif analysis_type == "modal":
            has_dead = any(
                p.self_weight_multiplier > 0
                for p in self._model.load_patterns.values()
            )
            has_explicit_mass = any(
                n.mass and any(m > 0 for m in n.mass)
                for n in self._model.nodes.values()
            )
            # Verificar que hay densidad en al menos un material si confiamos en DEAD
            has_density = False
            if has_dead:
                for sec in self._model.sections.values():
                    if sec.material_tag and sec.material_tag in self._model.materials:
                        mat = self._model.materials[sec.material_tag]
                        if mat.density > 0:
                            has_density = True
                            break

            if not has_dead and not has_explicit_mass:
                return False, (
                    "Análisis modal requiere masa en los nodos.\n"
                    "Asegúrese que existe el patrón DEAD con peso propio "
                    "(multiplicador > 0) o asigne masa explícita a los nodos."
                )

            if has_dead and not has_density and not has_explicit_mass:
                return False, (
                    "El patrón DEAD existe pero ningún material tiene densidad definida.\n"
                    "Configure la densidad en: Definir → Materiales...\n"
                    "Y asocie el material a las secciones en: Definir → Secciones..."
                )

        return True, ""

    def _on_run(self) -> None:
        """Valida el modelo y ejecuta el análisis en un thread."""
        analysis_type = self._type_combo.currentData()

        # Validación pre-análisis
        ok, error_msg = self._validate_model(analysis_type)
        if not ok:
            self._results_label.setText(f"❌ {error_msg}")
            self._results_label.setStyleSheet(
                "color: #D32F2F; padding: 8px; font-size: 13px;"
            )
            self._log_edit.setPlainText(f"Validación fallida: {error_msg}")
            return

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
```

---

### Step 5 Verification Checklist
- [x] No hay errores de import al ejecutar `python -c "from gui.dialogs.analysis_dialog import AnalysisDialog"`
- [ ] **Modelo vacío:** Archivo → Nuevo modelo → F5 → "El modelo no tiene elementos definidos."
- [ ] **Sin apoyos:** Crear nodos y elementos sin restricciones → Análisis estático → "El modelo no tiene nodos restringidos"
- [ ] **Sin cargas:** Crear modelo sin patrones de carga (imposible con DEAD auto, pero verificar validación)
- [ ] **Modal sin masa ni densidad:** Crear modelo con material sin densidad y sin masas explícitas → Análisis modal → error descriptivo
- [ ] **Modal con DEAD + densidad:** Modelo demo con DEAD y density=2400 → Análisis modal → ejecuta correctamente
- [ ] **Elemento huérfano:** Crear elemento con nodo inexistente → análisis → "Elemento X referencia nodo inexistente Y"
- [ ] El error se muestra tanto en la pestaña "Resultados" como en el log

---

### Step 5 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Mensaje de commit sugerido:
```
feat(analysis): add pre-analysis model validation

- Validate nodes, elements, connectivity before running analysis
- Static: require load patterns and at least one support
- Modal: require mass (via DEAD+density or explicit node mass)
- Show descriptive error messages in results tab and log
```
