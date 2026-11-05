"""Тесты стратегий детекции рисков."""
from app.domain.entities import Clause, RiskLevel
from app.strategies.risk_rules import (
    AutoRenewalStrategy,
    ExclusiveRightsTransferStrategy,
    PenaltyWithoutCapStrategy,
    PersonalDataStrategy,
    RiskScanner,
    UnlimitedLiabilityStrategy,
    UnilateralTerminationStrategy,
)


def clause(text: str) -> Clause:
    return Clause(index=1, title="Тест", text=text)


def test_unlimited_liability_fires():
    findings = UnlimitedLiabilityStrategy().scan(
        clause("Исполнитель несет полную ответственность за все убытки Заказчика.")
    )
    assert len(findings) == 1
    assert findings[0].level == RiskLevel.HIGH


def test_unlimited_liability_silent_on_capped():
    findings = UnlimitedLiabilityStrategy().scan(
        clause("Ответственность Исполнителя ограничена суммой договора.")
    )
    assert findings == []


def test_penalty_without_cap_fires():
    findings = PenaltyWithoutCapStrategy().scan(
        clause("За просрочку выплачивается неустойка в размере 1% за каждый день.")
    )
    assert len(findings) == 1


def test_penalty_with_cap_silent():
    findings = PenaltyWithoutCapStrategy().scan(
        clause("Неустойка 0,1% в день, но не более 10% от суммы договора.")
    )
    assert findings == []


def test_auto_renewal_short_notice_fires():
    findings = AutoRenewalStrategy().scan(
        clause("Договор автоматически пролонгируется, отказ — за 3 дня.")
    )
    assert len(findings) == 1


def test_auto_renewal_long_notice_silent():
    findings = AutoRenewalStrategy().scan(
        clause("Договор автоматически продлевается, отказ возможен за 60 дней.")
    )
    assert findings == []


def test_exclusive_rights_fires():
    findings = ExclusiveRightsTransferStrategy().scan(
        clause("Все исключительные права на результаты работ переходят к Заказчику.")
    )
    assert len(findings) == 1


def test_personal_data_broad_consent_fires():
    findings = PersonalDataStrategy().scan(
        clause("Сторона вправе совершать любые действия с персональными данными.")
    )
    assert len(findings) == 1


def test_unilateral_termination_fires():
    findings = UnilateralTerminationStrategy().scan(
        clause("Заказчик вправе отказаться от договора в любой момент без объяснения причин.")
    )
    assert len(findings) == 1


def test_scanner_runs_all_strategies():
    scanner = RiskScanner()
    findings = scanner.scan(clause(
        "Исполнитель несет полную ответственность. "
        "Исключительные права переходят к Заказчику."
    ))
    rule_ids = {f.rule_id for f in findings}
    assert "unlimited_liability" in rule_ids
    assert "exclusive_rights_transfer" in rule_ids
