# Active Properties System — Implementation Plan

## Goal
Transform the Properties Panel into a pre-creation editor when drawing modes (DRAW_FRAME, DRAW_SHELL) are active, allowing users to configure element properties (section, transformation, element type) BEFORE drawing — eliminating the "draw → edit" workflow and reducing clicks by ~70%.

## Prerequisites
Make sure that the user is currently on the `feature/drawing-properties-panel` branch before beginning implementation.
If not, move them to the correct branch. If the branch does not exist, create it from main.

---

### Step-by-Step Instructions

---

#### Step 1: Drawing Template Data Model

Add the `DrawingTemplate` dataclass to `gui/core/model_data.py` and wire it into `StructuralModel`.

- [x] Open `gui/core/model_data.py`
- [x] Add the `DrawingTemplate` dataclass **after** the `LoadPattern` class (before the `AnalysisResult` class, around line 309). Copy and paste the code below:

```python
# ---------------------------------------------------------------------------
# Plantilla de dibujo — propiedades pre-asignadas para nuevos elementos
# ---------------------------------------------------------------------------

@dataclass
class DrawingTemplate:
    """Plantilla de propiedades para nuevos elementos dibujados en viewport."""

    # Para Frames
    frame_section_tag: Optional[int] = None
    frame_transf_tag: Optional[int] = None
    frame_elem_type: ElementType = ElementType.ELASTIC_BEAM_COLUMN

    # Para Shells
    shell_section_tag: Optional[int] = None
    shell_thickness: float = 0.2  # metros

    # Para Loads (patrón de carga activo — futuro)
    active_load_pattern_tag: int = 1  # Default to DEAD

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

- [x] In the `StructuralModel.__init__()` method, add the `drawing_template` field. Find the line:

```python
        self.load_patterns: dict[int, LoadPattern] = {}
```

And **after** it, add:

```python
        self.drawing_template = DrawingTemplate()
```

- [x] In the `StructuralModel.to_dict()` method, add the `drawing_template` serialization. Find:

```python
            "load_patterns": {str(k): v.to_dict() for k, v in self.load_patterns.items()},
```

And change it to:

```python
            "load_patterns": {str(k): v.to_dict() for k, v in self.load_patterns.items()},
            "drawing_template": self.drawing_template.to_dict(),
```

- [x] In the `StructuralModel.from_dict()` method, add template deserialization. Find the line:

```python
        for k, v in d.get("load_patterns", {}).items():
            model.load_patterns[int(k)] = LoadPattern.from_dict(v)
        return model
```

And change it to:

```python
        for k, v in d.get("load_patterns", {}).items():
            model.load_patterns[int(k)] = LoadPattern.from_dict(v)
        model.drawing_template = DrawingTemplate.from_dict(
            d.get("drawing_template", {})
        )
        return model
