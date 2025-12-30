"""Progress log for human-readable investigation tracking.

The progress log is a simple text file that records high-level
investigation milestones in a human-readable format.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def get_progress_path(session_path: str | Path) -> Path:
    """Get the path to the progress log file."""
    return Path(session_path) / "analysis" / "progress.txt"


def initialize_progress_log(session_path: str | Path) -> None:
    """Initialize the progress log file.

    Args:
        session_path: Path to the session directory
    """
    progress_path = get_progress_path(session_path)
    progress_path.parent.mkdir(parents=True, exist_ok=True)

    with open(progress_path, "w") as f:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] Investigation progress log initialized\n")

    logger.debug(f"Initialized progress log at {progress_path}")


def write_progress_log(session_path: str | Path, message: str) -> None:
    """Append a message to the progress log.

    Args:
        session_path: Path to the session directory
        message: Message to log
    """
    progress_path = get_progress_path(session_path)

    # Ensure directory exists
    progress_path.parent.mkdir(parents=True, exist_ok=True)

    # Append message with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with open(progress_path, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

    logger.debug(f"Progress: {message}")


def log_investigation_start(session_path: str | Path) -> None:
    """Log investigation start."""
    write_progress_log(session_path, "Investigation started")


def log_schema_inference_complete(
    session_path: str | Path, table_count: int, dimension_count: int
) -> None:
    """Log schema inference completion."""
    write_progress_log(
        session_path,
        f"Schema inference complete - {table_count} tables, {dimension_count} dimensions identified",
    )


def log_metric_validated(
    session_path: str | Path, metric: str, source_file: str
) -> None:
    """Log metric validation success."""
    write_progress_log(
        session_path, f"Target metric '{metric}' found in {source_file}"
    )


def log_metric_not_found(session_path: str | Path, metric: str) -> None:
    """Log metric validation failure."""
    write_progress_log(
        session_path, f"ERROR: Target metric '{metric}' not found in any file"
    )


def log_hypotheses_generated(session_path: str | Path, count: int) -> None:
    """Log hypothesis generation completion."""
    write_progress_log(session_path, f"Generated {count} hypotheses for investigation")


def log_hypothesis_start(session_path: str | Path, hypothesis_id: str, title: str) -> None:
    """Log start of hypothesis investigation."""
    write_progress_log(session_path, f"Investigating: [{hypothesis_id}] {title}")


def log_hypothesis_complete(
    session_path: str | Path, hypothesis_id: str, title: str, outcome: str
) -> None:
    """Log completion of hypothesis investigation."""
    write_progress_log(
        session_path, f"Completed: [{hypothesis_id}] {title} -> {outcome}"
    )


def log_investigation_complete(
    session_path: str | Path, confirmed_count: int, total_count: int
) -> None:
    """Log investigation completion."""
    write_progress_log(
        session_path,
        f"Investigation complete - {confirmed_count}/{total_count} hypotheses confirmed",
    )


def log_report_generated(session_path: str | Path) -> None:
    """Log report generation."""
    write_progress_log(session_path, "Report generated successfully")


def log_error(session_path: str | Path, error: str) -> None:
    """Log an error."""
    write_progress_log(session_path, f"ERROR: {error}")


def read_progress_log(session_path: str | Path) -> str:
    """Read the full progress log.

    Args:
        session_path: Path to the session directory

    Returns:
        Full progress log content
    """
    progress_path = get_progress_path(session_path)

    if not progress_path.exists():
        return ""

    with open(progress_path, "r") as f:
        return f.read()
