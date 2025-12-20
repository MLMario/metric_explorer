# Agent Tools Specification

**Branch**: `001-metric-drilldown-mvp` | **Date**: 2025-12-17
**Reference**: [plan.md](../plan.md) | [data-model.md](../data-model.md)

## Overview

This document defines the tool interfaces available to the AI Agent during investigation. The agent uses a **Memory Loop architecture** where:

1. **Schema Inference** uses CSV tools to read file metadata locally
2. **Analysis Execution** sends Python code to an external MCP server for sandboxed execution
3. **Compression** summarizes raw outputs into memory-efficient findings
4. **File Tools** manage session artifacts locally

The agent does NOT import pandas directly. All DataFrame operations run inside Docker containers via MCP.

---

## Tool Categories

1. **CSV Tools** - Read CSV file metadata and samples (local, for schema inference)
2. **MCP Code Execution** - Execute Python code in Docker containers (external)
3. **File Tools** - Session artifact management (local)
4. **Compression** - Summarize raw outputs for memory efficiency

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

## MCP Code Execution

The agent executes analysis code via an external MCP server running Docker containers. This provides sandboxed execution for dynamically generated Python code.

### Architecture

```
┌─────────────────┐         ┌─────────────────┐
│    Agent        │  MCP    │  Docker MCP     │
│   (LangGraph)   │ ──────► │    Server       │
│                 │  stdio  │                 │
│ - Generates code│◄─────── │ - pandas 2.x    │
│ - Receives output         │ - numpy         │
│                 │         │ - scipy         │
└─────────────────┘         └─────────────────┘
```

### Connection

Uses existing Docker MCP server (e.g., official Anthropic MCP server for code execution).

**Configuration**:
```python
MCP_CONFIG = {
    "transport": "stdio",  # or "http"
    "server_url": "http://localhost:3000",  # if HTTP
    "timeout_seconds": 60,
}
```

---

### `mcp_client.create_container`

Create a persistent Docker container for the investigation session.

**Signature**:
```python
async def create_container(session_id: str) -> str
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `session_id` | `str` | Yes | Session ID for container naming |

**Returns**: `str` - Container ID for subsequent operations

**Behavior**:
- Creates Docker container with pre-installed packages (pandas, numpy, scipy)
- Container persists across multiple code executions
- Returns unique container ID

**Example**:
```python
container_id = await mcp_client.create_container("abc123")
# Returns: "mcp_container_abc123_1702850400"
```

---

### `mcp_client.upload_files`

Upload CSV files to the container workspace before analysis.

**Signature**:
```python
async def upload_files(
    container_id: str,
    files: List[Dict[str, str]]
) -> bool
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `container_id` | `str` | Yes | Container ID from `create_container` |
| `files` | `List[Dict]` | Yes | List of `{"local_path": str, "container_path": str}` |

**Returns**: `bool` - True if all files uploaded successfully

**Example**:
```python
await mcp_client.upload_files(
    container_id="mcp_container_abc123_1702850400",
    files=[
        {"local_path": "/sessions/abc123/files/events.csv", "container_path": "/workspace/events.csv"},
        {"local_path": "/sessions/abc123/files/users.csv", "container_path": "/workspace/users.csv"}
    ]
)
```

---

### `mcp_client.execute_code`

Execute Python code in the container and return output.

**Signature**:
```python
async def execute_code(
    container_id: str,
    code: str
) -> Dict[str, Any]
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `container_id` | `str` | Yes | Container ID |
| `code` | `str` | Yes | Python code to execute |

**Returns**:
```python
{
    "success": bool,
    "stdout": str,       # Standard output from code execution
    "stderr": str,       # Standard error (if any)
    "execution_time_ms": int
}
```

**Behavior**:
- Code has access to pandas, numpy, scipy
- Files uploaded via `upload_files` are in `/workspace/`
- Variables persist between executions in same container
- Timeout after 60 seconds per execution

**Example**:
```python
result = await mcp_client.execute_code(
    container_id="mcp_container_abc123_1702850400",
    code="""
import pandas as pd

df = pd.read_csv('/workspace/events.csv')
baseline = df[(df['date'] >= '2025-11-24') & (df['date'] <= '2025-11-30')]
comparison = df[(df['date'] >= '2025-12-01') & (df['date'] <= '2025-12-07')]

baseline_dau = baseline.groupby('date')['user_id'].nunique().mean()
comparison_dau = comparison.groupby('date')['user_id'].nunique().mean()

print(f"Baseline DAU: {baseline_dau:.0f}")
print(f"Comparison DAU: {comparison_dau:.0f}")
print(f"Change: {(comparison_dau - baseline_dau) / baseline_dau * 100:.1f}%")
"""
)
# Returns: {
#   "success": True,
#   "stdout": "Baseline DAU: 95000\\nComparison DAU: 87000\\nChange: -8.4%",
#   "stderr": "",
#   "execution_time_ms": 1250
# }
```

---

### `mcp_client.list_workspace`

List files in the container workspace.

**Signature**:
```python
async def list_workspace(container_id: str) -> List[str]
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `container_id` | `str` | Yes | Container ID |

**Returns**: `List[str]` - List of file paths in workspace

**Example**:
```python
files = await mcp_client.list_workspace("mcp_container_abc123_1702850400")
# Returns: ["/workspace/events.csv", "/workspace/users.csv"]
```

---

### `mcp_client.destroy_container`

Cleanup container after analysis completes.

