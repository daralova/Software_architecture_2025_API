"""Базовый контракт команды (паттерн Command)."""
from __future__ import annotations

import abc
from typing import Any


class Command(abc.ABC):
    name: str = "command"

    @abc.abstractmethod
    def execute(self, payload: dict[str, Any]) -> dict[str, Any]: ...
