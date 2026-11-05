"""Стратегии разбора договора на пункты (паттерн Strategy).

NumberedClauseSplitter — основной: находит заголовки вида «1. Название».
Суб-нумерация («1.1.», «1.2.1») НЕ начинает новый пункт, а продолжает текущий —
иначе вложенные пункты «отваливаются» от родительского заголовка.
ParagraphClauseSplitter — fallback для договоров без сквозной нумерации.
ClauseSplitterSelector выбирает стратегию по качеству разбора.
"""
from __future__ import annotations

import abc
import re

from app.domain.entities import Clause

HEADING_RE = re.compile(r"^\s*(\d{1,3})\.\s+\S")
SUB_HEADING_RE = re.compile(r"^\s*\d{1,3}\.\d{1,3}")
MAX_TITLE_LEN = 80


class BaseClauseSplitter(abc.ABC):
    @abc.abstractmethod
    def split(self, text: str) -> list[Clause]: ...


class NumberedClauseSplitter(BaseClauseSplitter):
    def split(self, text: str) -> list[Clause]:
        blocks: list[tuple[str | None, list[str]]] = []
        current: tuple[str | None, list[str]] | None = None

        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if not line.strip():
                if current is not None:
                    current[1].append("")
                continue

            if SUB_HEADING_RE.match(line):
                # суб-пункт продолжает текущий заголовок
                if current is not None:
                    current[1].append(line)
                else:
                    current = (None, [line])
                continue

            if HEADING_RE.match(line):
                if current is not None:
                    blocks.append(current)
                current = (self._make_title(line), [line])
                continue

            if current is None:
                current = ("Преамбула", [line])
            else:
                current[1].append(line)

        if current is not None:
            blocks.append(current)

        clauses = []
        for idx, (title, lines) in enumerate(blocks, start=1):
            body = "\n".join(lines).strip()
            if not body:
                continue
            clauses.append(Clause(index=idx, title=title or "Пункт", text=body))
        return clauses

    @staticmethod
    def _make_title(heading_line: str) -> str:
        title = re.sub(r"^[\d\s.]+", "", heading_line.strip())
        title = title.strip()
        if len(title) > MAX_TITLE_LEN:
            title = title[:MAX_TITLE_LEN].rstrip(",;:- ") + "…"
        return title or "Пункт"


class ParagraphClauseSplitter(BaseClauseSplitter):
    def split(self, text: str) -> list[Clause]:
        blocks: list[str] = []
        current: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if not line.strip():
                if current:
                    blocks.append("\n".join(current).strip())
                    current = []
            else:
                current.append(line)
        if current:
            blocks.append("\n".join(current).strip())

        clauses = []
        for idx, block in enumerate(blocks, start=1):
            if not block:
                continue
            title = self._make_title(block)
            clauses.append(Clause(index=idx, title=title, text=block))
        return clauses

    @staticmethod
    def _make_title(block: str) -> str:
        first_sentence = re.split(r"(?<=[.!?])\s", " ".join(block.split()))[0]
        return first_sentence[:MAX_TITLE_LEN]


class ClauseSplitterSelector:
    """Композитная стратегия: нумерованный сплиттер + проверка покрытия."""

    def __init__(
        self,
        min_clauses: int = 2,
        min_coverage: float = 0.5,
    ) -> None:
        self._numbered = NumberedClauseSplitter()
        self._paragraph = ParagraphClauseSplitter()
        self._min_clauses = min_clauses
        self._min_coverage = min_coverage

    def split(self, text: str) -> list[Clause]:
        clauses = self._numbered.split(text)
        total_chars = max(len(text), 1)
        coverage = sum(len(c.text) for c in clauses) / total_chars
        if len(clauses) >= self._min_clauses and coverage >= self._min_coverage:
            return clauses
        return self._paragraph.split(text)
