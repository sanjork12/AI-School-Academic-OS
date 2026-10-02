"""Explicit Standard deviation v1 authoring provider, NOT generic academic inference.

Content choices are authored here. Acceptance fixtures are never read.
"""
import hashlib
from .authored_models import (AuthoredTeachingPackage,AuthoredIdentity,ContentBlock,InstructionalFormula,
    QuestionItem,Solution,SummaryStatistics,VisualData,SourcePedagogy,VerificationSummary,SlotPopulation)
from .authored_math import (raw_stats,summary_stats,display,question_text,solution_steps,visual_brief,
    verify_solution,verify_visual,verify_formula,render_expression)
from .authored_verification import verify_package_math
from .pedagogical_models import PedagogicalSpecification
from .pedagogical_validation import PedagogicalValidationReport

PROVIDER_ID='standard-deviation-population/v1'


def author_standard_deviation(pedagogy,validation):
    pedagogy=PedagogicalSpecification.model_validate(pedagogy)
    validation=PedagogicalValidationReport.model_validate(validation)
    if (not validation.authoring_readiness.ready_for_content_authoring or validation.violations or
        not all(c.valid for c in (validation.structural_coverage,validation.reference_integrity,validation.boundary_validation,validation.slot_validation))):
        raise ValueError('P3C authoring gate is closed')
    source=pedagogy.source_learning_specification
    if source.identity.view_key!='standard-deviation':raise ValueError('This explicit provider supports Standard deviation only')
    if any(validation.identity.get(k)!=getattr(source.identity,k) for k in ('view_key','awarding_body','qualification','specification_code')):
        raise ValueError('P3C identity does not match authoring input')
    expected_lr={r.ref for r in source.learning_requirements}
    if {r.requirement_ref for r in validation.coverage_matrix if r.kind=='learning_requirement'}!=expected_lr:
        raise ValueError('P3C coverage does not match authoring input')
    def one(rows,predicate,label):
        values=[r for r in rows if predicate(r)]
        if len(values)!=1:raise ValueError('Provider requires exactly one '+label)
        return values[0]
    conceptual=one(source.learning_requirements,lambda r:r.type=='conceptual_understanding','concept requirement')
    calculation=one(source.learning_requirements,lambda r:r.type=='capability','capability requirement')
    application=one(source.learning_requirements,lambda r:r.type=='capability_under_task_form','task requirement')
    concept=one(source.conceptual_basis,lambda c:c.concept_ref in conceptual.source_refs,'concept')
    if (concept.concept_ref!='concept-standard-deviation' or calculation.source_refs!=('capability-standard-deviation-calculate',)
        or set(application.source_refs)!={'capability-standard-deviation-calculate','task-form-summary-statistics'}):
        raise ValueError('Provider Product identity is incompatible')
    if concept.description!='A measure of dispersion about the mean in the units of the observations.':
        raise ValueError('Provider conceptual transformation needs review for changed upstream meaning')
    roles={}
    for role in ('conceptual_meaning','calculation_method','supported_task_form','worked_assessment_connection','practice_learning_check'):
        roles[role]=one(pedagogy.teaching_blocks,lambda b:b.role==role,role)
    slots={s.type:s for s in pedagogy.instructional_content}
    if set(slots)!={'calculation_method_slot','task_input_slot','worked_example_slot','learning_check_slot'} or len(slots)!=len(pedagogy.instructional_content):
        raise ValueError('Unexpected authoring slot structure')
    learning=[conceptual.ref,calculation.ref,application.ref]
    if set(learning)!=expected_lr:raise ValueError('Provider must preserve exactly the included requirements')
    def binding(role,requirements,slot=None,assess=False,level='required',origin='authored_instructional_content'):
        lr=tuple(sorted(requirements));block=roles[role]
        if not set(lr)<=set(block.covers_learning_requirement_refs):raise ValueError('Content exceeds its Teaching Block scope')
        slot_refs=()
        if slot:
            target=slots[slot]
            if target.ref not in block.instructional_content_refs or not set(lr)<=set(target.supports_learning_requirement_refs):raise ValueError('Content exceeds its authoring slot scope')
            slot_refs=(target.ref,)
        return dict(origin=origin,constraint_level=level,teaching_block_refs=(block.ref,),instructional_slot_refs=slot_refs,
            covers_learning_requirement_refs=() if assess else lr,assesses_learning_requirement_refs=lr if assess else ())
    def ref(name):return 'authored-sd-v1-'+name
    def variable(name):return dict(op='variable',name=name)
    def op(name,*args):return dict(op=name,args=list(args))
    general=op('sqrt',op('divide',variable('sum_squared_deviations'),variable('n')))
    summary=op('sqrt',op('subtract',op('divide',variable('sum_x2'),variable('n')),op('square',op('divide',variable('sum_x'),variable('n')))))
    formulas=[]
    for name,expression,role,requirement,slot in [('deviation-formula',general,'calculation_method',calculation,'calculation_method_slot'),('summary-formula',summary,'supported_task_form',application,'task_input_slot')]:
        text=render_expression(expression)
        formulas.append(InstructionalFormula(ref=ref(name),expression=expression,display_expression=text,
            verification=verify_formula(expression,text),**binding(role,[requirement.ref],slot)))
    blocks=[]
    blocks.append(ContentBlock(ref=ref('concept'),kind='concept_explanation',
        text='Standard deviation is a measure of how spread out the values in a dataset are around the mean. It is measured in the same units as the original observations.',
        **binding('conceptual_meaning',[conceptual.ref],origin='trusted_semantic_transformation')))
    datasets={'A':('8','9','10','11','12'),'B':('2','6','10','14','18')};claims={}
    for label,values in datasets.items():
        mean,variance,sd=raw_stats(values);claims[label]=dict(mean=str(mean),variance=str(variance),sd=str(sd))
    visual=VisualData(datasets=datasets,claims=claims,same_mean=True,sd_order=('A','B'),brief=visual_brief(claims))
    blocks.append(ContentBlock(ref=ref('visual'),kind='visual_comparison',text='Compare the supplied datasets: same mean, different spread.',visual=visual,
        verification=verify_visual(visual),**binding('conceptual_meaning',[conceptual.ref],level='recommended')))
    blocks.append(ContentBlock(ref=ref('method'),kind='calculation_method',
        text='Determine the mean. Determine each observation\'s deviation from the mean. Square the deviations. Average the squared deviations. Take the square root.',
        formula_refs=(formulas[0].ref,),**binding('calculation_method',[calculation.ref],'calculation_method_slot')))
    blocks.append(ContentBlock(ref=ref('summary-method'),kind='summary_statistics_method',
        text='Use the supplied number of observations, their sum, and the sum of their squares in the summary-statistics relationship. Take the square root of the resulting population variance.',
        instructional_inputs={'n':'number of observations','sum_x':'sum of the observations (Σx)','sum_x2':'sum of the squares of the observations (Σx²)'},
        formula_refs=(formulas[1].ref,),**binding('supported_task_form',[application.ref],'task_input_slot')))
    worked=[];practice=[];checks=[];solutions=[]
    cases=(('worked',5,'50','550','worked_example',worked,'worked_assessment_connection','worked_example_slot','required'),
        ('practice-1',10,'70','530','practice_item',practice,'practice_learning_check','learning_check_slot','recommended'),
        ('practice-2',8,'96','1200','practice_item',practice,'practice_learning_check','learning_check_slot','recommended'),
        ('calculation-check',20,'300','4700','calculation_check',checks,'practice_learning_check','learning_check_slot','required'))
    for name,n,total,squares,kind,collection,role,slot,level in cases:
        stats=SummaryStatistics(n=n,sum_x=total,sum_x2=squares);mean,variance,sd=summary_stats(n,total,squares)
        item_ref=ref(name+'-question');link=binding(role,[calculation.ref,application.ref],slot,assess=kind!='worked_example',level=level,origin='generated_original')
        solution=Solution(ref=ref(name+'-solution'),item_ref=item_ref,method_steps=solution_steps(stats),mean=str(mean),variance=str(variance),
            exact_answer=dict(op='sqrt',radicand=str(variance)),numeric_answer=str(sd),display_answer=display(sd),
            **{**link,'origin':'authored_instructional_content'})
        verification=verify_solution(stats,solution,question_text(stats))
        solution=solution.model_copy(update={'verification':verification});solutions.append(solution)
        item=QuestionItem(ref=item_ref,kind=kind,question=question_text(stats),summary=stats,
            capability_refs=('capability-standard-deviation-calculate',),task_form_refs=('task-form-summary-statistics',),
            assessment_structure_origin='reviewed_evidence_alignment',evidence_refs=tuple(sorted(application.evidence_refs)),verification=verification,**link)
        collection.append(item)
        blocks.append(ContentBlock(ref=ref(name+'-block'),kind=kind,text='Original authored item; the question and solution are stored separately.',item_ref=item.ref,**link))
    concept_link=binding('conceptual_meaning',[conceptual.ref],assess=True,level='flexible')
    concept_item=QuestionItem(ref=ref('concept-check-question'),kind='concept_check',question='What does standard deviation tell us about a set of observations?',**concept_link)
    checks.append(concept_item)
    solutions.append(Solution(ref=ref('concept-check-solution'),item_ref=concept_item.ref,
        expected_meaning='It measures how spread out the observations are around the mean.',key_semantic_elements=('spread or dispersion','around the mean'),**concept_link))
    blocks.append(ContentBlock(ref=ref('concept-check-block'),kind='concept_check',text='Explain the meaning in your own words; no exact-answer string is required.',item_ref=concept_item.ref,**concept_link))
    order={'concept_explanation':0,'visual_comparison':1,'calculation_method':2,'summary_statistics_method':3,'worked_example':4,'practice_item':5,'concept_check':6,'calculation_check':7}
    blocks.sort(key=lambda b:(order[b.kind],b.ref))
    population={s.ref:SlotPopulation(populated=any(s.ref in b.instructional_slot_refs for b in blocks),content_refs=tuple(sorted(b.ref for b in blocks if s.ref in b.instructional_slot_refs))) for s in sorted(slots.values(),key=lambda s:s.ref)}
    identity=source.identity.model_dump();identity['view_type']='authored_teaching_content'
    package=AuthoredTeachingPackage(identity=AuthoredIdentity(**identity),authoring_provider=PROVIDER_ID,
        source_pedagogical_specification=SourcePedagogy(view_key=source.identity.view_key,
            pedagogical_content_sha256=hashlib.sha256(pedagogy.serialize().encode('utf-8')).hexdigest(),
            validation_content_sha256=hashlib.sha256(validation.serialize().encode('utf-8')).hexdigest(),
            teaching_block_refs=tuple(sorted(b.ref for b in roles.values())),instructional_slot_refs=tuple(sorted(s.ref for s in slots.values())),learning_requirement_refs=tuple(sorted(learning))),
        content_blocks=tuple(blocks),instructional_formulas=tuple(formulas),worked_examples=tuple(worked),practice_items=tuple(practice),learning_checks=tuple(sorted(checks,key=lambda c:c.ref)),solutions=tuple(sorted(solutions,key=lambda s:s.ref)),
        verification_summary=VerificationSummary(mathematical_checks_passed=False,checks={},ready_for_downstream_content_validation=False),coverage_summary=population,
        evidence_boundaries=tuple(sorted(pedagogy.evidence_boundaries,key=lambda b:b.ref)),
        content_boundaries=(
            'Instructional formulas are supplied for teaching; formula memorisation is not required.',
            'No specific calculator or manual-only method is required.',
            'No calibrated difficulty, exam frequency, typical marks, common student mistakes or future-exam prediction is claimed.',
            'No new Learning Requirements or prerequisite requirements are introduced.',
            'This package uses population-style calculations; population-versus-sample comparison is outside this Learning Specification.',
            'Only the supported summary-statistics assessment task form is authored; no additional task form is made a required target.',
            'Two decimal places with ROUND_HALF_UP is this package\'s display choice, not a universal exam requirement.',
            'Input notation is newly authored instructional support, not a repair of uncertain source glyphs.',
            'Examples and numerical checks are original authored items, not Pearson questions or historical exam appearances.',
            'Slot population records supplied content only; downstream content validation is still required.'),
        trust_boundary='Authored candidate only. Mathematical verification is not academic approval, publication, pedagogical approval or proof of a completed lesson.')
    verification=verify_package_math(package)
    if not verification.mathematical_checks_passed:raise ValueError('Authored mathematics failed verification')
    return package.model_copy(update={'verification_summary':verification})
