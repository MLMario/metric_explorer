# Metric Drill-Down Agent
## Lean Product Requirements Document

**Author:** Mario  
**Date:** December 2024  
**Status:** MVP Definition

---

## 1. Problem Statement

### The Pain
When a key metric moves unexpectedly, data scientists spend hours on repetitive investigative work: identifying which dimensions to segment by, writing SQL queries to isolate drivers, and iterating through hypotheses until they find the root cause. This process is cognitively demanding, time-consuming, and often interrupted by other priorities—leading to delayed insights or incomplete investigations.

### Who Feels It
Senior data scientists at startups and growth-stage companies who are responsible for metrics reporting, deep dives, and explaining metric movements to stakeholders. These DS professionals are often the only analytics resource on a product team, making their time extremely scarce.

### Current Workarounds
- Manual SQL queries with trial-and-error segmentation
- Pre-built dashboards that lack the flexibility for ad-hoc investigation
- Spreadsheet-based analysis that doesn't scale
- Deprioritizing investigations entirely due to time constraints

---

## 2. Full Vision

The ideal Metric Drill-Down Agent automates the end-to-end metric investigation workflow:

### End-State User Flow

1. **Automatic Detection** — The agent monitors key metrics and surfaces anomalies that require investigation (out-of-bounds values, unexpected trend changes, concerning patterns)

2. **User Permission & Guidance** — The agent notifies the user and asks for permission to investigate. User can optionally provide guidance on where to look and hypotheses to explore.

3. **Context Gathering** — The agent autonomously gathers context on:
   - The metric itself (related metrics, input/output metrics, business context)
   - Available data (relevant datasets, table relationships, column definitions)
   - External factors (macro trends, seasonality, known events)

4. **Explanation Generation** — The agent investigates and produces 3-5 ranked explanations for the metric movement, each supported by data analysis

5. **Interactive Exploration** — User converses with the agent to provide guidance, ask follow-up questions, or explore the underlying analysis through a visual interface

6. **Handoff or Iteration** — If satisfied, user takes over the investigation or exports results. If not, the agent iterates based on feedback.

---

## 3. MVP Scope

### What's In

**User Provides:**
- SQL query defining the metric logic (required)
- Input table referenced in the query
- Date range to compare (e.g., this week vs. last week)
- CSV files containing tables to explore
- *(Optional)* Suggested dimensions or tables to prioritize

**Agent Capabilities:**

| Capability | MVP Implementation |
|------------|-------------------|
| Schema exploration | Scans provided CSV tables, infers column types (dimension vs. measure vs. ID vs. timestamp), infers data model relationships between tables |
| Dimension selection | Proposes which dimensions are worth segmenting by, with reasoning |
| Segmentation analysis | Runs analysis to identify drivers of metric movement |
| Explanation generation | Produces ranked list of potential explanations for the metric movement (see Explanation Output below) |
| Q&A capability | After report generation, user can ask questions about the analysis, request summaries, or clarify findings |

**Explanation Output Definition:**

An *explanation* is a potential reason (or group of related reasons) for why the metric moved. The agent produces 3-5 explanations with the following properties:

| Property | Description |
|----------|-------------|
| Independence | Each explanation is distinct from the others. Two explanations may overlap in the data they reference, but they must offer different interpretive angles or causal stories. |
| Composition | An explanation can be a single reason ("iOS crash rate spiked") or a group of related reasons ("New users from TikTok are dropping off at onboarding step 2, likely due to mismatched expectations from ad creative"). |
| Ranking | Explanations are ranked from most likely to least likely based on evidence strength, magnitude of contribution, and plausibility. |
| Evidence | Each explanation includes supporting data (segment sizes, % contribution, rate comparisons) and reasoning for its likelihood ranking. |

**Example Explanation Output:**