```

- [x] In the `StructuralModel.clear()` method, add template reset. Find:

```python
        # Re-crear DEAD obligatorio
        self.load_patterns[1] = LoadPattern(
```

And **before** it, add:

```python
        self.drawing_template = DrawingTemplate()
```

##### Step 1 Verification Checklist
- [x] No import errors — run `python -c "from gui.core.model_data import DrawingTemplate, StructuralModel; m = StructuralModel(); print(m.drawing_template)"` successfully
- [x] `m.drawing_template.frame_section_tag` is `None` by default
- [x] `m.drawing_template.frame_elem_type` is `ElementType.ELASTIC_BEAM_COLUMN`
- [x] `m.to_dict()` includes `"drawing_template"` key
- [x] `StructuralModel.from_dict(m.to_dict())` round-trips correctly

#### Step 1 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

---

#### Step 2: Properties Panel — Drawing Mode View

Add `show_drawing_template()` and `clear()` methods to `gui/panels/properties_panel.py` that display an editable form for pre-creation properties.

- [x] Open `gui/panels/properties_panel.py`
- [x] Add `QComboBox` to the imports. Find:

```python
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
```

And replace with:

```python
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
```

- [x] Add the runtime imports inside the `TYPE_CHECKING` block. Find:

```python
if TYPE_CHECKING:
    from gui.core.model_data import StructuralModel
    from gui.core.undo_manager import UndoManager
```

And replace with:

```python
if TYPE_CHECKING:
    from gui.core.model_data import StructuralModel
    from gui.core.undo_manager import UndoManager

from gui.core.model_data import ElementType, SectionType
```

- [x] Add the `clear()` method and `show_drawing_template()` method **after** the `show_item()` method (after the `self._layout.addStretch()` line at the end of `show_item()`). Find the end of `show_item()`:

```python
        self._layout.addWidget(grp)
        self._layout.addStretch()

    def _resolve_item(self, model, category, tag):
```

And insert the following **between** `self._layout.addStretch()` and `def _resolve_item`:

```python

    def clear(self) -> None:
        """Limpia el panel y muestra el placeholder."""
        self._current_item = None
        self._current_category = ""
        self._current_tag = 0
        self._field_widgets.clear()
        self._clear_layout()
        self._placeholder = QLabel("Seleccione un ítem\nen el Model Tree")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #9E9E9E; padding: 30px;")
        self._layout.addWidget(self._placeholder)

    def show_drawing_template(
        self,
        model: "StructuralModel",
        mode: str,
    ) -> None:
        """Muestra propiedades editables para elementos a crear.

        Parameters
        ----------
        model : StructuralModel
            Modelo actual.
        mode : str
            ``"frame"`` o ``"shell"``.
        """
        template = model.drawing_template

        # Limpiar layout actual
        self._clear_layout()
        self._current_item = None
        self._current_category = ""
        self._current_tag = 0
        self._field_widgets.clear()

        # Título
        if mode == "frame":
            title_text = "Propiedades del Frame a Crear"
        else:
            title_text = "Propiedades del Shell a Crear"
        title = QLabel(title_text)
        title.setStyleSheet(
            "font-weight: bold; font-size: 13px; padding: 6px 0; color: #1976D2;"
        )
        self._layout.addWidget(title)

        # Info box
        info = QLabel("Los elementos dibujados usarán estas propiedades")
        info.setStyleSheet(
            "color: #757575; font-size: 11px; padding: 4px; "
            "background: #E3F2FD; border-radius: 3px;"
        )
        info.setWordWrap(True)
        self._layout.addWidget(info)

        # Formulario
        grp = QGroupBox("Configuración")
        form = QFormLayout()
        grp.setLayout(form)

        if mode == "frame":
            self._build_frame_template_form(form, model, template)
        elif mode == "shell":
            self._build_shell_template_form(form, model, template)

        self._layout.addWidget(grp)

        # Hint para crear secciones si no hay
        if not model.sections:
            hint = QLabel(
                "\u26a0\ufe0f No hay secciones definidas.\n"
                "Crea una en Definir \u2192 Sección"
            )
            hint.setStyleSheet(
                "color: #F57C00; padding: 10px; "
                "background: #FFF3E0; border-radius: 3px;"
            )
            hint.setWordWrap(True)
            self._layout.addWidget(hint)

        self._layout.addStretch()

    # ------------------------------------------------------------------
    # Builders internos para formularios de template
    # ------------------------------------------------------------------

    def _build_frame_template_form(
        self,
        form: QFormLayout,
        model: "StructuralModel",
        template: "DrawingTemplate",
    ) -> None:
        """Construye los campos del formulario para template de frame."""
        from gui.core.model_data import DrawingTemplate  # noqa: F811

        # Dropdown: Tipo de Elemento
        combo_type = QComboBox()
        for elem_type in [
            ElementType.ELASTIC_BEAM_COLUMN,
            ElementType.FORCE_BEAM_COLUMN,
            ElementType.DISP_BEAM_COLUMN,
            ElementType.TRUSS,
            ElementType.COROT_TRUSS,
        ]:
            combo_type.addItem(elem_type.value, elem_type)
        current_idx = combo_type.findData(template.frame_elem_type)
        if current_idx >= 0:
            combo_type.setCurrentIndex(current_idx)
        combo_type.currentIndexChanged.connect(
            lambda _idx, c=combo_type, t=template: self._on_template_type_changed(t, c)
        )
        form.addRow("Tipo de Elemento:", combo_type)

        # Dropdown: Sección (poblado dinámicamente)
        combo_section = QComboBox()
        combo_section.addItem("(Sin asignar)", None)
        for tag, section in model.sections.items():
            display = f"{section.name} [{section.sec_type.value}]"
            combo_section.addItem(display, tag)
        if template.frame_section_tag is not None:
            idx = combo_section.findData(template.frame_section_tag)
            if idx >= 0:
                combo_section.setCurrentIndex(idx)
        combo_section.currentIndexChanged.connect(
            lambda _idx, c=combo_section, t=template: self._on_template_section_changed(t, c)
        )
        form.addRow("Sección:", combo_section)

        # Dropdown: Transformación
        combo_transf = QComboBox()
        combo_transf.addItem("(Sin asignar)", None)
        for tag, transf in model.geom_transfs.items():
            display = f"Tag {tag} [{transf.transf_type.value}]"
            combo_transf.addItem(display, tag)
        if template.frame_transf_tag is not None:
            idx = combo_transf.findData(template.frame_transf_tag)
            if idx >= 0:
                combo_transf.setCurrentIndex(idx)
        combo_transf.currentIndexChanged.connect(
            lambda _idx, c=combo_transf, t=template: self._on_template_transf_changed(t, c)
        )
        form.addRow("Transformación:", combo_transf)

    def _build_shell_template_form(
        self,
        form: QFormLayout,
        model: "StructuralModel",
        template: "DrawingTemplate",
    ) -> None:
        """Construye los campos del formulario para template de shell."""
        from gui.core.model_data import DrawingTemplate  # noqa: F811

        # Dropdown: Sección (solo secciones compatibles con shells)
        combo_section = QComboBox()
        combo_section.addItem("(Sin asignar)", None)
        for tag, section in model.sections.items():
            display = f"{section.name} [{section.sec_type.value}]"
            combo_section.addItem(display, tag)
        if template.shell_section_tag is not None:
            idx = combo_section.findData(template.shell_section_tag)
            if idx >= 0:
                combo_section.setCurrentIndex(idx)
        combo_section.currentIndexChanged.connect(
            lambda _idx, c=combo_section, t=template: self._on_template_shell_section_changed(t, c)
        )
        form.addRow("Sección:", combo_section)

        # Espesor
        spin_thick = QDoubleSpinBox()
        spin_thick.setDecimals(3)
        spin_thick.setRange(0.001, 10.0)
        spin_thick.setValue(template.shell_thickness)
        spin_thick.setSuffix(" m")
        spin_thick.editingFinished.connect(
            lambda s=spin_thick, t=template: self._on_template_thickness_changed(t, s.value())
        )
        form.addRow("Espesor:", spin_thick)

    # ------------------------------------------------------------------
    # Callbacks de template
    # ------------------------------------------------------------------

    @staticmethod
    def _on_template_type_changed(template: "DrawingTemplate", combo: QComboBox) -> None:
        template.frame_elem_type = combo.currentData()

    @staticmethod
    def _on_template_section_changed(template: "DrawingTemplate", combo: QComboBox) -> None:
        template.frame_section_tag = combo.currentData()

    @staticmethod
    def _on_template_transf_changed(template: "DrawingTemplate", combo: QComboBox) -> None:
        template.frame_transf_tag = combo.currentData()

    @staticmethod
    def _on_template_shell_section_changed(template: "DrawingTemplate", combo: QComboBox) -> None:
        template.shell_section_tag = combo.currentData()

    @staticmethod
    def _on_template_thickness_changed(template: "DrawingTemplate", value: float) -> None:
        template.shell_thickness = value

```

##### Step 2 Verification Checklist
- [x] No import errors — run `python -c "from gui.panels.properties_panel import PropertiesPanel; print('OK')"` successfully
- [x] `PropertiesPanel` has `clear()`, `show_drawing_template()` methods
- [x] `PropertiesPanel` has `_build_frame_template_form()`, `_build_shell_template_form()` methods

#### Step 2 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

---

#### Step 3: MainWindow — Trigger Panel Update on Mode Change

Modify `set_mode()` in `gui/main_window.py` to update the Properties Panel when entering/leaving drawing modes.

- [ ] Open `gui/main_window.py`
- [ ] In the `set_mode()` method, update the `InteractionMode.SELECT` branch to clear the properties panel. Find:

```python
        if mode == InteractionMode.SELECT:
            self._viewport.enable_picking(self._model)
            self._viewport.set_drawing_mode(False)
            self._viewport.clear_all_previews()
            self._set_offset_widgets_visible(False)
            self._update_statusbar()
```

And replace with:

```python
        if mode == InteractionMode.SELECT:
            self._viewport.enable_picking(self._model)
            self._viewport.set_drawing_mode(False)
            self._viewport.clear_all_previews()
            self._set_offset_widgets_visible(False)
            self._properties.clear()
            self._update_statusbar()
```

- [ ] In the same `set_mode()` method, inside the `else` branch (for drawing modes), add the panel update **after** the status bar message. Find:

```python
            snap = self._snap_mgr.status_text()
            self.statusBar().showMessage(
                f"Modo: {mode_label}  |  {snap}  |  "
                f"Clic en viewport para crear  |  Escape → Selección"
            )
```

And replace with:

```python
            snap = self._snap_mgr.status_text()
            self.statusBar().showMessage(
                f"Modo: {mode_label}  |  {snap}  |  "
                f"Clic en viewport para crear  |  Escape → Selección"
            )

            # Actualizar Properties Panel según modo de dibujo
            if mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(self._model, "frame")
            elif mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(self._model, "shell")
```

##### Step 3 Verification Checklist
- [ ] Launch the app with `python -m gui.main`
- [ ] Click "Dibujar Frame" → Properties Panel shows "Propiedades del Frame a Crear" with dropdowns for Tipo, Sección, Transformación
- [ ] Click "Dibujar Shell" → Properties Panel shows "Propiedades del Shell a Crear" with Sección and Espesor
- [ ] Press Escape (back to SELECT) → Properties Panel shows placeholder "Seleccione un ítem"
- [ ] Switch from DRAW_FRAME → DRAW_SHELL → Properties Panel updates correctly
- [ ] If no sections defined, see the warning hint "No hay secciones definidas"

#### Step 3 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

---

#### Step 4: Integration with Frame Drawing

Modify `_handle_draw_frame()` in `gui/main_window.py` to use the `drawing_template` values when creating elements.

- [ ] Open `gui/main_window.py`
- [ ] In `_handle_draw_frame()`, find the section where the element is created (inside the `else` / second-click block). Find:

```python
            # Crear elemento frame
            elem_tag = self._model.next_element_tag()
            element = Element(
                tag=elem_tag,
                elem_type=ElementType.ELASTIC_BEAM_COLUMN,
                node_i=self._frame_first_node,
                node_j=node_j_tag,
                section_tag=None,
                transf_tag=None,
            )
```

And replace with:

```python
            # Obtener propiedades del template de dibujo
            template = self._model.drawing_template
            elem_type = template.frame_elem_type
            section_tag = template.frame_section_tag
            transf_tag = template.frame_transf_tag

            # Para Truss/CorotTruss no se necesita transformación
            if elem_type in (ElementType.TRUSS, ElementType.COROT_TRUSS):
                transf_tag = None

            # Crear elemento frame con propiedades del template
            elem_tag = self._model.next_element_tag()
            element = Element(
                tag=elem_tag,
                elem_type=elem_type,
                node_i=self._frame_first_node,
                node_j=node_j_tag,
                section_tag=section_tag,
                transf_tag=transf_tag,
            )
```

- [ ] Update the log message at the end to show the actual properties used. Find:

```python
            self._console.log_success(
                f"Frame {elem_tag} creado: [{self._frame_first_node}→{node_j_tag}] "
                f"elasticBeamColumn"
            )
```

And replace with:

```python
            sec_display = f"Sección: {section_tag}" if section_tag else "Sección: N/A"
            self._console.log_success(
                f"Frame {elem_tag} creado: [{self._frame_first_node}→{node_j_tag}] "
                f"{elem_type.value} — {sec_display}"
            )
```

##### Step 4 Verification Checklist
- [ ] Launch the app with `python -m gui.main`
- [ ] Define a Section (Definir → Secciones) and a Transformation (Definir → Transformaciones)
- [ ] Activate "Dibujar Frame" mode
- [ ] In the Properties Panel, select the section and transformation from the dropdowns
- [ ] Draw a frame (2 clicks) → Console shows the section tag in the log message
- [ ] Select the created element in Model Tree → Verify section_tag and transf_tag are set correctly
- [ ] Draw 5 more frames → Verify all use the same section/transformation
- [ ] Change section in panel → Draw another frame → Verify it uses the new section

#### Step 4 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

---

#### Step 5: Integration with Shell Drawing

Modify `_handle_draw_shell()` in `gui/main_window.py` to use the `drawing_template` values when creating shell elements.

- [ ] Open `gui/main_window.py`
- [ ] In `_handle_draw_shell()`, find the section where the shell element is created (inside the `else` / fourth-click block). Find:

```python
            elem_tag = self._model.next_element_tag()
            element = Element(
                tag=elem_tag,
                elem_type=ElementType.SHELL_MITC4,
                node_i=self._shell_nodes[0],
                node_j=self._shell_nodes[1],
                node_k=self._shell_nodes[2],
                node_l=self._shell_nodes[3],
                section_tag=None,
                transf_tag=None,
            )
```

And replace with:

```python
            # Obtener propiedades del template de dibujo
            template = self._model.drawing_template
            shell_section_tag = template.shell_section_tag

            elem_tag = self._model.next_element_tag()
            element = Element(
                tag=elem_tag,
                elem_type=ElementType.SHELL_MITC4,
                node_i=self._shell_nodes[0],
                node_j=self._shell_nodes[1],
                node_k=self._shell_nodes[2],
                node_l=self._shell_nodes[3],
                section_tag=shell_section_tag,
                transf_tag=None,
            )
```

- [ ] Update the shell log message to include section info. Find:

```python
            self._console.log_success(
                f"Shell {elem_tag} creado: [{tags_str}] ShellMITC4"
            )
```

And replace with:

```python
            sec_display = f"Sección: {shell_section_tag}" if shell_section_tag else "Sección: N/A"
            self._console.log_success(
                f"Shell {elem_tag} creado: [{tags_str}] ShellMITC4 — {sec_display}"
            )
```

##### Step 5 Verification Checklist
- [ ] Launch the app with `python -m gui.main`
- [ ] Activate "Dibujar Shell" mode
- [ ] Select a section in the Properties Panel dropdown
- [ ] Draw a shell (4 clicks) → Console shows the section tag in the log message
- [ ] Select the created shell in Model Tree → Verify section_tag is set correctly

#### Step 5 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

---

#### Step 6: Visual Feedback in Status Bar

Update the status bar in `set_mode()` to show active drawing properties when in DRAW_FRAME or DRAW_SHELL mode.

- [ ] Open `gui/main_window.py`
- [ ] Find the status bar message in the `else` branch of `set_mode()`. Locate this block that was modified in Step 3:

```python
            snap = self._snap_mgr.status_text()
            self.statusBar().showMessage(
                f"Modo: {mode_label}  |  {snap}  |  "
                f"Clic en viewport para crear  |  Escape → Selección"
            )

            # Actualizar Properties Panel según modo de dibujo
            if mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(self._model, "frame")
            elif mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(self._model, "shell")
```

And replace the **entire block** with:

```python
            snap = self._snap_mgr.status_text()

            # Construir info de propiedades activas para status bar
            props_info = ""
            if mode == InteractionMode.DRAW_FRAME:
                template = self._model.drawing_template
                section_name = "(sin asignar)"
                if template.frame_section_tag:
                    sec = self._model.sections.get(template.frame_section_tag)
                    if sec:
                        section_name = sec.name
                transf_name = "(sin asignar)"
                if template.frame_transf_tag:
                    transf_name = f"Tag {template.frame_transf_tag}"
                props_info = f"  |  Sección: {section_name}  |  Transf: {transf_name}"
            elif mode == InteractionMode.DRAW_SHELL:
                template = self._model.drawing_template
                section_name = "(sin asignar)"
                if template.shell_section_tag:
                    sec = self._model.sections.get(template.shell_section_tag)
                    if sec:
                        section_name = sec.name
                props_info = f"  |  Sección: {section_name}"

            self.statusBar().showMessage(
                f"Modo: {mode_label}  |  {snap}{props_info}  |  "
                f"Clic en viewport para crear  |  Escape → Selección"
            )

            # Actualizar Properties Panel según modo de dibujo
            if mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(self._model, "frame")
            elif mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(self._model, "shell")
```

##### Step 6 Verification Checklist
- [ ] Launch the app with `python -m gui.main`
- [ ] Define a section (e.g., "IPE300") and a transformation
- [ ] Activate "Dibujar Frame"
- [ ] Select IPE300 in the Properties Panel
- [ ] Status bar should display something like: `Modo: Dibujar Frame | [SNAP ON] | Grilla: 1.0 | Sección: IPE300 | Transf: Tag 1 | Clic en viewport para crear | Escape → Selección`
- [ ] With no section selected → status bar shows `Sección: (sin asignar)`
- [ ] Activate "Dibujar Shell" → status bar shows shell section info

#### Step 6 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

---

#### Step 7: Smart Defaults and Auto-Refresh

Add auto-selection of the first section/transformation created, and refresh the Properties Panel when new sections or transformations are created while in a drawing mode.

- [ ] Open `gui/main_window.py`
- [ ] Modify `_on_define_section()` to auto-assign and refresh the panel. Find:

```python
    def _on_define_section(self) -> None:
        """Abre el diálogo para crear una nueva sección."""
        dlg = SectionDialog(
            self,
            next_tag=self._model.next_section_tag(),
            model=self._model,
        )
        if dlg.exec():
            sec = dlg.get_section()
            self._model.sections[sec.tag] = sec
            self._refresh_all()
            self._console.log_success(
                f"Sección creada: {sec.tag} — {sec.name} [{sec.sec_type.value}]"
            )
```

And replace with:

```python
    def _on_define_section(self) -> None:
        """Abre el diálogo para crear una nueva sección."""
        dlg = SectionDialog(
            self,
            next_tag=self._model.next_section_tag(),
            model=self._model,
        )
        if dlg.exec():
            sec = dlg.get_section()
            self._model.sections[sec.tag] = sec
            self._refresh_all()
            self._console.log_success(
                f"Sección creada: {sec.tag} — {sec.name} [{sec.sec_type.value}]"
            )

            # Auto-asignar si es la primera sección y template no tiene sección
            template = self._model.drawing_template
            if len(self._model.sections) == 1:
                if template.frame_section_tag is None:
                    template.frame_section_tag = sec.tag
                    self._console.log(
                        f"✓ Sección {sec.name} auto-seleccionada para frames"
                    )
                if template.shell_section_tag is None:
                    template.shell_section_tag = sec.tag
                    self._console.log(
                        f"✓ Sección {sec.name} auto-seleccionada para shells"
                    )

            # Refrescar panel si estamos en modo dibujo
            if self._interaction_mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(self._model, "frame")
            elif self._interaction_mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(self._model, "shell")
```

- [ ] Modify `_on_define_transf()` similarly. Find:

```python
    def _on_define_transf(self) -> None:
        """Abre el diálogo para crear una nueva transformación."""
        dlg = TransfDialog(
            self,
            next_tag=self._model.next_transf_tag(),
        )
        if dlg.exec():
            transf = dlg.get_transf()
            self._model.geom_transfs[transf.tag] = transf
            self._refresh_all()
            self._console.log_success(
                f"Transformación creada: {transf.tag} — {transf.transf_type.value}"
            )
```

And replace with:

```python
    def _on_define_transf(self) -> None:
        """Abre el diálogo para crear una nueva transformación."""
        dlg = TransfDialog(
            self,
            next_tag=self._model.next_transf_tag(),
        )
        if dlg.exec():
            transf = dlg.get_transf()
            self._model.geom_transfs[transf.tag] = transf
            self._refresh_all()
            self._console.log_success(
                f"Transformación creada: {transf.tag} — {transf.transf_type.value}"
            )

            # Auto-asignar si es la primera transformación
            template = self._model.drawing_template
            if len(self._model.geom_transfs) == 1 and template.frame_transf_tag is None:
                template.frame_transf_tag = transf.tag
                self._console.log(
                    f"✓ Transformación Tag {transf.tag} auto-seleccionada para frames"
                )

            # Refrescar panel si estamos en modo dibujo frame
            if self._interaction_mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(self._model, "frame")
```

##### Step 7 Verification Checklist
- [ ] Launch the app with `python -m gui.main`
- [ ] Activate "Dibujar Frame" mode (with no sections or transformations defined)
- [ ] Create a section (Definir → Secciones, e.g., "IPE300")
- [ ] Console should show `✓ Sección IPE300 auto-seleccionada para frames`
- [ ] Properties Panel should refresh and show IPE300 selected in the dropdown
- [ ] Create a transformation (Definir → Transformaciones)
- [ ] Console should show `✓ Transformación Tag 1 auto-seleccionada para frames`
- [ ] Properties Panel should show Tag 1 selected
- [ ] Create a second section → Verify it does NOT auto-select (only first is auto-selected)
- [ ] While not in a drawing mode, create a section → Verify no auto-refresh of panel occurs

#### Step 7 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

---

## Impact Summary

### Workflow Comparison

| **Task** | **Before** | **After** | **Improvement** |
|-----------|-----------|-------------|------------|
| Create 1 frame with section | Draw (2 clicks) → Properties Panel → Edit → Select → Enter (7 clicks) | Configure section (2 clicks) → Draw (2 clicks) = **4 clicks** | **43% reduction** |
| Create 100 frames with same section | 100 × 7 = **700 clicks** | 2 + (100 × 2) = **202 clicks** | **71% reduction** |
| Change section and create 20 frames | 20 × 7 = **140 clicks** | 2 + (20 × 2) = **42 clicks** | **70% reduction** |

### Files Modified

| File | Changes |
|------|---------|
| `gui/core/model_data.py` | Added `DrawingTemplate` dataclass; wired into `StructuralModel` (init, to_dict, from_dict, clear) |
| `gui/panels/properties_panel.py` | Added `clear()`, `show_drawing_template()`, template form builders, template callbacks; added `QComboBox` import |
| `gui/main_window.py` | Updated `set_mode()` with panel/statusbar integration; updated `_handle_draw_frame()` and `_handle_draw_shell()` to use template; updated `_on_define_section()` and `_on_define_transf()` with auto-assign and refresh |
