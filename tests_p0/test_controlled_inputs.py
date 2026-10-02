"""P6A.6b offline controls. No real provider construction or calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from academic_os.ai_authoring.brief import compile_brief, digest, serial
from academic_os.ai_authoring.controlled import CATALOG, MODE, context, validate_case, binding
from academic_os.ai_authoring.provenance import POLICY, LEGACY_POLICY
from academic_os.ai_authoring.service import read_inputs, run_once
from academic_os.ai_authoring.validation import validate_candidate, compose
from academic_os.ai_qualification.runner import execute
from academic_os.ai_qualification.reporting import rebuild
from academic_os.ai_qualification.storage import read, file_hash
from academic_os.authored_math import summary_stats, display
from tests_p0.provenance_replay import symbolic_content
from tests_p0.test_ai_authoring import FakeAuthor
from tests_p0.test_ai_qualification import SequenceAuthor


class ControlledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i = read_inputs('var/p0_q2.sqlite3')
        cls.ctx = context(CATALOG['A'])
        cls.good = run_once(cls.i, FakeAuthor(symbolic_content(CATALOG['A'].inputs.model_dump())), **cls.ctx)

    def audit(self, content, **ctx):
        return run_once(self.i, FakeAuthor(content), **(ctx or self.ctx))

    def run_saved(self, value=None, **options):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        return execute(self.i, lambda _: SequenceAuthor(symbolic_content() if value is None else value, []),
            attempts=1, output_dir=tmp.name, experiment_type='offline_synthetic', provider='synthetic_test',
            model='synthetic-no-model', integrity_reader=lambda: {'offline':True}, input_loader=lambda:self.i,
            **(options or self.ctx))

    def test_catalog_mathematics(self):
        expected = [('5','4','2.00'),('5/2','1','1.00'),('2','1/2','0.71'),('4/3','2/9','0.47'),
                    ('-3','0','0.00'),('1000','1','1.00'),('1/6','1/324','0.06'),('21/200','441/40000','0.11')]
        for case, result in zip(CATALOG.values(), expected):
            with self.subTest(case=case.controlled_case_id):
                i=validate_case(case).inputs; m,v,s=summary_stats(i.n,i.sum_x,i.sum_x2)
                self.assertEqual((str(m),str(v),display(s)),result)

    def test_all_eight_full_pipeline_and_composition(self):
        for key, case in CATALOG.items():
            with self.subTest(case=key):
                ctx=context(case); a=self.audit(symbolic_content(case.inputs.model_dump()), **ctx)
                v=a['validation']
                for gate in ('accepted','controlled_input_binding_valid','math_valid','solution_valid',
                             'expression_semantics_valid','derivation_provenance_valid','composition_valid'):
                    self.assertIs(v[gate],True,(key,gate,v))
                self.assertEqual(compose(a['candidate'],self.i,**ctx),a['experimental_package'])

    def test_brief_four_deterministic_and_distinct_hashes(self):
        hashes=set()
        for case in CATALOG.values():
            b=compile_brief(self.i,**context(case)); hashes.add(digest(b))
            self.assertEqual(b.schema_version,'authoring-brief/4')
            self.assertEqual(b.controlled_case,case)
            self.assertEqual(b.controlled_case_sha256,digest(case))
            self.assertNotIn('One original feasible set',serial(b))
            self.assertEqual(serial(b),serial(compile_brief(self.i,**context(case))))
            self.assertEqual(b.generation_policy,POLICY)
        self.assertEqual(len(hashes),8)

    def test_old_briefs_unchanged(self):
        self.assertEqual(digest(compile_brief(self.i)), '80267ba65c7f63ceb2f03048b14565dbebffb30c07fd52b4da1cf84a89f61149')
        from tests_p0.provenance_replay import RUN
        self.assertEqual(digest(compile_brief(self.i,policy=LEGACY_POLICY)),digest(read(RUN/'brief.json')))

    def test_immutable_case(self):
        with self.assertRaises(ValueError):CATALOG['A'].inputs.n=1
        with self.assertRaises(TypeError):CATALOG['A']=CATALOG['B']

    def test_exact_equivalent_encodings_and_preserved_strings(self):
        values=dict(n=2,sum_x='21/100',sum_x2='441/10000')
        a=self.audit(symbolic_content(values),**context(CATALOG['H']))
        self.assertTrue(a['validation']['accepted'])
        self.assertEqual(a['candidate']['content']['proposed_math_inputs'],values)

    def test_half_decimal_equals_half_fraction(self):
        c=validate_case(dict(controlled_case_id='half',inputs=dict(n=2,sum_x='0.5',sum_x2='0.5')))
        self.assertEqual(binding(c,dict(n=2,sum_x='1/2',sum_x2='1/2')),(True,'controlled_inputs_match'))

    def test_no_float_tolerance(self):
        self.assertFalse(binding(CATALOG['H'],dict(n=2,sum_x='0.21000000000000000000000000000001',sum_x2='0.0441'))[0])

    def test_missing_context_before_author(self):
        f=FakeAuthor()
        with self.assertRaises(ValueError):run_once(self.i,f,controlled_mode=MODE)
        self.assertEqual(f.calls,0)

    def test_missing_hash(self):
        with self.assertRaises(ValueError):compile_brief(self.i,controlled_mode=MODE,controlled_case=CATALOG['A'])

    def test_tampered_hash(self):
        with self.assertRaises(ValueError):compile_brief(self.i,**dict(self.ctx,controlled_case_sha256='0'*64))

    def test_wrong_id_hash(self):
        c=CATALOG['A'].model_copy(update={'controlled_case_id':'B'})
        with self.assertRaises(ValueError):compile_brief(self.i,**dict(self.ctx,controlled_case=c))

    def test_changed_case_after_brief(self):
        v=validate_candidate(self.good['candidate'],self.i,**context(CATALOG['B']))
        self.assertFalse(v.accepted); self.assertFalse(v.binding_valid)
        with self.assertRaises(ValueError):compose(self.good['candidate'],self.i,**context(CATALOG['B']))

    def test_changed_id_with_recomputed_hash(self):
        c=CATALOG['A'].model_copy(update={'controlled_case_id':'different'})
        self.assertFalse(validate_candidate(self.good['candidate'],self.i,**context(c)).accepted)

    def test_wrong_each_input(self):
        for field,value in (('n',11),('sum_x','49'),('sum_x2','291')):
            with self.subTest(field=field):
                values=dict(CATALOG['A'].inputs.model_dump(),**{field:value})
                a=self.audit(symbolic_content(values));v=a['validation']
                self.assertFalse(v['accepted']);self.assertFalse(v['controlled_input_binding_valid'])
                self.assertEqual(v['controlled_input_binding_reason'],'controlled_input_'+field+'_mismatch')
                self.assertTrue(v['math_valid']);self.assertTrue(v['solution_valid'])
                self.assertTrue(v['derivation_provenance_valid'])
                with self.assertRaises(ValueError):compose(a['candidate'],self.i,**self.ctx)

    def test_old_five_fifteen_fiftyfive_internally_correct_rejected(self):
        a=self.audit(symbolic_content(dict(n=5,sum_x='15',sum_x2='55')));v=a['validation']
        self.assertFalse(v['accepted']);self.assertFalse(v['controlled_input_binding_valid'])
        self.assertTrue(v['math_valid']);self.assertTrue(v['solution_valid'])
        self.assertTrue(v['expression_semantics_valid']);self.assertTrue(v['derivation_provenance_valid'])
        self.assertIsNone(a['experimental_package'])

    def test_solution_copy_structural_equality_retained(self):
        c=symbolic_content();c['proposed_solution']['inputs']['sum_x']='100/2'
        v=self.audit(c)['validation']
        self.assertTrue(v['controlled_input_binding_valid']);self.assertFalse(v['solution_valid']);self.assertFalse(v['accepted'])

    def test_provenance_cannot_be_bypassed(self):
        c=symbolic_content();c['proposed_solution']['first_term']['expression']='29'
        v=self.audit(c)['validation']
        self.assertTrue(v['controlled_input_binding_valid']);self.assertTrue(v['expression_semantics_valid'])
        self.assertFalse(v['derivation_provenance_valid']);self.assertFalse(v['accepted'])

    def test_missing_mode_cannot_downgrade_controlled_candidate(self):
        self.assertFalse(validate_candidate(self.good['candidate'],self.i).accepted)
        with self.assertRaises(ValueError):compose(self.good['candidate'],self.i)

    def test_context_without_mode_rejected(self):
        with self.assertRaises(ValueError):compile_brief(self.i,controlled_case=CATALOG['A'])

    def test_legacy_policy_rejected_for_controlled_mode(self):
        with self.assertRaises(ValueError):compile_brief(self.i,policy=LEGACY_POLICY,**self.ctx)

    def test_malformed_cases_before_factory(self):
        variants=[dict(n=True),dict(n=0),dict(n=1000001),dict(n='10'),dict(sum_x='1/0'),
                  dict(sum_x='1e2'),dict(sum_x='1'*129),dict(sum_x2='0'),dict(n=1,sum_x='2',sum_x2='5')]
        for change in variants:
            with self.subTest(change=change):
                case=dict(controlled_case_id='bad',inputs=dict(CATALOG['A'].inputs.model_dump(),**change))
                factory=Mock(side_effect=AssertionError('No provider'))
                with self.assertRaises((ValueError,ArithmeticError)):
                    execute(self.i,factory,attempts=1,output_dir='unused',experiment_type='offline_synthetic',
                        provider='synthetic',model='synthetic',integrity_reader=Mock(),input_loader=Mock(),
                        controlled_mode=MODE,controlled_case=case,controlled_case_sha256=digest(case))
                factory.assert_not_called()

    def test_unsafe_model_copy_reparsed(self):
        c=CATALOG['A'].model_copy(update={'inputs':CATALOG['A'].inputs.model_copy(update={'n':True})})
        with self.assertRaises(ValueError):compile_brief(self.i,**dict(self.ctx,controlled_case=c,controlled_case_sha256=digest(c)))

    def test_binding_omission_does_not_accept(self):
        with patch('academic_os.ai_authoring.controlled.binding',return_value=(None,'controlled_input_not_evaluated')):
            v=self.audit(symbolic_content())['validation']
        self.assertFalse(v['accepted']);self.assertFalse(v['composition_valid'])

    def test_runner_saved_context_replay(self):
        r,p=self.run_saved();directory=p.parent.parent
        self.assertEqual(r.status,'complete');self.assertTrue(r.attempts[0].accepted)
        self.assertIsNone(r.attempts[0].case_id)
        self.assertEqual(r.controlled_case,CATALOG['A']);self.assertEqual(r.attempts[0].returned_inputs,CATALOG['A'].inputs.model_dump())
        self.assertEqual(rebuild(directory)[0],r);self.assertEqual(rebuild(directory)[1],p)

    def test_runner_wrong_case_separate_reporting(self):
        r,_=self.run_saved(symbolic_content(dict(n=5,sum_x='15',sum_x2='55')))
        a=r.attempts[0];self.assertTrue(a.math_valid);self.assertFalse(a.controlled_input_binding_valid)
        self.assertEqual(r.rejection_summary['controlled_input_n_mismatch'],1)

    def test_operational_and_schema_failure_not_evaluated(self):
        for value in (RuntimeError('offline fixture'),{'bad':'schema'}):
            with self.subTest(value=str(value)):
                r,_=self.run_saved(value)
                self.assertEqual(r.attempts[0].controlled_input_binding_status,'NOT_EVALUATED')
                self.assertIsNone(r.attempts[0].controlled_input_binding_valid)

    def test_invalid_trusted_refresh_still_has_rebuildable_failure_report(self):
        values=iter([self.i,object()])
        with tempfile.TemporaryDirectory() as directory:
            trace=[]
            r,p=execute(self.i,lambda _:SequenceAuthor(symbolic_content(),trace),attempts=2,
                output_dir=directory,experiment_type='offline_synthetic',provider='synthetic_test',
                model='synthetic-no-model',integrity_reader=lambda:{},input_loader=lambda:next(values),**self.ctx)
            self.assertEqual(r.status,'incomplete')
            self.assertEqual(len(trace),1)
            self.assertEqual(r.operational_outcomes,{'input_validation_failure':1})
            self.assertFalse(r.attempts[0].accepted)
            self.assertIsNone(r.attempts[0].controlled_input_binding_valid)
            self.assertEqual(rebuild(p.parents[1])[0],r)

    def test_caller_dictionary_mutation_cannot_replace_captured_case(self):
        original=CATALOG['A'].model_dump()
        ctx=dict(self.ctx,controlled_case=original)
        class MutatingAuthor(FakeAuthor):
            def author(self,brief):
                original['inputs']['n']=5
                return super().author(brief)
        a=run_once(self.i,MutatingAuthor(symbolic_content()),**ctx)
        self.assertTrue(a['validation']['accepted'])
        self.assertEqual(a['brief']['controlled_case']['inputs']['n'],10)

    def test_report_missing_context_fails(self):
        r,p=self.run_saved();directory=p.parent.parent
        m=read(directory/'run.json');m.pop('controlled_mode')
        (directory/'run.json').write_text(serial(m),encoding='utf-8')
        with self.assertRaises(ValueError):rebuild(directory)

    def test_report_tampered_case_hash(self):
        r,p=self.run_saved();directory=p.parent.parent
        m=read(directory/'run.json');m['controlled_case_sha256']='0'*64
        (directory/'run.json').write_text(serial(m),encoding='utf-8')
        with self.assertRaises(ValueError):rebuild(directory)

    def test_report_omitted_gate_fails(self):
        r,p=self.run_saved();directory=p.parent.parent;folder=directory/'attempt-01'
        a=read(folder/'attempt.json');a.pop('controlled_input_binding_valid')
        (folder/'attempt.json').write_text(serial(a),encoding='utf-8')
        with self.assertRaises(ValueError):rebuild(directory)

    def test_report_recomputes_instead_of_trusting_flags(self):
        r,p=self.run_saved(symbolic_content(dict(n=5,sum_x='15',sum_x2='55')))
        directory=p.parent.parent;folder=directory/'attempt-01';a=read(folder/'attempt.json')
        audit=read(folder/a['candidate_artifact_ref']);v=audit['validation']
        for obj in (a,v):
            obj.update(controlled_input_binding_valid=True,controlled_input_binding_status='PASSED',
                       controlled_input_binding_reason='controlled_inputs_match')
        (folder/'validation.json').write_text(serial(v),encoding='utf-8')
        (folder/a['candidate_artifact_ref']).write_text(serial(audit),encoding='utf-8')
        for name in a['artifact_hashes']:a['artifact_hashes'][name]=file_hash(folder/name)
        (folder/'attempt.json').write_text(serial(a),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'exact replay'):rebuild(directory)

    def test_cli_controlled_dry_run_no_provider(self):
        from tests_p0.test_direct_v2_preflight import PreflightTests
        helper=PreflightTests();helper.inputs=self.i
        code,text=helper.cli(['--controlled-case','G','--attempts','1'])
        self.assertEqual(code,0);plan=json.loads(text)
        self.assertEqual(plan['brief']['controlled_case'],CATALOG['G'].model_dump())
        self.assertTrue(plan['provenance_verification_required']);self.assertEqual(plan['attempt_count'],1)


if __name__=='__main__':unittest.main()
