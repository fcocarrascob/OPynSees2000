# Sprint 5: Edición Avanzada + Packaging

## Goal
Convertir el Properties Panel de solo lectura a editable con soporte Undo/Redo, y crear la configuración de proyecto (`pyproject.toml`, `requirements.txt`, `README.md`) para distribución e instalación.

## Prerequisites
Sprint 4 completado y commiteado. Branch `feat/gui-sap2000-workflow`.

---

### Step-by-Step Instructions

---

#### Step 11: Properties Panel Editable + Undo/Redo

- [x] Crear `gui/core/undo_manager.py`
- [x] Refactorizar `gui/panels/properties_panel.py` para campos editables
- [x] Modificar `gui/main_window.py` para Ctrl+Z / Ctrl+Y

##### 11A. Crear `gui/core/undo_manager.py`

- [x] Crear el archivo con el siguiente contenido completo:

```python
"""
UndoManager — Sistema de Undo/Redo basado en Command Pattern.

Cada operación que modifica el modelo crea un UndoCommand que
sabe cómo hacer y deshacer el cambio. Los comandos se apilan
para soportar múltiples niveles de undo/redo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, Signal


class UndoCommand(ABC):
    """Comando base para undo/redo."""

    @abstractmethod
    def redo(self) -> None:
        """Ejecuta (o re-ejecuta) el comando."""

    @abstractmethod
    def undo(self) -> None:
        """Deshace el comando."""

    @abstractmethod
    def description(self) -> str:
        """Descripción corta del comando (para UI)."""


class PropertyChangeCommand(UndoCommand):
    """Comando para cambiar una propiedad de un objeto del modelo."""

    def __init__(
        self,
        target: Any,
        field_name: str,
        old_value: Any,
        new_value: Any,
        desc: str = "",
    ) -> None:
        self._target = target
        self._field = field_name
        self._old = old_value
        self._new = new_value
        self._desc = desc or f"Cambiar {field_name}"

    def redo(self) -> None:
        setattr(self._target, self._field, self._new)

    def undo(self) -> None:
        setattr(self._target, self._field, self._old)

    def description(self) -> str:
        return self._desc


class DictChangeCommand(UndoCommand):
    """Comando para agregar/eliminar/reemplazar un ítem en un dict del modelo."""

    def __init__(
        self,
        target_dict: dict,
        key: int,
        old_value: Any,       # None si se está agregando
        new_value: Any,       # None si se está eliminando
        desc: str = "",
    ) -> None:
        self._dict = target_dict
        self._key = key
        self._old = deepcopy(old_value) if old_value is not None else None
        self._new = deepcopy(new_value) if new_value is not None else None
        self._desc = desc

    def redo(self) -> None:
        if self._new is None:
            # Eliminar
            self._dict.pop(self._key, None)
        else:
            self._dict[self._key] = deepcopy(self._new)

    def undo(self) -> None:
        if self._old is None:
            # Revertir agregar → eliminar
            self._dict.pop(self._key, None)
        else:
            self._dict[self._key] = deepcopy(self._old)

    def description(self) -> str:
        return self._desc


class UndoManager(QObject):
    """Gestor de pila de Undo/Redo."""

    state_changed = Signal()  # emitido cuando cambia la pila

    def __init__(self, max_stack: int = 100) -> None:
        super().__init__()
        self._undo_stack: list[UndoCommand] = []
        self._redo_stack: list[UndoCommand] = []
        self._max = max_stack

    def execute(self, command: UndoCommand) -> None:
        """Ejecuta un comando y lo apila."""
        command.redo()
        self._undo_stack.append(command)
        if len(self._undo_stack) > self._max:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self.state_changed.emit()

    def undo(self) -> Optional[str]:
        """Deshace el último comando. Retorna la descripción."""
        if not self._undo_stack:
            return None
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        self.state_changed.emit()
        return cmd.description()

    def redo(self) -> Optional[str]:
        """Rehace el último comando deshecho. Retorna la descripción."""
        if not self._redo_stack:
            return None
        cmd = self._redo_stack.pop()
        cmd.redo()
        self._undo_stack.append(cmd)
        self.state_changed.emit()
        return cmd.description()

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo_description(self) -> str:
        """Descripción del próximo undo."""
        if self._undo_stack:
            return self._undo_stack[-1].description()
        return ""

    def redo_description(self) -> str:
        """Descripción del próximo redo."""
        if self._redo_stack:
            return self._redo_stack[-1].description()
        return ""

    def clear(self) -> None:
        """Limpia ambas pilas."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.state_changed.emit()
```

