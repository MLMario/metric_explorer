"""Shared configuration module for Metric Drill-Down Agent.

This module provides centralized configuration management using environment
variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default."""
    return os.environ.get(key, default)


def get_env_required(key: str) -> str:
    """Get required environment variable, raises if not set."""
    value = os.environ.get(key)
    if value is None:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def get_env_int(key: str, default: int) -> int:
    """Get environment variable as integer."""
    value = os.environ.get(key)
    if value is None:
        return default
    return int(value)


def get_env_float(key: str, default: float) -> float:
    """Get environment variable as float."""
    value = os.environ.get(key)
    if value is None:
        return default
    return float(value)


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    value = os.environ.get(key, "").lower()
    if not value:
        return default
    return value in ("true", "1", "yes", "on")


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SESSIONS_PATH = Path(get_env("SESSION_STORAGE_PATH", str(PROJECT_ROOT / "sessions")))

# Session configuration
SESSION_TIMEOUT_HOURS = get_env_int("SESSION_TIMEOUT_HOURS", 24)
MAX_FILE_SIZE_MB = get_env_int("MAX_FILE_SIZE_MB", 50)
MAX_FILES_PER_SESSION = get_env_int("MAX_FILES_PER_SESSION", 10)

# Backend configuration
BACKEND_HOST = get_env("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = get_env_int("BACKEND_PORT", 8000)

# Frontend configuration
FRONTEND_PORT = get_env_int("FRONTEND_PORT", 3000)
BACKEND_URL = get_env("BACKEND_URL", f"http://localhost:{BACKEND_PORT}")

# LLM configuration
ANTHROPIC_API_KEY = get_env("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = get_env("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
LLM_MAX_RETRIES = get_env_int("LLM_MAX_RETRIES", 3)
LLM_INITIAL_DELAY = get_env_float("LLM_INITIAL_DELAY", 1.0)
LLM_BACKOFF_MULTIPLIER = get_env_float("LLM_BACKOFF_MULTIPLIER", 2.0)
ANALYSIS_MAX_TURNS = get_env_int("ANALYSIS_MAX_TURNS", 10)

# Supabase configuration
SUPABASE_URL = get_env("SUPABASE_URL")
SUPABASE_ANON_KEY = get_env("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = get_env("SUPABASE_SERVICE_KEY")

# Logging
LOG_LEVEL = get_env("LOG_LEVEL", "INFO")
