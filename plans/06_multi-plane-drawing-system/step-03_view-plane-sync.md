# Step 3: Add Automatic View-Plane Synchronization

## Goal
Implement automatic camera view switching AND plane filter updates when entering drawing modes or changing working plane. XY → top view, XZ → front view, YZ → side view, Free → isometric. View toolbar buttons also update the working plane when in drawing mode (bidirectional sync).

## Prerequisites
Steps 1 and 2 must be completed and committed.

---

### Step-by-Step Instructions

#### 3.1 — Add `_sync_plane_and_view` method to MainWindow

- [ ] Open `gui/main_window.py`
- [ ] Add the following method right after the `_update_drawing_statusbar` method (around line 780):

```python
    def _sync_plane_and_view(self, plane_mode: str, elevation: float) -> None:
        """Sync camera view, ray-casting, and element filtering to plane.

        Parameters
        ----------
        plane_mode : str
            "XY", "XZ", "YZ" o "Free".
        elevation : float
            Elevación del eje bloqueado por el plano.
        """
        # Update VTK viewport ray-casting plane
        self._viewport.set_working_plane(plane_mode, elevation)

        # Update element visibility filter
        self._viewport.set_plane_filter(plane_mode, elevation)

        # Update camera view
        if plane_mode == "XY":
            self._viewport.set_view_xy()
        elif plane_mode == "XZ":
            self._viewport.set_view_xz()
        elif plane_mode == "YZ":
            self._viewport.set_view_yz()
        else:  # Free
            self._viewport.reset_view()

        # Update working plane visual
        template = self._model.drawing_template
        self._viewport.update_working_plane_visual(
            plane_mode, elevation, template.snap_spacing,
        )

        # Update status bar
        self._update_drawing_statusbar()
```

---

#### 3.2 — Use `_sync_plane_and_view` when entering drawing mode

- [ ] In `gui/main_window.py`, find the `set_mode` method's `else` block (drawing modes). Replace the block that currently reads:

```python
            # Sincronizar snap manager con template
            template = self._model.drawing_template
            self._snap_mgr.spacing = template.snap_spacing

            # Sincronizar plano de raycasting con template
            self._viewport.set_working_plane(
                template.working_plane_mode,
                template.working_plane_elevation,
            )

            # Sincronizar filtro de visibilidad por plano
            self._viewport.set_plane_filter(
                template.working_plane_mode,
                template.working_plane_elevation,
            )

            # Mostrar plano de trabajo visual
            self._viewport.update_working_plane_visual(
                template.working_plane_mode,
                template.working_plane_elevation,
                template.snap_spacing,
            )

            # Actualizar status bar con info del plano
            self._update_drawing_statusbar()
```

- [ ] Replace with:

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

---

#### 3.3 — Use `_sync_plane_and_view` from snap setting changed callback

