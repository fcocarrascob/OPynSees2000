# Step 4: Restrict Frame/Shell Drawing in Free 3D Mode

## Goal
Enforce that in "Free 3D" mode, frames and shells can ONLY be drawn between existing nodes (auto-snap required, no node creation in empty space). If user clicks in empty space, show an error message. In Free mode, DRAW_NODE auto-switches to XY plane. This ensures clean workflows: define points in planes, connect in 3D.

## Prerequisites
Steps 1–3 must be completed and committed.

---

### Step-by-Step Instructions

#### 4.1 — Modify `_handle_draw_frame` to require existing nodes in Free mode

- [ ] Open `gui/main_window.py`
- [ ] Find the `_handle_draw_frame` method. The method currently starts with:

```python
    def _handle_draw_frame(self, x: float, y: float, z: float) -> None:
        """Maneja clics en modo DRAW_FRAME (secuencia de 2 clics)."""
        from gui.viewport.picking import find_closest_node
        from gui.core.model_data import Node, Element, ElementType

        if self._frame_first_node is None:
```

- [ ] Replace the ENTIRE method with this new version that adds Free mode restrictions:

```python
    def _handle_draw_frame(self, x: float, y: float, z: float) -> None:
        """Maneja clics en modo DRAW_FRAME (secuencia de 2 clics)."""
        from gui.viewport.picking import find_closest_node
        from gui.core.model_data import Node, Element, ElementType

        template = self._model.drawing_template

        # In Free mode, REQUIRE existing node (wider tolerance)
        if template.working_plane_mode == "Free":
            free_tolerance = template.snap_tolerance * 2.5
            existing = find_closest_node(
                self._model, (x, y, z), tolerance=free_tolerance,
            )
            if existing is None:
                self._console.log_error(
                    "En modo 3D libre, debe hacer clic cerca de un nodo existente. "
                    "Use planos XY/XZ/YZ para crear nodos nuevos."
                )
                # Reset state
                self._frame_first_node = None
                self._frame_first_coords = None
                self._viewport.clear_all_previews()
                return
            # Force use of existing node coordinates
            node = self._model.nodes[existing]
            x, y, z = node.x, node.y, node.z

        if self._frame_first_node is None:
            # === PRIMER CLIC: establecer nodo I ===
            existing = find_closest_node(self._model, (x, y, z), tolerance=template.snap_tolerance)
            if existing is not None:
                self._frame_first_node = existing
                node = self._model.nodes[existing]
                self._frame_first_coords = (node.x, node.y, node.z)
                self._console.log(
                    f"Frame: nodo I = {existing} (existente)"
                )
            else:
                # Crear nodo nuevo como primer nodo (solo en modos de plano)
                tag = self._model.next_node_tag()
                node = Node(tag=tag, x=x, y=y, z=z)
                cmd = DictChangeCommand(
                    target_dict=self._model.nodes,
                    key=tag,
                    old_value=None,
                    new_value=node,
                    desc=f"Crear nodo {tag} para frame",
                )
                self._undo_mgr.execute(cmd)
                self._frame_first_node = tag
                self._frame_first_coords = (x, y, z)
                self._refresh_all()
                self._console.log(
                    f"Frame: nodo I = {tag} (nuevo: {x:.2f}, {y:.2f}, {z:.2f})"
                )
        else:
            # === SEGUNDO CLIC: establecer nodo J y crear frame ===
            commands: list = []

            # Resolver nodo J
            existing_j = find_closest_node(self._model, (x, y, z), tolerance=template.snap_tolerance)
            if existing_j is not None:
                node_j_tag = existing_j
                self._console.log(f"Frame: nodo J = {existing_j} (existente)")
            else:
                node_j_tag = self._model.next_node_tag()
                node_j = Node(tag=node_j_tag, x=x, y=y, z=z)
                commands.append(DictChangeCommand(
                    target_dict=self._model.nodes,
                    key=node_j_tag,
                    old_value=None,
                    new_value=node_j,
                    desc=f"Crear nodo {node_j_tag} para frame",
                ))
                self._console.log(
                    f"Frame: nodo J = {node_j_tag} (nuevo: {x:.2f}, {y:.2f}, {z:.2f})"
                )

            # Prevenir frame de un nodo a sí mismo
            if node_j_tag == self._frame_first_node:
                self._console.log_error("Frame: nodos I y J no pueden ser iguales.")
                return

            # Obtener propiedades del template de dibujo
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
            commands.append(DictChangeCommand(
                target_dict=self._model.elements,
                key=elem_tag,
                old_value=None,
                new_value=element,
                desc=f"Crear elemento {elem_tag}",
            ))

            # Ejecutar como comando compuesto
            if len(commands) == 1:
                self._undo_mgr.execute(commands[0])
            else:
                compound = CompoundUndoCommand(
                    commands,
                    desc=f"Crear frame {elem_tag} [{self._frame_first_node}\u2192{node_j_tag}]",
                )
                self._undo_mgr.execute(compound)

            self._refresh_all()
            sec_display = f"Sección: {section_tag}" if section_tag else "Sección: N/A"
            self._console.log_success(
                f"Frame {elem_tag} creado: [{self._frame_first_node}\u2192{node_j_tag}] "
                f"{elem_type.value} — {sec_display}"
            )

            # Reset para siguiente frame (continuo)
            self._frame_first_node = None
            self._frame_first_coords = None
            self._viewport.clear_all_previews()
```