##### 11B. Refactorizar `gui/panels/properties_panel.py` — Campos Editables

El Properties Panel actual es read-only. Se refactoriza para que los campos numéricos y de texto sean editables, y al presionar Enter se aplique el cambio mediante el UndoManager.

- [x] Reemplazar el contenido completo de `gui/panels/properties_panel.py`:

```python
"""
Panel de propiedades — Inspector editable de objetos del modelo.

Muestra las propiedades del ítem seleccionado en el Model Tree
como campos de formulario editables. Al presionar Enter en un campo,
se genera un UndoCommand y se aplica el cambio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from gui.core.model_data import StructuralModel
    from gui.core.undo_manager import UndoManager


# Campos read-only que no se deben editar
READ_ONLY_FIELDS = {"tag", "elem_type", "mat_type", "sec_type", "transf_type"}

# Mapeo de nombres de campo a etiquetas legibles (español)
HUMAN_LABELS = {
    "tag": "Tag",
    "x": "Coord. X [m]",
    "y": "Coord. Y [m]",
    "z": "Coord. Z [m]",
    "name": "Nombre",
    "mat_type": "Tipo de material",
    "sec_type": "Tipo de sección",
    "elem_type": "Tipo de elemento",
    "transf_type": "Tipo de transformación",
    "node_i": "Nodo I",
    "node_j": "Nodo J",
    "node_k": "Nodo K",
    "node_l": "Nodo L",
    "section_tag": "Sección (tag)",
    "transf_tag": "Transformación (tag)",
    "fixity": "Restricciones",
    "mass": "Masa nodal",
    "vecxz": "Vector vecxz",
    "fx": "Fx [kN]",
    "fy": "Fy [kN]",
    "fz": "Fz [kN]",
    "mx": "Mx [kN·m]",
    "my": "My [kN·m]",
    "mz": "Mz [kN·m]",
    "time_series_type": "TimeSeries",
    "node_tag": "Nodo (tag)",
    "params": "Parámetros",
    "loads": "Cargas",
    "ndm": "NDM",
    "ndf": "NDF",
}


class PropertiesPanel(QScrollArea):
    """Panel lateral derecho con propiedades editables."""

    # Señal emitida cuando se cambia una propiedad: (category, tag)
    property_changed = Signal(str, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(250)
        self.setWidgetResizable(True)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self._container)

        self._current_item: Any = None
        self._current_category: str = ""
        self._current_tag: int = 0
        self._undo_manager: Optional["UndoManager"] = None
        self._field_widgets: dict[str, QWidget] = {}

        # Placeholder
        self._placeholder = QLabel("Seleccione un ítem\nen el Model Tree")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #9E9E9E; padding: 30px;")
        self._layout.addWidget(self._placeholder)

    def set_undo_manager(self, mgr: "UndoManager") -> None:
        """Conecta el UndoManager para operaciones de edición."""
        self._undo_manager = mgr

    def show_item(
        self,
        model: "StructuralModel",
        category: str,
        tag: int,
    ) -> None:
        """Muestra las propiedades del ítem seleccionado."""
        item = self._resolve_item(model, category, tag)
        if item is None:
            return

        self._current_item = item
        self._current_category = category
        self._current_tag = tag
        self._field_widgets.clear()

        # Limpiar layout
        self._clear_layout()

        # Título
        title = QLabel(f"{category.capitalize()} — Tag {tag}")
        title.setStyleSheet(
            "font-weight: bold; font-size: 13px; padding: 6px 0;"
        )
        self._layout.addWidget(title)

        # Campos
        grp = QGroupBox("Propiedades")
        form = QFormLayout()
        grp.setLayout(form)

        for field_name, value in vars(item).items():
            if field_name.startswith("_"):
                continue

            label = HUMAN_LABELS.get(field_name, field_name)
            is_readonly = field_name in READ_ONLY_FIELDS

            widget = self._create_field_widget(
                item, field_name, value, is_readonly
            )
            self._field_widgets[field_name] = widget
            form.addRow(label + ":", widget)

        # Mostrar params como sub-campos si es dict
        if hasattr(item, "params") and isinstance(item.params, dict):
            grp_params = QGroupBox("Parámetros detallados")
            params_form = QFormLayout()
            grp_params.setLayout(params_form)
            for key, val in item.params.items():
                w = self._create_param_widget(item, key, val)
                params_form.addRow(f"{key}:", w)
            self._layout.addWidget(grp_params)

        self._layout.addWidget(grp)
        self._layout.addStretch()

    def _resolve_item(self, model, category, tag):
        """Busca el objeto dentro del modelo."""
        mapping = {
            "nodes": model.nodes,
            "materials": model.materials,
            "sections": model.sections,
            "geom_transfs": model.geom_transfs,
            "elements": model.elements,
            "load_patterns": model.load_patterns,
        }
        container = mapping.get(category)
        if container is None:
            return None
        return container.get(tag)

    def _create_field_widget(
        self, item: Any, field_name: str, value: Any, is_readonly: bool
    ) -> QWidget:
        """Crea el widget adecuado para un campo."""
        if is_readonly or isinstance(value, (tuple, list, dict)):
            # Solo lectura
            lbl = QLineEdit(self._format_value(value))
            lbl.setReadOnly(True)
            lbl.setStyleSheet("background: #F5F5F5; color: #616161;")
            return lbl

        if isinstance(value, float):
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e15, 1e15)
            spin.setValue(value)
            spin.editingFinished.connect(
                lambda fn=field_name, s=spin: self._on_field_edited(
                    item, fn, s.value()
                )
            )
            return spin

        if isinstance(value, int):
            spin = QDoubleSpinBox()
            spin.setDecimals(0)
            spin.setRange(-999_999, 999_999)
            spin.setValue(value)
            spin.editingFinished.connect(
                lambda fn=field_name, s=spin: self._on_field_edited(
                    item, fn, int(s.value())
                )
            )
            return spin

        if isinstance(value, str):
            edit = QLineEdit(value)
            edit.editingFinished.connect(
                lambda fn=field_name, e=edit: self._on_field_edited(
                    item, fn, e.text()
                )
            )
            return edit

        # Fallback read-only
        lbl = QLineEdit(self._format_value(value))
        lbl.setReadOnly(True)
        lbl.setStyleSheet("background: #F5F5F5; color: #616161;")
        return lbl

    def _create_param_widget(
        self, item: Any, key: str, value: Any
    ) -> QWidget:
        """Crea un widget editable para un parámetro del dict params."""
        if isinstance(value, (int, float)):
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1e15, 1e15)
            spin.setValue(float(value))
            spin.editingFinished.connect(
                lambda k=key, s=spin: self._on_param_edited(
                    item, k, s.value()
                )
            )
            return spin

        edit = QLineEdit(str(value))
        edit.setReadOnly(True)
        return edit

    def _on_field_edited(self, item: Any, field_name: str, new_value: Any) -> None:
        """Llamado cuando un campo es editado."""
        old_value = getattr(item, field_name, None)
        if old_value == new_value:
            return

        if self._undo_manager:
            from gui.core.undo_manager import PropertyChangeCommand

            desc = f"Editar {field_name} de tag {self._current_tag}"
            cmd = PropertyChangeCommand(item, field_name, old_value, new_value, desc)
            self._undo_manager.execute(cmd)
        else:
            setattr(item, field_name, new_value)

        self.property_changed.emit(self._current_category, self._current_tag)

    def _on_param_edited(self, item: Any, key: str, new_value: float) -> None:
        """Llamado cuando un parámetro del dict params es editado."""
        old_value = item.params.get(key)
        if old_value == new_value:
            return

        if self._undo_manager:
            from gui.core.undo_manager import PropertyChangeCommand

            # Crear un wrapper para editar el dict
            class ParamTarget:
                def __init__(self, params, k):
                    self._params = params
                    self._key = k
                @property
                def value(self):
                    return self._params[self._key]
                @value.setter
                def value(self, v):
                    self._params[self._key] = v

            target = ParamTarget(item.params, key)
            desc = f"Editar param {key} de tag {self._current_tag}"
            cmd = PropertyChangeCommand(target, "value", old_value, new_value, desc)
            self._undo_manager.execute(cmd)
        else:
            item.params[key] = new_value

        self.property_changed.emit(self._current_category, self._current_tag)

    def _clear_layout(self) -> None:
        """Elimina todos los widgets del layout."""
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    @staticmethod
    def _format_value(value: Any) -> str:
        """Formatea un valor para display en campo read-only."""
        if isinstance(value, float):
            if abs(value) > 1e6 or (0 < abs(value) < 1e-3):
                return f"{value:.4e}"
            return f"{value:.4f}"
        if isinstance(value, tuple):
            return "(" + ", ".join(str(v) for v in value) + ")"
        if isinstance(value, list):
            return f"[{len(value)} ítems]"
        if isinstance(value, dict):
            return f"{{{len(value)} params}}"
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)
```

