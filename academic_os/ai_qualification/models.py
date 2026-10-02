"""Persisted experiment records, explicitly separate from academic contracts."""
from typing import Literal
from pydantic import Field
from ..ai_authoring.models import Contract, ProvenanceStatus
from ..ai_authoring.controlled import ControlledCase, MODE

Experiment = Literal['live_normal', 'offline_synthetic', 'live_adversarial', 'offline_synthetic_stress']
Outcome = Literal['candidate_accepted', 'candidate_validation_rejected', 'candidate_schema_failure', 'provider_failure', 'input_validation_failure']


class Attempt(Contract):
    attempt_id: str
    candidate_id: str
    brief_ref: str
    brief_hash: str
    model_identifier: str
    started_at: str
    completed_at: str
    latency_ms: float | None
    provider_request_id: str | None
    provider_calls: int = Field(ge=0, le=1)
    provider_call_completed: bool | None = None
    outcome: Outcome
    operational_error: str | None
    schema_valid: bool | None
    content_complete: bool | None
    scaffold_valid: bool | None
    numeric_encoding_valid: bool | None = None
    expression_semantics_valid: bool | None = None
    derivation_provenance_valid: bool | None = None
    derivation_provenance_status: ProvenanceStatus = 'NOT_EVALUATED'
    acceptance_policy: str = 'sl10-expression-required/1' 
    math_valid: bool | None
    solution_valid: bool | None
    scope_valid: bool | None
    boundary_valid: bool | None
    composition_valid: bool | None
    accepted: bool
    violations: tuple[str, ...]
    warnings: tuple[str, ...]
    usage: dict[str, int | None]
    candidate_artifact_ref: str
    artifact_hashes: dict[str, str]
    observed_configuration: dict
    case_id: str | None = None
    expected_guardrail: str | None = None
    blocked: bool | None = None
    forbidden_behavior_observed: bool | None = None


class QualificationReport(Contract):
    schema_version: Literal['live-model-qualification/1'] = 'live-model-qualification/1'
    acceptance_policy: str = 'sl10-expression-required/1'
    identity: str
    experiment_type: Experiment
    status: Literal['complete', 'incomplete']
    completion_reason: str
    slot: dict[str, str]
    authoring_brief: dict[str, str]
    provider: str
    model: str
    configuration: dict
    requested_attempt_count: int = Field(ge=1, le=20)
    attempt_count: int = Field(ge=0)
    started_attempt_count: int = Field(ge=0)
    attempts: tuple[Attempt, ...]
    aggregate_validation: dict
    rejection_summary: dict[str, int]
    operational_outcomes: dict[str, int]
    usage_summary: dict
    latency_summary: dict
    stress_tests: tuple[Attempt, ...]
    stress_summary: dict
    safety_summary: dict
    baseline_integrity: dict
    limitations: tuple[str, ...]


class ControlledAttempt(Attempt):
    controlled_mode: Literal['sl10-controlled-input/1'] = MODE
    controlled_case: ControlledCase
    controlled_case_sha256: str
    returned_inputs: dict | None
    controlled_input_binding_valid: bool | None
    controlled_input_binding_status: Literal['PASSED', 'FAILED', 'NOT_EVALUATED']
    controlled_input_binding_reason: str


class ControlledQualificationReport(QualificationReport):
    controlled_mode: Literal['sl10-controlled-input/1'] = MODE
    controlled_case: ControlledCase
    controlled_case_sha256: str
    attempts: tuple[ControlledAttempt, ...]
