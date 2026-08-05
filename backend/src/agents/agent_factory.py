import json
import os
from functools import lru_cache

from openai import AzureOpenAI

from src.utils.config import get_settings

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


@lru_cache
def get_azure_client() -> AzureOpenAI:
    """Create one reusable Azure OpenAI client."""
    settings = get_settings()

    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


client = get_azure_client()

def load_prompt(name: str) -> str:
    """Load a prompt file from src/prompts."""
    with open(
        os.path.join(_PROMPTS_DIR, f"{name}.txt"),
        encoding="utf-8",
    ) as file:
        return file.read()


# Prompt files
GUARDRAILS_PROMPT = load_prompt("guardrails")
CLASSIFIER_PROMPT = load_prompt("classifier")
HYPOTHESIS_PROMPT = load_prompt("hypothesis_generator")
RANKER_PROMPT = load_prompt("significance_ranker")
ANOMALY_PROMPT = load_prompt("anomaly_scanner")
SYNTHESIZER_PROMPT = load_prompt("business_synthesizer")
FOLLOWUP_PROMPT = load_prompt("followup_generator")


def call_mini_json(system_prompt: str, user_content: str) -> dict:
    """gpt-4o-mini — JSON response. Guardrails, Classifier, Anomaly Scanner."""
    resp = client.chat.completions.create(
        model="gpt-5.4-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)


def call_full_json(system_prompt: str, user_content: str) -> dict:
    """gpt-4o — JSON response. Hypothesis Generator, Significance Ranker."""
    resp = client.chat.completions.create(
        model="gpt-5.4-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)


def call_mini_text(system_prompt: str, user_content: str) -> str:
    """gpt-4o-mini — free text. Business Synthesizer."""
    resp = client.chat.completions.create(
        model="gpt-5.4-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content


def call_followup(question: str, answer: str) -> list:
    """Generate 3 follow-up question suggestions."""
    try:
        result = call_mini_json(
            FOLLOWUP_PROMPT,
            f"Question: {question}\nAnswer: {answer}"
        )
        return result.get("followup_questions", [])
    except Exception:
        return []
