# Corrección de Bugs Críticos: Patrones de Carga SAP2000-Style

**Branch:** `fix/sap2000-load-pattern-validation`  
**Description:** Implementa validación pre-análisis, patrones de carga con peso propio automático (DEAD), y protección de campos read-only en el panel de propiedades.

**Status:** ✅ **APROBADO** — Decisiones de diseño confirmadas, listo para implementación.

---

## Goal

Resolver 3 bugs críticos identificados en OPynSees2000 e implementar el patrón de carga DEAD con peso propio automático al estilo SAP2000. Esto asegura que:
1. El modelo **siempre** tenga un patrón de carga "DEAD" con peso propio (multiplicador = 1.0)
2. Otros patrones de carga puedan opcionalmente incluir/excluir peso propio (multiplicador = 0 o 1)
3. El análisis modal sea confiable sin asignación silenciosa de masas
4. Los usuarios reciban validación clara antes de ejecutar análisis
5. Los campos read-only del panel de propiedades no sean editables

Este cambio arquitectónico transforma el modelo de datos para alinearse con SAP2000, donde cada modelo nuevo automáticamente tiene peso propio considerado.

---

## Implementation Steps

### Step 1: Agregar Factor de Peso Propio a LoadPattern, Densidad a Material, y Material Tag a Section
**Archivos:**
- [gui/core/model_data.py](gui/core/model_data.py) (LoadPattern, Material y Section dataclasses)
- [gui/core/project_io.py](gui/core/project_io.py) (serialización versionada)

**Qué:**
**A) LoadPattern - Campo self_weight_multiplier:**
Modificar el dataclass `LoadPattern` para agregar campo `self_weight_multiplier: float = 0.0`. Este factor determina si el patrón incluye peso propio:
- `1.0` = incluye peso propio completo (gravedad)
- `0.0` = sin peso propio
- Otros valores permiten factorización (ej: 1.2 para sobrecarga)

**B) Material - Campo density:**
Agregar campo `density: float = 0.0` al dataclass `Material` para almacenar densidad del material en kg/m³:
- Concreto típico: 2400 kg/m³
- Acero: 7850 kg/m³
- Madera: 600-800 kg/m³
- Aluminio: 2700 kg/m³

**C) Section - Campo material_tag (opcional):**
Agregar campo `material_tag: Optional[int] = None` al dataclass `Section` para referenciar el Material asociado y obtener su densidad durante el cálculo de peso propio. Si es `None`, no se calcula masa automática para esa sección.

Esto permite calcular peso propio desde geometría y propiedades del material sin valores hardcodeados.

Actualizar métodos `to_dict()` y `from_dict()` para los tres dataclasses, con **compatibilidad hacia atrás**:
- `self_weight_multiplier`: default = 0.0 si no existe
- `density`: default = 0.0 si no existe
- `material_tag`: default = None si no existe

Incrementar versión de formato a `"2.0"` en archivos nuevos.

**Testing:**
- Crear LoadPattern con `self_weight_multiplier=1.0` y verificar serialización
- Crear Material con `density=2400.0` y verificar serialización
- Crear Section con `material_tag=1` y verificar serialización
- Cargar archivo antiguo (.opss versión 1.0) y verificar defaults
- Verificar que archivo guardado incluye nuevos campos y version="2.0"

**Implementación técnica:**
```python
@dataclass
class Material:
    """Material uniaxial."""
    tag: int
    name: str
    mat_type: MaterialType
    params: dict = field(default_factory=dict)
    density: float = 0.0  # ← NUEVO CAMPO [kg/m³]

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "mat_type": self.mat_type.value,
            "params": dict(self.params),
            "density": self.density,  # ← NUEVO
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Material":
        return cls(
            tag=d["tag"],
            name=d["name"],
            mat_type=MaterialType(d["mat_type"]),
            params=d.get("params", {}),
            density=d.get("density", 0.0),  # ← COMPATIBILIDAD BACKWARD
        )

@dataclass
class Section:
    """Sección transversal."""
    tag: int
    name: str
    sec_type: SectionType
    params: dict = field(default_factory=dict)
    material_tag: Optional[int] = None  # ← NUEVO CAMPO (referencia a Material)

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "sec_type": self.sec_type.value,
            "params": dict(self.params),
            "material_tag": self.material_tag,  # ← NUEVO
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Section":
        return cls(
            tag=d["tag"],
            name=d["name"],
            sec_type=SectionType(d["sec_type"]),
            params=d.get("params", {}),
            material_tag=d.get("material_tag"),  # ← COMPATIBILIDAD (None si no existe)
        )

@dataclass
class LoadPattern:
    """Patrón de carga."""
    tag: int
    name: str
    time_series_type: str = "Constant"
    self_weight_multiplier: float = 0.0  # ← NUEVO CAMPO
    loads: list[NodalLoad] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "time_series_type": self.time_series_type,
            "self_weight_multiplier": self.self_weight_multiplier,  # ← NUEVO
            "loads": [load.to_dict() for load in self.loads],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LoadPattern":
        return cls(
            tag=d["tag"],
            name=d["name"],
            time_series_type=d.get("time_series_type", "Constant"),
            self_weight_multiplier=d.get("self_weight_multiplier", 0.0),  # ← COMPATIBILIDAD
            loads=[NodalLoad.from_dict(ld) for ld in d.get("loads", [])],
        )
```

```python
# En project_io.py
FILE_VERSION = "2.0"  # Actualizar versión

def save_model(model: StructuralModel, filepath: str) -> None:
    """Guarda modelo a archivo JSON."""
    data = {
        "version": FILE_VERSION,  # "2.0"
        "model": model.to_dict()
    }
    # ... resto del código

def load_model(filepath: str) -> StructuralModel:
    """Carga modelo desde archivo JSON."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    version = data.get("version", "1.0")
    if version not in ["1.0", "2.0"]:
        raise ValueError(f"Versión de archivo no soportada: {version}")
    
    # Material/Section/LoadPattern.from_dict() manejan compatibilidad automáticamente
    return StructuralModel.from_dict(data["model"])
```

