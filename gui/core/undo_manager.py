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
