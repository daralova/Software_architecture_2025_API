"""Сборка графа зависимостей (композиция адаптеров по настройкам)."""
from __future__ import annotations

from app.adapters.embeddings import make_embedder
from app.adapters.llm import make_llm
from app.adapters.parsers import ParserRegistry
from app.adapters.search import make_search_client
from app.adapters.storage import make_storage
from app.adapters.vector_store import make_vector_store
from app.core.config import Settings, get_settings
from app.facade.facade import ContractReviewFacade
from app.pipeline.pipeline import DocumentProcessingPipeline
from app.pipeline.stages import (
    EmbedStage,
    ParseStage,
    PersistStage,
    RagEnrichmentStage,
    RiskScanStage,
    SplitStage,
    SummarizeStage,
)
from app.rag.knowledge import DEFAULT_KNOWLEDGE
from app.rag.retriever import HybridRetriever
from app.repositories.base import KnowledgeRepository
from app.strategies.risk_rules import RiskScanner
from app.strategies.splitters import ClauseSplitterSelector


def build_facade(settings: Settings | None = None) -> ContractReviewFacade:
    settings = settings or get_settings()

    # --- инфраструктурные бэкенды ---
    engine = None
    contract_repo = report_repo = knowledge_repo = None
    if settings.storage_backend != "memory" or settings.vector_backend == "pgvector":
        from app.db.session import get_engine, make_session_factory
        from app.repositories.sqlalchemy_repo import (
            SqlAlchemyContractRepository,
            SqlAlchemyKnowledgeRepository,
            SqlAlchemyReportRepository,
        )

        engine = get_engine(settings)
        session_factory = make_session_factory(engine)
        contract_repo = SqlAlchemyContractRepository(session_factory)
        report_repo = SqlAlchemyReportRepository(session_factory)
        knowledge_repo = SqlAlchemyKnowledgeRepository(session_factory)

    if contract_repo is None:
        from app.repositories.memory import (
            InMemoryContractRepository,
            InMemoryKnowledgeRepository,
            InMemoryReportRepository,
        )

        contract_repo = InMemoryContractRepository()
        report_repo = InMemoryReportRepository()
        knowledge_repo = InMemoryKnowledgeRepository()

    storage = make_storage(settings)
    embedder = make_embedder(settings)
    vector_store = make_vector_store(settings, engine=engine)
    search_client = make_search_client(settings)
    retriever = HybridRetriever(
        embedder=embedder,
        vector_store=vector_store,
        search_client=search_client,
        top_k=settings.rag_top_k,
    )
    splitter = ClauseSplitterSelector()
    scanner = RiskScanner()
    llm = make_llm(settings)
    parsers = ParserRegistry()

    pipeline = DocumentProcessingPipeline([
        ParseStage(parsers, storage),
        SplitStage(splitter),
        EmbedStage(embedder),
        RiskScanStage(scanner),
        RagEnrichmentStage(retriever, top_k=settings.rag_top_k),
        SummarizeStage(llm),
        PersistStage(contract_repo, report_repo),
    ])

    return ContractReviewFacade(
        contract_repo=contract_repo,
        report_repo=report_repo,
        knowledge_repo=knowledge_repo,
        storage=storage,
        pipeline=pipeline,
        seed_chunks=list(DEFAULT_KNOWLEDGE),
        settings=settings,
    )
