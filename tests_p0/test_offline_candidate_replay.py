"""P6A.1d: original evidence, explicit transcriptions and negative controls."""
from academic_os.ai_authoring.provenance import LEGACY_POLICY
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_authoring.validation import validate_candidate
from tests_p0.offline_candidate_replay import fixture, transcriptions, probes, diagnostic, FIELDS


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=read_inputs('var/p0_q2.sqlite3')
        cls.records=[fixture(row,cls.inputs) for row in transcriptions()]

    def test_all_ten_classified_by_current_validator(self):
        self.assertEqual(len(self.records),10)
        for c,p,a in self.records:
            with self.subTest(attempt=p['source_attempt_id']):
                r=validate_candidate(c,self.inputs, policy=LEGACY_POLICY)
                self.assertFalse(r.accepted)
                self.assertTrue(r.math_valid and r.solution_valid)
                self.assertFalse(r.expression_semantics_valid)
                self.assertIn('unsupported_expression',r.violations)

    def test_raw_content_preserved_outside_four_fields(self):
        for c,p,a in self.records:
            content=copy.deepcopy(c['content'])
            for key in FIELDS:
                self.assertEqual(content['proposed_solution'][key]['expression'],a['candidate']['content']['proposed_solution'][key])
                content['proposed_solution'][key]=content['proposed_solution'][key]['expression']
            self.assertEqual(content,a['candidate']['content'])
            self.assertEqual(c['model_metadata'],a['candidate']['model_metadata'])
            self.assertEqual(p['lost_fields'],[])

    def test_historical_rejection(self):
        for c,p,a in self.records:
            self.assertFalse(a['validation']['accepted'])
            self.assertEqual(validate_candidate(a['candidate'],self.inputs, policy=LEGACY_POLICY).violations,('candidate_contract_version_unsupported',))

    def test_hash_bound_not_generic_transformation(self):
        row=copy.deepcopy(transcriptions()[0]);row['source_hash']='0'*64
        with self.assertRaisesRegex(ValueError,'differs'):fixture(row,self.inputs)

    def test_inspected_working_bound(self):
        row=copy.deepcopy(transcriptions()[0]);row['original_working']['first_term']='unknown'
        with self.assertRaisesRegex(ValueError,'changed'):fixture(row,self.inputs)

    def test_positive_and_negative_controls(self):
        for probe in probes([c for c,p,a in self.records]):
            with self.subTest(name=probe['name']):
                r=validate_candidate(probe['candidate'],self.inputs, policy=LEGACY_POLICY)
                # Historical P6A.1d fixtures retain equation strings; the new expression gate rejects them.
                self.assertFalse(r.accepted)
                self.assertIn('unsupported_expression',r.violations) if probe['expected_failure_class']!='numeric_encoding_invalid' else self.assertIn('numeric_encoding_invalid',r.violations)

    def test_encoding_failure_not_math_failure(self):
        p=probes([c for c,_,_ in self.records])[0]
        r=validate_candidate(p['candidate'],self.inputs, policy=LEGACY_POLICY)
        self.assertEqual(r.violations,('numeric_encoding_invalid',))
        self.assertEqual(diagnostic(r)['field'],'first_term.value')
        for key in ('math_valid','solution_valid','composition_valid'):
            self.assertEqual(r.verification_summary['stage_status'][key],'NOT_EVALUATED')

    def test_wrong_value_downstream_semantics(self):
        p=next(p for p in probes([c for c,_,_ in self.records]) if p['name']=='wrong-value')
        r=validate_candidate(p['candidate'],self.inputs, policy=LEGACY_POLICY);s=r.verification_summary['stage_status']
        self.assertEqual(s['math_valid'],'PASSED')  # input feasibility, not candidate-value certification
        self.assertEqual(s['solution_valid'],'FAILED')
        self.assertEqual(s['composition_valid'],'NOT_EVALUATED')

    def test_composition_diagnostic(self):
        candidate=copy.deepcopy(self.records[0][0])
        for key in FIELDS: candidate['content']['proposed_solution'][key]['expression']=candidate['content']['proposed_solution'][key]['value']
        with patch('academic_os.ai_authoring.validation.p5c',return_value=SimpleNamespace(renderer_readiness=SimpleNamespace(ready_for_rendering=False))):
            r=validate_candidate(candidate,self.inputs, policy=LEGACY_POLICY)
        self.assertEqual(diagnostic(r)['failure_class'],'composition_invalid')

    def test_expression_inconsistency_is_documented_not_reconciled(self):
        c=copy.deepcopy(self.records[1][0]);c['content']['proposed_solution']['first_term']['expression']='30/4 = 999'
        r=validate_candidate(c,self.inputs, policy=LEGACY_POLICY)
        self.assertFalse(r.accepted)
        self.assertFalse(r.expression_semantics_valid)
        self.assertIn('unsupported_expression',r.violations)


if __name__=='__main__':unittest.main()
