"""Independent semantic checks. Does not call the construction function."""
from pydantic import ValidationError
from academic_os.curriculum_ingestion.core import digest
from academic_os.curriculum_ingestion.service import serial
from academic_os.curriculum_capability.service import DECISIONS, PROMOTED
from .models import GovernedLearningSpecification, SpecValidation, GovernanceState
from .policy import POLICY_VERSION, POLICY_SHA256, READY, UNAVAILABLE


def validate_bound_spec(supplied, package, eligibility):
    errors = []
    semantic_hash = digest(serial(supplied))
    package_hash = digest(serial(package))
    def check(condition, code):
        if not condition: errors.append(code)
    try:
        spec = GovernedLearningSpecification.model_validate(supplied)
    except ValidationError:
        return SpecValidation(valid=False, status='FAIL', errors=['SPEC_SCHEMA_INVALID'],
            semantic_sha256=semantic_hash, source_package_hash=package_hash, policy_version=POLICY_VERSION)
    semantic_hash = digest(serial(spec))
    check(spec.source_package_hash == package_hash, 'SOURCE_PACKAGE_HASH_MISMATCH')
    check(spec.curriculum_scope == package.target, 'SELECTED_TARGET_MISMATCH')
    check(spec.policy_version == POLICY_VERSION and spec.policy_sha256 == POLICY_SHA256, 'POLICY_MISMATCH')
    check(eligibility.status in READY and eligibility.binding_valid, 'SCOPE_NOT_ELIGIBLE')
    check(spec.eligibility_hash == digest(serial(eligibility)), 'ELIGIBILITY_HASH_MISMATCH')
    check(spec.identity == digest(serial(['governed-learning-specification/1', package_hash, POLICY_SHA256])), 'IDENTITY_MISMATCH')
    check(spec.evidence == eligibility.evidence_refs, 'EVIDENCE_REFS_MISMATCH')
    check(spec.warnings == eligibility.warnings, 'WARNING_PROPAGATION_MISMATCH')
    check(spec.governance_state == GovernanceState(), 'GOVERNANCE_STATE_MISMATCH')
    source_ids = package.target.source_ids
    for name in ('learning_objectives', 'canonical_semantics', 'learning_intentions', 'task_capabilities'):
        check([v.source_id for v in getattr(spec, name)] == source_ids, name.upper() + '_SCOPE_MISMATCH')
    source_ref = 'package:' + package_hash
    policy_ref = 'policy:' + POLICY_VERSION
    def provenance(actual, classes, refs, ids, rule):
        check(actual.classifications == classes and actual.evidence_refs == refs and actual.source_ids == ids
              and actual.rule == rule and all(ref in spec.evidence for ref in refs), 'PROVENANCE_CLASSIFICATION_OR_BINDING_INVALID')
    if all(len(getattr(spec, name)) == len(package.objectives) for name in
           ('learning_objectives', 'canonical_semantics', 'learning_intentions', 'task_capabilities')):
        for obj, row, source, meaning, intention, task in zip(package.objectives, eligibility.objective_results,
                spec.learning_objectives, spec.canonical_semantics, spec.learning_intentions, spec.task_capabilities, strict=True):
            check(source.official_text == obj.official_text, 'OFFICIAL_WORDING_CHANGED')
            check((source.tier, source.topic_code, source.subtopic_code, source.objective_code, source.subtopic_notes)
                  == (obj.tier, obj.topic_code, obj.subtopic_code, obj.objective_code, obj.subtopic_notes), 'CURRICULUM_SCOPE_CHANGED')
            provenance(source.provenance, ['SOURCE_DERIVED'], [source_ref, 'parsed:' + package.target.run_id],
                       [obj.source_id], 'exact-parsed-wording/1')
            if len(obj.canonical_bindings) != 1:
                errors.append('CANONICAL_BINDING_REQUIRED'); continue
            binding = obj.canonical_bindings[0]
            check(meaning.canonical_id == binding.canonical_id and meaning.description == binding.canonical_wording
                  and meaning.decision_ids == row.decision_ids and meaning.relationship == binding.relationship,
                  'CANONICAL_SEMANTICS_OR_REVIEW_MISMATCH')
            provenance(meaning.provenance, ['CANONICAL_DERIVED', 'HUMAN_REVIEWED'],
                       [source_ref, PROMOTED, DECISIONS], [obj.source_id], 'recorded-equivalent-canonical-meaning/1')
            check(intention.canonical_id == binding.canonical_id and intention.statement == 'Student should be able to: ' + binding.canonical_wording,
                  'UNSUPPORTED_LEARNING_INTENTION')
            check(intention.intention_id == digest(serial(['learning-intention/1', package_hash, obj.source_id, binding.canonical_id])),
                  'INTENTION_IDENTITY_MISMATCH')
            provenance(intention.provenance, ['DETERMINISTIC_TRANSFORMATION'],
                       [source_ref, PROMOTED, DECISIONS, policy_ref], [obj.source_id], 'reviewed-capability-prefix/1')
            check(task.canonical_id == binding.canonical_id and task.action_meaning == binding.canonical_wording
                  and task.task_forms == [], 'UNSUPPORTED_TASK_CAPABILITY')
            provenance(task.provenance, ['CANONICAL_DERIVED', 'HUMAN_REVIEWED'],
                       [source_ref, PROMOTED, DECISIONS], [obj.source_id], 'recorded-equivalent-canonical-meaning/1')
    for name, (state, reason) in UNAVAILABLE.items():
        field = getattr(spec, name)
        check(field.status == state and field.reason_code == reason and field.claims == [], 'UNSUPPORTED_' + name.upper())
        provenance(field.provenance, ['DETERMINISTIC_TRANSFORMATION'], [source_ref, policy_ref], source_ids, 'no-unsupported-claims/1')
    return SpecValidation(valid=not errors, status='FAIL' if errors else 'PASS_WITH_WARNINGS', errors=errors,
        semantic_sha256=semantic_hash, source_package_hash=package_hash, policy_version=POLICY_VERSION)
