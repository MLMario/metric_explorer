"""Analysis execution node for hypothesis investigation.

This node orchestrates the investigation of each hypothesis by:
1. Copying files from session/files to session/analysis/files for analysis
2. Running Claude Agent SDK query() for each hypothesis with tool access
3. Parsing results and updating the findings ledger

The Claude Agent SDK provides an agentic loop where the model can:
- Read CSV files and analyze data
- Write and execute Python scripts
- Iterate until reaching a conclusion (CONFIRMED/RULED_OUT)
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)
from pydantic import BaseModel, Field

from ..memory import findings_ledger, progress_log, session_log
from ..state import Finding, Hypothesis, InvestigationState, SessionLog
from ..tools import mcp_client

logger = logging.getLogger(__name__)


class HypothesisOutcome(BaseModel):
    """Structured output for hypothesis investigation.

    This model is used with Claude Agent SDK's result_type parameter
    to force structured output from the agent.
    """

    outcome: Literal["CONFIRMED", "RULED_OUT"] = Field(
        description="Whether the hypothesis is confirmed or ruled out by the data"
    )
    evidence: str = Field(
        description="Specific findings with numbers supporting the conclusion"
    )
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="Confidence level in the conclusion based on data quality and coverage"
    )
    key_metrics: list[str] = Field(
        default_factory=list,
        description="List of key metrics discovered during analysis",
    )


def _load_analysis_prompt() -> str:
    """Load the analysis system prompt template."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "analysis_system.txt"
    with open(prompt_path, "r") as f:
        return f.read()


def _build_hypothesis_prompt(
    state: InvestigationState,
    hypothesis: Hypothesis,
    file_list: list[str],
    schema_summary: str,
) -> str:
    """Build the prompt for investigating a single hypothesis."""
    template = _load_analysis_prompt()

    baseline = state.get("baseline_period", {})
    comparison = state.get("comparison_period", {})

    prompt = template
    prompt = prompt.replace("{hypothesis_title}", hypothesis["title"])
    prompt = prompt.replace("{hypothesis_story}", hypothesis["causal_story"])
    prompt = prompt.replace("{hypothesis_pattern}", hypothesis["expected_pattern"])
    prompt = prompt.replace("{hypothesis_dimensions}", ", ".join(hypothesis.get("dimensions", [])))
    prompt = prompt.replace("{target_metric}", state.get("target_metric", ""))
    prompt = prompt.replace("{metric_definition}", state.get("metric_definition", ""))
    prompt = prompt.replace(
        "{baseline_period}",
        f"{baseline.get('start', 'N/A')} to {baseline.get('end', 'N/A')}",
    )
    prompt = prompt.replace(
        "{comparison_period}",
        f"{comparison.get('start', 'N/A')} to {comparison.get('end', 'N/A')}",
    )
    prompt = prompt.replace(
        "{business_context}", state.get("business_context", "No context provided")
    )
    prompt = prompt.replace("{file_list}", "\n".join(f"- {f}" for f in file_list))
    prompt = prompt.replace("{schema_summary}", schema_summary)

    return prompt


def _build_schema_summary(state: InvestigationState) -> str:
    """Build a schema summary string from the data model."""
    data_model = state.get("data_model", {})
    if not data_model:
        return "No schema information available"

    lines = []
    for table in data_model.get("tables", []):
        cols = ", ".join(
            f"{c['name']} ({c.get('inferred_type', 'unknown')})"
            for c in table.get("columns", [])[:6]
        )
        if len(table.get("columns", [])) > 6:
            cols += ", ..."
        lines.append(f"{table['name']}: {cols}")

    return "\n".join(lines) if lines else "No schema information available"


def _build_system_prompt() -> str:
    """Build the system prompt for hypothesis investigation."""
    return """You are a data analyst investigating a hypothesis about metric movement.

Your task is to thoroughly analyze the available data and determine if the hypothesis is supported by evidence.

## Process
1. First, read and understand the CSV files in the analysis/files directory
2. Write Python scripts to analyze the data (save to analysis/scripts/)
3. Execute scripts using bash: python analysis/scripts/<script_name>.py
4. Interpret results and gather evidence
5. Iterate as needed to build a complete picture

## Tools Available
- Read: Read CSV files and other text files
- Write: Write Python analysis scripts
- Bash: Execute Python scripts and shell commands
- Glob: Find files by pattern

## Required Python Packages
pandas, numpy, scipy are available in the environment.

## Important
Be specific with numbers and percentages. Support your conclusion with data.
Your final conclusion will be captured as a structured result."""


