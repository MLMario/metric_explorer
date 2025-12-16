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

4. **Hypothesis Generation** — The agent investigates and produces 3-5 ranked hypotheses explaining the metric movement, supported by data analysis

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
| Hypothesis output | Produces ranked list of hypotheses with supporting data |
| Iteration loop | User provides feedback, new tables, or new directions; agent adjusts and re-runs |

**Interface:**
- Chat-based interaction (Streamlit or CLI)
- Markdown report export

### What's Explicitly Out (Deferred to Future Versions)

| Capability | Reason for Deferral |
|------------|---------------------|
| Automatic anomaly detection | Requires persistent monitoring infrastructure; user can trigger manually for MVP |
| Direct warehouse connection | CSV upload simplifies auth, security, and setup; validates core value first |
| Statistical significance testing | Agent can reason about magnitude and patterns without formal hypothesis testing; reduces complexity |
| Pre-aggregated metric tables | MVP assumes user provides raw metric logic; agent doesn't need to reverse-engineer dashboard tables |
| Rich visual UI | Chat + markdown export is sufficient to validate; UI can come later |
| Persistent memory across sessions | Each investigation is standalone for MVP |
| External context gathering | No macro/news data integration; user provides context verbally if needed |

### MVP Assumptions

1. **Metric query assumption** — User provides the actual SQL logic to calculate the metric, not a pre-aggregated table. This means the agent can understand what's being measured and how.

2. **CSV-based data** — For MVP, the agent works with user-uploaded CSV files rather than connecting directly to a warehouse. This simplifies setup and allows faster iteration.

3. **Reasoning-based driver identification** — The agent identifies drivers through logical reasoning about magnitudes, proportions, and patterns rather than formal statistical tests. We will develop a specific methodology for how the agent reasons through driver identification.

---

## 4. User Flow

### Happy Path

```
┌─────────────────────────────────────────────────────────────────┐
│ USER                                                            │
│ Investigate why DAU dropped.                                    │
│                                                                 │
│ Metric query:                                                   │
│ SELECT date, COUNT(DISTINCT user_id) as dau                     │
│ FROM user_activity                                              │
│ GROUP BY date                                                   │
│                                                                 │
│ Compare: last 7 days vs prior 7 days                            │
│                                                                 │
│ [Attached: user_activity.csv, users.csv, sessions.csv]          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT                                                           │
│ I've analyzed your uploaded tables:                             │
│                                                                 │
│ • user_activity.csv (150K rows, 12 columns)                     │
│ • users.csv (45K rows, 8 columns)                               │
│ • sessions.csv (300K rows, 15 columns)                          │
│                                                                 │
│ Data model:                                                     │
│ • user_activity joins to users on user_id                       │
│ • sessions joins to user_activity on session_id                 │
│                                                                 │
│ Recommended dimensions to segment by:                           │
│ 1. platform (user_activity) — categorical, 3 values             │
│ 2. country (users) — categorical, 12 values                     │
│ 3. user_tenure_bucket (derived from users.created_at)           │
│ 4. acquisition_channel (users.utm_source)                       │
│                                                                 │
│ Should I proceed with these, or would you like to adjust?       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ USER                                                            │
│ Add device_type from sessions. Proceed.                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT                                                           │
│ Running analysis...                                             │
│                                                                 │
│ ## DAU Change: -8.2% WoW                                        │
│ Baseline: 42,340 → Current: 38,870                              │
│                                                                 │
│ ### Top Contributing Segments                                   │
│                                                                 │
│ **1. iOS + United States**                                      │
│ Contribution: 62% of total decline                              │
│ Segment change: -14.3% (vs -8.2% overall)                       │
│ This segment went from 18,200 to 15,600 DAU                     │
│ Reasoning: Decline rate nearly 2x the overall rate;             │
│ largest absolute user base makes this the primary driver        │
│                                                                 │
│ **2. New users (0-7 days tenure)**                              │
│ Contribution: 24% of total decline                              │
│ Segment change: -11.1%                                          │
│ Hypothesis: Possible onboarding issue or acquisition            │
│ channel quality shift                                           │
│                                                                 │
│ **3. device_type = iPhone 12**                                  │
│ Contribution: 18% of total decline                              │
│ Unexpected concentration in single device model                 │
│ Hypothesis: App compatibility or performance issue              │
│                                                                 │
│ ### Suggested Next Steps                                        │
│ • Investigate iOS app crashes or performance issues             │
│ • Check acquisition channel mix for new user changes            │
│ • Look at iPhone 12-specific session metrics                    │
│                                                                 │
│ Want me to explore any of these further?                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ USER                                                            │
│ Here's our crash logs. Can you check if crashes correlate       │
│ with the iPhone 12 finding?                                     │
│                                                                 │
│ [Attached: app_crashes.csv]                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT                                                           │
│ Analyzing app_crashes.csv...                                    │
│                                                                 │
│ **Finding: Strong correlation confirmed**                       │
│                                                                 │
│ iPhone 12 crash rate:                                           │
│ • Prior period: 0.8%                                            │
│ • Current period: 3.5%                                          │
│ • Change: +340%                                                 │
│                                                                 │
│ Timing aligns with the DAU drop. Other device models show       │
│ no significant crash rate change.                               │
│                                                                 │
│ **Confidence: High**                                            │
│ Timing match + segment isolation + magnitude all support        │
│ this as a root cause.                                           │
│                                                                 │
│ **Recommended action:**                                         │
│ Flag to engineering team. Check recent iOS releases or          │
│ app updates that may have introduced iPhone 12                  │
│ compatibility issues.                                           │
│                                                                 │
│ Want me to export this analysis?                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ USER                                                            │
│ Yes, export it.                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT                                                           │
│ [Generates markdown report for download]                        │
│                                                                 │
│ Report exported: dau_investigation_2024-12-06.md                │
└─────────────────────────────────────────────────────────────────┘
```

