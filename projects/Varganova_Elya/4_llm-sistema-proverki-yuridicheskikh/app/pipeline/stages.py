"""Стадии документа-обработки (паттерн Pipeline).

Каждая стадия — самостоятельный шаг с единственной ответственностью.
Порядок: Parse -> Split -> Embed -> RiskScan -> RagEnrichment -> Summarize -> Persist.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from app.adapters.embeddings import BaseEmbedder
from app.adapters.llm import BaseLLM
from app.adapters.parsers import ParserRegistry
from app.adapters.storage import BaseObjectStorage
from app.domain.entities import (
    AnalysisReport,
    Clause,
    Contract,
    ContractStatus,
    RiskFinding,
)
from app.rag.retriever import HybridRetriever
from app.strategies.risk_rules import RiskScanner
from app.strategies.splitters import BaseClauseSplitter


@dataclass
class PipelineContext:
    contract: Contract
    file_bytes: bytes | None = None
    text: str = ""
    clauses: list[Clause] = field(default_factory=list)
    findings: list[RiskFinding] = field(default_factory=list)
    report: AnalysisReport | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class Stage(abc.ABC):
    name: str = "stage"

    @abc.abstractmethod
    def run(self, ctx: PipelineContext) -> None: ...


class ParseStage(Stage):
    name = "parse"

    def __init__(self, registry: ParserRegistry, storage: BaseObjectStorage) -> None:
        self._registry = registry
        self._storage = storage

    def run(self, ctx: PipelineContext) -> None:
        if not ctx.text:
            data = ctx.file_bytes
            if data is None and ctx.contract.storage_key:
                data = self._storage.get(ctx.contract.storage_key)
            if data is None:
                raise ValueError(f"Нет исходных данных для договора {ctx.contract.id}")
            ctx.text = self._registry.parse(ctx.contract.filename, data)
        ctx.meta["text_length"] = len(ctx.text)


class SplitStage(Stage):
    name = "split"

    def __init__(self, splitter: BaseClauseSplitter) -> None:
        self._splitter = splitter

    def run(self, ctx: PipelineContext) -> None:
        ctx.clauses = self._splitter.split(ctx.text)
        ctx.meta["clauses_count"] = len(ctx.clauses)


class EmbedStage(Stage):
    name = "embed"

    def __init__(self, embedder: BaseEmbedder) -> None:
        self._embedder = embedder

    def run(self, ctx: PipelineContext) -> None:
        texts = [f"{clause.title}. {clause.text}" for clause in ctx.clauses]
        if texts:
            ctx.meta["clause_vectors"] = self._embedder.embed_batch(texts)


class RiskScanStage(Stage):
    name = "risk_scan"

    def __init__(self, scanner: RiskScanner) -> None:
        self._scanner = scanner

    def run(self, ctx: PipelineContext) -> None:
        ctx.findings = self._scanner.scan_all(ctx.clauses)
        ctx.meta["findings_count"] = len(ctx.findings)


class RagEnrichmentStage(Stage):
    name = "rag_enrichment"

    def __init__(self, retriever: HybridRetriever, top_k: int = 3) -> None:
        self._retriever = retriever
        self._top_k = top_k

    def run(self, ctx: PipelineContext) -> None:
        for finding in ctx.findings:
            clause = next(
                (c for c in ctx.clauses if c.index == finding.clause_index), None
            )
            if clause is None:
                continue
            query = f"{clause.title}. {finding.message} {finding.recommendation}"
            finding.citations = self._retriever.search(query, top_k=self._top_k)


class SummarizeStage(Stage):
    name = "summarize"

    def __init__(self, llm: BaseLLM) -> None:
        self._llm = llm

    def run(self, ctx: PipelineContext) -> None:
        draft = self._draft(ctx)
        ctx.meta["summary"] = self._llm.summarize(f"DRAFT:\n{draft}\n")

    @staticmethod
    def _draft(ctx: PipelineContext) -> str:
        high = sum(1 for f in ctx.findings if f.level.value == "high")
        medium = sum(1 for f in ctx.findings if f.level.value == "medium")
        low = sum(1 for f in ctx.findings if f.level.value == "low")
        lines = [
            f"Договор «{ctx.contract.filename}»: {len(ctx.clauses)} пунктов.",
            f"Выявлено рисков: высоких — {high}, средних — {medium}, низких — {low}.",
        ]
        for finding in ctx.findings:
            lines.append(f"- [{finding.level.value}] {finding.message}")
        return "\n".join(lines)


class PersistStage(Stage):
    name = "persist"

    def __init__(self, contract_repo, report_repo) -> None:
        self._contract_repo = contract_repo
        self._report_repo = report_repo

    def run(self, ctx: PipelineContext) -> None:
        report = AnalysisReport(
            contract_id=ctx.contract.id,
            status=ContractStatus.COMPLETED,
            summary=ctx.meta.get("summary", ""),
            clauses=list(ctx.clauses),
            findings=list(ctx.findings),
        )
        ctx.report = report
        ctx.contract.status = ContractStatus.COMPLETED
        ctx.contract.text = ctx.text or ctx.contract.text
        self._contract_repo.update(ctx.contract)
        self._report_repo.save(report)
