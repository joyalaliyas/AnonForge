from fastapi.testclient import TestClient

import src.agent1.detector as detector_module
from src.agent1.context_classifier import ContextClassificationError
from src.agent1.detector import DetectorAgent
from src.agent2.generator import GeneratorAgent
from src.api.main import app
from src.contracts.schemas import Agent2Output, DetectedEntity, EntityType, Replacement


client = TestClient(app)


def test_root_serves_web_ui() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "SafeText Studio" in response.text


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_process_endpoint(monkeypatch) -> None:
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
    payload = {
        "text": "Rahul from Kochi works at Infosys and feels stressed.",
        "locale": "en-IN",
    }

    response = client.post("/process", json=payload)
    data = response.json()

    assert response.status_code == 200
    assert data["original_text"] == payload["text"]
    assert "agent1" in data
    assert "agent2" in data
    assert payload["text"] != data["agent2"]["transformed_text"]


def test_process_endpoint_returns_503_on_classification_error(monkeypatch) -> None:
    monkeypatch.setattr(
        DetectorAgent,
        "_llm_entities",
        lambda self, _: [
            DetectedEntity(id="person-0", label=EntityType.PERSON, text="Any", start=0, end=3, confidence=0.95),
        ],
    )
    monkeypatch.setattr(
        detector_module,
        "classify_context",
        lambda _: (_ for _ in ()).throw(ContextClassificationError("simulated classifier failure")),
    )
    payload = {
        "text": "Any text",
        "locale": "en-IN",
    }

    response = client.post("/process", json=payload)
    assert response.status_code == 503
    assert response.json()["detail"] == "simulated classifier failure"


def test_process_csv_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(detector_module, "classify_context", lambda _: "employee_stress_situation")
    monkeypatch.setattr(
        DetectorAgent,
        "_llm_entities",
        lambda self, _: [
            DetectedEntity(id="person-0", label=EntityType.PERSON, text="Rahul", start=0, end=5, confidence=0.95),
        ],
    )
    monkeypatch.setattr(
        GeneratorAgent,
        "_llm_replacements",
        lambda self, _text, _agent1: {
            "person-0": "Arjun",
        },
    )

    csv_content = "text,team\nRahul is stressed,ops\n"
    response = client.post(
        "/process-csv",
        files={"file": ("input.csv", csv_content, "text/csv")},
        data={"text_column": "text", "locale": "en-IN"},
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "synthetic_text" in response.text
    assert "Arjun" in response.text
    assert "text_synthetic" in response.text


def test_process_csv_endpoint_auto_detects_issue_column(monkeypatch) -> None:
    monkeypatch.setattr(detector_module, "classify_context", lambda _: "employee_stress_situation")
    monkeypatch.setattr(
        DetectorAgent,
        "_llm_entities",
        lambda self, _: [
            DetectedEntity(id="person-0", label=EntityType.PERSON, text="Meera", start=0, end=5, confidence=0.95),
            DetectedEntity(id="location-1", label=EntityType.LOCATION, text="Chennai", start=22, end=29, confidence=0.92),
            DetectedEntity(id="company-2", label=EntityType.COMPANY, text="Zoho", start=39, end=43, confidence=0.92),
        ],
    )
    monkeypatch.setattr(
        GeneratorAgent,
        "generate",
        lambda self, text, _agent1: Agent2Output(
            replacements=[
                Replacement(entity_id="person-0", label=EntityType.PERSON, original="Meera", synthetic="Sara"),
                Replacement(entity_id="location-1", label=EntityType.LOCATION, original="Chennai", synthetic="Pune"),
                Replacement(entity_id="company-2", label=EntityType.COMPANY, original="Zoho", synthetic="TechNova"),
            ],
            transformed_text=text.replace("Meera", "Sara").replace("Chennai", "Pune").replace("Zoho", "TechNova"),
            used_fallback=False,
        ),
    )

    csv_content = "id,name,location,company,issue\n1,Meera,Chennai,Zoho,Experiencing emotional exhaustion\n"
    response = client.post(
        "/process-csv",
        files={"file": ("fakedataset.csv", csv_content, "text/csv")},
        data={"text_column": "auto", "locale": "en-IN"},
    )

    assert response.status_code == 200
    assert "synthetic_text" in response.text
    assert "Sara" in response.text
    assert "name_synthetic" in response.text
    assert "location_synthetic" in response.text
    assert "company_synthetic" in response.text
    assert "Sara" in response.text
    assert "Pune" in response.text
    assert "TechNova" in response.text
