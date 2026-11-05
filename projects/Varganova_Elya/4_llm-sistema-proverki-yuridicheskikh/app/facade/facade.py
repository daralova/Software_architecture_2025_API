"""Фасад системы проверки договоров (паттерн Facade).

Единая точка входа: и API-шлюз, и воркер работают только через фасад,
не зная деталей адаптеров, пайплайна и ретривера.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.entities import (
    AnalysisReport,
    Contract,
    ContractStatus,
    KnowledgeChunk,
)
from app.pipeline.pipeline import DocumentProcessingPipeline
from app.repositories.base import (
    ContractRepository,
    KnowledgeRepository,
    ReportRepository,
)
from app.workers.events import Event

logger = get_logger(__name__)


class ContractReviewFacade:
    def __init__(
        self,
        contract_repo: ContractRepository,
        report_repo: ReportRepository,
        knowledge_repo: KnowledgeRepository,
        storage,
        pipeline: DocumentProcessingPipeline,
        seed_chunks: list[KnowledgeChunk],
        settings: Settings,
    ) -> None:
        self._contract_repo = contract_repo
        self._report_repo = report_repo
        self._knowledge_repo = knowledge_repo
        self._storage = storage
        self._pipeline = pipeline
        self._seed_chunks = seed_chunks
        self._settings = settings
        self._indexed = False

    # --- загрузка договора (вызывает API) ---
    def upload(self, filename: str, content_type: str, data: bytes) -> dict[str, Any]:
        contract_id = f"contract_{uuid.uuid4().hex[:12]}"
        key = f"contracts/{contract_id}/{filename}"
        self._storage.put(key, data)
        contract = Contract(
            id=contract_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            storage_key=key,
            status=ContractStatus.UPLOADED,
        )
        self._contract_repo.add(contract)
        logger.info("Договор %s загружен (%s байт)", contract_id, len(data))
        event = Event(
            type="contract.uploaded",
            payload={"contract_id": contract_id, "object_key": key},
        )
        return {
            "contract_id": contract_id,
            "status": contract.status.value,
            "event": event.to_dict(),
        }

    # --- обработка (вызывает воркер) ---
    def process(self, contract_id: str) -> AnalysisReport:
        contract = self._contract_repo.get(contract_id)
        if contract is None:
            raise KeyError(f"Договор {contract_id} не найден")
        self.ensure_knowledge()
        file_bytes = None
        if contract.storage_key:
            file_bytes = self._storage.get(contract.storage_key)
        return self._pipeline.run_with_error_handling(
            contract,
            self._contract_repo,
            file_bytes=file_bytes,
            text=contract.text,
        )

    # --- чтение результатов (вызывает API) ---
    def get_contract(self, contract_id: str) -> Contract | None:
        return self._contract_repo.get(contract_id)

    def get_report(self, contract_id: str) -> AnalysisReport | None:
        return self._report_repo.latest_for(contract_id)

    # --- база знаний ---
    def ensure_knowledge(self) -> int:
        if not self._indexed:
            return self.reindex()
        return 0

    def reindex(self) -> int:
        if self._knowledge_repo.count() == 0:
            self._knowledge_repo.add_all(self._seed_chunks)
        retriever = self._pipeline_retriever()
        count = retriever.index(self._knowledge_repo.all())
        self._indexed = True
        logger.info("База знаний проиндексирована: %s чанков", count)
        return count

    def _pipeline_retriever(self):
        for stage in getattr(self._pipeline, "stages", []):
            retriever = getattr(stage, "_retriever", None)
            if retriever is not None:
                return retriever
        raise RuntimeError("Ретривер не найден в пайплайне")
