from typing import List

from src.contracts.schemas import DetectedEntity


def highlight_text(text: str, entities: List[DetectedEntity]) -> str:
    highlighted = text
    # Replace from right-to-left so indexes remain valid while editing the string.
    for entity in sorted(entities, key=lambda item: item.start, reverse=True):
        token = f"[{entity.label.value.upper()}]"
        highlighted = highlighted[: entity.start] + token + highlighted[entity.end :]
    return highlighted
