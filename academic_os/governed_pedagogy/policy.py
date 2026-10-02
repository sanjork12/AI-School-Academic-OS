"""Closed policy: diagnose absent inputs rather than generalize SD calculation design."""
import json
from pathlib import Path
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.service import serial
from academic_os.curriculum_ingestion.models import Warning
from .models import (Provenance, InputRequirement, RoleRequirement, RoleContract, ActionBinding,
                     PedagogicalSpecificationEligibility, LessonAuthoringEligibility)

VERSION = 'governed-pedagogical-readiness/1'
AUTHORING_VERSION = 'governed-lesson-authoring-gate/1'
RULES = dict(version=VERSION, input='governed-learning-specification/1',
    required=['success_criteria', 'activity_scope', 'check_alignment', 'pedagogical_adapter'],
    optional=['prerequisites_without_activity_dependency', 'misconceptions', 'worked_assessment_examples'],
    construction='NO_CONSTRUCTION_WHILE_REQUIRED_INPUTS_MISSING', auto_role_mapping=False,
    authoring=False, sequence=False)
POLICY_HASH = core.digest(serial(RULES))
CATALOG = Path(__file__).with_name('role_evidence.json')
ROLE_ROWS = (
    ('scope_framing', 'framing', 'required', 'EXACT_LEARNING_SCOPE_BINDING_REQUIRED', ['SL-01']),
    ('non_assessing_summary', 'framing', 'optional', 'SUMMARY_ONLY_NO_EXIT_CHECK_INFERRED', ['SL-15']),
    ('concept_explanation_retrieval', 'concept', 'unsupported', 'CONCEPT_AND_CHECK_EVIDENCE_REQUIRED', ['SL-02', 'SL-03', 'SL-04', 'SL-13']),
    ('method_formula_instruction', 'method', 'unsupported', 'NO_REVIEWED_CALCULATION_METHOD_ADAPTER', ['SL-05']),
    ('data_backed_demonstration', 'demonstration', 'unsupported', 'NO_SUPPORTED_DATA_TASK_OR_WORKED_EXAMPLE_SCOPE', ['SL-06', 'SL-07', 'SL-08', 'SL-09']),
    ('numerical_calculation_practice', 'practice', 'unsupported', 'NO_SUPPORTED_NUMERICAL_TASK_CONTRACT', ['SL-10', 'SL-11', 'SL-12']),
    ('assessment_check', 'assessment', 'unsupported', 'SUCCESS_CRITERIA_AND_CHECK_ALIGNMENT_REQUIRED', ['SL-04', 'SL-13', 'SL-14', 'SL-15']),
)


def catalog_evidence():
    value = json.loads(CATALOG.read_text(encoding='utf-8'))
    for path, expected in value['sources'].items():
        if core.digest((core.ROOT / path).read_bytes()) != expected:
            raise core.IngestionError('ROLE_EVIDENCE_CHANGED', 'Inspected role-policy evidence changed.')
    return value


def prov(spec, classes, refs, rule):
    return Provenance(classifications=classes, evidence_refs=refs,
        learning_intention_ids=[i.intention_id for i in spec.learning_intentions],
        source_ids=list(spec.curriculum_scope.source_ids), rule=rule)


def role_contract(spec, learning_hash):
    source = 'learning:' + learning_hash
    policy = 'policy:' + VERSION
    rows = [RoleRequirement(role_key=key, family=family, requirement=state, reason_code=reason,
        legacy_role_ids=legacy, provenance=prov(spec, ['DETERMINISTIC_POLICY'],
            [source, policy, 'academic_os/profiled_pedagogy.py'], 'bounded-role-admission/1'))
        for key, family, state, reason, legacy in ROLE_ROWS]
    return RoleContract(required_roles=[r.role_key for r in rows if r.requirement == 'required'],
        optional_roles=[r.role_key for r in rows if r.requirement == 'optional'],
        unsupported_roles=[r.role_key for r in rows if r.requirement == 'unsupported'], roles=rows,
        legacy_role_compatibility={f'SL-{n:02}': 'UNSUPPORTED_NO_TOPIC2_PROFILE_ADAPTER' for n in range(1, 16)},
        mandatory_sequence=[])


