# Step 2: Implement Plane-Filtered Element Visibility System

## Goal
Add a comprehensive element filtering system to `VTKViewport` that shows ONLY elements completely contained within the active plane. In Free mode, show all elements. This is the CORE feature of the multi-plane drawing system.

## Prerequisites
Step 1 (Fix Ray-Casting) must be completed and committed.

---

### Step-by-Step Instructions

#### 2.1 — Add plane filter state and model reference to VTKViewport.__init__

- [ ] Open `gui/viewport/vtk_widget.py`
- [ ] Find the working plane state variables added in Step 1 (inside `__init__`):

```python
        # Working plane state for ray-casting projection
        self._working_plane_mode: str = "XY"   # "XY", "XZ", "YZ", "Free"
        self._working_plane_elevation: float = 0.0
```

- [ ] Immediately after those lines, add:

```python
        # Plane filter state for element visibility
        self._plane_filter_mode: str = "Free"   # "XY", "XZ", "YZ", "Free"
        self._plane_filter_elevation: float = 0.0
        self._model_ref: "StructuralModel | None" = None  # Reference for re-filtering
```

---

#### 2.2 — Add plane filtering helper methods

- [ ] In `gui/viewport/vtk_widget.py`, add the following two methods right before the `_add_floor_grid` method (around line 127, before the comment `# Grilla de piso`):

```python
    # ------------------------------------------------------------------
    # Plane Filtering Helpers
    # ------------------------------------------------------------------

    def _node_in_active_plane(self, node) -> bool:
        """Determine if node is exactly in the active plane."""
        if self._plane_filter_mode == "Free":
            return True
        elif self._plane_filter_mode == "XY":
            return node.z == self._plane_filter_elevation
        elif self._plane_filter_mode == "XZ":
            return node.y == self._plane_filter_elevation
        elif self._plane_filter_mode == "YZ":
            return node.x == self._plane_filter_elevation
        return True

    def _element_in_active_plane(self, element, model) -> bool:
        """Determine if ALL nodes of element are in the active plane."""
        if self._plane_filter_mode == "Free":
            return True
        for nt in element.node_tags:
            node = model.nodes.get(nt)
            if node is None or not self._node_in_active_plane(node):
                return False
        return True

```

---

#### 2.3 — Modify `display_model` to store model reference

- [ ] Find the `display_model` method:

```python
    def display_model(self, model: StructuralModel) -> None:
        """Renderiza el modelo completo en el viewport."""
        self.plotter.clear()
```

- [ ] Replace it with:

```python
    def display_model(self, model: StructuralModel) -> None:
        """Renderiza el modelo completo en el viewport."""
        self._model_ref = model  # Keep reference for re-filtering
        self.plotter.clear()
```

---

#### 2.4 — Add plane filter to `_add_elements`

- [ ] Find the `_add_elements` method. Locate the for loop that iterates over elements. The current code starts with:

```python
        for elem in model.elements.values():
            if elem.is_shell:
                continue
            ni = model.nodes.get(elem.node_i)
            nj = model.nodes.get(elem.node_j)
```

- [ ] Replace it with (adding the filter check):

```python
        for elem in model.elements.values():
            if elem.is_shell:
                continue
            # Plane filter: skip if not in active plane
            if not self._element_in_active_plane(elem, model):
                continue
            ni = model.nodes.get(elem.node_i)
            nj = model.nodes.get(elem.node_j)
```

---

#### 2.5 — Add plane filter to `_add_shells`

- [ ] Find the `_add_shells` method. Locate the for loop:

```python
        for elem in model.elements.values():
            if not elem.is_shell:
                continue
            nodes = []
            for nt in elem.node_tags:
```

- [ ] Replace it with:

```python
        for elem in model.elements.values():
            if not elem.is_shell:
                continue
            # Plane filter: skip if not in active plane
            if not self._element_in_active_plane(elem, model):
                continue
            nodes = []
            for nt in elem.node_tags:
```

---

#### 2.6 — Add plane filter to `_add_nodes`

- [ ] Find the `_add_nodes` method:

```python
    def _add_nodes(self, model: StructuralModel) -> None:
        """Dibuja esferas en cada nodo libre (no empotrado)."""
        free_coords = [
            [n.x, n.y, n.z]
            for n in model.nodes.values()
            if not n.is_fully_fixed
        ]
```

- [ ] Replace with:

```python
    def _add_nodes(self, model: StructuralModel) -> None:
        """Dibuja esferas en cada nodo libre (no empotrado), filtrado por plano."""
        free_coords = [
            [n.x, n.y, n.z]
            for n in model.nodes.values()
            if not n.is_fully_fixed and self._node_in_active_plane(n)
        ]
```

---

#### 2.7 — Add plane filter to `_add_supports`

- [ ] Find the `_add_supports` method:

```python
    def _add_supports(self, model: StructuralModel) -> None:
        """Dibuja conos invertidos en nodos empotrados."""
        fixed_coords = [
            [n.x, n.y, n.z]
            for n in model.nodes.values()
            if n.is_fully_fixed
        ]
```

- [ ] Replace with:

```python
    def _add_supports(self, model: StructuralModel) -> None:
        """Dibuja conos invertidos en nodos empotrados, filtrado por plano."""
        fixed_coords = [
            [n.x, n.y, n.z]
            for n in model.nodes.values()
            if n.is_fully_fixed and self._node_in_active_plane(n)
        ]
```

---

#### 2.8 — Add plane filter to `_add_node_labels`

- [ ] Find the `_add_node_labels` method. The current iteration is:

