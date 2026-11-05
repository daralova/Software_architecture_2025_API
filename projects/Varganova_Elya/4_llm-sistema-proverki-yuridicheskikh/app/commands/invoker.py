"""Диспетчер команд (паттерн Command: invoker)."""
from __future__ import annotations

from typing import Any, Callable

from app.commands.base import Command
from app.core.logging import get_logger
from app.workers.events import Event

logger = get_logger(__name__)


class CommandInvoker:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._fallbacks: list[Callable[[Event], None]] = []

    def register(self, event_type: str, command: Command) -> None:
        self._commands[event_type] = command

    def register_fallback(self, handler: Callable[[Event], None]) -> None:
        self._fallbacks.append(handler)

    def handle(self, event: Event) -> dict[str, Any] | None:
        command = self._commands.get(event.type)
        if command is None:
            for fallback in self._fallbacks:
                fallback(event)
            logger.warning("Нет команды для события %r", event.type)
            return None
        logger.info("Событие %s -> команда %s", event.type, command.name)
        return command.execute(event.payload)
