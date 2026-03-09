# Menú Contextual y Asignación Rápida (Quick-Assign Context Menu)

**Branch:** `feature/quick-assign-context-menu`
**Description:** Implementar menú contextual (right-click) y herramientas de asignación rápida para operaciones comunes sin abrir diálogos

## Goal
Reducir clicks necesarios para operaciones frecuentes mediante menú contextual inteligente y modos de "pintar propiedades". Similar a SAP2000: click derecho en nodo → "Assign Restraint → Fixed" (2 clicks vs 5+ del flujo actual).

**Impacto UX:** Operaciones comunes (fixity, loads, section change) reducidas de 5-7 clicks a 2-3 clicks.

---

## Implementation Steps

### Step 1: Context Menu Infrastructure
**Files:**
- `gui/viewport/vtk_widget.py`

**What:**
Implementar `contextMenuEvent(event)` en `VTKViewport`:
1. Detectar si hay selección actual (`self.selected_node` o `self.selected_element`)
2. Crear `QMenu` contextual dinámico basado en lo seleccionado:
   - **Si Node seleccionado:**
     - "Asignar Restricción >" (submenu con presets: Empotrado, Articulado, Rodillo X/Y/Z, Libre)
     - "Aplicar Carga..." (abre `NodalLoadDialog` pre-configurado)
     - "Editar Propiedades" (abre en Properties panel o dialog)
     - "Eliminar Nodo"
   - **Si Element seleccionado:**
     - "Cambiar Sección >" (submenu con secciones existentes)
     - "Cambiar Tipo >" (submenu con tipos válidos)
     - "Copiar Propiedades" (activa modo Property Painter)
     - "Editar Elemento"
     - "Eliminar Elemento"
   - **Si no hay selección:**
     - "Seleccionar Todo"
     - "Deseleccionar"

3. Conectar acciones a handlers: `on_context_assign_fixity()`, `on_context_change_section()`, etc.

**Testing:**
- Right-click en nodo → ver menú con opciones de nodo
- Right-click en elemento → ver menú con opciones de elemento
- Right-click en vacío → ver menú general
- Seleccionar opción → ejecutar acción correspondiente

---

### Step 2: Quick Fixity Assignment (Context Menu)
**Files:**
- `gui/viewport/vtk_widget.py`
- `gui/core/undo_manager.py`

**What:**
Implementar submenu "Asignar Restricción":
- Al seleccionar preset (ej: "Empotrado"):
  ```python
  def on_context_assign_fixity(self, preset_name):
      node_tag = self.selected_node
      fixity_map = {
          'Empotrado': (1,1,1,1,1,1),
          'Articulado': (1,1,1,0,0,0),
          'Rodillo X': (0,1,1,0,0,0),
          ...
      }
      new_fixity = fixity_map[preset_name]
      # Create undo command
      cmd = DictChangeCommand(
          target_dict=self.model.nodes,
          key=node_tag,
          attr_path='fixity',
          old_value=self.model.nodes[node_tag].fixity,
          new_value=new_fixity
      )
      self.undo_manager.execute(cmd)
      self.update_viewport()  # Refresh support visualization
  ```
- Mostrar checkmark (✓) en submenu si preset ya está aplicado

**Testing:**
- Crear nodo libre → right-click → "Empotrado" → verificar que aparece cono verde
- Undo (Ctrl+Z) → verificar que vuelve a nodo libre (esfera roja)
- Aplicar "Rodillo X" → verificar fixity = (0,1,1,0,0,0)

---

### Step 3: Quick Section Assignment (Context Menu)
**Files:**
- `gui/viewport/vtk_widget.py`

**What:**
Implementar submenu "Cambiar Sección" para elementos:
- Poblar submenu dinámicamente con `self.model.sections.values()`
- Mostrar como `"IPE300 [Elastic3D]"` con checkmark (✓) en sección actual
- Al seleccionar:
  ```python
  def on_context_change_section(self, section_tag):
      elem_tag = self.selected_element
      old_section = self.model.elements[elem_tag].section_tag
      cmd = DictChangeCommand(...)
      self.undo_manager.execute(cmd)
      self.update_viewport()
  ```

