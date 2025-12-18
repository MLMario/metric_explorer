# Quickstart Guide: Metric Drill-Down Agent MVP

**Branch**: `001-metric-drilldown-mvp` | **Date**: 2025-12-17
**Reference**: [plan.md](./plan.md) | [research.md](./research.md)

## Prerequisites

Before starting, ensure you have:

| Tool | Version | Check Command |
|------|---------|---------------|
| Node.js | 20.x LTS | `node --version` |
| Python | 3.11+ | `python --version` |
| Docker | 24+ | `docker --version` |
| Docker Compose | 2.x | `docker compose version` |

You'll also need:
- **Anthropic API Key**: Get one from [console.anthropic.com](https://console.anthropic.com)

---

## Quick Start (Docker)

The fastest way to run the complete stack:

```bash
# 1. Clone and enter directory
cd metric_explorer

# 2. Copy environment template
cp .env.example .env

# 3. Add your Anthropic API key to .env
# Edit .env and set: ANTHROPIC_API_KEY=sk-ant-...

# 4. Start all services
docker compose up --build

# 5. Open browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

**Services Started**:
- `frontend` (Node.js/Express) - Port 3000
- `backend` (FastAPI) - Port 8000
- Sessions stored in `./sessions/` volume

---

## Local Development Setup

For active development, run services individually:

### 1. Backend Setup (FastAPI)

```bash
# Create Python virtual environment
cd backend
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Run development server
uvicorn src.main:app --reload --port 8000
```

Backend available at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

### 2. Agent Setup (Python)

The agent is a Python package imported by the backend. For isolated testing:

```bash
cd agent

# Create virtual environment (can share with backend)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run agent tests
pytest tests/ -v
```

### 3. Frontend Setup (Node.js)

```bash
cd frontend

# Install dependencies
npm install

# Set backend URL (create .env)
echo "BACKEND_URL=http://localhost:8000" > .env

# Run development server
npm run dev
```

Frontend available at: `http://localhost:3000`

---

## Environment Variables

Create a `.env` file in the project root (or in each service directory):

```bash
# ===================
# Required
# ===================
ANTHROPIC_API_KEY=sk-ant-api03-...

# ===================
# Backend Configuration
# ===================
SESSION_STORAGE_PATH=./sessions
SESSION_TIMEOUT_HOURS=24
MAX_FILE_SIZE_MB=50

# ===================
# Agent Configuration
# ===================
ANTHROPIC_MODEL=claude-sonnet-4-20250514
LLM_MAX_RETRIES=3
LLM_INITIAL_DELAY=1.0
LLM_BACKOFF_MULTIPLIER=2.0

# ===================
# Frontend Configuration
# ===================
BACKEND_URL=http://localhost:8000

# ===================
# Optional: Supabase (for metrics logging)
# ===================
# SUPABASE_URL=https://xxx.supabase.co
# SUPABASE_ANON_KEY=eyJ...
```

---

## Project Structure

```
metric_explorer/
├── frontend/               # Node.js/Express/HTMX
│   ├── src/
│   │   ├── server.js       # Entry point
│   │   ├── routes/         # Express routes
│   │   └── views/          # EJS templates
│   ├── package.json
│   └── tests/
│
├── backend/                # FastAPI
│   ├── src/
│   │   ├── main.py         # Entry point
│   │   ├── api/routes/     # API endpoints
│   │   ├── models/         # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── requirements.txt
│   └── tests/
│
├── agent/                  # LangGraph agent
│   ├── src/
│   │   ├── graph.py        # State machine
│   │   ├── nodes/          # Graph nodes
│   │   ├── tools/          # Analysis tools
│   │   └── prompts/        # LLM prompts
│   ├── requirements.txt
│   └── tests/
│
├── sessions/               # Runtime session storage (gitignored)
├── specs/                  # Design documentation
├── docker-compose.yml
└── .env.example
```

---

## Running Tests

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_sessions.py -v
```

### Agent Tests

```bash
cd agent
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run schema inference tests
pytest tests/test_schema_inference.py -v

# Run with mocked LLM (no API calls)
pytest tests/ -v -m "not integration"
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run with watch mode
npm run test:watch

# Run coverage
npm run test:coverage
```

---

## Common Development Tasks

### Add a New API Endpoint

1. Define schema in `backend/src/models/schemas.py`
2. Create route in `backend/src/api/routes/`
3. Register route in `backend/src/api/routes/__init__.py`
4. Add tests in `backend/tests/`
5. Update `specs/001-metric-drilldown-mvp/contracts/api.yaml`

### Add a New Agent Tool

1. Implement in `agent/src/tools/`
2. Add to tool registry in `agent/src/tools/__init__.py`
3. Add tests in `agent/tests/`
4. Document in `specs/001-metric-drilldown-mvp/contracts/agent-tools.md`

### Add a New Agent Node

1. Create node function in `agent/src/nodes/`
2. Register node in graph in `agent/src/graph.py`
3. Update state schema if needed in `agent/src/state.py`
4. Add tests in `agent/tests/`
5. Update flow diagram in `specs/001-metric-drilldown-mvp/plan.md`

### Add a New Frontend View

1. Create EJS template in `frontend/src/views/`
2. Add route in `frontend/src/routes/`
3. Add HTMX interactions as needed
4. Test accessibility (color contrast, labels, focus)

---

## Debugging

### Backend Logs

```bash
# Run with debug logging
LOG_LEVEL=DEBUG uvicorn src.main:app --reload
```

### Agent Debugging

```python
# In agent/src/graph.py, enable verbose mode
graph = StateGraph(InvestigationState)
# Add print statements or use LangSmith tracing

# Or run with LangSmith (requires account)
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=ls__...
```

### Frontend Debugging

```bash
# Run with debug output
DEBUG=express:* npm run dev

# Or check browser DevTools for HTMX errors
# HTMX errors appear in console
```

---

## API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | POST | Create session |
| `/api/sessions/{id}` | GET | Get session status |
| `/api/sessions/{id}` | DELETE | Delete session |
| `/api/sessions/{id}/files` | POST | Upload CSV |
| `/api/sessions/{id}/files/{fid}` | DELETE | Remove file |
| `/api/sessions/{id}/investigate` | POST | Start investigation |
| `/api/sessions/{id}/report` | GET | Get report |
| `/api/sessions/{id}/chat` | POST | Send Q&A message |

Full API documentation: `http://localhost:8000/docs` (Swagger UI)

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

Ensure your `.env` file contains a valid API key:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### "Connection refused" on frontend

Backend not running. Start it first:
```bash
cd backend && uvicorn src.main:app --reload --port 8000
```

### "File too large" error

Files must be under 50MB. Check file size:
```bash
ls -lh your_file.csv
```

### "No headers detected" error

CSV files must have a header row. Check first line:
```bash
head -1 your_file.csv
```

### Agent stuck / no response

1. Check Anthropic API status: [status.anthropic.com](https://status.anthropic.com)
2. Check API key has sufficient credits
3. Check logs for rate limit errors (429)

### Session expired

Sessions expire after 24 hours (default). Create a new session.

---

## Next Steps

After setup, you can:

1. **Try the demo**: Upload sample CSVs and run an investigation
2. **Read the spec**: `specs/001-metric-drilldown-mvp/spec.md`
3. **Understand the plan**: `specs/001-metric-drilldown-mvp/plan.md`
4. **Generate tasks**: Run `/speckit.tasks` to create implementation tasks

---

## Resources

- [Feature Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Technology Research](./research.md)
- [Data Model](./data-model.md)
- [API Contract](./contracts/api.yaml)
- [Agent Tools](./contracts/agent-tools.md)
- [Constitution](../../.specify/memory/constitution.md)
