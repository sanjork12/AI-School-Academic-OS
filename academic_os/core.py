"""Pure dependency and approval policy. No database/files/model calls at import."""
from validate_academic_knowledge_v03 import digest
from .models import normalise

def dependencies(record):
    k=record['kind'];p=record['payload'];refs=set(record['judgment_refs'])
    def add(kind,value):
        if value is not None:refs.add(kind+':'+value)
    for ref in p.get('provenance',{}).get('source_references',[]):
        if ref.startswith('locator:'):refs.add(ref)
    for ev in p.get('evidence_ids',[]):add('evidence',ev)
    if k=='locator':add('source',p['source_id'])
    if k=='question':
        add('source',p['paper_source_id']);add('locator',p['source_locator_id']);add('context',p['curriculum_context_id'])
    if k=='question_part':
        add('question',p['question_id']);add('locator',p['source_locator_id']);add('question_part',p['parent_part_id'])
    if k=='condition':
        add('question',p['question_id'])
        if p['resource_id'] is not None:raise ValueError('P0 resource-dependent conditions are not supported')
    if k=='part_mapping':
        add('question_part',p['part_id']);add('competency',p['canonical_id'])
        for cid in p['focus_concept_ids']:add('concept',cid)
        if p.get('semantics'):
            s=p['semantics'];add('parsed_part',s['parsed_part_id'])
            for cid in s['concept_link_ids']:add('concept_link',cid)
            for cid in s['task_condition_ids']:add('task_condition',cid)
    if k=='proposal':
        add('parsed_part',p['parsed_part_id']);add('competency',p['competency_id'])
        for cid in p['concept_ids']:add('concept',cid)
        for cid in p['concept_link_ids']:add('concept_link',cid)
        for cid in p['task_condition_ids']:add('task_condition',cid)
    if k=='concept_link':
        add('competency',p['canonical_id']);add('concept',p['concept_id'])
    if k=='evidence':
        for loc in p['source_locator_ids']:add('locator',loc)
        add(p['target']['kind'],p['target']['id']);add('context',p['context_id'])
        if p['objective_id'] is not None:raise ValueError('P0 uses located section labels, not unverified objective IDs')
    if k=='scope':
        add('context',p['context_id'])
        for loc in p['locator_ids']:add('locator',loc)
    if k=='parsed_part':
        add('question_part',p['part_id'])
        for span in p['spans']:add('locator',span['locator_id'])
    return sorted(refs)

