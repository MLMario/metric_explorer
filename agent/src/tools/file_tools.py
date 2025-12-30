"""File tools for session artifact management.

These tools manage reading and writing JSON artifacts, markdown reports,
and other files within session directories.
"""

import json
from pathlib import Path
from typing import Any


class FileToolError(Exception):
    """Base error for file tool operations."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class WriteFailedError(FileToolError):
    """File write operation failed."""

    def __init__(self, path: str, reason: str):
        super().__init__(
            code="WRITE_FAILED",
            message=f"Failed to write file: {reason}",
            details={"path": path, "reason": reason},
        )


class JSONDecodeError(FileToolError):
    """File is not valid JSON."""

    def __init__(self, path: str, reason: str):
        super().__init__(
            code="JSON_DECODE_ERROR",
            message=f"Invalid JSON file: {reason}",
            details={"path": path, "reason": reason},
        )


def write_json(
    session_path: str,
    filename: str,
    data: dict[str, Any],
) -> bool:
    """Write a JSON artifact to session storage.

    Args:
        session_path: Path to session directory
        filename: Filename (can include subdirectory, e.g., 'analysis/schema.json')
        data: Data to write

    Returns:
        True if written successfully

    Raises:
        WriteFailedError: If write operation fails
    """
    try:
        path = Path(session_path) / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return True
    except Exception as e:
        raise WriteFailedError(str(path), str(e))


def read_json(
    session_path: str,
    filename: str,
) -> dict[str, Any]:
    """Read a JSON artifact from session storage.

    Args:
        session_path: Path to session directory
        filename: Filename to read

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file does not exist
        JSONDecodeError: If file is not valid JSON
    """
    path = Path(session_path) / filename

    if not path.exists():
        raise FileNotFoundError(str(path))

    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise JSONDecodeError(str(path), str(e))


def write_markdown(
    session_path: str,
    content: str,
    filename: str = "report.md",
) -> str:
    """Write the final report to session storage.

    Args:
        session_path: Path to session directory
        content: Markdown content
        filename: Output filename (default: 'report.md')

    Returns:
        Full path to written file
    """
    try:
        path = Path(session_path) / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(path)
    except Exception as e:
        raise WriteFailedError(str(path), str(e))


def read_markdown(session_path: str, filename: str = "report.md") -> str:
    """Read a markdown file from session storage.

    Args:
        session_path: Path to session directory
        filename: Filename to read

    Returns:
        Markdown content
    """
    path = Path(session_path) / filename

    if not path.exists():
        raise FileNotFoundError(str(path))

    with open(path, encoding="utf-8") as f:
        return f.read()


def list_artifacts(
    session_path: str,
    subdirectory: str | None = None,
    pattern: str = "*",
) -> list[str]:
    """List all artifacts in a session directory.

    Args:
        session_path: Path to session directory
        subdirectory: Limit to subdirectory (e.g., 'analysis/hypotheses')
        pattern: Glob pattern (default: '*')

    Returns:
        List of artifact filenames (relative to subdirectory)
    """
    base_path = Path(session_path)
    if subdirectory:
        base_path = base_path / subdirectory

    if not base_path.exists():
        return []

    return [f.name for f in base_path.glob(pattern) if f.is_file()]


def append_to_file(
    session_path: str,
    filename: str,
    content: str,
) -> bool:
    """Append content to a file.

    Args:
        session_path: Path to session directory
        filename: Filename
        content: Content to append

    Returns:
        True if successful
    """
    try:
        path = Path(session_path) / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(content)

        return True
    except Exception as e:
        raise WriteFailedError(str(path), str(e))


def file_exists(session_path: str, filename: str) -> bool:
    """Check if a file exists in session storage.

    Args:
        session_path: Path to session directory
        filename: Filename to check

    Returns:
        True if file exists
    """
    return (Path(session_path) / filename).exists()
