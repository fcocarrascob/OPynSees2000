# Sprint 2: Dibujo de Geometría + Restricciones

## Goal
Implementar diálogos para agregar nodos y elementos al modelo (frames, truss, shell), y asignar condiciones de borde — habilitando los menús "Dibujar" y la acción "Restricciones" del menú "Asignar".

## Prerequisites
Sprint 1 completado y commiteado. Branch `feat/gui-sap2000-workflow`.

---

### Step-by-Step Instructions

---

#### Step 4: Diálogo de Nodos

- [x] Crear `gui/dialogs/node_dialog.py`
- [x] Modificar `gui/main_window.py` para habilitar Dibujar → Nodo...

##### 4A. Crear `gui/dialogs/node_dialog.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Diálogo para crear nodos por coordenadas.

Soporta creación individual y en secuencia (botón "Agregar otro").
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from gui.core.model_data import Node


class NodeDialog(QDialog):
    """Diálogo modal para crear un nodo por coordenadas."""

    def __init__(
        self,
        parent=None,
        node: Optional[Node] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar nodo" if node else "Nuevo nodo")
        self.setMinimumWidth(380)

        self._editing = node
        self._created_nodes: list[Node] = []
        self._next_tag = next_tag

        layout = QVBoxLayout(self)

        # --- Coordenadas ---
        grp_coords = QGroupBox("Coordenadas")
        form = QFormLayout()
        grp_coords.setLayout(form)

        self._tag_edit = QLineEdit(str(node.tag if node else next_tag))
        self._tag_edit.setReadOnly(True)
        form.addRow("Tag:", self._tag_edit)

        self._x_spin = QDoubleSpinBox()
        self._x_spin.setDecimals(4)
        self._x_spin.setRange(-1e6, 1e6)
        self._x_spin.setValue(node.x if node else 0.0)
        self._x_spin.setSuffix(" m")
        form.addRow("X:", self._x_spin)

        self._y_spin = QDoubleSpinBox()
        self._y_spin.setDecimals(4)
        self._y_spin.setRange(-1e6, 1e6)
        self._y_spin.setValue(node.y if node else 0.0)
        self._y_spin.setSuffix(" m")
        form.addRow("Y:", self._y_spin)

        self._z_spin = QDoubleSpinBox()
        self._z_spin.setDecimals(4)
        self._z_spin.setRange(-1e6, 1e6)
        self._z_spin.setValue(node.z if node else 0.0)
        self._z_spin.setSuffix(" m")
        form.addRow("Z:", self._z_spin)

        layout.addWidget(grp_coords)

        # --- Info ---
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #388E3C; padding: 4px;")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label)

        # --- Botones ---
        if node:
            # Modo edición: solo OK/Cancel
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
        else:
            # Modo creación: Agregar otro + Cerrar
            btn_layout = QHBoxLayout()

            self._btn_add = QPushButton("Agregar nodo")
            self._btn_add.clicked.connect(self._on_add_node)
            btn_layout.addWidget(self._btn_add)

            self._btn_add_another = QPushButton("Agregar y continuar")
            self._btn_add_another.setProperty("flat", "true")
            self._btn_add_another.clicked.connect(self._on_add_and_continue)
            btn_layout.addWidget(self._btn_add_another)

            self._btn_close = QPushButton("Cerrar")
            self._btn_close.setProperty("flat", "true")
            self._btn_close.clicked.connect(self.reject)
            btn_layout.addWidget(self._btn_close)

            layout.addLayout(btn_layout)

    # ---------------------------------------------------------------

    def _on_add_node(self) -> None:
        """Agrega un nodo y cierra el diálogo."""
        self._store_current_node()
        self.accept()

    def _on_add_and_continue(self) -> None:
        """Agrega un nodo y prepara para el siguiente."""
        self._store_current_node()
        # Incrementar tag
        self._next_tag += 1
        self._tag_edit.setText(str(self._next_tag))
        # Limpiar coordenadas (mantener Z para comodidad)
        self._x_spin.setValue(0.0)
        self._y_spin.setValue(0.0)
        self._x_spin.setFocus()
        self._x_spin.selectAll()
        self._info_label.setText(
            f"✔ Nodo {self._next_tag - 1} agregado. "
            f"Total: {len(self._created_nodes)}"
        )

    def _store_current_node(self) -> None:
        """Almacena el nodo actual en la lista interna."""
        tag = int(self._tag_edit.text())
        node = Node(
            tag=tag,
            x=self._x_spin.value(),
            y=self._y_spin.value(),
            z=self._z_spin.value(),
        )
        self._created_nodes.append(node)

    # ---------------------------------------------------------------
    # Resultado
    # ---------------------------------------------------------------

    def get_node(self) -> Node:
        """Retorna el nodo editado (modo edición)."""
        tag = int(self._tag_edit.text())
        return Node(
            tag=tag,
            x=self._x_spin.value(),
            y=self._y_spin.value(),
            z=self._z_spin.value(),
            fixity=self._editing.fixity if self._editing else (),
            mass=self._editing.mass if self._editing else (),
        )

    def get_created_nodes(self) -> list[Node]:
        """Retorna todos los nodos creados (modo creación secuencial)."""
        return list(self._created_nodes)
```

##### 4B. Modificar `gui/main_window.py` — Habilitar Nodo

- [x] Agregar import. Después de los imports de diálogos existentes, agregar:

```python
from gui.dialogs.node_dialog import NodeDialog
```

- [x] En `_build_menubar`, reemplazar el bloque del Nodo.

Reemplazar:
```python
        act_node = QAction("Nodo...", self)
        act_node.setEnabled(False)
        m_draw.addAction(act_node)
```
Con:
```python
        act_node = QAction("Nodo...", self)
        act_node.setToolTip("Agregar nodos al modelo")
        act_node.triggered.connect(self._on_draw_node)
        m_draw.addAction(act_node)
```

- [x] Agregar slot nuevo en la sección Slots:

```python
    def _on_draw_node(self) -> None:
        """Abre el diálogo para crear nodos."""
        dlg = NodeDialog(
            self,
            next_tag=self._model.next_node_tag(),
        )
        result = dlg.exec()
        nodes = dlg.get_created_nodes()
        if nodes:
            for node in nodes:
                self._model.nodes[node.tag] = node
            self._refresh_all()
            self._console.log_success(
                f"{len(nodes)} nodo(s) creado(s): "
                + ", ".join(str(n.tag) for n in nodes)
            )
```

- [x] Expandir `_on_tree_item_double_clicked` para soportar nodos. Dentro del método, agregar antes del cierre:

```python
        elif category == "nodes":
            node = self._model.nodes.get(tag)
            if not node:
                return
            dlg = NodeDialog(self, node=node)
            if dlg.exec():
                edited = dlg.get_node()
                self._model.nodes[tag] = edited
                self._refresh_all()
                self._console.log(
                    f"Nodo {tag} editado: ({edited.x}, {edited.y}, {edited.z})"
                )
```

##### Step 4 Verification Checklist

- [ ] Ejecutar GUI → Nuevo modelo → Dibujar → Nodo... → se abre diálogo
- [ ] Ingresar (5.0, 0.0, 3.5) → "Agregar nodo" → nodo aparece en tree y viewport como esfera roja
- [ ] Verificar tag auto-incremental
- [ ] Usar "Agregar y continuar" para crear 3 nodos seguidos → verificar todos en tree/viewport
- [ ] Doble-clic en nodo existente → editar coordenadas → viewport actualizado
- [ ] Guardar como .opss → Abrir → nodos nuevos persisten

#### Step 4 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: add node creation dialog

- Create NodeDialog with coordinate input (X, Y, Z)
- Support sequential node creation (Add & Continue)
- Enable Dibujar > Nodo menu action
- Double-click editing for nodes in tree"
```

---

#### Step 5: Diálogo de Elementos (Frames, Truss, Shell)

- [x] Crear `gui/dialogs/element_dialog.py`
- [x] Modificar `gui/core/model_data.py` para soportar elementos de 4 nodos (Shell)
- [x] Modificar `gui/viewport/vtk_widget.py` para renderizar shells
- [x] Modificar `gui/main_window.py` para habilitar Dibujar → Elemento...

##### 5A. Modificar `gui/core/model_data.py` — Soporte Shell (4 nodos)

- [x] En la clase `Element`, agregar campos para nodos adicionales (Shell).

Reemplazar la clase `Element` completa:

```python
@dataclass
class Element:
    """Elemento estructural."""
    tag: int
    elem_type: ElementType
    node_i: int
    node_j: int
    node_k: Optional[int] = None      # Para Shell (4 nodos)
    node_l: Optional[int] = None      # Para Shell (4 nodos)
    section_tag: Optional[int] = None
    transf_tag: Optional[int] = None
    params: dict = field(default_factory=dict)

    @property
    def is_shell(self) -> bool:
        """True si es un elemento de área (Shell)."""
        return self.elem_type == ElementType.SHELL_MITC4

    @property
    def node_tags(self) -> tuple[int, ...]:
        """Retorna todos los tags de nodos del elemento."""
        if self.is_shell:
            return (self.node_i, self.node_j, self.node_k or 0, self.node_l or 0)
        return (self.node_i, self.node_j)

    def to_dict(self) -> dict:
        d = {
            "tag": self.tag,
            "elem_type": self.elem_type.value,
            "node_i": self.node_i,
            "node_j": self.node_j,
            "section_tag": self.section_tag,
            "transf_tag": self.transf_tag,
            "params": dict(self.params),
        }
        if self.node_k is not None:
            d["node_k"] = self.node_k
        if self.node_l is not None:
            d["node_l"] = self.node_l
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Element":
        return cls(
            tag=d["tag"],
            elem_type=ElementType(d["elem_type"]),
            node_i=d["node_i"],
            node_j=d["node_j"],
            node_k=d.get("node_k"),
            node_l=d.get("node_l"),
            section_tag=d.get("section_tag"),
            transf_tag=d.get("transf_tag"),
            params=d.get("params", {}),
        )
```

##### 5B. Crear `gui/dialogs/element_dialog.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Diálogo para crear / editar elementos estructurales.

Soporta elementos frame (2 nodos), truss (2 nodos) y shell (4 nodos).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from gui.core.model_data import (
    Element,
    ElementType,
    StructuralModel,
)

# Tipos que requieren 4 nodos
SHELL_TYPES = {ElementType.SHELL_MITC4}

# Tipos que NO requieren transformación geométrica
NO_TRANSF_TYPES = {ElementType.TRUSS, ElementType.COROT_TRUSS, ElementType.SHELL_MITC4}


class ElementDialog(QDialog):
    """Diálogo modal para crear o editar un elemento."""

    def __init__(
        self,
        parent=None,
        model: Optional[StructuralModel] = None,
        element: Optional[Element] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar elemento" if element else "Nuevo elemento")
        self.setMinimumWidth(440)

        self._model = model or StructuralModel()
        self._editing = element

        layout = QVBoxLayout(self)

        # --- Tipo e info ---
        grp_info = QGroupBox("Tipo de elemento")
        form_type = QFormLayout()
        grp_info.setLayout(form_type)

        self._tag_edit = QLineEdit(str(element.tag if element else next_tag))
        self._tag_edit.setReadOnly(True)
        form_type.addRow("Tag:", self._tag_edit)

        self._type_combo = QComboBox()
        for et in ElementType:
            self._type_combo.addItem(et.value, et)
        if element:
            idx = self._type_combo.findData(element.elem_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form_type.addRow("Tipo:", self._type_combo)

        layout.addWidget(grp_info)

        # --- Conectividad ---
        grp_conn = QGroupBox("Conectividad (nodos)")
        self._conn_layout = QFormLayout()
        grp_conn.setLayout(self._conn_layout)

        self._node_i_spin = QSpinBox()
        self._node_i_spin.setRange(1, 999_999)
        self._node_i_spin.setValue(element.node_i if element else 1)
        self._conn_layout.addRow("Nodo I:", self._node_i_spin)

        self._node_j_spin = QSpinBox()
        self._node_j_spin.setRange(1, 999_999)
        self._node_j_spin.setValue(element.node_j if element else 2)
        self._conn_layout.addRow("Nodo J:", self._node_j_spin)

        # Nodos K y L para Shell
        self._node_k_spin = QSpinBox()
        self._node_k_spin.setRange(1, 999_999)
        self._node_k_spin.setValue(element.node_k if element and element.node_k else 3)
        self._lbl_k = QLabel("Nodo K:")

        self._node_l_spin = QSpinBox()
        self._node_l_spin.setRange(1, 999_999)
        self._node_l_spin.setValue(element.node_l if element and element.node_l else 4)
        self._lbl_l = QLabel("Nodo L:")

        self._conn_layout.addRow(self._lbl_k, self._node_k_spin)
        self._conn_layout.addRow(self._lbl_l, self._node_l_spin)

        layout.addWidget(grp_conn)

        # --- Propiedades ---
        grp_props = QGroupBox("Propiedades")
        self._props_layout = QFormLayout()
        grp_props.setLayout(self._props_layout)

        # Sección
        self._section_combo = QComboBox()
        self._section_combo.addItem("(ninguna)", None)
        for tag, sec in sorted(self._model.sections.items()):
            self._section_combo.addItem(
                f"{tag}: {sec.name} [{sec.sec_type.value}]", tag
            )
        if element and element.section_tag:
            idx = self._section_combo.findData(element.section_tag)
            if idx >= 0:
                self._section_combo.setCurrentIndex(idx)
        self._props_layout.addRow("Sección:", self._section_combo)

        # Transformación
        self._transf_combo = QComboBox()
        self._transf_combo.addItem("(ninguna)", None)
        for tag, transf in sorted(self._model.geom_transfs.items()):
            self._transf_combo.addItem(
                f"{tag}: {transf.transf_type.value}", tag
            )
        if element and element.transf_tag:
            idx = self._transf_combo.findData(element.transf_tag)
            if idx >= 0:
                self._transf_combo.setCurrentIndex(idx)
        self._lbl_transf = QLabel("Transformación:")
        self._props_layout.addRow(self._lbl_transf, self._transf_combo)

        layout.addWidget(grp_props)

        # --- Validación ---
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #D32F2F; padding: 4px;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._error_label)

        # --- Botones ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Mostrar/ocultar campos según tipo
        self._on_type_changed()

    # ---------------------------------------------------------------

    def _on_type_changed(self) -> None:
        """Muestra/oculta campos según el tipo de elemento."""
        elem_type: ElementType = self._type_combo.currentData()
        is_shell = elem_type in SHELL_TYPES
        needs_transf = elem_type not in NO_TRANSF_TYPES

        # Nodos K y L solo para Shell
        self._node_k_spin.setVisible(is_shell)
        self._lbl_k.setVisible(is_shell)
        self._node_l_spin.setVisible(is_shell)
        self._lbl_l.setVisible(is_shell)

        # Transformación no aplica a truss/shell
        self._transf_combo.setVisible(needs_transf)
        self._lbl_transf.setVisible(needs_transf)

    def _on_accept(self) -> None:
        """Valida y acepta."""
        elem_type: ElementType = self._type_combo.currentData()
        is_shell = elem_type in SHELL_TYPES

        # Validar que los nodos existen
        node_tags = [self._node_i_spin.value(), self._node_j_spin.value()]
        if is_shell:
            node_tags.extend([self._node_k_spin.value(), self._node_l_spin.value()])

        missing = [t for t in node_tags if t not in self._model.nodes]
        if missing:
            self._error_label.setText(
                f"❌ Nodos no encontrados: {', '.join(str(t) for t in missing)}"
            )
            return

        # Validar sección
        sec_tag = self._section_combo.currentData()
        if sec_tag is None:
            self._error_label.setText("❌ Debe seleccionar una sección.")
            return

        self._error_label.setText("")
        self.accept()

    def get_element(self) -> Element:
        """Retorna el elemento configurado."""
        tag = int(self._tag_edit.text())
        elem_type: ElementType = self._type_combo.currentData()
        is_shell = elem_type in SHELL_TYPES

        return Element(
            tag=tag,
            elem_type=elem_type,
            node_i=self._node_i_spin.value(),
            node_j=self._node_j_spin.value(),
            node_k=self._node_k_spin.value() if is_shell else None,
            node_l=self._node_l_spin.value() if is_shell else None,
            section_tag=self._section_combo.currentData(),
            transf_tag=self._transf_combo.currentData()
            if elem_type not in NO_TRANSF_TYPES
            else None,
        )
```

##### 5C. Modificar `gui/viewport/vtk_widget.py` — Renderizar Shells

- [x] Agregar método `_add_shells` en la clase `VTKViewport`. Insertar después de `_add_elements`:

```python
    def _add_shells(self, model: StructuralModel) -> None:
        """Dibuja elementos shell como superficies cuadriláteras."""
        shell_points: list[list[float]] = []
        shell_faces: list[list[int]] = []
        idx = 0

        for elem in model.elements.values():
            if not elem.is_shell:
                continue
            nodes = []
            for nt in elem.node_tags:
                n = model.nodes.get(nt)
                if n is None:
                    break
                nodes.append(n)
            if len(nodes) != 4:
                continue

            for n in nodes:
                shell_points.append([n.x, n.y, n.z])
            shell_faces.append([4, idx, idx + 1, idx + 2, idx + 3])
            idx += 4

        if not shell_points:
            return

        faces = np.hstack(shell_faces)
        shell_mesh = pv.PolyData(
            np.array(shell_points, dtype=float),
            faces=faces,
        )
        self.plotter.add_mesh(
            shell_mesh,
            color="#80CBC4",        # teal claro
            opacity=0.5,
            show_edges=True,
            edge_color="#00695C",   # teal oscuro
            line_width=1,
            name="shells",
        )
```

- [x] En `_add_elements`, filtrar los elementos shell para que no se dibujen como líneas. Modificar el loop para saltear shells:

En el método `_add_elements`, dentro del `for elem in model.elements.values():`, agregar al inicio del loop:
```python
            if elem.is_shell:
                continue
```

- [x] En `display_model`, agregar la llamada a `_add_shells`. Después de `self._add_elements(model)`, agregar:

```python
        self._add_shells(model)
```

##### 5D. Modificar `gui/main_window.py` — Habilitar Elemento

- [x] Agregar import:

```python
from gui.dialogs.element_dialog import ElementDialog
```

- [x] En `_build_menubar`, reemplazar el bloque de Elemento.

Reemplazar:
```python
        act_elem = QAction("Elemento...", self)
        act_elem.setEnabled(False)
        m_draw.addAction(act_elem)
```
Con:
```python
        act_elem = QAction("Elemento...", self)
        act_elem.setToolTip("Agregar elementos al modelo")
        act_elem.triggered.connect(self._on_draw_element)
        m_draw.addAction(act_elem)
```

- [x] Agregar slot:

```python
    def _on_draw_element(self) -> None:
        """Abre el diálogo para crear un elemento."""
        dlg = ElementDialog(
            self,
            model=self._model,
            next_tag=self._model.next_element_tag(),
        )
        if dlg.exec():
            elem = dlg.get_element()
            self._model.elements[elem.tag] = elem
            self._refresh_all()
            self._console.log_success(
                f"Elemento creado: {elem.tag} — {elem.elem_type.value} "
                f"[{elem.node_i}→{elem.node_j}]"
            )
```

- [x] Expandir `_on_tree_item_double_clicked` para soportar elementos:

Agregar al final del método:
```python
        elif category == "elements":
            elem = self._model.elements.get(tag)
            if not elem:
                return
            dlg = ElementDialog(self, model=self._model, element=elem)
            if dlg.exec():
                edited = dlg.get_element()
                self._model.elements[tag] = edited
                self._refresh_all()
                self._console.log(
                    f"Elemento {tag} editado: {edited.elem_type.value}"
                )
```

##### Step 5 Verification Checklist

- [ ] Ejecutar GUI → Cargar demo → Dibujar → Elemento... → se abre diálogo
- [ ] Verificar que ComboBoxes de sección y transformación muestran las opciones del demo
- [ ] Crear modelo nuevo → crear 4 nodos → crear elemento elasticBeamColumn → línea aparece en viewport
- [ ] Seleccionar tipo ShellMITC4 → aparecen campos Nodo K y Nodo L, desaparece Transformación
- [ ] Seleccionar tipo Truss → Nodos K/L ocultos, Transformación oculta
- [ ] Intentar crear con nodo inexistente → error "Nodos no encontrados"
- [ ] Intentar crear sin sección → error "Debe seleccionar una sección"
- [ ] Crear Shell con 4 nodos → superficie semi-transparente en viewport
- [ ] Guardar/abrir → elementos Shell persisten correctamente

#### Step 5 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: add element creation dialog with shell support

- Create ElementDialog for frame, truss, and shell elements
- Add node_k, node_l fields to Element for ShellMITC4
- Render shell elements as translucent quad surfaces
- Dynamic UI: show/hide fields based on element type
- Validation: check node existence and section assignment"
```

---

#### Step 6: Asignar Restricciones (Fixity)

- [x] Crear `gui/dialogs/fixity_dialog.py`
- [x] Modificar `gui/main_window.py` para habilitar Asignar → Restricciones...

##### 6A. Crear `gui/dialogs/fixity_dialog.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Diálogo para asignar condiciones de borde a nodos.

Presets: Empotrado, Articulado, Libre.
Selección individual de DOFs con checkboxes.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from gui.core.model_data import Node, StructuralModel


# Presets de condiciones de borde (6 DOF: dx, dy, dz, rx, ry, rz)
FIXITY_PRESETS: dict[str, tuple[int, ...]] = {
    "Libre": (0, 0, 0, 0, 0, 0),
    "Empotrado": (1, 1, 1, 1, 1, 1),
    "Articulado (pin)": (1, 1, 1, 0, 0, 0),
    "Rodillo X (libre en X)": (0, 1, 1, 0, 0, 0),
    "Rodillo Y (libre en Y)": (1, 0, 1, 0, 0, 0),
    "Rodillo Z (libre en Z)": (1, 1, 0, 0, 0, 0),
    "Personalizado": (),
}

DOF_LABELS = ["dx (traslación X)", "dy (traslación Y)", "dz (traslación Z)",
              "rx (rotación X)", "ry (rotación Y)", "rz (rotación Z)"]


class FixityDialog(QDialog):
    """Diálogo modal para asignar restricciones a nodos seleccionados."""

    def __init__(
        self,
        parent=None,
        model: Optional[StructuralModel] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Asignar restricciones")
        self.setMinimumWidth(460)
        self.setMinimumHeight(500)

        self._model = model or StructuralModel()

        layout = QVBoxLayout(self)

        # --- Selección de nodos ---
        grp_nodes = QGroupBox("Seleccionar nodos")
        nodes_layout = QVBoxLayout()
        grp_nodes.setLayout(nodes_layout)

        # Botones de selección rápida
        btn_row = QHBoxLayout()
        btn_all = QPushButton("Seleccionar todos")
        btn_all.setProperty("flat", "true")
        btn_all.clicked.connect(self._select_all)
        btn_row.addWidget(btn_all)

        btn_none = QPushButton("Deseleccionar todos")
        btn_none.setProperty("flat", "true")
        btn_none.clicked.connect(self._deselect_all)
        btn_row.addWidget(btn_none)

        btn_free = QPushButton("Solo libres")
        btn_free.setProperty("flat", "true")
        btn_free.clicked.connect(self._select_free_only)
        btn_row.addWidget(btn_free)

        nodes_layout.addLayout(btn_row)

        # Lista de nodos con checkboxes
        self._node_list = QListWidget()
        self._node_list.setMaximumHeight(180)
        for tag, node in sorted(self._model.nodes.items()):
            fix_str = " [EMP]" if node.is_fully_fixed else ""
            item = QListWidgetItem(
                f"Nodo {tag}: ({node.x:.1f}, {node.y:.1f}, {node.z:.1f}){fix_str}"
            )
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self._node_list.addItem(item)

        nodes_layout.addWidget(self._node_list)
        layout.addWidget(grp_nodes)

        # --- Condición de borde ---
        grp_fix = QGroupBox("Condición de borde")
        fix_layout = QVBoxLayout()
        grp_fix.setLayout(fix_layout)

        # Preset combo
        self._preset_combo = QComboBox()
        for name in FIXITY_PRESETS:
            self._preset_combo.addItem(name)
        self._preset_combo.setCurrentText("Empotrado")
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        fix_layout.addWidget(self._preset_combo)

        # DOF checkboxes
        self._dof_checks: list[QCheckBox] = []
        dof_form = QFormLayout()
        for i, label in enumerate(DOF_LABELS):
            cb = QCheckBox()
            cb.stateChanged.connect(self._on_dof_changed)
            self._dof_checks.append(cb)
            dof_form.addRow(label + ":", cb)
        fix_layout.addLayout(dof_form)

        layout.addWidget(grp_fix)

        # Info
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #757575; padding: 4px;")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label)

        # --- Botones ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Close
        )
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._on_apply
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Aplicar preset inicial
        self._on_preset_changed("Empotrado")

    # ---------------------------------------------------------------

    def _select_all(self) -> None:
        for i in range(self._node_list.count()):
            self._node_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        for i in range(self._node_list.count()):
            self._node_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _select_free_only(self) -> None:
        """Selecciona solo nodos sin restricciones."""
        for i in range(self._node_list.count()):
            item = self._node_list.item(i)
            tag = item.data(Qt.ItemDataRole.UserRole)
            node = self._model.nodes.get(tag)
            if node and not node.is_fixed:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _on_preset_changed(self, text: str) -> None:
        """Aplica un preset de fixity."""
        fixity = FIXITY_PRESETS.get(text, ())
        if not fixity:
            return  # Personalizado: no cambiar nada
        for i, val in enumerate(fixity):
            self._dof_checks[i].setChecked(val == 1)

    def _on_dof_changed(self) -> None:
        """Actualiza el preset combo si los DOFs no coinciden."""
        current = tuple(1 if cb.isChecked() else 0 for cb in self._dof_checks)
        for name, preset in FIXITY_PRESETS.items():
            if preset == current:
                self._preset_combo.blockSignals(True)
                self._preset_combo.setCurrentText(name)
                self._preset_combo.blockSignals(False)
                return
        self._preset_combo.blockSignals(True)
        self._preset_combo.setCurrentText("Personalizado")
        self._preset_combo.blockSignals(False)

    def _on_apply(self) -> None:
        """Aplica las restricciones a los nodos seleccionados."""
        fixity = tuple(1 if cb.isChecked() else 0 for cb in self._dof_checks)
        selected_tags = self._get_selected_tags()

        if not selected_tags:
            self._info_label.setText("⚠ No hay nodos seleccionados.")
            self._info_label.setStyleSheet("color: #FF8F00; padding: 4px;")
            return

        for tag in selected_tags:
            node = self._model.nodes.get(tag)
            if node:
                # Reemplazar fixity (dataclass inmutable → crear nuevo)
                self._model.nodes[tag] = Node(
                    tag=node.tag, x=node.x, y=node.y, z=node.z,
                    fixity=fixity, mass=node.mass,
                )

        self._applied = True
        self._info_label.setText(
            f"✔ Restricciones aplicadas a {len(selected_tags)} nodo(s)."
        )
        self._info_label.setStyleSheet("color: #388E3C; padding: 4px;")

        # Actualizar la lista para reflejar cambios
        self._refresh_node_list()

    def _get_selected_tags(self) -> list[int]:
        """Retorna los tags de nodos seleccionados."""
        tags = []
        for i in range(self._node_list.count()):
            item = self._node_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                tags.append(item.data(Qt.ItemDataRole.UserRole))
        return tags

    def _refresh_node_list(self) -> None:
        """Actualiza el texto de los ítems despues de aplicar."""
        for i in range(self._node_list.count()):
            item = self._node_list.item(i)
            tag = item.data(Qt.ItemDataRole.UserRole)
            node = self._model.nodes.get(tag)
            if node:
                fix_str = " [EMP]" if node.is_fully_fixed else (
                    " [FIX]" if node.is_fixed else ""
                )
                item.setText(
                    f"Nodo {tag}: ({node.x:.1f}, {node.y:.1f}, {node.z:.1f}){fix_str}"
                )

    # ---------------------------------------------------------------

    @property
    def was_applied(self) -> bool:
        """True si se aplicaron cambios."""
        return getattr(self, "_applied", False)
```

##### 6B. Modificar `gui/main_window.py` — Habilitar Restricciones

- [x] Agregar import:

```python
from gui.dialogs.fixity_dialog import FixityDialog
```

- [x] En `_build_menubar`, reemplazar el bloque de Restricciones.

Reemplazar:
```python
        act_fix = QAction("Restricciones...", self)
        act_fix.setEnabled(False)
        m_assign.addAction(act_fix)
```
Con:
```python
        act_fix = QAction("Restricciones...", self)
        act_fix.setToolTip("Asignar condiciones de borde a nodos")
        act_fix.triggered.connect(self._on_assign_fixity)
        m_assign.addAction(act_fix)
```

- [x] Agregar slot:

```python
    def _on_assign_fixity(self) -> None:
        """Abre el diálogo para asignar restricciones."""
        if not self._model.nodes:
            self._console.log_error("No hay nodos en el modelo.")
            return
        dlg = FixityDialog(self, model=self._model)
        dlg.exec()
        if dlg.was_applied:
            self._refresh_all()
            self._console.log_success("Restricciones aplicadas.")
```

##### Step 6 Verification Checklist

- [ ] Ejecutar GUI → Cargar demo → Asignar → Restricciones... → se abre diálogo con 27 nodos listados
- [ ] Nodos con [EMP] aparecen correctamente (nodos de base del demo)
- [ ] "Solo libres" selecciona solo nodos sin restricciones
- [ ] Seleccionar preset "Articulado" → checkboxes dx, dy, dz marcados, rx, ry, rz desmarcados
- [ ] Aplicar → nodos se actualizan en la lista con [FIX]
- [ ] Cerrar diálogo → viewport actualizado: conos verdes en nodos restringidos
- [ ] Cambiar preset a "Libre" → aplicar a nodos base → los conos verdes desaparecen del viewport
- [ ] Guardar como .opss → Abrir → restricciones persisten

#### Step 6 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: add fixity assignment dialog

- Create FixityDialog with node multi-selection
- Support presets: Fixed, Pinned, Roller X/Y/Z, Free, Custom
- Individual DOF checkboxes with bi-directional preset sync
- Enable Asignar > Restricciones menu action
- Quick selection buttons (all, none, free-only)"
```

---

## Sprint 2 Complete

Al finalizar Sprint 2, el estado de la GUI es:

| Feature | Estado |
|---------|--------|
| Dibujar → Nodo | ✅ Funcional (individual y secuencial) |
| Dibujar → Elemento | ✅ Funcional (frame, truss, shell) |
| Asignar → Restricciones | ✅ Funcional (presets + personalizado) |
| Soporte Shell (ShellMITC4) | ✅ Funcional (modelo + viewport) |
| Edición por doble-clic | ✅ Nodos, materiales, secciones, transformaciones, elementos |

**Archivos nuevos creados:** 3
- `gui/dialogs/node_dialog.py`
- `gui/dialogs/element_dialog.py`
- `gui/dialogs/fixity_dialog.py`

**Archivos modificados:** 3
- `gui/core/model_data.py` (Element ampliado con node_k/node_l, is_shell)
- `gui/viewport/vtk_widget.py` (_add_shells, filtro en _add_elements)
- `gui/main_window.py` (3 nuevas acciones + slots + doble-clic expandido)
