from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from academic_os.curriculum_ingestion.models import SelectedCurriculumTarget, Warning


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


ProvenanceClass = Literal['SOURCE_DERIVED', 'CANONICAL_DERIVED', 'DETERMINISTIC_TRANSFORMATION',
                          'MODEL_PROPOSED', 'HUMAN_REVIEWED', 'TRUSTED_SNAPSHOT']
EligibilityStatus = Literal['ELIGIBLE', 'ELIGIBLE_WITH_WARNINGS', 'REVIEW_REQUIRED', 'BLOCKED', 'UNSUPPORTED']


class Provenance(Model):
    classifications: list[ProvenanceClass] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    rule: str


class ObjectiveEligibility(Model):
    source_id: str
    status: EligibilityStatus
    reason_codes: list[str]
    missing_requirements: list[str]
    canonical_id: str | None
    decision_ids: list[str]


class LearningSpecificationEligibility(Model):
    schema_version: Literal['learning-spec-eligibility/1'] = 'learning-spec-eligibility/1'
    policy_version: str
    policy_sha256: str
    construction_scope: Literal['BOUNDED_REVIEWABLE_LEARNING_INTENTIONS_ONLY'] = 'BOUNDED_REVIEWABLE_LEARNING_INTENTIONS_ONLY'
    source_package_hash: str
    selected_target_id: str | None
    binding_valid: bool
    status: EligibilityStatus
    reason_codes: list[str]
    missing_requirements: list[str]
    warnings: list[Warning]
    evidence_refs: dict[str, str]
    selected_source_ids: list[str]
    objective_results: list[ObjectiveEligibility]
    independently_ready_source_ids: list[str]
    unresolved_source_ids: list[str]
    excluded_source_ids: list[str]
    publication_eligible: Literal[False] = False
    pedagogy_eligible: Literal[False] = False


class SourceObjective(Model):
    source_id: str
    official_text: str
    tier: str
    topic_code: str
    subtopic_code: str
    objective_code: str
    subtopic_notes: list[str]
    provenance: Provenance


class CanonicalSemantic(Model):
    source_id: str
    canonical_id: str
    description: str
    relationship: Literal['equivalent'] = 'equivalent'
    decision_ids: list[str] = Field(min_length=1)
    provenance: Provenance


class LearningIntention(Model):
    intention_id: str
    source_id: str
    canonical_id: str
    kind: Literal['capability'] = 'capability'
    statement: str
    provenance: Provenance


class TaskCapability(Model):
    source_id: str
    canonical_id: str
    action_meaning: str
    task_forms: list[str]
    task_form_state: Literal['TASK_FORM_EVIDENCE_UNAVAILABLE'] = 'TASK_FORM_EVIDENCE_UNAVAILABLE'
    provenance: Provenance


class UnavailableElement(Model):
    status: Literal['MISSING', 'REVIEW_REQUIRED', 'MODEL_AUTHORING_REQUIRED']
    reason_code: str
    claims: list[str]
    blocks_learning_intention_construction: Literal[False] = False
    provenance: Provenance


class GovernanceState(Model):
    state: Literal['QUALIFIED_REVIEWABLE_EVIDENCE'] = 'QUALIFIED_REVIEWABLE_EVIDENCE'
    review_basis: Literal['PINNED_HISTORICAL_HUMAN_CANONICAL_DECISIONS'] = 'PINNED_HISTORICAL_HUMAN_CANONICAL_DECISIONS'
    uploaded_source_human_approved: Literal[False] = False
    official_text_confirmed: Literal[False] = False
    spec_human_approved: Literal[False] = False
    trusted_snapshot_backed: Literal[False] = False
    published: Literal[False] = False
    pedagogy_eligible: Literal[False] = False
    model_calls: Literal[0] = 0


class GovernedLearningSpecification(Model):
    schema_version: Literal['governed-learning-specification/1'] = 'governed-learning-specification/1'
    construction_version: Literal['governed-learning-construction/1'] = 'governed-learning-construction/1'
    identity: str
    source_package_hash: str
    eligibility_hash: str
    policy_version: str
    policy_sha256: str
    curriculum_scope: SelectedCurriculumTarget
    learning_objectives: list[SourceObjective]
    canonical_semantics: list[CanonicalSemantic]
    learning_intentions: list[LearningIntention]
    task_capabilities: list[TaskCapability]
    success_criteria: UnavailableElement
    prerequisites: UnavailableElement
    known_misconceptions: UnavailableElement
    conceptual_knowledge: UnavailableElement
    concept_skill_task_relations: UnavailableElement
    assessment_evidence: UnavailableElement
    warnings: list[Warning]
    evidence: dict[str, str]
    governance_state: GovernanceState


class SpecValidation(Model):
    schema_version: Literal['governed-learning-validation/1'] = 'governed-learning-validation/1'
    valid: bool
    status: Literal['PASS_WITH_WARNINGS', 'FAIL']
    errors: list[str]
    semantic_sha256: str
    source_package_hash: str
    policy_version: str
    model_calls: Literal[0] = 0


class SpecReceipt(Model):
    spec_id: str
    semantic_sha256: str
    source_package_hash: str
    selected_target_id: str
    created_at: str
    artifacts: dict[str, str]
