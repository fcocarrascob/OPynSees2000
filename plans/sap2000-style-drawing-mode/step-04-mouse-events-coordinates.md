# Step 4: Viewport Mouse Event Handling & Coordinate Conversion

## Goal
Override mouse events in `VTKViewport` to capture clicks and mouse moves in drawing modes. Implement screen-to-world coordinate conversion via VTK ray casting to a working plane (Z=0). Integrate snap system. Emit signals with world coordinates for drawing commands.

## Prerequisites
Steps 1–3 must be completed and committed.

---

### Step-by-Step Instructions

#### 4.1 — Add new signals and state to `VTKViewport`

- [x] Open `gui/viewport/vtk_widget.py`
- [x] Add a new import at the top of the file, with the existing imports from `PySide6.QtCore`:

```python
from PySide6.QtCore import Signal, Qt, QTimer
```

- [x] Add the `QApplication` import to the PySide6.QtWidgets import:

```python
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
```

- [x] Add new signals to the `VTKViewport` class, after the existing `item_picked` signal:

```python
    # Señales para modo dibujo
    drawing_click = Signal(float, float, float)       # clic con coords mundo (snapped)
    drawing_mouse_move = Signal(float, float, float)   # movimiento con coords mundo (snapped)
```

- [x] In `__init__`, after `self._snap_mgr`, add:

```python
        # Working plane Z para proyección de rayos
        self._working_plane_z: float = 0.0

        # Throttle para mouse move (50ms)
        self._move_timer = QTimer(self)
        self._move_timer.setSingleShot(True)
        self._move_timer.setInterval(50)
        self._move_timer.timeout.connect(self._emit_throttled_move)
        self._pending_move_coords: tuple[float, float, float] | None = None
```

#### 4.2 — Implement screen-to-world coordinate conversion

- [x] Add these methods to `VTKViewport`, after `set_snap_manager`:

```python
    def set_working_plane_z(self, z: float) -> None:
        """Establece la elevación del plano de trabajo para proyección."""
        self._working_plane_z = z

    def _screen_to_world(self, screen_x: int, screen_y: int) -> tuple[float, float, float] | None:
        """
        Convierte coordenadas de pantalla a coordenadas del mundo 3D,
        proyectando el rayo de la cámara sobre el plano Z = _working_plane_z.

        Retorna None si el rayo es paralelo al plano.
        """
        renderer = self.plotter.renderer

        # Obtener dimensiones del viewport
        size = self.plotter.window_size
        if size[0] == 0 or size[1] == 0:
            return None

        # Normalizar coordenadas de pantalla [0, 1]
        # Qt da Y desde arriba; VTK espera Y desde abajo
        display_x = screen_x
        display_y = size[1] - screen_y

        # Usar VTK picker para obtener el punto en el plano de trabajo
        # Crear un WorldPointPicker
        picker = self.plotter.renderer.GetRenderWindow().GetInteractor()
        if picker is None:
            return None

        # Método alternativo: ray casting manual
        # Obtener posición y dirección del rayo de la cámara
        camera = renderer.GetActiveCamera()
        if camera is None:
            return None

        # Coordenadas normalizadas del viewport
        vp = renderer.GetViewport()
        vp_width = size[0] * (vp[2] - vp[0])
        vp_height = size[1] * (vp[3] - vp[1])

        if vp_width == 0 or vp_height == 0:
            return None

        # Display to normalized viewport
        norm_x = (display_x - size[0] * vp[0]) / vp_width
        norm_y = (display_y - size[1] * vp[1]) / vp_height

        # Usar el coordinate converter de VTK
        coord = renderer.GetActiveCamera().GetPosition()
        focal = renderer.GetActiveCamera().GetFocalPoint()

        import vtk
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

        # Intersect with Z = _working_plane_z
        # near_point + t * ray_dir = (x, y, _working_plane_z)
        # near_point[2] + t * ray_dir[2] = _working_plane_z
        if abs(ray_dir[2]) < 1e-12:
            return None  # Rayo paralelo al plano

        t = (self._working_plane_z - near_point[2]) / ray_dir[2]
        world_x = near_point[0] + t * ray_dir[0]
        world_y = near_point[1] + t * ray_dir[1]
        world_z = self._working_plane_z

        return (world_x, world_y, world_z)

    def _apply_snap(self, coords: tuple[float, float, float]) -> tuple[float, float, float]:
        """Aplica snap si está habilitado."""
        if self._snap_mgr and self._snap_mgr.enabled:
            return self._snap_mgr.snap_point(coords)
        return coords
```

