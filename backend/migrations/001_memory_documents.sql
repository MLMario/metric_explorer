-- Migration: Create memory_documents table for RAG retrieval
-- Requires: pgvector extension

-- Enable pgvector extension (run once per database)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create memory_documents table
CREATE TABLE IF NOT EXISTS memory_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 / Anthropic embedding dimension
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for session lookups
CREATE INDEX IF NOT EXISTS idx_memory_documents_session_id
ON memory_documents(session_id);

-- Index for similarity search using IVFFlat
-- Note: IVFFlat requires data to be present for optimal index creation
-- For small datasets, consider using HNSW instead
CREATE INDEX IF NOT EXISTS idx_memory_documents_embedding
ON memory_documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Function for similarity search with session filter
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    filter_session_id UUID DEFAULT NULL
)
RETURNS TABLE (
    document_id UUID,
    session_id UUID,
    content TEXT,
    created_at TIMESTAMPTZ,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        md.document_id,
        md.session_id,
        md.content,
        md.created_at,
        1 - (md.embedding <=> query_embedding) AS similarity
    FROM memory_documents md
    WHERE
        md.embedding IS NOT NULL
        AND (filter_session_id IS NULL OR md.session_id = filter_session_id)
    ORDER BY md.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Row-level security (optional, for multi-tenant scenarios)
-- ALTER TABLE memory_documents ENABLE ROW LEVEL SECURITY;

-- Cleanup function for expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_documents(
    expired_session_ids UUID[]
)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM memory_documents
    WHERE session_id = ANY(expired_session_ids);

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- Comment on table
COMMENT ON TABLE memory_documents IS
'Stores investigation memory for RAG-based Q&A retrieval. Each session has one document containing all analysis findings.';

COMMENT ON COLUMN memory_documents.embedding IS
'pgvector embedding (1536 dimensions) for similarity search. Generated from document content.';
