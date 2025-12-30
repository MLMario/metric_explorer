"""Hypothesis generator node for generating potential explanations.

This node uses an LLM to generate 5-7 hypotheses that could explain
the metric movement based on the business context and available dimensions.
"""

import json
import logging
import os
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import Hypothesis, InvestigationState

logger = logging.getLogger(__name__)


def _load_prompt_template() -> str:
    """Load the hypothesis generation prompt template."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "hypothesis_generation.txt"
    with open(prompt_path, "r") as f:
        return f.read()


def _build_prompt(state: InvestigationState) -> str:
    """Build the hypothesis generation prompt from state."""
    template = _load_prompt_template()

    # Get metric requirements
    metric_req = state.get("metric_requirements", {})
    source_file = metric_req.get("source_file", {}) if metric_req else {}

    # Get date ranges
    baseline = state.get("baseline_period", {})
    comparison = state.get("comparison_period", {})

    # Get available dimensions from data model
    data_model = state.get("data_model", {})
    dimensions = data_model.get("recommended_dimensions", []) if data_model else []

    # Also include dimension columns from schema
    if data_model and data_model.get("tables"):
        for table in data_model["tables"]:
            for col in table.get("columns", []):
                if col.get("inferred_type") == "dimension":
                    dim_name = col.get("name", "")
                    if dim_name and dim_name not in dimensions:
                        dimensions.append(dim_name)

    # Build prompt
    prompt = template
    prompt = prompt.replace("{target_metric}", state.get("target_metric", ""))
    prompt = prompt.replace("{metric_definition}", state.get("metric_definition", ""))
    prompt = prompt.replace(
        "{source_file}",
        f"{source_file.get('file_name', 'Unknown')} (ID: {source_file.get('file_id', 'N/A')})"
        if source_file
        else "Unknown",
    )
    prompt = prompt.replace("{baseline_start}", baseline.get("start", ""))
    prompt = prompt.replace("{baseline_end}", baseline.get("end", ""))
    prompt = prompt.replace("{comparison_start}", comparison.get("start", ""))
    prompt = prompt.replace("{comparison_end}", comparison.get("end", ""))
    prompt = prompt.replace(
        "{business_context}", state.get("business_context", "No context provided")
    )
    prompt = prompt.replace(
        "{investigation_prompt}",
        state.get("investigation_prompt") or "No specific focus areas provided",
    )
    prompt = prompt.replace(
        "{available_dimensions}",
        ", ".join(dimensions) if dimensions else "No dimensions identified",
    )

    return prompt


def _parse_hypotheses(response_text: str) -> list[Hypothesis]:
    """Parse LLM response into list of Hypothesis objects."""
    try:
        # Extract JSON from the response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        else:
            json_str = response_text.strip()

        data = json.loads(json_str)

        # Handle both array and object with hypotheses key
        if isinstance(data, dict) and "hypotheses" in data:
            hypothesis_list = data["hypotheses"]
        elif isinstance(data, list):
            hypothesis_list = data
        else:
            logger.error("Unexpected JSON structure in hypothesis response")
            return []

        hypotheses = []
        for i, h in enumerate(hypothesis_list):
            hypothesis = Hypothesis(
                id=h.get("id", f"H{i+1}"),
                title=h.get("title", f"Hypothesis {i+1}"),
                causal_story=h.get("causal_story", ""),
                dimensions=h.get("dimensions", []),
                expected_pattern=h.get("expected_pattern", ""),
                priority=h.get("priority", i + 1),
                status="PENDING",
            )
            hypotheses.append(hypothesis)

        return hypotheses

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse hypothesis JSON: {e}")
        return []


async def hypothesis_generator(state: InvestigationState) -> dict:
    """Generate hypotheses for the metric movement.

    Args:
        state: Current investigation state

    Returns:
        Updated state with generated hypotheses
    """
    logger.info(f"Generating hypotheses for session {state['session_id']}")

    # Build prompt
    prompt = _build_prompt(state)

    try:
        # Call LLM
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

        llm = ChatAnthropic(
            model=model,
            anthropic_api_key=api_key,
            temperature=0.7,  # Higher temp for creative hypothesis generation
            max_tokens=4096,
        )

        messages = [
            SystemMessage(
                content=(
                    "You are a data scientist expert at generating testable hypotheses "
                    "for metric investigations. Generate hypotheses in JSON format."
                )
            ),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)
        response_text = response.content

        # Parse hypotheses
        hypotheses = _parse_hypotheses(response_text)

        if not hypotheses:
            # Generate default hypothesis if parsing failed
            logger.warning("Failed to parse hypotheses, using default")
            hypotheses = [
                Hypothesis(
                    id="H1",
                    title="Segment-level change",
                    causal_story="A specific segment may be driving the overall metric change",
                    dimensions=state.get("selected_dimensions", [])[:2],
                    expected_pattern="One segment shows disproportionate change",
                    priority=1,
                    status="PENDING",
                )
            ]

        logger.info(f"Generated {len(hypotheses)} hypotheses")

        return {"hypotheses": hypotheses}

    except Exception as e:
        logger.exception(f"Hypothesis generation failed: {e}")
        # Return a default hypothesis on failure
        return {
            "hypotheses": [
                Hypothesis(
                    id="H1",
                    title="Data exploration",
                    causal_story="Explore the data to identify potential causes",
                    dimensions=[],
                    expected_pattern="Unknown",
                    priority=1,
                    status="PENDING",
                )
            ],
            "error": f"Hypothesis generation failed: {str(e)}",
        }
