# Feature Specification: Metric Drill-Down Agent MVP

**Feature Branch**: `001-metric-drilldown-mvp`
**Created**: 2025-12-16
**Status**: Draft
**Input**: User description: "Build the Metric Drill-Down Agent MVP - an AI-powered tool that helps data scientists investigate unexpected metric movements by analyzing CSV data, inferring schema relationships, segmenting by dimensions, and generating ranked explanations with a markdown report"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Metric Investigation (Priority: P1)

A senior data scientist notices that DAU dropped 8% week-over-week. They need to understand what's driving this decline. They upload 3 CSV files (user_activity, users, sessions), specify the target metric column name (e.g., "dau"), provide a metric definition describing how DAU is calculated, add business context about recent product changes, and submit an investigation prompt. The agent analyzes the data, infers relationships between tables, identifies relevant dimensions, runs segmentation analysis, and produces a ranked explanation report explaining the metric movement.

**Why this priority**: This is the core value proposition of the product. Without a complete investigation flow producing actionable explanations, the tool has no value. Every other feature depends on this working end-to-end.

**Independent Test**: Can be fully tested by uploading sample CSV files, providing metric context, and verifying the agent produces a coherent markdown report with ranked explanations supported by data.

**Acceptance Scenarios**:

1. **Given** a user has uploaded 3 CSV files with descriptions, specified target metric column, and provided metric definition and business context, **When** they click "Start Agent", **Then** the system displays progress indicators and produces a markdown report within 5 minutes
2. **Given** an investigation is complete, **When** the user views the report, **Then** they see a data model diagram, list of analyzed dimensions, ranked explanations with evidence and likelihood reasoning, and recommended next steps
3. **Given** the agent is analyzing data, **When** it generates explanations, **Then** each explanation shows supporting evidence (segment sizes, % contribution, rate comparisons) and likelihood reasoning
4. **Given** uploaded CSV files have relatable columns (e.g., user_id in multiple tables), **When** the agent infers schema, **Then** it correctly identifies foreign key relationships and displays them in the report

---

### User Story 2 - Post-Analysis Q&A (Priority: P2)

After receiving an investigation report, the data scientist has questions about the methodology and wants to drill into specific findings. They use the chat panel to ask "How did you calculate contribution to decline?" and the agent retrieves and displays the calculation methodology with an example. They also ask for a 2-sentence summary to share with their PM.

**Why this priority**: Q&A enables users to trust and verify findings without re-running the investigation. It's essential for user adoption but depends on Story 1 being complete.

**Independent Test**: Can be tested after Story 1 by asking predefined questions about the analysis and verifying the agent retrieves accurate information from session memory.

**Acceptance Scenarios**:

1. **Given** an investigation report is displayed, **When** the user asks "How did you calculate X?", **Then** the agent explains the methodology with concrete numbers from the analysis
2. **Given** the user asks for a summary to share, **When** the request is processed, **Then** the agent produces a concise stakeholder-ready summary
3. **Given** the user asks about specific data not highlighted in findings, **When** the agent responds, **Then** it retrieves and displays the relevant segment data with context for why it wasn't featured
4. **Given** the user questions a finding, **When** they challenge an assertion, **Then** the agent provides additional breakdowns to support or refine its explanation

---

### User Story 3 - Form-Based Input with File Descriptions (Priority: P3)

A data scientist visits the application and sees a structured form with clear sections. They upload CSV files one at a time, adding descriptions for each explaining what the file contains and how it relates to the investigation. They specify the target metric column name, fill in the metric definition, business context, and investigation prompt in separate text areas. The form validates that required fields are complete before submission.

**Why this priority**: Good UX reduces friction and ensures the agent receives complete context. However, a minimal form could work for initial testing; structured input is an enhancement.

**Independent Test**: Can be tested by verifying form renders correctly, validates required fields, accepts file uploads with descriptions, and submits data to the backend.

**Acceptance Scenarios**:

1. **Given** a user visits the landing page, **When** the page loads, **Then** they see three clear sections: Relevant Documents, Business Context, and Investigation Prompt
2. **Given** a user uploads a CSV file, **When** they provide no description, **Then** the form displays a validation error requiring a description
3. **Given** all required fields are completed, **When** the user clicks "Start Agent", **Then** the form data is submitted and the progress screen appears
4. **Given** a user has uploaded files, **When** they click "Remove" on a file, **Then** the file and its description are removed from the form

---

### User Story 4 - Report Download (Priority: P4)

After reviewing the investigation report, the data scientist wants to save it for documentation or sharing. They click "Download Report" and receive a well-formatted markdown file containing the complete analysis.

**Why this priority**: Export functionality enables workflow integration but is not essential for validating the core investigation capability.

**Independent Test**: Can be tested by completing an investigation and verifying the download button produces a valid markdown file matching the displayed report.

**Acceptance Scenarios**:

1. **Given** an investigation report is displayed, **When** the user clicks "Download Report", **Then** a markdown file is downloaded containing the full report
2. **Given** the downloaded report, **When** opened in any markdown viewer, **Then** it renders correctly with proper formatting

---

### Edge Cases

- What happens when a user uploads a CSV file with no headers? System displays an error indicating headers are required for schema inference.
- What happens when uploaded CSVs have no relatable columns (no shared keys)? Agent proceeds with single-table analysis and connects insights from single tables analysises  logically, it also notes in the report that cross-table queries where not possible.
- What happens when the target metric column is not found in any uploaded file? System displays an error listing all available columns from uploaded files and prompts user to correct the target metric name or upload additional files.
- What happens when CSV files are too large (> 50MB)? System displays a file size limit error before upload completes.
- What happens when the agent cannot identify any meaningful explanations? Report states that no significant patterns were found and suggests potential reasons (e.g., uniform change across all segments).
- What happens when user submits investigation with empty business context? Investigation proceeds but report notes that limited context was provided, which may affect explanation quality.
- What happens during browser close mid-investigation? Session data is preserved for a configurable timeout period; user can return to see results if complete.
- What happens when LLM API fails during analysis? System retries up to 3 times with exponential backoff; if all retries fail, displays error message and user must restart investigation.

## Clarifications

### Session 2025-12-17

- Q: How should the system behave when the AI Agent cannot complete analysis due to LLM API failures? → A: Retry up to 3 times with exponential backoff; then fail with error message
- Q: How should users specify the date ranges for metric comparison? → A: Two explicit date range pickers (baseline period + comparison period)

## Requirements *(mandatory)*

### Functional Requirements

**Input & Form**
- **FR-001**: System MUST accept multiple CSV file uploads (minimum 1, maximum 10 files per investigation)
- **FR-002**: System MUST require a text description for each uploaded file explaining its contents
- **FR-003**: System MUST accept a free-text business context field describing relevant background information
- **FR-004**: System MUST require user to specify the target metric column name that will be analyzed (must exist in uploaded CSV files)
- **FR-004a**: System MUST accept a metric definition (free text) describing how the metric is calculated (for LLM context only, not for computation)
- **FR-004b**: System MUST validate that target metric column exists in at least one uploaded CSV file before investigation starts
- **FR-005**: System MUST accept an optional investigation prompt with specific focus areas or suspected causes
- **FR-006**: System MUST validate that at least one CSV file is uploaded and the target metric column exists before submission
- **FR-006a**: System MUST provide two date range pickers: one for the baseline period and one for the comparison period (e.g., "Nov 24-30" vs "Dec 1-7")

**Ai Agent Capabilities**
- **FR-007**: AI Agent MUST analyze CSV headers and sample data to infer column types (dimension, measure, ID, timestamp)
- **FR-008**: AI Agent MUST identify potential foreign key relationships between uploaded tables based on column names and data patterns
- **FR-009**: AI Agent MUST display inferred data model relationships in the report
- **FR-010**: AI Agent MUST create a clear analysis plan to determine potential explanation.   
- **FR-011**: AI Agent plan MUST follow clear steps: Initial Data Exploration, Generate Hypothesis of Potential Explanations, Analyze data to validate or invalidate hypothesis and log conclusions 
- **FR-012**: AI Agent MUST be able to iterate on the plan if all potential explanatios are not supported by data up to two times. If no explnation is found, AI Agent MUST create a report of performed analysis and discarded information
- **FR-013**: Each explanation MUST be independent (offering different interpretive angles or causal stories)
- **FR-014**: Each explanation MUST include supporting evidence (segment sizes, % contribution, rate comparisons)
- **FR-015**: Each explanation MUST include likelihood reasoning explaining the confidence level
- **FR-016**: Explanations MUST be ranked from "Most Likely" to "Less Likely" based on evidence strength, temporal alignment, segment isolation, and plausibility

