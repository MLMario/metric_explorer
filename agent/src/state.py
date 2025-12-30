"""Agent state types for the investigation workflow.

This module defines all TypedDict types used in the LangGraph state machine
for the Metric Drill-Down Agent.
"""

from operator import add
from typing import Annotated, Literal, TypedDict


class FileInfo(TypedDict):
    """Information about an uploaded CSV file."""

    file_id: str
    name: str
    path: str
    description: str
    schema: dict | None  # {columns: [{name, type, cardinality}]}


class DateRange(TypedDict):
    """Date range for baseline/comparison periods."""

    start: str  # ISO date
    end: str


class ColumnSchema(TypedDict):
    """Schema for a single column."""

    name: str
    inferred_type: Literal["dimension", "measure", "id", "timestamp"]
    data_type: str  # string, integer, float, date, datetime
    cardinality: int
    sample_values: list[str]
    nullable: bool


class TableInfo(TypedDict):
    """Summary info for a table/file."""

    file_id: str
    name: str
    row_count: int
    column_count: int
    columns: list[ColumnSchema]


class Relationship(TypedDict):
    """Detected relationship between tables."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relationship_type: Literal["foreign_key", "similar_values"]
    confidence: float


class DataModel(TypedDict):
    """Inferred data model from schema inference."""

    tables: list[TableInfo]
    relationships: list[Relationship]
    recommended_dimensions: list[str]


class MetricRequirements(TypedDict):
    """Validation result from metric_identification node."""

    target_metric: str  # Column name user wants to analyze
    source_file: dict | None  # {file_id, file_name} where column was found
    validated: bool
    error_message: str | None


class Hypothesis(TypedDict):
    """A potential explanation for the metric movement."""

    id: str
    title: str
    causal_story: str
    dimensions: list[str]
    expected_pattern: str
    priority: int  # 1 = most plausible
    status: Literal["PENDING", "INVESTIGATING", "CONFIRMED", "RULED_OUT"]


class Finding(TypedDict):
    """Finding from a completed hypothesis investigation."""

    finding_id: str
    hypothesis_id: str
    outcome: Literal["CONFIRMED", "RULED_OUT"]
    evidence: str  # Key evidence supporting the conclusion
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    key_metrics: list[str]  # Key numbers discovered
    session_log_ref: str  # Path to session log JSON
    completed_at: str


class SessionLog(TypedDict):
    """Log of a single hypothesis investigation session."""

    hypothesis_id: str
    start_time: str
    end_time: str
    outcome: Literal["CONFIRMED", "RULED_OUT"]
    turns: int  # Number of query() turns
    total_tokens: int
    cost_usd: float
    key_findings: list[str]
    scripts_created: list[str]
    artifacts_created: list[str]


class Evidence(TypedDict):
    """Evidence supporting an explanation."""

    metric: str
    value: str
    interpretation: str


class Explanation(TypedDict):
    """A ranked explanation for the metric movement."""

    rank: int
    title: str
    likelihood: Literal["Most Likely", "Likely", "Possible", "Less Likely"]
    evidence: list[Evidence]
    reasoning: str
    causal_story: str
    source_hypotheses: list[str]


class InvestigationState(TypedDict):
    """Full state for the investigation workflow."""

    # Input (set at start)
    session_id: str
    files: list[FileInfo]
    business_context: str
    target_metric: str  # Column name to analyze (MUST exist in CSV)
    metric_definition: str  # Text description of how metric is calculated
    baseline_period: DateRange
    comparison_period: DateRange
    investigation_prompt: str | None

    # Schema Inference Output
    data_model: DataModel | None
    selected_dimensions: list[str] | None

    # Metric Identification Output
    metric_requirements: MetricRequirements | None

    # Hypothesis Generation Output
    hypotheses: Annotated[list[Hypothesis], add]

    # Analysis Execution Output (Python orchestrator + Claude Agent SDK)
    findings_ledger: Annotated[list[Finding], add]
    session_logs: Annotated[list[SessionLog], add]

    # Final Output
    explanations: list[Explanation] | None
    report_path: str | None
    memory_document_id: str | None  # Supabase document ID for RAG

    # Control
    status: Literal["running", "completed", "failed", "no_findings"]
    error: str | None
