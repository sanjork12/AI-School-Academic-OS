"""Composition validation, independent of P5B completeness/verification flags."""
import hashlib
from .profiled_validation_models import (Finding,Dimension,RolePopulation,DensityValidation,Readiness,CoverageRow,DensityRow,LearningCoverage,UnresolvedRole,ProfiledContentValidationReport)
from .profiled_content_models import ProfiledAuthoredPackage
from .profiled_content import compatibility
from .profiled_sd_provider import author,verify_new_content
from .profiled_pedagogy import digest,scope_fingerprint,validate_profiled_pedagogy
from .lesson_profiles import validate_lesson_profile,DENSITY_KEYS
from .content_validation import validate_authored_content
from .content_validation_rules import boundary_findings,actual

DIMENSIONS=('profile_structure','role_population','density_validation','reuse_integrity','new_content_integrity','composite_role_validation','academic_scope_validation','boundary_compliance','unresolved_validation')

def serial_sha(model):return hashlib.sha256(model.serialize().encode()).hexdigest()

def validate_profiled_content(candidate,profile,profiled,authored,p4b,learning,base):
    errors=[];warnings=[];failed=set();rows=[];densities=[];lr_rows=[];cr_map={};unresolved=[];math={};inputs={}
    key=getattr(getattr(profile,'identity',None),'profile_key','unknown')
    def issue(dimension,code,ref,message,severity='ERROR'):
        finding=Finding(severity=severity,code=code,ref=str(ref),message=message,dimension=dimension)
        (errors if severity=='ERROR' else warnings).append(finding)
        if severity=='ERROR':failed.add(dimension)
    def finish():
        ordered=lambda fs:tuple(sorted(fs,key=lambda f:(f.dimension,f.ref,f.code,f.message)))
        minimum=bool(densities) and all(r.minimum_compliance for r in densities)
        target=bool(densities) and all(r.target_attainment for r in densities)
        values={d:Dimension(valid=d not in failed) for d in DIMENSIONS if d not in ('role_population','density_validation')}
        return ProfiledContentValidationReport(identity=dict(topic_key='standard-deviation',profile_key=key),lesson_profile=key,input_contracts=inputs,
            **values,role_population=RolePopulation(valid='role_population' not in failed,required=len(getattr(profiled,'profiled_roles',())),populated=sum(r.status=='populated' for r in rows)),
            density_validation=DensityValidation(valid='density_validation' not in failed,minimum_compliance=minimum,target_attainment=target),
            renderer_readiness=Readiness(ready_for_rendering=not errors and bool(rows),blocking_codes=tuple(sorted({f.code for f in errors})),target_attainment=target),
            violations=ordered(errors),warnings=ordered(warnings),coverage_matrix=tuple(rows),density_summary=tuple(densities),learning_requirement_coverage=tuple(lr_rows),
            coverage_requirement_coverage=cr_map,unresolved_roles=tuple(unresolved),mathematical_verification=math,
            trust_summary=dict(current_service_required=True,academic_approval=False,student_mastery_claimed=False,quality_score_provided=False,
                target_policy='Current lesson-profile/1 has no mandatory-target flag. Minima (including min=target) are hard requirements; larger targets are preferred. Unknown profile schema/policy is rejected.',
                limitations=['Renderer eligibility for composition only; no PPTX generated or publication approved.','Duration is planning guidance, not guaranteed classroom runtime.','Language integrity is bounded to the current deterministic provider, not arbitrary semantic or student-response grading.']))
    try:
        profile=validate_lesson_profile(profile)
        key=profile.identity.profile_key
        v=validate_profiled_pedagogy(profiled,learning,base,profile)
        if not v.valid:raise ValueError('Current P5A validation failed: '+ '; '.join(v.violations))
        current=validate_authored_content(authored,base,learning)
        if current!=p4b or current.violations or not current.renderer_readiness.ready_for_rendering:raise ValueError('Current P4B reusable source validation failed')
        package=ProfiledAuthoredPackage.model_validate(candidate.model_dump() if isinstance(candidate,ProfiledAuthoredPackage) else candidate)
        inputs={'lesson-profile/1':digest(profile),'profiled-pedagogical-specification/1':digest(profiled),'learning-specification/1':digest(learning),
            'pedagogical-specification/1':digest(base),'authored-teaching-content/1':serial_sha(authored),'authored-content-validation/1':serial_sha(current),
            'profiled-authored-teaching-content/1':digest(package)}
    except (ValueError,TypeError,KeyError,AttributeError) as exc:
        for d in DIMENSIONS:failed.add(d)
        issue('profile_structure','invalid_input','input',str(exc));return finish()
    if package.profile_key!=key or profiled.identity.profile_key!=key:issue('profile_structure','profile_mismatch',package.profile_key,'Package, profile and pedagogy must identify the same profile')
    for binding,version,ref,h in ((package.source_profiled_pedagogy,profiled.schema_version,profiled.identity.ref,digest(profiled)),
        (package.source_authored_content,authored.schema_version,authored.identity.view_key,serial_sha(authored)),
        (package.source_authored_validation,current.schema_version,authored.identity.view_key,serial_sha(current))):
        if (binding.schema_version,binding.ref,binding.sha256)!=(version,ref,h):issue('reuse_integrity','stale_source_binding',binding.ref,'Source version binding differs from current inputs')
    learning_refs={r.ref for r in learning.learning_requirements};coverage_refs={r.ref for r in learning.coverage_requirements}
    if package.academic_scope_fingerprint!=scope_fingerprint(learning) or package.learning_requirement_refs!=profiled.learning_requirement_refs or package.coverage_requirement_refs!=profiled.coverage_requirement_refs:
        issue('academic_scope_validation','scope_mismatch','package','Scope fingerprint or original requirement identities differ')
    if package.evidence_boundaries!=profiled.evidence_boundaries or package.content_boundaries!=authored.content_boundaries:
        issue('boundary_compliance','boundary_changed','package','All current evidence/content boundaries must be preserved')
    def unique(objects,dimension):
        result={}
        for o in objects:
            if o.ref in result:issue(dimension,'duplicate_identity',o.ref,'Duplicate content identity')
            result[o.ref]=o
        return result
    blocks={b.ref:b for b in authored.content_blocks}
    all_old={o.ref:o for o in (*authored.content_blocks,*authored.instructional_formulas,*authored.worked_examples,*authored.practice_items,*authored.learning_checks,*authored.solutions)}
    old_solutions={s.item_ref:s for s in authored.solutions}
    references=unique(package.reused_content,'reuse_integrity');new=unique(package.new_content,'new_content_integrity');solutions=unique(package.new_solutions,'new_content_integrity')
    answers={}
    for s in package.new_solutions:
        if s.item_ref in answers:issue('new_content_integrity','duplicate_solution',s.item_ref,'Expected one separately addressable solution')
        answers[s.item_ref]=s
    if set(answers)!=set(new):issue('new_content_integrity','solution_set_mismatch','new_content','Every new item needs exactly one solution, with no orphan answers')
    if (set(new)|set(solutions))&set(all_old) or set(new)&set(solutions):issue('reuse_integrity','identity_collision','content','New content must not impersonate existing content or a solution')
    ref_valid={}
    for ref,record in references.items():
        ok=True;block=blocks.get(ref)
        if block is None:ok=False
        else:
            dependencies=list(block.formula_refs)
            if block.item_ref:dependencies.extend((block.item_ref,old_solutions[block.item_ref].ref))
            ok=(record.content_sha256==digest(block) and record.dependency_hashes=={r:digest(all_old[r]) for r in dependencies}
                and record.source_package_sha256==serial_sha(authored) and record.source_validation_sha256==serial_sha(current))
        ref_valid[ref]=ok
        if not ok:issue('reuse_integrity','reused_content_changed',ref,'Unknown reference, content mutation, missing dependency or stale validation binding')
    # Bound content policy only: individual expected provider objects, NOT a whole
    # P5B snapshot comparison. Removing a preferred item remains valid composition.
    expected={};ordinal={}
    for role in profiled.profiled_roles:
        if not role.substantive:continue
        start=ordinal.get(role.kind,0)
        for i in range(role.items.target):
            pair=author(role,start+i+1,learning)
            if pair:expected[pair[0].ref]=pair
        ordinal[role.kind]=start+role.items.target
    new_valid={}
    for ref,q in new.items():
        ok=True;s=answers.get(ref);pair=expected.get(ref)
        if not pair or q!=pair[0] or s!=pair[1]:
            issue('new_content_integrity','actual_content_changed',ref,'Content or separate solution differs from the bounded validated provider representation');ok=False
        if not actual(q.question):issue('new_content_integrity','empty_actual_content',ref,'A role needs actual question/content text');ok=False
        all_item_refs=set(q.learning_requirement_refs+q.assesses_learning_requirement_refs+q.concept_learning_requirement_refs+q.calculation_learning_requirement_refs)
        if not all_item_refs<=learning_refs or not set(q.assesses_learning_requirement_refs+q.concept_learning_requirement_refs+q.calculation_learning_requirement_refs)<=set(q.learning_requirement_refs):
            issue('academic_scope_validation','unknown_learning_ref',ref,'New item exceeds current learning identities');ok=False
        task_refs={s for r in learning.learning_requirements if r.type=='capability_under_task_form' for s in r.source_refs if s.startswith('task-form-')}
        if not set(q.task_form_refs)<=task_refs or q.creates_assessed_task_form:issue('academic_scope_validation','unsupported_task_form',ref,'No new assessed task form is allowed');ok=False
        if q.raw_values:
            calc={r.ref for r in learning.learning_requirements if r.type=='capability'}
            if not q.instructional_demonstration_only or q.task_form_refs or q.assesses_learning_requirement_refs or set(q.learning_requirement_refs)!=calc:
                issue('academic_scope_validation','raw_data_scope_expansion',ref,'Raw observations are instructional modelling of the general calculation capability only');ok=False
        if s:
            check=verify_new_content(q,s);math[ref]=check.model_dump(mode='json')
            if check.status!='verified':issue('new_content_integrity','math_recomputation_failed',ref,'Recomputed verification failed: '+str(check.checks));ok=False
        else:ok=False
        texts=[q.question,q.concept_prompt or '',*q.scaffolding]
        if s:texts.extend([s.expected_meaning or '',*s.method_steps,*s.key_semantic_elements])
        for text in texts:
            for code,clause in boundary_findings(text):issue('boundary_compliance',code,ref,clause);ok=False
        new_valid[ref]=ok
    decisions={}
    for d in package.role_decisions:
        if d.role_ref in decisions:issue('profile_structure','duplicate_role',d.role_ref,'Role has multiple decisions')
        decisions[d.role_ref]=d
    required={r.ref for r in profiled.profiled_roles if r.substantive}
    if set(decisions)-required:issue('profile_structure','unknown_role','roles','Unexpected role decision')
    allowed_framing={r.ref:r.learning_requirement_refs for r in profiled.profiled_roles if not r.substantive or r.kind=='exit_check'}
    if package.framing!=allowed_framing:issue('profile_structure','framing_mismatch','framing','Orientation/closure must reference the existing LRs directly')
    totals={kind:0 for kind in DENSITY_KEYS};used=set();used_new=set();role_sources={}
    for role in profiled.profiled_roles:
        if not role.substantive:
            ok=package.framing.get(role.ref)==role.learning_requirement_refs
            if not ok:failed.add('role_population')
            rows.append(CoverageRow(profiled_role_ref=role.ref,role_key=role.role_key,decision='framing',content_refs=(),learning_requirement_refs=role.learning_requirement_refs,
                coverage_requirement_refs=role.coverage_requirement_refs,support_mode=role.support_mode,minimum_requirement=0,target_requirement=0,actual_valid_content_count=0,
                minimum_compliance=ok,target_attainment=ok,status='populated' if ok else 'invalid',framing=True));continue
        d=decisions.get(role.ref);valid_refs=[];refs=();local_bad=False;expected_solutions=[]
        if d is None:issue('role_population','missing_role',role.ref,'Required role decision is absent');local_bad=True
        else:
            refs=d.reused_content_refs+d.new_content_refs
            if d.decision=='reuse' and d.new_content_refs:issue('profile_structure','decision_mismatch',role.ref,'REUSE cannot declare newly authored objects');local_bad=True
            if d.role_key!=role.role_key:issue('profile_structure','role_identity_mismatch',role.ref,'Role key disagrees with reference');local_bad=True
            if d.decision=='unresolved':
                dimensions=('content_resolution',)
                unresolved.append(UnresolvedRole(role_ref=role.ref,reason=d.reason,missing_compatibility_dimensions=dimensions))
                issue('unresolved_validation','unresolved_required_role',role.ref,d.reason)
            for ref in d.reused_content_refs:
                block=blocks.get(ref);ok=bool(block and ref_valid.get(ref))
                checks=compatibility(role,block,authored,learning,used) if block else {}
                if not ok or not checks or not all(checks.values()):
                    issue('reuse_integrity','incompatible_reuse',ref,'Missing/invalid reusable content or failed dimensions: '+','.join(k for k,v in checks.items() if not v));local_bad=True
                else:
                    valid_refs.append(ref)
                    if block.item_ref:expected_solutions.append(old_solutions[block.item_ref].ref)
                used.add(ref)
            for ref in d.new_content_refs:
                q=new.get(ref);ok=bool(q and new_valid.get(ref) and ref not in used)
                if q:
                    if q.semantic_role!=role.kind or set(q.learning_requirement_refs)!=set(role.learning_requirement_refs) or set(q.assesses_learning_requirement_refs)!=set(role.assesses_learning_requirement_refs) or q.support_mode!=role.support_mode:ok=False
                if not ok:issue('new_content_integrity','incompatible_new_content',ref,'New content fails identity, alignment, support mode, type or integrity');local_bad=True
                else:valid_refs.append(ref);expected_solutions.append(answers[ref].ref)
                used.add(ref);used_new.add(ref)
            if len(refs)!=len(set(refs)):issue('composite_role_validation','duplicate_composite_item',role.ref,'A repeated ref cannot increase density');local_bad=True
            if set(d.solution_refs)!=set(expected_solutions):issue('new_content_integrity','role_solution_mismatch',role.ref,'Role solution references must resolve separately to its items');local_bad=True
        count=len(set(valid_refs));minimum=count>=role.items.minimum;target=count>=role.items.target
        totals[role.kind]+=count
        if not minimum:
            issue('role_population','role_underpopulated',role.ref,'Valid content count is below role minimum')
            if role.items.target>1:issue('composite_role_validation','composite_underpopulated',role.ref,'Composite role does not meet its minimum item count')
        elif not target:issue('density_validation','preferred_target_not_met',role.ref,'Minimum met; preferred content target not attained','WARNING')
        if d and (d.supplied_items!=count or d.minimum_met!=minimum or d.target_met!=target):issue('role_population','stored_population_ignored',role.ref,'Population was recomputed from actual valid items','INFO')
        status='unresolved' if d and d.decision=='unresolved' else ('invalid' if local_bad else ('populated' if minimum else 'underpopulated'))
        if role.items.target>1 and status in ('invalid','unresolved'):failed.add('composite_role_validation')
        if status!='populated':failed.add('role_population')
        rows.append(CoverageRow(profiled_role_ref=role.ref,role_key=role.role_key,decision=d.decision if d else 'missing',content_refs=tuple(refs),
            learning_requirement_refs=role.learning_requirement_refs,coverage_requirement_refs=role.coverage_requirement_refs,support_mode=role.support_mode,
            minimum_requirement=role.items.minimum,target_requirement=role.items.target,actual_valid_content_count=count,minimum_compliance=minimum,target_attainment=target,status=status))
        role_sources[role.ref]=(set(valid_refs)&set(references),set(valid_refs)&set(new))
    if set(new)-used_new:issue('new_content_integrity','orphan_new_content','new_content','New objects are not assigned to a required role')
    for kind in DENSITY_KEYS:
        policy=getattr(profile.density_policy,kind);count=totals[kind]
        densities.append(DensityRow(kind=kind,minimum=policy.minimum,target=policy.target,actual_valid_content_count=count,minimum_compliance=count>=policy.minimum,target_attainment=count>=policy.target))
        if count<policy.minimum:issue('density_validation','density_below_minimum',kind,'Actual valid items below required density')
    populated={r.profiled_role_ref for r in rows if r.status=='populated'}
    for lr in sorted(learning_refs):
        roles=[r for r in profiled.profiled_roles if r.ref in populated and r.substantive and lr in r.learning_requirement_refs]
        teaches=tuple(r.ref for r in roles if lr not in r.assesses_learning_requirement_refs);assesses=tuple(r.ref for r in roles if lr in r.assesses_learning_requirement_refs)
        if not teaches:issue('academic_scope_validation','learning_teaching_gap',lr,'No valid substantive teaching role covers this LR')
        if not assesses:issue('academic_scope_validation','learning_check_gap',lr,'No valid check role covers this LR')
        lr_rows.append(LearningCoverage(learning_requirement_ref=lr,teaching_coverage=teaches,assessment_check_coverage=assesses,
            reused_content_refs=tuple(sorted({x for r in roles for x in role_sources[r.ref][0]})),new_content_refs=tuple(sorted({x for r in roles for x in role_sources[r.ref][1]}))))
    for cr in sorted(coverage_refs):
        cr_map[cr]=tuple(r.ref for r in profiled.profiled_roles if r.ref in populated and cr in r.coverage_requirement_refs)
        if not cr_map[cr]:issue('academic_scope_validation','coverage_requirement_gap',cr,'Original coverage requirement no longer satisfied')
    issue('profile_structure','bounded_validation','package','Composition eligibility is not proof of pedagogical effectiveness or classroom duration','WARNING')
    return finish()
