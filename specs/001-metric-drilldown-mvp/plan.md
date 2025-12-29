# Implementation Plan: Metric Drill-Down Agent MVP

**Branch**: `001-metric-drilldown-mvp` | **Date**: 2025-12-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-metric-drilldown-mvp/spec.md`

## Summary

Build an AI-powered metric investigation tool that enables data scientists to upload CSV files, provide metric context, and receive ranked explanations for unexpected metric movements. The system follows a three-tier architecture: Node.js/HTMX frontend for form-based input, FastAPI backend for API orchestration and session management, and a LangGraph-based AI agent for data analysis and explanation generation.

## Technical Context

**Language/Version**: Python 3.11+ (Backend/Agent), Node.js 20+ (Frontend)
**Primary Dependencies**: FastAPI, LangGraph, Claude Agent SDK, HTMX, Supabase MCP, Supabase-py
**Storage**: File-based session storage (local), Supabase (memory documents for RAG)
**Testing**: pytest (backend/agent), Vitest (frontend)
**Target Platform**: Linux server (local-first, AWS-transferable)
**Project Type**: Web application (frontend + backend + agent)
**Performance Goals**: Investigation completion in under 15 minutes for datasets up to 500K rows
**Constraints**: 50MB max file size per CSV, 24-hour session timeout default, Claude API rate limits
**Scale/Scope**: Single-user sessions, MVP demo phase, 3-10 CSV files per investigation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Implementation Approach |
|-----------|--------|------------------------|
| I. Understandable Code | ✅ PASS | Descriptive naming, explicit logic, minimal comments only where needed |
| II. Simple Form-to-Report UX | ✅ PASS | Three-section form (Files, Context, Prompt), automated flow, markdown output with download |
| III. Transparent AI Reasoning | ✅ PASS | All explanations show underlying data, contribution %, methodology available via Q&A |
| IV. Test Critical Paths | ✅ PASS | Tests for schema inference, hypothesis generation, API flows, memory retrieval |
| V. Ephemeral Session Data | ✅ PASS | Session-scoped directories, configurable timeout (24h default), no persistent accounts |
| VI. Modular Architecture | ✅ PASS | Clean separation: UI (Node.js/HTMX) ↔ API (FastAPI) ↔ Agent (Python/LangGraph) |

**Technology Constraints Compliance**:
- ✅ Frontend: Node.js with HTMX
- ✅ Backend API: FastAPI (Python)
- ✅ Database: Supabase (memory documents + RAG retrieval for Q&A)
- ✅ Agent: LangGraph + Claude Agent SDK (using query() for iterative analysis)
- ✅ Tools: Supabase MCP for file retrieval, native bash for Python execution
- ✅ LLM: Claude models exclusively

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           METRIC DRILL-DOWN AGENT                                │
│                              System Architecture                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     HTTP/HTMX      ┌─────────────┐      REST API       ┌─────────────┐
│   BROWSER   │◄──────────────────►│   FRONTEND  │◄───────────────────►│   BACKEND   │
│             │                    │  (Node.js)  │                     │  (FastAPI)  │
│  - Form UI  │                    │             │                     │             │
│  - Report   │                    │  - Express  │                     │  - Sessions │
│    Display  │                    │  - HTMX     │                     │  - Files    │
│  - Chat     │                    │  - EJS      │                     │  - Agent    │
│    Panel    │                    │    Views    │                     │    Invoke   │
└─────────────┘                    └─────────────┘                     └──────┬──────┘
                                                                              │
                                                                              │ Python
                                                                              │ Import
                                                                              ▼
                                   ┌──────────────────────────────────────────────────┐
                                   │                    AI AGENT                       │
                                   │                  (LangGraph)                      │
                                   │                                                   │
                                   │  ┌───────────────────────────────────────────┐   │
                                   │  │              STATE GRAPH                   │   │
                                   │  │                                           │   │
                                   │  │  START → Schema → Metric Validate →      │   │
                                   │  │        Hypothesize → Analysis → Report   │   │
                                   │  │                       ↓                   │   │
                                   │  │            Python Orchestrator Loop       │   │
                                   │  │            (One query() per hypothesis)   │   │
                                   │  └───────────────────────────────────────────┘   │
                                   │                                                   │
                                   │  ┌───────────────────────────────────────────┐   │
                                   │  │        CLAUDE AGENT SDK (query())          │   │
                                   │  │  - Iterative analysis per hypothesis      │   │
                                   │  │  - Writes Python scripts to /scripts/     │   │
                                   │  │  - Executes via native bash               │   │
                                   │  └───────────────────────────────────────────┘   │
                                   └──────────────────────────┬────────────────────────┘
                                                              │
                                          ┌───────────────────┼───────────────────┐
                                          ▼                   ▼                   ▼
                                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                                   │   Claude    │    │   Session   │    │  Supabase   │
                                   │  Agent SDK  │    │   Storage   │    │  (Files +   │
                                   │   query()   │    │   (Files)   │    │   RAG)      │
                                   └─────────────┘    └─────────────┘    └─────────────┘
                                                                                │
                                                              ┌─────────────────┘
                                                              ▼
                                                       ┌─────────────┐
                                                       │ Supabase MCP│
                                                       │   Server    │
                                                       │(File Export)│
                                                       └─────────────┘
```

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW DIAGRAM                                    │
└──────────────────────────────────────────────────────────────────────────────────┘