```python
        points = []
        labels = []
        for tag, node in model.nodes.items():
            points.append([node.x, node.y, node.z])
            labels.append(str(tag))
```

- [ ] Replace with:

```python
        points = []
        labels = []
        for tag, node in model.nodes.items():
            if not self._node_in_active_plane(node):
                continue
            points.append([node.x, node.y, node.z])
            labels.append(str(tag))
```

---

#### 2.9 — Add plane filter to `_add_element_labels`

- [ ] Find the `_add_element_labels` method. The current iteration is:

```python
        for tag, elem in model.elements.items():
            ni = model.nodes.get(elem.node_i)
            nj = model.nodes.get(elem.node_j)
            if ni is None or nj is None:
                continue
```

- [ ] Replace with:

```python
        for tag, elem in model.elements.items():
            if not self._element_in_active_plane(elem, model):
                continue
            ni = model.nodes.get(elem.node_i)
            nj = model.nodes.get(elem.node_j)
            if ni is None or nj is None:
                continue
```

---

#### 2.10 — Add plane filter to `_add_load_arrows`

- [ ] Find the `_add_load_arrows` method. Inside the nested loops, after getting the node:

```python
                node = model.nodes.get(load.node_tag)
                if node is None:
                    continue
                origin = [node.x, node.y, node.z]
```

- [ ] Replace with:

```python
                node = model.nodes.get(load.node_tag)
                if node is None:
                    continue
                if not self._node_in_active_plane(node):
                    continue
                origin = [node.x, node.y, node.z]
```

---

#### 2.11 — Add `set_plane_filter` public method

- [ ] In `gui/viewport/vtk_widget.py`, find the `set_working_plane` method added in Step 1 and add the following new method right after it:

```python
    def set_plane_filter(self, mode: str, elevation: float) -> None:
        """Update plane filter and re-render model.

        Parameters
        ----------
        mode : str
            "XY", "XZ", "YZ" o "Free".
        elevation : float
            Elevación del eje bloqueado.
        """
        self._plane_filter_mode = mode
        self._plane_filter_elevation = elevation

        # Re-render if model is loaded
        if self._model_ref is not None:
            self.display_model(self._model_ref)
```

---

#### 2.12 — Connect plane filter to `MainWindow._on_snap_setting_changed`

- [ ] Open `gui/main_window.py`
- [ ] Find the `_on_snap_setting_changed` method. After the existing `set_working_plane` call (added in Step 1), add the plane filter update. The block should look like:

```python
        # Actualizar visual del plano de trabajo
        if field_name in ("working_plane_mode", "working_plane_elevation", "snap_spacing"):
            self._viewport.update_working_plane_visual(
                template.working_plane_mode,
                template.working_plane_elevation,
                template.snap_spacing,
            )

            # Actualizar plano de raycasting para proyección
            self._viewport.set_working_plane(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
```

- [ ] Add right after the `set_working_plane` call:

```python
            # Actualizar filtro de visibilidad por plano
            self._viewport.set_plane_filter(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
```

---

#### 2.13 — Set plane filter when entering drawing mode

- [ ] In `gui/main_window.py`, find the `set_mode` method where the working plane is synced (the lines added in Step 1):

```python
            # Sincronizar plano de raycasting con template
            self._viewport.set_working_plane(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
```

- [ ] Add right after:

```python
            # Sincronizar filtro de visibilidad por plano
            self._viewport.set_plane_filter(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
```

---

#### 2.14 — Reset plane filter when returning to SELECT mode

- [ ] In the `set_mode` method, find the SELECT mode block:

```python
        if mode == InteractionMode.SELECT:
            self._viewport.enable_picking(self._model)
            self._viewport.set_drawing_mode(False)
            self._viewport.clear_all_previews()
            self._viewport.hide_working_plane_visual()
            self._set_offset_widgets_visible(False)
            self._properties.clear()
            self._update_statusbar()
```

- [ ] Add the plane filter reset right before `self._properties.clear()`:

```python
        if mode == InteractionMode.SELECT:
            self._viewport.enable_picking(self._model)
            self._viewport.set_drawing_mode(False)
            self._viewport.clear_all_previews()
            self._viewport.hide_working_plane_visual()
            self._viewport.set_plane_filter("Free", 0.0)  # Show all elements
            self._set_offset_widgets_visible(False)
            self._properties.clear()
            self._update_statusbar()
```

---

### Step 2 Verification Checklist

- [ ] No import or syntax errors
- [ ] Load the demo model (has 27 nodes across Z=0, Z=3.5, Z=7.0)
- [ ] Enter DRAW_FRAME mode with XY plane at Z=0 → verify only Z=0 nodes and ground-floor beams visible (supports visible too since they are at Z=0)
- [ ] Change elevation to Z=3.5 → verify only Z=3.5 nodes and first-floor beams visible, other floors disappear
- [ ] Change elevation to Z=7.0 → verify only Z=7.0 nodes and second-floor beams visible
- [ ] Columns (spanning Z=0→3.5 or Z=3.5→7.0) should NOT be visible in any single plane view (they span multiple planes)
- [ ] Switch to Free mode → verify ALL elements visible again (full model)
- [ ] Exit to SELECT mode → verify ALL elements visible (filter reset to Free)
- [ ] Test with labels enabled → verify labels also filtered
- [ ] Test with loads visible → verify load arrows also filtered
- [ ] Create a new shell with 4 nodes at Z=3.5 → verify visible only in XY Z=3.5 view
- [ ] Performance: switching planes on demo model should be instant (no lag)

---

#### Step 2 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
