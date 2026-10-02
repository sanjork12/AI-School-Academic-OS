"""Target-specific publication governance, separate from academic review.

Events live in the existing immutable requests journal, distinguished by a
service-owned record_type. Candidate JSON cannot create journal receipts.
No schema migration or mutable flag is needed; current heads are derived.
"""
import json
from .core import manifest,validate_graph
from .sources import integrity
from .review_bundles import BundleSpec,guard,require_current_ticket
from .storage import now
from validate_academic_knowledge_v03 import digest

RECORD_TYPE='publication_governance/1'


def history(store):
    # requests is append-only (existing DB triggers). No reliance on candidate fields.
    events=[]
    for row in store.db.execute('SELECT result FROM requests ORDER BY rowid'):
        result=json.loads(row['result'])
        if result.get('record_type')==RECORD_TYPE:events.append(result)
    return events


def heads(store):
    return {(e['target_id'],e['proposal_key']):e for e in history(store)}


def event_state(graph,target,key,event):
    if event is None:return 'none'
    if event['action']=='reopen':return 'reopened'
    if (event['target_version']!=target.version or key not in target.required_roots
        or key not in graph or graph[key]['record']['kind']!='proposal'
        or graph[key]['record']['payload']['candidate_action']!='unresolved'):
        return 'stale'
    if event['versions']!=manifest(graph,[key]) or integrity(graph,event['versions']):return 'stale'
    return 'deferred'


def selection(store,graph,target):
    current=heads(store);deferred=[];states=[]
    for key in target.required_roots:
        event=current.get((target.target_id,key));state=event_state(graph,target,key,event)
        if event:states.append(dict(proposal_key=key,state=state,decision_id=event['request_id']))
        if state=='deferred':deferred.append(event)
    roots=tuple(k for k in target.required_roots if k not in {e['proposal_key'] for e in deferred})
    # Remove roots, never subtract shared/transitive dependencies from a closure.
    required=manifest(graph,roots) if roots else {}
    effective=[e for e in deferred if e['proposal_key'] not in required]
    for item in states:
        if item['state']=='deferred' and item['proposal_key'] in required:item['state']='required_by_dependency'
    return dict(roots=roots,deferrals=effective,states=states)


def ticket(graph,decisions,target,key,event):
    spec=BundleSpec('UNRESOLVED:'+target.target_id+':'+key,'Publication governance',
                    (key,),participation=target.version)
    result=guard(graph,decisions,spec,manifest(graph,[key]))
    result.update(target_id=target.target_id,target_version=target.version,
                  governance_head=event['request_id'] if event else None)
    result['token']=digest({k:v for k,v in result.items() if k!='token'})
    return result


def require_ticket(expected,current):
    # Same P1B body-integrity/version/head CAS contract, with target-specific context.
    try:require_current_ticket(expected,current)
    except ValueError as exc:
        details=[]
        if isinstance(expected,dict):
            for field in ('target_version','governance_head'):
                if expected.get(field)!=current[field]:details.append(f'{field}: expected {expected.get(field)}, current {current[field]}')
        raise ValueError(str(exc)+('; '+'; '.join(details) if details else '')) from exc


def inspect(service,target_id,key):
    from .publication import TARGETS
    target=TARGETS[target_id]
    with service.store.transaction('DEFERRED'):
        graph=service.store.graph();decisions=service.store.decisions();validate_graph(graph)
        if key not in target.required_roots:raise ValueError('Proposal is not a declared required root of this target')
        if graph[key]['record']['kind']!='proposal':raise ValueError('Governance requires an academic proposal')
        p=graph[key]['record']['payload'];event=heads(service.store).get((target_id,key))
        state=event_state(graph,target,key,event);selected=selection(service.store,graph,target)
        effective=any(e['proposal_key']==key for e in selected['deferrals'])
        return dict(proposal_key=key,proposal_version=graph[key]['version'],target_id=target_id,target_version=target.version,
            academic_state=p['candidate_action'],observation=p['observation'],alternatives=p['alternatives'],evidence_scope=p['evidence_scope'],
            governance_state=state,governance_event=event,
            participation='DEFERRED FROM '+target_id if effective else 'REQUIRED — currently blocking '+target_id if p['candidate_action']=='unresolved' else 'REQUIRED — normal academic review applies',
            review_ticket=ticket(graph,decisions,target,key,event),
            history=[e for e in history(service.store) if e['target_id']==target_id and e['proposal_key']==key],
            notice='Inspection only. Defer changes target participation, never academic truth or source verification.')


def decide(service,target_id,key,action,reviewer,reason,expected_ticket,request_id):
    from .publication import TARGETS
    if action not in ('defer','reopen'):raise ValueError('Governance action must be explicit defer or reopen')
    if not reviewer.strip() or not reason.strip():raise ValueError('Reviewer and reason must be nonempty')
    target=TARGETS[target_id]
    rd=digest(dict(operation='publication_governance',target_id=target_id,proposal_key=key,action=action,
                   reviewer=reviewer,reason=reason,ticket=expected_ticket))
    with service.store.transaction():
        cached=service.store.retry(request_id,rd)
        if cached is not None:return cached
        graph=service.store.graph();decisions=service.store.decisions();validate_graph(graph)
        if key not in target.required_roots or graph[key]['record']['kind']!='proposal':
            raise ValueError('Only a declared proposal root can be deferred from this target')
        previous=heads(service.store).get((target_id,key))
        require_ticket(expected_ticket,ticket(graph,decisions,target,key,previous))
        if action=='defer':
            if graph[key]['record']['payload']['candidate_action']!='unresolved':raise ValueError('Only unresolved academic proposals can be deferred')
            errors=integrity(graph,manifest(graph,[key]))
            if errors:raise ValueError('Defer evidence integrity failed: '+'; '.join(errors))
        elif previous is None:raise ValueError('Cannot reopen without a governance decision')
        event=dict(record_type=RECORD_TYPE,target_id=target_id,target_version=target.version,proposal_key=key,
                   proposal_version=graph[key]['version'],versions=manifest(graph,[key]),action=action,
                   reviewer=reviewer,reason=reason,created_at=now(),request_id=request_id,
                   supersedes=previous['request_id'] if previous else None,reviewed_ticket=expected_ticket)
        # Reopening/replacing a decision immediately withdraws snapshots that used it.
        # Content/dependency changes are also checked by Service.snapshot on every read.
        if previous:
            for row in service.store.db.execute('SELECT snapshot_id,payload FROM snapshots'):
                payload=json.loads(row['payload'])
                if any(e['target_id']==target_id and e['proposal_key']==key for e in payload.get('publication_governance',[])):
                    service.store.db.execute('INSERT OR IGNORE INTO snapshot_blocks VALUES(?,?,?,?)',
                        (row['snapshot_id'],'governance:'+request_id,'Publication governance superseded/reopened',now()))
        service.store.remember(request_id,rd,event)
        return event