1. FORM SUBMISSION
   Browser → [CSV Files + Descriptions + Target Metric + Definition + Context + Date Ranges] → Frontend
   Frontend → POST /api/sessions/create → Backend (creates session directory)
   Frontend → POST /api/sessions/{id}/files → Backend (stores each file)

2. INVESTIGATION START
   Frontend → POST /api/sessions/{id}/investigate → Backend
   Backend → Validates session has required data
   Backend → Invokes Agent with InvestigationState

3. AGENT EXECUTION (detailed in Agent Design section)
   Agent Graph executes: Schema → Metric ID → Hypothesize → Analyze → Report
   Agent writes artifacts to /sessions/{id}/ throughout execution

4. REPORT DELIVERY
   Agent → Writes /sessions/{id}/report.md
   Backend → Returns report content + session status
   Frontend → Renders markdown in report view + enables chat panel

5. MEMORY DUMP (after analysis completes)
   Agent → Compiles all findings from findings_ledger.json into memory document
   Agent → Stores memory document in Supabase with embeddings

6. Q&A FLOW (uses RAG retrieval from Supabase)
   Browser → Chat message → Frontend
   Frontend → POST /api/sessions/{id}/chat → Backend
   Backend → RAG retrieval from Supabase memory document
   Backend → LLM generates response with retrieved context
   Backend → Returns response → Frontend → Updates chat panel
```

---

## Project Structure

### Documentation (this feature)

```text
specs/001-metric-drilldown-mvp/
├── plan.md              # This file
├── research.md          # Phase 0: Technology decisions
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Developer setup guide
├── contracts/           # Phase 1: API specifications
│   ├── api.yaml         # OpenAPI 3.0 spec for backend
│   └── agent-tools.md   # Agent tool interface definitions
└── tasks.md             # Phase 2: Implementation tasks (via /speckit.tasks)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── server.js                    # Express entry point
│   ├── routes/
│   │   ├── index.js                 # Landing page (form)
│   │   ├── session.js               # Session management routes
│   │   └── api.js                   # Proxy to backend API
│   ├── views/
│   │   ├── layout.ejs               # Base layout
│   │   ├── form.ejs                 # Investigation form
│   │   ├── report.ejs               # Report display + chat
│   │   └── partials/
│   │       ├── file-card.ejs        # Uploaded file display
│   │       ├── chat-message.ejs     # Chat bubble component
│   │       └── explanation.ejs      # Explanation card
│   └── public/
│       ├── css/
│       │   └── styles.css           # Custom styles
│       └── js/
│           └── app.js               # Minimal JS (file preview, markdown render)
├── package.json
└── tests/
    └── routes.test.js

backend/
├── src/
│   ├── main.py                      # FastAPI application entry
│   ├── config.py                    # Environment configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── sessions.py          # Session CRUD
│   │   │   ├── files.py             # File upload/delete
│   │   │   ├── investigate.py       # Trigger investigation
│   │   │   └── chat.py              # Q&A endpoint
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── error_handler.py     # Global error handling
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py               # Session model
│   │   └── schemas.py               # Pydantic request/response schemas
│   └── services/
│       ├── __init__.py
│       ├── session_manager.py       # Session lifecycle management
│       ├── file_handler.py          # CSV validation & storage
│       └── agent_runner.py          # Agent invocation wrapper
├── requirements.txt
└── tests/
    ├── conftest.py
    ├── test_sessions.py
    ├── test_files.py
    └── test_investigation.py

agent/
├── src/
│   ├── __init__.py
│   ├── graph.py                     # LangGraph state machine definition
│   ├── state.py                     # InvestigationState TypedDict
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── schema_inference.py      # Infer column types & relationships
│   │   ├── metric_identification.py # Validate metric columns exist in data
│   │   ├── hypothesis_generator.py  # Generate potential explanations
│   │   ├── analysis_execution.py    # Memory Loop: iterative code execution
│   │   ├── memory_dump.py           # Dump findings to Supabase
│   │   └── report_generator.py      # Compile final markdown report
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── csv_tools.py             # Read headers, sample rows, row count
│   │   ├── file_tools.py            # Read/write session artifacts
│   │   └── mcp_client.py            # MCP server connection & code execution
│   ├── prompts/
│   │   ├── schema_inference.txt
│   │   ├── metric_identification.txt # (unused - pure Python validation)
│   │   ├── hypothesis_generation.txt
│   │   ├── analysis_decision.txt    # ANALYZE/DRILL_DOWN/PIVOT/CONCLUDE
│   │   ├── compression.txt          # Compress raw output to 2-3 sentences
│   │   ├── report_template.txt
│   │   └── qa_response.txt
│   └── memory/
│       ├── __init__.py
│       ├── working_memory.py        # Build context for each iteration
│       ├── findings_ledger.py       # Track compressed findings
│       └── supabase_rag.py          # RAG retrieval for Q&A
├── requirements.txt
└── tests/
    ├── conftest.py
    ├── test_schema_inference.py
    ├── test_hypothesis_generation.py
    ├── test_analysis_execution.py
    └── test_memory_dump.py

