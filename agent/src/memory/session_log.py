"""Session log for per-hypothesis investigation logs.

Each hypothesis investigation gets its own session log that records
the detailed steps, findings, and outcomes.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..state import SessionLog

logger = logging.getLogger(__name__)


def get_logs_dir(session_path: str | Path) -> Path:
    """Get the path to the logs directory."""
    return Path(session_path) / "analysis" / "logs"


def create_session_log(
    session_path: str | Path,
    hypothesis_id: str,
) -> tuple[Path, Path]:
    """Create new session log files (JSON and Markdown).

    Args:
        session_path: Path to the session directory
        hypothesis_id: ID of the hypothesis being investigated

    Returns:
        Tuple of (json_path, md_path)
    """
    logs_dir = get_logs_dir(session_path)
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    base_name = f"session_{hypothesis_id}_{timestamp}"

    json_path = logs_dir / f"{base_name}.json"
    md_path = logs_dir / f"{base_name}.md"

    # Initialize JSON log
    initial_log: SessionLog = {
        "hypothesis_id": hypothesis_id,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": "",
        "outcome": "RULED_OUT",  # Default, will be updated
        "turns": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "key_findings": [],
        "scripts_created": [],
        "artifacts_created": [],
    }

    with open(json_path, "w") as f:
        json.dump(initial_log, f, indent=2)

    # Initialize Markdown log
    with open(md_path, "w") as f:
        f.write(f"# Session Log: {hypothesis_id}\n\n")
        f.write(f"**Started**: {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("---\n\n")

    return json_path, md_path


def update_session_log_json(
    json_path: str | Path,
    outcome: str | None = None,
    turns: int | None = None,
    total_tokens: int | None = None,
    cost_usd: float | None = None,
    key_findings: list[str] | None = None,
    scripts_created: list[str] | None = None,
    artifacts_created: list[str] | None = None,
) -> None:
    """Update the JSON session log.

    Args:
        json_path: Path to the JSON log file
        outcome: Investigation outcome (CONFIRMED/RULED_OUT)
        turns: Number of query turns
        total_tokens: Total tokens used
        cost_usd: Total cost in USD
        key_findings: List of key findings
        scripts_created: List of script paths
        artifacts_created: List of artifact paths
    """
    path = Path(json_path)

    with open(path, "r") as f:
        log_data = json.load(f)

    if outcome is not None:
        log_data["outcome"] = outcome
        log_data["end_time"] = datetime.now(timezone.utc).isoformat()
    if turns is not None:
        log_data["turns"] = turns
    if total_tokens is not None:
        log_data["total_tokens"] = total_tokens
    if cost_usd is not None:
        log_data["cost_usd"] = cost_usd
    if key_findings is not None:
        log_data["key_findings"] = key_findings
    if scripts_created is not None:
        log_data["scripts_created"] = scripts_created
    if artifacts_created is not None:
        log_data["artifacts_created"] = artifacts_created

    with open(path, "w") as f:
        json.dump(log_data, f, indent=2)


def append_session_log_md(
    md_path: str | Path,
    step_number: int,
    action_type: str,
    what_i_did: str,
    what_i_found: str,
    interpretation: str,
    decision: str,
    reasoning: str,
) -> None:
    """Append a step to the Markdown session log.

    Args:
        md_path: Path to the Markdown log file
        step_number: Step number
        action_type: Type of action (Analysis, Script, Interpretation, etc.)
        what_i_did: Description of the action
        what_i_found: Data or results found
        interpretation: What the results mean
        decision: Decision made (continue, pivot, conclude)
        reasoning: Why this decision
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    entry = f"""## [{timestamp}] Step {step_number}: {action_type}

**What I did**: {what_i_did}

**What I found**: {what_i_found}

**My interpretation**: {interpretation}

**Decision**: {decision}

**Reasoning**: {reasoning}

---

"""
    with open(md_path, "a") as f:
        f.write(entry)


def finalize_session_log_md(
    md_path: str | Path,
    outcome: str,
    evidence: str,
    confidence: str,
    key_metrics: list[str],
) -> None:
    """Finalize the Markdown session log with conclusion.

    Args:
        md_path: Path to the Markdown log file
        outcome: CONFIRMED or RULED_OUT
        evidence: Evidence supporting the conclusion
        confidence: HIGH/MEDIUM/LOW
        key_metrics: List of key metrics discovered
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    conclusion = f"""## [{timestamp}] Conclusion

**OUTCOME**: {outcome}

**EVIDENCE**: {evidence}

**CONFIDENCE**: {confidence}

**KEY METRICS**:
"""
    for metric in key_metrics:
        conclusion += f"- {metric}\n"

    conclusion += "\n---\n*Session completed*\n"

    with open(md_path, "a") as f:
        f.write(conclusion)


def read_session_log(session_path: str | Path, hypothesis_id: str) -> dict[str, Any] | None:
    """Read the most recent session log for a hypothesis.

    Args:
        session_path: Path to the session directory
        hypothesis_id: ID of the hypothesis

    Returns:
        Session log data or None if not found
    """
    logs_dir = get_logs_dir(session_path)

    if not logs_dir.exists():
        return None

    # Find matching logs
    pattern = f"session_{hypothesis_id}_*.json"
    matching_logs = sorted(logs_dir.glob(pattern), reverse=True)

    if not matching_logs:
        return None

    # Return most recent
    with open(matching_logs[0], "r") as f:
        return json.load(f)


def get_session_log_ref(json_path: str | Path, session_path: str | Path) -> str:
    """Get a relative reference to the session log.

    Args:
        json_path: Absolute path to JSON log
        session_path: Session directory path

    Returns:
        Relative path suitable for storing in findings
    """
    json_path = Path(json_path)
    session_path = Path(session_path)

    try:
        return str(json_path.relative_to(session_path))
    except ValueError:
        return str(json_path.name)
