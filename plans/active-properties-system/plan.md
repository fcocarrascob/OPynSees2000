# Sistema de Propiedades Activas con Panel de Propiedades (Properties-Panel Based Active System)

**Branch:** `feature/drawing-properties-panel`
**Description:** Aprovechar el Panel de Propiedades para configurar las propiedades de elementos Frame/Shell ANTES de dibujarlos, eliminando el flujo "dibujar → editar"

## Goal
Transformar el Panel de Propiedades en un **editor pre-creación** cuando se activan los modos de dibujo (DRAW_FRAME, DRAW_SHELL). Similar a SAP2000 donde configuras las propiedades del elemento antes de dibujarlo en el viewport.

**Flujo de trabajo nuevo:**
1. Usuario activa "Dibujar Frame" 
2. Panel de Propiedades muestra: "**Propiedades del Frame a Crear**"
3. Usuario selecciona: Sección, Transformación, Tipo de Elemento
4. Usuario dibuja 2-clicks → Frame se crea con esas propiedades
5. Continúa dibujando más frames con las mismas propiedades

**Impacto UX:** Reduce la creación de un frame de 4 pasos a 1 paso. 100 frames con misma sección: 400 clicks → 100 clicks (75% reducción).

---

## Implementation Steps

### Step 1: Drawing Template Data Model
**Files:** 
- `gui/core/model_data.py`

**What:** 
Agregar clase `DrawingTemplate` a `StructuralModel` para almacenar propiedades pre-dibujo:
```python
@dataclass
class DrawingTemplate:
    """Plantilla de propiedades para nuevos elementos."""
    # Para Frames
    frame_section_tag: Optional[int] = None
    frame_transf_tag: Optional[int] = None
    frame_elem_type: ElementType = ElementType.ELASTIC_BEAM_COLUMN
    
    # Para Shells
    shell_section_tag: Optional[int] = None
    shell_thickness: float = 0.2  # metros
    
    # Para Loads (usado en modo asignación rápida - futuro)
    active_load_pattern_tag: int = 1  # Default to DEAD
```

Agregar instancia a `StructuralModel`:
```python
@dataclass
class StructuralModel:
    # ... campos existentes ...
    drawing_template: DrawingTemplate = field(default_factory=DrawingTemplate)
```

**Testing:** 
- Crear modelo → verificar que `model.drawing_template` existe
- Cambiar `drawing_template.frame_section_tag = 5` → verificar que se mantiene
- Verificar valores default

---

### Step 2: Properties Panel - Drawing Mode View
**Files:**
- `gui/panels/properties_panel.py`

**What:**
Agregar método `show_drawing_template()` que muestra formulario editable de propiedades pre-creación:

