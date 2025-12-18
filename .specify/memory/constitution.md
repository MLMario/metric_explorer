<!--
SYNC IMPACT REPORT
==================
Version change: 0.0.0 → 1.0.0 (initial ratification)
Modified principles: N/A (initial constitution)
Added sections:
  - 6 Core Principles (I-VI)
  - Technology Constraints
  - MVP Interface Flow
  - Explicit Non-Goals
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ Compatible (Constitution Check section exists)
  - .specify/templates/spec-template.md: ✅ Compatible (requirements and user stories supported)
  - .specify/templates/tasks-template.md: ✅ Compatible (phase structure aligns with modular architecture)
Follow-up TODOs: None
==================
-->

# Metric Drill-Down Agent Constitution

## Core Principles

### I. Understandable Code

- Code MUST prioritize readability and explicit logic over clever or minimalist implementations
- Variable names MUST be descriptive; function signatures MUST be clear and self-documenting
- Comments SHOULD only be added where logic is not self-evident from the code itself
- Stability and maintainability MUST take precedence over elegant minimalism
- All code MUST be written with the assumption that it will evolve beyond the MVP phase

**Rationale**: This MVP will evolve; long-term maintainability matters more than short-term elegance. Future developers (including future-you) must be able to understand and modify the code quickly.

### II. Simple Form-to-Report UX

- User interface MUST follow a form-based input pattern with clear sections: Files, Business Context, Investigation Prompt
- Investigation flow MUST be fully automated with visible progress indicators
- Report output MUST be rendered in markdown with a download option available
- Post-analysis Q&A chat MUST be limited to clarification only; it MUST NOT support iteration or adding new data mid-investigation
- Web interface MUST follow accessibility-first design principles (WCAG compliance)
- No mid-investigation data additions are permitted in the MVP

**Rationale**: Target users are busy data scientists who need to quickly investigate metric anomalies. Structured input reduces cognitive load and ensures complete context is provided upfront.

### III. Transparent AI Reasoning

- Every hypothesis MUST show the underlying data that supports it
- Contribution percentages and rate comparisons MUST be displayed alongside findings
- System MUST explain methodology when user asks "how did you calculate X"
- Uncertainty MUST never be hidden; confidence levels MUST be surfaced explicitly
- Schema inference logic and dimension selection reasoning MUST be visible to users

**Rationale**: Data scientists need to trust and verify AI-generated findings. Black-box outputs are unacceptable in analytical contexts where decisions have business impact.

### IV. Test Critical Paths

- Hypothesis generation and segmentation logic MUST have automated tests
- Schema inference from CSV headers and sample data MUST be tested
- API connections and data flow between components MUST be tested
- Session memory retrieval accuracy MUST be validated through tests
- UI components and styling testing MAY be skipped for MVP

**Rationale**: Analysis correctness is non-negotiable; incorrect hypotheses waste user time and erode trust. UI polish can be deferred until core functionality is proven reliable.

### V. Ephemeral Session Data

- All uploads and analysis artifacts MUST be stored in session-scoped directories
- Session data MUST be deleted after a configurable timeout period
- Persistent user accounts and investigation history MUST NOT be implemented for MVP
- Data handling expectations MUST be clearly communicated in the UI before users upload files

**Rationale**: Ephemeral data simplifies security considerations, avoids GDPR/privacy complexity, and allows the team to validate core value proposition before investing in persistence infrastructure.

### VI. Modular Architecture

- System MUST maintain clean separation: UI (Node.js/HTMX) ↔ API (FastAPI) ↔ Agent (Python/LangChain)
- File storage MUST be session-scoped: `/session/{id}/files/`, `/analysis/`, `/results/`, `/report.md`
- Each component MUST be independently deployable
- Architecture MUST be local-first but AWS-transferable without requiring refactoring
- All configuration MUST use environment variables; no hardcoded values for deployment-specific settings

**Rationale**: Demo today, production tomorrow. Clean boundaries enable independent scaling, testing, and deployment of each layer.

## Technology Constraints

- **Frontend**: Node.js with HTMX for UI simplicity and minimal JavaScript complexity
- **Backend API**: FastAPI (Python) for type safety and async performance
- **Database**: Supabase (remote API only, no local client installation required)
- **Agent Framework**: LangChain + Claude SDK (Anthropic API)
- **Tools**: Docker MCP server for pre-built MCP integrations
- **LLM**: Claude models exclusively; no multi-model fallbacks

## MVP Interface Flow

1. **Form Input Page**: File uploads with descriptions, business context text area, metric SQL definition, investigation prompt
2. **Progress Screen**: Real-time status updates during automated investigation
3. **Report Display**: Rendered markdown report with embedded data tables and Q&A chat panel
4. **Download Option**: Export final report as markdown file

## Explicit Non-Goals (MVP)

The following capabilities are explicitly out of scope for the MVP phase:

- Multi-user sessions or authentication systems
- Direct data warehouse connections (CSV upload only)
- Mid-investigation iteration (adding new tables after analysis begins)
- Statistical significance testing or p-value calculations
- Persistent investigation history across sessions
- Rich visual data exploration UI (charts, graphs, drill-down visualizations)
- External context gathering (macro economic trends, news correlation)

## Governance

- This constitution supersedes all other practices; feature requests that violate constitutional principles MUST be rejected or deferred until the constitution is amended
- Constitutional amendments require:
  1. Explicit written justification for the change
  2. Version bump following semantic versioning (MAJOR for principle changes, MINOR for additions, PATCH for clarifications)
  3. Review of all dependent templates for compatibility
- All PRs and code reviews MUST verify compliance with constitutional principles
- Complexity beyond what is specified MUST be explicitly justified in implementation plans

**Version**: 1.0.0 | **Ratified**: 2025-12-16 | **Last Amended**: 2025-12-16