"""Доменные сущности предметной области.

Слой не зависит от фреймворков и инфраструктуры: только dataclasses и enum.
"""
from __future__ import annotations

import datetime as dt
import enum
import uuid
from dataclasses import dataclass, field
from typing import Any


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ContractStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def _now() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Clause:
    """Пункт договора, выделенный сплиттером."""

    index: int
    title: str
    text: str

    @property
    def preview(self) -> str:
        snippet = " ".join(self.text.split())
        return snippet[:160] + ("…" if len(snippet) > 160 else "")


@dataclass
class RiskFinding:
    """Обнаруженный риск в конкретном пункте."""

    clause_index: int
    rule_id: str
    level: RiskLevel
    message: str
    snippet: str = ""
    recommendation: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clause_index": self.clause_index,
            "rule_id": self.rule_id,
            "level": self.level.value,
            "message": self.message,
            "snippet": self.snippet,
            "recommendation": self.recommendation,
            "citations": self.citations,
        }


@dataclass
class Contract:
    id: str
    filename: str
    content_type: str = ""
    size_bytes: int = 0
    storage_key: str = ""
    text: str = ""
    status: ContractStatus = ContractStatus.UPLOADED
    error: str | None = None
    created_at: dt.datetime = field(default_factory=_now)
    updated_at: dt.datetime = field(default_factory=_now)


@dataclass
class KnowledgeChunk:
    """Атомарная единица базы юридических знаний (для RAG)."""

    id: str
    title: str
    source: str
    content: str


@dataclass
class AnalysisReport:
    contract_id: str
    status: ContractStatus = ContractStatus.COMPLETED
    summary: str = ""
    clauses: list[Clause] = field(default_factory=list)
    findings: list[RiskFinding] = field(default_factory=list)
    created_at: dt.datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "status": self.status.value,
            "summary": self.summary,
            "clauses": [
                {"index": c.index, "title": c.title, "text": c.text}
                for c in self.clauses
            ],
            "findings": [f.to_dict() for f in self.findings],
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisReport":
        clauses = [Clause(**c) for c in data.get("clauses", [])]
        findings = [
            RiskFinding(
                clause_index=f["clause_index"],
                rule_id=f["rule_id"],
                level=RiskLevel(f["level"]),
                message=f["message"],
                snippet=f.get("snippet", ""),
                recommendation=f.get("recommendation", ""),
                citations=f.get("citations", []),
            )
            for f in data.get("findings", [])
        ]
        return cls(
            contract_id=data["contract_id"],
            status=ContractStatus(data.get("status", "completed")),
            summary=data.get("summary", ""),
            clauses=clauses,
            findings=findings,
        )
