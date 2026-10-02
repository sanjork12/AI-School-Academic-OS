"""P4B adversarial content fixtures are isolated copies, never trust authorities."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from academic_os.authored_service import AuthoredTeachingService
from academic_os.learning_service import LearningSpecificationService
from academic_os.pedagogical_service import PedagogicalSpecificationService
from academic_os.content_validation import validate_authored_content
from academic_os.content_validation_service import AuthoredContentValidationService,content_validation_text,ContentValidationRead
from academic_os.content_validation_models import RendererReadiness
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_reader import UnusableSnapshot
from tests_p0.teacher_product_acceptance import state

DB=Path('var/p0_q2.sqlite3');TOPIC='standard-deviation'


class ContentValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state();cls.a=AuthoredTeachingService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.p=PedagogicalSpecificationService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.l=LearningSpecificationService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.good=validate_authored_content(cls.a.view,cls.p.view,cls.l.view)
    @classmethod
    def tearDownClass(cls):assert cls.before==state()
    def data(self):return self.a.view.model_dump(mode='json')
    def validate(self,data):return validate_authored_content(data,self.p.view,self.l.view)
    def bad(self,data,code=None):
        r=self.validate(data);self.assertFalse(r.renderer_readiness.ready_for_rendering)
        self.assertTrue(r.violations)
        if code:self.assertIn(code,{v.code for v in r.violations})
        return r
    def block(self,data,kind):return next(b for b in data['content_blocks'] if b['kind']==kind)
    def numerical(self,data):return next(s for s in data['solutions'] if s['numeric_answer'] is not None)
    def repair_population(self,data):
        for slot,row in data['coverage_summary'].items():
            row['content_refs']=sorted(b['ref'] for b in data['content_blocks'] if slot in b['instructional_slot_refs'])
            row['populated']=bool(row['content_refs'])
    def claim(self,text):
        d=self.data();self.block(d,'concept_explanation')['text']+=' '+text
        return self.bad(d)

    def test_01_current_all_dimensions(self):
        r=self.good;self.assertEqual(r.schema_version,'authored-content-validation/1')
        for name in ('reference_integrity','content_completeness','mathematical_integrity','learning_alignment','coverage_requirement_validation','boundary_compliance'):self.assertTrue(getattr(r,name).valid,name)
        self.assertTrue(r.renderer_readiness.ready_for_rendering);self.assertFalse(r.violations)

    def test_02_actual_coverage_matrix(self):
        self.assertEqual(len(self.good.coverage_matrix),5)
        for r in self.good.coverage_matrix:
            self.assertEqual(r.status,'covered' if r.kind=='learning_requirement' else 'satisfied');self.assertTrue(r.evidence_refs)
        self.assertEqual({r.requirement_ref for r in self.good.coverage_matrix},{r.ref for r in (*self.l.view.learning_requirements,*self.l.view.coverage_requirements)})

    def test_03_four_real_slots(self):
        self.assertEqual(len(self.good.slot_population),4)
        self.assertTrue(all(s.populated and s.evidence_refs for s in self.good.slot_population))
        self.assertEqual({s.semantic_role for s in self.good.slot_population},{'calculation_method_slot','task_input_slot','worked_example_slot','learning_check_slot'})

    def test_04_math_recomputed(self):
        self.assertEqual(len(self.good.verification_summary),7)
        self.assertTrue(all(v.status=='verified' for v in self.good.verification_summary.values()))

    def test_05_placeholder_method(self):
        d=self.data();self.block(d,'calculation_method')['text']='Provide a valid calculation method.'
        r=self.bad(d,'block_content_incomplete');self.assertEqual(sum(s.populated for s in r.slot_population),3)

    def test_06_placeholder_worked_question(self):
        d=self.data();d['worked_examples'][0]['question']='Provide an aligned worked example.'
        r=self.bad(d,'question_content_incomplete');self.assertFalse(r.coverage_requirement_validation.valid)

    def test_07_placeholder_learning_check(self):
        d=self.data();next(q for q in d['learning_checks'] if q['kind']=='calculation_check')['question']='Add a learning check.'
        r=self.bad(d);self.assertFalse(next(s for s in r.slot_population if s.semantic_role=='learning_check_slot').populated)

    def test_08_placeholder_concept(self):
        d=self.data();self.block(d,'concept_explanation')['text']='Explain standard deviation.'
        self.assertFalse(self.bad(d).learning_alignment.valid)

    def test_09_missing_solution(self):
        d=self.data();d['solutions']=[s for s in d['solutions'] if s['item_ref']!=d['worked_examples'][0]['ref']]
        self.bad(d,'solution_missing_or_ambiguous')

    def test_10_solution_target_unknown_or_wrong_kind(self):
        for target,code in [('TEST-unknown','broken_ref'),(self.a.view.content_blocks[0].ref,'wrong_kind_ref')]:
            d=self.data();d['solutions'][0]['item_ref']=target;self.bad(d,code)

    def test_11_unknown_lr(self):
        d=self.data();d['practice_items'][0]['assesses_learning_requirement_refs']=['TEST-outside-spec']
        r=self.bad(d,'broken_ref');self.assertFalse(r.coverage_requirement_validation.valid)

    def test_12_wrong_kind_task(self):
        d=self.data();d['worked_examples'][0]['task_form_refs']=d['worked_examples'][0]['capability_refs']
        self.bad(d,'wrong_kind_ref')

    def test_13_unknown_block_and_slot(self):
        for field in ('teaching_block_refs','instructional_slot_refs'):
            d=self.data();d['content_blocks'][0][field]=['TEST-unknown'];self.bad(d,'broken_ref')

    def test_14_wrong_role_existing_lr(self):
        d=self.data();self.block(d,'concept_explanation')['covers_learning_requirement_refs']=self.block(d,'calculation_method')['covers_learning_requirement_refs']
        self.bad(d,'block_target_mismatch')

    def test_15_duplicate_identities(self):
        for group in ('content_blocks','instructional_formulas','worked_examples','practice_items','learning_checks','solutions'):
            with self.subTest(group=group):
                d=self.data();d[group].append(copy.deepcopy(d[group][0]));self.bad(d,'duplicate_or_colliding_ref')

    def test_16_duplicate_display_text_allowed(self):
        d=self.data()
        for b in d['content_blocks']:
            if b['item_ref']:b['text']='Original authored item; question and solution are separate.'
        self.assertTrue(self.validate(d).renderer_readiness.ready_for_rendering)

    def test_17_stored_math_success_cannot_bypass(self):
        d=self.data();self.numerical(d)['numeric_answer']='99'
        self.assertTrue(d['verification_summary']['mathematical_checks_passed'])
        self.assertEqual(self.numerical(d)['verification']['status'],'verified')
        self.assertFalse(self.bad(d,'mathematical_verification_failed').mathematical_integrity.valid)

    def test_18_corrupt_each_answer_representation(self):
        for field,value in [('mean','9'),('variance','999'),('exact_answer',{'op':'sqrt','radicand':'999'}),('numeric_answer','NaN'),('display_answer','3.17'),('method_steps',['Wrong method'])]:
            with self.subTest(field=field):
                d=self.data();self.numerical(d)[field]=value;self.bad(d,'mathematical_verification_failed')

    def test_19_all_numerical_items_rechecked(self):
        for group in ('worked_examples','practice_items','learning_checks'):
            for i,q in enumerate(self.data()[group]):
                if q['summary']:
                    d=self.data();d[group][i]['summary']['sum_x2']='1';self.bad(d,'mathematical_verification_failed')

    def test_20_invalid_summary_domain(self):
        for field,value in [('n',0),('n',-1),('n',True),('sum_x','Infinity'),('sum_x2','NaN')]:
            d=self.data();d['worked_examples'][0]['summary'][field]=value;self.bad(d,'mathematical_verification_failed')

    def test_21_formula_ast_recomputed(self):
        d=self.data();d['instructional_formulas'][0]['expression']['args']=[{'op':'variable','name':'n'}]
        self.bad(d,'mathematical_verification_failed')

    def test_22_formula_role(self):
        d=self.data();d['instructional_formulas'][0]['formula_memorisation_required']=True
        self.bad(d,'formula_role_invalid')

    def test_23_formula_missing(self):
        d=self.data();d['instructional_formulas']=[]
        for b in d['content_blocks']:b['formula_refs']=[]
        self.bad(d,'block_content_incomplete')

    def test_24_visual_data_corruption(self):
        d=self.data();self.block(d,'visual_comparison')['visual']['datasets']['A']=['0','0','0'];self.bad(d,'mathematical_verification_failed')

    def test_25_visual_claim_corruption(self):
        for field,value in [('same_mean',False),('sd_order',['B','A']),('brief','Dataset A is more dispersed.')]:
            d=self.data();self.block(d,'visual_comparison')['visual'][field]=value;self.bad(d,'mathematical_verification_failed')

    def test_26_visual_text_corruption(self):
        d=self.data();self.block(d,'visual_comparison')['text']='Same mean, different spread. Dataset A is more dispersed.'
        self.bad(d,'block_content_incomplete')

    def test_27_concept_semantics_missing(self):
        for text in ('Standard deviation measures spread.','Standard deviation measures dispersion around the mean.','Standard deviation is not spread around the mean in the same units as observations.'):
            d=self.data();self.block(d,'concept_explanation')['text']=text;self.bad(d,'block_content_incomplete')

    def test_28_concept_paraphrase_allowed(self):
        d=self.data();self.block(d,'concept_explanation')['text']='Standard deviation describes dispersion about the mean, in the units of the observations.'
        s=next(s for s in d['solutions'] if s['expected_meaning']);s['expected_meaning']='It describes dispersion about the average.'
        self.assertTrue(self.validate(d).renderer_readiness.ready_for_rendering)

    def test_29_concept_answer_metadata_not_enough(self):
        d=self.data();next(s for s in d['solutions'] if s['expected_meaning'])['expected_meaning']='It tells us the largest value.'
        self.bad(d,'question_content_incomplete')

    def test_30_concept_semantic_metadata_required(self):
        d=self.data();next(s for s in d['solutions'] if s['expected_meaning'])['key_semantic_elements']=['around the mean']
        self.bad(d,'question_content_incomplete')

    def test_31_summary_definitions_incomplete(self):
        d=self.data();self.block(d,'summary_statistics_method')['instructional_inputs']['sum_x2']='square of the sum of the observations'
        self.bad(d,'block_content_incomplete')

    def test_32_summary_content_removed_metadata_retained(self):
        d=self.data();kinds={'summary_statistics_method','worked_example','practice_item','calculation_check'}
        for b in d['content_blocks']:
            if b['kind'] in kinds:b['text']='Provide an aligned item.'
        r=self.bad(d)
        self.assertEqual(next(row.status for row in r.coverage_matrix if row.semantic_role=='capability_under_task_form'),'uncovered')
        self.assertTrue(all(row['populated'] for row in d['coverage_summary'].values()))

    def test_33_missing_actual_role(self):
        d=self.data();d['content_blocks']=[b for b in d['content_blocks'] if b['kind']!='calculation_method'];self.repair_population(d)
        self.bad(d,'content_role_missing')

    def test_34_missing_reviewed_alignment(self):
        d=self.data();d['worked_examples'][0]['assessment_structure_origin']=None
        self.assertFalse(self.bad(d,'reviewed_alignment_missing').coverage_requirement_validation.valid)

    def test_35_boundary_claims_in_actual_text(self):
        claims={'formula_memorisation':'Students must memorise this formula.','calculator_method':'Students must use a specific calculator button sequence.',
            'difficulty':'This is a medium difficulty question.','common_mistakes':'Most students confuse standard deviation with variance.',
            'prerequisites':'Variance must be mastered first.','frequency':'This is frequently tested.',
            'typical_marks':'This is usually 2 marks.','exam_prediction':'This is likely to appear next year.',
            'sample_comparison':'Sample standard deviation uses n - 1.','originality_claim':'This is an Edexcel question.'}
        for code,text in claims.items():
            with self.subTest(code=code):self.assertIn(code,{v.code for v in self.claim(text).violations})

    def test_36_negation_does_not_hide_positive_claim(self):
        for text in ('No calculator is required, but students must memorise this formula.','No image is needed; most students confuse these terms.','No source is copied and variance must be mastered first.'):
            self.assertFalse(self.claim(text).boundary_compliance.valid)

    def test_37_allowed_instructional_formula(self):
        d=self.data();self.block(d,'calculation_method')['text']+=' Here is the formula used for this calculation. Students do not need to memorise it.'
        self.assertTrue(self.validate(d).renderer_readiness.ready_for_rendering)

    def test_38_boundary_checks_all_prose_locations(self):
        d=self.data();self.numerical(d)['method_steps'].append('Students must memorise this formula.')
        self.assertFalse(self.bad(d).boundary_compliance.valid)
        d=self.data();self.block(d,'summary_statistics_method')['instructional_inputs']['n']='Number of observations. This is an advanced question.'
        self.assertFalse(self.bad(d).boundary_compliance.valid)

    def test_39_origins(self):
        d=self.data();d['content_blocks'][0]['origin']='unknown';self.bad(d,'contract_schema_invalid')
        d=self.data();d['practice_items'][0]['origin']='trusted_semantic_transformation';self.bad(d,'question_origin_mismatch')

    def test_40_copy_claim(self):
        d=self.data();d['practice_items'][0]['source_question_copy']=True;self.bad(d,'source_question_copy')

    def test_41_boundary_removal(self):
        d=self.data();d['evidence_boundaries'].pop();self.bad(d,'evidence_boundaries_changed')

    def test_42_upstream_hash_mismatch(self):
        d=self.data();d['source_pedagogical_specification']['pedagogical_content_sha256']='fake';self.bad(d,'stale_upstream_binding')

    def test_43_current_p3c_gate_recomputed(self):
        p=self.p.view.model_dump(mode='json');p['teaching_blocks'][0]['constraints'].append({'level':'required','statement':'Students must memorise the formula.'})
        r=validate_authored_content(self.data(),p,self.l.view)
        self.assertFalse(r.renderer_readiness.ready_for_rendering);self.assertIn('authoring_gate_closed',{e.code for e in r.violations})

    def test_44_forged_population_cannot_replace_content(self):
        d=self.data();d['content_blocks']=[]
        r=self.bad(d,'slot_unpopulated');self.assertEqual(sum(s.populated for s in r.slot_population),0)

    def test_45_malformed_inputs_fail_closed(self):
        for data in ({},None,[],{'schema_version':'authored-teaching-content/9'}):
            self.bad(data,'contract_schema_invalid')

    def test_46_determinism_no_input_mutation(self):
        d=self.data();before=copy.deepcopy(d)
        self.assertEqual(self.validate(d).serialize(),self.validate(d).serialize());self.assertEqual(d,before)

    def test_47_live_service_and_reversed_snapshots(self):
        r=AuthoredContentValidationService(DB).read_topic(TOPIC,tuple(reversed(PROTECTED_SNAPSHOTS)))
        self.assertEqual(r.view.serialize(),self.good.serialize());self.assertTrue(r.provenance['current_upstream_validated'])

    def test_48_fresh_reads_and_revocation(self):
        service=AuthoredContentValidationService(DB)
        with patch.object(service._authored,'read_topic',return_value=self.a) as a,patch.object(service._pedagogy,'read_topic',return_value=self.p) as p,patch.object(service._learning,'read_topic',return_value=self.l) as l:
            service.read_topic(TOPIC,PROTECTED_SNAPSHOTS);service.read_topic(TOPIC,PROTECTED_SNAPSHOTS)
            self.assertEqual((a.call_count,p.call_count,l.call_count),(2,2,2))
        with patch.object(service._authored,'read_topic',side_effect=UnusableSnapshot('TEST revoked')):
            with self.assertRaises(UnusableSnapshot):service.read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_49_provenance_conflict(self):
        service=AuthoredContentValidationService(DB);a=copy.deepcopy(self.a);a.provenance['upstream']['upstream']={'changed':True}
        with patch.object(service._authored,'read_topic',return_value=a),patch.object(service._pedagogy,'read_topic',return_value=self.p),patch.object(service._learning,'read_topic',return_value=self.l):
            with self.assertRaisesRegex(ValueError,'changed'):service.read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_50_saved_json_not_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'isolated.json';path.write_text(self.a.view.serialize(),encoding='utf-8')
            with self.assertRaises(sqlite3.DatabaseError):AuthoredContentValidationService(path).read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_51_cli_readonly_exit_codes(self):
        from academic_os.cli import main
        with patch('academic_os.cli.Store',side_effect=AssertionError('Write Store opened')),patch('builtins.print'):
            self.assertEqual(main(['--db',str(DB),'validate-authored-content',TOPIC]),0)
            failed=self.good.model_copy(update={'renderer_readiness':RendererReadiness(ready_for_rendering=False,blocking_codes=('TEST',))})
            with patch.object(AuthoredContentValidationService,'read_topic',return_value=ContentValidationRead(failed,{})):
                self.assertEqual(main(['--db',str(DB),'validate-authored-content',TOPIC]),2)

    def test_52_frozen_files_and_database(self):
        before=json.loads(Path('output/p4b_authored_content_validation/before.json').read_text(encoding='utf-8'))
        self.assertEqual(state(),before['database'])
        for path,h in before['files'].items():self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(),h,path)

    def test_53_trust_and_warnings(self):
        text=content_validation_text(self.good);self.assertIn('Ready for rendering: YES',text)
        for key in ('academic_approval','trusted_snapshot','pedagogical_quality_assessed','student_mastery_assessed','rendered_artifact_created'):self.assertFalse(self.good.trust_summary[key])
        self.assertEqual({w.severity for w in self.good.warnings},{'WARNING'})

    def test_54_malformed_nested_data(self):
        for field,value in [('kind',[]),('ref',{}),('item_ref',[]),('text',None)]:
            d=self.data();d['content_blocks'][0][field]=value;self.bad(d,'contract_schema_invalid')

    def test_55_hidden_numeric_payload(self):
        d=self.data();s=next(s for s in d['solutions'] if s['expected_meaning']);s['numeric_answer']='999'
        self.bad(d,'question_content_incomplete')
        d=self.data();b=self.block(d,'concept_explanation');b['visual']=copy.deepcopy(self.block(d,'visual_comparison')['visual'])
        b['visual']['claims']['A']['mean']='999';self.bad(d,'mathematical_verification_failed')

    def test_56_missing_scope_policy(self):
        d=self.data();d['content_boundaries']=[t for t in d['content_boundaries'] if 'population' not in t]
        self.bad(d,'content_scope_missing')

    def test_57_recommendations_not_upgraded_to_requirements(self):
        d=self.data();optional={'visual_comparison','practice_item','concept_check'}
        removed={q['ref'] for group in ('practice_items','learning_checks') for q in d[group] if q['kind'] in optional}
        d['content_blocks']=[b for b in d['content_blocks'] if b['kind'] not in optional]
        d['practice_items']=[];d['learning_checks']=[q for q in d['learning_checks'] if q['ref'] not in removed]
        d['solutions']=[s for s in d['solutions'] if s['item_ref'] not in removed];self.repair_population(d)
        r=self.validate(d);self.assertTrue(r.renderer_readiness.ready_for_rendering)
        self.assertIn('recommended_visual_missing',{w.code for w in r.warnings})


if __name__=='__main__':unittest.main()
