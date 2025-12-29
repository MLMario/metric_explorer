# Data Model: Metric Drill-Down Agent MVP

**Branch**: `001-metric-drilldown-mvp` | **Date**: 2025-12-17
**Reference**: [spec.md](./spec.md) | [plan.md](./plan.md)

## Overview

This document defines all data entities, their attributes, and relationships for the Metric Drill-Down Agent MVP. Entities are derived from the specification's Key Entities section and the implementation plan's state definitions.

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA MODEL OVERVIEW                                 │
│                 (Claude Agent SDK Orchestrator Architecture)                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│     SESSION     │
│                 │
│  session_id (PK)│
│  status         │
│  created_at     │
│  expires_at     │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐        ┌─────────────────┐
│  UPLOADED_FILE  │        │ INVESTIGATION   │
│                 │        │    CONTEXT      │
│  file_id (PK)   │        │                 │
│  session_id (FK)│        │  session_id (FK)│
│  name           │        │  target_metric  │
│  description    │        │  metric_defn    │
│  schema         │        │  business_ctx   │
│  row_count      │        │  baseline_dates │
│  path           │        │  comparison_dates│
│                 │        │  prompt         │
└────────┬────────┘        └────────┬────────┘
         │                          │
         │ 1:1                      │
         ▼                          │
┌─────────────────┐                 │
│   FILE_SCHEMA   │                 │
│                 │                 │
│  columns[]      │                 │
│  types[]        │                 │
│  cardinalities[]│                 │
└─────────────────┘                 │
                                    │
┌───────────────────────────────────┘
│
│  Referenced by Analysis
▼
┌─────────────────┐        ┌─────────────────┐
│   DATA_MODEL    │        │METRIC_REQUIREMENTS│
│   (Inferred)    │        │                 │
│                 │        │  session_id (FK)│
│  session_id (FK)│        │  target_metric  │
│  tables[]       │        │  source_file    │
│  relationships[]│        │  validated      │
│  dimensions[]   │        │  error_message  │
└────────┬────────┘        └────────┬────────┘
         │                          │
         │                          │ (if validated)
         │                          ▼
         │                 ┌─────────────────┐
         │                 │   HYPOTHESIS    │
         │                 │                 │
         │                 │  hypothesis_id  │
         │                 │  session_id (FK)│
         │                 │  title          │
         │                 │  causal_story   │
         │                 │  dimensions[]   │
         │                 │  expected_pattern│
         │                 │  priority       │
         │                 │  status (enum)  │  ← PENDING/INVESTIGATING/
         │                 └────────┬────────┘    CONFIRMED/RULED_OUT
         │                          │
         │                          │ Referenced by
         │                          ▼
         │                 ┌─────────────────┐        ┌─────────────────┐
         │                 │    FINDING      │←───────│  SESSION_LOG    │
         │                 │ (per hypothesis)│  1:1   │                 │
         │                 │                 │        │  hypothesis_id  │
         │                 │  finding_id     │        │  start_time     │
         │                 │  hypothesis_id  │        │  end_time       │
         │                 │  outcome        │        │  outcome        │
         │                 │  evidence       │        │  turns          │
         │                 │  confidence     │        │  key_findings   │
         │                 │  session_log_ref│        │  scripts_created│
         │                 └────────┬────────┘        └─────────────────┘
         │                          │
         └──────────────────────────┤
                                    │ Aggregated into
                                    ▼
                           ┌─────────────────┐
                           │ FINDINGS_LEDGER │
                           │                 │
                           │  session_id (FK)│
                           │  findings[]     │
                           │  created_at     │
                           └────────┬────────┘
                                    │
                                    │ Compiled into
                                    ▼
                           ┌─────────────────┐
                           │  EXPLANATION    │
                           │                 │
                           │  session_id (FK)│
                           │  rank           │
                           │  title          │
                           │  likelihood     │
                           │  evidence[]     │
                           │  reasoning      │
                           │  causal_story   │
                           └────────┬────────┘
                                    │
                                    │ Compiled into
                                    ▼
                           ┌─────────────────┐
                           │     REPORT      │
                           │                 │
                           │  session_id (FK)│
                           │  content (md)   │
                           │  generated_at   │
                           └────────┬────────┘
                                    │
                           ┌────────┴────────┐
                           │                 │
                           ▼                 ▼
                  ┌─────────────────┐  ┌─────────────────┐
                  │ MEMORY_DOCUMENT │  │  CHAT_MESSAGE   │
                  │   (Supabase)    │  │                 │
                  │                 │  │  message_id     │
                  │  document_id    │  │  session_id (FK)│
                  │  session_id     │  │  role           │
                  │  content        │  │  content        │
                  │  embedding[]    │  │  timestamp      │
                  │  created_at     │  │  artifacts_ref[]│
                  └─────────────────┘  └─────────────────┘
                          ↑                     │
                          │                     │
                          └─────────────────────┘
                            RAG retrieval for Q&A
