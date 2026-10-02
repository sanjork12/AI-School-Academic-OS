"""Deterministic candidate inspection, never a trusted snapshot read."""
from .core import decision_state
from .examples.q2_semantics import ASSIGNMENTS, COMPETENCIES, CONCEPTS, CONDITIONS, concept_id


def q2_report(graph, decisions, publication):
    parts = []
    errors = []
    for label in 'abc':
        pid = 'Q2-' + label
        mappings = []
        for key, row in sorted(graph.items()):
            p = row['record']['payload']
            if row['record']['kind'] != 'part_mapping' or p['part_id'] != pid:
                continue
            s = p.get('semantics')
            if not s:
                errors.append(key + ': semantic annotation missing')
                continue
            competency = graph['competency:' + p['canonical_id']]['record']['payload']
            mappings.append(dict(mapping_id=p['mapping_id'], role=s['role'],
                competency_id=p['canonical_id'], competency=competency['skill_name'],
                concept_ids=sorted(p['focus_concept_ids']),
                concepts=sorted(graph['concept:' + cid]['record']['payload']['name'] for cid in p['focus_concept_ids']),
                task_condition_ids=s['task_condition_ids'],
                task_conditions=[graph['task_condition:' + cid]['record']['payload']['name'] for cid in s['task_condition_ids']],
                candidate_status=p['review_status'], approval_status=decision_state(graph, key, decisions.get(key)),
                competency_approval=decision_state(graph, 'competency:' + p['canonical_id'], decisions.get('competency:' + p['canonical_id'])),
                parsed_part_id=s['parsed_part_id']))
        expected = [a for a in ASSIGNMENTS if a[0] == label]
        if len(mappings) != len(expected):
            errors.append(pid + ': unexpected number of semantic mappings')
        for _, suffix, role, condition in expected:
            matching = [m for m in mappings if m['competency_id'] == 'CAN-STAT-' + suffix and m['role'] == role]
            if len(matching) != 1:
                errors.append(pid + ': missing/ambiguous ' + role + ' ' + suffix)
                continue
            m = matching[0]
            if (m['concept_ids'] != sorted(concept_id(c) for c in COMPETENCIES[suffix][2])
                or m['concepts'] != sorted(CONCEPTS[c][0] for c in COMPETENCIES[suffix][2])
                or m['task_condition_ids'] != [condition] or m['task_conditions'] != [CONDITIONS[condition][0]]
                or m['competency'] != COMPETENCIES[suffix][0]):
                errors.append(pid + ': Gold Standard semantic values differ')
        mappings.sort(key=lambda m:(m['role']!='primary',m['mapping_id']))
        parts.append(dict(part_id=pid, mappings=mappings))
    return dict(view='candidate_architecture_report_not_trusted_snapshot',
        architecture_valid=not errors and publication['schema_valid'], validation_errors=errors,
        parts=parts, publication=publication,
        approval_states={k:decision_state(graph,k,decisions.get(k)) for k in sorted(publication['versions'])},
        notice='Gold Standard is an acceptance fixture, not a production approval. Trusted reads require Service.snapshot.')
