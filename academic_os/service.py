"""Application service shared by the CLI and a future API.

The caller is a trusted local operator. Candidate documents are untrusted.
OS/DB owners can bypass local controls; this is not production authentication.
"""
import json
import os
from copy import deepcopy
from pathlib import Path
from validate_academic_knowledge_v03 import digest
from .models import normalise
from .core import validate_graph,manifest,decision_state,evaluate
from .sources import integrity
from .compatibility import validate_v03
from .storage import canonical,now

class Service:
    def __init__(self,store):self.store=store

    def stage(self,items,expected_heads,request_id):
        """Atomic batch CAS. Caller must state old version, or None for new IDs."""
        normalized=[normalise(x) for x in items]
        if len({x[0] for x in normalized})!=len(normalized):raise ValueError('Duplicate object in batch')
        if set(expected_heads)!={x[0] for x in normalized}:raise ValueError('Expected heads must cover exactly the batch')
        request_digest=digest(dict(op='stage',items=items,expected_heads=expected_heads))
        with self.store.transaction():
            cached=self.store.retry(request_id,request_digest)
            if cached is not None:return cached
            graph=self.store.graph();changed=[]
            for key,version,record in normalized:
                old=graph.get(key,{}).get('version')
                if old!=expected_heads[key]:raise ValueError(f'Version conflict for {key}: expected {expected_heads[key]}, current {old}')
                graph[key]=dict(version=version,record=record)
                if old!=version:changed.append(key)
            validate_graph(graph)
            # Schema/references in staging are independent of trusted review state.
            validate_v03(graph,{})
            errors=integrity(graph,[k for k,_,_ in normalized])
            if errors:raise ValueError('; '.join(errors))
            for key,version,record in normalized:
                self.store.db.execute('INSERT OR IGNORE INTO versions VALUES(?,?,?,?)',(key,version,canonical(record),now()))
                self.store.db.execute('INSERT INTO heads VALUES(?,?) ON CONFLICT(object_key) DO UPDATE SET version=excluded.version',(key,version))
            self.store.invalidate(changed,'stage:'+request_id,'Content or declared dependencies changed')
            result={key:version for key,version,_ in normalized}
            self.store.remember(request_id,request_digest,result)
            return result

    def inspect(self,key=None):
        with self.store.transaction('DEFERRED'):
            graph=self.store.graph();reviews=self.store.decisions();result=[]
            for k in ([key] if key else sorted(graph)):
                if k not in graph:raise ValueError('Unknown object '+k)
                dep=manifest(graph,[k]);d=reviews.get(k)
                item=dict(key=k,version=graph[k]['version'],state=decision_state(graph,k,d),
                    expected_decision=d['decision_id'] if d else None,dependency_digest=digest(dep),dependencies=dep)
                if key:
                    item['record']=graph[k]['record']
                    item['evidence_bundle']={x:graph[x] for x in dep if x!=k}
                    item['history']=[dict(r) for r in self.store.db.execute('SELECT * FROM reviews WHERE object_key=? ORDER BY rowid',(k,))]
                result.append(item)
            return result[0] if key else result

    def plan_q2(self):
        from .mapping import plan_q2
        with self.store.transaction('DEFERRED'):
            graph=self.store.graph()
            validate_graph(graph)
            errors=integrity(graph,graph)
            if errors:raise ValueError('; '.join(errors))
            return plan_q2(graph)

    def plan_q2_semantics(self):
        from .examples.q2_semantics import build_plan
        with self.store.transaction('DEFERRED'):
            graph=self.store.graph();validate_graph(graph)
            errors=integrity(graph,graph)
            if errors:raise ValueError('; '.join(errors))
            return build_plan(graph)

    def q2_semantics_report(self):
        from .semantic_report import q2_report
        from .examples.q2 import ROOTS
        with self.store.transaction('DEFERRED'):
            graph=self.store.graph();decisions=self.store.decisions()
            validate_graph(graph)
            return q2_report(graph,decisions,self._check(graph,ROOTS,decisions))

    def review_sources(self):
        from .source_bundles import ALL_SOURCE_BUNDLES as SOURCE_BUNDLES,source_bundle_view
        with self.store.transaction('DEFERRED'):
            graph=self.store.graph();decisions=self.store.decisions();validate_graph(graph)
            return [source_bundle_view(graph,decisions,s) for s in SOURCE_BUNDLES.values() if all(k in graph for k in s.roots)]

    def review_source(self,bundle_id):
        from .source_bundles import ALL_SOURCE_BUNDLES as SOURCE_BUNDLES,source_bundle_view
        with self.store.transaction('DEFERRED'):
            graph=self.store.graph();decisions=self.store.decisions();validate_graph(graph)
            return source_bundle_view(graph,decisions,SOURCE_BUNDLES[bundle_id])

    def review_source_bundle(self,bundle_id,action,reviewer,reason,expected_ticket,request_id):
        """Explicit local-operator action, atomically delegated to P0 review.

        Verify and reject both cover the source and every included locator.
        Existing valid verifications are reused, never academic approvals.
        """
        from .source_bundles import ALL_SOURCE_BUNDLES as SOURCE_BUNDLES,source_versions
        from .review_bundles import guard,require_current_ticket
        if action not in ('verify','reject'):raise ValueError('Source bundle action must be verify or reject')
        if not reviewer.strip() or not reason.strip():raise ValueError('Reviewer and reason must be nonempty')
        spec=SOURCE_BUNDLES[bundle_id]
        rd=digest(dict(operation='review_source_bundle',bundle_id=bundle_id,action=action,
                       reviewer=reviewer,reason=reason,expected_ticket=expected_ticket))
        with self.store.transaction():
            cached=self.store.retry(request_id,rd)
            if cached is not None:return cached
            graph=self.store.graph();decisions=self.store.decisions();validate_graph(graph)
            versions=source_versions(graph,spec)
            require_current_ticket(expected_ticket,guard(graph,decisions,spec,versions))
            if action=='verify':
                errors=integrity(graph,versions)
                if errors:raise ValueError('Source verification blocked: '+'; '.join(errors))
            created=[];reused=[]
            # P0 requires source identity verification before locator verification.
            keys=sorted(versions,key=lambda k:(graph[k]['record']['kind']!='source',k))
            for key in keys:
                previous=decisions.get(key)
                if action=='verify' and decision_state(graph,key,previous)=='verify':
                    reused.append(dict(key=key,decision_id=previous['decision_id']))
                    continue
                child_id='source-bundle-object-'+digest(dict(request_id=request_id,key=key))
                created.append(self.review(key,action,reviewer,
                    f'Source bundle {bundle_id}; request {request_id}: {reason}',
                    graph[key]['version'],digest(manifest(graph,[key])),
                    previous['decision_id'] if previous else None,child_id))
            result=dict(bundle_id=bundle_id,action=action,request_id=request_id,reviewer=reviewer,
                        reason=reason,created_at=now(),reviewed_ticket=expected_ticket,
                        created=created,reused=reused)
            self.store.remember(request_id,rd,result)
            return result

    def review_bundles(self,bundle_id=None):
        from .review_bundles import BUNDLES,bundle_view
        with self.store.transaction('DEFERRED'):
            graph=self.store.graph();decisions=self.store.decisions();validate_graph(graph)
            specs=[BUNDLES[bundle_id]] if bundle_id else [s for s in BUNDLES.values() if all(k in graph for k in s.roots)]
            views=[bundle_view(graph,decisions,s,self._check(graph,s.roots,decisions)) for s in specs]
            for view in views:
                if view.get('candidate_action')=='unresolved':
                    from .publication import TARGETS
                    root=BUNDLES[view['bundle_id']].roots[0]
                    view['publication_governance']=[self.review_unresolved(root,t.target_id) for t in TARGETS.values() if root in t.required_roots]
            return views[0] if bundle_id else views

    def review_bundle(self,bundle_id,action,reviewer,reason,expected_ticket,request_id):
        """One explicit decision, one outer transaction, ordinary P0 reviews.

        Approve covers required academic objects only; reject rejects the
        interpretation root, not independently reusable shared definitions.
        """
        from .review_bundles import BUNDLES,guard,require_current_ticket
        if action not in ('approve','reject','revise'):raise ValueError('Bundle action must be approve, reject or revise; content changes use stage')
        if not reviewer.strip() or not reason.strip():raise ValueError('Reviewer and reason must be nonempty')
        spec=BUNDLES[bundle_id]
        request=dict(operation='review_bundle',bundle_id=bundle_id,action=action,reviewer=reviewer,
                     reason=reason,expected_ticket=expected_ticket)
        rd=digest(request)
        with self.store.transaction():
            cached=self.store.retry(request_id,rd)
            if cached is not None:return cached
            graph=self.store.graph();decisions=self.store.decisions();validate_graph(graph)
            versions=manifest(graph,spec.roots)
            require_current_ticket(expected_ticket,guard(graph,decisions,spec,versions))
            report=self._check(graph,spec.roots,decisions)
            if action=='approve' and (not report['schema_valid'] or not report['source_verified']):
                raise ValueError('Bundle approval requires verified, consistent sources and locators: '+'; '.join(report['reasons']))
            keys=([k for k in versions if graph[k]['record']['kind'] not in ('source','locator')]
                  if action=='approve' else list(spec.roots))
            created=[];reused=[]
            for key in keys:
                previous=decisions.get(key)
                if action=='approve' and decision_state(graph,key,previous)=='approve':
                    reused.append(dict(key=key,decision_id=previous['decision_id']))
                    continue
                child_id='bundle-object-'+digest(dict(request_id=request_id,key=key))
                result=self.review(key,action,reviewer,f'Bundle {bundle_id}; request {request_id}: {reason}',
                    graph[key]['version'],digest(manifest(graph,[key])),
                    previous['decision_id'] if previous else None,child_id)
                created.append(result)
            result=dict(bundle_id=bundle_id,action=action,request_id=request_id,
                        reviewer=reviewer,reason=reason,created_at=now(),
                        reviewed_ticket=expected_ticket,created=created,reused=reused)
            self.store.remember(request_id,rd,result)
            return result

    def review(self,key,action,reviewer,reason,expected_version,expected_dependency_digest,
               expected_decision,request_id,replacement_action=None):
        if not reviewer.strip() or not reason.strip():raise ValueError('Reviewer and reason must be nonempty')
        op=action
        if action=='supersede':
            if expected_decision is None or replacement_action not in ['approve','reject','revise','verify']:
                raise ValueError('Supersede requires an existing decision and explicit replacement action')
            action=replacement_action
        elif replacement_action is not None:raise ValueError('Replacement action only applies to supersede')
        if action not in ['approve','reject','revise','revoke','verify']:raise ValueError('Unknown review action')
        request=dict(op=op,key=key,action=action,reviewer=reviewer,reason=reason,version=expected_version,
                     dependency_digest=expected_dependency_digest,expected_decision=expected_decision)
        rd=digest(request)
        with self.store.transaction():
            cached=self.store.retry(request_id,rd)
            if cached is not None:return cached
            graph=self.store.graph();decisions=self.store.decisions()
            if key not in graph:raise ValueError('Unknown review object')
            latest=decisions.get(key)
            if (latest['decision_id'] if latest else None)!=expected_decision:raise ValueError('Review conflict: another decision is current')
            if graph[key]['version']!=expected_version:raise ValueError('Review version conflict')
            deps=manifest(graph,[key]);dd=digest(deps)
            if dd!=expected_dependency_digest:raise ValueError('Review dependency conflict: inspect the current evidence again')
            is_source=graph[key]['record']['kind'] in ['source','locator']
            if (action=='verify' and not is_source) or (action=='approve' and is_source):
                raise ValueError('Source verification and academic approval are distinct operations')
            if action=='approve' and graph[key]['record']['kind']=='proposal' and graph[key]['record']['payload']['candidate_action']=='unresolved':
                raise ValueError('Unresolved canonical identity requires explicit candidate revision before approval')
            if action in ['approve','verify']:
                validate_graph(graph);errors=integrity(graph,deps)
                if errors:raise ValueError('; '.join(errors))
                if graph[key]['record']['kind']=='locator':
                    skey='source:'+graph[key]['record']['payload']['source_id']
                    if decision_state(graph,skey,decisions.get(skey))!='verify':raise ValueError('Verify source identity before locator')
            if action=='revoke' and latest is None:raise ValueError('Cannot revoke without a previous decision')
            self.store.db.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?,?,?)',
                (request_id,key,expected_version,reviewer,now(),action,reason,dd,canonical(deps),expected_decision))
            self.store.db.execute('INSERT INTO review_heads VALUES(?,?) ON CONFLICT(object_key) DO UPDATE SET decision_id=excluded.decision_id',(key,request_id))
            if latest:self.store.invalidate([key],'review:'+request_id,'Review superseded or revoked; old snapshot must not be used')
            result=dict(decision_id=request_id,object_key=key,action=action,supersedes=expected_decision,dependency_digest=dd)
            self.store.remember(request_id,rd,result)
            return result

    def _check(self,graph,roots,decisions):
        try:
            validate_graph(graph);used=manifest(graph,roots)
            selected={k:graph[k] for k in used}
            errors=integrity(graph,used)
            # v0.3 revalidates identities and source/part/evidence associations.
            if not errors:validate_v03(selected,decisions,reference_graph=graph)
            return evaluate(graph,roots,decisions,errors)
        except (ValueError,OSError,KeyError) as exc:
            return dict(schema_valid=False,source_verified=False,human_approved=False,publishable=False,reasons=[str(exc)],versions={})

    def check(self,roots):
        with self.store.transaction('DEFERRED'):return self._check(self.store.graph(),roots,self.store.decisions())

    def review_unresolved(self,proposal_key,target_id):
        from .governance import inspect
        return inspect(self,target_id,proposal_key)

    def decide_unresolved(self,proposal_key,target_id,action,reviewer,reason,expected_ticket,request_id):
        from .governance import decide
        return decide(self,target_id,proposal_key,action,reviewer,reason,expected_ticket,request_id)

    def check_target(self,target_id):
        from .publication import TARGETS,participation
        from .review_bundles import object_view
        target=TARGETS[target_id]
        with self.store.transaction('DEFERRED'):
            graph=self.store.graph();decisions=self.store.decisions()
            from .governance import selection
            governance=selection(self.store,graph,target)
            report=self._check(graph,governance['roots'],decisions)
            if not governance['roots']:
                report['publishable']=False;report['reasons'].append('No remaining required roots; empty target publication prohibited')
            required,optional=participation(graph,governance['roots'],target.optional_roots) if governance['roots'] else ({},{})
            report.update(effective_roots=list(governance['roots']),deferred_unresolved=governance['deferrals'],governance_states=governance['states'])
            report.update(target=target.definition(),target_version=target.version,
                          optional_candidates=[object_view(graph,decisions,k) for k in optional],
                          participation_notice='Required closure wins over optional labels. Only required objects enter the snapshot.')
            return report

    def publish_target(self,target_id):
        from .publication import TARGETS
        target=TARGETS[target_id]
        return self.publish(target.required_roots,publication_target=target)

    def publish(self,roots,publication_target=None):
        if publication_target is not None:
            from .publication import TARGETS
            if TARGETS.get(publication_target.target_id)!=publication_target:
                raise ValueError('Unknown or altered publication target policy')
        with self.store.transaction():
            graph=self.store.graph();decisions=self.store.decisions();governance=None
            if publication_target is not None:
                if set(roots)!=set(publication_target.required_roots):raise ValueError('Publication target/root mismatch')
                from .governance import selection
                governance=selection(self.store,graph,publication_target)
                roots=governance['roots']
                if not roots:raise ValueError('Empty governed publication target prohibited')
            report=self._check(graph,roots,decisions)
            if not report['publishable']:raise ValueError('Publication blocked: '+'; '.join(report['reasons']))
            versions=report['versions']
            objects={}
            for key,version in versions.items():
                record=deepcopy(graph[key]['record']);p=record['payload'];decision=decisions[key]
                # Materialized publication state comes exclusively from the journal.
                # The original candidate remains immutable in versions, addressed by
                # content_version; the snapshot itself has a separate content hash.
                if record['kind'] in ('source','locator'):
                    p.update(verification_status='verified',verification_reference=decision['decision_id'])
                else:
                    if 'review_status' in p:p.update(review_status='approved',review_decision_id=decision['decision_id'])
                    if 'status' in p:p.update(status='approved',registry_decision_id=decision['decision_id'])
                objects[key]=dict(**record,content_version=version,publication_state='verified' if record['kind'] in ('source','locator') else 'approved')
            payload=dict(format='academic-os-readonly-snapshot/1',roots=sorted(set(roots)),versions=versions,
                         objects=objects,
                         reviews={k:decisions[k] for k in versions})
            if publication_target is not None:
                from .publication import semantic_units
                if governance['deferrals']:payload['publication_governance']=governance['deferrals']
                payload['publication_target']=dict(**publication_target.definition(),version=publication_target.version)
                payload['semantic_units']=semantic_units(objects)
            sid=digest(payload)
            if self.store.db.execute('SELECT 1 FROM snapshot_blocks WHERE snapshot_id=?',(sid,)).fetchone():
                raise ValueError('Previously withdrawn snapshot cannot be resurrected; new review/version required')
            self.store.db.execute('INSERT OR IGNORE INTO snapshots VALUES(?,?,?)',(sid,canonical(payload),now()))
            for k,v in versions.items():self.store.db.execute('INSERT OR IGNORE INTO snapshot_members VALUES(?,?,?)',(sid,k,v))
            return dict(snapshot_id=sid,publishable=True,object_count=len(versions))

    def snapshot(self,sid):
        """Required read path: never serve a detached snapshot without this status check."""
        with self.store.transaction():
            row=self.store.db.execute('SELECT * FROM snapshots WHERE snapshot_id=?',(sid,)).fetchone()
            if row is None:raise ValueError('Unknown snapshot')
            payload=json.loads(row['payload'])
            if digest(payload)!=sid:raise ValueError('Snapshot content integrity error')
            graph=self.store.graph();decisions=self.store.decisions()
            current_roots=payload['roots'];governance_errors=[]
            if payload.get('publication_governance'):
                from .publication import TARGETS
                from .governance import selection
                target=TARGETS.get(payload['publication_target']['target_id'])
                if target is None or target.version!=payload['publication_target']['version']:
                    governance_errors.append('Publication target changed since governance review')
                else:
                    current=selection(self.store,graph,target);current_roots=current['roots']
                    if current['deferrals']!=payload['publication_governance'] or set(current_roots)!=set(payload['roots']):
                        governance_errors.append('Publication governance is stale, reopened or changed')
            report=self._check(graph,current_roots,decisions)
            errors=list(report['reasons'])+governance_errors
            if report['versions']!=payload['versions']:errors.append('Current dependency closure changed')
            for k,v in payload['versions'].items():
                if graph.get(k,{}).get('version')!=v:errors.append('Current version changed: '+k)
                if decisions.get(k)!=payload['reviews'].get(k):errors.append('Current review changed: '+k)
            if errors:
                self.store.db.execute('INSERT OR IGNORE INTO snapshot_blocks VALUES(?,?,?,?)',(sid,'integrity:'+digest(errors),'; '.join(errors),now()))
            blocks=[dict(r) for r in self.store.db.execute('SELECT * FROM snapshot_blocks WHERE snapshot_id=? ORDER BY event',(sid,))]
            return dict(snapshot_id=sid,usable=not blocks,blocks=blocks,payload=payload if not blocks else None)

    def export(self,sid,directory):
        current=self.snapshot(sid)
        if not current['usable']:raise ValueError('Snapshot withdrawn; read denied')
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        path=directory/(sid+'.json');text=canonical(current['payload'])+'\n'
        try:
            with path.open('x',encoding='utf-8',newline='\n') as f:f.write(text);f.flush();os.fsync(f.fileno())
        except FileExistsError:
            if path.read_text(encoding='utf-8')!=text:raise ValueError('Existing snapshot file differs; refusing overwrite')
        path.chmod(0o444)
        return dict(snapshot_id=sid,path=str(path.resolve()),notice='Read-only export. Consumers must call snapshot status before use; detached files cannot reflect later revocation.')