async def _investigate_hypothesis_with_sdk(
    session_path: Path,
    hypothesis: Hypothesis,
    prompt: str,
    state: InvestigationState,
) -> tuple[SessionLog, Finding]:
    """Investigate a single hypothesis using Claude Agent SDK.

    Uses the query() async generator to run an agentic loop where the model
    can read files, write scripts, and execute them iteratively until
    reaching a conclusion.
    """
    hypothesis_id = hypothesis["id"]
    start_time = datetime.now(timezone.utc)

    # Create session log files
    json_path, md_path = session_log.create_session_log(session_path, hypothesis_id)

    # Get configuration from environment
    max_turns = int(os.environ.get("ANALYSIS_MAX_TURNS", "10"))

    # Configure Claude Agent SDK options with structured output
    options = ClaudeAgentOptions(
        system_prompt=_build_system_prompt(),
        allowed_tools=["Read", "Write", "Bash", "Glob", "Grep"],
        permission_mode="acceptEdits",  # Auto-accept file operations
        cwd=str(session_path),  # Working directory for the agent
        max_turns=max_turns,
        result_type=HypothesisOutcome,  # Force structured output
    )

    # Track metrics
    total_tokens = 0
    cost_usd = 0.0
    turns = 0
    scripts_created = []
    step_number = 0

    # Default result in case of failure
    parsed_result = HypothesisOutcome(
        outcome="RULED_OUT",
        evidence="Analysis could not be completed",
        confidence="LOW",
        key_metrics=[],
    )

    try:
        # Run the Claude Agent SDK query
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                turns += 1
                step_number += 1

                # Extract text content from the message
                text_parts = []
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        # Track tool usage
                        tool_name = block.name
                        if tool_name == "Write" and "scripts/" in str(block.input):
                            # Track script creation
                            script_path = block.input.get("file_path", "")
                            if script_path:
                                scripts_created.append(script_path)

                # Combine text for this turn
                turn_text = "\n".join(text_parts)

                # Log this step to markdown
                session_log.append_session_log_md(
                    md_path,
                    step_number=step_number,
                    action_type="Analysis",
                    what_i_did=f"Turn {turns} of investigation",
                    what_i_found=turn_text[:500] + "..." if len(turn_text) > 500 else turn_text,
                    interpretation="Continuing analysis...",
                    decision="Continue" if turns < max_turns else "Conclude",
                    reasoning="Agent reasoning step",
                )

                logger.debug(f"Hypothesis {hypothesis_id} turn {turns}: {turn_text[:200]}...")

            elif isinstance(message, ResultMessage):
                # Final result with metrics and structured output
                total_tokens = getattr(message, "total_tokens", 0)
                cost_usd = getattr(message, "total_cost_usd", 0.0)
                turns = getattr(message, "num_turns", turns)

                # Get the structured result directly from the message
                if hasattr(message, "result") and message.result is not None:
                    parsed_result = message.result

                logger.info(
                    f"Hypothesis {hypothesis_id} complete: "
                    f"{turns} turns, {total_tokens} tokens, ${cost_usd:.4f}"
                )

    except Exception as e:
        logger.exception(f"Analysis failed for hypothesis {hypothesis_id}: {e}")
        parsed_result = HypothesisOutcome(
            outcome="RULED_OUT",
            evidence=f"Analysis failed: {str(e)}",
            confidence="LOW",
            key_metrics=[],
        )

    # Finalize logs
    session_log.finalize_session_log_md(
        md_path,
        outcome=parsed_result.outcome,
        evidence=parsed_result.evidence,
        confidence=parsed_result.confidence,
        key_metrics=parsed_result.key_metrics,
    )

    session_log.update_session_log_json(
        json_path,
        outcome=parsed_result.outcome,
        turns=turns,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        key_findings=parsed_result.key_metrics,
        scripts_created=scripts_created,
    )

    end_time = datetime.now(timezone.utc)

    # Build SessionLog
    log_entry: SessionLog = {
        "hypothesis_id": hypothesis_id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "outcome": parsed_result.outcome,
        "turns": turns,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "key_findings": parsed_result.key_metrics,
        "scripts_created": scripts_created,
        "artifacts_created": [],
    }

    # Build Finding
    finding = Finding(
        finding_id=f"F{hypothesis_id}",
        hypothesis_id=hypothesis_id,
        outcome=parsed_result.outcome,
        evidence=parsed_result.evidence,
        confidence=parsed_result.confidence,
        key_metrics=parsed_result.key_metrics,
        session_log_ref=session_log.get_session_log_ref(json_path, session_path),
        completed_at=end_time.isoformat(),
    )

    return log_entry, finding