**Signature**:
```python
async def destroy_container(container_id: str) -> bool
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `container_id` | `str` | Yes | Container ID to destroy |

**Returns**: `bool` - True if destroyed successfully

**Behavior**:
- Removes container and all workspace data
- Should be called after `memory_dump` node completes
- Releases Docker resources

---

### Pre-installed Packages

The MCP container image includes:

| Package | Version | Purpose |
|---------|---------|---------|
| pandas | 2.x | DataFrame operations |
| numpy | latest | Numerical computation |
| scipy | latest | Statistical analysis |

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

## Compression

After each MCP code execution, raw output is compressed to a 2-3 sentence summary for memory efficiency.

### `compression.summarize_output`

Compress raw code execution output to a concise finding summary.

**Signature**:
```python
async def summarize_output(
    raw_output: str,
    hypothesis_context: str,
    iteration: int
) -> str
```

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `raw_output` | `str` | Yes | stdout from MCP code execution |
| `hypothesis_context` | `str` | Yes | Current hypothesis being tested |
| `iteration` | `int` | Yes | Current loop iteration number |

**Returns**: `str` - 2-3 sentence summary (max 500 chars)

**Behavior**:
- Uses LLM to summarize raw output
- Summary answers: What was tested? What numbers were found? What does it imply?
- Separate LLM call from decision call

**Example**:
```python
summary = await compression.summarize_output(
    raw_output="""
    Baseline DAU: 95000
    Comparison DAU: 87000
    Change: -8.4%

    By platform:
    iOS: 45000 -> 38000 (-15.6%)
    Android: 38000 -> 37500 (-1.3%)
    Web: 12000 -> 11500 (-4.2%)
    """,
    hypothesis_context="Platform-specific issues causing DAU decline",
    iteration=3
)
# Returns: "iOS DAU dropped 15.6% (45K→38K) while Android and Web stayed
#           relatively flat (-1.3% and -4.2%). iOS accounts for ~87% of the
#           total DAU decline, strongly supporting the hypothesis."
```

---

### Working Memory Assembly

Each Memory Loop iteration assembles working memory from:

```python
def build_working_memory(state: InvestigationState) -> str:
    """Build context for LLM decision (~6000 tokens budget)."""
    return f"""
## Objective
Investigate: {state['investigation_context']['target_metric']}
Definition: {state['investigation_context']['metric_definition']}
Period: {state['investigation_context']['baseline_period']} vs {state['investigation_context']['comparison_period']}

## Hypothesis Status
{format_hypothesis_status(state['hypotheses'])}

## Compressed Findings (Last 5)
{format_findings(state['findings_ledger'][-5:])}

## Last Execution Result
{state['iteration_logs'][-1]['compressed_summary'] if state['iteration_logs'] else 'No previous execution'}

## Available Data
Files in workspace: {state['container_files']}
Schema: {summarize_schema(state['data_model'])}
"""
```

**Token Budget**:
- Working memory: ~6000 tokens
- Leaves room for LLM response with code
- Old findings compressed to stay within budget

---

### Memory Dump

After analysis completes, all memory is compiled and stored in Supabase:

```python
async def dump_memory_to_supabase(
    session_id: str,
    state: InvestigationState
) -> str:
    """Compile all analysis memory and store for RAG retrieval."""

    document = compile_memory_document(
        context=state['investigation_context'],
        data_model=state['data_model'],
        hypotheses=state['hypotheses'],
        findings=state['findings_ledger'],
        iterations=state['iteration_logs'],
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

# MCP Errors
ERROR_CONTAINER_CREATE_FAILED = "CONTAINER_CREATE_FAILED"
ERROR_CONTAINER_NOT_FOUND = "CONTAINER_NOT_FOUND"
ERROR_CODE_EXECUTION_FAILED = "CODE_EXECUTION_FAILED"
ERROR_CODE_EXECUTION_TIMEOUT = "CODE_EXECUTION_TIMEOUT"
ERROR_FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
ERROR_MCP_CONNECTION_FAILED = "MCP_CONNECTION_FAILED"

# Compression Errors
ERROR_COMPRESSION_FAILED = "COMPRESSION_FAILED"
ERROR_MEMORY_DUMP_FAILED = "MEMORY_DUMP_FAILED"
```

### MCP Error Recovery

```python
async def execute_with_retry(container_id: str, code: str, max_retries: int = 2) -> Dict:
    """Execute code with retry on transient failures."""
    for attempt in range(max_retries + 1):
        try:
            result = await mcp_client.execute_code(container_id, code)
            if result['success']:
                return result
            # Code error (not transient) - don't retry
            if "SyntaxError" in result['stderr'] or "NameError" in result['stderr']:
                return result
        except MCPConnectionError:
            if attempt == max_retries:
                raise
            await asyncio.sleep(1.0 * (attempt + 1))
    return result
```

---

## Tool Summary

| Category | Tool | Purpose |
|----------|------|---------|
| CSV | `csv_tools.get_headers` | Read column headers |
| CSV | `csv_tools.sample_rows` | Get sample data for schema inference |
| CSV | `csv_tools.get_row_count` | Count rows in file |
| MCP | `mcp_client.create_container` | Create Docker container for session |
| MCP | `mcp_client.upload_files` | Upload CSVs to container workspace |
| MCP | `mcp_client.execute_code` | Run Python code in container |
| MCP | `mcp_client.list_workspace` | List files in container |
| MCP | `mcp_client.destroy_container` | Cleanup container |
| File | `file_tools.write_json` | Write JSON artifacts |
| File | `file_tools.read_json` | Read JSON artifacts |
| File | `file_tools.write_markdown` | Write report |
| File | `file_tools.list_artifacts` | List session artifacts |
| Compression | `compression.summarize_output` | Compress raw output to finding |
