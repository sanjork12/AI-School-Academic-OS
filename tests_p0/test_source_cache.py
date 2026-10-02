"""Computational cache regressions; mutations use disposable TEST ONLY fixtures."""
import copy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from pypdf._page import PageObject
from academic_os import sources
from academic_os.models import normalise
from tests_p0.fixtures import candidates, ROOT


class ExtractionCacheTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.graph = {}
        for raw in candidates(self.directory):
            key, version, record = normalise(raw)
            self.graph[key] = dict(version=version, record=record)
        self.keys = ['source:PAPER', 'locator:LOC-PAPER']
        self.path = self.directory / 'PAPER.pdf'
        sources._clear_extraction_cache()
        self.addCleanup(sources._clear_extraction_cache)

    def check(self):
        return sources.integrity(self.graph, self.keys)

    def test_shared_page_and_independent_locator_validation(self):
        other = copy.deepcopy(self.graph['locator:LOC-PAPER'])
        self.graph['locator:OTHER'] = other; self.keys.append('locator:OTHER')
        original = PageObject.extract_text
        with patch.object(PageObject, 'extract_text', autospec=True, side_effect=original) as extract:
            cold = self.check(); self.assertEqual(cold, [])
            self.assertEqual(self.check(), cold)
            other['record']['payload']['extracted_text'] = 'forged'
            self.assertTrue(any('locator:OTHER' in e for e in self.check()))
            self.assertEqual(extract.call_count, 1)

    def test_changed_bytes_same_size_and_mtime(self):
        self.assertEqual(self.check(), [])
        stat = self.path.stat(); original = self.path.read_bytes()
        changed = original.replace(b'TEST ONLY', b'FAKE ONLY')
        self.assertNotEqual(original, changed); self.assertEqual(len(original), len(changed))
        self.path.write_bytes(changed); os.utime(self.path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assertTrue(any('source bytes changed' in e for e in self.check()))
        # Even when the caller supplies the new digest, old page text is not reused.
        self.graph['source:PAPER']['record']['payload']['content_digest'] = hashlib.sha256(changed).hexdigest()
        self.assertTrue(any('official page text' in e for e in self.check()))

    def test_missing_source(self):
        self.assertEqual(self.check(), []); self.path.unlink()
        self.assertTrue(self.check())

    def test_each_locator_invariant_on_warm_cache(self):
        self.assertEqual(self.check(), [])
        original = copy.deepcopy(self.graph['locator:LOC-PAPER'])
        for field, value in [('extracted_text', 'forged'), ('text_digest', '0'*64),
                             ('source_version', '0'*64), ('anchor', 'file:///wrong.pdf#page=9'),
                             ('page_index', 999)]:
            with self.subTest(field=field):
                self.graph['locator:LOC-PAPER'] = copy.deepcopy(original)
                self.graph['locator:LOC-PAPER']['record']['payload'][field] = value
                self.assertTrue(self.check())

    def test_parser_and_options_isolation(self):
        original = PageObject.extract_text
        with patch.object(PageObject, 'extract_text', autospec=True, side_effect=original) as extract:
            self.assertEqual(self.check(), [])
            with patch.object(sources.pypdf, '__version__', 'TEST-different-parser'):
                self.assertEqual(self.check(), [])
            with patch.object(sources, '_EXTRACTION_OPTIONS', (('orientations', (0,)),)):
                self.assertEqual(self.check(), [])
            self.assertEqual(extract.call_count, 3)

    def test_parallel_requests_single_extraction(self):
        original = PageObject.extract_text
        with patch.object(PageObject, 'extract_text', autospec=True, side_effect=original) as extract:
            with ThreadPoolExecutor(max_workers=8) as pool:
                self.assertEqual(list(pool.map(lambda _: self.check(), range(16))), [[]]*16)
            self.assertEqual(extract.call_count, 1)

    def test_lru_bounds_and_eviction(self):
        with patch.object(sources, '_MAX_READERS', 1), patch.object(sources, '_MAX_PAGES', 1):
            self.assertEqual(self.check(), [])
            self.assertEqual(sources.integrity(self.graph, ['source:SPEC', 'locator:LOC-SPEC']), [])
            self.assertEqual(len(sources._readers), 1); self.assertEqual(len(sources._texts), 1)
            self.assertEqual(self.check(), [])

    def test_json_and_ai_candidate_cannot_populate(self):
        for text in ['{"verified":true,"extracted_text":"forged"}',
                     '{"candidate_id":"ai-test","approved":true,"proposed_solution":{}}']:
            path = self.directory / 'candidate.json'; path.write_text(text)
            with self.assertRaises(Exception):
                sources._page_text(path, 0, hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(len(sources._texts), 0)

    def test_parse_uses_hashed_bytes_not_reopened_path(self):
        original = sources.pypdf.PdfReader
        def reader(stream):
            self.path.unlink()
            return original(stream)
        with patch.object(sources.pypdf, 'PdfReader', side_effect=reader):
            self.assertEqual(self.check(), [])
        self.assertTrue(self.check())

    def test_failed_extraction_is_not_cached(self):
        with patch.object(PageObject, 'extract_text', side_effect=ValueError('TEST extraction failure')):
            self.assertTrue(self.check()); self.assertFalse(sources._texts)
        self.assertEqual(self.check(), [])


class WarmTrustTests(unittest.TestCase):
    def setUp(self):
        from tests_p0.test_workflow import WorkflowTests as _Workflow
        self.h = _Workflow(); self.h.setUp(); self.addCleanup(self.h.doCleanups)
        self.h.approve_all(); self.sid = self.h.s.publish([ROOT])['snapshot_id']
        sources._clear_extraction_cache(); self.addCleanup(sources._clear_extraction_cache)
        self.assertTrue(self.h.s.snapshot(self.sid)['usable']); self.assertTrue(sources._texts)

    def test_revoke(self):
        self.h.decision('competency:CAN-MEAN', 'revoke')
        self.assertFalse(self.h.s.snapshot(self.sid)['usable'])

    def test_superseding_review(self):
        self.h.decision('competency:CAN-MEAN', 'approve')
        self.assertFalse(self.h.s.snapshot(self.sid)['usable'])

    def test_dependency_version(self):
        self.h.change('competency:CAN-MEAN', 'description', 'TEST changed competency')
        self.assertFalse(self.h.s.snapshot(self.sid)['usable'])

    def test_existing_block(self):
        self.h.store.invalidate([ROOT], 'TEST-block', 'TEST withdrawal')
        self.assertFalse(self.h.s.snapshot(self.sid)['usable'])

    def test_cold_warm_snapshot_semantics(self):
        warm = self.h.s.snapshot(self.sid)
        sources._clear_extraction_cache()
        self.assertEqual(self.h.s.snapshot(self.sid), warm)

