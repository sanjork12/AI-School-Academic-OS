"""Product/pedagogical planning contracts; neither academic truth nor content."""
import json
from typing import Literal
from pydantic import Field,model_validator
from .product_models import ProductModel
from .learning_models import EvidenceBoundary

ProfileKey=Literal['focused-review','standard-lesson']
RoleKind=Literal['orientation','concept_explanation','concept_visual','early_concept_retrieval','calculation_method','mini_worked_example','summary_method','full_worked_examples','guided_practice','independent_practice','concept_check','calculation_check','exit_check']

class Contract(ProductModel):
    def serialize(self):return json.dumps(self.model_dump(mode='json'),ensure_ascii=False,sort_keys=True,indent=2)+'\n'

class Count(ProductModel):
    minimum:int=Field(ge=0,strict=True)
    target:int=Field(ge=0,strict=True)
    @model_validator(mode='after')
    def ordered(self):
        if self.target<self.minimum:raise ValueError('Target cannot be below minimum')
        return self

class MinuteRange(ProductModel):
    min:int=Field(gt=0,strict=True)
    max:int=Field(gt=0,strict=True)
    @model_validator(mode='after')
    def ordered(self):
        if self.max<self.min:raise ValueError('Invalid minute range')
        return self

class Duration(ProductModel):
    target_minutes:int=Field(gt=0,strict=True)
    acceptable_range_minutes:MinuteRange
    interpretation:Literal['planning_target_not_runtime_guarantee']='planning_target_not_runtime_guarantee'
    @model_validator(mode='after')
    def within_range(self):
        if not self.acceptable_range_minutes.min<=self.target_minutes<=self.acceptable_range_minutes.max:raise ValueError('Duration target outside acceptable range')
        return self

class ProfileIdentity(ProductModel):
    profile_key:ProfileKey
    profile_type:Literal['lesson_purpose_density']='lesson_purpose_density'
    title:str

class DensityPolicy(ProductModel):
    concept_explanation:Count
    concept_visual:Count
    early_concept_retrieval:Count
    calculation_method:Count
    mini_worked_example:Count
    summary_method:Count
    full_worked_examples:Count
    guided_practice:Count
    independent_practice:Count
    concept_check:Count
    calculation_check:Count
    exit_check:Count

class PracticePolicy(ProductModel):
    support_modes:tuple[Literal['guided','independent'],...]
    support_is_not_difficulty:Literal[True]=True
    learner_ability_not_inferred:Literal[True]=True

class AssessmentPolicy(ProductModel):
    exit_check_required:bool
    only_existing_learning_requirements:Literal[True]=True

class RendererPolicy(ProductModel):
    duration_to_slide_count:Literal['prohibited']='prohibited'
    content_then_manifest_then_rendering:Literal[True]=True

class TimePhase(ProductModel):
    key:str
    title:str
    suggested_range_minutes:MinuteRange

class TimePlan(ProductModel):
    interpretation:Literal['suggestions_not_additive_schedule']='suggestions_not_additive_schedule'
    sequence_basis:Literal['chosen_pedagogical_design_not_trusted_academic_sequence']='chosen_pedagogical_design_not_trusted_academic_sequence'
    phases:tuple[TimePhase,...]

class LessonProfile(Contract):
    schema_version:Literal['lesson-profile/1']='lesson-profile/1'
    identity:ProfileIdentity
    configuration_basis:Literal['user_specified_gold_product_configuration']='user_specified_gold_product_configuration'
    duration:Duration
    purpose:str
    academic_scope_policy:Literal['preserve_learning_specification']='preserve_learning_specification'
    density_policy:DensityPolicy
    practice_policy:PracticePolicy
    assessment_policy:AssessmentPolicy
    prerequisite_policy:Literal['not_asserted']='not_asserted'
    difficulty_policy:Literal['not_asserted']='not_asserted'
    learner_history_policy:Literal['not_asserted']='not_asserted'
    renderer_policy:RendererPolicy=RendererPolicy()
    time_plan:TimePlan

class SourceBinding(ProductModel):
    schema_version:str
    ref:str
    sha256:str=Field(pattern=r'^[0-9a-f]{64}$')

class ProfiledIdentity(ProductModel):
    ref:str
    topic_key:Literal['standard-deviation']='standard-deviation'
    profile_key:ProfileKey
    title:str

class ProfiledRole(ProductModel):
    ref:str
    role_key:str
    kind:RoleKind
    title:str
    phase:Literal['orientation','concept_development','calculation_development','supported_task_form','supported_practice','independent_application','check_and_closure']
    origin:Literal['base_pedagogy','profile_density_expansion']
    base_teaching_block_ref:str|None
    learning_requirement_refs:tuple[str,...]
    assesses_learning_requirement_refs:tuple[str,...]=()
    coverage_requirement_refs:tuple[str,...]=()
    profile_reason:str
    support_mode:Literal['not_applicable','guided','independent']='not_applicable'
    substantive:bool=True
    items:Count

class AuthoringRequirement(ProductModel):
    ref:str
    role_ref:str
    status:Literal['unpopulated']='unpopulated'
    content_kind:RoleKind
    items:Count
    learning_requirement_refs:tuple[str,...]
    coverage_requirement_refs:tuple[str,...]
    reuse_hint:Literal['potential_existing_p4a','new_authoring_required']
    additional_target_items:int=Field(ge=0,strict=True)
    reuse_is_not_validated:Literal[True]=True

class ScopeValidation(ProductModel):
    policy:Literal['preserve_learning_specification']='preserve_learning_specification'
    same_learning_requirement_identity:Literal[True]=True
    same_coverage_requirement_identity:Literal[True]=True
    same_evidence_boundaries:Literal[True]=True
    academic_scope_expanded:Literal[False]=False
    coverage_status:Literal['planned_only']='planned_only'
    ready_as_authored_content:Literal[False]=False
    ready_for_rendering:Literal[False]=False

class ProfiledPedagogicalSpecification(Contract):
    schema_version:Literal['profiled-pedagogical-specification/1']='profiled-pedagogical-specification/1'
    identity:ProfiledIdentity
    lesson_profile:SourceBinding
    source_learning_specification:SourceBinding
    source_base_pedagogy:SourceBinding
    academic_scope_fingerprint:str=Field(pattern=r'^[0-9a-f]{64}$')
    learning_requirement_refs:tuple[str,...]
    coverage_requirement_refs:tuple[str,...]
    profiled_roles:tuple[ProfiledRole,...]
    density_summary:DensityPolicy
    time_plan:TimePlan
    evidence_boundaries:tuple[EvidenceBoundary,...]
    scope_validation:ScopeValidation=ScopeValidation()
    authoring_requirements:tuple[AuthoringRequirement,...]

class ProfileValidation(Contract):
    schema_version:Literal['profiled-pedagogical-validation/1']='profiled-pedagogical-validation/1'
    valid:bool
    violations:tuple[str,...]
    ready_for_content_authoring:bool
    ready_as_authored_content:Literal[False]=False
    ready_for_rendering:Literal[False]=False