```

---

## Entity Specifications

### Session

Represents a single investigation session. Root entity for all session-scoped data.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `session_id` | `string (UUID)` | PK, Required | Unique identifier for the session |
| `status` | `enum` | Required | Current state: `created`, `has_files`, `running`, `completed`, `failed`, `expired` |
| `created_at` | `datetime (ISO)` | Required | Session creation timestamp |
| `expires_at` | `datetime (ISO)` | Required | Calculated: `created_at + SESSION_TIMEOUT_HOURS` |
| `file_count` | `integer` | >= 0 | Number of uploaded files |
| `report_ready` | `boolean` | Default: false | True when report is generated |

**Status Transitions**:
```
created → has_files (on first file upload)
has_files → running (on investigation start)
running → completed (on successful report generation)
running → failed (on unrecoverable error)
any → expired (on timeout check)
```

**Storage**: `sessions/{session_id}/metadata.json`

---

### UploadedFile

A CSV file provided by the user with its metadata.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `file_id` | `string (UUID)` | PK, Required | Unique identifier for the file |
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `original_name` | `string` | Required, max 255 | Original filename (e.g., `user_activity.csv`) |
| `description` | `string` | Required, max 2000 | User-provided description of file contents |
| `path` | `string` | Required | Relative path to stored file |
| `row_count` | `integer` | >= 1 | Number of data rows (excluding header) |
| `size_bytes` | `integer` | <= 52428800 | File size (max 50MB) |
| `schema` | `FileSchema` | Optional | Inferred schema (populated after schema inference) |
| `uploaded_at` | `datetime (ISO)` | Required | Upload timestamp |

**Validation Rules**:
- File must have `.csv` extension
- File must have header row
- File size <= 50MB (FR edge case)
- Session can have 1-10 files (FR-001)

**Storage**:
- File: `sessions/{session_id}/files/{file_id}.csv`
- Metadata: `sessions/{session_id}/files/{file_id}_meta.json`

---

### FileSchema

Inferred schema for a single CSV file.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `columns` | `array<Column>` | Required | List of column definitions |

**Column**:

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `name` | `string` | Required | Column header name |
| `inferred_type` | `enum` | Required | `dimension`, `measure`, `id`, `timestamp` |
| `data_type` | `string` | Required | Detected data type: `string`, `integer`, `float`, `date`, `datetime` |
| `cardinality` | `integer` | >= 1 | Estimated unique value count |
| `sample_values` | `array<string>` | max 5 | Representative sample values |
| `nullable` | `boolean` | Required | True if column has null/empty values |

**Storage**: Embedded in `{file_id}_meta.json`

---

### InvestigationContext

User-provided inputs for the investigation.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `target_metric` | `string` | Required, max 100 | Column name to analyze (must exist in CSV files) |
| `metric_definition` | `string` | Required, max 2000 | Text description of how metric is calculated (for LLM context) |
| `business_context` | `string` | Optional, max 5000 | Background information about the metric |
| `baseline_period` | `DateRange` | Required | Reference time period |
| `comparison_period` | `DateRange` | Required | Period being investigated |
| `investigation_prompt` | `string` | Optional, max 2000 | Specific focus areas or suspected causes |
| `submitted_at` | `datetime (ISO)` | Required | When investigation was started |

**DateRange**:

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `start` | `date (ISO)` | Required | Start date (inclusive) |
| `end` | `date (ISO)` | Required | End date (inclusive) |

**Validation Rules**:
- `baseline_period.end` < `comparison_period.start` OR periods can overlap (user choice)
- At least one file must be uploaded before submission (FR-006)
- `target_metric` must be provided (FR-004)
- `target_metric` column must exist in at least one uploaded file (FR-004b)

**Storage**: `sessions/{session_id}/context.json`

---

### DataModel

Inferred relationships between uploaded files.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `tables` | `array<TableInfo>` | Required | Table summaries |
| `relationships` | `array<Relationship>` | Optional | Detected foreign key relationships |
| `recommended_dimensions` | `array<string>` | Required | Columns suitable for segmentation |
| `inferred_at` | `datetime (ISO)` | Required | Schema inference timestamp |

**TableInfo**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `file_id` | `string (UUID)` | Reference to UploadedFile |
| `name` | `string` | Derived table name (from filename) |
| `row_count` | `integer` | Number of rows |
| `column_count` | `integer` | Number of columns |

**Relationship**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `from_table` | `string` | Source table name |
| `from_column` | `string` | Source column |
| `to_table` | `string` | Target table name |
| `to_column` | `string` | Target column |
| `relationship_type` | `string` | `foreign_key`, `similar_values` |
| `confidence` | `float` | 0.0-1.0 confidence score |

**Storage**: `sessions/{session_id}/analysis/schema.json`

---

### MetricRequirements

Validation result from the metric_identification node. Confirms that the user-specified target metric column exists in the uploaded files.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `target_metric` | `string` | Required | Column name user wants to analyze |
| `source_file` | `object` | Optional | {file_id, file_name} where column was found |
| `validated` | `boolean` | Required | True if column was found |
| `error_message` | `string` | Optional | Error details if not validated |
| `created_at` | `datetime (ISO)` | Required | Validation timestamp |

**SourceFile** (when validated=true):

| Attribute | Type | Description |
|-----------|------|-------------|
| `file_id` | `string (UUID)` | Reference to UploadedFile containing this column |
| `file_name` | `string` | Human-readable file name |

**Example (valid)**:
```json
{
  "session_id": "abc-123",
  "target_metric": "dau",
  "source_file": {"file_id": "file-001", "file_name": "user_metrics.csv"},
  "validated": true,
  "error_message": null,
  "created_at": "2025-12-17T10:30:00Z"
}
```

**Example (invalid)**:
```json
{
  "session_id": "abc-123",
  "target_metric": "dau",
  "source_file": null,
  "validated": false,
  "error_message": "Column 'dau' not found in any uploaded file. Available columns: event_date, revenue, session_count, user_id",
  "created_at": "2025-12-17T10:30:00Z"
}
```

**Error State**: When `validated = false`, the investigation exits early with the error message.

**Storage**: `sessions/{session_id}/analysis/metric_requirements.json`

---

### Hypothesis

A potential explanation for the metric movement.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `hypothesis_id` | `string` | PK, Required | Unique ID (e.g., `hyp_001`) |
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `title` | `string` | Required, max 100 | Concise hypothesis title |
| `causal_story` | `string` | Required, max 500 | 1-2 sentence narrative |
| `dimensions` | `array<string>` | Required | Columns to test |
| `expected_pattern` | `string` | Required | What data pattern would validate this |
| `priority` | `integer` | 1-10 | 1 = most plausible |
| `status` | `enum` | Required | `PENDING`, `INVESTIGATING`, `CONFIRMED`, `RULED_OUT` |
| `created_at` | `datetime (ISO)` | Required | Generation timestamp |

**Status Transitions** (Claude Agent SDK Orchestrator):
```
PENDING → INVESTIGATING (when orchestrator starts query() for this hypothesis)
INVESTIGATING → CONFIRMED (when Claude Agent SDK concludes with supporting evidence)
INVESTIGATING → RULED_OUT (when Claude Agent SDK concludes with contradicting evidence)
```

**Storage**: `sessions/{session_id}/analysis/hypotheses.json` (all hypotheses in single file)

---

### Finding

Result from a completed hypothesis investigation session.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `finding_id` | `string` | PK, Required | Unique ID (e.g., `F1`) |
| `hypothesis_id` | `string` | FK → Hypothesis, Required | Which hypothesis was investigated |
| `outcome` | `enum` | Required | `CONFIRMED`, `RULED_OUT` |
| `evidence` | `string` | Required, max 500 | Key evidence supporting the conclusion |
| `confidence` | `enum` | Required | `HIGH`, `MEDIUM`, `LOW` |
| `key_metrics` | `array<string>` | Required | Key numbers discovered |
| `session_log_ref` | `string` | Required | Path to session log JSON |
| `completed_at` | `datetime (ISO)` | Required | Completion timestamp |

**Example**:
```json
{
  "finding_id": "F1",
  "hypothesis_id": "H1",
  "outcome": "CONFIRMED",
  "evidence": "iOS DAU dropped 15.6% while Android +0.2%",
  "confidence": "HIGH",
  "key_metrics": ["iOS DAU: -15.6%", "Android DAU: +0.2%"],
  "session_log_ref": "logs/session_H1_20251229T103045.json",
  "completed_at": "2025-12-29T10:35:12Z"
}
```

**Storage**: Part of `findings_ledger.json`

---

### SessionLog

Log of a single hypothesis investigation session (Claude Agent SDK query()).

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `hypothesis_id` | `string` | PK, Required | Which hypothesis was investigated |
| `start_time` | `datetime (ISO)` | Required | Session start timestamp |
| `end_time` | `datetime (ISO)` | Required | Session end timestamp |
| `outcome` | `enum` | Required | `CONFIRMED`, `RULED_OUT` |
| `turns` | `integer` | Required | Number of query() turns |
| `total_tokens` | `integer` | Required | Total tokens used |
| `cost_usd` | `float` | Required | Total cost in USD |
| `key_findings` | `array<string>` | Required | Key findings discovered |
| `scripts_created` | `array<string>` | Required | Python scripts written |
| `artifacts_created` | `array<string>` | Required | Output files created |

**Example**:
```json
{
  "hypothesis_id": "H1",
  "start_time": "2025-12-29T10:30:46Z",
  "end_time": "2025-12-29T10:35:12Z",
  "outcome": "CONFIRMED",
  "turns": 7,
  "total_tokens": 15420,
  "cost_usd": 0.046,
  "key_findings": [
    "iOS DAU: 45K → 38K (-15.6%)",
    "Android DAU: 38K → 38.5K (+0.2%)",
    "iOS v17.2.1 has 90% of iOS decline"
  ],
  "scripts_created": ["001_device_analysis.py"],
  "artifacts_created": ["device_breakdown.csv"]
}
```

**Storage**: `sessions/{session_id}/analysis/logs/session_{hypothesis_id}_{timestamp}.json`

---

### ProgressLog

High-level investigation log file (human-readable).

| Attribute | Type | Description |
|-----------|------|-------------|
| content | `string (plain text)` | Timestamped log entries |

**Format**:
```
[2025-12-29 10:30:45] Investigation started
[2025-12-29 10:30:46] Investigating: iOS App Update Impact
[2025-12-29 10:35:12] Completed: iOS App Update Impact → CONFIRMED
[2025-12-29 10:35:13] Investigating: Android Regression
[2025-12-29 10:38:45] Completed: Android Regression → RULED_OUT
[2025-12-29 10:38:46] Investigation complete - 1 hypothesis confirmed
```

**Storage**: `sessions/{session_id}/analysis/progress.txt`

---

### FindingsLedger

Aggregation of all findings from hypothesis investigations. Built incrementally as each hypothesis completes.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `findings` | `array<Finding>` | Required | All findings (one per hypothesis) |
| `summary` | `object` | Required | Summary statistics |
| `created_at` | `datetime (ISO)` | Required | Ledger creation timestamp |
| `updated_at` | `datetime (ISO)` | Required | Last update timestamp |

**Summary Object**:
```json
{
  "total_hypotheses": 5,
  "confirmed": 1,
  "ruled_out": 4,
  "pending": 0
}
```

**Example**:
```json
{
  "session_id": "abc-123",
  "created_at": "2025-12-29T10:30:45Z",
  "updated_at": "2025-12-29T10:38:46Z",
  "findings": [
    {
      "finding_id": "F1",
      "hypothesis_id": "H1",
      "outcome": "CONFIRMED",
      "evidence": "iOS DAU dropped 15.6% while Android +0.2%",
      "confidence": "HIGH",
      "key_metrics": ["iOS DAU: -15.6%", "Android DAU: +0.2%"],
      "session_log_ref": "logs/session_H1_20251229T103045.json",
      "completed_at": "2025-12-29T10:35:12Z"
    }
  ],
  "summary": {
    "total_hypotheses": 5,
    "confirmed": 1,
    "ruled_out": 4,
    "pending": 0
  }
}
```

**Storage**: `sessions/{session_id}/analysis/findings_ledger.json`

---

### MemoryDocument

Document stored in Supabase for RAG-based Q&A retrieval.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `document_id` | `string (UUID)` | PK, Required | Supabase document ID |
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `content` | `string` | Required | Full compiled analysis memory |
| `embedding` | `vector` | Required | pgvector embedding for similarity search |
| `created_at` | `datetime (ISO)` | Required | Document creation timestamp |

**Content Structure**: Compiled from:
1. Investigation context (metric, dates, business context)
2. Data model summary
3. All hypotheses with final status
4. All compressed findings (findings_ledger)
5. Report content
6. Key reasoning and conclusions

**Storage**: Supabase `memory_documents` table (pgvector enabled)

**Usage**: Q&A handler performs similarity search against this document to retrieve relevant context for answering user questions.

---

### Explanation

A ranked finding explaining metric movement.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `rank` | `integer` | 1-N, Required | Position in ranking |
| `title` | `string` | Required, max 100 | Explanation title |
| `likelihood` | `enum` | Required | `Most Likely`, `Likely`, `Possible`, `Less Likely` |
| `evidence` | `array<Evidence>` | Required | Supporting data points |
| `reasoning` | `string` | Required, max 1000 | Why this confidence level |
| `causal_story` | `string` | Required, max 500 | Narrative explanation |
| `source_hypotheses` | `array<string>` | Required | Hypothesis IDs that contributed |

**Likelihood Mapping**:
- Rank 1: `Most Likely`
- Rank 2-3: `Likely`
- Rank 4-5: `Possible`
- Rank 6+: `Less Likely`

**Storage**: `sessions/{session_id}/results/explanations.json`

---

### Report

Final markdown output of the investigation.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `content` | `string (markdown)` | Required | Full report content |
| `generated_at` | `datetime (ISO)` | Required | Report generation timestamp |
| `status` | `enum` | Required | `completed`, `no_findings` |

**Report Sections** (required):
1. Header (metric name, periods, overall change)
2. Data Model (schema visualization)
3. Analysis Performed (plan summary)
4. Explanations (ranked list with evidence)
5. Recommended Next Steps
6. Footer (generation timestamp)

**Storage**: `sessions/{session_id}/report.md`

---

### ChatMessage

Q&A interaction after report generation.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `message_id` | `string (UUID)` | PK, Required | Unique message identifier |
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `role` | `enum` | Required | `user`, `assistant` |
| `content` | `string` | Required, max 5000 | Message content |
| `timestamp` | `datetime (ISO)` | Required | Message timestamp |
| `artifacts_referenced` | `array<string>` | Optional | Artifact paths used in response |

**Storage**: `sessions/{session_id}/chat/history.json` (array of messages)

---

## Storage Structure Summary

### Local Session Storage (File-based)

```
sessions/{session_id}/
├── metadata.json               # Session entity
├── context.json                # InvestigationContext entity
├── files/
│   ├── {file_id}.csv           # Raw UploadedFile
│   └── {file_id}_meta.json     # UploadedFile metadata + FileSchema
├── analysis/
│   ├── progress.txt            # ProgressLog (human-readable)
│   ├── hypotheses.json         # All Hypothesis entities
│   ├── schema.json             # DataModel entity
│   ├── metric_requirements.json # MetricRequirements entity
│   ├── scripts/                # Python scripts written by agent
│   │   ├── 001_device_analysis.py
│   │   └── 002_geo_breakdown.py
│   ├── logs/                   # Per-hypothesis session logs
│   │   ├── session_H1_*.md     # Human-readable session log
│   │   ├── session_H1_*.json   # SessionLog entity
│   │   └── ...
│   ├── artifacts/              # Analysis outputs
│   │   └── device_breakdown.csv
│   └── findings_ledger.json    # FindingsLedger (built incrementally)
├── results/
│   └── explanations.json       # Array of Explanation entities
├── report.md                   # Report entity (content only)
└── chat/
    └── history.json            # Array of ChatMessage entities
