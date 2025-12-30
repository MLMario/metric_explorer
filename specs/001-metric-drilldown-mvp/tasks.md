# Tasks: Metric Drill-Down Agent MVP

**Input**: Design documents from `/specs/001-metric-drilldown-mvp/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml, contracts/agent-tools.md, quickstart.md

**Tests**: Tests are NOT explicitly requested in spec.md. Test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`, `agent/src/`
- **Shared config**: `shared/`
- **Sessions**: `sessions/` (runtime, gitignored)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure per plan.md (frontend/, backend/, agent/, shared/, sessions/)
- [X] T002 [P] Initialize Node.js project with Express dependencies in frontend/package.json
- [X] T003 [P] Initialize Python project with FastAPI dependencies in backend/requirements.txt
- [X] T004 [P] Initialize Python project with LangGraph dependencies in agent/requirements.txt
- [X] T005 [P] Create shared config module in shared/config.py
- [X] T006 Create .env.example with all environment variables per research.md
- [X] T007 Create docker-compose.yml for local development per quickstart.md
- [X] T008 [P] Configure ESLint/Prettier for frontend in frontend/.eslintrc.js
- [X] T009 [P] Configure Ruff/Black for Python projects in pyproject.toml
- [X] T010 Create .gitignore with sessions/, venv/, node_modules/, __pycache__/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

### Backend Foundation

- [X] T011 Create FastAPI application entry point in backend/src/main.py
- [X] T012 [P] Implement environment configuration in backend/src/config.py
- [X] T013 [P] Create Pydantic schemas for Session, File, InvestigationRequest in backend/src/models/schemas.py
- [X] T014 [P] Create error response models and error codes in backend/src/models/errors.py
- [X] T015 Implement global error handler middleware in backend/src/api/middleware/error_handler.py
- [X] T016 Create session storage directory manager in backend/src/services/session_manager.py
- [X] T017 Register API routes in backend/src/api/routes/__init__.py

### Agent Foundation

- [X] T018 Create InvestigationState TypedDict in agent/src/state.py
- [X] T019 [P] Create FileInfo, Hypothesis, Finding, SessionLog TypedDicts in agent/src/state.py
- [X] T020 Create LangGraph state machine skeleton in agent/src/graph.py
- [X] T021 [P] Create CSV tools module in agent/src/tools/csv_tools.py
- [X] T022 [P] Create file tools module in agent/src/tools/file_tools.py
- [X] T023 Create prompt templates directory in agent/src/prompts/

### Frontend Foundation

- [X] T024 Create Express server entry point in frontend/src/server.js
- [X] T025 [P] Create base EJS layout template in frontend/src/views/layout.ejs
- [X] T026 [P] Create CSS styles with WCAG 2.1 AA compliance in frontend/src/public/css/styles.css
- [X] T027 Create route index with proxy to backend in frontend/src/routes/index.js
- [X] T028 [P] Add marked.js for markdown rendering in frontend/src/public/js/app.js

### Supabase Foundation

- [X] T029 Create Supabase client wrapper in agent/src/memory/supabase_rag.py
- [X] T030 Create memory_documents table schema (SQL migration) in backend/migrations/001_memory_documents.sql

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Complete Metric Investigation (Priority: P1) MVP

**Goal**: Enable users to upload CSV files, provide context, and receive a ranked explanation report

**Independent Test**: Upload sample CSV files, provide metric context, verify agent produces markdown report with ranked explanations

### Backend - Session & File Management

- [X] T031 [US1] Implement POST /api/sessions endpoint in backend/src/api/routes/sessions.py
- [X] T032 [US1] Implement GET /api/sessions/{id} endpoint in backend/src/api/routes/sessions.py
- [X] T033 [US1] Implement DELETE /api/sessions/{id} endpoint in backend/src/api/routes/sessions.py
- [X] T034 [US1] Implement POST /api/sessions/{id}/files endpoint in backend/src/api/routes/files.py
- [X] T035 [US1] Implement PUT /api/sessions/{id}/files/{fid} endpoint in backend/src/api/routes/files.py
- [X] T036 [US1] Implement DELETE /api/sessions/{id}/files/{fid} endpoint in backend/src/api/routes/files.py
- [X] T037 [US1] Implement file validation (CSV, 50MB, headers) in backend/src/services/file_handler.py

