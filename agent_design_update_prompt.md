## Context

I'm building an AI agent called the **Metric Movement Investigator** that automates the process of investigating why a business metric moved unexpectedly. This is a common task for data scientists: when conversion rate drops 15%, they need to systematically investigate 

the current architecture decribed in plan.md. which reflects the functional requirements from specs.md that should not change. pla.md also reflect the overall project guidelines established in consitution.md. 

plan.md was created following the prompt written in speckit.plan.md, which also creates research.md based on the technical concetps that will be needed to create plan.md. 

## Task:

You task is to simplify agent design established in plan.md and update the documents accordingly. 

To to this you need to first research: 

1) Claude Agent overall SDK and best practice
2) Understanding of how Agent SDK executes an iterative process
3) Python code used for Claude Agent SDK Implementation

Once research is done, plan how you are going to approach updating plan.md and related documents and execute update based on the Agent Design and other relevant changes

---

## Agent Design Changes

### Overall Approach: 

1) Keep langchain and AGENT STATE GRAPH as the main orchestrator of the agent flow. The main objective is to update the agent analysis node that currently implements a memory loop by using Claude SDK query() supported by a file based memory system. This will require using a python orchestrator within the analysis node to be able to do analysis on all hypothesis, after this orchestrator is done, we will have the output files needed for the memory_dump node and then report_generator to do it's job. 


### Analysis Node Design Details

#### 1. Orchestrator-Driven Architecture within the analysis node

Use a **Python orchestrator loop** that controls which hypothesis to test next, NOT an agent that loops internally.

```
PYTHON ORCHESTRATOR
    │
    ├── reads hypotheses.json
    ├── picks next untested hypothesis
    ├── calls query() for that hypothesis --> claude agent SDK should be executing an iterative analysis process here based on a prompt
    ├── captures result
    └── repeats until done
```

**Rationale**: Easier to debug, clean session logs per hypothesis, can parallelize later.

#### 2. One Hypothesis = One Session = One `query()` Call

Each hypothesis gets its own fresh context window. The orchestrator passes context via:
- The prompt (which hypothesis to test)
- File system (progress.txt, hypotheses.json from previous sessions)
- query() is an iterative process, calling query() once per hypothesis reaches the objective of having an iterative loop to perform analysis for hypothesis and replacing the need of having a memory loop

#### 3. File-Based Memory

```
/{session_id}/analysis/
├── progress.txt          # High-level investigation log
├── hypotheses.json       # All hypotheses with status
├── files/                 # CSV files from Supabase
├── scripts/              # Python analysis scripts
├── logs/                 # Detailed session logs
│   ├── session_H1_*.md   # Human-readable per session
│   └── session_H1_*.json # Structured summary per session
├── artifacts/            # Charts, tables, outputs
└── findings/             # Final report
```


#### 4. Single MCP Server: Supabase CSV Export

Only one MCP server needed — to fetch data from Supabase and save as CSV files, still using docker MCP servers infrastructure to find an adequate MCP for this task. 


#### 5. Python Execution via Native Bash

No MCP server for Python. The agent writes scripts to `/scripts/` and runs them via bash:
```bash
python scripts/001_device_analysis.py
```

#### 6. Detailed Session Logging

Each session produces:
- `logs/session_{hypothesis_id}_{timestamp}.md` — Step-by-step reasoning, streamed from Claude Agent SDK
- `logs/session_{hypothesis_id}_{timestamp}.json` — Structured summary

Log format for each step:
```markdown
## [Timestamp] Step N: [Action Type]

**What I did**: [description]
**What I found**: [data/results]  
**My interpretation**: [what this means]
**Decision**: [continue/pivot/conclude]
**Reasoning**: [why this decision]

```

## Concepts that must be included in the plan related to the analysis node

### The Session Logging System

Implement comprehensive logging:

1. **Stream capture** — Capture every message from `query()` 
2. **Markdown log** — Human-readable step-by-step narrative
3. **JSON summary** — Structured data for programmatic access

The agent should write the markdown log itself (via system prompt instructions), but the orchestrator should capture raw messages for debugging.

### Defined File Schemas

you must define Document the exact format for:

1. **progress.txt** — Investigation log format
2. **hypotheses.json** — Schema for hypothesis tracking
3. **session_*.json** — Schema for session summaries

