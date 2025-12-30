"""Agent runner service for executing the investigation workflow.

This service invokes the LangGraph agent to analyze uploaded files and
generate an investigation report.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Add agent to path if not already
agent_path = Path(__file__).parent.parent.parent.parent / "agent" / "src"
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))


def _load_file_infos(session_path: Path) -> list[dict[str, Any]]:
    """Load file information from session directory."""
    files_path = session_path / "files"
    file_infos = []

    for meta_file in files_path.glob("*_meta.json"):
        with open(meta_file, "r") as f:
            meta = json.load(f)

        file_id = meta_file.stem.replace("_meta", "")
        csv_path = files_path / f"{file_id}.csv"

        if csv_path.exists():
            file_infos.append(
                {
                    "file_id": file_id,
                    "name": meta.get("original_name", csv_path.name),
                    "path": str(csv_path),
                    "description": meta.get("description", ""),
                    "schema": meta.get("schema"),
                }
            )

    return file_infos


def _load_context(session_path: Path) -> dict[str, Any]:
    """Load investigation context from session directory."""
    context_path = session_path / "context.json"
    with open(context_path, "r") as f:
        return json.load(f)


async def run_investigation_async(session_id: str, session_path_str: str) -> None:
    """Run the investigation workflow asynchronously.

    Args:
        session_id: UUID of the session
        session_path_str: Path to session directory
    """
    from ..services.session_manager import session_manager

    session_path = Path(session_path_str)

    try:
        logger.info(f"Starting investigation for session {session_id}")

        # Load file information
        files = _load_file_infos(session_path)
        if not files:
            raise ValueError("No files found in session")

        # Load investigation context
        context = _load_context(session_path)

        # Import and run the agent graph
        from graph import get_graph
        from state import InvestigationState

        # Build initial state
        initial_state: InvestigationState = {
            "session_id": session_id,
            "files": files,
            "business_context": context.get("business_context", ""),
            "target_metric": context["target_metric"],
            "metric_definition": context["metric_definition"],
            "baseline_period": context["baseline_period"],
            "comparison_period": context["comparison_period"],
            "investigation_prompt": context.get("investigation_prompt"),
            # Initialize outputs
            "data_model": None,
            "selected_dimensions": None,
            "metric_requirements": None,
            "hypotheses": [],
            "findings_ledger": [],
            "session_logs": [],
            "explanations": None,
            "report_path": None,
            "memory_document_id": None,
            "status": "running",
            "error": None,
        }

        # Get compiled graph and run
        graph = get_graph()
        final_state = await graph.ainvoke(initial_state)

        # Update session status based on result
        from uuid import UUID

        session_uuid = UUID(session_id)
        final_status = final_state.get("status", "completed")

        if final_status == "failed":
            session_manager.update_session(session_uuid, status="failed")
            logger.error(
                f"Investigation failed for session {session_id}: "
                f"{final_state.get('error', 'Unknown error')}"
            )
        elif final_status == "no_findings":
            session_manager.update_session(
                session_uuid, status="completed", report_ready=True
            )
            logger.info(
                f"Investigation completed for session {session_id} with no findings"
            )
        else:
            session_manager.update_session(
                session_uuid, status="completed", report_ready=True
            )
            logger.info(f"Investigation completed successfully for session {session_id}")

    except Exception as e:
        logger.exception(f"Investigation failed for session {session_id}")
        # Update session to failed status
        try:
            from uuid import UUID

            session_manager.update_session(UUID(session_id), status="failed")
        except Exception:
            pass

        # Write error to session directory
        error_path = session_path / "error.json"
        with open(error_path, "w") as f:
            json.dump(
                {
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                f,
                indent=2,
            )


def run_investigation(session_id: str, session_path_str: str) -> None:
    """Run the investigation workflow (sync wrapper for background task).

    Args:
        session_id: UUID of the session
        session_path_str: Path to session directory
    """
    # Run the async function in an event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(run_investigation_async(session_id, session_path_str))
