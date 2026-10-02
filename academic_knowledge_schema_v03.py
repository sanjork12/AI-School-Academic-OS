"""Parallel v0.3 architecture prototype; no dependency on or mutation of v0.1/v0.2."""
from typing import Annotated, Literal, Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
ID = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
SourceType = Literal["official_syllabus", "official_specification_note", "official_teacher_guide",
                     "official_past_paper", "official_mark_scheme", "official_or_endorsed_textbook",
                     "third_party_textbook", "other"]
Kind = Literal["context", "concept", "competency", "action_classification", "concept_link", "scope_exclusion",
               "objective", "scope", "objective_mapping", "question", "question_part",
               "condition", "resource", "resource_use", "part_mapping", "evidence"]
SYNTHETIC_NOTICE = "SYNTHETIC ARCHITECTURE TEST DATA — NOT OFFICIAL CURRICULUM DATA"
AUTHORITY_BY_SOURCE = {
    "official_syllabus": "official_requirement", "official_specification_note": "official_requirement",
    "official_teacher_guide": "official_clarification", "official_past_paper": "official_assessment",
    "official_mark_scheme": "official_assessment", "official_or_endorsed_textbook": "official_or_endorsed_textbook",
    "third_party_textbook": "third_party_material", "other": "unclassified",
}


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TargetRef(Model):
    kind: Kind
    id: ID


class Provenance(Model):
    origin: Literal["real", "synthetic"]
    creation_method: Literal["source_import", "human", "ai", "rule"]
    source_references: list[Text] = Field(min_length=1)
    synthetic_notice: Text | None = None

    @model_validator(mode="after")
    def check_origin(self) -> Self:
        if self.origin == "synthetic":
            if self.synthetic_notice != SYNTHETIC_NOTICE:
                raise ValueError("Synthetic provenance requires explicit notice")
        elif self.synthetic_notice is not None:
            raise ValueError("Real provenance cannot carry synthetic notice")
        return self


class Reviewable(Model):
    review_status: Literal["pending", "approved", "rejected"] = "pending"
    review_decision_id: ID | None = None
    provenance: Provenance


class SourceDocument(Model):
    source_id: ID
    title: Text
    source_type: SourceType
    origin: Literal["real", "synthetic"]
    verification_status: Literal["unverified", "verified"] = "unverified"
    publisher: Text | None = None
    edition: Text | None = None
    artifact_reference: Text | None = None
    content_digest: Digest | None = None
    verification_reference: Text | None = None
    synthetic_notice: Text | None = None

    @model_validator(mode="after")
    def check_verification(self) -> Self:
        if self.origin == "synthetic":
            if self.synthetic_notice != SYNTHETIC_NOTICE or self.verification_status == "verified":
                raise ValueError("Synthetic source needs notice and cannot be verified real material")
        elif self.synthetic_notice is not None:
            raise ValueError("Real source cannot carry synthetic notice")
        if self.verification_status == "verified" and not all(
            (self.artifact_reference, self.content_digest, self.verification_reference)
        ):
            raise ValueError("Verified source requires artifact, digest and external verification reference")
        return self

    @property
    def authority(self) -> str:
        return AUTHORITY_BY_SOURCE[self.source_type]


class SourceLocator(Model):
    locator_id: ID
    source_id: ID
    locator_kind: Literal["section", "question_part", "conversation_item", "legacy_record"]
    label: Text
    verification_status: Literal["unverified", "verified"] = "unverified"
    page_index: Annotated[int, Field(ge=0)] | None = None
    anchor: Text | None = None
    assessment_part_id: ID | None = None
    assessment_question_id: ID | None = None
    verification_reference: Text | None = None


class CurriculumContext(Model):
    context_id: ID
    exam_board: Text
    qualification: Text
    subject: Text
    specification_code: Text | None = None
    curriculum_version: Text | None = None
    educational_stage: Text | None = None
    tier: Text | None = None
    pathway: Text | None = None
    provenance: Provenance


class CanonicalConcept(Reviewable):
    concept_id: ID
    subject_domain: Text
    name: Text
    description: Text


