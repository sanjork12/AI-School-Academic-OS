"""Independent checks; never calls brief, candidate or composition constructors."""
from .models import Brief,RepresentationCandidate,ConceptCheckCandidate,Validation
from .policy import hash_of,role_id,supported,CONTRACTS,PROHIBITED,PROVENANCE,SYMBOL_MEANINGS

def validate_brief(value,pedagogy_service):
    b=Brief.model_validate(value);s=b.governed_spec;c=s.approved_evidence;family=b.binding.role_family
    if not pedagogy_service.validate_pedagogical_spec(s).valid or not supported(s,family):raise ValueError('UPSTREAM_SPEC_INVALID_OR_UNSUPPORTED')
    bind=b.binding
    if (bind.role_id,bind.source_id,bind.tier,bind.pedagogical_spec_hash,bind.learning_spec_hash,bind.approved_pack_id,bind.approved_pack_hash,bind.proposal_hash,bind.review_hash,bind.contract_version)!=(role_id(s,family),c.source_id,c.tier,hash_of(s),c.learning_spec_hash,c.pack.evidence_identity,c.pack_hash,c.proposal_hash,c.review_hash,CONTRACTS[family]):raise ValueError('BRIEF_BINDING_INVALID')
    acts=[a for a in c.activity_scope if a.category==family];ids={i for a in acts for i in a.criterion_ids};aids={a.activity_id for a in acts}
    if b.success_criteria!=[r for r in c.success_criteria if r.criterion_id in ids] or b.activity_constraints!=acts or b.check_alignments!=[r for r in c.check_alignment if r.activity_id in aids and r.criterion_id in ids]:raise ValueError('APPROVED_CONSTRAINT_PROJECTION_CHANGED')
    if b.source_context!=s.source_learning_spec.learning_objectives[0] or b.reviewed_canonical!=s.source_learning_spec.canonical_semantics[0] or b.learning_intention!=s.source_learning_spec.learning_intentions[0]:raise ValueError('SOURCE_CANONICAL_CONTEXT_CHANGED')
    if b.warnings!=s.warnings or b.provenance!=PROVENANCE or b.prohibited_content!=PROHIBITED or b.allowed_modes!=sorted({a.response_mode for a in acts}):raise ValueError('BRIEF_POLICY_OR_WARNINGS_CHANGED')
    return b

def validate_candidate(value,brief,pedagogy_service):
    canonical_candidate=value
    checks=dict.fromkeys(['brief_valid','schema_valid','binding_valid','alignment_valid','semantic_valid','response_valid','provenance_valid'],False);errors=[]
    try:
        b=validate_brief(brief,pedagogy_service);checks['brief_valid']=True
        cls=RepresentationCandidate if b.binding.role_family=='REPRESENTATION' else ConceptCheckCandidate
        raw=value.model_dump(mode='json') if hasattr(value,'model_dump') else value
        c=cls.model_validate(raw);canonical_candidate=c;checks['schema_valid']=True
        checks['binding_valid']=c.binding==b.binding and c.brief_hash==hash_of(b)
        a=c.alignment
        criterion=next((x for x in b.success_criteria if x.criterion_id==a.criterion_id),None)
        activity=next((x for x in b.activity_constraints if x.activity_id==a.activity_id),None)
        check=next((x for x in b.check_alignments if x.check_id==a.check_id),None)
        expected_action='INTERPRET_SYMBOL' if b.binding.role_family=='REPRESENTATION' else 'SELECT_SYMBOL'
        checks['alignment_valid']=bool(criterion and activity and check and a.intention_id==b.learning_intention.intention_id==criterion.linked_learning_intention==check.intention_id and a.criterion_id in activity.criterion_ids and check.criterion_id==a.criterion_id and check.activity_id==a.activity_id and criterion.observable_student_action==expected_action)
        content=c.content
        if isinstance(c,RepresentationCandidate):
            checks['semantic_valid']=SYMBOL_MEANINGS[content.symbol]==content.expected_meaning
        else:
            matching=[x for x in content.choices if SYMBOL_MEANINGS[x]==content.stated_meaning]
            checks['semantic_valid']=len(content.choices)==len(set(content.choices)) and matching==[content.expected_symbol]
        checks['response_valid']=bool(activity and check and content.response_mode==activity.response_mode==check.evidence_form and content.response_mode in b.allowed_modes)
        expected_prov={k:c.content_origin for k in content.model_dump(mode='json')}
        checks['provenance_valid']=c.field_provenance==expected_prov
    except (ValueError,KeyError,TypeError,AttributeError) as exc:
        errors.append('CONTRACT_OR_CONTEXT_INVALID:'+type(exc).__name__)
    errors.extend(k.upper()+'_FAILED' for k,v in checks.items() if not v)
    return Validation(valid=all(checks.values()) and not errors,errors=errors,candidate_hash=hash_of(canonical_candidate),brief_hash=hash_of(brief),checks=checks)
