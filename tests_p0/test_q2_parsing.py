import copy
import tempfile
import unittest
from pathlib import Path

from academic_os.examples.q2 import build_candidates, ROOTS
from academic_os.mapping import plan_q2
from academic_os.models import normalise
from academic_os.parsing import parse_q2
from academic_os.service import Service
from academic_os.storage import Store


class Q2ParsingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'test.sqlite3')
        self.addCleanup(self.store.close)
        self.service = Service(self.store)
        items = build_candidates()
        self.service.stage(items, {normalise(x)[0]: None for x in items}, 'TEST-SEED')

    def stage_plan(self):
        bundle = self.service.plan_q2()
        self.service.stage(**bundle, request_id='TEST-PARSE')
        return bundle

    def test_real_text_parts_marks_and_offsets(self):
        graph = self.store.graph()
        parts = parse_q2(graph)
        self.assertEqual([p['payload']['marks'] for p in parts], [1, 2, 2])
        for record in parts:
            for span in record['payload']['spans']:
                text = graph['locator:' + span['locator_id']]['record']['payload']['extracted_text']
                self.assertEqual(span['text'], text[span['start']:span['end']])
        spans = {s['role']: s['text'] for s in parts[2]['payload']['spans']}
        self.assertIn('equal numbers', spans['comparison_context'])
        self.assertIn('no answer given for (b)', spans['mark_scheme_notes'])
        self.assertNotIn('equal numbers', spans['prompt'])

    def test_plan_is_pure_and_deterministic(self):
        graph = self.store.graph()
        before = copy.deepcopy(graph)
        a = plan_q2(graph)
        self.assertEqual(a, plan_q2(graph))
        self.assertEqual(graph, before)
        self.assertEqual(len(a['items']), 15)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0], 0)

    def test_missing_marker_fails_closed(self):
        graph = self.store.graph()
        graph['locator:QP-Q2']['record']['payload']['extracted_text'] = graph['locator:QP-Q2']['record']['payload']['extracted_text'].replace('(b)', '(d)')
        with self.assertRaisesRegex(ValueError, 'found 0'):
            parse_q2(graph)

    def test_duplicate_marker_fails_closed(self):
        graph = self.store.graph()
        graph['locator:QP-Q2']['record']['payload']['extracted_text'] += '\n(a) duplicate'
        with self.assertRaisesRegex(ValueError, 'found 2'):
            parse_q2(graph)

    def test_changed_instruction_is_not_assigned_old_mapping(self):
        graph = self.store.graph()
        for lid in ['QP-Q2', 'QP-Q2-a', 'QP-Q2-b', 'QP-Q2-c']:
            p = graph['locator:' + lid]['record']['payload']
            p['extracted_text'] = p['extracted_text'].replace('Calculate the mean', 'Explain the median')
        with self.assertRaisesRegex(ValueError, 'Unresolved Q2 mapping'):
            plan_q2(graph)

    def test_paper_scheme_marks_disagreement_rejected(self):
        graph = self.store.graph()
        p = graph['locator:MS-Q2-a']['record']['payload']
        p['extracted_text'] = p['extracted_text'].replace('(1)', '(9)', 1)
        with self.assertRaisesRegex(ValueError, 'allocations disagree'):
            parse_q2(graph)

    def test_stage_is_idempotent_and_real_case_stays_blocked(self):
        bundle = self.stage_plan()
        self.service.stage(**bundle, request_id='TEST-PARSE')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM heads').fetchone()[0], 38)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0], 0)
        report = self.service.check(ROOTS)
        self.assertTrue(report['schema_valid'])
        self.assertFalse(report['publishable'])
        self.assertIn('parsed_part:PARSED-Q2-a', report['versions'])
        with self.assertRaisesRegex(ValueError, 'blocked'):
            self.service.publish(ROOTS)

    def test_forged_span_cannot_enter_staging(self):
        bundle = self.service.plan_q2()
        bundle['items'][0]['payload']['spans'][0]['text'] = 'Invented original text'
        with self.assertRaisesRegex(ValueError, 'differs from located'):
            self.service.stage(**bundle, request_id='TEST-FORGE')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM heads').fetchone()[0], 35)

    def test_wrong_locator_version_rejected(self):
        bundle = self.service.plan_q2()
        bundle['items'][0]['payload']['spans'][0]['locator_version'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'locator version is stale'):
            self.service.stage(**bundle, request_id='TEST-OLD-LOCATOR')

    def test_cross_part_span_rejected(self):
        bundle = self.service.plan_q2()
        bundle['items'][0]['payload']['part_id'] = 'Q2-b'
        with self.assertRaisesRegex(ValueError, 'another question/part'):
            self.service.stage(**bundle, request_id='TEST-WRONG-PART')

    def test_stale_plan_cannot_overwrite_mapping_edit(self):
        bundle = self.service.plan_q2()
        item = self.service.inspect(ROOTS[0])
        item['record']['payload']['rationale'] = 'TEST concurrent editor'
        self.service.stage([item['record']], {item['key']: item['version']}, 'TEST-EDIT')
        with self.assertRaisesRegex(ValueError, 'Version conflict'):
            self.service.stage(**bundle, request_id='TEST-OLD-PLAN')

    def test_parsed_content_change_stales_mapping_approval(self):
        self.stage_plan()
        mapping = self.service.inspect(ROOTS[0])
        self.service.review(ROOTS[0], 'approve', 'TEST-ONLY', 'TEST ONLY isolated database',
                            mapping['version'], mapping['dependency_digest'], None, 'TEST-REVIEW')
        parsed = self.service.inspect('parsed_part:PARSED-Q2-a')
        parsed['record']['payload']['warnings'].append('TEST revised interpretation warning')
        self.service.stage([parsed['record']], {parsed['key']: parsed['version']}, 'TEST-PARSED-CHANGE')
        self.assertEqual(self.service.inspect(ROOTS[0])['state'], 'stale')


if __name__ == '__main__':
    unittest.main()