shared/
├── __init__.py
└── config.py                        # Shared settings (env vars)

sessions/                            # Runtime session storage (gitignored)
├── {session_id}/
│   ├── metadata.json
│   ├── context.json                 # Investigation context from form
│   ├── files/
│   │   ├── {file_id}.csv
│   │   └── {file_id}_meta.json
│   ├── analysis/
│   │   ├── progress.txt             # High-level investigation log
│   │   ├── hypotheses.json          # All hypotheses with status
│   │   ├── schema.json              # Inferred data model
│   │   ├── metric_requirements.json
│   │   ├── scripts/                 # Python scripts written by agent
│   │   │   └── NNN_description.py
│   │   ├── logs/                    # Per-hypothesis session logs
│   │   │   ├── session_H1_*.md      # Human-readable session log
│   │   │   └── session_H1_*.json    # Structured session summary
│   │   ├── artifacts/               # Analysis outputs (CSVs, charts)
│   │   │   └── output_*.csv
│   │   └── findings_ledger.json     # Incrementally built findings
│   ├── results/
│   │   └── explanations.json
│   ├── report.md
│   └── chat/
│       └── history.json

docker-compose.yml                   # Local development setup
.env.example                         # Environment template
```

**Structure Decision**: Web application with three distinct projects (frontend, backend, agent) per Constitution Principle VI. The agent is a separate Python package imported by the backend, enabling independent testing and potential future extraction to a microservice.

---

## Component Design: Frontend (Node.js/HTMX)

### Overview

Lightweight Node.js server using Express, EJS templates, and HTMX for dynamic interactions. Minimal custom JavaScript; server-side rendering with HTMX-powered partial updates.

### Key Design Decisions

1. **HTMX for Interactivity**: Form submissions, file uploads, and chat use HTMX attributes (`hx-post`, `hx-target`, `hx-swap`) for seamless updates without full page reloads.

2. **EJS Templates**: Server-side rendering with partials for reusable components.

3. **Proxy Pattern**: Frontend proxies API calls to backend, handling CORS and simplifying deployment.

### Page Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                         FORM PAGE (/)                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ SECTION 1: Relevant Documents                              │  │
│  │ ┌─────────────────────────────────────────────────────┐   │  │
│  │ │ [File Card] user_activity.csv         [Remove]      │   │  │
│  │ │ Description: [textarea]                             │   │  │
│  │ └─────────────────────────────────────────────────────┘   │  │
│  │ [+ Add File] (hx-post="/api/files/upload")                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ SECTION 2: Business Context                                │  │
│  │ Target Metric Column: [text input] (e.g., "dau", "revenue")│  │
│  │ Metric Definition: [textarea - how is metric calculated?] │  │
│  │ Related Context: [textarea]                               │  │
│  │ Baseline Period: [date] to [date]                         │  │
│  │ Comparison Period: [date] to [date]                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ SECTION 3: Investigation Prompt (optional)                 │  │
│  │ [textarea - specific hypotheses or focus areas]           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [ START AGENT ] (hx-post="/api/sessions/{id}/investigate")     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     REPORT PAGE (/session/{id})                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────┬────────────────────┐   │
│  │          REPORT PANEL (70%)         │  CHAT PANEL (30%)  │   │
│  │  ┌─────────────────────────────┐   │ ┌────────────────┐ │   │
│  │  │ # Investigation Report      │   │ │ Agent: Ready   │ │   │
│  │  │                             │   │ │ to answer...   │ │   │
│  │  │ ## Data Model               │   │ ├────────────────┤ │   │
│  │  │ [schema visualization]      │   │ │ User: How did  │ │   │
│  │  │                             │   │ │ you calculate  │ │   │
│  │  │ ## Explanations             │   │ │ contribution?  │ │   │
│  │  │ ### 1. Most Likely          │   │ ├────────────────┤ │   │
│  │  │ Evidence: ...               │   │ │ Agent: The     │ │   │
│  │  │                             │   │ │ contribution   │ │   │
│  │  │ [Download Report]           │   │ │ is calculated..│ │   │
│  │  └─────────────────────────────┘   │ ├────────────────┤ │   │
│  │                                     │ │ [input] [Send] │ │   │
│  └─────────────────────────────────────┴────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### HTMX Interactions

| Action | HTMX Attribute | Target | Swap |
|--------|---------------|--------|------|
| Upload file | `hx-post="/api/files"` | `#file-list` | `beforeend` |
| Remove file | `hx-delete="/api/files/{id}"` | `closest .file-card` | `outerHTML` |
| Submit form | `hx-post="/api/investigate"` | `body` | `innerHTML` (redirects to report) |
| Send chat | `hx-post="/api/chat"` | `#chat-messages` | `beforeend` |

### Accessibility (WCAG 2.1 AA)

