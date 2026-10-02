"""P3B candidate design; all mutated data below is TEST ONLY, never real approvals."""
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
from academic_os.pedagogical_core import build_pedagogical_specification
from academic_os.pedagogical_service import PedagogicalSpecificationService,pedagogical_specification_text
from academic_os.pedagogical_models import PedagogicalSpecification
from academic_os.learning_service import LearningSpecificationService
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_reader import UnusableSnapshot
from academic_os.storage import Store
from academic_os.service import Service
from tests_p0.teacher_product_acceptance import state

DB=Path('var/p0_q2.sqlite3');TOPIC='standard-deviation'
GOLD=Path('tests_p0/fixtures/pedagogical_standard_deviation_gold.json')


class PedagogicalSpecificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state();cls.learning=LearningSpecificationService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.result=PedagogicalSpecificationService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS);cls.view=cls.result.view
        cls.gold=json.loads(GOLD.read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):assert cls.before==state(),'Pedagogical tests changed real DB'

    def fixture(self):return self.learning.view.model_dump(mode='json')
    def block(self,role):return next(b for b in self.view.teaching_blocks if b.role==role)

    def test_01_schema(self):
        self.assertEqual(self.view.schema_version,'pedagogical-specification/1')
        self.assertEqual(self.view.source_learning_specification.schema_version,'learning-specification/1')

    def test_02_unsupported_schema(self):
        data=self.fixture();data['schema_version']='learning-specification/99'
        with self.assertRaisesRegex(ValueError,'Unsupported learning schema'):build_pedagogical_specification(data)

    def test_03_upstream_not_mutated(self):
        data=self.fixture();before=copy.deepcopy(data);build_pedagogical_specification(data);self.assertEqual(before,data)

    def test_04_frozen_upstream_files(self):
        before=json.loads(Path('output/p3b_pedagogical_specification/before.json').read_text(encoding='utf-8'))
        for file,digest in before['files'].items():self.assertEqual(hashlib.sha256(Path(file).read_bytes()).hexdigest(),digest,file)

    def test_05_identity(self):
        expected=self.learning.view.identity.model_dump();expected['view_type']='pedagogical_specification'
        self.assertEqual(self.view.identity.model_dump(),expected);self.assertEqual(self.view.status,'candidate')

    def test_06_five_gold_roles(self):
        self.assertEqual(len(self.view.teaching_blocks),5)
        self.assertEqual({b.role for b in self.view.teaching_blocks},{b['role'] for b in self.gold['blocks']})

    def test_07_gold_coverage(self):
        learning={r.ref:r.type for r in self.learning.view.learning_requirements};coverage={r.ref:r.type for r in self.learning.view.coverage_requirements}
        for expected in self.gold['blocks']:
            b=self.block(expected['role'])
            self.assertEqual({learning[r] for r in b.covers_learning_requirement_refs},set(expected['learning_types']))
            self.assertEqual({coverage[r] for r in b.covers_coverage_requirement_refs},set(expected['coverage_types']))

    def test_08_gold_constraint_levels(self):
        for expected in self.gold['blocks']:
            block=self.block(expected['role']);self.assertEqual({c.level for c in block.constraints},set(expected['levels']))
            for level in ('required','recommended','flexible'):
                if level+'_contains' in expected:self.assertIn(expected[level+'_contains'],' '.join(c.statement for c in block.constraints if c.level==level))

    def test_09_concept_meaning_required(self):
        requirement=next(r for r in self.learning.view.learning_requirements if r.type=='conceptual_understanding')
        self.assertIn(requirement.statement,[c.statement for c in self.block('conceptual_meaning').constraints if c.level=='required'])

    def test_10_visual_recommended_only(self):
        block=self.block('conceptual_meaning')
        self.assertTrue(any('visual comparison' in c.statement and c.level=='recommended' for c in block.constraints))
        self.assertFalse(any('visual comparison' in c.statement and c.level=='required' for c in block.constraints))

    def test_11_no_numeric_scores(self):
        text=self.view.serialize()
        for name in ('confidence_score','importance_score','freedom_score','difficulty_score'):self.assertNotIn(name,text)

    def test_12_method_is_unfilled_slot(self):
        slot=next(c for c in self.view.instructional_content if c.type=='calculation_method_slot')
        self.assertEqual(slot.status,'candidate_slot');self.assertFalse(slot.formula_memorisation_required)
        self.assertIn('Exact method content is not supplied',slot.purpose)

    def test_13_no_calculator_or_formula_content(self):
        text=' '.join(c.purpose for c in self.view.instructional_content)
        for token in ('sqrt','Σ','σ','SHIFT','MODE','s²'):self.assertNotIn(token,text)
        self.assertTrue(all(not c.formula_memorisation_required for c in self.view.instructional_content))

    def test_14_input_slot_preserves_uncertainty(self):
        slot=next(c for c in self.view.instructional_content if c.type=='task_input_slot')
        self.assertIn('Exact notation is unavailable',slot.purpose);self.assertTrue(slot.source_quality_notes)
        self.assertIn('do not repair glyphs',slot.purpose)

    def test_15_no_new_learning_requirements(self):
        for attr in ('learning_requirements','coverage_requirements','evidence_boundaries'):
            self.assertEqual({r.ref:r for r in getattr(self.learning.view,attr)},{r.ref:r for r in getattr(self.view.source_learning_specification,attr)})
        self.assertEqual(len(self.view.source_learning_specification.learning_requirements),3)

    def test_16_worked_example_alignment(self):
        slot=next(c for c in self.view.instructional_content if c.type=='worked_example_slot')
        self.assertEqual(len(slot.supports_learning_requirement_refs),2)
        self.assertEqual(len(slot.evidence_refs),2)
        self.assertIn('task-form-summary-statistics',slot.source_product_refs)
        self.assertIn('capability-standard-deviation-calculate',slot.source_product_refs)

    def test_17_no_question_reproduction(self):
        text=self.view.serialize()
        self.assertNotIn('question_wording',text)
        for e in self.learning.view.assessment_evidence:self.assertNotIn(e.question_wording,text)
        self.assertIn('do not require copying',' '.join(c.statement for c in self.block('worked_assessment_connection').constraints))

    def test_18_practice_assessment_refs(self):
        slot=next(c for c in self.view.instructional_content if c.type=='learning_check_slot')
        self.assertEqual(slot.assesses_learning_requirement_refs,slot.supports_learning_requirement_refs)
        self.assertEqual(len(slot.assesses_learning_requirement_refs),2)

    def test_19_progression_not_required(self):
        block=self.block('practice_learning_check')
        self.assertTrue(any('independent application' in c.statement and c.level=='recommended' for c in block.constraints))
        self.assertFalse(any('independent application' in c.statement and c.level=='required' for c in block.constraints))
        self.assertTrue(any('no fixed practice sequence' in c.statement for c in block.constraints))

    def test_20_flexible_practice_choices(self):
        text=' '.join(c.statement for c in self.block('practice_learning_check').constraints if c.level=='flexible')
        for phrase in ('question count','context','pair work','exit-ticket','presentation'):self.assertIn(phrase,text)

    def test_21_planned_not_validated(self):
        self.assertEqual(self.view.coverage_map.status,'planned_coverage')
        self.assertIn('not a',self.view.trust_boundary)
        self.assertIn('unresolved content slots',' '.join(c.statement for c in self.view.generator_constraints))

    def test_22_coverage_map_exact(self):
        for ref,blocks in self.view.coverage_map.learning_requirements.items():
            self.assertEqual(set(blocks),{b.ref for b in self.view.teaching_blocks if ref in b.covers_learning_requirement_refs})
        for ref,blocks in self.view.coverage_map.coverage_requirements.items():
            self.assertEqual(set(blocks),{b.ref for b in self.view.teaching_blocks if ref in b.covers_coverage_requirement_refs})

    def test_23_ten_boundaries(self):
        self.assertEqual(len(self.view.evidence_boundaries),10)
        self.assertEqual({b.ref:b for b in self.view.evidence_boundaries},{b.ref:b for b in self.learning.view.evidence_boundaries})

    def test_24_normal_no_canonical_ids(self):
        text=self.view.serialize()
        for value in ('CAN-STAT','CON-STAT','TC-SUMMARY',*PROTECTED_SNAPSHOTS):self.assertNotIn(value,text)

    def test_25_full_provenance_chain(self):
        provenance=self.result.provenance
        for b in self.view.teaching_blocks:
            self.assertIn(b.ref,provenance['teaching_blocks'])
            for lr in b.covers_learning_requirement_refs:self.assertIn(lr,provenance['upstream']['learning_requirements'])
        self.assertIn('capability-standard-deviation-calculate',provenance['upstream']['upstream']['upstream']['product_refs'])

    def test_26_oracle_not_read_by_production(self):
        with patch('builtins.open',side_effect=AssertionError('File read')),patch.object(Path,'read_text',side_effect=AssertionError('Oracle read')):
            self.assertEqual(build_pedagogical_specification(self.learning.view).serialize(),self.view.serialize())
        for path in Path('academic_os').glob('pedagogical_*.py'):
            text=path.read_text(encoding='utf-8')
            for token in ('standard-deviation','LR-SD','Q2(b)','Q3(b)(ii)','pedagogical_standard_deviation_gold'):self.assertNotIn(token,text)

    def test_27_no_topic_branching(self):
        data=self.fixture();data['identity']['view_key']='TEST-other';data['identity']['title']='TEST other topic'
        for r in data['learning_requirements']:r['statement']='TEST unrelated requirement '+r['type']
        view=build_pedagogical_specification(data)
        self.assertEqual(len(view.teaching_blocks),5)
        self.assertTrue(any(c.statement.startswith('TEST unrelated') for b in view.teaching_blocks for c in b.constraints))

    def test_28_names_do_not_determine_coverage(self):
        data=self.fixture()
        for r in data['learning_requirements']:r['statement']='TEST identical display string'
        view=build_pedagogical_specification(data)
        self.assertEqual(view.coverage_map,self.view.coverage_map)

    def test_29_repeated_output(self):self.assertEqual(build_pedagogical_specification(self.learning.view).serialize(),self.view.serialize())

    def test_30_reversed_collections(self):
        data=self.fixture()
        for field in ('learning_requirements','coverage_requirements','evidence_boundaries','assessment_evidence','conceptual_basis'):data[field].reverse()
        self.assertEqual(build_pedagogical_specification(data).serialize(),self.view.serialize())

    def test_31_refs_stable_on_wording_change(self):
        data=self.fixture();data['identity']['title']='TEST label'
        for r in data['learning_requirements']:r['statement']='TEST changed display'
        view=build_pedagogical_specification(data)
        self.assertEqual([b.ref for b in view.teaching_blocks],[b.ref for b in self.view.teaching_blocks])

    def test_32_unique_refs(self):
        refs=[b.ref for b in self.view.teaching_blocks]+[c.ref for c in self.view.instructional_content]
        self.assertEqual(len(refs),len(set(refs)))

    def test_33_wrong_coverage_map_rejected(self):
        data=self.view.model_dump();ref=next(iter(data['coverage_map']['learning_requirements']));data['coverage_map']['learning_requirements'][ref]=()
        with self.assertRaisesRegex(ValueError,'Planned coverage'):PedagogicalSpecification.model_validate(data)

    def test_34_unknown_content_ref_rejected(self):
        data=self.view.model_dump();data['teaching_blocks'][0]['instructional_content_refs']=('TEST unknown',)
        with self.assertRaisesRegex(ValueError,'Unknown teaching block'):PedagogicalSpecification.model_validate(data)

    def test_35_status_cannot_be_approved(self):
        data=self.view.model_dump();data['status']='approved'
        with self.assertRaises(ValueError):PedagogicalSpecification.model_validate(data)

    def test_36_real_db_unchanged(self):self.assertEqual(state(),self.before)

    def test_37_saved_json_not_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.json';path.write_text(self.learning.view.serialize(),encoding='utf-8')
            with self.assertRaises(sqlite3.DatabaseError):PedagogicalSpecificationService(path).read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_38_fresh_read_every_time(self):
        service=PedagogicalSpecificationService(DB)
        with patch.object(service._learning,'read_topic',return_value=self.learning) as read:
            service.read_topic(TOPIC,PROTECTED_SNAPSHOTS);service.read_topic(TOPIC,PROTECTED_SNAPSHOTS);self.assertEqual(read.call_count,2)
        with patch.object(service._learning,'read_topic',side_effect=UnusableSnapshot('TEST withdrawn')):
            with self.assertRaises(UnusableSnapshot):service.read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_39_cli_json(self):
        run=subprocess.run([sys.executable,'-X','utf8','-m','academic_os','--db',str(DB),'pedagogical-specification',TOPIC,'--json'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout),self.view.model_dump(mode='json'))

    def test_40_human_output(self):
        text=pedagogical_specification_text(self.view)
        for label in ('Status: Candidate','Required:','Recommended:','Flexible:','Coverage: planned only','Evidence boundaries'):self.assertIn(label,text)
        self.assertNotIn('CAN-STAT',text)

    def test_41_real_revocation_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.sqlite3';source=sqlite3.connect(DB.resolve().as_uri()+'?mode=ro',uri=True);dest=sqlite3.connect(path)
            try:source.backup(dest)
            finally:source.close();dest.close()
            reader=PedagogicalSpecificationService(path);reader.read_topic(TOPIC,PROTECTED_SNAPSHOTS);store=Store(path)
            try:
                service=Service(store);key='proposal:PROPOSE-Q3-2023-b-ii';i=service.inspect(key)
                service.review(key,'revoke','TEST-ONLY-OPERATOR','TEST ONLY pedagogical revocation',i['version'],i['dependency_digest'],i['expected_decision'],'TEST-P3B-REVOKE')
            finally:store.close()
            before=path.read_bytes()
            with self.assertRaises(UnusableSnapshot):reader.read_topic(TOPIC,PROTECTED_SNAPSHOTS)
            self.assertEqual(before,path.read_bytes())

    def test_42_reversed_snapshots(self):
        other=PedagogicalSpecificationService(DB).read_topic(TOPIC,tuple(reversed(PROTECTED_SNAPSHOTS)))
        self.assertEqual(other.view.serialize(),self.view.serialize());self.assertEqual(other.provenance,self.result.provenance)

    def test_43_cli_no_write_store(self):
        from academic_os.cli import main
        with patch('academic_os.cli.Store',side_effect=AssertionError('Write store opened')),patch('builtins.print'):
            self.assertEqual(main(['--db',str(DB),'pedagogical-specification',TOPIC]),0)

    def test_44_no_raw_bypass(self):
        for path in Path('academic_os').glob('pedagogical_*.py'):
            text=path.read_text(encoding='utf-8')
            for token in ('import sqlite3','read_usable_snapshots','from .storage','from .service import','_compose(','getenv','load_dotenv'):self.assertNotIn(token,text)

    def test_45_no_unresolved_leak_or_new_claim(self):
        text=self.view.serialize()
        for token in ('Q3(c)(ii)','underestimate','CONTEXT-INFER','variance must be taught first','medium-difficulty','students usually confuse'):
            self.assertNotIn(token,text)
