"""Служебные роуты: health-check и переиндексация знаний."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1", tags=["admin"])


@router.get("/admin/reindex")
def reindex(request: Request):
    facade = request.app.state.facade
    count = facade.reindex()
    return {"indexed_chunks": count}


@router.get("/health")
def health(request: Request):
    facade = request.app.state.facade
    return {"status": "ok", "app": facade._settings.app_name}
