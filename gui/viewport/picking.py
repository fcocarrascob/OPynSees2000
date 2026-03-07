"""
Picking — Selección interactiva de nodos y elementos en el viewport.

Usa el sistema de picking de PyVista/VTK para detectar clics
sobre nodos y elementos, emitiendo señales al MainWindow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    from gui.core.model_data import StructuralModel


def find_closest_node(
    model: StructuralModel,
    point: tuple[float, float, float],
    tolerance: float = 0.5,
) -> Optional[int]:
    """
    Retorna el tag del nodo más cercano al punto dado,
    o None si está fuera de la tolerancia.
    """
    if not model.nodes:
        return None

    picked = np.array(point)
    best_tag = None
    best_dist = tolerance

    for tag, node in model.nodes.items():
        dist = np.linalg.norm(picked - np.array(node.coords))
        if dist < best_dist:
            best_dist = dist
            best_tag = tag

    return best_tag


def find_closest_element(
    model: StructuralModel,
    point: tuple[float, float, float],
    tolerance: float = 0.5,
) -> Optional[int]:
    """
    Retorna el tag del elemento cuyo segmento lineal está más
    cercano al punto dado, o None si está fuera de la tolerancia.
    """
    if not model.elements:
        return None

    picked = np.array(point)
    best_tag = None
    best_dist = tolerance

    for tag, elem in model.elements.items():
        ni = model.nodes.get(elem.node_i)
        nj = model.nodes.get(elem.node_j)
        if ni is None or nj is None:
            continue

        a = np.array(ni.coords)
        b = np.array(nj.coords)
        ab = b - a
        ab_len = np.linalg.norm(ab)
        if ab_len < 1e-12:
            continue

        # Proyección del punto sobre el segmento
        t = np.dot(picked - a, ab) / (ab_len ** 2)
        t = max(0.0, min(1.0, t))
        closest = a + t * ab
        dist = np.linalg.norm(picked - closest)

        if dist < best_dist:
            best_dist = dist
            best_tag = tag

    return best_tag