async def analysis_execution(state: InvestigationState) -> dict:
    """Execute hypothesis investigations using Claude Agent SDK orchestrator.

    This node:
    1. Retrieves files from storage to analysis directory
    2. Iterates through each hypothesis
    3. Runs Claude Agent SDK query() for each hypothesis
    4. Records findings to the ledger
    5. Updates session logs

    Args:
        state: Current investigation state

    Returns:
        Updated state with findings_ledger and session_logs
    """
    session_id = state["session_id"]
    logger.info(f"Starting analysis execution for session {session_id}")

    # Get session path
    sessions_root = os.environ.get("SESSION_STORAGE_PATH", "./sessions")
    session_path = Path(sessions_root) / session_id

    # Initialize findings ledger
    findings_ledger.initialize_findings_ledger(session_path)
    progress_log.log_investigation_start(session_path)

    # Prepare analysis directory with files
    analysis_files_dir = session_path / "analysis" / "files"
    analysis_files_dir.mkdir(parents=True, exist_ok=True)

    # Copy files to analysis directory (keeps originals untouched)
    copied_files = await mcp_client.copy_files_to_analysis_dir(
        session_id, str(analysis_files_dir)
    )

    if not copied_files:
        # Fall back to using files from state
        files = state.get("files", [])
        copied_files = [f["path"] for f in files if f.get("path")]

    # Build schema summary
    schema_summary = _build_schema_summary(state)

    # Get file list for prompts
    file_names = [Path(f).name for f in copied_files]

    # Process each hypothesis
    hypotheses = state.get("hypotheses", [])
    updated_hypotheses = []
    all_findings = []
    all_session_logs = []

    for hypothesis in hypotheses:
        hypothesis_id = hypothesis["id"]
        title = hypothesis["title"]

        logger.info(f"Investigating hypothesis {hypothesis_id}: {title}")
        progress_log.log_hypothesis_start(session_path, hypothesis_id, title)

        # Update hypothesis status
        hypothesis["status"] = "INVESTIGATING"

        # Build prompt
        prompt = _build_hypothesis_prompt(state, hypothesis, file_names, schema_summary)

        # Run investigation
        try:
            log_entry, finding = await _investigate_hypothesis_with_sdk(
                session_path, hypothesis, prompt, state
            )

            # Update hypothesis status based on outcome
            hypothesis["status"] = finding["outcome"]

            # Add to ledger
            findings_ledger.add_finding_to_ledger(session_path, finding)

            all_findings.append(finding)
            all_session_logs.append(log_entry)

            progress_log.log_hypothesis_complete(
                session_path, hypothesis_id, title, finding["outcome"]
            )

        except Exception as e:
            logger.exception(f"Failed to investigate hypothesis {hypothesis_id}: {e}")
            hypothesis["status"] = "RULED_OUT"
            progress_log.log_error(session_path, f"Investigation of {hypothesis_id} failed: {e}")

        updated_hypotheses.append(hypothesis)

    # Log completion
    confirmed_count = sum(1 for f in all_findings if f["outcome"] == "CONFIRMED")
    progress_log.log_investigation_complete(session_path, confirmed_count, len(updated_hypotheses))

    logger.info(
        f"Analysis execution complete: {confirmed_count}/{len(updated_hypotheses)} confirmed"
    )

    return {
        "hypotheses": updated_hypotheses,
        "findings_ledger": all_findings,
        "session_logs": all_session_logs,
    }
