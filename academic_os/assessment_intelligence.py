"""Downstream, deterministic observations. Production entry always refreshes P2A trust."""
from dataclasses import dataclass
import hashlib
import json
from typing import Literal
from .product_models import (ProductModel, TeacherTopicView, AssessmentExample,
    AcademicMeaning, Capability, Curriculum, TrustSummary)
from .product_service import AcademicProductService


class IntelligenceIdentity(ProductModel):
    view_key:str
    view_type:Literal['assessment_intelligence']='assessment_intelligence'
    title:str


class Focus(ProductModel):
    concepts:tuple[AcademicMeaning,...]
    capabilities:tuple[Capability,...]


class ReviewedExample(AssessmentExample):
    ref:str
    epistemic_level:Literal['observed_evidence']='observed_evidence'


class Pattern(ProductModel):
    type:Literal['shared_capability','shared_task_form','distinct_question_wording','shared_marks']
    epistemic_level:Literal['derived_observation']='derived_observation'
    statement:str
    evidence_refs:tuple[str,...]
    evidence_count:int


class EvidenceSummary(ProductModel):
    reviewed_example_count:int
    shared_capability:bool
    shared_task_form:bool
    distinct_question_wording:bool


class Limitation(ProductModel):
    code:str
    message:str


class IntelligenceTrust(ProductModel):
    upstream_teacher_view_validated:Literal[True]=True
    analytics_enabled:Literal[False]=False
    upstream:TrustSummary


class AssessmentIntelligenceView(ProductModel):
    artifact_kind:Literal['assessment_intelligence_read_model']='assessment_intelligence_read_model'
    schema_version:Literal['assessment-intelligence/1']='assessment-intelligence/1'
    upstream_schema_version:Literal['teacher-topic/2']='teacher-topic/2'
    identity:IntelligenceIdentity
    assessment_focus:Focus
    reviewed_examples:tuple[ReviewedExample,...]
    observed_patterns:tuple[Pattern,...]
    evidence_summary:EvidenceSummary
    limitations:tuple[Limitation,...]
    curriculum:Curriculum
    trust_summary:IntelligenceTrust

    def serialize(self):
        return json.dumps(self.model_dump(mode='json'),ensure_ascii=False,sort_keys=True,indent=2)+'\n'