---

#### 4.2 — Modify `_handle_draw_shell` to require existing nodes in Free mode

- [ ] Find the `_handle_draw_shell` method. Replace the ENTIRE method with this new version:

```python
    def _handle_draw_shell(self, x: float, y: float, z: float) -> None:
        """Maneja clics en modo DRAW_SHELL (secuencia de 4 clics)."""
        from gui.viewport.picking import find_closest_node
        from gui.core.model_data import Node, Element, ElementType

        template = self._model.drawing_template

        # In Free mode, REQUIRE existing node (wider tolerance)
        if template.working_plane_mode == "Free":
            free_tolerance = template.snap_tolerance * 2.5
            existing = find_closest_node(
                self._model, (x, y, z), tolerance=free_tolerance,
            )
            if existing is None:
                self._console.log_error(
                    "En modo 3D libre, debe hacer clic cerca de un nodo existente. "
                    "Use planos XY/XZ/YZ para crear nodos nuevos."
                )
                # Reset state
                self._shell_nodes.clear()
                self._shell_coords.clear()
                self._viewport.clear_all_previews()
                return
            # Force use of existing node coordinates
            node = self._model.nodes[existing]
            x, y, z = node.x, node.y, node.z

        click_num = len(self._shell_nodes) + 1  # 1, 2, 3, o 4
        node_labels = {1: "I", 2: "J", 3: "K", 4: "L"}

        # Resolver nodo: snap a existente o crear nuevo
        existing = find_closest_node(self._model, (x, y, z), tolerance=template.snap_tolerance)
        commands_for_node: list = []

        if existing is not None:
            node_tag = existing
            node_obj = self._model.nodes[existing]
            node_coords = (node_obj.x, node_obj.y, node_obj.z)
            self._console.log(
                f"Shell: nodo {node_labels[click_num]} = {existing} (existente)"
            )
        else:
            node_tag = self._model.next_node_tag()
            node_obj = Node(tag=node_tag, x=x, y=y, z=z)
            node_coords = (x, y, z)
            commands_for_node.append(DictChangeCommand(
                target_dict=self._model.nodes,
                key=node_tag,
                old_value=None,
                new_value=node_obj,
                desc=f"Crear nodo {node_tag} para shell",
            ))
            self._console.log(
                f"Shell: nodo {node_labels[click_num]} = {node_tag} "
                f"(nuevo: {x:.2f}, {y:.2f}, {z:.2f})"
            )

        # Prevenir nodo duplicado en el mismo shell
        if node_tag in self._shell_nodes:
            self._console.log_error(
                f"Shell: nodo {node_tag} ya está en la secuencia. Seleccione otro."
            )
            return

        self._shell_nodes.append(node_tag)
        self._shell_coords.append(node_coords)

        if click_num < 4:
            # Aún no tenemos 4 nodos — crear nodo inmediatamente si es nuevo
            for cmd in commands_for_node:
                self._undo_mgr.execute(cmd)
            if commands_for_node:
                self._refresh_all()

            # Actualizar preview
            self._viewport.show_preview_shell_lines(self._shell_coords)
            remaining = 4 - click_num
            self._console.log(
                f"Shell: {click_num}/4 nodos — faltan {remaining}"
            )
        else:
            # === CUARTO CLIC: crear shell ===
            all_commands: list = list(commands_for_node)

            # Obtener propiedades del template de dibujo
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
            all_commands.append(DictChangeCommand(
                target_dict=self._model.elements,
                key=elem_tag,
                old_value=None,
                new_value=element,
                desc=f"Crear shell {elem_tag}",
            ))

            # Ejecutar como comando compuesto
            tags_str = "\u2192".join(str(t) for t in self._shell_nodes)
            if len(all_commands) == 1:
                self._undo_mgr.execute(all_commands[0])
            else:
                compound = CompoundUndoCommand(
                    all_commands,
                    desc=f"Crear shell {elem_tag} [{tags_str}]",
                )
                self._undo_mgr.execute(compound)

            self._refresh_all()
            sec_display = f"Sección: {shell_section_tag}" if shell_section_tag else "Sección: N/A"
            self._console.log_success(
                f"Shell {elem_tag} creado: [{tags_str}] ShellMITC4 — {sec_display}"
            )

            # Reset para siguiente shell (continuo)
            self._shell_nodes.clear()
            self._shell_coords.clear()
            self._viewport.clear_all_previews()
```

