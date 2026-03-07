"""
Persistencia del modelo — lectura/escritura JSON (.opss).

Formato del archivo:
{
  "format": "OPynSees2000",
  "version": 1,
  "model": { ... StructuralModel.to_dict() ... }
}
"""

from __future__ import annotations

import json
from pathlib import Path

from gui.core.model_data import StructuralModel


PROJECT_VERSION = 1
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


def load_project(path: Path) -> StructuralModel:
    """Carga un modelo desde archivo JSON (.opss)."""
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

    return StructuralModel.from_dict(data["model"])
