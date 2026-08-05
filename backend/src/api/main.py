
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import ask, health
from src.utils.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sql_agent.main")

# LangSmith tracing -- if enabled, every LLM call made through LangChain's
# interface (which OpenAI's client is wrapped by indirectly via LangGraph's
# own usage elsewhere) gets traced automatically. Set as env vars so the
# LangChain callback system picks them up with zero code changes.
if settings.LANGCHAIN_TRACING_V2:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

app = FastAPI(title="SQL Analytics Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ask.router, prefix="/api")
