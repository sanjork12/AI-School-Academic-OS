"""P1B.1: all decisions use TEST ONLY isolated databases and copied sources."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from academic_os.models import normalise
from academic_os.source_bundles import SOURCE_BUNDLES, NOTICE
from .bundle_fixtures import seed, approve_core

QP='SOURCE-BUNDLE-QP-Q2'
MS='SOURCE-BUNDLE-MS-Q2'
SPEC='SOURCE-BUNDLE-SPEC-2.3'

class SourceBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store,self.s=seed(self.tmp.name);self.addCleanup(self.store.close);self.seq=0

    def decide(self,bid=QP,action='verify',ticket=None,rid=None):
        self.seq+=1
        return self.s.review_source_bundle(bid,action,'TEST-ONLY-OPERATOR','TEST ONLY source verification',
            ticket if ticket is not None else self.s.review_source(bid)['review_ticket'],rid or 'TEST-SOURCE-'+str(self.seq))

    def counts(self):
        return {t:self.store.db.execute('select count(*) from '+t).fetchone()[0]
                for t in ('reviews','review_heads','requests','snapshot_blocks','snapshots')}

    def revise(self,key,field,value):
        # Real immutable revision, including all pinned downstream locator/span versions.
        graph=self.store.graph();records={k:copy.deepcopy(v['record']) for k,v in graph.items()}
        records[key]['payload'][field]=value
        for k,r in records.items():
            if r['kind']=='locator':
                r['payload']['source_version']=normalise(records['source:'+r['payload']['source_id']])[1]
        for r in records.values():
            if r['kind']=='parsed_part':
                for span in r['payload']['spans']:
                    span['locator_version']=normalise(records['locator:'+span['locator_id']])[1]
        changed={k:r for k,r in records.items() if normalise(r)[1]!=graph[k]['version']}
        self.s.stage(list(changed.values()),{k:graph[k]['version'] for k in changed},'TEST-REVISION')

    def test_deterministic(self):
        self.assertEqual(self.s.review_sources(),self.s.review_sources())

    def assert_members(self,bid,expected):
        self.assertEqual(set(self.s.review_source(bid)['review_ticket']['versions']),set(expected))

    def test_ms_members(self):
        self.assert_members(MS,['source:MS','locator:MS-Q2-a','locator:MS-Q2-b','locator:MS-Q2-c'])

    def test_qp_members(self):
        self.assert_members(QP,['source:QP','locator:QP-Q2','locator:QP-Q2-a','locator:QP-Q2-b','locator:QP-Q2-c'])

    def test_spec_members(self):
        self.assert_members(SPEC,['source:SPEC','locator:SPEC-2.3'])

    def test_inspection_read_only(self):
        before=self.counts();path=Path(self.tmp.name)/'TEST-ONLY.db';sha=hashlib.sha256(path.read_bytes()).hexdigest()
        self.s.review_sources();self.s.review_source(QP)
        self.assertEqual(before,self.counts());self.assertEqual(sha,hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(self.store.decisions(),{})

    def test_ticket_pins_source(self):
        t=self.s.review_source(QP)['review_ticket']
        self.assertEqual(t['versions']['source:QP'],self.s.inspect('source:QP')['version'])
        self.assertIsNone(t['review_heads']['source:QP'])

    def test_ticket_pins_locators(self):
        g=self.s.review_source(QP)
        for loc in g['locators']:
            self.assertEqual(g['review_ticket']['versions'][loc['key']],loc['version'])
            self.assertIsNone(g['review_ticket']['review_heads'][loc['key']])

    def stale_revision(self,key,field,value):
        t=self.s.review_source(QP)['review_ticket'];old=t['versions'][key]
        self.revise(key,field,value);new=self.s.inspect(key)['version'];before=self.counts()
        with self.assertRaises(ValueError) as err:self.decide(ticket=t)
        self.assertIn('stale/conflict',str(err.exception));self.assertIn(old,str(err.exception));self.assertIn(new,str(err.exception))
        self.assertEqual(before,self.counts())

    def test_source_revision_stale(self):self.stale_revision('source:QP','identity_basis','TEST ONLY revised identity basis')
    def test_locator_revision_stale(self):self.stale_revision('locator:QP-Q2-a','text_summary','TEST ONLY revised locator summary')

    def test_stale_decision_head(self):
        t=self.s.review_source(QP)['review_ticket'];self.decide(action='reject')
        with self.assertRaisesRegex(ValueError,'review_heads'):self.decide(ticket=t)

    def test_verify_exact_versions_and_scope(self):
        g=self.s.review_source(QP);self.decide(ticket=g['review_ticket'])
        decisions=self.store.decisions();self.assertEqual(set(decisions),set(g['review_ticket']['versions']))
        for k,d in decisions.items():
            self.assertEqual(d['action'],'verify');self.assertEqual(d['object_version'],g['review_ticket']['versions'][k])
            self.assertEqual(d['reviewer'],'TEST-ONLY-OPERATOR')
        self.assertTrue(self.s.review_source(QP)['source_verified'])

    def test_no_academic_approval(self):
        self.decide()
        self.assertFalse(any(d['action']=='approve' for d in self.store.decisions().values()))
        self.assertTrue(all(o['state']=='pending' for o in self.s.inspect() if not o['key'].startswith(('source:','locator:'))))

    def test_reject_all_members_supersedes(self):
        self.decide();old=self.store.decisions();self.decide(action='reject')
        for k,d in self.store.decisions().items():
            self.assertEqual(d['action'],'reject');self.assertEqual(d['supersedes'],old[k]['decision_id'])
        self.assertFalse(self.s.review_source(QP)['source_verified'])
        self.assertFalse(self.s.check_target('Q2-CORE')['publishable'])

    def test_atomic_failure_rolls_back_children_and_requests(self):
        before=self.counts();original=self.s.review;calls=[]
        def fail(*args,**kwargs):
            calls.append(args[0])
            if len(calls)==3:raise RuntimeError('TEST ONLY injected failure')
            return original(*args,**kwargs)
        with patch.object(self.s,'review',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'injected'):self.decide()
        self.assertEqual(calls[0],'source:QP');self.assertEqual(before,self.counts());self.assertEqual(self.store.decisions(),{})

    def test_parent_receipt_failure_rolls_back(self):
        before=self.counts();original=self.store.remember
        def fail(request_id,*args):
            if request_id=='TEST-PARENT-FAIL':raise RuntimeError('TEST ONLY receipt failure')
            return original(request_id,*args)
        with patch.object(self.store,'remember',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'receipt failure'):self.decide(rid='TEST-PARENT-FAIL')
        self.assertEqual(before,self.counts());self.assertEqual(self.store.decisions(),{})

    def test_preverified_shared_source_is_reused(self):
        item=self.s.inspect('source:QP')
        self.s.review(item['key'],'verify','TEST-ONLY-OPERATOR','TEST ONLY shared source',
            item['version'],item['dependency_digest'],None,'TEST-SHARED')
        result=self.decide()
        self.assertEqual(result['reused'],[dict(key='source:QP',decision_id='TEST-SHARED')])
        self.assertEqual(len(result['created']),4)

    def test_concurrent_decisions_cannot_overwrite(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from academic_os.storage import Store
        from academic_os.service import Service
        ticket=self.s.review_source(QP)['review_ticket'];barrier=Barrier(2)
        def run(action):
            store=Store(self.store.path)
            try:
                barrier.wait(timeout=10)
                try:
                    Service(store).review_source_bundle(QP,action,'TEST-ONLY-'+action,'TEST ONLY concurrency',
                        ticket,'TEST-CONCURRENT-'+action)
                    return 'ok'
                except ValueError as e:
                    self.assertIn('stale/conflict',str(e));return 'conflict'
            finally:store.close()
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(run,['verify','reject']))
        self.assertCountEqual(results,['ok','conflict']);self.assertEqual(self.counts()['reviews'],5)

    def test_exact_retry_is_idempotent(self):
        t=self.s.review_source(QP)['review_ticket'];r=self.decide(ticket=t,rid='TEST-IDEMPOTENT');before=self.counts()
        self.assertEqual(r,self.decide(ticket=t,rid='TEST-IDEMPOTENT'));self.assertEqual(before,self.counts())

    def test_fresh_request_reuses_valid_verifications(self):
        self.decide();before=self.counts()['reviews'];r=self.decide()
        self.assertEqual(r['created'],[]);self.assertEqual(len(r['reused']),5);self.assertEqual(before,self.counts()['reviews'])

    def test_conflicting_request_rejected(self):
        self.decide(rid='TEST-CONFLICT');before=self.counts()
        with self.assertRaisesRegex(ValueError,'Idempotency'):self.decide(action='reject',rid='TEST-CONFLICT')
        self.assertEqual(before,self.counts())

    def test_bytes_change_blocks_even_with_valid_ticket(self):
        g=self.s.review_source(QP);p=Path(g['metadata']['artifact_reference']);p.write_bytes(p.read_bytes()+b'\n% TEST ONLY alteration')
        with self.assertRaisesRegex(ValueError,'blocked'):self.decide(ticket=g['review_ticket'])
        self.assertEqual(self.counts()['reviews'],0)

    def test_tampered_ticket_rejected(self):
        t=self.s.review_source(QP)['review_ticket'];t['versions']['source:QP']='forged'
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.decide(ticket=t)

    def test_source_only_blocks_academics(self):
        for bid in SOURCE_BUNDLES:self.decide(bid)
        r=self.s.check_target('Q2-CORE');self.assertTrue(r['source_verified']);self.assertFalse(r['human_approved']);self.assertFalse(r['publishable'])

    def test_happy_path_and_rejection_withdraws_snapshot(self):
        for bid in SOURCE_BUNDLES:self.decide(bid)
        approve_core(self.s);r=self.s.publish_target('Q2-CORE');snap=self.s.snapshot(r['snapshot_id'])
        self.assertTrue(snap['usable']);self.assertEqual(r,self.s.publish_target('Q2-CORE'))
        self.assertEqual(len(snap['payload']['semantic_units']),3)
        self.assertEqual(self.s.inspect('part_mapping:MAP-Q2-c-CONTEXT-INFER')['state'],'pending')
        self.assertNotIn('part_mapping:MAP-Q2-c-CONTEXT-INFER',snap['payload']['objects'])
        self.decide(action='reject');self.assertFalse(self.s.snapshot(r['snapshot_id'])['usable'])
        with self.assertRaisesRegex(ValueError,'blocked'):self.s.publish_target('Q2-CORE')

    def test_cli_ticket_workflow_and_no_overwrite(self):
        db=str(Path(self.tmp.name)/'TEST-ONLY.db');ticket=str(Path(self.tmp.name)/'test.ticket')
        def cli(*args):return subprocess.run([sys.executable,'-X','utf8','-m','academic_os','--db',db,*args],capture_output=True,text=True,encoding='utf-8')
        r=cli('review-source',QP,'--save-ticket',ticket);self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn(NOTICE,r.stdout);self.assertIn('Source version:',r.stdout);self.assertEqual(self.counts()['reviews'],0)
        self.assertEqual(cli('review-source',QP,'--save-ticket',ticket).returncode,1)
        r=cli('decide-source',QP,'verify','--ticket',ticket,'--reason','TEST ONLY isolated CLI','--request-id','TEST-CLI')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn('VERIFIED',cli('review-sources').stdout)

if __name__=='__main__':unittest.main()