def evaluate_verified(spec):
    catalog = catalog_evidence(); learning_hash = core.digest(serial(spec))
    source = 'learning:' + learning_hash; policy = 'policy:' + VERSION
    evidence = {**spec.evidence, **catalog['sources'], source: learning_hash, policy: POLICY_HASH,
        'role-catalog': core.digest(CATALOG.read_bytes())}
    requirements = []
    def add(key, status, required, reason):
        requirements.append(InputRequirement(key=key, status=status, required=required, reason_code=reason,
            provenance=prov(spec, ['LEARNING_SPEC_DERIVED', 'DETERMINISTIC_POLICY'], [source, policy], 'pedagogy-input-requirements/1')))
    add('source_and_tier', 'AVAILABLE', True, 'CURRENT_SOURCE_BOUND_LEARNING_SPEC')
    add('learning_intentions', 'AVAILABLE', True, 'GOVERNED_INTENTIONS_PRESENT')
    add('canonical_scope', 'AVAILABLE', True, 'EXACT_REVIEWED_CANONICAL_SCOPE')
    # The supported upstream v1 contract explicitly has no populated versions of these fields.
    # Its independent validator rejects invented claims, so they cannot be supplied as flags.
    add('success_criteria', 'REVIEW_REQUIRED', True, 'SUCCESS_CRITERIA_REQUIRED')
    add('concept_knowledge', 'OPTIONAL_UNAVAILABLE', False, 'CONCEPT_ROLE_REQUIRES_REVIEWED_CONCEPT_MEANING')
    add('activity_scope', 'MISSING', True, 'ACTIVITY_SCOPE_REQUIRED')
    add('check_alignment', 'MISSING', True, 'CHECK_ALIGNMENT_REQUIRED')
    add('pedagogical_adapter', 'AUTHORING_REQUIRED', True, 'PEDAGOGICAL_AUTHORING_REQUIRED')
    add('prerequisites', 'OPTIONAL_UNAVAILABLE', False, 'PREREQUISITE_EVIDENCE_REQUIRED_IF_ACTIVITY_DEPENDS_ON_IT')
    add('misconceptions', 'OPTIONAL_UNAVAILABLE', False, 'MISCONCEPTION_EVIDENCE_UNAVAILABLE')
    add('assessment_examples', 'OPTIONAL_UNAVAILABLE', False, 'WORKED_ASSESSMENT_ROLE_REQUIRES_REVIEWED_EXAMPLES')
    warnings = list(spec.warnings) + [Warning(code='NO_GENERIC_CALCULATION_MAPPING',
        message='A reviewed capability meaning does not establish calculation method, task graph or Standard Deviation role compatibility.')]
    actions = [ActionBinding(source_id=x.source_id, canonical_id=x.canonical_id, action_meaning=x.description,
        provenance=Provenance(classifications=['CANONICAL_DERIVED', 'HUMAN_REVIEWED'],
            evidence_refs=[source, *x.provenance.evidence_refs], learning_intention_ids=[i.intention_id for i in spec.learning_intentions if i.source_id == x.source_id],
            source_ids=[x.source_id], rule='preserve-reviewed-action-meaning/1')) for x in spec.canonical_semantics]
    missing = [r.reason_code for r in requirements if r.required and r.status != 'AVAILABLE']
    return PedagogicalSpecificationEligibility(policy_version=VERSION, policy_sha256=POLICY_HASH,
        learning_spec_hash=learning_hash, selected_target_id=spec.curriculum_scope.target_id,
        status='REVIEW_REQUIRED', reason_codes=['PEDAGOGICAL_INPUTS_INCOMPLETE'], missing_requirements=missing,
        requirements=requirements, warnings=warnings, evidence_refs=evidence, actions=actions,
        role_contract=role_contract(spec, learning_hash), binding_valid=True)


