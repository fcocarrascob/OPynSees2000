# Sprint 1: Persistencia + Definición de Propiedades

## Goal
Implementar serialización JSON del modelo (save/load), diálogos de definición de materiales, secciones y transformaciones geométricas — habilitando los 4 menús placeholder del grupo "Definir".

## Prerequisites
Asegurar que el usuario está en la branch `feat/gui-sap2000-workflow`.
Si no existe, crearla desde `main`:
```bash
git checkout -b feat/gui-sap2000-workflow
```

---

### Step-by-Step Instructions

---

#### Step 1: Serialización y Proyecto (Save/Load)

#### Step 1: Serialización y Proyecto (Save/Load)

- [x] Agregar métodos `to_dict()` y `from_dict()` a **todas** las dataclasses en `gui/core/model_data.py`
- [x] Crear el archivo `gui/core/project_io.py`
- [x] Modificar `gui/main_window.py` para agregar acciones Abrir / Guardar

##### 1A. Agregar serialización a `gui/core/model_data.py`

Agregar los siguientes métodos a cada clase. La posición exacta de inserción se indica para cada una.

- [ ] En la clase `Node`, agregar después del property `is_fully_fixed`:

- [x] En la clase `Node`, agregar después del property `is_fully_fixed`:

```python
    def to_dict(self) -> dict:
        """Serializa el nodo a diccionario."""
        return {
            "tag": self.tag,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "fixity": list(self.fixity),
            "mass": list(self.mass),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        """Crea un nodo desde diccionario."""
        return cls(
            tag=d["tag"],
            x=d["x"],
            y=d["y"],
            z=d.get("z", 0.0),
            fixity=tuple(d.get("fixity", ())),
            mass=tuple(d.get("mass", ())),
        )
```

- [ ] En la clase `Material`, agregar al final de la clase (después del comentario de params):

- [x] En la clase `Material`, agregar al final de la clase (después del comentario de params):

```python
    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "mat_type": self.mat_type.value,
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Material":
        return cls(
            tag=d["tag"],
            name=d["name"],
            mat_type=MaterialType(d["mat_type"]),
            params=d.get("params", {}),

- [ ] En la clase `Section`, agregar al final:

- [x] En la clase `Section`, agregar al final:

```python
    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "sec_type": self.sec_type.value,
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Section":
        return cls(
            tag=d["tag"],
            name=d["name"],
            sec_type=SectionType(d["sec_type"]),
            params=d.get("params", {}),
        )
```

- [ ] En la clase `GeomTransf`, agregar al final:

```python
    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "transf_type": self.transf_type.value,
            "vecxz": list(self.vecxz),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GeomTransf":
        return cls(
            tag=d["tag"],
            transf_type=TransfType(d["transf_type"]),
            vecxz=tuple(d.get("vecxz", (0.0, 0.0, 1.0))),
        )
```

- [ ] En la clase `Element`, agregar al final:

- [x] En la clase `Element`, agregar al final:
    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "elem_type": self.elem_type.value,
            "node_i": self.node_i,
            "node_j": self.node_j,
            "section_tag": self.section_tag,
            "transf_tag": self.transf_tag,
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Element":
        return cls(
            tag=d["tag"],
            elem_type=ElementType(d["elem_type"]),
            node_i=d["node_i"],
            node_j=d["node_j"],
            section_tag=d.get("section_tag"),
            transf_tag=d.get("transf_tag"),
```

- [ ] En la clase `NodalLoad`, agregar al final:

- [x] En la clase `NodalLoad`, agregar al final:

```python
    def to_dict(self) -> dict:
        return {
            "node_tag": self.node_tag,
            "fx": self.fx, "fy": self.fy, "fz": self.fz,
            "mx": self.mx, "my": self.my, "mz": self.mz,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NodalLoad":
        return cls(
            node_tag=d["node_tag"],
        )
```

- [ ] En la clase `LoadPattern`, agregar al final:

- [x] En la clase `LoadPattern`, agregar al final:

```python
    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "name": self.name,
            "time_series_type": self.time_series_type,
            "loads": [load.to_dict() for load in self.loads],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LoadPattern":
        return cls(
            tag=d["tag"],
            name=d["name"],
            time_series_type=d.get("time_series_type", "Constant"),
            loads=[NodalLoad.from_dict(ld) for ld in d.get("loads", [])],
        )
```

- [x] En la clase `StructuralModel`, agregar los siguientes métodos **antes** del método `clear()`:

