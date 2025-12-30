"""Session storage directory manager."""

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from ..config import settings
from ..models.errors import SessionNotFoundError


SessionStatus = Literal["created", "has_files", "running", "completed", "failed", "expired"]


class SessionMetadata:
    """Session metadata structure."""

    def __init__(
        self,
        session_id: UUID,
        status: SessionStatus,
        created_at: datetime,
        expires_at: datetime,
        file_count: int = 0,
        report_ready: bool = False,
    ):
        self.session_id = session_id
        self.status = status
        self.created_at = created_at
        self.expires_at = expires_at
        self.file_count = file_count
        self.report_ready = report_ready

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": str(self.session_id),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "file_count": self.file_count,
            "report_ready": self.report_ready,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionMetadata":
        """Create from dictionary."""
        return cls(
            session_id=UUID(data["session_id"]),
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            file_count=data.get("file_count", 0),
            report_ready=data.get("report_ready", False),
        )


class SessionManager:
    """Manages session storage directories."""

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or settings.SESSIONS_PATH
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: UUID) -> Path:
        """Get path to session directory."""
        return self.base_path / str(session_id)

    def _metadata_path(self, session_id: UUID) -> Path:
        """Get path to session metadata file."""
        return self._session_path(session_id) / "metadata.json"

    def create_session(self) -> SessionMetadata:
        """Create a new session with directory structure."""
        session_id = uuid4()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=settings.SESSION_TIMEOUT_HOURS)

        session_path = self._session_path(session_id)
        session_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (session_path / "files").mkdir(exist_ok=True)
        (session_path / "analysis").mkdir(exist_ok=True)
        (session_path / "analysis" / "scripts").mkdir(exist_ok=True)
        (session_path / "analysis" / "logs").mkdir(exist_ok=True)
        (session_path / "analysis" / "artifacts").mkdir(exist_ok=True)
        (session_path / "results").mkdir(exist_ok=True)
        (session_path / "chat").mkdir(exist_ok=True)

        metadata = SessionMetadata(
            session_id=session_id,
            status="created",
            created_at=now,
            expires_at=expires_at,
        )

        self._save_metadata(metadata)
        return metadata

    def get_session(self, session_id: UUID) -> SessionMetadata:
        """Get session metadata. Raises SessionNotFoundError if not found."""
        metadata_path = self._metadata_path(session_id)
        if not metadata_path.exists():
            raise SessionNotFoundError(str(session_id))

        with open(metadata_path) as f:
            data = json.load(f)

        metadata = SessionMetadata.from_dict(data)

        # Check if expired
        if datetime.now(timezone.utc) > metadata.expires_at:
            metadata.status = "expired"
            self._save_metadata(metadata)

        return metadata

    def update_session(
        self,
        session_id: UUID,
        status: SessionStatus | None = None,
        file_count: int | None = None,
        report_ready: bool | None = None,
    ) -> SessionMetadata:
        """Update session metadata."""
        metadata = self.get_session(session_id)

        if status is not None:
            metadata.status = status
        if file_count is not None:
            metadata.file_count = file_count
        if report_ready is not None:
            metadata.report_ready = report_ready

        self._save_metadata(metadata)
        return metadata

    def delete_session(self, session_id: UUID) -> bool:
        """Delete a session and all its data."""
        session_path = self._session_path(session_id)
        if not session_path.exists():
            raise SessionNotFoundError(str(session_id))

        shutil.rmtree(session_path)
        return True

    def session_exists(self, session_id: UUID) -> bool:
        """Check if session exists."""
        return self._metadata_path(session_id).exists()

    def get_session_path(self, session_id: UUID) -> Path:
        """Get the session directory path."""
        if not self.session_exists(session_id):
            raise SessionNotFoundError(str(session_id))
        return self._session_path(session_id)

    def get_files_path(self, session_id: UUID) -> Path:
        """Get the files directory path for a session."""
        return self.get_session_path(session_id) / "files"

    def count_files(self, session_id: UUID) -> int:
        """Count CSV files in session."""
        files_path = self.get_files_path(session_id)
        return len(list(files_path.glob("*.csv")))

    def cleanup_expired_sessions(self) -> int:
        """Delete all expired sessions. Returns count of deleted sessions."""
        deleted = 0
        for session_dir in self.base_path.iterdir():
            if not session_dir.is_dir():
                continue
            try:
                session_id = UUID(session_dir.name)
                metadata = self.get_session(session_id)
                if metadata.status == "expired":
                    self.delete_session(session_id)
                    deleted += 1
            except (ValueError, SessionNotFoundError):
                # Invalid session directory or already deleted
                continue
        return deleted

    def _save_metadata(self, metadata: SessionMetadata) -> None:
        """Save session metadata to file."""
        metadata_path = self._metadata_path(metadata.session_id)
        with open(metadata_path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)


# Global session manager instance
session_manager = SessionManager()
