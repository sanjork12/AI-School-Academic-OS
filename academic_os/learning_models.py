"""Learning contract identities and coverage constraints, not academic ontology."""
import json
from typing import Literal
from pydantic import model_validator
from .product_models import ProductModel, Curriculum
from .assessment_intelligence import ReviewedExample, IntelligenceTrust


class LearningIdentity(ProductModel):
    view_key:str
    view_type:Literal['learning_specification']='learning_specification'
    title:str
    subject:str
    qualification:str
    awarding_body:str
    specification_code:str
    curriculum_section:str


class ConceptualBasis(ProductModel):
    concept_ref:str
    name:str
    description:str


class LearningRequirement(ProductModel):
    ref:str
    type:Literal['conceptual_understanding','capability','capability_under_task_form']
    epistemic_class:Literal['evidence_backed_requirement']='evidence_backed_requirement'
    statement:str
    source_refs:tuple[str,...]
    evidence_refs:tuple[str,...]=()
    scope_note:str


class CoverageRequirement(ProductModel):
    ref:str
    type:Literal['teaching_assessment_connection','assessment_alignment']
    epistemic_class:Literal['evidence_backed_requirement']='evidence_backed_requirement'
    statement:str
    learning_requirement_refs:tuple[str,...]
    source_refs:tuple[str,...]
    evidence_refs:tuple[str,...]
    policy_basis:Literal['learning-specification/1 coverage policy']='learning-specification/1 coverage policy'


class EvidenceBoundary(ProductModel):
    ref:str
    code:str
    epistemic_class:Literal['evidence_boundary']='evidence_boundary'
    statement:str
    basis:Literal['upstream_limitation','contract_scope']
    source_refs:tuple[str,...]


class LearningSpecification(ProductModel):
    artifact_kind:Literal['learning_specification_read_model']='learning_specification_read_model'
    schema_version:Literal['learning-specification/1']='learning-specification/1'
    identity:LearningIdentity
    source_contracts:tuple[Literal['teacher-topic/2','assessment-intelligence/1'],...]
    conceptual_basis:tuple[ConceptualBasis,...]
    learning_requirements:tuple[LearningRequirement,...]
    coverage_requirements:tuple[CoverageRequirement,...]
    assessment_evidence:tuple[ReviewedExample,...]
    evidence_boundaries:tuple[EvidenceBoundary,...]
    curriculum:Curriculum
    trust_summary:IntelligenceTrust

    @model_validator(mode='after')
    def references(self):
        all_refs=[r.ref for r in (*self.learning_requirements,*self.coverage_requirements,*self.evidence_boundaries,*self.assessment_evidence)]
        if len(all_refs)!=len(set(all_refs)):raise ValueError('Learning contract refs must be unique')
        learning={r.ref for r in self.learning_requirements}
        evidence={e.ref for e in self.assessment_evidence}
        for r in (*self.learning_requirements,*self.coverage_requirements):
            if not r.source_refs or not set(r.evidence_refs)<=evidence:
                raise ValueError('Requirements need source refs and resolving evidence refs')
        for r in self.coverage_requirements:
            if not r.learning_requirement_refs or not set(r.learning_requirement_refs)<=learning:
                raise ValueError('Coverage refs must resolve to included learning requirements')
        return self

    def serialize(self):
        return json.dumps(self.model_dump(mode='json'),ensure_ascii=False,sort_keys=True,indent=2)+'\n'
