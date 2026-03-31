from src.agent1.detector import DetectorAgent
from src.agent2.generator import GeneratorAgent
from src.contracts.schemas import ProcessResponse


class PrivacyPipeline:
    def __init__(self) -> None:
        self._detector = DetectorAgent()
        self._generator = GeneratorAgent()

    def run(self, text: str, locale: str) -> ProcessResponse:
        agent1 = self._detector.detect(text)
        agent2 = self._generator.generate(text, agent1)
        return ProcessResponse(
            original_text=text,
            locale=locale,
            agent1=agent1,
            agent2=agent2,
        )
