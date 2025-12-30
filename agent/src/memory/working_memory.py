"""Working memory for compiling analysis memory documents.

This module compiles all investigation data into a structured document
that can be stored in Supabase for RAG-based Q&A retrieval.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..state import InvestigationState
from . import findings_ledger, progress_log

logger = logging.getLogger(__name__)


def compile_memory_document(
    session_path: str | Path,
    state: InvestigationState,
) -> str:
    """Compile all analysis memory into a document for RAG storage.

    This creates a comprehensive text document containing:
    - Investigation context (metric, dates, business context)
    - Data model summary
    - All hypotheses with final status
    - All findings from the ledger
    - Key reasoning and conclusions

    Args:
        session_path: Path to the session directory
        state: Final investigation state

    Returns:
        Compiled memory document as a string
    """
    session_path = Path(session_path)
    sections = []

    # Header
    sections.append("# Investigation Memory Document")
    sections.append(f"Session ID: {state.get('session_id', 'Unknown')}")
    sections.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    sections.append("")

    # Investigation Context
    sections.append("## Investigation Context")
    sections.append("")
    sections.append(f"**Target Metric**: {state.get('target_metric', 'Unknown')}")
    sections.append(f"**Metric Definition**: {state.get('metric_definition', 'Not provided')}")
    sections.append("")

    baseline = state.get("baseline_period", {})
    comparison = state.get("comparison_period", {})
    sections.append(
        f"**Baseline Period**: {baseline.get('start', 'N/A')} to {baseline.get('end', 'N/A')}"
    )
    sections.append(
        f"**Comparison Period**: {comparison.get('start', 'N/A')} to {comparison.get('end', 'N/A')}"
    )
    sections.append("")

    if state.get("business_context"):
        sections.append("**Business Context**:")
        sections.append(state["business_context"])
        sections.append("")

    if state.get("investigation_prompt"):
        sections.append("**Investigation Focus**:")
        sections.append(state["investigation_prompt"])
        sections.append("")

    # Data Model
    sections.append("## Data Model")
    sections.append("")
    data_model = state.get("data_model", {})
    if data_model:
        sections.append("### Tables Analyzed")
        for table in data_model.get("tables", []):
            sections.append(f"- **{table.get('name', 'Unknown')}**: {table.get('row_count', 0):,} rows")
            columns = table.get("columns", [])
            if columns:
                col_summary = ", ".join(
                    f"{c.get('name', '')} ({c.get('inferred_type', 'unknown')})"
                    for c in columns[:5]
                )
                if len(columns) > 5:
                    col_summary += f" (+{len(columns) - 5} more)"
                sections.append(f"  Columns: {col_summary}")
        sections.append("")

        if data_model.get("relationships"):
            sections.append("### Relationships")
            for rel in data_model["relationships"]:
                sections.append(
                    f"- {rel.get('from_table', '')}.{rel.get('from_column', '')} -> "
                    f"{rel.get('to_table', '')}.{rel.get('to_column', '')} "
                    f"({rel.get('relationship_type', 'unknown')})"
                )
            sections.append("")

        if data_model.get("recommended_dimensions"):
            sections.append("### Key Dimensions")
            sections.append(", ".join(data_model["recommended_dimensions"]))
            sections.append("")

    # Hypotheses
    sections.append("## Hypotheses Investigated")
    sections.append("")
    hypotheses = state.get("hypotheses", [])
    for hyp in hypotheses:
        status_emoji = "✓" if hyp.get("status") == "CONFIRMED" else "✗"
        sections.append(f"### [{status_emoji}] {hyp.get('id', 'H?')}: {hyp.get('title', 'Unknown')}")
        sections.append(f"**Status**: {hyp.get('status', 'UNKNOWN')}")
        sections.append(f"**Causal Story**: {hyp.get('causal_story', 'N/A')}")
        sections.append(f"**Expected Pattern**: {hyp.get('expected_pattern', 'N/A')}")
        sections.append(f"**Dimensions**: {', '.join(hyp.get('dimensions', []))}")
        sections.append("")

    # Findings
    sections.append("## Key Findings")
    sections.append("")
    try:
        ledger = findings_ledger.read_findings_ledger(session_path)
        for finding in ledger.get("findings", []):
            sections.append(f"### Finding {finding.get('finding_id', '?')}")
            sections.append(f"**Hypothesis**: {finding.get('hypothesis_id', 'Unknown')}")
            sections.append(f"**Outcome**: {finding.get('outcome', 'Unknown')}")
            sections.append(f"**Confidence**: {finding.get('confidence', 'Unknown')}")
            sections.append(f"**Evidence**: {finding.get('evidence', 'N/A')}")
            if finding.get("key_metrics"):
                sections.append("**Key Metrics**:")
                for metric in finding["key_metrics"]:
                    sections.append(f"- {metric}")
            sections.append("")
    except Exception as e:
        logger.warning(f"Failed to read findings ledger: {e}")
        sections.append("*No findings available*")
        sections.append("")

    # Explanations (if available)
    explanations = state.get("explanations", [])
    if explanations:
        sections.append("## Explanations (Ranked)")
        sections.append("")
        for exp in explanations:
            sections.append(f"### {exp.get('rank', '?')}. {exp.get('title', 'Unknown')}")
            sections.append(f"**Likelihood**: {exp.get('likelihood', 'Unknown')}")
            sections.append(f"**Causal Story**: {exp.get('causal_story', 'N/A')}")
            sections.append(f"**Reasoning**: {exp.get('reasoning', 'N/A')}")
            if exp.get("evidence"):
                sections.append("**Evidence**:")
                for ev in exp["evidence"]:
                    if isinstance(ev, dict):
                        sections.append(
                            f"- {ev.get('metric', 'Unknown')}: {ev.get('value', 'N/A')} "
                            f"({ev.get('interpretation', '')})"
                        )
                    else:
                        sections.append(f"- {ev}")
            sections.append("")

    # Progress Summary
    sections.append("## Investigation Progress")
    sections.append("")
    try:
        progress = progress_log.read_progress_log(session_path)
        if progress:
            sections.append("```")
            sections.append(progress)
            sections.append("```")
    except Exception as e:
        logger.warning(f"Failed to read progress log: {e}")
        sections.append("*No progress log available*")
    sections.append("")

    # Footer
    sections.append("---")
    sections.append("*This document is generated for RAG-based Q&A retrieval*")

    return "\n".join(sections)


def get_memory_document_summary(state: InvestigationState) -> str:
    """Generate a short summary for the memory document.

    Args:
        state: Investigation state

    Returns:
        Brief summary string
    """
    hypotheses = state.get("hypotheses", [])
    confirmed = [h for h in hypotheses if h.get("status") == "CONFIRMED"]

    target_metric = state.get("target_metric", "Unknown metric")

    if confirmed:
        return (
            f"Investigation of {target_metric}: "
            f"{len(confirmed)} of {len(hypotheses)} hypotheses confirmed. "
            f"Top finding: {confirmed[0].get('title', 'Unknown')}"
        )
    else:
        return (
            f"Investigation of {target_metric}: "
            f"0 of {len(hypotheses)} hypotheses confirmed. "
            "No clear explanation found."
        )
