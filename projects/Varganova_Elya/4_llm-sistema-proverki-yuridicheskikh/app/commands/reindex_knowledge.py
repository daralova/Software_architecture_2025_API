"""Команда переиндексации базы знаний."""
from __future__ import annotations

from typing import Any

from app.commands.base import Command


class ReindexKnowledgeCommand(Command):
    name = "reindex_knowledge"

    def __init__(self, facade) -> None:
        self._facade = facade

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        count = self._facade.reindex()
        return {"indexed_chunks": count}
