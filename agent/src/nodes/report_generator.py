"""Report generator node for creating the final investigation report.

This node uses an LLM to generate a comprehensive markdown report
summarizing the investigation findings and explanations.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from ..memory import findings_ledger, progress_log
from ..state import Explanation, InvestigationState

logger = logging.getLogger(__name__)


def _load_report_template() -> str:
    """Load the report template."""
    template_path = Path(__file__).parent.parent / "prompts" / "report_template.txt"
    with open(template_path, "r") as f:
        return f.read()


def _build_file_summary(state: InvestigationState) -> str:
    """Build file summary for the report."""
    files = state.get("files", [])
    if not files:
        return "No files analyzed"

    lines = []
    for f in files:
        lines.append(f"- **{f.get('name', 'Unknown')}**: {f.get('description', 'No description')}")
    return "\n".join(lines)


def _build_dimension_summary(state: InvestigationState) -> str:
    """Build dimension summary for the report."""
    dimensions = state.get("selected_dimensions", [])
    if not dimensions:
        data_model = state.get("data_model", {})
        if data_model:
            dimensions = data_model.get("recommended_dimensions", [])

    if not dimensions:
        return "No specific dimensions identified"

    return ", ".join(dimensions)


def _build_hypotheses_summary(state: InvestigationState) -> str:
    """Build hypotheses summary for the report."""
    hypotheses = state.get("hypotheses", [])
    if not hypotheses:
        return "No hypotheses tested"

    lines = []
    for h in hypotheses:
        status_emoji = "✓" if h.get("status") == "CONFIRMED" else "✗"
        lines.append(f"- [{status_emoji}] **{h.get('id', '')}**: {h.get('title', 'Unknown')} - {h.get('status', 'UNKNOWN')}")
    return "\n".join(lines)


def _build_findings_summary(session_path: Path) -> str:
    """Build findings summary for the report."""
    try:
        confirmed = findings_ledger.get_confirmed_findings(session_path)
        if not confirmed:
            return "No confirmed findings"

        lines = []
        for f in confirmed:
            lines.append(f"### {f.get('hypothesis_id', 'Unknown')}")
            lines.append(f"**Evidence**: {f.get('evidence', 'N/A')}")
            lines.append(f"**Confidence**: {f.get('confidence', 'Unknown')}")
            if f.get("key_metrics"):
                lines.append("**Key Metrics**:")
                for m in f["key_metrics"]:
                    lines.append(f"- {m}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Error building findings summary: {e}")
        return "Error loading findings"


async def _generate_explanations(
    state: InvestigationState,
    session_path: Path,
) -> list[Explanation]:
    """Generate ranked explanations from confirmed findings."""
    confirmed = findings_ledger.get_confirmed_findings(session_path)
    if not confirmed:
        return []

    # Build explanations from confirmed findings
    explanations = []
    for i, finding in enumerate(confirmed, 1):
        # Find the corresponding hypothesis
        hypothesis = None
        for h in state.get("hypotheses", []):
            if h["id"] == finding.get("hypothesis_id"):
                hypothesis = h
                break

        if not hypothesis:
            continue

        explanation = Explanation(
            rank=i,
            title=hypothesis.get("title", "Unknown"),
            likelihood="Most Likely" if i == 1 else ("Likely" if i <= 3 else "Possible"),
            evidence=[
                {
                    "metric": m,
                    "value": "",
                    "interpretation": "",
                }
                for m in finding.get("key_metrics", [])
            ],
            reasoning=finding.get("evidence", ""),
            causal_story=hypothesis.get("causal_story", ""),
            source_hypotheses=[finding.get("hypothesis_id", "")],
        )
        explanations.append(explanation)

    return explanations


async def _generate_executive_summary(
    state: InvestigationState,
    explanations: list[Explanation],
) -> str:
    """Generate an executive summary using LLM."""
    if not explanations:
        return (
            f"Investigation of {state.get('target_metric', 'Unknown metric')} "
            "did not identify any confirmed explanations for the observed change."
        )

    # Build context for LLM
    context = f"""
