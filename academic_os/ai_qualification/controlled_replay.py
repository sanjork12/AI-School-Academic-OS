"""Verify saved request authority and recompute input binding without a provider."""
from ..ai_authoring.brief import digest
from ..ai_authoring.controlled import require_context, binding, ControlledBrief, ControlledValidation
from ..ai_authoring.models import Candidate

CONTEXT_KEYS = ('controlled_mode', 'controlled_case', 'controlled_case_sha256')
RESULT_KEYS = ('controlled_input_binding_valid', 'controlled_input_binding_status', 'controlled_input_binding_reason')


def saved_context(manifest, brief, policy):
    data = {k: manifest.get(k) for k in CONTEXT_KEYS}
    case = require_context(**data, policy=policy)
    if case is None:
        if brief.get('schema_version') == 'authoring-brief/4' or any(k in brief for k in CONTEXT_KEYS):
            raise ValueError('Controlled brief lacks saved application context')
        return None, {}
    parsed = ControlledBrief.model_validate(brief)
    if parsed.controlled_case != case or parsed.controlled_case_sha256 != data['controlled_case_sha256']:
        raise ValueError('Saved brief and application case differ')
    if digest(brief) != manifest['authoring_brief']['sha256']:
        raise ValueError('Saved controlled brief hash differs')
    return case, dict(data, controlled_case=case)


def verify_attempt(record, audit, manifest, brief, case):
    validation = ControlledValidation.model_validate(audit['validation'])
    for owner in (record.model_dump(mode='json'), validation.model_dump(mode='json')):
        for key in CONTEXT_KEYS:
            if owner[key] != manifest[key]:
                raise ValueError('Controlled case differs between run and attempt')
    if audit['brief'] != brief or record.brief_ref != brief['identity']:
        raise ValueError('Controlled attempt brief differs')
    candidate = audit['candidate']
    returned = candidate['content']['proposed_math_inputs'] if candidate else None
    if record.returned_inputs != returned:
        raise ValueError('Returned input evidence differs')
    valid, reason = None, 'controlled_input_not_evaluated'
    if candidate is not None:
        c = Candidate.model_validate(candidate)
        if c.brief_ref != brief['identity'] or c.brief_sha256 != digest(brief):
            raise ValueError('Candidate controlled brief binding differs')
        valid, reason = binding(case, c.content.proposed_math_inputs)
    status = 'NOT_EVALUATED' if valid is None else ('PASSED' if valid else 'FAILED')
    if (validation.controlled_input_binding_valid, validation.controlled_input_binding_status,
        validation.controlled_input_binding_reason) != (valid, status, reason):
        raise ValueError('Saved controlled validation differs from exact replay')
    operational = record.outcome in ('provider_failure', 'input_validation_failure', 'candidate_schema_failure')
    expected = (None, 'NOT_EVALUATED', 'controlled_input_not_evaluated') if operational else (valid, status, reason)
    if tuple(getattr(record, k) for k in RESULT_KEYS) != expected:
        raise ValueError('Attempt controlled result differs from replay')
    if record.accepted and (valid is not True or validation.controlled_input_binding_valid is not True):
        raise ValueError('Controlled acceptance lacks a binding pass')
