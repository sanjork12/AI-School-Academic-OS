"""Small explicit publication policies; participation is NOT a mapping role.

Required roots use P0's unchanged transitive manifest. Optional roots describe
separate explorations; they never subtract anything from the required closure.
"""
from dataclasses import asdict, dataclass
from validate_academic_knowledge_v03 import digest
from .core import manifest
from .examples.q2 import ROOTS


@dataclass(frozen=True)
class PublicationTarget:
    target_id: str
    title: str
    required_roots: tuple[str, ...]
    optional_roots: tuple[str, ...] = ()

    def definition(self):
        result = asdict(self)
        result['required_roots'] = list(self.required_roots)
        result['optional_roots'] = list(self.optional_roots)
        return result

    @property
    def version(self):
        return digest(self.definition())


TARGETS = {
    'Q2-CORE': PublicationTarget('Q2-CORE', 'Q2 core academic interpretation', tuple(ROOTS[:3]), (ROOTS[3],)),
    'Q2-WITH-SECONDARY': PublicationTarget('Q2-WITH-SECONDARY', 'Q2 including contextual inference', tuple(ROOTS)),
}


TARGETS['Q3-2023-CORE']=PublicationTarget('Q3-2023-CORE','June 2023 Q3 complete reviewed interpretation',
    tuple('proposal:PROPOSE-Q3-2023-'+p for p in ('a','b-i','b-ii','c-i','c-ii')))


def participation(graph, required_roots, optional_roots):
    required = manifest(graph, required_roots)
    optional = manifest(graph, optional_roots) if optional_roots else {}
    return required, {k:v for k,v in optional.items() if k not in required}


def semantic_units(objects):
    """Only called on the validated required snapshot objects, never staging."""
    units = {}
    for key, row in sorted(objects.items()):
        p = row['payload']
        if row['kind']=='proposal':
            if p['candidate_action']=='unresolved':raise ValueError('Unresolved proposal cannot materialize')
            parsed=objects['parsed_part:'+p['parsed_part_id']]['payload'];part=parsed['part_id']
            units[part]=dict(part_id=part,question=objects['question_part:'+part]['payload']['label'],interpretations=[dict(
                mapping_id=p['proposal_id'],role='primary',competency=dict(id=p['competency_id'],name=objects['competency:'+p['competency_id']]['payload']['skill_name']),
                concepts=[dict(id=c,name=objects['concept:'+c]['payload']['name']) for c in p['concept_ids']],
                task_conditions=[dict(id=c,name=objects['task_condition:'+c]['payload']['name']) for c in p['task_condition_ids']],
                parsed_part_ref='parsed_part:'+p['parsed_part_id'],evidence_refs=sorted(set('locator:'+s['locator_id'] for s in parsed['spans'])),evidence_scope=p['evidence_scope'])])
            continue
        if row['kind'] != 'part_mapping' or not p.get('semantics'):
            continue
        s = p['semantics']; part = p['part_id']
        competency = objects['competency:' + p['canonical_id']]['payload']
        unit = units.setdefault(part, dict(part_id=part,
            question=objects['question_part:' + part]['payload']['label'], interpretations=[]))
        unit['interpretations'].append(dict(mapping_id=p['mapping_id'], role=s['role'],
            competency=dict(id=p['canonical_id'], name=competency['skill_name']),
            concepts=[dict(id=c, name=objects['concept:' + c]['payload']['name']) for c in p['focus_concept_ids']],
            task_conditions=[dict(id=c, name=objects['task_condition:' + c]['payload']['name']) for c in s['task_condition_ids']],
            parsed_part_ref='parsed_part:' + s['parsed_part_id'],
            evidence_refs=['evidence:' + e for e in p['evidence_ids']]))
    for unit in units.values():
        unit['interpretations'].sort(key=lambda x:(x['role']!='primary', x['mapping_id']))
    return [units[k] for k in sorted(units)]
