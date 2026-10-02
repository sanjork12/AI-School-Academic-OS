"""Parallel architecture prototype. No v0.1 imports, mutation or promotion."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
ReviewStatus = Literal["pending", "approved", "rejected"]
SourceType = Literal[
    "official_syllabus", "official_specification_note", "official_teacher_guide",
    "official_past_paper", "official_mark_scheme", "official_or_endorsed_textbook",
    "third_party_textbook", "other",
]
Authority = Literal[
    "official_requirement", "official_clarification", "official_assessment",
    "official_or_endorsed_textbook", "third_party_material", "unclassified",
]
SYNTHETIC_NOTICE = (
    "SYNTHETIC ARCHITECTURE TEST DATA — NOT OFFICIAL CURRICULUM DATA"
)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Provenance(Model):
    origin: Literal["real", "synthetic"]
    source_reference: Text
    synthetic_notice: str | None = None

    @model_validator(mode="after")
    def marked_origin(self) -> Self:
        synthetic = self.origin == "synthetic"
        if synthetic:
            if self.synthetic_notice != SYNTHETIC_NOTICE:
                raise ValueError("Synthetic data requires the explicit synthetic notice")
            if not self.source_reference.startswith("synthetic://"):
                raise ValueError("Synthetic source reference must use synthetic://")
        elif self.synthetic_notice is not None or self.source_reference.startswith("synthetic://"):
            raise ValueError("Real data cannot use synthetic provenance")
        return self


class CurriculumContext(Model):
    context_id: Identifier
    exam_board: Text
    qualification: Text
    subject: Text
    specification_code: Text | None = None
    curriculum_version: Text | None = None
    educational_stage: Text | None = None
    tier: Text | None = None
    pathway: Text | None = None
    provenance: Provenance


class CanonicalCompetency(Model):
    canonical_id: Identifier
    subject_domain: Text
    skill_name: Text
    description: Text | None = None
    status: Literal["draft", "reviewed", "approved"] = "draft"
    provenance: Provenance


class OfficialObjectiveReference(Model):
    official_source_id: Identifier
    context_id: Identifier
    # Readability copy only; validator checks real excerpts against parsed source.
    wording_excerpt: Text | None = None
    provenance: Provenance


class ScopeExclusion(Model):
    application: Text
    evidence_ids: list[Identifier] = Field(min_length=1)
    rationale: Text
    review_status: ReviewStatus = "pending"


class CurriculumScope(Model):
    scope_id: Identifier
    official_source_id: Identifier
    canonical_id: Identifier
    context_id: Identifier
    scope_description: Text
    constraints: list[Text] = Field(default_factory=list)
    included_applications: list[Text] = Field(default_factory=list)
    excluded_applications: list[ScopeExclusion] = Field(default_factory=list)
    unresolved_scope: list[Text] = Field(default_factory=list)
    evidence_ids: list[Identifier] = Field(default_factory=list)
    review_status: ReviewStatus = "pending"
    provenance: Provenance


class CurriculumEvidence(Model):
    evidence_id: Identifier
    official_source_id: Identifier
    context_id: Identifier
    canonical_id: Identifier | None = None
    scope_id: Identifier | None = None
    source_type: SourceType
    authority: Authority
    observation: Text
    evidence_role: Literal["supports", "clarifies", "contradicts"]
    observation_status: Literal[
        "observed", "ambiguous", "insufficient_evidence", "not_observed"
    ]
    # Explicit source assertion, never inferred from absence in an examined sample.
    explicit_exclusion: bool = False
    application: Text | None = None
    confidence: Probability | None = None
    review_status: ReviewStatus = "pending"
    provenance: Provenance

    @model_validator(mode="after")
    def no_exclusion_from_absence(self) -> Self:
        if self.explicit_exclusion and (
            self.observation_status != "observed"
            or self.evidence_role != "supports"
            or self.application is None
        ):
            raise ValueError("Explicit exclusion needs an observed, supporting, named assertion")
        return self


class OfficialCompetencyMapping(Model):
    official_source_id: Identifier
    context_id: Identifier
    canonical_id: Identifier
    relationship: Literal["equivalent", "broader", "narrower", "partial"]
    confidence: Probability
    mapping_method: Literal["human", "ai", "rule"]
    review_status: ReviewStatus = "pending"
    evidence_ids: list[Identifier] = Field(default_factory=list)
    # Reference the existing audit decision, not a duplicate of its contents.
    human_review_decision_id: Identifier | None = None
    provenance: Provenance


class QuestionReference(Model):
    question_id: Identifier
    source_type: SourceType
    curriculum_context_id: Identifier | None = None
    provenance: Provenance


class QuestionCompetencyMapping(Model):
    question_id: Identifier
    canonical_id: Identifier
    primary: bool = True
    confidence: Probability


class QuestionDifficulty(Model):
    question_id: Identifier
    # Task-level illustrative scale, not calibrated across cohorts/curricula.
    scale: Literal["0_to_1_higher_is_harder"] = "0_to_1_higher_is_harder"
    predicted_difficulty: Probability | None = None
    observed_difficulty: Probability | None = None
    reasoning_steps: Annotated[int, Field(ge=0)] | None = None
    scaffolding_level: Literal["none", "partial", "substantial"] | None = None
    context_familiarity: Literal["familiar", "mixed", "novel"] | None = None
    difficulty_method: Literal["expert_estimate", "ai_prediction", "empirical", "mixed"] | None = None
    observed_sample_size: Annotated[int, Field(gt=0)] | None = None
    provenance: Provenance

    @model_validator(mode="after")
    def measurement_requirements(self) -> Self:
        if self.predicted_difficulty is not None or self.observed_difficulty is not None:
            if self.difficulty_method is None:
                raise ValueError("A difficulty measurement requires its method")
        if self.observed_difficulty is not None:
            if self.observed_sample_size is None or self.difficulty_method not in ("empirical", "mixed"):
                raise ValueError("Observed difficulty requires a sample size and empirical/mixed method")
        elif self.observed_sample_size is not None:
            raise ValueError("Sample size without observed difficulty is ambiguous")
        if self.predicted_difficulty is not None and self.difficulty_method == "empirical":
            raise ValueError("Prediction plus empirical observation must use mixed method")
        return self


class AcademicKnowledgePrototype(Model):
    schema_version: Literal["0.2"] = "0.2"
    purpose: Literal["architecture_prototype_not_production"] = "architecture_prototype_not_production"
    synthetic_notice: Literal[SYNTHETIC_NOTICE] = SYNTHETIC_NOTICE
    contexts: list[CurriculumContext]
    competencies: list[CanonicalCompetency]
    objective_references: list[OfficialObjectiveReference]
    scopes: list[CurriculumScope]
    evidence: list[CurriculumEvidence]
    mappings: list[OfficialCompetencyMapping]
    questions: list[QuestionReference] = Field(default_factory=list)
    question_mappings: list[QuestionCompetencyMapping] = Field(default_factory=list)
    question_difficulties: list[QuestionDifficulty] = Field(default_factory=list)
