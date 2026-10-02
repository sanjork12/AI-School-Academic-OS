"""P3C negative cases mutate isolated in-memory copies only."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from academic_os.pedagogical_validation import validate_pedagogical_contract,PedagogicalValidationService,validation_text
from academic_os.pedagogical_service import PedagogicalSpecificationService
from academic_os.learning_service import LearningSpecificationService
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_reader import UnusableSnapshot
from tests_p0.teacher_product_acceptance import state

DB=Path('var/p0_q2.sqlite3');TOPIC='standard-deviation'


class PedagogicalValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state();cls.learning=LearningSpecificationService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.pedagogy=PedagogicalSpecificationService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.result=PedagogicalValidationService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS);cls.view=cls.result.view
    @classmethod
    def tearDownClass(cls):assert cls.before==state()
    def fixture(self):return self.pedagogy.view.model_dump(mode='json')
    def validate(self,data):return validate_pedagogical_contract(data,self.learning.view)
    def codes(self,view):return {v.code for v in view.violations}
    def claim(self,text,level='required'):
        data=self.fixture();data['teaching_blocks'][0]['constraints'].append(dict(level=level,statement=text));return self.validate(data)

    def test_01_current_result(self):
        v=self.view;self.assertEqual(v.schema_version,'pedagogical-validation/1')
        self.assertTrue(v.structural_coverage.valid);self.assertEqual(v.structural_coverage.learning_planned,3);self.assertEqual(v.structural_coverage.coverage_planned,2)
        self.assertTrue(v.reference_integrity.valid);self.assertTrue(v.boundary_validation.valid);self.assertTrue(v.slot_validation.valid)
        self.assertTrue(v.authoring_readiness.ready_for_content_authoring);self.assertFalse(v.content_readiness.ready)
        self.assertFalse(v.authoring_readiness.ready_as_completed_teaching_content);self.assertFalse(v.violations)

    def test_02_four_unpopulated_slots(self):
        self.assertEqual(self.view.content_readiness.required_slots_total,4);self.assertEqual(self.view.content_readiness.populated,0)
        self.assertEqual(len(self.view.content_readiness.unpopulated),4)

    def test_03_matrix_uses_stable_refs(self):
        self.assertEqual(len(self.view.coverage_matrix),5)
        self.assertTrue(all(r.coverage_status=='covered' for r in self.view.coverage_matrix))
        self.assertEqual(sorted(len(r.covered_by_block_refs) for r in self.view.coverage_matrix),[1,1,1,3,3])

    def test_04_missing_task_block(self):
        data=self.fixture();data['teaching_blocks']=[b for b in data['teaching_blocks'] if b['role']!='supported_task_form']
        v=self.validate(data);row=next(r for r in v.coverage_matrix if r.required_role=='supported_task_form')
        self.assertEqual(row.coverage_status,'uncovered');self.assertEqual(len(row.covered_by_block_refs),2)
        self.assertFalse(v.structural_coverage.valid);self.assertFalse(v.authoring_readiness.ready_for_content_authoring)

    def test_05_missing_coverage_requirement(self):
        data=self.fixture()
        for b in data['teaching_blocks']:
            if b['role']=='worked_assessment_connection':b['covers_coverage_requirement_refs']=[]
        v=self.validate(data);self.assertEqual(v.structural_coverage.coverage_planned,1);self.assertFalse(v.structural_coverage.valid)

    def test_06_broken_lr(self):
        data=self.fixture();data['teaching_blocks'][0]['covers_learning_requirement_refs']=['TEST-unknown']
        v=self.validate(data);self.assertIn('broken_ref',self.codes(v));self.assertFalse(v.reference_integrity.valid)

    def test_07_wrong_kind(self):
        data=self.fixture();data['teaching_blocks'][0]['covers_learning_requirement_refs']=['task-form-summary-statistics']
        self.assertIn('wrong_kind_ref',self.codes(self.validate(data)))
        data=self.fixture();data['source_learning_specification']['assessment_evidence'][0]['task_form_refs']=['capability-standard-deviation-calculate']
        v=self.validate(data);self.assertIn('wrong_kind_ref',self.codes(v));self.assertFalse(v.reference_integrity.valid)
        data=self.fixture();data['source_learning_specification']['assessment_evidence'][0]['capability_ref']='TEST-unknown'
        self.assertIn('broken_ref',self.codes(self.validate(data)))

    def test_08_formula_overclaim(self):self.assertIn('formula_memorisation',self.codes(self.claim('Students must memorise the standard deviation formula.')))
    def test_09_difficulty_overclaim(self):self.assertIn('difficulty',self.codes(self.claim('This is a medium-difficulty topic.')))
    def test_10_prerequisite_overclaim(self):self.assertIn('prerequisites',self.codes(self.claim('Variance must be mastered before this lesson.')))
    def test_11_common_mistake_overclaim(self):self.assertIn('common_mistakes',self.codes(self.claim('Students commonly confuse standard deviation with variance.')))
    def test_12_frequency_overclaim(self):self.assertIn('frequency',self.codes(self.claim('Standard deviation is frequently tested.')))
    def test_13_typical_marks_overclaim(self):self.assertIn('typical_marks',self.codes(self.claim('This is usually 2 marks.')))
    def test_14_prediction_overclaim(self):self.assertIn('exam_prediction',self.codes(self.claim('This is likely to appear next year.')))
    def test_15_calculator_overclaim(self):self.assertIn('calculator_method',self.codes(self.claim('Students must use a specific calculator button sequence.')))
    def test_16_sequence_overclaim(self):self.assertIn('teaching_sequence',self.codes(self.claim('This sequence is academically required.')))
    def test_17_unsupported_task(self):self.assertIn('unsupported_task_form',self.codes(self.claim('Students must calculate from raw data.')))

    def test_18_allowed_instructional_support(self):
        for text,level in [('Provide a valid calculation method.','required'),('Provide a formula as instructional support, without requiring memorisation.','required'),('A teacher may demonstrate calculator use.','flexible'),('Consider guided to independent application.','recommended'),('Both reviewed examples carry 2 marks.','recommended')]:
            with self.subTest(text=text):self.assertTrue(self.claim(text,level).authoring_readiness.ready_for_content_authoring)

    def test_19_negation_does_not_hide_other_clause(self):
        self.assertIn('formula_memorisation',self.codes(self.claim('No calculator is required, but students must memorise the formula.')))

    def test_20_missing_boundary(self):
        data=self.fixture();data['evidence_boundaries'].pop()
        self.assertIn('evidence_boundaries_changed',self.codes(self.validate(data)))

    def test_21_mutated_learning(self):
        data=self.fixture();data['source_learning_specification']['learning_requirements'][0]['statement']='TEST changed learning'
        self.assertIn('upstream_learning_changed',self.codes(self.validate(data)))

    def test_22_slot_missing_not_just_empty(self):
        data=self.fixture();slot=data['instructional_content'].pop();
        for b in data['teaching_blocks']:b['instructional_content_refs']=[r for r in b['instructional_content_refs'] if r!=slot['ref']]
        v=self.validate(data);self.assertIn('required_slot_missing',self.codes(v));self.assertFalse(v.slot_validation.valid)

    def test_23_placeholder_not_content(self):
        data=self.fixture()
        for c in data['instructional_content']:c['purpose']='Provide an aligned authored example. This slot is complete.'
        v=self.validate(data);self.assertEqual(v.content_readiness.populated,0);self.assertFalse(v.content_readiness.ready)

    def test_24_forged_populated_status(self):
        data=self.fixture();data['instructional_content'][0]['status']='populated'
        v=self.validate(data);self.assertIn('contract_schema_invalid',self.codes(v));self.assertFalse(v.authoring_readiness.ready_as_completed_teaching_content)

    def test_25_duplicate_block(self):
        data=self.fixture();data['teaching_blocks'].append(copy.deepcopy(data['teaching_blocks'][0]))
        self.assertIn('duplicate_or_colliding_ref',self.codes(self.validate(data)))

    def test_26_duplicate_content(self):
        data=self.fixture();data['instructional_content'].append(copy.deepcopy(data['instructional_content'][0]))
        self.assertIn('duplicate_or_colliding_ref',self.codes(self.validate(data)))

    def test_27_duplicate_titles_allowed(self):
        data=self.fixture()
        for b in data['teaching_blocks']:b['title']='TEST same title'
        self.assertTrue(self.validate(data).authoring_readiness.ready_for_content_authoring)

    def test_28_wrong_product_alignment(self):
        data=self.fixture();data['instructional_content'][0]['source_product_refs']=['TEST-other-task']
        v=self.validate(data);self.assertIn('instructional_alignment_mismatch',self.codes(v));self.assertIn('unsupported_task_form',self.codes(v))

    def test_29_learning_check_targets(self):
        data=self.fixture()
        for c in data['instructional_content']:
            if c['type']=='learning_check_slot':c['assesses_learning_requirement_refs']=[]
        self.assertIn('learning_check_targets_missing',self.codes(self.validate(data)))

    def test_30_completion_overclaim(self):
        data=self.fixture();data['coverage_map']['status']='validated_coverage'
        self.assertIn('coverage_completion_overclaim',self.codes(self.validate(data)))

    def test_31_deterministic_order(self):
        data=self.fixture()
        for field in ('teaching_blocks','instructional_content','evidence_boundaries','generator_constraints'):data[field].reverse()
        self.assertEqual(self.validate(data).serialize(),self.view.serialize())

    def test_32_deterministic_violations(self):
        data=self.fixture();data['teaching_blocks'][0]['constraints']+=[dict(level='required',statement='Students must memorise the formula.'),dict(level='required',statement='This is a medium-difficulty topic.')]
        first=self.validate(data).serialize();data['teaching_blocks'].reverse()
        self.assertEqual(first,self.validate(data).serialize())

    def test_33_no_mutation(self):
        data=self.fixture();before=copy.deepcopy(data);self.validate(data);self.assertEqual(data,before)

    def test_34_frozen_files_and_db(self):
        before=json.loads(Path('output/p3c_pedagogical_validation/before.json').read_text(encoding='utf-8'))
        for f,h in before['files'].items():self.assertEqual(hashlib.sha256(Path(f).read_bytes()).hexdigest(),h,f)
        self.assertEqual(state(),before['database'])

    def test_35_fresh_service_and_withdrawal(self):
        service=PedagogicalValidationService(DB)
        with patch.object(service._pedagogy,'read_topic',side_effect=UnusableSnapshot('TEST withdrawn')):
            with self.assertRaises(UnusableSnapshot):service.read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        with patch.object(service._pedagogy,'read_topic',return_value=self.pedagogy) as p,patch.object(service._learning,'read_topic',return_value=self.learning) as l:
            service.read_topic(TOPIC,PROTECTED_SNAPSHOTS);service.read_topic(TOPIC,PROTECTED_SNAPSHOTS);self.assertEqual((p.call_count,l.call_count),(2,2))

    def test_36_saved_json_not_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'TEST.json';file.write_text(self.pedagogy.view.serialize(),encoding='utf-8')
            with self.assertRaises(sqlite3.DatabaseError):PedagogicalValidationService(file).read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_37_cli_no_write_store(self):
        from academic_os.cli import main
        with patch('academic_os.cli.Store',side_effect=AssertionError('Write store opened')),patch('builtins.print'):
            self.assertEqual(main(['--db',str(DB),'validate-pedagogy',TOPIC]),0)

    def test_38_human_and_payload(self):
        text=validation_text(self.view);self.assertIn('Ready for content authoring: YES',text);self.assertIn('Ready as completed teaching content: NO',text)
        for token in ('CAN-STAT','CON-STAT','TC-SUMMARY',*PROTECTED_SNAPSHOTS,'quality_score','confidence_score'):self.assertNotIn(token,self.view.serialize())

    def test_39_schema_version_rejected(self):
        data=self.fixture();data['schema_version']='pedagogical-specification/9'
        self.assertIn('unsupported_schema',self.codes(self.validate(data)))

    def test_40_formula_flag_rejected(self):
        data=self.fixture();data['instructional_content'][0]['formula_memorisation_required']=True
        self.assertIn('formula_memorisation',self.codes(self.validate(data)))
