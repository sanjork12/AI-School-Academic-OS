"""Bounded display policy; exclusions concern this objective, not the curriculum."""
from .policy import PROHIBITED,CONTRACTS,supported,hash_of
from academic_os.governed_pedagogy.models import GovernedPedagogicalSpecification

VERSION='bounded-scope-framing/1'
LABELS={'INTERPRET_SYMBOL':'Interpret the reviewed inequality symbols >, <, ≥ and ≤.',
        'SELECT_SYMBOL':'Select the reviewed inequality symbol matching a stated relation.'}
EXCLUSIONS={'SOLVING_LINEAR_INEQUALITIES':'SOLVING_INEQUALITIES',
            'NUMBER_LINE_SOLUTION_SETS':'NUMBER_LINE_SOLUTIONS',
            'COMPOUND_INEQUALITIES':'COMPOUND_OR_QUADRATIC_INEQUALITIES',
            'QUADRATIC_INEQUALITIES':'COMPOUND_OR_QUADRATIC_INEQUALITIES',
            'INEQUALITY_REGIONS':'SOLUTION_REGIONS',
            'UNRELATED_ALGEBRA_MANIPULATION':'ALGEBRAIC_MANIPULATION'}
PROVENANCE={
    'binding':['SOURCE_BOUND_CONTEXT','GOVERNED_LEARNING_SPEC','APPROVED_PEDAGOGICAL_EVIDENCE'],
    'source_context':['SOURCE_BOUND_CONTEXT'],
    'reviewed_canonical':['REVIEWED_CANONICAL_SEMANTIC'],
    'learning_intention':['GOVERNED_LEARNING_SPEC'],
    'included_capabilities':['APPROVED_PEDAGOGICAL_EVIDENCE','DETERMINISTIC_POLICY'],
    'excluded_capabilities':['DETERMINISTIC_POLICY'],
    'required_role_families':['APPROVED_PEDAGOGICAL_EVIDENCE'],
    'lesson_scope_statement':['GOVERNED_LEARNING_SPEC','APPROVED_PEDAGOGICAL_EVIDENCE','DETERMINISTIC_POLICY'],
    'warnings':['SOURCE_BOUND_CONTEXT','GOVERNED_LEARNING_SPEC','APPROVED_PEDAGOGICAL_EVIDENCE','DETERMINISTIC_POLICY'],
    'identity':['DETERMINISTIC_POLICY'],
    'construction_version':['DETERMINISTIC_POLICY'],
    'disposition':['DETERMINISTIC_POLICY'],
    'schema_version':['DETERMINISTIC_POLICY'],
    'human_approved':['DETERMINISTIC_POLICY'],'published':['DETERMINISTIC_POLICY'],'model_calls':['DETERMINISTIC_POLICY']}

def checked_spec(value,service):
    raw=value.model_dump(mode='json') if hasattr(value,'model_dump') else value
    s=GovernedPedagogicalSpecification.model_validate(raw)
    if not service.validate_pedagogical_spec(s).valid or not all(supported(s,f) for f in CONTRACTS):
        raise ValueError('INVALID_OR_UNSUPPORTED_GOVERNED_SCOPE')
    if not any(r.role_key=='scope_framing' and r.family=='framing' and r.requirement=='required' for r in s.role_contract.roles):
        raise ValueError('SCOPE_FRAMING_NOT_REQUIRED')
    if any(c.observable_student_action not in LABELS for c in s.approved_evidence.success_criteria):
        raise ValueError('UNSUPPORTED_CAPABILITY_TEMPLATE')
    if not all(x in PROHIBITED for x in EXCLUSIONS.values()):raise ValueError('EXCLUSION_POLICY_CHANGED')
    return s

def render(intention,statements):
    return 'Learning focus: '+intention+'\nThis lesson is limited to: '+' '.join(statements)

def identity(value):
    raw=value.model_dump(mode='json') if hasattr(value,'model_dump') else dict(value)
    raw.pop('identity',None)
    return 'scope-'+hash_of(raw)