```

### Supabase Storage (RAG)

```sql
-- memory_documents table
CREATE TABLE memory_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- pgvector for similarity search
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for similarity search
CREATE INDEX ON memory_documents
USING ivfflat (embedding vector_cosine_ops);
```

---

## Pydantic Models (Backend)

```python
# backend/src/models/schemas.py

from datetime import datetime, date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from uuid import UUID

class DateRange(BaseModel):
    start: date
    end: date

class SessionCreate(BaseModel):
    pass  # Empty; session created with defaults

class SessionResponse(BaseModel):
    session_id: UUID
    status: Literal["created", "has_files", "running", "completed", "failed", "expired"]
    created_at: datetime
    expires_at: datetime
    file_count: int = 0
    report_ready: bool = False

class FileUploadResponse(BaseModel):
    file_id: UUID
    original_name: str
    row_count: int
    size_bytes: int

class FileMetadataUpdate(BaseModel):
    description: str = Field(..., max_length=2000)

class InvestigationRequest(BaseModel):
    target_metric: str = Field(..., max_length=100)
    metric_definition: str = Field(..., max_length=2000)
    business_context: Optional[str] = Field(None, max_length=5000)
    baseline_period: DateRange
    comparison_period: DateRange
    investigation_prompt: Optional[str] = Field(None, max_length=2000)