```python
    def to_dict(self) -> dict:
        """Serializa el modelo completo a diccionario."""
        return {
            "ndm": self.ndm,
            "ndf": self.ndf,
            "nodes": {str(k): v.to_dict() for k, v in self.nodes.items()},
            "materials": {str(k): v.to_dict() for k, v in self.materials.items()},
            "sections": {str(k): v.to_dict() for k, v in self.sections.items()},
            "geom_transfs": {str(k): v.to_dict() for k, v in self.geom_transfs.items()},
            "elements": {str(k): v.to_dict() for k, v in self.elements.items()},
            "load_patterns": {str(k): v.to_dict() for k, v in self.load_patterns.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StructuralModel":
        for k, v in d.get("nodes", {}).items():
            model.nodes[int(k)] = Node.from_dict(v)
        for k, v in d.get("materials", {}).items():
            model.materials[int(k)] = Material.from_dict(v)
        for k, v in d.get("sections", {}).items():
            model.sections[int(k)] = Section.from_dict(v)
        for k, v in d.get("geom_transfs", {}).items():
            model.geom_transfs[int(k)] = GeomTransf.from_dict(v)
        for k, v in d.get("elements", {}).items():
            model.elements[int(k)] = Element.from_dict(v)
        for k, v in d.get("load_patterns", {}).items():
            model.load_patterns[int(k)] = LoadPattern.from_dict(v)
        return model
```

##### 1B. Crear `gui/core/project_io.py`

- [x] Crear el archivo `gui/core/project_io.py` con el siguiente contenido completo:

```python

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
```

##### 1C. Modificar `gui/main_window.py` — Agregar Save/Load

- [x] Agregar `QFileDialog` al bloque de imports de PySide6:

Reemplazar:
```python
from PySide6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
)
```
Con:
```python
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
)
```

- [x] Agregar import de `project_io` después de los imports de gui existentes:

Después de la línea `from gui.viewport.vtk_widget import VTKViewport`, agregar:
```python
from gui.core.project_io import save_project, load_project, FILE_FILTER
```

- [x] En `__init__`, agregar variable de archivo actual. Después de `self._model = StructuralModel.create_demo()`, agregar:

```python
        self._current_file: Path | None = None
```

- [x] En `_build_menubar`, reemplazar la sección completa `# --- Archivo ---` con:

```python
        # --- Archivo ---
        m_file = mb.addMenu("&Archivo")

        act_new = QAction("Nuevo modelo", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._on_new_model)
        m_file.addAction(act_new)

        act_open = QAction("Abrir...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._on_open)
        m_file.addAction(act_open)

        act_save = QAction("Guardar como...", self)
        act_save.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save.triggered.connect(self._on_save_as)
        m_file.addAction(act_save)

        m_file.addSeparator()

        act_demo = QAction("Cargar demo", self)
        act_demo.triggered.connect(self._on_load_demo)
        m_file.addAction(act_demo)

        m_file.addSeparator()

        act_exit = QAction("Salir", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        m_file.addAction(act_exit)
```

- [x] En `_build_toolbar`, agregar botones de Abrir y Guardar. Después del botón "Demo" y antes del `tb.addSeparator()`, agregar:

```python
        act_open_tb = QAction("Abrir", self)
        act_open_tb.setToolTip("Abrir proyecto (Ctrl+O)")
        act_open_tb.triggered.connect(self._on_open)
        tb.addAction(act_open_tb)

        act_save_tb = QAction("Guardar", self)
        act_save_tb.setToolTip("Guardar como... (Ctrl+Shift+S)")
        act_save_tb.triggered.connect(self._on_save_as)
        tb.addAction(act_save_tb)
```

- [x] En la sección Slots, agregar los siguientes métodos nuevos (después de `_on_about`):

```python
    def _on_open(self) -> None:
        """Abre un archivo .opss."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir proyecto", "", FILE_FILTER,
        )
        if not path:
            return
        try:
            self._model = load_project(Path(path))
            self._current_file = Path(path)
            self._refresh_all()
            self._update_title()
            self._console.log_success(f"Proyecto abierto: {path}")
        except Exception as exc:
            self._console.log_error(f"Error al abrir: {exc}")

    def _on_save_as(self) -> None:
        """Guarda el modelo como archivo .opss."""
        default_name = str(self._current_file) if self._current_file else ""
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar proyecto como", default_name, FILE_FILTER,
        )
        if not path:
            return
        if not path.endswith(".opss"):
            path += ".opss"
        try:
            save_project(self._model, Path(path))
            self._current_file = Path(path)
            self._update_title()
            self._console.log_success(f"Proyecto guardado: {path}")
        except Exception as exc:
            self._console.log_error(f"Error al guardar: {exc}")

    def _update_title(self) -> None:
        """Actualiza el título de la ventana con el nombre del archivo."""
        base = "OPynSees2000 — OpenSeesPy GUI"
        if self._current_file:
            base = f"{self._current_file.stem} — {base}"
        self.setWindowTitle(base)
```

