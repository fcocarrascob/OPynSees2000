# Step 1: Fix Ray-Casting for XZ/YZ Planes

## Goal
Replace the hardcoded Z-plane intersection in `_screen_to_world()` with a generalized ray-plane intersection that adapts to the current working plane mode (XY, XZ, YZ, Free), enabling correct 3D coordinate picking in all plane modes.

## Prerequisites
Make sure you are on the `feature/multi-plane-drawing-system` branch before beginning.
If not, create it from the current branch:

```bash
git checkout -b feature/multi-plane-drawing-system
```

---

### Step-by-Step Instructions

#### 1.1 — Add working plane mode/elevation state and `set_working_plane()` method

- [ ] Open `gui/viewport/vtk_widget.py`
- [ ] Replace the existing `_working_plane_z` instance variable and the `set_working_plane_z` method with a generalized plane tracking system.
- [ ] Find this block in `__init__` (around line 88):

```python
        # Working plane Z para proyección de rayos
        self._working_plane_z: float = 0.0
```

- [ ] Replace it with the following:

```python
        # Working plane state for ray-casting projection
        self._working_plane_mode: str = "XY"   # "XY", "XZ", "YZ", "Free"
        self._working_plane_elevation: float = 0.0
```

---

#### 1.2 — Replace `set_working_plane_z` with `set_working_plane`

- [ ] Find the `set_working_plane_z` method (around line 683):

```python
    def set_working_plane_z(self, z: float) -> None:
        """Establece la elevación del plano de trabajo para proyección."""
        self._working_plane_z = z
```

- [ ] Replace it with:

```python
    def set_working_plane(self, mode: str, elevation: float) -> None:
        """Establece el plano de trabajo activo para proyección de rayos.

        Parameters
        ----------
        mode : str
            "XY", "XZ", "YZ" o "Free".
        elevation : float
            Elevación del eje bloqueado por el plano.
        """
        self._working_plane_mode = mode
        self._working_plane_elevation = elevation
```

---

#### 1.3 — Replace _screen_to_world with generalized ray-plane intersection

- [ ] Find the entire `_screen_to_world` method (starts around line 697) and replace it completely.
- [ ] Delete the existing method and paste this new version:

```python
    def _screen_to_world(self, screen_x: int, screen_y: int) -> tuple[float, float, float] | None:
        """
        Convierte coordenadas de pantalla a coordenadas del mundo 3D,
        proyectando el rayo de la cámara sobre el plano de trabajo activo.

        Planos y normales:
          - XY: normal=(0,0,1), punto=(0,0,elevation)
          - XZ: normal=(0,1,0), punto=(0,elevation,0)
          - YZ: normal=(1,0,0), punto=(elevation,0,0)
          - Free: normal=(0,0,1), punto=(0,0,0) (fallback al plano Z=0)

        Retorna None si el rayo es paralelo al plano.
        """
        renderer = self.plotter.renderer

        # Obtener dimensiones del viewport
        size = self.plotter.window_size
        if size[0] == 0 or size[1] == 0:
            return None

        # Qt da Y desde arriba; VTK espera Y desde abajo
        display_x = screen_x
        display_y = size[1] - screen_y

        # Cámara
        camera = renderer.GetActiveCamera()
        if camera is None:
            return None

        # Viewport normalization
        vp = renderer.GetViewport()
        vp_width = size[0] * (vp[2] - vp[0])
        vp_height = size[1] * (vp[3] - vp[1])

        if vp_width == 0 or vp_height == 0:
            return None

        import vtk  # noqa: F811

        # Convertir display coords a world coords en near/far planes
        renderer.SetDisplayPoint(display_x, display_y, 0.0)
        renderer.DisplayToWorld()
        near_point = list(renderer.GetWorldPoint()[:3])

        renderer.SetDisplayPoint(display_x, display_y, 1.0)
        renderer.DisplayToWorld()
        wp = renderer.GetWorldPoint()
        if wp[3] != 0:
            far_point = [wp[i] / wp[3] for i in range(3)]
        else:
            far_point = list(wp[:3])

        # Ray direction
        ray_dir = [far_point[i] - near_point[i] for i in range(3)]

        # Determine plane normal and point based on working plane mode
        mode = self._working_plane_mode
        elev = self._working_plane_elevation

        if mode == "XY":
            plane_normal = [0.0, 0.0, 1.0]
            plane_point = [0.0, 0.0, elev]
        elif mode == "XZ":
            plane_normal = [0.0, 1.0, 0.0]
            plane_point = [0.0, elev, 0.0]
        elif mode == "YZ":
            plane_normal = [1.0, 0.0, 0.0]
            plane_point = [elev, 0.0, 0.0]
        else:
            # Free mode: fallback to Z=0 plane
            plane_normal = [0.0, 0.0, 1.0]
            plane_point = [0.0, 0.0, 0.0]

        # Ray-plane intersection: t = dot(plane_point - ray_origin, normal) / dot(ray_dir, normal)
        denom = sum(ray_dir[i] * plane_normal[i] for i in range(3))
        if abs(denom) < 1e-12:
            return None  # Rayo paralelo al plano

        diff = [plane_point[i] - near_point[i] for i in range(3)]
        t = sum(diff[i] * plane_normal[i] for i in range(3)) / denom

        world_x = near_point[0] + t * ray_dir[0]
        world_y = near_point[1] + t * ray_dir[1]
        world_z = near_point[2] + t * ray_dir[2]

        return (world_x, world_y, world_z)
```

---

#### 1.4 — Update `MainWindow._on_snap_setting_changed` to use `set_working_plane`

- [ ] Open `gui/main_window.py`
- [ ] Find the `_on_snap_setting_changed` method (around line 730) and replace the block that updates the raycasting plane. Find this code:

```python
            # Actualizar plano Z de raycasting para proyección
            if template.working_plane_mode == "XY":
                self._viewport.set_working_plane_z(template.working_plane_elevation)
            elif template.working_plane_mode == "Free":
                self._viewport.set_working_plane_z(0.0)
            # Para XZ y YZ, el raycasting sigue proyectando a Z=working_plane_z
            # pero el snap_with_plane corregirá el eje apropiado
```

- [ ] Replace it with:

```python
            # Actualizar plano de raycasting para proyección
            self._viewport.set_working_plane(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
```

---

#### 1.5 — Update `set_mode` to sync working plane on entering drawing mode

- [ ] In the same `gui/main_window.py`, find the `set_mode` method, specifically the `else` block where drawing mode is activated. After the line:

```python
            self._snap_mgr.spacing = template.snap_spacing
```

- [ ] Add the following line immediately after it:

```python
            # Sincronizar plano de raycasting con template
            self._viewport.set_working_plane(
                template.working_plane_mode,
                template.working_plane_elevation,
            )
```

---

### Step 1 Verification Checklist

- [ ] No import errors or syntax errors when running the application
- [ ] Enter DRAW_NODE mode with XY plane at Z=3.0 → click in viewport → verify node Z-coordinate is exactly 3.0
- [ ] Switch to XZ plane at Y=5.0 → click in viewport → verify node Y-coordinate is exactly 5.0
- [ ] Switch to YZ plane at X=2.0 → click in viewport → verify node X-coordinate is exactly 2.0
- [ ] Switch to Free mode → click in viewport → verify all coordinates are free (Z=0 fallback)
- [ ] Test Shift-override in XZ mode → verify it temporarily uses Free snap
- [ ] Verify frame drawing still works correctly (2-click workflow) in all plane modes
- [ ] Verify shell drawing still works correctly (4-click workflow) in all plane modes

---

#### Step 1 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