##### 11C. Modificar `gui/main_window.py` — Undo/Redo

- [x] Agregar import:

```python
from gui.core.undo_manager import UndoManager
```

- [x] En `__init__`, crear el UndoManager y conectarlo. Después de crear los widgets y antes de `_build_menubar()`:

```python
        self._undo_mgr = UndoManager(max_stack=100)
        self._properties.set_undo_manager(self._undo_mgr)
```

- [x] Conectar `property_changed` del properties panel. En `__init__`, después de las conexiones existentes:

```python
        self._properties.property_changed.connect(self._on_property_changed)
```

- [x] Agregar un menú Editar. En `_build_menubar`, agregar ANTES del menú Definir:

```python
        # --- Editar ---
        m_edit = mb.addMenu("&Editar")

        self._act_undo = QAction("Deshacer", self)
        self._act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._act_undo.setEnabled(False)
        self._act_undo.triggered.connect(self._on_undo)
        m_edit.addAction(self._act_undo)

        self._act_redo = QAction("Rehacer", self)
        self._act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._act_redo.setEnabled(False)
        self._act_redo.triggered.connect(self._on_redo)
        m_edit.addAction(self._act_redo)

        m_edit.addSeparator()

        act_delete = QAction("Eliminar selección", self)
        act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        act_delete.setEnabled(False)
        m_edit.addAction(act_delete)
        self._act_delete = act_delete
```

