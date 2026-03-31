from typing import List

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.agent1.context_classifier import LLMProcessingError
from src.agent2.validators import OutputValidator
from src.contracts.schemas import Agent1Output, Agent2Output, Replacement


load_dotenv()


class GeneratorAgent:
    def __init__(self) -> None:
        self._validator = OutputValidator()

    def generate(self, text: str, agent1_output: Agent1Output) -> Agent2Output:
        replacements_map = self._llm_replacements(text, agent1_output)
        replacements: List[Replacement] = []
        transformed = text

        for entity in sorted(agent1_output.entities, key=lambda item: item.start, reverse=True):
            synthetic_value = replacements_map.get(entity.id)
            if not synthetic_value:
                raise LLMProcessingError(f"Missing LLM replacement for entity id {entity.id}.")
            replacements.append(
                Replacement(
                    entity_id=entity.id,
                    label=entity.label,
                    original=entity.text,
                    synthetic=synthetic_value,
                )
            )
            transformed = transformed[: entity.start] + synthetic_value + transformed[entity.end :]

        # Keep replacement list in original reading order.
        replacements.reverse()
        output = Agent2Output(replacements=replacements, transformed_text=transformed, used_fallback=False)

        if self._validator.validate(output, agent1_output.entities):
            return output
        raise LLMProcessingError("LLM replacements failed validation checks.")

    def _llm_replacements(self, text: str, agent1_output: Agent1Output) -> dict[str, str]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMProcessingError("OPENAI_API_KEY is missing. Configure it in .env.")

        model = os.getenv("OPENAI_GENERATION_MODEL", os.getenv("OPENAI_CONTEXT_MODEL", "gpt-4o-mini"))
        client = OpenAI(api_key=api_key)

        entities_for_prompt = [
            {
                "entity_id": entity.id,
                "label": entity.label.value,
                "text": entity.text,
            }
            for entity in agent1_output.entities
        ]

        prompt = (
            "Generate safe synthetic replacements for sensitive entities while preserving sentence meaning and tone. "
            "Return strict JSON only as: {\"replacements\": [{\"entity_id\": \"...\", \"synthetic\": \"...\"}]}. "
            "Preserve consistency for repeated entities and avoid reusing original values.\n\n"
            f"Context label: {agent1_output.context}\n"
            f"Original text: {text}\n"
            f"Entities: {json.dumps(entities_for_prompt, ensure_ascii=True)}"
        )

        try:
            response = client.responses.create(model=model, input=prompt, temperature=0)
            raw = (response.output_text or "").strip()
            payload = self._parse_json(raw)
        except Exception as exc:
            raise LLMProcessingError(f"OpenAI replacement generation failed: {exc}") from exc

        replacements = payload.get("replacements", [])
        if not isinstance(replacements, list):
            raise LLMProcessingError("Replacement response did not contain a replacements list.")

        replacement_map: dict[str, str] = {}
        for row in replacements:
            if not isinstance(row, dict):
                continue
            entity_id = str(row.get("entity_id", "")).strip()
            synthetic = str(row.get("synthetic", "")).strip()
            if entity_id and synthetic:
                replacement_map[entity_id] = synthetic

        return replacement_map

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
