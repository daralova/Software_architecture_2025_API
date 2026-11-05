-- Схема БД с поддержкой pgvector (эмбеддинги юридической базы знаний).
-- PostgreSQL: используйте образ pgvector/pgvector или установите расширение.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS contracts (
    id           VARCHAR(64) PRIMARY KEY,
    filename     TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT '',
    size_bytes   INTEGER NOT NULL DEFAULT 0,
    storage_key  TEXT NOT NULL DEFAULT '',
    text         TEXT NOT NULL DEFAULT '',
    status       VARCHAR(32) NOT NULL DEFAULT 'uploaded',
    error        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id          BIGSERIAL PRIMARY KEY,
    contract_id VARCHAR(64) NOT NULL,
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reports_contract ON analysis_reports (contract_id);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id        VARCHAR(64) PRIMARY KEY,
    title     TEXT NOT NULL,
    source    TEXT NOT NULL DEFAULT '',
    content   TEXT NOT NULL,
    embedding VECTOR(384)
);
