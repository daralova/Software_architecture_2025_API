"""API Gateway приложения (FastAPI)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import routes_admin, routes_analysis, routes_contracts
from app.core.config import get_settings
from app.core.logging import get_logger
from app.facade.container import build_facade

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.facade = build_facade(settings)
    app.state.settings = settings
    indexed = app.state.facade.ensure_knowledge()
    logger.info("API готово; чанков знаний проиндексировано: %s", indexed)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="LLM-система проверки юридических договоров",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(routes_contracts.router)
    app.include_router(routes_analysis.router)
    app.include_router(routes_admin.router)
    return app


app = create_app()
