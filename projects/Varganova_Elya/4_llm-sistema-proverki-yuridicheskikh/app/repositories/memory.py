"""In-memory реализации репозиториев: для демо, тестов и dev-режима."""
from __future__ import annotations

import threading

from app.domain.entities import AnalysisReport, Contract, KnowledgeChunk
from app.repositories.base import (
    ContractRepository,
    KnowledgeRepository,
    ReportRepository,
)


class InMemoryContractRepository(ContractRepository):
    def __init__(self) -> None:
        self._items: dict[str, Contract] = {}
        self._lock = threading.Lock()

    def add(self, contract: Contract) -> None:
        with self._lock:
            self._items[contract.id] = contract

    def get(self, contract_id: str):
        with self._lock:
            return self._items.get(contract_id)

    def update(self, contract: Contract) -> None:
        with self._lock:
            self._items[contract.id] = contract

    def all(self) -> list[Contract]:
        with self._lock:
            return list(self._items.values())


class InMemoryReportRepository(ReportRepository):
    def __init__(self) -> None:
        self._items: dict[str, list[AnalysisReport]] = {}
        self._lock = threading.Lock()

    def save(self, report: AnalysisReport) -> None:
        with self._lock:
            self._items.setdefault(report.contract_id, []).insert(0, report)

    def latest_for(self, contract_id: str):
        with self._lock:
            reports = self._items.get(contract_id)
            return reports[0] if reports else None


class InMemoryKnowledgeRepository(KnowledgeRepository):
    def __init__(self) -> None:
        self._items: dict[str, KnowledgeChunk] = {}
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def add_all(self, chunks: list[KnowledgeChunk]) -> None:
        with self._lock:
            for chunk in chunks:
                self._items[chunk.id] = chunk

    def all(self) -> list[KnowledgeChunk]:
        with self._lock:
            return list(self._items.values())

    def count(self) -> int:
        with self._lock:
            return len(self._items)