- All inputs have `<label>` elements with `for` attribute
- Color contrast minimum 4.5:1 (text), 3:1 (UI components)
- Focus indicators visible on all interactive elements
- ARIA live regions for dynamic content (`aria-live="polite"` on chat)
- Skip links and logical heading hierarchy

---

## Component Design: Backend API (FastAPI)

### Overview

FastAPI backend provides REST endpoints for session management, file handling, investigation orchestration, and Q&A. Runs the agent as an in-process Python module.

### API Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| POST | `/api/sessions` | Create session | `{}` | `{session_id, created_at}` |
| GET | `/api/sessions/{id}` | Get session status | - | `{status, files, report_ready}` |
| DELETE | `/api/sessions/{id}` | Delete session | - | `{success}` |
| POST | `/api/sessions/{id}/files` | Upload file | `multipart/form-data` | `{file_id, name, rows}` |
| PUT | `/api/sessions/{id}/files/{fid}` | Update description | `{description}` | `{success}` |
| DELETE | `/api/sessions/{id}/files/{fid}` | Remove file | - | `{success}` |
| POST | `/api/sessions/{id}/investigate` | Start investigation | `{target_metric, metric_definition, context, dates, prompt}` | `{status: "running"}` |
| GET | `/api/sessions/{id}/report` | Get report | - | `{content, format: "markdown"}` |
| POST | `/api/sessions/{id}/chat` | Send Q&A | `{message}` | `{response}` |

### Session State Machine

```
                    ┌──────────────┐
                    │   CREATED    │  POST /sessions
                    └──────┬───────┘
                           │
                           │ POST /files (first file)
                           ▼
                    ┌──────────────┐
           ┌───────│   HAS_FILES  │◄───────┐
           │       └──────┬───────┘        │
           │              │                │
           │ DELETE       │ POST           │ POST /files
           │ (all files)  │ /investigate   │
           │              ▼                │
           │       ┌──────────────┐        │
           │       │   RUNNING    │────────┘ (not allowed)
           │       └──────┬───────┘
           │              │
           │       ┌──────┴───────┐
           │       │              │
           │       ▼              ▼
           │ ┌──────────┐  ┌──────────┐
           │ │ COMPLETED│  │  FAILED  │
           │ └────┬─────┘  └────┬─────┘
           │      │             │
           │      │ Q&A enabled │
           │      ▼             │
           │ ┌──────────┐       │
           └►│  EXPIRED │◄──────┘ (timeout)
             └──────────┘
                 │
                 ▼
             [Deleted]
```

### Error Handling

```python
# Retry configuration for LLM calls
RETRY_CONFIG = {
    "max_attempts": 3,
    "initial_delay": 1.0,
    "backoff_multiplier": 2.0,  # 1s, 2s, 4s
    "retryable_errors": [429, 500, 502, 503, 504]
}

# Error responses follow standard format
{
    "error": {
        "code": "SESSION_NOT_FOUND",
        "message": "Session abc123 does not exist",
        "details": {}
    }
}
```

### Session Storage

```
sessions/{session_id}/
├── metadata.json              # {status, created_at, timeout_at, file_count}
├── files/
│   ├── {uuid}.csv             # Raw uploaded file
│   └── {uuid}_meta.json       # {original_name, description, schema, row_count}
├── context.json               # {target_metric, metric_definition, business_context, dates, prompt}
├── analysis/
│   ├── schema.json            # Inferred data model
│   ├── metric_requirements.json # Validated metric columns
│   └── hypotheses/
│       ├── hyp_001.json       # Individual hypothesis + validation result
│       └── hyp_002.json
├── results/
│   └── explanations.json      # Final ranked explanations
├── report.md                  # Generated markdown report
└── chat/
    └── history.json           # [{role, content, timestamp}]
```

---

## Component Design: AI Agent (LangGraph)

### Overview

The agent is implemented using LangGraph, providing a stateful graph-based workflow. Each node performs a specific analysis step, with conditional edges for iteration logic.

### Agent State Schema