---

### Step 1.5: Actualizar Diálogo de Material con Campo Densidad
**Archivos:**
- [gui/dialogs/material_dialog.py](gui/dialogs/material_dialog.py)

**Qué:**
Agregar un campo `QDoubleSpinBox` en el diálogo de material para configurar la densidad:
- Etiqueta: "Densidad [kg/m³]:"
- Rango: 0.0 a 20000.0
- Valor por defecto según tipo de material:
  - **Concreto** (Concrete01/02): 2400.0 kg/m³
  - **Acero** (Steel02, ElasticPP, Hysteretic): 7850.0 kg/m³
  - **Elástico genérico**: 2400.0 kg/m³ (configurable por usuario)
- Tooltip: "Densidad del material para cálculo de peso propio. Concreto: 2400, Acero: 7850, Madera: 600-800"

El campo debe estar **siempre visible** independiente del tipo de material, ubicado después del nombre del material y antes de los parámetros específicos.

**Testing:**
- Crear material Steel02 → verificar densidad default 7850
- Crear material Concrete01 → verificar densidad default 2400
- Modificar densidad a 3000 → guardar → cargar → verificar persistencia
- Verificar que densidad se almacena en Material.density

**Implementación técnica:**
```python
# En MaterialDialog.__init__(), después del campo "Nombre"

# Campo de densidad (común a todos los materiales)
self._density_spinbox = QDoubleSpinBox()
self._density_spinbox.setRange(0.0, 20000.0)
self._density_spinbox.setDecimals(1)
self._density_spinbox.setSingleStep(100.0)
self._density_spinbox.setSuffix(" kg/m³")
self._density_spinbox.setToolTip(
    "Densidad del material para cálculo de peso propio.\n"
    "Valores típicos:\n"
    "• Concreto: 2400 kg/m³\n"
    "• Acero: 7850 kg/m³\n"
    "• Madera: 600-800 kg/m³\n"
    "• Aluminio: 2700 kg/m³"
)

# Valor inicial: si edita material existente, usar su densidad; sino, default por tipo
if material:
    self._density_spinbox.setValue(material.density)
else:
    # Default según tipo inicial
    default_density = self._get_default_density(self._type_combo.currentText())
    self._density_spinbox.setValue(default_density)

form_layout.addRow("Densidad:", self._density_spinbox)

# Conectar cambio de tipo a actualización de densidad default
self._type_combo.currentTextChanged.connect(self._on_type_changed)

# ... resto del código (parámetros dinámicos)

def _get_default_density(self, mat_type_str: str) -> float:
    """Retorna densidad típica según tipo de material."""
    if "Concrete" in mat_type_str:
        return 2400.0  # Concreto
    elif "Steel" in mat_type_str or "Hysteretic" in mat_type_str or "ElasticPP" in mat_type_str:
        return 7850.0  # Acero
    else:
        return 2400.0  # Default genérico

def _on_type_changed(self, new_type: str) -> None:
    """Actualiza campos dinámicos y densidad default al cambiar tipo."""
    # Actualizar densidad solo si está en valor default actual
    # (no sobrescribir si usuario ya modificó manualmente)
    current_density = self._density_spinbox.value()
    
    # Regenerar parámetros dinámicos
    self._rebuild_params_section()
    
    # Sugerir nueva densidad (solo si no fue editada manualmente)
    if current_density in [2400.0, 7850.0, 0.0]:  # Valores típicos
        new_default = self._get_default_density(new_type)
        self._density_spinbox.setValue(new_default)

def get_material(self) -> Material:
    """Retorna material configurado."""
    tag = int(self._tag_edit.text())
    name = self._name_edit.text().strip()
    mat_type = MaterialType(self._type_combo.currentText())
    density = self._density_spinbox.value()  # ← NUEVO
    
    # Recopilar parámetros dinámicos
    params = {}
    for param_key, widget in self._param_widgets.items():
        params[param_key] = widget.value()
    
    return Material(
        tag=tag,
        name=name,
        mat_type=mat_type,
        params=params,
        density=density  # ← NUEVO
    )
```

---

### Step 1.6: Actualizar Diálogo de Sección con Campo Material Tag
**Archivos:**
- [gui/dialogs/section_dialog.py](gui/dialogs/section_dialog.py)

**Qué:**
Agregar un `QComboBox` en el diálogo de sección para seleccionar el material asociado:
- Etiqueta: "Material (para densidad):"
- Opciones: Lista de materiales disponibles en el modelo (tag: nombre)
- Opcional: Puede dejarse vacío (None) si no se necesita calcular peso propio
- Tooltip: "Material asociado para obtener densidad en cálculo de peso propio. Opcional."

El campo debe estar ubicado después del nombre de la sección y antes de los parámetros geométricos.

**Testing:**
- Crear sección → seleccionar material 1 → verificar `section.material_tag = 1`
- Crear sección sin material → verificar `section.material_tag = None`
- Editar sección → cambiar material → guardar → verificar actualización
- Verificar que material_tag se serializa correctamente

