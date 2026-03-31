import src.agent1.detector as detector_module
from src.agent1.detector import DetectorAgent
from src.agent2.generator import GeneratorAgent
from src.contracts.schemas import DetectedEntity, EntityType


def test_generator_replaces_detected_entities(monkeypatch) -> None:
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
    monkeypatch.setattr(
        GeneratorAgent,
        "_llm_replacements",
        lambda self, _text, _agent1: {
            "person-0": "Arjun",
            "location-0": "Bangalore",
            "company-0": "TechNova",
        },
    )
    detector = DetectorAgent()
    generator = GeneratorAgent()

    agent1 = detector.detect(text)
    output = generator.generate(text, agent1)

    assert "Rahul" not in output.transformed_text
    assert "Kochi" not in output.transformed_text
    assert "Infosys" not in output.transformed_text
    assert len(output.replacements) >= 3