```python
from typing import TypedDict, List, Optional, Literal, Annotated
from operator import add

class FileInfo(TypedDict):
    file_id: str
    name: str
    path: str
    description: str
    schema: Optional[dict]  # {columns: [{name, type, cardinality}]}

class DateRange(TypedDict):
    start: str  # ISO date
    end: str

class Hypothesis(TypedDict):
    id: str
    title: str
    causal_story: str
    dimensions: List[str]
    expected_pattern: str
    priority: int
    status: Literal["PENDING", "INVESTIGATING", "CONFIRMED", "RULED_OUT"]

class Finding(TypedDict):
    """Finding from a completed hypothesis investigation."""
    finding_id: str
    hypothesis_id: str
    outcome: Literal["CONFIRMED", "RULED_OUT"]
    evidence: str  # Key evidence supporting the conclusion
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    key_metrics: List[str]  # Key numbers discovered
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
    key_findings: List[str]
    scripts_created: List[str]
    artifacts_created: List[str]

class Explanation(TypedDict):
    rank: int
    title: str
    likelihood: Literal["Most Likely", "Likely", "Possible", "Less Likely"]
    evidence: List[dict]
    reasoning: str
    causal_story: str

class MetricRequirements(TypedDict):
    """Validation result from metric_identification node."""
    target_metric: str  # The column name user wants to analyze
    source_file: Optional[dict]  # {file_id, file_name} where column was found
    validated: bool  # True if column was found
    error_message: Optional[str]  # Error details if not validated

class InvestigationState(TypedDict):
    # Input (set at start)
    session_id: str
    files: List[FileInfo]
    business_context: str
    target_metric: str  # Column name to analyze (MUST exist in CSV)
    metric_definition: str  # Text description of how metric is calculated (for LLM context)
    baseline_period: DateRange
    comparison_period: DateRange
    investigation_prompt: Optional[str]

    # Schema Inference Output
    data_model: Optional[dict]  # {tables, relationships}
    selected_dimensions: Optional[List[str]]

    # Metric Identification Output
    metric_requirements: Optional[MetricRequirements]

    # Hypothesis Generation Output
    hypotheses: Annotated[List[Hypothesis], add]

    # Analysis Execution Output (Python orchestrator + Claude Agent SDK)
    findings_ledger: Annotated[List[Finding], add]  # Findings per hypothesis
    session_logs: Annotated[List[SessionLog], add]  # Session logs per hypothesis

    # Final Output
    explanations: Optional[List[Explanation]]
    report_path: Optional[str]
    memory_document_id: Optional[str]  # Supabase document ID for RAG

    # Control
    status: Literal["running", "completed", "failed", "no_findings"]
    error: Optional[str]
```

### Agent Graph Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AGENT STATE GRAPH (LangGraph)                            │
│                   with Claude Agent SDK Orchestrator Architecture                │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │    START    │
                              │  (input)    │
                              └──────┬──────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   schema_inference    │  Node 1
                         │                       │
                         │ • Read CSV headers    │
                         │ • Sample 100 rows     │
                         │ • LLM infers types    │
                         │ • Detect FK relations │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ metric_identification │  Node 2
                         │                       │
                         │ • Validate target     │
                         │   metric column       │
                         │   exists in files     │
                         └───────────┬───────────┘
                                     │
                              ┌──────┴──────┐
                              │             │
                         validated?    NOT validated
                              │             │
                              ▼             ▼
                         ┌─────────┐   ┌─────────┐
                         │ continue│   │  ERROR  │
                         │         │   │ (exit)  │
                         └────┬────┘   └─────────┘
                              │
                              ▼
                         ┌───────────────────────┐
                         │ hypothesis_generator  │  Node 3
                         │                       │
                         │ • Generate 5-7 hypos  │
                         │ • Based on context +  │
                         │   user prompt         │
                         │ • Status: PENDING     │
                         └───────────┬───────────┘
                                     │
                                     ▼
    ┌────────────────────────────────────────────────────────────────────────────┐
    │                     ANALYSIS_EXECUTION NODE (Node 4)                        │
    │               Python Orchestrator + Claude Agent SDK query()                │
    ├────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │   ┌─────────────────────────────────────────────────────────────────────┐  │
    │   │                    PYTHON ORCHESTRATOR LOOP                          │  │
    │   │                                                                      │  │
    │   │    ┌───────────────────────────────────────────────────────────┐    │  │
    │   │    │ 1. INITIALIZE                                             │    │  │
    │   │    │    • Fetch files from Supabase via MCP                   │    │  │
    │   │    │    • Write hypotheses.json                               │    │  │
    │   │    │    • Initialize progress.txt                             │    │  │
    │   │    │    • Initialize findings_ledger.json                     │    │  │
    │   │    └───────────────────────────┬───────────────────────────────┘    │  │
    │   │                                │                                     │  │
    │   │                                ▼                                     │  │
    │   │    ┌───────────────────────────────────────────────────────────┐    │  │
    │   │    │ 2. FOR EACH PENDING HYPOTHESIS:                           │    │  │
    │   │    │    ┌─────────────────────────────────────────────────┐   │    │  │
    │   │    │    │ a. Update status → INVESTIGATING                │   │    │  │
    │   │    │    │ b. Log to progress.txt                          │   │    │  │
    │   │    │    │                                                 │   │    │  │
    │   │    │    │ c. Call query() with Claude Agent SDK:          │   │    │  │
    │   │    │    │    ┌────────────────────────────────────────┐  │   │    │  │
    │   │    │    │    │ CLAUDE AGENT SDK SESSION               │  │   │    │  │
    │   │    │    │    │ • Reads data files                     │  │   │    │  │
    │   │    │    │    │ • Writes Python scripts to /scripts/   │  │   │    │  │
    │   │    │    │    │ • Executes via native bash             │  │   │    │  │
    │   │    │    │    │ • Writes session log to /logs/         │  │   │    │  │
    │   │    │    │    │ • Iterates until CONFIRMED/RULED_OUT   │  │   │    │  │
    │   │    │    │    └────────────────────────────────────────┘  │   │    │  │
    │   │    │    │                                                 │   │    │  │
    │   │    │    │ d. Capture session result                       │   │    │  │
    │   │    │    │ e. Update hypothesis status                     │   │    │  │
    │   │    │    │ f. Add to findings_ledger.json (incremental)   │   │    │  │
    │   │    │    │ g. Save session log JSON                        │   │    │  │
    │   │    │    │ h. Log completion to progress.txt               │   │    │  │
    │   │    │    └─────────────────────────────────────────────────┘   │    │  │
    │   │    │                                                           │    │  │
    │   │    │    REPEAT for each hypothesis                            │    │  │
    │   │    └───────────────────────────────────────────────────────────┘    │  │
    │   │                                                                      │  │
    │   └─────────────────────────────────────────────────────────────────────┘  │
    │                                                                             │
    └───────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        ▼
                         ┌───────────────────────┐
                         │     memory_dump       │  Node 5
                         │                       │
                         │ • Read findings_ledger│
                         │ • Store in Supabase   │
                         │ • Generate embeddings │
                         │   for RAG retrieval   │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │  report_generator     │  Node 6
                         │                       │
                         │ • Rank explanations   │
                         │ • Format markdown     │
                         │ • Write report.md     │
                         └───────────┬───────────┘
                                     │
                                     ▼
                              ┌─────────────┐
                              │     END     │
                              │  (output)   │
                              └─────────────┘
