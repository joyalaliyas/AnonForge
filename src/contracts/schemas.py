from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    PERSON = "person"
    LOCATION = "location"
    COMPANY = "company"
    EMAIL = "email"
    PHONE = "phone"
    ID = "id"
    OTHER = "other"


class ProcessRequest(BaseModel):
    text: str = Field(min_length=1)
    locale: str = "en-IN"


class DetectedEntity(BaseModel):
    id: str
    label: EntityType
    text: str
    start: int
    end: int
    confidence: float = Field(ge=0.0, le=1.0)


class Agent1Output(BaseModel):
    entities: List[DetectedEntity]
    context: str
    highlighted_text: str


class Replacement(BaseModel):
    entity_id: str
    label: EntityType
    original: str
    synthetic: str


class Agent2Output(BaseModel):
    replacements: List[Replacement]
    transformed_text: str
    used_fallback: bool = False


class ProcessResponse(BaseModel):
    original_text: str
    locale: str
    agent1: Agent1Output
    agent2: Agent2Output
