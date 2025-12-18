# Implementation Plan: Metric Drill-Down Agent MVP

**Branch**: `001-metric-drilldown-mvp` | **Date**: 2025-12-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-metric-drilldown-mvp/spec.md`

## Summary

Build an AI-powered metric investigation tool that enables data scientists to upload CSV files, provide metric context, and receive ranked explanations for unexpected metric movements. The system follows a three-tier architecture: Node.js/HTMX frontend for form-based input, FastAPI backend for API orchestration and session management, and a LangGraph-based AI agent for data analysis and explanation generation.

## Technical Context

**Language/Version**: Python 3.11+ (Backend/Agent), Node.js 20+ (Frontend)
**Primary Dependencies**: FastAPI, LangGraph, Anthropic Claude SDK, HTMX, MCP Client, Supabase-py
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
- ✅ Agent: LangGraph + Claude SDK (using LangChain's Anthropic integration)
- ✅ Tools: Docker MCP server for code execution (required)
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
                                   │  │  START → Schema → Plan → Hypothesize →   │   │
                                   │  │         Analyze → [Decision] → Report    │   │
                                   │  │                      ↓                    │   │
                                   │  │                  Iterate (max 2)          │   │
                                   │  └───────────────────────────────────────────┘   │
                                   │                                                   │
                                   │  ┌───────────────────────────────────────────┐   │
                                   │  │           MCP CODE EXECUTION               │   │
                                   │  │  Docker container with pandas/numpy/scipy │   │
                                   │  │  Agent generates code → MCP executes      │   │
                                   │  └───────────────────────────────────────────┘   │
                                   └──────────────────────────┬────────────────────────┘
                                                              │
                                          ┌───────────────────┼───────────────────┐
                                          ▼                   ▼                   ▼
                                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                                   │   Claude    │    │   Session   │    │  Supabase   │
                                   │     API     │    │   Storage   │    │  (Memory +  │
                                   │ (Anthropic) │    │   (Files)   │    │   RAG)      │
                                   └─────────────┘    └─────────────┘    └─────────────┘
                                                                                │
                                                              ┌─────────────────┘
                                                              ▼
                                                       ┌─────────────┐
                                                       │  Docker MCP │
                                                       │   Server    │
                                                       │  (External) │
                                                       └─────────────┘
```

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW DIAGRAM                                    │
└──────────────────────────────────────────────────────────────────────────────────┘

1. FORM SUBMISSION
   Browser → [CSV Files + Descriptions + Context + SQL + Date Ranges] → Frontend
   Frontend → POST /api/sessions/create → Backend (creates session directory)
   Frontend → POST /api/sessions/{id}/files → Backend (stores each file)

2. INVESTIGATION START
   Frontend → POST /api/sessions/{id}/investigate → Backend
   Backend → Validates session has required data
   Backend → Invokes Agent with InvestigationState

3. AGENT EXECUTION (detailed in Agent Design section)
   Agent Graph executes: Schema → Plan → Hypothesize → Analyze → Report
   Agent writes artifacts to /sessions/{id}/ throughout execution

4. REPORT DELIVERY
   Agent → Writes /sessions/{id}/report.md
   Backend → Returns report content + session status
   Frontend → Renders markdown in report view + enables chat panel

5. MEMORY DUMP (after analysis completes)
   Agent → Compiles all findings, iterations, reasoning into memory document
   Agent → Stores memory document in Supabase with embeddings
   MCP Container → Destroyed after memory dump complete

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
│   │   ├── analysis_planner.py      # Create investigation plan
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
│   ├── files/
│   │   ├── {file_id}.csv
│   │   └── {file_id}_meta.json
│   ├── analysis/
│   │   ├── schema.json
│   │   ├── plan.json
│   │   ├── hypotheses/
│   │   │   └── hyp_NNN.json         # Hypothesis with status
│   │   ├── findings_ledger.json     # Compressed findings list
│   │   ├── iterations/
│   │   │   └── iter_NNN.json        # Full iteration log
│   │   └── full_outputs/
│   │       └── output_NNN.txt       # Raw MCP execution output
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
│  │ Metric Definition: [textarea - SQL or description]        │  │
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
| POST | `/api/sessions/{id}/investigate` | Start investigation | `{context, sql, dates, prompt}` | `{status: "running"}` |
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
├── context.json               # {business_context, metric_sql, dates, prompt}
├── analysis/
│   ├── schema.json            # Inferred data model
│   ├── plan.json              # Analysis plan
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
    """Compressed finding from a single analysis iteration."""
    finding_id: str
    iteration: int
    summary: str  # 2-3 sentence compressed summary
    full_output_ref: str  # Path to raw output file
    hypothesis_affected: str  # Which hypothesis this relates to
    created_at: str

class IterationLog(TypedDict):
    """Full log of a single memory loop iteration."""
    iteration: int
    decision: Literal["ANALYZE", "DRILL_DOWN", "PIVOT", "CONCLUDE"]
    code_executed: str  # Python code sent to MCP
    raw_output: str  # stdout/stderr from execution
    compressed_summary: str  # Finding summary
    hypothesis_status_changes: dict  # {hyp_id: new_status}