```

### Analysis Execution Configuration

```python
ANALYSIS_CONFIG = {
    "max_turns_per_hypothesis": 10,  # Max query() iterations per hypothesis
    "model": "claude-sonnet-4-20250514",
    "allowed_tools": ["Read", "Write", "Bash", "Glob"],
    "permission_mode": "acceptEdits",
}
```

### Node Specifications

#### Node 1: `schema_inference`

**Purpose**: Analyze uploaded CSV files to infer column types and relationships.

**Tools Used**:
- `csv_tools.get_headers(file_path) → List[str]`
- `csv_tools.sample_rows(file_path, n=100) → List[dict]`
- `csv_tools.get_row_count(file_path) → int`

**LLM Prompt** (simplified):
```
Analyze these CSV files to infer their schema.

Files:
{for each file: name, description, headers, sample_rows}

For each column, determine:
1. Type: dimension | measure | id | timestamp
2. Cardinality estimate
3. Potential relationships to other tables

Output JSON:
{
  "tables": [...],
  "relationships": [...],
  "recommended_dimensions": [...]
}
```

**Output**: Updates `state.data_model`, `state.selected_dimensions`

---

#### Node 2: `metric_identification`

**Purpose**: Validate that the user-specified target metric column exists in the uploaded files.

**Tools Used**: None (pure Python logic - no LLM call needed)

**Logic** (simplified Python):
```python
def metric_identification(state: InvestigationState) -> MetricRequirements:
    target_metric = state.target_metric

    # Search for target_metric column in all file schemas
    for file in state.files:
        if target_metric in file.schema["columns"]:
            return MetricRequirements(
                target_metric=target_metric,
                source_file={"file_id": file.file_id, "file_name": file.name},
                validated=True,
                error_message=None
            )

    # Column not found - collect all available columns
    all_columns = []
    for file in state.files:
        all_columns.extend([col["name"] for col in file.schema["columns"]])

    return MetricRequirements(
        target_metric=target_metric,
        source_file=None,
        validated=False,
        error_message=f"Column '{target_metric}' not found in any uploaded file. "
                      f"Available columns: {', '.join(sorted(set(all_columns)))}"
    )
```

**Conditional Exit**:
- If `validated = true`: Proceed to `hypothesis_generator`
- If `validated = false`: Set `state.status = "failed"` with error message, exit graph

**Error Message Format**:
```
Column 'dau' not found in any uploaded file. Available columns:
event_date, event_type, revenue, session_count, user_id
```

**Output**: Updates `state.metric_requirements`

**Key Simplification**: No LLM call required. This is a pure lookup operation - the user explicitly provides the column name, we just verify it exists.

---

#### Node 3: `hypothesis_generator`

**Purpose**: Generate potential explanations for the metric movement. This node serves as the implicit investigation planner - the generated hypotheses define what will be explored.

**Tools Used**: None (LLM reasoning only)

**LLM Prompt** (simplified):
```
Generate 5-7 hypotheses for why this metric changed.

Target Metric: {target_metric}
Metric Definition: {metric_definition}
Source File: {metric_requirements.source_file}
Context: {business_context}
User Focus: {investigation_prompt}
Available Dimensions: {selected_dimensions}

Each hypothesis must have:
- Unique ID
- Title (concise)
- Causal story (1-2 sentences)
- Dimensions to test
- Expected pattern if true
- Priority (1 = most plausible)
- Status: PENDING

Output JSON array of hypotheses.
```

**Output**: Updates `state.hypotheses` (all with status=PENDING)

---

#### Node 4: `analysis_execution` (Python Orchestrator + Claude Agent SDK)

**Purpose**: Iteratively analyze data to validate/invalidate hypotheses using Claude Agent SDK `query()` calls.

**Architecture**: Python orchestrator loop that calls `query()` once per hypothesis.

**Phase 1: Initialize**
```python
session_path = get_session_path(state.session_id)

