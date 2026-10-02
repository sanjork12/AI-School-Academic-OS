"""P4A oracle and adversarial checks; trusted state is never changed."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from academic_os.authored_service import AuthoredTeachingService
from academic_os.authored_sd import author_standard_deviation
from academic_os.authored_models import AuthoredTeachingPackage
from academic_os.authored_math import summary_stats,raw_stats,display,verify_formula,render_expression
from academic_os.authored_verification import verify_package_math
from academic_os.pedagogical_service import PedagogicalSpecificationService
from academic_os.pedagogical_validation import PedagogicalValidationService
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_reader import UnusableSnapshot
from tests_p0.teacher_product_acceptance import state

DB=Path('var/p0_q2.sqlite3');TOPIC='standard-deviation'


class AuthoredTeachingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state()
        cls.p=PedagogicalSpecificationService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.v=PedagogicalValidationService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.package=author_standard_deviation(cls.p.view,cls.v.view)
        cls.gold=json.loads(Path('tests_p0/fixtures/authored_standard_deviation_gold.json').read_text(encoding='utf-8'))
    @classmethod
    def tearDownClass(cls):assert cls.before==state()
    def data(self):return self.package.model_dump(mode='json')
    def numerical(self,data):return next(s for s in data['solutions'] if s['numeric_answer'] is not None)
    def failed(self,data):
        result=verify_package_math(data)
        self.assertFalse(result.mathematical_checks_passed)
        self.assertFalse(result.ready_for_downstream_content_validation)
        self.assertFalse(result.ready_as_completed_teaching_content)

    def test_01_oracle_shape(self):
        p=self.package;g=self.gold
        self.assertEqual(p.schema_version,g['schema_version']);self.assertEqual(p.status,g['status'])
        for field,n in g['counts'].items():self.assertEqual(len(getattr(p,field)),n)
        self.assertEqual(len(p.coverage_summary),g['slots'])
        self.assertEqual(len(p.source_pedagogical_specification.learning_requirement_refs),g['learning_requirements'])

    def test_02_oracle_answers(self):
        solutions={s.item_ref:s for s in self.package.solutions}
        for q in (*self.package.worked_examples,*self.package.practice_items,*self.package.learning_checks):
            if q.summary is None:continue
            expected=self.gold['numerical_items'][str(q.summary.n)];s=solutions[q.ref]
            for field in ('sum_x','sum_x2'):self.assertEqual(getattr(q.summary,field),expected[field])
            for field in ('mean','variance'):self.assertEqual(getattr(s,field),expected[field])
            self.assertEqual(s.exact_answer,dict(op='sqrt',radicand=expected['radicand']))
            self.assertEqual(s.display_answer,expected['display'])

    def test_03_visual_oracle(self):
        v=next(b.visual for b in self.package.content_blocks if b.visual)
        self.assertEqual(v.datasets,{'A':('8','9','10','11','12'),'B':('2','6','10','14','18')})
        for label,expected in self.gold['visual'].items():
            for field,value in expected.items():self.assertEqual(v.claims[label][field],value)
        self.assertTrue(v.same_mean);self.assertEqual(v.sd_order,('A','B'))

    def test_04_math_summary(self):
        r=verify_package_math(self.package)
        self.assertEqual(len(r.checks),7);self.assertTrue(r.mathematical_checks_passed)
        self.assertTrue(r.ready_for_downstream_content_validation);self.assertFalse(r.ready_as_completed_teaching_content)
        self.assertEqual(r,self.package.verification_summary)

    def test_05_closed_gate(self):
        v=self.v.view.model_dump();v['authoring_readiness']['ready_for_content_authoring']=False
        with self.assertRaisesRegex(ValueError,'gate'):author_standard_deviation(self.p.view,v)

    def test_06_invalid_structure_gate(self):
        for field in ('structural_coverage','reference_integrity','boundary_validation','slot_validation'):
            with self.subTest(field=field):
                v=self.v.view.model_dump();v[field]['valid']=False
                with self.assertRaisesRegex(ValueError,'gate'):author_standard_deviation(self.p.view,v)

    def test_07_incomplete_upstream_is_allowed(self):
        self.assertFalse(self.v.view.authoring_readiness.ready_as_completed_teaching_content)
        self.assertTrue(self.package.verification_summary.mathematical_checks_passed)
        self.assertEqual(self.v.view.content_readiness.populated,0)
        self.assertTrue(all(s.status=='candidate_slot' for s in self.p.view.instructional_content))

    def test_08_original_and_alignment(self):
        for q in (*self.package.worked_examples,*self.package.practice_items,*self.package.learning_checks):
            if q.summary:
                self.assertEqual(q.origin,'generated_original');self.assertNotIn('Pearson',q.question)
                self.assertEqual(q.assessment_structure_origin,'reviewed_evidence_alignment')
                self.assertEqual(q.task_form_refs,('task-form-summary-statistics',));self.assertEqual(len(q.evidence_refs),2)
                self.assertEqual(q.capability_refs,('capability-standard-deviation-calculate',))

    def test_09_question_solution_separation(self):
        for group in ('worked_examples','practice_items','learning_checks'):
            for q in self.data()[group]:
                self.assertNotIn('numeric_answer',q);self.assertNotIn('expected_meaning',q)
                self.assertNotIn('display_answer',q);self.assertNotIn('method_steps',q)
        self.assertEqual(len({s.item_ref for s in self.package.solutions}),5)

    def test_10_concept_check_semantics(self):
        q=next(q for q in self.package.learning_checks if q.kind=='concept_check')
        s=next(s for s in self.package.solutions if s.item_ref==q.ref)
        self.assertEqual(s.key_semantic_elements,('spread or dispersion','around the mean'))
        self.assertFalse(s.exact_string_matching_required);self.assertIsNone(s.numeric_answer)
        self.assertFalse(q.instructional_slot_refs);self.assertEqual(len(q.assesses_learning_requirement_refs),1)

    def test_11_alignment_no_new_requirements(self):
        existing={r.ref for r in self.p.view.source_learning_specification.learning_requirements}
        self.assertEqual(set(self.package.source_pedagogical_specification.learning_requirement_refs),existing)
        for b in self.package.content_blocks:
            self.assertTrue(set(b.covers_learning_requirement_refs+b.assesses_learning_requirement_refs)<=existing)
            source=next(t for t in self.p.view.teaching_blocks if t.ref==b.teaching_block_refs[0])
            self.assertTrue(set(b.covers_learning_requirement_refs+b.assesses_learning_requirement_refs)<=set(source.covers_learning_requirement_refs))
        self.assertEqual({b.constraint_level for b in self.package.content_blocks},{'required','recommended','flexible'})

    def test_12_boundaries(self):
        self.assertEqual(set(b.ref for b in self.package.evidence_boundaries),set(b.ref for b in self.p.view.evidence_boundaries))
        self.assertEqual(len(self.package.evidence_boundaries),10)
        self.assertIn('not a universal exam requirement',' '.join(self.package.content_boundaries))
        for f in self.package.instructional_formulas:self.assertFalse(f.formula_memorisation_required)

    def test_13_slot_population(self):
        self.assertTrue(all(r.populated and r.status=='content_supplied_pending_validation' for r in self.package.coverage_summary.values()))
        for slot in self.p.view.instructional_content:
            for block in self.package.content_blocks:
                if slot.ref in block.instructional_slot_refs:
                    self.assertTrue(set(block.covers_learning_requirement_refs+block.assesses_learning_requirement_refs)<=set(slot.supports_learning_requirement_refs))

    def test_14_corrupted_answers(self):
        for field,value in [('mean','99'),('variance','99'),('numeric_answer','99'),('display_answer','99'),('exact_answer',{'op':'sqrt','radicand':'99'}),('exact_answer',None),('method_steps',['fake'])]:
            with self.subTest(field=field):
                d=self.data();self.numerical(d)[field]=value;self.failed(d)

    def test_15_nonfinite_stored_answer(self):
        for value in ('NaN','Infinity','-Infinity'):
            d=self.data();self.numerical(d)['numeric_answer']=value;self.failed(d)

    def test_16_stored_labels_not_authority(self):
        d=self.data();self.numerical(d)['numeric_answer']='123'
        self.assertTrue(d['verification_summary']['mathematical_checks_passed'])
        self.assertEqual(self.numerical(d)['verification']['status'],'verified');self.failed(d)

    def test_17_corrupted_summary(self):
        d=self.data();d['worked_examples'][0]['summary']['sum_x2']='551';self.failed(d)

    def test_18_corrupted_question(self):
        d=self.data();d['worked_examples'][0]['question']='A dataset has 99 observations.';self.failed(d)

    def test_19_invalid_summaries(self):
        for args in [(0,0,0),(-1,0,0),(True,0,0),(1.5,0,0),(2,10,1),(1,2,5),(3,'NaN',4),(3,1,'Infinity')]:
            with self.subTest(args=args),self.assertRaises(ValueError):summary_stats(*args)
        self.assertEqual(summary_stats(1,2,4)[1],0)

    def test_20_raw_data_edge_cases(self):
        for values in ([],['NaN'],['Infinity'],[True]):
            with self.subTest(values=values),self.assertRaises(ValueError):raw_stats(values)
        self.assertEqual(raw_stats([-2,-2,-2])[1],0)

    def test_21_rounding_explicit(self):
        self.assertEqual(display('2.345'),'2.35');self.assertEqual(display('2.3449'),'2.34')
        self.assertEqual(display('2'),'2.00');self.assertEqual(display('-2.345'),'-2.35')

    def test_22_formula_recomputation(self):
        for f in self.package.instructional_formulas:
            self.assertEqual(verify_formula(f.expression,f.display_expression).status,'verified')
            e=copy.deepcopy(f.expression);e['args'][0]={'op':'variable','name':'sum_x'}
            self.assertEqual(verify_formula(e,render_expression(e)).status,'failed')

    def test_23_formula_display_tamper(self):
        d=self.data();d['instructional_formulas'][0]['display_expression']='sqrt(n)';self.failed(d)

    def test_24_invalid_formula_ast(self):
        for ast in ({'op':'eval','args':['bad']},{'op':'sqrt','args':[None]},{'op':'variable','name':'n'}):
            with self.subTest(ast=ast):self.assertEqual(verify_formula(ast,'bad').status,'failed')

    def test_25_visual_claims_tamper(self):
        for field in ('mean','variance','sd'):
            d=self.data();next(b['visual'] for b in d['content_blocks'] if b['visual'])['claims']['A'][field]='99';self.failed(d)

    def test_26_visual_data_and_relationship_tamper(self):
        for field,value in [('datasets',{'A':['10'],'B':['10']}),('same_mean',False),('sd_order',['B','A']),('brief','Wrong claim')]:
            d=self.data();next(b['visual'] for b in d['content_blocks'] if b['visual'])[field]=value;self.failed(d)

    def test_27_schema_references(self):
        for field,value in [('teaching_block_refs',['unknown']),('instructional_slot_refs',['unknown']),('covers_learning_requirement_refs',['unknown']),('origin','approved')]:
            d=self.data();d['content_blocks'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):AuthoredTeachingPackage.model_validate(d)

    def test_28_duplicate_and_missing_solution(self):
        d=self.data();d['solutions'].pop()
        with self.assertRaises(ValueError):AuthoredTeachingPackage.model_validate(d)
        d=self.data();d['content_blocks'].append(copy.deepcopy(d['content_blocks'][0]))
        with self.assertRaises(ValueError):AuthoredTeachingPackage.model_validate(d)

    def test_29_cannot_claim_approval(self):
        for status in ('approved','trusted','published','academically_verified'):
            d=self.data();d['status']=status
            with self.assertRaises(ValueError):AuthoredTeachingPackage.model_validate(d)
        d=self.data();d['verification_summary']['ready_as_completed_teaching_content']=True
        with self.assertRaises(ValueError):AuthoredTeachingPackage.model_validate(d)

    def test_30_provider_pure_no_fixture_reads(self):
        before=self.p.view.serialize()
        with patch('builtins.open',side_effect=AssertionError('File read')),patch.object(Path,'read_text',side_effect=AssertionError('Fixture read')):
            other=author_standard_deviation(self.p.view,self.v.view)
        self.assertEqual(other.serialize(),self.package.serialize());self.assertEqual(before,self.p.view.serialize())

    def test_31_provider_guards_changed_semantics(self):
        d=self.p.view.model_dump();d['source_learning_specification']['conceptual_basis'][0]['description']='Different meaning'
        with self.assertRaises(ValueError):author_standard_deviation(d,self.v.view)
        with self.assertRaises(ValueError):AuthoredTeachingService(DB).read_topic('other',PROTECTED_SNAPSHOTS)

    def test_32_fresh_service_no_cache(self):
        s=AuthoredTeachingService(DB)
        with patch.object(s._validation,'read_topic',return_value=self.v) as v,patch.object(s._pedagogy,'read_topic',return_value=self.p) as p:
            s.read_topic(TOPIC,PROTECTED_SNAPSHOTS);s.read_topic(TOPIC,PROTECTED_SNAPSHOTS)
            self.assertEqual((v.call_count,p.call_count),(2,2))
        with patch.object(s._validation,'read_topic',side_effect=UnusableSnapshot('TEST withdrawn')):
            with self.assertRaises(UnusableSnapshot):s.read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_33_provenance_race_refused(self):
        s=AuthoredTeachingService(DB);v=copy.deepcopy(self.v);v.provenance['upstream']={'changed':True}
        with patch.object(s._validation,'read_topic',return_value=v),patch.object(s._pedagogy,'read_topic',return_value=self.p):
            with self.assertRaisesRegex(ValueError,'changed'):s.read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_34_saved_json_not_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'candidate.json';path.write_text(self.package.serialize(),encoding='utf-8')
            with self.assertRaises(sqlite3.DatabaseError):AuthoredTeachingService(path).read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_35_real_service_deterministic(self):
        result=AuthoredTeachingService(DB).read_topic(TOPIC,tuple(reversed(PROTECTED_SNAPSHOTS)))
        self.assertEqual(result.view.serialize(),self.package.serialize())
        self.assertTrue(result.provenance['upstream']['current_upstream_validated'])

    def test_36_cli_read_only_and_output_guard(self):
        from academic_os.cli import main
        with tempfile.TemporaryDirectory() as tmp,patch('academic_os.cli.Store',side_effect=AssertionError('Write store opened')),patch('builtins.print'):
            path=Path(tmp)/'output.json';args=['--db',str(DB),'author-teaching-content',TOPIC,'--output',str(path)]
            self.assertEqual(main(args),0);self.assertEqual(path.read_text(encoding='utf-8'),self.package.serialize())
            path.write_text('KEEP',encoding='utf-8');self.assertEqual(main(args),1);self.assertEqual(path.read_text(),'KEEP')

    def test_37_frozen_state(self):
        before=json.loads(Path('output/p4a_authored_teaching_content/before.json').read_text(encoding='utf-8'))
        self.assertEqual(state(),before['database'])
        for f,h in before['files'].items():self.assertEqual(hashlib.sha256(Path(f).read_bytes()).hexdigest(),h,f)

    def test_38_upstream_content_hashes(self):
        source=self.package.source_pedagogical_specification
        self.assertEqual(source.pedagogical_content_sha256,hashlib.sha256(self.p.view.serialize().encode()).hexdigest())
        self.assertEqual(source.validation_content_sha256,hashlib.sha256(self.v.view.serialize().encode()).hexdigest())


if __name__=='__main__':unittest.main()
