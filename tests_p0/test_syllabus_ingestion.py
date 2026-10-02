"""Offline ingestion contracts and real API, with external network denied."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]/'tmp/p6ui-deps'))
import importlib
import os
import json
import socket
import tempfile
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from console_api.app import create_app,ORIGINS
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.service import IngestionService,Storage
from academic_os.curriculum_ingestion.models import ExtractRequest,ParseRequest
from academic_os.curriculum_ingestion.validation import validate_curriculum

ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/'international-gcse-in-mathematics-spec-a.pdf'
def wait(service,r):
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        result=service.get(r.run_id)
        if result.status not in ('queued','running'):return result
        time.sleep(.01)
    raise AssertionError('Ingestion timed out')

class IngestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'tmp');cls.root=Path(cls.temp.name);cls.s=IngestionService(cls.root)
        cls.bytes=PDF.read_bytes();cls.db=core.digest((ROOT/'var/p0_q2.sqlite3').read_bytes())
        cls.net=patch('socket.socket.connect',side_effect=AssertionError('No network'));cls.net.start()
        cls.doc=cls.s.upload(cls.bytes,'syllabus.pdf','application/pdf');cls.ex={};cls.parsed={}
        for tier,(start,end) in core.RANGES.items():
            ex=wait(cls.s,cls.s.submit_extract(cls.doc.document_id,ExtractRequest(tier=tier,start_page=start,end_page=end)));assert ex.status=='succeeded';cls.ex[tier]=ex
            r=wait(cls.s,cls.s.submit_parse(cls.doc.document_id,ParseRequest(extraction_run_id=ex.run_id,mode='preserved')));assert r.status=='succeeded',r;cls.parsed[tier]=r
    @classmethod
    def tearDownClass(cls):
        cls.s.close();cls.net.stop();cls.temp.cleanup();assert core.digest((ROOT/'var/p0_q2.sqlite3').read_bytes())==cls.db
    def test_upload_identity(self):
        self.assertEqual(self.doc.sha256,core.KNOWN_SHA);self.assertEqual(self.doc.byte_size,len(self.bytes));self.assertEqual(self.doc.page_count,70)
        again=self.s.upload(self.bytes,'renamed.pdf','application/pdf');self.assertNotEqual(again.document_id,self.doc.document_id);self.assertEqual(again.sha256,self.doc.sha256)
    def test_invalid_pdf(self):
        for data in (b'',b'not PDF',b'%PDF-1.7\nnot a document'):
            with self.assertRaisesRegex(core.IngestionError,'PDF'):self.s.upload(data,'x.pdf','application/pdf')
    def test_unsupported_type(self):
        for name,mime in [('x.docx','application/pdf'),('x.pdf','text/plain')]:
            with self.assertRaises(core.IngestionError) as c:self.s.upload(self.bytes,name,mime)
            self.assertEqual(c.exception.code,'UNSUPPORTED_FILE_TYPE')
    def test_size_limit(self):
        with self.assertRaises(core.IngestionError) as c:self.s.upload(b'x'*(core.MAX_UPLOAD+1),'x.pdf','application/pdf')
        self.assertEqual(c.exception.code,'UPLOAD_TOO_LARGE')
    def test_path_filename_rejected(self):
        for name in ('../x.pdf','..\\x.pdf','C:\\x.pdf','x\x00.pdf','x:ads.pdf'):
            with self.assertRaises(core.IngestionError):self.s.upload(self.bytes,name,'application/pdf')
    def test_extraction_actual_text(self):
        e=self.s.output(self.ex['foundation'].run_id,'extraction');self.assertEqual([x['page_number'] for x in e['pages']],[21,22]);self.assertIn('Use of',e['text']);self.assertEqual(e['source_sha256'],self.doc.sha256)
    def test_page_range_rejected(self):
        for start,end in ((0,1),(2,1),(1,71),(1,11)):
            with self.assertRaises(core.IngestionError):core.extract_pages(PDF,start,end)
    def test_empty_text_no_ocr(self):
        import pymupdf
        with pymupdf.open() as d:d.new_page();data=d.tobytes()
        p=self.root/'blank.pdf';p.write_bytes(data);r=core.extract_pages(p,1,1)
        self.assertEqual(r.pages[0].text,'');self.assertEqual(r.warnings[0].code,'TEXT_NOT_AVAILABLE')
    def test_profile_gate_no_model(self):
        d=self.s.upload(self.bytes+b'\n% alternate bytes','different.pdf','application/pdf');self.assertEqual(d.status,'UNSUPPORTED_CURRICULUM_PROFILE')
        r=wait(self.s,self.s.submit_extract(d.document_id,ExtractRequest(tier='foundation',start_page=21,end_page=22)))
        self.assertEqual(r.status,'blocked');self.assertEqual(r.errors[0].code,'UNSUPPORTED_CURRICULUM_PROFILE');self.assertEqual(r.stages['parsing'],'NOT_EVALUATED')
    def test_tiers_and_exact_preserved_wording(self):
        for tier,count in [('foundation',25),('higher',16)]:
            r=self.parsed[tier];v=self.s.output(r.run_id,'validation');self.assertTrue(v['structure_valid']);self.assertEqual(v['objective_count'],count);self.assertEqual(v['subtopic_count'],8)
            self.assertEqual(self.s.output(r.run_id,'parsed'),json.loads((ROOT/f'output/topic2_{tier}_parsed.json').read_text(encoding='utf-8')))
    def test_source_id_semantics(self):
        tree=self.s.tree(self.parsed['higher'].run_id);self.assertEqual(tree.topics[0].subtopics[0].objectives[0].source_id,'EDX-4MA1-H-2.1-A')
    def test_warning_preservation(self):
        t=self.s.tree(self.parsed['foundation'].run_id)
        self.assertTrue(any(w.code=='SYMBOL_EXTRACTION_WARNING' for w in t.warnings));self.assertTrue(any(w.code=='PARSER_WARNING' for w in t.warnings));self.assertFalse(t.validation.official_text_confirmed)
    def test_capability_source_binding(self):
        c=self.s.capabilities(self.parsed['foundation'].run_id,'2.1','A');self.assertTrue(c.CURRICULUM_BROWSABLE)
        self.assertFalse(c.LESSON_GENERATION_SUPPORTED);self.assertFalse(c.QUESTION_GENERATION_SUPPORTED);self.assertFalse(c.PRESENTATION_SUPPORTED)
        self.assertEqual(c.target.source_sha256,self.doc.sha256);self.assertEqual(c.target.source_ids,['EDX-4MA1-F-2.1-A']);self.assertEqual(c,self.s.capabilities(self.parsed['foundation'].run_id,'2.1','A'))
        self.assertNotEqual(c.target.target_id,self.s.capabilities(self.parsed['foundation'].run_id,'2.2').target.target_id)
    def test_invalid_selection(self):
        for sub,obj in [('9.9',None),('2.1','Z'),(None,'A')]:
            with self.assertRaises(core.IngestionError):self.s.capabilities(self.parsed['foundation'].run_id,sub,obj)
    def test_model_missing_configuration(self):
        with patch.dict('os.environ',{},clear=True),patch('dotenv.load_dotenv'):
            r=wait(self.s,self.s.submit_parse(self.doc.document_id,ParseRequest(extraction_run_id=self.ex['foundation'].run_id,mode='live',confirm_model_call=True)))
        self.assertEqual(r.status,'blocked');self.assertEqual(r.errors[0].code,'MODEL_CONFIGURATION_MISSING');self.assertEqual(r.model_calls,0);self.assertEqual(r.stages['validation'],'NOT_EVALUATED')
    def test_explicit_live_consent(self):
        with self.assertRaises(core.IngestionError):self.s.submit_parse(self.doc.document_id,ParseRequest(extraction_run_id=self.ex['foundation'].run_id,mode='live'))
    def test_provider_error_sanitized(self):
        with patch('openai.OpenAI',side_effect=RuntimeError('sk-test-secret-do-not-leak')):
            with self.assertRaises(core.IngestionError) as c:core.live_parse('text','foundation',{'model':'configured-model'})
        self.assertEqual(c.exception.code,'PARSER_FAILED');self.assertNotIn('sk-test',str(c.exception))
    def test_live_adapter_fixture_and_validation_failure(self):
        data=json.loads((ROOT/'output/topic2_foundation_parsed.json').read_text(encoding="utf-8"));data['subtopics'].pop()
        with patch.object(core,'model_configuration',return_value={'model':'offline-test-double'}),patch.object(core,'live_parse',return_value=data) as provider:
            r=wait(self.s,self.s.submit_parse(self.doc.document_id,ParseRequest(extraction_run_id=self.ex['foundation'].run_id,mode='live',confirm_model_call=True)))
            provider.assert_called_once()
        self.assertEqual(r.status,'failed');self.assertEqual(r.errors[0].code,'CURRICULUM_VALIDATION_FAILED');self.assertFalse(self.s.output(r.run_id,'validation')['structure_valid'])
        with self.assertRaises(core.IngestionError):self.s.tree(r.run_id)
    def test_structure_is_not_official_approval(self):
        data=json.loads((ROOT/'output/topic2_foundation_parsed.json').read_text(encoding="utf-8"));data['subtopics'][0]['objectives'][0]['official_text']='Changed wording not detected by structure alone'
        v=validate_curriculum(data,'foundation');self.assertTrue(v['structure_valid']);self.assertFalse(v['official_text_confirmed'])
    def test_parse_run_provider_failure_sanitized(self):
        with patch.object(core,'model_configuration',return_value={'model':'offline-test-double'}),patch('openai.OpenAI',side_effect=RuntimeError('sk-test-secret-never-return')):
            r=wait(self.s,self.s.submit_parse(self.doc.document_id,ParseRequest(extraction_run_id=self.ex['foundation'].run_id,mode='live',confirm_model_call=True)))
        self.assertEqual(r.errors[0].code,'PARSER_FAILED');self.assertNotIn('sk-test',r.model_dump_json());self.assertEqual(r.stages['validation'],'NOT_EVALUATED')
    def test_mutated_parse_rejected(self):
        r=wait(self.s,self.s.submit_parse(self.doc.document_id,ParseRequest(extraction_run_id=self.ex['foundation'].run_id,mode='preserved')))
        p=self.root/'runs'/r.run_id/'parsed.json';p.write_text('{}')
        with self.assertRaises(core.IngestionError) as c:self.s.capabilities(r.run_id)
        self.assertEqual(c.exception.code,'EVIDENCE_CHANGED')
    def test_chunked_upload_limit(self):
        # Service boundary independently enforces the same limit as HTTP streaming.
        with patch.object(core,'inspect_pdf',side_effect=AssertionError('Must reject before PDF parsing')):
            with self.assertRaises(core.IngestionError) as c:self.s.upload(b'x'*(core.MAX_UPLOAD+1),'large.pdf','application/pdf')
        self.assertEqual(c.exception.code,'UPLOAD_TOO_LARGE')
    def test_cross_document_extraction_rejected(self):
        other=self.s.upload(self.bytes,'other.pdf','application/pdf')
        with self.assertRaises(core.IngestionError):self.s.submit_parse(other.document_id,ParseRequest(extraction_run_id=self.ex['foundation'].run_id,mode='preserved'))
    def test_range_tier_mismatch(self):
        ex=wait(self.s,self.s.submit_extract(self.doc.document_id,ExtractRequest(tier='higher',start_page=21,end_page=22)))
        r=wait(self.s,self.s.submit_parse(self.doc.document_id,ParseRequest(extraction_run_id=ex.run_id,mode='preserved')))
        self.assertEqual(r.status,'blocked');self.assertEqual(r.model_calls,0)
    def test_immutable_terminal_evidence(self):
        r=self.parsed['foundation'];p=self.root/'runs'/r.run_id/'result.json';before=p.read_bytes()
        self.s.tree(r.run_id);self.s.capabilities(r.run_id);self.assertEqual(before,p.read_bytes())
        with self.assertRaises(FileExistsError):self.s.storage.write(('runs',r.run_id,'result.json'),b'{}')
    def test_restart_reads_completed_results(self):
        s=IngestionService(self.root)
        try:self.assertEqual(s.tree(self.parsed['foundation'].run_id).source_sha256,self.doc.sha256)
        finally:s.close()
    def test_path_escape(self):
        with self.assertRaises(core.IngestionError):self.s.storage.safe('..','escape')
        with self.assertRaises(core.IngestionError):self.s.document('../escape')
    def test_symlink_rejected(self):
        link=self.root/'escape';target=self.root/'target';target.mkdir()
        try:link.symlink_to(target,target_is_directory=True)
        except OSError:
            import subprocess
            result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
        try:
            with self.assertRaises(core.IngestionError):self.s.storage.safe('escape','x')
        finally:link.rmdir() if link.is_junction() else link.unlink()
    def test_upload_extract_does_not_construct_provider(self):
        with patch('openai.OpenAI',side_effect=AssertionError('No model')):
            d=self.s.upload(self.bytes,'again.pdf','application/pdf');self.s.document(d.document_id)
            r=wait(self.s,self.s.submit_extract(d.document_id,ExtractRequest(tier='foundation',start_page=21,end_page=22)))
        self.assertEqual(r.model_calls,0);self.assertEqual(r.status,'succeeded')
    def test_cli_imports_are_side_effect_free(self):
        with patch('openai.OpenAI',side_effect=AssertionError('No model')),patch.object(Path,'write_text',side_effect=AssertionError('No writes')):
            for module in ['extract_syllabus','parse_curriculum','validate_curriculum','add_source_ids']:importlib.import_module(module)

class IngestionAPITests(unittest.TestCase):
    def test_real_upload_to_tree_offline(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory,TestClient(create_app(Path(directory))) as client,patch('openai.OpenAI',side_effect=AssertionError('No provider')):
            headers={'Origin':ORIGINS[0],'X-Console-Token':client.get('/api/session').json()['token'],'Content-Type':'application/pdf'}
            response=client.post('/api/syllabi?filename=known.pdf',headers=headers,content=PDF.read_bytes());self.assertEqual(response.status_code,201,response.text);doc=response.json()
            self.assertEqual(client.get('/api/syllabi/'+doc['document_id']).json()['sha256'],core.KNOWN_SHA)
            headers['Content-Type']='application/json'
            def finish(r):
                self.assertEqual(r.status_code,202,r.text);identity=r.json()['run_id']
                for _ in range(300):
                    result=client.get('/api/curriculum-runs/'+identity).json()
                    if result['status'] not in ('queued','running'):return result
                    time.sleep(.01)
                self.fail('API timeout')
            ex=finish(client.post('/api/syllabi/'+doc['document_id']+'/extract',headers=headers,json={'tier':'foundation','start_page':21,'end_page':22}));self.assertEqual(ex['status'],'succeeded')
            run=finish(client.post('/api/syllabi/'+doc['document_id']+'/parse',headers=headers,json={'extraction_run_id':ex['run_id'],'mode':'preserved'}));self.assertEqual(run['status'],'succeeded');self.assertEqual(run['model_calls'],0)
            tree=client.get('/api/curriculum-runs/'+run['run_id']+'/tree').json();self.assertEqual(tree['validation']['objective_count'],25)
            cap=client.get('/api/curriculum-runs/'+run['run_id']+'/capabilities?subtopic=2.1').json();self.assertTrue(cap['CURRICULUM_BROWSABLE']);self.assertFalse(cap['LESSON_GENERATION_SUPPORTED'])
            self.assertEqual(len(client.get('/api/syllabi/'+doc['document_id']+'/runs').json()),2)
            evidence={'document':doc,'extraction_run':ex,'parse_run':run,'tree':tree,'capability':cap,'model_api_calls':0}
            # Dedicated evidence, never overwrite P6UI.2 artifacts.
            if os.environ.get('P6UI_INGESTION_EVIDENCE'):
                out=ROOT/os.environ['P6UI_INGESTION_EVIDENCE']
                with out.open('x',encoding='utf-8') as f:json.dump(evidence,f,indent=2)
    def test_http_upload_guards(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory,TestClient(create_app(Path(directory))) as c:
            h={'Origin':ORIGINS[0],'X-Console-Token':c.get('/api/session').json()['token'],'Content-Type':'application/pdf'}
            self.assertEqual(c.post('/api/syllabi?filename=x.pdf',content=b'%PDF-').status_code,403)
            self.assertEqual(c.post('/api/syllabi?filename=../x.pdf',headers=h,content=PDF.read_bytes()).json()['error']['code'],'PATH_REJECTED')
            self.assertEqual(c.post('/api/syllabi?filename=x.pdf',headers={**h,'Content-Type':'text/plain'},content=b'x').status_code,415)
            self.assertEqual(c.post('/api/syllabi?filename=x.pdf',headers={**h,'Content-Length':str(core.MAX_UPLOAD+1)},content=b'x').status_code,413)
            self.assertEqual(c.get('/api/syllabi/not-an-id').status_code,404)

if __name__=='__main__':unittest.main()
