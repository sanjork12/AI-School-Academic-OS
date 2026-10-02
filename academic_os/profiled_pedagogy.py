"""Pure profile transformation: density and sequencing without scope expansion."""
import hashlib,json
from .learning_models import LearningSpecification
from .pedagogical_models import PedagogicalSpecification
from .pedagogical_validation import validate_pedagogical_contract
from .lesson_profiles import validate_lesson_profile,DENSITY_KEYS
from .lesson_profile_models import (SourceBinding,ProfiledIdentity,ProfiledRole,Count,
    ProfiledPedagogicalSpecification,AuthoringRequirement,ProfileValidation)


def digest(value):
    data=value.model_dump(mode='json') if hasattr(value,'model_dump') else value
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def scope_fingerprint(learning):
    """Bind definition content, not only mutable IDs. Excludes profile/layout/time."""
    data=LearningSpecification.model_validate(learning.model_dump() if isinstance(learning,LearningSpecification) else learning)
    scoped={k:data.model_dump(mode='json')[k] for k in ('identity','conceptual_basis','learning_requirements','coverage_requirements','evidence_boundaries','assessment_evidence','curriculum')}
    for key in ('conceptual_basis','learning_requirements','coverage_requirements','evidence_boundaries','assessment_evidence'):
        scoped[key]=sorted(scoped[key],key=lambda r:r.get('ref',r.get('concept_ref','')))
    scoped['supported_product_refs']=sorted({ref for r in data.learning_requirements for ref in r.source_refs})
    return digest(scoped)


