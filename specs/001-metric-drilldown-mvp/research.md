# Technology Research: Metric Drill-Down Agent MVP

**Branch**: `001-metric-drilldown-mvp` | **Date**: 2025-12-17
**Reference**: [spec.md](./spec.md) | [plan.md](./plan.md)

## Purpose

This document captures technology decisions, library choices, and rationale for the Metric Drill-Down Agent MVP. All decisions are governed by the [Constitution](../../.specify/memory/constitution.md).

---

## Technology Stack Summary

| Layer | Technology | Version | Why This Choice |
|-------|------------|---------|-----------------|
| Frontend Runtime | Node.js | 20 LTS | Constitution requires Node.js; LTS for stability |
| Frontend Framework | Express | 4.x | Minimal, well-documented, HTMX-compatible |
| Frontend Interactivity | HTMX | 2.x | Constitution requires HTMX; progressive enhancement |
| Frontend Templates | EJS | 3.x | Simple, no build step, server-side rendering |
| Backend Framework | FastAPI | 0.109+ | Constitution requires FastAPI; async, Pydantic |
| Backend Validation | Pydantic | 2.x | Built into FastAPI; strict type validation |
| Agent Framework | LangGraph | 0.2+ | Graph-based agent orchestrator |
| LLM SDK | Claude Agent SDK | 1.x | Claude Agent SDK for iterative analysis via query() |
| LangChain Integration | langchain-anthropic | 0.2+ | LangGraph + Claude integration |
| MCP Server | Supabase MCP | - | File retrieval from Supabase storage |
| Code Execution | Native bash | - | Python scripts executed via bash (no container) |
| Markdown Rendering | marked (frontend) | 9.x | Browser-side markdown rendering |
| Testing (Python) | pytest | 8.x | Standard Python testing; fixtures, async support |
| Testing (Node) | Vitest | 1.x | Fast, ESM-native, minimal config |
| Database | Supabase | - | Required for memory documents + RAG retrieval |
| RAG Retrieval | supabase-py + pgvector | - | Similarity search for Q&A |

---

## Dependency Deep-Dive

### Frontend Dependencies

#### Express (v4.x)
**Purpose**: HTTP server, routing, middleware
**Why**: Mature, minimal, well-documented. Constitution requires Node.js but doesn't prescribe framework. Express is the simplest choice that supports HTMX patterns.
**Alternatives Rejected**:
- Fastify: Slightly more complex, HTMX examples sparse
- Koa: Less middleware ecosystem
- Hono: Newer, less documentation for server-rendered apps

#### HTMX (v2.x)
**Purpose**: Dynamic updates without custom JavaScript
**Why**: Constitution mandates HTMX. Enables server-side HTML fragments for file uploads, form validation, and chat.
**Key Features Used**:
- `hx-post`, `hx-delete`: Form submissions and file removal
- `hx-target`, `hx-swap`: Partial page updates
- `hx-trigger`: Event-based updates for chat polling
- `hx-indicator`: Loading states (minimal, per FR-023)

#### EJS (v3.x)
**Purpose**: Server-side templating
**Why**: No build step, simple syntax, partials support. Aligns with Constitution Principle I (understandable code).
**Alternatives Rejected**:
- Pug: Indentation-based syntax harder to read
- Handlebars: More complex, overkill for MVP
- React/Vue SSR: Build complexity violates Principle I

#### marked (v9.x)
**Purpose**: Client-side markdown rendering for reports
**Why**: Small footprint, GFM support, sanitization built-in.
**Usage**: Render `report.md` content in browser.

---

### Backend Dependencies

#### FastAPI (v0.109+)
**Purpose**: REST API framework
**Why**: Constitution mandates FastAPI. Async native, Pydantic integration, automatic OpenAPI docs.
**Key Features Used**:
- Path operations for all endpoints
- Dependency injection for session validation
- BackgroundTasks for cleanup jobs
- HTTPException for structured errors

#### Pydantic (v2.x)
**Purpose**: Request/response validation, settings management
**Why**: Bundled with FastAPI; strict validation prevents bad data reaching agent.
**Key Models**:
- `SessionCreate`, `SessionResponse`
- `FileUpload`, `FileMetadata`
- `InvestigationRequest`, `ReportResponse`
- `ChatMessage`, `ChatResponse`

#### python-multipart
**Purpose**: File upload parsing
**Why**: Required by FastAPI for `File` and `Form` parameters.

#### aiofiles
**Purpose**: Async file I/O
**Why**: Non-blocking file operations for CSV storage and artifact writing.

---

### Agent Dependencies

#### LangGraph (v0.2+)
**Purpose**: Agent workflow orchestration with Python orchestrator
**Why**: Graph-based state machine for sequencing investigation phases. The `analysis_execution` node uses a Python orchestrator loop that calls Claude Agent SDK `query()` once per hypothesis.
**Key Features Used**:
- `StateGraph`: Define nodes and edges
- `TypedDict` state: Typed investigation state
- Linear graph with analysis handled by Claude Agent SDK

