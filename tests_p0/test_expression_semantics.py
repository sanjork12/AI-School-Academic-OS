"""Controlled grammar, exact evaluator, integration and immutable offline replay."""
from academic_os.ai_authoring.provenance import LEGACY_POLICY
import copy
from decimal import Decimal
from fractions import Fraction
import unittest
from unittest.mock import patch
from academic_os.ai_authoring.expressions import parse,evaluate,context_for,check,verify_solution_expressions,ExpressionError
from academic_os.ai_authoring.validation import validate_candidate
from academic_os.ai_authoring.service import read_inputs,run_once
from academic_os.ai_qualification.stress import synthetic_content
from tests_p0.test_ai_authoring import FakeAuthor
from tests_p0.expression_replay import replay

INPUTS=dict(n=5,sum_x='15',sum_x2='55')


class ParserTests(unittest.TestCase):
    def test_canonical_square_and_division(self):
        self.assertEqual(parse('(Σx / n)²'),parse('(sum_x / n)^2'))
        self.assertEqual(parse('30 ÷ 4'),parse('30/4'))
        self.assertEqual(parse('1.50'),parse('1.5'))

    def test_required_vocabulary(self):
        for expression,value in [('Σx','15'),('Σx²','55'),('Σx / n','3'),('(Σx / n)²','9'),('Σx² / n','11'),
            ('Σx² / n - (Σx / n)²','2'),('first term','11'),('second term','9'),('first term - second term','2'),('radicand','2')]:
            with self.subTest(expression=expression):self.assertTrue(check(expression,value,INPUTS)['valid'])

    def test_wrong_corresponding_values(self):
        for expression,value in [('Σx / n','4'),('(Σx / n)²','8'),('Σx² / n','10')]:
            self.assertEqual(check(expression,value,INPUTS)['reason'],'expression_value_mismatch')

    def test_exact_fraction_and_signed_decimal(self):
        context,_=context_for(INPUTS)
        for text,value in [('15/2',Fraction(15,2)),('-1/2',Fraction(-1,2)),('0.1',Fraction(1,10)),('0.3 - 0.2',Fraction(1,10))]:
            self.assertEqual(evaluate(parse(text),context),value)

    def test_root_decimal_policy(self):
        r=check('sqrt(2)','1.414213562373095048801688724209698078569671875',INPUTS)
        self.assertTrue(r['valid']);self.assertEqual(r['comparison'],'decimal_absolute_tolerance_1e-40')
        self.assertFalse(check('sqrt(radicand)','1.4142',INPUTS)['valid'])
        self.assertTrue(check('sqrt(4)','2',INPUTS)['valid'])

    def test_unsupported_code_operators_and_prose(self):
        for text in ['1+2','2*3','2**2','n[0]','n.real','__import__("os")','[x for x in n]','lambda:1','sum(n)',
                     'therefore 11','30/4 = 999','Σx / (n-1) # sample','1e3','2^3','{n:1}']:
            with self.subTest(text=text):self.assertFalse(check(text,'1',INPUTS)['valid'])

    def test_malformed(self):
        for text in ('','(','(1','1)','1/','sqrt()','1 2','()'):
            self.assertEqual(check(text,'1',INPUTS)['reason'],'parser_failure')

    def test_zero_and_negative_root(self):
        self.assertEqual(check('1/0','1',INPUTS)['reason'],'division_by_zero')
        self.assertEqual(check('sqrt(-1)','1',INPUTS)['reason'],'negative_radicand')
        self.assertTrue(check('0','0',INPUTS)['valid'])

    def test_bounded_input_and_depth(self):
        for text in ('9'*257,'('*18+'1'+')'*18):self.assertEqual(check(text,'1',INPUTS)['reason'],'expression_limit')
        text='9'*128
        for _ in range(4):text='('+text+')²'
        self.assertEqual(check(text,'1',INPUTS)['reason'],'arithmetic_limit')

    def test_nonfinite_and_non_ascii_values(self):
        for value in ('NaN','Infinity','١','1e0','1/0','9'*129):self.assertFalse(check('1',value,INPUTS)['valid'])

    def test_unsupported_root_composition(self):
        self.assertEqual(check('sqrt(2)/2','1',INPUTS)['reason'],'unsupported_root_composition')

    def test_context_does_not_use_claimed_terms(self):
        c=synthetic_content();c['proposed_solution']['first_term'].update(expression='first term',value='999')
        r=verify_solution_expressions(c);self.assertFalse(r['expression_semantics_valid'])
        self.assertEqual(r['checks']['first_term']['evaluated_value'],'29')

    def test_wrong_expression_and_claim_cannot_agree_on_wrong_answer(self):
        c=synthetic_content();c['proposed_solution']['first_term'].update(expression='999',value='999')
        r=verify_solution_expressions(c)
        self.assertEqual(r['checks']['first_term']['reason'],'expression_expected_value_mismatch')


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.inputs=read_inputs('var/p0_q2.sqlite3')

    def test_current_candidate_dimension(self):
        audit=run_once(self.inputs,FakeAuthor(), policy=LEGACY_POLICY)
        self.assertTrue(audit['validation']['accepted']);self.assertTrue(audit['validation']['expression_semantics_valid'])

    def test_wrong_expression_correct_value_blocks(self):
        c=synthetic_content();c['proposed_solution']['first_term']['expression']='28'
        r=run_once(self.inputs,FakeAuthor(c), policy=LEGACY_POLICY)['validation']
        self.assertFalse(r['accepted']);self.assertFalse(r['expression_semantics_valid'])
        self.assertTrue(r['math_valid']);self.assertTrue(r['solution_valid'])
        self.assertEqual(r['verification_summary']['stage_status']['composition_valid'],'NOT_EVALUATED')

    def test_unsupported_not_guessed(self):
        c=synthetic_content();c['proposed_solution']['first_term']['expression']='29 = 29'
        r=run_once(self.inputs,FakeAuthor(c), policy=LEGACY_POLICY)['validation']
        self.assertIn('unsupported_expression',r['violations']);self.assertFalse(r['accepted'])

    def test_encoding_failure_expression_not_evaluated(self):
        c=synthetic_content();c['proposed_solution']['first_term']['value']='29 = 29'
        r=run_once(self.inputs,FakeAuthor(c), policy=LEGACY_POLICY)['validation']
        self.assertEqual(r['verification_summary']['stage_status']['expression_semantics_valid'],'NOT_EVALUATED')

    def test_saved_live_replay_deterministic_without_provider_or_current_db(self):
        with patch('socket.socket.connect',side_effect=AssertionError('No network')),patch('academic_os.ai_authoring.service.read_inputs',side_effect=AssertionError('No current academic read')):
            a=replay();b=replay()
        self.assertEqual(a,b);self.assertEqual(a['candidate_count'],10)
        self.assertEqual(a['expression_checks_performed'],40)
        self.assertEqual(a['expression_semantics_valid_count'],10)
        self.assertEqual(a['unsupported_expression_count'],0)


if __name__=='__main__':unittest.main()
