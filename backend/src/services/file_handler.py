"""CSV file validation and storage handler."""

import csv
import json
from io import StringIO
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from ..config import settings
from ..models.errors import (
    FileTooLargeError,
    InvalidFileTypeError,
    MaxFilesExceededError,
    NoHeadersError,
)
from .session_manager import session_manager


class FileMetadata:
    """File metadata structure."""

    def __init__(
        self,
        file_id: UUID,
        original_name: str,
        description: str,
        row_count: int,
        size_bytes: int,
        headers: list[str],
    ):
        self.file_id = file_id
        self.original_name = original_name
        self.description = description
        self.row_count = row_count
        self.size_bytes = size_bytes
        self.headers = headers

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_id": str(self.file_id),
            "original_name": self.original_name,
            "description": self.description,
            "row_count": self.row_count,
            "size_bytes": self.size_bytes,
            "headers": self.headers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FileMetadata":
        """Create from dictionary."""
        return cls(
            file_id=UUID(data["file_id"]),
            original_name=data["original_name"],
            description=data["description"],
            row_count=data["row_count"],
            size_bytes=data["size_bytes"],
            headers=data["headers"],
        )


class FileHandler:
    """Handles CSV file validation and storage."""

    def validate_file_type(self, filename: str) -> None:
        """Validate file is a CSV. Raises InvalidFileTypeError if not."""
        if not filename.lower().endswith(".csv"):
            raise InvalidFileTypeError()

    def validate_file_size(self, content: bytes) -> None:
        """Validate file size. Raises FileTooLargeError if too large."""
        if len(content) > settings.MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(settings.MAX_FILE_SIZE_MB)

    def validate_max_files(self, session_id: UUID) -> None:
        """Validate session hasn't exceeded max files. Raises MaxFilesExceededError if exceeded."""
        current_count = session_manager.count_files(session_id)
        if current_count >= settings.MAX_FILES_PER_SESSION:
            raise MaxFilesExceededError(settings.MAX_FILES_PER_SESSION)

    def validate_csv_headers(self, content: bytes) -> list[str]:
        """
        Validate CSV has headers and return them.
        Raises NoHeadersError if no headers detected.
        """
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except UnicodeDecodeError:
                raise NoHeadersError()

        reader = csv.reader(StringIO(text))
        try:
            headers = next(reader)
        except StopIteration:
            raise NoHeadersError()

        if not headers or all(h.strip() == "" for h in headers):
            raise NoHeadersError()

        return [h.strip() for h in headers]

    def count_rows(self, content: bytes) -> int:
        """Count data rows in CSV (excluding header)."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        reader = csv.reader(StringIO(text))
        next(reader, None)  # Skip header
        return sum(1 for _ in reader)

    async def save_file(
        self,
        session_id: UUID,
        filename: str,
        content: bytes,
        description: str,
    ) -> FileMetadata:
        """
        Validate and save a CSV file to the session.
        Returns FileMetadata on success.
        Raises various errors on validation failure.
        """
        # Validate
        self.validate_file_type(filename)
        self.validate_file_size(content)
        self.validate_max_files(session_id)
        headers = self.validate_csv_headers(content)
        row_count = self.count_rows(content)

        # Generate file ID and save
        file_id = uuid4()
        files_path = session_manager.get_files_path(session_id)

        # Save CSV file
        csv_path = files_path / f"{file_id}.csv"
        with open(csv_path, "wb") as f:
            f.write(content)

        # Create and save metadata
        metadata = FileMetadata(
            file_id=file_id,
            original_name=filename,
            description=description,
            row_count=row_count,
            size_bytes=len(content),
            headers=headers,
        )

        meta_path = files_path / f"{file_id}_meta.json"
        with open(meta_path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        # Update session file count and status
        new_count = session_manager.count_files(session_id)
        session_manager.update_session(
            session_id,
            file_count=new_count,
            status="has_files" if new_count > 0 else "created",
        )

        return metadata

    def get_file_metadata(self, session_id: UUID, file_id: UUID) -> FileMetadata | None:
        """Get file metadata. Returns None if not found."""
        files_path = session_manager.get_files_path(session_id)
        meta_path = files_path / f"{file_id}_meta.json"

        if not meta_path.exists():
            return None

        with open(meta_path) as f:
            data = json.load(f)

        return FileMetadata.from_dict(data)

    def update_file_description(
        self, session_id: UUID, file_id: UUID, description: str
    ) -> FileMetadata | None:
        """Update file description. Returns updated metadata or None if not found."""
        metadata = self.get_file_metadata(session_id, file_id)
        if metadata is None:
            return None

        metadata.description = description

        files_path = session_manager.get_files_path(session_id)
        meta_path = files_path / f"{file_id}_meta.json"
        with open(meta_path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        return metadata

    def delete_file(self, session_id: UUID, file_id: UUID) -> bool:
        """Delete a file from the session. Returns True if deleted, False if not found."""
        files_path = session_manager.get_files_path(session_id)

        csv_path = files_path / f"{file_id}.csv"
        meta_path = files_path / f"{file_id}_meta.json"

        if not csv_path.exists():
            return False

        csv_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

        # Update session file count and status
        new_count = session_manager.count_files(session_id)
        session_manager.update_session(
            session_id,
            file_count=new_count,
            status="has_files" if new_count > 0 else "created",
        )

        return True

    def list_files(self, session_id: UUID) -> list[FileMetadata]:
        """List all files in a session."""
        files_path = session_manager.get_files_path(session_id)
        files = []

        for meta_path in files_path.glob("*_meta.json"):
            with open(meta_path) as f:
                data = json.load(f)
            files.append(FileMetadata.from_dict(data))

        return files


# Global file handler instance
file_handler = FileHandler()
