"""P6A.4 independent identity, policy, immutable replay and reporting controls."""
import copy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from academic_os.ai_authoring.provenance import POLICY, LEGACY_POLICY, verify_solution_provenance
from academic_os.ai_authoring.expressions import verify_solution_expressions
from academic_os.ai_authoring.brief import compile_brief, digest
from academic_os.ai_authoring.models import Candidate, ProviderContent, Validation
from academic_os.ai_authoring.service import read_inputs, run_once
from academic_os.ai_authoring.validation import validate_candidate, compose
from academic_os.ai_qualification.runner import execute
from academic_os.ai_qualification.reporting import rebuild
from tests_p0.provenance_replay import controls, historical_replay, symbolic_content, symbolic_replay, RUN
from tests_p0.test_ai_authoring import FakeAuthor, synthetic
from tests_p0.test_ai_qualification import SequenceAuthor


class ProvenanceTests(unittest.TestCase):
    def test_positive_and_negative_controls(self):
        for case in symbolic_replay()['controls']:
            with self.subTest(case=case['name']):
                self.assertTrue(case['expectation_met'],case['provenance'])

    def test_identity_collisions_preserve_numeric_pass(self):
        cases={c['name']:c for c in symbolic_replay()['controls']}
        for name in ('wrong_first_source','wrong_mean_source','wrong_second_source',
                     'swapped_variance_zero','equal_wrong_denominator','equal_literal_denominator',
                     'zero_literal','constant_variance','self_variance','self_first'):
            with self.subTest(name=name):
                c=cases[name]
                self.assertTrue(c['expression_semantics']['expression_semantics_valid'])
                self.assertFalse(c['provenance']['derivation_provenance_valid'])

    def test_resolution_never_uses_candidate_claims(self):
        c=symbolic_content();c['proposed_solution']['first_term']['value']='999'
        r=verify_solution_provenance(c)
        self.assertTrue(r['derivation_provenance_valid'])
        self.assertEqual(r['checks']['variance']['resolved_symbolic_sources'][0]['value'],'29')
        self.assertFalse(verify_solution_expressions(c)['expression_semantics_valid'])

    def test_no_historical_failure_backfill(self):
        c=synthetic();r=verify_solution_provenance(c,historical=True)
        self.assertEqual(r['status'],'INSUFFICIENT_EVIDENCE');self.assertIsNone(r['derivation_provenance_valid'])
        self.assertTrue(all(x['ast'] is not None and x['valid'] is None for x in r['checks'].values()))

    def test_mixed_literal_no_credit(self):
        c=symbolic_content();c['proposed_solution']['mean']['expression']='sum_x / 10'
        self.assertFalse(verify_solution_provenance(c)['derivation_provenance_valid'])

    def test_canonical_aliases_and_parentheses(self):
        c=symbolic_content();c['proposed_solution']['variance']['expression']='((Σx² ÷ n) - ((Σx ÷ n)²))'
        self.assertTrue(verify_solution_provenance(c)['derivation_provenance_valid'])

    def test_arbitrary_equivalent_structure_is_rejected(self):
        c=symbolic_content();c['proposed_solution']['mean']['expression']='sum_x / n - 0'
        self.assertTrue(verify_solution_expressions(c)['expression_semantics_valid'])
        self.assertFalse(verify_solution_provenance(c)['derivation_provenance_valid'])

    def test_replays_deterministic_offline(self):
        with patch.object(socket.socket,'connect',side_effect=AssertionError('No network')), \
             patch.object(socket,'create_connection',side_effect=AssertionError('No network')):
            first=historical_replay();self.assertEqual(first,historical_replay())
            self.assertEqual(symbolic_replay(),symbolic_replay())
        self.assertEqual(first['historically_accepted'],10)
        self.assertEqual(first['expression_semantics_passed'],40)
        self.assertEqual(first['status_counts'],dict(PASSED=0,FAILED=0,INSUFFICIENT_EVIDENCE=40,NOT_EVALUATED=0))


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=read_inputs('var/p0_q2.sqlite3')

    def author(self,c=None):
        return run_once(self.inputs,FakeAuthor(symbolic_content() if c is None else c),policy=POLICY)

    def test_future_symbolic_acceptance(self):
        a=self.author();v=a['validation']
        self.assertTrue(v['accepted']);self.assertTrue(v['derivation_provenance_valid'])
        self.assertEqual(v['derivation_provenance_status'],'PASSED')
        self.assertEqual(v['acceptance_policy'],POLICY)
        self.assertEqual(a['candidate']['schema_version'],'ai-author-candidate/2')
        self.assertFalse(a['ready_for_rendering']);self.assertFalse(a['academic_approval'])

    def test_numeric_valid_provenance_invalid(self):
        a=self.author(synthetic());v=a['validation']
        for k in ('math_valid','solution_valid','expression_semantics_valid'):self.assertTrue(v[k])
        self.assertFalse(v['accepted']);self.assertFalse(v['derivation_provenance_valid'])
        self.assertEqual(v['verification_summary']['stage_status']['composition_valid'],'NOT_EVALUATED')

    def test_independent_provenance_pass_wrong_claim(self):
        c=symbolic_content();c['proposed_solution']['mean']['value']='999'
        v=self.author(c)['validation']
        self.assertTrue(v['derivation_provenance_valid']);self.assertFalse(v['solution_valid'])
        self.assertFalse(v['expression_semantics_valid']);self.assertFalse(v['accepted'])

    def test_early_failure_not_evaluated(self):
        c=symbolic_content();c['proposed_solution']['mean']['value']='invalid'
        v=self.author(c)['validation']
        self.assertIsNone(v['derivation_provenance_valid'])
        self.assertEqual(v['derivation_provenance_status'],'NOT_EVALUATED')

    def test_legacy_compatibility_is_explicit_in_result(self):
        v=run_once(self.inputs,FakeAuthor(synthetic()),policy=LEGACY_POLICY)['validation']
        self.assertTrue(v['accepted']);self.assertIsNone(v['derivation_provenance_valid'])
        self.assertEqual(v['acceptance_policy'],LEGACY_POLICY)

    def test_historical_validation_absence_is_null(self):
        audit=json.loads(next((RUN/'attempt-01').glob('ai-candidate-*.json')).read_text())
        v=Validation.model_validate(audit['validation'])
        self.assertTrue(v.accepted);self.assertIsNone(v.derivation_provenance_valid)
        self.assertEqual(v.derivation_provenance_status,'NOT_EVALUATED')

    def test_generation_brief_version_and_binding(self):
        old=compile_brief(self.inputs, policy=LEGACY_POLICY);new=compile_brief(self.inputs,policy=POLICY)
        self.assertEqual(old.schema_version,'authoring-brief/2');self.assertEqual(new.schema_version,'authoring-brief/3')
        self.assertEqual(new.generation_policy,POLICY);self.assertNotEqual(digest(old),digest(new))
        historical=json.loads((RUN/'brief.json').read_text())
        self.assertEqual(digest(old),digest(historical))
        text=' '.join(new.required_output)
        self.assertIn('sum_x2 / n',text);self.assertIn('not literal substitutions',text)

    def test_candidate_cannot_select_or_downgrade_policy(self):
        legacy=run_once(self.inputs,FakeAuthor(),policy=LEGACY_POLICY)['candidate']
        r=validate_candidate(legacy,self.inputs,policy=POLICY)
        self.assertFalse(r.binding_valid);self.assertFalse(r.accepted)
        c=symbolic_content();c['acceptance_policy']=LEGACY_POLICY
        self.assertFalse(self.author(c)['validation']['schema_valid'])
        with self.assertRaises(ValueError):run_once(self.inputs,FakeAuthor(),policy='unknown')

    def test_compose_rechecks_required_provenance(self):
        a=self.author();c=copy.deepcopy(a['candidate'])
        c['content']['proposed_solution']['variance']['expression']='4'
        with self.assertRaises(ValueError):compose(Candidate.model_validate(c),self.inputs,policy=POLICY)

    def test_candidate_payload_schema_unchanged(self):
        self.assertEqual(set(ProviderContent.model_fields),{'question_template','proposed_math_inputs','scaffold_steps','proposed_solution'})
        self.assertEqual(Candidate.model_fields['schema_version'].default,'ai-author-candidate/2')

    def test_qualification_statuses_and_report_rebuild(self):
        values=iter([symbolic_content(),synthetic(),RuntimeError('synthetic provider failure')])
        with tempfile.TemporaryDirectory() as folder:
            report,path=execute(self.inputs,lambda _:SequenceAuthor(next(values),[]),attempts=3,
                output_dir=folder,experiment_type='offline_synthetic',provider='synthetic_test',model='synthetic-no-model',
                integrity_reader=lambda:{},input_loader=lambda:self.inputs,policy=POLICY)
            self.assertEqual(report.status,'complete');self.assertEqual(report.acceptance_policy,POLICY)
            self.assertEqual([r.derivation_provenance_valid for r in report.attempts],[True,False,None])
            self.assertEqual(report.aggregate_validation['derivation_provenance_status_counts'],
                             dict(PASSED=1,FAILED=1,INSUFFICIENT_EVIDENCE=0,NOT_EVALUATED=1))
            self.assertEqual(report,rebuild(path.parents[1])[0])

    def test_historical_reporting_keeps_acceptance_and_null(self):
        with tempfile.TemporaryDirectory() as folder:
            report,_=rebuild(RUN,output_dir=folder)
            self.assertEqual(report.aggregate_validation['accepted_count'],10)
            self.assertTrue(all(r.derivation_provenance_valid is None for r in report.attempts))
            self.assertEqual(report.aggregate_validation['derivation_provenance_status_counts']['NOT_EVALUATED'],10)


if __name__ == '__main__':
    unittest.main()
