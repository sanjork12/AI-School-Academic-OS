"""Human-defined P1A acceptance fixture, always submitted as candidates.

No parser output or source text is regenerated here. Existing identities and
evidence are retained; approvals can only be added by the operator service.
"""
from copy import deepcopy
from academic_os.models import normalise

CONCEPTS = {
    'MEAN': ('Mean', 'The arithmetic average of observations.'),
    'SD': ('Standard deviation', 'A measure of dispersion about the mean in the units of the observations.'),
    'SPREAD': ('Variation / spread', 'The dispersion of values within a distribution.'),
    'EXTREMES': ('Extreme values', 'Values toward the ends of a distribution.'),
}
COMPETENCIES = {
    'MEAN-CALC': ('Calculate the mean', 'Calculate the arithmetic mean of observations.', ['MEAN']),
    'SD-CALC': ('Calculate standard deviation', 'Calculate the standard deviation of a distribution.', ['SD']),
    'VARIATION-INTERPRET': ('Interpret measures of variation', 'Interpret measures of dispersion and their implications without claiming guarantees about individual extremes.', ['SD', 'SPREAD']),
    'CONTEXT-INFER': ('Make contextual inferences using statistical evidence', 'Use statistical evidence to draw qualified contextual inferences.', ['SD', 'SPREAD', 'EXTREMES']),
}
CONDITIONS = {
    'TC-SUMMARY-STATISTICS': ('From summary statistics', 'input_form', 'The requested calculation uses supplied summary statistics.'),
    'TC-COMPARE-VARIATION-SD': ('Compare variation using standard deviation', 'comparison_form', 'Compare two groups or distributions using standard deviation in a contextual decision.'),
}
ASSIGNMENTS = [('a', 'MEAN-CALC', 'primary', 'TC-SUMMARY-STATISTICS'),
               ('b', 'SD-CALC', 'primary', 'TC-SUMMARY-STATISTICS'),
               ('c', 'VARIATION-INTERPRET', 'primary', 'TC-COMPARE-VARIATION-SD'),
               ('c', 'CONTEXT-INFER', 'secondary', 'TC-COMPARE-VARIATION-SD')]


def concept_id(suffix):
    return 'CON-STAT-' + suffix


def link_id(competency, concept):
    return 'LINK-' + competency + '-' + concept


def build_plan(graph):
    items = []
    def provenance(*locators):
        return dict(origin='real', creation_method='rule', source_references=['locator:' + x for x in locators])

    for suffix, (name, description) in CONCEPTS.items():
        locs = ['SPEC-2.3'] if suffix != 'EXTREMES' else ['MS-Q2-c']
        items.append(dict(kind='concept', payload=dict(concept_id=concept_id(suffix), subject_domain='Statistics',
                     name=name, description=description, provenance=provenance(*locs))))
    for suffix, (name, description, concepts) in COMPETENCIES.items():
        record = deepcopy(graph['competency:CAN-STAT-' + suffix]['record'])
        record['payload'].update(skill_name=name, description=description)
        items.append(record)
        for concept in concepts:
            items.append(dict(kind='concept_link', payload=dict(link_id=link_id(suffix, concept),
                canonical_id='CAN-STAT-' + suffix, concept_id=concept_id(concept),
                rationale='P1A human-defined acceptance fixture: the capability applies this concept; academic review remains required.',
                provenance=record['payload']['provenance'])))
    for cid, (name, kind, description) in CONDITIONS.items():
        items.append(dict(kind='task_condition', payload=dict(condition_id=cid, name=name, kind=kind,
                     description=description, provenance=provenance('QP-Q2'))))
    for part, competency, role, condition in ASSIGNMENTS:
        parsed_id = 'PARSED-Q2-' + part
        if graph['parsed_part:' + parsed_id]['record']['payload']['part_id'] != 'Q2-' + part:
            raise ValueError('P1A requires the existing matching parsed Q2 record')
        mapping_id = 'MAP-Q2-' + part + '-' + competency
        record = deepcopy(graph['part_mapping:' + mapping_id]['record'])
        p = record['payload']
        if p['part_id'] != 'Q2-' + part or p['canonical_id'] != 'CAN-STAT-' + competency:
            raise ValueError('Existing Q2 mapping identity differs from P1A fixture')
        concepts = COMPETENCIES[competency][2]
        p['focus_concept_ids'] = [concept_id(c) for c in concepts]
        p['semantics'] = dict(role=role, parsed_part_id=parsed_id,
            concept_link_ids=[link_id(competency, c) for c in concepts], task_condition_ids=[condition])
        # Keep evidence, source references, parser dependency and curriculum scope.
        if competency == 'VARIATION-INTERPRET':
            record = correct_primary_boundary(record)
        items.append(record)
    return dict(items=items, expected_heads={normalise(x)[0]: graph.get(normalise(x)[0], {}).get('version') for x in items})


PRIMARY_KEY = 'part_mapping:MAP-Q2-c-VARIATION-INTERPRET'
BOUNDARY_NOTE = ('Q2(c) question-specific mark-scheme reasoning uses larger SD, greater spread and more extreme values '
                 'to support the possibility of faster times and Coach B; this does not establish a universal '
                 'canonical dependency on Extreme values, or guarantee individual extremes.')


def correct_primary_boundary(record):
    """Revise only the primary mapping; retain question-specific reasoning."""
    record = deepcopy(record)
    p = record['payload']
    if (record['kind'] != 'part_mapping' or p['mapping_id'] != PRIMARY_KEY.split(':', 1)[1]
            or p['canonical_id'] != 'CAN-STAT-VARIATION-INTERPRET'
            or p['semantics']['role'] != 'primary'):
        raise ValueError('Expected Q2(c) primary variation mapping')
    p['focus_concept_ids'] = [c for c in p['focus_concept_ids'] if c != 'CON-STAT-EXTREMES']
    p['semantics']['concept_link_ids'] = [c for c in p['semantics']['concept_link_ids']
                                        if c != 'LINK-VARIATION-INTERPRET-EXTREMES']
    if BOUNDARY_NOTE not in p['rationale']:
        p['rationale'] += ' ' + BOUNDARY_NOTE
    return record


def build_boundary_correction(graph):
    """Existing stage/CAS plan; no deletion, review, or publication side effects.

    Historical concept links stay in immutable storage, outside the current
    primary required closure. Do not rebuild/stage unrelated approved objects.
    """
    row = graph[PRIMARY_KEY]
    return dict(items=[correct_primary_boundary(row['record'])],
                expected_heads={PRIMARY_KEY: row['version']})
