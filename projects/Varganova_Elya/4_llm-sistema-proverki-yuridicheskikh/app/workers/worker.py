"""Асинхронный воркер: потребляет события и исполняет команды."""
from __future__ import annotations

import signal
import sys

from app.commands.analyze_contract import AnalyzeContractCommand
from app.commands.invoker import CommandInvoker
from app.commands.reindex_knowledge import ReindexKnowledgeCommand
from app.core.config import get_settings
from app.core.logging import get_logger
from app.facade.container import build_facade
from app.workers.events import make_event_bus

logger = get_logger("worker")


def build_invoker(facade) -> CommandInvoker:
    invoker = CommandInvoker()
    invoker.register("contract.uploaded", AnalyzeContractCommand(facade))
    invoker.register("knowledge.reindex_requested", ReindexKnowledgeCommand(facade))
    return invoker


def run_forever() -> None:
    settings = get_settings()
    facade = build_facade(settings)
    facade.ensure_knowledge()
    invoker = build_invoker(facade)
    bus = make_event_bus(settings)

    def _stop(signum, frame):  # noqa: ANN001
        logger.info("Остановка воркера (сигнал %s)", signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    logger.info("Воркер слушает шину (%s)", settings.bus_backend)
    for event in bus.stream(timeout=1.0):
        try:
            invoker.handle(event)
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка обработки события %s", event.id)


if __name__ == "__main__":
    run_forever()