#### 4.3 — Override mouse events for drawing mode

- [x] Add these mouse event overrides to `VTKViewport`, after the coordinate conversion methods:

```python
    def mousePressEvent(self, event) -> None:
        """Captura clics en modo dibujo; delega al plotter en modo selección."""
        if self._drawing_mode and event.button() == Qt.MouseButton.LeftButton:
            # Obtener posición del widget interior (plotter)
            pos = self.plotter.mapFromParent(event.pos())
            coords = self._screen_to_world(pos.x(), pos.y())
            if coords is not None:
                snapped = self._apply_snap(coords)
                self.drawing_click.emit(snapped[0], snapped[1], snapped[2])
            return  # No propagar al plotter
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Captura movimiento en modo dibujo para preview."""
        if self._drawing_mode:
            pos = self.plotter.mapFromParent(event.pos())
            coords = self._screen_to_world(pos.x(), pos.y())
            if coords is not None:
                snapped = self._apply_snap(coords)
                self._pending_move_coords = snapped
                if not self._move_timer.isActive():
                    self._move_timer.start()
            return
        super().mouseMoveEvent(event)

    def _emit_throttled_move(self) -> None:
        """Emite la señal de movimiento con throttle de 50ms."""
        if self._pending_move_coords is not None:
            x, y, z = self._pending_move_coords
            self.drawing_mouse_move.emit(x, y, z)
            self._pending_move_coords = None
```

#### 4.4 — Connect drawing signals in `MainWindow`

- [x] In `MainWindow.__init__`, in the connections section (after `self._undo_mgr.state_changed.connect(...)` ), add:

```python
        self._viewport.drawing_click.connect(self._on_drawing_click)
        self._viewport.drawing_mouse_move.connect(self._on_drawing_mouse_move)
```

- [x] Add placeholder slots in the Slots section of `MainWindow`:

```python
    def _on_drawing_click(self, x: float, y: float, z: float) -> None:
        """Maneja clic en modo dibujo — placeholder para Steps 6-8."""
        self._console.log(f"Drawing click: ({x:.2f}, {y:.2f}, {z:.2f})")

    def _on_drawing_mouse_move(self, x: float, y: float, z: float) -> None:
        """Maneja movimiento en modo dibujo — placeholder para Step 5."""
        pass  # Preview updates will be added in Step 5
```

---

### Step 4 Verification Checklist
- [ ] No build errors — run `python -m gui.main` and verify the window opens
- [ ] Switch to any Draw mode (e.g., "Dibujar Nodo")
- [ ] Click in the viewport — console should print `Drawing click: (X, Y, Z)` with world coordinates
- [ ] With snap ON (default), coordinates should be rounded to multiples of 1.0 (e.g., `5.00, 3.00, 0.00`)
- [ ] Disable snap (F9), click again — coordinates should be exact (e.g., `5.23, 3.17, 0.00`)
- [ ] Test in different camera views (3D, XY, XZ, YZ) — coordinates should always be correct
- [ ] Z coordinate should always be `0.00` (working plane Z=0)
- [ ] In SELECT mode, clicking still selects elements/nodes as before
- [ ] Camera rotation/panning still works in draw mode (right-click, middle-click)

---

### Step 4 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
