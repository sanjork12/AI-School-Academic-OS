"""Offline qualification/stress regressions. Every provider is synthetic or mocked."""
from academic_os.ai_authoring.provenance import LEGACY_POLICY
import contextlib
import copy
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
from academic_os.ai_authoring.brief import ROLE, serial
from academic_os.ai_authoring.models import Metadata
from academic_os.ai_authoring.provider import OpenAICandidateAuthor, ProviderReply
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_qualification.runner import execute
from academic_os.ai_qualification.reporting import rebuild
from academic_os.ai_qualification.observer import ObservedAuthor, operational_code
from academic_os.ai_qualification.stress import cases, synthetic_content, SyntheticStressAuthor
from academic_os.ai_qualification.storage import read
from tests_p0.teacher_product_acceptance import state


class SequenceAuthor:
    def __init__(self,value,trace,latency=1,usage=None):
        self.value=value;self.trace=trace;self.latency=latency;self.usage=usage or {};self.last={}
    def author(self,brief):
        self.trace.append(serial(brief))
        if isinstance(self.value,BaseException):raise self.value
        if isinstance(self.value,ProviderReply):return self.value
        self.last={'configuration':{'structured_output_mode':'synthetic_json'},'call_count':0}
        return ProviderReply(serial(self.value),Metadata(provider='synthetic_test',model='synthetic-no-model',latency_seconds=self.latency,**self.usage))


class QualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state();cls.inputs=read_inputs('var/p0_q2.sqlite3')
    @classmethod
    def tearDownClass(cls):assert cls.before==state()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.trace=[]
    def run_values(self,values,**options):
        values=iter(values)
        return execute(self.inputs,lambda case:SequenceAuthor(next(values),self.trace),attempts=options.pop('attempts',1),
            output_dir=self.tmp.name,experiment_type='offline_synthetic',provider='synthetic_test',model='synthetic-no-model',
            integrity_reader=options.pop('integrity_reader',lambda:{'freeze_inventory_matches':True}),
            input_loader=options.pop('input_loader',lambda:self.inputs),**options, policy=LEGACY_POLICY)
    def test_01_independent_stable_briefs_and_default_ten(self):
        r,p=self.run_values([synthetic_content() for _ in range(10)],attempts=10)
        self.assertEqual(len(self.trace),10);self.assertEqual(len(set(self.trace)),1)
        self.assertEqual(r.attempt_count,10);self.assertEqual(r.aggregate_validation['accepted_count'],10)
        self.assertFalse(r.safety_summary['model_quality_certified']);self.assertFalse(r.safety_summary['qualification_threshold_defined'])
    def test_02_candidate_rejection_separate_from_operational_failure(self):
        bad=synthetic_content();bad['proposed_solution']['display_answer']='-1.00'
        r,_=self.run_values([synthetic_content(),bad,RuntimeError('network')],attempts=3)
        self.assertEqual(r.operational_outcomes,{'candidate_accepted':1,'candidate_validation_rejected':1,'provider_failure':1})
        self.assertEqual(r.aggregate_validation['rejected_count'],1)
        self.assertEqual(r.aggregate_validation['math_valid_evaluated_count'],2)
        self.assertIsNone(r.attempts[2].math_valid);self.assertEqual(r.attempts[2].violations,())
    def test_03_schema_failure_not_counted_as_math(self):
        d=synthetic_content();d['approved']=True
        r,_=self.run_values([d]);self.assertEqual(r.attempts[0].outcome,'candidate_schema_failure')
        self.assertEqual(r.rejection_summary,{'schema_invalid':1});self.assertIsNone(r.attempts[0].math_valid)
    def test_04_missing_usage_stays_unknown(self):
        r,_=self.run_values([synthetic_content()]);self.assertIsNone(r.usage_summary['total_tokens']['known_sum'])
        self.assertEqual(r.usage_summary['total_tokens']['missing_attempts'],1);self.assertEqual(r.usage_summary['cost_status'],'not_computed')
    def test_05_known_usage_and_latency(self):
        replies=[ProviderReply(serial(synthetic_content()),Metadata(provider='synthetic_test',model='test',latency_seconds=n,input_tokens=10,output_tokens=20,total_tokens=30)) for n in (1,3,2)]
        r,_=self.run_values(replies,attempts=3)
        self.assertEqual(r.usage_summary['total_tokens']['known_sum'],90)
        self.assertEqual((r.latency_summary['min'],r.latency_summary['max'],r.latency_summary['mean'],r.latency_summary['median']),(1000,3000,2000,2000))
    def test_06_all_synthetic_stress_cases_blocked(self):
        catalog=[dict(case_id=k,**v) for k,v in cases().items()]
        r,_=execute(self.inputs,lambda c:SyntheticStressAuthor(c),attempts=len(catalog),output_dir=self.tmp.name,
            experiment_type='offline_synthetic_stress',provider='offline_synthetic',model='synthetic-no-model',
            integrity_reader=lambda:{},input_loader=lambda:self.inputs,stress_cases=catalog, policy=LEGACY_POLICY)
        self.assertEqual(len(catalog),16);self.assertEqual(r.stress_summary,{'attempted':16,'correctly_blocked':16,'unexpectedly_accepted':0,'inconclusive':0})
        self.assertEqual(r.aggregate_validation['attempts'],0);self.assertEqual(r.attempts,())
        for x in r.stress_tests:self.assertTrue(x.blocked,x.case_id)
    def test_07_report_rebuild_is_identical_without_provider(self):
        r,p=self.run_values([synthetic_content()]);count=len(self.trace)
        r2,p2=rebuild(p.parents[1]);self.assertEqual(r,r2);self.assertEqual(p,p2);self.assertEqual(len(self.trace),count)
    def test_08_interrupt_after_six_keeps_six(self):
        r,p=self.run_values([synthetic_content() for _ in range(6)]+[KeyboardInterrupt()],attempts=10)
        self.assertEqual((r.attempt_count,r.started_attempt_count,r.requested_attempt_count),(6,7,10))
        self.assertEqual(r.status,'incomplete');self.assertEqual(len(self.trace),7)
        self.assertEqual(rebuild(p.parents[1])[0],r)
    def test_09_missing_completion_is_incomplete(self):
        r,p=self.run_values([synthetic_content()]);(p.parents[1]/'completion.json').unlink()
        again,_=rebuild(p.parents[1]);self.assertEqual(again.status,'incomplete');self.assertIsNone(again.baseline_integrity['after'])
    def test_10_tampered_raw_artifact_detected(self):
        r,p=self.run_values([synthetic_content()]);(p.parents[1]/'attempt-01'/'raw_candidate.json').write_text('{}')
        with self.assertRaises(ValueError):rebuild(p.parents[1])
    def test_11_tampered_attempt_summary_detected(self):
        r,p=self.run_values([synthetic_content()]);record=p.parents[1]/'attempt-01'/'attempt.json'
        d=read(record);d['accepted']=False;record.write_text(json.dumps(d))
        with self.assertRaises(ValueError):rebuild(p.parents[1])
    def test_12_multiple_runs_coexist(self):
        _,p1=self.run_values([synthetic_content()]);_,p2=self.run_values([synthetic_content()])
        self.assertNotEqual(p1.parents[1],p2.parents[1]);self.assertTrue(p1.exists())
    def test_13_attempt_bounds_before_provider(self):
        for n in (0,21,10000,True):
            with self.subTest(n=n),self.assertRaises(ValueError):self.run_values([],attempts=n)
        self.assertEqual(self.trace,[])
    def test_14_integrity_mismatch_stops_run(self):
        states=iter([{'freeze_inventory_matches':True},{'freeze_inventory_matches':False}])
        r,_=self.run_values([synthetic_content()],integrity_reader=lambda:next(states))
        self.assertEqual(r.status,'incomplete');self.assertFalse(r.baseline_integrity['unchanged'])
    def test_15_preexisting_integrity_mismatch_no_calls(self):
        with self.assertRaises(ValueError):self.run_values([],integrity_reader=lambda:{'freeze_inventory_matches':False})
        self.assertEqual(self.trace,[])
    def test_16_input_refresh_failure_stops_remaining_attempts(self):
        def fail():raise ValueError('revoked')
        r,_=self.run_values([synthetic_content()]*3,attempts=3,input_loader=fail)
        self.assertEqual(len(self.trace),0);self.assertEqual(r.attempt_count,0);self.assertEqual(r.status,'incomplete')
    def test_17_no_live_intent_cli_refuses(self):
        from academic_os.ai_qualification.__main__ import main
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            main(['qualify-ai-author','standard-deviation','--profile','standard-lesson','--role',ROLE])
    def test_18_cli_max_checked_before_inputs(self):
        from academic_os.ai_qualification.__main__ import main
        with patch('academic_os.ai_qualification.__main__.read_inputs',side_effect=AssertionError()),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            main(['qualify-ai-author','standard-deviation','--profile','standard-lesson','--role',ROLE,'--attempts','10000','--live'])
    def test_19_dry_run_no_provider_or_credentials(self):
        from academic_os.ai_qualification.__main__ import main
        output=io.StringIO()
        with patch.dict(os.environ,{'ACADEMIC_OS_AUTHOR_MODEL':'gpt-5.6-sol'}),patch('academic_os.ai_qualification.__main__.read_inputs',return_value=self.inputs),patch.object(OpenAICandidateAuthor,'from_environment',side_effect=AssertionError('No billing')),contextlib.redirect_stdout(output):
            result=main(['qualify-ai-author','standard-deviation','--profile','standard-lesson','--role',ROLE,'--dry-run'])
        self.assertEqual(result,0);d=json.loads(output.getvalue());self.assertEqual(d['attempt_count'],10);self.assertFalse(d['live_api_will_be_called'])
    def test_20_observer_keeps_normal_prompt_identical(self):
        response=SimpleNamespace(output_text=serial(synthetic_content()),output_parsed=object(),usage=None,status='completed',_request_id='req_test',model='test')
        client=Mock();client.responses.parse.return_value=response
        author=OpenAICandidateAuthor('test',client)
        from academic_os.ai_authoring.brief import compile_brief
        brief=compile_brief(self.inputs, policy=LEGACY_POLICY);author.author(brief);first=client.responses.parse.call_args.kwargs
        observed=ObservedAuthor(author);observed.author(brief);second=client.responses.parse.call_args.kwargs
        self.assertEqual(first,second);self.assertEqual(observed.last['call_count'],1);self.assertEqual(observed.last['provider_request_id'],'req_test')
    def test_21_live_wrong_math_preserves_original_and_blocks(self):
        response=SimpleNamespace(output_text=serial(synthetic_content()),output_parsed=object(),usage=None,status='completed')
        client=Mock();client.responses.parse.return_value=response
        provider=OpenAICandidateAuthor('test',client)
        r,p=execute(self.inputs,lambda c:ObservedAuthor(provider,c['case_id']),attempts=1,output_dir=self.tmp.name,
            experiment_type='live_adversarial',provider='mock_openai',model='test',integrity_reader=lambda:{},input_loader=lambda:self.inputs,
            stress_cases=[{'case_id':'wrong_math','expected_guardrail':'solution_valid'}], policy=LEGACY_POLICY)
        self.assertEqual(client.responses.parse.call_count,1);self.assertTrue(r.stress_tests[0].blocked)
        folder=p.parents[1]/'attempt-01';raw=read(folder/'raw_candidate.json')['raw_response']
        self.assertEqual(json.loads(raw)['proposed_solution']['display_answer'],'2.00')
        self.assertIn('live_adversarial',client.responses.parse.call_args.kwargs['input'][1]['content'])
    def test_22_live_refusal_not_guardrail_success(self):
        client=Mock();client.responses.parse.return_value=SimpleNamespace(output_text='',output_parsed=None,usage=None,status='completed')
        r,_=execute(self.inputs,lambda c:ObservedAuthor(OpenAICandidateAuthor('test',client),c['case_id']),attempts=1,output_dir=self.tmp.name,
            experiment_type='live_adversarial',provider='mock_openai',model='test',integrity_reader=lambda:{},input_loader=lambda:self.inputs,
            stress_cases=[{'case_id':'exam_claim','expected_guardrail':'boundary_valid'}], policy=LEGACY_POLICY)
        self.assertEqual(r.stress_summary['correctly_blocked'],0);self.assertEqual(r.stress_summary['inconclusive'],1)
    def test_23_operational_error_categories(self):
        for name,code in [('AuthenticationError','authentication_or_permission_failure'),('RateLimitError','rate_limit'),
            ('APITimeoutError','provider_timeout'),('APIConnectionError','network_error'),('ValidationError','structured_output_transport_failure')]:
            self.assertEqual(operational_code(type(name,(Exception,),{})('Bearer never-persist')),code)
    def test_24_secret_raw_is_not_saved(self):
        d=synthetic_content();d['question_template']='Bearer synthetic-secret-token'
        r,p=self.run_values([d])
        for f in p.parents[1].rglob('*.json'):self.assertNotIn('synthetic-secret-token',f.read_text(encoding='utf-8'))
        self.assertFalse(r.attempts[0].accepted)
    def test_25_no_changes_to_trusted_state(self):self.assertEqual(state(),self.before)
    def test_26_no_report_rebuild_input_reads(self):
        _,p=self.run_values([synthetic_content()])
        with patch('academic_os.ai_authoring.service.read_inputs',side_effect=AssertionError('No state reads')),patch.object(OpenAICandidateAuthor,'from_environment',side_effect=AssertionError('No model')):
            rebuild(p.parents[1])
    def test_27_provider_failure_no_second_call(self):
        response=ProviderReply('',Metadata(provider='test',model='test',latency_seconds=1),'provider_failed_no_retry')
        r,_=self.run_values([response]);self.assertEqual(len(self.trace),1);self.assertEqual(r.operational_outcomes,{'provider_failure':1})
        self.assertEqual(r.rejection_summary,{})
    def test_28_unknown_fields_report_schema_rejects(self):
        from academic_os.ai_qualification.models import QualificationReport
        r,_=self.run_values([synthetic_content()]);d=r.model_dump();d['qualified']=True
        with self.assertRaises(ValueError):QualificationReport.model_validate(d)
    def test_29_changed_inputs_not_counted_as_model_rejection(self):
        from dataclasses import replace
        changed=replace(self.inputs,package=self.inputs.package.model_copy(update={'content_boundaries':('changed',)}))
        r,_=self.run_values([synthetic_content()]*3,attempts=3,input_loader=lambda:changed)
        self.assertEqual(len(self.trace),0);self.assertEqual(r.attempt_count,0)
        self.assertEqual(r.status,'incomplete');self.assertEqual(r.rejection_summary,{})


class QualificationConsoleTests(unittest.TestCase):
    def test_gbk_dry_run_json_preserves_unicode(self):
        from academic_os.ai_authoring.brief import compile_brief
        from academic_os.ai_qualification.__main__ import main
        brief=compile_brief(read_inputs('var/p0_q2.sqlite3'), policy=LEGACY_POLICY)
        buffer=io.BytesIO();console=io.TextIOWrapper(buffer,encoding='gbk',write_through=True)
        with patch.dict(os.environ,{'ACADEMIC_OS_AUTHOR_MODEL':'gpt-5.6-sol'}),patch('academic_os.ai_qualification.__main__.read_inputs',return_value=object()),patch('academic_os.ai_qualification.__main__.compile_brief',return_value=brief),contextlib.redirect_stdout(console):
            code=main(['qualify-ai-author','standard-deviation','--profile','standard-lesson','--role',ROLE,'--dry-run'])
        data=json.loads(buffer.getvalue().decode('gbk'));console.detach()
        self.assertEqual(code,0);self.assertEqual(data['brief'],brief.model_dump(mode='json'))
        self.assertFalse(data['live_api_will_be_called'])


if __name__=='__main__':unittest.main()