- [ ] Find the `_on_snap_setting_changed` method. Replace the block for working_plane_mode/elevation/spacing changes:

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

            # Actualizar filtro de visibilidad por plano
            self._viewport.set_plane_filter(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
```

- [ ] Replace with:

```python
        # Actualizar vista, raycasting y filtro cuando cambia plano/elevación/spacing
        if field_name in ("working_plane_mode", "working_plane_elevation", "snap_spacing"):
            self._sync_plane_and_view(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
```

---

#### 3.4 — Add bidirectional sync: view buttons update plane when in drawing mode

- [ ] Find the `_build_toolbar` method in `gui/main_window.py`. Locate the view toolbar buttons. Currently they are:

```python
        act_iso = QAction("3D", self)
        act_iso.setToolTip("Vista isométrica (0)")
        act_iso.triggered.connect(self._viewport.reset_view)
        tb.addAction(act_iso)

        act_xy = QAction("XY", self)
        act_xy.setToolTip("Vista planta (7)")
        act_xy.triggered.connect(self._viewport.set_view_xy)
        tb.addAction(act_xy)

        act_xz = QAction("XZ", self)
        act_xz.setToolTip("Vista frontal (1)")
        act_xz.triggered.connect(self._viewport.set_view_xz)
        tb.addAction(act_xz)

        act_yz = QAction("YZ", self)
        act_yz.setToolTip("Vista lateral (3)")
        act_yz.triggered.connect(self._viewport.set_view_yz)
        tb.addAction(act_yz)
```

- [ ] Replace with:

```python
        act_iso = QAction("3D", self)
        act_iso.setToolTip("Vista isométrica (0)")
        act_iso.triggered.connect(self._on_view_iso)
        tb.addAction(act_iso)

        act_xy = QAction("XY", self)
        act_xy.setToolTip("Vista planta (7)")
        act_xy.triggered.connect(self._on_view_xy)
        tb.addAction(act_xy)

        act_xz = QAction("XZ", self)
        act_xz.setToolTip("Vista frontal (1)")
        act_xz.triggered.connect(self._on_view_xz)
        tb.addAction(act_xz)

        act_yz = QAction("YZ", self)
        act_yz.setToolTip("Vista lateral (3)")
        act_yz.triggered.connect(self._on_view_yz)
        tb.addAction(act_yz)
```

---

#### 3.5 — Add the view handler methods

- [ ] Add the following methods after `_sync_plane_and_view` in `gui/main_window.py`:

```python
    def _on_view_iso(self) -> None:
        """Handle 3D/Isometric view button."""
        if self._interaction_mode != InteractionMode.SELECT:
            # In drawing mode: switch plane to Free
            template = self._model.drawing_template
            template.working_plane_mode = "Free"
            self._sync_plane_and_view("Free", template.working_plane_elevation)
            # Refresh properties panel to reflect change
            self._refresh_drawing_properties()
        else:
            self._viewport.reset_view()

    def _on_view_xy(self) -> None:
        """Handle XY view button."""
        if self._interaction_mode != InteractionMode.SELECT:
            template = self._model.drawing_template
            template.working_plane_mode = "XY"
            self._sync_plane_and_view("XY", template.working_plane_elevation)
            self._refresh_drawing_properties()
        else:
            self._viewport.set_view_xy()

    def _on_view_xz(self) -> None:
        """Handle XZ view button."""
        if self._interaction_mode != InteractionMode.SELECT:
            template = self._model.drawing_template
            template.working_plane_mode = "XZ"
            self._sync_plane_and_view("XZ", template.working_plane_elevation)
            self._refresh_drawing_properties()
        else:
            self._viewport.set_view_xz()

    def _on_view_yz(self) -> None:
        """Handle YZ view button."""
        if self._interaction_mode != InteractionMode.SELECT:
            template = self._model.drawing_template
            template.working_plane_mode = "YZ"
            self._sync_plane_and_view("YZ", template.working_plane_elevation)
            self._refresh_drawing_properties()
        else:
            self._viewport.set_view_yz()

    def _refresh_drawing_properties(self) -> None:
        """Refresh properties panel when in a drawing mode."""
        if self._interaction_mode == InteractionMode.DRAW_FRAME:
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

#### 3.6 — Update menu bar view actions to use the new handlers

- [ ] In `_build_menubar`, find the view menu actions:

```python
        act_iso = QAction("Vista isométrica", self)
        act_iso.setShortcut(QKeySequence("0"))
        act_iso.triggered.connect(self._viewport.reset_view)
        m_display.addAction(act_iso)

        act_xy = QAction("Vista XY (planta)", self)
        act_xy.setShortcut(QKeySequence("7"))
        act_xy.triggered.connect(self._viewport.set_view_xy)
        m_display.addAction(act_xy)

        act_xz = QAction("Vista XZ (frontal)", self)
        act_xz.setShortcut(QKeySequence("1"))
        act_xz.triggered.connect(self._viewport.set_view_xz)
        m_display.addAction(act_xz)

        act_yz = QAction("Vista YZ (lateral)", self)
        act_yz.setShortcut(QKeySequence("3"))
        act_yz.triggered.connect(self._viewport.set_view_yz)
        m_display.addAction(act_yz)
```

- [ ] Replace with:

```python
        act_iso = QAction("Vista isométrica", self)
        act_iso.setShortcut(QKeySequence("0"))
        act_iso.triggered.connect(self._on_view_iso)
        m_display.addAction(act_iso)

        act_xy = QAction("Vista XY (planta)", self)
        act_xy.setShortcut(QKeySequence("7"))
        act_xy.triggered.connect(self._on_view_xy)
        m_display.addAction(act_xy)

        act_xz = QAction("Vista XZ (frontal)", self)
        act_xz.setShortcut(QKeySequence("1"))
        act_xz.triggered.connect(self._on_view_xz)
        m_display.addAction(act_xz)

        act_yz = QAction("Vista YZ (lateral)", self)
        act_yz.setShortcut(QKeySequence("3"))
        act_yz.triggered.connect(self._on_view_yz)
        m_display.addAction(act_yz)
```

---

### Step 3 Verification Checklist

- [ ] No import or syntax errors
- [ ] Enter DRAW_FRAME mode with XY plane Z=0 → verify camera snaps to top view (XY) + only Z=0 elements visible
- [ ] Change to XZ plane in Properties Panel → verify camera snaps to front view + only matching elements visible
- [ ] Click YZ view button while in drawing mode → verify plane updates to YZ, camera to side view, properties panel reflects YZ
- [ ] Click 3D button while in drawing mode → verify plane updates to Free, camera to isometric, all elements visible
- [ ] Change elevation from 0 to 3.5 → verify filter updates, camera stays same orientation
- [ ] Exit to SELECT mode (Escape) → verify switches to all elements visible, camera unchanged
- [ ] In SELECT mode, click XY/XZ/YZ/3D buttons → verify they only change camera (no plane filter changes)
- [ ] Keyboard shortcuts (0/1/3/7) → verify they also use bidirectional sync in drawing mode
- [ ] Verify `_refresh_viewport` (F6) still works
- [ ] Verify deformed view toggle still works

---

#### Step 3 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
