import json
import os
from typing import List

from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()


_ALLOWED_CONTEXTS = [
    "employee_stress_situation",
    "support_ticket",
    "health_related_note",
    "general_business_statement",
]


class LLMProcessingError(RuntimeError):
    pass


class ContextClassificationError(LLMProcessingError):
    pass


def _parse_json_payload(raw: str) -> dict:
    candidate = raw.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()
    return json.loads(candidate)


def _llm_context(text: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ContextClassificationError("OPENAI_API_KEY is missing. Configure it in .env.")

    model = os.getenv("OPENAI_CONTEXT_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    prompt = f"""**Persona:** Act as a highly accurate text classification expert.

**Context:** You are part of a system designed to categorize user-submitted text for [Specify the overall purpose of the classification system - e.g., content moderation, topic routing, sentiment analysis]. Accurate classification is critical for [Explain why accurate classification is important - e.g., ensuring appropriate content filtering, delivering relevant information].

**Task:** Classify the provided text into *exactly one* of the predefined context labels.  If the text does not clearly fit any of the allowed labels, select the *most relevant* label and briefly explain your reasoning in a separate "reasoning" field within the JSON output.

**Input Data:**
*   **Allowed Labels:** {_ALLOWED_CONTEXTS} (This will be dynamically populated with a list of valid context labels).
*   **Text to Classify:** {text} (This will be dynamically populated with the text to be classified).

**Output Format & Constraints:**
*   Return a strict JSON object with the following keys: "context" and "reasoning".
*   The "context" field should contain *only* one of the allowed labels from {_ALLOWED_CONTEXTS}.
*   The "reasoning" field should be a brief (1-2 sentence) explanation of why that label was chosen, *especially* if the classification was ambiguous. If the classification was straightforward, the reasoning can be omitted.
*   Ensure the JSON is valid and well-formatted.

**Goal:** To accurately categorize the input text based on its content, even in cases of ambiguity, providing a justification for the chosen label.
"""

    try:
        response = client.responses.create(model=model, input=prompt, temperature=0)
    except Exception as exc:
        raise ContextClassificationError(f"OpenAI request failed: {exc}") from exc

    raw = (response.output_text or "").strip()
    if not raw:
        raise ContextClassificationError("OpenAI returned an empty response.")

    try:
        parsed = _parse_json_payload(raw)
    except Exception as exc:
        raise ContextClassificationError(f"Model response was not valid JSON: {raw[:180]}") from exc

    label = parsed.get("context")
    if label in _ALLOWED_CONTEXTS:
        return label
    raise ContextClassificationError(
        f"Model returned invalid context label: {label}. Allowed labels: {_ALLOWED_CONTEXTS}"
    )


def classify_context(text: str) -> str:
    return _llm_context(text)
