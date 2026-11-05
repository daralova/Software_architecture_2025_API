"""Стратегии детекции рискованных условий (паттерн Strategy).

Каждая стратегия — независимый детектор одного класса рисков. Новая проверка
добавляется одним классом в RISK_STRATEGIES без изменения остального кода.
"""
from __future__ import annotations

import abc
import re

from app.domain.entities import Clause, RiskFinding, RiskLevel

class BaseRiskStrategy(abc.ABC):
    rule_id: str = "base"
    level: RiskLevel = RiskLevel.MEDIUM
    recommendation: str = ""

    @abc.abstractmethod
    def match(self, clause: Clause) -> bool: ...

    def message(self, clause: Clause) -> str:
        return f"Пункт {clause.index} содержит рискованное условие."

    def scan(self, clause: Clause) -> list[RiskFinding]:
        if not self.match(clause):
            return []
        snippet = " ".join(clause.text.split())[:200]
        return [
            RiskFinding(
                clause_index=clause.index,
                rule_id=self.rule_id,
                level=self.level,
                message=self.message(clause),
                snippet=snippet,
                recommendation=self.recommendation,
            )
        ]


class UnlimitedLiabilityStrategy(BaseRiskStrategy):
    rule_id = "unlimited_liability"
    level = RiskLevel.HIGH
    recommendation = (
        "Ограничить ответственность суммой по договору; исключить слова "
        "«полная ответственность» и «без ограничений»."
    )
    _pattern = re.compile(
        r"полную?\s+ответственность|ответственность\s+в\s+полном\s+объ[её]ме"
        r"|все\s+убытки[^.]*(?:без|в\s+полном)|без\s+каких-?либо\s+ограничени[йя]",
        re.IGNORECASE,
    )

    def match(self, clause: Clause) -> bool:
        return bool(self._pattern.search(clause.text))

    def message(self, clause: Clause) -> str:
        return (
            f"Пункт {clause.index}: ответственность фактически не ограничена — "
            "сторона отвечает за все убытки в полном объёме."
        )


class UnilateralTerminationStrategy(BaseRiskStrategy):
    rule_id = "unilateral_termination"
    level = RiskLevel.MEDIUM
    recommendation = (
        "Согласовать симметричное право отказа: равные сроки уведомления и "
        "последствия расторжения для обеих сторон."
    )
    _pattern = re.compile(
        r"односторон\w+\s+(?:отказ|расторжен)|(?:вправе\s+(?:отказаться|расторгнуть))"
        r"[^.]{0,120}(?:в\s+любой\s+момент|без\s+объяснения\s+причин)?"
        r"|без\s+объяснения\s+причин",
        re.IGNORECASE,
    )

    def match(self, clause: Clause) -> bool:
        return bool(self._pattern.search(clause.text))

    def message(self, clause: Clause) -> str:
        return (
            f"Пункт {clause.index}: допускается односторонний отказ без "
            "взвешенных для обеих сторон условий выхода."
        )


class PenaltyWithoutCapStrategy(BaseRiskStrategy):
    rule_id = "penalty_without_cap"
    level = RiskLevel.MEDIUM
    recommendation = (
        "Установить верхний предел неустойки (например, не более 10% от суммы "
        "договора) — иначе её размер формально не ограничен."
    )
    _penalty_re = re.compile(r"неустойк\w+|пени|штраф[а-я]*", re.IGNORECASE)
    _percent_re = re.compile(r"\d+(?:[.,]\d+)?\s*%")
    # предел считается установленным, только если рядом со словами-ограничителями
    # стоит числовой порог (например, «не более 10%»)
    _cap_re = re.compile(
        r"(?:не\s+более|но\s+не\s+свыше|не\s+превыша\w+|максимум\w*|ограничен\w*)"
        r"[^.]{0,60}?\d+(?:[.,]\d+)?\s*%",
        re.IGNORECASE,
    )

    def match(self, clause: Clause) -> bool:
        if not self._penalty_re.search(clause.text):
            return False
        if not self._percent_re.search(clause.text):
            return False
        return not self._cap_re.search(clause.text)

    def message(self, clause: Clause) -> str:
        return (
            f"Пункт {clause.index}: неустойка/штраф привязан к проценту, но "
            "верхний предел не установлен."
        )