class Explanation(TypedDict):
    rank: int
    title: str
    likelihood: Literal["Most Likely", "Likely", "Possible", "Less Likely"]
    evidence: List[dict]
    reasoning: str
    causal_story: str

class InvestigationState(TypedDict):
    # Input (set at start)
    session_id: str
    files: List[FileInfo]
    business_context: str
    metric_sql: str
    baseline_period: DateRange
    comparison_period: DateRange
    investigation_prompt: Optional[str]

    # Schema Inference Output
    data_model: Optional[dict]  # {tables, relationships}
    selected_dimensions: Optional[List[str]]

    # Planning Output
    analysis_plan: Optional[dict]

    # Hypothesis Generation Output
    hypotheses: Annotated[List[Hypothesis], add]

    # Memory Loop State (analysis_execution node)
    container_id: Optional[str]  # MCP container reference
    findings_ledger: Annotated[List[Finding], add]  # Compressed findings
    iteration_logs: Annotated[List[IterationLog], add]  # Full iteration history
    loop_iteration: int  # Current loop count (0-15)
    stall_count: int  # Consecutive similar outputs

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
│                         with Memory Loop Architecture                            │
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
                         │   analysis_planner    │  Node 2
                         │                       │
                         │ • Review data model   │
                         │ • Parse metric SQL    │
                         │ • Create investigation│
                         │   plan                │
                         └───────────┬───────────┘
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
    │                         Memory Loop Architecture                            │
    ├────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
    │   │  INITIALIZE │────►│ MCP Create  │────►│ Upload CSVs │                  │
    │   │             │     │ Container   │     │ to Container│                  │
    │   └─────────────┘     └─────────────┘     └──────┬──────┘                  │
    │                                                   │                         │
    │                              ┌────────────────────┘                         │
    │                              ▼                                              │
    │   ┌──────────────────────────────────────────────────────────────────────┐ │
    │   │                    MEMORY LOOP (max 15 iterations)                    │ │
    │   │                                                                       │ │
    │   │    ┌───────────────────────────────────────────────────────────┐     │ │
    │   │    │ 1. BUILD WORKING MEMORY (~6000 tokens)                    │     │ │
    │   │    │    • Objective: metric, question, hypothesis status       │     │ │
    │   │    │    • Compressed findings from ledger                      │     │ │
    │   │    │    • Last execution result                                │     │ │
    │   │    └───────────────────────────┬───────────────────────────────┘     │ │
    │   │                                │                                      │ │
    │   │                                ▼                                      │ │
    │   │    ┌───────────────────────────────────────────────────────────┐     │ │
    │   │    │ 2. LLM DECISION                                           │     │ │
    │   │    │    Output: {decision, code, hypothesis_updates}           │     │ │
    │   │    │    Decisions:                                             │     │ │
    │   │    │    • ANALYZE: Run code to test hypothesis                 │     │ │
    │   │    │    • DRILL_DOWN: Deeper analysis on promising segment     │     │ │
    │   │    │    • PIVOT: Try different angle, new hypothesis           │     │ │
    │   │    │    • CONCLUDE: Sufficient evidence gathered               │     │ │
    │   │    └───────────────────────────┬───────────────────────────────┘     │ │
    │   │                                │                                      │ │
    │   │              ┌─────────────────┼─────────────────┐                    │ │
    │   │              ▼                 ▼                 ▼                    │ │
    │   │    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │ │
    │   │    │  ANALYZE/   │   │  CONCLUDE   │   │ EXIT (max   │               │ │
    │   │    │  DRILL_DOWN/│   │             │   │ iter/stall) │               │ │
    │   │    │  PIVOT      │   └──────┬──────┘   └──────┬──────┘               │ │
    │   │    └──────┬──────┘          │                 │                       │ │
    │   │           │                 │                 │                       │ │
    │   │           ▼                 │                 │                       │ │
    │   │    ┌───────────────┐        │                 │                       │ │
    │   │    │ 3. EXECUTE    │        │                 │                       │ │
    │   │    │    CODE       │        │                 │                       │ │
    │   │    │ via MCP Server│        │                 │                       │ │
    │   │    │ (pandas/numpy)│        │                 │                       │ │
    │   │    └───────┬───────┘        │                 │                       │ │
    │   │            │                │                 │                       │ │
    │   │            ▼                │                 │                       │ │
    │   │    ┌───────────────┐        │                 │                       │ │
    │   │    │ 4. COMPRESS   │        │                 │                       │ │
    │   │    │    RESULT     │        │                 │                       │ │
    │   │    │ (2-3 sentences)│       │                 │                       │ │
    │   │    └───────┬───────┘        │                 │                       │ │
    │   │            │                │                 │                       │ │
    │   │            ▼                │                 │                       │ │
    │   │    ┌───────────────┐        │                 │                       │ │
    │   │    │ 5. UPDATE     │        │                 │                       │ │
    │   │    │ • findings_ledger     │                 │                       │ │
    │   │    │ • hypothesis status   │                 │                       │ │
    │   │    │ • stall detection     │                 │                       │ │
    │   │    └───────┬───────┘        │                 │                       │ │
    │   │            │                │                 │                       │ │
    │   │            └────────────────┼─────────────────┤                       │ │
    │   │                   LOOP      │                 │                       │ │
    │   └─────────────────────────────┼─────────────────┼───────────────────────┘ │
    │                                 │                 │                         │
    │                                 ▼                 ▼                         │
    │                          ┌─────────────────────────────┐                   │
    │                          │ CLEANUP: Destroy Container  │                   │
    │                          └─────────────────────────────┘                   │
    │                                                                             │
    └───────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                                        ▼
                         ┌───────────────────────┐
                         │     memory_dump       │  Node 5
                         │                       │
                         │ • Compile findings    │
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

