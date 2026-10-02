"""Role-based WHAT contract projection. No files, database, oracle, or model calls."""
import hashlib
import json
from .product_models import TeacherTopicView
from .assessment_intelligence import AssessmentIntelligenceView,_derive as derive_assessment
from .learning_models import (LearningSpecification,LearningIdentity,ConceptualBasis,
    LearningRequirement,CoverageRequirement,EvidenceBoundary)


def _identity(view,prefix,kind,source_refs):
    i=view.identity
    key=[i.awarding_body,i.qualification,i.specification_code,i.view_key,kind,sorted(source_refs)]
    return prefix+'-'+hashlib.sha256(json.dumps(key,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def build_learning_specification(teacher,assessment):
    """Pure transform of a validated pair; this function alone does not authenticate JSON."""
    teacher=teacher.model_dump(mode='json') if isinstance(teacher,TeacherTopicView) else teacher
    assessment=assessment.model_dump(mode='json') if isinstance(assessment,AssessmentIntelligenceView) else assessment
    if teacher.get('schema_version')!='teacher-topic/2':raise ValueError('Unsupported teacher schema; expected teacher-topic/2')
    if assessment.get('schema_version')!='assessment-intelligence/1':raise ValueError('Unsupported assessment schema; expected assessment-intelligence/1')
    teacher=TeacherTopicView.model_validate(teacher)
    assessment=AssessmentIntelligenceView.model_validate(assessment)
    # Reuse P2B's rules to check that both contracts describe exactly the same read.
    # P2B deterministically normalizes input ordering; no snapshot logic is repeated.
    expected=derive_assessment(teacher)
    def unordered(value):
        # Frozen P2B collections carry no pedagogical sequence. Preserve duplicates.
        if isinstance(value,dict):return {k:unordered(v) for k,v in value.items()}
        if isinstance(value,list):return sorted((unordered(v) for v in value),key=lambda v:json.dumps(v,sort_keys=True))
        return value
    if unordered(assessment.model_dump(mode='json'))!=unordered(expected.model_dump(mode='json')):
        raise ValueError('Upstream contracts disagree; refresh both from the same trusted inputs')
    assessment=expected
    learning=[]
    evidence=assessment.reviewed_examples
    def add(kind,statement,refs,examples=()):
        learning.append(LearningRequirement(ref=_identity(teacher,'lr',kind,refs),type=kind,statement=statement,
            source_refs=tuple(sorted(refs)),evidence_refs=tuple(sorted(examples)),
            scope_note='Only the cited Product meaning is required; no method, prerequisite, formula or teaching sequence is inferred.'))
    for concept in sorted(teacher.concepts,key=lambda c:c.ref):
        if not concept.description.strip():raise ValueError('Conceptual meaning is unavailable: '+concept.ref)
        add('conceptual_understanding',f'Student should understand "{concept.name}": {concept.description}',(concept.ref,))
    for capability in sorted(teacher.capabilities,key=lambda c:c.ref):
        if not capability.description.strip():raise ValueError('Capability meaning is unavailable: '+capability.ref)
        supporting=tuple(e.ref for e in evidence if e.capability_ref==capability.ref)
        add('capability',f'Student should be able to: {capability.description}',(capability.ref,),supporting)
        for task in sorted(capability.task_forms,key=lambda t:t.ref):
            matches=tuple(e.ref for e in evidence if e.capability_ref==capability.ref and task.ref in e.task_form_refs)
            # An unassessed task form is not promoted into an evidence-backed task requirement.
            if not matches:continue
            if not task.description.strip():raise ValueError('Task-form meaning is unavailable: '+task.ref)
            add('capability_under_task_form',f'Student should be able to: {capability.description} Under the task form "{task.name}": {task.description}',
                (capability.ref,task.ref),matches)
    coverage=[]
    tasked=[r for r in learning if r.type=='capability_under_task_form']
    def cover(kind,statement,requirements):
        refs=tuple(sorted({s for r in requirements for s in r.source_refs}))
        coverage.append(CoverageRequirement(ref=_identity(teacher,'cr',kind,refs),type=kind,statement=statement,
            learning_requirement_refs=tuple(sorted(r.ref for r in requirements)),source_refs=refs,
            evidence_refs=tuple(sorted({e for r in requirements for e in r.evidence_refs}))))
    if tasked:cover('teaching_assessment_connection',
        'Teaching material should provide an assessment connection aligned to the supported capability and task form. Copying a past-paper question is not required.',tasked)
    if learning:cover('assessment_alignment',
        'Assessment material must declare which included Learning Requirements it assesses; unsupported content must not silently be labelled as covered.',learning)
    boundaries=[]
    limits={l.code:l.message for l in assessment.limitations}
    def boundary(code,message,basis,refs):
        boundaries.append(EvidenceBoundary(ref=_identity(teacher,'eb',code,refs),code=code,statement=message,basis=basis,source_refs=refs))
    for code in ('insufficient_evidence_for_frequency','insufficient_evidence_for_typical_marks','difficulty_not_calibrated','no_exam_prediction','no_student_error_evidence'):
        if code not in limits:raise ValueError('Required upstream limitation unavailable: '+code)
        boundary(code,limits[code],'upstream_limitation',('assessment-intelligence/1:limitations/'+code,))
    for code,message in (
        ('prerequisites_not_modelled','Prerequisite knowledge has not yet been modelled by these contracts.'),
        ('teaching_sequence_not_established','Teaching sequence has not yet been established by these contracts.'),
        ('calculator_method_not_established','A required calculator or manual method has not been established.'),
        ('formula_memorisation_not_established','Formula knowledge or memorisation requirements have not been established by the current trusted Product Contracts.'),
        ('unsupported_task_forms_excluded','This Learning Specification includes only its explicitly supported task forms, not every possible task form for the topic.'),
    ):boundary(code,message,'contract_scope',('teacher-topic/2','assessment-intelligence/1'))
    identity=teacher.identity.model_dump();identity['view_type']='learning_specification'
    return LearningSpecification(identity=LearningIdentity(**identity),source_contracts=('teacher-topic/2','assessment-intelligence/1'),
        conceptual_basis=tuple(ConceptualBasis(concept_ref=c.ref,name=c.name,description=c.description) for c in sorted(teacher.concepts,key=lambda c:c.ref)),
        learning_requirements=tuple(learning),coverage_requirements=tuple(coverage),assessment_evidence=evidence,
        evidence_boundaries=tuple(boundaries),curriculum=assessment.curriculum,trust_summary=assessment.trust_summary)
