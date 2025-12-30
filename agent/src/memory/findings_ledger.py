"""Findings ledger for tracking investigation findings.

The findings ledger is incrementally built as each hypothesis investigation
completes. It stores all findings that will be used for report generation.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..state import Finding

logger = logging.getLogger(__name__)


def get_ledger_path(session_path: str | Path) -> Path:
    """Get the path to the findings ledger file."""
    return Path(session_path) / "analysis" / "findings_ledger.json"


def initialize_findings_ledger(session_path: str | Path) -> None:
    """Initialize an empty findings ledger.

    Args:
        session_path: Path to the session directory
    """
    ledger_path = get_ledger_path(session_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    initial_ledger = {
        "session_id": Path(session_path).name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "findings": [],
        "summary": {
            "total_hypotheses": 0,
            "confirmed": 0,
            "ruled_out": 0,
            "pending": 0,
        },
    }

    with open(ledger_path, "w") as f:
        json.dump(initial_ledger, f, indent=2)

    logger.debug(f"Initialized findings ledger at {ledger_path}")


def read_findings_ledger(session_path: str | Path) -> dict[str, Any]:
    """Read the findings ledger.

    Args:
        session_path: Path to the session directory

    Returns:
        Ledger data as a dictionary
    """
    ledger_path = get_ledger_path(session_path)

    if not ledger_path.exists():
        initialize_findings_ledger(session_path)

    with open(ledger_path, "r") as f:
        return json.load(f)


def add_finding_to_ledger(session_path: str | Path, finding: Finding) -> None:
    """Add a finding to the ledger (incremental update).

    Args:
        session_path: Path to the session directory
        finding: Finding to add
    """
    ledger = read_findings_ledger(session_path)

    # Add the finding
    ledger["findings"].append(dict(finding))

    # Update summary
    summary = ledger["summary"]
    summary["total_hypotheses"] = len(ledger["findings"])
    summary["confirmed"] = sum(
        1 for f in ledger["findings"] if f.get("outcome") == "CONFIRMED"
    )
    summary["ruled_out"] = sum(
        1 for f in ledger["findings"] if f.get("outcome") == "RULED_OUT"
    )
    summary["pending"] = summary["total_hypotheses"] - summary["confirmed"] - summary["ruled_out"]

    # Update timestamp
    ledger["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Save
    ledger_path = get_ledger_path(session_path)
    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2)

    logger.debug(
        f"Added finding {finding['finding_id']} to ledger "
        f"(total: {summary['total_hypotheses']})"
    )


def get_confirmed_findings(session_path: str | Path) -> list[Finding]:
    """Get all confirmed findings from the ledger.

    Args:
        session_path: Path to the session directory

    Returns:
        List of confirmed findings
    """
    ledger = read_findings_ledger(session_path)
    return [f for f in ledger["findings"] if f.get("outcome") == "CONFIRMED"]


def get_all_findings(session_path: str | Path) -> list[Finding]:
    """Get all findings from the ledger.

    Args:
        session_path: Path to the session directory

    Returns:
        List of all findings
    """
    ledger = read_findings_ledger(session_path)
    return ledger.get("findings", [])
