"""SQLAlchemy-реализации репозиториев для PostgreSQL."""
from __future__ import annotations

import datetime as dt
import json

from app.domain.entities import (
    AnalysisReport,
    Clause,
    Contract,
    ContractStatus,
    KnowledgeChunk,
    RiskFinding,
    RiskLevel,
)
from app.repositories.base import (
    ContractRepository,
    KnowledgeRepository,
    ReportRepository,
)


def _as_list(value):
    return list(value) if isinstance(value, (list, tuple)) else value


class SqlAlchemyContractRepository(ContractRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def add(self, contract: Contract) -> None:
        from app.db.models import ContractModel

        with self._session_factory() as session:
            session.add(ContractModel(
                id=contract.id,
                filename=contract.filename,
                content_type=contract.content_type,
                size_bytes=contract.size_bytes,
                storage_key=contract.storage_key,
                text=contract.text,
                status=contract.status.value,
                error=contract.error,
                created_at=contract.created_at,
                updated_at=contract.updated_at,
            ))
            session.commit()

    def get(self, contract_id: str):
        from app.db.models import ContractModel

        with self._session_factory() as session:
            model = session.get(ContractModel, contract_id)
            if model is None:
                return None
            return self._to_entity(model)

    def update(self, contract: Contract) -> None:
        from app.db.models import ContractModel

        with self._session_factory() as session:
            model = session.get(ContractModel, contract.id)
            if model is None:
                return
            model.filename = contract.filename
            model.content_type = contract.content_type
            model.size_bytes = contract.size_bytes
            model.storage_key = contract.storage_key
            model.text = contract.text
            model.status = contract.status.value
            model.error = contract.error
            model.updated_at = dt.datetime.now(tz=dt.timezone.utc)
            session.commit()

    def all(self) -> list[Contract]:
        from app.db.models import ContractModel

        with self._session_factory() as session:
            models = session.query(ContractModel).order_by(ContractModel.created_at).all()
            return [self._to_entity(m) for m in models]

    @staticmethod
    def _to_entity(model) -> Contract:
        return Contract(
            id=model.id,
            filename=model.filename,
            content_type=model.content_type,
            size_bytes=model.size_bytes,
            storage_key=model.storage_key,
            text=model.text,
            status=ContractStatus(model.status),
            error=model.error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyReportRepository(ReportRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def save(self, report: AnalysisReport) -> None:
        from app.db.models import AnalysisReportModel

        with self._session_factory() as session:
            session.add(AnalysisReportModel(
                contract_id=report.contract_id,
                payload=json.dumps(report.to_dict(), ensure_ascii=False),
            ))
            session.commit()

    def latest_for(self, contract_id: str):
        from app.db.models import AnalysisReportModel

        with self._session_factory() as session:
            model = (
                session.query(AnalysisReportModel)
                .filter(AnalysisReportModel.contract_id == contract_id)
                .order_by(AnalysisReportModel.id.desc())
                .first()
            )
            if model is None:
                return None
            return AnalysisReport.from_dict(json.loads(model.payload))


class SqlAlchemyKnowledgeRepository(KnowledgeRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def clear(self) -> None:
        from app.db.models import KnowledgeChunkModel

        with self._session_factory() as session:
            session.query(KnowledgeChunkModel).delete()
            session.commit()

    def add_all(self, chunks: list[KnowledgeChunk]) -> None:
        from app.db.models import KnowledgeChunkModel

        with self._session_factory() as session:
            for chunk in chunks:
                session.merge(KnowledgeChunkModel(
                    id=chunk.id, title=chunk.title,
                    source=chunk.source, content=chunk.content,
                ))
            session.commit()

    def all(self) -> list[KnowledgeChunk]:
        from app.db.models import KnowledgeChunkModel

        with self._session_factory() as session:
            models = session.query(KnowledgeChunkModel).all()
            return [
                KnowledgeChunk(id=m.id, title=m.title, source=m.source, content=m.content)
                for m in models
            ]

    def count(self) -> int:
        from app.db.models import KnowledgeChunkModel

        with self._session_factory() as session:
            return session.query(KnowledgeChunkModel).count()
