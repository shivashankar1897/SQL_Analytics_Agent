
import hashlib
import json
import logging
import time

import redis

from src.utils.config import settings

logger = logging.getLogger("sql_agent.cache")

_client = None


def get_redis():
    global _client
    if not settings.CACHE_ENABLED:
        return None
    if _client is None:
        try:
            _client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            _client.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable, caching disabled: {e}")
            _client = False  # sentinel: tried and failed, don't retry every call
    return _client or None


def _question_cache_key(question: str) -> str:
    normalized = question.strip().lower()
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"query:{digest}"


def get_cached_result(question: str):
    r = get_redis()
    if not r:
        return None
    try:
        raw = r.get(_question_cache_key(question))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def set_cached_result(question: str, result: dict):
    r = get_redis()
    if not r:
        return
    try:
        r.setex(_question_cache_key(question), settings.CACHE_TTL_QUERY_SECONDS, json.dumps(result, default=str))
    except Exception:
        pass


def get_cached_schema():
    r = get_redis()
    if not r:
        return None
    try:
        return r.get("schema:context")
    except Exception:
        return None


def set_cached_schema(schema_text: str):
    r = get_redis()
    if not r:
        return
    try:
        r.setex("schema:context", settings.CACHE_TTL_SCHEMA_SECONDS, schema_text)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Circuit breaker for the expensive investigative path
# ---------------------------------------------------------------------------

def check_investigative_circuit_breaker(session_id: str) -> bool:
    """Returns True if the session is ALLOWED to use the investigative path,
    False if it has exceeded the call limit and should be blocked.
    Fails open (returns True) if Redis is unreachable."""
    r = get_redis()
    if not r:
        return True
    try:
        key = f"investigative_calls:{session_id}"
        count = r.incr(key)
        if count == 1:
            r.expire(key, settings.INVESTIGATIVE_CALL_WINDOW_SECONDS)
        return count <= settings.INVESTIGATIVE_CALL_LIMIT_PER_SESSION
    except Exception:
        return True


def check_rate_limit(session_id: str) -> bool:
    """General per-session rate limit, independent of question type.
    Fails open if Redis is unreachable."""
    r = get_redis()
    if not r:
        return True
    try:
        key = f"rate_limit:{session_id}:{int(time.time() // 60)}"
        count = r.incr(key)
        if count == 1:
            r.expire(key, 60)
        return count <= settings.RATE_LIMIT_PER_MINUTE
    except Exception:
        return True
