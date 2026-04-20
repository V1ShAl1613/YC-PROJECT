-- Legal AI Agent — PostgreSQL Schema
-- Run: psql -U legalai -d legalai -f 001_init.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS documents (
    doc_id          TEXT PRIMARY KEY,
    case_name       TEXT NOT NULL,
    court           TEXT,
    year            INTEGER,
    jurisdiction    TEXT,
    judge           TEXT,
    source          TEXT CHECK (source IN ('indian_kanoon', 'courtlistener', 'manual')),
    url             TEXT,
    summary         TEXT,
    text            TEXT,
    metadata_json   JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jurisdiction  ON documents (jurisdiction);
CREATE INDEX IF NOT EXISTS idx_year          ON documents (year);
CREATE INDEX IF NOT EXISTS idx_court         ON documents (court);
CREATE INDEX IF NOT EXISTS idx_source        ON documents (source);
CREATE INDEX IF NOT EXISTS idx_text_search   ON documents USING GIN (to_tsvector('english', text));

CREATE TABLE IF NOT EXISTS queries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_text      TEXT NOT NULL,
    jurisdiction    TEXT,
    answer          TEXT,
    fallback        BOOLEAN DEFAULT FALSE,
    confidence_score REAL,
    confidence_label TEXT,
    citation_count  INTEGER DEFAULT 0,
    latency_ms      REAL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS citations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id        UUID REFERENCES queries(id) ON DELETE CASCADE,
    doc_id          TEXT REFERENCES documents(doc_id),
    relevance_score REAL,
    paragraph_used  TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_citations_query ON citations (query_id);

-- Trigger: auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tg_documents_updated_at
  BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
