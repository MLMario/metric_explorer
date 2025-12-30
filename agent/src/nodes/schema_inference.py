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

import logging
from pathlib import Path
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..state import (
    ColumnSchema,
    DataModel,
    InvestigationState,
    Relationship,
    TableInfo,
)
from ..tools import csv_tools

logger = logging.getLogger(__name__)


# Pydantic models for structured LLM output
class ColumnSchemaModel(BaseModel):
    """Schema for a single column - Pydantic version for LLM output."""

    name: str = Field(description="Column name from the CSV header")
    inferred_type: Literal["dimension", "measure", "id", "timestamp"] = Field(
        description="Semantic type of the column"
    )
    data_type: str = Field(
        description="Data type: string, integer, float, date, or datetime"
    )
    cardinality: int = Field(default=0, description="Number of unique values")
    sample_values: list[str] = Field(
        default_factory=list, description="Sample values from this column"
    )
    nullable: bool = Field(default=False, description="Whether column contains nulls")


class TableInfoModel(BaseModel):
    """Summary info for a table/file - Pydantic version for LLM output."""

    file_id: str = Field(description="ID of the file this table comes from")
    name: str = Field(description="Name of the table/file")
    row_count: int = Field(description="Number of rows in the table")
    column_count: int = Field(description="Number of columns")
    columns: list[ColumnSchemaModel] = Field(description="Schema for each column")


class RelationshipModel(BaseModel):
    """Detected relationship between tables - Pydantic version for LLM output."""

    from_table: str = Field(description="Source table name")
    from_column: str = Field(description="Source column name")
    to_table: str = Field(description="Target table name")
    to_column: str = Field(description="Target column name")
    relationship_type: Literal["foreign_key", "similar_values"] = Field(
        description="Type of relationship"
    )
    confidence: float = Field(description="Confidence score 0-1")


class DataModelSchema(BaseModel):
    """Inferred data model - Pydantic version for LLM output."""

    tables: list[TableInfoModel] = Field(description="List of tables with schemas")
    relationships: list[RelationshipModel] = Field(
        default_factory=list, description="Detected relationships between tables"
    )
    recommended_dimensions: list[str] = Field(
        default_factory=list,
        description="Recommended dimension columns for drill-down analysis",
    )


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


def _to_data_model(schema: DataModelSchema) -> DataModel:
    """Convert Pydantic model to TypedDict for state compatibility.

    The LLM returns a Pydantic model (DataModelSchema), but the LangGraph
    state expects TypedDict types. This function converts between them.
    """
    # Convert tables
    tables: list[TableInfo] = []
    for table in schema.tables:
        columns: list[ColumnSchema] = []
        for col in table.columns:
            columns.append(
                ColumnSchema(
                    name=col.name,
                    inferred_type=col.inferred_type,
                    data_type=col.data_type,
                    cardinality=col.cardinality,
                    sample_values=col.sample_values,
                    nullable=col.nullable,
                )
            )
        tables.append(
            TableInfo(
                file_id=table.file_id,
                name=table.name,
                row_count=table.row_count,
                column_count=table.column_count,
                columns=columns,
            )
        )

    # Convert relationships
    relationships: list[Relationship] = []
    for rel in schema.relationships:
        relationships.append(
            Relationship(
                from_table=rel.from_table,
                from_column=rel.from_column,
                to_table=rel.to_table,
                to_column=rel.to_column,
                relationship_type=rel.relationship_type,
                confidence=rel.confidence,
            )
        )

    return DataModel(
        tables=tables,
        relationships=relationships,
        recommended_dimensions=schema.recommended_dimensions,
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

    # Call LLM with structured output
    try:
        import os

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

        llm = ChatAnthropic(
            model=model,
            anthropic_api_key=api_key,
            temperature=0.2,
            max_tokens=4096,
        )

        # Use structured output to get Pydantic model directly
        structured_llm = llm.with_structured_output(DataModelSchema)

        messages = [
            SystemMessage(
                content="You are a data analyst expert. Analyze the CSV schemas provided."
            ),
            HumanMessage(content=prompt),
        ]

        # Response is already a DataModelSchema Pydantic model
        schema_response: DataModelSchema = await structured_llm.ainvoke(messages)

        # Convert Pydantic model to TypedDict for state compatibility
        data_model = _to_data_model(schema_response)

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
