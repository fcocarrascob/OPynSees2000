# Step 3: Actualizar Diálogo de Patrón de Carga + Protección DEAD

## Goal
Agregar campo `self_weight_multiplier` al diálogo de patrones de carga, bloquear el multiplicador del patrón DEAD, y prevenir su eliminación.

## Prerequisites
Steps 1, 1.5, 1.6 y 2 completados y commiteados. Estás en la branch `fix/sap2000-load-pattern-validation`.

---

### Step-by-Step Instructions

#### 3.1 — Reemplazar `load_pattern_dialog.py` completo

- [ ] Abrir `gui/dialogs/load_pattern_dialog.py`
- [ ] Reemplazar el contenido **completo** del archivo con:

```python
"""
Diálogo para crear / editar patrones de carga.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QVBoxLayout,
)

from gui.core.model_data import LoadPattern

# Tipos de TimeSeries disponibles
TIME_SERIES_TYPES = ["Constant", "Linear", "Path"]


class LoadPatternDialog(QDialog):
    """Diálogo modal para crear o editar un patrón de carga."""

    def __init__(
        self,
        parent=None,
        pattern: Optional[LoadPattern] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar patrón" if pattern else "Nuevo patrón de carga")
        self.setMinimumWidth(420)

        self._editing = pattern
        is_dead = pattern is not None and pattern.tag == 1

        layout = QVBoxLayout(self)

        grp = QGroupBox("Patrón de carga")
        form = QFormLayout()
        grp.setLayout(form)

        self._tag_edit = QLineEdit(str(pattern.tag if pattern else next_tag))
        self._tag_edit.setReadOnly(True)
        form.addRow("Tag:", self._tag_edit)

        self._name_edit = QLineEdit(pattern.name if pattern else "")
        self._name_edit.setPlaceholderText("Ej: Carga muerta, Carga viva, Sismo X")
        form.addRow("Nombre:", self._name_edit)

        self._ts_combo = QComboBox()
        for ts in TIME_SERIES_TYPES:
            self._ts_combo.addItem(ts)
        if pattern:
            idx = self._ts_combo.findText(pattern.time_series_type)
            if idx >= 0:
                self._ts_combo.setCurrentIndex(idx)
        form.addRow("Time Series:", self._ts_combo)

        # --- Multiplicador de peso propio ---
        self._sw_spinbox = QDoubleSpinBox()
        self._sw_spinbox.setRange(-5.0, 5.0)
        self._sw_spinbox.setDecimals(2)
        self._sw_spinbox.setSingleStep(0.1)
        self._sw_spinbox.setValue(
            pattern.self_weight_multiplier if pattern else 0.0
        )

        if is_dead:
            # DEAD: multiplicador bloqueado en 1.0
            self._sw_spinbox.setValue(1.0)
            self._sw_spinbox.setReadOnly(True)
            self._sw_spinbox.setEnabled(False)
            self._sw_spinbox.setToolTip(
                "El patrón DEAD siempre tiene multiplicador 1.0 (no editable)"
            )
        else:
            self._sw_spinbox.setToolTip(
                "Factor peso propio: 1.0 = completo, 0.0 = sin peso.\n"
                "Permite factorización (ej: 1.2 para sobrecarga)."
            )

        form.addRow("Mult. peso propio:", self._sw_spinbox)

        layout.addWidget(grp)

        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self.accept()

    def get_pattern(self) -> LoadPattern:
        """Retorna el patrón configurado."""
        tag = int(self._tag_edit.text())
        # Forzar mult=1.0 para DEAD (defensa en profundidad)
        mult = 1.0 if tag == 1 else self._sw_spinbox.value()
        return LoadPattern(
            tag=tag,
            name=self._name_edit.text().strip(),
            time_series_type=self._ts_combo.currentText(),
            self_weight_multiplier=mult,
            loads=self._editing.loads if self._editing else [],
        )
```

#### 3.2 — Proteger eliminación de DEAD en `main_window.py`

