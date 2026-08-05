# src/agents/pipeline.py
# Author: Suresh D R | AI Product Developer & Technology Mentor

import os
import time
import logging

from langgraph.graph import StateGraph, END

from src.agents.nodes import (
    anomaly_node, chart_node, classifier_node, followup_node,
    guardrails_node, investigation_node, report_node,
    simple_lookup_node, synthesizer_node,
)
from src.agents.state import AnalyticsState
from src.utils.cache import get_cached_result, set_cached_result
from src.utils.config import settings

logger = logging.getLogger("sql_agent.pipeline")

# Enable LangSmith tracing if configured
if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    logger.info(f"LangSmith tracing enabled — project: {settings.LANGCHAIN_PROJECT}")


def _route_after_guardrails(state: AnalyticsState) -> str:
    return "blocked" if state.get("guardrail_blocked") else "continue"


def _route_after_classifier(state: AnalyticsState) -> str:
    return state["question_type"]


def build_pipeline():
    graph = StateGraph(AnalyticsState)

    graph.add_node("guardrails",    guardrails_node)
    graph.add_node("classifier",    classifier_node)
    graph.add_node("simple_lookup", simple_lookup_node)
    graph.add_node("investigation", investigation_node)
    graph.add_node("anomaly_scan",  anomaly_node)
    graph.add_node("chart",         chart_node)
    graph.add_node("synthesizer",   synthesizer_node)
    graph.add_node("followup",      followup_node)
    graph.add_node("report",        report_node)

    graph.set_entry_point("guardrails")
    graph.add_conditional_edges("guardrails", _route_after_guardrails, {
        "blocked": END,
        "continue": "classifier",
    })
    graph.add_conditional_edges("classifier", _route_after_classifier, {
        "simple_lookup": "simple_lookup",
        "investigative": "investigation",
    })
    graph.add_edge("simple_lookup", "anomaly_scan")
    graph.add_edge("investigation", "anomaly_scan")
    graph.add_edge("anomaly_scan",  "chart")
    graph.add_edge("chart",         "synthesizer")
    graph.add_edge("synthesizer",   "followup")
    graph.add_edge("followup",      "report")
    graph.add_edge("report",        END)

    return graph.compile()


_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


def run_pipeline(message: str, session_id: str, conversation_history: list = None) -> dict:
    start_time = time.time()

    cached = get_cached_result(message)
    if cached:
        cached["elapsed_seconds"] = round(time.time() - start_time, 3)
        cached["from_cache"] = True
        return cached

    initial_state = AnalyticsState(
        message=message,
        session_id=session_id,
        conversation_history=conversation_history or [],
        guardrail_blocked=False,
        block_reason="",
        question_type="",
        sql_used="",
        result_df=[],
        hypothesis_questions=[],
        evidence={},
        dominant_cause="",
        confidence="",
        ruled_out=[],
        anomaly_found=False,
        anomaly_description="",
        chart_type="",
        chart_json="",
        final_answer="",
        suggested_followups=[],
        report_markdown="",
    )

    pipeline = get_pipeline()
    result = pipeline.invoke(initial_state)
    elapsed = round(time.time() - start_time, 2)

    response = {
        "question_type":       result.get("question_type"),
        "blocked":             result.get("guardrail_blocked"),
        "block_reason":        result.get("block_reason"),
        "sql_used":            result.get("sql_used"),
        "answer":              result.get("final_answer"),
        "confidence":          result.get("confidence"),
        "dominant_cause":      result.get("dominant_cause"),
        "ruled_out":           result.get("ruled_out"),
        "anomaly_found":       result.get("anomaly_found"),
        "anomaly_description": result.get("anomaly_description"),
        "chart_type":          result.get("chart_type"),
        "chart_json":          result.get("chart_json"),
        "suggested_followups": result.get("suggested_followups", []),
        "report_markdown":     result.get("report_markdown", ""),
        "elapsed_seconds":     elapsed,
        "from_cache":          False,
    }

    if not response["blocked"]:
        set_cached_result(message, response)

    logger.info(
        f"session={session_id} type={response['question_type']} "
        f"blocked={response['blocked']} elapsed={elapsed}s"
    )
    return response
