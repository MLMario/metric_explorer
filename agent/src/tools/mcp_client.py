"""Local file utilities for the analysis workflow.

This module provides utilities for working with session files stored locally.
For MVP, files are stored on the local filesystem in the session directory.
Backend and agent share the same filesystem.

Note: Future versions may add Supabase storage integration for distributed
agent execution, but that is out of scope for MVP.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileOperationError(Exception):
    """Base error for file operations."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class FileNotFoundError(FileOperationError):
    """File not found in session directory."""

    def __init__(self, file_id: str, reason: str):
        super().__init__(
            code="FILE_NOT_FOUND",
            message=f"File {file_id} not found: {reason}",
            details={"file_id": file_id, "reason": reason},
        )


class FileCopyError(FileOperationError):
    """File copy operation failed."""

    def __init__(self, reason: str):
        super().__init__(
            code="FILE_COPY_FAILED",
            message=f"Failed to copy files: {reason}",
            details={"reason": reason},
        )


async def list_local_session_files(session_id: str) -> list[dict[str, Any]]:
    """List all files in a session's local directory.

    Reads CSV files from the session's files directory on the local filesystem.
    The backend must have already saved files here before calling this function.

    Args:
        session_id: UUID of the session

    Returns:
        List of file info dicts with file_id, name, size_bytes
    """
    session_path = _get_session_path(session_id)
    files_path = session_path / "files"

    if not files_path.exists():
        return []

    files = []
    for csv_file in files_path.glob("*.csv"):
        file_id = csv_file.stem
        # Check if this is the actual file (not a meta file)
        if "_meta" in file_id:
            continue

        meta_file = files_path / f"{file_id}_meta.json"
        name = csv_file.name
        if meta_file.exists():
            import json

            with open(meta_file) as f:
                meta = json.load(f)
                name = meta.get("original_name", csv_file.name)

        files.append(
            {
                "file_id": file_id,
                "name": name,
                "size_bytes": csv_file.stat().st_size,
            }
        )

    return files


async def verify_file_exists(file_path: str) -> bool:
    """Verify that a file exists at the given path.

    Args:
        file_path: Path to the file

    Returns:
        True if file exists, False otherwise
    """
    return Path(file_path).exists()


async def copy_files_to_analysis_dir(
    session_id: str, target_dir: str
) -> list[str]:
    """Copy session files to the analysis working directory.

    Copies CSV files from the session's files directory to the specified
    target directory for analysis. This keeps original files untouched.

    Args:
        session_id: UUID of the session
        target_dir: Directory to copy files to (typically session/analysis/files)

    Returns:
        List of copied file paths
    """
    session_path = _get_session_path(session_id)
    source_dir = session_path / "files"
    target_path = Path(target_dir)

    # Create target directory
    target_path.mkdir(parents=True, exist_ok=True)

    if not source_dir.exists():
        logger.warning(f"Source directory does not exist: {source_dir}")
        return []

    copied_files = []
    for csv_file in source_dir.glob("*.csv"):
        # Skip meta files
        if "_meta" in csv_file.stem:
            continue

        dest_file = target_path / csv_file.name
        try:
            shutil.copy2(csv_file, dest_file)
            copied_files.append(str(dest_file))
            logger.debug(f"Copied {csv_file} to {dest_file}")
        except Exception as e:
            logger.error(f"Failed to copy {csv_file}: {e}")

    logger.info(f"Copied {len(copied_files)} files to {target_dir}")
    return copied_files


def _get_session_path(session_id: str) -> Path:
    """Get the session directory path."""
    # Try to get from environment or use default
    sessions_root = os.environ.get("SESSION_STORAGE_PATH", "./sessions")
    return Path(sessions_root) / session_id