El modelo actual no tiene un botón explícito de "Eliminar patrón de carga" como acción separada, pero tiene la acción genérica `_act_delete` ("Eliminar selección") en el menú Editar. Para prevenir la eliminación de DEAD, necesitamos agregar lógica al eliminar ítems del árbol.

- [ ] Abrir `gui/main_window.py`
- [ ] Localizar la acción `_act_delete` (línea ~183). Actualmente está deshabilitada (`setEnabled(False)`). Necesitamos implementar la eliminación con protección DEAD.

- [ ] Agregar el siguiente método **nuevo** al final de la sección de Slots (antes de `closeEvent`):

**Buscar este bloque (al final de los slots, antes de closeEvent):**
```python
    def _on_property_changed(self, category: str, tag: int) -> None:
        """Llamado cuando el properties panel edita una propiedad."""
        self._refresh_all()

    # ------------------------------------------------------------------
    # Override close
    # ------------------------------------------------------------------
```

**Reemplazar con:**
```python
    def _on_property_changed(self, category: str, tag: int) -> None:
        """Llamado cuando el properties panel edita una propiedad."""
        self._refresh_all()

    def _on_delete_selected(self) -> None:
        """Elimina el ítem seleccionado en el árbol."""
        current = self._tree.currentItem()
        if current is None:
            return
        category = current.data(0, 100)
        tag = current.data(0, 101)
        if category is None or tag is None:
            return

        # Prevenir eliminación del patrón DEAD
        if category == "load_patterns" and tag == 1:
            self._console.log_error(
                "El patrón DEAD (tag=1) es obligatorio y no puede eliminarse."
            )
            return

        mapping = {
            "nodes": self._model.nodes,
            "materials": self._model.materials,
            "sections": self._model.sections,
            "geom_transfs": self._model.geom_transfs,
            "elements": self._model.elements,
            "load_patterns": self._model.load_patterns,
        }
        container = mapping.get(category)
        if container is None or tag not in container:
            return

        container.pop(tag)
        self._refresh_all()
        self._console.log(f"Eliminado: {category} → tag {tag}")

    # ------------------------------------------------------------------
    # Override close
    # ------------------------------------------------------------------
```

- [ ] Ahora conectar la acción `_act_delete` y habilitarla. Localizar estas líneas dentro de `_build_menubar`:

**Buscar:**
```python
        act_delete = QAction("Eliminar selección", self)
        act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        act_delete.setEnabled(False)
        m_edit.addAction(act_delete)
        self._act_delete = act_delete
```

**Reemplazar con:**
```python
        act_delete = QAction("Eliminar selección", self)
        act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        act_delete.setEnabled(True)
        act_delete.triggered.connect(self._on_delete_selected)
        m_edit.addAction(act_delete)
        self._act_delete = act_delete
```

---

### Step 3 Verification Checklist
- [ ] No hay errores de import al ejecutar `python -c "from gui.dialogs.load_pattern_dialog import LoadPatternDialog"`
- [ ] Al crear nuevo patrón de carga → campo "Mult. peso propio:" visible, valor por defecto 0.0
- [ ] Al editar patrón DEAD → multiplicador muestra 1.0 y está **deshabilitado** (gris)
- [ ] Al crear patrón con mult=0.5 → `get_pattern().self_weight_multiplier == 0.5`
- [ ] `get_pattern()` para tag=1 siempre retorna `self_weight_multiplier=1.0`
- [ ] Seleccionar DEAD en árbol → presionar Delete → mensaje de error en consola, no se elimina
- [ ] Seleccionar otro patrón → presionar Delete → se elimina correctamente
- [ ] Seleccionar nodo → presionar Delete → se elimina correctamente
- [ ] La GUI abre sin errores

---

### Step 3 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Mensaje de commit sugerido:
```
feat(ui): add self-weight multiplier to load pattern dialog + protect DEAD

- LoadPatternDialog: add QDoubleSpinBox for self_weight_multiplier
- DEAD pattern (tag=1): multiplier locked at 1.0, field disabled
- Implement _on_delete_selected with DEAD deletion protection
- Enable Delete action in Edit menu
```
