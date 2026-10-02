"""Small exact-scope policy for reviewable capability intentions, not P3A publication."""
from academic_os.curriculum_ingestion.core import digest
from academic_os.curriculum_ingestion.service import serial
from academic_os.curriculum_ingestion.models import Warning
from academic_os.curriculum_capability.service import read_historical_evidence, DECISIONS, PROMOTED
from .models import LearningSpecificationEligibility, ObjectiveEligibility

POLICY_VERSION = 'bounded-reviewed-learning-intentions/1'
POLICY = dict(version=POLICY_VERSION, scope='BOUNDED_REVIEWABLE_LEARNING_INTENTIONS_ONLY',
    selection='ALL_SELECTED_OBJECTIVES_OR_NO_CONSTRUCTION',
    mapping='ONE_EQUIVALENT_CANONICAL_BINDING_WITH_MATCHING_HUMAN_DECISION',
    meaning='EXACT_RECORDED_APPROVED_DESCRIPTION',
    source='REVALIDATED_CAPABILITY_PACKAGE_AND_SOURCE_BINDINGS',
    optional=['assessed_success_criteria', 'prerequisites', 'misconceptions', 'concept_graph', 'assessment_examples'],
    publication=False, pedagogy=False, model_calls=0)
POLICY_SHA256 = digest(serial(POLICY))
READY = ('ELIGIBLE', 'ELIGIBLE_WITH_WARNINGS')
UNAVAILABLE = {
    'success_criteria': ('REVIEW_REQUIRED', 'SUCCESS_CRITERIA_EVIDENCE_UNAVAILABLE'),
    'prerequisites': ('MISSING', 'PREREQUISITE_EVIDENCE_UNAVAILABLE'),
    'known_misconceptions': ('MISSING', 'MISCONCEPTION_EVIDENCE_UNAVAILABLE'),
    'conceptual_knowledge': ('MISSING', 'CONCEPT_MEANING_EVIDENCE_UNAVAILABLE'),
    'concept_skill_task_relations': ('MISSING', 'CONCEPT_SKILL_TASK_RELATIONS_UNAVAILABLE'),
    'assessment_evidence': ('MISSING', 'REVIEWED_ASSESSMENT_EVIDENCE_UNAVAILABLE'),
}


def objective_decision(obj, values):
    """An approval label alone is insufficient; source-specific receipts must match."""
    missing = []
    canonical_id = None
    receipts = []
    if obj.mapping_status != 'MAPPED' or not obj.canonical_bindings:
        missing.append('CANONICAL_MAPPING_' + obj.mapping_status)
    elif len(obj.canonical_bindings) != 1:
        missing.append('UNAMBIGUOUS_CANONICAL_SCOPE_REQUIRED')
    else:
        binding = obj.canonical_bindings[0]
        canonical_id = binding.canonical_id
        if binding.official_source_id != obj.source_id:
            missing.append('SOURCE_SPECIFIC_CANONICAL_BINDING_REQUIRED')
        if binding.relationship != 'equivalent':
            missing.append('EQUIVALENT_SEMANTIC_SCOPE_REQUIRED')
        if binding.historical_review_status != 'approved' or binding.human_review_evidence != 'RECORDED_DECISION':
            missing.append('RECORDED_HUMAN_CANONICAL_DECISION_REQUIRED')
        for decision in values[DECISIONS]['decisions']:
            if (decision['decision_id'] not in binding.decision_ids or decision['decision'] != 'approve'
                    or decision.get('reviewed_by') != 'human'
                    or decision['approved_canonical_id'] != binding.canonical_id
                    or decision['approved_description'] != binding.canonical_wording):
                continue
            mappings = decision.get('approved_official_mappings', [])
            if any(m['official_source_id'] == obj.source_id and m['canonical_id'] == binding.canonical_id
                   and m['relationship'] == 'equivalent' and m['review_status'] == 'approved'
                   and m['mapping_method'] == 'human' for m in mappings):
                receipts.append(decision['decision_id'])
        if not receipts:
            missing.append('SOURCE_AND_DESCRIPTION_MATCHING_REVIEW_REQUIRED')
        if not binding.canonical_wording.strip():
            missing.append('CANONICAL_MEANING_REQUIRED')
    return ObjectiveEligibility(source_id=obj.source_id,
        status='REVIEW_REQUIRED' if missing else 'ELIGIBLE_WITH_WARNINGS',
        reason_codes=missing or ['EXACT_HUMAN_REVIEWED_EQUIVALENT_MEANING'],
        missing_requirements=missing, canonical_id=canonical_id, decision_ids=sorted(receipts))


def evidence_refs(package, package_hash):
    return {**package.evidence, 'package:' + package_hash: package_hash,
        'target:' + package.target.target_id: package.target.target_id,
        'parsed:' + package.target.run_id: package.target.parsed_sha256,
        'validation:' + package.target.run_id: package.target.validation_sha256,
        'policy:' + POLICY_VERSION: POLICY_SHA256}


def evaluate_verified(package):
    """Service must authenticate the package first. This function grants no trust."""
    values, _ = read_historical_evidence()
    package_hash = digest(serial(package))
    rows = [objective_decision(o, values) for o in package.objectives]
    ready = [r.source_id for r in rows if r.status in READY]
    unresolved = [r.source_id for r in rows if r.status not in READY]
    missing = [r.source_id + ':' + code for r in rows for code in r.missing_requirements]
    if not rows:
        missing.append('NONEMPTY_SELECTED_SCOPE_REQUIRED')
    status = 'BLOCKED' if not rows else 'REVIEW_REQUIRED' if unresolved else 'ELIGIBLE_WITH_WARNINGS'
    warnings = list(package.warnings) + [Warning(code='BOUNDED_CONSTRUCTION_ONLY',
        message='Historical canonical review permits only a reviewable skill restatement, not approval of the uploaded source or this specification.')]
    warnings.extend(Warning(code=reason, message=field + ': no governed evidence; no claim constructed.')
                    for field, (_, reason) in UNAVAILABLE.items())
    return LearningSpecificationEligibility(policy_version=POLICY_VERSION, policy_sha256=POLICY_SHA256,
        source_package_hash=package_hash, selected_target_id=package.target.target_id, binding_valid=True,
        status=status, reason_codes=['EXACT_SCOPE_REVIEW_REQUIRED'] if unresolved else ['EMPTY_SCOPE'] if not rows else ['BOUNDED_REVIEWED_INTENTIONS_PERMITTED'],
        missing_requirements=missing, warnings=warnings, evidence_refs=evidence_refs(package, package_hash),
        selected_source_ids=list(package.target.source_ids), objective_results=rows,
        independently_ready_source_ids=ready, unresolved_source_ids=unresolved, excluded_source_ids=[])
