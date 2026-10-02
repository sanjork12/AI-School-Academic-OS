"""Offline role/support boundaries, numerical reuse and immutable qualification."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from academic_os.ai_authoring.brief import digest
from academic_os.ai_authoring.models import Candidate, ProviderContent
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_authoring import role_authoring as sl11
from academic_os.ai_authoring.roles import SL11, HINT, support_binding
from academic_os.ai_authoring.controlled import validate_case
from academic_os.ai_authoring.validation import validate_candidate as validate_sl10
from academic_os.ai_qualification.role_offline import evaluate, save, rebuild
from tests_p0.provenance_replay import symbolic_content


def fixture(i, values=None, **context):
    content = symbolic_content(values or dict(n=5, sum_x='30', sum_x2='190'))
    content['scaffold_steps'] = []
    return sl11.bind_candidate(content, i, candidate_id='ai-candidate-'+'7'*32,
        metadata=dict(provider='synthetic_test',model='offline-no-model',latency_seconds=0), **context)


def negative_cases(candidate):
    def changed(path, value):
        c = candidate.model_dump(mode='json'); target = c
        for key in path[:-1]: target = target[key]
        target[path[-1]] = value
        return c
    return {
        'sl10_role': (changed(['role_ref'], 'profiled-sd-standard-lesson-SL-10'), 'role_binding_invalid'),
        'four_scaffolds': (changed(['content','scaffold_steps'], symbolic_content()['scaffold_steps']), 'model_authored_scaffold_forbidden'),
        'stale_brief': (changed(['brief_sha256'], '0'*64), 'brief_binding_invalid'),
        'stale_role_policy': (changed(['current_inputs_sha256'], '0'*64), 'role_policy_binding_invalid'),
        'wrong_math': (changed(['content','proposed_solution','variance','value'], '3'), 'mathematical_value_invalid'),
        'expression_mismatch': (changed(['content','proposed_solution','mean','expression'], 'sum_x2 / n'), 'expression_semantics_valid'),
        'wrong_source': (changed(['content','proposed_solution','first_term','expression'], 'sum_x / n'), 'provenance_wrong_source'),
        'solution_inputs': (changed(['content','proposed_solution','inputs','sum_x'], '31'), 'solution_verification_invalid'),
        'answer_leakage': (changed(['content','question_template'], candidate.content.question_template+' Answer: 1.41.'), 'student_visible_answer_or_support_invalid'),
        'extra_hint_field': (changed(['content','formula_hint'], HINT), 'schema_invalid'),
        'numeric_encoding': (changed(['content','proposed_solution','mean','value'], '30/5 = 6'), 'numeric_encoding_invalid'),
    }


class SL11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = read_inputs('var/p0_q2.sqlite3')
        cls.c = fixture(cls.i)
        cls.hint = support_binding(cls.i)

    def test_positive_numerical_and_composition(self):
        before = digest(self.i.package)
        v = sl11.validate_candidate(self.c, self.i)
        self.assertTrue(v['accepted'], v)
        for k in ('role_binding_valid','support_policy_valid','math_valid','solution_valid',
                  'expression_semantics_valid','derivation_provenance_valid','numeric_encoding_valid'):
            self.assertIs(v[k], True)
        self.assertIsNone(v['scaffold_valid'])
        self.assertEqual(v['scaffold_status'], 'NOT_APPLICABLE')
        result = sl11.compose(self.c, self.i)
        self.assertEqual(result['formula_hint']['text'], HINT)
        self.assertEqual(result['formula_hint_sha256'], digest(self.hint))
        self.assertNotIn('solution', result['student_content'])
        self.assertEqual(result['teacher_solution']['display_answer'], '1.41')
        self.assertEqual(result['solution_visibility'], 'teacher_sidecar_only')
        for k in ('academic_approval','ready_for_p5c','ready_for_rendering','publishable'): self.assertFalse(result[k])
        self.assertEqual(digest(self.i.package), before)

    def test_negative_cases(self):
        for name, (candidate, code) in negative_cases(self.c).items():
            with self.subTest(case=name):
                v = sl11.validate_candidate(candidate, self.i)
                self.assertFalse(v['accepted']); self.assertIn(code, v['violations'])
                with self.assertRaises(ValueError): sl11.compose(candidate, self.i)

    def test_sl11_rejected_by_sl10(self):
        v = validate_sl10(self.c, self.i)
        self.assertFalse(v.accepted); self.assertIn('role_binding_invalid', v.violations)

    def test_sl10_controlled_failure_precedence_preserved(self):
        from academic_os.ai_authoring.controlled import CATALOG, context
        from academic_os.ai_authoring.service import run_once
        from tests_p0.test_ai_authoring import FakeAuthor
        content = symbolic_content(dict(n=5,sum_x='30',sum_x2='190'))
        content['proposed_solution']['mean']['value'] = 'not a scalar'
        result = run_once(self.i, FakeAuthor(content), **context(CATALOG['A']))['validation']
        self.assertEqual(result['verification_summary']['primary_failure']['code'], 'controlled_input_n_mismatch')
        self.assertIn('numeric_encoding_invalid', result['violations'])

    def test_missing_or_changed_application_hint(self):
        bad = self.hint.model_dump(); bad['source_sha256'] = '0'*64
        for hint in (None, bad, dict(self.hint.model_dump(),text='Answer: 1.41')):
            with self.subTest(hint=hint):
                v = sl11.validate_candidate(self.c, self.i, support=hint)
                self.assertFalse(v['accepted']); self.assertFalse(v['support_policy_valid'])

    def test_current_base_hint_required(self):
        i = copy.deepcopy(self.i)
        items = list(i.package.new_content)
        n = next(n for n,q in enumerate(items) if q.ref == self.hint.source_ref)
        items[n] = items[n].model_copy(update={'scaffolding':()})
        i = replace(i, package=i.package.model_copy(update={'new_content':tuple(items)}))
        self.assertFalse(sl11.validate_candidate(self.c, i)['accepted'])

    def test_controlled_exact_binding(self):
        case = validate_case(dict(controlled_case_id='SL11-primary',inputs=dict(n=5,sum_x='30',sum_x2='190')))
        ctx = dict(controlled_case=case,controlled_case_sha256=digest(case))
        c = fixture(self.i, **ctx)
        self.assertTrue(sl11.validate_candidate(c,self.i,**ctx)['controlled_input_binding_valid'])
        self.assertTrue(sl11.validate_candidate(c,self.i,**ctx)['accepted'])
        other = fixture(self.i, dict(n=6,sum_x='30',sum_x2='174'), **ctx)
        v = sl11.validate_candidate(other,self.i,**ctx)
        self.assertFalse(v['accepted']); self.assertFalse(v['controlled_input_binding_valid'])
        with self.assertRaises(ValueError): sl11.compile_brief(self.i,controlled_case=case,controlled_case_sha256='0'*64)

    def test_fraction_reuse(self):
        case = validate_case(dict(controlled_case_id='SL11-fraction',inputs=dict(n=2,sum_x='0.5',sum_x2='0.5')))
        ctx = dict(controlled_case=case,controlled_case_sha256=digest(case))
        c = fixture(self.i,dict(n=2,sum_x='1/2',sum_x2='1/2'),**ctx)
        self.assertTrue(sl11.validate_candidate(c,self.i,**ctx)['accepted'])
        self.assertEqual(c.content.proposed_math_inputs.sum_x, '1/2')

    def test_provenance_numeric_collision(self):
        c = fixture(self.i,dict(n=5,sum_x='5',sum_x2='5')).model_dump(mode='json')
        c['content']['proposed_solution']['first_term']['expression'] = 'sum_x / n'
        v = sl11.validate_candidate(c,self.i)
        self.assertTrue(v['math_valid']); self.assertTrue(v['expression_semantics_valid'])
        self.assertFalse(v['derivation_provenance_valid']); self.assertFalse(v['accepted'])

    def test_rebind_required_after_policy_change(self):
        c = self.c.model_dump(mode='json')
        b = sl11.compile_brief(self.i).model_dump(mode='json'); b['support_policy'] = 'stale-policy/0'
        c['brief_sha256'] = digest(b)
        self.assertFalse(sl11.validate_candidate(c,self.i)['accepted'])

    def test_candidate_schema_unchanged(self):
        before = json.loads(Path('output/p6a7b_sl11/before.json').read_text())
        self.assertEqual(digest(Candidate.model_json_schema()), before['candidate_schema_sha256'])
        self.assertEqual(digest(ProviderContent.model_json_schema()), before['provider_schema_sha256'])

    def test_qualification_rebuild_and_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            record = evaluate(self.c,self.i,support=self.hint)
            path = save(record,temp)
            self.assertEqual(rebuild(path,self.i),record)
            self.assertEqual(save(record,temp),path)
            record['validation']['accepted'] = False
            path.write_text(json.dumps(record),encoding='utf-8')
            with self.assertRaises(ValueError): rebuild(path,self.i)

    def test_rejected_qualification_preserves_failure(self):
        bad = self.c.model_dump(mode='json'); bad['role_ref'] = 'profiled-sd-standard-lesson-SL-10'
        with tempfile.TemporaryDirectory() as temp:
            record = evaluate(bad,self.i,support=self.hint)
            self.assertIsNone(record['composition'])
            self.assertEqual(rebuild(save(record,temp),self.i),record)
