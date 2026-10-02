"""Structured deterministic scope; never an authored teaching candidate."""
from typing import Literal
from .models import Model
from academic_os.governed_learning.models import SourceObjective,CanonicalSemantic,LearningIntention
from academic_os.pedagogy_evidence.models import Criterion
from academic_os.curriculum_ingestion.models import Warning

Origin=Literal['SOURCE_BOUND_CONTEXT','REVIEWED_CANONICAL_SEMANTIC','GOVERNED_LEARNING_SPEC','APPROVED_PEDAGOGICAL_EVIDENCE','DETERMINISTIC_POLICY']

class ScopeBinding(Model):
    source_id:str
    tier:str
    learning_spec_id:str
    learning_spec_hash:str
    pedagogical_spec_id:str
    pedagogical_spec_hash:str
    approved_pack_id:str
    approved_pack_hash:str

class IncludedCapability(Model):
    criterion:Criterion
    statement:str
    provenance:Literal['APPROVED_PEDAGOGICAL_EVIDENCE']='APPROVED_PEDAGOGICAL_EVIDENCE'

class ExcludedCapability(Model):
    capability:str
    status:Literal['OUTSIDE_SELECTED_OBJECTIVE_SCOPE']='OUTSIDE_SELECTED_OBJECTIVE_SCOPE'
    policy_ref:str
    provenance:Literal['DETERMINISTIC_POLICY']='DETERMINISTIC_POLICY'

class ScopeFraming(Model):
    schema_version:Literal['scope-framing/1']='scope-framing/1'
    construction_version:Literal['bounded-scope-framing/1']='bounded-scope-framing/1'
    disposition:Literal['DETERMINISTIC_FRAMING']='DETERMINISTIC_FRAMING'
    identity:str
    binding:ScopeBinding
    source_context:SourceObjective
    reviewed_canonical:CanonicalSemantic
    learning_intention:LearningIntention
    included_capabilities:list[IncludedCapability]
    excluded_capabilities:list[ExcludedCapability]
    required_role_families:list[str]
    lesson_scope_statement:str
    warnings:list[Warning]
    provenance:dict[str,list[Origin]]
    human_approved:Literal[False]=False
    published:Literal[False]=False
    model_calls:Literal[0]=0