class ActionClassification(Reviewable):
    value: Literal["calculation", "determination", "interpretation", "contextual_inference",
                   "data_preparation", "classification"]
    rationale: Text


class CanonicalCompetency(Model):
    canonical_id: ID
    subject_domain: Text
    skill_name: Text
    description: Text | None = None
    status: Literal["draft", "reviewed", "approved"] = "draft"
    registry_decision_id: ID | None = None
    action_classification: ActionClassification | None = None
    provenance: Provenance


class CompetencyConceptLink(Reviewable):
    link_id: ID
    canonical_id: ID
    concept_id: ID
    relationship: Literal["applies_concept"] = "applies_concept"
    rationale: Text
    evidence_ids: list[ID] = Field(default_factory=list)


class GoldStandardEntry(Model):
    entry_id: ID
    baseline_id: ID
    baseline_version: Text
    label: Text
    category: Literal["competency", "concept", "scope", "condition", "resource"]
    disposition: Literal["approved", "strong_candidate", "candidate", "recorded", "deferred"]
    rationale: Text
    decision_source_reference: ID  # A locator, not a manufactured reviewer signature.
    target: TargetRef | None = None
    evidence_ids: list[ID] = Field(default_factory=list)
    provenance: Provenance


class OfficialObjectiveReference(Model):
    objective_id: ID
    context_id: ID
    source_locator_id: ID
    wording_excerpt: Text | None = None
    provenance: Provenance


class ScopeExclusion(Reviewable):
    exclusion_id: ID
    application: Text
    evidence_ids: list[ID] = Field(min_length=1)
    rationale: Text


class CurriculumScope(Reviewable):
    scope_id: ID
    objective_id: ID
    canonical_id: ID
    context_id: ID
    scope_description: Text
    constraints: list[Text] = Field(default_factory=list)
    included_applications: list[Text] = Field(default_factory=list)
    excluded_applications: list[ScopeExclusion] = Field(default_factory=list)
    unresolved_scope: list[Text] = Field(default_factory=list)
    concept_ids: list[ID] = Field(default_factory=list)
    evidence_ids: list[ID] = Field(default_factory=list)


class OfficialCompetencyMapping(Reviewable):
    mapping_id: ID
    objective_id: ID
    context_id: ID
    canonical_id: ID
    relationship: Literal["equivalent", "broader", "narrower", "partial"]
    confidence: Probability
    mapping_method: Literal["human", "ai", "rule"]
    evidence_ids: list[ID] = Field(default_factory=list)


class Question(Model):
    question_id: ID
    paper_source_id: ID
    label: Text
    source_locator_id: ID
    curriculum_context_id: ID | None = None
    provenance: Provenance


class QuestionPart(Model):
    part_id: ID
    question_id: ID
    label: Text
    node_kind: Literal["container", "assessable"]
    source_locator_id: ID
    parent_part_id: ID | None = None
    provenance: Provenance


class TaskCondition(Reviewable):
    condition_id: ID
    question_id: ID
    kind: Literal["input_form", "context_detail", "given_model"]
    description: Text
    availability: Literal["given_in_question", "recalled_from_resource"]
    resource_id: ID | None = None
    evidence_ids: list[ID] = Field(default_factory=list)


class PartConditionLink(Model):
    part_id: ID
    condition_id: ID


class ContextResource(Model):
    resource_id: ID
    name: Text
    resource_kind: Literal["dataset"] = "dataset"
    description: Text
    version: Text | None = None
    artifact_source_id: ID | None = None
    provenance: Provenance


class ResourceUse(Reviewable):
    use_id: ID
    resource_id: ID
    target: TargetRef
    relationship: Literal["familiarity_required", "uses_context"]
    description: Text
    evidence_ids: list[ID] = Field(default_factory=list)