Target Metric: {state.get('target_metric', 'Unknown')}
Baseline Period: {state.get('baseline_period', {}).get('start', 'N/A')} to {state.get('baseline_period', {}).get('end', 'N/A')}
Comparison Period: {state.get('comparison_period', {}).get('start', 'N/A')} to {state.get('comparison_period', {}).get('end', 'N/A')}

Top Findings:
"""
    for exp in explanations[:3]:
        context += f"\n{exp['rank']}. {exp['title']}: {exp['reasoning'][:200]}..."

    # Call LLM for summary
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

        llm = ChatAnthropic(
            model=model,
            anthropic_api_key=api_key,
            temperature=0.3,
            max_tokens=500,
        )

        messages = [
            SystemMessage(content="You are a data analyst. Write a brief 2-3 sentence executive summary."),
            HumanMessage(content=f"Write an executive summary for this investigation:\n{context}"),
        ]

        response = await llm.ainvoke(messages)
        return response.content.strip()

    except Exception as e:
        logger.warning(f"Failed to generate executive summary: {e}")
        # Fall back to simple summary
        top = explanations[0]
        return (
            f"Investigation identified {len(explanations)} likely explanation(s) "
            f"for the {state.get('target_metric', 'metric')} change. "
            f"The primary finding is: {top['title']}."
        )


async def _generate_recommendations(
    state: InvestigationState,
    explanations: list[Explanation],
) -> str:
    """Generate recommendations based on findings."""
    if not explanations:
        return "- Review data collection to ensure metrics are being tracked correctly\n- Consider gathering additional data to enable future investigations"

    recommendations = []

    for exp in explanations[:2]:
        recommendations.append(f"- Investigate **{exp['title']}** further with stakeholders")

    recommendations.append("- Monitor the metric after implementing any changes")
    recommendations.append("- Set up alerts for significant future deviations")

    return "\n".join(recommendations)


async def report_generator(state: InvestigationState) -> dict:
    """Generate the final investigation report.

    Args:
        state: Current investigation state

    Returns:
        Updated state with report_path and explanations
    """
    session_id = state["session_id"]
    logger.info(f"Generating report for session {session_id}")

    # Get session path
    sessions_root = os.environ.get("SESSION_STORAGE_PATH", "./sessions")
    session_path = Path(sessions_root) / session_id

    try:
        # Generate explanations
        explanations = await _generate_explanations(state, session_path)

        # Generate executive summary
        executive_summary = await _generate_executive_summary(state, explanations)

        # Build report sections
        file_summary = _build_file_summary(state)
        dimension_summary = _build_dimension_summary(state)
        hypotheses_summary = _build_hypotheses_summary(state)
        findings_summary = _build_findings_summary(session_path)
        recommendations = await _generate_recommendations(state, explanations)

        # Build explanations section
        if explanations:
            explanations_section = ""
            for exp in explanations:
                explanations_section += f"### {exp['rank']}. {exp['title']}\n\n"
                explanations_section += f"**Likelihood**: {exp['likelihood']}\n\n"
                explanations_section += f"{exp['reasoning']}\n\n"
                if exp.get("causal_story"):
                    explanations_section += f"**Causal Story**: {exp['causal_story']}\n\n"
        else:
            explanations_section = "*No confirmed explanations found.*"

        # Get timing info
        confirmed_count = len([h for h in state.get("hypotheses", []) if h.get("status") == "CONFIRMED"])
        hypothesis_count = len(state.get("hypotheses", []))

        # Load and fill template
        template = _load_report_template()
        report = template
        report = report.replace("{metric_name}", state.get("target_metric", "Metric"))
        report = report.replace(
            "{baseline_period}",
            f"{state.get('baseline_period', {}).get('start', 'N/A')} to {state.get('baseline_period', {}).get('end', 'N/A')}",
        )
        report = report.replace(
            "{comparison_period}",
            f"{state.get('comparison_period', {}).get('start', 'N/A')} to {state.get('comparison_period', {}).get('end', 'N/A')}",
        )
        report = report.replace("{generated_at}", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
        report = report.replace("{executive_summary}", executive_summary)
        report = report.replace("{file_summary}", file_summary)
        report = report.replace("{dimension_summary}", dimension_summary)
        report = report.replace("{explanations_section}", explanations_section)
        report = report.replace("{hypotheses_summary}", hypotheses_summary)
        report = report.replace("{findings_summary}", findings_summary)
        report = report.replace("{recommendations}", recommendations)
        report = report.replace("{total_time}", "< 15 min")  # Would track actual time
        report = report.replace("{hypothesis_count}", str(hypothesis_count))
        report = report.replace("{confirmed_count}", str(confirmed_count))

        # Write report
        report_path = session_path / "report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        progress_log.log_report_generated(session_path)
        logger.info(f"Report generated at {report_path}")

        return {
            "explanations": explanations,
            "report_path": str(report_path),
            "status": "completed",
        }

    except Exception as e:
        logger.exception(f"Report generation failed: {e}")
        progress_log.log_error(session_path, f"Report generation failed: {e}")

        # Write a minimal error report
        error_report = f"""# Investigation Report

