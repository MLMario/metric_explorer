"""Metric identification node for validating target metric exists.

This node validates that the user-specified target metric column
exists in at least one of the uploaded files. No LLM call is needed -
this is a pure Python lookup operation.
"""

import logging

from ..state import InvestigationState, MetricRequirements

logger = logging.getLogger(__name__)


def metric_identification(state: InvestigationState) -> dict:
    """Validate that the target metric column exists in uploaded files.

    This is a pure Python validation - no LLM call needed.
    The user explicitly provides the column name, we just verify it exists.

    Args:
        state: Current investigation state with files and target_metric

    Returns:
        Updated state with metric_requirements
    """
    target_metric = state.get("target_metric", "")
    files = state.get("files", [])
    data_model = state.get("data_model")

    logger.info(f"Validating target metric: {target_metric}")

    if not target_metric:
        return {
            "metric_requirements": MetricRequirements(
                target_metric="",
                source_file=None,
                validated=False,
                error_message="Target metric column name is required",
            )
        }

    # Search for target_metric column in all file schemas
    all_columns = set()

    # First try to find in data_model (has enriched schema info)
    if data_model and data_model.get("tables"):
        for table in data_model["tables"]:
            for column in table.get("columns", []):
                col_name = column.get("name", "")
                all_columns.add(col_name)

                if col_name.lower() == target_metric.lower():
                    logger.info(
                        f"Found target metric '{target_metric}' in {table['name']}"
                    )
                    return {
                        "metric_requirements": MetricRequirements(
                            target_metric=target_metric,
                            source_file={
                                "file_id": table["file_id"],
                                "file_name": table["name"],
                            },
                            validated=True,
                            error_message=None,
                        )
                    }

    # Fall back to checking file schemas directly
    for file_info in files:
        schema = file_info.get("schema")
        if schema and schema.get("columns"):
            for column in schema["columns"]:
                col_name = column.get("name", "") if isinstance(column, dict) else column
                all_columns.add(col_name)

                if str(col_name).lower() == target_metric.lower():
                    logger.info(
                        f"Found target metric '{target_metric}' in {file_info['name']}"
                    )
                    return {
                        "metric_requirements": MetricRequirements(
                            target_metric=target_metric,
                            source_file={
                                "file_id": file_info["file_id"],
                                "file_name": file_info["name"],
                            },
                            validated=True,
                            error_message=None,
                        )
                    }

    # If not found in schema, try reading headers directly from files
    from ..tools import csv_tools

    for file_info in files:
        try:
            headers = csv_tools.get_headers(file_info["path"])
            for header in headers:
                all_columns.add(header)
                if header.lower() == target_metric.lower():
                    logger.info(
                        f"Found target metric '{target_metric}' in {file_info['name']} headers"
                    )
                    return {
                        "metric_requirements": MetricRequirements(
                            target_metric=target_metric,
                            source_file={
                                "file_id": file_info["file_id"],
                                "file_name": file_info["name"],
                            },
                            validated=True,
                            error_message=None,
                        )
                    }
        except Exception as e:
            logger.warning(f"Error reading headers from {file_info['path']}: {e}")

    # Column not found
    sorted_columns = sorted(all_columns)
    error_message = (
        f"Column '{target_metric}' not found in any uploaded file. "
        f"Available columns: {', '.join(sorted_columns)}"
    )

    logger.warning(error_message)

    return {
        "metric_requirements": MetricRequirements(
            target_metric=target_metric,
            source_file=None,
            validated=False,
            error_message=error_message,
        )
    }
