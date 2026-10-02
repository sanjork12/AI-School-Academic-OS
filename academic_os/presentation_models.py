"""Presentation references and layout only; never a second academic content store."""
import json
from typing import Literal
from .product_models import ProductModel


class ManifestSlide(ProductModel):
    ref:str
    slide_number:int
    slide_type:str
    title:str
    content_refs:tuple[str,...]
    learning_requirement_refs:tuple[str,...]
    student_visible:Literal[True]=True
    teacher_only_refs:tuple[str,...]=()
    layout_intent:str
    visual_refs:tuple[str,...]=()
    notes_refs:tuple[str,...]=()


class PresentationManifest(ProductModel):
    schema_version:Literal['presentation-manifest/1']='presentation-manifest/1'
    identity:dict
    artifact_type:Literal['student_classroom_pptx']='student_classroom_pptx'
    audience:Literal['UK A Level Mathematics students']='UK A Level Mathematics students'
    language:Literal['English']='English'
    aspect_ratio:Literal['16:9']='16:9'
    slides:tuple[ManifestSlide,...]
    content_coverage:dict[str,tuple[str,...]]
    solution_visibility:dict[str,str]
    render_constraints:tuple[str,...]
    source_validation:dict[str,str]

    def serialize(self):return json.dumps(self.model_dump(mode='json'),sort_keys=True,ensure_ascii=False,indent=2)+'\n'


class ArtifactRenderValidation(ProductModel):
    schema_version:Literal['artifact-render-validation/1']='artifact-render-validation/1'
    valid:bool
    checks:dict[str,bool]
    violations:tuple[str,...]
    warnings:tuple[str,...]
    artifact_sha256:str
    manifest_sha256:str
    authored_content_sha256:str
    slide_count:int
    content_coverage:dict[str,tuple[str,...]]
    learning_requirement_refs:tuple[str,...]

    def serialize(self):return json.dumps(self.model_dump(mode='json'),sort_keys=True,ensure_ascii=False,indent=2)+'\n'
