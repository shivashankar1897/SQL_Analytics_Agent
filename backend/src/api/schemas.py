
from typing import Optional, List
from pydantic import BaseModel


class AskRequest(BaseModel):
    message: str
    session_id: str
    conversation_history: List[dict] = []   # buffer memory from frontend


class AskResponse(BaseModel):
    question_type: Optional[str] = None
    blocked: bool = False
    block_reason: str = ""
    sql_used: str = ""
    answer: str = ""
    confidence: str = ""
    dominant_cause: str = ""
    ruled_out: List[str] = []
    anomaly_found: bool = False
    anomaly_description: str = ""
    chart_type: str = ""
    chart_json: str = ""
    suggested_followups: List[str] = []
    report_markdown: str = ""
    elapsed_seconds: float = 0.0
    from_cache: bool = False
