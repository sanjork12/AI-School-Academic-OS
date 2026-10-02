from .models import RepresentationCandidate,ConceptCheckCandidate,AuthoredRoleContent
from .brief import build_brief
from .validation import validate_candidate,validate_brief
from .policy import hash_of,MEANING_LABELS,supported,role_id,CONTRACTS,MAPPING_VERSION

def role_eligibility(spec,family,pedagogy_service):
    valid=pedagogy_service.validate_pedagogical_spec(spec).valid
    ok=valid and supported(spec,family)
    return dict(role_family=family,status='ELIGIBLE_WITH_WARNINGS' if ok else 'BLOCKED',
        role_id=role_id(spec,family) if ok else None,mapping_policy=MAPPING_VERSION,
        contract=CONTRACTS.get(family),validator_available=ok,provenance_enforced=ok,composition_available=ok,
        live_qualified=False,lesson_ready=False)

def compose(value,brief,pedagogy_service,*,validation=None):
    report=validate_candidate(value,brief,pedagogy_service)
    if not report.valid:raise ValueError('CANDIDATE_REJECTED')
    if validation is not None and validation!=report:raise ValueError('STALE_OR_FORGED_VALIDATION')
    b=validate_brief(brief,pedagogy_service)
    cls=RepresentationCandidate if b.binding.role_family=='REPRESENTATION' else ConceptCheckCandidate
    c=cls.model_validate(value);content=c.content
    if isinstance(c,RepresentationCandidate):
        student=dict(instruction=content.instruction,symbol=content.symbol,response_mode=content.response_mode)
        teacher=dict(expected_meaning=content.expected_meaning,expected_response=MEANING_LABELS[content.expected_meaning])
    else:
        student=dict(instruction=content.instruction,stated_meaning=MEANING_LABELS[content.stated_meaning],choices=content.choices,response_mode=content.response_mode)
        teacher=dict(expected_symbol=content.expected_symbol)
    return AuthoredRoleContent(binding=c.binding,candidate_hash=hash_of(c),validation_hash=hash_of(report),brief_hash=hash_of(b),candidate=c,
        student_content=student,teacher_validation=teacher,lineage=dict(source_context='GOVERNED_SOURCE_CONTEXT',pedagogical_constraints='APPROVED_PEDAGOGICAL_CONSTRAINT',
            authored_fields=c.content_origin,semantic_validation='DETERMINISTIC_VALIDATION',display_mapping='DETERMINISTIC_VALIDATION',mapping_policy=MAPPING_VERSION))

def validate_composition(value,brief,pedagogy_service):
    """Validate lineage and student/teacher separation without composing again."""
    try:
        a=AuthoredRoleContent.model_validate(value);r=validate_candidate(a.candidate,brief,pedagogy_service)
        if not r.valid or a.candidate_hash!=hash_of(a.candidate) or a.validation_hash!=hash_of(r) or a.brief_hash!=hash_of(brief) or a.binding!=a.candidate.binding:raise ValueError('COMPOSITION_LINEAGE_CHANGED')
        c=a.candidate.content
        if isinstance(a.candidate,RepresentationCandidate):
            student=dict(instruction=c.instruction,symbol=c.symbol,response_mode=c.response_mode)
            teacher=dict(expected_meaning=c.expected_meaning,expected_response=MEANING_LABELS[c.expected_meaning])
        else:
            student=dict(instruction=c.instruction,stated_meaning=MEANING_LABELS[c.stated_meaning],choices=c.choices,response_mode=c.response_mode)
            teacher=dict(expected_symbol=c.expected_symbol)
        lineage=dict(source_context='GOVERNED_SOURCE_CONTEXT',pedagogical_constraints='APPROVED_PEDAGOGICAL_CONSTRAINT',authored_fields=a.candidate.content_origin,semantic_validation='DETERMINISTIC_VALIDATION',display_mapping='DETERMINISTIC_VALIDATION',mapping_policy=MAPPING_VERSION)
        if a.student_content!=student or a.teacher_validation!=teacher or a.lineage!=lineage:raise ValueError('COMPOSITION_CONTENT_CHANGED')
        return dict(valid=True,semantic_hash=hash_of(a),errors=[])
    except (ValueError,KeyError,TypeError,AttributeError) as exc:return dict(valid=False,errors=[str(exc)])
