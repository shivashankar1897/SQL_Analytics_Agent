
from fastapi import APIRouter
from sqlalchemy import text

from src.tools.sql_tools import get_engine
from src.utils.cache import get_redis

router = APIRouter()


@router.get("/health")
def health():
    status = {"status": "ok", "checks": {}}

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"failed: {e}"
        status["status"] = "degraded"

    r = get_redis()
    status["checks"]["redis"] = "ok" if r else "disabled_or_unreachable"

    return status