**Implementación técnica:**
```python
# En SectionDialog.__init__()

# Material selector (opcional)
self._material_combo = QComboBox()
self._material_combo.addItem("(Ninguno - sin peso propio)", None)

# Poblar con materiales del modelo
if hasattr(parent, '_model'):  # Acceder al modelo desde main_window
    for mat_tag in sorted(parent._model.materials.keys()):
        mat = parent._model.materials[mat_tag]
        self._material_combo.addItem(
            f"{mat_tag}: {mat.name} ({mat.density} kg/m³)", 
            mat_tag
        )

# Valor initial
if section and section.material_tag:
    idx = self._material_combo.findData(section.material_tag)
    if idx >= 0:
        self._material_combo.setCurrentIndex(idx)

self._material_combo.setToolTip(
    "Material asociado para obtener densidad en cálculo de peso propio.\n"
    "Si no se selecciona, el elemento no contribuirá a la masa del modelo."
)

form_layout.addRow("Material (densidad):", self._material_combo)

# ... resto de parámetros geométricos

def get_section(self) -> Section:
    """Retorna sección configurada."""
    tag = int(self._tag_edit.text())
    name = self._name_edit.text().strip()
    sec_type = SectionType(self._type_combo.currentText())
    material_tag = self._material_combo.currentData()  # ← NUEVO (None o int)
    
    # Recopilar parámetros geométricos
    params = {}
    for param_key, widget in self._param_widgets.items():
        params[param_key] = widget.value()
    
    return Section(
        tag=tag,
        name=name,
        sec_type=sec_type,
        params=params,
        material_tag=material_tag  # ← NUEVO
    )
```

**NOTA:** El diálogo necesita acceso al modelo para listar materiales. Requiere pasar `model` como parámetro al constructor o acceder desde `parent._model`.

---

### Step 2: Auto-Crear Patrón DEAD con Peso Propio en Modelos Nuevos
**Archivos:**
- [gui/core/model_data.py](gui/core/model_data.py) (StructuralModel.__init__ y create_demo)
- [gui/main_window.py](gui/main_window.py) (acción Nuevo Modelo y apertura de archivos)
- [gui/core/project_io.py](gui/core/project_io.py) (notificación al cargar modelos antiguos)

**Qué:**
Modificar `StructuralModel.__init__()` para automáticamente crear un patrón "DEAD" (tag=1) con `self_weight_multiplier=1.0` cuando se inicializa un modelo **nuevo** (no al cargar desde archivo).

Actualizar `create_demo()` para:
1. Incluir el patrón DEAD como primer patrón del modelo demo
2. **Asignar densidades a los materiales** (concreto = 2400 kg/m³)

**MIGRACIÓN DE MODELOS ANTIGUOS:**
Al cargar archivos .opss versión 1.0 (sin `self_weight_multiplier`):
- **NO** crear patrón DEAD automáticamente (preserva comportamiento existente)
- Patrones existentes tendrán `self_weight_multiplier = 0.0` por defecto
- Mostrar notificación en consola: *"ℹ️ Modelo cargado sin patrón DEAD. Considere agregar peso propio para análisis modal confiable."*

**Testing:**
- Crear modelo nuevo → verificar que existe patrón tag=1 con nombre "DEAD" y multiplicador 1.0
- Cargar modelo demo → verificar patrón DEAD presente
- Cargar modelo antiguo (versión 1.0) → NO crear DEAD, mostrar notificación
- Verificar que el árbol del modelo muestra "DEAD" automáticamente en modelos nuevos

**Implementación técnica:**
```python
# En model_data.py
class StructuralModel:
    def __init__(self, ndm: int = 3, ndf: int = 6, auto_create_dead: bool = True) -> None:
        """
        Inicializa modelo estructural.
        
        Parameters
        ----------
        ndm : int
            Número de dimensiones (2 o 3)
        ndf : int
            Grados de libertad por nodo
        auto_create_dead : bool
            Si True, crea patrón DEAD automáticamente (modelos nuevos).
            Si False, no crea DEAD (usado al cargar desde archivo).
        """
        self.ndm = ndm
        self.ndf = ndf
        self.nodes: dict[int, Node] = {}
        self.materials: dict[int, Material] = {}
        self.sections: dict[int, Section] = {}
        self.geom_transfs: dict[int, GeomTransf] = {}
        self.elements: dict[int, Element] = {}
        self.load_patterns: dict[int, LoadPattern] = {}
        
        # ← Auto-crear patrón DEAD con peso propio (solo modelos nuevos)
        if auto_create_dead:
            self.load_patterns[1] = LoadPattern(
                tag=1,
                name="DEAD",
                time_series_type="Linear",
                self_weight_multiplier=1.0,
                loads=[]
            )

    @classmethod
    def from_dict(cls, d: dict) -> "StructuralModel":
        """Crea modelo desde diccionario (NO auto-crear DEAD)."""
        model = cls(
            ndm=d.get("ndm", 3),
            ndf=d.get("ndf", 6),
            auto_create_dead=False  # ← Desactivar auto-creación al cargar
        )
        # ... resto de deserialización
        for k, v in d.get("load_patterns", {}).items():
            model.load_patterns[int(k)] = LoadPattern.from_dict(v)
        return model

    @classmethod
    def create_demo(cls) -> "StructuralModel":
        """Crea un pórtico 3D de demostración."""
        model = cls(ndm=3, ndf=6, auto_create_dead=True)  # ← DEAD se crea automático
        
        # --- Material con DENSIDAD ---
        model.materials[1] = Material(
            tag=1, 
            name="Concreto f'c=28 MPa",
            mat_type=MaterialType.ELASTIC,
            params={"E": 24_821_000.0},  # kN/m²
            density=2400.0  # ← NUEVO: kg/m³
        )
        
        # --- Secciones con MATERIAL_TAG ---
        model.sections[1] = Section(
            tag=1, 
            name="Columna 40×40",
            sec_type=SectionType.ELASTIC_3D,
            params={"A": 0.16, "E": 24_821_000.0,
                    "Iz": 2.1333e-3, "Iy": 2.1333e-3,
                    "G": 10_342_000.0, "J": 3.6053e-3},
            material_tag=1  # ← NUEVO: referencia a Material 1 para densidad
        )
        model.sections[2] = Section(
            tag=2, 
            name="Viga 30×50",
            sec_type=SectionType.ELASTIC_3D,
            params={"A": 0.15, "E": 24_821_000.0,
                    "Iz": 3.125e-3, "Iy": 1.125e-3,
                    "G": 10_342_000.0, "J": 3.516e-3},
            material_tag=1  # ← NUEVO
        )
        
        # ... resto del código demo (nodos, elementos, etc.)
        
        # Nota: DEAD ya existe (auto-creado), solo agregar cargas si necesario
        # model.load_patterns[1].loads.append(...)  # opcional
        
        return model
```

