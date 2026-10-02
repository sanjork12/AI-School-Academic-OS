"""Actual PDF evidence, deterministic package replay and adversarial binding checks."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1] / 'tmp/p6ui-deps'))
import copy
import json
import socket
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.models import ExtractRequest, ParseRequest
from academic_os.curriculum_ingestion.service import IngestionService, serial
from academic_os.curriculum_capability.service import AcademicCapabilityService, PROMOTED
from tests_p0.test_syllabus_ingestion import wait, ROOT, PDF


class CapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        cls.s = IngestionService(Path(cls.temp.name))
        cls.c = AcademicCapabilityService(cls.s)
        cls.db = core.digest((ROOT / 'var/p0_q2.sqlite3').read_bytes())
        real_connect = socket.socket.connect
        def local_only(sock, address):
            if address[0] not in ('127.0.0.1', '::1'):
                raise AssertionError('No external network')
            return real_connect(sock, address)
        cls.net = patch('socket.socket.connect', local_only)
        cls.net.start()
        cls.doc = cls.s.upload(PDF.read_bytes(), 'source.pdf', 'application/pdf')
        cls.runs = {}
        for tier, (start, end) in core.RANGES.items():
            ex = wait(cls.s, cls.s.submit_extract(cls.doc.document_id, ExtractRequest(tier=tier, start_page=start, end_page=end)))
            run = wait(cls.s, cls.s.submit_parse(cls.doc.document_id, ParseRequest(extraction_run_id=ex.run_id, mode='preserved')))
            assert run.status == 'succeeded', run
            cls.runs[tier] = run

    @classmethod
    def tearDownClass(cls):
        cls.s.close(); cls.net.stop(); cls.temp.cleanup()
        assert core.digest((ROOT / 'var/p0_q2.sqlite3').read_bytes()) == cls.db

    def target(self, tier='foundation', sub=None, obj=None):
        return self.s.capabilities(self.runs[tier].run_id, sub, obj).target

    def package(self, tier='foundation', sub=None, obj=None):
        return self.c.build_capability_package(self.target(tier, sub, obj))

    def reject_target(self, **changes):
        t = self.target().model_copy(update=changes)
        with self.assertRaises(core.IngestionError):
            self.c.build_capability_package(t)

    def test_foundation_topic(self):
        p = self.package()
        self.assertEqual(p.coverage.selected_objectives, 25)
        self.assertEqual(p.coverage.canonical_mapped, 6)
        self.assertTrue(p.eligibility['CURRICULUM_BROWSABLE'].eligible)

    def test_higher_topic(self):
        p = self.package('higher')
        self.assertEqual(p.coverage.selected_objectives, 16)
        self.assertEqual(p.coverage.canonical_mapped, 7)
        self.assertTrue(all(o.tier == 'Higher' for o in p.objectives))

    def test_subtopic(self):
        p = self.package('foundation', '2.8')
        self.assertEqual(p.coverage.selected_objectives, 5)
        self.assertTrue(all(o.subtopic_code == '2.8' for o in p.objectives))

    def test_objective(self):
        p = self.package('foundation', '2.8', 'A')
        self.assertEqual([o.source_id for o in p.objectives], ['EDX-4MA1-F-2.8-A'])

    def test_source_text_and_ids(self):
        for tier in core.RANGES:
            parsed = self.s.output(self.runs[tier].run_id, 'parsed')
            expected = [(o['source_id'], o['official_text']) for s in parsed['subtopics'] for o in s['objectives']]
            self.assertEqual([(o.source_id, o.official_text) for o in self.package(tier).objectives], expected)

    def test_mapping_receipt_not_uploaded_approval(self):
        o = self.package('foundation', '2.8', 'A').objectives[0]
        b = o.canonical_bindings[0]
        self.assertEqual(b.official_source_id, o.source_id)
        self.assertEqual(b.human_review_evidence, 'RECORDED_DECISION')
        self.assertEqual(b.decision_ids, ['REV-4MA1-T2-INEQ-SYMBOLS-001'])
        self.assertFalse(o.human_reviewed); self.assertFalse(o.promoted)
        self.assertFalse(b.trusted_snapshot_backed); self.assertFalse(b.uploaded_target_approved)

    def test_legacy_label_does_not_invent_receipt(self):
        b = self.package('foundation', '2.6', 'A').objectives[0].canonical_bindings[0]
        self.assertEqual(b.historical_review_status, 'approved')
        self.assertEqual(b.human_review_evidence, 'NOT_AVAILABLE')

    def test_unmapped_preserved(self):
        p = self.package('foundation', '2.1')
        self.assertTrue(all(o.mapping_status == 'UNMAPPED' for o in p.objectives))
        self.assertTrue(p.eligibility['CURRICULUM_BROWSABLE'].eligible)

    def test_ai_proposal_review_required(self):
        o = self.package('foundation', '2.8', 'B').objectives[0]
        self.assertEqual(o.mapping_status, 'REVIEW_REQUIRED')
        self.assertTrue(o.ai_proposal_ids); self.assertEqual(o.canonical_bindings, [])

    def test_warnings_preserved(self):
        p = self.package()
        tree = self.s.tree(self.runs['foundation'].run_id)
        self.assertEqual(p.warnings[:len(tree.warnings)], tree.warnings)
        self.assertIn('PARSER_WARNING', [w.code for w in p.warnings])
        self.assertTrue(all(o.warnings == tree.warnings for o in p.objectives))

    def test_no_generation_eligibility(self):
        p = self.package()
        for name, state in p.eligibility.items():
            if name == 'CURRICULUM_BROWSABLE': continue
            self.assertFalse(state.eligible); self.assertTrue(state.missing_requirements)
        self.assertFalse(p.academically_approved)

    def test_no_parser_or_provider(self):
        with patch.object(self.s, 'submit_parse', side_effect=AssertionError('No parse')), patch.object(core, 'live_parse', side_effect=AssertionError('No provider')):
            self.assertEqual(self.package().model_calls, 0)

    def test_deterministic_bytes_and_validation(self):
        a = self.package(); b = self.package()
        self.assertEqual(serial(a), serial(b))
        self.assertEqual(self.c.validate_capability_package(a), self.c.validate_capability_package(b))

    def test_persist_restart_and_no_overwrite(self):
        p = self.package(); receipt = self.c.persist(p)
        before = self.c.storage.read(receipt.package_id, 'receipt.json')
        self.assertEqual(self.c.persist(p), receipt)
        self.assertEqual(before, self.c.storage.read(receipt.package_id, 'receipt.json'))
        self.assertEqual(AcademicCapabilityService(self.s).read_capability_package(receipt.package_id), p)

    def test_stale_target(self): self.reject_target(target_id='0' * 64)
    def test_wrong_document_hash(self): self.reject_target(source_sha256='0' * 64)
    def test_wrong_tier(self): self.reject_target(tier='higher')
    def test_wrong_source_id(self): self.reject_target(source_ids=['EDX-4MA1-H-2.6-A'])
    def test_wrong_validation_hash(self): self.reject_target(validation_sha256='0' * 64)
    def test_wrong_run_hash(self): self.reject_target(run_sha256='0' * 64)
    def test_unsupported_profile(self): self.reject_target(profile='other')
    def test_both_tiers_not_silently_merged(self): self.reject_target(tier='foundation+higher')

    def test_wrong_subtopic_objective(self):
        t = self.target('foundation', '2.6', 'A').model_copy(update={'objective_codes': ['E']})
        with self.assertRaises(core.IngestionError): self.c.build_capability_package(t)

    def test_other_run_substitution(self):
        self.reject_target(run_id=self.runs['higher'].run_id)

    def test_foundation_higher_identity(self):
        f = self.package('foundation', '2.6', 'A'); h = self.package('higher', '2.6', 'A')
        self.assertNotEqual(f.objectives[0].objective_identity, h.objectives[0].objective_identity)
        self.assertNotEqual(f.objectives[0].source_id, h.objectives[0].source_id)

    def test_wrong_mapping_source(self):
        p = self.package('foundation', '2.6', 'A').model_dump(mode='json')
        p['objectives'][0]['canonical_bindings'][0]['official_source_id'] = 'EDX-4MA1-H-2.6-A'
        with self.assertRaises(core.IngestionError): self.c.validate_capability_package(p)

    def test_eligibility_tamper(self):
        p = self.package().model_dump(mode='json'); p['eligibility']['LEARNING_SPEC_ELIGIBLE']['eligible'] = True
        with self.assertRaises(core.IngestionError): self.c.validate_capability_package(p)

    def test_package_file_tamper(self):
        receipt = self.c.persist(self.package('higher', '2.1'))
        path = self.c.storage.safe(receipt.package_id, 'package.json'); original = path.read_bytes()
        try:
            path.write_bytes(original + b' ')
            with self.assertRaises(core.IngestionError): self.c.read_capability_package(receipt.package_id)
        finally: path.write_bytes(original)

    def test_missing_validation(self):
        t = self.target(); path = self.s.storage.safe('runs', t.run_id, 'validation.json'); raw = path.read_bytes()
        try:
            path.unlink()
            with self.assertRaises((core.IngestionError, FileNotFoundError)): self.c.build_capability_package(t)
        finally: path.write_bytes(raw)

    def test_parsed_after_validation_tamper(self):
        t = self.target(); path = self.s.storage.safe('runs', t.run_id, 'parsed.json'); raw = path.read_bytes()
        try:
            path.write_bytes(raw + b' ')
            with self.assertRaises(core.IngestionError): self.c.build_capability_package(t)
        finally: path.write_bytes(raw)

    def test_wrong_validation_with_updated_digest(self):
        t = self.target(); run = self.s.current[t.run_id]
        path = self.s.storage.safe('runs', t.run_id, 'validation.json'); raw = path.read_bytes(); old = run.outputs['validation']
        try:
            data = json.loads(raw); data['objective_count'] = 999; changed = serial(data)
            path.write_bytes(changed); run.outputs['validation'] = core.digest(changed)
            with self.assertRaises(core.IngestionError) as exc: self.c.build_capability_package(t)
            self.assertEqual(exc.exception.code, 'VALIDATION_BINDING_INVALID')
        finally: path.write_bytes(raw); run.outputs['validation'] = old

    def test_changed_source_file(self):
        t = self.target(); path = self.s.storage.safe('uploads', t.document_id, 'source.pdf'); raw = path.read_bytes()
        try:
            path.write_bytes(raw + b'\n')
            with self.assertRaises(core.IngestionError): self.c.build_capability_package(t)
        finally: path.write_bytes(raw)

    def test_historical_mapping_digest_check(self):
        original = Path.read_bytes
        def changed(path):
            value = original(path)
            return value + b' ' if path.as_posix().endswith(PROMOTED) else value
        with patch.object(Path, 'read_bytes', changed), self.assertRaises(core.IngestionError): self.package()

    def test_api_build_read_and_guard(self):
        from console_api.app import create_app, ORIGINS
        with TestClient(create_app(self.temp.name)) as client:
            t = self.target()
            url = '/api/curriculum-targets/' + t.target_id + '/capability-package'
            self.assertEqual(client.post(url, json=t.model_dump(mode='json')).status_code, 403)
            headers = {'origin': ORIGINS[0], 'x-console-token': client.get('/api/session').json()['token']}
            response = client.post(url, json=t.model_dump(mode='json'), headers=headers)
            self.assertEqual(response.status_code, 201, response.text)
            receipt = response.json()
            result = client.get('/api/capability-packages/' + receipt['package_id'])
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json(), self.package().model_dump(mode='json'))
            self.assertEqual(client.post(url, content=b' ' * 16385, headers={**headers, 'content-type': 'application/json'}).status_code, 413)
            stale = t.model_dump(mode='json'); stale['source_sha256'] = '0' * 64
            self.assertEqual(client.post(url, json=stale, headers=headers).status_code, 400)
