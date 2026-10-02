"""Closed, bounded authoring contracts; none of these models publish academic state."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from academic_os.governed_learning.models import GovernedLearningSpecification

class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, revalidate_instances='always')

Component = Literal['success_criteria', 'activity_scope', 'check_alignment', 'pedagogical_adapter']
Family = Literal['ORIENTATION', 'REPRESENTATION', 'CONCEPT_CHECK', 'SUMMARY']

class Brief(Model):
    schema_version: Literal['pedagogical-evidence-authoring-brief/1'] = 'pedagogical-evidence-authoring-brief/1'
    policy_version: Literal['bounded-symbol-evidence-authoring/1'] = 'bounded-symbol-evidence-authoring/1'
    learning_spec_hash: str
    source_learning_spec: GovernedLearningSpecification
    allowed_categories: list[Component]
    role_evidence_hash: str
    prohibited_claims: list[str]
    authoring_constraints: list[str]
    review_requirements: list[str]

class Basis(Model):
    classification: Literal['PROPOSED'] = 'PROPOSED'
    origin: Literal['SYNTHETIC_OFFLINE', 'HUMAN_AUTHORED', 'MODEL_PROPOSED']
    brief_hash: str
    source_id: str
    intention_id: str

class Criterion(Model):
    criterion_id: str = Field(pattern=r'^SC-[1-9][0-9]*$')
    linked_learning_intention: str
    observable_student_action: Literal['INTERPRET_SYMBOL', 'SELECT_SYMBOL']
    scope: Literal['REVIEWED_INEQUALITY_SYMBOLS_ONLY']
    conditions: Literal['SYMBOL_REPRESENTATION', 'RELATION_REPRESENTATION']
    quality_or_completion_rule: Literal['MEANING_MATCHES_REVIEWED_SYMBOL', 'SYMBOL_MATCHES_STATED_RELATION']
    evidence_basis: Basis

class Activity(Model):
    activity_id: str = Field(pattern=r'^ACT-[1-9][0-9]*$')
    category: Literal['REPRESENTATION', 'CONCEPT_CHECK']
    criterion_ids: list[str] = Field(min_length=1)
    response_mode: Literal['SYMBOL_SELECTION', 'SYMBOL_INTERPRETATION']
    scope: Literal['REVIEWED_INEQUALITY_SYMBOLS_ONLY']
    evidence_basis: Basis

class Check(Model):
    check_id: str = Field(pattern=r'^CHK-[1-9][0-9]*$')
    intention_id: str
    criterion_id: str
    activity_id: str
    evidence_form: Literal['SYMBOL_SELECTION', 'SYMBOL_INTERPRETATION']
    prohibited_shortcut: Literal['NO_COMPLETION_WITHOUT_OBSERVABLE_RESPONSE']
    evidence_basis: Basis

class Adapter(Model):
    schema_version: Literal['pedagogical-adapter/1'] = 'pedagogical-adapter/1'
    canonical_id: str
    action_meaning: str
    criterion_ids: list[str] = Field(min_length=1)
    activity_ids: list[str] = Field(min_length=1)
    check_ids: list[str] = Field(min_length=1)
    candidate_role_families: list[Family] = Field(min_length=1)
    evidence_basis: Basis
    executable: Literal[False] = False

class Proposal(Model):
    schema_version: Literal['pedagogical-evidence-proposal/1'] = 'pedagogical-evidence-proposal/1'
    status: Literal['PROPOSED'] = 'PROPOSED'
    brief: Brief
    source_id: str
    tier: str
    source_wording: str
    success_criteria: list[Criterion] = Field(min_length=1)
    activity_scope: list[Activity] = Field(min_length=1)
    check_alignment: list[Check] = Field(min_length=1)
    pedagogical_adapter: Adapter

class ComponentDecision(Model):
    component: Component
    decision: Literal['APPROVE', 'REJECT', 'REVISE', 'DEFER']
    rationale: str = Field(min_length=8, max_length=4000)

class Review(Model):
    schema_version: Literal['pedagogical-evidence-review/1'] = 'pedagogical-evidence-review/1'
    policy_version: Literal['bounded-symbol-evidence-authoring/1'] = 'bounded-symbol-evidence-authoring/1'
    proposal_hash: str
    reviewer_id: str = Field(min_length=1)
    domain: Literal['HUMAN_REVIEW', 'SYNTHETIC_TEST_ONLY']
    decisions: list[ComponentDecision]
    purpose: Literal['GOVERNED_PEDAGOGICAL_CONSTRUCTION_ONLY'] = 'GOVERNED_PEDAGOGICAL_CONSTRUCTION_ONLY'

class ReviewReceipt(Model):
    review: Review
    semantic_hash: str
    recorded_at: str
    signature: str

class Pack(Model):
    schema_version: Literal['approved-pedagogical-evidence-pack/1'] = 'approved-pedagogical-evidence-pack/1'
    proposal: Proposal
    review_receipt: ReviewReceipt
    evidence_identity: str
    publication_approved: Literal[False] = False
    trusted_state_changed: Literal[False] = False