def authoring_without_spec(eligibility):
    return LessonAuthoringEligibility(status='BLOCKED', reason_codes=['VALID_PEDAGOGICAL_SPEC_REQUIRED'],
        missing_requirements=['VALID_PEDAGOGICAL_SPEC_REQUIRED', *eligibility.missing_requirements,
            'EXECUTABLE_ROLE_CONTRACTS_REQUIRED', 'ROLE_SPECIFIC_CONTENT_VALIDATORS_REQUIRED'],
        warnings=eligibility.warnings, evidence_refs=eligibility.evidence_refs,
        learning_spec_hash=eligibility.learning_spec_hash, pedagogical_spec_hash=None, policy_version=AUTHORING_VERSION)


APPROVED_VERSION = 'approved-evidence-pedagogical-readiness/1'
APPROVED_RULES = dict(base=RULES, version=APPROVED_VERSION, consumer='approved-pedagogical-evidence-consumer/1',
    requirements_unchanged=True, authenticated_human_approval_required=True, exact_components=True, concrete_roles=False)
APPROVED_HASH = core.digest(serial(APPROVED_RULES))

def evaluate_with_approved(spec, consumed):
    """Existing four mandatory requirements acquire evidence, never become optional.

Caller must authenticate and independently validate consumed evidence first.
"""
    base=evaluate_verified(spec)
    refs=['learning:'+consumed.learning_spec_hash,'pack:'+consumed.pack_hash,'review:'+consumed.review_hash,'consumer:'+consumed.schema_version]
    provenance=prov(spec,['LEARNING_SPEC_DERIVED','APPROVED_PEDAGOGICAL_EVIDENCE','DETERMINISTIC_POLICY','HUMAN_REVIEWED'],refs,'exact-approved-component-consumption/1')
    requirements=[r.model_copy(update=dict(status='AVAILABLE',reason_code='APPROVED_'+r.key.upper()+'_PRESENT',provenance=provenance)) if r.key in RULES['required'] else r for r in base.requirements]
    remaining_reasons={'concept_explanation_retrieval':'CONCEPT_MEANING_AND_RETRIEVAL_ADAPTER_UNAVAILABLE',
                       'assessment_check':'BROADER_ASSESSMENT_ROLE_MAPPING_UNAVAILABLE'}
    roles=[r.model_copy(update={'reason_code':remaining_reasons[r.role_key]}) if r.role_key in remaining_reasons else r for r in base.role_contract.roles]
    for family in consumed.pedagogical_adapter.candidate_role_families:
        roles.append(RoleRequirement(role_key='approved_'+family.lower(),family=family,requirement='required',reason_code='EXACT_APPROVED_ROLE_FAMILY',legacy_role_ids=[],provenance=provenance))
    contract=base.role_contract.model_copy(update=dict(roles=roles,required_roles=[r.role_key for r in roles if r.requirement=='required']))
    evidence={**base.evidence_refs,'approved-pack':consumed.pack_hash,'approved-pack-identity':consumed.pack.evidence_identity,'approved-proposal':consumed.proposal_hash,'human-review':consumed.review_hash,'approved-brief':consumed.brief_hash,'consumer':core.digest(serial(consumed))}
    missing=[r.reason_code for r in requirements if r.required and r.status!='AVAILABLE']
    return base.model_copy(update=dict(policy_version=APPROVED_VERSION,policy_sha256=APPROVED_HASH,requirements=requirements,
        role_contract=contract,evidence_refs=evidence,missing_requirements=missing,
        status='REVIEW_REQUIRED' if missing else ('ELIGIBLE_WITH_WARNINGS' if base.warnings else 'ELIGIBLE'),
        reason_codes=['PEDAGOGICAL_INPUTS_INCOMPLETE'] if missing else ['APPROVED_PEDAGOGICAL_INPUTS_BOUND']))