```python
# En project_io.py, función load_model()
def load_model(filepath: str) -> tuple[StructuralModel, str]:
    """
    Carga modelo desde archivo JSON.
    
    Returns
    -------
    tuple[StructuralModel, str]
        Modelo cargado y mensaje de notificación (vacío si no hay notificación).
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    version = data.get("version", "1.0")
    model = StructuralModel.from_dict(data["model"])
    
    notification = ""
    
    # Detectar modelos antiguos sin DEAD
    if version == "1.0" and 1 not in model.load_patterns:
        notification = (
            "ℹ️ Modelo cargado sin patrón DEAD. "
            "Considere agregar peso propio para análisis modal confiable.\n"
            "Puede crear el patrón DEAD desde: Cargas > Nuevo patrón de carga."
        )
    
    return model, notification
```

```python
# En main_window.py, método _open_model()
def _open_model(self) -> None:
    """Abre modelo existente."""
    filepath, _ = QFileDialog.getOpenFileName(
        self, "Abrir modelo", "", "OPynSees files (*.opss)"
    )
    if not filepath:
        return
    
    try:
        model, notification = load_model(filepath)  # ← Recibe notificación
        self._model = model
        self._current_file = filepath
        self._refresh_all()
        
        # Mostrar notificación si existe
        if notification:
            self._console_panel.append(notification)
            QMessageBox.information(self, "Información", notification)
        
    except Exception as e:
        QMessageBox.critical(self, "Error", f"No se pudo cargar el archivo:\n{e}")
```

---

### Step 3: Actualizar Diálogo de Patrón de Carga con Campo Self-Weight
**Archivos:**
- [gui/dialogs/load_pattern_dialog.py](gui/dialogs/load_pattern_dialog.py)
- [gui/main_window.py](gui/main_window.py) (deshabilitar botón "Eliminar" para DEAD)

**Qué:**
Agregar un `QDoubleSpinBox` en el formulario del diálogo para editar el campo `self_weight_multiplier`:
- Etiqueta: "Multiplicador peso propio:"
- Rango: -5.0 a 5.0
- Valor por defecto: 0.0 (excepto DEAD que es 1.0)
- Tooltip: "Factor para incluir peso propio. 1.0 = peso completo, 0.0 = sin peso"

**RESTRICCIONES IMPORTANTES:**
1. **Patrón DEAD (tag=1):** Campo `self_weight_multiplier` **deshabilitado** (read-only) con valor **fijo 1.0**
2. **Eliminar DEAD:** Botón "Eliminar patrón de carga" en `main_window.py` debe estar **deshabilitado** cuando DEAD esté seleccionado en el árbol

**Testing:**
- Crear nuevo patrón de carga y configurar multiplicador a 0.5 → funciona
- Editar patrón DEAD → multiplicador es 1.0 y está bloqueado (grayed out)
- Intentar eliminar DEAD desde árbol → botón deshabilitado
- Guardar y cargar modelo → multiplicador persiste

**Implementación técnica:**
```python
# En LoadPatternDialog.__init__()
self._sw_spinbox = QDoubleSpinBox()
self._sw_spinbox.setRange(-5.0, 5.0)
self._sw_spinbox.setDecimals(2)
self._sw_spinbox.setSingleStep(0.1)
self._sw_spinbox.setValue(pattern.self_weight_multiplier if pattern else 0.0)
self._sw_spinbox.setToolTip(
    "Factor peso propio: 1.0 = completo, 0.0 = sin peso.\n"
    "Permite factorización (ej: 1.2 para sobrecarga)."
)

# ← BLOQUEAR si es DEAD (tag=1)
if pattern and pattern.tag == 1:
    self._sw_spinbox.setReadOnly(True)
    self._sw_spinbox.setEnabled(False)
    self._sw_spinbox.setToolTip("El patrón DEAD siempre tiene multiplicador 1.0 (no editable)")

form.addRow("Multiplicador peso propio:", self._sw_spinbox)

# En get_pattern(), forzar mult=1.0 para DEAD
tag = int(self._tag_edit.text())
mult = 1.0 if tag == 1 else self._sw_spinbox.value()

return LoadPattern(
    tag=tag,
    name=self._name_edit.text().strip(),
    time_series_type=self._ts_combo.currentText(),
    self_weight_multiplier=mult,
    loads=self._editing.loads if self._editing else []
)
```

```python
# En main_window.py, método que maneja botón "Eliminar patrón"
def _delete_load_pattern(self) -> None:
    """Elimina patrón de carga seleccionado."""
    selected = self._model_tree.currentItem()
    if not selected:
        return
    
    # Obtener tag del patrón
    pattern_tag = ...  # extraer de selected
    
    # ← PREVENIR eliminación de DEAD
    if pattern_tag == 1:
        QMessageBox.warning(
            self,
            "No se puede eliminar DEAD",
            "El patrón DEAD (tag=1) es obligatorio y no puede eliminarse.\n"
            "Todos los modelos requieren peso propio para análisis confiable."
        )
        return
    
    # Continuar con eliminación normal...
```

---

### Step 4: Actualizar Generador de Scripts con Cálculo de Masa y Peso Propio
**Archivos:**
- [gui/core/script_generator.py](gui/core/script_generator.py)

**Qué:**
Modificar la generación de scripts para implementar el sistema DEAD con auto-cálculo de masa:

1. **Calcular masa tributaria por nodo** desde elementos conectados (área × espesor × densidad para shells, volumen × densidad para sólidos, peso lineal × longitud para frames)
2. **Generar comandos `ops.mass()`** basados en masa calculada o masa explícita del nodo
3. **Generar cargas gravitacionales** como `masa × 9.81 × self_weight_multiplier` en dirección -Y (2D) o -Z (3D)

**Algoritmo de cálculo de masa:**
```
Para cada nodo:
    masa_tributaria = 0
    Para cada elemento conectado al nodo:
        # Obtener densidad del material asociado a la sección
        section = model.sections[elem.section_tag]
        material = model.materials[section.material_tag]  # ← NUEVO LOOKUP
        density = material.density  # [kg/m³]
        
        Si density == 0:
            continuar  # Skip elemento sin densidad definida
        
        Si elemento es frame/truss:
            peso_elem = A × L × density  # [kg]
            masa_tributaria += peso_elem / n_nodos_elemento
        Si elemento es shell:
            peso_elem = A_shell × espesor × density
            masa_tributaria += peso_elem / n_nodos_elemento
    
    masa_final = max(nodo.mass_explicit, masa_tributaria)
```

**NOTA IMPORTANTE:** 
- **NO hay densidad hardcodeada** — se obtiene desde `Material.density`
- Si un material tiene `density = 0.0`, sus elementos no contribuyen a masa (warning en console)
- Elementos frame/truss: peso = A_sección × longitud × density_material
- Elementos shell: requieren parámetro espesor (futura extensión, usar Section.params si existe)

**Testing:**
- Generar script con DEAD para pórtico 3D → verificar comandos `ops.mass()` correctos
- Ejecutar análisis modal → verificar períodos realistas
- Comparar masa calculada vs masa esperada manualmente
- Verificar cargas gravitacionales = masa × 9.81

**Implementación técnica:**
```python
def _calculate_nodal_masses(model: StructuralModel) -> dict[int, float]:
    """
    Calcula masa tributaria por nodo desde elementos conectados.
    Usa densidad definida en Material asociado a cada sección.
    """
    nodal_masses = {tag: 0.0 for tag in model.nodes.keys()}
    
    for elem in model.elements.values():
        section = model.sections.get(elem.section_tag)
        if not section:
            continue
        
        # Obtener densidad del material asociado
        density = 0.0
        if section.material_tag and section.material_tag in model.materials:
            material = model.materials[section.material_tag]
            density = material.density
        
        if density == 0.0:
            # Skip elemento sin densidad definida
            continue
        
        # Obtener nodos del elemento
        elem_nodes = [elem.node_i, elem.node_j]
        if elem.node_k:
            elem_nodes.append(elem.node_k)
        if elem.node_l:
            elem_nodes.append(elem.node_l)
        
        # Calcular peso elemento según tipo
        if elem.elem_type in [ElementType.ELASTIC_BEAM_COLUMN, 
                               ElementType.FORCE_BEAM_COLUMN,
                               ElementType.DISP_BEAM_COLUMN,
                               ElementType.TRUSS,
                               ElementType.COROT_TRUSS]:
            # Frame/Truss: peso = A × L × densidad
            node_i = model.nodes[elem.node_i]
            node_j = model.nodes[elem.node_j]
            length = ((node_j.x - node_i.x)**2 + 
                     (node_j.y - node_i.y)**2 + 
                     (node_j.z - node_i.z)**2)**0.5
            
            area = section.params.get("A", 0.0)  # m²
            elem_weight = area * length * density  # kg
            
            # Distribuir a nodos (mitad a cada extremo para 2 nodos)
            mass_per_node = elem_weight / len(elem_nodes)
            for node_tag in elem_nodes:
                nodal_masses[node_tag] += mass_per_node
        
        # TODO: Shell elements (requiere parámetro espesor en section.params)
        elif elem.elem_type == ElementType.SHELL_MITC4:
            # Requiere espesor: section.params.get("thickness", 0.0)
            # peso = area_shell × thickness × density
            pass
    
    return nodal_masses

# En generate_script(), ANTES de la sección de patrones de carga
if model.load_patterns:
    # Calcular masas si existe patrón con peso propio
    has_self_weight = any(p.self_weight_multiplier > 0 
                          for p in model.load_patterns.values())
    
    if has_self_weight:
        lines.append("# " + "=" * 58)
        lines.append("# MASAS NODALES (Auto-calculadas desde geometría + densidad)")
        lines.append("# " + "=" * 58)
        
        nodal_masses = _calculate_nodal_masses(model)
        grav_dir = 2 if model.ndm == 3 else 1  # Z para 3D, Y para 2D
        
        for node_tag in sorted(model.nodes.keys()):
            node = model.nodes[node_tag]
            
            # Priorizar masa explícita si existe, sino usar calculada
            if node.mass and len(node.mass) > grav_dir and node.mass[grav_dir] > 0:
                mass_val = node.mass[grav_dir]
            else:
                mass_val = nodal_masses[node_tag]
            
            if mass_val > 0:
                mass_vec = [0.0] * model.ndf
                mass_vec[grav_dir] = mass_val
                mass_args = ", ".join(f"{m:.6f}" for m in mass_vec)
                lines.append(f"ops.mass({node_tag}, {mass_args})")
        lines.append("")

# En sección de patrones de carga
for pat_tag in sorted(model.load_patterns.keys()):
    pat = model.load_patterns[pat_tag]
    ts_tag = pat_tag
    lines.append(f"# Patrón: {pat.name}")
    lines.append(f"ops.timeSeries('{pat.time_series_type}', {ts_tag})")
    lines.append(f"ops.pattern('Plain', {pat_tag}, {ts_tag})")
    
    # Cargas nodales explícitas del patrón
    for load in pat.loads:
        args = f"{load.fx}, {load.fy}, {load.fz}, {load.mx}, {load.my}, {load.mz}"
        lines.append(f"ops.load({load.node_tag}, {args})")
    
    # ← NUEVO: Cargas gravitacionales por peso propio
    if pat.self_weight_multiplier != 0.0:
        lines.append(f"# Peso propio (factor = {pat.self_weight_multiplier})")
        grav_dir = 2 if model.ndm == 3 else 1  # Z para 3D, Y para 2D
        nodal_masses = _calculate_nodal_masses(model)
        
        for node_tag in sorted(model.nodes.keys()):
            node = model.nodes[node_tag]
            
            # Usar masa explícita o calculada
            if node.mass and len(node.mass) > grav_dir and node.mass[grav_dir] > 0:
                mass_val = node.mass[grav_dir]
            else:
                mass_val = nodal_masses[node_tag]
            
            if mass_val > 0:
                grav_force = -mass_val * 9.81 * pat.self_weight_multiplier
                load_vec = [0.0] * model.ndf
                load_vec[grav_dir] = grav_force
                load_args = ", ".join(f"{v:.6f}" for v in load_vec)
                lines.append(f"ops.load({node_tag}, {load_args})")
    
    lines.append("")
```

