"""Authored candidate contract. Mathematical checks are not academic approval."""
import json
from typing import Literal
from pydantic import Field,model_validator
from .product_models import ProductModel
from .learning_models import LearningIdentity,EvidenceBoundary
from .authored_math import MathVerification

Origin=Literal['trusted_semantic_transformation','authored_instructional_content','generated_original','reviewed_evidence_alignment']


class AuthoredIdentity(LearningIdentity):
    view_type:Literal['authored_teaching_content']='authored_teaching_content'


class SummaryStatistics(ProductModel):
    n:int=Field(strict=True)
    sum_x:str
    sum_x2:str


class AuthoredObject(ProductModel):
    ref:str
    origin:Origin
    constraint_level:Literal['required','recommended','flexible']
    teaching_block_refs:tuple[str,...]
    instructional_slot_refs:tuple[str,...]=()
    covers_learning_requirement_refs:tuple[str,...]=()
    assesses_learning_requirement_refs:tuple[str,...]=()


class VisualData(ProductModel):
    datasets:dict[str,tuple[str,...]]
    claims:dict[str,dict[str,str]]
    same_mean:bool
    sd_order:tuple[str,...]
    brief:str


class ContentBlock(AuthoredObject):
    kind:Literal['concept_explanation','visual_comparison','calculation_method','summary_statistics_method','worked_example','practice_item','concept_check','calculation_check']
    text:str
    item_ref:str | None=None
    formula_refs:tuple[str,...]=()
    instructional_inputs:dict[str,str]=Field(default_factory=dict)
    visual:VisualData | None=None
    verification:MathVerification | None=None


class InstructionalFormula(AuthoredObject):
    role:Literal['instructional_formula']='instructional_formula'
    formula_memorisation_required:Literal[False]=False
    expression:dict
    display_expression:str
    verification:MathVerification


class QuestionItem(AuthoredObject):
    kind:Literal['worked_example','practice_item','concept_check','calculation_check']
    question:str
    summary:SummaryStatistics | None=None
    capability_refs:tuple[str,...]=()
    task_form_refs:tuple[str,...]=()
    assessment_structure_origin:Literal['reviewed_evidence_alignment'] | None=None
    evidence_refs:tuple[str,...]=()
    verification:MathVerification | None=None


class Solution(AuthoredObject):
    item_ref:str
    method_steps:tuple[str,...]=()
    mean:str | None=None
    variance:str | None=None
    exact_answer:dict | None=None
    numeric_answer:str | None=None
    display_answer:str | None=None
    expected_meaning:str | None=None
    key_semantic_elements:tuple[str,...]=()
    exact_string_matching_required:Literal[False]=False
    verification:MathVerification | None=None


class SourcePedagogy(ProductModel):
    schema_version:Literal['pedagogical-specification/1']='pedagogical-specification/1'
    validation_schema_version:Literal['pedagogical-validation/1']='pedagogical-validation/1'
    view_key:str
    pedagogical_content_sha256:str
    validation_content_sha256:str
    teaching_block_refs:tuple[str,...]
    instructional_slot_refs:tuple[str,...]
    learning_requirement_refs:tuple[str,...]


class VerificationSummary(ProductModel):
    mathematical_checks_passed:bool
    checks:dict[str,MathVerification]
    ready_for_downstream_content_validation:bool
    ready_as_completed_teaching_content:Literal[False]=False


class SlotPopulation(ProductModel):
    status:Literal['content_supplied_pending_validation']='content_supplied_pending_validation'
    populated:bool
    content_refs:tuple[str,...]


class AuthoredTeachingPackage(ProductModel):
    schema_version:Literal['authored-teaching-content/1']='authored-teaching-content/1'
    artifact_kind:Literal['authored_teaching_candidate']='authored_teaching_candidate'
    status:Literal['authored_candidate']='authored_candidate'
    identity:AuthoredIdentity
    authoring_provider:str
    source_pedagogical_specification:SourcePedagogy
    content_blocks:tuple[ContentBlock,...]
    instructional_formulas:tuple[InstructionalFormula,...]
    worked_examples:tuple[QuestionItem,...]
    practice_items:tuple[QuestionItem,...]
    learning_checks:tuple[QuestionItem,...]
    solutions:tuple[Solution,...]
    verification_summary:VerificationSummary
    coverage_summary:dict[str,SlotPopulation]
    evidence_boundaries:tuple[EvidenceBoundary,...]
    content_boundaries:tuple[str,...]
    trust_boundary:str

    @model_validator(mode='after')
    def relationships(self):
        objects=(*self.content_blocks,*self.instructional_formulas,*self.worked_examples,*self.practice_items,*self.learning_checks,*self.solutions)
        refs=[o.ref for o in objects]
        if len(refs)!=len(set(refs)):raise ValueError('Authored refs must be unique')
        source=self.source_pedagogical_specification
        for o in objects:
            if not o.teaching_block_refs or not set(o.teaching_block_refs)<=set(source.teaching_block_refs):raise ValueError('Authored teaching block ref does not resolve')
            if not set(o.instructional_slot_refs)<=set(source.instructional_slot_refs):raise ValueError('Authored slot ref does not resolve')
            learning=set(o.covers_learning_requirement_refs)|set(o.assesses_learning_requirement_refs)
            if not learning or not learning<=set(source.learning_requirement_refs):raise ValueError('Authored LR ref does not resolve')
        items={q.ref for q in (*self.worked_examples,*self.practice_items,*self.learning_checks)}
        if sorted(s.item_ref for s in self.solutions)!=sorted(items):raise ValueError('Every item requires exactly one separate solution')
        formulas={f.ref for f in self.instructional_formulas}
        for b in self.content_blocks:
            if b.item_ref is not None and b.item_ref not in items:raise ValueError('Content item ref does not resolve')
            if not set(b.formula_refs)<=formulas:raise ValueError('Formula ref does not resolve')
        if set(self.coverage_summary)!=set(source.instructional_slot_refs):raise ValueError('Every upstream slot must be reported')
        for slot,row in self.coverage_summary.items():
            actual={b.ref for b in self.content_blocks if slot in b.instructional_slot_refs}
            if set(row.content_refs)!=actual or row.populated!=bool(actual):raise ValueError('Slot population must match supplied content')
        return self

    def serialize(self):return json.dumps(self.model_dump(mode='json'),ensure_ascii=False,sort_keys=True,indent=2)+'\n'
