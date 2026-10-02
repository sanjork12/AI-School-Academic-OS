"""Closed symbolic content; no numerical candidate or exam-bank dependencies."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from academic_os.governed_pedagogy.models import GovernedPedagogicalSpecification
from academic_os.governed_learning.models import SourceObjective,CanonicalSemantic,LearningIntention
from academic_os.pedagogy_evidence.models import Criterion,Activity,Check
from academic_os.curriculum_ingestion.models import Warning

class Model(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,revalidate_instances='always')

Family=Literal['REPRESENTATION','CONCEPT_CHECK']
Symbol=Literal['>','<','≥','≤']
Meaning=Literal['GREATER_THAN','LESS_THAN','GREATER_THAN_OR_EQUAL_TO','LESS_THAN_OR_EQUAL_TO']
Origin=Literal['OFFLINE_FIXTURE_CONTENT','MODEL_AUTHORED_CONTENT']

class Binding(Model):
    role_id:str
    role_family:Family
    source_id:str
    tier:str
    pedagogical_spec_hash:str
    learning_spec_hash:str
    approved_pack_id:str
    approved_pack_hash:str
    proposal_hash:str
    review_hash:str
    contract_version:str
    mapping_policy:Literal['bounded-symbol-role-mapping/1']='bounded-symbol-role-mapping/1'

class Brief(Model):
    schema_version:Literal['generic-role-authoring-brief/1']='generic-role-authoring-brief/1'
    binding:Binding
    governed_spec:GovernedPedagogicalSpecification
    source_context:SourceObjective
    reviewed_canonical:CanonicalSemantic
    learning_intention:LearningIntention
    success_criteria:list[Criterion]
    activity_constraints:list[Activity]
    check_alignments:list[Check]
    allowed_modes:list[str]
    prohibited_content:list[str]
    semantic_policy:Literal['reviewed-inequality-symbol-semantics/1']='reviewed-inequality-symbol-semantics/1'
    validation_policy:Literal['generic-symbolic-role-validation/1']='generic-symbolic-role-validation/1'
    warnings:list[Warning]
    provenance:dict[str,str]

class Alignment(Model):
    intention_id:str
    criterion_id:str
    activity_id:str
    check_id:str

class RepresentationContent(Model):
    instruction:Literal['Interpret the displayed inequality symbol.']
    symbol:Symbol
    response_mode:Literal['SYMBOL_INTERPRETATION']
    expected_meaning:Meaning

class ConceptCheckContent(Model):
    instruction:Literal['Select the symbol matching the stated meaning.']
    stated_meaning:Meaning
    choices:list[Symbol]=Field(min_length=2,max_length=4)
    response_mode:Literal['SYMBOL_SELECTION']
    expected_symbol:Symbol

class CandidateBase(Model):
    binding:Binding
    brief_hash:str
    alignment:Alignment
    status:Literal['PROPOSED']='PROPOSED'
    scope:Literal['REVIEWED_INEQUALITY_SYMBOLS_ONLY']='REVIEWED_INEQUALITY_SYMBOLS_ONLY'
    content_origin:Origin
    field_provenance:dict[str,Origin]

class RepresentationCandidate(CandidateBase):
    schema_version:Literal['representation-role-candidate/1']='representation-role-candidate/1'
    content:RepresentationContent

class ConceptCheckCandidate(CandidateBase):
    schema_version:Literal['concept-check-role-candidate/1']='concept-check-role-candidate/1'
    content:ConceptCheckContent

class Validation(Model):
    schema_version:Literal['generic-role-validation/1']='generic-role-validation/1'
    policy_version:Literal['generic-symbolic-role-validation/1']='generic-symbolic-role-validation/1'
    valid:bool
    errors:list[str]
    candidate_hash:str
    brief_hash:str
    checks:dict[str,bool]
    provenance:Literal['DETERMINISTIC_VALIDATION']='DETERMINISTIC_VALIDATION'
    pedagogically_approved:Literal[False]=False
    publishable:Literal[False]=False

class AuthoredRoleContent(Model):
    schema_version:Literal['authored-generic-role-content/1']='authored-generic-role-content/1'
    composition_version:Literal['bounded-symbol-role-composition/1']='bounded-symbol-role-composition/1'
    binding:Binding
    candidate_hash:str
    validation_hash:str
    brief_hash:str
    candidate:RepresentationCandidate|ConceptCheckCandidate
    student_content:dict
    teacher_validation:dict
    lineage:dict[str,str]
    status:Literal['VALIDATED_ROLE_CONTENT_NOT_A_LESSON']='VALIDATED_ROLE_CONTENT_NOT_A_LESSON'
    published:Literal[False]=False
    human_approved:Literal[False]=False
    renderer_ready:Literal[False]=False