# Fetch files from Supabase via MCP
await retrieve_files_from_supabase(
    session_id=state.session_id,
    target_dir=f"{session_path}/analysis/files/"
)

# Initialize file-based memory
initialize_analysis_directory(session_path)
write_hypotheses_json(session_path, state.hypotheses)
write_progress_log(session_path, "Investigation started")
initialize_findings_ledger(session_path)
```

**Phase 2: Hypothesis Investigation Loop**

For each PENDING hypothesis:

```python
for hypothesis in state.hypotheses:
    if hypothesis.status != "PENDING":
        continue

    # Update status
    hypothesis.status = "INVESTIGATING"
    write_hypotheses_json(session_path, state.hypotheses)
    write_progress_log(session_path, f"Investigating: {hypothesis.title}")

    # Build investigation prompt
    prompt = build_investigation_prompt(
        hypothesis=hypothesis,
        context=state.investigation_context,
        data_model=state.data_model,
        file_list=list_analysis_files(session_path)
    )

    # Call Claude Agent SDK
    session_log = SessionLog(hypothesis_id=hypothesis.id, start_time=now())

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Bash", "Glob"],
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            cwd=session_path,
            max_turns=10
        )
    ):
        session_log.messages.append(message)

        if isinstance(message, ResultMessage):
            result = parse_investigation_result(message)
            session_log.outcome = result.outcome
            session_log.end_time = now()

    # Update hypothesis
    hypothesis.status = result.outcome  # CONFIRMED or RULED_OUT
    hypothesis.evidence = result.evidence

    # Save logs and update ledger (incrementally)
    save_session_log(session_path, hypothesis.id, session_log)
    add_finding_to_ledger(session_path, Finding(
        finding_id=f"F{len(state.findings_ledger) + 1}",
        hypothesis_id=hypothesis.id,
        outcome=result.outcome,
        evidence=result.evidence,
        confidence=result.confidence,
        key_metrics=result.key_metrics,
        session_log_ref=f"logs/session_{hypothesis.id}_{timestamp}.json",
        completed_at=now()
    ))

    write_progress_log(session_path, f"Completed: {hypothesis.title} → {result.outcome}")
```

**System Prompt for Analysis Agent**:
```markdown
You are investigating a hypothesis about metric movement. Your goal is to either CONFIRM or RULE OUT this hypothesis through data analysis.

## Your Task
Hypothesis: {hypothesis.title}
Story: {hypothesis.causal_story}
Expected pattern if true: {hypothesis.expected_pattern}
Dimensions to analyze: {hypothesis.dimensions}

## Available Data
Files in /analysis/files/: {file_list}
Data schema: {schema_summary}

## Your Process
1. Write a Python script to analyze the relevant dimensions
2. Save the script to /analysis/scripts/NNN_description.py
3. Run the script using bash: `python /analysis/scripts/NNN_description.py`
4. Interpret the results
5. Repeat if you need more analysis
6. Conclude with CONFIRMED or RULED_OUT

## Logging Your Work
As you work, write your reasoning to a markdown log file at:
/analysis/logs/session_{hypothesis_id}_{timestamp}.md

Use this format for each step:
## [Timestamp] Step N: [Action Type]

**What I did**: [description]
**What I found**: [data/results]
**My interpretation**: [what this means]
**Decision**: [continue/pivot/conclude]
**Reasoning**: [why this decision]

## Conclusion Format
When you're done, your final message must include:
- OUTCOME: CONFIRMED or RULED_OUT
- EVIDENCE: Key numbers that support your conclusion
- CONFIDENCE: HIGH/MEDIUM/LOW
```

**Output**: Updates `state.hypotheses`, `state.findings_ledger`, `state.session_logs`

---

#### Node 5: `memory_dump`

**Purpose**: Persist all analysis memory to Supabase for Q&A retrieval.

**Logic**:
```python
session_path = get_session_path(state.session_id)

# Read findings from file-based memory
findings_ledger = read_findings_ledger(session_path)

# Compile full memory document
memory_document = compile_memory_document(
    findings=findings_ledger,
    session_logs=state.session_logs,
    hypotheses=state.hypotheses,
    schema=state.data_model,
    report_summary=generate_summary(state)
)

# Store in Supabase with embeddings
doc_id = supabase.store_document(
    session_id=state.session_id,
    content=memory_document,
    generate_embeddings=True
)

state.memory_document_id = doc_id
```

**Output**: Updates `state.memory_document_id`

---

#### Node 6: `report_generator`

**Purpose**: Compile validated explanations into a formatted markdown report.

**Tools Used**:
- `file_tools.write_markdown(session_path, content) → path`
- `file_tools.write_json(session_path, filename, data)`

**Report Structure**:
```markdown
# {Metric Name} Investigation Report

**Investigation Period**: {baseline} vs {comparison}
**Overall Change**: {change_pct}%

## Data Model

{schema_visualization}

## Analysis Performed

{summary_of_plan_execution}

## Explanations (Ranked by Likelihood)

### 1. {title} (Most Likely)

**Evidence**:
- {evidence_point_1}
- {evidence_point_2}