```
## Explanations (Ranked by Likelihood)

### 1. New onboarding flow is causing drop-off (Most Likely)
Evidence: 58% of decline concentrated in users created after Dec 2 launch.
New user DAU dropped 18.4% vs 8.2% overall. Timing aligns perfectly.
Likelihood reasoning: Strong temporal alignment + segment isolation + 
large magnitude = high confidence this is a primary driver.

### 2. TikTok acquisition cohort quality degraded (Likely)
Evidence: TikTok users dropped 24.1%, 3x the overall rate.
However, this overlaps significantly with explanation #1 (TikTok users 
are disproportionately new users experiencing the new onboarding).
Likelihood reasoning: Could be independent (ad targeting changed) or 
correlated with #1. Moderate confidence as standalone explanation.

### 3. iOS-specific technical issue (Possible)
Evidence: iOS dropped 11.2% vs Android 4.2%.
However, the gap narrows when controlling for user tenure.
Likelihood reasoning: Some independent iOS effect exists, but smaller 
than it first appears. Lower confidence as primary driver.

### 4. Seasonal holiday dip (Less Likely)
Evidence: Historical data shows 2-3% DAU dip during this period.
Current drop (8.2%) far exceeds seasonal norm.
Likelihood reasoning: Seasonality is a contributing factor but cannot 
explain the majority of the decline. Low confidence as primary driver.
```

**Interface:**
- Form-based input page for investigation setup
- Automated investigation → markdown report output
- Chat window for post-analysis Q&A

### What's Explicitly Out (Deferred to Future Versions)

| Capability | Reason for Deferral |
|------------|---------------------|
| Automatic anomaly detection | Requires persistent monitoring infrastructure; user can trigger manually for MVP |
| Direct warehouse connection | CSV upload simplifies auth, security, and setup; validates core value first |
| Statistical significance testing | Agent can reason about magnitude and patterns without formal hypothesis testing; reduces complexity |
| Pre-aggregated metric tables | MVP assumes user provides raw metric logic; agent doesn't need to reverse-engineer dashboard tables |
| Rich visual UI for data exploration | Form input + chat Q&A is sufficient to validate; interactive visualizations can come later |
| Persistent memory across sessions | Each investigation is standalone for MVP |
| External context gathering | No macro/news data integration; user provides context through the form |
| Iteration loop with new data | User cannot add new tables mid-investigation; they can start a new investigation instead |

### MVP Assumptions

1. **Metric query assumption** — User provides the actual SQL logic to calculate the metric, not a pre-aggregated table. This means the agent can understand what's being measured and how.

2. **CSV-based data** — For MVP, the agent works with user-uploaded CSV files rather than connecting directly to a warehouse. This simplifies setup and allows faster iteration.

3. **Reasoning-based driver identification** — The agent identifies drivers through logical reasoning about magnitudes, proportions, and patterns rather than formal statistical tests. We will develop a specific methodology for how the agent reasons through driver identification.

---

## 4. MVP User Interface

### Landing Page: Investigation Setup Form

