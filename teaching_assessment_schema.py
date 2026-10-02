"""Isolated teaching demo schema; no change to stable v0.1/v0.2 models."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1)]
Topic = Literal['data_types','location','spread','comparison','lds']

class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Competency(Model):
    competency_id: Text
    skill_name: Text
    topic_group: Topic
    classification: Literal['candidate_canonical','teaching_only_grouping']
    review_status: Literal['pending']
    provenance: Literal['teacher_generated']

class Scope(Model):
    competency_id: Text
    context_id: Literal['CTX-EDX-9MA0-2017-STAT']
    expectations: Text
    status: Literal['teacher_selected_scope_pending_review']

class Context(Model):
    context_id: Literal['CTX-EDX-9MA0-2017-STAT']
    exam_board: Literal['Pearson Edexcel']
    qualification: Literal['A Level Mathematics']
    qualification_code: Literal['9MA0']
    curriculum_version: Literal['2017 qualification']
    educational_stage: Literal['UK Level 3 / A Level']
    component: Literal['Statistics / Applied Mathematics']
    unit: Literal['Statistics: Exploring and Summarising Data']
    material_notice: Text
    facts: list[dict]
    sources: list[dict]
    source_limitations: Text
    numerical_data_origin: Literal['synthetic_illustrative']

class Part(Model):
    part_id: Text
    marks: Annotated[int, Field(ge=1,le=10)]
    primary_competency: Text
    supporting_competencies: list[Text]
    prompt: Text
    predicted_difficulty: Annotated[int, Field(ge=1,le=5)]
    difficulty_basis: Text
    reasoning_steps: list[Text] = Field(min_length=1)
    answer: Text
    marking_points: list[Text] = Field(min_length=1)
    acceptable_alternatives: Text
    interpretation_requirements: Text

class Question(Model):
    question_id: Text
    title: Text
    context: Text
    question_purpose: Text
    question_format: Text
    provenance: Literal['teacher_generated']
    data_provenance: Literal['synthetic_illustrative']
    notice: Text
    data_notice: Text
    data: list[list[str]]
    parts: list[Part] = Field(min_length=1)

class Practice(Model):
    practice_id: Text
    prompt: Text
    answer: Text

class Slide(Model):
    slide_id: Annotated[int, Field(ge=1)]
    title: Text
    competency_ids: list[Text]
    body: list[Text]
    student_check: Practice
    worked_example_id: str | None
    table: list[list[str]]
    chart: dict | None
    speaker_notes: str
    provenance: Literal['teacher_generated']
    data_notice: Text

class TeachingSection(Model):
    lesson_section: Text
    slide_ids: list[int]
    learning_objectives: list[Text]
    canonical_competencies: list[Text]
    key_concepts: list[Text]
    worked_examples: list[Text]
    student_checks: list[Text]
    common_mistakes: list[Text]
    exam_focus: Text

class CorePack(Model):
    schema_version: Literal['teaching_demo_0.1']
    context: Context
    competencies: list[Competency]
    scopes: list[Scope]
    slides: list[Slide]
    sections: list[TeachingSection]
    questions: list[Question]
    total_marks: Literal[48]
    duration_minutes: Literal[55]
    material_notice: Text
    mark_scheme_notice: Text
    human_review_status: Literal['pending']
