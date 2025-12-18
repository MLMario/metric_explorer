# Memory Loop Architecture for Analysis Execution

## Purpose

This document describes the high-level architecture for implementing an iterative analysis loop within the Metric Movement Investigator agent. The intended reader is Claude Code, who will handle implementation details.

---

## Problem

The analysis execution phase cannot be a single pre-planned script because:

1. Each analysis step's findings determine what to investigate next
2. Raw results accumulate and would exceed context window limits
3. The agent needs to maintain state (DataFrames, files) across multiple LLM calls

---

## Solution: Structured Memory Loop

A single-agent loop that iterates through: **Read Context → Reason → Execute → Compress → Repeat**

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY LOOP                               │
│                                                              │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│    │  BUILD   │    │   LLM    │    │ EXECUTE  │            │
│    │ CONTEXT  │───▶│ DECISION │───▶│  CODE    │────┐       │
│    └──────────┘    └──────────┘    └──────────┘    │       │
│         ▲                                          │       │
│         │          ┌──────────┐                    │       │
│         └──────────│ COMPRESS │◀───────────────────┘       │
│                    │ & STORE  │                            │
│                    └──────────┘                            │
│                                                              │
│    Loop continues until: CONCLUDE decision or max iterations │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Concepts

### 1. Two-Tier Memory

| Memory Type | What It Contains | Where It Lives | In LLM Context? |
|-------------|------------------|----------------|-----------------|
| **Working Memory** | Compressed findings + last result | Assembled fresh each iteration | ✅ Yes |
| **Persistent State** | Full outputs, DataFrames, files | External storage + Docker container | ❌ No |

The LLM only sees a bounded context each iteration, but full history is preserved externally.

### 2. Compression

After each code execution, the raw output is compressed to 2-3 sentences capturing:
- What was tested
- Key numbers found
- What it implies

Only the **most recent** result is shown in full. All prior results are shown as compressed summaries.

### 3. Hypothesis Tracking

The agent maintains a list of hypotheses with statuses:
- `PENDING` — not yet investigated
- `INVESTIGATING` — currently being tested  
- `CONFIRMED` — evidence supports this explanation
- `RULED_OUT` — evidence contradicts this explanation

This prevents aimless exploration and enables stall detection.

### 4. Persistent Code Execution

Code runs in a Docker container via MCP that persists across iterations:
- DataFrames can be pickled and reloaded
- Files written in step 1 are available in step 5
- No need to re-run setup code each iteration

---

## Loop Flow (Each Iteration)

### Step 1: Build Context
Assemble what the LLM sees:
```
- Original objective (always)
- Current hypothesis status (compressed)
- Prior findings (compressed summaries only)
- Available workspace files (list)
- Last execution result (full, but truncated if huge)
```

### Step 2: LLM Decision
LLM chooses one of:
- **ANALYZE**: Run specific analysis code
- **DRILL_DOWN**: Go deeper on a finding
- **PIVOT**: Abandon current hypothesis, try another
- **CONCLUDE**: Sufficient evidence gathered, provide explanation

Output includes: decision type, rationale, code (if applicable), or conclusion.

### Step 3: Execute Code
Run the generated Python code in the persistent Docker container via MCP. Capture stdout, stderr, files created.

### Step 4: Compress & Store
- Use LLM to compress raw output to key insights (2-3 sentences)
- Store compressed summary in findings ledger
- Store full output in external storage (not LLM context)
- Update hypothesis status if evidence was found
- Set last_result to full output for next iteration

### Step 5: Loop Control
- If decision was CONCLUDE → exit loop, return conclusion
- If max iterations reached → generate partial conclusion, exit
- If stall detected → force pivot to next hypothesis
- Otherwise → continue to next iteration

---

## Stall Detection

The loop detects when investigation is stuck:

1. **No hypothesis progress**: N consecutive steps without confirming or ruling out any hypothesis
2. **Repetitive analysis**: Last 3 step summaries are nearly identical

When stall detected → force PIVOT to next pending hypothesis, or CONCLUDE if none remain.

---

## Context Budget

Approximate token allocation per iteration:

| Section | Budget |
|---------|--------|
| Objective | ~200 |
| Hypothesis status | ~300 |
| Compressed findings (last 8-10) | ~2000 |
| Workspace file list | ~200 |
| Last result (full) | ~3000 |
| Instructions | ~300 |
| **Total** | ~6000 |

This leaves room for the LLM response within typical context limits.

---

## Integration Requirements

### MCP Server
The Docker MCP server must support:
- Creating a persistent container with a session ID
- Executing Python scripts and returning stdout/stderr
- Installing pip packages
- Uploading files to container workspace
- Container cleanup

### LLM Client
Must support:
- Basic completions
- Structured output (to parse decisions reliably)

---

## Configuration Parameters

| Parameter | Purpose | Suggested Default |
|-----------|---------|-------------------|
| `max_iterations` | Hard limit on loop iterations | 15 |
| `min_iterations_before_conclude` | Prevent premature conclusions | 3 |
| `stall_threshold` | Steps without progress before forced pivot | 4 |
| `max_findings_in_context` | How many compressed findings to show | 10 |
| `last_result_max_chars` | Truncate long outputs | 4000 |

---

## Error Handling

| Scenario | Response |
|----------|----------|
| Code syntax/runtime error | Show error to LLM, let it fix in next iteration |
| 3+ consecutive errors | Force pivot to new hypothesis |
| Timeout | Log and suggest simpler analysis |
| MCP connection failure | Retry with backoff, fail if persistent |

---

## Output

The loop produces:
- **Conclusion**: Explanation of the metric movement with evidence
- **Confidence**: High/Medium/Low based on evidence strength
- **Findings trail**: List of compressed findings for transparency
- **Hypothesis outcomes**: Which were confirmed/ruled out

---

## Summary

The Memory Loop enables iterative, exploratory analysis by:

1. **Compressing history** — Only summaries in context, full data stored externally
2. **Persisting execution state** — Docker container maintains DataFrames across iterations
3. **Tracking hypotheses** — Structured exploration with stall detection
4. **Bounded context** — Same token budget every iteration regardless of investigation depth

This is a **single-agent architecture**. Multi-agent extensions (parallel segment analysis, specialist agents) can be added later if needed.
