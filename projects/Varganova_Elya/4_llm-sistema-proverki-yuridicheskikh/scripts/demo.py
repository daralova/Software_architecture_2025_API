"""Демонстрация работы пайплайна без инфраструктуры.

Запуск: python scripts/demo.py  (нужен только Python >= 3.10)
Все адаптеры — in-memory / rule-based, т.е. демо работает офлайн.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import Settings  # noqa: E402
from app.facade.container import build_facade  # noqa: E402
from app.workers.events import make_event_bus  # noqa: E402
from app.commands.analyze_contract import AnalyzeContractCommand  # noqa: E402
from app.commands.invoker import CommandInvoker  # noqa: E402

SAMPLE_CONTRACT = """ДОГОВОР ОКАЗАНИЯ УСЛУГ N 12/2026

1. ПРЕДМЕТ ДОГОВОРА
1.1. Исполнитель обязуется оказать услуги по разработке программного обеспечения,
а Заказчик обязуется принять и оплатить их в порядке, предусмотренном настоящим Договором.
1.2. Услуги считаются оказанными после подписания акта обеими сторонами.

2. ЦЕНА И ПОРЯДОК РАСЧЕТОВ
2.1. Стоимость услуг составляет 1 200 000 рублей, НДС не облагается.

3. ОТВЕТСТВЕННОСТЬ СТОРОН
3.1. За нарушение сроков Заказчик вправе требовать неустойку в размере 1% от
стоимости услуг за каждый день просрочки.
3.2. Исполнитель несет полную ответственность за все убытки Заказчика без
каких-либо ограничений.

4. ПЕРЕДАЧА ИСПОЛНИТЕЛЬСКИХ ПРАВ
4.1. Все исключительные права на результаты услуг полностью переходят к Заказчику
с момента подписания акта.

5. СРОК ДЕЙСТВИЯ
5.1. Договор вступает в силу с момента подписания и автоматически пролонгируется
на каждый следующий год, если ни одна из сторон не заявила об отказе за 3 дня
до истечения срока.

6. ЗАЩИТА ПЕРСОНАЛЬНЫХ ДАННЫХ
6.1. Заказчик вправе совершать любые действия с персональными данными работников
Исполнителя без дополнительного согласия.
"""


def main() -> None:
    settings = Settings()
    facade = build_facade(settings)
    facade.ensure_knowledge()

    uploaded = facade.upload("demo_contract.txt", "text/plain", SAMPLE_CONTRACT.encode("utf-8"))
    contract_id = uploaded["contract_id"]
    print(f"[1] Договор загружен: {contract_id}")

    invoker = CommandInvoker()
    invoker.register("contract.uploaded", AnalyzeContractCommand(facade))

    event_data = uploaded["event"]
    print(f"[2] Событие {event_data['type']} отправлено в шину")

    invoker.handle(
        type("EventStub", (), {"type": event_data["type"], "payload": event_data["payload"], "id": "demo"})()
    )

    report = facade.get_report(contract_id)
    if report is None:
        print("Отчёт не найден")
        return

    print(f"[3] Пунктов найдено: {len(report.clauses)}")
    for clause in report.clauses:
        print(f"    {clause.index:>2}. {clause.title}")

    print(f"[4] Рисков: {len(report.findings)}")
    for finding in report.findings:
        print(f"    [{finding.level.value.upper():<6}] {finding.message}")
        for citation in finding.citations[:2]:
            print(f"           основание: {citation['title']} ({citation['source']})")

    print("[5] Резюме:")
    for line in report.summary.splitlines():
        print("    " + line)

    print()
    print("Полный JSON отчёта:")
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2)[:2000] + " …")


if __name__ == "__main__":
    main()
