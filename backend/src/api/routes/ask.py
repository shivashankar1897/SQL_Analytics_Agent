
from fastapi import APIRouter, HTTPException
from src.agents.pipeline import run_pipeline
from src.api.schemas import AskRequest, AskResponse

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        result = run_pipeline(
            message=req.message,
            session_id=req.session_id,
            conversation_history=req.conversation_history,
        )
        return result
    except Exception as e:
        import traceback
        import logging
        logging.getLogger("sql_agent.api").error(f"Pipeline error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")