- [ ] Modificar `_on_new_model` para reiniciar el archivo actual:

Reemplazar:
```python
    def _on_new_model(self) -> None:
        self._model.clear()
        self._refresh_all()
        self._console.log("Modelo limpiado.")
```
Con:
```python
    def _on_new_model(self) -> None:
        self._model.clear()
        self._current_file = None
        self._update_title()
        self._refresh_all()
        self._console.log("Modelo limpiado.")
```

##### Step 1 Verification Checklist

- [ ] Sin errores de compilación (`python -c "from gui.core.model_data import StructuralModel; m = StructuralModel.create_demo(); d = m.to_dict(); m2 = StructuralModel.from_dict(d); print(f'OK: {len(m2.nodes)} nodos')"`)
- [ ] Ejecutar la GUI (`python -m gui`) — verificar que el menú Archivo tiene: Nuevo, Abrir, Guardar como, Cargar demo, Salir
- [ ] Cargar demo → Guardar como `test.opss` → Nuevo → Abrir `test.opss` → verificar que el modelo se recupera (27 nodos, 54 elementos)
- [ ] Verificar que el JSON de `test.opss` es legible y tiene estructura clara
- [ ] Verificar que el título de la ventana muestra el nombre del archivo

#### Step 1 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: add JSON serialization (save/load .opss files)

