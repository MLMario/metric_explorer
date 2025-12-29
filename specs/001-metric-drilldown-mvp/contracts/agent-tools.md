# Agent Tools Specification

**Branch**: `001-metric-drilldown-mvp` | **Date**: 2025-12-17
**Reference**: [plan.md](../plan.md) | [data-model.md](../data-model.md)

## Overview

This document defines the tool interfaces available to the AI Agent during investigation. The agent uses a **Claude Agent SDK Orchestrator architecture** where:

1. **Schema Inference** uses CSV tools to read file metadata locally
2. **Analysis Execution** uses Claude Agent SDK `query()` for iterative hypothesis investigation
3. **File Tools** manage session artifacts and logs locally
4. **Supabase MCP** retrieves uploaded files from Supabase storage

The Claude Agent SDK provides the iterative analysis capability - the agent writes Python scripts and executes them via native bash.

---

## Tool Categories

1. **CSV Tools** - Read CSV file metadata and samples (local, for schema inference)
2. **Claude Agent SDK** - Iterative hypothesis investigation via `query()`
3. **File Tools** - Session artifact management (local)
4. **Supabase MCP** - Retrieve files from Supabase storage

---

## CSV Tools

### `csv_tools.get_headers`

Read column headers from a CSV file.

**Signature**:
```python
def get_headers(file_path: str) -> List[str]
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_path` | `str` | Yes | Absolute path to CSV file |

**Returns**: `List[str]` - List of column header names

**Errors**:
| Error | Condition |
|-------|-----------|
| `FileNotFoundError` | File does not exist |
| `CSVParseError` | File is not valid CSV |
| `NoHeadersError` | File appears to have no headers |

**Example**:
```python
headers = csv_tools.get_headers("/sessions/abc123/files/users.csv")
# Returns: ["user_id", "name", "email", "created_at", "country"]
```

---

### `csv_tools.sample_rows`

Get a sample of rows from a CSV file for schema inference.

**Signature**:
```python
def sample_rows(
    file_path: str,
    n: int = 100,
    random_seed: Optional[int] = None
) -> List[Dict[str, Any]]
```

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `file_path` | `str` | Yes | - | Absolute path to CSV file |
| `n` | `int` | No | 100 | Number of rows to sample |
| `random_seed` | `int` | No | None | Seed for reproducible sampling |

**Returns**: `List[Dict[str, Any]]` - List of row dictionaries

**Behavior**:
- If file has <= n rows, returns all rows
- If file has > n rows, samples randomly
- Returns rows as dictionaries with header keys

**Example**:
```python
rows = csv_tools.sample_rows("/sessions/abc123/files/users.csv", n=5)
# Returns: [
#   {"user_id": "u001", "name": "Alice", "email": "alice@example.com", ...},
#   {"user_id": "u002", "name": "Bob", "email": "bob@example.com", ...},
#   ...
# ]
```

---

### `csv_tools.get_row_count`

Count total rows in a CSV file (excluding header).

**Signature**:
```python
def get_row_count(file_path: str) -> int
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_path` | `str` | Yes | Absolute path to CSV file |

**Returns**: `int` - Number of data rows

**Example**:
```python
count = csv_tools.get_row_count("/sessions/abc123/files/events.csv")
# Returns: 154203
```

---

## Claude Agent SDK

The analysis execution node uses Claude Agent SDK `query()` to perform iterative hypothesis investigation. Each hypothesis gets its own `query()` call.

### Architecture

```
┌─────────────────┐         ┌─────────────────┐
│ Python          │         │ Claude Agent    │
│ Orchestrator    │────────►│ SDK query()     │
│                 │         │                 │
│ - Picks hypo    │◄────────│ - Reads files   │
│ - Captures logs │         │ - Writes scripts│
│ - Updates ledger│         │ - Runs via bash │
└─────────────────┘         └─────────────────┘
```

### Configuration

```python
from claude_agent_sdk import query, ClaudeAgentOptions

ANALYSIS_CONFIG = {
    "max_turns": 10,  # Max iterations per hypothesis
    "allowed_tools": ["Read", "Write", "Bash", "Glob"],
    "permission_mode": "acceptEdits",
    "model": "claude-sonnet-4-20250514"
}
```

