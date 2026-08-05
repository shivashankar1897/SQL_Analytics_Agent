from typing import TypedDict


class AnalyticsState(TypedDict):
    # Input
    message: str
    session_id: str
    conversation_history: list   # LangChain buffer memory — last N turns

    # Guardrails
    guardrail_blocked: bool
    block_reason: str

    # Classification
    question_type: str           # "simple_lookup" | "investigative"

    # Simple lookup path
    sql_used: str
    result_df: list              # list of dict records

    # Investigative path
    hypothesis_questions: list
    evidence: dict
    dominant_cause: str
    confidence: str
    ruled_out: list

    # Shared by both paths
    anomaly_found: bool
    anomaly_description: str
    chart_type: str
    chart_json: str
    final_answer: str
    suggested_followups: list    # 3 suggested follow-up questions
    report_markdown: str         # downloadable report
