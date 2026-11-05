"""Конвейер обработки договора (паттерн Pipeline)."""
from __future__ import annotations

import logging

from app.core.logging import get_logger
from app.domain.entities import ContractStatus
from app.pipeline.stages import PipelineContext, Stage

logger = get_logger("pipeline")


class DocumentProcessingPipeline:
    def __init__(self, stages: list[Stage]) -> None:
        self.stages = stages

    def run(self, ctx: PipelineContext):
        for stage in self.stages:
            logger.info("Стадия %s: старт", stage.name)
            stage.run(ctx)
            logger.info("Стадия %s: готово", stage.name)
        return ctx.report

    def run_with_error_handling(self, contract, contract_repo, **kwargs):
        """Запуск с переводом статуса договора в FAILED при ошибке стадии."""
        ctx = PipelineContext(contract=contract, **kwargs)
        try:
            contract.status = ContractStatus.PROCESSING
            contract_repo.update(contract)
            return self.run(ctx)
        except Exception as exc:  # noqa: BLE001 — воркер должен пережить сбой
            logger.exception("Обработка договора %s упала", contract.id)
            contract.status = ContractStatus.FAILED
            contract.error = str(exc)
            contract_repo.update(contract)
            raise