- [x] Conectar `state_changed` del UndoManager. En `__init__`:

```python
        self._undo_mgr.state_changed.connect(self._update_undo_actions)
```

- [x] Agregar slots:

```python
    def _on_undo(self) -> None:
        desc = self._undo_mgr.undo()
        if desc:
            self._refresh_all()
            self._console.log(f"↩ Deshacer: {desc}")

    def _on_redo(self) -> None:
        desc = self._undo_mgr.redo()
        if desc:
            self._refresh_all()
            self._console.log(f"↪ Rehacer: {desc}")

    def _update_undo_actions(self) -> None:
        self._act_undo.setEnabled(self._undo_mgr.can_undo())
        self._act_redo.setEnabled(self._undo_mgr.can_redo())
        if self._undo_mgr.can_undo():
            self._act_undo.setToolTip(
                f"Deshacer: {self._undo_mgr.undo_description()}"
            )
        if self._undo_mgr.can_redo():
            self._act_redo.setToolTip(
                f"Rehacer: {self._undo_mgr.redo_description()}"
            )

    def _on_property_changed(self, category: str, tag: int) -> None:
        """Llamado cuando el properties panel edita una propiedad."""
        self._refresh_all()
```

- [x] Modificar `_on_new_model` para limpiar undo:

Agregar al final de `_on_new_model`:
```python
        self._undo_mgr.clear()
```

##### Step 11 Verification Checklist

- [ ] Ejecutar GUI → Cargar demo → Seleccionar nodo en tree → Properties panel muestra campos editables
- [ ] Cambiar coordenada X del nodo → presionar Tab/Enter → viewport actualizado en tiempo real
- [ ] Ctrl+Z → coordenada restaurada → viewport vuelve al estado anterior
- [ ] Ctrl+Y → coordenada re-aplicada
- [ ] Editar nombre de material en properties → Enter → tree actualizado
- [ ] Editar parámetro E de sección → Enter → cambio aplicado
- [ ] 5 ediciones consecutivas → Ctrl+Z 5 veces → todos revertidos correctamente
- [ ] Nuevo modelo → Ctrl+Z no hace nada (pila limpia)
- [ ] Menú Editar muestra tooltips con descripción del próximo undo/redo