```python
def show_drawing_template(
    self, 
    model: "StructuralModel", 
    mode: str  # "frame" o "shell"
) -> None:
    """Muestra propiedades editables para elementos a crear."""
    template = model.drawing_template
    
    # Limpiar layout actual
    self._clear_layout()
    
    # Título
    title_text = "Propiedades del Frame a Crear" if mode == "frame" else "Propiedades del Shell a Crear"
    title = QLabel(title_text)
    title.setStyleSheet("font-weight: bold; font-size: 13px; padding: 6px 0; color: #1976D2;")
    self._layout.addWidget(title)
    
    # Info box
    info = QLabel("Los elementos dibujados usarán estas propiedades")
    info.setStyleSheet("color: #757575; font-size: 11px; padding: 4px; background: #E3F2FD; border-radius: 3px;")
    info.setWordWrap(True)
    self._layout.addWidget(info)
    
    # Formulario
    grp = QGroupBox("Configuración")
    form = QFormLayout()
    grp.setLayout(form)
    
    if mode == "frame":
        # Dropdown: Tipo de Elemento
        combo_type = QComboBox()
        for elem_type in [ElementType.ELASTIC_BEAM_COLUMN, 
                          ElementType.FORCE_BEAM_COLUMN, 
                          ElementType.DISP_BEAM_COLUMN,
                          ElementType.TRUSS,
                          ElementType.COROT_TRUSS]:
            combo_type.addItem(elem_type.value, elem_type)
        current_idx = combo_type.findData(template.frame_elem_type)
        if current_idx >= 0:
            combo_type.setCurrentIndex(current_idx)
        combo_type.currentIndexChanged.connect(
            lambda: self._on_template_type_changed(model, combo_type)
        )
        form.addRow("Tipo de Elemento:", combo_type)
        
        # Dropdown: Sección (poblado dinámicamente)
        combo_section = QComboBox()
        combo_section.addItem("(Sin asignar)", None)
        for tag, section in model.sections.items():
            display = f"{section.name} [{section.sec_type.value}]"
            combo_section.addItem(display, tag)
        if template.frame_section_tag:
            idx = combo_section.findData(template.frame_section_tag)
            if idx >= 0:
                combo_section.setCurrentIndex(idx)
        combo_section.currentIndexChanged.connect(
            lambda: self._on_template_section_changed(model, combo_section)
        )
        form.addRow("Sección:", combo_section)
        
        # Dropdown: Transformación
        combo_transf = QComboBox()
        combo_transf.addItem("(Sin asignar)", None)
        for tag, transf in model.geom_transfs.items():
            display = f"Tag {tag} [{transf.transf_type.value}]"
            combo_transf.addItem(display, tag)
        if template.frame_transf_tag:
            idx = combo_transf.findData(template.frame_transf_tag)
            if idx >= 0:
                combo_transf.setCurrentIndex(idx)
        combo_transf.currentIndexChanged.connect(
            lambda: self._on_template_transf_changed(model, combo_transf)
        )
        form.addRow("Transformación:", combo_transf)
        
    elif mode == "shell":
        # Similar para shells...
        combo_section = QComboBox()
        combo_section.addItem("(Sin asignar)", None)
        for tag, section in model.sections.items():
            if section.sec_type in [SectionType.SHELL_SECTION]:  # Filtrar solo shells
                display = f"{section.name} [{section.sec_type.value}]"
                combo_section.addItem(display, tag)
        # ... conectar a callback
        form.addRow("Sección:", combo_section)
        
        spin_thick = QDoubleSpinBox()
        spin_thick.setDecimals(3)
        spin_thick.setRange(0.001, 10.0)
        spin_thick.setValue(template.shell_thickness)
        spin_thick.setSuffix(" m")
        spin_thick.editingFinished.connect(
            lambda: self._on_template_thickness_changed(model, spin_thick.value())
        )
        form.addRow("Espesor:", spin_thick)
    
    self._layout.addWidget(grp)
    
    # Hint para crear secciones si no hay
    if not model.sections:
        hint = QLabel("⚠️ No hay secciones definidas.\nCrea una en Definir → Sección")
        hint.setStyleSheet("color: #F57C00; padding: 10px; background: #FFF3E0; border-radius: 3px;")
        hint.setWordWrap(True)
        self._layout.addWidget(hint)
    
    self._layout.addStretch()
```

**Callbacks para actualizar template:**
```python
def _on_template_type_changed(self, model, combo):
    model.drawing_template.frame_elem_type = combo.currentData()

def _on_template_section_changed(self, model, combo):
    model.drawing_template.frame_section_tag = combo.currentData()

def _on_template_transf_changed(self, model, combo):
    model.drawing_template.frame_transf_tag = combo.currentData()

def _on_template_thickness_changed(self, model, value):
    model.drawing_template.shell_thickness = value
```

**Testing:**
- Activar modo Select → Properties Panel muestra placeholder "Seleccione un ítem"
- Activar modo "Dibujar Frame" → Properties Panel muestra "Propiedades del Frame a Crear" con dropdowns
- Cambiar Sección a IPE300 → verificar que `model.drawing_template.frame_section_tag` actualiza
- Cambiar Tipo a "forceBeamColumn" → verificar actualización

---

### Step 3: MainWindow - Trigger Panel Update on Mode Change
**Files:**
- `gui/main_window.py`

**What:**
Modificar método `set_mode()` para actualizar el Properties Panel según el modo:

```python
def set_mode(self, mode: InteractionMode) -> None:
    """Cambia el modo de interacción activo."""
    # ... código existente ...
    
    # Actualizar Properties Panel según modo
    if mode == InteractionMode.DRAW_FRAME:
        self._properties_panel.show_drawing_template(self._model, "frame")
    elif mode == InteractionMode.DRAW_SHELL:
        self._properties_panel.show_drawing_template(self._model, "shell")
    elif mode == InteractionMode.SELECT:
        # Volver a placeholder
        self._properties_panel.clear()  # Nuevo método para limpiar y mostrar placeholder
        
    # ... resto del código ...
```

Agregar método `clear()` a `PropertiesPanel`:
```python
def clear(self) -> None:
    """Limpia el panel y muestra el placeholder."""
    self._current_item = None
    self._current_category = ""
    self._current_tag = 0
    self._clear_layout()
    self._layout.addWidget(self._placeholder)
```

**Testing:**
- Cambiar de modo SELECT → DRAW_FRAME → verificar que panel muestra propiedades
- Cambiar DRAW_FRAME → SELECT → verificar que panel vuelve a placeholder
- Cambiar DRAW_FRAME → DRAW_SHELL → verificar cambio de formulario

---

### Step 4: Integration with Frame Drawing
**Files:**
- `gui/main_window.py` (método `_handle_draw_frame()`)

