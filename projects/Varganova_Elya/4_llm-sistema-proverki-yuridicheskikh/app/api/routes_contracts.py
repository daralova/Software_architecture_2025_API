"""Роуты загрузки и статуса договоров (API Gateway)."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter(prefix="/api/v1", tags=["contracts"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.post("/contracts", status_code=202)
async def upload_contract(
    request: object = None,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    filename: str | None = Form(None),
):
    """Загрузка договора. Ставит событие в очередь, обработка — асинхронная."""
    facade = request.app.state.facade  # type: ignore[attr-defined]

    if file is not None:
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Файл слишком большой (лимит 20 МБ)")
        result = facade.upload(file.filename or "document.txt", file.content_type or "", data)
        return result

    if text:
        name = filename or "pasted.txt"
        result = facade.upload(name, "text/plain", text.encode("utf-8"))
        return result

    raise HTTPException(status_code=400, detail="Нужен файл (multipart) или поле text")


@router.get("/contracts/{contract_id}")
def get_contract(contract_id: str, request: object = None):
    facade = request.app.state.facade  # type: ignore[attr-defined]
    contract = facade.get_contract(contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Договор не найден")
    return {
        "contract_id": contract.id,
        "filename": contract.filename,
        "status": contract.status.value,
        "error": contract.error,
        "size_bytes": contract.size_bytes,
        "created_at": contract.created_at.isoformat(),
    }
