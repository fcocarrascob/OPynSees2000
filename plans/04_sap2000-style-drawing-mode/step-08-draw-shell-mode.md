# Step 8: Draw Shell Mode (4-Click Sequence)

## Goal
Implement the four-click sequence for DRAW_SHELL mode: each click establishes a node (I, J, K, L), with progressive preview lines showing the developing quadrilateral. The fourth click creates the shell element. Uses compound undo for the entire operation (all created nodes + element).

## Prerequisites
Steps 1–7 must be completed and committed.

---

### Step-by-Step Instructions

#### 8.1 — Add shell drawing state to `MainWindow`

- [x] Open `gui/main_window.py`
- [x] In `__init__`, after the frame state attributes (`self._frame_first_coords`), add:

```python
        # Estado de dibujo de shells (4 clics)
        self._shell_nodes: list[int] = []       # tags de nodos acumulados (0-3)
        self._shell_coords: list[tuple[float, float, float]] = []  # coords de nodos acumulados
```

#### 8.2 — Implement `_handle_draw_shell`

- [x] Replace the placeholder `_handle_draw_shell` method with:

```python
    def _handle_draw_shell(self, x: float, y: float, z: float) -> None:
        """Maneja clics en modo DRAW_SHELL (secuencia de 4 clics)."""
        from gui.viewport.picking import find_closest_node
        from gui.core.model_data import Node, Element, ElementType

        click_num = len(self._shell_nodes) + 1  # 1, 2, 3, o 4
        node_labels = {1: "I", 2: "J", 3: "K", 4: "L"}

        # Resolver nodo: snap a existente o crear nuevo
        existing = find_closest_node(self._model, (x, y, z), tolerance=0.15)
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
            all_commands.append(DictChangeCommand(
                target_dict=self._model.elements,
                key=elem_tag,
                old_value=None,
                new_value=element,
                desc=f"Crear shell {elem_tag}",
            ))

            # Ejecutar como comando compuesto
            tags_str = "→".join(str(t) for t in self._shell_nodes)
            if len(all_commands) == 1:
                self._undo_mgr.execute(all_commands[0])
            else:
                compound = CompoundUndoCommand(
                    all_commands,
                    desc=f"Crear shell {elem_tag} [{tags_str}]",
                )
                self._undo_mgr.execute(compound)

            self._refresh_all()
            self._console.log_success(
                f"Shell {elem_tag} creado: [{tags_str}] ShellMITC4"
            )

            # Reset para siguiente shell (continuo)
            self._shell_nodes.clear()
            self._shell_coords.clear()
            self._viewport.clear_all_previews()
```

#### 8.3 — Implement shell preview on mouse move

- [x] Replace the placeholder `_update_shell_preview` method with:

```python
    def _update_shell_preview(self, x: float, y: float, z: float) -> None:
        """Actualiza preview progresiva de shell durante movimiento del mouse."""
        # Construir lista temporal: nodos confirmados + cursor actual
        preview_pts = list(self._shell_coords) + [(x, y, z)]
        self._viewport.show_preview_shell_lines(preview_pts)
        self._viewport.show_preview_node((x, y, z))
```

#### 8.4 — Handle Escape to cancel shell in progress

- [x] Update the `keyPressEvent` in `MainWindow` to handle shell cancellation. Replace the full method with:

```python
    def keyPressEvent(self, event) -> None:
        """Maneja atajos de teclado globales."""
        if event.key() == Qt.Key.Key_Escape:
            # Cancelar operaciones en progreso
            if self._interaction_mode == InteractionMode.DRAW_FRAME and self._frame_first_node is not None:
                self._frame_first_node = None
                self._frame_first_coords = None
                self._viewport.clear_all_previews()
                self._console.log("Frame cancelado — esperando primer nodo.")
                return
            if self._interaction_mode == InteractionMode.DRAW_SHELL and self._shell_nodes:
                self._shell_nodes.clear()
                self._shell_coords.clear()
                self._viewport.clear_all_previews()
                self._console.log("Shell cancelado — esperando primer nodo.")
                return
            if self._interaction_mode != InteractionMode.SELECT:
                self.set_mode(InteractionMode.SELECT)
                return
        elif event.key() == Qt.Key.Key_R:
            if self._interaction_mode == InteractionMode.DRAW_NODE:
                self._reset_offset()
                self._console.log("Offset reseteado a (0, 0, 0)")
                return
        super().keyPressEvent(event)
```

#### 8.5 — Reset shell state on mode change

- [x] In `set_mode()`, add shell state reset alongside frame state reset. After the frame reset lines, add:

```python
        # Reset shell drawing state
        self._shell_nodes.clear()
        self._shell_coords.clear()
```

The beginning of `set_mode` should now look like:

```python
    def set_mode(self, mode: InteractionMode) -> None:
        """Cambia el modo de interacción activo."""
        old_mode = self._interaction_mode
        self._interaction_mode = mode

        # Reset frame drawing state
        self._frame_first_node = None
        self._frame_first_coords = None

        # Reset shell drawing state
        self._shell_nodes.clear()
        self._shell_coords.clear()

        # Sincronizar toolbar buttons
        ...
```

---

### Step 8 Verification Checklist
- [ ] No build errors — run `python -m gui.main` and verify the window opens
- [ ] Enter "Dibujar Shell" mode
- [ ] Click 1st position — console shows "Shell: nodo I = X":
  - [ ] Preview shows snap indicator
  - [ ] Console shows "Shell: 1/4 nodos — faltan 3"
- [ ] Click 2nd position:
  - [ ] Preview line appears: I → J
  - [ ] Console shows "Shell: 2/4 nodos — faltan 2"
- [ ] Click 3rd position:
  - [ ] Preview shows L-shape: I → J → K
  - [ ] Console shows "Shell: 3/4 nodos — faltan 1"
- [ ] Move mouse before 4th click:
  - [ ] Preview shows developing quad with cursor position
- [ ] Click 4th position:
  - [ ] Shell element created with all 4 nodes
  - [ ] Console shows "Shell X creado: [I→J→K→L] ShellMITC4"
  - [ ] Element appears in viewport (semi-transparent teal)
  - [ ] Element appears in model tree
- [ ] Create second shell continuously (mode stays active)
- [ ] Test with mix of existing and new nodes:
  - [ ] Existing nodes reused (no duplicates)
  - [ ] New nodes created only when no nearby node exists
- [ ] Press Escape at any stage (e.g., after 2 clicks):
  - [ ] Cancels current shell, returns to "waiting for 1st node"
  - [ ] Preview lines disappear
- [ ] Press Escape again:
  - [ ] Returns to SELECT mode
- [ ] Test undo (Ctrl+Z) after creating shell:
  - [ ] Undoes entire shell + created nodes as single operation
- [ ] Test redo (Ctrl+Shift+Z):
  - [ ] Restores shell and nodes
- [ ] Switch modes during shell creation:
  - [ ] Shell state is reset cleanly

---

### Step 8 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
