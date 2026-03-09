# Step 1: Enhance SnapManager with Working Plane Support

## Goal
Extend `SnapManager` to support working plane modes (XY, XZ, YZ, Free) with axis-locking and configurable elevation snapping.

## Prerequisites
Make sure you are currently on the `feature/configurable-snap-system` branch before beginning implementation.
If not, move to the correct branch. If the branch does not exist, create it from main.

### Step-by-Step Instructions

#### Step 1.1: Replace snap_manager.py with working plane support

- [x] Open `gui/viewport/snap_manager.py`
- [x] Replace the **entire file contents** with the code below:

```python
"""
SnapManager — Sistema de snap a grilla con soporte de planos de trabajo.

Redondea coordenadas al espaciado de grilla con restricciones por plano:
  - XY: bloquea Z a elevación, snap libre en X/Y
  - XZ: bloquea Y a elevación, snap libre en X/Z
  - YZ: bloquea X a elevación, snap libre en Y/Z
  - Free: snap libre en los tres ejes
"""

from __future__ import annotations


# Planos de trabajo válidos
VALID_PLANES = ("XY", "XZ", "YZ", "Free")


class SnapManager:
    """Gestor de snap a grilla con soporte de planos de trabajo."""

    def __init__(self, spacing: float = 1.0, enabled: bool = True) -> None:
        self._spacing = spacing
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def spacing(self) -> float:
        return self._spacing

    @spacing.setter
    def spacing(self, value: float) -> None:
        if value > 0:
            self._spacing = value

    def snap(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        """
        Redondea coordenadas al múltiplo más cercano del espaciado.

        Si snap está deshabilitado, retorna las coordenadas sin cambiar.
        """
        if not self._enabled:
            return (x, y, z)
        s = self._spacing
        return (
            round(x / s) * s,
            round(y / s) * s,
            round(z / s) * s,
        )

    def snap_point(self, point: tuple[float, float, float]) -> tuple[float, float, float]:
        """Versión con tupla de entrada."""
        return self.snap(point[0], point[1], point[2])

    def snap_with_plane(
        self,
        x: float,
        y: float,
        z: float,
        plane_mode: str,
        elevation: float,
        spacing: float | None = None,
    ) -> tuple[float, float, float]:
        """
        Redondea coordenadas al múltiplo más cercano del espaciado,
        aplicando restricciones del plano de trabajo.

        Parameters
        ----------
        x, y, z : float
            Coordenadas de entrada.
        plane_mode : str
            Modo de plano: "XY", "XZ", "YZ" o "Free".
        elevation : float
            Elevación del plano de trabajo (eje bloqueado).
        spacing : float | None
            Espaciado de grilla. Si es None, usa self._spacing.

        Returns
        -------
        tuple[float, float, float]
            Coordenadas con snap y restricción de plano aplicados.
        """
        if not self._enabled:
            return (x, y, z)

        s = spacing if spacing is not None else self._spacing

        if plane_mode == "XY":
            # Snap X/Y a grilla, Z bloqueado a elevación
            return (
                round(x / s) * s,
                round(y / s) * s,
                elevation,
            )
        elif plane_mode == "XZ":
            # Snap X/Z a grilla, Y bloqueado a elevación
            return (
                round(x / s) * s,
                elevation,
                round(z / s) * s,
            )
        elif plane_mode == "YZ":
            # Snap Y/Z a grilla, X bloqueado a elevación
            return (
                elevation,
                round(y / s) * s,
                round(z / s) * s,
            )
        else:
            # Free: snap los tres ejes
            return (
                round(x / s) * s,
                round(y / s) * s,
                round(z / s) * s,
            )

    def snap_point_with_plane(
        self,
        point: tuple[float, float, float],
        plane_mode: str,
        elevation: float,
        spacing: float | None = None,
    ) -> tuple[float, float, float]:
        """Versión con tupla de entrada para snap_with_plane."""
        return self.snap_with_plane(
            point[0], point[1], point[2],
            plane_mode, elevation, spacing,
        )

    def status_text(self) -> str:
        """Texto para mostrar en status bar."""
        if self._enabled:
            return f"[SNAP ON] | Grilla: {self._spacing}"
        return "[SNAP OFF]"
```

##### Step 1 Verification Checklist
- [x] No import errors: run `python -c "from gui.viewport.snap_manager import SnapManager"`
- [x] Test backward compatibility — existing `snap()` method still works:
  ```python
  python -c "
  from gui.viewport.snap_manager import SnapManager
  sm = SnapManager(spacing=1.0)
  assert sm.snap(1.3, 2.7, 0.4) == (1.0, 3.0, 0.0), 'snap() failed'
  print('snap() OK')
  "
  ```
- [x] Test `snap_with_plane()` for XY mode:
  ```python
  python -c "
  from gui.viewport.snap_manager import SnapManager
  sm = SnapManager(spacing=1.0)
  result = sm.snap_with_plane(1.3, 2.7, 5.5, 'XY', 3.0)
  assert result == (1.0, 3.0, 3.0), f'XY failed: {result}'
  print('XY plane OK')
  "
  ```
- [x] Test `snap_with_plane()` for XZ mode:
  ```python
  python -c "
  from gui.viewport.snap_manager import SnapManager
  sm = SnapManager(spacing=1.0)
  result = sm.snap_with_plane(1.3, 2.7, 5.5, 'XZ', 4.0)
  assert result == (1.0, 4.0, 6.0), f'XZ failed: {result}'
  print('XZ plane OK')
  "
  ```
- [x] Test `snap_with_plane()` for YZ mode:
  ```python
  python -c "
  from gui.viewport.snap_manager import SnapManager
  sm = SnapManager(spacing=1.0)
  result = sm.snap_with_plane(1.3, 2.7, 5.5, 'YZ', 2.0)
  assert result == (2.0, 3.0, 6.0), f'YZ failed: {result}'
  print('YZ plane OK')
  "
  ```
- [x] Test `snap_with_plane()` for Free mode:
  ```python
  python -c "
  from gui.viewport.snap_manager import SnapManager
  sm = SnapManager(spacing=1.0)
  result = sm.snap_with_plane(1.3, 2.7, 5.5, 'Free', 0.0)
  assert result == (1.0, 3.0, 6.0), f'Free failed: {result}'
  print('Free mode OK')
  "
  ```
- [x] Test disabled snap returns unchanged coords:
  ```python
  python -c "
  from gui.viewport.snap_manager import SnapManager
  sm = SnapManager(spacing=1.0, enabled=False)
  result = sm.snap_with_plane(1.3, 2.7, 5.5, 'XY', 3.0)
  assert result == (1.3, 2.7, 5.5), f'Disabled failed: {result}'
  print('Disabled snap OK')
  "
  ```
- [x] Test custom spacing parameter:
  ```python
  python -c "
  from gui.viewport.snap_manager import SnapManager
  sm = SnapManager(spacing=1.0)
  result = sm.snap_with_plane(1.3, 2.7, 5.5, 'XY', 0.0, spacing=0.5)
  assert result == (1.5, 2.5, 0.0), f'Custom spacing failed: {result}'
  print('Custom spacing OK')
  "
  ```
- [x] Application still launches: `python -m gui`

#### Step 1 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.
