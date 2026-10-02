"""Reuse/gap infrastructure; content authoring is delegated to a bounded provider."""
import hashlib
from .authored_models import AuthoredTeachingPackage
from .content_validation import validate_authored_content
from .lesson_profiles import lesson_profile
from .profiled_pedagogy import validate_profiled_pedagogy,digest
from .profiled_content_models import ProfiledAuthoredPackage,RoleDecision,ReusedReference
from .lesson_profile_models import SourceBinding
from .profiled_sd_provider import author,verify_new_content

ROLE_TYPES={'concept_explanation':'concept_explanation','concept_visual':'visual_comparison','calculation_method':'calculation_method',
    'summary_method':'summary_statistics_method','full_worked_examples':'worked_example','independent_practice':'practice_item',
    'concept_check':'concept_check','calculation_check':'calculation_check'}


def compatibility(role,block,authored,learning,used=()):
    """Semantic identity and scope checks; deliberately does not inspect titles."""
    items={q.ref:q for q in (*authored.worked_examples,*authored.practice_items,*authored.learning_checks)}
    item=items.get(block.item_ref)
    covered=set(block.covers_learning_requirement_refs+block.assesses_learning_requirement_refs)
    assessed=set(block.assesses_learning_requirement_refs)
    task_lr={r.ref for r in learning.learning_requirements if r.type=='capability_under_task_form'}
    expected_tasks={s for r in learning.learning_requirements if r.ref in task_lr for s in r.source_refs if s.startswith('task-form-')}
    task_ok=not (set(role.learning_requirement_refs)&task_lr) or (set(item.task_form_refs)==expected_tasks if item else block.kind=='summary_statistics_method')
    return dict(learning_requirements=set(role.learning_requirement_refs)<=covered and set(role.assesses_learning_requirement_refs)<=assessed,
        semantic_role=ROLE_TYPES.get(role.kind)==block.kind,content_type=ROLE_TYPES.get(role.kind)==block.kind,
        task_form=task_ok,evidence_boundaries={b.ref:b for b in authored.evidence_boundaries}=={b.ref:b for b in learning.evidence_boundaries},
        base_lineage=role.base_teaching_block_ref in block.teaching_block_refs,
        distinct_density_instance=block.ref not in used)


def analyze_role(role,authored,learning,used=()):
    known={r.ref for r in learning.learning_requirements}
    if not set(role.learning_requirement_refs)<=known or not set(role.assesses_learning_requirement_refs)<=set(role.learning_requirement_refs):
        return [],{},'Role academic alignment cannot be established'
    checks={b.ref:compatibility(role,b,authored,learning,used) for b in authored.content_blocks}
    selected=[b for b in sorted(authored.content_blocks,key=lambda b:b.ref) if all(checks[b.ref].values())]
    return selected[:role.items.target],checks,None


