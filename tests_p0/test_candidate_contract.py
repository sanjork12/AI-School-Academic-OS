"""P6A.1c offline contract Gold and immutable historical replay."""
from academic_os.ai_authoring.provenance import LEGACY_POLICY
import copy
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from academic_os.ai_authoring.brief import compile_brief, serial
from academic_os.ai_authoring.service import read_inputs, run_once
from academic_os.ai_authoring.validation import validate_candidate
from academic_os.ai_qualification.reference_baseline import sha
from academic_os.ai_qualification.runner import execute
from tests_p0.test_ai_authoring import FakeAuthor
from tests_p0.test_ai_qualification import SequenceAuthor

GOLD = Path('tests_p0/fixtures/p6a1c_gold.json')
RUN = Path('output/p6a1_live_qualification/run-3ce33e8d738f42df96182e5ca5409dd9')


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = read_inputs('var/p0_q2.sqlite3')
        cls.gold = json.loads(GOLD.read_text())['cases']
        cls.before = {p:sha(p) for p in RUN.rglob('*') if p.is_file()}
        cls.db = sha('var/p0_q2.sqlite3')

    @classmethod
    def tearDownClass(cls):
        assert cls.before == {p:sha(p) for p in RUN.rglob('*') if p.is_file()}
        assert cls.db == sha('var/p0_q2.sqlite3')

    def content(self): return copy.deepcopy(self.gold[1]['content'])

    def report(self, content):
        author = FakeAuthor(content)
        audit = run_once(self.inputs, author, policy=LEGACY_POLICY)
        self.assertEqual(author.calls, 1)
        return audit['validation']

    def test_gold(self):
        for case in self.gold:
            with self.subTest(case=case['id']):
                result = self.report(case['content'])
                self.assertEqual(result['accepted'], case['accepted'], result)
                if 'reason' in case: self.assertIn(case['reason'], result['violations'])

    def test_all_ten_historical_candidates_stay_rejected(self):
        candidates = list(RUN.glob('attempt-*/ai-candidate-*.json'))
        self.assertEqual(len(candidates), 10)
        for path in candidates:
            original = json.loads(path.read_text(encoding='utf-8'))
            self.assertFalse(original['validation']['accepted'])
            first = original['candidate']['content']['proposed_solution']['first_term']
            self.assertIsNone(re.fullmatch(r'-?\d+(?:\.\d+|/\d+)?', first, re.ASCII))
            result = validate_candidate(original['candidate'], self.inputs, policy=LEGACY_POLICY)
            self.assertEqual(result.violations, ('candidate_contract_version_unsupported',))
            self.assertEqual(result.verification_summary['stage_status']['math_valid'], 'NOT_EVALUATED')

    def test_encoding_does_not_cascade(self):
        c=self.content();c['proposed_solution']['first_term']['value']='30/4 = 15/2'
        r=self.report(c);s=r['verification_summary']
        self.assertEqual(r['violations'], ['numeric_encoding_invalid'])
        self.assertEqual(s['primary_failure'], dict(code='numeric_encoding_invalid',field='first_term.value'))
        for key in ('math_valid','solution_valid','composition_valid'):
            self.assertEqual(s['stage_status'][key], 'NOT_EVALUATED')

    def test_scalar_grammar_stays_strict(self):
        for value in ('(15/2)','15 / 2','therefore 5/4','1e0','NaN','Infinity','١','9'*129):
            c=self.content();c['proposed_solution']['first_term']['value']=value
            self.assertIn('numeric_encoding_invalid', self.report(c)['violations'])

    def test_each_value_recomputed(self):
        for key in ('first_term','second_term','mean','variance'):
            c=self.content();c['proposed_solution'][key]['value']='4'
            r=self.report(c)
            self.assertIn('mathematical_value_invalid', r['violations'])
            self.assertEqual(r['verification_summary']['stage_status']['composition_valid'], 'NOT_EVALUATED')

    def test_expression_flexibility_and_no_execution(self):
        for text in ('30/4','30 ÷ 4'):
            c=self.content();c['proposed_solution']['first_term']['expression']=text
            r=self.report(c);self.assertTrue(r['accepted'], r)
            self.assertTrue(r['verification_summary']['expression_math_verified'])

    def test_expression_is_not_authority(self):
        c=self.content();c['proposed_solution']['first_term'].update(expression='30/4 = 15/2',value='4')
        self.assertFalse(self.report(c)['accepted'])

    def test_expression_boundary_screen(self):
        c=self.content();c['proposed_solution']['first_term']['expression']='Use sample standard deviation with n - 1.'
        self.assertFalse(self.report(c)['boundary_valid'])

    def test_required_pair_fields(self):
        for key in ('expression','value'):
            c=self.content();del c['proposed_solution']['first_term'][key]
            r=self.report(c);self.assertEqual(r['violations'], ['schema_invalid'])
            self.assertEqual(r['verification_summary']['stage_status']['math_valid'], 'NOT_EVALUATED')

    def test_input_identity(self):
        c=self.content();c['proposed_solution']['inputs']=dict(n=5,sum_x='15',sum_x2='55')
        r=self.report(c);self.assertIn('solution_verification_invalid',r['violations'])

    def test_final_fields_verified(self):
        for field,value in (('exact_radicand','4'),('numeric_answer','1.118'),('display_answer','1.11'),('numeric_answer','5/4')):
            c=self.content();c['proposed_solution'][field]=value
            self.assertIn('solution_verification_invalid',self.report(c)['violations'])

    def test_no_fixed_digit_requirement(self):
        for value in ('1.118033988749894848204586834365638117720309180','1.11803398874989484820458683436563811772031'):
            c=self.content();c['proposed_solution']['numeric_answer']=value
            self.assertTrue(self.report(c)['accepted'])

    def test_zero_denominator(self):
        c=self.content();c['proposed_solution']['first_term']['value']='1/0'
        self.assertIn('mathematical_value_invalid', self.report(c)['violations'])

    def test_invalid_inputs_arithmetic_failed_solution_unevaluated(self):
        c=self.content();c['proposed_math_inputs']['sum_x2']='1'
        r=self.report(c);s=r['verification_summary']['stage_status']
        self.assertEqual(s['math_valid'],'FAILED');self.assertEqual(s['solution_valid'],'NOT_EVALUATED')

    def test_brief_and_versions(self):
        b=compile_brief(self.inputs, policy=LEGACY_POLICY);text=serial(b)
        self.assertEqual(b.schema_version,'authoring-brief/2')
        for part in ('expression','value','scalar','55/5','1e-40','ROUND_HALF_UP'):self.assertIn(part,text)
        self.assertNotIn('45 decimal digits',text)
        a=run_once(self.inputs,FakeAuthor(self.content()), policy=LEGACY_POLICY)
        self.assertEqual(a['candidate']['schema_version'],'ai-author-candidate/2')
        self.assertFalse(a['experimental_package']['ready_for_rendering'])

    def test_qualification_preserves_not_evaluated(self):
        c=self.content();c['proposed_solution']['first_term']['value']='30/4 = 15/2'
        with tempfile.TemporaryDirectory() as out:
            r,_=execute(self.inputs,lambda _:SequenceAuthor(c,[]),attempts=1,output_dir=out,
                experiment_type='offline_synthetic',provider='synthetic_test',model='synthetic-no-model',
                integrity_reader=lambda:{},input_loader=lambda:self.inputs, policy=LEGACY_POLICY)
            self.assertIsNone(r.attempts[0].math_valid)
            self.assertIsNone(r.attempts[0].composition_valid)
            self.assertEqual(r.attempts[0].violations,('numeric_encoding_invalid',))

    def test_composition_failure_diagnostic(self):
        a=run_once(self.inputs,FakeAuthor(self.content()), policy=LEGACY_POLICY)
        from types import SimpleNamespace
        with patch('academic_os.ai_authoring.validation.p5c',return_value=SimpleNamespace(renderer_readiness=SimpleNamespace(ready_for_rendering=False))):
            r=validate_candidate(a['candidate'],self.inputs, policy=LEGACY_POLICY)
        self.assertIn('composition_invalid',r.violations)


if __name__ == '__main__': unittest.main()
