import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from academic_os.examples.q2 import ROOTS
from academic_os.models import normalise
from academic_os.service import Service
from academic_os.storage import Store
from .bundle_fixtures import seed,verify_sources,approve_core,scenario

A='BUNDLE-Q2-A';B='BUNDLE-Q2-B';C='BUNDLE-Q2-C-PRIMARY';OPTIONAL='BUNDLE-Q2-C-SECONDARY-CANDIDATE'


class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store,self.s=seed(self.tmp.name);self.addCleanup(self.store.close);self.seq=0

    def review(self,bid,action='approve',ticket=None,request_id=None):
        self.seq+=1
        return self.s.review_bundle(bid,action,'TEST-ONLY-OPERATOR','TEST ONLY',
            ticket or self.s.review_bundles(bid)['review_ticket'],request_id or 'TEST-BUNDLE-'+str(self.seq))

    def decide(self,key,action):
        self.seq+=1;item=self.s.inspect(key)
        return self.s.review(key,action,'TEST-ONLY-OPERATOR','TEST ONLY',item['version'],
            item['dependency_digest'],item['expected_decision'],'TEST-OBJECT-'+str(self.seq))

    def change(self,key,field,value):
        self.seq+=1;item=self.s.inspect(key);item['record']['payload'][field]=value
        self.s.stage([item['record']],{key:item['version']},'TEST-REVISION-'+str(self.seq))

    def ready(self):
        verify_sources(self.s);approve_core(self.s)

    def test_required_happy_path_optional_pending_and_excluded(self):
        report=scenario(self.s)
        self.assertEqual(report['before_review'],dict(source_verified=False,human_approved=False,publishable=False))
        self.assertEqual(report['after_source_verification_only'],dict(source_verified=True,human_approved=False,publishable=False))
        self.assertEqual(report['after_core_academic_approval'],dict(source_verified=True,human_approved=True,publishable=True))
        self.assertTrue(report['snapshot_usable']);self.assertTrue(report['optional_candidates_excluded'])
        self.assertEqual(report['optional_candidate_status'],'pending')
        self.assertEqual([u['part_id'] for u in report['semantic_units']],['Q2-a','Q2-b','Q2-c'])
        self.assertEqual(len(report['semantic_units'][2]['interpretations']),1)

    def test_unverified_source_blocks(self):
        self.assertFalse(self.s.check_target('Q2-CORE')['source_verified'])

    def test_verified_sources_without_locators_block(self):
        for sid in ['QP','MS','SPEC']:self.decide('source:'+sid,'verify')
        self.assertFalse(self.s.check_target('Q2-CORE')['source_verified'])

    def test_verified_sources_and_locators_do_not_approve_academics(self):
        verify_sources(self.s);r=self.s.check_target('Q2-CORE')
        self.assertTrue(r['source_verified']);self.assertFalse(r['human_approved']);self.assertFalse(r['publishable'])

    def test_reject_required_source_blocks(self):
        verify_sources(self.s);self.decide('source:QP','reject')
        self.assertFalse(self.s.check_target('Q2-CORE')['source_verified'])

    def test_reject_required_locator_blocks(self):
        verify_sources(self.s);self.decide('locator:QP-Q2-a','reject')
        self.assertFalse(self.s.check_target('Q2-CORE')['source_verified'])

    def test_source_bytes_revision_invalidates_verification(self):
        verify_sources(self.s)
        path=Path(self.s.inspect('source:QP')['record']['payload']['artifact_reference'])
        path.write_bytes(path.read_bytes()+b'\n% TEST ONLY revision')
        self.assertFalse(self.s.check_target('Q2-CORE')['source_verified'])
        self.assertTrue(any(g['integrity_errors'] for g in self.s.review_sources()))

    def test_bundle_approval_requires_source_verification(self):
        with self.assertRaisesRegex(ValueError,'requires verified'):self.review(A)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0],0)

    def test_a_approval_only_covers_required_academic_objects(self):
        verify_sources(self.s);bundle=self.s.review_bundles(A);result=self.review(A)
        self.assertEqual({r['object_key'] for r in result['created']},set(bundle['decision_scope']['approve']))
        self.assertEqual(self.s.inspect(ROOTS[1])['state'],'pending')

    def test_shared_task_condition_approval_reused(self):
        verify_sources(self.s);self.review(A)
        before=self.s.inspect('task_condition:TC-SUMMARY-STATISTICS')
        result=self.review(B);after=self.s.inspect(before['key'])
        self.assertEqual(before['version'],after['version']);self.assertEqual(before['history'],after['history'])
        self.assertIn(before['key'],[r['key'] for r in result['reused']])
        self.assertEqual(self.s.inspect(ROOTS[1])['state'],'approve')

    def test_primary_does_not_approve_secondary(self):
        verify_sources(self.s);self.review(C)
        self.assertEqual(self.s.inspect(ROOTS[3])['state'],'pending')
        self.assertEqual(self.s.inspect('competency:CAN-STAT-CONTEXT-INFER')['state'],'pending')

    def test_reject_optional_does_not_withdraw_primary_snapshot(self):
        self.ready();sid=self.s.publish_target('Q2-CORE')['snapshot_id']
        self.review(OPTIONAL,'reject')
        self.assertTrue(self.s.snapshot(sid)['usable']);self.assertTrue(self.s.check_target('Q2-CORE')['publishable'])
        self.assertEqual(self.s.inspect(ROOTS[3])['state'],'reject')

    def test_optional_only_revision_does_not_stale_core_snapshot(self):
        self.ready();sid=self.s.publish_target('Q2-CORE')['snapshot_id']
        self.change('competency:CAN-STAT-CONTEXT-INFER','description','TEST revised optional interpretation')
        self.assertTrue(self.s.snapshot(sid)['usable'])
        self.assertEqual(self.s.inspect(ROOTS[2])['state'],'approve')

    def test_secondary_required_in_other_explicit_target(self):
        self.ready();self.assertTrue(self.s.check_target('Q2-CORE')['publishable'])
        self.assertFalse(self.s.check_target('Q2-WITH-SECONDARY')['publishable'])
        self.review(OPTIONAL)
        self.assertTrue(self.s.check_target('Q2-WITH-SECONDARY')['publishable'])

    def test_optional_label_never_subtracts_actual_dependency(self):
        item=self.s.inspect(ROOTS[2]);item['record']['judgment_refs'].append(ROOTS[3])
        self.s.stage([item['record']],{item['key']:item['version']},'TEST-EXPLICIT-REQUIRED')
        report=self.s.check_target('Q2-CORE')
        self.assertIn(ROOTS[3],report['versions'])
        self.assertNotIn(ROOTS[3],[x['key'] for x in report['optional_candidates']])
        self.assertFalse(report['publishable'])

    def test_cannot_relabel_smaller_closure_as_q2_core(self):
        from dataclasses import replace
        from academic_os.publication import TARGETS
        forged=replace(TARGETS['Q2-CORE'],required_roots=(ROOTS[0],))
        with self.assertRaisesRegex(ValueError,'altered publication target'):
            self.s.publish(forged.required_roots,publication_target=forged)

    def test_stale_bundle_primary_competency_revision(self):
        verify_sources(self.s);ticket=self.s.review_bundles(B)['review_ticket']
        self.change('competency:CAN-STAT-SD-CALC','description','TEST V2 definition')
        with self.assertRaisesRegex(ValueError,'expected .*current'):self.review(B,ticket=ticket)
        self.assertEqual(self.s.inspect(ROOTS[1])['state'],'pending')

    def test_task_condition_revision_reports_stale_objects(self):
        self.ready();self.change('task_condition:TC-SUMMARY-STATISTICS','description','TEST V2 condition')
        bundle=self.s.review_bundles(B)
        self.assertIn(ROOTS[1],bundle['stale_objects']);self.assertFalse(bundle['publishable'])

    def test_parsed_part_revision_reports_stale_objects(self):
        self.ready();self.change('parsed_part:PARSED-Q2-b','warnings',['TEST revised warning'])
        self.assertIn(ROOTS[1],self.s.review_bundles(B)['stale_objects'])

    def test_bundle_generation_deterministic_and_read_only(self):
        a=self.s.review_bundles();self.assertEqual(a,self.s.review_bundles())
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0],0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM snapshots').fetchone()[0],0)

    def test_duplicate_bundle_command_idempotent(self):
        verify_sources(self.s);ticket=self.s.review_bundles(A)['review_ticket']
        a=self.review(A,ticket=ticket,request_id='TEST-IDEMPOTENT')
        n=self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0]
        self.assertEqual(a,self.review(A,ticket=ticket,request_id='TEST-IDEMPOTENT'))
        self.assertEqual(n,self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0])

    def test_reused_request_id_with_different_action_conflicts(self):
        verify_sources(self.s);ticket=self.s.review_bundles(A)['review_ticket']
        self.review(A,ticket=ticket,request_id='TEST-ID')
        with self.assertRaisesRegex(ValueError,'Idempotency key conflict'):
            self.review(A,'reject',ticket=ticket,request_id='TEST-ID')

    def test_only_a_approved_cannot_publish_whole_q2_core(self):
        verify_sources(self.s);self.review(A)
        self.assertTrue(self.s.review_bundles(A)['publishable'])
        self.assertFalse(self.s.check_target('Q2-CORE')['publishable'])
        with self.assertRaisesRegex(ValueError,'blocked'):self.s.publish_target('Q2-CORE')

    def test_rejected_required_mapping_blocks(self):
        self.ready();self.review(B,'reject')
        self.assertFalse(self.s.check_target('Q2-CORE')['publishable'])

    def test_withdraw_required_object_denies_snapshot(self):
        self.ready();sid=self.s.publish_target('Q2-CORE')['snapshot_id']
        self.decide('task_condition:TC-SUMMARY-STATISTICS','revoke')
        self.assertFalse(self.s.snapshot(sid)['usable']);self.assertIsNone(self.s.snapshot(sid)['payload'])

    def test_snapshot_only_contains_required_trusted_versions(self):
        self.ready();sid=self.s.publish_target('Q2-CORE')['snapshot_id'];snapshot=self.s.snapshot(sid)['payload']
        self.assertEqual(snapshot['versions'],self.s.check_target('Q2-CORE')['versions'])
        self.assertNotIn('competency:CAN-STAT-CONTEXT-INFER',snapshot['objects'])
        self.assertTrue(all(r['publication_state'] in ('approved','verified') for r in snapshot['objects'].values()))

    def test_revision_after_publication_blocks_snapshot(self):
        self.ready();sid=self.s.publish_target('Q2-CORE')['snapshot_id']
        self.change('competency:CAN-STAT-MEAN-CALC','description','TEST new meaning')
        self.assertFalse(self.s.snapshot(sid)['usable'])

    def test_unchanged_target_publication_deterministic(self):
        self.ready();self.assertEqual(self.s.publish_target('Q2-CORE'),self.s.publish_target('Q2-CORE'))

    def test_a_bundle_academic_content(self):
        b=self.s.review_bundles(A)
        self.assertEqual(b['concepts'],['Mean']);self.assertEqual(b['competency'],'Calculate the mean')
        self.assertEqual(b['task_conditions'],['From summary statistics'])

    def test_b_bundle_academic_content(self):
        b=self.s.review_bundles(B)
        self.assertEqual(b['concepts'],['Standard deviation']);self.assertEqual(b['competency'],'Calculate standard deviation')
        self.assertEqual(b['task_conditions'],['From summary statistics'])

    def test_c_primary_contains_two_required_canonical_concepts(self):
        b=self.s.review_bundles(C)
        self.assertEqual(set(b['concepts']),{'Standard deviation','Variation / spread'})
        self.assertEqual(b['role'],'primary')

    def test_optional_bundle_explicitly_marked(self):
        b=self.s.review_bundles(OPTIONAL)
        self.assertIn('optional in Q2-CORE',b['participation']);self.assertEqual(b['role'],'secondary')
        self.assertFalse(b['human_approved'])

    def test_source_evidence_references_no_large_duplicated_text(self):
        bundle=self.s.review_bundles(A)
        self.assertEqual(len(bundle['sources']),3);self.assertEqual(len(bundle['evidence_refs']),2)
        self.assertNotIn('extracted_text',json.dumps(bundle))
        self.assertTrue(all(l['anchor'] for g in bundle['sources'] for l in g['locators']))

    def test_bundle_distinguishes_verification_and_academic_approval(self):
        verify_sources(self.s);b=self.s.review_bundles(A)
        self.assertTrue(b['source_verified']);self.assertFalse(b['human_approved'])

    def test_unresolved_required_scope_not_hidden(self):
        self.change('scope:SCOPE-STAT-2.3','association_status','unresolved')
        bundle=self.s.review_bundles(A)
        self.assertTrue(any('unresolved scope' in reason for reason in bundle['blockers']))
        self.assertFalse(bundle['publishable'])

    def test_bundle_transaction_rolls_back_all_reviews_and_receipts(self):
        verify_sources(self.s);before=self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0]
        receipts_before=self.store.db.execute('SELECT count(*) FROM requests').fetchone()[0]
        self.store.db.execute("CREATE TRIGGER test_bundle_fail BEFORE INSERT ON requests WHEN NEW.request_id='TEST-FAIL' BEGIN SELECT RAISE(ABORT,'TEST receipt failure'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'receipt failure'):self.review(A,request_id='TEST-FAIL')
        self.assertEqual(before,self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0])
        self.assertEqual(receipts_before,self.store.db.execute('SELECT count(*) FROM requests').fetchone()[0])
        self.assertEqual(self.s.inspect(ROOTS[0])['state'],'pending')
        self.assertIsNone(self.store.db.execute("SELECT * FROM requests WHERE request_id='TEST-FAIL'").fetchone())

    def test_bundle_reject_does_not_reject_shared_task_condition(self):
        self.ready();self.review(B,'reject')
        self.assertEqual(self.s.inspect('task_condition:TC-SUMMARY-STATISTICS')['state'],'approve')
        self.assertEqual(self.s.inspect(ROOTS[0])['state'],'approve')

    def test_concurrent_bundle_decisions_fail_without_partial_overwrite(self):
        verify_sources(self.s);ticket=self.s.review_bundles(A)['review_ticket'];barrier=threading.Barrier(2)
        def run(n):
            store=Store(self.store.path)
            try:
                barrier.wait(timeout=10)
                try:
                    Service(store).review_bundle(A,'approve' if n==1 else 'reject','TEST-'+str(n),'TEST',ticket,'TEST-CONCURRENT-'+str(n))
                    return 'ok'
                except ValueError as e:
                    self.assertIn('stale/conflict',str(e));return 'conflict'
            finally:store.close()
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(run,[1,2]))
        self.assertCountEqual(results,['ok','conflict'])

    def test_source_review_views_have_file_and_locator_versions(self):
        groups=self.s.review_sources();self.assertEqual(len(groups),3)
        for g in groups:
            self.assertEqual(len(g['source']['version']),64);self.assertTrue(g['metadata']['source_type'])
            for l in g['locators']:self.assertTrue(l['page_number']);self.assertTrue(l['source_version'])

    def test_tampered_or_foreign_ticket_rejected(self):
        verify_sources(self.s);ticket=self.s.review_bundles(A)['review_ticket']
        with self.assertRaisesRegex(ValueError,'stale/conflict'):self.review(B,ticket=ticket)
        ticket['versions'][ROOTS[0]]='0'*64
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.review(A,ticket=ticket)

    def test_cli_inspection_never_approves_and_explicit_decision_works(self):
        ticket=Path(self.tmp.name)/'ticket.json'
        def run(*args):
            return subprocess.run([sys.executable,'-X','utf8','-m','academic_os','--db',str(self.store.path),*args],capture_output=True,text=True,encoding='utf-8')
        result=run('review-bundle',A);self.assertEqual(result.returncode,0);self.assertIn('Calculate the mean',result.stdout)
        self.assertIn('all three core bundles required',result.stdout)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0],0)
        verify_sources(self.s)
        result=run('review-bundle',A,'--save-ticket',str(ticket));self.assertEqual(result.returncode,0)
        result=run('decide-bundle',A,'approve','--ticket',str(ticket),'--reason','TEST ONLY CLI temporary corpus','--request-id','TEST-CLI-BUNDLE')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        result=run('check','--target','Q2-CORE');self.assertEqual(result.returncode,2)


if __name__=='__main__':unittest.main()