### Iteration Scenarios

**Scenario A: User disagrees with dimension selection**
```
AGENT: Recommended dimensions: platform, country, user_tenure...
USER: Don't bother with country, we're US-only. 
      Focus on feature_used from the sessions table instead.
AGENT: Got it. Removing country, adding feature_used. Proceeding...
```

**Scenario B: Initial hypotheses don't pan out**
```
AGENT: Top segments are iOS/US and new users...
USER: We already checked iOS—no issues there. 
      Can you dig deeper into the new user segment? 
      Maybe break it down by acquisition channel.
AGENT: Re-running with acquisition_channel breakdown for new users...
```

**Scenario C: User provides new context mid-investigation**
```
USER: Actually, we launched a new onboarding flow on Monday. 
      Can you check if the drop aligns with that date?
AGENT: Analyzing daily breakdown around Monday...
       [Finds step-change on Monday]
       The drop does align with Monday's launch.
```

---

## 5. Key Assumptions & Risks

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
| Iteration context gets lost in long conversations | Maintain structured state object; summarize context periodically |

---

## 6. Success Criteria

### MVP Launch Criteria
The MVP is ready for user testing when:
- [ ] Agent can ingest 3+ CSV files and correctly infer schema relationships
- [ ] Agent proposes reasonable dimensions without user guidance in >80% of test cases
- [ ] Agent produces a ranked hypothesis list for a metric change
- [ ] User can provide feedback and agent adjusts analysis accordingly
- [ ] User can upload additional tables mid-conversation
- [ ] Markdown export works reliably

### Validation Success Metrics
The MVP is validated when:
- [ ] 5+ data scientists complete an investigation using the tool
- [ ] Average investigation time is perceived as faster than manual approach (qualitative)
- [ ] Users report they would use this tool again for future investigations
- [ ] At least 1 user identifies a root cause they might have missed manually

### Signals to Proceed to V2
- Users request warehouse connection (friction with CSV upload)
- Users request alerting/monitoring (want agent to detect, not just investigate)
- Users want to share reports with stakeholders (need better formatting/UI)
- Core hypothesis generation is trusted and accurate

---

## Appendix: Driver Identification Methodology

*To be developed—this section will document the specific reasoning framework the agent uses to identify and rank drivers.*

Key principles to incorporate:
- Contribution sizing (what % of total change does this segment explain?)
- Rate comparison (is segment change rate meaningfully different from overall?)
- Isolation (does the pattern persist when controlling for other dimensions?)
- Plausibility (does the pattern suggest a believable causal mechanism?)
- Actionability (can someone actually do something with this finding?)

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
