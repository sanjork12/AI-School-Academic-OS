"""Independent qualification/contract validation; never calls a constructor."""
from pydantic import ValidationError
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.service import serial
from .models import Qualification, GovernedPedagogicalSpecification, Governance, Validation
from .policy import VERSION, POLICY_HASH, ROLE_ROWS, evaluate_verified, authoring_without_spec
from .policy import evaluate_with_approved, APPROVED_VERSION, APPROVED_HASH
from .consumer import validate_consumed, authenticate
from .models import PedagogicalSpecificationEligibility
from academic_os.governed_learning.models import GovernedLearningSpecification


def role_errors(role):
    errors = []
    expected = {k: (family, state, reason, legacy) for k, family, state, reason, legacy in ROLE_ROWS}
    if [r.role_key for r in role.roles] != list(expected): errors.append('ROLE_SUBSTITUTION_OR_OMISSION')
    for row in role.roles:
        if row.role_key not in expected: continue
        family, state, reason, legacy = expected[row.role_key]
        if (row.family, row.requirement, row.reason_code, row.legacy_role_ids) != (family, state, reason, legacy):
            errors.append('ROLE_REQUIREMENT_CHANGED')
    for state in ('required', 'optional', 'unsupported'):
        if getattr(role, state + '_roles') != [k for k, (_, s, _, _) in expected.items() if s == state]:
            errors.append('ROLE_PARTITION_CHANGED')
    if role.mandatory_sequence: errors.append('UNSUPPORTED_SEQUENCE')
    if role.legacy_role_compatibility != {f'SL-{n:02}': 'UNSUPPORTED_NO_TOPIC2_PROFILE_ADAPTER' for n in range(1, 16)}:
        errors.append('UNSUPPORTED_STANDARD_DEVIATION_ROLE')
    return errors


def report(value, errors):
    raw = value.model_dump(mode='json') if hasattr(value, 'model_dump') else value
    schema = raw.get('schema_version', 'unknown') if isinstance(raw, dict) else 'unknown'
    return Validation(validated_schema=str(schema), valid=not errors, status='FAIL' if errors else 'PASS_WITH_WARNINGS',
        errors=errors, semantic_sha256=core.digest(serial(value)), policy_version=raw.get('policy_version',VERSION) if isinstance(raw,dict) else VERSION)


def validate_qualification_bound(value, learning_service):
    try: q = Qualification.model_validate(value)
    except ValidationError: return report(value, ['QUALIFICATION_SCHEMA_INVALID'])
    if not learning_service.validate_learning_spec(q.source_learning_spec).valid:
        return report(q, ['LEARNING_SPEC_INVALID'])
    expected = evaluate_verified(q.source_learning_spec)
    errors = role_errors(q.eligibility.role_contract) if q.eligibility.role_contract else ['ROLE_CONTRACT_MISSING']
    if q.eligibility != expected: errors.append('ELIGIBILITY_BINDING_OR_EVIDENCE_MISMATCH')
    if q.lesson_authoring_eligibility != authoring_without_spec(expected): errors.append('AUTHORING_GATE_MISMATCH')
    if q.governance_state != Governance(): errors.append('GOVERNANCE_STATE_CHANGED')
    return report(q, errors)