```
┌─────────────────────────────────────────────────────────────────┐
│                    METRIC DRILL-DOWN AGENT                      │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  SECTION 1: Relevant Documents                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Upload files for the agent to analyze. Each file requires      │
│  a description explaining its contents and relevance.           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 📄 user_activity.csv                              [Remove] │  │
│  │ Description: Main event table with user actions.          │  │
│  │ Contains user_id, timestamp, platform, event_type.        │  │
│  │ This is the base table for DAU calculation.               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 📄 users.csv                                      [Remove] │  │
│  │ Description: User dimension table with demographics       │  │
│  │ and acquisition info. Includes user_id, created_at,       │  │
│  │ country, utm_source, platform.                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 📄 sessions.csv                                   [Remove] │  │
│  │ Description: Session-level data with device info.         │  │
│  │ Joins to user_activity on session_id. Contains            │  │
│  │ device_type, os_version, app_version.                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [+ Add another file]                                           │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  SECTION 2: Relevant Business Context                           │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Metric Investigation Context *                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ We noticed DAU dropped ~8% week-over-week. Need to        │  │
│  │ understand what's driving this decline. The metric is     │  │
│  │ calculated as COUNT(DISTINCT user_id) from user_activity  │  │
│  │ grouped by date.                                          │  │
│  │                                                           │  │
│  │ SQL:                                                      │  │
│  │ SELECT date, COUNT(DISTINCT user_id) as dau               │  │
│  │ FROM user_activity                                        │  │
│  │ GROUP BY date                                             │  │
│  │                                                           │  │
│  │ Compare: Dec 1-7 vs Nov 24-30                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Relevant Metrics Context                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Related metrics to consider:                              │  │
│  │ - New user signups (upstream of DAU)                      │  │
│  │ - Day-1 retention (quality indicator)                     │  │
│  │ - Sessions per user (engagement depth)                    │  │
│  │ - App crashes (potential cause)                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Business Context & Definitions                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ - We're a US-focused consumer app                         │  │
│  │ - iOS is ~60% of our user base                            │  │
│  │ - We launched a new onboarding flow on Dec 2              │  │
│  │ - "New user" = created within last 7 days                 │  │
│  │ - Holiday season typically shows slight DAU dip           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  SECTION 3: Investigation Prompt                                │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Any specific instructions or hypotheses for the agent?         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Focus on understanding whether the new onboarding flow    │  │
│  │ is related to the drop. Also interested in any platform-  │  │
│  │ specific patterns since we had some iOS issues last       │  │
│  │ month.                                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│                        ┌─────────────────┐                      │
│                        │  START AGENT ▶  │                      │
│                        └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. User Flow

### Happy Path

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: User fills out the investigation form                   │
│                                                                 │
│ • Uploads 3 CSV files with descriptions                         │
│ • Provides metric context and SQL definition                    │
│ • Adds business context about the US focus and new launch       │
│ • Writes prompt focusing on onboarding flow and iOS             │
│ • Clicks "START AGENT"                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Agent processes and investigates                        │
│                                                                 │
│ [Loading screen with progress indicator]                        │
│                                                                 │
│ ✓ Analyzing uploaded files...                                   │
│ ✓ Inferring schema and data model...                            │
│ ✓ Identifying relevant dimensions...                            │
│ ⟳ Running segmentation analysis...                              │
│ ○ Generating explanations...                                    │
│ ○ Compiling report...                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Agent presents findings + chat opens                    │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │                    INVESTIGATION REPORT                     │ │
│ │                                                             │ │
│ │ ## DAU Investigation: -8.2% Week-over-Week                  │ │
│ │ Baseline: 42,340 → Current: 38,870                          │ │
│ │                                                             │ │
│ │ ### Data Model Identified                                   │ │
│ │ • user_activity ← users (via user_id)                       │ │
│ │ • user_activity ← sessions (via session_id)                 │ │
│ │                                                             │ │
│ │ ### Dimensions Analyzed                                     │ │
│ │ • platform (from user_activity)                             │ │
│ │ • country (from users) — filtered to US per context         │ │
│ │ • user_tenure_bucket (derived from users.created_at)        │ │
│ │ • acquisition_channel (from users.utm_source)               │ │
│ │ • device_type (from sessions)                               │ │
│ │                                                             │ │
│ │ ### Explanations (Ranked by Likelihood)                      │ │
│ │                                                             │ │
│ │ **1. New onboarding flow is causing drop-off (Most Likely)**│ │
│ │ Evidence:                                                   │ │
│ │ • 58% of decline concentrated in new users (0-7 days)       │ │
│ │ • New user DAU dropped 18.4% vs 8.2% overall                │ │
│ │ • Timing aligns with Dec 2 launch                           │ │
│ │ Likelihood reasoning: Strong temporal alignment + segment   │ │
│ │ isolation + large magnitude = high confidence.              │ │
│ │                                                             │ │
│ │ **2. TikTok acquisition cohort quality degraded (Likely)**  │ │
│ │ Evidence:                                                   │ │
│ │ • TikTok users dropped 24.1%, 3x the overall rate           │ │
│ │ • Overlaps with explanation #1 (TikTok users skew new)      │ │
│ │ Likelihood reasoning: Could be independent (ad targeting    │ │
│ │ changed) or correlated with #1. Needs further isolation.    │ │
│ │                                                             │ │
│ │ **3. iOS-specific technical issue (Possible)**              │ │
│ │ Evidence:                                                   │ │
│ │ • iOS dropped 11.2% vs Android 4.2%                         │ │
│ │ • Gap narrows when controlling for user tenure              │ │
│ │ Likelihood reasoning: Some independent iOS effect exists,   │ │
│ │ but appears secondary to onboarding issue.                  │ │
│ │                                                             │ │
│ │ **4. Seasonal holiday dip (Less Likely)**                   │ │
│ │ Evidence:                                                   │ │
│ │ • Historical data shows 2-3% dip during this period         │ │
│ │ • Current drop (8.2%) far exceeds seasonal norm             │ │
│ │ Likelihood reasoning: Contributing factor but cannot        │ │
│ │ explain majority of decline.                                │ │
│ │                                                             │ │
│ │ ### Recommended Next Steps                                  │ │
│ │ 1. Compare onboarding completion rates: old vs new flow     │ │
│ │ 2. Analyze TikTok cohort behavior in onboarding funnel      │ │
│ │ 3. Check if iOS new users have different drop-off point     │ │
│ │                                                             │ │
│ │                              [Download Report (.md)]        │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ CHAT                                                        │ │
│ │                                                             │ │
│ │ Agent: I've completed the investigation. The report above   │ │
│ │ summarizes my findings. Feel free to ask any questions      │ │
│ │ about the analysis, request clarifications, or ask for      │ │
│ │ summaries.                                                  │ │
│ │                                                             │ │
│ │ ┌───────────────────────────────────────────────────────┐   │ │
│ │ │ Type your question...                                 │   │ │
│ │ └───────────────────────────────────────────────────────┘   │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Q&A Conversation Scenarios

**Scenario A: User asks for clarification on methodology**
```
USER: How did you calculate "contribution to decline"?

