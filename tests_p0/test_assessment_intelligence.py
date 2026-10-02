"""P2B: real state is read-only; mutations below are TEST ONLY copies/fixtures."""
import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from academic_os.assessment_intelligence import AssessmentIntelligenceService,_derive,intelligence_text
from academic_os.product_service import AcademicProductService
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_reader import UnusableSnapshot
from academic_os.storage import Store
from academic_os.service import Service
from tests_p0.teacher_product_acceptance import state

DB=Path('var/p0_q2.sqlite3')
TOPIC='standard-deviation'


class AssessmentIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state()
        cls.upstream=AcademicProductService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.input=cls.upstream.view.model_dump(mode='json')
        cls.result=AssessmentIntelligenceService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.view=cls.result.view

    @classmethod
    def tearDownClass(cls):
        assert state()==cls.before,'P2B changed real database'

    def fixture(self):return copy.deepcopy(self.input)

    def test_01_schema(self):
        self.assertEqual(self.view.schema_version,'assessment-intelligence/1')
        self.assertEqual(self.view.upstream_schema_version,'teacher-topic/2')
        self.assertEqual(self.view.identity.view_key,TOPIC)
        self.assertEqual(self.view.identity.view_type,'assessment_intelligence')

    def test_02_unsupported_schema(self):
        data=self.fixture();data['schema_version']='teacher-topic/1'
        with self.assertRaisesRegex(ValueError,'Unsupported upstream schema'):_derive(data)

    def test_03_input_unchanged(self):
        data=self.fixture();before=copy.deepcopy(data);_derive(data)
        self.assertEqual(data,before)
        self.assertEqual(self.upstream.view.serialize(),Path('output/p2a_teacher_view/standard_deviation.json').read_text(encoding='utf-8'))

    def test_04_focus(self):
        focus=self.view.assessment_focus
        self.assertEqual(focus.concepts[0].name,'Standard deviation')
        self.assertEqual(focus.capabilities[0].name,'Calculate standard deviation')
        self.assertEqual(focus.capabilities[0].task_forms[0].name,'From summary statistics')

    def test_05_exact_evidence_preserved(self):
        self.assertEqual([(e.year,e.question_part,e.marks) for e in self.view.reviewed_examples],[(2025,'Q2(b)',2),(2023,'Q3(b)(ii)',2)])
        for actual,expected in zip(self.view.reviewed_examples,self.upstream.view.assessment_evidence):
            self.assertEqual(actual.model_dump(exclude={'ref','epistemic_level'}),expected.model_dump())

    def test_06_same_refs(self):
        examples=self.view.reviewed_examples
        self.assertEqual(len({e.capability_ref for e in examples}),1)
        self.assertEqual(len({e.task_form_refs for e in examples}),1)
        self.assertEqual(len({e.ref for e in examples}),2)

    def test_07_observation_types(self):
        self.assertEqual({p.type for p in self.view.observed_patterns},
            {'shared_capability','shared_task_form','distinct_question_wording','shared_marks'})
        self.assertTrue(all(p.epistemic_level=='derived_observation' for p in self.view.observed_patterns))
        self.assertTrue(all(e.epistemic_level=='observed_evidence' for e in self.view.reviewed_examples))

    def test_08_all_patterns_trace_to_evidence(self):
        refs={e.ref for e in self.view.reviewed_examples}
        for p in self.view.observed_patterns:
            self.assertEqual(set(p.evidence_refs),refs);self.assertEqual(p.evidence_count,2)
        self.assertEqual(set(self.result.provenance['assessment_examples']),refs)

    def test_09_limitations(self):
        self.assertTrue({'insufficient_evidence_for_frequency','insufficient_evidence_for_typical_marks',
            'difficulty_not_calibrated','no_exam_prediction','no_student_error_evidence'}<= {l.code for l in self.view.limitations})

    def test_10_marks_not_typical(self):
        statements=' '.join(p.statement for p in self.view.observed_patterns)
        self.assertIn('All 2 reviewed examples carry 2 marks.',statements)
        self.assertNotIn('typical',statements)

    def test_11_task_not_usual(self):
        statements=' '.join(p.statement for p in self.view.observed_patterns)
        self.assertIn('All 2 reviewed examples use the task form',statements)
        self.assertNotIn('usually',statements)

    def test_12_no_generalising_claims(self):
        text=self.view.serialize().lower()
        for phrase in ('frequently tested','commonly tested','high frequency','low frequency',
            'popular question type','often appears','rarely appears','typically 2 marks',
            'usually assessed from summary statistics','difficulty_score','prediction_score','trust_score'):
            with self.subTest(phrase=phrase):self.assertNotIn(phrase,text)
        claims=' '.join(p.statement for p in self.view.observed_patterns).lower()
        for word in ('easy','medium','hard','introductory','challenging','mistake','next exam'):
            self.assertNotIn(word,claims)

    def test_13_excluded_unresolved(self):
        text=self.view.serialize()
        for token in ('Q3(c)(ii)','CONTEXT-INFER','underestimate','pending','deferred'):
            self.assertNotIn(token,text)

    def test_14_curriculum_boundary(self):
        self.assertEqual(self.view.curriculum,self.upstream.view.curriculum)
        self.assertEqual(self.view.curriculum.references[0].association_status,'candidate')
        self.assertTrue(self.view.trust_summary.upstream.curriculum_verified)
        self.assertFalse(self.view.trust_summary.upstream.curriculum_association_confirmed)

    def test_15_source_warnings_not_patterns(self):
        statements=' '.join(p.statement for p in self.view.observed_patterns)
        for e in self.view.reviewed_examples:
            self.assertTrue(e.reading_notes)
            for note in e.reading_notes:self.assertNotIn(note,statements)

    def test_16_fresh_upstream_each_read(self):
        service=AssessmentIntelligenceService(DB)
        with patch.object(service._products,'read_topic',return_value=self.upstream) as read:
            service.read_topic(TOPIC,PROTECTED_SNAPSHOTS);service.read_topic(TOPIC,PROTECTED_SNAPSHOTS)
            self.assertEqual(read.call_count,2)
        with patch.object(service._products,'read_topic',side_effect=UnusableSnapshot('TEST withdrawal')):
            with self.assertRaises(UnusableSnapshot):service.read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_17_no_raw_db_dependency(self):
        source=Path('academic_os/assessment_intelligence.py').read_text(encoding='utf-8')
        for token in ('import sqlite3','from .storage','from .service import','read_usable_snapshots','_compose('):
            self.assertNotIn(token,source)

    def test_18_normal_vs_provenance(self):
        text=self.view.serialize()
        for token in ('CAN-STAT','CON-STAT','TC-SUMMARY',*PROTECTED_SNAPSHOTS):self.assertNotIn(token,text)
        refs=self.result.provenance['upstream']['product_refs']
        self.assertEqual(refs['capability-standard-deviation-calculate']['object_key'],'competency:CAN-STAT-SD-CALC')

    def test_19_repeated_deterministic(self):
        self.assertEqual(_derive(self.input).serialize(),_derive(self.input).serialize())

    def test_20_reverse_order(self):
        data=self.fixture()
        for key in ('concepts','capabilities','assessment_evidence'):data[key].reverse()
        for c in data['capabilities']:c['task_forms'].reverse();c['concept_refs'].reverse()
        for e in data['assessment_evidence']:e['task_form_refs'].reverse();e['reading_notes'].reverse()
        data['curriculum']['references'].reverse()
        self.assertEqual(_derive(data).serialize(),self.view.serialize())

    def test_21_ref_independent_of_mutable_content(self):
        data=self.fixture()
        for e in data['assessment_evidence']:
            e['assessment_label']='TEST label';e['question_wording']='TEST edited wording';e['marks']=3
        self.assertEqual({e.ref for e in _derive(data).reviewed_examples},{e.ref for e in self.view.reviewed_examples})

    def test_22_duplicate_coordinates_rejected(self):
        data=self.fixture();data['assessment_evidence'][1]=copy.deepcopy(data['assessment_evidence'][0])
        with self.assertRaisesRegex(ValueError,'assessment identity'):_derive(data)

    def test_23_unknown_coordinates_rejected(self):
        for field in ('year','session','paper'):
            data=self.fixture();data['assessment_evidence'][0][field]=None
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'identity requires'):_derive(data)

    def test_24_no_comparison_for_one(self):
        data=self.fixture();data['assessment_evidence']=data['assessment_evidence'][:1]
        data['trust_summary']['reviewed_example_count']=1
        view=_derive(data);self.assertFalse(view.observed_patterns)
        self.assertFalse(view.evidence_summary.shared_capability)

    def test_25_no_evidence(self):
        data=self.fixture();data['assessment_evidence']=[];data['trust_summary']['reviewed_example_count']=0
        self.assertFalse(_derive(data).observed_patterns)

    def test_26_changed_marks_remove_shared_marks(self):
        data=self.fixture();data['assessment_evidence'][0]['marks']=3
        self.assertNotIn('shared_marks',{p.type for p in _derive(data).observed_patterns})

    def test_27_unknown_marks_not_inferred(self):
        data=self.fixture()
        for e in data['assessment_evidence']:e['marks']=None
        self.assertNotIn('shared_marks',{p.type for p in _derive(data).observed_patterns})

    def test_28_same_wording_no_context_claim(self):
        data=self.fixture();data['assessment_evidence'][1]['question_wording']=data['assessment_evidence'][0]['question_wording']
        self.assertNotIn('distinct_question_wording',{p.type for p in _derive(data).observed_patterns})

    def test_29_whitespace_not_wording_difference(self):
        data=self.fixture();data['assessment_evidence'][1]['question_wording']='  '+data['assessment_evidence'][0]['question_wording'].replace(' ','  ')+' '
        self.assertFalse(_derive(data).evidence_summary.distinct_question_wording)

    def test_30_other_capability_not_shared(self):
        data=self.fixture();cap=copy.deepcopy(data['capabilities'][0]);cap['ref']='TEST-other';cap['task_forms']=[]
        data['capabilities'].append(cap);data['assessment_evidence'][1]['capability_ref']='TEST-other'
        data['assessment_evidence'][1]['task_form_refs']=[]
        view=_derive(data)
        self.assertFalse(view.evidence_summary.shared_capability);self.assertFalse(view.evidence_summary.shared_task_form)

    def test_31_unreviewed_flag_rejected(self):
        data=self.fixture();data['trust_summary']['assessment_evidence_reviewed']=False
        with self.assertRaises(ValueError):_derive(data)

    def test_32_count_mismatch_rejected(self):
        data=self.fixture();data['trust_summary']['reviewed_example_count']=100
        with self.assertRaisesRegex(ValueError,'count mismatch'):_derive(data)

    def test_33_cli_json(self):
        run=subprocess.run([sys.executable,'-X','utf8','-m','academic_os','--db',str(DB),
            'assessment-intelligence',TOPIC,'--json'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(run.stdout),self.view.model_dump(mode='json'))

    def test_34_human_language(self):
        text=intelligence_text(self.view)
        for label in ('Student capability','Task form','Reviewed examples: 2','Observed across reviewed evidence','Evidence limits','Evidence/source-quality note'):
            self.assertIn(label,text)
        self.assertNotIn('CAN-STAT',text)

    def test_35_real_revocation_blocks_next_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.sqlite3'
            source=sqlite3.connect(DB.resolve().as_uri()+'?mode=ro',uri=True)
            dest=sqlite3.connect(path)
            try:source.backup(dest)
            finally:source.close();dest.close()
            reader=AssessmentIntelligenceService(path)
            reader.read_topic(TOPIC,PROTECTED_SNAPSHOTS)
            store=Store(path)
            try:
                service=Service(store);key='proposal:PROPOSE-Q3-2023-b-ii';i=service.inspect(key)
                service.review(key,'revoke','TEST-ONLY-OPERATOR','TEST ONLY P2B revocation',
                    i['version'],i['dependency_digest'],i['expected_decision'],'TEST-P2B-REVOKE')
            finally:store.close()
            before=path.read_bytes()
            with self.assertRaises(UnusableSnapshot):reader.read_topic(TOPIC,PROTECTED_SNAPSHOTS)
            self.assertEqual(before,path.read_bytes())

    def test_36_detached_json_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST-fixture.json';path.write_text(self.upstream.view.serialize(),encoding='utf-8')
            with self.assertRaises(sqlite3.DatabaseError):AssessmentIntelligenceService(path).read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_37_database_unchanged(self):self.assertEqual(state(),self.before)

    def test_38_reverse_snapshots(self):
        actual=AssessmentIntelligenceService(DB).read_topic(TOPIC,tuple(reversed(PROTECTED_SNAPSHOTS)))
        self.assertEqual(actual.view.serialize(),self.view.serialize());self.assertEqual(actual.provenance,self.result.provenance)

    def test_39_upstream_trust_preserved(self):
        self.assertEqual(self.view.trust_summary.upstream,self.upstream.view.trust_summary)
        self.assertFalse(self.view.trust_summary.analytics_enabled)

    def test_40_cli_no_store_constructor(self):
        from academic_os.cli import main
        with patch('academic_os.cli.Store',side_effect=AssertionError('Production write store opened')),patch('builtins.print'):
            self.assertEqual(main(['--db',str(DB),'assessment-intelligence',TOPIC]),0)