**Likelihood Reasoning**: {reasoning}

### 2. {title} (Likely)
...

## Recommended Next Steps

1. {actionable_recommendation_1}
2. {actionable_recommendation_2}

---
*Generated by Metric Drill-Down Agent*
```

**Output**: Updates `state.explanations`, `state.report_path`, `state.status = "completed"`

---

#### Node 8: `no_findings_report`

**Purpose**: Generate report when no explanations could be validated.

**Report includes**:
- What was analyzed
- Hypotheses that were tested and discarded
- Possible reasons (uniform change, data limitations, etc.)
- Suggestions for gathering additional data

**Output**: Updates `state.report_path`, `state.status = "no_findings"`

---

### Q&A Mode Handler (RAG-based)

Q&A uses RAG retrieval from the Supabase memory document created by `memory_dump`:

```python
def handle_qa_query(session_id: str, question: str) -> str:
    # Get memory document ID from session
    memory_doc_id = get_memory_document_id(session_id)

    # RAG retrieval from Supabase
    relevant_chunks = supabase.similarity_search(
        document_id=memory_doc_id,
        query=question,
        top_k=5
    )

    # Build context from retrieved chunks
    context = "\n\n".join([chunk.content for chunk in relevant_chunks])

    # Generate response with retrieved context
    response = llm.generate(
        prompt=QA_PROMPT.format(
            context=context,
            question=question,
            session_summary=get_session_summary(session_id)
        )
    )

    # Save to chat history (local file, not Supabase)
    save_chat_message(session_id, {"role": "user", "content": question})
    save_chat_message(session_id, {"role": "assistant", "content": response})

    return response
```

**Note**: The MCP container is destroyed after analysis. Q&A cannot execute new code - it can only retrieve information from the stored memory document.

---

### Agent Tools Specification

With the Memory Loop architecture, tools are simplified. Data analysis happens via MCP code execution, not pre-built tools.

| Tool | Function | Parameters | Returns |
|------|----------|------------|---------|
| **CSV Tools** (for schema inference) |
| `csv_tools.get_headers` | Read column headers | `file_path: str` | `List[str]` |
| `csv_tools.sample_rows` | Get sample data | `file_path: str, n: int = 100` | `List[dict]` |
| `csv_tools.get_row_count` | Count total rows | `file_path: str` | `int` |
| **File Tools** (for session artifacts) |
| `file_tools.write_json` | Write JSON artifact | `session_path: str, filename: str, data: dict` | `bool` |
| `file_tools.read_json` | Read JSON artifact | `session_path: str, filename: str` | `dict` |
| `file_tools.write_markdown` | Write report | `session_path: str, content: str` | `str (path)` |
| **MCP Client** (for code execution) |
| `mcp_client.create_container` | Create Docker container | `session_id: str` | `str (container_id)` |
| `mcp_client.upload_file` | Upload file to container | `container_id: str, file_path: str` | `bool` |
| `mcp_client.execute_code` | Run Python code | `container_id: str, code: str` | `{stdout, stderr, success}` |
| `mcp_client.destroy_container` | Cleanup container | `container_id: str` | `bool` |

---

### MCP Code Execution (Required)

The agent executes analysis code via an external Docker MCP server. This is **required** for MVP, not a future enhancement.

**Connection**: Uses existing Docker MCP server (e.g., official Anthropic MCP server)

**Container Environment**:
- Base image with pandas, numpy, scipy pre-installed
- Session-scoped workspace at `/workspace`
- CSV files uploaded at start of analysis_execution
- Container destroyed after memory dump

**Execution Flow**:
```
Agent generates Python code
    ↓
mcp_client.execute_code(container_id, code)
    ↓
MCP Server runs code in Docker container
    ↓
Returns stdout/stderr to agent
    ↓
Agent compresses result and continues
```

**Security**: Code runs in isolated container. No access to host filesystem or network beyond MCP protocol.

---

## Complexity Tracking

| Aspect | Decision | Justification |
|--------|----------|---------------|
| Three projects (frontend/backend/agent) | Required | Constitution Principle VI mandates clean separation |
| LangGraph for agent | Chosen over simple chain | Agent has iteration logic; graph structure matches workflow |
| File-based session storage | Chosen over database | Constitution V (ephemeral), VI (local-first); simplest AWS-transferable approach |
| MCP for code execution | Chosen over direct tools | Agent generates code dynamically; MCP provides sandboxed execution |
| Memory Loop architecture | Chosen over single-pass | Iterative analysis enables deeper investigation and hypothesis refinement |
| Supabase for Q&A memory | Required | RAG retrieval for Q&A; container destroyed after analysis |
| Compression per iteration | Required | Keeps working memory within ~6000 token budget |

---

## Next Steps

1. Generate `research.md` - technology decisions for dependencies
2. Generate `data-model.md` - entity field specifications
3. Generate `contracts/api.yaml` - OpenAPI specification
4. Generate `contracts/agent-tools.md` - tool interface documentation
5. Generate `quickstart.md` - developer setup guide
6. Run `/speckit.tasks` to generate implementation tasks
