"""Protected snapshots are read only; all adversarial changes use disposable DBs.

Pure-composition conflicts intentionally use TEST ONLY copies of checked payloads:
the current single-head store normally rejects older versions before composition.
"""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from academic_os.product_catalog import PROTECTED_SNAPSHOTS,PRODUCT_REFS,product_ref
from academic_os.product_reader import read_usable_snapshots,UnusableSnapshot
from academic_os.product_service import AcademicProductService,_compose,CompositionConflict
from academic_os.product_models import TeacherTopicView
from academic_os.storage import Store
from academic_os.service import Service

DB=Path('var/p0_q2.sqlite3')
Q2,Q3=PROTECTED_SNAPSHOTS
TOPIC='standard-deviation'


def database_state(path):
    c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        return {name:list(c.execute('SELECT * FROM '+name)) for name in
            ('versions','heads','reviews','review_heads','requests','snapshots','snapshot_members','snapshot_blocks')}
    finally:c.close()


class TeacherProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=database_state(DB);cls.before_hash=hashlib.sha256(DB.read_bytes()).hexdigest()
        cls.payloads=read_usable_snapshots(DB,PROTECTED_SNAPSHOTS)
        cls.result=_compose(TOPIC,cls.payloads);cls.view=cls.result.view
    @classmethod
    def tearDownClass(cls):
        assert cls.before==database_state(DB),'Product tests changed real records'
        assert cls.before_hash==hashlib.sha256(DB.read_bytes()).hexdigest(),'Product tests changed real DB bytes'
    def temporary_store(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        store=Store(Path(tmp.name)/'TEST.sqlite3');self.addCleanup(store.close)
        c=sqlite3.connect(DB.resolve().as_uri()+'?mode=ro',uri=True)
        try:c.backup(store.db)
        finally:c.close()
        return store,Service(store)
    def revoke(self,service,key):
        i=service.inspect(key)
        service.review(key,'revoke','TEST-ONLY-OPERATOR','TEST ONLY disposable DB revocation',
            i['version'],i['dependency_digest'],i['expected_decision'],'TEST-REVOKE')
    def test_01_unusable_rejected(self):
        store,s=self.temporary_store();self.revoke(s,'proposal:PROPOSE-Q3-2023-b-ii')
        with self.assertRaises(UnusableSnapshot):AcademicProductService(store.path).get_topic_view(TOPIC,[Q3])
    def test_02_q2_usable(self):
        v=_compose(TOPIC,{Q2:self.payloads[Q2]}).view;self.assertEqual(v.trust_summary.reviewed_example_count,1)
    def test_03_q3_usable(self):
        v=_compose(TOPIC,{Q3:self.payloads[Q3]}).view;self.assertEqual(v.trust_summary.reviewed_example_count,1)
    def test_04_detached_export_not_trust(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'export.json';p.write_text(json.dumps(self.payloads[Q2]),encoding='utf-8')
            with self.assertRaises((ValueError,sqlite3.DatabaseError)):AcademicProductService(p).get_topic_view(TOPIC,[Q2])
        with self.assertRaises(ValueError):read_usable_snapshots(DB,[self.payloads[Q2]])
    def test_05_composition_order(self):
        self.assertEqual(self.view.serialize(),_compose(TOPIC,dict(reversed(list(self.payloads.items())))).view.serialize())
    def test_06_same_competency_identity(self):
        traces=self.result.provenance['assessment_examples']
        self.assertEqual({t['canonical_id'] for t in traces},{'CAN-STAT-SD-CALC'});self.assertEqual(len(self.view.capabilities),1)
    def test_07_same_concept_identity(self):
        self.assertEqual({t['concept_id'] for t in self.result.provenance['assessment_examples']},{'CON-STAT-SD'})
        self.assertEqual(len(self.view.concepts),1)
    def test_08_same_task_identity(self):
        self.assertEqual({tuple(t['task_condition_ids']) for t in self.result.provenance['assessment_examples']},{('TC-SUMMARY-STATISTICS',)})
        self.assertEqual(len(self.view.capabilities[0].task_forms),1)
    def test_09_both_assessments_visible(self):
        self.assertEqual([(e.year,e.question_part) for e in self.view.assessment_evidence],[(2025,'Q2(b)'),(2023,'Q3(b)(ii)')])
    def test_10_canonical_version_conflict(self):
        for key in ('competency:CAN-STAT-SD-CALC','concept:CON-STAT-SD','task_condition:TC-SUMMARY-STATISTICS'):
            with self.subTest(key=key):
                p=copy.deepcopy(self.payloads);p[Q3]['objects'][key]['content_version']='TEST-INCOMPATIBLE'
                with self.assertRaisesRegex(CompositionConflict,'Incompatible published versions'):_compose(TOPIC,p)
    def test_11_title_from_concept(self):self.assertEqual(self.view.identity.title,'Standard deviation')
    def test_12_capability(self):self.assertEqual(self.view.capabilities[0].name,'Calculate standard deviation')
    def test_13_task_form(self):self.assertEqual(self.view.capabilities[0].task_forms[0].name,'From summary statistics')
    def test_14_q2_wording_marks(self):
        e=self.view.assessment_evidence[0];self.assertIn('coach A',e.question_wording);self.assertEqual(e.marks,2);self.assertEqual(e.paper,'9MA0/31')
    def test_15_q3_directive_and_marks(self):
        e=self.view.assessment_evidence[1];self.assertIn('Calculate estimates',e.question_wording);self.assertIn('Daily Total Rainfall',e.question_wording);self.assertEqual(e.marks,2)
    def test_16_internal_identifiers_hidden(self):
        text=self.view.serialize()
        for value in ('CAN-STAT','TC-SUMMARY','CON-STAT','PROPOSE-','dependency_digest','review_heads','content_version','decision_id',Q2,Q3):self.assertNotIn(value,text)
    def test_17_object_and_unit_order_independent(self):
        p=copy.deepcopy(self.payloads)
        for payload in p.values():
            payload['objects']=dict(reversed(list(payload['objects'].items())))
            payload['semantic_units'].reverse()
        self.assertEqual(self.view.serialize(),_compose(TOPIC,p).view.serialize())
    def test_18_byte_serialization_stable(self):
        self.assertEqual(self.view.serialize().encode(),_compose(TOPIC,self.payloads).view.serialize().encode())
    def test_19_deferred_not_teacher_truth(self):
        for text in (self.view.serialize(),json.dumps(self.result.provenance['assessment_examples'])):
            for value in ('c-ii','Q3(c)(ii)','underestimate','winter'):self.assertNotIn(value,text)
    def test_20_optional_candidate_absent(self):
        self.assertNotIn('CONTEXT-INFER',json.dumps(self.result.provenance));self.assertNotIn('contextual inference',self.view.serialize().lower())
    def test_21_pending_mapping_rejected(self):
        store,s=self.temporary_store();i=s.inspect('proposal:PROPOSE-Q3-2023-b-ii');r=copy.deepcopy(i['record'])
        r['payload']['reasoning']+=' TEST ONLY new pending version'
        s.stage([r],{i['key']:i['version']},'TEST-NEW-PENDING')
        with self.assertRaises(UnusableSnapshot):AcademicProductService(store.path).get_topic_view(TOPIC,[Q3])
    def test_22_unverified_source_rejected(self):
        store,s=self.temporary_store();self.revoke(s,'source:QP-2023')
        with self.assertRaises(UnusableSnapshot):AcademicProductService(store.path).get_topic_view(TOPIC,[Q3])
    def test_23_q2_snapshot_unchanged(self):
        raw=dict((r[0],r[1]) for r in self.before['snapshots']);self.assertEqual(json.loads(raw[Q2]),self.payloads[Q2])
    def test_24_q3_snapshot_unchanged(self):
        raw=dict((r[0],r[1]) for r in self.before['snapshots']);self.assertEqual(json.loads(raw[Q3]),self.payloads[Q3])
    def test_25_q2_gold_standard_roots(self):
        p=self.payloads[Q2];self.assertEqual([u['question'] for u in p['semantic_units']],['Q2(a)','Q2(b)','Q2(c)'])
        self.assertEqual(p['publication_target']['target_id'],'Q2-CORE')
    def test_26_q3_gold_standard_roots(self):
        self.assertEqual([u['question'] for u in self.payloads[Q3]['semantic_units']],['Q3(a)','Q3(b)(i)','Q3(b)(ii)','Q3(c)(i)'])
    def test_27_governance_unchanged(self):self.assertEqual(self.before['requests'],database_state(DB)['requests'])
    def test_28_source_and_academic_decisions_unchanged(self):self.assertEqual(self.before['reviews'],database_state(DB)['reviews'])
    def test_29_no_stale_service_cache(self):
        store,s=self.temporary_store();product=AcademicProductService(store.path)
        self.assertEqual(product.get_topic_view(TOPIC,[Q2,Q3]).trust_summary.reviewed_example_count,2)
        self.revoke(s,'proposal:PROPOSE-Q3-2023-b-ii')
        with self.assertRaises(UnusableSnapshot):product.get_topic_view(TOPIC,[Q2,Q3])
    def test_30_rejected_reads_do_not_write_blocks_to_database(self):
        store,s=self.temporary_store()
        # Append an explicit block to simulate a prior withdrawal, only in TEST DB.
        store.db.execute('INSERT INTO snapshot_blocks VALUES(?,?,?,?)',(Q3,'TEST-BLOCK','TEST ONLY withdrawal','TEST'))
        before=database_state(store.path);h=hashlib.sha256(store.path.read_bytes()).hexdigest()
        with self.assertRaises(UnusableSnapshot):AcademicProductService(store.path).get_topic_view(TOPIC,[Q3])
        self.assertEqual(before,database_state(store.path));self.assertEqual(h,hashlib.sha256(store.path.read_bytes()).hexdigest())
    def test_31_same_version_conflicting_definition(self):
        p=copy.deepcopy(self.payloads);p[Q3]['objects']['concept:CON-STAT-SD']['payload']['description']='TEST ONLY conflicting definition'
        with self.assertRaises(CompositionConflict):_compose(TOPIC,p)
    def test_32_description_verbatim(self):
        self.assertEqual(self.view.concepts[0].description,self.payloads[Q2]['objects']['concept:CON-STAT-SD']['payload']['description'])
    def test_33_scope_candidate_not_equivalence(self):
        self.assertTrue(self.view.trust_summary.curriculum_verified);self.assertFalse(self.view.trust_summary.curriculum_association_confirmed)
        self.assertEqual(self.view.curriculum.references[0].association_status,'candidate')
    def test_34_no_curriculum_fallback(self):
        p=copy.deepcopy(self.payloads)
        for item in p.values():item['objects']['locator:SPEC-2.3']['payload']['extracted_text']='TEST ONLY no matching wording'
        view=_compose(TOPIC,p).view;self.assertFalse(view.trust_summary.curriculum_verified);self.assertEqual(view.curriculum.references,())
    def test_35_duplicate_inputs_do_not_duplicate_examples(self):
        view=AcademicProductService(DB).get_topic_view(TOPIC,[Q2,Q3,Q2])
        self.assertEqual(view.serialize(),self.view.serialize())
    def test_36_missing_db_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'missing.sqlite3'
            with self.assertRaises(FileNotFoundError):AcademicProductService(p).get_topic_view(TOPIC,[Q2])
            self.assertFalse(p.exists())
    def test_37_cli_text_json_and_safe_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'view.json';base=[sys.executable,'-X','utf8','-m','academic_os','--db',str(DB),'teacher-topic',TOPIC]
            r=subprocess.run(base+['--json','--output',str(output)],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(r.returncode,0,r.stderr+r.stdout);self.assertEqual(output.read_bytes(),self.view.serialize().encode())
            self.assertEqual(json.loads(r.stdout),self.view.model_dump(mode='json'))
            r=subprocess.run(base,capture_output=True,text=True,encoding='utf-8');self.assertEqual(r.returncode,0);self.assertIn('2 reviewed assessment examples',r.stdout)
            output.write_text('TEST ONLY existing unrelated file',encoding='utf-8')
            r=subprocess.run(base+['--output',str(output)],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(r.returncode,1);self.assertEqual(output.read_text(encoding='utf-8'),'TEST ONLY existing unrelated file')
    def test_38_whole_request_rejects_one_bad_snapshot(self):
        store,s=self.temporary_store();self.revoke(s,'proposal:PROPOSE-Q3-2023-b-ii')
        with self.assertRaises(UnusableSnapshot):AcademicProductService(store.path).get_topic_view(TOPIC,[Q2,Q3])
    def test_39_teacher_schema_refuses_internal_fields(self):
        payload=self.view.model_dump();payload['snapshot_id']=Q2
        with self.assertRaises(ValueError):TeacherTopicView(**payload)
    def test_40_marks_are_examples_not_statistics(self):
        d=self.view.model_dump(mode='json')
        for key in ('frequency','difficulty','confidence','trend','common_mistakes','exam_probability'):self.assertNotIn(key,d)
        self.assertEqual(d['trust_summary']['source_count'],5)
    def test_41_no_question_label_shortcuts_or_guessed_metadata(self):
        p=copy.deepcopy(self.payloads)
        for payload in p.values():
            for row in payload['objects'].values():
                if row['kind']=='question':row['payload']['label']='TEST ONLY unnamed assessment'
                if row['kind']=='question_part':row['payload']['label']='TEST ONLY differently named exercise'
        view=_compose(TOPIC,p).view
        self.assertEqual(len(view.assessment_evidence),2)
        self.assertTrue(all(e.year is None and e.session is None and e.paper is None for e in view.assessment_evidence))
    def test_42_corrupt_snapshot_rejected_without_mutation(self):
        store,s=self.temporary_store()
        # TEST ONLY adversarial detached row; no foundation mutation in the real DB.
        store.db.execute('DROP TRIGGER snapshots_no_update')
        payload=copy.deepcopy(self.payloads[Q3]);payload['semantic_units'][0]['question']='TEST CORRUPTION'
        store.db.execute('UPDATE snapshots SET payload=? WHERE snapshot_id=?',(json.dumps(payload),Q3))
        before=database_state(store.path)
        with self.assertRaisesRegex(ValueError,'Snapshot content integrity'):AcademicProductService(store.path).get_topic_view(TOPIC,[Q3])
        self.assertEqual(before,database_state(store.path))
    def test_43_v2_identity_and_no_flat_legacy_fields(self):
        d=self.view.model_dump(mode='json')
        self.assertEqual(d['schema_version'],'teacher-topic/2')
        self.assertEqual(d['identity']['view_key'],'standard-deviation')
        self.assertEqual(d['identity']['view_type'],'knowledge_topic')
        for field in ('competencies','task_forms','curriculum_wording'):self.assertNotIn(field,d)
    def test_44_product_identity_separate_from_concept(self):
        p=copy.deepcopy(self.payloads)
        for payload in p.values():payload['objects']['concept:CON-STAT-SD']['payload']['name']='TEST ONLY new concept display'
        v=_compose(TOPIC,p).view
        self.assertEqual(v.identity.title,'Standard deviation');self.assertNotEqual(v.identity.view_key,v.concepts[0].ref)
        self.assertEqual(v.concepts[0].name,'TEST ONLY new concept display')
    def test_45_product_refs_identity_traceability(self):
        expected={'concept-standard-deviation':'concept:CON-STAT-SD',
            'capability-standard-deviation-calculate':'competency:CAN-STAT-SD-CALC',
            'task-form-summary-statistics':'task_condition:TC-SUMMARY-STATISTICS'}
        self.assertEqual({r:t['object_key'] for r,t in self.result.provenance['product_refs'].items()},expected)
        self.assertTrue(all(len(t['snapshot_ids'])==2 for t in self.result.provenance['product_refs'].values()))
    def test_46_individual_snapshots_reuse_refs(self):
        a=_compose(TOPIC,{Q2:self.payloads[Q2]}).view;b=_compose(TOPIC,{Q3:self.payloads[Q3]}).view
        self.assertEqual(a.capabilities[0].ref,b.capabilities[0].ref)
        self.assertEqual(a.capabilities[0].task_forms[0].ref,b.capabilities[0].task_forms[0].ref)
        self.assertEqual(a.concepts[0].ref,b.concepts[0].ref)
    def test_47_capability_relationships(self):
        c=self.view.capabilities[0]
        self.assertEqual(c.concept_refs,(self.view.concepts[0].ref,))
        self.assertEqual(c.task_forms[0].name,'From summary statistics')
        self.assertEqual(c.ref,'capability-standard-deviation-calculate')
    def test_48_evidence_uses_refs_not_display_relationships(self):
        for e in self.view.assessment_evidence:
            self.assertEqual(e.capability_ref,self.view.capabilities[0].ref)
            self.assertEqual(e.task_form_refs,(self.view.capabilities[0].task_forms[0].ref,))
            self.assertNotIn('competency',e.model_dump());self.assertNotIn('task_forms',e.model_dump())
    def test_49_renaming_capability_preserves_refs_and_evidence(self):
        p=copy.deepcopy(self.payloads)
        for payload in p.values():payload['objects']['competency:CAN-STAT-SD-CALC']['payload']['skill_name']='TEST ONLY renamed capability'
        v=_compose(TOPIC,p).view
        self.assertEqual(v.assessment_evidence,self.view.assessment_evidence)
        self.assertEqual(v.capabilities[0].ref,self.view.capabilities[0].ref)
        self.assertEqual(v.capabilities[0].name,'TEST ONLY renamed capability')
    def test_50_renaming_task_form_preserves_refs_and_evidence(self):
        p=copy.deepcopy(self.payloads)
        for payload in p.values():payload['objects']['task_condition:TC-SUMMARY-STATISTICS']['payload']['name']='TEST ONLY renamed task'
        v=_compose(TOPIC,p).view
        self.assertEqual(v.assessment_evidence,self.view.assessment_evidence)
        self.assertEqual(v.capabilities[0].task_forms[0].ref,self.view.capabilities[0].task_forms[0].ref)
    def test_51_no_unsupported_task_relationship(self):
        p=copy.deepcopy(self.payloads[Q2]);p['objects']['part_mapping:MAP-Q2-b-SD-CALC']['payload']['semantics']['task_condition_ids']=[]
        with self.assertRaisesRegex(ValueError,'lacks published support'):_compose(TOPIC,{Q2:p})
    def test_52_no_unsupported_concept_relationship(self):
        p=copy.deepcopy(self.payloads[Q2]);p['objects']['part_mapping:MAP-Q2-b-SD-CALC']['payload']['semantics']['concept_link_ids']=[]
        with self.assertRaisesRegex(ValueError,'lacks published support'):_compose(TOPIC,{Q2:p})
    def test_53_duplicate_product_refs_rejected(self):
        d=self.view.model_dump();d['capabilities'][0]['ref']=d['concepts'][0]['ref']
        with self.assertRaisesRegex(ValueError,'unique'):TeacherTopicView(**d)
        with patch.dict(PRODUCT_REFS,{'concept:CON-STAT-SD':'task-form-summary-statistics'}):
            with self.assertRaisesRegex(ValueError,'collision'):product_ref('concept:CON-STAT-SD')
    def test_54_unknown_identity_not_slugged_from_name(self):
        with self.assertRaisesRegex(ValueError,'No product reference'):product_ref('competency:TEST-UNKNOWN')
    def test_55_dangling_capability_reference_rejected(self):
        d=self.view.model_dump();d['assessment_evidence'][0]['capability_ref']='unknown'
        with self.assertRaisesRegex(ValueError,'capability_ref'):TeacherTopicView(**d)
    def test_56_wrong_parent_task_ref_rejected(self):
        d=self.view.model_dump();c=copy.deepcopy(d['capabilities'][0]);c['ref']='TEST-other-capability';c['task_forms']=()
        d['capabilities']=(*d['capabilities'],c);d['assessment_evidence'][0]['capability_ref']=c['ref']
        with self.assertRaisesRegex(ValueError,'belong'):TeacherTopicView(**d)
    def test_57_dangling_concept_ref_rejected(self):
        d=self.view.model_dump();d['capabilities'][0]['concept_refs']=('unknown',)
        with self.assertRaisesRegex(ValueError,'concept refs'):TeacherTopicView(**d)
    def test_58_v1_academic_content_and_notes_preserved(self):
        old=json.loads(Path('output/p2a_teacher_view/p2a1_baseline/standard_deviation.json').read_text(encoding='utf-8'))
        for previous,current in zip(old['assessment_evidence'],self.view.assessment_evidence):
            for field in ('assessment_label','year','session','paper','question_part','marks','question_wording','reading_notes'):
                self.assertEqual(previous[field],current.model_dump(mode='json')[field])
        self.assertEqual(old['concepts'][0]['description'],self.view.concepts[0].description)
        self.assertEqual(old['trust_summary'],self.view.trust_summary.model_dump(mode='json'))
    def test_59_notes_classified_as_evidence(self):
        from academic_os.product_models import AssessmentExample
        self.assertIn('not teaching',AssessmentExample.model_fields['reading_notes'].description)
        from academic_os.product_rendering import teacher_topic_text
        text=teacher_topic_text(self.view)
        self.assertIn('Evidence/source-quality note:',text);self.assertIn('Students should be able to',text)
        self.assertNotIn('CAN-STAT-',text)
    def test_60_v1_schema_not_silently_accepted(self):
        d=self.view.model_dump();d['schema_version']='teacher-topic/1'
        with self.assertRaises(ValueError):TeacherTopicView(**d)


if __name__=='__main__':unittest.main()