def _example_ref(view,e):
    # Structured assessment coordinates, never wording, marks, labels, or array position.
    if any(x is None or (isinstance(x,str) and not x.strip()) for x in (e.year,e.session,e.paper,e.question_part)):
        raise ValueError('Assessment identity requires year, session, paper and question part')
    coordinates=[view.identity.awarding_body,view.identity.qualification,
        view.identity.specification_code,e.year,e.session,e.paper,e.question_part]
    return 'assessment-example-'+hashlib.sha256(json.dumps(coordinates,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def _derive(upstream):
    """Pure internal transform; a JSON fixture is not an authenticated production input."""
    data=upstream.model_dump(mode='json') if isinstance(upstream,TeacherTopicView) else upstream
    if data.get('schema_version')!='teacher-topic/2':
        raise ValueError('Unsupported upstream schema: expected teacher-topic/2')
    view=TeacherTopicView.model_validate(data)
    trust=view.trust_summary
    if not trust.assessment_evidence_reviewed or not trust.canonical_knowledge_approved:
        raise ValueError('Reviewed evidence and approved knowledge required')
    if trust.reviewed_example_count!=len(view.assessment_evidence):
        raise ValueError('Upstream reviewed evidence count mismatch')
    examples={}
    for e in view.assessment_evidence:
        ref=_example_ref(view,e)
        if ref in examples:raise ValueError('Duplicate or conflicting assessment identity: '+ref)
        payload=e.model_dump();payload['task_form_refs']=tuple(sorted(e.task_form_refs))
        payload['reading_notes']=tuple(sorted(e.reading_notes))
        examples[ref]=ReviewedExample(ref=ref,**payload)
    ordered=tuple(sorted(examples.values(),key=lambda e:(-(e.year or 0),e.ref)))
    refs=tuple(sorted(examples));n=len(refs)
    caps={c.ref:c for c in view.capabilities}
    forms={t.ref:t for c in view.capabilities for t in c.task_forms}
    shared_cap=n>=2 and len({e.capability_ref for e in ordered})==1
    common_forms=set.intersection(*(set(e.task_form_refs) for e in ordered)) if ordered else set()
    shared_form=n>=2 and bool(common_forms)
    distinct=n>=2 and len({' '.join(e.question_wording.split()) for e in ordered})>1
    patterns=[]
    def add(kind,statement):
        patterns.append(Pattern(type=kind,statement=statement,evidence_refs=refs,evidence_count=n))
    if shared_cap:add('shared_capability',f'All {n} reviewed examples assess "{caps[ordered[0].capability_ref].name}".')
    if shared_form:
        for ref in sorted(common_forms):add('shared_task_form',f'All {n} reviewed examples use the task form "{forms[ref].name}".')
    if distinct:add('distinct_question_wording','The reviewed examples have different question wording; no context classification is inferred.')
    if n>=2 and len({e.marks for e in ordered})==1 and ordered[0].marks is not None:
        add('shared_marks',f'All {n} reviewed examples carry {ordered[0].marks} marks.')
    limitations=tuple(Limitation(code=code,message=message) for code,message in (
        ('insufficient_evidence_for_frequency',f'The {n} reviewed examples do not establish assessment frequency.'),
        ('insufficient_evidence_for_typical_marks','These reviewed examples do not establish a typical mark allocation.'),
        ('difficulty_not_calibrated','No calibrated difficulty evidence is available.'),
        ('no_exam_prediction','Reviewed historical evidence does not support prediction of future exam appearance.'),
        ('no_student_error_evidence','No student response evidence supports common-mistake claims.'),
        ('no_context_classification','Question wording comparison does not establish a context taxonomy.'),
    ))
    capabilities=tuple(c.model_copy(update={'concept_refs':tuple(sorted(c.concept_refs)),
        'task_forms':tuple(sorted(c.task_forms,key=lambda t:t.ref))}) for c in sorted(view.capabilities,key=lambda c:c.ref))
    return AssessmentIntelligenceView(identity=IntelligenceIdentity(view_key=view.identity.view_key,title=view.identity.title),
        assessment_focus=Focus(concepts=tuple(sorted(view.concepts,key=lambda c:c.ref)),capabilities=capabilities),
        reviewed_examples=ordered,observed_patterns=tuple(patterns),
        evidence_summary=EvidenceSummary(reviewed_example_count=n,shared_capability=shared_cap,
            shared_task_form=shared_form,distinct_question_wording=distinct),limitations=limitations,
        curriculum=Curriculum(references=tuple(sorted(view.curriculum.references,key=lambda r:(r.section,r.wording,r.association_status,r.association_note)))),
        trust_summary=IntelligenceTrust(upstream=trust))


@dataclass(frozen=True)
class IntelligenceRead:
    view:AssessmentIntelligenceView
    provenance:dict


class AssessmentIntelligenceService:
    def __init__(self,database):self._products=AcademicProductService(database)

    def read_topic(self,topic_key,snapshot_ids):
        upstream=self._products.read_topic(topic_key,snapshot_ids)
        view=_derive(upstream.view)
        traces=upstream.provenance['assessment_examples']
        if len(traces)!=len(upstream.view.assessment_evidence):raise ValueError('Upstream provenance count mismatch')
        provenance=dict(upstream_schema_version=upstream.view.schema_version,upstream=upstream.provenance,
            assessment_examples={_example_ref(upstream.view,e):trace for e,trace in zip(upstream.view.assessment_evidence,traces)},
            patterns=[p.model_dump(mode='json') for p in view.observed_patterns])
        return IntelligenceRead(view,provenance)


def intelligence_text(view):
    lines=[view.identity.title,'Assessment Intelligence','', 'Student capability']
    for c in view.assessment_focus.capabilities:
        lines.append(c.name);lines.extend('Task form: '+t.name for t in c.task_forms)
    lines.extend(['',f'Reviewed examples: {len(view.reviewed_examples)}'])
    for e in view.reviewed_examples:
        lines.extend([f'{e.session} {e.year} — {e.paper} — {e.question_part} — {e.marks} marks',e.question_wording])
        lines.extend('Evidence/source-quality note: '+note for note in e.reading_notes)
    lines.extend(['','Observed across reviewed evidence',*(p.statement for p in view.observed_patterns),
        '', 'Evidence limits',*(l.message for l in view.limitations),'','Curriculum reference'])
    for r in view.curriculum.references:lines.extend([r.section,r.wording,'Association: '+r.association_status,r.association_note])
    lines.extend(['','Trust: reviewed assessment evidence; analytics disabled.',view.trust_summary.upstream.validity_notice])
    return '\n'.join(lines)