#### Step 11 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "feat: editable properties panel with undo/redo

- Refactor PropertiesPanel to editable fields (float, int, str)
- Create UndoManager with Command Pattern (100-level stack)
- PropertyChangeCommand and DictChangeCommand
- Add Editar menu with Ctrl+Z / Ctrl+Y shortcuts
- Real-time viewport update on property change
- Param-level editing for material/section parameters"
```

---

#### Step 12: Configuración de Proyecto y Packaging

- [x] Crear `pyproject.toml`
- [x] Crear `requirements.txt`
- [x] Actualizar `.gitignore` si necesario
- [x] Actualizar `README.md`

##### 12A. Crear `pyproject.toml`

- [x] Crear el archivo en la raíz del workspace:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "opynsees2000"
version = "0.2.0"
description = "GUI tipo SAP2000 para modelado estructural con OpenSeesPy"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
    {name = "OPynSees2000 Contributors"},
]
keywords = ["opensees", "structural-engineering", "gui", "fem", "earthquake"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Education",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering",
]
dependencies = [
    "PySide6>=6.6",
    "pyvista>=0.43",
    "pyvistaqt>=0.11",
    "numpy>=1.24",
]

[project.optional-dependencies]
analysis = [
    "openseespy>=3.5",
]
plotting = [
    "matplotlib>=3.7",
]
dev = [
    "pytest>=7.0",
    "pytest-qt>=4.0",
    "ruff>=0.1",
]

[project.scripts]
opynsees2000 = "gui.main:main"

[project.gui-scripts]
opynsees2000-gui = "gui.main:main"

[project.urls]
Homepage = "https://github.com/your-user/OPynSees2000"
Documentation = "https://github.com/your-user/OPynSees2000/tree/main/docs"
Repository = "https://github.com/your-user/OPynSees2000"

[tool.setuptools.packages.find]
include = ["gui*"]

[tool.ruff]
line-length = 95
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
qt_api = "pyside6"
```

##### 12B. Crear `requirements.txt`

- [x] Generar desde el venv actual ejecutando en terminal:

```bash
pip freeze > requirements.txt
```

Alternativamente, crear manualmente con las dependencias mínimas:

```
PySide6>=6.6
pyvista>=0.43
pyvistaqt>=0.11
numpy>=1.24
```

##### 12C. Actualizar `.gitignore`

- [x] Verificar que `.gitignore` incluye al menos:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
*.egg

# Virtual environment
.venv/
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project
*.opss
```

##### 12D. Actualizar `README.md`

- [x] Reemplazar o actualizar el README.md de la raíz del workspace:

```markdown
# OPynSees2000

**GUI tipo SAP2000 para modelado estructural con OpenSeesPy.**

Interfaz gráfica interactiva para crear modelos de análisis estructural,
generar scripts OpenSeesPy, y ejecutar análisis estático y modal — todo
desde una interfaz visual al estilo SAP2000.

## Características

- **Modelado visual** — nodos, elementos (frame, truss, shell), restricciones
- **Definición de propiedades** — materiales, secciones, transformaciones
- **Cargas** — patrones de carga con cargas nodales
- **Viewport 3D** — PyVista/VTK con etiquetas, selección interactiva, flechas de carga
- **Generación de scripts** — exporta código OpenSeesPy listo para ejecutar
- **Análisis** — estático lineal y modal con visualización de deformada
- **Persistencia** — guardar/abrir proyectos en formato JSON (.opss)
- **Undo/Redo** — edición de propiedades con Ctrl+Z / Ctrl+Y

## Requisitos

- Python ≥ 3.10
- PySide6 ≥ 6.6
- PyVista ≥ 0.43
- NumPy ≥ 1.24
- OpenSeesPy ≥ 3.5 (opcional, para ejecución de análisis)

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/your-user/OPynSees2000.git
cd OPynSees2000

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS

# Instalar dependencias
pip install -e .

# Con soporte de análisis
pip install -e ".[analysis]"
```

## Ejecución

```bash
# Desde la raíz del proyecto
python -m gui