### Backend - Investigation Orchestration

- [X] T038 [US1] Implement POST /api/sessions/{id}/investigate endpoint in backend/src/api/routes/investigate.py
- [X] T039 [US1] Create agent runner service in backend/src/services/agent_runner.py
- [X] T040 [US1] Implement GET /api/sessions/{id}/report endpoint in backend/src/api/routes/investigate.py

### Agent - Schema Inference Node

- [X] T041 [US1] Implement csv_tools.get_headers() in agent/src/tools/csv_tools.py
- [X] T042 [US1] Implement csv_tools.sample_rows() in agent/src/tools/csv_tools.py
- [X] T043 [US1] Implement csv_tools.get_row_count() in agent/src/tools/csv_tools.py
- [X] T044 [US1] Create schema inference prompt in agent/src/prompts/schema_inference.txt
- [X] T045 [US1] Implement schema_inference node in agent/src/nodes/schema_inference.py

### Agent - Metric Identification Node

- [X] T046 [US1] Implement metric_identification node (pure Python validation) in agent/src/nodes/metric_identification.py

### Agent - Hypothesis Generator Node

- [X] T047 [US1] Create hypothesis generation prompt in agent/src/prompts/hypothesis_generation.txt
- [X] T048 [US1] Implement hypothesis_generator node in agent/src/nodes/hypothesis_generator.py

### Agent - Analysis Execution Node (Claude Agent SDK)

- [X] T049 [US1] Create Supabase MCP client for file retrieval in agent/src/tools/mcp_client.py
- [X] T050 [US1] Create analysis system prompt in agent/src/prompts/analysis_system.txt
- [X] T051 [US1] Implement Python orchestrator loop in agent/src/nodes/analysis_execution.py
- [X] T052 [US1] Implement Claude Agent SDK query() integration in agent/src/nodes/analysis_execution.py
- [X] T053 [US1] Implement findings_ledger.json incremental update logic in agent/src/memory/findings_ledger.py
- [X] T054 [US1] Implement progress.txt logging in agent/src/memory/progress_log.py
- [X] T055 [US1] Implement session log JSON/MD writing in agent/src/memory/session_log.py

### Agent - Memory Dump Node

- [X] T056 [US1] Implement compile_memory_document() in agent/src/memory/working_memory.py
- [X] T057 [US1] Implement memory_dump node in agent/src/nodes/memory_dump.py
- [X] T058 [US1] Implement Supabase document storage with embeddings in agent/src/memory/supabase_rag.py

### Agent - Report Generator Node

- [X] T059 [US1] Create report template prompt in agent/src/prompts/report_template.txt
- [X] T060 [US1] Implement report_generator node in agent/src/nodes/report_generator.py
- [X] T061 [US1] Implement no_findings_report fallback in agent/src/nodes/report_generator.py

### Agent - Graph Assembly

- [X] T062 [US1] Wire all nodes into LangGraph state machine in agent/src/graph.py
- [X] T063 [US1] Add conditional edges for metric validation in agent/src/graph.py
- [X] T064 [US1] Add conditional edge for no_findings path in agent/src/graph.py

### Frontend - Form UI

- [ ] T065 [US1] Create investigation form template in frontend/src/views/form.ejs
- [ ] T066 [US1] Create file card partial for uploaded files in frontend/src/views/partials/file-card.ejs
- [ ] T067 [US1] Implement HTMX file upload (hx-post) in frontend/src/views/form.ejs
- [ ] T068 [US1] Implement HTMX file remove (hx-delete) in frontend/src/views/partials/file-card.ejs
- [ ] T069 [US1] Add date range pickers for baseline/comparison periods in frontend/src/views/form.ejs
- [ ] T070 [US1] Implement form validation (required fields) in frontend/src/views/form.ejs
- [ ] T071 [US1] Create session routes (form page, submit) in frontend/src/routes/session.js

