"""
Panel del árbol de modelo (Model Tree).

Muestra la estructura jerárquica del modelo:
  Modelo
  ├── Nodos (N)
  ├── Materiales (M)
  ├── Secciones (S)
  ├── Transformaciones (T)
  ├── Elementos (E)
  ├── Patrones de Carga (P)
  └── Análisis
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

if TYPE_CHECKING:
    from gui.core.model_data import StructuralModel


class ModelTree(QTreeWidget):
    """Árbol jerárquico del modelo estructural."""

    item_selected = Signal(str, int)  # (category, tag)

    # Categorías del árbol
    CATEGORIES = [
        ("Nodos", "nodes"),
        ("Materiales", "materials"),
        ("Secciones", "sections"),
        ("Transformaciones", "geom_transfs"),
        ("Elementos", "elements"),
        ("Patrones de Carga", "load_patterns"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["Modelo"])
        self.setAnimated(True)
        self.setIndentation(18)
        self.setRootIsDecorated(True)
        self.setMinimumWidth(200)

        # Nodos raíz por categoría
        self._roots: dict[str, QTreeWidgetItem] = {}
        self._init_tree()

        self.itemClicked.connect(self._on_item_clicked)

    def _init_tree(self) -> None:
        """Crea las categorías raíz vacías."""
        self.clear()
        self._roots.clear()
        for label, key in self.CATEGORIES:
            item = QTreeWidgetItem(self, [label])
            item.setData(0, 100, key)  # role 100 = attr name
            item.setExpanded(True)
            self._roots[key] = item

    def refresh(self, model: StructuralModel) -> None:
        """Actualiza el árbol con los datos del modelo."""
        # Limpiar hijos de cada categoría
        for root in self._roots.values():
            root.takeChildren()

        # Nodos
        for tag, node in model.nodes.items():
            fix_str = " [EMP]" if node.is_fully_fixed else ""
            text = f"Nodo {tag}: ({node.x:.1f}, {node.y:.1f}, {node.z:.1f}){fix_str}"
            child = QTreeWidgetItem(self._roots["nodes"], [text])
            child.setData(0, 100, "nodes")
            child.setData(0, 101, tag)

        # Materiales
        for tag, mat in model.materials.items():
            text = f"Mat {tag}: {mat.name} [{mat.mat_type.value}]"
            child = QTreeWidgetItem(self._roots["materials"], [text])
            child.setData(0, 100, "materials")
            child.setData(0, 101, tag)

        # Secciones
        for tag, sec in model.sections.items():
            text = f"Sec {tag}: {sec.name} [{sec.sec_type.value}]"
            child = QTreeWidgetItem(self._roots["sections"], [text])
            child.setData(0, 100, "sections")
            child.setData(0, 101, tag)

        # Transformaciones
        for tag, transf in model.geom_transfs.items():
            text = f"Transf {tag}: {transf.transf_type.value}"
            child = QTreeWidgetItem(self._roots["geom_transfs"], [text])
            child.setData(0, 100, "geom_transfs")
            child.setData(0, 101, tag)

        # Elementos
        for tag, elem in model.elements.items():
            text = f"Elem {tag}: {elem.elem_type.value} [{elem.node_i}→{elem.node_j}]"
            child = QTreeWidgetItem(self._roots["elements"], [text])
            child.setData(0, 100, "elements")
            child.setData(0, 101, tag)

        # Patrones de carga
        for tag, pat in model.load_patterns.items():
            text = f"Patrón {tag}: {pat.name}"
            child = QTreeWidgetItem(self._roots["load_patterns"], [text])
            child.setData(0, 100, "load_patterns")
            child.setData(0, 101, tag)

        # Actualizar conteos en labels
        for label, key in self.CATEGORIES:
            root = self._roots[key]
            count = root.childCount()
            root.setText(0, f"{label} ({count})")

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Emite señal cuando se hace click en un hijo."""
        category = item.data(0, 100)
        tag = item.data(0, 101)
        if category and tag is not None:
            self.item_selected.emit(category, tag)
