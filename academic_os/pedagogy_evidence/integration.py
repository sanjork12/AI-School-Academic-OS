"""Consumption adapter, not a replacement for P6UI.5's closed readiness policy."""
from .models import Pack
from .validation import COMPONENTS, hash_of

def consume_approved_evidence(learning_spec, pack, evidence_service, pedagogy_service):
    result = evidence_service.validate_pedagogical_evidence_pack(pack)
    if not result['valid']: raise ValueError('INVALID_EVIDENCE_PACK')
    p = Pack.model_validate(pack)
    if p.proposal.brief.learning_spec_hash != hash_of(learning_spec): raise ValueError('PACK_LEARNING_BINDING_MISMATCH')
    eligibility = pedagogy_service.evaluate_pedagogical_spec_eligibility(learning_spec)
    if not eligibility.binding_valid: raise ValueError('CURRENT_LEARNING_BINDING_INVALID')
    payload = p.proposal.model_dump(mode='json')
    return dict(learning_spec_hash=hash_of(learning_spec), evidence_identity=p.evidence_identity,
        domain=result['domain'], supplied_requirements={key:payload[key] for key in COMPONENTS},
        candidate_role_families=payload['pedagogical_adapter']['candidate_role_families'],
        existing_p6ui5_eligibility=eligibility.model_dump(mode='json'),
        consumption='FOUR_REQUIRED_CONTRACTS_SUPPLIED',
        construction='NOT_EXECUTED_REQUIRES_FUTURE_CONSTRUCTION_ADAPTER',
        lesson_authoring='BLOCKED', legacy_roles_activated=[], trusted_state_changed=False)