### Memory Loop Configuration

```python
MEMORY_LOOP_CONFIG = {
    "max_iterations": 15,           # Maximum loop iterations
    "stall_threshold": 3,           # Consecutive similar outputs before exit
    "working_memory_budget": 6000,  # Approximate tokens per iteration
    "compression_model": "claude-sonnet-4-20250514",  # Same as decision model
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

#### Node 2: `analysis_planner`

**Purpose**: Create a structured plan for investigating the metric.

**Tools Used**: None (LLM reasoning only)

**LLM Prompt** (simplified):
```
Create an analysis plan for this metric investigation.

Metric: {metric_sql}
Context: {business_context}
Data Model: {data_model}
Dimensions: {selected_dimensions}
Periods: {baseline} vs {comparison}

Plan must include:
1. Initial Data Exploration steps
2. Key hypotheses to investigate
3. Evidence criteria for ranking explanations

Output JSON plan.
```

**Output**: Updates `state.analysis_plan`

---

#### Node 3: `hypothesis_generator`

**Purpose**: Generate potential explanations for the metric movement.

**Tools Used**: None (LLM reasoning only)

**LLM Prompt** (simplified):
```
Generate 5-7 hypotheses for why this metric changed.

Metric Change: {observed_change}
Context: {business_context}
User Focus: {investigation_prompt}
Available Dimensions: {dimensions}

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

#### Node 4: `analysis_execution` (Memory Loop)

**Purpose**: Iteratively analyze data to validate/invalidate hypotheses using MCP code execution.

**Architecture**: Internal loop with bounded context (see diagram above).

**Phase 1: Initialize**
```python
# Create MCP container
container_id = mcp_client.create_container(session_id)

# Upload CSV files to container workspace
for file in state.files:
    mcp_client.upload_file(container_id, file.path)

state.container_id = container_id
state.loop_iteration = 0
state.stall_count = 0
```

**Phase 2: Memory Loop** (up to 15 iterations)

Each iteration:

1. **Build Working Memory** (~6000 tokens):
```python
working_memory = build_context(
    objective=f"Investigate {state.metric_sql} change",
    hypothesis_status={h.id: h.status for h in state.hypotheses},
    compressed_findings=state.findings_ledger[-10:],  # Last 10 findings
    last_result=state.iteration_logs[-1] if state.iteration_logs else None
)
```

2. **LLM Decision**:
```python
decision_prompt = ANALYSIS_DECISION_PROMPT.format(
    working_memory=working_memory,
    available_files=list_container_files(container_id)
)

response = llm.generate(decision_prompt)
# Returns: {decision, code, hypothesis_updates, reasoning}
```

3. **Execute Code** (for ANALYZE/DRILL_DOWN/PIVOT):
```python
if response.decision != "CONCLUDE":
    result = mcp_client.execute_code(container_id, response.code)
    # result: {stdout, stderr, success}
```

4. **Compress Result**:
```python
compressed = llm.generate(COMPRESSION_PROMPT.format(
    code=response.code,
    output=result.stdout,
    hypothesis=current_hypothesis
))
# Returns: 2-3 sentence summary of what was learned
```

5. **Update State**:
```python
# Add finding to ledger
state.findings_ledger.append(Finding(
    finding_id=f"find_{state.loop_iteration}",
    iteration=state.loop_iteration,
    summary=compressed,
    full_output_ref=save_full_output(result),
    hypothesis_affected=response.hypothesis_updates.get("id")
))

# Update hypothesis statuses
for hyp_id, new_status in response.hypothesis_updates.items():
    update_hypothesis_status(state, hyp_id, new_status)

# Stall detection
if is_similar_to_previous(compressed, state.findings_ledger):
    state.stall_count += 1
else:
    state.stall_count = 0

state.loop_iteration += 1
```

**Exit Conditions**:
- `response.decision == "CONCLUDE"`
- `state.loop_iteration >= 15`
- `state.stall_count >= 3`

**Phase 3: Cleanup**
```python
mcp_client.destroy_container(container_id)
state.container_id = None
```

**Output**: Updates `state.findings_ledger`, `state.iteration_logs`, hypothesis statuses

---

#### Node 5: `memory_dump`

**Purpose**: Persist all analysis memory to Supabase for Q&A retrieval.

**Logic**:
```python
# Compile full memory document
memory_document = compile_memory_document(
    findings=state.findings_ledger,
    iterations=state.iteration_logs,
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