def validate_graph(graph):
    for key,r in graph.items():
        actual,version,_=normalise(r['record'])
        if key!=actual or version!=r['version']:raise ValueError('Version digest mismatch: '+key)
        for dep in dependencies(r['record']):
            if dep not in graph:raise ValueError('Unknown dependency '+dep+' on '+key)
    for key,r in graph.items():
        rec=r['record'];p=rec['payload'];kind=rec['kind']
        if kind=='locator' and p['source_version']!=graph['source:'+p['source_id']]['version']:
            raise ValueError('Locator source version is stale: '+key)
        if kind=='proposal':
            parsed=graph['parsed_part:'+p['parsed_part_id']]['record']['payload']
            if graph['question_part:'+parsed['part_id']]['record']['payload']['node_kind']!='assessable':raise ValueError('Proposal must reference an assessable parsed part')
            for field in ('concept_ids','concept_link_ids','task_condition_ids'):
                if len(p[field])!=len(set(p[field])):raise ValueError('Duplicate proposal relationship')
            if p['candidate_action']=='unresolved':
                if p['competency_id'] is not None:raise ValueError('Unresolved proposal cannot assert a canonical competency')
                if not p['alternatives']:raise ValueError('Unresolved proposal needs explicit alternatives')
            else:
                if not p['competency_id'] or not p['concept_ids'] or not p['task_condition_ids']:
                    raise ValueError('Resolved proposal needs competency, concepts and task conditions')
                linked=set()
                for lid in p['concept_link_ids']:
                    link=graph['concept_link:'+lid]['record']['payload']
                    if link['canonical_id']!=p['competency_id']:raise ValueError('Proposal concept link competency mismatch')
                    linked.add(link['concept_id'])
                if linked!=set(p['concept_ids']):raise ValueError('Proposal concept links must cover its concepts')
        if kind=='part_mapping':
            part=graph['question_part:'+p['part_id']]['record']['payload']
            if part['node_kind']!='assessable':raise ValueError('Container cannot be assessed')
            if not p['evidence_ids']:raise ValueError('Mapping must cite evidence')
            for eid in p['evidence_ids']:
                ev=graph['evidence:'+eid]['record']['payload']
                if ev['target']!={'kind':'part_mapping','id':p['mapping_id']}:raise ValueError('Evidence target mismatch')
            if p.get('semantics'):
                semantic=p['semantics']
                parsed=graph['parsed_part:'+semantic['parsed_part_id']]['record']['payload']
                if parsed['part_id']!=p['part_id']:raise ValueError('Semantic mapping parsed part mismatch')
                concepts=set()
                for lid in semantic['concept_link_ids']:
                    link=graph['concept_link:'+lid]['record']['payload']
                    if link['canonical_id']!=p['canonical_id']:raise ValueError('Semantic concept link competency mismatch')
                    concepts.add(link['concept_id'])
                if concepts!=set(p['focus_concept_ids']):raise ValueError('Semantic focus concepts must match concept relationships')
                for field in ['concept_link_ids','task_condition_ids']:
                    if len(set(semantic[field]))!=len(semantic[field]):raise ValueError('Duplicate semantic reference')
        if kind=='task_condition':
            for ref in p['provenance']['source_references']:
                if not ref.startswith('locator:'):raise ValueError('Task condition provenance requires a locator')
                loc=graph[ref]['record']['payload']
                source=graph['source:'+loc['source_id']]['record']['payload']
                if source['origin']!=p['provenance']['origin']:raise ValueError('Task condition provenance origin mismatch')
        if kind=='question_part' and p['parent_part_id'] is not None:
            parent=graph['question_part:'+p['parent_part_id']]['record']['payload']
            if parent['node_kind']!='container' or parent['question_id']!=p['question_id']:raise ValueError('Invalid part parent')
        if kind=='parsed_part':
            part=graph['question_part:'+p['part_id']]['record']['payload']
            roles=[s['role'] for s in p['spans']]
            if any(roles.count(role)!=1 for role in ['prompt','mark_scheme','shared_stem']):
                raise ValueError('Parsed part needs one prompt, scheme and shared stem')
            for span in p['spans']:
                loc=graph['locator:'+span['locator_id']]
                lp=loc['record']['payload']
                if loc['version']!=span['locator_version']:raise ValueError('Parsed span locator version is stale')
                if span['end']>len(lp['extracted_text']) or lp['extracted_text'][span['start']:span['end']]!=span['text']:
                    raise ValueError('Parsed span differs from located original text')
                if lp['assessment_question_id']!=part['question_id'] or lp['assessment_part_id'] not in (None,p['part_id']):
                    raise ValueError('Parsed span refers to another question/part')
                source=graph['source:'+lp['source_id']]['record']['payload']
                required_type='official_mark_scheme' if span['role'] in ('mark_scheme','mark_scheme_notes') else 'official_past_paper'
                if source['source_type']!=required_type:
                    raise ValueError('Parsed span source type does not match its role')

def manifest(graph, roots):
    if not roots:raise ValueError('Empty selection cannot be published')
    seen=set();todo=list(roots)
    while todo:
        key=todo.pop()
        if key in seen:continue
        if key not in graph:raise ValueError('Unknown object '+key)
        seen.add(key);todo.extend(dependencies(graph[key]['record']))
        # New contradictory evidence about a target is relevant even when its author
        # did not add it to the target's supporting evidence_ids.
        for other,row in graph.items():
            if row['record']['kind']=='evidence':
                t=row['record']['payload']['target']
                if t['kind']+':'+t['id']==key:todo.append(other)
    return {key:graph[key]['version'] for key in sorted(seen)}

def decision_state(graph,key,decision):
    if decision is None:return 'pending'
    if decision['action'] in ['revoke','reject','revise']:return decision['action']
    if decision['dependency_digest']!=digest(manifest(graph,[key])):return 'stale'
    return decision['action']

def evaluate(graph, roots, decisions, integrity_errors):
    selected=manifest(graph,roots);reasons=list(integrity_errors);source_ok=not integrity_errors;human_ok=True
    for key in selected:
        r=graph[key]['record'];p=r['payload'];state=decision_state(graph,key,decisions.get(key))
        expected='verify' if r['kind'] in ['source','locator'] else 'approve'
        if state!=expected:
            reasons.append(f'{key}: {state}; requires {expected}')
            if expected=='verify':source_ok=False
            else:human_ok=False
        if r['kind']=='proposal' and p['candidate_action']=='unresolved':reasons.append(key+': unresolved canonical identity; explicit revision and review required')
        if r['kind']=='scope' and p['association_status']=='unresolved':reasons.append(key+': unresolved scope')
        if r['kind']=='evidence' and (p['evidence_role']=='contradicts' or p['observation_status']!='observed'):
            reasons.append(key+': blocking conflict or unresolved evidence')
        if r['kind']=='part_mapping' and p['assessment_extent']=='undetermined':reasons.append(key+': assessment extent unresolved')
    return dict(schema_valid=True,source_verified=source_ok,human_approved=human_ok,
                publishable=not reasons,reasons=reasons,versions=selected)
