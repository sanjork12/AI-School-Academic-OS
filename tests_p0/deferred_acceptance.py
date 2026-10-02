"""Read-only real-state audit after tests; writes only acceptance artifacts."""
import hashlib
import json
from pathlib import Path
import re
from academic_os.storage import Store
from academic_os.service import Service
from academic_os.governance import history

OUTPUT=Path('output/p1c1_deferred_unresolved')
KEY='proposal:PROPOSE-Q3-2023-c-ii'
TARGET='Q3-2023-CORE'
Q2='04765fa526fc03ee889f8e0691a23e07de4dcbd5486a779317a928c0809a7070'


def main():
    before=json.loads((OUTPUT/'before.json').read_text(encoding='utf-8'))
    temporary=json.loads((OUTPUT/'temporary-defer-test.json').read_text(encoding='utf-8'))
    path=Path('var/p0_q2.sqlite3').resolve(strict=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before['sha256'], 'Unexpected real database before audit'
    store=Store(path)
    try:
        store.db.execute('PRAGMA query_only=ON')
        service=Service(store);view=service.review_unresolved(KEY,TARGET)
        check=service.check_target(TARGET)
        with store.transaction('DEFERRED'):q2=service.snapshot(Q2)
        after={name:[dict(r) for r in store.db.execute('SELECT * FROM '+name)] for name in before['tables']}
        events=history(store)
        states={k:service.inspect(k)['state'] for k in ('source:QP-2023','source:MS-2023',
            *('proposal:PROPOSE-Q3-2023-'+p for p in ('a','b-i','b-ii','c-i','c-ii')))}
    finally:store.close()
    file_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    assert before['tables']==after, 'Real database rows changed'
    assert file_hash==before['sha256'], 'Real database bytes changed'
    assert q2==before['q2_snapshot'] and q2['usable'], 'Protected Q2 snapshot changed'
    assert view['academic_state']=='unresolved' and view['governance_state']=='none'
    assert not events and not check['publishable'] and set(states.values())=={'pending'}
    pinned=json.loads(Path('output/academic_knowledge_v03/stable_baseline_sha256.json').read_text(encoding='utf-8'))
    missing=[];changed=[]
    for name,expected in pinned['files'].items():
        file=Path(name)
        if not file.exists():missing.append(name)
        elif hashlib.sha256(file.read_bytes()).hexdigest()!=expected:changed.append(name)
    assert not changed, 'Protected historical file hashes changed'
    raw=(OUTPUT/'full-suite.txt').read_bytes()
    log=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    match=re.search(r'Ran (\d+) tests? in ([\d.]+)s',log)
    assert match, 'Full suite has not completed'
    total=int(match[1]);failures=int(re.search(r'failures=(\d+)',log)[1]) if re.search(r'failures=(\d+)',log) else 0
    errors=int(re.search(r'errors=(\d+)',log)[1]) if re.search(r'errors=(\d+)',log) else 0
    skipped=int(re.search(r'skipped=(\d+)',log)[1]) if re.search(r'skipped=(\d+)',log) else 0
    assert failures==0 and errors==1 and 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in log
    focused=[line for line in log.splitlines() if re.match(r'test_.*\(tests_p0.test_deferred_governance\.',line)]
    assert len(focused)==31 and all(line.endswith(' ... ok') for line in focused),focused
    assert (OUTPUT/'rendering-smoke.txt').read_text(encoding='utf-8').startswith('PASS:')
    report=dict(status='P1C.1 DEFERRED UNRESOLVED GOVERNANCE PASSED',
        changed_files=['academic_os/governance.py','academic_os/service.py','academic_os/cli.py','academic_os/review_rendering.py',
            'tests_p0/test_deferred_governance.py','tests_p0/deferred_demo.py','tests_p0/deferred_acceptance.py',
            'docs/P1C1_DEFERRED_UNRESOLVED.md','docs/P1C_CANONICAL_REUSE.md'],
        governance_model=dict(storage='append-only requests journal',record_type='publication_governance/1',
            migration_required=False,trust_boundary='local OS operator; not production authentication',
            scope='target version + proposal/dependency manifest; no academic state mutation'),
        real_database=dict(path=str(path),sha256_before=before['sha256'],sha256_after=file_hash,all_original_rows_unchanged=True,
            academic_state=view['academic_state'],governance_state=view['governance_state'],
            participation=view['participation'],publishable=check['publishable'],states=states,
            human_academic_source_decisions_before=len(before['tables']['reviews']),human_academic_source_decisions_after=len(after['reviews']),
            governance_decisions_before=0,governance_decisions_after=len(events),
            snapshots_before=len(before['tables']['snapshots']),snapshots_after=len(after['snapshots'])),
        temporary=dict(pre_defer_publishable=temporary['state_a']['publishable'],
            post_defer_publishable=temporary['state_b']['publishable'],
            final_flags={k:temporary['state_c'][k] for k in ('schema_valid','source_verified','human_approved','publishable')},
            semantic_parts=[u['part_id'] for u in temporary['semantic_units']],
            unresolved_entered_trusted_snapshot=temporary['unresolved_entered_trusted_snapshot'],
            parsed_unresolved_entered_trusted_snapshot=temporary['parsed_unresolved_entered_trusted_snapshot'],
            deterministic_republication=temporary['deterministic_republication'],
            proposal_unchanged_after_defer=temporary['proposal_unchanged_after_defer'],test_only=True),
        q2=dict(snapshot_id=Q2,usable=q2['usable'],unchanged=True),
        tests=dict(total=total,passed=total-failures-errors-skipped,failures=failures,errors=errors,skipped=skipped,
            governance_tests_passed=len(focused),final_renderer_smoke='passed in disposable database',not_run=0,duration_seconds=float(match[2]),
            baseline='Prior P1C recorded result: 327 total, 326 passed, 1 known missing-PPT error',
            known_error='Protected PPT missing; test and pinned hash preserved',log='full-suite.txt'),
        historical_integrity=dict(pinned=len(pinned['files']),unchanged=len(pinned['files'])-len(missing),missing=missing,changed=changed),
        architectural_notes=[
            'Current small journal uses linear scans; future scale can add indexed governance persistence behind the same service.',
            'Shared MS c(ii) evidence remains required for c(i); it is not a trusted c(ii) interpretation.',
            'Governed snapshot validity requires the service read path; detached exports do not attest current usability.',
            'Source and academic approvals of unchanged content do not invalidate a committed defer; content/target changes do.'])
    (OUTPUT/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
