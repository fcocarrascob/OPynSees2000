# Step 7: Draw Frame Mode Implementation (2-Node Elements)

## Goal
Implement the two-click sequence for DRAW_FRAME mode to create 2-node linear elements (beams, columns, braces). First click establishes node I, second click establishes node J and creates the frame element. Snaps to existing nodes within 0.15 units tolerance. Uses compound undo for the entire operation. Shows preview line during second click.

## Prerequisites
Steps 1–6 must be completed and committed.

---

### Step-by-Step Instructions

#### 7.1 — Add frame drawing state to `MainWindow`

- [x] Open `gui/main_window.py`
- [x] In `__init__`, after `self._snap_mgr` creation, add:

```python
        # Estado de dibujo de frames (2 clics)
        self._frame_first_node: int | None = None  # tag del primer nodo (None = esperando 1er clic)
        self._frame_first_coords: tuple[float, float, float] | None = None
```

#### 7.2 — Add node snapping helper

- [x] Add this utility method to `MainWindow`, in the Mode switching section:

```python
    def _find_or_create_node(
        self, x: float, y: float, z: float, tolerance: float = 0.15
    ) -> tuple[int, bool]:
        """
        Busca un nodo existente cercano o crea uno nuevo.

        Returns:
            (tag, was_created) — tag del nodo y si fue creado nuevo.
        """
        from gui.viewport.picking import find_closest_node
        existing = find_closest_node(self._model, (x, y, z), tolerance=tolerance)
        if existing is not None:
            return (existing, False)

        tag = self._model.next_node_tag()
        from gui.core.model_data import Node
        node = Node(tag=tag, x=x, y=y, z=z)
        return (tag, True)
```

#### 7.3 — Implement `_handle_draw_frame`

- [x] Replace the placeholder `_handle_draw_frame` method with:

```python
    def _handle_draw_frame(self, x: float, y: float, z: float) -> None:
        """Maneja clics en modo DRAW_FRAME (secuencia de 2 clics)."""
        from gui.viewport.picking import find_closest_node
        from gui.core.model_data import Node, Element, ElementType

        if self._frame_first_node is None:
            # === PRIMER CLIC: establecer nodo I ===
            existing = find_closest_node(self._model, (x, y, z), tolerance=0.15)
            if existing is not None:
                self._frame_first_node = existing
                node = self._model.nodes[existing]
                self._frame_first_coords = (node.x, node.y, node.z)
                self._console.log(
                    f"Frame: nodo I = {existing} (existente)"
                )
            else:
                # Crear nodo nuevo como primer nodo
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
            existing_j = find_closest_node(self._model, (x, y, z), tolerance=0.15)
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

            # Crear elemento frame
            elem_tag = self._model.next_element_tag()
            # Si hay commands pendientes (nodo J nuevo), calcular tag correcto
            # El next_element_tag() ya es correcto porque solo creamos nodos
            element = Element(
                tag=elem_tag,
                elem_type=ElementType.ELASTIC_BEAM_COLUMN,
                node_i=self._frame_first_node,
                node_j=node_j_tag,
                section_tag=None,
                transf_tag=None,
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
                    desc=f"Crear frame {elem_tag} [{self._frame_first_node}→{node_j_tag}]",
                )
                self._undo_mgr.execute(compound)

            self._refresh_all()
            self._console.log_success(
                f"Frame {elem_tag} creado: [{self._frame_first_node}→{node_j_tag}] "
                f"elasticBeamColumn"
            )

            # Reset para siguiente frame (continuo)
            self._frame_first_node = None
            self._frame_first_coords = None
            self._viewport.clear_all_previews()
```

#### 7.4 — Implement frame preview on mouse move

- [x] Replace the placeholder `_update_frame_preview` method with:

```python
    def _update_frame_preview(self, x: float, y: float, z: float) -> None:
        """Actualiza preview de línea durante el segundo clic del frame."""
        if self._frame_first_coords is not None:
            # Mostrar preview line desde primer nodo hasta cursor
            self._viewport.show_preview_line(self._frame_first_coords, (x, y, z))
            self._viewport.show_preview_node((x, y, z))
        else:
            # Antes del primer clic, solo mostrar preview node
            self._viewport.show_preview_node((x, y, z))
```

#### 7.5 — Handle Escape to cancel frame in progress

- [x] Update the `keyPressEvent` in `MainWindow` to also reset frame state:

```python
    def keyPressEvent(self, event) -> None:
        """Maneja atajos de teclado globales."""
        if event.key() == Qt.Key.Key_Escape:
            if self._interaction_mode == InteractionMode.DRAW_FRAME and self._frame_first_node is not None:
                # Cancelar frame en progreso, volver al primer clic
                self._frame_first_node = None
                self._frame_first_coords = None
                self._viewport.clear_all_previews()
                self._console.log("Frame cancelado — esperando primer nodo.")
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

#### 7.6 — Reset frame state on mode change

- [x] In `set_mode()`, add frame state reset at the beginning of the method (after `old_mode = ...`):

```python
        # Reset frame drawing state
        self._frame_first_node = None
        self._frame_first_coords = None
```

---

### Step 7 Verification Checklist
- [ ] No build errors — run `python -m gui.main` and verify the window opens
- [ ] Enter "Dibujar Frame" mode
- [ ] Click first position — console shows "Frame: nodo I = X":
  - [ ] If near existing node (≤0.15 units): snaps to existing node
  - [ ] If no nearby node: creates new node
- [ ] Move mouse after first click:
  - [ ] Orange preview line stretches from first node to cursor
  - [ ] Snap indicator appears at grid points
- [ ] Click second position — frame element created:
  - [ ] Console shows "Frame X creado: [I→J] elasticBeamColumn"
  - [ ] Element appears in viewport and model tree
  - [ ] Correct element type (elasticBeamColumn)
- [ ] Create second frame continuously (mode stays active)
- [ ] Press Escape during 2nd click:
  - [ ] Cancels current frame, returns to "waiting for 1st node"
  - [ ] Preview line disappears
- [ ] Press Escape again:
  - [ ] Returns to SELECT mode
- [ ] Test undo (Ctrl+Z):
  - [ ] Undoes entire frame operation (element + created nodes)
- [ ] Test redo (Ctrl+Shift+Z):
  - [ ] Restores the frame and nodes
- [ ] Create frame between two existing nodes — no new nodes created, only element

---

### Step 7 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