---

#### 4.3 — Auto-switch to XY plane when entering DRAW_NODE in Free mode

- [ ] Find the `set_mode` method. After the mode check for drawing modes, add a check for DRAW_NODE + Free. Locate this section inside the `else` block (for drawing modes):

```python
            # Sincronizar snap manager con template
            template = self._model.drawing_template
            self._snap_mgr.spacing = template.snap_spacing

            # Sincronizar vista, raycasting y filtro de plano
            self._sync_plane_and_view(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
```

- [ ] Replace with:

```python
            # Sincronizar snap manager con template
            template = self._model.drawing_template
            self._snap_mgr.spacing = template.snap_spacing

            # Auto-switch to XY if entering DRAW_NODE in Free mode
            if mode == InteractionMode.DRAW_NODE and template.working_plane_mode == "Free":
                template.working_plane_mode = "XY"
                self._console.log(
                    "Modo Free no permite crear nodos. Cambiado a plano XY."
                )

            # Sincronizar vista, raycasting y filtro de plano
            self._sync_plane_and_view(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
```

---

#### 4.4 — Show DRAW_NODE snap settings in Properties Panel

- [ ] In the `set_mode` method, after the existing block that updates Properties Panel for frame/shell modes, add support for DRAW_NODE mode. Find:

```python
            # Actualizar Properties Panel según modo de dibujo
            if mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(
                    self._model, "frame",
                    on_snap_setting_changed=self._on_snap_setting_changed,
                )
            elif mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(
                    self._model, "shell",
                    on_snap_setting_changed=self._on_snap_setting_changed,
                )
```

- [ ] Replace with:

```python
            # Actualizar Properties Panel según modo de dibujo
            if mode == InteractionMode.DRAW_NODE:
                self._properties.show_drawing_template(
                    self._model, "node",
                    on_snap_setting_changed=self._on_snap_setting_changed,
                )
            elif mode == InteractionMode.DRAW_FRAME:
                self._properties.show_drawing_template(
                    self._model, "frame",
                    on_snap_setting_changed=self._on_snap_setting_changed,
                )
            elif mode == InteractionMode.DRAW_SHELL:
                self._properties.show_drawing_template(
                    self._model, "shell",
                    on_snap_setting_changed=self._on_snap_setting_changed,
                )
```

