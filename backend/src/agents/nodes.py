# src/agents/nodes.py
# Author: Suresh D R | AI Product Developer & Technology Mentor

import json
import logging
from datetime import datetime

import pandas as pd

from src.agents.agent_factory import (
    ANOMALY_PROMPT, CLASSIFIER_PROMPT, GUARDRAILS_PROMPT,
    HYPOTHESIS_PROMPT, RANKER_PROMPT, SYNTHESIZER_PROMPT,
    call_followup, call_full_json, call_mini_json, call_mini_text,
)
from src.agents.state import AnalyticsState
from src.tools.chart_tools import build_chart
from src.tools.sql_tools import run_sql_pipeline
from src.utils.cache import check_investigative_circuit_breaker

logger = logging.getLogger("sql_agent.pipeline")


def guardrails_node(state: AnalyticsState) -> AnalyticsState:
    result = call_mini_json(GUARDRAILS_PROMPT, state["message"])
    state["guardrail_blocked"] = not result.get("safe", True)
    state["block_reason"] = result.get("reason", "")
    if state["guardrail_blocked"]:
        logger.warning(f"Guardrail blocked: {state['block_reason']} | session={state['session_id']}")
    return state


def classifier_node(state: AnalyticsState) -> AnalyticsState:
    result = call_mini_json(CLASSIFIER_PROMPT, state["message"])
    state["question_type"] = result.get("type", "simple_lookup")
    return state


def simple_lookup_node(state: AnalyticsState) -> AnalyticsState:
    pipeline_result = run_sql_pipeline(
        state["message"],
        conversation_history=state.get("conversation_history", [])
    )
    if pipeline_result["success"]:
        state["sql_used"] = pipeline_result["sql"]
        state["result_df"] = pipeline_result["df"].to_dict(orient="records")
    else:
        state["sql_used"] = ""
        state["result_df"] = []
        state["block_reason"] = pipeline_result["reason"]
    return state


def investigation_node(state: AnalyticsState) -> AnalyticsState:
    if not check_investigative_circuit_breaker(state["session_id"]):
        state["dominant_cause"] = ""
        state["confidence"] = "LOW"
        state["ruled_out"] = []
        state["evidence"] = {}
        state["result_df"] = []
        state["block_reason"] = (
            "Investigative question limit reached for this session. "
            "Simple lookups still work — try again in a few minutes."
        )
        state["guardrail_blocked"] = True
        return state

    hyp_result = call_full_json(HYPOTHESIS_PROMPT, state["message"])
    state["hypothesis_questions"] = hyp_result.get("hypothesis_questions", [])

    evidence = {}
    first_success_df = None
    for i, question in enumerate(state["hypothesis_questions"], 1):
        pr = run_sql_pipeline(question)
        evidence[f"hypothesis_{i}"] = {
            "question": question,
            "success": pr["success"],
            "data": pr["df"].to_dict(orient="records") if pr["success"] else None,
        }
        if pr["success"] and first_success_df is None and not pr["df"].empty:
            first_success_df = pr["df"]

    state["evidence"] = evidence
    ranking = call_full_json(RANKER_PROMPT, json.dumps(evidence, default=str))
    state["dominant_cause"] = ranking.get("dominant_cause") or ""
    state["confidence"] = ranking.get("confidence", "LOW")
    state["ruled_out"] = ranking.get("ruled_out", [])
    state["result_df"] = (
        first_success_df.to_dict(orient="records") if first_success_df is not None else []
    )
    return state


def anomaly_node(state: AnalyticsState) -> AnalyticsState:
    if state["result_df"]:
        result = call_mini_json(
            ANOMALY_PROMPT,
            f"Question: {state['message']}\nResult: {json.dumps(state['result_df'], default=str)}",
        )
        state["anomaly_found"] = result.get("anomaly_found", False)
        state["anomaly_description"] = result.get("description", "")
    else:
        state["anomaly_found"] = False
        state["anomaly_description"] = ""
    return state


def chart_node(state: AnalyticsState) -> AnalyticsState:
    if state["result_df"]:
        df = pd.DataFrame(state["result_df"])
        chart_json, chart_type = build_chart(df, state["message"][:60])
        state["chart_json"] = chart_json or ""
        state["chart_type"] = chart_type
    else:
        state["chart_json"] = ""
        state["chart_type"] = "none"
    return state


def synthesizer_node(state: AnalyticsState) -> AnalyticsState:
    if state["question_type"] == "simple_lookup":
        context = f"Data: {state['result_df']}\nAnomaly: {state['anomaly_description']}"
    else:
        context = (
            f"Dominant cause: {state['dominant_cause']}\n"
            f"Confidence: {state['confidence']}\n"
            f"Ruled out: {state['ruled_out']}\n"
            f"Supporting data: {state['result_df'][:5]}"
        )
    state["final_answer"] = call_mini_text(
        SYNTHESIZER_PROMPT,
        f"Question: {state['message']}\n{context}"
    )
    return state


def followup_node(state: AnalyticsState) -> AnalyticsState:
    """Generate 3 follow-up question suggestions."""
    try:
        followups = call_followup(state["message"], state["final_answer"])
        state["suggested_followups"] = [q for q in followups if q and isinstance(q, str)]
    except Exception as e:
        logger.warning(f"Followup generation failed: {e}")
        state["suggested_followups"] = []
    return state


def report_node(state: AnalyticsState) -> AnalyticsState:
    """Build a downloadable markdown report from the full result."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# SQL Analytics Report",
        f"**Generated:** {now}  ",
        f"**Question:** {state['message']}",
        f"**Query Type:** {state['question_type']}",
        "",
        "## Answer",
        state["final_answer"],
        "",
    ]
    if state.get("anomaly_found"):
        lines += ["## ⚠️ Anomaly Detected", state["anomaly_description"], ""]
    if state["question_type"] == "investigative" and state.get("dominant_cause"):
        lines += [
            "## Root Cause Analysis",
            f"**Dominant Cause:** {state['dominant_cause']}",
            f"**Confidence:** {state['confidence']}",
            "",
            "### Hypotheses Ruled Out",
        ]
        for item in state.get("ruled_out", []):
            lines.append(f"- ~~{item}~~")
        lines.append("")
    if state.get("sql_used"):
        lines += ["## SQL Used", f"```sql\n{state['sql_used']}\n```", ""]
    if state.get("result_df"):
        df = pd.DataFrame(state["result_df"])
        lines += ["## Data", df.to_markdown(index=False), ""]
    if state.get("suggested_followups"):
        lines += ["## Suggested Follow-up Questions"]
        for q in state["suggested_followups"]:
            lines.append(f"- {q}")
    lines += ["", "---", "*Author: Suresh D R | AI Product Developer & Technology Mentor*"]
    state["report_markdown"] = "\n".join(lines)
    return state
