# Step 1: Agregar Campos a Dataclasses (LoadPattern, Material, Section)

## Goal
Agregar `self_weight_multiplier` a `LoadPattern`, `density` a `Material`, y `material_tag` a `Section` en los dataclasses del modelo, con serialización versionada y compatibilidad hacia atrás.

## Prerequisites
Asegúrate de estar en la branch `fix/sap2000-load-pattern-validation`. Si no existe, créala desde `main`:
```bash
git checkout main
git pull origin main
git checkout -b fix/sap2000-load-pattern-validation
```

---

### Step-by-Step Instructions

#### 1.1 — Actualizar dataclass `Material` en `model_data.py`

- [x] Abrir `gui/core/model_data.py`
- [x] Agregar el import `Optional` (ya presente vía `from typing import Optional`)
- [x] Localizar el dataclass `Material` (línea ~113) y reemplazar **completo** con:

```python
@dataclass
class Material:
    """Material uniaxial."""
    tag: int
    name: str
    mat_type: MaterialType
    params: dict = field(default_factory=dict)
    density: float = 0.0  # Densidad [kg/m³] para cálculo de peso propio
    # params varía según tipo. Ej: Steel02 → {Fy, E0, b, R0, cR1, cR2}

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "mat_type": self.mat_type.value,
            "params": dict(self.params),
            "density": self.density,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Material":
        return cls(
            tag=d["tag"],
            name=d["name"],
            mat_type=MaterialType(d["mat_type"]),
            params=d.get("params", {}),
            density=d.get("density", 0.0),
        )
```

#### 1.2 — Actualizar dataclass `Section` en `model_data.py`

- [x] Localizar el dataclass `Section` (línea ~137) y reemplazar **completo** con:

```python
@dataclass
class Section:
    """Sección transversal."""
    tag: int
    name: str
    sec_type: SectionType
    params: dict = field(default_factory=dict)
    material_tag: Optional[int] = None  # Referencia a Material para densidad
    # Ej Elastic3D: {A, E, Iz, Iy, G, J}

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "sec_type": self.sec_type.value,
            "params": dict(self.params),
            "material_tag": self.material_tag,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Section":
        return cls(
            tag=d["tag"],
            name=d["name"],
            sec_type=SectionType(d["sec_type"]),
            params=d.get("params", {}),
            material_tag=d.get("material_tag"),
        )
```

#### 1.3 — Actualizar dataclass `LoadPattern` en `model_data.py`

- [x] Localizar el dataclass `LoadPattern` (línea ~243) y reemplazar **completo** con:

```python
@dataclass
class LoadPattern:
    """Patrón de carga."""
    tag: int
    name: str
    time_series_type: str = "Constant"
    self_weight_multiplier: float = 0.0  # Factor de peso propio (1.0 = completo)
    loads: list[NodalLoad] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "time_series_type": self.time_series_type,
            "self_weight_multiplier": self.self_weight_multiplier,
            "loads": [load.to_dict() for load in self.loads],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LoadPattern":
        return cls(
            tag=d["tag"],
            name=d["name"],
            time_series_type=d.get("time_series_type", "Constant"),
            self_weight_multiplier=d.get("self_weight_multiplier", 0.0),
            loads=[NodalLoad.from_dict(ld) for ld in d.get("loads", [])],
        )
```

#### 1.4 — Actualizar `project_io.py` con versionado

- [x] Abrir `gui/core/project_io.py`
- [x] Reemplazar el archivo **completo** con:

```python
"""
Persistencia del modelo — lectura/escritura JSON (.opss).

Formato del archivo:
{
  "format": "OPynSees2000",
  "version": 2,
  "model": { ... StructuralModel.to_dict() ... }
}
"""

from __future__ import annotations

import json
from pathlib import Path

from gui.core.model_data import StructuralModel


PROJECT_VERSION = 2
FILE_FILTER = "OPynSees2000 (*.opss);;Todos los archivos (*)"


def save_project(model: StructuralModel, path: Path) -> None:
    """Guarda el modelo como archivo JSON (.opss)."""
    data = {
        "format": "OPynSees2000",
        "version": PROJECT_VERSION,
        "model": model.to_dict(),
    }
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_project(path: Path) -> tuple[StructuralModel, str]:
    """
    Carga un modelo desde archivo JSON (.opss).

    Returns
    -------
    tuple[StructuralModel, str]
        Modelo cargado y mensaje de notificación (vacío si no hay).
    """
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)

    fmt = data.get("format", "")
    if fmt != "OPynSees2000":
        raise ValueError(f"Formato de archivo no reconocido: '{fmt}'")

    version = data.get("version", 0)
    if version > PROJECT_VERSION:
        raise ValueError(
            f"Versión de archivo ({version}) más nueva que la soportada ({PROJECT_VERSION})."
        )

    model = StructuralModel.from_dict(data["model"])

    notification = ""
    if version < 2:
        # Modelo antiguo: no tiene self_weight_multiplier / density / material_tag
        has_dead = any(
            p.name.upper() == "DEAD" and p.self_weight_multiplier > 0
            for p in model.load_patterns.values()
        )
        if not has_dead:
            notification = (
                "ℹ️ Modelo cargado sin patrón DEAD con peso propio. "
                "Considere agregar peso propio para análisis modal confiable.\n"
                "Puede crear el patrón DEAD desde: Definir → Patrones de carga..."
            )

    return model, notification
```

#### 1.5 — Actualizar `main_window.py` para nueva firma de `load_project`

- [x] Abrir `gui/main_window.py`
- [x] Localizar el método `_on_open` (línea ~517) y reemplazar **completo** con:

```python
    def _on_open(self) -> None:
        """Abre un archivo .opss."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir proyecto", "", FILE_FILTER,
        )
        if not path:
            return
        try:
            self._model, notification = load_project(Path(path))
            self._current_file = Path(path)
            self._refresh_all()
            self._update_title()
            self._console.log_success(f"Proyecto abierto: {path}")
            if notification:
                self._console.log(notification)
        except Exception as exc:
            self._console.log_error(f"Error al abrir: {exc}")
```

#### 1.6 — Actualizar etiquetas en `properties_panel.py`

- [x] Abrir `gui/panels/properties_panel.py`
- [x] Agregar las siguientes entradas al diccionario `HUMAN_LABELS`:

```python
    "density": "Densidad [kg/m³]",
    "material_tag": "Material (tag)",
    "self_weight_multiplier": "Mult. peso propio",
```

---

### Step 1 Verification Checklist
- [x] No hay errores de import al ejecutar `python -c "from gui.core.model_data import Material, Section, LoadPattern"`
- [x] `Material(tag=1, name="Test", mat_type=MaterialType.ELASTIC, density=2400.0).to_dict()` incluye `"density": 2400.0`
- [x] `Material.from_dict({"tag":1,"name":"T","mat_type":"Elastic"})` retorna objeto con `density=0.0` (backward compat)
- [x] `Section(tag=1, name="S", sec_type=SectionType.ELASTIC_3D, material_tag=1).to_dict()` incluye `"material_tag": 1`
- [x] `Section.from_dict({"tag":1,"name":"S","sec_type":"Elastic3D"})` retorna objeto con `material_tag=None` (backward compat)
- [x] `LoadPattern(tag=1, name="DEAD", self_weight_multiplier=1.0).to_dict()` incluye `"self_weight_multiplier": 1.0`
- [x] `LoadPattern.from_dict({"tag":1,"name":"P"})` retorna objeto con `self_weight_multiplier=0.0` (backward compat)
- [x] `load_project()` retorna tuple `(model, notification)` correctamente
- [ ] La GUI abre sin errores

---

### Step 1 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Mensaje de commit sugerido:
```
feat(model): add density, material_tag, self_weight_multiplier fields

- Material: add density field [kg/m³] with backward compat default 0.0
- Section: add material_tag field (Optional[int]) for density lookup
- LoadPattern: add self_weight_multiplier field with default 0.0
- project_io: bump version to 2, load_project returns (model, notification)
- properties_panel: add HUMAN_LABELS for new fields
```