---

### Step 5: Implementar Validación Pre-Análisis
**Archivos:**
- [gui/dialogs/analysis_dialog.py](gui/dialogs/analysis_dialog.py) (nuevo método `_validate_model()`)

**Qué:**
Crear método privado `_validate_model(analysis_type: str) -> tuple[bool, str]` que valida:

**Para Análisis Estático:**
1. Modelo tiene ≥ 1 nodo
2. Modelo tiene ≥ 1 elemento
3. Existe ≥ 1 patrón de carga
4. Al menos 1 nodo tiene restricción (is_fixed)
5. Todos los elementos referencian nodos existentes
6. Todos los elementos tienen section_tag y transf_tag válidos

**Para Análisis Modal:**
1. Modelo tiene ≥ 1 nodo
2. Modelo tiene ≥ 1 elemento
3. **CRÍTICO:** Verificar que exista patrón DEAD (tag=1) con mult=1.0 **O** que al menos 1 nodo tenga masa explícita
4. Si no hay masas ni DEAD, mostrar error: "Análisis modal requiere masa. Cree nodos con masa o asegúrese que existe el patrón DEAD con peso propio."
5. Todos los elementos referencian nodos existentes

Llamar `_validate_model()` antes de iniciar `AnalysisWorker`. Si retorna `False`, mostrar mensaje de error en consola y no iniciar análisis.

**Testing:**
- Intentar análisis estático sin nodos → error
- Intentar análisis modal sin DEAD ni masas → error
- Intentar análisis con elemento huérfano (nodo inexistente) → error
- Modelo válido → análisis ejecuta correctamente

**Implementación técnica:**
```python
def _validate_model(self, analysis_type: str) -> tuple[bool, str]:
    """Valida modelo antes de análisis. Retorna (ok, msg_error)."""
    if not self._model.nodes:
        return False, "El modelo no tiene nodos definidos."
    
    if not self._model.elements:
        return False, "El modelo no tiene elementos definidos."
    
    # Validar conectividad de elementos
    for elem_tag, elem in self._model.elements.items():
        if elem.node_i not in self._model.nodes:
            return False, f"Elemento {elem_tag} referencia nodo inexistente {elem.node_i}."
        if elem.node_j not in self._model.nodes:
            return False, f"Elemento {elem_tag} referencia nodo inexistente {elem.node_j}."
        # Shell elements Node K, L...
        if elem.node_k and elem.node_k not in self._model.nodes:
            return False, f"Elemento {elem_tag} referencia nodo inexistente {elem.node_k}."
        if elem.node_l and elem.node_l not in self._model.nodes:
            return False, f"Elemento {elem_tag} referencia nodo inexistente {elem.node_l}."
    
    if analysis_type == "static":
        if not self._model.load_patterns:
            return False, "Análisis estático requiere al menos un patrón de carga."
        
        has_support = any(n.is_fixed for n in self._model.nodes.values())
        if not has_support:
            return False, "El modelo no tiene nodos restringidos (apoyos)."
    
    elif analysis_type == "modal":
        # Verificar masa: debe tener DEAD o nodos con masa explícita
        has_dead = 1 in self._model.load_patterns and \
                   self._model.load_patterns[1].self_weight_multiplier > 0
        has_mass = any(n.mass and any(m > 0 for m in n.mass) 
                       for n in self._model.nodes.values())
        
        if not has_dead and not has_mass:
            return False, (
                "Análisis modal requiere masa en los nodos.\n"
                "Asegúrese que existe el patrón DEAD con peso propio (multiplicador > 0) "
                "o asigne masa explícita a los nodos."
            )
    
    return True, ""

# En _run_analysis():
ok, error_msg = self._validate_model(self._analysis_type)
if not ok:
    self._console.append(f"❌ ERROR: {error_msg}")
    return
```

---

### Step 6: Proteger Campos Read-Only en Panel de Propiedades
**Archivos:**
- [gui/panels/properties_panel.py](gui/panels/properties_panel.py)

**Qué:**
Ampliar la constante `READ_ONLY_FIELDS` para incluir:
- `"tag"` (ya existe)
- `"elem_type"`, `"mat_type"`, `"sec_type"`, `"transf_type"` (ya existen)
- **NUEVO:** `"time_series_type"` (debe editarse desde el diálogo, no inline)

Modificar el método `_populate_fields()` para que los widgets de los campos read-only se creen como `QLabel` en lugar de `QLineEdit`, evitando edición accidental.

**Alternativa:** Usar `QLineEdit` pero llamar `setReadOnly(True)` y aplicar estilo visual diferenciador (fondo gris claro).

**Testing:**
- Seleccionar nodo en árbol → campo "Tag" no es editable
- Seleccionar material → campo "Tipo de material" no es editable
- Seleccionar patrón de carga → campo "Time Series" no es editable
- Intentar editar campos normales (nombre, coordenadas) → funciona correctamente

