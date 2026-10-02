"""Independent validation: no proposal builder or approval constructor is called."""
from pydantic import ValidationError
from academic_os.curriculum_ingestion.service import serial
from academic_os.curriculum_ingestion.core import digest
from academic_os.governed_pedagogy.policy import catalog_evidence
from .models import Proposal, Brief

COMPONENTS = ['success_criteria', 'activity_scope', 'check_alignment', 'pedagogical_adapter']
PROHIBITIONS = ['NO_SOURCE_MUTATION', 'NO_CANONICAL_AS_OFFICIAL', 'NO_APPROVAL_CLAIMS', 'NO_CONTENT_OR_QUESTIONS', 'NO_SD_CALCULATION_ASSUMPTIONS', 'NO_PUBLICATION']
CONSTRAINTS = ['TARGET_SPECIFIC_SYMBOL_CONTRACTS_ONLY', 'ROLE_FAMILIES_ARE_NON_EXECUTABLE_PROPOSALS', 'PRESERVE_ALL_UPSTREAM_WARNINGS']
REVIEWS = ['EXACT_PROPOSAL_HASH', 'ALL_FOUR_COMPONENT_DECISIONS', 'AUTHENTICATED_REVIEW_RECEIPT', 'HUMAN_PEDAGOGICAL_JUDGMENT_REQUIRED']
ROLE_REFERENCES = {'ORIENTATION': ('SL-01', 'orientation'), 'REPRESENTATION': ('SL-03', 'concept_visual'),
                   'CONCEPT_CHECK': ('SL-13', 'concept_check'), 'SUMMARY': ('SL-15', 'exit_check')}
def hash_of(value): return digest(serial(value))

def validate_brief(value, learning):
    b = Brief.model_validate(value); s = b.source_learning_spec
    if not learning.validate_learning_spec(s).valid: raise ValueError('LEARNING_SPEC_INVALID')
    if b.learning_spec_hash != hash_of(s): raise ValueError('STALE_LEARNING_HASH')
    if (s.curriculum_scope.source_ids != ['EDX-4MA1-F-2.8-A'] or len(s.learning_intentions) != 1
            or len(s.canonical_semantics) != 1 or len(s.learning_objectives) != 1):
        raise ValueError('UNSUPPORTED_BOUNDED_TARGET')
    catalog = catalog_evidence()
    kinds = {r['role_id']: r['kind'] for r in catalog['roles']}
    if any(kinds.get(role) != kind for role, kind in ROLE_REFERENCES.values()): raise ValueError('ROLE_REFERENCE_CHANGED')
    if (b.allowed_categories != COMPONENTS or b.prohibited_claims != PROHIBITIONS
            or b.authoring_constraints != CONSTRAINTS or b.review_requirements != REVIEWS
            or b.role_evidence_hash != hash_of(catalog)):
        raise ValueError('BRIEF_POLICY_CHANGED')
    return b

def validate_proposal(value, brief, learning):
    errors = []
    try:
        b = validate_brief(brief, learning); p = Proposal.model_validate(value)
        if p.brief != b: raise ValueError('BRIEF_BINDING_CHANGED')
        s = b.source_learning_spec; obj = s.learning_objectives[0]; intent = s.learning_intentions[0]; can = s.canonical_semantics[0]
        if (p.source_id, p.tier, p.source_wording) != (obj.source_id, obj.tier, obj.official_text): raise ValueError('SOURCE_TIER_WORDING_CHANGED')
        def unique(rows, key):
            ids = [getattr(r, key) for r in rows]
            if len(ids) != len(set(ids)): raise ValueError('DUPLICATE_IDS')
            return set(ids)
        cs = unique(p.success_criteria, 'criterion_id'); acts = unique(p.activity_scope, 'activity_id'); checks = unique(p.check_alignment, 'check_id')
        origins = set()
        for row in [*p.success_criteria, *p.activity_scope, *p.check_alignment, p.pedagogical_adapter]:
            basis = row.evidence_basis; origins.add(basis.origin)
            if (basis.brief_hash, basis.source_id, basis.intention_id) != (hash_of(b), obj.source_id, intent.intention_id): raise ValueError('PROVENANCE_BINDING_INVALID')
        if len(origins) != 1: raise ValueError('MIXED_ORIGINS')
        for c in p.success_criteria:
            if c.linked_learning_intention != intent.intention_id: raise ValueError('CRITERION_INTENTION_INVALID')
            expected = ('SYMBOL_REPRESENTATION','MEANING_MATCHES_REVIEWED_SYMBOL') if c.observable_student_action == 'INTERPRET_SYMBOL' else ('RELATION_REPRESENTATION','SYMBOL_MATCHES_STATED_RELATION')
            if (c.conditions,c.quality_or_completion_rule) != expected: raise ValueError('CRITERION_ACTION_RULE_MISMATCH')
        if set(x for a in p.activity_scope for x in a.criterion_ids) != cs: raise ValueError('ACTIVITY_COVERAGE_INVALID')
        by_c = {c.criterion_id:c for c in p.success_criteria}; by_a = {a.activity_id:a for a in p.activity_scope}
        for a in p.activity_scope:
            if len(a.criterion_ids) != len(set(a.criterion_ids)): raise ValueError('DUPLICATE_CRITERION_REF')
            for cid in a.criterion_ids:
                mode = 'SYMBOL_INTERPRETATION' if by_c[cid].observable_student_action == 'INTERPRET_SYMBOL' else 'SYMBOL_SELECTION'
                if a.response_mode != mode: raise ValueError('ACTIVITY_ACTION_MISMATCH')
        if {c.criterion_id for c in p.check_alignment} != cs: raise ValueError('CHECK_COVERAGE_INVALID')
        for c in p.check_alignment:
            a = by_a.get(c.activity_id)
            if c.intention_id != intent.intention_id or not a or c.criterion_id not in a.criterion_ids or c.evidence_form != a.response_mode: raise ValueError('CHECK_LINK_INVALID')
        a = p.pedagogical_adapter
        if (a.canonical_id,a.action_meaning) != (can.canonical_id,can.description): raise ValueError('ADAPTER_SEMANTIC_INVALID')
        for refs, expected in [(a.criterion_ids,cs),(a.activity_ids,acts),(a.check_ids,checks)]:
            if set(refs) != expected or len(refs) != len(set(refs)): raise ValueError('ADAPTER_COVERAGE_INVALID')
        roles = a.candidate_role_families
        required = {r.category for r in p.activity_scope} | {'CONCEPT_CHECK'}
        if len(roles) != len(set(roles)) or not required.issubset(roles): raise ValueError('ROLE_REQUIREMENTS_INVALID')
    except (ValidationError, ValueError, KeyError, OSError) as exc:
        errors.append(str(exc))
    return dict(valid=not errors, errors=errors, proposal_hash=hash_of(value), pedagogical_truth_confirmed=False)
