"""Trusted read work counts and warm-cache governance; no provider calls."""
from academic_os.ai_authoring.provenance import LEGACY_POLICY
import unittest
from unittest.mock import patch
from pypdf._page import PageObject
from academic_os import sources, service, governance
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_authoring.brief import compile_brief
from tests_p0.teacher_product_acceptance import state


class RepresentativeCacheTests(unittest.TestCase):
    def test_full_input_path_counts_and_warm_semantics(self):
        before = state(); sources._clear_extraction_cache()
        self.addCleanup(sources._clear_extraction_cache)
        original_snapshot = service.Service.snapshot
        original_extract = PageObject.extract_text
        original_integrity = sources.integrity
        with patch.object(service.Service, 'snapshot', autospec=True, side_effect=original_snapshot) as snapshots, \
             patch.object(service, 'integrity', wraps=original_integrity) as checks, \
             patch.object(governance, 'integrity', wraps=original_integrity) as deferred, \
             patch.object(sources.pypdf, 'PdfReader', wraps=sources.pypdf.PdfReader) as readers, \
             patch.object(PageObject, 'extract_text', autospec=True, side_effect=original_extract) as extracts:
            cold = compile_brief(read_inputs('var/p0_q2.sqlite3'), policy=LEGACY_POLICY)
            self.assertEqual(snapshots.call_count, 160)
            self.assertEqual(checks.call_count, 160); self.assertEqual(deferred.call_count, 80)
            self.assertEqual(readers.call_count, 5); self.assertEqual(extracts.call_count, 5)
            warm = compile_brief(read_inputs('var/p0_q2.sqlite3'), policy=LEGACY_POLICY)
            self.assertEqual(cold, warm)
            self.assertEqual(snapshots.call_count, 320)
            self.assertEqual(checks.call_count + deferred.call_count, 480)
            self.assertEqual(readers.call_count, 5); self.assertEqual(extracts.call_count, 5)
        self.assertEqual(state(), before)


class WarmGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests_p0.test_deferred_governance import DeferredGovernanceTests
        cls.fixture = DeferredGovernanceTests
        cls.fixture.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.tearDownClass()

    def setUp(self):
        self.h = self.fixture(); self.h.setUp(); self.addCleanup(self.h.doCleanups)
        self.sid = self.h.published()
        sources._clear_extraction_cache(); self.addCleanup(sources._clear_extraction_cache)
        self.assertTrue(self.h.s.snapshot(self.sid)['usable'])

    def test_deferred_dependency_change(self):
        self.h.change()
        with patch.object(governance, 'selection', wraps=governance.selection) as selection:
            self.assertFalse(self.h.s.snapshot(self.sid)['usable'])
            self.assertEqual(selection.call_count, 1)

    def test_governance_reopen(self):
        self.h.decide(action='reopen', request='TEST-REOPEN-WARM')
        self.assertFalse(self.h.s.snapshot(self.sid)['usable'])
