"""Memory dump node for storing analysis memory in Supabase.

This node compiles all investigation data into a memory document
and stores it in Supabase for RAG-based Q&A retrieval.
"""

import logging
import os
from pathlib import Path

from ..memory import working_memory
from ..memory.supabase_rag import store_memory_document
from ..state import InvestigationState

logger = logging.getLogger(__name__)


async def memory_dump(state: InvestigationState) -> dict:
    """Compile and store memory document in Supabase.

    This node:
    1. Compiles all investigation data into a memory document
    2. Stores the document in Supabase with embeddings for RAG
    3. Returns the document ID for future reference

    Args:
        state: Current investigation state

    Returns:
        Updated state with memory_document_id
    """
    session_id = state["session_id"]
    logger.info(f"Dumping memory for session {session_id}")

    # Get session path
    sessions_root = os.environ.get("SESSION_STORAGE_PATH", "./sessions")
    session_path = Path(sessions_root) / session_id

    try:
        # Compile memory document
        memory_document = working_memory.compile_memory_document(session_path, state)

        # Save locally for reference
        memory_path = session_path / "analysis" / "memory_document.md"
        with open(memory_path, "w", encoding="utf-8") as f:
            f.write(memory_document)

        logger.debug(f"Memory document saved to {memory_path}")

        # Store in Supabase (if configured)
        document_id = None
        supabase_url = os.environ.get("SUPABASE_URL")
        if supabase_url:
            try:
                document_id = await store_memory_document(
                    session_id=session_id,
                    content=memory_document,
                    metadata={
                        "target_metric": state.get("target_metric", ""),
                        "summary": working_memory.get_memory_document_summary(state),
                    },
                )
                logger.info(f"Memory document stored in Supabase: {document_id}")
            except Exception as e:
                logger.warning(f"Failed to store memory in Supabase: {e}")
                # Continue without Supabase - local storage is available
        else:
            logger.info("Supabase not configured - memory stored locally only")

        return {"memory_document_id": document_id}

    except Exception as e:
        logger.exception(f"Memory dump failed: {e}")
        return {
            "memory_document_id": None,
            "error": f"Memory dump failed: {str(e)}",
        }
