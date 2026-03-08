# Step 6: Proteger Campos Read-Only en Panel de Propiedades

## Goal
Ampliar los campos read-only del panel de propiedades para incluir `time_series_type` y `self_weight_multiplier` (para DEAD), usando `QLabel` estilizado en lugar de `QLineEdit` editable.

## Prerequisites
Steps 1–5 completados y commiteados. Estás en la branch `fix/sap2000-load-pattern-validation`.

---

### Step-by-Step Instructions

#### 6.1 — Actualizar `READ_ONLY_FIELDS` en `properties_panel.py`

- [x] Abrir `gui/panels/properties_panel.py`
- [x] Localizar la constante `READ_ONLY_FIELDS` (línea ~32) y reemplazar:

**Buscar:**
```python
# Campos read-only que no se deben editar
READ_ONLY_FIELDS = {"tag", "elem_type", "mat_type", "sec_type", "transf_type"}
```

**Reemplazar con:**
```python
# Campos read-only que no se deben editar
READ_ONLY_FIELDS = {
    "tag",
    "elem_type",
    "mat_type",
    "sec_type",
    "transf_type",
    "time_series_type",
}
```

#### 6.2 — Actualizar `HUMAN_LABELS` para nuevos campos

- [x] Verificar que las entradas agregadas en Step 1 ya están presentes en `HUMAN_LABELS`:

```python
    "density": "Densidad [kg/m³]",
    "material_tag": "Material (tag)",
    "self_weight_multiplier": "Mult. peso propio",
```

Si no están, agregarlas al diccionario `HUMAN_LABELS`.

#### 6.3 — Mejorar visualización de campos read-only

El código actual en `_create_field_widget` ya maneja campos read-only con `QLineEdit` + `setReadOnly(True)` + estilo gris. Esto es correcto y funcional. No requiere cambios adicionales.

El handler existente:
```python
        if is_readonly or isinstance(value, (tuple, list, dict)):
            # Solo lectura
            lbl = QLineEdit(self._format_value(value))
            lbl.setReadOnly(True)
            lbl.setStyleSheet("background: #F5F5F5; color: #616161;")
            return lbl
```

Esto ya cubre correctamente:
- `tag` → read-only (es int, pero detectado por READ_ONLY_FIELDS)
- `elem_type`, `mat_type`, etc. → read-only (son Enum, formateados via `_format_value`)
- `time_series_type` → **NUEVO**: ahora será read-only (es str)
- `fixity`, `mass` → read-only (son tuple, detectados por isinstance)
- `loads` → read-only (es list, detectado por isinstance)

**NOTA:** El campo `time_series_type` es un `str`, por lo que sin estar en `READ_ONLY_FIELDS` se mostraría como `QLineEdit` **editable**. Al agregarlo a `READ_ONLY_FIELDS`, ahora se mostrará como campo gris no editable.

---

### Step 6 Verification Checklist
- [x] No hay errores de import al ejecutar `python -c "from gui.panels.properties_panel import PropertiesPanel"`
- [ ] Seleccionar nodo en árbol → campo "Tag" no es editable (fondo gris)
- [ ] Seleccionar material en árbol → campo "Tipo de material" no es editable
- [ ] Seleccionar sección en árbol → campo "Tipo de sección" no es editable
- [ ] Seleccionar elemento en árbol → campo "Tipo de elemento" no es editable
- [ ] Seleccionar patrón de carga en árbol → campo "TimeSeries" no es editable (fondo gris)
- [ ] Seleccionar patrón de carga → campo "Mult. peso propio" **sí es editable** (es float)
- [ ] Campos normales (nombre, coordenadas) → siguen siendo editables
- [ ] La GUI abre sin errores

---

### Step 6 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Mensaje de commit sugerido:
```
fix(ui): protect time_series_type as read-only in properties panel

- Add time_series_type to READ_ONLY_FIELDS set
- Ensures TimeSeries type can only be changed via dialog, not inline edit
```