- Add to_dict/from_dict to all model dataclasses
- Create project_io module for save/load
- Add Abrir/Guardar como menu actions and toolbar buttons
- Track current file path and update window title"
```

---

#### Step 2: Diálogo de Materiales

- [x] Crear el archivo `gui/dialogs/material_dialog.py`
- [x] Modificar `gui/main_window.py` para habilitar y conectar la acción de Materiales

##### 2A. Crear `gui/dialogs/material_dialog.py`

-- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Diálogo para crear / editar materiales uniaxiales.

Campos dinámicos que cambian según el tipo de material seleccionado.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QVBoxLayout,
)

from gui.core.model_data import Material, MaterialType


# ---------------------------------------------------------------------------
# Esquema de parámetros por tipo de material
# Cada entrada: (clave_param, etiqueta_ui, valor_por_defecto)
# ---------------------------------------------------------------------------

MATERIAL_PARAMS: dict[MaterialType, list[tuple[str, str, float]]] = {
    MaterialType.ELASTIC: [
        ("E", "Módulo de elasticidad E [kN/m²]", 200_000_000.0),
    ],
    MaterialType.STEEL02: [
        ("Fy", "Esfuerzo de fluencia Fy [kN/m²]", 420_000.0),
        ("E0", "Módulo elástico E0 [kN/m²]", 200_000_000.0),
        ("b", "Razón de endurecimiento b", 0.01),
        ("R0", "Parámetro R0", 18.0),
        ("cR1", "Parámetro cR1", 0.925),
        ("cR2", "Parámetro cR2", 0.15),
    ],
    MaterialType.CONCRETE01: [
        ("fpc", "Resistencia pico f'c [kN/m²]", -28_000.0),
        ("epsc0", "Deformación en f'c", -0.002),
        ("fpcu", "Resistencia residual [kN/m²]", -5_600.0),
        ("epsU", "Deformación última", -0.005),
    ],
    MaterialType.CONCRETE02: [
        ("fpc", "Resistencia pico f'c [kN/m²]", -28_000.0),
        ("epsc0", "Deformación en f'c", -0.002),
        ("fpcu", "Resistencia residual [kN/m²]", -5_600.0),
        ("epsU", "Deformación última", -0.005),
        ("lam", "Factor de rigidez de descarga λ", 0.1),
        ("ft", "Resistencia a tracción ft [kN/m²]", 2_800.0),
        ("Ets", "Módulo de softening Ets [kN/m²]", 1_400_000.0),
    ],
    MaterialType.ELASTIC_PP: [
        ("E", "Módulo de elasticidad E [kN/m²]", 200_000_000.0),
        ("epsyP", "Deformación de fluencia (+)", 0.002),
    ],
    MaterialType.HYSTERETIC: [
        ("s1p", "Esfuerzo punto 1 (+) [kN/m²]", 420_000.0),
        ("e1p", "Deformación punto 1 (+)", 0.002),
        ("s2p", "Esfuerzo punto 2 (+) [kN/m²]", 500_000.0),
        ("e2p", "Deformación punto 2 (+)", 0.01),
        ("s3p", "Esfuerzo punto 3 (+) [kN/m²]", 420_000.0),
        ("e3p", "Deformación punto 3 (+)", 0.05),
        ("s1n", "Esfuerzo punto 1 (−) [kN/m²]", -420_000.0),
        ("e1n", "Deformación punto 1 (−)", -0.002),
        ("s2n", "Esfuerzo punto 2 (−) [kN/m²]", -500_000.0),
        ("e2n", "Deformación punto 2 (−)", -0.01),
        ("s3n", "Esfuerzo punto 3 (−) [kN/m²]", -420_000.0),
        ("e3n", "Deformación punto 3 (−)", -0.05),
        ("pinchX", "Factor pinchX", 0.8),
        ("pinchY", "Factor pinchY", 0.2),
        ("damage1", "Daño 1", 0.0),
        ("damage2", "Daño 2", 0.0),
        ("beta", "Beta (degradación rigidez)", 0.0),
    ],
}


class MaterialDialog(QDialog):
    """Diálogo modal para crear o editar un material uniaxial."""

    def __init__(
        self,
        parent=None,
        material: Optional[Material] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar material" if material else "Nuevo material")
        self.setMinimumWidth(440)

        self._editing = material
        self._param_widgets: dict[str, QDoubleSpinBox] = {}

        layout = QVBoxLayout(self)

        # --- Información básica ---
        grp_info = QGroupBox("Información")
        form_info = QFormLayout()
        grp_info.setLayout(form_info)

        self._tag_edit = QLineEdit(str(material.tag if material else next_tag))
        self._tag_edit.setReadOnly(True)
        form_info.addRow("Tag:", self._tag_edit)

        self._name_edit = QLineEdit(material.name if material else "")
        self._name_edit.setPlaceholderText("Ej: Acero A36, Concreto f'c=28 MPa")
        form_info.addRow("Nombre:", self._name_edit)

        self._type_combo = QComboBox()
        for mt in MaterialType:
            self._type_combo.addItem(mt.value, mt)
        if material:
            idx = self._type_combo.findData(material.mat_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
        self._type_combo.currentIndexChanged.connect(self._rebuild_params)
        form_info.addRow("Tipo:", self._type_combo)

        layout.addWidget(grp_info)

        # --- Parámetros (dinámico) ---
        self._params_group = QGroupBox("Parámetros")
        self._params_layout = QFormLayout()
        self._params_group.setLayout(self._params_layout)
        layout.addWidget(self._params_group)

        # --- Botones ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Construir parámetros iniciales
        self._rebuild_params()

    # ---------------------------------------------------------------
    # Parámetros dinámicos
    # ---------------------------------------------------------------

    def _rebuild_params(self) -> None:
        """Reconstruye los campos de parámetros según el tipo seleccionado."""
        # Limpiar layout anterior
        while self._params_layout.count():
            child = self._params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._param_widgets.clear()

        mat_type: MaterialType = self._type_combo.currentData()
        schema = MATERIAL_PARAMS.get(mat_type, [])

        for key, label, default in schema:
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e15, 1e15)
            # Si estamos editando y el param existe, usar su valor
            if (
                self._editing
                and self._editing.mat_type == mat_type
                and key in self._editing.params
            ):
                spin.setValue(self._editing.params[key])
            else:
                spin.setValue(default)
            self._param_widgets[key] = spin
            self._params_layout.addRow(label, spin)

    # ---------------------------------------------------------------
    # Aceptar
    # ---------------------------------------------------------------

    def _on_accept(self) -> None:
        """Valida y acepta el diálogo."""
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            self._name_edit.setStyleSheet("border: 1px solid #D32F2F;")
            return
        self._name_edit.setStyleSheet("")
        self.accept()

    # ---------------------------------------------------------------
    # Resultado
    # ---------------------------------------------------------------

    def get_material(self) -> Material:
        """Retorna el material configurado con los valores del diálogo."""
        tag = int(self._tag_edit.text())
        name = self._name_edit.text().strip()
        mat_type: MaterialType = self._type_combo.currentData()
        params = {k: w.value() for k, w in self._param_widgets.items()}
        return Material(tag=tag, name=name, mat_type=mat_type, params=params)
```

##### 2B. Modificar `gui/main_window.py` — Habilitar Materiales

-- [x] Agregar import del diálogo. Después de `from gui.core.project_io import ...`, agregar:

```python
from gui.dialogs.material_dialog import MaterialDialog
```

- [ ] En `_build_menubar`, reemplazar el bloque de la acción de Materiales.

Reemplazar:
```python
        act_mat = QAction("Materiales...", self)
        act_mat.setToolTip("Definir materiales uniaxiales")
        act_mat.setEnabled(False)  # placeholder
        m_define.addAction(act_mat)
```
Con:
```python
        act_mat = QAction("Materiales...", self)
        act_mat.setToolTip("Definir materiales uniaxiales")
        act_mat.triggered.connect(self._on_define_material)
        m_define.addAction(act_mat)
```

