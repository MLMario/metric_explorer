"""CSV tools for reading file metadata and samples.

These tools are used during schema inference to analyze uploaded CSV files
without loading the entire dataset into memory.
"""

import csv
import random
from pathlib import Path
from typing import Any


class CSVToolError(Exception):
    """Base error for CSV tool operations."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class FileNotFoundError(CSVToolError):
    """File does not exist."""

    def __init__(self, file_path: str):
        super().__init__(
            code="FILE_NOT_FOUND",
            message=f"File not found: {file_path}",
            details={"file_path": file_path},
        )


class InvalidCSVError(CSVToolError):
    """File is not valid CSV."""

    def __init__(self, file_path: str, reason: str):
        super().__init__(
            code="INVALID_CSV",
            message=f"Invalid CSV file: {reason}",
            details={"file_path": file_path, "reason": reason},
        )


class NoHeadersError(CSVToolError):
    """CSV file appears to have no headers."""

    def __init__(self, file_path: str):
        super().__init__(
            code="NO_HEADERS",
            message="CSV file must have a header row",
            details={"file_path": file_path},
        )


def get_headers(file_path: str) -> list[str]:
    """Read column headers from a CSV file.

    Args:
        file_path: Absolute path to CSV file

    Returns:
        List of column header names

    Raises:
        FileNotFoundError: File does not exist
        InvalidCSVError: File is not valid CSV
        NoHeadersError: File appears to have no headers
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(file_path)

    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)

            if not headers:
                raise NoHeadersError(file_path)

            # Check for empty headers
            if all(h.strip() == "" for h in headers):
                raise NoHeadersError(file_path)

            return [h.strip() for h in headers]
    except csv.Error as e:
        raise InvalidCSVError(file_path, str(e))
    except UnicodeDecodeError as e:
        raise InvalidCSVError(file_path, f"Encoding error: {e}")


def sample_rows(
    file_path: str,
    n: int = 100,
    random_seed: int | None = None,
) -> list[dict[str, Any]]:
    """Get a sample of rows from a CSV file for schema inference.

    Args:
        file_path: Absolute path to CSV file
        n: Number of rows to sample (default: 100)
        random_seed: Optional seed for reproducible sampling

    Returns:
        List of row dictionaries with header keys

    Behavior:
        - If file has <= n rows, returns all rows
        - If file has > n rows, samples randomly
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(file_path)

    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Read all rows into memory for sampling
            # For very large files, consider reservoir sampling
            all_rows = list(reader)

            if len(all_rows) <= n:
                return all_rows

            # Random sample
            if random_seed is not None:
                random.seed(random_seed)

            return random.sample(all_rows, n)
    except csv.Error as e:
        raise InvalidCSVError(file_path, str(e))
    except UnicodeDecodeError as e:
        raise InvalidCSVError(file_path, f"Encoding error: {e}")


def get_row_count(file_path: str) -> int:
    """Count total rows in a CSV file (excluding header).

    Args:
        file_path: Absolute path to CSV file

    Returns:
        Number of data rows
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(file_path)

    try:
        with open(path, newline="", encoding="utf-8") as f:
            # Skip header
            next(f, None)
            # Count remaining lines
            return sum(1 for _ in f)
    except UnicodeDecodeError as e:
        raise InvalidCSVError(file_path, f"Encoding error: {e}")


def infer_column_type(values: list[str]) -> str:
    """Infer the data type from a sample of values.

    Args:
        values: List of string values from a column

    Returns:
        Inferred type: 'integer', 'float', 'date', 'datetime', or 'string'
    """
    # Filter out empty/null values
    non_empty = [v for v in values if v and v.strip()]
    if not non_empty:
        return "string"

    # Try integer
    try:
        for v in non_empty[:20]:
            int(v.replace(",", ""))
        return "integer"
    except ValueError:
        pass

    # Try float
    try:
        for v in non_empty[:20]:
            float(v.replace(",", ""))
        return "float"
    except ValueError:
        pass

    # Try date patterns
    import re

    date_patterns = [
        r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
        r"^\d{2}/\d{2}/\d{4}$",  # MM/DD/YYYY
        r"^\d{2}-\d{2}-\d{4}$",  # DD-MM-YYYY
    ]
    datetime_patterns = [
        r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}",  # ISO datetime
    ]

    sample = non_empty[:10]
    for pattern in datetime_patterns:
        if all(re.match(pattern, v) for v in sample):
            return "datetime"
    for pattern in date_patterns:
        if all(re.match(pattern, v) for v in sample):
            return "date"

    return "string"


def get_column_cardinality(file_path: str, column: str, sample_size: int = 1000) -> int:
    """Estimate cardinality (unique value count) for a column.

    Args:
        file_path: Absolute path to CSV file
        column: Column name
        sample_size: Number of rows to sample

    Returns:
        Estimated unique value count
    """
    rows = sample_rows(file_path, n=sample_size)
    values = [row.get(column, "") for row in rows]
    return len(set(values))