def build_profiled_content(profiled,authored,validation,learning,base,provider=author):
    p=lesson_profile(profiled.identity.profile_key)
    valid=validate_profiled_pedagogy(profiled,learning,base,p)
    if not valid.valid:raise ValueError('P5A gate is closed: '+ '; '.join(valid.violations))
    a=AuthoredTeachingPackage.model_validate(authored.model_dump() if isinstance(authored,AuthoredTeachingPackage) else authored)
    current=validate_authored_content(a,base,learning)
    if current!=validation or not current.renderer_readiness.ready_for_rendering or current.violations:raise ValueError('Current P4B reuse gate is closed or content/report versions differ')
    source_hash=hashlib.sha256(a.serialize().encode()).hexdigest()
    validation_hash=hashlib.sha256(current.serialize().encode()).hexdigest()
    objects={o.ref:o for o in (*a.content_blocks,*a.instructional_formulas,*a.worked_examples,*a.practice_items,*a.learning_checks,*a.solutions)}
    solutions={s.item_ref:s for s in a.solutions};used=set();reused={};new=[];answers=[];decisions=[];verification={};framing={};ordinals={}
    for role in profiled.profiled_roles:
        if not role.substantive:
            framing[role.ref]=role.learning_requirement_refs;continue
        selected,checks,problem=analyze_role(role,a,learning,used)
        new_refs=[];solution_refs=[]
        ordinal=ordinals.get(role.kind,0)
        for block in selected:
            refs=list(block.formula_refs)
            if block.item_ref:
                refs.extend((block.item_ref,solutions[block.item_ref].ref));solution_refs.append(solutions[block.item_ref].ref)
            reused[block.ref]=ReusedReference(ref=block.ref,content_sha256=digest(block),dependency_hashes={r:digest(objects[r]) for r in refs},source_package_sha256=source_hash,source_validation_sha256=validation_hash)
            used.add(block.ref)
        missing=role.items.target-len(selected)
        if not problem:
            for n in range(missing):
                try:
                    generated=provider(role,ordinal+len(selected)+n+1,learning)
                    if generated is None:problem='No safe deterministic provider for remaining role content';break
                    item,solution=generated
                    report=verify_new_content(item,solution)
                    if report.status!='verified':problem='New content failed deterministic verification: '+str(report.model_dump());break
                    if set(item.learning_requirement_refs)!=set(role.learning_requirement_refs) or set(item.assesses_learning_requirement_refs)!=set(role.assesses_learning_requirement_refs):
                        problem='Provider content does not preserve role alignment';break
                    task_lr={r.ref for r in learning.learning_requirements if r.type=='capability_under_task_form'}
                    tasks={s for r in learning.learning_requirements if r.ref in task_lr for s in r.source_refs if s.startswith('task-form-')}
                    if item.semantic_role!=role.kind or item.support_mode!=role.support_mode or (set(item.task_form_refs)!=tasks if set(role.learning_requirement_refs)&task_lr else bool(item.task_form_refs)):
                        problem='Provider semantic role, support mode or task form is incompatible';break
                    if item.ref in objects or item.ref in {q.ref for q in new}:problem='Provider content identity collision';break
                    new.append(item);answers.append(solution);new_refs.append(item.ref);solution_refs.append(solution.ref);verification[item.ref]=report
                except (ValueError,TypeError,KeyError,ArithmeticError) as exc:problem='Provider could not safely author: '+str(exc);break
        ordinals[role.kind]=ordinal+role.items.target
        supplied=len(selected)+len(new_refs)
        decision='unresolved' if problem else ('author_new' if new_refs else 'reuse')
        for row in checks.values():row['current_p4b_validation']=True
        decisions.append(RoleDecision(role_ref=role.ref,role_key=role.role_key,decision=decision,
            reason=problem or ('Retained compatible validated content; authored only the remaining distinct density items.' if new_refs else 'All required compatibility dimensions passed for existing validated objects.'),
            reused_content_refs=tuple(b.ref for b in selected),new_content_refs=tuple(new_refs),solution_refs=tuple(solution_refs),minimum_items=role.items.minimum,target_items=role.items.target,
            supplied_items=supplied,minimum_met=supplied>=role.items.minimum,target_met=supplied>=role.items.target,compatibility=checks))
        if role.kind=='exit_check':framing[role.ref]=role.learning_requirement_refs
    unresolved=tuple(d.role_ref for d in decisions if d.decision=='unresolved')
    minimum=all(d.minimum_met for d in decisions);target=all(d.target_met for d in decisions)
    complete=minimum and not unresolved
    return ProfiledAuthoredPackage(profile_key=p.identity.profile_key,source_profiled_pedagogy=SourceBinding(schema_version=profiled.schema_version,ref=profiled.identity.ref,sha256=digest(profiled)),
        source_authored_content=SourceBinding(schema_version=a.schema_version,ref=a.identity.view_key,sha256=source_hash),
        source_authored_validation=SourceBinding(schema_version=current.schema_version,ref=a.identity.view_key,sha256=validation_hash),
        academic_scope_fingerprint=profiled.academic_scope_fingerprint,learning_requirement_refs=profiled.learning_requirement_refs,coverage_requirement_refs=profiled.coverage_requirement_refs,
        evidence_boundaries=profiled.evidence_boundaries,content_boundaries=a.content_boundaries,framing=framing,role_decisions=tuple(decisions),
        reused_content=tuple(reused[r] for r in sorted(reused)),new_content=tuple(new),new_solutions=tuple(answers),mathematical_verification=verification,
        content_complete=complete,minimum_density_met=minimum,target_density_met=target,unresolved_role_refs=unresolved,ready_for_p5c=complete and target)


def verify_profiled_package(candidate,profiled,authored,validation,learning,base,provider=author):
    """P5B integrity/math checks only; does not replace future P5C validation."""
    errors=[]
    try:
        value=ProfiledAuthoredPackage.model_validate(candidate.model_dump() if isinstance(candidate,ProfiledAuthoredPackage) else candidate)
        expected=build_profiled_content(profiled,authored,validation,learning,base,provider)
        answers={s.item_ref:s for s in value.new_solutions}
        if len(answers)!=len(value.new_solutions) or set(answers)!={q.ref for q in value.new_content}:errors.append('Questions require exactly one separate solution each')
        for q in value.new_content:
            if q.ref not in answers or verify_new_content(q,answers[q.ref]).status!='verified':errors.append('Recomputed verification failed: '+q.ref)
        for field in ProfiledAuthoredPackage.model_fields:
            if getattr(value,field)!=getattr(expected,field):errors.append('Package integrity mismatch: '+field)
    except (ValueError,TypeError,KeyError) as exc:errors.append(str(exc))
    return dict(valid=not errors,violations=errors,ready_for_rendering=False,validation_scope='P5B integrity and mathematical verification; P5C remains required')
