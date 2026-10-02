"""Profile-aware content references and separate original questions/solutions."""
from typing import Literal
from pydantic import Field
from .lesson_profile_models import Contract,SourceBinding
from .product_models import ProductModel
from .authored_models import SummaryStatistics
from .authored_math import MathVerification
from .learning_models import EvidenceBoundary

class NewContent(ProductModel):
    ref:str
    semantic_role:str
    content_origin:Literal['generated_original']='generated_original'
    lineage:Literal['created_for_profile_density']='created_for_profile_density'
    learning_requirement_refs:tuple[str,...]
    assesses_learning_requirement_refs:tuple[str,...]=()
    task_form_refs:tuple[str,...]=()
    question:str
    concept_prompt:str|None=None
    concept_learning_requirement_refs:tuple[str,...]=()
    calculation_learning_requirement_refs:tuple[str,...]=()
    summary:SummaryStatistics|None=None
    raw_values:tuple[str,...]=()
    scaffolding:tuple[str,...]=()
    support_mode:Literal['not_applicable','guided','independent']='not_applicable'
    instructional_demonstration_only:bool=False
    creates_assessed_task_form:Literal[False]=False

class NewSolution(ProductModel):
    ref:str
    item_ref:str
    content_origin:Literal['authored_instructional_content']='authored_instructional_content'
    method_steps:tuple[str,...]=()
    mean:str|None=None
    variance:str|None=None
    exact_answer:dict|None=None
    numeric_answer:str|None=None
    display_answer:str|None=None
    expected_meaning:str|None=None
    key_semantic_elements:tuple[str,...]=()
    exact_string_matching_required:Literal[False]=False
    deviations:tuple[str,...]=()
    squared_deviations:tuple[str,...]=()

class ReusedReference(ProductModel):
    ref:str
    content_sha256:str
    dependency_hashes:dict[str,str]
    source_package_sha256:str
    source_validation_sha256:str

class RoleDecision(ProductModel):
    role_ref:str
    role_key:str
    decision:Literal['reuse','author_new','unresolved']
    reason:str
    reused_content_refs:tuple[str,...]=()
    new_content_refs:tuple[str,...]=()
    solution_refs:tuple[str,...]=()
    minimum_items:int
    target_items:int
    supplied_items:int
    minimum_met:bool
    target_met:bool
    compatibility:dict[str,dict[str,bool]]

class ProfiledAuthoredPackage(Contract):
    schema_version:Literal['profiled-authored-teaching-content/1']='profiled-authored-teaching-content/1'
    profile_key:str
    authoring_provider:Literal['standard-deviation-profile-density/1']='standard-deviation-profile-density/1'
    status:Literal['candidate_pending_p5c']='candidate_pending_p5c'
    source_profiled_pedagogy:SourceBinding
    source_authored_content:SourceBinding
    source_authored_validation:SourceBinding
    academic_scope_fingerprint:str
    learning_requirement_refs:tuple[str,...]
    coverage_requirement_refs:tuple[str,...]
    evidence_boundaries:tuple[EvidenceBoundary,...]
    content_boundaries:tuple[str,...]
    framing:dict[str,tuple[str,...]]
    role_decisions:tuple[RoleDecision,...]
    reused_content:tuple[ReusedReference,...]
    new_content:tuple[NewContent,...]
    new_solutions:tuple[NewSolution,...]
    mathematical_verification:dict[str,MathVerification]
    content_complete:bool
    minimum_density_met:bool
    target_density_met:bool
    unresolved_role_refs:tuple[str,...]
    ready_for_p5c:bool
    ready_for_rendering:Literal[False]=False