# O usando el entry point (después de pip install -e .)
opynsees2000
```

## Estructura del proyecto

```
gui/
├── main.py                 # Entry point
├── main_window.py          # Ventana principal
├── core/
│   ├── model_data.py       # Dataclasses del modelo
│   ├── project_io.py       # Serialización JSON
│   ├── script_generator.py # Generador OpenSeesPy
│   ├── analysis_runner.py  # Ejecución de análisis
│   └── undo_manager.py     # Sistema Undo/Redo
├── dialogs/                # Diálogos modales
├── panels/                 # Paneles laterales
├── viewport/               # Viewport 3D PyVista
└── theme/                  # QSS theme
docs/                       # Documentación de fundamentos
ejemplos/                   # Scripts de ejemplo OpenSeesPy
```

## Flujo de trabajo

1. **Definir** — materiales, secciones, transformaciones, patrones de carga
2. **Dibujar** — nodos (coordenadas), elementos (conectividad)
3. **Asignar** — restricciones, cargas nodales
4. **Analizar** — estático lineal o modal
5. **Resultados** — deformada, desplazamientos, períodos

## Licencia

MIT
```

##### 12E. Crear `gui/main.py` actualizado (entry point)

- [x] Verificar que `gui/main.py` exporta una función `main()` para el entry point de `pyproject.toml`. Si no la tiene, actualizar:

Agregar al final de `gui/main.py` (si no existe ya):

```python
def main():
    """Entry point para pyproject.toml [project.scripts]."""
    import sys
    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow

    app = QApplication(sys.argv)

    # Cargar QSS
    qss_path = Path(__file__).parent / "theme" / "light.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

Y asegurarse de que el bloque `if __name__ == "__main__":` llame a `main()`.

##### Step 12 Verification Checklist

- [ ] `pip install -e .` desde la raíz → instala sin errores
- [ ] `python -m gui` → GUI se abre normalmente
- [ ] `opynsees2000` (entry point) → GUI se abre
- [ ] `pip install -e ".[analysis]"` → instala openseespy
- [ ] Verificar que `.gitignore` excluye `__pycache__/`, `.venv/`, `*.opss`
- [ ] README.md legible en GitHub/VS Code preview

#### Step 12 STOP & COMMIT
**STOP & COMMIT:** Agent must stop here and wait for the user to test, stage, and commit the change.

Commit sugerido:
```bash
git add -A
git commit -m "chore: add pyproject.toml, requirements.txt, update README

- Create pyproject.toml with PEP 621 metadata
- Define optional deps: analysis, plotting, dev
- Entry point: opynsees2000 CLI and GUI scripts
- Update README with full installation and usage guide
- Update .gitignore for Python project patterns"
```

---

## Sprint 5 Complete

Al finalizar Sprint 5, OPynSees2000 es un proyecto completo:

| Feature | Estado |
|---------|--------|
| Properties Panel editable | ✅ Float, int, str + params |
| Undo/Redo (Ctrl+Z / Ctrl+Y) | ✅ 100 niveles, Command Pattern |
| pyproject.toml | ✅ PEP 621, entry points |
| requirements.txt | ✅ Dependencias congeladas |
| README.md actualizado | ✅ Instalación, uso, estructura |
| `pip install -e .` | ✅ Funcional |

**Archivos nuevos creados:** 3
- `gui/core/undo_manager.py`
- `pyproject.toml`
- `requirements.txt`

**Archivos modificados:** 3
- `gui/panels/properties_panel.py` (refactor completo a editable)
- `gui/main_window.py` (menú Editar + Undo/Redo + property_changed)
- `README.md` (documentación completa)

---

## Proyecto Completo 🏁

Todos los 12 steps y 5 sprints están documentados. Al completar los 5 sprints, OPynSees2000 tendrá:

```
✅ Persistencia JSON (.opss)
✅ Diálogos de definición (materiales, secciones, transformaciones)
✅ Dibujo de geometría (nodos, elementos frame/truss/shell)
✅ Asignación de restricciones y cargas
✅ Viewport 3D con etiquetas, picking, flechas de carga
✅ Generación de scripts OpenSeesPy
✅ Análisis estático y modal con resultados
✅ Properties Panel editable con Undo/Redo
✅ Packaging con pyproject.toml
```
