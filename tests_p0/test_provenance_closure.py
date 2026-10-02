"""Omitted public policies must never select historical compatibility behavior."""
import ast
import copy
import inspect
from pathlib import Path
import tempfile
import unittest

from academic_os.ai_authoring.brief import compile_brief, digest
from academic_os.ai_authoring.models import Candidate
from academic_os.ai_authoring.provenance import POLICY, LEGACY_POLICY
from academic_os.ai_authoring.service import read_inputs, run_once
from academic_os.ai_authoring.validation import validate_candidate, compose
from academic_os.ai_qualification.runner import execute
from tests_p0.provenance_replay import symbolic_content, RUN
from tests_p0.test_ai_authoring import FakeAuthor, synthetic
from tests_p0.test_ai_qualification import SequenceAuthor
import json


class ClosurePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = read_inputs('var/p0_q2.sqlite3')

    def test_all_public_defaults_require_provenance(self):
        for function in (compile_brief, run_once, validate_candidate, compose, execute):
            with self.subTest(entrypoint=function.__name__):
                self.assertEqual(inspect.signature(function).parameters['policy'].default, POLICY)

    def test_omitted_brief_policy_selects_version_three(self):
        brief = compile_brief(self.inputs)
        self.assertEqual(brief.schema_version, 'authoring-brief/3')
        self.assertEqual(brief.generation_policy, POLICY)
        self.assertEqual(validate_candidate({}, self.inputs).brief_ref, brief.identity)

    def test_omitted_service_policy_rejects_literal_work(self):
        result = run_once(self.inputs, FakeAuthor(synthetic()))['validation']
        self.assertTrue(result['expression_semantics_valid'])
        self.assertFalse(result['accepted'])
        self.assertFalse(result['derivation_provenance_valid'])
        self.assertEqual(result['acceptance_policy'], POLICY)

    def test_omitted_validation_and_compose_recheck_literals(self):
        audit = run_once(self.inputs, FakeAuthor(symbolic_content()))
        self.assertTrue(audit['validation']['accepted'])
        self.assertEqual(audit['validation']['brief_ref'], audit['brief']['identity'])
        candidate = copy.deepcopy(audit['candidate'])
        self.assertTrue(validate_candidate(candidate, self.inputs).accepted)
        self.assertIsNotNone(compose(Candidate.model_validate(candidate), self.inputs))
        candidate['content']['proposed_solution']['variance']['expression'] = '4'
        result = validate_candidate(candidate, self.inputs)
        self.assertTrue(result.expression_semantics_valid)
        self.assertFalse(result.accepted)
        self.assertFalse(result.derivation_provenance_valid)
        with self.assertRaises(ValueError):
            compose(Candidate.model_validate(candidate), self.inputs)

    def test_explicit_legacy_remains_compatible_but_cannot_downgrade_default(self):
        audit = run_once(self.inputs, FakeAuthor(synthetic()), policy=LEGACY_POLICY)
        candidate = Candidate.model_validate(audit['candidate'])
        self.assertTrue(audit['validation']['accepted'])
        self.assertEqual(audit['validation']['brief_ref'], audit['brief']['identity'])
        self.assertTrue(validate_candidate(candidate, self.inputs, policy=LEGACY_POLICY).accepted)
        self.assertIsNotNone(compose(candidate, self.inputs, policy=LEGACY_POLICY))
        self.assertFalse(validate_candidate(candidate, self.inputs).binding_valid)
        with self.assertRaises(ValueError):
            compose(candidate, self.inputs)
        old = compile_brief(self.inputs, policy=LEGACY_POLICY)
        self.assertEqual(digest(old), digest(json.loads((RUN / 'brief.json').read_text())))

    def test_runner_omission_rejects_literals_and_accepts_symbols(self):
        values = iter([synthetic(), symbolic_content()])
        with tempfile.TemporaryDirectory() as folder:
            report, path = execute(self.inputs, lambda _: SequenceAuthor(next(values), []),
                attempts=2, output_dir=folder, experiment_type='offline_synthetic',
                provider='synthetic_test', model='synthetic-no-model',
                integrity_reader=lambda: {}, input_loader=lambda: self.inputs)
            self.assertEqual(report.acceptance_policy, POLICY)
            self.assertEqual([r.derivation_provenance_valid for r in report.attempts], [False, True])
            self.assertEqual(report.aggregate_validation['accepted_count'], 1)
            brief = json.loads((path.parents[1] / 'brief.json').read_text())
            self.assertEqual(brief['schema_version'], 'authoring-brief/3')

    def test_cli_service_and_runner_pass_policy_explicitly(self):
        expected = {
            'academic_os/ai_authoring/__main__.py': {'compile_brief', 'run_once'},
            'academic_os/ai_qualification/__main__.py': {'compile_brief', 'execute'},
            'academic_os/ai_authoring/service.py': {'compile_brief', 'validate_candidate', 'compose'},
            'academic_os/ai_qualification/runner.py': {'compile_brief', 'run_once'},
        }
        for path, names in expected.items():
            calls = [n for n in ast.walk(ast.parse(Path(path).read_text()))
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in names]
            self.assertEqual({n.func.id for n in calls}, names, path)
            for call in calls:
                with self.subTest(path=path, call=call.func.id, line=call.lineno):
                    selected = next((kw.value for kw in call.keywords if kw.arg == 'policy'), None)
                    self.assertIsInstance(selected, ast.Name)
                    self.assertEqual(selected.id, 'POLICY' if path.endswith('__main__.py') else 'policy')
