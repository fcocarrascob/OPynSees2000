# Step 2: Auto-Crear Patrón DEAD en Modelos Nuevos

## Goal
Modificar `StructuralModel` para auto-crear un patrón "DEAD" (tag=1, `self_weight_multiplier=1.0`) en modelos nuevos, actualizar el modelo demo con densidades y `material_tag`, y manejar migración de modelos antiguos.

## Prerequisites
Steps 1, 1.5, y 1.6 completados y commiteados. Estás en la branch `fix/sap2000-load-pattern-validation`.

---

### Step-by-Step Instructions

#### 2.1 — Modificar `StructuralModel.__init__` y `create_demo` en `model_data.py`

- [ ] Abrir `gui/core/model_data.py`
- [ ] Localizar la clase `StructuralModel` (línea ~295) y reemplazar el `__init__` implícito del dataclass y los métodos `from_dict`, `clear` y `create_demo`.

**Buscar el inicio de la clase:**
```python
@dataclass
class StructuralModel:
    """
    Contenedor central de todos los objetos del modelo.
    Es el 'documento' que la GUI edita.
    """
    ndm: int = 3                                # dimensiones del modelo
    ndf: int = 6                                # grados de libertad por nodo

    nodes: dict[int, Node] = field(default_factory=dict)
    materials: dict[int, Material] = field(default_factory=dict)
    sections: dict[int, Section] = field(default_factory=dict)
    geom_transfs: dict[int, GeomTransf] = field(default_factory=dict)
    elements: dict[int, Element] = field(default_factory=dict)
    load_patterns: dict[int, LoadPattern] = field(default_factory=dict)
```

**Reemplazar con:**
```python
class StructuralModel:
    """
    Contenedor central de todos los objetos del modelo.
    Es el 'documento' que la GUI edita.
    """

    def __init__(
        self,
        ndm: int = 3,
        ndf: int = 6,
        auto_create_dead: bool = True,
    ) -> None:
        self.ndm = ndm
        self.ndf = ndf
        self.nodes: dict[int, Node] = {}
        self.materials: dict[int, Material] = {}
        self.sections: dict[int, Section] = {}
        self.geom_transfs: dict[int, GeomTransf] = {}
        self.elements: dict[int, Element] = {}
        self.load_patterns: dict[int, LoadPattern] = {}

        if auto_create_dead:
            self.load_patterns[1] = LoadPattern(
                tag=1,
                name="DEAD",
                time_series_type="Linear",
                self_weight_multiplier=1.0,
                loads=[],
            )
```

- [ ] Localizar el método `from_dict` y reemplazar **completo** con:

```python
    @classmethod
    def from_dict(cls, d: dict) -> "StructuralModel":
        """Crea un modelo desde diccionario (NO auto-crear DEAD al cargar)."""
        model = cls(ndm=d.get("ndm", 3), ndf=d.get("ndf", 6), auto_create_dead=False)
        for k, v in d.get("nodes", {}).items():
            model.nodes[int(k)] = Node.from_dict(v)
        for k, v in d.get("materials", {}).items():
            model.materials[int(k)] = Material.from_dict(v)
        for k, v in d.get("sections", {}).items():
            model.sections[int(k)] = Section.from_dict(v)
        for k, v in d.get("geom_transfs", {}).items():
            model.geom_transfs[int(k)] = GeomTransf.from_dict(v)
        for k, v in d.get("elements", {}).items():
            model.elements[int(k)] = Element.from_dict(v)
        for k, v in d.get("load_patterns", {}).items():
            model.load_patterns[int(k)] = LoadPattern.from_dict(v)
        return model
```

- [ ] Localizar el método `clear` y reemplazar **completo** con:

```python
    def clear(self) -> None:
        """Borra todo el modelo y re-crea DEAD."""
        self.nodes.clear()
        self.materials.clear()
        self.sections.clear()
        self.geom_transfs.clear()
        self.elements.clear()
        self.load_patterns.clear()
        # Re-crear DEAD obligatorio
        self.load_patterns[1] = LoadPattern(
            tag=1,
            name="DEAD",
            time_series_type="Linear",
            self_weight_multiplier=1.0,
            loads=[],
        )
```

- [ ] Localizar el método `create_demo` y reemplazar **completo** con:

```python
    @classmethod
    def create_demo(cls) -> "StructuralModel":
        """Crea un pórtico 3D de demostración."""
        model = cls(ndm=3, ndf=6, auto_create_dead=True)
        # DEAD ya fue creado en __init__

        # --- Parámetros geométricos ---
        spans_x = [0.0, 5.0, 10.0]         # 2 vanos en X de 5 m
        spans_y = [0.0, 4.0, 8.0]          # 2 vanos en Y de 4 m
        heights = [0.0, 3.5, 7.0]          # 2 pisos de 3.5 m

        # --- Nodos ---
        tag = 1
        node_grid: dict[tuple[int, int, int], int] = {}
        for iz, z in enumerate(heights):
            for iy, y in enumerate(spans_y):
                for ix, x in enumerate(spans_x):
                    fixity = (1, 1, 1, 1, 1, 1) if iz == 0 else ()
                    node = Node(tag=tag, x=x, y=y, z=z, fixity=fixity)
                    model.nodes[tag] = node
                    node_grid[(ix, iy, iz)] = tag
                    tag += 1

        # --- Material con densidad ---
        model.materials[1] = Material(
            tag=1, name="Concreto f'c=28 MPa",
            mat_type=MaterialType.ELASTIC,
            params={"E": 24_821_000.0},
            density=2400.0,
        )

        # --- Secciones con material_tag ---
        model.sections[1] = Section(
            tag=1, name="Columna 40×40",
            sec_type=SectionType.ELASTIC_3D,
            params={"A": 0.16, "E": 24_821_000.0,
                    "Iz": 2.1333e-3, "Iy": 2.1333e-3,
                    "G": 10_342_000.0, "J": 3.6053e-3},
            material_tag=1,
        )
        model.sections[2] = Section(
            tag=2, name="Viga 30×50",
            sec_type=SectionType.ELASTIC_3D,
            params={"A": 0.15, "E": 24_821_000.0,
                    "Iz": 3.125e-3, "Iy": 1.125e-3,
                    "G": 10_342_000.0, "J": 3.516e-3},
            material_tag=1,
        )

        # --- Transformaciones ---
        model.geom_transfs[1] = GeomTransf(
            tag=1, transf_type=TransfType.PDELTA, vecxz=(1.0, 0.0, 0.0)
        )  # columnas
        model.geom_transfs[2] = GeomTransf(
            tag=2, transf_type=TransfType.LINEAR, vecxz=(0.0, 0.0, 1.0)
        )  # vigas

        # --- Elementos ---
        elem_tag = 1

        # Columnas (verticales)
        for iz in range(len(heights) - 1):
            for iy in range(len(spans_y)):
                for ix in range(len(spans_x)):
                    ni = node_grid[(ix, iy, iz)]
                    nj = node_grid[(ix, iy, iz + 1)]
                    model.elements[elem_tag] = Element(
                        tag=elem_tag,
                        elem_type=ElementType.ELASTIC_BEAM_COLUMN,
                        node_i=ni, node_j=nj,
                        section_tag=1, transf_tag=1,
                    )
                    elem_tag += 1

        # Vigas en X
        for iz in range(1, len(heights)):
            for iy in range(len(spans_y)):
                for ix in range(len(spans_x) - 1):
                    ni = node_grid[(ix, iy, iz)]
                    nj = node_grid[(ix + 1, iy, iz)]
                    model.elements[elem_tag] = Element(
                        tag=elem_tag,
                        elem_type=ElementType.ELASTIC_BEAM_COLUMN,
                        node_i=ni, node_j=nj,
                        section_tag=2, transf_tag=2,
                    )
                    elem_tag += 1

        # Vigas en Y
        for iz in range(1, len(heights)):
            for ix in range(len(spans_x)):
                for iy in range(len(spans_y) - 1):
                    ni = node_grid[(ix, iy, iz)]
                    nj = node_grid[(ix, iy + 1, iz)]
                    model.elements[elem_tag] = Element(
                        tag=elem_tag,
                        elem_type=ElementType.ELASTIC_BEAM_COLUMN,
                        node_i=ni, node_j=nj,
                        section_tag=2, transf_tag=2,
                    )
                    elem_tag += 1

        return model
```

**NOTA IMPORTANTE:** Al cambiar `StructuralModel` de `@dataclass` a clase normal, hay que **eliminar** el decorador `@dataclass` que está encima de la clase. Solo la línea `@dataclass`.

#### 2.2 — Actualizar `_on_new_model` en `main_window.py`

- [ ] Abrir `gui/main_window.py`
- [ ] El método `_on_new_model` ya llama `self._model.clear()`, que ahora re-crea DEAD automáticamente. **No requiere cambios.**

#### 2.3 — Verificar que `_on_open` usa la nueva firma de `load_project`

- [ ] Verificar que el método `_on_open` que modificamos en Step 1 maneja el tuple `(model, notification)` correctamente. Ya fue actualizado en Step 1.

---

### Step 2 Verification Checklist
- [ ] No hay errores de import al ejecutar `python -c "from gui.core.model_data import StructuralModel"`
- [ ] `StructuralModel()` crea modelo con `load_patterns = {1: LoadPattern(tag=1, name='DEAD', self_weight_multiplier=1.0)}`
- [ ] `StructuralModel(auto_create_dead=False)` crea modelo con `load_patterns = {}`
- [ ] `StructuralModel.from_dict({"ndm":3,"ndf":6})` crea modelo **sin** DEAD (auto_create_dead=False)
- [ ] `model.clear()` limpia todo y re-crea DEAD automáticamente
- [ ] `StructuralModel.create_demo()` incluye DEAD con mult=1.0, material con density=2400, secciones con material_tag=1
- [ ] Al abrir la GUI → modelo demo muestra "DEAD" en el árbol de patrones de carga
- [ ] Menú Archivo → Nuevo modelo → árbol muestra "DEAD" como único patrón
- [ ] Al hacer `next_pattern_tag()` en modelo nuevo → retorna 2 (DEAD usa tag=1)

---

### Step 2 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Mensaje de commit sugerido:
```
feat(model): auto-create DEAD pattern with self-weight in new models

- StructuralModel: convert from dataclass to regular class with __init__
- Auto-create DEAD pattern (tag=1, mult=1.0) on new model and clear()
- from_dict: load with auto_create_dead=False to preserve file contents  
- create_demo: add density=2400 to material, material_tag=1 to sections
```
