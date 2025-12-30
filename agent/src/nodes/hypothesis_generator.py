"""Hypothesis generator node for generating potential explanations.

This node uses an LLM to generate 5-7 hypotheses that could explain
the metric movement based on the business context and available dimensions.
"""

import logging
import os
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..state import Hypothesis, InvestigationState

logger = logging.getLogger(__name__)


# Pydantic models for structured LLM output
class HypothesisModel(BaseModel):
    """Pydantic model for a single hypothesis - for LLM output."""

    id: str = Field(description="Unique identifier like H1, H2, etc.")
    title: str = Field(description="Short title for the hypothesis")
    causal_story: str = Field(
        description="Explanation of why this might cause the metric change"
    )
    dimensions: list[str] = Field(
        default_factory=list, description="Dimensions to investigate"
    )
    expected_pattern: str = Field(
        description="What pattern we expect to see if hypothesis is true"
    )
    priority: int = Field(description="Priority ranking, 1 = highest")


class HypothesesResponse(BaseModel):
    """Wrapper for list of hypotheses - for LLM structured output."""

    hypotheses: list[HypothesisModel] = Field(
        description="List of 5-7 hypotheses to investigate"
    )


def _to_hypotheses(response: HypothesesResponse) -> list[Hypothesis]:
    """Convert Pydantic model to list of TypedDict for state compatibility.

    The LLM returns a Pydantic model (HypothesesResponse), but the LangGraph
    state expects TypedDict types. This function converts between them.
    """
    return [
        Hypothesis(
            id=h.id,
            title=h.title,
            causal_story=h.causal_story,
            dimensions=h.dimensions,
            expected_pattern=h.expected_pattern,
            priority=h.priority,
            status="PENDING",
        )
        for h in response.hypotheses
    ]


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

        # Use structured output to get Pydantic model directly
        structured_llm = llm.with_structured_output(HypothesesResponse)

        messages = [
            SystemMessage(
                content=(
                    "You are a data scientist expert at generating testable hypotheses "
                    "for metric investigations."
                )
            ),
            HumanMessage(content=prompt),
        ]

        # Response is already a HypothesesResponse Pydantic model
        response: HypothesesResponse = await structured_llm.ainvoke(messages)

        # Convert Pydantic model to TypedDict for state compatibility
        hypotheses = _to_hypotheses(response)

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
