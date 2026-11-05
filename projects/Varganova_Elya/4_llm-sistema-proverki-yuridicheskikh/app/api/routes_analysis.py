"""Роуты отчётов анализа."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.get("/analysis/{contract_id}")
def get_analysis(contract_id: str, request: Request):
    facade = request.app.state.facade
    contract = facade.get_contract(contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Договор не найден")
    report = facade.get_report(contract_id)
    if report is None:
        return {
            "contract_id": contract_id,
            "status": contract.status.value,
            "detail": "Отчёт ещё не готов — обработка идёт асинхронно",
        }
    return report.to_dict()