def validate_spec_bound(value, learning_service, evidence_service=None):
    try: spec = GovernedPedagogicalSpecification.model_validate(value)
    except ValidationError: return report(value, ['PEDAGOGICAL_SCHEMA_INVALID'])
    errors = []
    if not learning_service.validate_learning_spec(spec.source_learning_spec).valid:
        return report(spec, ['LEARNING_SPEC_INVALID'])
    consumed=None
    if spec.approved_evidence is not None:
        try:consumed=validate_consumed(spec.approved_evidence,spec.source_learning_spec,evidence_service)
        except (ValueError,OSError,core.IngestionError):return report(spec,['APPROVED_EVIDENCE_INVALID'])
    expected = evaluate_with_approved(spec.source_learning_spec,consumed) if consumed else evaluate_verified(spec.source_learning_spec)
    if spec.learning_spec_hash != core.digest(serial(spec.source_learning_spec)): errors.append('LEARNING_HASH_MISMATCH')
    if spec.learning_scope != spec.source_learning_spec.curriculum_scope: errors.append('SOURCE_TIER_SCOPE_MISMATCH')
    if spec.policy_version != expected.policy_version or spec.eligibility.policy_sha256 != expected.policy_sha256: errors.append('POLICY_MISMATCH')
    if spec.construction_version!=('governed-approved-pedagogical-construction/1' if consumed else 'governed-pedagogical-construction/1'):errors.append('CONSTRUCTION_VERSION_MISMATCH')
    if spec.eligibility != expected: errors.append('ELIGIBILITY_EVIDENCE_MISMATCH')
    if expected.status not in ('ELIGIBLE', 'ELIGIBLE_WITH_WARNINGS'): errors.append('PEDAGOGICAL_INPUTS_INCOMPLETE')
    if consumed:errors.extend(approved_role_errors(spec.role_contract,expected.role_contract))
    else:errors.extend(role_errors(spec.role_contract))
    if spec.role_contract != expected.role_contract: errors.append('ROLE_PROVENANCE_MISMATCH')
    if spec.warnings != expected.warnings: errors.append('WARNINGS_CHANGED')
    if spec.instructional_goal_refs != [x.intention_id for x in spec.source_learning_spec.learning_intentions]:
        errors.append('LEARNING_GOALS_CHANGED')
    if spec.activity_constraints != expected.requirements: errors.append('UNSUPPORTED_ACTIVITY_CONSTRAINTS')
    if spec.teaching_phases: errors.append('UNSUPPORTED_TEACHING_PHASES')
    if spec.governance_state != Governance(): errors.append('GOVERNANCE_STATE_CHANGED')
    return report(spec, errors)


def approved_role_errors(role, expected):
    errors=[]
    if role!=expected:errors.append('APPROVED_ROLE_CONTRACT_CHANGED')
    if any(r.enabled_for_authoring for r in role.roles) or role.mandatory_sequence or role.profile_selected:errors.append('UNSUPPORTED_EXECUTABLE_ROLES')
    if any(r.legacy_role_ids for r in role.roles if r.role_key.startswith('approved_')):errors.append('INVENTED_CONCRETE_ROLE_MAPPING')
    return errors

def validate_eligibility_bound(value,learning_spec,approved_pack,learning_service,evidence_service):
    """No consumer or specification constructor invocation."""
    try:
        spec=GovernedLearningSpecification.model_validate(learning_spec)
        if not learning_service.validate_learning_spec(spec).valid:raise ValueError('LEARNING_SPEC_INVALID')
        given=PedagogicalSpecificationEligibility.model_validate(value)
        if approved_pack is None:expected=evaluate_verified(spec)
        else:
            # Policy only reads pack, hashes, adapter and binding properties. Build no DTO here.
            pack=authenticate(spec,approved_pack,evidence_service)
            from academic_os.pedagogy_evidence.validation import hash_of
            p=pack.proposal
            # A consumer supplied inside a spec is validated independently by validate_consumed.
            # For standalone eligibility, derive its exact canonical serialization directly.
            raw=dict(schema_version='approved-pedagogical-evidence-consumer/1',pack=pack.model_dump(mode='json'),pack_hash=hash_of(pack),learning_spec_hash=hash_of(spec),source_id=p.source_id,tier=p.tier,proposal_hash=hash_of(p),review_hash=pack.review_receipt.semantic_hash,brief_hash=hash_of(p.brief),authoring_policy_version=p.brief.policy_version,
                success_criteria=[x.model_dump(mode='json') for x in p.success_criteria],activity_scope=[x.model_dump(mode='json') for x in p.activity_scope],check_alignment=[x.model_dump(mode='json') for x in p.check_alignment],pedagogical_adapter=p.pedagogical_adapter.model_dump(mode='json'),warnings=[x.model_dump(mode='json') for x in spec.warnings],mapping='EXACT_COMPONENT_COPY_NO_SEMANTIC_TRANSFORMATION',provenance=['LEARNING_SPEC_DERIVED','APPROVED_PEDAGOGICAL_EVIDENCE','DETERMINISTIC_POLICY','HUMAN_REVIEWED'])
            consumed=validate_consumed(raw,spec,evidence_service)
            expected=evaluate_with_approved(spec,consumed)
        return report(value,[] if given==expected else ['ELIGIBILITY_BINDING_OR_REQUIREMENTS_CHANGED'])
    except (ValueError,OSError,core.IngestionError):return report(value,['ELIGIBILITY_INPUT_INVALID'])
