"""P1C: copied sources, TEST ONLY approvals, isolated per-test databases."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from academic_os.storage import Store
from academic_os.service import Service
from academic_os.q3_pipeline import plan_q3
from academic_os.q3_parsing import PARTS,SOURCE_DIR,build_source_plan
from academic_os.canonical_proposals import Registry,interpret,semantic_plan
from academic_os.core import manifest,evaluate
from academic_os.models import normalise
from validate_academic_knowledge_v03 import digest
from .bundle_fixtures import seed,verify_sources,approve_core


class CanonicalReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir=tempfile.TemporaryDirectory();cls.base,service=seed(cls.base_dir.name)
        verify_sources(service);approve_core(service);cls.snapshot=service.publish_target('Q2-CORE')['snapshot_id']
        cls.sources=Path(cls.base_dir.name)/'q3-sources';shutil.copytree(SOURCE_DIR,cls.sources)
        cls.plan=plan_q3(cls.base.graph(),cls.base.decisions(),cls.sources)
        cls.oracle=json.loads((Path(__file__).parent/'fixtures/q3_gold_standard.json').read_text(encoding='utf-8-sig'))
    @classmethod
    def tearDownClass(cls):cls.base.close();cls.base_dir.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'TEST.db');self.addCleanup(self.store.close)
        self.base.db.backup(self.store.db);self.s=Service(self.store)
        self.before=self.store.graph();self.decisions=self.store.decisions()
        self.s.stage(**self.plan,request_id='TEST-Q3-STAGE')
    def proposal(self,part):return self.store.graph()['proposal:PROPOSE-Q3-2023-'+part]['record']['payload']
    def bundle(self,part):return self.s.review_bundles('BUNDLE-Q3-2023-'+part.upper())
    def verify(self):
        for sid in ('QP','MS'):
            bid='SOURCE-BUNDLE-'+sid+'-Q3-2023'
            self.s.review_source_bundle(bid,'verify','TEST-ONLY-OPERATOR','TEST ONLY copied PDFs',self.s.review_source(bid)['review_ticket'],'TEST-VERIFY-'+sid)
    def test_01_qp_identity(self):
        p=self.store.graph()['source:QP-2023']['record']['payload']
        self.assertIn('20 June 2023',p['version_label']);self.assertIn('P72819A',p['identity_basis']);self.assertNotEqual(p['content_digest'],self.before['source:QP']['record']['payload']['content_digest'])
    def test_02_ms_identity(self):
        p=self.store.graph()['source:MS-2023']['record']['payload'];self.assertIn('Summer 2023',p['identity_basis']);self.assertIn('PMT',p['identity_basis'])
    def test_03_deterministic_locators_and_exact_spans(self):
        self.assertEqual(build_source_plan(self.before,self.sources),build_source_plan(self.before,self.sources))
        g=self.store.graph()
        for part in PARTS:
            for span in g['parsed_part:PARSED-Q3-2023-'+part]['record']['payload']['spans']:
                loc=g['locator:'+span['locator_id']];self.assertEqual(span['locator_version'],loc['version'])
                self.assertEqual(span['text'],loc['record']['payload']['extracted_text'][span['start']:span['end']])
    def test_04_inspection_no_decisions(self):
        self.s.review_sources();self.s.review_bundles();self.assertEqual(self.decisions,self.store.decisions())
    def test_05_glyph_caution(self):
        p=self.store.graph()['parsed_part:PARSED-Q3-2023-b-ii']['record']['payload']
        self.assertTrue(any('no silent repair' in w for w in p['warnings']));self.assertIn('',self.store.graph()['locator:MS-2023-Q3-b-i']['record']['payload']['extracted_text'])
    def test_06_mean_reuse(self):self.assertEqual(self.proposal('b-i')['competency_id'],self.oracle['b-i']['id'])
    def test_07_no_mean_duplicate(self):
        added=[r for k,r in self.store.graph().items() if k not in self.before and r['record']['kind']=='competency'];self.assertFalse(any('mean' in r['record']['payload']['skill_name'].lower() for r in added))
    def test_08_sd_reuse(self):self.assertEqual(self.proposal('b-ii')['competency_id'],self.oracle['b-ii']['id'])
    def test_09_no_sd_duplicate(self):
        self.assertEqual(sum(r['record']['kind']=='competency' and 'standard deviation' in r['record']['payload']['skill_name'].lower() for r in self.store.graph().values()),1)
    def test_10_shared_task_reused(self):
        for part in ['b-i','b-ii']:self.assertEqual(self.proposal(part)['task_condition_ids'],[self.oracle[part]['task']])
    def test_11_registry_approval_reused(self):
        for part in ['b-i','b-ii']:
            p=self.proposal(part);self.assertEqual(p['candidate_action'],'reuse_existing')
            for item in p['registry_lookup']:self.assertEqual(item['candidate_action'],'reuse_existing')
        self.assertEqual(self.decisions,self.store.decisions())
    def test_12_new_mapping_pending(self):
        for part in PARTS:self.assertEqual(self.s.inspect('proposal:PROPOSE-Q3-2023-'+part)['state'],'pending')
    def test_13_preparation_candidate(self):
        p=self.proposal('a');self.assertEqual(p['candidate_action'],self.oracle['a']['action'])
        c=self.store.graph()['competency:'+p['competency_id']]['record']['payload'];self.assertEqual(c['skill_name'],self.oracle['a']['competency']);self.assertEqual(c['status'],'draft')
    def test_14_preparation_scope_not_universal(self):self.assertIn('not all data preparation',self.proposal('a')['evidence_scope'])
    def test_15_representativeness_candidate(self):
        p=self.proposal('c-i');self.assertEqual(p['candidate_action'],'create_candidate');self.assertEqual(self.store.graph()['competency:'+p['competency_id']]['record']['payload']['skill_name'],self.oracle['c-i']['competency'])
    def test_16_no_dataset_identity(self):
        for k,row in self.store.graph().items():
            if k not in self.before and row['record']['kind'] in ('competency','concept','task_condition'):
                p=row['record']['payload'];identity=k+' '+p.get('name',p.get('skill_name',''))
                for forbidden in ('Leeming','1987','Rainfall','May','October','winter','0.025'):self.assertNotIn(forbidden,identity)
    def test_17_unresolved(self):self.assertEqual(self.proposal('c-ii')['candidate_action'],'unresolved')
    def test_18_reasoning_preserved(self):
        p=self.proposal('c-ii');self.assertIn('winter',p['observation'].lower());self.assertIn('underestimate',p['observation']);self.assertTrue(p['alternatives'])
    def test_19_no_context_infer_shortcut(self):
        p=self.proposal('c-ii');self.assertIsNone(p['competency_id']);self.assertNotIn('competency:CAN-STAT-CONTEXT-INFER',self.bundle('c-ii')['review_ticket']['versions'])
    def test_20_unresolved_not_rejected(self):self.assertEqual(self.proposal('c-ii')['review_status'],'pending')
    def test_21_unresolved_not_excluded(self):self.assertIn('proposal:PROPOSE-Q3-2023-c-ii',self.s.check_target('Q3-2023-CORE')['versions'])
    def test_22_unresolved_observed(self):self.assertTrue(self.proposal('c-ii')['observation'])
    def test_23_new_sources_pending(self):
        for k in self.store.graph():
            if k not in self.before and k.startswith(('source:','locator:')):self.assertEqual(self.s.inspect(k)['state'],'pending')
    def test_24_publication_blocked(self):
        r=self.s.check_target('Q3-2023-CORE');self.assertFalse(r['publishable']);self.assertTrue(any('unresolved canonical' in x for x in r['reasons']))
    def test_25_q2_snapshot_usable(self):self.assertTrue(self.s.snapshot(self.snapshot)['usable'])
    def test_26_q2_decisions_unchanged(self):self.assertEqual(self.decisions,self.store.decisions())
    def test_27_q2_versions_unchanged(self):
        for k,v in self.before.items():self.assertEqual(v,self.store.graph()[k])
    def test_28_q2_oracle(self):
        oracle=json.loads((Path(__file__).parent/'fixtures/q2_gold_standard.json').read_text(encoding='utf-8-sig'));snapshot=self.s.snapshot(self.snapshot)['payload']
        for unit in snapshot['semantic_units']:
            expected=oracle['parts'][unit['part_id']];i=unit['interpretations'][0]
            self.assertEqual(i['competency']['id'],expected['competency']);self.assertEqual(sorted(c['id'] for c in i['concepts']),sorted(expected['concepts']))
            self.assertEqual([c['id'] for c in i['task_conditions']],expected['task_conditions'])
        for key in oracle['excluded']:self.assertNotIn(key,snapshot['objects'])
        self.assertTrue(self.s.check_target('Q2-CORE')['publishable'])
    def test_29_unresolved_blocks_even_all_approved_states(self):
        g=self.store.graph();roots=['proposal:PROPOSE-Q3-2023-'+p for p in PARTS]
        fake={k:dict(action='verify' if r['record']['kind'] in ('source','locator') else 'approve',dependency_digest=digest(manifest(g,[k]))) for k,r in g.items()}
        r=evaluate(g,roots,fake,[]);self.assertFalse(r['publishable']);self.assertTrue(any('unresolved canonical' in x for x in r['reasons']))
    def test_30_no_decision_rewrite(self):
        self.assertEqual([tuple(x) for x in self.base.db.execute('select * from reviews')],[tuple(x) for x in self.store.db.execute('select * from reviews')])
    def test_31_no_snapshot_rewrite(self):
        self.assertEqual([tuple(x) for x in self.base.db.execute('select * from snapshots')],[tuple(x) for x in self.store.db.execute('select * from snapshots')])
    def test_32_append_versions(self):self.assertEqual(self.store.db.execute('select count(*) from versions').fetchone()[0]-self.base.db.execute('select count(*) from versions').fetchone()[0],43)
    def test_33_deterministic_and_idempotent(self):
        self.assertEqual(self.plan,plan_q3(self.before,self.decisions,self.sources));before=self.store.db.execute('select count(*) from versions').fetchone()[0]
        self.s.stage(**self.plan,request_id='TEST-Q3-STAGE')
        again=plan_q3(self.store.graph(),self.store.decisions(),self.sources);self.s.stage(**again,request_id='TEST-REPEAT')
        self.assertEqual(before,self.store.db.execute('select count(*) from versions').fetchone()[0])
    def test_34_rules_ignore_context_numbers_and_ids(self):
        for context in ['Leeming 1987 summary statistics','Different place 2040 summary statistics']:
            meaning=interpret('Find an estimate of the average','', 'B1 awarded','',context)
            self.assertEqual(meaning['competency'],'Calculate the mean')
    def test_35_same_case_identity_different_evidence_not_forced(self):
        meaning=interpret('Explain why the shape is skewed','','B1','Skewness','summary statistics')
        self.assertIsNone(meaning['competency'])
        meaning=interpret('Prepare these data','','Convert special codes to a numerical value','', 'different dataset')
        self.assertEqual(meaning['competency'],'Prepare data for statistical analysis')
    def test_36_pending_registry_not_trusted(self):
        registry=Registry(self.store.graph(),self.store.decisions());r=registry.lookup('competency','Prepare data for statistical analysis')
        self.assertEqual(r['candidate_action'],'unresolved');self.assertIsNone(r['selected'])
    def test_37_existing_definition_not_reapproved_when_mapping_approved(self):
        self.verify();bid='BUNDLE-Q3-2023-B-I';old=self.store.decisions()['competency:CAN-STAT-MEAN-CALC']
        result=self.s.review_bundle(bid,'approve','TEST-ONLY-OPERATOR','TEST ONLY new mapping',self.s.review_bundles(bid)['review_ticket'],'TEST-NEW-MAP')
        self.assertEqual(old,self.store.decisions()['competency:CAN-STAT-MEAN-CALC'])
        self.assertTrue(any(x['key']=='competency:CAN-STAT-MEAN-CALC' for x in result['reused']))
        self.assertTrue(self.s.snapshot(self.snapshot)['usable'])
    def test_38_unresolved_approval_fails_atomically(self):
        self.verify();before=self.store.decisions();bid='BUNDLE-Q3-2023-C-II'
        with self.assertRaisesRegex(ValueError,'Unresolved canonical'):
            self.s.review_bundle(bid,'approve','TEST-ONLY-OPERATOR','TEST ONLY forbidden unresolved',self.s.review_bundles(bid)['review_ticket'],'TEST-UNRESOLVED')
        self.assertEqual(before,self.store.decisions())
    def test_39_revise_and_stale_ticket(self):
        bid='BUNDLE-Q3-2023-A';ticket=self.s.review_bundles(bid)['review_ticket']
        self.s.review_bundle(bid,'revise','TEST-ONLY-OPERATOR','TEST ONLY needs revision',ticket,'TEST-REVISE')
        self.assertEqual(self.s.inspect('proposal:PROPOSE-Q3-2023-a')['state'],'revise')
        with self.assertRaisesRegex(ValueError,'stale/conflict'):self.s.review_bundle(bid,'reject','TEST-ONLY-OPERATOR','TEST ONLY old ticket',ticket,'TEST-OLD')
    def test_40_cli_reviewer_view(self):
        result=subprocess.run([sys.executable,'-X','utf8','-m','academic_os','--db',str(self.store.path),'review-bundle','BUNDLE-Q3-2023-B-I'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertIn('REUSE_EXISTING',result.stdout);self.assertIn('Calculate the mean',result.stdout);self.assertIn('Q3-2023-CORE',result.stdout)
    def test_41_parse_hierarchy_marks_and_dependencies(self):
        g=self.store.graph();self.assertEqual([g['parsed_part:PARSED-Q3-2023-'+p]['record']['payload']['marks'] for p in PARTS],[2,1,2,1,1])
        self.assertEqual(g['question_part:Q3-2023-b-i']['record']['payload']['parent_part_id'],'Q3-2023-b')
        self.assertIn('question_part:Q3-2023-b-i',g['question_part:Q3-2023-c-ii']['record']['judgment_refs'])
    def test_42_candidate_cannot_attest_approval(self):
        raw=copy.deepcopy(self.store.graph()['proposal:PROPOSE-Q3-2023-a']['record']);raw['payload']['review_status']='approved';raw['payload']['review_decision_id']='FORGED'
        with self.assertRaises(ValueError):normalise(raw)

    def test_43_projection_validates_original_associations(self):
        from academic_os.compatibility import validate_v03
        g=copy.deepcopy(self.store.graph());raw=g['locator:MS-Q2-a']['record']
        raw['payload']['assessment_part_id']='NONEXISTENT'
        k,v,r=normalise(raw);g[k]=dict(version=v,record=r)
        selected={k:g[k] for k in manifest(g,['proposal:PROPOSE-Q3-2023-b-i'])}
        with self.assertRaisesRegex(ValueError,'Unknown question_part'):validate_v03(selected,{},reference_graph=g)

    def test_44_registry_lookup_is_not_an_approval_credential(self):
        raw=copy.deepcopy(self.store.graph()['proposal:PROPOSE-Q3-2023-a']['record'])
        raw['payload']['registry_lookup']=[dict(kind='competency',query='Fake',candidate_action='reuse_existing',selected='competency:FAKE')]
        self.s.stage([raw],{'proposal:PROPOSE-Q3-2023-a':self.store.graph()['proposal:PROPOSE-Q3-2023-a']['version']},'TEST-UNTRUSTED-LOOKUP')
        self.assertFalse(self.s.check_target('Q3-2023-CORE')['publishable']);self.assertEqual(self.decisions,self.store.decisions())

if __name__=='__main__':unittest.main()