class ExclusiveRightsTransferStrategy(BaseRiskStrategy):
    rule_id = "exclusive_rights_transfer"
    level = RiskLevel.HIGH
    recommendation = (
        "Уточнить объём и момент перехода исключительных прав; предусмотреть "
        "компенсацию за отчуждение и сохранить права на инструменты."
    )
    _pattern = re.compile(
        r"исключительные\s+права[^.]{0,200}(?:переход\w+|отчужд\w+)"
        r"|(?:переход\w+|отчужд\w+)[^.]{0,100}исключительн\w+\s+права",
        re.IGNORECASE,
    )

    def match(self, clause: Clause) -> bool:
        return bool(self._pattern.search(clause.text))

    def message(self, clause: Clause) -> str:
        return (
            f"Пункт {clause.index}: исключительные права переходят контрагенту — "
            "проверьте объём передачи, момент и встречное предоставление."
        )


class AutoRenewalStrategy(BaseRiskStrategy):
    rule_id = "auto_renewal"
    level = RiskLevel.MEDIUM
    recommendation = (
        "Увеличить срок уведомления об отказе от пролонгации (30–60 дней) и "
        "зафиксировать форму уведомления; короткий срок ведёт к незаметному "
        "продлению на новый период."
    )
    _pattern = re.compile(
        r"(?:пролонгиру\w+|продл[её]н\w+|продлевается)\s*(?:автоматически|[^.]*)"
        r"|автоматически\s+(?:пролонгиру\w+|продл[её]н\w+|продлевается)",
        re.IGNORECASE,
    )
    _short_notice_re = re.compile(r"(?:за|не\s+позднее\s+чем\s+за)\s*(\d{1,2})\s*дн")

    def match(self, clause: Clause) -> bool:
        if not self._pattern.search(clause.text):
            return False
        notice = self._short_notice_re.search(clause.text)
        return notice is None or int(notice.group(1)) < 30

    def message(self, clause: Clause) -> str:
        return (
            f"Пункт {clause.index}: автоматическая пролонгация с коротким сроком "
            "уведомления об отказе."
        )


class PersonalDataStrategy(BaseRiskStrategy):
    rule_id = "personal_data"
    level = RiskLevel.HIGH
    recommendation = (
        "Указать конкретные цели и состав обрабатываемых данных, порядок "
        "поручения обработки и требования безопасности (152-ФЗ)."
    )
    _pattern = re.compile(r"персональн\w+\s+данн\w+", re.IGNORECASE)
    _broad_consent_re = re.compile(
        r"люб\w+\s+действи\w+\s+с\s+персональн\w+"
        r"|без\s+дополнительного\s+согласия"
        r"|любые\s+цели",
        re.IGNORECASE,
    )

    def match(self, clause: Clause) -> bool:
        if not self._pattern.search(clause.text):
            return False
        return bool(self._broad_consent_re.search(clause.text))

    def message(self, clause: Clause) -> str:
        return (
            f"Пункт {clause.index}: согласие на обработку персональных данных "
            "сформулировано слишком широко."
        )


RISK_STRATEGIES: list[BaseRiskStrategy] = [
    UnlimitedLiabilityStrategy(),
    UnilateralTerminationStrategy(),
    PenaltyWithoutCapStrategy(),
    ExclusiveRightsTransferStrategy(),
    AutoRenewalStrategy(),
    PersonalDataStrategy(),
]


class RiskScanner:
    """Фасад над набором стратегий: прогоняет все детекторы по пункту."""

    def __init__(self, strategies: list[BaseRiskStrategy] | None = None) -> None:
        self._strategies = strategies or list(RISK_STRATEGIES)

    def scan(self, clause: Clause) -> list[RiskFinding]:
        findings: list[RiskFinding] = []
        for strategy in self._strategies:
            findings.extend(strategy.scan(clause))
        return findings

    def scan_all(self, clauses: list[Clause]) -> list[RiskFinding]:
        findings: list[RiskFinding] = []
        for clause in clauses:
            findings.extend(self.scan(clause))
        return findings
