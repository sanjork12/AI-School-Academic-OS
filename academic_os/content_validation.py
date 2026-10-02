"""Pure P4B diagnostics. Current trust is established only by the service boundary."""
import hashlib
import json
import re
from pydantic import ValidationError
from .authored_models import AuthoredTeachingPackage,InstructionalFormula,VisualData,SummaryStatistics,Solution
from .authored_math import verify_formula,verify_visual,verify_solution,result
from .learning_models import LearningSpecification
from .pedagogical_models import PedagogicalSpecification
from .pedagogical_validation import validate_pedagogical_contract,Finding,Check
from .content_validation_models import AuthoredContentValidationReport,ContentCoverageRow,ContentSlotRow,RendererReadiness
from .content_validation_rules import actual,meaning,method,normal,boundary_findings


def rows(value):return [x for x in value if isinstance(x,dict)] if isinstance(value,(list,tuple)) else []
def refs(value):return tuple(x for x in value if isinstance(x,str)) if isinstance(value,(list,tuple)) else ()
def obj(value):return value if isinstance(value,dict) else {}
def lr_refs(item):return set(refs(item.get('covers_learning_requirement_refs'))+refs(item.get('assesses_learning_requirement_refs')))
def digest(value):return hashlib.sha256((json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()
def serialized_hash(value):return hashlib.sha256(value.serialize().encode()).hexdigest()


def validate_authored_content(candidate,pedagogy,learning):
    # Malformed nested JSON must return diagnostics, not crash a renderer gate.
    # Valid-schema programming errors are deliberately not swallowed.
    try:AuthoredTeachingPackage.model_validate(candidate.model_dump(mode='json') if isinstance(candidate,AuthoredTeachingPackage) else candidate)
    except (ValidationError,TypeError,ValueError):
        try:return _validate_authored_content(candidate,pedagogy,learning)
        except (TypeError,AttributeError,KeyError,IndexError):
            source=LearningSpecification.model_validate(learning)
            identity=source.identity.model_dump();identity['view_type']='authored_content_validation'
            failed=Check(valid=False)
            finding=Finding(severity='ERROR',code='contract_schema_invalid',ref='contract',message='Malformed nested authored data cannot be evaluated safely.')
            return AuthoredContentValidationReport(identity=identity,input_contracts={'learning-specification/1':serialized_hash(source)},
                reference_integrity=failed,content_completeness=failed,mathematical_integrity=failed,learning_alignment=failed,
                coverage_requirement_validation=failed,boundary_compliance=failed,slot_population=(),coverage_matrix=(),verification_summary={},
                renderer_readiness=RendererReadiness(ready_for_rendering=False,blocking_codes=('contract_schema_invalid',)),
                violations=(finding,),warnings=(),trust_summary=dict(trust_basis='Invalid input; no trust established.',academic_approval=False,trusted_snapshot=False))
    return _validate_authored_content(candidate,pedagogy,learning)


def _validate_authored_content(candidate,pedagogy,learning):
    """Validate isolated candidate data against caller-supplied upstream contracts.

    P3C is recomputed, not accepted as a candidate-supplied readiness boolean.
    This function is suitable for synthetic tests; it does not authenticate JSON.
    """
    p=PedagogicalSpecification.model_validate(pedagogy)
    l=LearningSpecification.model_validate(learning)
    gate=validate_pedagogical_contract(p,l)
    data=candidate.model_dump(mode='json') if isinstance(candidate,AuthoredTeachingPackage) else obj(candidate)
    errors=[];categories=set();invalid_refs=set();invalid_alignment=set();math_checks={}
    def error(category,code,ref,message):
        ref=str(ref);categories.add(category)
        errors.append(Finding(severity='ERROR',code=code,ref=ref,message=message))
        if category=='references':invalid_refs.add(ref)
        if category=='alignment':invalid_alignment.add(ref)
    try:AuthoredTeachingPackage.model_validate(data)
    except (ValidationError,TypeError,ValueError):error('schema','contract_schema_invalid','contract','Input violates frozen authored-teaching-content/1 shape or internal relationships.')
    if not gate.authoring_readiness.ready_for_content_authoring:error('gate','authoring_gate_closed','upstream','Current P3C contract is not ready for authoring.')
    if l.identity.view_key!='standard-deviation':error('alignment','unsupported_validation_profile','upstream','P4B v1 supports the Standard deviation content profile only.')
    if any(obj(data.get('identity')).get(k)!=v for k,v in l.identity.model_dump().items() if k!='view_type'):
        error('references','identity_mismatch','identity','Authored identity differs from current learning identity.')
    upstream=obj(data.get('source_pedagogical_specification'))
    if upstream.get('pedagogical_content_sha256')!=serialized_hash(p) or upstream.get('validation_content_sha256')!=serialized_hash(gate):
        error('references','stale_upstream_binding','source_pedagogical_specification','Authored upstream hashes do not match current P3B/P3C.')
    learning_by={r.ref:r for r in l.learning_requirements};teaching={b.ref:b for b in p.teaching_blocks};slots={s.ref:s for s in p.instructional_content}
    evidence={e.ref:e for e in l.assessment_evidence}
    capabilities={e.capability_ref for e in l.assessment_evidence};tasks={t for e in l.assessment_evidence for t in e.task_form_refs}
    registry={r:'learning_requirement' for r in learning_by}|{r:'teaching_block' for r in teaching}|{r:'slot' for r in slots}|{r:'evidence' for r in evidence}|{r:'capability' for r in capabilities}|{r:'task_form' for r in tasks}
    registry.update({r.ref:'coverage_requirement' for r in l.coverage_requirements})
    registry.update({r.ref:'boundary' for r in l.evidence_boundaries})
    registry.update({r.concept_ref:'concept' for r in l.conceptual_basis})
    for field,expected in [('teaching_block_refs',teaching),('instructional_slot_refs',slots),('learning_requirement_refs',learning_by)]:
        if set(refs(upstream.get(field)))!=set(expected):error('references','upstream_ref_set_mismatch',field,'Declared source references must match actual upstream entities.')
    groups={name:rows(data.get(name)) for name in ('content_blocks','instructional_formulas','worked_examples','practice_items','learning_checks','solutions')}
    blocks=groups['content_blocks'];formulas=groups['instructional_formulas'];solutions=groups['solutions']
    questions=groups['worked_examples']+groups['practice_items']+groups['learning_checks']
    objects=[o for group in groups.values() for o in group]
    for name,items in groups.items():
        for item in items:
            ref=item.get('ref')
            if not isinstance(ref,str) or not ref.strip():error('references','invalid_identity',name,'Object ref must be nonempty.');continue
            if ref in registry:error('references','duplicate_or_colliding_ref',ref,'Ref collides with an authored or upstream identity.')
            registry[ref]=name
    def index(items):return {o['ref']:o for o in items if isinstance(o.get('ref'),str)}
    question_by=index(questions);formula_by=index(formulas)
    def check(owner,field,allowed,values=None):
        for ref in refs(owner.get(field)) if values is None else values:
            if ref not in allowed:error('references','wrong_kind_ref' if ref in registry else 'broken_ref',owner.get('ref',field),field+' has an invalid target: '+ref)
    for item in objects:
        ref=item.get('ref','object');declared=lr_refs(item)
        check(item,'teaching_block_refs',teaching);check(item,'instructional_slot_refs',slots)
        check(item,'covers_learning_requirement_refs',learning_by);check(item,'assesses_learning_requirement_refs',learning_by)
        for tb in refs(item.get('teaching_block_refs')):
            if tb in teaching and not declared<=set(teaching[tb].covers_learning_requirement_refs):error('alignment','teaching_scope_mismatch',ref,'Authored learning targets exceed the cited Teaching Block.')
        for sr in refs(item.get('instructional_slot_refs')):
            if sr in slots:
                if not declared<=set(slots[sr].supports_learning_requirement_refs):error('alignment','slot_scope_mismatch',ref,'Learning targets exceed the cited slot.')
                if not any(sr in teaching[t].instructional_content_refs for t in refs(item.get('teaching_block_refs')) if t in teaching):error('alignment','slot_owner_mismatch',ref,'Slot does not belong to the cited Teaching Block.')
        if not declared:error('alignment','learning_target_missing',ref,'Every authored object must identify an existing learning target.')
    roles={r.type:r.ref for r in l.learning_requirements}
    concept_target={roles.get('conceptual_understanding')};calculation_target={roles.get('capability')};task_target={roles.get('capability_under_task_form')}
    numerical_targets=calculation_target|task_target
    solution_for={}
    for s in solutions:
        target=s.get('item_ref');check(s,'item_ref',question_by,(target,) if isinstance(target,str) else ())
        if isinstance(target,str):solution_for.setdefault(target,[]).append(s)
        if s.get('origin') not in ('authored_instructional_content','generated_original'):error('boundaries','solution_origin_mismatch',s.get('ref'),'Solutions are authored content, not reviewed source records.')
    for q in questions:
        qr=q.get('ref','question');matches=solution_for.get(qr,[])
        if len(matches)!=1:error('completeness','solution_missing_or_ambiguous',qr,'A question requires exactly one separate solution.')
        if len(matches)==1:
            s=matches[0]
            for field in ('teaching_block_refs','instructional_slot_refs','covers_learning_requirement_refs','assesses_learning_requirement_refs'):
                if set(refs(s.get(field)))!=set(refs(q.get(field))):error('alignment','solution_alignment_mismatch',s.get('ref'), 'Solution and question targets differ.')
        check(q,'capability_refs',capabilities);check(q,'task_form_refs',tasks);check(q,'evidence_refs',evidence)
        expected=concept_target if q.get('kind')=='concept_check' else numerical_targets
        if lr_refs(q)!=expected:error('alignment','question_target_mismatch',qr,'Question role does not match its actual learning targets.')
        if q.get('kind')!='worked_example' and set(refs(q.get('assesses_learning_requirement_refs')))!=expected:error('alignment','assessment_targets_missing',qr,'Assessment items must explicitly assess their supported targets.')
        if q.get('kind')!='concept_check':
            if set(refs(q.get('capability_refs')))!=capabilities or set(refs(q.get('task_form_refs')))!=tasks:error('alignment','task_alignment_missing',qr,'Numerical question requires the supported capability and summary-statistics task form.')
            allowed_evidence={e for lr in expected if lr in learning_by for e in learning_by[lr].evidence_refs}
            if not refs(q.get('evidence_refs')) or not set(refs(q.get('evidence_refs')))<=allowed_evidence or q.get('assessment_structure_origin')!='reviewed_evidence_alignment':error('alignment','reviewed_alignment_missing',qr,'Numerical question must cite reviewed structural evidence for its targets.')
        elif refs(q.get('task_form_refs')) or refs(q.get('capability_refs')):error('alignment','concept_task_mismatch',qr,'Concept meaning check must not claim a numerical task.')
        if q.get('origin') not in ('generated_original','authored_instructional_content'):error('boundaries','question_origin_mismatch',qr,'Question must be original or authored instructional content.')
    for group,allowed in [('worked_examples',{'worked_example'}),('practice_items',{'practice_item'}),('learning_checks',{'concept_check','calculation_check'})]:
        for q in groups[group]:
            if q.get('kind') not in allowed:error('alignment','question_collection_mismatch',q.get('ref'), 'Question is in the wrong collection for its role.')
    for b in blocks:
        br=b.get('ref','block');target=b.get('item_ref')
        if target is not None:
            check(b,'item_ref',question_by,(target,) if isinstance(target,str) else ())
            q=question_by.get(target,{}) if isinstance(target,str) else {}
            if q and (q.get('kind')!=b.get('kind') or any(set(refs(q.get(field)))!=set(refs(b.get(field))) for field in ('teaching_block_refs','instructional_slot_refs','covers_learning_requirement_refs','assesses_learning_requirement_refs'))):error('alignment','block_question_mismatch',br,'Content block and question roles/targets differ.')
        check(b,'formula_refs',formula_by)
    for q in questions:
        if not any(b.get('item_ref')==q.get('ref') for b in blocks):error('references','unlinked_question',q.get('ref'),'Question requires a content block that supplies its rendering context.')
    def verify(ref,fn):
        try:report=fn()
        except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError):report=result({'well_formed_mathematical_content':False})
        math_checks[str(ref)]=report
        if report.status!='verified':error('math','mathematical_verification_failed',ref,'Recomputed mathematical content failed; inspect verification_summary.')
        return report.status=='verified'
    valid_formula={}
    for f in formulas:
        fr=f.get('ref','formula')
        def verify_f(f=f):
            parsed=InstructionalFormula.model_validate(f)
            return verify_formula(parsed.expression,parsed.display_expression)
        valid_formula[fr]=verify(fr,verify_f)
        if f.get('role')!='instructional_formula' or f.get('formula_memorisation_required') is not False:error('boundaries','formula_role_invalid',fr,'Formulas must remain instructional support without memorisation requirements.')
        if f.get('origin')!='authored_instructional_content':error('boundaries','formula_origin_mismatch',fr,'Formula is newly authored instructional support.')
    valid_question={}
    for q in questions:
        qr=q.get('ref','question');ss=solution_for.get(qr,[]);s=ss[0] if len(ss)==1 else {}
        valid=actual(q.get('question')) and bool(s)
        if q.get('kind')=='concept_check':
            elements=' '.join(refs(s.get('key_semantic_elements')))
            valid=valid and meaning(s.get('expected_meaning')) and meaning(elements)
            valid=valid and bool(re.search(r'\b(?:standard deviation|sd)\b',normal(q.get('question')))) and bool(re.search(r'\b(?:tell|meaning|measure|describe|explain)\b',normal(q.get('question'))))
            valid=valid and s.get('exact_string_matching_required') is False and q.get('summary') is None
            valid=valid and not s.get('method_steps') and all(s.get(f) is None for f in ('mean','variance','exact_answer','numeric_answer','display_answer'))
        else:
            def verify_q(q=q,s=s):return verify_solution(SummaryStatistics.model_validate(q.get('summary')),Solution.model_validate(s),q.get('question'))
            valid=verify(qr,verify_q) and valid
        if not valid:error('completeness','question_content_incomplete',qr,'Question/solution content is missing, placeholder, semantically incomplete or mathematically invalid.')
        valid_question[qr]=valid and qr not in invalid_refs|invalid_alignment and s.get('ref') not in invalid_refs|invalid_alignment
    def formula_support(b,expected,variable):
        found=False
        for fr in refs(b.get('formula_refs')):
            f=formula_by.get(fr,{})
            encoded=json.dumps(f.get('expression',{}),sort_keys=True)
            aligned=lr_refs(f)==expected and set(refs(f.get('teaching_block_refs')))==set(refs(b.get('teaching_block_refs')))
            if not aligned:error('alignment','formula_target_mismatch',fr,'Formula and method learning/Teaching Block targets differ.')
            if valid_formula.get(fr) and aligned and '"'+variable+'"' in encoded:found=True
        return found
    valid_blocks={};kind_by={}
    expected_targets={'concept_explanation':concept_target,'visual_comparison':concept_target,'concept_check':concept_target,
        'calculation_method':calculation_target,'summary_statistics_method':task_target,
        'worked_example':numerical_targets,'practice_item':numerical_targets,'calculation_check':numerical_targets}
    for b in blocks:
        br=b.get('ref','block');kind=b.get('kind');valid=False
        if b.get('visual') is not None and kind!='visual_comparison':
            verify(br,lambda b=b:verify_visual(VisualData.model_validate(b.get('visual'))))
            error('alignment','content_payload_role_mismatch',br,'Visual payload requires a visual content role.')
        if (b.get('item_ref') is not None and kind not in ('worked_example','practice_item','concept_check','calculation_check')) or (b.get('formula_refs') and kind not in ('calculation_method','summary_statistics_method')) or (b.get('instructional_inputs') and kind!='summary_statistics_method'):
            error('alignment','content_payload_role_mismatch',br,'Content payload does not belong to this block role.')
        if kind!='concept_explanation' and b.get('origin') not in ('authored_instructional_content','generated_original'):error('boundaries','block_origin_mismatch',br,'Instructional content cannot claim to be trusted academic meaning or reviewed source evidence.')
        if isinstance(kind,str):kind_by.setdefault(kind,[]).append(br)
        if lr_refs(b)!=expected_targets.get(kind,set()):error('alignment','block_target_mismatch',br,'Content kind does not support its declared learning targets.')
        if kind=='concept_explanation':
            valid=meaning(b.get('text'),units=True)
            if b.get('origin')!='trusted_semantic_transformation':error('boundaries','concept_origin_mismatch',br,'Concept explanation must identify its trusted semantic transformation.')
        elif kind=='visual_comparison':
            valid=verify(br,lambda b=b:verify_visual(VisualData.model_validate(b.get('visual'))))
            text=normal(b.get('text'))
            valid=valid and actual(text) and bool(re.search(r'(?:same|equal) (?:mean|average)',text)) and bool(re.search(r'different (?:spread|dispersion)',text)) and not re.search(r'\b(?:not|never)\b|dataset a.{0,20}more dispersed',text)
        elif kind=='calculation_method':valid=method(b.get('text')) and formula_support(b,calculation_target,'sum_squared_deviations')
        elif kind=='summary_statistics_method':
            inputs=obj(b.get('instructional_inputs'));text=normal(b.get('text'))
            definitions=(bool(re.search(r'number of (?:observations|values)',normal(inputs.get('n')))),
                bool(re.search(r'sum of (?:the )?(?:observations|values)',normal(inputs.get('sum_x')))),
                bool(re.search(r'sum of (?:the )?squares of (?:the )?(?:observations|values)',normal(inputs.get('sum_x2')))))
            valid=all(definitions) and actual(text) and 'square root' in text and 'summary' in text and not re.search(r'\b(?:not|never|skip)\b',text) and formula_support(b,task_target,'sum_x2')
        elif kind in ('worked_example','practice_item','concept_check','calculation_check'):
            valid=valid_question.get(b.get('item_ref'),False) and actual(b.get('text'))
        if not valid:error('completeness','block_content_incomplete',br,'Block lacks valid actual content for its semantic role.')
        valid_blocks[br]=bool(valid) and br not in invalid_refs|invalid_alignment
    # Check every authored prose location, not only titles or metadata labels.
    for item in objects:
        ir=item.get('ref','object');texts=[]
        for field in ('text','question','expected_meaning','display_expression'):texts.append(item.get(field))
        texts.extend(refs(item.get('method_steps')));texts.extend(refs(item.get('key_semantic_elements')))
        texts.extend(obj(item.get('instructional_inputs')).values());texts.append(obj(item.get('visual')).get('brief'))
        for text in texts:
            for code,clause in boundary_findings(text):error('boundaries',code,ir,'Unsupported authored claim: '+clause)
        if item.get('source_question_copy') is True:error('boundaries','source_question_copy',ir,'Source copying is not supported by this contract.')
    if sorted(rows(data.get('evidence_boundaries')),key=lambda x:str(x.get('ref')))!=sorted([b.model_dump(mode='json') for b in l.evidence_boundaries],key=lambda x:x['ref']):error('boundaries','evidence_boundaries_changed','evidence_boundaries','All upstream evidence boundaries must be preserved.')
    for text in refs(data.get('content_boundaries')):
        for code,clause in boundary_findings(text):error('boundaries',code,'content_boundaries','Unsupported boundary declaration: '+clause)
    if not refs(data.get('content_boundaries')):error('boundaries','content_boundaries_missing','content_boundaries','Authored scope boundaries must be explicit.')
    scope=' '.join(normal(t) for t in refs(data.get('content_boundaries')))
    for policy,pattern in {
        'population_sample_scope':r'population.{0,100}sample.{0,70}outside',
        'formula_support_only':r'formula.{0,100}memori[sz]ation is not required',
        'rounding_not_exam_rule':r'two decimal places.{0,100}round_half_up.{0,100}not a universal exam requirement',
    }.items():
        if not re.search(pattern,scope):error('boundaries','content_scope_missing','content_boundaries','Missing explicit authored scope policy: '+policy)
    for required in ('concept_explanation','calculation_method','summary_statistics_method','worked_example','calculation_check'):
        if not kind_by.get(required):error('completeness','content_role_missing',required,'Current Standard deviation profile requires this actual content role.')
    slot_rows=[]
    slot_kinds={'calculation_method_slot':{'calculation_method'},'task_input_slot':{'summary_statistics_method'},'worked_example_slot':{'worked_example'},'learning_check_slot':{'calculation_check'}}
    for sr,s in sorted(slots.items()):
        contributing=tuple(sorted(b['ref'] for b in blocks if isinstance(b.get('ref'),str) and valid_blocks.get(b['ref']) and sr in refs(b.get('instructional_slot_refs')) and b.get('kind') in slot_kinds.get(s.type,set())))
        slot_rows.append(ContentSlotRow(slot_ref=sr,semantic_role=s.type,populated=bool(contributing),evidence_refs=contributing))
        if not contributing:error('completeness','slot_unpopulated',sr,'No valid actual content satisfies this upstream slot role.')
    matrix=[]
    required_kinds={'conceptual_understanding':{'concept_explanation'},'capability':{'calculation_method'},'capability_under_task_form':{'summary_statistics_method'}}
    for lr,r in sorted(learning_by.items()):
        contributing=[b for b in blocks if valid_blocks.get(b.get('ref')) and lr in lr_refs(b)]
        present={b.get('kind') for b in contributing};covered=required_kinds[r.type]<=present
        matrix.append(ContentCoverageRow(requirement_ref=lr,kind='learning_requirement',semantic_role=r.type,status='covered' if covered else 'uncovered',evidence_refs=tuple(sorted(b['ref'] for b in contributing))))
        if not covered:error('alignment','learning_coverage_missing',lr,'Metadata claims alone do not establish actual coverage for this learning role.')
    worked=[q for q in groups['worked_examples'] if valid_question.get(q.get('ref')) and q.get('assessment_structure_origin')=='reviewed_evidence_alignment' and any(valid_blocks.get(b.get('ref')) and b.get('item_ref')==q.get('ref') for b in blocks)]
    assessments=groups['practice_items']+groups['learning_checks']
    for cr in sorted(l.coverage_requirements,key=lambda r:r.ref):
        contributors=worked if cr.type=='teaching_assessment_connection' else assessments
        satisfied=bool(contributors) and all(valid_question.get(q.get('ref')) for q in contributors)
        if cr.type=='assessment_alignment':satisfied=satisfied and all(refs(q.get('assesses_learning_requirement_refs')) for q in contributors)
        matrix.append(ContentCoverageRow(requirement_ref=cr.ref,kind='coverage_requirement',semantic_role=cr.type,status='satisfied' if satisfied else 'unsatisfied',evidence_refs=tuple(sorted(q['ref'] for q in contributors if valid_question.get(q.get('ref'))))))
        if not satisfied:error('coverage','coverage_requirement_unsatisfied',cr.ref,'Required actual assessment connection/alignment is absent or invalid.')
    warnings=(Finding(severity='WARNING',code='bounded_semantic_rules',ref='validation_profile',message='Standard deviation v1 uses structured targets and concept-answer semantic elements plus bounded prose rules. Frozen P4A concept explanations lack structured semantic-element fields. This is not arbitrary-language semantic proof.'),
        Finding(severity='WARNING',code='limited_math_scope',ref='mathematical_integrity',message='Shared P4A exact rational feasibility, 50-digit square roots and ROUND_HALF_UP 2dp apply; formula checks use deterministic datasets, not symbolic proof or constrained moment solving.'),
        Finding(severity='WARNING',code='not_quality_or_plagiarism_review',ref='trust_summary',message='No pedagogical quality scoring, student grading, copyright similarity detection or academic approval is performed.'))
    if not kind_by.get('visual_comparison'):
        warnings+= (Finding(severity='WARNING',code='recommended_visual_missing',ref='conceptual_meaning',message='The recommended visual comparison is absent; a recommendation is not promoted to a required slot.'),)
    unique={(e.code,e.ref,e.message):e for e in errors};ordered=tuple(unique[k] for k in sorted(unique))
    valid=lambda category:category not in categories and 'schema' not in categories
    identity=l.identity.model_dump();identity['view_type']='authored_content_validation'
    return AuthoredContentValidationReport(identity=identity,
        input_contracts={'authored-teaching-content/1':digest(data),'pedagogical-specification/1':serialized_hash(p),'pedagogical-validation/1':serialized_hash(gate),'learning-specification/1':serialized_hash(l)},
        reference_integrity=Check(valid=valid('references')),content_completeness=Check(valid=valid('completeness')),
        mathematical_integrity=Check(valid=valid('math')),learning_alignment=Check(valid=valid('alignment')),
        coverage_requirement_validation=Check(valid=valid('coverage')),boundary_compliance=Check(valid=valid('boundaries')),
        slot_population=tuple(slot_rows),renderer_readiness=RendererReadiness(ready_for_rendering=not errors,blocking_codes=tuple(sorted({e.code for e in errors}))),
        violations=ordered,warnings=warnings,coverage_matrix=tuple(matrix),verification_summary=dict(sorted(math_checks.items())),
        trust_summary=dict(trust_basis='Caller must use the live service for current trust; pure diagnostics do not authenticate JSON.',
            upstream_authoring_ready=gate.authoring_readiness.ready_for_content_authoring,validation_profile='standard-deviation/v1',
            academic_approval=False,trusted_snapshot=False,pedagogical_quality_assessed=False,student_mastery_assessed=False,rendered_artifact_created=False))
