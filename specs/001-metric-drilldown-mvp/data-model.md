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
│                        (Memory Loop Architecture)                            │
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
│  name           │        │  business_ctx   │
│  description    │        │  metric_sql     │
│  schema         │        │  baseline_dates │
│  row_count      │        │  comparison_dates│
│  path           │        │  prompt         │
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
│   DATA_MODEL    │        │ ANALYSIS_PLAN   │
│   (Inferred)    │        │                 │
│                 │        │  session_id (FK)│
│  session_id (FK)│        │  objectives[]   │
│  tables[]       │        │  created_at     │
│  relationships[]│        └────────┬────────┘
│  dimensions[]   │                 │
└────────┬────────┘                 │
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
         │                 │    FINDING      │←───────│ ITERATION_LOG   │
         │                 │  (Compressed)   │  1:1   │                 │
         │                 │                 │        │  iteration      │
         │                 │  finding_id     │        │  decision       │
         │                 │  iteration      │        │  code_executed  │
         │                 │  summary        │        │  raw_output     │
         │                 │  full_output_ref│        │  compressed_sum │
         │                 │  hypothesis_ref │        │  hyp_changes    │
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
| `business_context` | `string` | Optional, max 5000 | Background information about the metric |
| `metric_sql` | `string` | Required, max 2000 | SQL or text definition of the metric |
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
- `metric_sql` must be provided (FR-004)

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

### AnalysisPlan

Structured plan for investigating the metric.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `steps` | `array<PlanStep>` | Required | Ordered analysis steps |
| `created_at` | `datetime (ISO)` | Required | Plan creation timestamp |

**PlanStep**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `step_number` | `integer` | Execution order |
| `phase` | `string` | `exploration`, `hypothesis_generation`, `validation` |
| `description` | `string` | What this step accomplishes |
| `tables_involved` | `array<string>` | Files/tables used |
| `dimensions_to_check` | `array<string>` | Columns to analyze |

**Storage**: `sessions/{session_id}/analysis/plan.json`

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

**Status Transitions** (Memory Loop):
```
PENDING → INVESTIGATING (when loop starts examining this hypothesis)
INVESTIGATING → CONFIRMED (when evidence supports the hypothesis)
INVESTIGATING → RULED_OUT (when evidence contradicts the hypothesis)
INVESTIGATING → PENDING (when pivoting to different approach)
```

**Storage**: `sessions/{session_id}/analysis/hypotheses/hyp_{NNN}.json`

---

### Finding

A compressed summary of one Memory Loop iteration result.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `finding_id` | `string` | PK, Required | Unique ID (e.g., `find_001`) |
| `iteration` | `integer` | Required | Which loop iteration (1-15) |
| `summary` | `string` | Required, max 500 | 2-3 sentence compressed summary |
| `full_output_ref` | `string` | Required | Path to full raw output |
| `hypothesis_affected` | `string` | Optional | Which hypothesis this finding relates to |
| `created_at` | `datetime (ISO)` | Required | Finding timestamp |

**Summary Format**: Compressed by LLM to answer:
1. What was tested/analyzed?
2. What key numbers or patterns were found?
3. What does this imply for the hypothesis?

**Storage**: Part of `findings_ledger.json`

---

### IterationLog

Full record of one Memory Loop iteration (for debugging/audit).

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `iteration` | `integer` | PK, Required | Loop iteration number (1-15) |
| `decision` | `enum` | Required | `ANALYZE`, `DRILL_DOWN`, `PIVOT`, `CONCLUDE` |
| `code_executed` | `string` | Required | Python code sent to MCP server |
| `raw_output` | `string` | Required | stdout/stderr from execution |
| `compressed_summary` | `string` | Required | The 2-3 sentence summary |
| `hypothesis_status_changes` | `object` | Optional | Any status changes to hypotheses |
| `timestamp` | `datetime (ISO)` | Required | Iteration timestamp |

**Decision Types**:
- `ANALYZE`: Execute analysis code on current hypothesis
- `DRILL_DOWN`: Deeper investigation into a finding
- `PIVOT`: Switch to a different hypothesis or approach
- `CONCLUDE`: Investigation complete, generate report

**Storage**: `sessions/{session_id}/analysis/iterations/iter_{NNN}.json`

---

### FindingsLedger

Aggregation of all compressed findings from the Memory Loop.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `session_id` | `string (UUID)` | FK → Session, Required | Parent session |
| `findings` | `array<Finding>` | Required | All compressed findings |
| `hypothesis_outcomes` | `object` | Required | Final status of each hypothesis |
| `total_iterations` | `integer` | Required | How many loop iterations ran |
| `exit_reason` | `enum` | Required | `CONCLUDE`, `MAX_ITERATIONS`, `STALL_DETECTED` |
| `created_at` | `datetime (ISO)` | Required | Ledger finalization timestamp |

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
│   ├── schema.json             # DataModel entity
│   ├── plan.json               # AnalysisPlan entity
│   ├── hypotheses/
│   │   ├── hyp_001.json        # Hypothesis with status
│   │   ├── hyp_002.json
│   │   └── ...
│   ├── findings_ledger.json    # FindingsLedger (compressed findings)
│   ├── iterations/
│   │   ├── iter_001.json       # IterationLog (full record)
│   │   ├── iter_002.json
│   │   └── ...
│   └── full_outputs/
│       ├── output_001.txt      # Raw MCP execution output
│       ├── output_002.txt
│       └── ...
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
    business_context: Optional[str] = Field(None, max_length=5000)
    metric_sql: str = Field(..., max_length=2000)
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
| Get findings ledger | Read `sessions/{id}/analysis/findings_ledger.json` |
| Get iteration log | Read `sessions/{id}/analysis/iterations/iter_{N}.json` |
| Get raw output | Read `sessions/{id}/analysis/full_outputs/output_{N}.txt` |
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
| InvestigationContext | metric_sql required | `METRIC_SQL_REQUIRED` |
| InvestigationContext | at least 1 file uploaded | `NO_FILES_UPLOADED` |
| InvestigationContext | dates valid | `INVALID_DATE_RANGE` |
| ChatMessage | session must be completed | `INVESTIGATION_NOT_COMPLETE` |