class Evidence(Reviewable):
    evidence_id: ID
    source_locator_ids: list[ID] = Field(min_length=1)
    target: TargetRef
    observation: Text
    content_kind: Literal["quotation", "paraphrase", "interpretation"]
    evidence_role: Literal["supports", "clarifies", "contradicts"]
    observation_status: Literal["observed", "ambiguous", "insufficient_evidence", "not_observed"]
    examined_sample: Text | None = None
    confidence: Probability | None = None
    context_id: ID | None = None
    objective_id: ID | None = None
    explicit_exclusion: bool = False
    application: Text | None = None

    @model_validator(mode="after")
    def check_assertion(self) -> Self:
        if self.observation_status == "not_observed" and self.examined_sample is None:
            raise ValueError("Not observed needs an explicit examined sample")
        if self.explicit_exclusion and not (
            self.observation_status == "observed" and self.evidence_role == "supports" and self.application
            and self.target.kind == "scope"
        ):
            raise ValueError("Exclusion needs an observed supporting named scope assertion")
        return self


class PartCompetencyMapping(Reviewable):
    mapping_id: ID
    part_id: ID
    canonical_id: ID
    role: Literal["assessed", "supporting"]
    assessment_extent: Literal["partial", "full", "undetermined"]
    rationale: Text
    evidence_ids: list[ID] = Field(default_factory=list)
    mapping_method: Literal["human", "ai", "rule"]
    confidence: Probability | None = None
    focus_concept_ids: list[ID] = Field(default_factory=list)


class QuestionDifficulty(Model):
    part_id: ID
    scale: Literal["0_to_1_higher_is_harder"] = "0_to_1_higher_is_harder"
    calibration_status: Literal["uncalibrated_prototype"] = "uncalibrated_prototype"
    predicted_difficulty: Probability | None = None
    observed_difficulty: Probability | None = None
    reasoning_steps: Annotated[int, Field(ge=0)] | None = None
    scaffolding_level: Literal["none", "partial", "substantial"] | None = None
    context_familiarity: Literal["familiar", "mixed", "novel"] | None = None
    difficulty_method: Literal["expert_estimate", "ai_prediction", "empirical", "mixed"] | None = None
    observed_sample_size: Annotated[int, Field(gt=0)] | None = None
    provenance: Provenance

    @model_validator(mode="after")
    def measurement(self) -> Self:
        if (self.predicted_difficulty is not None or self.observed_difficulty is not None) and self.difficulty_method is None:
            raise ValueError("Difficulty measurement needs a method")
        if self.observed_difficulty is not None:
            if self.observed_sample_size is None or self.difficulty_method not in ("empirical", "mixed"):
                raise ValueError("Observed difficulty needs sample size and empirical/mixed method")
        elif self.observed_sample_size is not None:
            raise ValueError("Sample size without observed difficulty")
        if self.predicted_difficulty is not None and self.difficulty_method == "empirical":
            raise ValueError("Prediction with empirical observation requires mixed method")
        return self


class ReviewDecision(Model):
    decision_id: ID
    target: TargetRef
    target_content_digest: Digest
    decision: Literal["approved", "rejected"]
    reviewer_reference: Text
    decision_source_reference: Text
    rationale: Text
    supersedes_decision_id: ID | None = None


class AcademicKnowledgePrototype(Model):
    schema_version: Literal["0.3"] = "0.3"
    purpose: Literal["architecture_prototype_not_production"] = "architecture_prototype_not_production"
    evidence_notice: Text
    sources: list[SourceDocument]
    locators: list[SourceLocator]
    contexts: list[CurriculumContext]
    concepts: list[CanonicalConcept]
    competencies: list[CanonicalCompetency]
    concept_links: list[CompetencyConceptLink] = Field(default_factory=list)
    gold_standard_entries: list[GoldStandardEntry]
    objective_references: list[OfficialObjectiveReference] = Field(default_factory=list)
    scopes: list[CurriculumScope] = Field(default_factory=list)
    objective_mappings: list[OfficialCompetencyMapping] = Field(default_factory=list)
    questions: list[Question]
    question_parts: list[QuestionPart]
    task_conditions: list[TaskCondition] = Field(default_factory=list)
    part_condition_links: list[PartConditionLink] = Field(default_factory=list)
    resources: list[ContextResource] = Field(default_factory=list)
    resource_uses: list[ResourceUse] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    part_mappings: list[PartCompetencyMapping] = Field(default_factory=list)
    question_difficulties: list[QuestionDifficulty] = Field(default_factory=list)
    review_decisions: list[ReviewDecision] = Field(default_factory=list)