def build_profiled_pedagogy(learning,base,profile):
    l=LearningSpecification.model_validate(learning.model_dump() if isinstance(learning,LearningSpecification) else learning)
    b=PedagogicalSpecification.model_validate(base.model_dump() if isinstance(base,PedagogicalSpecification) else base)
    p=validate_lesson_profile(profile)
    validation=validate_pedagogical_contract(b,l)
    if not validation.authoring_readiness.ready_for_content_authoring or validation.violations:raise ValueError('Current base pedagogy failed P3C: '+ '; '.join(v.code for v in validation.violations))
    groups={kind:[r.ref for r in l.learning_requirements if r.type==kind] for kind in ('conceptual_understanding','capability','capability_under_task_form')}
    if l.identity.view_key!='standard-deviation' or any(len(g)!=1 for g in groups.values()):raise ValueError('Profile adapter requires the three existing Standard deviation Learning Requirements')
    concept=tuple(groups['conceptual_understanding']);calculation=tuple(groups['capability']);task=tuple(groups['capability_under_task_form'])
    application=tuple(sorted(calculation+task));all_lr=tuple(sorted(concept+application))
    blocks={block.role:block for block in b.teaching_blocks}
    if len(blocks)!=len(b.teaching_blocks):raise ValueError('Ambiguous base role lineage')
    standard=p.identity.profile_key=='standard-lesson';prefix='SL' if standard else 'FR';roles=[];requirements=[]
    def add(kind,title,phase,targets,base_kind=None,*,assesses=False,expanded=False,support='not_applicable',minimum=1,target=1,new=False,extra=0):
        number=len(roles)+1;key=f'{prefix}-{number:02}';ref=f'profiled-sd-{p.identity.profile_key}-{key}'
        block=blocks[base_kind] if base_kind else None
        cr=block.covers_coverage_requirement_refs if block else ()
        role=ProfiledRole(ref=ref,role_key=key,kind=kind,title=title,phase=phase,
            origin='profile_density_expansion' if expanded or block is None else 'base_pedagogy',base_teaching_block_ref=block.ref if block else None,
            learning_requirement_refs=tuple(sorted(targets)),assesses_learning_requirement_refs=tuple(sorted(targets)) if assesses else (),
            coverage_requirement_refs=tuple(sorted(cr)),profile_reason='Additional pedagogical opportunity for the same existing requirements.' if expanded else 'Preserve the base pedagogical function within the chosen lesson design.',
            support_mode=support,substantive=kind!='orientation',items=Count(minimum=minimum,target=target))
        roles.append(role)
        if role.substantive:requirements.append(AuthoringRequirement(ref=ref+'-authoring',role_ref=ref,content_kind=kind,items=role.items,
            learning_requirement_refs=role.learning_requirement_refs,coverage_requirement_refs=role.coverage_requirement_refs,
            reuse_hint='new_authoring_required' if new else 'potential_existing_p4a',additional_target_items=target if new else extra))
    if standard:add('orientation','Learning orientation','orientation',all_lr,expanded=True,minimum=0,target=0)
    add('concept_explanation','Concept explanation','concept_development',concept,'conceptual_meaning')
    add('concept_visual','Concept visual comparison','concept_development',concept,'conceptual_meaning')
    if standard:add('early_concept_retrieval','Early concept retrieval/check','concept_development',concept,'conceptual_meaning',assesses=True,expanded=True,new=True)
    add('calculation_method','Calculation method','calculation_development',calculation,'calculation_method')
    if standard:add('mini_worked_example','Mini worked example','calculation_development',calculation,'calculation_method',expanded=True,new=True)
    add('summary_method','Summary-statistics method','supported_task_form',task,'supported_task_form')
    add('full_worked_examples','Worked example 1' if standard else 'Worked example','supported_task_form',application,'worked_assessment_connection')
    if standard:
        add('full_worked_examples','Worked example 2','supported_task_form',application,'worked_assessment_connection',expanded=True,new=True)
        for n in (1,2):add('guided_practice',f'Guided practice {n}','supported_practice',application,'practice_learning_check',expanded=True,support='guided',new=True)
        add('independent_practice','Independent practice set','independent_application',application,'practice_learning_check',support='independent',minimum=2,target=3,extra=1)
    else:
        for n in (1,2):add('independent_practice',f'Independent practice {n}','independent_application',application,'practice_learning_check',support='independent',expanded=n>1)
    add('concept_check','Concept check','check_and_closure',concept,'conceptual_meaning',assesses=True,expanded=True)
    add('calculation_check','Calculation/application check','check_and_closure',application,'practice_learning_check',assesses=True)
    if standard:add('exit_check','Exit check + learning summary','check_and_closure',all_lr,'practice_learning_check',assesses=True,expanded=True,new=True)
    totals={kind:dict(minimum=sum(r.items.minimum for r in roles if r.kind==kind),target=sum(r.items.target for r in roles if r.kind==kind)) for kind in DENSITY_KEYS}
    if totals!=p.density_policy.model_dump():raise ValueError('Role item counts do not match profile density')
    cr_refs=tuple(sorted(r.ref for r in l.coverage_requirements))
    if {r for role in roles for r in role.coverage_requirement_refs}!=set(cr_refs):raise ValueError('Coverage requirement lost during profiling')
    return ProfiledPedagogicalSpecification(identity=ProfiledIdentity(ref='profiled-standard-deviation-'+p.identity.profile_key,profile_key=p.identity.profile_key,title=l.identity.title+' — '+p.identity.title),
        lesson_profile=SourceBinding(schema_version=p.schema_version,ref=p.identity.profile_key,sha256=digest(p)),
        source_learning_specification=SourceBinding(schema_version=l.schema_version,ref=l.identity.view_key,sha256=digest(l)),
        source_base_pedagogy=SourceBinding(schema_version=b.schema_version,ref=b.identity.view_key,sha256=digest(b)),
        academic_scope_fingerprint=scope_fingerprint(l),learning_requirement_refs=all_lr,coverage_requirement_refs=cr_refs,
        profiled_roles=tuple(roles),density_summary=p.density_policy,time_plan=p.time_plan,evidence_boundaries=l.evidence_boundaries,
        authoring_requirements=tuple(requirements))


def validate_profiled_pedagogy(candidate,learning,base,profile):
    """Authenticate through the service; this pure check only validates supplied data."""
    errors=[]
    try:
        supplied=ProfiledPedagogicalSpecification.model_validate(candidate.model_dump() if isinstance(candidate,ProfiledPedagogicalSpecification) else candidate)
        expected=build_profiled_pedagogy(learning,base,profile)
        for field in ProfiledPedagogicalSpecification.model_fields:
            if getattr(supplied,field)!=getattr(expected,field):errors.append('Profile contract mismatch: '+field)
    except (ValueError,TypeError,KeyError) as exc:errors.append(str(exc))
    return ProfileValidation(valid=not errors,violations=tuple(errors),ready_for_content_authoring=not errors)