-- [x] En `__init__`, agregar conexión de doble-clic en el tree. Después de `self._tree.item_selected.connect(self._on_tree_item_selected)`, agregar:

```python
    self._tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
```

-- [x] En la sección Slots, agregar los siguientes métodos (después de `_on_save_as`):

```python
    def _on_define_material(self) -> None:
        """Abre el diálogo para crear un nuevo material."""
        dlg = MaterialDialog(
            self,
            next_tag=self._model.next_material_tag(),
        )
        if dlg.exec():
            mat = dlg.get_material()
            self._model.materials[mat.tag] = mat
            self._refresh_all()
            self._console.log_success(
                f"Material creado: {mat.tag} — {mat.name} [{mat.mat_type.value}]"
            )

    def _on_tree_item_double_clicked(self, item, column) -> None:
        """Abre diálogo de edición al hacer doble-clic en un ítem del tree."""
        category = item.data(0, 100)
        tag = item.data(0, 101)
        if tag is None:
            return

        if category == "materials":
            mat = self._model.materials.get(tag)
            if not mat:
                return
            dlg = MaterialDialog(self, material=mat)
            if dlg.exec():
                edited = dlg.get_material()
                self._model.materials[tag] = edited
                self._refresh_all()
                self._console.log(f"Material {tag} editado: {edited.name}")
```

##### Step 2 Verification Checklist

- [ ] Sin errores al importar: `python -c "from gui.dialogs.material_dialog import MaterialDialog; print('OK')"`
- [ ] Ejecutar la GUI → Menú Definir → Materiales... → se abre el diálogo
- [ ] Crear material Elastic con nombre "Acero A36" y E=200000000 → aparece en el tree bajo "Materiales (1)"
- [ ] Cambiar tipo a Steel02 → aparecen campos Fy, E0, b, R0, cR1, cR2
- [ ] Cambiar tipo a Concrete01 → aparecen campos fpc, epsc0, fpcu, epsU
- [ ] Doble-clic en el material creado en el tree → abre diálogo con valores precargados
- [ ] Editar el nombre y aceptar → el tree se actualiza con el nuevo nombre
- [ ] El material del demo "Concreto f'c=28 MPa" también se puede editar con doble-clic

#### Step 2 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: add material definition dialog

- Create MaterialDialog with dynamic parameter fields per material type
- Support Elastic, Steel02, Concrete01/02, ElasticPP, Hysteretic
- Enable Definir > Materiales menu action
- Double-click on tree item opens edit dialog"
```

---

#### Step 3: Diálogos de Secciones y Transformaciones

- [x] Crear `gui/dialogs/section_dialog.py`
- [x] Crear `gui/dialogs/transf_dialog.py`
- [x] Modificar `gui/main_window.py` para habilitar y conectar ambas acciones


##### 3A. Crear `gui/dialogs/section_dialog.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Diálogo para crear / editar secciones transversales.

Campos dinámicos que cambian según el tipo de sección.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from gui.core.model_data import Section, SectionType


# ---------------------------------------------------------------------------
# Esquema de parámetros por tipo de sección
# ---------------------------------------------------------------------------

SECTION_PARAMS: dict[SectionType, list[tuple[str, str, float]]] = {
    SectionType.ELASTIC_2D: [
        ("A", "Área A [m²]", 0.16),
        ("E", "Módulo E [kN/m²]", 24_821_000.0),
        ("Iz", "Inercia Iz [m⁴]", 2.1333e-3),
    ],
    SectionType.ELASTIC_3D: [
        ("A", "Área A [m²]", 0.16),
        ("E", "Módulo E [kN/m²]", 24_821_000.0),
        ("Iz", "Inercia Iz [m⁴]", 2.1333e-3),
        ("Iy", "Inercia Iy [m⁴]", 2.1333e-3),
        ("G", "Módulo de corte G [kN/m²]", 10_342_000.0),
        ("J", "Constante de torsión J [m⁴]", 3.6053e-3),
    ],
    SectionType.FIBER: [],  # Secciones de fibra requieren manejo especial (futuro)
}