AGENT: For each segment, I calculated contribution as:

       (Segment's absolute change) / (Total absolute change) × 100

       For example, new users (0-7 days):
       • Prior period: 8,200 DAU
       • Current period: 6,690 DAU  
       • Segment decline: 1,510 users
       • Total decline: 3,470 users (42,340 → 38,870)
       • Contribution: 1,510 / 3,470 = 43.5%

       Note: Contributions can sum to more than 100% when segments 
       overlap (e.g., a user can be both "new" and "iOS").
```

**Scenario B: User asks for a summary to share**
```
USER: Can you give me a 2-sentence summary I can share with 
      my PM?

AGENT: "DAU dropped 8.2% WoW, with 58% of the decline 
       concentrated in new users who experienced the Dec 2 
       onboarding flow launch. Recommend investigating 
       onboarding completion rates to identify where new 
       users are dropping off."
```

**Scenario C: User asks about specific data**
```
USER: What was the actual DAU number for TikTok users in 
      each period?

AGENT: TikTok acquisition users (utm_source = 'tiktok'):
       • Prior period (Nov 24-30): 3,420 DAU
       • Current period (Dec 1-7): 2,595 DAU
       • Change: -825 users (-24.1%)

       This represents 23.8% of your total decline.
```

**Scenario D: User asks about data the agent analyzed**
```
USER: Which columns did you find in the sessions table?

AGENT: From your sessions.csv file, I identified these columns:
       
       • session_id (ID field — primary key)
       • user_id (ID field — foreign key to users)
       • timestamp (datetime)
       • device_type (dimension — 8 unique values)
       • os_version (dimension — 12 unique values)
       • app_version (dimension — 5 unique values)
       • session_duration_sec (measure)
       • pages_viewed (measure)
       
       I used device_type for segmentation based on your 
       mention of iOS issues. os_version and app_version 
       were not used but could be relevant for debugging.
```

**Scenario E: User asks about something not in the analysis**
```
USER: Did you find anything about Android users?

AGENT: Android showed a smaller decline than iOS:
       • Android DAU change: -4.2% (vs -11.2% for iOS)
       • Android contribution to total decline: 18%
       
       I didn't highlight this in the top findings because 
       the Android pattern was close to the overall average 
       and didn't stand out as a driver. The iOS 
       concentration suggested looking there first.
```

**Scenario F: User questions a finding**
```
USER: Are you sure the iOS pattern isn't independent from 
      the new user pattern? We had some crashes last month.

AGENT: Good question. I can break this down further:

       New users on iOS: -22.3%
       New users on Android: -12.1%
       Existing users on iOS: -5.8%
       Existing users on Android: -4.1%

       The iOS effect does appear somewhat independent — 
       existing iOS users dropped more than existing Android 
       users. However, the largest effect is the interaction: 
       new + iOS users dropped most severely.

       If you have crash data, that could help distinguish 
       whether there's an iOS-specific bug affecting all 
       users, or if the onboarding flow has iOS-specific 
       problems.
```

---

## 6. Agent Memory (MVP)

### Overview

During an investigation session, the agent needs to reference various artifacts without bloating the context window. The MVP implements a lightweight memory system that stores and retrieves information on-demand.

### What the Agent Remembers (Session Scope)

| Artifact Type | Source | Storage Approach |
|--------------|--------|------------------|
| User form inputs | Form submission | Stored in session state; summarized in context |
| File metadata | Uploaded CSVs | Schema + descriptions stored; raw data queried on-demand |
| File descriptions | User-provided | Full text stored in session state |
| SQL metric definition | Form input | Full text stored in session state |
| Business context | Form input | Full text stored in session state |
| Investigation prompt | Form input | Full text stored in session state |
| Python analysis code | Agent-generated | Stored externally; retrieved when user asks "how did you calculate X" |
| Intermediate results | Agent-generated | Stored externally; retrieved when user asks about specific numbers |
| Final markdown report | Agent-generated | Stored as file; agent retrieves sections on-demand when answering questions |

### Memory Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONTEXT WINDOW                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • Summarized form inputs                                  │  │
│  │ • Schema overview (tables, columns, relationships)        │  │
│  │ • Current conversation history                            │  │
│  │ • Retrieved artifacts (on-demand)                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ retrieve when needed
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXTERNAL STORAGE                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ /session/{id}/files/           → uploaded CSVs            │  │
│  │ /session/{id}/analysis/        → Python code executed     │  │
│  │ /session/{id}/results/         → intermediate dataframes  │  │
│  │ /session/{id}/report.md        → final markdown output    │  │
│  │ /session/{id}/metadata.json    → form inputs, schema      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Retrieval Triggers

The agent retrieves from external storage when:

| User Question Pattern | Agent Retrieves |
|----------------------|-----------------|
| "How did you calculate X?" | Python code for that calculation |
| "What was the exact number for Y?" | Results dataframe with Y |
| "What columns are in table Z?" | Schema metadata for Z |
| "Can you explain finding #2 more?" | Relevant section of markdown report |
| "What did I say about...?" | Original form inputs |
| "Show me the raw data for..." | Subset of CSV file |

### What's NOT in Context Window

To keep context manageable, these are stored externally and only retrieved on-demand:

- Full CSV file contents (only schema + sample rows in context)
- Complete Python analysis code (only relevant snippets retrieved)
- Full markdown report (only referenced sections retrieved)
- All intermediate calculation results (retrieved by topic)

### Implementation Notes

**MVP approach:** Use simple file-based storage within the session directory. Each artifact type has a known path pattern. When the agent needs to answer a question, it determines which artifact(s) are relevant and reads them.

**Retrieval mechanism:** Agent uses tool calls to read from storage:
- `read_file(path)` — retrieve stored artifact
- `query_dataframe(table, query)` — run pandas query on stored CSV
- `get_code_for(calculation_name)` — retrieve specific analysis code

**Context summarization:** At investigation start, create a summary document that fits in context:
```
## Session Context Summary

### Files Provided
- user_activity.csv: 150K rows, 12 columns [user events table]
- users.csv: 45K rows, 8 columns [user dimension table]
- sessions.csv: 300K rows, 15 columns [session details]

### Data Model
user_activity.user_id → users.user_id
user_activity.session_id → sessions.session_id

### Metric Definition
DAU = COUNT(DISTINCT user_id) FROM user_activity GROUP BY date

### Key Context
- US-focused app, iOS ~60% of users
- New onboarding launched Dec 2
- Investigating: Dec 1-7 vs Nov 24-30
```

### Session Lifecycle

1. **Session start** — User submits form; agent creates session directory and stores all inputs
2. **Investigation** — Agent runs analysis, stores code and results in session directory
3. **Report generation** — Agent writes markdown report to session directory
4. **Q&A phase** — Agent retrieves from session directory as needed to answer questions
5. **Session end** — User closes browser or explicitly ends session; storage retained for [X hours] then deleted

---

## 7. Key Assumptions & Risks

### Assumptions to Validate

| Assumption | Risk if Wrong | Validation Approach |
|------------|---------------|---------------------|
| LLM can reliably infer column semantics from CSV headers and sample data | Agent suggests irrelevant dimensions, wastes user time | Test with 10 real table schemas; compare agent suggestions to expert DS judgment |
| Users can provide metric SQL logic (not just dashboard references) | Target users don't have access to underlying queries | Interview 5 potential users about their current investigation workflow |
| Reasoning-based driver identification is "good enough" without stats | Users don't trust findings without p-values | Build methodology, test on known historical investigations, compare to ground truth |
| CSV upload is acceptable friction for MVP | Users bounce at setup step | Track setup completion rate; gather feedback on friction points |
| Chat interface is sufficient for investigation workflow | Users need visual data exploration | Observe users during testing; note where they want to "see" data differently |

### Technical Risks

| Risk | Mitigation |
|------|------------|
| LLM generates incorrect SQL / analysis logic | Include query preview step; let user approve before execution |
| Large CSV files cause performance issues | Set file size limits for MVP; optimize or move to warehouse connection later |
| Agent "hallucinates" patterns that don't exist | Develop explicit methodology with guard rails; show underlying numbers |
| Memory retrieval returns irrelevant context | Design clear artifact naming; test retrieval accuracy on common question patterns |
| Form input doesn't capture enough context | Iterate on form fields based on user testing; allow freeform text |

---

## 8. Success Criteria

### MVP Launch Criteria
The MVP is ready for user testing when:
- [ ] Form-based input captures all required context (files with descriptions, business context, metric SQL)
- [ ] Agent can ingest 3+ CSV files and correctly infer schema relationships
- [ ] Agent proposes reasonable dimensions without user guidance in >80% of test cases
- [ ] Agent produces ranked explanations for a metric change
- [ ] Agent generates a complete markdown report
- [ ] Q&A chat allows users to ask clarifying questions about the analysis
- [ ] Agent retrieves relevant information from session memory to answer questions
- [ ] Markdown export/download works reliably

### Validation Success Metrics
The MVP is validated when:
- [ ] 5+ data scientists complete an investigation using the tool
- [ ] Average investigation time is perceived as faster than manual approach (qualitative)
- [ ] Users successfully use Q&A to clarify findings without needing to re-run investigation
- [ ] Users report they would use this tool again for future investigations
- [ ] At least 1 user identifies a root cause they might have missed manually

### Signals to Proceed to V2
- Users request warehouse connection (friction with CSV upload)
- Users request alerting/monitoring (want agent to detect, not just investigate)
- Users want to add new data mid-investigation (iteration loop)
- Users want to share reports with stakeholders (need better formatting/UI)
- Core explanation generation is trusted and accurate

---

## Appendix: Explanation Generation Methodology

*To be developed—this section will document the specific reasoning framework the agent uses to generate and rank explanations.*

### What is an Explanation?

An explanation is a potential reason (or group of related reasons) for why the metric moved. Explanations differ from raw "segments" or "drivers" in that they:
- Offer an interpretive angle or causal story, not just a data observation
- Can combine multiple related factors into a coherent narrative
- Are ranked by likelihood, not just by contribution size

### Explanation Generation Process

1. **Identify significant segments** — Find dimensions where the segment change rate meaningfully differs from overall
2. **Group related segments** — Combine segments that point to the same underlying cause (e.g., "new users" + "TikTok channel" → "new TikTok users struggling with onboarding")
3. **Formulate causal stories** — For each group, articulate what might have caused this pattern
4. **Assess independence** — Determine which explanations are truly independent vs. overlapping
5. **Rank by likelihood** — Order explanations from most to least likely

### Likelihood Ranking Criteria

| Factor | Description | Weight |
|--------|-------------|--------|
| Evidence strength | How much of the total change does this explanation account for? | High |
| Temporal alignment | Does the pattern align with known events or changes? | High |
| Segment isolation | Does the pattern persist when controlling for other factors? | Medium |
| Plausibility | Does the explanation suggest a believable causal mechanism? | Medium |
| Consistency | Is the pattern consistent across related metrics? | Medium |
| Actionability | Can someone actually do something with this finding? | Low (tiebreaker) |

### Likelihood Labels

| Label | Meaning |
|-------|---------|
| Most Likely | Strong evidence, high confidence this is a primary driver |
| Likely | Good evidence, moderate confidence, may need further investigation |
| Possible | Some evidence, but could be correlation or secondary effect |
| Less Likely | Weak evidence, likely a minor contributor or coincidence |

---

## Appendix: Competitive Landscape

*To be added—brief overview of existing tools and how this differs.*

Potential comparables:
- Metaplane, Monte Carlo (data observability—detection, not investigation)
- Mode, Hex (notebooks—general purpose, not investigation-specific)
- Narrator (metrics layer—different problem)
- Internal tools at large tech companies (not available to market)

---

## Appendix: Future Roadmap Ideas

**V2 candidates:**
- Iteration loop (add new tables mid-investigation, re-run with guidance)
- Direct warehouse connection (Snowflake, BigQuery, Redshift)
- Statistical significance testing
- Automated anomaly detection & alerting
- Saved investigations & institutional memory
- Stakeholder-ready report formatting

**V3+ candidates:**
- Multi-metric investigation (correlated movements)
- External data integration (macro trends, competitors, news)
- Team collaboration features
- Integration with BI tools (Looker, Tableau, Metabase)
