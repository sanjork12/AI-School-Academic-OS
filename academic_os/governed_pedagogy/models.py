from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from academic_os.curriculum_ingestion.models import Warning, SelectedCurriculumTarget
from academic_os.governed_learning.models import GovernedLearningSpecification


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


Status = Literal['ELIGIBLE', 'ELIGIBLE_WITH_WARNINGS', 'REVIEW_REQUIRED', 'BLOCKED', 'UNSUPPORTED']


class Provenance(Model):
    classifications: list[Literal['LEARNING_SPEC_DERIVED', 'CANONICAL_DERIVED', 'DETERMINISTIC_POLICY',
                                 'HUMAN_REVIEWED', 'MODEL_PROPOSED', 'TRUSTED_REFERENCE', 'APPROVED_PEDAGOGICAL_EVIDENCE']] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    learning_intention_ids: list[str]
    source_ids: list[str]
    rule: str


class InputRequirement(Model):
    key: str
    status: Literal['AVAILABLE', 'MISSING', 'OPTIONAL_UNAVAILABLE', 'REVIEW_REQUIRED', 'AUTHORING_REQUIRED', 'UNSUPPORTED']
    required: bool
    reason_code: str
    provenance: Provenance


class RoleRequirement(Model):
    role_key: str
    family: str
    requirement: Literal['required', 'optional', 'unsupported']
    enabled_for_authoring: Literal[False] = False
    reason_code: str
    legacy_role_ids: list[str]
    provenance: Provenance


class RoleContract(Model):
    schema_version: Literal['governed-pedagogical-role-contract/1'] = 'governed-pedagogical-role-contract/1'
    purpose: Literal['NON_EXECUTABLE_PLANNING_CONSTRAINTS'] = 'NON_EXECUTABLE_PLANNING_CONSTRAINTS'
    required_roles: list[str]
    optional_roles: list[str]
    unsupported_roles: list[str]
    roles: list[RoleRequirement]
    legacy_role_compatibility: dict[str, str]
    mandatory_sequence: list[str]
    profile_selected: Literal[False] = False


class ActionBinding(Model):
    source_id: str
    canonical_id: str
    action_meaning: str
    semantic_role: Literal['REVIEWED_CAPABILITY_MEANING_NOT_A_TASK_GRAPH'] = 'REVIEWED_CAPABILITY_MEANING_NOT_A_TASK_GRAPH'
    provenance: Provenance


class PedagogicalSpecificationEligibility(Model):
    schema_version: Literal['pedagogical-spec-eligibility/1'] = 'pedagogical-spec-eligibility/1'
    policy_version: str
    policy_sha256: str
    learning_spec_hash: str
    selected_target_id: str | None
    status: Status
    reason_codes: list[str]
    missing_requirements: list[str]
    requirements: list[InputRequirement]
    warnings: list[Warning]
    evidence_refs: dict[str, str]
    actions: list[ActionBinding]
    role_contract: RoleContract | None
    binding_valid: bool


class LessonAuthoringEligibility(Model):
    schema_version: Literal['lesson-authoring-eligibility/1'] = 'lesson-authoring-eligibility/1'
    status: Status
    reason_codes: list[str]
    missing_requirements: list[str]
    warnings: list[Warning]
    evidence_refs: dict[str, str]
    learning_spec_hash: str
    pedagogical_spec_hash: str | None
    policy_version: str
    model_calls: Literal[0] = 0


class Governance(Model):
    state: Literal['QUALIFICATION_EVIDENCE_ONLY'] = 'QUALIFICATION_EVIDENCE_ONLY'
    approved: Literal[False] = False
    published: Literal[False] = False
    trusted_state_changed: Literal[False] = False
    model_calls: Literal[0] = 0


class PhaseContract(Model):
    phase_key: str
    role_refs: list[str]
    learning_intention_ids: list[str]
    provenance: Provenance


from .consumer import ConsumedEvidence


class GovernedPedagogicalSpecification(Model):
    schema_version: Literal['governed-pedagogical-specification/1'] = 'governed-pedagogical-specification/1'
    construction_version: Literal['governed-pedagogical-construction/1', 'governed-approved-pedagogical-construction/1'] = 'governed-pedagogical-construction/1'
    learning_spec_hash: str
    source_learning_spec: GovernedLearningSpecification
    eligibility: PedagogicalSpecificationEligibility
    policy_version: str
    learning_scope: SelectedCurriculumTarget
    instructional_goal_refs: list[str]
    teaching_phases: list[PhaseContract]
    role_contract: RoleContract
    activity_constraints: list[InputRequirement]
    warnings: list[Warning]
    governance_state: Governance
    approved_evidence: ConsumedEvidence | None = None


class Validation(Model):
    validated_schema: str
    valid: bool
    status: Literal['PASS_WITH_WARNINGS', 'FAIL']
    errors: list[str]
    semantic_sha256: str
    policy_version: str


class Qualification(Model):
    schema_version: Literal['pedagogical-qualification/1'] = 'pedagogical-qualification/1'
    source_learning_spec: GovernedLearningSpecification
    eligibility: PedagogicalSpecificationEligibility
    lesson_authoring_eligibility: LessonAuthoringEligibility
    governance_state: Governance
