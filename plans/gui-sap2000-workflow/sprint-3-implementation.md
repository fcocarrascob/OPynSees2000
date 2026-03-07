# Sprint 3: Cargas + Viewport Mejorado

## Goal
Implementar patrones de carga con cargas nodales, y mejorar el viewport con etiquetas, selección interactiva y visualización de flechas de carga — completando la pipeline Definir → Dibujar → Asignar.

## Prerequisites
Sprint 2 completado y commiteado. Branch `feat/gui-sap2000-workflow`.

---

### Step-by-Step Instructions

---

#### Step 7: Patrones de Carga y Cargas Nodales

- [x] Crear `gui/dialogs/load_pattern_dialog.py`
- [x] Crear `gui/dialogs/nodal_load_dialog.py`
- [x] Modificar `gui/main_window.py` para habilitar Definir → Patrones de carga... y Asignar → Cargas nodales...

##### 7A. Crear `gui/dialogs/load_pattern_dialog.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Diálogo para crear / editar patrones de carga.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QVBoxLayout,
)

from gui.core.model_data import LoadPattern

# Tipos de TimeSeries disponibles
TIME_SERIES_TYPES = ["Constant", "Linear", "Path"]


class LoadPatternDialog(QDialog):
    """Diálogo modal para crear o editar un patrón de carga."""

    def __init__(
        self,
        parent=None,
        pattern: Optional[LoadPattern] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar patrón" if pattern else "Nuevo patrón de carga")
        self.setMinimumWidth(380)

        self._editing = pattern

        layout = QVBoxLayout(self)

        grp = QGroupBox("Patrón de carga")
        form = QFormLayout()
        grp.setLayout(form)

        self._tag_edit = QLineEdit(str(pattern.tag if pattern else next_tag))
        self._tag_edit.setReadOnly(True)
        form.addRow("Tag:", self._tag_edit)

        self._name_edit = QLineEdit(pattern.name if pattern else "")
        self._name_edit.setPlaceholderText("Ej: Carga muerta, Carga viva, Sismo X")
        form.addRow("Nombre:", self._name_edit)

        self._ts_combo = QComboBox()
        for ts in TIME_SERIES_TYPES:
            self._ts_combo.addItem(ts)
        if pattern:
            idx = self._ts_combo.findText(pattern.time_series_type)
            if idx >= 0:
                self._ts_combo.setCurrentIndex(idx)
        form.addRow("Time Series:", self._ts_combo)

        layout.addWidget(grp)

        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self.accept()

    def get_pattern(self) -> LoadPattern:
        """Retorna el patrón configurado."""
        tag = int(self._tag_edit.text())
        return LoadPattern(
            tag=tag,
            name=self._name_edit.text().strip(),
            time_series_type=self._ts_combo.currentText(),
            loads=self._editing.loads if self._editing else [],
        )
```

##### 7B. Crear `gui/dialogs/nodal_load_dialog.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Diálogo para asignar cargas nodales dentro de un patrón de carga.

Permite seleccionar nodo, ingresar fuerzas Fx/Fy/Fz y momentos Mx/My/Mz,
y agregar múltiples cargas en secuencia.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from gui.core.model_data import LoadPattern, NodalLoad, StructuralModel


class NodalLoadDialog(QDialog):
    """Diálogo modal para asignar cargas nodales a un patrón."""

    def __init__(
        self,
        parent=None,
        model: Optional[StructuralModel] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Asignar cargas nodales")
        self.setMinimumWidth(500)
        self.setMinimumHeight(580)

        self._model = model or StructuralModel()
        self._applied = False

        layout = QVBoxLayout(self)

        # --- Selección de patrón ---
        grp_pattern = QGroupBox("Patrón de carga")
        pat_layout = QFormLayout()
        grp_pattern.setLayout(pat_layout)

        self._pattern_combo = QComboBox()
        if not self._model.load_patterns:
            self._pattern_combo.addItem("(sin patrones definidos)", None)
        else:
            for tag, pat in sorted(self._model.load_patterns.items()):
                self._pattern_combo.addItem(
                    f"{tag}: {pat.name} [{pat.time_series_type}]", tag
                )
        pat_layout.addRow("Patrón:", self._pattern_combo)
        layout.addWidget(grp_pattern)

        # --- Selección de nodo ---
        grp_load = QGroupBox("Carga nodal")
        load_form = QFormLayout()
        grp_load.setLayout(load_form)

        self._node_spin = QSpinBox()
        self._node_spin.setRange(1, 999_999)
        self._node_spin.setValue(1)
        load_form.addRow("Nodo:", self._node_spin)

        # Fuerzas
        self._fx_spin = QDoubleSpinBox()
        self._fx_spin.setDecimals(2)
        self._fx_spin.setRange(-1e10, 1e10)
        self._fx_spin.setSuffix(" kN")
        load_form.addRow("Fx:", self._fx_spin)

        self._fy_spin = QDoubleSpinBox()
        self._fy_spin.setDecimals(2)
        self._fy_spin.setRange(-1e10, 1e10)
        self._fy_spin.setSuffix(" kN")
        load_form.addRow("Fy:", self._fy_spin)

        self._fz_spin = QDoubleSpinBox()
        self._fz_spin.setDecimals(2)
        self._fz_spin.setRange(-1e10, 1e10)
        self._fz_spin.setSuffix(" kN")
        load_form.addRow("Fz:", self._fz_spin)

        # Momentos
        self._mx_spin = QDoubleSpinBox()
        self._mx_spin.setDecimals(2)
        self._mx_spin.setRange(-1e10, 1e10)
        self._mx_spin.setSuffix(" kN·m")
        load_form.addRow("Mx:", self._mx_spin)

        self._my_spin = QDoubleSpinBox()
        self._my_spin.setDecimals(2)
        self._my_spin.setRange(-1e10, 1e10)
        self._my_spin.setSuffix(" kN·m")
        load_form.addRow("My:", self._my_spin)

        self._mz_spin = QDoubleSpinBox()
        self._mz_spin.setDecimals(2)
        self._mz_spin.setRange(-1e10, 1e10)
        self._mz_spin.setSuffix(" kN·m")
        load_form.addRow("Mz:", self._mz_spin)

        layout.addWidget(grp_load)

        # --- Lista de cargas añadidas ---
        grp_list = QGroupBox("Cargas asignadas en esta sesión")
        list_layout = QVBoxLayout()
        grp_list.setLayout(list_layout)

        self._load_list = QListWidget()
        self._load_list.setMaximumHeight(120)
        list_layout.addWidget(self._load_list)

        layout.addWidget(grp_list)

        # --- Info ---
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #388E3C; padding: 4px;")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label)

        # --- Botones ---
        btn_layout = QHBoxLayout()

        self._btn_add = QPushButton("Agregar carga")
        self._btn_add.clicked.connect(self._on_add_load)
        btn_layout.addWidget(self._btn_add)

        self._btn_close = QPushButton("Cerrar")
        self._btn_close.setProperty("flat", "true")
        self._btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_close)

        layout.addLayout(btn_layout)

    # ---------------------------------------------------------------

    def _on_add_load(self) -> None:
        """Agrega la carga nodal al patrón seleccionado."""
        pat_tag = self._pattern_combo.currentData()
        if pat_tag is None:
            self._info_label.setText("⚠ No hay patrones de carga definidos.")
            self._info_label.setStyleSheet("color: #FF8F00; padding: 4px;")
            return

        node_tag = self._node_spin.value()
        if node_tag not in self._model.nodes:
            self._info_label.setText(f"❌ Nodo {node_tag} no existe.")
            self._info_label.setStyleSheet("color: #D32F2F; padding: 4px;")
            return

        load = NodalLoad(
            node_tag=node_tag,
            fx=self._fx_spin.value(),
            fy=self._fy_spin.value(),
            fz=self._fz_spin.value(),
            mx=self._mx_spin.value(),
            my=self._my_spin.value(),
            mz=self._mz_spin.value(),
        )

        # Agregar al patrón
        pattern = self._model.load_patterns.get(pat_tag)
        if pattern:
            pattern.loads.append(load)
            self._applied = True

        # Mostrar en lista
        forces = []
        if load.fx != 0:
            forces.append(f"Fx={load.fx}")
        if load.fy != 0:
            forces.append(f"Fy={load.fy}")
        if load.fz != 0:
            forces.append(f"Fz={load.fz}")
        if load.mx != 0:
            forces.append(f"Mx={load.mx}")
        if load.my != 0:
            forces.append(f"My={load.my}")
        if load.mz != 0:
            forces.append(f"Mz={load.mz}")
        desc = ", ".join(forces) if forces else "(sin cargas)"
        self._load_list.addItem(
            f"Nodo {node_tag}: {desc}"
        )

        self._info_label.setText(
            f"✔ Carga añadida al nodo {node_tag} (patrón {pat_tag})."
        )
        self._info_label.setStyleSheet("color: #388E3C; padding: 4px;")

        # Reset fuerzas para la siguiente carga
        for spin in (self._fx_spin, self._fy_spin, self._fz_spin,
                     self._mx_spin, self._my_spin, self._mz_spin):
            spin.setValue(0.0)
        self._node_spin.setValue(self._node_spin.value())
        self._node_spin.setFocus()

    @property
    def was_applied(self) -> bool:
        return self._applied
```

##### 7C. Modificar `gui/main_window.py` — Habilitar Patrones y Cargas

- [x] Agregar imports:

```python
from gui.dialogs.load_pattern_dialog import LoadPatternDialog
from gui.dialogs.nodal_load_dialog import NodalLoadDialog
```

- [x] En `_build_menubar`, reemplazar el bloque de Patrones de carga.

Reemplazar:
```python
        act_pattern = QAction("Patrones de carga...", self)
        act_pattern.setEnabled(False)
        m_define.addAction(act_pattern)
```
Con:
```python
        act_pattern = QAction("Patrones de carga...", self)
        act_pattern.setToolTip("Definir patrones de carga (TimeSeries)")
        act_pattern.triggered.connect(self._on_define_pattern)
        m_define.addAction(act_pattern)
```

- [x] En `_build_menubar`, reemplazar el bloque de Cargas nodales.

Reemplazar:
```python
        act_load = QAction("Cargas nodales...", self)
        act_load.setEnabled(False)
        m_assign.addAction(act_load)
```
Con:
```python
        act_load = QAction("Cargas nodales...", self)
        act_load.setToolTip("Asignar fuerzas y momentos a nodos")
        act_load.triggered.connect(self._on_assign_nodal_loads)
        m_assign.addAction(act_load)
```

- [x] Agregar slots:

```python
    def _on_define_pattern(self) -> None:
        """Abre el diálogo para crear un patrón de carga."""
        dlg = LoadPatternDialog(
            self,
            next_tag=self._model.next_pattern_tag(),
        )
        if dlg.exec():
            pat = dlg.get_pattern()
            self._model.load_patterns[pat.tag] = pat
            self._refresh_all()
            self._console.log_success(
                f"Patrón de carga creado: {pat.tag} — {pat.name}"
            )

    def _on_assign_nodal_loads(self) -> None:
        """Abre el diálogo para asignar cargas nodales."""
        if not self._model.load_patterns:
            self._console.log_error(
                "Primero debe crear un patrón de carga (Definir → Patrones de carga...)."
            )
            return
        if not self._model.nodes:
            self._console.log_error("No hay nodos en el modelo.")
            return
        dlg = NodalLoadDialog(self, model=self._model)
        dlg.exec()
        if dlg.was_applied:
            self._refresh_all()
            self._console.log_success("Cargas nodales asignadas.")
```

- [x] Expandir `_on_tree_item_double_clicked` para soportar patrones de carga:

Agregar al final del método:
```python
        elif category == "load_patterns":
            pat = self._model.load_patterns.get(tag)
            if not pat:
                return
            dlg = LoadPatternDialog(self, pattern=pat)
            if dlg.exec():
                edited = dlg.get_pattern()
                self._model.load_patterns[tag] = edited
                self._refresh_all()
                self._console.log(f"Patrón {tag} editado: {edited.name}")
```

##### Step 7 Verification Checklist

- [ ] Ejecutar GUI → Definir → Patrones de carga... → crear "Gravedad" (Constant) → aparece en tree
- [ ] Intentar Asignar → Cargas nodales sin patrones → error en consola
- [ ] Crear patrón → Asignar → Cargas nodales → seleccionar patrón → Nodo 15, Fz=-100 → "Agregar carga"
- [ ] Agregar segunda carga: Nodo 16, Fz=-50 → ambas aparecen en lista del diálogo
- [ ] Cerrar → verificar que las cargas están en el tree dentro del patrón
- [ ] Guardar como .opss → Abrir → cargas nodales y patrones persisten

#### Step 7 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: add load patterns and nodal load assignment

- Create LoadPatternDialog for defining load patterns
- Create NodalLoadDialog for assigning forces/moments to nodes
- Support sequential load addition within a pattern
- Enable Definir > Patrones de carga and Asignar > Cargas nodales"
```

---

#### Step 8: Viewport Mejorado — Etiquetas, Selección, Cargas

- [x] Crear `gui/viewport/picking.py` — lógica de selección interactiva
- [x] Refactorizar `gui/viewport/vtk_widget.py` — etiquetas, flechas de carga, picking
- [x] Modificar `gui/main_window.py` — botones toggle en toolbar + conexiones

##### 8A. Crear `gui/viewport/picking.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
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
```

##### 8B. Refactorizar `gui/viewport/vtk_widget.py` — Etiquetas, Flechas, Picking

La refactorización agrega tres capacidades toggleables al viewport existente. Se modifica el archivo existente con las siguientes adiciones:

- [x] Agregar imports al inicio del archivo. Después de los imports existentes, agregar:

```python
from PySide6.QtCore import Signal
from gui.viewport.picking import find_closest_node, find_closest_element
```

- [x] Agregar colores nuevos al bloque de constantes:

```python
COLOR_LOAD_FORCE = "#D32F2F"      # rojo — fuerzas
COLOR_LOAD_MOMENT = "#7B1FA2"     # morado — momentos
COLOR_HIGHLIGHT = "#FFD600"       # amarillo — selección
COLOR_LABEL = "#212121"           # negro/gris oscuro
```

- [x] En la clase `VTKViewport`, agregar señal y atributos de estado. Agregar inmediatamente después de la declaración de clase:

```python
    # Señal emitida al hacer clic en un nodo/elemento: (category, tag)
    item_picked = Signal(str, int)
```

- [x] En `__init__`, agregar flags de toggle después de `self._setup_renderer()`:

```python
        # Estado de toggles
        self._show_labels = False
        self._show_loads = False
        self._selected_tag: int | None = None
        self._selected_category: str | None = None
```

- [x] Agregar método toggle de etiquetas:

```python
    def toggle_labels(self, show: bool) -> None:
        """Activa/desactiva etiquetas de nodos y elementos."""
        self._show_labels = show
```

- [x] Agregar método toggle de cargas:

```python
    def toggle_loads(self, show: bool) -> None:
        """Activa/desactiva visualización de flechas de carga."""
        self._show_loads = show
```

- [x] En `display_model`, agregar llamadas condicionales. Después de `self._add_supports(model)`, añadir:

```python
        if self._show_labels:
            self._add_node_labels(model)
            self._add_element_labels(model)
        if self._show_loads:
            self._add_load_arrows(model)
```

- [x] Agregar método `_add_node_labels`:

```python
    def _add_node_labels(self, model: StructuralModel) -> None:
        """Muestra etiquetas numéricas en cada nodo."""
        if not model.nodes:
            return

        points = []
        labels = []
        for tag, node in model.nodes.items():
            points.append([node.x, node.y, node.z])
            labels.append(str(tag))

        cloud = pv.PolyData(np.array(points, dtype=float))
        cloud["labels"] = labels

        self.plotter.add_point_labels(
            cloud,
            "labels",
            font_size=10,
            text_color=COLOR_LABEL,
            point_size=0,
            shape=None,
            render_points_as_spheres=False,
            always_visible=True,
            name="node_labels",
        )
```

- [x] Agregar método `_add_element_labels`:

```python
    def _add_element_labels(self, model: StructuralModel) -> None:
        """Muestra etiquetas numéricas en el punto medio de cada elemento."""
        points = []
        labels = []

        for tag, elem in model.elements.items():
            ni = model.nodes.get(elem.node_i)
            nj = model.nodes.get(elem.node_j)
            if ni is None or nj is None:
                continue
            mid = [(ni.x + nj.x) / 2, (ni.y + nj.y) / 2, (ni.z + nj.z) / 2]
            points.append(mid)
            labels.append(str(tag))

        if not points:
            return

        cloud = pv.PolyData(np.array(points, dtype=float))
        cloud["labels"] = labels

        self.plotter.add_point_labels(
            cloud,
            "labels",
            font_size=9,
            text_color="#1565C0",
            point_size=0,
            shape=None,
            render_points_as_spheres=False,
            always_visible=True,
            name="element_labels",
        )
```

- [x] Agregar método `_add_load_arrows`:

```python
    def _add_load_arrows(self, model: StructuralModel) -> None:
        """Dibuja flechas 3D representando las cargas nodales."""
        force_origins: list[list[float]] = []
        force_dirs: list[list[float]] = []
        moment_origins: list[list[float]] = []
        moment_dirs: list[list[float]] = []

        # Recopilar todas las cargas de todos los patrones
        for pattern in model.load_patterns.values():
            for load in pattern.loads:
                node = model.nodes.get(load.node_tag)
                if node is None:
                    continue
                origin = [node.x, node.y, node.z]

                # Fuerzas
                for comp, axis in [(load.fx, [1, 0, 0]),
                                   (load.fy, [0, 1, 0]),
                                   (load.fz, [0, 0, 1])]:
                    if abs(comp) > 1e-6:
                        sign = 1.0 if comp > 0 else -1.0
                        force_origins.append(origin)
                        force_dirs.append([a * sign for a in axis])

                # Momentos
                for comp, axis in [(load.mx, [1, 0, 0]),
                                   (load.my, [0, 1, 0]),
                                   (load.mz, [0, 0, 1])]:
                    if abs(comp) > 1e-6:
                        sign = 1.0 if comp > 0 else -1.0
                        moment_origins.append(origin)
                        moment_dirs.append([a * sign for a in axis])

        # Escala de flechas (longitud fija para visibilidad)
        arrow_scale = 0.8

        # Dibujar flechas de fuerzas
        if force_origins:
            origins = np.array(force_origins, dtype=float)
            dirs = np.array(force_dirs, dtype=float)
            arrows = pv.PolyData(origins)
            arrows["vectors"] = dirs * arrow_scale
            arrows.set_active_vectors("vectors")
            glyphs = arrows.glyph(
                orient="vectors",
                scale=False,
                factor=arrow_scale,
                geom=pv.Arrow(
                    start=(0, 0, 0),
                    direction=(1, 0, 0),
                    tip_length=0.3,
                    tip_radius=0.1,
                    shaft_radius=0.03,
                    shaft_resolution=12,
                ),
            )
            self.plotter.add_mesh(
                glyphs,
                color=COLOR_LOAD_FORCE,
                name="load_force_arrows",
            )

        # Dibujar flechas de momentos (más delgadas, color distinto)
        if moment_origins:
            origins = np.array(moment_origins, dtype=float)
            dirs = np.array(moment_dirs, dtype=float)
            arrows = pv.PolyData(origins)
            arrows["vectors"] = dirs * arrow_scale * 0.7
            arrows.set_active_vectors("vectors")
            glyphs = arrows.glyph(
                orient="vectors",
                scale=False,
                factor=arrow_scale * 0.7,
                geom=pv.Arrow(
                    start=(0, 0, 0),
                    direction=(1, 0, 0),
                    tip_length=0.35,
                    tip_radius=0.08,
                    shaft_radius=0.02,
                    shaft_resolution=12,
                ),
            )
            self.plotter.add_mesh(
                glyphs,
                color=COLOR_LOAD_MOMENT,
                name="load_moment_arrows",
            )
```

- [x] Agregar método `highlight_node` para selección:

```python
    def highlight_node(self, model: StructuralModel, tag: int) -> None:
        """Resalta un nodo con color amarillo."""
        self.plotter.remove_actor("highlight", render=False)
        node = model.nodes.get(tag)
        if not node:
            return
        sphere = pv.Sphere(radius=0.2, center=(node.x, node.y, node.z))
        self.plotter.add_mesh(
            sphere,
            color=COLOR_HIGHLIGHT,
            opacity=0.8,
            name="highlight",
        )
```

- [x] Agregar método `highlight_element` para selección:

```python
    def highlight_element(self, model: StructuralModel, tag: int) -> None:
        """Resalta un elemento con color amarillo."""
        self.plotter.remove_actor("highlight", render=False)
        elem = model.elements.get(tag)
        if not elem:
            return
        ni = model.nodes.get(elem.node_i)
        nj = model.nodes.get(elem.node_j)
        if not ni or not nj:
            return
        line = pv.Line(
            pointa=(ni.x, ni.y, ni.z),
            pointb=(nj.x, nj.y, nj.z),
        )
        self.plotter.add_mesh(
            line,
            color=COLOR_HIGHLIGHT,
            line_width=8,
            render_lines_as_tubes=True,
            name="highlight",
        )
```

- [x] Agregar método `clear_highlight`:

```python
    def clear_highlight(self) -> None:
        """Elimina cualquier resaltado activo."""
        self.plotter.remove_actor("highlight", render=False)
```

- [x] Agregar método `enable_picking` que registra el callback de clic:

```python
    def enable_picking(self, model: StructuralModel) -> None:
        """Habilita picking interactivo en el viewport."""
        self._pick_model = model

        def _on_pick(point):
            if point is None:
                return
            p = (point[0], point[1], point[2])
            # Primero intentar nodo, luego elemento
            node_tag = find_closest_node(self._pick_model, p, tolerance=0.5)
            if node_tag is not None:
                self.highlight_node(self._pick_model, node_tag)
                self.item_picked.emit("nodes", node_tag)
                return
            elem_tag = find_closest_element(self._pick_model, p, tolerance=0.5)
            if elem_tag is not None:
                self.highlight_element(self._pick_model, elem_tag)
                self.item_picked.emit("elements", elem_tag)

        self.plotter.enable_point_picking(
            callback=_on_pick,
            show_message=False,
            show_point=False,
            use_picker=True,
            picker="cell",
            tolerance=0.025,
        )
```

##### 8C. Modificar `gui/main_window.py` — Toggle buttons + Picking

- [x] En `_build_toolbar`, agregar botones toggle después del separador final. Añadir antes del cierre del método:

```python
        tb.addSeparator()

        self._act_labels = QAction("Etiquetas", self)
        self._act_labels.setToolTip("Mostrar/ocultar etiquetas de nodos y elementos")
        self._act_labels.setCheckable(True)
        self._act_labels.setChecked(False)
        self._act_labels.toggled.connect(self._on_toggle_labels)
        tb.addAction(self._act_labels)

        self._act_loads = QAction("Cargas", self)
        self._act_loads.setToolTip("Mostrar/ocultar flechas de carga")
        self._act_loads.setCheckable(True)
        self._act_loads.setChecked(False)
        self._act_loads.toggled.connect(self._on_toggle_loads)
        tb.addAction(self._act_loads)
```

- [x] Agregar los toggle slots:

```python
    def _on_toggle_labels(self, checked: bool) -> None:
        """Toggle de etiquetas de nodos/elementos."""
        self._viewport.toggle_labels(checked)
        self._viewport.display_model(self._model)
        state = "activadas" if checked else "desactivadas"
        self._console.log(f"Etiquetas {state}.")

    def _on_toggle_loads(self, checked: bool) -> None:
        """Toggle de visualización de cargas."""
        self._viewport.toggle_loads(checked)
        self._viewport.display_model(self._model)
        state = "activadas" if checked else "desactivadas"
        self._console.log(f"Flechas de carga {state}.")
```

- [x] Conectar picking. En `_refresh_all`, después de `self._viewport.display_model(self._model)`, agregar:

```python
        self._viewport.enable_picking(self._model)
```

- [x] Conectar la señal de picking. En `__init__`, después de la conexión de `item_selected`, agregar:

```python
        self._viewport.item_picked.connect(self._on_viewport_pick)
```

- [x] Agregar slot de picking:

```python
    def _on_viewport_pick(self, category: str, tag: int) -> None:
        """Maneja la selección de un objeto en el viewport."""
        self._properties.show_item(self._model, category, tag)
        self._console.log(f"Seleccionado: {category} → tag {tag}")
```

##### Step 8 Verification Checklist

- [ ] Ejecutar GUI → Cargar demo → Toolbar: "Etiquetas" toggle → números de nodos y elementos visibles
- [ ] Desactivar "Etiquetas" → números desaparecen
- [ ] Crear patrón de carga → asignar cargas → activar "Cargas" toggle → flechas rojas visibles
- [ ] Asignar momentos → flechas moradas visibles
- [ ] Clic en nodo en viewport → nodo resaltado amarillo + properties panel muestra info del nodo
- [ ] Clic en elemento → elemento resaltado amarillo + properties panel muestra info del elemento
- [ ] Alternar entre nodo y elemento → highlight se actualiza correctamente
- [ ] Guardar/Abrir → toggles mantienen su estado visual

#### Step 8 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: enhance viewport with labels, loads, and picking

- Add toggle for node/element labels (tag numbers)
- Add load visualization with force (red) and moment (purple) arrows
- Implement interactive picking via VTK point picker
- Highlight selected nodes (yellow sphere) and elements (yellow tube)
- Connect picking to properties panel for instant inspection
- Add toolbar toggle buttons for Labels and Loads"
```

---

## Sprint 3 Complete

Al finalizar Sprint 3, el estado de la GUI es:

| Feature | Estado |
|---------|--------|
| Definir → Patrones de carga | ✅ Funcional |
| Asignar → Cargas nodales | ✅ Funcional (con selección de patrón) |
| Etiquetas de nodos/elementos | ✅ Toggle en toolbar |
| Flechas de carga (fuerzas/momentos) | ✅ Toggle en toolbar |
| Selección interactiva (picking) | ✅ Click en viewport → highlight + properties |
| Doble-clic para editar patrones | ✅ Funcional |

**Pipeline completa disponible:**
```
Definir (materiales, secciones, transf, patrones)
  → Dibujar (nodos, elementos)
    → Asignar (restricciones, cargas)
      → [Sprint 4: Analizar]
```

**Archivos nuevos creados:** 3
- `gui/dialogs/load_pattern_dialog.py`
- `gui/dialogs/nodal_load_dialog.py`
- `gui/viewport/picking.py`

**Archivos modificados:** 2
- `gui/viewport/vtk_widget.py` (etiquetas, flechas, picking, highlight)
- `gui/main_window.py` (2 nuevas acciones + toggle buttons + picking)
