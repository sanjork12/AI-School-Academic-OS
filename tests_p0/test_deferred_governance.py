"""Governance decisions are TEST ONLY, in disposable databases and copied sources."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from academic_os.storage import Store
from academic_os.service import Service
from academic_os.q3_pipeline import plan_q3
from academic_os.q3_parsing import SOURCE_DIR
from academic_os.publication import TARGETS
from academic_os.governance import history
from academic_os.models import normalise
from academic_os.review_rendering import bundles_text
from .bundle_fixtures import seed,verify_sources,approve_core

KEY='proposal:PROPOSE-Q3-2023-c-ii'
TARGET='Q3-2023-CORE'


class DeferredGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory();cls.base,s=seed(cls.directory.name)
        verify_sources(s);approve_core(s);cls.q2=s.publish_target('Q2-CORE')['snapshot_id']
        sources=Path(cls.directory.name)/'q3';shutil.copytree(SOURCE_DIR,sources)
        s.stage(**plan_q3(cls.base.graph(),cls.base.decisions(),sources),request_id='TEST-Q3')
    @classmethod
    def tearDownClass(cls):cls.base.close();cls.directory.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'TEST.sqlite3');self.addCleanup(self.store.close)
        self.base.db.backup(self.store.db);self.s=Service(self.store)
    def inspect(self):return self.s.review_unresolved(KEY,TARGET)
    def decide(self,action='defer',ticket=None,request='TEST-DEFER'):
        return self.s.decide_unresolved(KEY,TARGET,action,'TEST-ONLY-OPERATOR','TEST ONLY defer unresolved interpretation',ticket or self.inspect()['review_ticket'],request)
    def change(self,key=KEY):
        row=self.store.graph()[key];record=copy.deepcopy(row['record'])
        record['payload']['observation']+=' TEST ONLY new evidence'
        self.s.stage([record],{key:row['version']},'TEST-CHANGE')
    def prepare_publication(self):
        for sid in ('QP','MS'):
            bid='SOURCE-BUNDLE-'+sid+'-Q3-2023'
            self.s.review_source_bundle(bid,'verify','TEST-ONLY-OPERATOR','TEST ONLY copied PDF',self.s.review_source(bid)['review_ticket'],'TEST-VERIFY-'+sid)
        for part in ('A','B-I','B-II','C-I'):
            bid='BUNDLE-Q3-2023-'+part
            self.s.review_bundle(bid,'approve','TEST-ONLY-OPERATOR','TEST ONLY interpretation',self.s.review_bundles(bid)['review_ticket'],'TEST-APPROVE-'+part)
    def published(self):
        self.decide();self.prepare_publication();return self.s.publish_target(TARGET)['snapshot_id']
    def test_inspection_read_only(self):
        before=[tuple(r) for r in self.store.db.execute('select * from requests')]
        self.assertEqual(self.inspect()['governance_state'],'none');self.s.review_bundles('BUNDLE-Q3-2023-C-II')
        self.assertEqual(before,[tuple(r) for r in self.store.db.execute('select * from requests')])
    def test_initial_unresolved_blocks(self):
        result=self.s.check_target(TARGET);self.assertFalse(result['publishable']);self.assertIn(KEY,result['versions'])
        self.assertTrue(any('unresolved canonical' in r for r in result['reasons']))
    def test_explicit_action_required(self):
        for action in ('approve','exclude','',None):
            with self.assertRaises(ValueError):self.decide(action=action)
        self.assertEqual(history(self.store),[])
    def test_target_specific(self):
        other=replace(TARGETS[TARGET],target_id='Q3-2023-RESEARCH')
        with patch.dict(TARGETS,{other.target_id:other}):
            self.decide();result=self.s.check_target(other.target_id)
            self.assertIn(KEY,result['versions']);self.assertFalse(result['publishable'])
    def test_preserves_academic_versions_evidence_alternatives_and_registry(self):
        graph=self.store.graph();reviews=self.store.decisions();self.decide()
        self.assertEqual(graph,self.store.graph());self.assertEqual(reviews,self.store.decisions())
        self.assertEqual(self.inspect()['academic_state'],'unresolved')
    def test_only_root_removed_shared_evidence_retained(self):
        self.decide();result=self.s.check_target(TARGET)
        self.assertNotIn(KEY,result['versions']);self.assertNotIn('parsed_part:PARSED-Q3-2023-c-ii',result['versions'])
        self.assertIn('locator:MS-2023-Q3-c-ii',result['versions'])
        self.assertEqual(len(result['effective_roots']),4)
    def test_pending_still_blocks(self):
        self.decide();result=self.s.check_target(TARGET)
        self.assertFalse(result['publishable']);self.assertTrue(result['reasons'])
        with self.assertRaisesRegex(ValueError,'Publication blocked'):self.s.publish_target(TARGET)
    def test_dependency_requirement_wins_over_defer(self):
        key='proposal:PROPOSE-Q3-2023-a';row=self.store.graph()[key];record=copy.deepcopy(row['record'])
        record['judgment_refs'].append(KEY)
        self.s.stage([record],{key:row['version']},'TEST-REQUIRED-DEPENDENCY')
        self.decide();result=self.s.check_target(TARGET)
        self.assertIn(KEY,result['versions']);self.assertFalse(result['publishable'])
        self.assertEqual(result['governance_states'][0]['state'],'required_by_dependency')
    def test_source_byte_change_invalidates_defer(self):
        self.decide();path=Path(self.store.graph()['source:QP-2023']['record']['payload']['artifact_reference'])
        original=path.read_bytes()
        try:
            path.write_bytes(original+b'\n% TEST ONLY changed bytes\n')
            self.assertEqual(self.inspect()['governance_state'],'stale')
            self.assertFalse(self.s.check_target(TARGET)['publishable'])
        finally:path.write_bytes(original)
    def test_review_head_change_invalidates_unused_ticket(self):
        ticket=self.inspect()['review_ticket'];bid='SOURCE-BUNDLE-QP-Q3-2023'
        self.s.review_source_bundle(bid,'verify','TEST-ONLY','TEST ONLY',self.s.review_source(bid)['review_ticket'],'TEST-NEW-SOURCE-HEAD')
        with self.assertRaisesRegex(ValueError,'stale/conflict'):self.decide(ticket=ticket)
    def test_governance_journal_immutable(self):
        import sqlite3
        self.decide()
        # Use the actual journal key column, independent of candidate object IDs.
        column=self.store.db.execute('pragma table_info(requests)').fetchone()['name']
        with self.assertRaisesRegex(sqlite3.IntegrityError,'immutable history'):
            self.store.db.execute('DELETE FROM requests WHERE '+column+'=?',('TEST-DEFER',))
    def test_proposal_ticket_stale(self):
        ticket=self.inspect()['review_ticket'];self.change()
        with self.assertRaisesRegex(ValueError,'stale/conflict'):self.decide(ticket=ticket)
    def test_dependency_ticket_stale(self):
        ticket=self.inspect()['review_ticket'];key='question_part:Q3-2023-c-ii';row=self.store.graph()[key]
        record=copy.deepcopy(row['record']);record['payload']['label']+=' TEST ONLY clarified label'
        self.s.stage([record],{key:row['version']},'TEST-DEP-CHANGE')
        with self.assertRaisesRegex(ValueError,'stale/conflict'):self.decide(ticket=ticket)
    def test_target_ticket_stale(self):
        ticket=self.inspect()['review_ticket']
        with patch.dict(TARGETS,{TARGET:replace(TARGETS[TARGET],title='Changed publication policy')}):
            with self.assertRaisesRegex(ValueError,'target_version'):self.decide(ticket=ticket)
    def test_request_idempotent(self):
        ticket=self.inspect()['review_ticket'];first=self.decide(ticket=ticket)
        self.assertEqual(first,self.decide(ticket=ticket));self.assertEqual(len(history(self.store)),1)
    def test_request_conflict(self):
        self.decide()
        with self.assertRaises(ValueError):self.decide(action='reopen')
        self.assertEqual(len(history(self.store)),1)
    def test_competing_operator_conflict(self):
        ticket=self.inspect()['review_ticket']
        with tempfile.TemporaryDirectory():
            second=Store(self.store.path)
            try:
                self.decide(ticket=ticket)
                with self.assertRaisesRegex(ValueError,'governance_head'):
                    Service(second).decide_unresolved(KEY,TARGET,'defer','TEST-SECOND','TEST ONLY competing decision',ticket,'TEST-SECOND')
            finally:second.close()
        self.assertEqual(len(history(self.store)),1)
    def test_new_version_does_not_inherit_defer(self):
        self.decide();self.change();self.assertEqual(self.inspect()['governance_state'],'stale')
        self.assertIn(KEY,self.s.check_target(TARGET)['versions'])
    def test_audit_metadata(self):
        event=self.decide()
        for name in ('reviewer','reason','proposal_version','versions','target_version','created_at','request_id','reviewed_ticket'):self.assertTrue(event[name])
        self.assertEqual(event['target_id'],TARGET);self.assertEqual(event['proposal_key'],KEY)
        self.assertEqual(self.inspect()['history'],[event])
    def test_full_publication_excludes_unresolved(self):
        sid=self.published();report=self.s.check_target(TARGET)
        for flag in ('schema_valid','source_verified','human_approved','publishable'):self.assertTrue(report[flag],report['reasons'])
        snapshot=self.s.snapshot(sid);self.assertTrue(snapshot['usable']);p=snapshot['payload']
        self.assertEqual([u['part_id'] for u in p['semantic_units']],['Q3-2023-a','Q3-2023-b-i','Q3-2023-b-ii','Q3-2023-c-i'])
        self.assertNotIn(KEY,p['objects']);self.assertNotIn('parsed_part:PARSED-Q3-2023-c-ii',p['objects'])
        self.assertEqual(p['publication_governance'],history(self.store));self.assertEqual(self.inspect()['academic_state'],'unresolved')
        self.assertEqual(sid,self.s.publish_target(TARGET)['snapshot_id'])
    def test_reopen_withdraws_snapshot(self):
        sid=self.published();event=self.decide('reopen',request='TEST-REOPEN')
        self.assertEqual(event['supersedes'],'TEST-DEFER');self.assertFalse(self.s.snapshot(sid)['usable'])
        self.assertFalse(self.s.check_target(TARGET)['publishable'])
    def test_excluded_content_change_withdraws_snapshot(self):
        sid=self.published();self.change();self.assertFalse(self.s.snapshot(sid)['usable'])
    def test_target_change_withdraws_snapshot(self):
        sid=self.published()
        with patch.dict(TARGETS,{TARGET:replace(TARGETS[TARGET],title='Changed policy')}):
            self.assertFalse(self.s.snapshot(sid)['usable'])
    def test_q2_unchanged(self):
        before=self.s.snapshot(self.q2);self.published();self.assertEqual(before,self.s.snapshot(self.q2))
    def test_tampered_ticket(self):
        ticket=self.inspect()['review_ticket'];ticket['target_version']='FORGED'
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.decide(ticket=ticket)
    def test_candidate_cannot_forge_defer(self):
        record=copy.deepcopy(self.store.graph()[KEY]['record']);record['payload']['deferred']=True
        with self.assertRaises(ValueError):normalise(record)
    def test_resolved_proposal_not_deferred(self):
        key='proposal:PROPOSE-Q3-2023-a';ticket=self.s.review_unresolved(key,TARGET)['review_ticket']
        with self.assertRaisesRegex(ValueError,'Only unresolved'):
            self.s.decide_unresolved(key,TARGET,'defer','TEST','TEST ONLY',ticket,'TEST-RESOLVED')
    def test_atomic_rollback(self):
        sid=self.published();ticket=self.inspect()['review_ticket']
        with patch.object(self.store,'remember',side_effect=RuntimeError('TEST write failure')):
            with self.assertRaises(RuntimeError):self.decide('reopen',ticket,'TEST-ROLLBACK')
        self.assertEqual(len(history(self.store)),1);self.assertTrue(self.s.snapshot(sid)['usable'])
    def test_cli_inspect_and_explicit_defer(self):
        ticket=Path(self.tmp.name)/'ticket.json'
        base=[sys.executable,'-X','utf8','-m','academic_os','--db',str(self.store.path)]
        result=subprocess.run(base+['review-unresolved',KEY,'--target',TARGET,'--save-ticket',str(ticket)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('No decision',result.stdout);self.assertEqual(history(self.store),[])
        result=subprocess.run(base+['decide-unresolved',KEY,'defer','--target',TARGET,'--ticket',str(ticket),'--reason','TEST ONLY disposable DB','--request-id','TEST-CLI'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertEqual(self.inspect()['governance_state'],'deferred')
    def test_unresolved_display_not_registry_decision(self):
        view=self.s.review_bundles('BUNDLE-Q3-2023-C-II');rendered=bundles_text([view])
        self.assertIn('UNRESOLVED',rendered);self.assertNotIn('[CREATE_CANDIDATE]',rendered);self.assertIn('currently blocking',rendered)
    def test_empty_target_blocked(self):
        with patch.dict(TARGETS,{TARGET:replace(TARGETS[TARGET],required_roots=(KEY,))}):
            self.decide();self.assertFalse(self.s.check_target(TARGET)['publishable'])
            with self.assertRaisesRegex(ValueError,'Empty'):self.s.publish_target(TARGET)


if __name__=='__main__':unittest.main()

