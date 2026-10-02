"""Content-only provider schema; application bindings never come from the model."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Inputs(Contract):
    n: int = Field(strict=True)
    sum_x: str
    sum_x2: str


StepType = Literal['compute_first_term', 'compute_second_term', 'subtract_variance_terms', 'square_root']


class Scaffold(Contract):
    type: StepType
    instruction: str


class WorkingValue(Contract):
    expression: str = Field(min_length=1, max_length=256, description="Untrusted explanatory calculation or equation; never evaluated or rendered by production.")
    value: str = Field(description="Scalar only: integer, decimal or simple rational, e.g. 11 or 15/2; never an equation.")


class ProposedSolution(Contract):
    inputs: Inputs
    first_term: WorkingValue
    second_term: WorkingValue
    mean: WorkingValue
    variance: WorkingValue
    exact_radicand: str
    numeric_answer: str
    display_answer: str


class ProviderContent(Contract):
    # Numbers are separate fields: prose cannot silently override a statistic.
    question_template: str
    proposed_math_inputs: Inputs
    scaffold_steps: list[Scaffold]
    proposed_solution: ProposedSolution


class AuthoringBrief(Contract):
    schema_version: Literal['authoring-brief/2'] = 'authoring-brief/2'
    identity: Literal['standard-deviation-standard-lesson-SL-10/2'] = 'standard-deviation-standard-lesson-SL-10/2'
    profile_context: str
    role: Literal['Guided practice 1'] = 'Guided practice 1'
    learning_targets: tuple[str, ...]
    task_form: Literal['From summary statistics'] = 'From summary statistics'
    support_mode: Literal['guided'] = 'guided'
    formula: str
    required_output: tuple[str, ...]
    allowed_question_templates: tuple[str, ...]
    allowed_scaffolds: dict[str, tuple[str, ...]]
    forbidden_content: tuple[str, ...]
    content_origin_policy: Literal['ai_generated_candidate'] = 'ai_generated_candidate'
    copyright_policy: str
    solution_policy: str


class ProvenanceBrief(AuthoringBrief):
    schema_version: Literal['authoring-brief/3'] = 'authoring-brief/3'
    identity: Literal['standard-deviation-standard-lesson-SL-10/3'] = 'standard-deviation-standard-lesson-SL-10/3'
    generation_policy: Literal['sl10-provenance-required/1'] = 'sl10-provenance-required/1'


ProvenanceStatus = Literal['PASSED', 'FAILED', 'INSUFFICIENT_EVIDENCE', 'NOT_EVALUATED']


class Metadata(Contract):
    provider: str
    model: str
    latency_seconds: float = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost: Literal['not_computed'] = 'not_computed'


class Candidate(Contract):
    schema_version: Literal['ai-author-candidate/2'] = 'ai-author-candidate/2'
    candidate_id: str = Field(pattern=r'^ai-candidate-[0-9a-f]{32}$')
    brief_ref: str
    brief_sha256: str
    current_inputs_sha256: str
    role_ref: str
    learning_requirement_refs: tuple[str, ...]
    task_form_refs: tuple[str, ...]
    content_origin: Literal['ai_generated_candidate'] = 'ai_generated_candidate'
    content: ProviderContent
    model_metadata: Metadata


class Validation(Contract):
    schema_version: Literal['ai-candidate-validation/1', 'ai-candidate-validation/2'] = 'ai-candidate-validation/2'
    candidate_id: str
    brief_ref: str
    schema_valid: bool
    binding_valid: bool
    content_complete: bool
    scaffold_valid: bool
    math_valid: bool
    solution_valid: bool
    expression_semantics_valid: bool = False
    derivation_provenance_valid: bool | None = None
    derivation_provenance_status: ProvenanceStatus = 'NOT_EVALUATED'
    acceptance_policy: str = 'sl10-expression-required/1' 
    scope_valid: bool
    boundary_valid: bool
    separation_valid: bool
    origin_valid: bool
    composition_valid: bool
    accepted: bool
    violations: tuple[str, ...]
    warnings: tuple[str, ...]
    verification_summary: dict
