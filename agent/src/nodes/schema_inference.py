"""Schema inference node for analyzing CSV file schemas.

This node reads uploaded CSV files and uses an LLM to infer:
- Column types (dimension, measure, id, timestamp)
- Data types (string, integer, float, date, datetime)
- Relationships between tables
- Recommended dimensions for drill-down analysis

Note: For MVP, files are stored locally in the session directory. The backend
saves files to sessions/<session_id>/files/ and the agent reads from the same
filesystem. File paths are passed via state["files"][i]["path"].
"""

import json
import logging
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import DataModel, InvestigationState, TableInfo
from ..tools import csv_tools

logger = logging.getLogger(__name__)


def _load_prompt_template() -> str:
    """Load the schema inference prompt template."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "schema_inference.txt"
    with open(prompt_path, "r") as f:
        return f.read()


def _build_file_descriptions(files: list[dict]) -> str:
    """Build file descriptions for the prompt."""
    descriptions = []

    for file_info in files:
        file_path = file_info["path"]

        # Verify file exists before attempting to read
        if not Path(file_path).exists():
            logger.error(f"File not found: {file_path}")
            descriptions.append(
                f"### {file_info['name']}\n"
                f"**Error**: File not found at {file_path}\n"
            )
            continue

        # Get headers and samples
        try:
            headers = csv_tools.get_headers(file_path)
            row_count = csv_tools.get_row_count(file_path)
            samples = csv_tools.sample_rows(file_path, n=10)

            # Format sample data as markdown table
            sample_table = "| " + " | ".join(headers) + " |\n"
            sample_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
            for row in samples[:5]:
                values = [str(row.get(h, ""))[:30] for h in headers]
                sample_table += "| " + " | ".join(values) + " |\n"

            desc = f"""### {file_info['name']}
**File ID**: {file_info['file_id']}
**Description**: {file_info.get('description', 'No description provided')}
**Row Count**: {row_count:,}
**Columns**: {', '.join(headers)}

**Sample Data**:
{sample_table}
"""
            descriptions.append(desc)

        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")
            descriptions.append(f"### {file_info['name']}\nError reading file: {e}\n")

    return "\n".join(descriptions)


def _parse_llm_response(response_text: str) -> DataModel:
    """Parse the LLM response into a DataModel structure."""
    # Extract JSON from the response
    try:
        # Try to find JSON block in the response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        else:
            # Try to parse the whole response as JSON
            json_str = response_text.strip()

        data = json.loads(json_str)

        # Build DataModel from parsed data
        tables = []
        for table_data in data.get("tables", []):
            table = TableInfo(
                file_id=table_data.get("file_id", ""),
                name=table_data.get("name", ""),
                row_count=table_data.get("row_count", 0),
                column_count=table_data.get("column_count", 0),
                columns=table_data.get("columns", []),
            )
            tables.append(table)

        return DataModel(
            tables=tables,
            relationships=data.get("relationships", []),
            recommended_dimensions=data.get("recommended_dimensions", []),
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        # Return empty data model on parse failure
        return DataModel(
            tables=[],
            relationships=[],
            recommended_dimensions=[],
        )


async def schema_inference(state: InvestigationState) -> dict:
    """Analyze CSV file schemas and infer data model.

    Args:
        state: Current investigation state with file information

    Returns:
        Updated state with data_model and selected_dimensions
    """
    logger.info(f"Starting schema inference for session {state['session_id']}")

    files = state.get("files", [])
    if not files:
        logger.warning("No files to analyze")
        return {
            "data_model": DataModel(
                tables=[],
                relationships=[],
                recommended_dimensions=[],
            ),
            "selected_dimensions": [],
        }

    # Build file descriptions for prompt
    file_descriptions = _build_file_descriptions(files)

    # Load prompt template
    prompt_template = _load_prompt_template()
    prompt = prompt_template.replace("{file_descriptions}", file_descriptions)

    # Call LLM
    try:
        # Import settings from backend (shared config)
        import os

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

        llm = ChatAnthropic(
            model=model,
            anthropic_api_key=api_key,
            temperature=0.2,
            max_tokens=4096,
        )

        messages = [
            SystemMessage(
                content="You are a data analyst expert. Analyze CSV schemas and return JSON."
            ),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)
        response_text = response.content

        # Parse response
        data_model = _parse_llm_response(response_text)

        # Also update file schemas in the files list
        updated_files = []
        for file_info in files:
            # Find the table info for this file
            for table in data_model["tables"]:
                if table["file_id"] == file_info["file_id"]:
                    file_info["schema"] = {"columns": table["columns"]}
                    break
            updated_files.append(file_info)

        logger.info(
            f"Schema inference complete: {len(data_model['tables'])} tables, "
            f"{len(data_model['relationships'])} relationships"
        )

        return {
            "data_model": data_model,
            "selected_dimensions": data_model.get("recommended_dimensions", []),
            "files": updated_files,
        }

    except Exception as e:
        logger.exception(f"Schema inference failed: {e}")
        return {
            "data_model": DataModel(
                tables=[],
                relationships=[],
                recommended_dimensions=[],
            ),
            "selected_dimensions": [],
            "error": f"Schema inference failed: {str(e)}",
        }