**What:**
Modificar `_handle_draw_frame()` para usar valores del `drawing_template` al crear elementos:

```python
def _handle_draw_frame(self, x: float, y: float, z: float) -> None:
    """Maneja clics en modo DRAW_FRAME (2 clics)."""
    # ... código existente de snap y creación de nodos ...
    
    # SEGUNDO CLIC: crear frame
    if self._frame_first_node is not None:
        # ... código de creación de node_j ...
        
        # === OBTENER PROPIEDADES DEL TEMPLATE ===
        template = self._model.drawing_template
        section_tag = template.frame_section_tag
        transf_tag = template.frame_transf_tag
        elem_type = template.frame_elem_type
        
        # Validación: avisar si no hay sección/transf (opcional: permitir crear igual)
        if section_tag is None:
            self._console.log("⚠️ Advertencia: Frame sin sección asignada (editar después)")
        if transf_tag is None and elem_type not in [ElementType.TRUSS, ElementType.COROT_TRUSS]:
            self._console.log("⚠️ Advertencia: Frame sin transformación (editar después)")
        
        # Crear elemento con propiedades del template
        elem_tag = self._model.next_element_tag()
        element = Element(
            tag=elem_tag,
            elem_type=elem_type,
            node_i=self._frame_first_node,
            node_j=node_j_tag,
            section_tag=section_tag,  # ← DESDE TEMPLATE
            transf_tag=transf_tag,    # ← DESDE TEMPLATE
        )
        
        # ... resto del código de undo command ...
        
        self._console.log_success(
            f"Frame {elem_tag} creado: [{self._frame_first_node}→{node_j_tag}] "
            f"{elem_type.value} — Sección: {section_tag or 'N/A'}"
        )
```

**Testing:**
- Configurar template: Sección=IPE300, Transf=1, Tipo=elasticBeamColumn
- Dibujar frame (2 clicks)
- Verificar en model tree que elemento tiene section_tag correcto
- Verificar en console log que muestra "Sección: 1" (no "N/A")
- Dibujar 5 frames más → verificar que todos usan las mismas propiedades
- Cambiar sección en panel → dibujar otro frame → verificar que usa nueva sección

---

### Step 5: Integration with Shell Drawing
**Files:**
- `gui/main_window.py` (método `_handle_draw_shell()`)

**What:**
Similar al Step 4, modificar `_handle_draw_shell()` para usar `drawing_template.shell_section_tag`:

```python
def _handle_draw_shell(self, x: float, y: float, z: float) -> None:
    # ... código de 4 clics ...
    
    # CUARTO CLIC: crear shell
    if len(self._shell_nodes) == 3:
        # ... código de node L ...
        
        # Obtener propiedades del template
        template = self._model.drawing_template
        section_tag = template.shell_section_tag
        
        if section_tag is None:
            self._console.log("⚠️ Advertencia: Shell sin sección asignada")
        
        elem_tag = self._model.next_element_tag()
        element = Element(
            tag=elem_tag,
            elem_type=ElementType.SHELL_MITC4,
            node_i=self._shell_nodes[0],
            node_j=self._shell_nodes[1],
            node_k=self._shell_nodes[2],
            node_l=self._shell_nodes[3],
            section_tag=section_tag,  # ← DESDE TEMPLATE
            transf_tag=None,
        )
        
        # ... resto del código ...
```

**Testing:**
- Activar modo Shell
- Configurar sección en panel
- Dibujar shell (4 clicks)
- Verificar que shell tiene section_tag correcto

---

### Step 6: Visual Feedback in Status Bar
**Files:**
- `gui/main_window.py`

**What:**
Actualizar status bar para mostrar propiedades activas cuando está en modo dibujo:

```python
def set_mode(self, mode: InteractionMode) -> None:
    # ... código existente ...
    
    if mode == InteractionMode.DRAW_FRAME:
        # ... viewport config ...
        template = self._model.drawing_template
        section_name = "(sin asignar)"
        if template.frame_section_tag:
            sec = self._model.sections.get(template.frame_section_tag)
            if sec:
                section_name = sec.name
        
        transf_name = "(sin asignar)"
        if template.frame_transf_tag:
            transf_name = f"Tag {template.frame_transf_tag}"
        
        snap = self._snap_mgr.status_text()
        self.statusBar().showMessage(
            f"Modo: Dibujar Frame  |  {snap}  |  "
            f"📐 Sección: {section_name}  |  Transf: {transf_name}  |  "
            f"Escape → Selección"
        )
```

**Testing:**
- Configurar sección IPE300
- Ver en status bar: "📐 Sección: IPE300 | Transf: Tag 1"
- Cambiar sección → ver actualización inmediata en status bar

---

### Step 7: Persistence in Project Files
**Files:**
- `gui/core/project_io.py`
- `gui/core/model_data.py`

