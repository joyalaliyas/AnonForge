from typing import Dict

from src.contracts.schemas import EntityType


_FAKE_VALUES = {
    EntityType.PERSON: ["Arjun", "Maya", "Nikhil", "Sara", "Dev"],
    EntityType.LOCATION: ["Bangalore", "Pune", "Hyderabad", "City X"],
    EntityType.COMPANY: ["Company Y", "TechNova", "Vertex Labs", "Apex Systems"],
}


class ConsistencyManager:
    def __init__(self) -> None:
        self._map: Dict[str, str] = {}

    def resolve(self, label: EntityType, source_text: str) -> str:
        key = f"{label.value}:{source_text.lower()}"
        if key in self._map:
            return self._map[key]

        synthetic = self._generate(label, source_text)
        self._map[key] = synthetic
        return synthetic

    @staticmethod
    def _fallback(label: EntityType, index: int) -> str:
        if label == EntityType.PERSON:
            return f"Person {index}"
        if label == EntityType.LOCATION:
            return f"City {index}"
        if label == EntityType.COMPANY:
            return f"Company {index}"
        return f"{label.value.upper()}_{index}"

    def _generate(self, label: EntityType, source_text: str) -> str:
        options = _FAKE_VALUES.get(label)
        if options:
            idx = abs(hash(source_text.lower())) % len(options)
            return options[idx]
        idx = len(self._map) + 1
        return self._fallback(label, idx)
