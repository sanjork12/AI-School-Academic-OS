"""Bounded SL-10 source identity checks. No arithmetic inference or parser changes."""
from .expressions import FIELDS, ExpressionError, context_for, parse

VERSION = 'sl10-derivation-provenance/1'
LEGACY_POLICY = 'sl10-expression-required/1'
POLICY = 'sl10-provenance-required/1'
POLICIES = (LEGACY_POLICY, POLICY)
STATUSES = ('PASSED', 'FAILED', 'INSUFFICIENT_EVIDENCE', 'NOT_EVALUATED')

# Application-owned dependencies; values always come from context_for(), never claims.
DEPENDENCIES = {
    'n': ('proposed_math_inputs.n',),
    'sum_x': ('proposed_math_inputs.sum_x',),
    'sum_x2': ('proposed_math_inputs.sum_x2',),
    'first_term': ('sum_x2', 'n'),
    'second_term': ('sum_x', 'n'),
    'radicand': ('first_term', 'second_term'),
}
ROLE_EXPRESSIONS = {
    'first_term': ('sum_x2 / n',),
    'second_term': ('(sum_x / n)^2',),
    'mean': ('sum_x / n',),
    'variance': ('first term - second term', 'sum_x2 / n - (sum_x / n)^2'),
}
SELF_REFERENCES = {'first_term': {'first_term'}, 'second_term': {'second_term'},
                   'mean': set(), 'variance': {'radicand'}}


def require_policy(policy):
    if policy not in POLICIES:
        raise ValueError('Unknown application-owned acceptance policy')
    return policy


def walk(ast, path='$'):
    yield path, ast
    for key in ('left', 'right', 'arg'):
        if key in ast:
            yield from walk(ast[key], path+'.'+key)


def shape(ast):
    """Erase names only for diagnosing a rejected tree, never for acceptance."""
    return (ast['op'], *(shape(ast[k]) for k in ('left', 'right', 'arg') if k in ast))


def outcome(status):
    return True if status == 'PASSED' else False if status == 'FAILED' else None


def verify_solution_provenance(content, *, historical=False, semantics=None):
    """Identity first; historic literal absence is not an evaluated identity violation.

    Semantics is contextual evidence only and cannot change a provenance decision.
    Callers must separately enforce schema, encoding, arithmetic and solution gates.
    """
    context, expected = context_for(content['proposed_math_inputs'])
    checks = {}
    for field in FIELDS:
        expression = content['proposed_solution'][field]['expression']
        templates = [parse(text) for text in ROLE_EXPRESSIONS[field]]
        row = dict(field='proposed_solution.'+field, expression=expression, ast=None,
                   expected_semantic_role=field, expected_dependency_structure=templates,
                   expected_value=str(expected[field]), resolved_symbolic_sources=[],
                   status='FAILED', valid=False, reason=None, verifier_version=VERSION,
                   policy=POLICY, evidence_mode='historical' if historical else 'current',
                   expression_semantics_valid=(semantics['checks'][field]['valid'] if semantics else None))
        try:
            ast = parse(expression)
            row['ast'] = ast
            nodes = list(walk(ast))
            symbols = {node['name'] for _, node in nodes if node['op'] == 'variable'}
            row['resolved_symbolic_sources'] = [dict(ast_path=path, name=node['name'],
                value=str(context[node['name']]), dependencies=list(DEPENDENCIES[node['name']]))
                for path, node in nodes if node['op'] == 'variable']
            if symbols & SELF_REFERENCES[field]:
                reason = 'provenance_self_reference'
            elif any(node['op'] == 'constant' for _, node in nodes):
                reason = ('provenance_insufficient_historical_evidence' if historical
                          else 'provenance_literal_source_unidentified')
                if historical:
                    row['status'] = 'INSUFFICIENT_EVIDENCE'
            elif ast in templates:
                row['status'] = 'PASSED'
                reason = 'provenance_verified'
            elif field == 'variance' and ast.get('op') == 'subtract' and any(
                    ast['left'] == t['right'] and ast['right'] == t['left'] for t in templates):
                reason = 'provenance_swapped_operands'
            elif any(shape(ast) == shape(t) for t in templates):
                reason = 'provenance_wrong_source'
            else:
                reason = 'provenance_wrong_structure'
            row['reason'] = reason
        except ExpressionError as exc:
            row['reason'] = 'provenance_unsupported_for_role'
            row['expression_error'] = exc.code
        row['valid'] = outcome(row['status'])
        checks[field] = row
    statuses = {c['status'] for c in checks.values()}
    status = next((s for s in ('FAILED', 'INSUFFICIENT_EVIDENCE', 'NOT_EVALUATED') if s in statuses), 'PASSED')
    return dict(verifier_version=VERSION, policy=POLICY, status=status,
                derivation_provenance_valid=outcome(status), dependency_map={k:list(v) for k,v in DEPENDENCIES.items()},
                checks=checks, scope='Four intermediate derivations only; no candidate square-root expression, pedagogy or academic approval.')
