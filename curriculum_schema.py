from typing import Literal
from pydantic import BaseModel, Field


class LearningObjective(BaseModel):
    code: str
    official_text: str

    # Generated deterministically after AI extraction.
    # Example: EDX-4MA1-F-2.7-A
    source_id: str | None = None


class Subtopic(BaseModel):
    code: str
    name: str
    objectives: list[LearningObjective] = Field(
        default_factory=list
    )
    notes: list[str] = Field(
        default_factory=list
    )


class CurriculumTopic(BaseModel):
    exam_board: Literal["Pearson Edexcel"]
    qualification: Literal["International GCSE"]
    subject: Literal["Mathematics A"]
    specification_code: Literal["4MA1"]

    tier_source: Literal[
        "Foundation",
        "Higher"
    ]

    topic_code: str
    topic_name: str

    subtopics: list[Subtopic]

    warnings: list[str] = Field(
        default_factory=list
    )