### Frontend - Report View

- [ ] T072 [US1] Create report display template in frontend/src/views/report.ejs
- [ ] T073 [US1] Create explanation card partial in frontend/src/views/partials/explanation.ejs
- [ ] T074 [US1] Implement markdown rendering with marked.js in frontend/src/views/report.ejs
- [ ] T075 [US1] Add report route (GET /session/{id}) in frontend/src/routes/session.js

### Frontend - API Proxy

- [ ] T076 [US1] Create API proxy routes in frontend/src/routes/api.js
- [ ] T077 [US1] Implement error handling in proxy in frontend/src/routes/api.js

**Checkpoint**: User Story 1 (Complete Metric Investigation) should be fully functional and testable independently

---

## Phase 4: User Story 2 - Post-Analysis Q&A (Priority: P2)

**Goal**: Enable users to ask questions about the analysis and get accurate answers via RAG

**Independent Test**: After completing investigation, ask "How did you calculate X?" and verify agent explains methodology with numbers

### Backend - Chat Endpoints

- [ ] T078 [US2] Implement POST /api/sessions/{id}/chat endpoint in backend/src/api/routes/chat.py
- [ ] T079 [US2] Implement GET /api/sessions/{id}/chat endpoint (chat history) in backend/src/api/routes/chat.py
- [ ] T080 [US2] Validate session is completed before allowing chat in backend/src/api/routes/chat.py

### Agent - Q&A Handler

- [ ] T081 [US2] Create Q&A response prompt in agent/src/prompts/qa_response.txt
- [ ] T082 [US2] Implement similarity_search() in agent/src/memory/supabase_rag.py
- [ ] T083 [US2] Implement handle_qa_query() function in agent/src/memory/supabase_rag.py
- [ ] T084 [US2] Implement chat history save/load in agent/src/memory/chat_history.py

### Frontend - Chat Panel

- [ ] T085 [US2] Create chat panel in report view in frontend/src/views/report.ejs
- [ ] T086 [US2] Create chat message partial in frontend/src/views/partials/chat-message.ejs
- [ ] T087 [US2] Implement HTMX chat submit (hx-post) in frontend/src/views/report.ejs
- [ ] T088 [US2] Add ARIA live region for accessibility in frontend/src/views/report.ejs
- [ ] T089 [US2] Add chat API proxy route in frontend/src/routes/api.js

**Checkpoint**: User Story 2 (Post-Analysis Q&A) should work independently after US1 is complete

---

## Phase 5: User Story 3 - Form-Based Input with Descriptions (Priority: P3)

**Goal**: Improve form UX with clear sections, file descriptions, and validation

**Independent Test**: Verify form renders correctly, validates required fields, and accepts file uploads with descriptions

### Frontend - Form Improvements

- [ ] T090 [US3] Add three-section layout to form in frontend/src/views/form.ejs
- [ ] T091 [US3] Add description textarea per file in frontend/src/views/partials/file-card.ejs
- [ ] T092 [US3] Implement client-side validation for descriptions in frontend/src/views/form.ejs
- [ ] T093 [US3] Add visual validation feedback (error states) in frontend/src/public/css/styles.css
- [ ] T094 [US3] Ensure all inputs have proper labels in frontend/src/views/form.ejs

### Backend - Description Validation

- [ ] T095 [US3] Enforce description required on file upload in backend/src/api/routes/files.py

**Checkpoint**: User Story 3 (Form-Based Input) should work independently

---

## Phase 6: User Story 4 - Report Download (Priority: P4)

**Goal**: Enable users to download the report as a markdown file

**Independent Test**: Complete investigation, click download, verify markdown file matches displayed report

### Backend - Download Endpoint

