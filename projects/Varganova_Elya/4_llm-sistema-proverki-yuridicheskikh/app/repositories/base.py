"""Абстрактные контракты хранилищ (паттерн Repository)."""
from __future__ import annotations

import abc
from typing import Optional

from app.domain.entities import AnalysisReport, Contract, KnowledgeChunk


class ContractRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, contract: Contract) -> None: ...

    @abc.abstractmethod
    def get(self, contract_id: str) -> Optional[Contract]: ...

    @abc.abstractmethod
    def update(self, contract: Contract) -> None: ...

    @abc.abstractmethod
    def all(self) -> list[Contract]: ...


class ReportRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, report: AnalysisReport) -> None: ...

    @abc.abstractmethod
    def latest_for(self, contract_id: str) -> Optional[AnalysisReport]: ...


class KnowledgeRepository(abc.ABC):
    @abc.abstractmethod
    def clear(self) -> None: ...

    @abc.abstractmethod
    def add_all(self, chunks: list[KnowledgeChunk]) -> None: ...

    @abc.abstractmethod
    def all(self) -> list[KnowledgeChunk]: ...

    @abc.abstractmethod
    def count(self) -> int: ...