**Alternative Rejected**:
- LangChain LCEL: Less flexible for complex state management
- CrewAI: Multi-agent overkill; single agent sufficient
- AutoGen: Conversation-based; not suited for structured analysis

#### langchain-anthropic (v0.2+)
**Purpose**: Claude integration for LangGraph
**Why**: Constitution requires Claude models; this package provides `ChatAnthropic` class for LangGraph nodes.
**Configuration**:
```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0.3,  # Lower for consistent analysis
    max_tokens=4096
)
```

#### anthropic (v0.40+)
**Purpose**: Direct API access
**Why**: Native SDK; `langchain-anthropic` uses this under the hood.
**Usage**: Direct calls for compression prompts.

#### Claude Agent SDK (v1.x)
**Purpose**: Iterative analysis within hypothesis investigation sessions
**Why**: Provides `query()` function that handles the agentic loop internally. Each hypothesis gets its own `query()` call, which iterates until the agent reaches a conclusion.
**Key Features Used**:
- `query()`: Async generator that yields messages as agent works
- `ClaudeAgentOptions`: Configure allowed tools, max turns, working directory
- `ResultMessage`: Final result with metrics (duration, tokens, cost)

**Configuration**:
```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt=hypothesis_prompt,
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Bash", "Glob"],
        system_prompt=ANALYSIS_SYSTEM_PROMPT,
        cwd=session_path,
        max_turns=10,
        permission_mode="acceptEdits"
    )
):
    # Process streamed messages
    pass
```

**Python Execution**:
- Agent writes scripts to `/analysis/scripts/` directory
- Executes via native bash: `python scripts/001_analysis.py`
- Required packages (pandas, numpy, scipy) installed in agent environment

#### supabase-py (v2.x)
**Purpose**: Supabase client for memory storage and RAG retrieval
**Why**: Required for storing memory documents after analysis, and RAG-based Q&A.
**Key Operations**:
- `store_document()`: Store memory document with embeddings
- `similarity_search()`: Find relevant chunks for Q&A

---

### Testing Dependencies

#### pytest (v8.x)
**Purpose**: Python test framework
**Why**: Standard choice; fixtures, parameterization, async support.
**Plugins**:
- `pytest-asyncio`: Test async endpoints
- `pytest-cov`: Coverage reporting

#### httpx
**Purpose**: Async HTTP client for testing FastAPI
**Why**: FastAPI recommends; async compatible with `TestClient`.

#### Vitest (v1.x)
**Purpose**: Node.js test framework
**Why**: Fast, ESM-native, minimal config. Better DX than Jest for simple projects.
**Usage**: Test Express routes, HTMX response fragments.

---

## Infrastructure Decisions

### Session Storage

**Decision**: File-based session storage (not database)
**Why**:
- Constitution Principle V (ephemeral data)
- Constitution Principle VI (local-first, AWS-transferable)
- Simplest approach for MVP; no database setup required

**Structure**:
```
sessions/{uuid}/
├── metadata.json      # Session status, timestamps
├── context.json       # Investigation context from form
├── files/             # Uploaded CSVs + metadata
├── analysis/
│   ├── progress.txt   # High-level investigation log
│   ├── hypotheses.json  # All hypotheses with status
│   ├── schema.json    # Inferred data model
│   ├── metric_requirements.json
│   ├── scripts/       # Python scripts written by agent
│   ├── logs/          # Per-hypothesis session logs
│   │   ├── session_H1_*.md   # Human-readable log
│   │   └── session_H1_*.json # Structured summary
│   ├── artifacts/     # Analysis outputs (CSVs, charts)
│   └── findings_ledger.json  # Incrementally built findings
├── results/           # Final explanations
├── report.md          # Final output
└── chat/              # Q&A history (local)
```

**Cleanup**: Background task scans for expired sessions (24h default).

### Supabase Usage

**Decision**: Required for memory storage and RAG retrieval
**Why**: After analysis completes, all agent memory (findings, iterations, reasoning) is compiled into a document and stored in Supabase. Q&A uses RAG similarity search against this document.

**What's stored in Supabase**:
- Memory documents with embeddings (pgvector)
- Session metadata (optional)

**What's NOT stored in Supabase**:
- Raw CSV files (stay in session directory)
- User accounts (explicitly non-goal per Constitution)
- Investigation history across sessions

### Supabase MCP Server

**Decision**: Required for file retrieval from Supabase storage
**Why**: Users upload CSV files through the UI, which stores them in Supabase. The agent needs to retrieve these files before analysis.

**MCP Server Selection**: Research and select an established MCP server that can:
1. Connect to Supabase storage
2. Retrieve uploaded files by session ID
3. Copy files to local session directories

**Candidates**:
- Official Supabase MCP server (if available)
- Community MCP servers for Supabase/PostgreSQL
- Generic file storage MCP servers

**Integration Point**: Called at start of `analysis_execution` node

