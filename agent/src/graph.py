"""LangGraph state machine for the investigation workflow.

This module defines the agent graph that orchestrates the investigation process:
1. Schema Inference - Analyze CSV file schemas
2. Metric Identification - Validate target metric exists
3. Hypothesis Generation - Generate potential explanations
4. Analysis Execution - Investigate each hypothesis (Claude Agent SDK)
5. Memory Dump - Store findings in Supabase for RAG
6. Report Generation - Compile final markdown report
"""

from langgraph.graph import END, StateGraph

from .nodes import (
    analysis_execution,
    hypothesis_generator,
    memory_dump,
    metric_identification,
    no_findings_report,
    report_generator,
    schema_inference,
)
from .state import InvestigationState


def should_continue_after_metric_validation(state: InvestigationState) -> str:
    """Conditional edge after metric identification.

    Returns:
        'continue' if metric validated, 'error' if not found
    """
    if state.get("metric_requirements") and state["metric_requirements"].get("validated"):
        return "continue"
    return "error"


def should_generate_report(state: InvestigationState) -> str:
    """Conditional edge after memory dump.

    Returns:
        'report' if findings exist, 'no_findings' if none confirmed
    """
    findings = state.get("findings_ledger", [])
    confirmed = [f for f in findings if f.get("outcome") == "CONFIRMED"]
    if confirmed:
        return "report"
    return "no_findings"


def error_exit(state: InvestigationState) -> dict:
    """Handle error exit from the graph."""
    return {
        "status": "failed",
        "error": state.get("metric_requirements", {}).get(
            "error_message", "Metric validation failed"
        ),
    }


def create_investigation_graph() -> StateGraph:
    """Create the investigation workflow graph.

    Graph structure:
        START -> schema_inference -> metric_identification
        metric_identification --(validated)--> hypothesis_generator
        metric_identification --(not validated)--> END (error)
        hypothesis_generator -> analysis_execution
        analysis_execution -> memory_dump
        memory_dump --(has findings)--> report_generator -> END
        memory_dump --(no findings)--> no_findings_report -> END
    """
    # Create graph with InvestigationState
    graph = StateGraph(InvestigationState)

    # Add nodes with actual implementations
    graph.add_node("schema_inference", schema_inference)
    graph.add_node("metric_identification", metric_identification)
    graph.add_node("hypothesis_generator", hypothesis_generator)
    graph.add_node("analysis_execution", analysis_execution)
    graph.add_node("memory_dump", memory_dump)
    graph.add_node("report_generator", report_generator)
    graph.add_node("no_findings_report", no_findings_report)
    graph.add_node("error_exit", error_exit)

    # Set entry point
    graph.set_entry_point("schema_inference")

    # Add edges
    graph.add_edge("schema_inference", "metric_identification")

    # Conditional edge after metric identification (T063)
    graph.add_conditional_edges(
        "metric_identification",
        should_continue_after_metric_validation,
        {
            "continue": "hypothesis_generator",
            "error": "error_exit",
        },
    )

    graph.add_edge("hypothesis_generator", "analysis_execution")
    graph.add_edge("analysis_execution", "memory_dump")

    # Conditional edge after memory dump (T064)
    graph.add_conditional_edges(
        "memory_dump",
        should_generate_report,
        {
            "report": "report_generator",
            "no_findings": "no_findings_report",
        },
    )

    # Terminal edges
    graph.add_edge("report_generator", END)
    graph.add_edge("no_findings_report", END)
    graph.add_edge("error_exit", END)

    return graph


def compile_graph():
    """Compile the investigation graph for execution."""
    graph = create_investigation_graph()
    return graph.compile()


# Compiled graph instance (lazy initialization)
_compiled_graph = None


def get_graph():
    """Get the compiled investigation graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_graph()
    return _compiled_graph
