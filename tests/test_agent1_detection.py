import src.agent1.detector as detector_module
from src.agent1.detector import DetectorAgent
from src.contracts.schemas import DetectedEntity, EntityType


def test_detector_finds_entities_and_context(monkeypatch) -> None:
    text = "Rahul from Kochi works at Infosys and feels stressed."
    monkeypatch.setattr(detector_module, "classify_context", lambda _: "employee_stress_situation")
    monkeypatch.setattr(
        DetectorAgent,
        "_llm_entities",
        lambda self, _: [
            DetectedEntity(id="person-0", label=EntityType.PERSON, text="Rahul", start=0, end=5, confidence=0.95),
            DetectedEntity(id="location-0", label=EntityType.LOCATION, text="Kochi", start=11, end=16, confidence=0.94),
            DetectedEntity(id="company-0", label=EntityType.COMPANY, text="Infosys", start=26, end=33, confidence=0.93),
        ],
    )
    agent = DetectorAgent()

    output = agent.detect(text)

    labels = [entity.label.value for entity in output.entities]
    assert "person" in labels
    assert "location" in labels
    assert "company" in labels
    assert output.context == "employee_stress_situation"
    assert "[PERSON]" in output.highlighted_text
