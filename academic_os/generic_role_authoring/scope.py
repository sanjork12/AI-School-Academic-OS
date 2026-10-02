"""Construction and independent field-level validation of governed framing."""
from .scope_models import ScopeFraming,ScopeBinding,IncludedCapability,ExcludedCapability
from .scope_policy import checked_spec,LABELS,EXCLUSIONS,PROVENANCE,VERSION,render,identity
from .policy import hash_of,MAPPING_VERSION,CONTRACTS,role_id,supported

def build_scope_framing(spec,service):
    s=checked_spec(spec,service);ls=s.source_learning_spec;c=s.approved_evidence
    included=[IncludedCapability(criterion=x,statement=LABELS[x.observable_student_action]) for x in c.success_criteria]
    q=ScopeFraming(identity='',binding=ScopeBinding(source_id=c.source_id,tier=c.tier,
        learning_spec_id=ls.identity,learning_spec_hash=s.learning_spec_hash,
        pedagogical_spec_id=hash_of(s),pedagogical_spec_hash=hash_of(s),
        approved_pack_id=c.pack.evidence_identity,approved_pack_hash=c.pack_hash),
        source_context=ls.learning_objectives[0],reviewed_canonical=ls.canonical_semantics[0],
        learning_intention=ls.learning_intentions[0],included_capabilities=included,
        excluded_capabilities=[ExcludedCapability(capability=k,policy_ref=MAPPING_VERSION+':'+v) for k,v in EXCLUSIONS.items()],
        required_role_families=sorted({r.family for r in s.role_contract.roles if r.requirement=='required' and r.role_key!='scope_framing'}),
        lesson_scope_statement=render(ls.learning_intentions[0].statement,[x.statement for x in included]),
        warnings=s.warnings,provenance=PROVENANCE)
    return q.model_copy(update={'identity':identity(q)})

def validate_scope_framing(value,spec,service):
    checks={};errors=[];canonical=value
    try:
        s=checked_spec(spec,service);checks['upstream']=True
        raw=value.model_dump(mode='json') if hasattr(value,'model_dump') else value
        q=ScopeFraming.model_validate(raw);canonical=q;checks['schema']=True
        c=s.approved_evidence;ls=s.source_learning_spec;b=q.binding
        checks['bindings']=(b.source_id,b.tier,b.learning_spec_id,b.learning_spec_hash,b.pedagogical_spec_id,b.pedagogical_spec_hash,b.approved_pack_id,b.approved_pack_hash)==(c.source_id,c.tier,ls.identity,s.learning_spec_hash,hash_of(s),hash_of(s),c.pack.evidence_identity,c.pack_hash)
        checks['source_canonical']=q.source_context==ls.learning_objectives[0] and q.reviewed_canonical==ls.canonical_semantics[0]
        checks['intention']=q.learning_intention==ls.learning_intentions[0]
        checks['included']=[x.criterion for x in q.included_capabilities]==c.success_criteria and all(x.statement==LABELS[x.criterion.observable_student_action] for x in q.included_capabilities)
        checks['excluded']=[(x.capability,x.policy_ref) for x in q.excluded_capabilities]==[(k,MAPPING_VERSION+':'+v) for k,v in EXCLUSIONS.items()]
        checks['roles']=q.required_role_families==sorted({r.family for r in s.role_contract.roles if r.requirement=='required' and r.role_key!='scope_framing'})
        checks['warnings']=q.warnings==s.warnings
        checks['provenance']=q.provenance==PROVENANCE
        checks['rendering']=q.lesson_scope_statement==render(ls.learning_intentions[0].statement,[LABELS[x.observable_student_action] for x in c.success_criteria])
        checks['identity']=q.identity==identity(q)
    except (ValueError,TypeError,KeyError,AttributeError):errors.append('INVALID_SCOPE_OR_GOVERNED_INPUT')
    errors.extend(k.upper()+'_MISMATCH' for k,v in checks.items() if not v)
    return dict(schema_version='scope-framing-validation/1',policy_version=VERSION,valid=not errors and len(checks)==12,
        errors=errors,checks=checks,scope_hash=hash_of(canonical),pedagogical_spec_hash=hash_of(spec),model_calls=0)

def build_lesson_authoring_plan(spec,framing,service):
    s=checked_spec(spec,service);report=validate_scope_framing(framing,s,service)
    if not report['valid']:raise ValueError('VALID_SCOPE_FRAMING_REQUIRED')
    gate=service.evaluate_lesson_authoring_eligibility(s,scope_framing=framing)
    rows=[]
    for role in s.role_contract.roles:
        if role.requirement=='unsupported':continue
        if role.role_key=='scope_framing':
            rows.append(dict(role_key=role.role_key,requirement=role.requirement,disposition='DETERMINISTIC_FRAMING',scope_hash=report['scope_hash'],validation_hash=hash_of(report)))
        elif role.role_key.startswith('approved_') and supported(s,role.family):
            rows.append(dict(role_key=role.role_key,requirement=role.requirement,disposition='AI_AUTHORABLE',role_id=role_id(s,role.family),contract=CONTRACTS[role.family],live_qualified=False))
        else:rows.append(dict(role_key=role.role_key,requirement=role.requirement,disposition='UNSUPPORTED' if role.requirement=='required' else 'OPTIONAL_NOT_IMPLEMENTED'))
    return dict(schema_version='generic-lesson-authoring-plan/1',pedagogical_spec_hash=hash_of(s),roles=rows,mandatory_sequence=[],
        authoring_eligibility=gate.model_dump(mode='json'),content_generated=False,render_ready=False,published=False,model_calls=0)
