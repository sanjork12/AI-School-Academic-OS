"""P6A.2 offline preflight and mocked pipeline tests. No external calls."""
from academic_os.ai_authoring.provenance import LEGACY_POLICY
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from academic_os.ai_authoring.brief import ROLE,compile_brief,digest
from academic_os.ai_authoring.provider import configured_model,OpenAICandidateAuthor
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_qualification.__main__ import main
from academic_os.ai_qualification.runner import execute
from academic_os.ai_qualification.reference_baseline import ACTIVE_REFERENCE_BASELINE
from academic_os.ai_authoring.provenance import POLICY
from academic_os.ai_qualification.stress import synthetic_content
from tests_p0.test_ai_qualification import SequenceAuthor


class PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.inputs=read_inputs('var/p0_q2.sqlite3')

    def cli(self,extra=(),environment=None,inputs_error=None,engineering=None):
        buffer=io.StringIO()
        env={'ACADEMIC_OS_AUTHOR_MODEL':'gpt-5.6-sol'} if environment is None else environment
        state=engineering or dict(freeze_inventory_matches=True,engineering_baseline=dict(valid=True,reference_version=ACTIVE_REFERENCE_BASELINE))
        with patch.dict(os.environ,env),patch('dotenv.load_dotenv'), \
             patch('academic_os.ai_qualification.__main__.read_inputs',return_value=self.inputs,side_effect=inputs_error), \
             patch('academic_os.ai_qualification.__main__.capture',return_value=state), \
             patch.object(OpenAICandidateAuthor,'from_environment',side_effect=AssertionError('Provider forbidden')) as factory, \
             contextlib.redirect_stdout(buffer):
            code=main(['qualify-ai-author','standard-deviation','--profile','standard-lesson','--role',ROLE,'--dry-run',*extra])
        factory.assert_not_called()
        return code,buffer.getvalue()

    def test_preflight_contract_and_model(self):
        code,text=self.cli();self.assertEqual(code,0);d=json.loads(text)
        self.assertEqual(d['model'],'gpt-5.6-sol');self.assertEqual(d['provider'],'openai')
        self.assertEqual(d['candidate_contract_version'],'ai-author-candidate/2')
        self.assertEqual(d['engineering_baseline_version'],ACTIVE_REFERENCE_BASELINE)
        self.assertEqual(d['acceptance_policy'],POLICY)
        self.assertTrue(d['provenance_verification_required'])
        self.assertEqual(d['brief_hash'],digest(compile_brief(self.inputs,policy=POLICY)))
        self.assertEqual(d['attempt_count'],10);self.assertEqual(d['stress_cases'],[])
        self.assertFalse(d['live_api_will_be_called']);self.assertIsNone(d['model_qualified'])
        self.assertFalse(d['expression_semantics_verified'])

    def test_preflight_deterministic(self):self.assertEqual(self.cli(),self.cli())
    def test_missing_model_blocks(self):self.assertEqual(self.cli(environment={'ACADEMIC_OS_AUTHOR_MODEL':''})[0],2)
    def test_different_model_blocks(self):self.assertEqual(self.cli(environment={'ACADEMIC_OS_AUTHOR_MODEL':'another-model'})[0],2)
    def test_secret_like_model_not_exposed(self):
        code,text=self.cli(environment={'ACADEMIC_OS_AUTHOR_MODEL':'Bearer hidden-key'})
        self.assertEqual(code,2);self.assertNotIn('hidden-key',text)

    def test_old_active_baseline_blocks(self):
        self.assertEqual(self.cli(engineering=dict(freeze_inventory_matches=True,engineering_baseline=dict(valid=True,reference_version='v1.2')))[0],2)

    def test_baseline_mismatch_blocks(self):
        self.assertEqual(self.cli(engineering=dict(freeze_inventory_matches=False))[0],2)

    def test_snapshot_source_governance_and_unresolved_block(self):
        for reason in ('snapshot invalid','source verification failed','governance invalidated','unresolved blocking input'):
            with self.subTest(reason=reason):self.assertEqual(self.cli(inputs_error=ValueError(reason))[0],2)

    def test_unready_p5c_blocks(self):
        with patch('academic_os.ai_authoring.brief.p5c') as gate:
            gate.return_value.renderer_readiness.ready_for_rendering=False
            self.assertEqual(self.cli()[0],2)

    def test_no_live_intent_refused(self):
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            main(['qualify-ai-author','standard-deviation','--profile','standard-lesson','--role',ROLE])

    def test_dotenv_resolution_shared_without_sdk(self):
        with patch.dict(os.environ,{'ACADEMIC_OS_AUTHOR_MODEL':'gpt-5.6-sol'}),patch('dotenv.load_dotenv') as load,patch.dict('sys.modules',{'openai':Mock(OpenAI=Mock(side_effect=AssertionError('No SDK client')))}):
            self.assertEqual(configured_model(),'gpt-5.6-sol');load.assert_called_once_with(override=False)

    def test_operator_output_location(self):
        _,text=self.cli(['--output-dir','output/p6a2_live_qualification'])
        self.assertEqual(Path(json.loads(text)['output_location']),Path('output/p6a2_live_qualification'))

    def run_values(self,values,loader=None):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        trace=[];values=iter(values)
        r,path=execute(self.inputs,lambda _:SequenceAuthor(next(values),trace),attempts=2,output_dir=tmp.name,
            experiment_type='offline_synthetic',provider='synthetic_test',model='synthetic-no-model',
            integrity_reader=lambda:{},input_loader=loader or (lambda:self.inputs), policy=LEGACY_POLICY)
        return r,path,trace

    def test_fresh_read_before_and_after_each_call(self):
        events=[]
        def load():events.append('read');return self.inputs
        values=[synthetic_content(),synthetic_content()]
        with patch.object(SequenceAuthor,'author',autospec=True) as author:
            from academic_os.ai_authoring.provider import ProviderReply
            from academic_os.ai_authoring.models import Metadata
            from academic_os.ai_authoring.brief import serial
            def reply(self_,brief):events.append('provider');return ProviderReply(serial(self_.value),Metadata(provider='test',model='test',latency_seconds=0))
            author.side_effect=reply
            r,_,_=self.run_values(values,load)
        self.assertEqual(events,['read','provider','read','read','provider','read'])
        self.assertEqual(r.aggregate_validation['accepted_count'],2)

    def test_revocation_before_next_attempt_no_call(self):
        count=0
        def load():
            nonlocal count
            count+=1
            if count==3:raise ValueError('revoked between attempts')
            return self.inputs
        r,_,trace=self.run_values([synthetic_content()]*2,load)
        self.assertEqual(len(trace),1);self.assertEqual(r.attempt_count,1);self.assertEqual(r.status,'incomplete')

    def test_invalid_first_read_no_calls(self):
        def fail():raise ValueError('source changed')
        r,_,trace=self.run_values([synthetic_content()]*2,fail)
        self.assertEqual(trace,[]);self.assertEqual(r.attempt_count,0)

    def test_rejection_does_not_stop_next_attempt_and_raw_unchanged(self):
        c=synthetic_content();c['proposed_solution']['first_term']['value']='55/5 = 11'
        r,path,trace=self.run_values([c,synthetic_content()])
        self.assertEqual(len(trace),2);self.assertEqual(r.aggregate_validation['accepted_count'],1)
        self.assertFalse(r.attempts[0].numeric_encoding_valid);self.assertIsNone(r.attempts[0].math_valid)
        raw=json.loads((path.parents[1]/'attempt-01/raw_candidate.json').read_text())['raw_response']
        self.assertEqual(json.loads(raw),c)

    def test_provider_failure_not_quality_failure(self):
        r,_,trace=self.run_values([RuntimeError('network'),synthetic_content()])
        self.assertEqual(len(trace),2);self.assertEqual(r.operational_outcomes['provider_failure'],1)
        self.assertEqual(r.aggregate_validation['provider_failures'],1)
        self.assertEqual(r.aggregate_validation['numeric_encoding_valid_evaluated_count'],1)
        self.assertEqual(r.rejection_summary,{})

    def test_mock_transport_calls_and_completion_counts(self):
        from types import SimpleNamespace
        from academic_os.ai_authoring.brief import serial
        from academic_os.ai_qualification.observer import ObservedAuthor
        client=Mock()
        client.responses.parse.side_effect=[SimpleNamespace(output_text=serial(synthetic_content()),
            output_parsed=object(),usage=None,status='completed'),RuntimeError('synthetic transport failure')]
        with tempfile.TemporaryDirectory() as out:
            r,_=execute(self.inputs,lambda _:ObservedAuthor(OpenAICandidateAuthor('gpt-5.6-sol',client)),
                attempts=2,output_dir=out,experiment_type='live_normal',provider='mock_openai',model='gpt-5.6-sol',
                integrity_reader=lambda:{},input_loader=lambda:self.inputs, policy=LEGACY_POLICY)
        self.assertEqual(client.responses.parse.call_count,2)
        self.assertEqual(r.aggregate_validation['provider_calls_completed'],1)
        self.assertEqual(r.aggregate_validation['provider_failures'],1)
        self.assertEqual(r.aggregate_validation['accepted_count'],1)
        self.assertEqual([a.provider_calls for a in r.attempts],[1,1])


if __name__=='__main__':unittest.main()