- [ ] T096 [US4] Implement GET /api/sessions/{id}/report/download endpoint in backend/src/api/routes/investigate.py
- [ ] T097 [US4] Set Content-Disposition header for download in backend/src/api/routes/investigate.py

### Frontend - Download Button

- [ ] T098 [US4] Add download button to report view in frontend/src/views/report.ejs
- [ ] T099 [US4] Style download button for accessibility in frontend/src/public/css/styles.css

**Checkpoint**: User Story 4 (Report Download) should work independently

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Session Management

- [ ] T100 Implement session timeout cleanup background task in backend/src/services/session_manager.py
- [ ] T101 Add session expiry check on all endpoints in backend/src/api/middleware/session_check.py

### Error Handling

- [ ] T102 Add retry logic for LLM API calls (3 retries, exponential backoff) in agent/src/nodes/utils.py
- [ ] T103 Implement graceful error reporting to frontend in backend/src/api/routes/investigate.py

### Accessibility

- [ ] T104 Verify WCAG 2.1 AA color contrast in frontend/src/public/css/styles.css
- [ ] T105 Add skip links and focus indicators in frontend/src/views/layout.ejs

### Documentation

- [ ] T106 Validate quickstart.md instructions work end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational (Phase 2)
  - User Story 2 (P2): Can start after US1 is complete (needs RAG data from analysis)
  - User Story 3 (P3): Can start after Foundational (Phase 2) - parallel with US1
  - User Story 4 (P4): Can start after Foundational (Phase 2) - parallel with US1
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Foundation (Phase 2)
       │
       ├──────────────────┬──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
    US1 (P1)           US3 (P3)          US4 (P4)
    Core Flow          Form UX           Download
       │
       ▼
    US2 (P2)
    Q&A Chat
       │
       ▼
    Polish (Phase 7)
```

### Within Each User Story

- Backend models → Backend services → Backend routes
- Agent tools → Agent nodes → Agent graph
- Frontend partials → Frontend pages → Frontend routes

### Parallel Opportunities

**Phase 1 (Setup)**: T002, T003, T004, T005, T008, T009 can run in parallel

**Phase 2 (Foundation)**: T012-T014, T018-T019, T021-T022, T025-T026, T028 can run in parallel

**Phase 3 (US1)**:
- T041-T043 (CSV tools) in parallel
- T065-T070 (Frontend form) after backend routes ready

**Phase 4 (US2)**: T081-T084 (Agent Q&A) in parallel with T085-T089 (Frontend chat)

---

## Parallel Example: Phase 2 Foundation

```bash
# Launch all parallel foundation tasks together:
Task: "Create environment configuration in backend/src/config.py"
Task: "Create Pydantic schemas in backend/src/models/schemas.py"
Task: "Create error response models in backend/src/models/errors.py"
Task: "Create FileInfo, Hypothesis TypedDicts in agent/src/state.py"
Task: "Create CSV tools module in agent/src/tools/csv_tools.py"
Task: "Create file tools module in agent/src/tools/file_tools.py"
Task: "Create base EJS layout template in frontend/src/views/layout.ejs"
Task: "Create CSS styles in frontend/src/public/css/styles.css"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 - Complete Metric Investigation
4. **STOP and VALIDATE**: Test US1 independently with sample CSVs
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 3 → Form UX improvements → Deploy/Demo
4. Add User Story 4 → Report download → Deploy/Demo
5. Add User Story 2 → Q&A capability → Deploy/Demo
6. Polish phase → Production ready

### Key Files Per Component

| Component | Key Files |
|-----------|-----------|
| Backend | main.py, config.py, sessions.py, files.py, investigate.py, chat.py |
| Agent | graph.py, state.py, schema_inference.py, analysis_execution.py, report_generator.py |
| Frontend | server.js, form.ejs, report.ejs, styles.css, app.js |
| Shared | config.py, .env |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- MVP = Phase 1 + Phase 2 + Phase 3 (User Story 1)