**What:**
Agregar serialización de `drawing_template` en archivos `.opss`:

**En `DrawingTemplate`:**
```python
def to_dict(self) -> dict:
    return {
        "frame_section_tag": self.frame_section_tag,
        "frame_transf_tag": self.frame_transf_tag,
        "frame_elem_type": self.frame_elem_type.value if self.frame_elem_type else None,
        "shell_section_tag": self.shell_section_tag,
        "shell_thickness": self.shell_thickness,
        "active_load_pattern_tag": self.active_load_pattern_tag,
    }

@classmethod
def from_dict(cls, data: dict) -> "DrawingTemplate":
    elem_type_str = data.get("frame_elem_type")
    elem_type = ElementType(elem_type_str) if elem_type_str else ElementType.ELASTIC_BEAM_COLUMN
    
    return cls(
        frame_section_tag=data.get("frame_section_tag"),
        frame_transf_tag=data.get("frame_transf_tag"),
        frame_elem_type=elem_type,
        shell_section_tag=data.get("shell_section_tag"),
        shell_thickness=data.get("shell_thickness", 0.2),
        active_load_pattern_tag=data.get("active_load_pattern_tag", 1),
    )
```

**En `StructuralModel.to_dict()`:**
```python
def to_dict(self) -> dict:
    return {
        # ... campos existentes ...
        "drawing_template": self.drawing_template.to_dict(),
    }
```

**En `StructuralModel.from_dict()`:**
```python
@classmethod
def from_dict(cls, data: dict) -> "StructuralModel":
    # ... código existente ...
    
    drawing_template = DrawingTemplate.from_dict(
        data.get("drawing_template", {})
    )
    
    return cls(
        # ... campos existentes ...
        drawing_template=drawing_template,
    )
```

**Testing:**
- Configurar propiedades: Sección=IPE300, Transf=1
- Guardar proyecto
- Cerrar aplicación
- Abrir proyecto
- Activar modo "Dibujar Frame"
- Verificar que panel muestra IPE300 y Transf 1

---

### Step 8: Smart Defaults and Auto-Refresh
**Files:**
- `gui/main_window.py`
- `gui/panels/properties_panel.py`

**What:**
**Auto-refresh panel cuando se crean secciones/transformaciones nuevas:**

En `_on_define_section()`, después de crear sección:
```python
# Si hay solo 1 sección y template no tiene sección, auto-asignar
if len(self._model.sections) == 1:
    self._model.drawing_template.frame_section_tag = sec.tag
    self._console.log(f"✓ Sección {sec.name} auto-seleccionada para dibujo")

# Si estamos en modo DRAW_FRAME, actualizar panel para reflejar nueva sección
if self._interaction_mode == InteractionMode.DRAW_FRAME:
    self._properties_panel.show_drawing_template(self._model, "frame")
```

Similar para transformaciones.

**Testing:**
- Activar "Dibujar Frame" (sin secciones)
- Crear sección IPE300 desde menú
- Verificar que panel se actualiza y muestra IPE300 en dropdown
- Verificar mensaje "✓ Sección IPE300 auto-seleccionada"

---

## Impact Summary

### Comparación de Workflow

| **Tarea** | **Antes** | **Después** | **Mejora** |
|-----------|-----------|-------------|------------|
| Crear 1 frame con sección | Dibujar (2 clicks) → Properties Panel → F2 → Seleccionar → Enter (7 clicks) | Configurar sección (2 clicks) → Dibujar (2 clicks) = **4 clicks** | **43% reducción** |
| Crear 100 frames con misma sección | 100 × 7 = **700 clicks** | 2 + (100 × 2) = **202 clicks** | **71% reducción** |
| Cambiar sección y crear 20 frames | 20 × 7 = **140 clicks** | 2 + (20 × 2) = **42 clicks** | **70% reducción** |

### Ventajas sobre el Plan Original (Toolbar)

✅ **Reutiliza UI existente**: No agrega toolbar adicional, panel ya existe  
✅ **Más espacio**: Panel tiene más espacio vertical para formularios complejos  
✅ **Contextual**: Panel solo muestra opciones relevantes al modo actual  
✅ **Flujo natural**: "Configurar → Dibujar" es más intuitivo que "Toolbar siempre visible"  
✅ **Feedback visual claro**: Título del panel dice "Propiedades del Frame **a Crear**"  
✅ **Extensible**: Fácil agregar más propiedades por modo (ej: material, color, layer)

### UX similar a SAP2000
✅ Pre-selección de propiedades antes de dibujar  
✅ Elementos creados instantáneamente correctos (sin post-edición)  
✅ Persistencia de configuración entre sesiones  
✅ Smart defaults (auto-seleccionar única sección)  
✅ Feedback en status bar