**Implementación técnica:**
```python
READ_ONLY_FIELDS = {
    "tag", 
    "elem_type", 
    "mat_type", 
    "sec_type", 
    "transf_type",
    "time_series_type"  # ← NUEVO
}

# En _populate_fields()
for key, value in sorted(obj_dict.items()):
    if key.startswith("_"):
        continue
    
    label_text = HUMAN_LABELS.get(key, key.replace("_", " ").title())
    
    if key in READ_ONLY_FIELDS:
        # Campo read-only: usar QLabel con estilo
        value_widget = QLabel(str(value))
        value_widget.setStyleSheet("QLabel { color: gray; font-style: italic; }")
    else:
        # Campo editable normal
        if isinstance(value, (int, float)):
            value_widget = QDoubleSpinBox()
            # ... configuración spinbox
        else:
            value_widget = QLineEdit(str(value))
            # ... configuración lineedit
    
    self._form_layout.addRow(label_text, value_widget)
```

---

### Step 7: Remover Lógica de Auto-Mass Silenciosa en analysis_runner.py
**Archivos:**
- [gui/core/analysis_runner.py](gui/core/analysis_runner.py)

**Qué:**
Eliminar el código que automáticamente asigna masa unitaria (1.0) a nodos sin masa en `run_modal_analysis()` (línea ~93). Con el nuevo sistema DEAD, la masa se calcula desde el peso propio, haciendo innecesaria esta asignación.

**IMPORTANTE:** Si después de validación el modelo tiene DEAD con mult>0, el script generado ya incluirá masas implícitas vía peso propio. No es necesario asignar masa adicional.

**Testing:**
- Ejecutar análisis modal con DEAD presente → análisis exitoso
- Ejecutar análisis modal sin DEAD ni masas → validación lo bloquea (Step 5)
- Verificar que log de análisis no muestra mensaje "Asignando masa unitaria..."

**Implementación técnica:**
```python
# En run_modal_analysis(), REMOVER estas líneas:
# for node_tag, node in model.nodes.items():
#     if not node.mass or all(m == 0 for m in node.mass):
#         script_lines.append(f"ops.mass({node_tag}, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0)")

# Comentario nuevo:
# Las masas se obtienen automáticamente del patrón DEAD mediante peso propio.
# La validación pre-análisis (Step 5) asegura que existe DEAD o masas explícitas.
```

---

## Testing Strategy

### Pruebas Unitarias (Manual)
1. **Modelo Nuevo:** Crear modelo → verificar patrón DEAD existe → tag=1, mult=1.0
2. **Compatibilidad:** Cargar archivo .opss antiguo → verificar default mult=0.0 en patrones
3. **Diálogo LoadPattern:** Crear patrón con mult=0.5 → guardar → cargar → verificar persistencia
4. **Validación Estática:** Modelo vacío → intentar análisis → ver error descriptivo
5. **Validación Modal:** Modelo sin DEAD ni masas → intentar análisis → ver error descriptivo
6. **Script Generation:** Modelo con DEAD → exportar script → verificar cargas gravitacionales
7. **Properties Panel:** Seleccionar objetos → verificar tags/tipos no editables

### Pruebas de Integración
1. **Workflow Completo:**
   - Crear modelo nuevo
   - Agregar nodos con masa
   - Agregar elementos
   - Ejecutar análisis modal → verificar resultados coherentes
   - Guardar modelo
   - Cargar modelo
   - Re-ejecutar análisis → resultados idénticos

2. **SAP2000 Parity Check:**
   - Crear pórtico 3D simple en OPynSees2000 con DEAD
   - Crear mismo pórtico en SAP2000 con DEAD
   - Comparar períodos modales → verificar coincidencia (±5%)

### Casos de Borde
1. Modelo con DEAD vacío (sin cargas nodales) pero mult=1.0 → análisis modal debe funcionar
2. Modelo con 2 patrones: DEAD (mult=1) + LIVE (mult=0) → análisis estático debe considerar ambos
3. Editar patrón DEAD → campo mult debe estar bloqueado

---

## Design Decisions (Approved)

### ✅ Decisión 1: Cálculo de Masa desde Peso Propio
**Elección:** Opción A - Auto-calcular masa nodal (mejorada con densidad parametrizada)

Al encontrar patrón DEAD (o cualquier patrón con `self_weight_multiplier > 0`), el script generator calculará automáticamente la masa nodal tributaria desde los elementos conectados:

```
masa_nodo = (suma_peso_elementos_conectados / 9.81) × self_weight_multiplier
peso_elemento = Area × Longitud × densidad_material
```

**Implementación robusta:**
- **Densidad parametrizada:** Campo `Material.density` [kg/m³] configurable por usuario
- **Linkage Section-Material:** Campo `Section.material_tag` opcional referencia al Material para obtener densidad
- **Sin valores hardcodeados:** Cada material puede tener densidad diferente (concreto 2400, acero 7850, etc.)
- **Script generation:** Comandos `ops.mass()` generados automáticamente antes de cargas gravitacionales

Máxima similitud con SAP2000 + flexibilidad para materiales heterogéneos.

---

### ✅ Decisión 2: Dirección de Gravedad
**Elección:** Opción A - Hardcodear convención estructuras

- **2D (ndm=2):** Gravedad en eje **-Y**
- **3D (ndm=3):** Gravedad en eje **-Z** (vertical hacia abajo)

Implementación simple sin campos adicionales. Convención estándar para edificios y pórticos.

---

### ✅ Decisión 3: Modificación del Patrón DEAD
**Elección:** Opción C - DEAD editable pero `self_weight_multiplier` fijo

- Usuarios **pueden** editar: nombre del patrón, cargas nodales adicionales
- Usuarios **NO pueden** editar: `self_weight_multiplier` (bloqueado en 1.0)
- Usuarios **NO pueden** eliminar el patrón DEAD (tag=1 reservado)

