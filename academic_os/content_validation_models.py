"""Renderer eligibility diagnostics, never academic or pedagogical approval."""
import json
from typing import Literal
from .product_models import ProductModel
from .pedagogical_validation import Finding,Check
from .authored_math import MathVerification


class ContentCoverageRow(ProductModel):
    requirement_ref:str
    kind:Literal['learning_requirement','coverage_requirement']
    semantic_role:str
    status:Literal['covered','uncovered','invalid','satisfied','unsatisfied']
    evidence_refs:tuple[str,...]


class ContentSlotRow(ProductModel):
    slot_ref:str
    semantic_role:str
    populated:bool
    evidence_refs:tuple[str,...]


class RendererReadiness(ProductModel):
    ready_for_rendering:bool
    blocking_codes:tuple[str,...]


class AuthoredContentValidationReport(ProductModel):
    schema_version:Literal['authored-content-validation/1']='authored-content-validation/1'
    identity:dict
    input_contracts:dict[str,str]
    reference_integrity:Check
    content_completeness:Check
    mathematical_integrity:Check
    learning_alignment:Check
    coverage_requirement_validation:Check
    boundary_compliance:Check
    slot_population:tuple[ContentSlotRow,...]
    renderer_readiness:RendererReadiness
    violations:tuple[Finding,...]
    warnings:tuple[Finding,...]
    coverage_matrix:tuple[ContentCoverageRow,...]
    verification_summary:dict[str,MathVerification]
    trust_summary:dict

    def serialize(self):return json.dumps(self.model_dump(mode='json'),sort_keys=True,ensure_ascii=False,indent=2)+'\n'
