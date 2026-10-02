"""Teacher API v2. Product references are separate from academic identities."""
import json
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator


class ProductModel(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)


class TopicIdentity(ProductModel):
    view_key:str
    view_type:Literal['knowledge_topic']='knowledge_topic'
    title:str
    subject:str
    qualification:str
    awarding_body:str
    specification_code:str
    curriculum_section:str


class AcademicMeaning(ProductModel):
    ref:str
    name:str
    description:str


class CurriculumWording(ProductModel):
    section:str
    wording:str
    association_status:Literal['candidate','unavailable']
    association_note:str


class Curriculum(ProductModel):
    references:tuple[CurriculumWording,...]


class Capability(AcademicMeaning):
    concept_refs:tuple[str,...]
    task_forms:tuple[AcademicMeaning,...]


class AssessmentExample(ProductModel):
    assessment_label:str
    session:str | None
    year:int | None
    paper:str | None
    question_part:str
    question_wording:str
    marks:int | None
    capability_ref:str
    task_form_refs:tuple[str,...]
    reading_notes:tuple[str,...]=Field(description='Evidence extraction/source-quality notes, not teaching content or common mistakes.')


class TrustSummary(ProductModel):
    curriculum_verified:bool
    curriculum_association_confirmed:bool
    canonical_knowledge_approved:bool
    assessment_evidence_reviewed:bool
    source_count:int
    reviewed_example_count:int
    scope_note:str
    validity_notice:str='Checked for this read only. A saved product view is not a trusted snapshot; refresh through the product service before use.'


class TeacherTopicView(ProductModel):
    artifact_kind:Literal['teacher_product_read_model']='teacher_product_read_model'
    schema_version:Literal['teacher-topic/2']='teacher-topic/2'
    identity:TopicIdentity
    concepts:tuple[AcademicMeaning,...]
    capabilities:tuple[Capability,...]
    curriculum:Curriculum
    assessment_evidence:tuple[AssessmentExample,...]
    trust_summary:TrustSummary

    @model_validator(mode='after')
    def relationships(self):
        concepts={c.ref for c in self.concepts}
        capabilities={c.ref:c for c in self.capabilities}
        refs=[c.ref for c in self.concepts]+[c.ref for c in self.capabilities]+[t.ref for c in self.capabilities for t in c.task_forms]
        if len(refs)!=len(set(refs)) or any(not r.strip() for r in refs):
            raise ValueError('Product entity refs must be nonempty and unique within the view')
        for c in self.capabilities:
            if len(c.concept_refs)!=len(set(c.concept_refs)) or not set(c.concept_refs)<=concepts:
                raise ValueError('Capability concept refs must resolve uniquely')
        for e in self.assessment_evidence:
            if e.capability_ref not in capabilities:raise ValueError('Unknown evidence capability_ref')
            allowed={t.ref for t in capabilities[e.capability_ref].task_forms}
            if len(e.task_form_refs)!=len(set(e.task_form_refs)) or not set(e.task_form_refs)<=allowed:
                raise ValueError('Evidence task refs must belong to its capability')
        return self

    def serialize(self):
        return json.dumps(self.model_dump(mode='json'),ensure_ascii=False,sort_keys=True,indent=2)+'\n'
