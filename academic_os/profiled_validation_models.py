"""Profile composition validation report; not academic approval or quality scoring."""
from typing import Literal
from .lesson_profile_models import Contract
from .product_models import ProductModel

class Finding(ProductModel):
    severity:Literal['ERROR','WARNING','INFO']
    code:str
    ref:str
    message:str
    dimension:str

class Dimension(ProductModel):
    valid:bool

class RolePopulation(Dimension):
    required:int
    populated:int

class DensityValidation(Dimension):
    minimum_compliance:bool
    target_attainment:bool
    policy:Literal['minimum_required_target_preferred']='minimum_required_target_preferred'

class Readiness(ProductModel):
    ready_for_rendering:bool
    blocking_codes:tuple[str,...]
    target_attainment:bool

class CoverageRow(ProductModel):
    profiled_role_ref:str
    role_key:str
    decision:str
    content_refs:tuple[str,...]
    learning_requirement_refs:tuple[str,...]
    coverage_requirement_refs:tuple[str,...]
    support_mode:str
    minimum_requirement:int
    target_requirement:int
    actual_valid_content_count:int
    minimum_compliance:bool
    target_attainment:bool
    status:Literal['populated','underpopulated','unresolved','invalid']
    framing:bool=False

class DensityRow(ProductModel):
    kind:str
    minimum:int
    target:int
    actual_valid_content_count:int
    minimum_compliance:bool
    target_attainment:bool

class LearningCoverage(ProductModel):
    learning_requirement_ref:str
    teaching_coverage:tuple[str,...]
    assessment_check_coverage:tuple[str,...]
    reused_content_refs:tuple[str,...]
    new_content_refs:tuple[str,...]

class UnresolvedRole(ProductModel):
    role_ref:str
    reason:str
    missing_compatibility_dimensions:tuple[str,...]

class ProfiledContentValidationReport(Contract):
    schema_version:Literal['profiled-content-validation/1']='profiled-content-validation/1'
    identity:dict[str,str]
    lesson_profile:str
    input_contracts:dict[str,str]
    profile_structure:Dimension
    role_population:RolePopulation
    density_validation:DensityValidation
    reuse_integrity:Dimension
    new_content_integrity:Dimension
    composite_role_validation:Dimension
    academic_scope_validation:Dimension
    boundary_compliance:Dimension
    unresolved_validation:Dimension
    renderer_readiness:Readiness
    violations:tuple[Finding,...]
    warnings:tuple[Finding,...]
    coverage_matrix:tuple[CoverageRow,...]
    density_summary:tuple[DensityRow,...]
    learning_requirement_coverage:tuple[LearningCoverage,...]
    coverage_requirement_coverage:dict[str,tuple[str,...]]
    unresolved_roles:tuple[UnresolvedRole,...]
    mathematical_verification:dict
    trust_summary:dict
