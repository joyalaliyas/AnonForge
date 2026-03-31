import re
from typing import List

from src.contracts.schemas import Agent2Output, DetectedEntity


_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){10}\b")


class OutputValidator:
    def validate(self, output: Agent2Output, original_entities: List[DetectedEntity]) -> bool:
        text = output.transformed_text
        if _EMAIL_RE.search(text) or _PHONE_RE.search(text):
            return False

        for entity in original_entities:
            if len(entity.text) < 3:
                continue
            if entity.text.lower() in text.lower():
                return False

        return True