**Enhancement:** Si no hay secciones definidas, mostrar "No hay secciones (crear primero)" deshabilitado.

**Testing:**
- Crear frame con sección "IPE200"
- Right-click → "Cambiar Sección" → "IPE300" → verificar cambio en Properties Panel
- Verificar checkmark en "IPE300" si vuelves a abrir menú
- Undo → verificar que vuelve a "IPE200"

---

### Step 4: Property Painter Mode
**Files:**
- `gui/viewport/vtk_widget.py`
- `gui/main_window.py` (nuevo botón en toolbar)

**What:**
Implementar modo "Property Painter" (inspirado en SAP2000's Match Properties):
1. **Activación:**
   - Click derecho en elemento → "Copiar Propiedades"
   - O botón toolbar "🖌️ Pintar Propiedades"
2. **Comportamiento:**
   - Cambiar cursor a icono de pincel
   - Guardar propiedades del elemento fuente: `section_tag`, `transf_tag`, `params`
   - Esperar clicks en otros elementos
   - Cada click: aplicar propiedades copiadas con `UndoCommand`
   - ESC para salir del modo
3. **Visual feedback:**
   - Elemento fuente: resaltar en color naranja permanente
   - Elementos pintados: flash verde breve al aplicar

**Testing:**
- Crear frame F1 con IPE300
- Right-click F1 → "Copiar Propiedades"
- Click en frames F2, F3, F4 → verificar que todos cambian a IPE300
- ESC → modo termina, volver a Select
- Undo 3 veces → F2, F3, F4 vuelven a propiedades originales

---

### Step 5: Quick Load Assignment (Context Menu)
**Files:**
- `gui/viewport/vtk_widget.py`
- `gui/dialogs/nodal_load_dialog.py`

**What:**
Modificar flujo de asignación de cargas:
1. **Context menu "Aplicar Carga...":**
   - Abre `NodalLoadDialog` PRE-CONFIGURADO con:
     - Node selection: solo el nodo seleccionado (checkbox marcado, otros desmarcados)
     - Load pattern: usar `active_props.load_pattern_tag`
   - Permite rápidamente ingresar Fx, Fy, Fz → Apply
2. **Optional Enhancement:** Submenu rápido "Cargas Predefinidas":
   - "Vertical 10 kN" → aplica (0, 0, -10)
   - "Lateral X 5 kN" → aplica (5, 0, 0)
   - "Personalizado..." → abre dialog completo

**Testing:**
- Seleccionar nodo N1
- Right-click → "Aplicar Carga..." → dialog abre con N1 pre-seleccionado
- Ingresar Fz=-50 → Apply → verificar que carga se agregó a patrón activo
- Toggle "Loads" view → ver flecha roja en N1

---

### Step 6: Keyboard Shortcuts for Quick Actions
**Files:**
- `gui/main_window.py`

**What:**
Agregar shortcuts para acciones rápidas (SAP2000 usa Alt+A+R para restricciones):
- `R`: Asignar Empotrado a selección actual
- `H`: Asignar Articulado (Hinge)
- `M`: Activar Property Painter Mode
- `L`: Abrir quick load dialog para selección

Mostrar estos shortcuts en tooltips y menú contextual.

**Testing:**
- Seleccionar nodo → presionar `R` → verificar que se empotra
- Seleccionar elemento → presionar `M` → activar Property Painter
- Verificar que shortcuts no interfieren con otros (Ctrl+R ya usado, etc.)

---

## Impact Summary
**Antes:** 
- Asignar fixity: Click nodo → Menú Asignar → Condiciones de borde → Select nodes → Select preset → OK (7 clicks)
- Cambiar sección: Click elemento → Properties → F2 → Dropdown → Seleccionar → Enter (6 clicks + typing)

**Después:** 
- Asignar fixity: Right-click → Empotrado (2 clicks)
- Cambiar sección: Right-click → Sección → IPE300 (3 clicks)
- Property Painter: Right-click → Copiar → Click, Click, Click en 10 elementos (1+10 clicks para 10 elementos)

**UX similar a SAP2000:** ✅ Context menus, ✅ Property painter, ✅ Quick assign
