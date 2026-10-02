"""Deterministic design policy from learning roles; no academic content generation."""
import hashlib
import json
from .learning_models import LearningSpecification
from .pedagogical_models import (PedagogicalSpecification,PedagogicalIdentity,TeachingBlock,
    InstructionalContent,Constraint,CoverageMap,SourceLearningContract,EvidenceReference)


def build_pedagogical_specification(learning):
    """Pure transform. Production must obtain current learning through its service."""
    data=learning.model_dump(mode='json') if isinstance(learning,LearningSpecification) else learning
    if data.get('schema_version')!='learning-specification/1':raise ValueError('Unsupported learning schema; expected learning-specification/1')
    source=LearningSpecification.model_validate(data)
    # Collection order is serialization order only, never a mandated lesson sequence.
    source=source.model_copy(update={
        'learning_requirements':tuple(sorted(source.learning_requirements,key=lambda r:r.ref)),
        'coverage_requirements':tuple(sorted(source.coverage_requirements,key=lambda r:r.ref)),
        'evidence_boundaries':tuple(sorted(source.evidence_boundaries,key=lambda r:r.ref)),
        'assessment_evidence':tuple(sorted(source.assessment_evidence,key=lambda r:r.ref)),
        'conceptual_basis':tuple(sorted(source.conceptual_basis,key=lambda r:r.concept_ref)),
    })
    groups={kind:[r for r in source.learning_requirements if r.type==kind] for kind in ('conceptual_understanding','capability','capability_under_task_form')}
    coverage={r.type:r for r in source.coverage_requirements}
    if len(coverage)!=len(source.coverage_requirements):raise ValueError('Ambiguous coverage policy types')
    evidence={e.ref:e for e in source.assessment_evidence}
    boundary_refs=tuple(b.ref for b in source.evidence_boundaries)
    blocks=[];contents=[]
    def identity(prefix,role,refs):
        key=[source.identity.awarding_body,source.identity.qualification,source.identity.specification_code,source.identity.view_key,role,sorted(refs)]
        return prefix+'-'+hashlib.sha256(json.dumps(key,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    def content(kind,requirements,purpose):
        refs=tuple(sorted(r.ref for r in requirements));ev=tuple(sorted({e for r in requirements for e in r.evidence_refs}))
        item=InstructionalContent(ref=identity('ic',kind,refs),type=kind,purpose=purpose,
            supports_learning_requirement_refs=refs,source_product_refs=tuple(sorted({s for r in requirements for s in r.source_refs})),
            evidence_refs=ev,assesses_learning_requirement_refs=refs if kind=='learning_check_slot' else (),
            source_quality_notes=tuple(sorted({note for e in ev for note in evidence[e].reading_notes})))
        contents.append(item);return item.ref
    def block(role,title,purpose,requirements,constraints,slots=(),cr=()):
        refs=tuple(sorted(r.ref for r in requirements))
        blocks.append(TeachingBlock(ref=identity('tb',role,refs),role=role,title=title,purpose=purpose,
            covers_learning_requirement_refs=refs,covers_coverage_requirement_refs=tuple(sorted(cr)),
            constraints=tuple(Constraint(level=level,statement=text) for level,text in constraints),
            instructional_content_refs=tuple(slots),evidence_refs=tuple(sorted({e for r in requirements for e in r.evidence_refs})),boundary_refs=boundary_refs))
    for r in groups['conceptual_understanding']:
        block('conceptual_meaning','Conceptual Meaning','Communicate the cited trusted conceptual meaning.',[r],[
            ('required',r.statement),
            ('recommended','Use a visual comparison to illustrate the cited conceptual meaning; this is teaching advice, not a new academic requirement.'),
            ('flexible','Choose context, numbers, visual representation, diagram style and example dataset while preserving the cited meaning.')])
    for r in groups['capability']:
        slot=content('calculation_method_slot',[r],'Provide a valid instructional method sufficient for the cited capability. Exact method content is not supplied by this deterministic core.')
        block('calculation_method','Calculation Method','Prepare learners to perform the included capability.',[r],[
            ('required','Provide a valid instructional calculation method sufficient for: '+r.statement),
            ('flexible','Choose the method presentation within the evidence boundaries. Neither a specific calculator sequence, manual-only method nor formula memorisation is required.')],[slot])
    for r in groups['capability_under_task_form']:
        if not r.evidence_refs:raise ValueError('Task-form design requires reviewed supporting evidence')
        slot=content('task_input_slot',[r],'Identify the inputs encountered in the supported task form from reviewed evidence. Exact notation is unavailable as structured upstream input; retain source warnings and do not repair glyphs or invent notation.')
        block('supported_task_form','Apply the Supported Task Form','Apply the capability under its evidenced task conditions.',[r],[
            ('required',r.statement),
            ('flexible','Choose how to present task-specific inputs; they are instructional support, not new Learning Requirements or prerequisites.')],[slot])
    application=groups['capability']+groups['capability_under_task_form']
    for policy,role,title,kind,purpose in (
        ('teaching_assessment_connection','worked_assessment_connection','Worked Assessment Connection','worked_example_slot','Provide at least one worked-example design aligned to the declared capability and supported task form, traceable to the reviewed assessment structure.'),
        ('assessment_alignment','practice_learning_check','Practice & Learning Check','learning_check_slot','Provide at least one learning-check design aligned to declared Learning Requirements. Future items must declare assesses_learning_requirement_refs.'),
    ):
        if policy not in coverage:continue
        cr=coverage[policy]
        if policy=='teaching_assessment_connection':
            selected=[r for r in application if r.ref in cr.learning_requirement_refs or set(r.source_refs)<=set(cr.source_refs)]
            if not selected or not any(r.type=='capability_under_task_form' for r in selected):raise ValueError('Assessment connection lacks a supported task requirement')
        else:selected=[r for r in application if r.ref in cr.learning_requirement_refs]
        if not selected:raise ValueError('Coverage policy has no supported learning design')
        slot=content(kind,selected,purpose)
        constraints=[('required',purpose),('required','Preserve alignment to the declared learning and Product refs. Do not silently assess unsupported content.')]
        if policy=='teaching_assessment_connection':
            constraints.extend([('required','Describe an aligned structure; do not require copying a Pearson past-paper question or generate a complete question here.'),
                ('flexible','Future authors may choose original values and context while preserving capability and task alignment.')])
        else:
            constraints.extend([('recommended','Consider progression from supported or guided application toward independent application; no fixed practice sequence is required.'),
                ('flexible','Choose question count, context, practice format, individual or pair work, exit-ticket format and presentation style.')])
        block(role,title,purpose,selected,constraints,[slot],[cr.ref])
    lr_map={r.ref:tuple(sorted(b.ref for b in blocks if r.ref in b.covers_learning_requirement_refs)) for r in source.learning_requirements}
    cr_map={r.ref:tuple(sorted(b.ref for b in blocks if r.ref in b.covers_coverage_requirement_refs)) for r in source.coverage_requirements}
    identity_data=source.identity.model_dump();identity_data['view_type']='pedagogical_specification'
    source_view=SourceLearningContract(identity=source.identity,conceptual_basis=source.conceptual_basis,
        learning_requirements=source.learning_requirements,coverage_requirements=source.coverage_requirements,
        evidence_boundaries=source.evidence_boundaries,assessment_evidence=tuple(EvidenceReference(**e.model_dump(include=set(EvidenceReference.model_fields))) for e in source.assessment_evidence))
    return PedagogicalSpecification(identity=PedagogicalIdentity(**identity_data),source_learning_specification=source_view,
        teaching_blocks=tuple(blocks),instructional_content=tuple(contents),coverage_map=CoverageMap(learning_requirements=lr_map,coverage_requirements=cr_map),
        evidence_boundaries=source.evidence_boundaries,generator_constraints=(
            Constraint(level='required',statement='Preserve academic meaning, all included learning/coverage requirements and evidence boundaries. Instructional support must not become academic truth, new learning requirements or assessment evidence.'),
            Constraint(level='required',statement='This is planned coverage only; unresolved content slots do not prove a complete or sufficient lesson.'),
            Constraint(level='recommended',statement='Use coherent method presentation, aligned worked-example structures and supported-to-independent practice where useful.'),
            Constraint(level='flexible',statement='Choose contexts, values, visual styles, slide layout and practice format within the required boundaries; block order is not a mandatory teaching sequence.'),
        ),trust_boundary='Pedagogical candidate only, not academic approval, curriculum truth, a validated lesson or validated coverage. Refresh upstream trust before use; no new academic decision is created.')