---

### `query()` - Hypothesis Investigation

Execute an iterative analysis session for a single hypothesis.

**Signature**:
```python
async for message in query(
    prompt: str,
    options: ClaudeAgentOptions
) -> AsyncIterator[Message]
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `prompt` | `str` | Yes | Investigation prompt with hypothesis details |
| `options` | `ClaudeAgentOptions` | Yes | Configuration for the session |

**ClaudeAgentOptions**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `allowed_tools` | `List[str]` | Tools the agent can use |
| `system_prompt` | `str` | System instructions for the agent |
| `cwd` | `str` | Working directory for file operations |
| `max_turns` | `int` | Maximum iterations (default: 10) |
| `permission_mode` | `str` | How to handle permissions |

**Message Types**:
- `AssistantMessage`: Agent's reasoning and tool calls
- `ToolResultBlock`: Output from tool execution
- `ResultMessage`: Final result with metrics

**Example**:
```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

async def investigate_hypothesis(session_path: str, hypothesis: Hypothesis):
    prompt = f"""
    Investigate this hypothesis about metric movement:

    Hypothesis: {hypothesis.title}
    Story: {hypothesis.causal_story}
    Expected pattern: {hypothesis.expected_pattern}
    Dimensions: {hypothesis.dimensions}

    Available files in /analysis/files/

    Either CONFIRM or RULE OUT this hypothesis with evidence.
    """

    session_log = []
    result = None

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Bash", "Glob"],
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            cwd=session_path,
            max_turns=10,
            permission_mode="acceptEdits"
        )
    ):
        session_log.append(message)

        if isinstance(message, ResultMessage):
            # Extract metrics from final message
            result = {
                "outcome": extract_outcome(message),  # CONFIRMED or RULED_OUT
                "evidence": extract_evidence(message),
                "duration_ms": message.duration_ms,
                "turns": message.num_turns,
                "total_tokens": message.total_tokens,
                "cost_usd": message.total_cost_usd
            }

    return session_log, result
```

---

### Agent Tools (within query session)

During `query()` execution, the agent has access to these Claude Code tools:

| Tool | Purpose |
|------|---------|
| `Read` | Read files from session directory |
| `Write` | Write Python scripts and logs |
| `Bash` | Execute Python scripts via bash |
| `Glob` | List files matching patterns |

**Workflow**:
1. Agent reads data files from `/analysis/files/`
2. Agent writes Python script to `/analysis/scripts/NNN_description.py`
3. Agent executes: `python /analysis/scripts/NNN_description.py`
4. Agent interprets output and decides next action
5. Agent writes session log to `/analysis/logs/`
6. Repeat until CONFIRMED or RULED_OUT

---

### System Prompt

The analysis agent receives this system prompt:

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

---

### Python Environment

Scripts executed via bash have access to:

| Package | Version | Purpose |
|---------|---------|---------|
| pandas | 2.x | DataFrame operations |
| numpy | latest | Numerical computation |
| scipy | latest | Statistical analysis |

These packages must be installed in the agent runtime environment.

---

## File Tools

### `file_tools.write_json`

Write a JSON artifact to session storage.

**Signature**:
```python
def write_json(
    session_path: str,
    filename: str,
    data: Dict[str, Any]
) -> bool
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `session_path` | `str` | Yes | Path to session directory |
| `filename` | `str` | Yes | Filename (can include subdirectory, e.g., `analysis/schema.json`) |
| `data` | `dict` | Yes | Data to write |

**Returns**: `bool` - True if written successfully

**Example**:
```python
file_tools.write_json(
    session_path="/sessions/abc123",
    filename="analysis/schema.json",
    data={"tables": [...], "relationships": [...]}
)
```

---

### `file_tools.read_json`

Read a JSON artifact from session storage.