Botón "Eliminar" en UI estará deshabilitado cuando DEAD esté seleccionado. Balance entre usabilidad y seguridad.

---

### ✅ Decisión 4: Múltiples Patrones con Peso Propio
**Elección:** SÍ - Permitir flexibilidad total

Usuarios pueden crear patrones adicionales con `self_weight_multiplier ≠ 0` (ej: "DEAD+Equipment" con mult=1.2, "DEAD_Partial" con mult=0.5).

Útil para factorización de cargas y casos de carga especiales. No se aplica restricción.

---

### ✅ Decisión 5: Migración de Modelos Antiguos
**Elección:** Opción B - Preservar comportamiento existente

Al cargar archivos .opss sin `self_weight_multiplier`:
- **NO** crear patrón DEAD automáticamente
- Aplicar `self_weight_multiplier = 0.0` por defecto a patrones existentes
- Mostrar notificación en consola: "ℹ️ Modelo cargado sin patrón DEAD. Considere agregar peso propio para análisis modal."

Preserva resultados de análisis anteriores. Usuario no tiene modelos legacy, así que esto solo afecta compatibilidad futura.

---

## Notes

- **Versionado de Archivos:** Incrementar versión de formato .opss a `"2.0"` para detectar modelos con/sin `self_weight_multiplier`, `density` y `material_tag`.
- **Undo/Redo:** LoadPattern es objeto mutable en diccionario. Los cambios en `load_patterns` deben usar `DictChangeCommand` del undo_manager.
- **Localización:** Todos los mensajes de error en español (ya consistente con codebase).
- **Performance:** Validación pre-análisis es O(n) en nodos/elementos. Aceptable para modelos <10,000 elementos.
- **Densidad Parametrizada:** Campo `density` en Material permite materiales heterogéneos (concreto, acero, madera) en mismo modelo.
- **Section-Material Linkage:** Campo `material_tag` en Section permite asociar opcionalmente un material para obtener densidad. Si es `None`, el elemento no contribuye a masa automática.
- **Shell Elements:** Cálculo de masa para shells requiere parámetro `thickness` en `section.params` (extensión futura).
- **DEAD Inmutable:** Tag 1 siempre reservado para DEAD. UI debe prevenir eliminación y cambio de multiplicador.
- **Compatibilidad Backward:** Archivos versión 1.0 se cargan correctamente con defaults: `self_weight_multiplier=0.0`, `density=0.0`, `material_tag=None`.
- **Múltiples Patrones con Peso:** Permitido crear múltiples patrones con `mult > 0` (ej: DEAD_Partial=0.5, DEAD_Equipment=1.2).
- **Gravedad Hardcodeada:** 2D usa -Y, 3D usa -Z. Sin configuración de usuario (decisión simplificadora).
- **Warnings en Console:** Si un elemento tiene `section.material_tag=None` o `material.density=0`, no contribuye a masa (puede generar warning en validación).

---

## Success Criteria

✅ Modelo nuevo automáticamente tiene patrón DEAD (tag=1, mult=1.0)  
✅ Diálogo LoadPattern permite configurar multiplicador de peso propio  
✅ Campo mult del patrón DEAD está bloqueado (read-only)  
✅ Análisis estático valida existencia de nodos, elementos, cargas, apoyos  
✅ Análisis modal valida existencia de masa (DEAD o explícita)  
✅ Script generado incluye cargas gravitacionales basadas en masa × 9.81 × mult  
✅ Panel de propiedades bloquea edición de tags y tipos  
✅ Auto-mass silenciosa removida de analysis_runner.py  
✅ Archivos .opss antiguos se cargan con compatibilidad hacia atrás  
✅ Tests manuales pasan en workflow completo (crear → analizar → guardar → cargar)  

---

## Timeline Estimate

| Step | Complejidad | Tiempo Estimado |
|------|-------------|-----------------|
| 1. Model data fields (LoadPattern + Material + Section) | Media | 50 min |
| 1.5. Diálogo Material + density UI | Media | 45 min |
| 1.6. Diálogo Section + material_tag UI | Media | 40 min |
| 2. Auto-crear DEAD + migración | Media | 45 min |
| 3. Diálogo LoadPattern + protección DEAD | Media | 60 min |
| 4. Script generation + cálculo masa desde densidad | **Alta** | **120 min** |
| 5. Validación pre-análisis | Media | 60 min |
| 6. Properties panel read-only | Baja | 30 min |
| 7. Remover auto-mass | Baja | 15 min |
| **Testing completo** | | 120 min |
| **TOTAL** | | **~9.5 horas** |

**Nota:** Tiempo aumentó 1.5h por Steps 1.5 y 1.6 (UI para density y material_tag). Arquitectura más robusta que versión hardcodeada.

---

## Additional Considerations

### Cambios Futuros (No en este PR)
- Distributed element loads (Step 4 requiere infraestructura de carga distribuida)
- Load combinations (combinar múltiples patrones con factores)
- Response spectrum analysis (requiere integración modal + espectro)
- Time-history analysis (requiere acelerogramas + integrador Newmark)

### Documentación a Actualizar
- [docs/06-cargas.md](docs/06-cargas.md) — Explicar campo self_weight_multiplier
- [docs/08-analisis-modal.md](docs/08-analisis-modal.md) — Explicar masa desde DEAD
- [docs/11-buenas-practicas.md](docs/11-buenas-practicas.md) — Recomendar siempre usar DEAD

### SAP2000 Feature Parity Status
Después de este PR:
- ✅ Auto-create DEAD pattern
- ✅ Self-weight multiplier
- ✅ Pre-analysis validation
- ❌ Distributed loads (futuro)
- ❌ Load combinations (futuro)
- ❌ Response spectrum wizard (futuro)
