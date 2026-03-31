import json
import os
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

from src.agent1.context_classifier import LLMProcessingError, classify_context
from src.agent1.highlighter import highlight_text
from src.contracts.schemas import Agent1Output, DetectedEntity, EntityType


load_dotenv()


_ALLOWED_ENTITY_LABELS = [label.value for label in EntityType]


class DetectorAgent:
    def detect(self, text: str) -> Agent1Output:
        entities = self._llm_entities(text)
        deduped = self._dedupe_entities(entities)
        context = classify_context(text)
        return Agent1Output(
            entities=deduped,
            context=context,
            highlighted_text=highlight_text(text, deduped),
        )

    def _llm_entities(self, text: str) -> List[DetectedEntity]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMProcessingError("OPENAI_API_KEY is missing. Configure it in .env.")

        model = os.getenv("OPENAI_ENTITY_MODEL", os.getenv("OPENAI_CONTEXT_MODEL", "gpt-4o-mini"))
        client = OpenAI(api_key=api_key)
        prompt = (
            "Extract sensitive entities from the input text. "
            f"Allowed labels: {_ALLOWED_ENTITY_LABELS}. "
            "Return strict JSON only as: {\"entities\": [{\"text\": \"...\", \"label\": \"...\", \"confidence\": 0.0-1.0}]}. "
            "Do not include entities not present in text.\n\n"
            f"Text:\n{text}"
        )

        try:
            response = client.responses.create(model=model, input=prompt, temperature=0)
            raw = (response.output_text or "").strip()
            payload = self._parse_json(raw)
        except Exception as exc:
            raise LLMProcessingError(f"OpenAI entity detection failed: {exc}") from exc

        entities = payload.get("entities", [])
        if not isinstance(entities, list):
            raise LLMProcessingError("Entity detection response did not contain an entities list.")

        resolved: List[DetectedEntity] = []
        used_spans: set[tuple[int, int]] = set()
        for idx, item in enumerate(entities):
            if not isinstance(item, dict):
                continue
            value = str(item.get("text", "")).strip()
            label_raw = str(item.get("label", "")).strip().lower()
            if not value or label_raw not in _ALLOWED_ENTITY_LABELS:
                continue
            span = self._find_span(text, value, used_spans)
            if span is None:
                continue

            start, end = span
            used_spans.add(span)
            confidence = float(item.get("confidence", 0.8))
            confidence = max(0.0, min(1.0, confidence))
            resolved.append(
                DetectedEntity(
                    id=f"{label_raw}-{idx}",
                    label=EntityType(label_raw),
                    text=text[start:end],
                    start=start,
                    end=end,
                    confidence=confidence,
                )
            )
        return resolved

    @staticmethod
    def _parse_json(raw: str) -> dict:
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

    @staticmethod
    def _find_span(text: str, value: str, used_spans: set[tuple[int, int]]) -> tuple[int, int] | None:
        text_lower = text.lower()
        value_lower = value.lower()
        start = 0
        while True:
            idx = text_lower.find(value_lower, start)
            if idx == -1:
                return None
            span = (idx, idx + len(value))
            if span not in used_spans:
                return span
            start = idx + 1

    @staticmethod
    def _entity_from_match(entity_id: str, label: EntityType, value: str, start: int, end: int, confidence: float) -> DetectedEntity:
        return DetectedEntity(id=entity_id, label=label, text=value, start=start, end=end, confidence=confidence)

    @staticmethod
    def _dedupe_entities(entities: List[DetectedEntity]) -> List[DetectedEntity]:
        by_span = {}
        for entity in entities:
            key = (entity.start, entity.end)
            if key not in by_span or entity.confidence > by_span[key].confidence:
                by_span[key] = entity
        return sorted(by_span.values(), key=lambda item: item.start)
