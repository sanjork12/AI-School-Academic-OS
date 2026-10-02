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
from academic_os.storage import Store
from academic_os.service import Service
from academic_os.models import normalise
from validate_academic_knowledge_v03 import digest
from tests_p0.fixtures import candidates,ROOT,pdf

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name);self.path=self.directory/'store.db'
        self.store=Store(self.path);self.addCleanup(self.store.close);self.s=Service(self.store)
        self.rows=candidates(self.directory);self.expected={normalise(x)[0]:None for x in self.rows}
        self.s.stage(self.rows,self.expected,'TEST-import');self.counter=0
    def decision(self,key,action='approve',**kw):
        i=self.s.inspect(key);self.counter+=1
        args=dict(key=key,action=action,reviewer='TEST-ONLY-REVIEWER',reason='TEST ONLY decision, no real approval',
             expected_version=i['version'],expected_dependency_digest=i['dependency_digest'],expected_decision=i['expected_decision'],request_id='TEST-review-'+str(self.counter))
        args.update(kw);return self.s.review(**args)
    def verify_sources(self):
        for prefix in ['source:','locator:']:
            for r in self.s.inspect():
                if r['key'].startswith(prefix):self.decision(r['key'],'verify')
    def approve_all(self):
        self.verify_sources()
        for r in self.s.inspect():
            if not r['key'].startswith(('source:','locator:')):self.decision(r['key'])
    def change(self,key,field,value):
        i=self.s.inspect(key);r=copy.deepcopy(i['record']);r['payload'][field]=value
        self.counter+=1;return self.s.stage([r],{key:i['version']},'TEST-change-'+str(self.counter))

    def test_registration_extraction_are_not_verification(self):
        r=self.s.check([ROOT]);self.assertTrue(r['schema_valid']);self.assertFalse(r['source_verified']);self.assertFalse(r['publishable'])
    def test_source_verified_not_academic_approved(self):
        self.verify_sources();r=self.s.check([ROOT]);self.assertTrue(r['source_verified']);self.assertFalse(r['human_approved']);self.assertFalse(r['publishable'])
    def test_approved_mapping_to_draft_registry_blocked(self):
        self.verify_sources();self.decision(ROOT)
        r=self.s.check([ROOT]);self.assertFalse(r['publishable']);self.assertIn('competency:CAN-MEAN: pending; requires approve',r['reasons'])
        self.assertEqual(self.s.inspect(ROOT)['state'],'approve')
    def test_competency_change_stales_mapping(self):
        self.approve_all();self.assertTrue(self.s.check([ROOT])['publishable'])
        self.change('competency:CAN-MEAN','description','TEST changed meaning')
        self.assertEqual(self.s.inspect(ROOT)['state'],'stale');self.assertFalse(self.s.check([ROOT])['publishable'])
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM versions WHERE object_key='competency:CAN-MEAN'").fetchone()[0],2)
    def test_condition_context_scope_changes_stale_mapping(self):
        self.approve_all()
        for key,field in [('condition:COND','description'),('context:CTX','curriculum_version'),('scope:SCOPE','description')]:
            self.change(key,field,'TEST revised');self.assertEqual(self.s.inspect(ROOT)['state'],'stale')
    def test_evidence_change_stales_mapping(self):
        self.approve_all();self.change('evidence:EV-PAPER','observation','TEST different reading');self.assertEqual(self.s.inspect(ROOT)['state'],'stale')
    def test_locator_change_stales_verification_and_mapping(self):
        self.approve_all();self.change('locator:LOC-PAPER','text_summary','TEST corrected summary')
        self.assertEqual(self.s.inspect('locator:LOC-PAPER')['state'],'stale')
        self.assertEqual(self.s.inspect(ROOT)['state'],'stale')
        self.assertFalse(self.s.check([ROOT])['publishable'])
    def test_source_metadata_version_requires_new_locator_version(self):
        self.approve_all();i=self.s.inspect('source:PAPER');r=i['record'];r['payload']['version_label']='TEST corrected edition'
        with self.assertRaisesRegex(ValueError,'Locator source version is stale'):
            self.s.stage([r],{i['key']:i['version']},'TEST-source-alone')
        loc=self.s.inspect('locator:LOC-PAPER');loc['record']['payload']['source_version']=normalise(r)[1]
        self.s.stage([r,loc['record']],{i['key']:i['version'],loc['key']:loc['version']},'TEST-source-and-locator')
        self.assertEqual(self.s.inspect('source:PAPER')['state'],'stale')
        self.assertEqual(self.s.inspect(ROOT)['state'],'stale')
    def test_official_text_tampering_rejected_even_with_new_digest(self):
        key='locator:LOC-PAPER';i=self.s.inspect(key);r=i['record'];r['payload'].update(extracted_text='Forged official text',text_digest=digest('Forged official text'))
        with self.assertRaisesRegex(ValueError,'official page text'):self.s.stage([r],{key:i['version']},'TEST-forge')
        self.assertEqual(self.s.inspect(key)['version'],i['version'])
    def test_file_bytes_change_invalidates_verification(self):
        self.approve_all();p=self.directory/'PAPER.pdf';p.write_bytes(p.read_bytes()+b'\n% changed bytes')
        r=self.s.check([ROOT]);self.assertFalse(r['publishable']);self.assertFalse(r['source_verified']);self.assertTrue(any('bytes changed' in x for x in r['reasons']))
    def test_self_supplied_approval_rejected(self):
        key=ROOT;i=self.s.inspect(key);r=i['record'];r['payload']['review_status']='approved'
        with self.assertRaisesRegex(ValueError,'Candidate cannot'):self.s.stage([r],{key:i['version']},'TEST-fake-review')
    def test_self_supplied_verification_rejected(self):
        key='source:PAPER';i=self.s.inspect(key);r=i['record'];r['payload'].update(verification_status='verified',verification_reference='fake')
        with self.assertRaises(ValueError):self.s.stage([r],{key:i['version']},'TEST-fake-verify')
        r['payload']['reviewer']='invented'
        with self.assertRaises(ValueError):normalise(r)
    def test_revoke_blocks_new_publish_and_old_read(self):
        self.approve_all();sid=self.s.publish([ROOT])['snapshot_id'];before=self.store.db.execute('SELECT payload FROM snapshots').fetchone()[0]
        self.decision('competency:CAN-MEAN','revoke')
        with self.assertRaisesRegex(ValueError,'blocked'):self.s.publish([ROOT])
        self.assertFalse(self.s.snapshot(sid)['usable']);self.assertIsNone(self.s.snapshot(sid)['payload'])
        self.assertEqual(self.store.db.execute('SELECT payload FROM snapshots').fetchone()[0],before)
    def test_source_revoke_blocks(self):
        self.approve_all();self.decision('source:PAPER','revoke');self.assertFalse(self.s.check([ROOT])['source_verified'])
    def test_duplicate_import_and_decision_idempotent(self):
        n=self.store.db.execute('SELECT count(*) FROM versions').fetchone()[0]
        self.s.stage(self.rows,self.expected,'TEST-import');self.assertEqual(n,self.store.db.execute('SELECT count(*) FROM versions').fetchone()[0])
        i=self.s.inspect(ROOT);kwargs=dict(key=ROOT,action='approve',reviewer='TEST-ONLY',reason='TEST',expected_version=i['version'],expected_dependency_digest=i['dependency_digest'],expected_decision=None,request_id='TEST-duplicate')
        self.assertEqual(self.s.review(**kwargs),self.s.review(**kwargs));self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0],1)
        kwargs['reason']='different'
        with self.assertRaisesRegex(ValueError,'Idempotency key conflict'):self.s.review(**kwargs)
    def test_conflicting_decision_cas(self):
        i=self.s.inspect(ROOT);self.decision(ROOT)
        with self.assertRaisesRegex(ValueError,'Review conflict'):self.decision(ROOT,'reject',expected_decision=i['expected_decision'])
        self.assertEqual(self.s.inspect(ROOT)['state'],'approve')
    def test_dependency_conflict_from_stale_review_screen(self):
        i=self.s.inspect(ROOT);self.change('competency:CAN-MEAN','description','changed')
        with self.assertRaisesRegex(ValueError,'dependency conflict'):self.decision(ROOT,expected_dependency_digest=i['dependency_digest'])
    def test_version_conflict(self):
        key='competency:CAN-MEAN';i=self.s.inspect(key);self.change(key,'description','one')
        with self.assertRaisesRegex(ValueError,'Version conflict'):self.s.stage([i['record']],{key:i['version']},'TEST-conflict')
        self.assertEqual(self.s.inspect(key)['record']['payload']['description'],'one')
    def test_batch_rollback(self):
        a=self.s.inspect('competency:CAN-MEAN');b=self.s.inspect(ROOT)
        a['record']['payload']['description']='should roll back';b['record']['payload']['canonical_id']='MISSING'
        before=self.store.db.execute('SELECT count(*) FROM versions').fetchone()[0]
        with self.assertRaises(ValueError):self.s.stage([a['record'],b['record']],{a['key']:a['version'],b['key']:b['version']},'TEST-rollback')
        self.assertEqual(before,self.store.db.execute('SELECT count(*) FROM versions').fetchone()[0])
    def test_review_transaction_rolls_back_after_journal_insert(self):
        self.store.db.execute("CREATE TRIGGER test_fail_receipt BEFORE INSERT ON requests BEGIN SELECT RAISE(ABORT,'TEST receipt failure'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'receipt failure'):self.decision(ROOT)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0],0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM review_heads').fetchone()[0],0)
        self.assertEqual(self.s.inspect(ROOT)['state'],'pending')
    def test_same_valid_version_publish_is_deterministic_and_persistent(self):
        self.approve_all();a=self.s.publish([ROOT]);b=self.s.publish([ROOT]);self.assertEqual(a,b)
        other=Store(self.path)
        try:self.assertEqual(Service(other).publish([ROOT]),a)
        finally:other.close()
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM snapshots').fetchone()[0],1)
    def test_snapshot_export_no_overwrite(self):
        self.approve_all();sid=self.s.publish([ROOT])['snapshot_id'];out=self.directory/'export'
        a=self.s.export(sid,out);self.assertEqual(a,self.s.export(sid,out))
        p=Path(a['path']);p.chmod(0o666);p.write_text('tampered')
        with self.assertRaisesRegex(ValueError,'refusing overwrite'):self.s.export(sid,out)
    def test_snapshot_source_tamper_denies_read(self):
        self.approve_all();sid=self.s.publish([ROOT])['snapshot_id'];p=self.directory/'PAPER.pdf';old=p.read_bytes();p.write_bytes(old+b'% change')
        self.assertFalse(self.s.snapshot(sid)['usable']);p.write_bytes(old)
        self.assertFalse(self.s.snapshot(sid)['usable'])
    def test_revise_reject_and_supersede(self):
        self.approve_all();self.decision(ROOT,'revise');self.assertFalse(self.s.check([ROOT])['publishable'])
        self.decision(ROOT,'supersede',replacement_action='reject');self.assertEqual(self.s.inspect(ROOT)['state'],'reject')
        self.decision(ROOT,'supersede',replacement_action='approve');self.assertTrue(self.s.check([ROOT])['publishable'])
    def test_history_immutable(self):
        self.approve_all();self.s.publish([ROOT])
        for table in ['versions','reviews','snapshots']:
            with self.assertRaises(sqlite3.IntegrityError):self.store.db.execute('DELETE FROM '+table)
    def test_confidence_cannot_bypass_gate(self):
        self.change(ROOT,'confidence',1.0);self.assertFalse(self.s.check([ROOT])['publishable'])
    def test_unresolved_scope_blocks_even_after_approval(self):
        self.change('scope:SCOPE','association_status','unresolved');self.approve_all();self.assertFalse(self.s.check([ROOT])['publishable'])
    def test_contradiction_not_attached_still_blocks(self):
        self.approve_all();r=self.s.inspect('evidence:EV-PAPER')['record'];r['payload'].update(evidence_id='EV-CONFLICT',evidence_role='contradicts')
        self.s.stage([r],{'evidence:EV-CONFLICT':None},'TEST-conflicting-evidence')
        self.assertEqual(self.s.inspect(ROOT)['state'],'stale');self.decision('evidence:EV-CONFLICT');self.decision(ROOT)
        self.assertFalse(self.s.check([ROOT])['publishable'])
    def test_new_reverse_evidence_withdraws_existing_snapshot(self):
        self.approve_all();sid=self.s.publish([ROOT])['snapshot_id']
        r=self.s.inspect('evidence:EV-PAPER')['record'];r['payload'].update(evidence_id='EV-NEW-CONFLICT',evidence_role='contradicts')
        self.s.stage([r],{'evidence:EV-NEW-CONFLICT':None},'TEST-new-conflict')
        self.assertFalse(self.s.snapshot(sid)['usable'])
        self.assertIsNone(self.s.snapshot(sid)['payload'])
    def test_published_state_is_materialized_from_journal(self):
        self.approve_all();sid=self.s.publish([ROOT])['snapshot_id']
        objects=self.s.snapshot(sid)['payload']['objects']
        self.assertEqual(objects['competency:CAN-MEAN']['payload']['status'],'approved')
        self.assertEqual(objects[ROOT]['payload']['review_status'],'approved')
        self.assertEqual(objects['source:PAPER']['payload']['verification_status'],'verified')
        self.assertEqual(self.s.inspect('competency:CAN-MEAN')['record']['payload']['status'],'draft')
        self.assertEqual(objects[ROOT]['content_version'],self.s.inspect(ROOT)['version'])
    def test_parsed_part_requires_review_and_can_publish_with_test_sources(self):
        spans=[]
        for role,lid in [('shared_stem','LOC-PAPER'),('prompt','LOC-PAPER'),('mark_scheme','LOC-SCHEME')]:
            loc=self.s.inspect('locator:'+lid);text=loc['record']['payload']['extracted_text']
            spans.append(dict(role=role,locator_id=lid,locator_version=loc['version'],start=0,end=len(text),text=text))
        parsed=dict(kind='parsed_part',payload=dict(parsed_id='PARSED-TEST',part_id='PART',parser_version='TEST-ONLY/1',marks=1,spans=spans))
        mapping=self.s.inspect(ROOT);mapping['record']['judgment_refs'].append('parsed_part:PARSED-TEST')
        self.s.stage([parsed,mapping['record']],{'parsed_part:PARSED-TEST':None,ROOT:mapping['version']},'TEST-PARSED')
        self.assertIn('parsed_part:PARSED-TEST: pending; requires approve',self.s.check([ROOT])['reasons'])
        self.approve_all();sid=self.s.publish([ROOT])['snapshot_id']
        self.assertTrue(self.s.snapshot(sid)['usable'])
        self.decision('parsed_part:PARSED-TEST','revoke')
        self.assertFalse(self.s.snapshot(sid)['usable'])
    def test_concurrent_reviews_cannot_overwrite(self):
        i=self.s.inspect(ROOT);barrier=threading.Barrier(2)
        def write(n):
            db=Store(self.path);s=Service(db)
            try:
                barrier.wait(timeout=10)
                try:s.review(ROOT,'approve' if n==1 else 'reject','TEST-'+str(n),'TEST concurrent',i['version'],i['dependency_digest'],None,'TEST-thread-'+str(n));return 'ok'
                except ValueError:return 'conflict'
            finally:db.close()
        with ThreadPoolExecutor(2) as ex:results=list(ex.map(write,[1,2]))
        self.assertCountEqual(results,['ok','conflict']);self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0],1)
    def test_import_does_not_write_or_call_models(self):
        result=subprocess.run([sys.executable,'-c','import academic_os, academic_os.core, academic_os.service; print("OK")'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0);self.assertEqual(result.stdout.strip(),'OK')
    def test_cli_decision_idempotency_conflict_and_blocked_publication(self):
        def run(*arguments):
            result=subprocess.run([sys.executable,'-X','utf8','-m','academic_os','--db',str(self.path),*arguments],capture_output=True,text=True,encoding='utf-8')
            return result.returncode,json.loads(result.stdout)
        code,i=run('inspect',ROOT);self.assertEqual(code,0)
        args=['review',ROOT,'approve','--reason','TEST ONLY CLI on temporary sources',
              '--expected-version',i['version'],'--expected-dependencies',i['dependency_digest'],
              '--expected-decision','none','--request-id','TEST-CLI']
        code,decision=run(*args);self.assertEqual(code,0)
        self.assertEqual(run(*args),(0,decision))
        args[-1]='TEST-CLI-CONFLICT';code,error=run(*args)
        self.assertEqual(code,1);self.assertIn('Review conflict',error['error'])
        code,report=run('check','--root',ROOT);self.assertEqual(code,2);self.assertFalse(report['publishable'])
        code,error=run('publish','--root',ROOT);self.assertEqual(code,1);self.assertIn('blocked',error['error'])

class RealQ2Tests(unittest.TestCase):
    def test_real_case_blocked_without_human_review(self):
        from academic_os.examples.q2 import build_candidates,ROOTS
        rows=build_candidates()
        with tempfile.TemporaryDirectory() as td:
            db=Store(Path(td)/'real.db')
            try:
                s=Service(db);s.stage(rows,{normalise(x)[0]:None for x in rows},'REAL-TEST-IMPORT-NO-APPROVAL')
                r=s.check(ROOTS);self.assertTrue(r['schema_valid']);self.assertFalse(r['publishable'])
                self.assertEqual(db.db.execute('SELECT count(*) FROM reviews').fetchone()[0],0)
                with self.assertRaises(ValueError):s.publish(ROOTS)
                self.assertEqual(s.inspect('locator:QP-Q2')['record']['payload']['page_index'],3)
                self.assertEqual(s.inspect('locator:MS-Q2-a')['record']['payload']['page_index'],6)
            finally:db.close()

if __name__=='__main__':unittest.main()