---

#### 4.5 — Update `_refresh_drawing_properties` to include DRAW_NODE

- [ ] Find the `_refresh_drawing_properties` method added in Step 3 and replace it with:

```python
    def _refresh_drawing_properties(self) -> None:
        """Refresh properties panel when in a drawing mode."""
        if self._interaction_mode == InteractionMode.DRAW_NODE:
            self._properties.show_drawing_template(
                self._model, "node",
                on_snap_setting_changed=self._on_snap_setting_changed,
            )
        elif self._interaction_mode == InteractionMode.DRAW_FRAME:
            self._properties.show_drawing_template(
                self._model, "frame",
                on_snap_setting_changed=self._on_snap_setting_changed,
            )
        elif self._interaction_mode == InteractionMode.DRAW_SHELL:
            self._properties.show_drawing_template(
                self._model, "shell",
                on_snap_setting_changed=self._on_snap_setting_changed,
            )
```

---

#### 4.6 — Handle `show_drawing_template` for "node" mode in PropertiesPanel

- [ ] Open `gui/panels/properties_panel.py`
- [ ] Find the `show_drawing_template` method. The title logic currently is:

```python
        # Título
        if mode == "frame":
            title_text = "Propiedades del Frame a Crear"
        else:
            title_text = "Propiedades del Shell a Crear"
```

- [ ] Replace with:

```python
        # Título
        if mode == "frame":
            title_text = "Propiedades del Frame a Crear"
        elif mode == "shell":
            title_text = "Propiedades del Shell a Crear"
        else:
            title_text = "Modo Dibujo de Nodos"
```

---

#### 4.7 — Skip element template form for "node" mode

- [ ] In the same `show_drawing_template` method, find the form building section:

```python
        if mode == "frame":
            self._build_frame_template_form(form, model, template)
        elif mode == "shell":
            self._build_shell_template_form(form, model, template)

        self._layout.addWidget(grp)
```

- [ ] Replace with:

```python
        if mode == "frame":
            self._build_frame_template_form(form, model, template)
            self._layout.addWidget(grp)
        elif mode == "shell":
            self._build_shell_template_form(form, model, template)
            self._layout.addWidget(grp)
        # "node" mode: skip element config, only show snap settings below
```

---

#### 4.8 — Skip "no sections" hint for node mode

- [ ] In `show_drawing_template`, find the hint block:

```python
        # Hint para crear secciones si no hay
        if not model.sections:
```

- [ ] Replace with:

```python
        # Hint para crear secciones si no hay (only for frame/shell modes)
        if not model.sections and mode in ("frame", "shell"):
```

---

### Step 4 Verification Checklist

- [ ] No import or syntax errors
- [ ] Enter Free 3D mode, try DRAW_FRAME and click in empty space → verify error message "En modo 3D libre, debe hacer clic cerca de un nodo existente..."
- [ ] Create 2 nodes in XY plane (e.g., at (0,0,3) and (5,0,3)), switch to Free mode, click near them → verify frame created between existing nodes
- [ ] Click slightly far from node in Free mode → verify wider tolerance (2.5×) still catches the node
- [ ] Try DRAW_SHELL with 4 clicks near existing nodes in Free mode → verify shell created
- [ ] Try shell with one click in empty space in Free mode → verify error message, complete state reset
- [ ] Verify XY/XZ/YZ plane modes still allow node creation (no change in behavior)
- [ ] Enter DRAW_NODE in Free mode → verify auto-switch to XY and console message
- [ ] Verify DRAW_NODE Properties Panel shows "Modo Dibujo de Nodos" title with snap settings
- [ ] Verify Undo works correctly after creating frames/shells in both plane and Free modes

---

#### Step 4 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
