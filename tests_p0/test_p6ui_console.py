"""Real service/API acceptance; all outbound sockets and model construction denied."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]/'tmp/p6ui-deps'))
import time
import socket
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from console_api.app import create_app, ORIGINS
from console_api import adapter as a

class ConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=a.sha(a.DATABASE)
        connect=socket.socket.connect
        def local_only(sock,address):
            if not isinstance(address,tuple) or address[0] not in ('127.0.0.1','::1'):raise AssertionError('Outbound network forbidden')
            return connect(sock,address)
        cls.network=patch('socket.socket.connect',new=local_only);cls.network.start()
        cls.provider=patch('academic_os.ai_authoring.provider.OpenAICandidateAuthor.from_environment',side_effect=AssertionError('Provider forbidden'));cls.provider.start()
        cls.client=TestClient(create_app());cls.client.__enter__()
        cls.headers={'Origin':ORIGINS[0],'X-Console-Token':cls.client.get('/api/session').json()['token']}
        response=cls.client.post('/api/runs/assemble-standard-lesson',headers=cls.headers,json={})
        assert response.status_code==202,response.text
        cls.initial=response.json();cls.id=cls.initial['id']
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            cls.run_record=cls.client.get('/api/runs/'+cls.id).json()
            if cls.run_record['status'] not in ('queued','running'):break
            time.sleep(.05)
        cls.lesson=cls.client.get(f'/api/runs/{cls.id}/lesson').json()
    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None,None,None);cls.provider.stop();cls.network.stop()
        assert a.sha(a.DATABASE)==cls.before,'Trusted database mutated'
    def test_health_database(self):
        d=self.client.get('/api/health').json();self.assertEqual(d['database'],str(a.DATABASE));self.assertFalse(d['model_calls_enabled'])
    def test_sources_topic(self):
        self.assertEqual(len(self.client.get('/api/sources').json()),2)
        d=self.client.get('/api/topics/standard-deviation').json()
        self.assertEqual(d['source']['snapshots'],a.SNAPSHOTS);self.assertFalse(d['trust']['curriculum_association_confirmed'])
    def test_curriculum(self):
        d=self.client.get('/api/curriculum/topic2').json()
        self.assertEqual([x['total'] for x in d],[25,16]);self.assertEqual(sum(x['mapped'] for x in d),13)
        for t in d:self.assertEqual(t['structure']['status'],'PASS');self.assertTrue(t['warnings']);self.assertEqual(len(t['subtopics']),8)
    def test_real_assembly_and_order(self):
        self.assertEqual(self.initial['status'],'queued');self.assertEqual(self.run_record['status'],'succeeded',self.run_record)
        self.assertEqual([x['slot'] for x in self.lesson['roles']],[f'SL-{i:02}' for i in range(1,16)])
        self.assertTrue(all(x['blocks'] for x in self.lesson['roles']))
    def test_validation(self):
        e={x['id']:x for x in self.run_record['stages']}
        self.assertEqual(e['p4b']['status'],'PASS');self.assertEqual(e['p5c']['status'],'PASS')
        self.assertTrue(e['p5c']['details']['report']['renderer_readiness']['ready_for_rendering'])
        self.assertFalse(e['curriculum_association_confirmed']['details']['value']);self.assertEqual(e['approval']['status'],'NOT_EVALUATED')
    def test_question_solution_separation(self):
        q=self.client.get(f'/api/runs/{self.id}/questions').json();s=self.client.get(f'/api/runs/{self.id}/solutions').json()
        self.assertGreater(len(q),5);self.assertEqual({x['solution_id'] for x in q},{x['id'] for x in s})
        for item in q:self.assertNotIn('answer',item);self.assertEqual(item['visibility'],'student')
        for item in s:self.assertEqual(item['visibility'],'teacher-only')
        self.assertNotIn('display_answer',str(self.lesson))
    def test_artifacts(self):
        items=self.client.get('/api/artifacts').json();ppt=next(x for x in items if x['title'].endswith('.pptx'))
        d=self.client.get('/api/artifacts/'+ppt['id']);self.assertEqual(d.status_code,200);self.assertTrue(d.content.startswith(b'PK'))
    def test_path_traversal(self):
        for value in ('..%2F..%2F.env','D:%5Csecrets','not-registered','%252e%252e%252f.env'):
            self.assertEqual(self.client.get('/api/artifacts/'+value).status_code,404)
        with self.assertRaises(ValueError):a.Registry().add(a.ROOT/'requirements-p6ui.txt','bad','bad')
    def test_unsupported_topic(self):
        r=self.client.post('/api/runs/assemble-standard-lesson',headers=self.headers,json={'topic':'topic2'})
        self.assertEqual(r.status_code,422)
    def test_request_paths_and_operations_not_supported(self):
        self.assertEqual(self.client.post('/api/runs/assemble-standard-lesson',headers=self.headers,json={'output_path':'../evil'}).status_code,422)
        self.assertEqual(self.client.post('/api/execute',headers=self.headers,json={'cmd':'anything'}).status_code,404)
    def test_origin_session_host(self):
        self.assertEqual(self.client.get('/api/session',headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.get('/api/health',headers={'Host':'evil.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/runs/assemble-standard-lesson',json={}).status_code,403)
        self.assertEqual(self.client.post('/api/runs/assemble-standard-lesson',headers=self.headers,content='x'*3000).status_code,413)
    def test_history(self):
        d=self.client.get('/api/history').json();self.assertEqual({x['milestone'] for x in d},{'P6A.5','P6A.6','P6A.7b'})
        controlled=[e for h in d if h['milestone']=='P6A.6' for e in h['evidence'] if e['id']=='controlled_input_binding_valid']
        self.assertTrue(all(e['status']=='PASS' for e in controlled))
        self.assertTrue(any(not x['accepted'] for x in d));self.assertTrue(all(x['label']=='HISTORICAL EVIDENCE' for x in d))
    def test_failed_service_never_success(self):
        with patch('console_api.adapter.assembly',side_effect=ValueError('Secret test string')):
            r=self.client.post('/api/runs/assemble-standard-lesson',headers=self.headers,json={}).json()
            for _ in range(200):
                d=self.client.get('/api/runs/'+r['id']).json()
                if d['status']=='failed':break
                time.sleep(.01)
        self.assertEqual(d['status'],'failed');self.assertNotIn('Secret test string',str(d))
        self.assertEqual(self.client.get(f"/api/runs/{r['id']}/lesson").status_code,409)
    def test_artifact_mutation_rejected(self):
        p=a.ROOT/'output/p6ui2/registry-test.json';p.write_text('{}')
        reg=a.Registry();identity=reg.add(p,'test','test',False);p.write_text('{"changed":true}')
        with self.assertRaises(ValueError):reg.get(identity)
        p.unlink()

if __name__=='__main__':unittest.main()