- **FR-017**: AI Agent MUST generate a markdown report containing: data model, analsis performed, ranked explanations with evidence, and recommended next steps
- **FR-018**: AI Agent MUST show underlying data (actual numbers) supporting each explanation
- **FR-019**: AI Agent MUST allow report download as a markdown file

**Q&A Capability**
- **FR-020**: System MUST provide a chat interface for post-analysis questions
- **FR-021**: AI Agent MUST retrieve relevant information from session memory to answer methodology questions through chat interface
- **FR-022**: AI Agent MUST be able to produce summaries of findings at varying levels of detail 

**Progress & Feedback**
- **FR-023**: System MUST NOT display progress indicators during investigation showing current analysis stage
- **FR-024**: System MUST display likelihood labels for explanations (Most Likely, Likely, Possible, Less Likely)

**Session Management**
- **FR-025**: System MUST store all uploads and analysis artifacts in session-scoped directories
- **FR-026**: System MUST delete session data after a configurable timeout period (default: 24 hours)

**Accessibility**
- **FR-027**: Web interface MUST meet WCAG 2.1 AA accessibility standards

### Key Entities

- **Session**: Represents a single investigation session. Contains session ID, creation timestamp, timeout configuration, and references to all artifacts. Deleted after configurable timeout.
- **Uploaded File**: A CSV file provided by the user. Contains file name, user-provided description, detected schema (columns with inferred types), row count.
- **Data Model**: Inferred relationships between uploaded files. Contains table names, column mappings, and foreign key relationships.
- **Investigation Context**: User-provided inputs for the investigation. Contains target metric column name, metric definition (text description), business context text, investigation prompt, comparison date ranges.
- **Analysis Result**: Intermediate calculation outputs. Contains dimension segmentation results, contribution calculations, rate comparisons.
- **Explanation**: A ranked finding explaining metric movement. Contains causal story, supporting evidence (segment data, % contribution, rate comparisons), likelihood label, and reasoning. An explanation can combine multiple related factors into a coherent narrative.
- **Report**: Final markdown output. Contains all sections (data model, dimensions, explanations, recommended next steps).
- **Chat Message**: Q&A interaction. Contains user question, agent response, referenced artifacts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete the full investigation flow (form submission to report display) in under 15 minutes
- **SC-002**: Schema inference correctly identifies column types (dimension vs. measure) in at least 80% of test cases without user correction
- **SC-003**: At least 3 of 5 pilot users report that the investigation saved them time compared to manual analysis
- **SC-004**: Q&A successfully retrieves accurate methodology explanations for 90% of "how did you calculate X" questions
- **SC-005**: 80% of pilot users successfully complete an investigation on their first attempt without needing to restart
- **SC-006**: Reports contain actionable explanations that users rate as "useful" or "very useful" in at least 70% of investigations
- **SC-007**: Form validation prevents incomplete submissions 100% of the time (no investigations started with missing required fields)
- **SC-008**: Downloaded markdown reports render correctly in standard markdown viewers (GitHub, VS Code, Notion)
- **SC-009**: Agent proposes reasonable dimensions without user guidance in more than 80% of test cases
- **SC-010**: At least 1 pilot user identifies a root cause they might have missed manually

### Assumptions

- Users know the column name in their data that contains the metric they want to analyze
- Users can provide a text description of how the metric is calculated (for LLM context)
- CSV files are properly formatted with headers in the first row
- Users can export relevant data to CSV from their data warehouse
- Investigation sessions are standalone; users do not need to reference prior sessions
- English is the primary language for both input and output
- Reasoning-based driver identification is sufficient without formal statistical significance testing
- Users will provide sufficient business context for the agent to generate meaningful explanations
