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
| Agent Framework | LangGraph | 0.2+ | Graph-based agent with Memory Loop architecture |
| LLM SDK | Anthropic | 0.40+ | Constitution requires Claude SDK |
| LangChain Integration | langchain-anthropic | 0.2+ | LangGraph + Claude integration |
| MCP Client | mcp | 1.x | Code execution in Docker containers |
| Code Execution | Docker MCP Server | - | External server for sandboxed pandas/numpy execution |
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
**Purpose**: Agent workflow orchestration with Memory Loop
**Why**: Graph-based state machine with internal loops for iterative analysis. The `analysis_execution` node runs an internal Memory Loop (up to 15 iterations) while the outer graph remains linear.
**Key Features Used**:
- `StateGraph`: Define nodes and edges
- `TypedDict` state: Typed investigation state with memory fields
- No external conditional edges needed (loop is internal to node)

**Alternative Rejected**:
- LangChain LCEL: Linear chains don't support internal loops
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

#### MCP Client (mcp v1.x)
**Purpose**: Connect to Docker MCP Server for code execution
**Why**: Agent generates Python code dynamically; MCP provides sandboxed execution.
**Key Operations**:
- `create_container(session_id)`: Create session-scoped container
- `upload_file(container_id, path)`: Upload CSVs to container
- `execute_code(container_id, code)`: Run Python, get stdout/stderr
- `destroy_container(container_id)`: Cleanup after analysis

**Container Pre-installed Packages** (in Docker MCP Server):
- pandas 2.x
- numpy
- scipy

**Note**: pandas is NOT imported in our agent code. It runs inside the MCP container.

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
├── files/             # Uploaded CSVs + metadata
├── analysis/
│   ├── schema.json    # Inferred data model
│   ├── plan.json      # Investigation plan
│   ├── hypotheses/    # Hypothesis files with status
│   ├── findings_ledger.json  # Compressed findings
│   ├── iterations/    # Full iteration logs
│   └── full_outputs/  # Raw MCP execution outputs
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

### Docker MCP Server

**Decision**: Required external service for code execution
**Why**: Agent generates Python code dynamically; needs sandboxed execution environment.

**Connection**: Uses existing Docker MCP server (e.g., official Anthropic MCP server)
**Container Lifecycle**: Created at start of `analysis_execution`, destroyed after `memory_dump`
**Pre-installed**: pandas, numpy, scipy in container image

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

### LLM Calls (Memory Loop Architecture)

**Pre-Loop Nodes** (fixed cost):
- **Schema inference**: 1 call (~5-10s)
- **Planning**: 1 call (~3-5s)
- **Hypothesis generation**: 1 call (~5-10s)

**Memory Loop** (variable, up to 15 iterations):
- **Decision call**: ~6000 tokens input (working memory) → code output
- **Compression call**: Raw output → 2-3 sentence summary
- **Per iteration**: ~10-15s (decision + execution + compression)

**Post-Loop Nodes** (fixed cost):
- **Memory dump**: Compilation, no LLM call
- **Report generation**: 1 call (~5-10s)

**Token Budget**:
- Working memory per iteration: ~6000 tokens
- Max iterations: 15
- Worst case total: ~90K input tokens + compression overhead
- Target: Complete investigation in < 15 minutes (SC-001)

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

# MCP Server
MCP_SERVER_URL=http://localhost:3000
MCP_TRANSPORT=stdio  # or http

# Supabase (required for memory storage + RAG)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
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
