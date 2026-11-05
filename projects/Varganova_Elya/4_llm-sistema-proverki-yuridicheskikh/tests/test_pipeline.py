"""Интеграционный тест пайплайна на in-memory стеке."""
from app.core.config import Settings
from app.facade.container import build_facade
from app.strategies.splitters import NumberedClauseSplitter, ParagraphClauseSplitter

SAMPLE = """ДОГОВОР N 5

1. ПРЕДМЕТ ДОГОВОРА
1.1. Исполнитель оказывает услуги по разработке ПО.
1.2. Услуги считаются оказанными после подписания акта.

2. ОТВЕТСТВЕННОСТЬ
2.1. Исполнитель несет полную ответственность за все убытки без ограничений.
"""


def test_numbered_splitter_ignores_sub_items():
    clauses = NumberedClauseSplitter().split(SAMPLE)
    # заголовок документа -> преамбула, затем два нумерованных пункта;
    # суб-пункты 1.1 и 1.2 НЕ создают отдельных пунктов
    assert len(clauses) == 3
    assert clauses[0].title == "Преамбула"
    assert clauses[1].title == "ПРЕДМЕТ ДОГОВОРА"
    assert "1.1." in clauses[1].text
    assert "1.2." in clauses[1].text


def test_paragraph_fallback():
    clauses = ParagraphClauseSplitter().split("Первый абзац текста.\n\nВторой абзац.\n")
    assert len(clauses) == 2


def test_end_to_end_pipeline():
    settings = Settings()
    facade = build_facade(settings)
    facade.ensure_knowledge()
    uploaded = facade.upload("test.txt", "text/plain", SAMPLE.encode("utf-8"))
    report = facade.process(uploaded["contract_id"])

    assert report.status.value == "completed"
    assert len(report.clauses) == 3
    assert any(f.rule_id == "unlimited_liability" for f in report.findings)
    # у каждого рискового пункта есть RAG-цитаты
    for finding in report.findings:
        assert finding.citations, f"нет цитат для {finding.rule_id}"
    assert "риск" in report.summary.lower() or "Выявлено" in report.summary
