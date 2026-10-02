"""Deterministic review presentation over P0 objects. No persisted approval flags."""
from dataclasses import asdict, dataclass
from validate_academic_knowledge_v03 import digest
from .core import decision_state, manifest
from .publication import participation
from .examples.q2 import ROOTS


@dataclass(frozen=True)
class BundleSpec:
    bundle_id: str
    subject: str
    roots: tuple[str, ...]
    optional_roots: tuple[str, ...] = ()
    participation: str = 'required in Q2-CORE'


BUNDLES = {
    'BUNDLE-Q2-A': BundleSpec('BUNDLE-Q2-A', 'Q2(a) Academic Interpretation', (ROOTS[0],)),
    'BUNDLE-Q2-B': BundleSpec('BUNDLE-Q2-B', 'Q2(b) Academic Interpretation', (ROOTS[1],)),
    'BUNDLE-Q2-C-PRIMARY': BundleSpec('BUNDLE-Q2-C-PRIMARY', 'Q2(c) Primary Academic Interpretation', (ROOTS[2],), (ROOTS[3],)),
    'BUNDLE-Q2-C-SECONDARY-CANDIDATE': BundleSpec('BUNDLE-Q2-C-SECONDARY-CANDIDATE',
        'Q2(c) Secondary Candidate Interpretation', (ROOTS[3],), participation='optional in Q2-CORE; required in Q2-WITH-SECONDARY'),
}


for _part in ('a','b-i','b-ii','c-i','c-ii'):
    _id='BUNDLE-Q3-2023-'+_part.upper()
    BUNDLES[_id]=BundleSpec(_id,'June 2023 Q3('+_part+') semantic proposal',
        ('proposal:PROPOSE-Q3-2023-'+_part,),participation='required in Q3-2023-CORE; unresolved blocks publication')


def label(record):
    p = record['payload']
    for name in ('name','skill_name','title','label','description','mapping_id','link_id','evidence_id','parsed_id','proposal_id','context_id'):
        if p.get(name): return p[name]
    return record['kind']


def object_view(graph, decisions, key):
    row = graph[key]; decision = decisions.get(key)
    return dict(key=key, kind=row['record']['kind'], label=label(row['record']), version=row['version'],
        state=decision_state(graph,key,decision), decision_id=decision['decision_id'] if decision else None)


def source_view(graph, decisions, keys):
    """References, metadata and bounded summaries, not copied PDF passages."""
    groups = []
    for key in sorted(k for k in keys if graph[k]['record']['kind']=='source'):
        p = graph[key]['record']['payload']
        group = dict(bundle_id='SOURCE-Q2-' + p['source_id'], subject=p['title'],
            source=object_view(graph,decisions,key), metadata={k:p[k] for k in
                ['source_type','curriculum_identity','version_label','identity_basis','artifact_reference','content_digest']}, locators=[])
        for lkey in sorted(k for k in keys if graph[k]['record']['kind']=='locator'):
            loc = graph[lkey]['record']['payload']
            if loc['source_id'] != p['source_id']: continue
            group['locators'].append(dict(**object_view(graph,decisions,lkey),
                page_number=loc['page_index']+1, anchor=loc['anchor'], region=loc['visual_region'],
                expected_content=loc['text_summary'], source_version=loc['source_version']))
        groups.append(group)
    return groups


def guard(graph, decisions, spec, versions):
    result = dict(bundle_id=spec.bundle_id, definition_version=digest(asdict(spec)),
        versions=versions, review_heads={k:decisions[k]['decision_id'] if k in decisions else None for k in versions})
    result['token'] = digest(result)
    return result


def require_current_ticket(expected, current):
    if not isinstance(expected,dict) or set(expected)!=set(current):
        raise ValueError('Invalid review ticket; save the inspected bundle ticket')
    token_data = {k:v for k,v in expected.items() if k!='token'}
    if digest(token_data)!=expected['token']:
        raise ValueError('Review ticket content hash mismatch')
    if expected == current: return
    changes = []
    for field in ('versions','review_heads'):
        previous = expected.get(field,{})
        if not isinstance(previous,dict): raise ValueError('Invalid review ticket '+field)
        for key in sorted(set(previous) | set(current[field])):
            if previous.get(key)!=current[field].get(key):
                changes.append(f'{key} {field}: expected {previous.get(key)}, current {current[field].get(key)}')
    raise ValueError('Bundle stale/conflict; inspect again. ' + ('; '.join(changes) or
        f"definition/token: expected {expected['token']}, current {current['token']}"))


def bundle_view(graph, decisions, spec, publication):
    if graph[spec.roots[0]]['record']['kind']=='proposal':
        from .proposal_review import proposal_view
        return proposal_view(graph,decisions,spec,publication)
    required, optional = participation(graph,spec.roots,spec.optional_roots)
    mapping = graph[spec.roots[0]]['record']['payload']
    s = mapping['semantics']
    parsed = graph['parsed_part:' + s['parsed_part_id']]['record']['payload']
    prompt = next(span['text'] for span in parsed['spans'] if span['role']=='prompt')
    prompt = ' '.join(prompt.split())
    return dict(bundle_id=spec.bundle_id, subject=spec.subject, participation=spec.participation,
        question_preview=prompt[:160] + ('…' if len(prompt)>160 else ''),
        concepts=[graph['concept:'+c]['record']['payload']['name'] for c in mapping['focus_concept_ids']],
        competency=graph['competency:'+mapping['canonical_id']]['record']['payload']['skill_name'], role=s['role'],
        task_conditions=[graph['task_condition:'+c]['record']['payload']['name'] for c in s['task_condition_ids']],
        interpretation_notes=mapping['rationale'], parse_warnings=parsed['warnings'],
        parsed_ranges=[{k:span[k] for k in ('role','locator_id','start','end')} for span in parsed['spans']],
        required_objects=[object_view(graph,decisions,k) for k in required],
        optional_candidate_objects=[object_view(graph,decisions,k) for k in optional],
        sources=source_view(graph,decisions,required),
        evidence_refs=mapping['evidence_ids'], parsed_part_ref='parsed_part:'+s['parsed_part_id'],
        evidence=[dict(evidence_id=eid,**{k:graph['evidence:'+eid]['record']['payload'][k]
            for k in ('source_locator_ids','content_kind','evidence_role','observation_status')}) for eid in mapping['evidence_ids']],
        source_verified=publication['source_verified'], human_approved=publication['human_approved'],
        publishable=publication['publishable'], blockers=publication['reasons'],
        stale_objects=[k for k in required if decision_state(graph,k,decisions.get(k))=='stale'],
        decision_scope=dict(approve=[k for k in required if graph[k]['record']['kind'] not in ('source','locator')],
            reject=list(spec.roots)),
        review_ticket=guard(graph,decisions,spec,required),
        notice='Inspection only. No recommended or automatic decision. Modify uses Service.stage; reject affects interpretation roots only.')
