"""
Persistencia del modelo — lectura/escritura JSON (.opss).

Formato del archivo:
{
  "format": "OPynSees2000",
  "version": 2,
  "model": { ... StructuralModel.to_dict() ... }
}
"""

from __future__ import annotations

import json
from pathlib import Path

from gui.core.model_data import StructuralModel


PROJECT_VERSION = 2
FILE_FILTER = "OPynSees2000 (*.opss);;Todos los archivos (*)"


def save_project(model: StructuralModel, path: Path) -> None:
    """Guarda el modelo como archivo JSON (.opss)."""
    data = {
        "format": "OPynSees2000",
        "version": PROJECT_VERSION,
        "model": model.to_dict(),
    }
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_project(path: Path) -> tuple[StructuralModel, str]:
    """
    Carga un modelo desde archivo JSON (.opss).

    Returns
    -------
    tuple[StructuralModel, str]
        Modelo cargado y mensaje de notificación (vacío si no hay).
    """
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)

    fmt = data.get("format", "")
    if fmt != "OPynSees2000":
        raise ValueError(f"Formato de archivo no reconocido: '{fmt}'")

    version = data.get("version", 0)
    if version > PROJECT_VERSION:
        raise ValueError(
            f"Versión de archivo ({version}) más nueva que la soportada ({PROJECT_VERSION})."
        )

    model = StructuralModel.from_dict(data["model"])

    notification = ""
    if version < 2:
        # Modelo antiguo: no tiene self_weight_multiplier / density / material_tag
        has_dead = any(
            p.name.upper() == "DEAD" and p.self_weight_multiplier > 0
            for p in model.load_patterns.values()
        )
        if not has_dead:
            notification = (
                "ℹ️ Modelo cargado sin patrón DEAD con peso propio. "
                "Considere agregar peso propio para análisis modal confiable.\n"
                "Puede crear el patrón DEAD desde: Definir → Patrones de carga..."
            )

    return model, notification