### Native Python Execution

**Decision**: Agent executes Python scripts via native bash (no Docker container)
**Why**: Simpler architecture, faster execution, no container overhead.

**How it works**:
1. Agent writes Python scripts to `/analysis/scripts/` directory
2. Agent runs scripts via bash: `python scripts/NNN_analysis.py`
3. Output captured from stdout/stderr

**Required Environment**: pandas, numpy, scipy installed in agent runtime environment

---

## LLM Configuration

### Model Selection

**Primary**: `claude-sonnet-4-20250514` (Claude Sonnet)
**Why**: Best balance of speed and quality for analysis tasks. Opus is slower; Haiku may lack reasoning depth.

**Fallback Strategy**: None (Constitution: "no multi-model fallbacks")

### Retry Configuration

Per spec clarification (FR edge case):
```python
RETRY_CONFIG = {
    "max_attempts": 3,
    "initial_delay_seconds": 1.0,
    "backoff_multiplier": 2.0,  # 1s, 2s, 4s
    "retryable_status_codes": [429, 500, 502, 503, 504]
}
```

### Rate Limiting

Claude API limits (standard tier):
- 60 requests/minute
- 100K tokens/minute

**Mitigation**: Memory Loop is sequential (one LLM call per iteration). With max 15 iterations plus compression calls, worst case is ~30 LLM calls per investigation, well within limits.

---

## Security Considerations

### File Uploads

- **Size Limit**: 50MB per file (FR edge case)
- **Type Validation**: Must have `.csv` extension
- **Header Validation**: First row must be headers (FR edge case)
- **Storage**: Session directory only; never in shared paths
- **Cleanup**: Deleted with session after timeout

### Input Sanitization

- All user text (descriptions, context, prompts) passed to LLM
- No SQL injection risk (pandas, not database)
- No XSS risk (EJS auto-escapes; markdown sanitized)

### Session Security

- Session IDs: UUID v4 (unpredictable)
- No authentication (MVP); sessions are anonymous
- No cross-session data access

---

## Performance Considerations

### CSV Processing

- **Target**: 500K rows per file (SC-001: 15min total)
- **Approach**: pandas with chunked reading if needed
- **Memory**: Load one DataFrame at a time; release after analysis

### LLM Calls (Claude Agent SDK Architecture)

**Pre-Analysis Nodes** (fixed cost):
- **Schema inference**: 1 call (~5-10s)
- **Metric identification**: 1 call (~2-3s)
- **Hypothesis generation**: 1 call (~5-10s)

**Analysis Execution** (Claude Agent SDK query()):
- **Per hypothesis**: 1 `query()` call with up to 10 turns
- **Typical hypotheses**: 5-7 generated
- **Each turn**: Agent reasons, writes script, executes, interprets
- **Logging**: Agent writes markdown log per hypothesis

**Post-Analysis Nodes** (fixed cost):
- **Memory dump**: Compilation, no LLM call
- **Report generation**: 1 call (~5-10s)

**Token Budget**:
- Per hypothesis session: ~10K-20K tokens (depends on complexity)
- 5-7 hypotheses: ~50K-140K tokens total
- Max turns per hypothesis: 10
- Target: Complete investigation in < 15 minutes (SC-001)

**Cost Tracking**:
```python
# Each ResultMessage includes metrics
if isinstance(message, ResultMessage):
    print(f"Duration: {message.duration_ms}ms")
    print(f"Turns: {message.num_turns}")
    print(f"Tokens: {message.total_tokens}")
    print(f"Cost: ${message.total_cost_usd}")
```

### Frontend

- **HTMX partials**: Small HTML fragments (~1-5KB)
- **Report rendering**: Single markdown file (~20-50KB)
- **No heavy JavaScript**: No SPA bundle overhead

---

## Development Environment

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Node.js | 20.x LTS | Frontend runtime |
| Python | 3.11+ | Backend and agent |
| Docker | 24+ | Local development containers |
| Docker Compose | 2.x | Multi-container orchestration |

### Environment Variables

```bash
# .env.example
# Frontend
BACKEND_URL=http://localhost:8000

# Backend
SESSION_STORAGE_PATH=./sessions
SESSION_TIMEOUT_HOURS=24
MAX_FILE_SIZE_MB=50

# Agent
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
LLM_MAX_RETRIES=3
ANALYSIS_MAX_TURNS=10  # Max turns per hypothesis

# Supabase (required for file storage + memory + RAG)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...  # For file retrieval MCP
```

---

## Known Limitations

1. **No streaming**: Report delivered on completion, not incrementally
2. **No persistence**: Investigation lost after session expires
3. **Single LLM**: No fallback if Claude API unavailable
4. **File size**: 50MB limit may exclude large datasets
5. **No auth**: Anyone with session ID can access (MVP acceptable)

---

## References

- [Constitution](../../.specify/memory/constitution.md)
- [Feature Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [HTMX Documentation](https://htmx.org/)
