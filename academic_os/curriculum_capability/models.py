from typing import Literal
from pydantic import BaseModel, ConfigDict
from academic_os.curriculum_ingestion.models import SelectedCurriculumTarget, Warning


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Eligibility(Model):
    eligible: bool
    status: Literal['PASS', 'PASS_WITH_WARNINGS', 'BLOCKED', 'NOT_ELIGIBLE']
    reason_code: str
    missing_requirements: list[str]


class CanonicalBinding(Model):
    official_source_id: str
    canonical_id: str
    canonical_wording: str
    relationship: str
    evidence_path: str
    evidence_sha256: str
    historical_review_status: str
    mapping_method: str
    human_review_evidence: Literal['RECORDED_DECISION', 'NOT_AVAILABLE']
    decision_ids: list[str]
    historically_promoted: bool
    trusted_snapshot_backed: Literal[False] = False
    uploaded_target_approved: Literal[False] = False


class ObjectiveEvidence(Model):
    objective_identity: str
    objective_code: str
    official_text: str
    source_id: str
    tier: str
    topic_code: str
    topic_name: str
    subtopic_code: str
    subtopic_name: str
    subtopic_notes: list[str]
    source_sha256: str
    origin: Literal['parser-derived'] = 'parser-derived'
    parsed: Literal[True] = True
    structure_valid: Literal[True] = True
    source_bound: Literal[True] = True
    human_reviewed: Literal[False] = False
    promoted: Literal[False] = False
    trusted_snapshot_backed: Literal[False] = False
    warning_scope: Literal['run-wide; not attributed to individual glyphs'] = 'run-wide; not attributed to individual glyphs'
    warnings: list[Warning]
    validation_sha256: str
    mapping_status: Literal['MAPPED', 'UNMAPPED', 'REVIEW_REQUIRED']
    canonical_bindings: list[CanonicalBinding]
    ai_proposal_ids: list[str]


class Coverage(Model):
    selected_objectives: int
    canonical_mapped: int
    unmapped: int
    review_required: int
    warnings: int


class AcademicCapabilityPackage(Model):
    schema_version: Literal['academic-capability-package/1'] = 'academic-capability-package/1'
    construction_version: Literal['topic2-capability-construction/1'] = 'topic2-capability-construction/1'
    target: SelectedCurriculumTarget
    source_binding: dict[str, str]
    objectives: list[ObjectiveEvidence]
    coverage: Coverage
    unresolved_items: list[str]
    warnings: list[Warning]
    eligibility: dict[str, Eligibility]
    supported_capabilities: list[str]
    unsupported_capabilities: list[str]
    evidence: dict[str, str]
    academically_approved: Literal[False] = False
    model_calls: Literal[0] = 0


class PackageReceipt(Model):
    package_id: str
    package_sha256: str
    source_target_id: str
    construction_version: str
    created_at: str