class InvestigationResponse(BaseModel):
    status: Literal["running", "completed", "failed"]
    message: str

class ReportResponse(BaseModel):
    content: str
    generated_at: datetime
    status: Literal["completed", "no_findings"]

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=5000)

class ChatResponse(BaseModel):
    response: str
    artifacts_referenced: List[str] = []
```

---

## TypedDict Models (Agent)

See [plan.md](./plan.md#agent-state-schema) for the full `InvestigationState` TypedDict definition.

---

## Index/Query Patterns

### Local File Access

| Operation | Access Pattern |
|-----------|----------------|
| Get session | Read `sessions/{id}/metadata.json` |
| List session files | List `sessions/{id}/files/*.csv` |
| Get file metadata | Read `sessions/{id}/files/{fid}_meta.json` |
| Get analysis artifacts | Read `sessions/{id}/analysis/*.json` |
| Get metric requirements | Read `sessions/{id}/analysis/metric_requirements.json` |
| Get hypotheses | Read `sessions/{id}/analysis/hypotheses.json` |
| Get findings ledger | Read `sessions/{id}/analysis/findings_ledger.json` |
| Get progress log | Read `sessions/{id}/analysis/progress.txt` |
| Get session log | Read `sessions/{id}/analysis/logs/session_{H}_{ts}.json` |
| List scripts | List `sessions/{id}/analysis/scripts/*.py` |
| List artifacts | List `sessions/{id}/analysis/artifacts/*` |
| Get report | Read `sessions/{id}/report.md` |
| Get chat history | Read `sessions/{id}/chat/history.json` |
| Find expired sessions | Scan all `sessions/*/metadata.json` where `expires_at < now` |

### Supabase RAG Queries

| Operation | Query Pattern |
|-----------|---------------|
| Store memory document | `INSERT INTO memory_documents (session_id, content, embedding)` |
| Retrieve for Q&A | Similarity search: `SELECT * FROM memory_documents ORDER BY embedding <=> query_embedding LIMIT k` |
| Delete on session expiry | `DELETE FROM memory_documents WHERE session_id = ?` |

---

## Validation Constraints Summary

| Entity | Constraint | Error Code |
|--------|------------|------------|
| Session | max 10 files | `MAX_FILES_EXCEEDED` |
| UploadedFile | max 50MB | `FILE_TOO_LARGE` |
| UploadedFile | must have .csv extension | `INVALID_FILE_TYPE` |
| UploadedFile | must have header row | `NO_HEADERS` |
| InvestigationContext | target_metric required | `TARGET_METRIC_REQUIRED` |
| InvestigationContext | metric_definition required | `METRIC_DEFINITION_REQUIRED` |
| InvestigationContext | at least 1 file uploaded | `NO_FILES_UPLOADED` |
| InvestigationContext | dates valid | `INVALID_DATE_RANGE` |
| MetricRequirements | target_metric column must exist | `COLUMN_NOT_FOUND` |
| ChatMessage | session must be completed | `INVESTIGATION_NOT_COMPLETE` |
