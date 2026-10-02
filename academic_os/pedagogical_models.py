"""Candidate teaching design, separate from trusted learning requirements."""
import json
from typing import Literal
from pydantic import model_validator
from .product_models import ProductModel
from .learning_models import EvidenceBoundary,LearningIdentity,LearningRequirement,CoverageRequirement,ConceptualBasis


class EvidenceReference(ProductModel):
    ref:str
    year:int | None
    session:str | None
    paper:str | None
    question_part:str
    capability_ref:str
    task_form_refs:tuple[str,...]
    reading_notes:tuple[str,...]


class SourceLearningContract(ProductModel):
    schema_version:Literal['learning-specification/1']='learning-specification/1'
    identity:LearningIdentity
    conceptual_basis:tuple[ConceptualBasis,...]
    learning_requirements:tuple[LearningRequirement,...]
    coverage_requirements:tuple[CoverageRequirement,...]
    evidence_boundaries:tuple[EvidenceBoundary,...]
    assessment_evidence:tuple[EvidenceReference,...]


class PedagogicalIdentity(LearningIdentity):
    view_type:Literal['pedagogical_specification']='pedagogical_specification'


class Constraint(ProductModel):
    level:Literal['required','recommended','flexible']
    statement:str


class InstructionalContent(ProductModel):
    ref:str
    type:Literal['calculation_method_slot','task_input_slot','worked_example_slot','learning_check_slot']
    status:Literal['candidate_slot']='candidate_slot'
    purpose:str
    supports_learning_requirement_refs:tuple[str,...]
    source_product_refs:tuple[str,...]
    evidence_refs:tuple[str,...]
    formula_memorisation_required:Literal[False]=False
    assesses_learning_requirement_refs:tuple[str,...]=()
    source_quality_notes:tuple[str,...]=()


class TeachingBlock(ProductModel):
    ref:str
    role:Literal['conceptual_meaning','calculation_method','supported_task_form','worked_assessment_connection','practice_learning_check']
    title:str
    purpose:str
    covers_learning_requirement_refs:tuple[str,...]
    covers_coverage_requirement_refs:tuple[str,...]
    constraints:tuple[Constraint,...]
    instructional_content_refs:tuple[str,...]
    evidence_refs:tuple[str,...]
    boundary_refs:tuple[str,...]


class CoverageMap(ProductModel):
    status:Literal['planned_coverage']='planned_coverage'
    learning_requirements:dict[str,tuple[str,...]]
    coverage_requirements:dict[str,tuple[str,...]]


class PedagogicalSpecification(ProductModel):
    artifact_kind:Literal['pedagogical_specification_candidate']='pedagogical_specification_candidate'
    schema_version:Literal['pedagogical-specification/1']='pedagogical-specification/1'
    status:Literal['candidate']='candidate'
    identity:PedagogicalIdentity
    source_learning_specification:SourceLearningContract
    teaching_blocks:tuple[TeachingBlock,...]
    instructional_content:tuple[InstructionalContent,...]
    coverage_map:CoverageMap
    evidence_boundaries:tuple[EvidenceBoundary,...]
    generator_constraints:tuple[Constraint,...]
    trust_boundary:str

    @model_validator(mode='after')
    def relationships(self):
        source=self.source_learning_specification
        learning={r.ref for r in source.learning_requirements}
        coverage={r.ref for r in source.coverage_requirements}
        evidence={e.ref for e in source.assessment_evidence}
        boundaries={b.ref for b in source.evidence_boundaries}
        content={c.ref:c for c in self.instructional_content}
        refs=[b.ref for b in self.teaching_blocks]+[c.ref for c in self.instructional_content]
        if len(refs)!=len(set(refs)) or set(refs)&(learning|coverage|boundaries|evidence):raise ValueError('Pedagogical refs must be unique and distinct from source refs')
        if self.evidence_boundaries!=source.evidence_boundaries:raise ValueError('Evidence boundaries must be preserved')
        actual_lr={r:[] for r in sorted(learning)};actual_cr={r:[] for r in sorted(coverage)}
        for b in self.teaching_blocks:
            if not set(b.covers_learning_requirement_refs)<=learning or not set(b.covers_coverage_requirement_refs)<=coverage:
                raise ValueError('Unknown coverage requirement ref')
            if not set(b.evidence_refs)<=evidence or not set(b.boundary_refs)<=boundaries or not set(b.instructional_content_refs)<=set(content):
                raise ValueError('Unknown teaching block evidence/content/boundary ref')
            for ref in b.covers_learning_requirement_refs:actual_lr[ref].append(b.ref)
            for ref in b.covers_coverage_requirement_refs:actual_cr[ref].append(b.ref)
        for c in self.instructional_content:
            if not set(c.supports_learning_requirement_refs)<=learning or not set(c.assesses_learning_requirement_refs)<=set(c.supports_learning_requirement_refs) or not set(c.evidence_refs)<=evidence:
                raise ValueError('Unknown instructional learning/evidence ref')
        for actual,declared in ((actual_lr,self.coverage_map.learning_requirements),(actual_cr,self.coverage_map.coverage_requirements)):
            if {k:tuple(sorted(v)) for k,v in actual.items()}!=declared or any(not v for v in actual.values()):
                raise ValueError('Planned coverage must match blocks and cover every requirement')
        return self

    def serialize(self):
        return json.dumps(self.model_dump(mode='json'),ensure_ascii=False,sort_keys=True,indent=2)+'\n'
