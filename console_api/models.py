"""Explicit presentation DTOs; evidence details are serialized core reports."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

State = Literal['PASS','FAIL','NOT_EVALUATED','NOT_APPLICABLE','BLOCKED']
class DTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Source(DTO):
    id: str
    title: str
    capability: str
    database: str | None = None
    snapshots: list[str] = Field(default_factory=list)

class Artifact(DTO):
    id: str
    title: str
    sha256: str
    category: str
    historical: bool

class Evidence(DTO):
    id: str
    label: str
    status: State
    details: dict = Field(default_factory=dict)
    artifact_id: str | None = None

class Block(DTO):
    id: str
    text: str
    details: dict = Field(default_factory=dict)
    visibility: Literal['student'] = 'student'

class Role(DTO):
    id: str
    slot: str
    semantic_role: str
    title: str
    purpose: str
    source_type: str
    source_refs: list[str]
    validation: State
    ai_capability: str
    blocks: list[Block]

class Question(DTO):
    id: str
    role: str
    text: str
    inputs: dict
    solution_id: str | None
    visibility: Literal['student'] = 'student'

class Solution(DTO):
    id: str
    item_ref: str
    role: str
    steps: list[str]
    answer: str
    visibility: Literal['teacher-only'] = 'teacher-only'
    details: dict

class Lesson(DTO):
    profile: Literal['standard-lesson'] = 'standard-lesson'
    roles: list[Role]
    limitations: list[str]

class RunRequest(DTO):
    source: Literal['standard-deviation'] = 'standard-deviation'
    topic: Literal['standard-deviation'] = 'standard-deviation'
    profile: Literal['standard-lesson'] = 'standard-lesson'

class Run(DTO):
    id: str
    operation: Literal['assemble-standard-lesson'] = 'assemble-standard-lesson'
    selection: RunRequest
    database: str
    snapshots: list[str]
    started_at: str
    ended_at: str | None = None
    status: Literal['queued','running','succeeded','failed','blocked']
    stages: list[Evidence] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)

class Objective(DTO):
    code: str
    official_text: str
    source_id: str
    mappings: list[dict]

class Subtopic(DTO):
    code: str
    name: str
    notes: list[str]
    objectives: list[Objective]

class Curriculum(DTO):
    topic_code: str
    topic_name: str
    tier_source: str
    subtopics: list[Subtopic]
    warnings: list[str]
    structure: Evidence
    mapped: int
    total: int
    artifact_id: str

class Historical(DTO):
    id: str
    label: Literal['HISTORICAL EVIDENCE'] = 'HISTORICAL EVIDENCE'
    milestone: str
    role: str
    mode: str
    model: str
    accepted: bool
    evidence: list[Evidence]
    limitations: list[str]

class Health(DTO):
    status: str = 'ok'
    database: str
    model_calls_enabled: Literal[False] = False
    model_call_policy: str = 'No automatic or lesson model calls; syllabus live parsing requires a separate confirmed action.'
    trusted_state_writes: Literal[False] = False

class Topic(DTO):
    source: Source
    trust: dict
    provenance: dict