class SectionDialog(QDialog):
    """Diálogo modal para crear o editar una sección transversal."""

    def __init__(
        self,
        parent=None,
        section: Optional[Section] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar sección" if section else "Nueva sección")
        self.setMinimumWidth(440)

        self._editing = section
        self._param_widgets: dict[str, QDoubleSpinBox] = {}

        layout = QVBoxLayout(self)

        # --- Información básica ---
        grp_info = QGroupBox("Información")
        form_info = QFormLayout()
        grp_info.setLayout(form_info)

        self._tag_edit = QLineEdit(str(section.tag if section else next_tag))
        self._tag_edit.setReadOnly(True)
        form_info.addRow("Tag:", self._tag_edit)

        self._name_edit = QLineEdit(section.name if section else "")
        self._name_edit.setPlaceholderText("Ej: Columna 40×40, Viga 30×50")
        form_info.addRow("Nombre:", self._name_edit)

        self._type_combo = QComboBox()
        for st in SectionType:
            self._type_combo.addItem(st.value, st)
        if section:
            idx = self._type_combo.findData(section.sec_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
        self._type_combo.currentIndexChanged.connect(self._rebuild_params)
        form_info.addRow("Tipo:", self._type_combo)

        layout.addWidget(grp_info)

        # --- Parámetros (dinámico) ---
        self._params_group = QGroupBox("Parámetros")
        self._params_layout = QFormLayout()
        self._params_group.setLayout(self._params_layout)
        layout.addWidget(self._params_group)

        # --- Nota para tipo Fiber ---
        self._fiber_label = QLabel(
            "⚠ Las secciones de fibra requieren un editor\n"
            "especializado (disponible en versión futura)."
        )
        self._fiber_label.setStyleSheet("color: #FF8F00; padding: 8px;")
        self._fiber_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fiber_label.setVisible(False)
        layout.addWidget(self._fiber_label)

        # --- Botones ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Construir parámetros iniciales
        self._rebuild_params()

    # ---------------------------------------------------------------

    def _rebuild_params(self) -> None:
        """Reconstruye los campos según el tipo de sección."""
        while self._params_layout.count():
            child = self._params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._param_widgets.clear()

        sec_type: SectionType = self._type_combo.currentData()
        schema = SECTION_PARAMS.get(sec_type, [])

        # Mostrar/ocultar nota de fiber
        self._fiber_label.setVisible(sec_type == SectionType.FIBER)

        for key, label, default in schema:
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e15, 1e15)
            if (
                self._editing
                and self._editing.sec_type == sec_type
                and key in self._editing.params
            ):
                spin.setValue(self._editing.params[key])
            else:
                spin.setValue(default)
            self._param_widgets[key] = spin
            self._params_layout.addRow(label, spin)

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            self._name_edit.setStyleSheet("border: 1px solid #D32F2F;")
            return
        self._name_edit.setStyleSheet("")
        self.accept()

    def get_section(self) -> Section:
        """Retorna la sección configurada."""
        tag = int(self._tag_edit.text())
        name = self._name_edit.text().strip()
        sec_type: SectionType = self._type_combo.currentData()
        params = {k: w.value() for k, w in self._param_widgets.items()}
        return Section(tag=tag, name=name, sec_type=sec_type, params=params)
```


##### 3B. Crear `gui/dialogs/transf_dialog.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
Diálogo para crear / editar transformaciones geométricas.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from gui.core.model_data import GeomTransf, TransfType


# Presets de vectores vecxz comunes
VECXZ_PRESETS: dict[str, tuple[float, float, float]] = {
    "Columnas (vertical Z)": (0.0, 0.0, 1.0),
    "Vigas en X": (0.0, 0.0, 1.0),
    "Vigas en Y": (0.0, 0.0, 1.0),
    "Columnas (plano XZ)": (1.0, 0.0, 0.0),
    "Personalizado": (0.0, 0.0, 1.0),
}


class TransfDialog(QDialog):
    """Diálogo modal para crear o editar una transformación geométrica."""

    def __init__(
        self,
        parent=None,
        transf: Optional[GeomTransf] = None,
        next_tag: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Editar transformación" if transf else "Nueva transformación"
        )
        self.setMinimumWidth(400)

        self._editing = transf

        layout = QVBoxLayout(self)

        # --- Información básica ---
        grp_info = QGroupBox("Información")
        form_info = QFormLayout()
        grp_info.setLayout(form_info)

        self._tag_edit = QLineEdit(str(transf.tag if transf else next_tag))
        self._tag_edit.setReadOnly(True)
        form_info.addRow("Tag:", self._tag_edit)

        self._type_combo = QComboBox()
        for tt in TransfType:
            self._type_combo.addItem(tt.value, tt)
        if transf:
            idx = self._type_combo.findData(transf.transf_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
        form_info.addRow("Tipo:", self._type_combo)

        layout.addWidget(grp_info)

        # --- Vector vecxz ---
        grp_vec = QGroupBox("Vector de orientación (vecxz)")
        vec_layout = QVBoxLayout()
        grp_vec.setLayout(vec_layout)

        # Preset selector
        self._preset_combo = QComboBox()
        for preset_name in VECXZ_PRESETS:
            self._preset_combo.addItem(preset_name)
        self._preset_combo.setCurrentIndex(len(VECXZ_PRESETS) - 1)  # "Personalizado"
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        vec_layout.addWidget(self._preset_combo)

        # Spinboxes para X, Y, Z
        vec_form = QFormLayout()

        default_vec = transf.vecxz if transf else (0.0, 0.0, 1.0)

        self._vec_x = QDoubleSpinBox()
        self._vec_x.setDecimals(4)
        self._vec_x.setRange(-100.0, 100.0)
        self._vec_x.setValue(default_vec[0])
        vec_form.addRow("X:", self._vec_x)

        self._vec_y = QDoubleSpinBox()
        self._vec_y.setDecimals(4)
        self._vec_y.setRange(-100.0, 100.0)
        self._vec_y.setValue(default_vec[1])
        vec_form.addRow("Y:", self._vec_y)

        self._vec_z = QDoubleSpinBox()
        self._vec_z.setDecimals(4)
        self._vec_z.setRange(-100.0, 100.0)
        self._vec_z.setValue(default_vec[2])
        vec_form.addRow("Z:", self._vec_z)

        vec_layout.addLayout(vec_form)

        # Nota explicativa
        note = QLabel(
            "El vector vecxz define el plano local xz del elemento.\n"
            "Para columnas, normalmente (0, 0, 1) o (1, 0, 0).\n"
            "Para vigas horizontales, normalmente (0, 0, 1)."
        )
        note.setStyleSheet("color: #757575; font-size: 11px; padding: 4px;")
        vec_layout.addWidget(note)

        layout.addWidget(grp_vec)

        # --- Botones ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---------------------------------------------------------------

    def _on_preset_changed(self, text: str) -> None:
        """Aplica un preset de vector vecxz."""
        vec = VECXZ_PRESETS.get(text)
        if vec and text != "Personalizado":
            self._vec_x.setValue(vec[0])
            self._vec_y.setValue(vec[1])
            self._vec_z.setValue(vec[2])

    def get_transf(self) -> GeomTransf:
        """Retorna la transformación configurada."""
        tag = int(self._tag_edit.text())
        transf_type: TransfType = self._type_combo.currentData()
        vecxz = (self._vec_x.value(), self._vec_y.value(), self._vec_z.value())
        return GeomTransf(tag=tag, transf_type=transf_type, vecxz=vecxz)
```


##### 3C. Modificar `gui/main_window.py` — Habilitar Secciones y Transformaciones

- [x] Agregar imports. Después de `from gui.dialogs.material_dialog import MaterialDialog`, agregar:

```python
from gui.dialogs.section_dialog import SectionDialog
from gui.dialogs.transf_dialog import TransfDialog
```

- [x] En `_build_menubar`, reemplazar el bloque de Secciones.

Reemplazar:
```python
        act_sec = QAction("Secciones...", self)
        act_sec.setEnabled(False)
        m_define.addAction(act_sec)
```
Con:
```python
        act_sec = QAction("Secciones...", self)
        act_sec.setToolTip("Definir secciones transversales")
        act_sec.triggered.connect(self._on_define_section)
        m_define.addAction(act_sec)
```


- [x] En `_build_menubar`, reemplazar el bloque de Transformaciones.

Reemplazar:
```python
        act_transf = QAction("Transformaciones...", self)
        act_transf.setEnabled(False)
        m_define.addAction(act_transf)
```
Con:
```python
        act_transf = QAction("Transformaciones...", self)
        act_transf.setToolTip("Definir transformaciones geométricas")
        act_transf.triggered.connect(self._on_define_transf)
        m_define.addAction(act_transf)
```


- [x] Agregar slots nuevos en la sección Slots (después de `_on_tree_item_double_clicked`):

```python
    def _on_define_section(self) -> None:
        """Abre el diálogo para crear una nueva sección."""
        dlg = SectionDialog(
            self,
            next_tag=self._model.next_section_tag(),
        )
        if dlg.exec():
            sec = dlg.get_section()
            self._model.sections[sec.tag] = sec
            self._refresh_all()
            self._console.log_success(
                f"Sección creada: {sec.tag} — {sec.name} [{sec.sec_type.value}]"
            )

    def _on_define_transf(self) -> None:
        """Abre el diálogo para crear una nueva transformación."""
        dlg = TransfDialog(
            self,
            next_tag=self._model.next_transf_tag(),
        )
        if dlg.exec():
            transf = dlg.get_transf()
            self._model.geom_transfs[transf.tag] = transf
            self._refresh_all()
            self._console.log_success(
                f"Transformación creada: {transf.tag} — {transf.transf_type.value}"
            )
```


- [x] Expandir `_on_tree_item_double_clicked` para soportar secciones y transformaciones.

Reemplazar el método completo:
```python
    def _on_tree_item_double_clicked(self, item, column) -> None:
        """Abre diálogo de edición al hacer doble-clic en un ítem del tree."""
        category = item.data(0, 100)
        tag = item.data(0, 101)
        if tag is None:
            return

        if category == "materials":
            mat = self._model.materials.get(tag)
            if not mat:
                return
            dlg = MaterialDialog(self, material=mat)
            if dlg.exec():
                edited = dlg.get_material()
                self._model.materials[tag] = edited
                self._refresh_all()
                self._console.log(f"Material {tag} editado: {edited.name}")
```
Con:
```python
    def _on_tree_item_double_clicked(self, item, column) -> None:
        """Abre diálogo de edición al hacer doble-clic en un ítem del tree."""
        category = item.data(0, 100)
        tag = item.data(0, 101)
        if tag is None:
            return

        if category == "materials":
            mat = self._model.materials.get(tag)
            if not mat:
                return
            dlg = MaterialDialog(self, material=mat)
            if dlg.exec():
                edited = dlg.get_material()
                self._model.materials[tag] = edited
                self._refresh_all()
                self._console.log(f"Material {tag} editado: {edited.name}")

        elif category == "sections":
            sec = self._model.sections.get(tag)
            if not sec:
                return
            dlg = SectionDialog(self, section=sec)
            if dlg.exec():
                edited = dlg.get_section()
                self._model.sections[tag] = edited
                self._refresh_all()
                self._console.log(f"Sección {tag} editada: {edited.name}")

        elif category == "geom_transfs":
            transf = self._model.geom_transfs.get(tag)
            if not transf:
                return
            dlg = TransfDialog(self, transf=transf)
            if dlg.exec():
                edited = dlg.get_transf()
                self._model.geom_transfs[tag] = edited
                self._refresh_all()
                self._console.log(
                    f"Transformación {tag} editada: {edited.transf_type.value}"
                )
```

##### Step 3 Verification Checklist

- [ ] Sin errores de import: `python -c "from gui.dialogs.section_dialog import SectionDialog; from gui.dialogs.transf_dialog import TransfDialog; print('OK')"`
- [ ] Ejecutar GUI → Definir → Secciones... → se abre diálogo de sección
- [ ] Crear sección Elastic3D "Columna 40×40" con A=0.16, E=24821000, Iz=2.1333e-3, Iy=2.1333e-3, G=10342000, J=3.6053e-3 → aparece en el tree
- [ ] Cambiar tipo a Elastic2D → campos se reducen a A, E, Iz
- [ ] Cambiar tipo a Fiber → aparece nota de "versión futura"
- [ ] Doble-clic en sección existente → abre diálogo con valores precargados
- [ ] Definir → Transformaciones... → se abre diálogo de transformación
- [ ] Crear transformación PDelta con vecxz=(1, 0, 0) → aparece en el tree
- [ ] Seleccionar preset "Columnas (vertical Z)" → vecxz se actualiza a (0, 0, 1)
- [ ] Doble-clic en transformación existente → abre diálogo con valores precargados
- [ ] Guardar como .opss → Abrir → verificar que secciones y transformaciones nuevas persisten

#### Step 3 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: add section and geometric transform dialogs

- Create SectionDialog with dynamic params (Elastic2D, Elastic3D, Fiber)
- Create TransfDialog with type selection and vecxz presets
- Enable Definir > Secciones and Transformaciones menu actions
- Double-click editing for sections and transforms in tree"
```

---

## Sprint 1 Complete

Al finalizar Sprint 1, el estado de la GUI es:

| Feature | Estado |
|---------|--------|
| Archivo → Nuevo/Abrir/Guardar como | ✅ Funcional |
| Definir → Materiales | ✅ Funcional (crear + editar) |
| Definir → Secciones | ✅ Funcional (crear + editar) |
| Definir → Transformaciones | ✅ Funcional (crear + editar) |
| Definir → Patrones de carga | ❌ Pendiente (Sprint 3) |
| Dibujar → Nodo/Elemento | ❌ Pendiente (Sprint 2) |
| Serialización JSON .opss | ✅ Funcional |

**Archivos nuevos creados:** 4
- `gui/core/project_io.py`
- `gui/dialogs/material_dialog.py`
- `gui/dialogs/section_dialog.py`
- `gui/dialogs/transf_dialog.py`

**Archivos modificados:** 2
- `gui/core/model_data.py` (to_dict/from_dict en todas las clases)
- `gui/main_window.py` (menú, toolbar, slots)