**Signature**:
```python
def read_json(
    session_path: str,
    filename: str
) -> Dict[str, Any]
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `session_path` | `str` | Yes | Path to session directory |
| `filename` | `str` | Yes | Filename to read |

**Returns**: `Dict[str, Any]` - Parsed JSON data

**Errors**:
| Error | Condition |
|-------|-----------|
| `FileNotFoundError` | File does not exist |
| `JSONDecodeError` | File is not valid JSON |

---

### `file_tools.write_markdown`

Write the final report to session storage.

**Signature**:
```python
def write_markdown(
    session_path: str,
    content: str,
    filename: str = "report.md"
) -> str
```

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `session_path` | `str` | Yes | - | Path to session directory |
| `content` | `str` | Yes | - | Markdown content |
| `filename` | `str` | No | "report.md" | Output filename |

**Returns**: `str` - Full path to written file

**Example**:
```python
report_path = file_tools.write_markdown(
    session_path="/sessions/abc123",
    content="# Investigation Report\n\n## Summary\n..."
)
# Returns: "/sessions/abc123/report.md"
```

---

### `file_tools.list_artifacts`

List all artifacts in a session directory.

**Signature**:
```python
def list_artifacts(
    session_path: str,
    subdirectory: Optional[str] = None
) -> List[str]
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `session_path` | `str` | Yes | Path to session directory |
| `subdirectory` | `str` | No | Limit to subdirectory (e.g., "analysis/hypotheses") |

**Returns**: `List[str]` - List of artifact paths

**Example**:
```python
hypotheses = file_tools.list_artifacts(
    session_path="/sessions/abc123",
    subdirectory="analysis/hypotheses"
)
# Returns: ["hyp_001.json", "hyp_002.json", "hyp_003.json"]
```

---

## Supabase MCP

The Supabase MCP server retrieves uploaded files from Supabase storage before analysis begins.

### Purpose

Users upload CSV files through the UI, which stores them in Supabase storage. Before analysis, the orchestrator uses the Supabase MCP to fetch these files and copy them to the local session directory.

### Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ Python          │  MCP    │  Supabase MCP   │  HTTP   │   Supabase      │
│ Orchestrator    │────────►│    Server       │────────►│   Storage       │
│                 │         │                 │         │                 │
│ - Session init  │◄────────│ - List files    │◄────────│ - CSV files     │
│ - Copy files    │   files │ - Download      │  data   │ - Metadata      │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

### MCP Server Selection

**Task**: Research and select an established MCP server that can:
1. Connect to Supabase storage
2. List files by session ID
3. Download files to local directories

**Candidates**:
- Official Supabase MCP server (if available)
- Community MCP servers for Supabase/PostgreSQL
- Generic file storage MCP servers

---

### `supabase_mcp.list_session_files`

List all files uploaded for a session.

**Signature**:
```python
async def list_session_files(session_id: str) -> List[Dict[str, str]]
```

**Returns**:
```python
[
    {"file_id": "uuid", "name": "events.csv", "size_bytes": 1024000},
    {"file_id": "uuid", "name": "users.csv", "size_bytes": 512000}
]
```

---

### `supabase_mcp.download_file`

Download a file from Supabase to local path.

**Signature**:
```python
async def download_file(
    file_id: str,
    destination_path: str
) -> bool
```

---

### Integration Pattern

```python
async def retrieve_files_from_supabase(
    session_id: str,
    target_dir: str
) -> List[str]:
    """Fetch all session files from Supabase to local directory."""

    # List files in Supabase for this session
    files = await supabase_mcp.list_session_files(session_id)

    downloaded = []
    for file_info in files:
        dest_path = f"{target_dir}/{file_info['name']}"
        success = await supabase_mcp.download_file(
            file_id=file_info['file_id'],
            destination_path=dest_path
        )
        if success:
            downloaded.append(dest_path)

    return downloaded
```

---

## Memory Dump

After analysis completes, all memory is compiled and stored in Supabase for RAG retrieval:

```python
async def dump_memory_to_supabase(
    session_id: str,
    state: InvestigationState
) -> str:
    """Compile all analysis memory and store for RAG retrieval."""

    session_path = get_session_path(session_id)
    findings_ledger = read_findings_ledger(session_path)

    document = compile_memory_document(
        context=state['investigation_context'],
        data_model=state['data_model'],
        hypotheses=state['hypotheses'],
        findings=findings_ledger,
        session_logs=state['session_logs'],
        report=state['report_content']
    )

    embedding = await generate_embedding(document)

    doc_id = await supabase.insert(
        table='memory_documents',
        data={
            'session_id': session_id,
            'content': document,
            'embedding': embedding
        }
    )

    return doc_id
```

---

## Error Handling

All tools follow consistent error patterns:

```python
class ToolError(Exception):
    """Base error for tool operations."""
    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

# CSV Tool Errors
ERROR_FILE_NOT_FOUND = "FILE_NOT_FOUND"
ERROR_INVALID_CSV = "INVALID_CSV"
ERROR_NO_HEADERS = "NO_HEADERS"

# File Tool Errors
ERROR_WRITE_FAILED = "WRITE_FAILED"
ERROR_JSON_DECODE = "JSON_DECODE_ERROR"

# Claude Agent SDK Errors
ERROR_QUERY_TIMEOUT = "QUERY_TIMEOUT"
ERROR_MAX_TURNS_EXCEEDED = "MAX_TURNS_EXCEEDED"
ERROR_TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"

# Supabase MCP Errors
ERROR_FILE_DOWNLOAD_FAILED = "FILE_DOWNLOAD_FAILED"
ERROR_MCP_CONNECTION_FAILED = "MCP_CONNECTION_FAILED"
ERROR_SESSION_NOT_FOUND = "SESSION_NOT_FOUND"

# Memory Errors
ERROR_MEMORY_DUMP_FAILED = "MEMORY_DUMP_FAILED"
ERROR_EMBEDDING_FAILED = "EMBEDDING_FAILED"
```

### Claude Agent SDK Error Recovery

```python
async def investigate_with_retry(
    hypothesis: Hypothesis,
    session_path: str,
    max_retries: int = 2
) -> Tuple[SessionLog, InvestigationResult]:
    """Run hypothesis investigation with retry on transient failures."""
    for attempt in range(max_retries + 1):
        try:
            session_log, result = await run_hypothesis_investigation(
                session_path=session_path,
                hypothesis=hypothesis
            )
            return session_log, result
        except QueryTimeoutError:
            if attempt == max_retries:
                raise
            # Reduce max_turns for retry
            hypothesis.max_turns = max(5, hypothesis.max_turns - 2)
            await asyncio.sleep(1.0 * (attempt + 1))
    raise ToolError(ERROR_QUERY_TIMEOUT, "Investigation failed after retries")
```

### Supabase MCP Error Recovery

```python
async def download_with_retry(
    file_id: str,
    destination_path: str,
    max_retries: int = 2
) -> bool:
    """Download file with retry on transient failures."""
    for attempt in range(max_retries + 1):
        try:
            success = await supabase_mcp.download_file(file_id, destination_path)
            if success:
                return True
        except MCPConnectionError:
            if attempt == max_retries:
                raise
            await asyncio.sleep(1.0 * (attempt + 1))
    return False
```

---

## Tool Summary

| Category | Tool | Purpose |
|----------|------|---------|
| CSV | `csv_tools.get_headers` | Read column headers |
| CSV | `csv_tools.sample_rows` | Get sample data for schema inference |
| CSV | `csv_tools.get_row_count` | Count rows in file |
| Claude SDK | `query()` | Iterative hypothesis investigation |
| Claude SDK | `ClaudeAgentOptions` | Configure investigation session |
| Supabase MCP | `supabase_mcp.list_session_files` | List uploaded files for session |
| Supabase MCP | `supabase_mcp.download_file` | Download file to local path |
| File | `file_tools.write_json` | Write JSON artifacts |
| File | `file_tools.read_json` | Read JSON artifacts |
| File | `file_tools.write_markdown` | Write report |
| File | `file_tools.list_artifacts` | List session artifacts |
| Memory | `dump_memory_to_supabase` | Store memory document for RAG |
