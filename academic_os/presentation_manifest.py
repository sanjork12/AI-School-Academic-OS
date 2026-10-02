"""Deterministic Standard deviation presentation adapter; no new teaching content."""
import hashlib
from .authored_models import AuthoredTeachingPackage
from .content_validation_models import AuthoredContentValidationReport
from .learning_models import LearningSpecification
from .presentation_models import PresentationManifest,ManifestSlide


def sha(model):return hashlib.sha256(model.serialize().encode()).hexdigest()


def gate(authored,validation,learning):
    a=AuthoredTeachingPackage.model_validate(authored.model_dump() if isinstance(authored,AuthoredTeachingPackage) else authored)
    v=AuthoredContentValidationReport.model_validate(validation.model_dump() if isinstance(validation,AuthoredContentValidationReport) else validation)
    l=LearningSpecification.model_validate(learning)
    dimensions=('reference_integrity','content_completeness','mathematical_integrity','learning_alignment','coverage_requirement_validation','boundary_compliance')
    if not v.renderer_readiness.ready_for_rendering or v.violations or not all(getattr(v,d).valid for d in dimensions):raise ValueError('P4B rendering gate is closed')
    if v.input_contracts.get('authored-teaching-content/1')!=sha(a) or v.input_contracts.get('learning-specification/1')!=sha(l):raise ValueError('P4B report does not bind these content versions')
    if a.identity.view_key!='standard-deviation' or l.identity.view_key!=a.identity.view_key:raise ValueError('Unsupported presentation profile')
    return a,v,l


PROFILES=('standard-deviation-classroom/1','standard-deviation-classroom/2')

def build_manifest(authored,validation,learning,profile=PROFILES[0]):
    if profile not in PROFILES:raise ValueError('Unsupported presentation design profile')
    a,v,l=gate(authored,validation,learning)
    blocks={}
    for b in a.content_blocks:blocks.setdefault(b.kind,[]).append(b)
    requirements={r.ref:r for r in l.learning_requirements}
    items={q.ref:q for q in (*a.worked_examples,*a.practice_items,*a.learning_checks)}
    solutions={s.item_ref:s for s in a.solutions}
    def one(kind):
        values=blocks.get(kind,[])
        if len(values)!=1:raise ValueError('11-slide profile requires exactly one '+kind+' block; no content will be invented')
        return values[0]
    practice=sorted(blocks.get('practice_item',[]),key=lambda b:b.ref)
    if len(practice)!=2:raise ValueError('11-slide profile requires exactly two authored practice items')
    mapping=[('concept','What is standard deviation?',one('concept_explanation')),
        ('visual_comparison','Same mean, different spread',one('visual_comparison')),
        ('calculation_method','How standard deviation works',one('calculation_method')),
        ('task_form_method','From summary statistics',one('summary_statistics_method')),
        ('worked_example','Worked example',one('worked_example')),
        ('student_practice','Practice 1',practice[0]),('student_practice','Practice 2',practice[1]),
        ('concept_check','Concept check',one('concept_check')),('calculation_check','Calculation check',one('calculation_check'))]
    slides=[ManifestSlide(ref='slide-01',slide_number=1,slide_type='title_learning_goals',title='Standard Deviation',content_refs=(),learning_requirement_refs=tuple(sorted(requirements)),layout_intent='title_and_three_goals')]
    visibility={}
    for i,(kind,title,b) in enumerate(mapping,2):
        visible=[b.ref,*b.formula_refs];teacher=[]
        if b.item_ref:
            q=items[b.item_ref];visible.append(q.ref);solution=solutions[q.ref]
            if kind=='worked_example':
                visible.extend((*one('summary_statistics_method').formula_refs,solution.ref));visibility[solution.ref]='student_worked_example'
            else:teacher.append(solution.ref);visibility[solution.ref]='teacher_sidecar_only'
        slides.append(ManifestSlide(ref=f'slide-{i:02}',slide_number=i,slide_type=kind,title=title,
            content_refs=tuple(visible),learning_requirement_refs=tuple(sorted(set(b.covers_learning_requirement_refs+b.assesses_learning_requirement_refs))),
            teacher_only_refs=tuple(teacher),layout_intent=kind,visual_refs=(b.ref,) if b.visual else ()))
    slides.append(ManifestSlide(ref='slide-11',slide_number=11,slide_type='learning_summary',title='Summary',content_refs=(),learning_requirement_refs=tuple(sorted(requirements)),layout_intent='three_goals_and_attribution'))
    coverage={o.ref:tuple(s.ref for s in slides if o.ref in s.content_refs+s.teacher_only_refs) for o in (*a.content_blocks,*a.instructional_formulas,*a.worked_examples,*a.practice_items,*a.learning_checks,*a.solutions)}
    if any(not s for s in coverage.values()):raise ValueError('Presentation profile cannot map all authored objects')
    if profile==PROFILES[1]:
        slides=[s.model_copy(update={'layout_intent':'classroom-v2/'+s.slide_type}) for s in slides]
    return PresentationManifest(identity=dict(topic_key=a.identity.view_key,title=a.identity.title,profile=profile),
        slides=tuple(slides),content_coverage=coverage,solution_visibility=visibility,
        render_constraints=('No new academic content.','Use validated values and formula ASTs.','Keep practice/check solutions outside the PPTX.',
            'Use editable text, mathematical notation and data marks.','No official branding or endorsement.','Renderer eligibility is not academic publication.'),
        source_validation={'authored_content_sha256':sha(a),'content_validation_sha256':sha(v),'learning_specification_sha256':sha(l)})


def validate_manifest(manifest,authored,validation,learning):
    try:
        supplied=PresentationManifest.model_validate(manifest.model_dump() if isinstance(manifest,PresentationManifest) else manifest)
        expected=build_manifest(authored,validation,learning,supplied.identity.get('profile'))
        if supplied!=expected:return ('Manifest differs from the deterministic validated content mapping, order, visibility or version binding.',)
        return ()
    except (ValueError,TypeError,KeyError) as exc:return (str(exc),)
