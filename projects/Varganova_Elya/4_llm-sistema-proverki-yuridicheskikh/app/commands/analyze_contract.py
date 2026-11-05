"""Команда анализа договора: связывает Kafka-событие с фасадом."""
from __future__ import annotations

from typing import Any

from app.commands.base import Command


class AnalyzeContractCommand(Command):
    name = "analyze_contract"

    def __init__(self, facade) -> None:
        self._facade = facade

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        contract_id = payload["contract_id"]
        report = self._facade.process(contract_id)
        return report.to_dict()
