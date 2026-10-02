import copy
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from academic_os.examples.q2 import build_candidates, ROOTS
from academic_os.models import normalise
from academic_os.service import Service
from academic_os.storage import Store
from tests_p0.fixtures import candidates, ROOT


class SemanticTrustTests(unittest.TestCase):
    """Approvals/publication use only generated TEST-ONLY temporary PDFs."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'test.db'
        self.store = Store(self.path); self.addCleanup(self.store.close)
        self.s = Service(self.store); self.sequence = 0
        rows = candidates(self.tmp.name)
        self.s.stage(rows, {normalise(x)[0]: None for x in rows}, 'TEST-BASE')
        prov = self.s.inspect('competency:CAN-MEAN')['record']['payload']['provenance']
        additions = []
        for cid, name in [('C-MEAN', 'Mean'), ('C-COUNT', 'Number of observations')]:
            additions.append(dict(kind='concept', payload=dict(concept_id=cid, name=name,
                subject_domain='Statistics', description='TEST ONLY ' + name, provenance=prov)))
            additions.append(dict(kind='concept_link', payload=dict(link_id='LINK-' + cid,
                canonical_id='CAN-MEAN', concept_id=cid, rationale='TEST explicit relationship', provenance=prov)))
        additions.append(dict(kind='task_condition', payload=dict(condition_id='TC-SUMMARY',
            name='From summary statistics', kind='input_form', description='TEST supplied summaries', provenance=prov)))
        spans = []
        for role, lid in [('shared_stem','LOC-PAPER'), ('prompt','LOC-PAPER'), ('mark_scheme','LOC-SCHEME')]:
            loc = self.s.inspect('locator:' + lid); text = loc['record']['payload']['extracted_text']
            spans.append(dict(role=role, locator_id=lid, locator_version=loc['version'], start=0, end=len(text), text=text))
        additions.append(dict(kind='parsed_part', payload=dict(parsed_id='PARSED-TEST', part_id='PART',
            parser_version='TEST/1', marks=1, spans=spans)))
        mapping = self.s.inspect(ROOT)
        mapping['record']['payload'].update(focus_concept_ids=['C-MEAN','C-COUNT'],
            semantics=dict(role='primary', parsed_part_id='PARSED-TEST',
                           concept_link_ids=['LINK-C-MEAN','LINK-C-COUNT'], task_condition_ids=['TC-SUMMARY']))
        additions.append(mapping['record'])
        self.bundle = dict(items=additions, expected_heads={normalise(x)[0]:None for x in additions})
        self.bundle['expected_heads'][ROOT] = mapping['version']
        self.s.stage(**self.bundle, request_id='TEST-SEMANTICS')

    def decide(self, key, action='approve'):
        item = self.s.inspect(key); self.sequence += 1
        return self.s.review(key, action, 'TEST-ONLY-REVIEWER', 'TEST ONLY temporary PDFs',
            item['version'], item['dependency_digest'], item['expected_decision'], 'TEST-REVIEW-' + str(self.sequence))

    def approve(self):
        for prefix in ['source:', 'locator:']:
            for item in self.s.inspect():
                if item['key'].startswith(prefix): self.decide(item['key'], 'verify')
        for item in self.s.inspect():
            if not item['key'].startswith(('source:', 'locator:')): self.decide(item['key'])

    def change(self, key, field, value):
        item = self.s.inspect(key); item['record']['payload'][field] = value
        self.sequence += 1
        return self.s.stage([item['record']], {key:item['version']}, 'TEST-CHANGE-' + str(self.sequence))

    def test_concept_and_competency_have_distinct_types(self):
        self.assertEqual(self.s.inspect('concept:C-MEAN')['record']['kind'], 'concept')
        self.assertEqual(self.s.inspect('competency:CAN-MEAN')['record']['kind'], 'competency')

    def test_competency_references_multiple_concepts(self):
        deps = self.s.inspect(ROOT)['dependencies']
        self.assertIn('concept:C-MEAN', deps); self.assertIn('concept:C-COUNT', deps)

    def test_concept_referenced_by_multiple_competencies(self):
        comp = self.s.inspect('competency:CAN-MEAN')['record']; comp['payload']['canonical_id'] = 'CAN-OTHER'
        link = self.s.inspect('concept_link:LINK-C-MEAN')['record']
        link['payload'].update(link_id='LINK-OTHER', canonical_id='CAN-OTHER')
        self.s.stage([comp,link], {'competency:CAN-OTHER':None,'concept_link:LINK-OTHER':None}, 'TEST-SECOND-LINK')
        self.assertIn('concept:C-MEAN', self.s.inspect('concept_link:LINK-OTHER')['dependencies'])

    def test_task_condition_distinct_from_competency_and_scope(self):
        condition = self.s.inspect('task_condition:TC-SUMMARY')['record']
        self.assertEqual(condition['kind'], 'task_condition')
        self.assertNotIn('question_id', condition['payload'])
        self.assertNotIn('context_id', condition['payload'])
        self.assertNotEqual(condition['kind'], self.s.inspect('scope:SCOPE')['record']['kind'])
        self.assertNotIn('SUMMARY', self.s.inspect('competency:CAN-MEAN')['record']['payload']['canonical_id'])

    def test_candidate_semantics_block_trusted_publication(self):
        self.assertFalse(self.s.check([ROOT])['publishable'])
        with self.assertRaisesRegex(ValueError, 'blocked'): self.s.publish([ROOT])

    def test_fully_approved_semantics_publish_deterministically(self):
        self.approve(); first = self.s.publish([ROOT])
        self.assertEqual(first, self.s.publish([ROOT]))
        snapshot = self.s.snapshot(first['snapshot_id'])
        self.assertTrue(snapshot['usable'])
        self.assertEqual(snapshot['payload']['objects']['concept:C-MEAN']['payload']['review_status'], 'approved')
        self.assertIn('task_condition:TC-SUMMARY', snapshot['payload']['versions'])

    def test_pending_semantic_dependency_blocks_otherwise_approved_graph(self):
        self.approve(); self.decide('task_condition:TC-SUMMARY', 'revise')
        self.assertFalse(self.s.check([ROOT])['publishable'])

    def test_question_part_revision_stales_mapping(self):
        self.approve(); self.change('question_part:PART', 'label', 'TEST revised part')
        self.assertEqual(self.s.inspect(ROOT)['state'], 'stale')

    def test_competency_revision_stales_mapping(self):
        self.approve(); self.change('competency:CAN-MEAN', 'description', 'TEST changed definition')
        self.assertEqual(self.s.inspect(ROOT)['state'], 'stale')

    def test_task_condition_revision_stales_mapping(self):
        self.approve(); self.change('task_condition:TC-SUMMARY', 'description', 'TEST changed assessment form')
        self.assertEqual(self.s.inspect(ROOT)['state'], 'stale')

    def test_concept_revision_stales_mapping(self):
        self.approve(); self.change('concept:C-MEAN', 'description', 'TEST changed concept')
        self.assertEqual(self.s.inspect(ROOT)['state'], 'stale')

    def test_concept_relationship_revision_stales_mapping(self):
        self.approve(); self.change('concept_link:LINK-C-MEAN', 'rationale', 'TEST changed relationship')
        self.assertEqual(self.s.inspect(ROOT)['state'], 'stale')

    def test_withdrawal_blocks_old_snapshot_reads(self):
        self.approve(); sid = self.s.publish([ROOT])['snapshot_id']
        self.decide('concept_link:LINK-C-MEAN', 'revoke')
        self.assertFalse(self.s.snapshot(sid)['usable'])
        self.assertFalse(self.s.check([ROOT])['publishable'])

    def test_semantic_stage_idempotent(self):
        before = self.store.db.execute('SELECT count(*) FROM versions').fetchone()[0]
        self.s.stage(**self.bundle, request_id='TEST-SEMANTICS')
        self.assertEqual(before, self.store.db.execute('SELECT count(*) FROM versions').fetchone()[0])

    def test_invalid_concept_reference_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown dependency concept:MISSING'):
            self.change('concept_link:LINK-C-MEAN', 'concept_id', 'MISSING')

    def test_invalid_competency_reference_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown dependency competency:MISSING'):
            self.change('concept_link:LINK-C-MEAN', 'canonical_id', 'MISSING')

    def test_invalid_task_condition_reference_rejected(self):
        semantic = self.s.inspect(ROOT)['record']['payload']['semantics']
        semantic['task_condition_ids'] = ['MISSING']
        with self.assertRaisesRegex(ValueError, 'Unknown dependency task_condition:MISSING'):
            self.change(ROOT, 'semantics', semantic)

    def test_wrong_existing_concept_link_target_rejected(self):
        comp = self.s.inspect('competency:CAN-MEAN')['record']; comp['payload']['canonical_id'] = 'CAN-OTHER'
        self.s.stage([comp], {'competency:CAN-OTHER':None}, 'TEST-OTHER')
        with self.assertRaisesRegex(ValueError, 'concept link competency mismatch'):
            self.change('concept_link:LINK-C-MEAN', 'canonical_id', 'CAN-OTHER')

    def test_cannot_forge_concept_approval(self):
        with self.assertRaisesRegex(ValueError, 'Candidate cannot'):
            self.change('concept:C-MEAN', 'review_status', 'approved')

    def test_concurrent_semantic_revision_cannot_overwrite(self):
        item = self.s.inspect('task_condition:TC-SUMMARY'); barrier = threading.Barrier(2)
        def run(number):
            store = Store(self.path)
            try:
                record = copy.deepcopy(item['record']); record['payload']['description'] = 'TEST editor ' + str(number)
                barrier.wait(timeout=10)
                try:
                    Service(store).stage([record], {item['key']:item['version']}, 'TEST-CONCURRENT-' + str(number))
                    return 'ok'
                except ValueError as error:
                    self.assertIn('Version conflict', str(error)); return 'conflict'
            finally: store.close()
        with ThreadPoolExecutor(2) as pool: results = list(pool.map(run, [1,2]))
        self.assertCountEqual(results, ['ok','conflict'])


class Q2GoldStandardTests(unittest.TestCase):
    """Read actual Q2 candidates; never submit any approval for real sources."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        cls.store = Store(Path(cls.tmp.name) / 'q2.db'); cls.addClassCleanup(cls.store.close)
        cls.s = Service(cls.store)
        rows = build_candidates()
        cls.s.stage(rows, {normalise(x)[0]:None for x in rows}, 'TEST-Q2-SEED')
        cls.s.stage(**cls.s.plan_q2(), request_id='TEST-Q2-PARSE')
        cls.parsed_before = {k:r for k,r in cls.store.graph().items() if k.startswith('parsed_part:')}
        cls.s.stage(**cls.s.plan_q2_semantics(), request_id='TEST-Q2-SEMANTICS')
        cls.graph = cls.store.graph(); cls.report = cls.s.q2_semantics_report()

    def mapping(self, part, suffix):
        return self.graph['part_mapping:MAP-Q2-' + part + '-' + suffix]['record']['payload']

    def test_q2a_mean_primary(self):
        p = self.mapping('a','MEAN-CALC')
        self.assertEqual(p['canonical_id'], 'CAN-STAT-MEAN-CALC')
        self.assertEqual(p['focus_concept_ids'], ['CON-STAT-MEAN'])
        self.assertEqual(p['semantics']['role'], 'primary')

    def test_q2b_standard_deviation_primary(self):
        p = self.mapping('b','SD-CALC')
        self.assertEqual(p['canonical_id'], 'CAN-STAT-SD-CALC')
        self.assertEqual(p['focus_concept_ids'], ['CON-STAT-SD'])
        self.assertEqual(p['semantics']['role'], 'primary')

    def test_q2c_variation_primary_and_two_canonical_concepts(self):
        p = self.mapping('c','VARIATION-INTERPRET')
        self.assertEqual(p['semantics']['role'], 'primary')
        self.assertEqual(set(p['focus_concept_ids']), {'CON-STAT-SD','CON-STAT-SPREAD'})

    def test_q2c_secondary_is_candidate_only(self):
        p = self.mapping('c','CONTEXT-INFER')
        self.assertEqual(p['semantics']['role'], 'secondary')
        self.assertEqual(p['review_status'], 'pending')
        self.assertEqual(self.s.inspect('competency:CAN-STAT-CONTEXT-INFER')['state'], 'pending')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM reviews').fetchone()[0], 0)

    def test_summary_task_condition_reused_for_a_and_b(self):
        a = self.mapping('a','MEAN-CALC')['semantics']['task_condition_ids']
        b = self.mapping('b','SD-CALC')['semantics']['task_condition_ids']
        self.assertEqual(a,b); self.assertEqual(a,['TC-SUMMARY-STATISTICS'])

    def test_no_new_variant_or_question_specific_competencies(self):
        comps = [r['record']['payload'] for r in self.graph.values() if r['record']['kind']=='competency']
        self.assertEqual(len(comps),4)
        for comp in comps:
            identity = (comp['canonical_id'] + ' ' + comp['skill_name']).lower()
            for forbidden in ['edexcel','9ma0','a level','paper 31','q2','coach','runner','summary']:
                self.assertNotIn(forbidden,identity)

    def test_concept_identities_curriculum_independent(self):
        concepts = [r['record']['payload'] for r in self.graph.values() if r['record']['kind']=='concept']
        self.assertEqual(len(concepts),4)
        for c in concepts:
            self.assertNotIn('Q2', c['concept_id']); self.assertNotIn('9MA0', c['concept_id'])

    def test_existing_parsed_text_and_versions_unchanged(self):
        self.assertEqual(self.parsed_before,{k:r for k,r in self.graph.items() if k.startswith('parsed_part:')})

    def test_gold_report_valid_but_not_publishable(self):
        self.assertTrue(self.report['architecture_valid'], self.report['validation_errors'])
        self.assertFalse(self.report['publication']['publishable'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM snapshots').fetchone()[0], 0)
        self.assertEqual(self.report,self.s.q2_semantics_report())

    def test_existing_evidence_and_parser_dependencies_included(self):
        deps = self.s.inspect(ROOTS[1])['dependencies']
        for key in ['parsed_part:PARSED-Q2-b','evidence:EV-MS-MAP-Q2-b-SD-CALC',
                    'concept:CON-STAT-SD','concept_link:LINK-SD-CALC-SD',
                    'task_condition:TC-SUMMARY-STATISTICS','condition:COND-SUMMARY','scope:SCOPE-STAT-2.3']:
            self.assertIn(key,deps)

    def test_many_to_many_part_competency_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'many.db')
            try:
                s = Service(store)
                rows = [r['record'] for r in self.graph.values()]
                s.stage(rows, {normalise(x)[0]:None for x in rows}, 'TEST-COPY')
                # Explicit TEST candidate: same mean competency used by another
                # part; no inference or new secondary is added to the real fixture.
                mapping = copy.deepcopy(self.graph['part_mapping:MAP-Q2-a-MEAN-CALC']['record'])
                p = mapping['payload']; p.update(mapping_id='TEST-B-MEAN', part_id='Q2-b', evidence_ids=[])
                p['semantics']['role'] = 'secondary'; p['semantics']['parsed_part_id'] = 'PARSED-Q2-b'
                mapping['judgment_refs'] = ['parsed_part:PARSED-Q2-b']
                rows = []
                for source in ['QP','MS']:
                    e = copy.deepcopy(self.graph['evidence:EV-' + source + '-MAP-Q2-b-SD-CALC']['record'])
                    eid = 'TEST-' + source + '-B-MEAN'
                    e['payload'].update(evidence_id=eid, target=dict(kind='part_mapping',id='TEST-B-MEAN'))
                    rows.append(e); p['evidence_ids'].append(eid)
                rows.append(mapping)
                s.stage(rows, {normalise(x)[0]:None for x in rows}, 'TEST-MANY')
                mappings = [r['record']['payload'] for r in store.graph().values() if r['record']['kind']=='part_mapping']
                self.assertEqual({m['part_id'] for m in mappings if m['canonical_id']=='CAN-STAT-MEAN-CALC'}, {'Q2-a','Q2-b'})
                self.assertEqual(len([m for m in mappings if m['part_id']=='Q2-b']), 2)
            finally: store.close()

    def test_report_detects_semantic_drift(self):
        from academic_os.semantic_report import q2_report
        graph = copy.deepcopy(self.graph)
        graph['concept:CON-STAT-MEAN']['record']['payload']['name'] = 'Median'
        report = q2_report(graph, {}, self.report['publication'])
        self.assertFalse(report['architecture_valid'])


if __name__ == '__main__': unittest.main()
