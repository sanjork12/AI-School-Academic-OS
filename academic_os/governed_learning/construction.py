"""Bounded deterministic projection; callers enter through the validating service."""
from academic_os.curriculum_ingestion.core import digest
from academic_os.curriculum_ingestion.service import serial
from academic_os.curriculum_capability.service import DECISIONS, PROMOTED
from .policy import POLICY_VERSION, POLICY_SHA256, UNAVAILABLE
from .models import (Provenance, SourceObjective, CanonicalSemantic, LearningIntention,
                     TaskCapability, UnavailableElement, GovernanceState, GovernedLearningSpecification)


def construct_verified(package, eligibility):
    package_hash = eligibility.source_package_hash
    source_ref = 'package:' + package_hash
    policy_ref = 'policy:' + POLICY_VERSION
    sources, semantics, intentions, tasks = [], [], [], []
    for obj, row in zip(package.objectives, eligibility.objective_results, strict=True):
        binding = obj.canonical_bindings[0]
        sources.append(SourceObjective(source_id=obj.source_id, official_text=obj.official_text, tier=obj.tier,
            topic_code=obj.topic_code, subtopic_code=obj.subtopic_code, objective_code=obj.objective_code,
            subtopic_notes=list(obj.subtopic_notes), provenance=Provenance(classifications=['SOURCE_DERIVED'],
                evidence_refs=[source_ref, 'parsed:' + package.target.run_id], source_ids=[obj.source_id], rule='exact-parsed-wording/1')))
        provenance = Provenance(classifications=['CANONICAL_DERIVED', 'HUMAN_REVIEWED'],
            evidence_refs=[source_ref, PROMOTED, DECISIONS], source_ids=[obj.source_id], rule='recorded-equivalent-canonical-meaning/1')
        semantics.append(CanonicalSemantic(source_id=obj.source_id, canonical_id=binding.canonical_id,
            description=binding.canonical_wording, decision_ids=row.decision_ids, provenance=provenance))
        intentions.append(LearningIntention(
            intention_id=digest(serial(['learning-intention/1', package_hash, obj.source_id, binding.canonical_id])),
            source_id=obj.source_id, canonical_id=binding.canonical_id,
            statement='Student should be able to: ' + binding.canonical_wording,
            provenance=Provenance(classifications=['DETERMINISTIC_TRANSFORMATION'],
                evidence_refs=[source_ref, PROMOTED, DECISIONS, policy_ref], source_ids=[obj.source_id],
                rule='reviewed-capability-prefix/1')))
        tasks.append(TaskCapability(source_id=obj.source_id, canonical_id=binding.canonical_id,
            action_meaning=binding.canonical_wording, task_forms=[], provenance=provenance))
    unavailable = {field: UnavailableElement(status=state, reason_code=reason, claims=[],
        provenance=Provenance(classifications=['DETERMINISTIC_TRANSFORMATION'],
            evidence_refs=[source_ref, policy_ref], source_ids=list(package.target.source_ids),
            rule='no-unsupported-claims/1')) for field, (state, reason) in UNAVAILABLE.items()}
    return GovernedLearningSpecification(
        identity=digest(serial(['governed-learning-specification/1', package_hash, POLICY_SHA256])),
        source_package_hash=package_hash, eligibility_hash=digest(serial(eligibility)),
        policy_version=POLICY_VERSION, policy_sha256=POLICY_SHA256, curriculum_scope=package.target,
        learning_objectives=sources, canonical_semantics=semantics, learning_intentions=intentions,
        task_capabilities=tasks, **unavailable, warnings=eligibility.warnings,
        evidence=eligibility.evidence_refs, governance_state=GovernanceState())
