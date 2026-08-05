# tests/test_pipeline_routing.py
# Author: Suresh D R | AI Product Developer & Technology Mentor

from src.agents.pipeline import _route_after_classifier, _route_after_guardrails


def test_route_blocked_when_guardrail_flags():
    assert _route_after_guardrails({"guardrail_blocked": True}) == "blocked"


def test_route_continue_when_guardrail_clears():
    assert _route_after_guardrails({"guardrail_blocked": False}) == "continue"


def test_route_to_simple_lookup():
    assert _route_after_classifier({"question_type": "simple_lookup"}) == "simple_lookup"


def test_route_to_investigative():
    assert _route_after_classifier({"question_type": "investigative"}) == "investigative"
