"""
SnapManager — Sistema minimalista de snap a grilla.

Redondea coordenadas al espaciado de grilla (invisiblemente).
Sin grilla visual; solo snap lógico + indicador sutil.
"""

from __future__ import annotations

import math


class SnapManager:
    """Gestor de snap a grilla invisible."""

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

    def status_text(self) -> str:
        """Texto para mostrar en status bar."""
        if self._enabled:
            return f"[SNAP ON] | Grilla: {self._spacing}"
        return "[SNAP OFF]"
