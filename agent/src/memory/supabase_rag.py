"""Supabase client wrapper for RAG memory storage and retrieval.

This module handles storing investigation memory documents in Supabase
with embeddings for similarity search, enabling Q&A after analysis.
"""

import os
from typing import Any

from supabase import create_client, Client


class SupabaseRAGError(Exception):
    """Error during Supabase RAG operations."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class SupabaseRAG:
    """Supabase client for memory document storage and RAG retrieval."""

    def __init__(
        self,
        url: str | None = None,
        key: str | None = None,
    ):
        """Initialize Supabase client.

        Args:
            url: Supabase project URL (defaults to SUPABASE_URL env var)
            key: Supabase service key (defaults to SUPABASE_SERVICE_KEY env var)
        """
        self.url = url or os.environ.get("SUPABASE_URL")
        self.key = key or os.environ.get("SUPABASE_SERVICE_KEY")

        if not self.url or not self.key:
            raise SupabaseRAGError(
                code="MISSING_CREDENTIALS",
                message="Supabase URL and key are required",
            )

        self._client: Client | None = None

    @property
    def client(self) -> Client:
        """Get or create Supabase client (lazy initialization)."""
        if self._client is None:
            self._client = create_client(self.url, self.key)
        return self._client

    async def store_document(
        self,
        session_id: str,
        content: str,
        embedding: list[float] | None = None,
    ) -> str:
        """Store a memory document with optional embedding.

        Args:
            session_id: Session identifier
            content: Full document content
            embedding: Optional pre-computed embedding vector

        Returns:
            Document ID from Supabase
        """
        try:
            data = {
                "session_id": session_id,
                "content": content,
            }

            if embedding:
                data["embedding"] = embedding

            result = self.client.table("memory_documents").insert(data).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]["document_id"]

            raise SupabaseRAGError(
                code="INSERT_FAILED",
                message="Failed to insert document",
            )
        except Exception as e:
            raise SupabaseRAGError(
                code="STORE_DOCUMENT_FAILED",
                message=f"Failed to store document: {e}",
                details={"session_id": session_id},
            )

    async def similarity_search(
        self,
        query_embedding: list[float],
        session_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Find similar documents using vector similarity.

        Args:
            query_embedding: Query vector for similarity search
            session_id: Optional filter by session
            top_k: Number of results to return

        Returns:
            List of matching documents with similarity scores
        """
        try:
            # Use Supabase RPC for vector similarity search
            params = {
                "query_embedding": query_embedding,
                "match_count": top_k,
            }

            if session_id:
                params["filter_session_id"] = session_id

            result = self.client.rpc("match_documents", params).execute()

            return result.data or []
        except Exception as e:
            raise SupabaseRAGError(
                code="SIMILARITY_SEARCH_FAILED",
                message=f"Failed to search documents: {e}",
            )

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        """Get a document by ID.

        Args:
            document_id: Document identifier

        Returns:
            Document data or None if not found
        """
        try:
            result = (
                self.client.table("memory_documents")
                .select("*")
                .eq("document_id", document_id)
                .execute()
            )

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            raise SupabaseRAGError(
                code="GET_DOCUMENT_FAILED",
                message=f"Failed to get document: {e}",
                details={"document_id": document_id},
            )

    async def get_session_document(self, session_id: str) -> dict[str, Any] | None:
        """Get the memory document for a session.

        Args:
            session_id: Session identifier

        Returns:
            Document data or None if not found
        """
        try:
            result = (
                self.client.table("memory_documents")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            raise SupabaseRAGError(
                code="GET_SESSION_DOCUMENT_FAILED",
                message=f"Failed to get session document: {e}",
                details={"session_id": session_id},
            )

    async def delete_session_documents(self, session_id: str) -> int:
        """Delete all documents for a session (cleanup on expiry).

        Args:
            session_id: Session identifier

        Returns:
            Number of documents deleted
        """
        try:
            result = (
                self.client.table("memory_documents")
                .delete()
                .eq("session_id", session_id)
                .execute()
            )

            return len(result.data) if result.data else 0
        except Exception as e:
            raise SupabaseRAGError(
                code="DELETE_DOCUMENTS_FAILED",
                message=f"Failed to delete documents: {e}",
                details={"session_id": session_id},
            )


# Global instance (lazy initialization)
_supabase_rag: SupabaseRAG | None = None


def get_supabase_rag() -> SupabaseRAG:
    """Get the global Supabase RAG instance."""
    global _supabase_rag
    if _supabase_rag is None:
        _supabase_rag = SupabaseRAG()
    return _supabase_rag


async def store_memory_document(
    session_id: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """Store a memory document in Supabase.

    This is a convenience function that handles initialization
    and embedding generation.

    Args:
        session_id: Session identifier
        content: Full document content
        metadata: Optional metadata (not stored, for logging only)

    Returns:
        Document ID or None if storage is not configured
    """
    try:
        rag = get_supabase_rag()

        # For MVP, store without embeddings
        # In production, would generate embeddings here
        document_id = await rag.store_document(
            session_id=session_id,
            content=content,
            embedding=None,  # Will be generated by Supabase function
        )

        return document_id

    except SupabaseRAGError as e:
        if e.code == "MISSING_CREDENTIALS":
            # Supabase not configured - this is OK for MVP
            return None
        raise


async def search_memory(
    session_id: str,
    query: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Search memory documents for a session.

    Args:
        session_id: Session to search within
        query: Search query text
        top_k: Number of results to return

    Returns:
        List of matching document chunks
    """
    try:
        rag = get_supabase_rag()

        # For MVP, do simple session lookup instead of vector search
        doc = await rag.get_session_document(session_id)
        if doc:
            return [doc]
        return []

    except SupabaseRAGError:
        return []