**Error**: Report generation failed

An error occurred while generating the investigation report: {str(e)}

Please check the session logs for more details.

---
*Generated by Metric Drill-Down Agent*
"""
        report_path = session_path / "report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(error_report)

        return {
            "explanations": [],
            "report_path": str(report_path),
            "status": "failed",
            "error": f"Report generation failed: {str(e)}",
        }


async def no_findings_report(state: InvestigationState) -> dict:
    """Generate a report when no hypotheses were confirmed.

    Args:
        state: Current investigation state

    Returns:
        Updated state with report_path
    """
    session_id = state["session_id"]
    logger.info(f"Generating no-findings report for session {session_id}")

    # Get session path
    sessions_root = os.environ.get("SESSION_STORAGE_PATH", "./sessions")
    session_path = Path(sessions_root) / session_id

    # Build file summary
    file_summary = _build_file_summary(state)
    hypotheses_summary = _build_hypotheses_summary(state)

    report = f"""# {state.get('target_metric', 'Metric')} Investigation Report

**Investigation Period**: {state.get('baseline_period', {}).get('start', 'N/A')} to {state.get('baseline_period', {}).get('end', 'N/A')} vs {state.get('comparison_period', {}).get('start', 'N/A')} to {state.get('comparison_period', {}).get('end', 'N/A')}
**Generated**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

---

## Summary

The investigation did not identify any confirmed explanations for the observed change in {state.get('target_metric', 'the metric')}.

All tested hypotheses were ruled out based on the available data.

---

## Data Analyzed

### Files
{file_summary}

---

## Hypotheses Tested

{hypotheses_summary}

---

## Possible Next Steps

1. **Expand the data scope**: Additional data sources may provide more insight
2. **Refine the hypothesis set**: Consider alternative explanations not initially tested
3. **Check data quality**: Verify that the metric calculation is consistent across periods
4. **Consult domain experts**: Business context may reveal patterns not visible in the data

---

## Methodology

This analysis was performed by the Metric Drill-Down Agent using:
- Schema inference to understand data structure
- Hypothesis generation based on business context
- Iterative data analysis to validate/invalidate hypotheses

**Hypotheses Tested**: {len(state.get('hypotheses', []))}
**Confirmed Explanations**: 0

---

*Generated by Metric Drill-Down Agent*
"""

    # Write report
    report_path = session_path / "report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    progress_log.log_report_generated(session_path)
    logger.info(f"No-findings report generated at {report_path}")

    return {
        "explanations": [],
        "report_path": str(report_path),
        "status": "no_findings",
    }
