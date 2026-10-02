"""Reuse real completed curriculum runs; no parsing, providers or trusted writes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.service import IngestionService, serial
from academic_os.curriculum_capability.service import AcademicCapabilityService
from academic_os.governed_learning.service import GovernedLearningService
from academic_os.governed_learning.policy import READY
from tests_p0.capability_package_acceptance import RUNS, ROOT


class GovernedLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        cls.ingestion = IngestionService()
        cls.capabilities = AcademicCapabilityService(cls.ingestion, Path(cls.tmp.name) / 'packages')
        cls.service = GovernedLearningService(cls.capabilities, Path(cls.tmp.name) / 'specs')
        cls.network = patch('socket.socket.connect', side_effect=AssertionError('No network'))
        cls.network.start()
        cls.parse = patch.object(cls.ingestion, 'submit_parse', side_effect=AssertionError('No new parse'))
        cls.parse.start()
        cls.db = core.digest((ROOT / 'var/p0_q2.sqlite3').read_bytes())

    @classmethod
    def tearDownClass(cls):
        cls.parse.stop(); cls.network.stop(); cls.ingestion.close(); cls.tmp.cleanup()
        assert core.digest((ROOT / 'var/p0_q2.sqlite3').read_bytes()) == cls.db

    def package(self, tier='foundation', sub='2.8', obj='A'):
        target = self.ingestion.capabilities(RUNS[tier], sub, obj).target
        return self.capabilities.build_capability_package(target)

    def eligible(self, package=None):
        return self.service.evaluate_learning_spec_eligibility(package or self.package())

    def spec(self, package=None):
        package = package or self.package()
        return self.service.build_learning_spec(package, self.eligible(package))

    def altered_spec(self, mutate):
        value = self.spec().model_dump(mode='json'); mutate(value)
        self.assertFalse(self.service.validate_learning_spec(value).valid)

    def altered_package(self, mutate):
        value = self.package().model_dump(mode='json'); mutate(value)
        result = self.eligible(value)
        self.assertNotIn(result.status, READY)

    def test_real_objective_eligible(self):
        e = self.eligible()
        self.assertEqual(e.status, 'ELIGIBLE_WITH_WARNINGS')
        self.assertEqual(e.independently_ready_source_ids, ['EDX-4MA1-F-2.8-A'])
        self.assertFalse(e.publication_eligible); self.assertFalse(e.pedagogy_eligible)

    def test_foundation_exact_coverage(self):
        p = self.package('foundation', None, None); e = self.eligible(p)
        self.assertEqual(e.status, 'REVIEW_REQUIRED')
        self.assertEqual(e.selected_source_ids, p.target.source_ids)
        self.assertEqual(len(e.objective_results), 25)
        self.assertEqual(len(e.independently_ready_source_ids), 2)
        self.assertEqual(len(e.unresolved_source_ids), 23)
        self.assertEqual(e.excluded_source_ids, [])

    def test_higher_exact_coverage(self):
        p = self.package('higher', None, None); e = self.eligible(p)
        self.assertEqual(e.status, 'REVIEW_REQUIRED')
        self.assertEqual(len(e.objective_results), 16)
        self.assertEqual(e.independently_ready_source_ids, ['EDX-4MA1-H-2.8-B'])
        self.assertEqual(len(e.unresolved_source_ids), 15)

    def test_subtopic_review_required(self):
        p = self.package('foundation', '2.8', None); e = self.eligible(p)
        self.assertEqual(len(e.objective_results), 5)
        self.assertEqual(len(e.unresolved_source_ids), 3)
        with self.assertRaises(core.IngestionError): self.service.build_learning_spec(p, e)

    def test_mapped_label_without_receipt_not_enough(self):
        e = self.eligible(self.package('foundation', '2.6', 'A'))
        self.assertEqual(e.status, 'REVIEW_REQUIRED')
        self.assertIn('RECORDED_HUMAN_CANONICAL_DECISION_REQUIRED', e.objective_results[0].reason_codes)

    def test_review_required_real_proposal(self):
        e = self.eligible(self.package('foundation', '2.8', 'B'))
        self.assertEqual(e.status, 'REVIEW_REQUIRED')
        self.assertEqual(e.independently_ready_source_ids, [])

    def test_empty_higher_scope_blocked(self):
        p = self.package('higher', '2.4', None)
        self.assertEqual(self.eligible(p).status, 'BLOCKED')

    def test_official_wording_intact(self):
        p = self.package(); s = self.spec(p)
        self.assertEqual(s.learning_objectives[0].official_text, p.objectives[0].official_text)
        self.assertEqual(s.canonical_semantics[0].description, p.objectives[0].canonical_bindings[0].canonical_wording)

    def test_source_canonical_transform_classes(self):
        s = self.spec()
        self.assertEqual(s.learning_objectives[0].provenance.classifications, ['SOURCE_DERIVED'])
        self.assertEqual(s.canonical_semantics[0].provenance.classifications, ['CANONICAL_DERIVED', 'HUMAN_REVIEWED'])
        self.assertEqual(s.learning_intentions[0].provenance.classifications, ['DETERMINISTIC_TRANSFORMATION'])
        self.assertEqual(s.learning_intentions[0].statement, 'Student should be able to: ' + s.canonical_semantics[0].description)

    def test_no_unsupported_optional_claims(self):
        s = self.spec()
        for name in ('success_criteria', 'prerequisites', 'known_misconceptions', 'conceptual_knowledge', 'concept_skill_task_relations', 'assessment_evidence'):
            field = getattr(s, name)
            self.assertEqual(field.claims, [])
            self.assertTrue(field.reason_code.endswith('UNAVAILABLE'))
        self.assertEqual(s.task_capabilities[0].task_forms, [])

    def test_warning_propagation(self):
        p = self.package(); e = self.eligible(p); s = self.spec(p)
        self.assertEqual(e.warnings[:len(p.warnings)], p.warnings)
        self.assertEqual(s.warnings, e.warnings)
        self.assertIn('HUMAN_REVIEW_REQUIRED', [w.code for w in s.warnings])

    def test_determinism_and_validation_replay(self):
        p = self.package(); a = self.spec(p); b = self.spec(p)
        self.assertEqual(serial(self.eligible(p)), serial(self.eligible(p)))
        self.assertEqual(serial(a), serial(b))
        va = self.service.validate_learning_spec(a); vb = self.service.validate_learning_spec(b)
        self.assertTrue(va.valid); self.assertEqual(va, vb)
        self.assertEqual(va.semantic_sha256, core.digest(serial(a)))

    def test_independent_validator_does_not_call_builder(self):
        s = self.spec()
        with patch('academic_os.governed_learning.service.construct_verified', side_effect=AssertionError('Validator must be independent')):
            self.assertTrue(self.service.validate_learning_spec(s).valid)

    def test_storage_repeat_restart(self):
        s = self.spec(); receipt = self.service.persist(s)
        self.assertEqual(self.service.persist(s), receipt)
        second = GovernedLearningService(self.capabilities, self.service.storage.root)
        self.assertEqual(second.read_learning_spec(receipt.spec_id), s)

    def test_tier_separate_explicit_canonical_reuse(self):
        f = self.spec(self.package('foundation', '2.8', 'E'))
        h = self.spec(self.package('higher', '2.8', 'B'))
        self.assertEqual(f.canonical_semantics[0].canonical_id, h.canonical_semantics[0].canonical_id)
        self.assertNotEqual(f.source_package_hash, h.source_package_hash)
        self.assertNotEqual(f.learning_objectives[0].source_id, h.learning_objectives[0].source_id)
        self.assertNotEqual(f.curriculum_scope.tier, h.curriculum_scope.tier)

    def test_stale_capability_package_hash(self):
        e = self.service.evaluate_learning_spec_eligibility(self.package(), '0' * 64)
        self.assertEqual(e.status, 'BLOCKED'); self.assertIn('SOURCE_PACKAGE_HASH_MISMATCH', e.reason_codes)

    def test_wrong_tier(self):
        self.altered_package(lambda p: p['target'].update(tier='Higher'))

    def test_source_objective_substitution(self):
        self.altered_package(lambda p: p['objectives'][0].update(source_id='EDX-4MA1-F-2.8-B'))

    def test_missing_canonical_binding(self):
        self.altered_package(lambda p: p['objectives'][0].update(canonical_bindings=[]))

    def test_review_required_treated_as_approved(self):
        p = self.package('foundation', '2.8', 'B').model_dump(mode='json')
        p['objectives'][0]['canonical_bindings'] = self.package().model_dump(mode='json')['objectives'][0]['canonical_bindings']
        p['objectives'][0]['mapping_status'] = 'MAPPED'
        self.assertEqual(self.eligible(p).status, 'BLOCKED')

    def test_unmapped_silently_removed(self):
        p = self.package('foundation', None, None).model_dump(mode='json')
        p['objectives'] = [o for o in p['objectives'] if o['mapping_status'] == 'MAPPED']
        self.assertEqual(self.eligible(p).status, 'BLOCKED')

    def test_source_wording_replaced(self):
        self.altered_spec(lambda s: s['learning_objectives'][0].update(official_text=s['canonical_semantics'][0]['description']))

    def test_invented_prerequisite(self):
        self.altered_spec(lambda s: s['prerequisites'].update(claims=['Must master arithmetic']))

    def test_invented_misconception(self):
        self.altered_spec(lambda s: s['known_misconceptions'].update(claims=['Students reverse symbols']))

    def test_invented_success_criterion(self):
        self.altered_spec(lambda s: s['success_criteria'].update(claims=['Score 80 percent']))

    def test_tampered_intention(self):
        self.altered_spec(lambda s: s['learning_intentions'][0].update(statement='Teach a worked example'))

    def test_eligibility_policy_mismatch(self):
        p = self.package(); e = self.eligible(p).model_copy(update={'policy_version': 'other/1'})
        with self.assertRaises(core.IngestionError): self.service.build_learning_spec(p, e)

    def test_spec_policy_mismatch(self):
        self.altered_spec(lambda s: s.update(policy_sha256='0' * 64))

    def test_unsupported_curriculum_profile(self):
        p = self.package().model_dump(mode='json'); p['target']['profile'] = 'unknown'
        self.assertEqual(self.eligible(p).status, 'UNSUPPORTED')

    def test_cross_tier_binding_substitution(self):
        s = self.spec(self.package('higher', '2.8', 'B')).model_dump(mode='json')
        s['canonical_semantics'][0]['source_id'] = 'EDX-4MA1-F-2.8-E'
        self.assertFalse(self.service.validate_learning_spec(s).valid)

    def test_missing_provenance(self):
        self.altered_spec(lambda s: s['learning_intentions'][0].pop('provenance'))

    def test_false_trusted_snapshot_classification(self):
        self.altered_spec(lambda s: s['canonical_semantics'][0]['provenance'].update(classifications=['TRUSTED_SNAPSHOT']))

    def test_model_content_not_source_derived(self):
        self.altered_spec(lambda s: s['learning_intentions'][0]['provenance'].update(classifications=['SOURCE_DERIVED']))

    def test_false_publication(self):
        self.altered_spec(lambda s: s['governance_state'].update(published=True))

    def test_warning_removed(self):
        self.altered_spec(lambda s: s.update(warnings=[]))

    def test_stored_spec_tampered(self):
        receipt = self.service.persist(self.spec())
        path = self.service.storage.safe(receipt.spec_id, 'learning-specification.json'); raw = path.read_bytes()
        try:
            path.write_bytes(raw + b' ')
            with self.assertRaises(core.IngestionError): self.service.read_learning_spec(receipt.spec_id)
        finally: path.write_bytes(raw)

    def test_stored_construction_input_tampered(self):
        receipt = self.service.persist(self.spec())
        path = self.service.storage.safe(receipt.spec_id, 'construction-input.json'); raw = path.read_bytes()
        try:
            path.write_bytes(raw + b' ')
            with self.assertRaises(core.IngestionError): self.service.read_learning_spec(receipt.spec_id)
        finally: path.write_bytes(raw)

    def test_stale_eligibility_missing_objective_row(self):
        p = self.package(); e = self.eligible(p).model_copy(update={'objective_results': []})
        with self.assertRaises(core.IngestionError): self.service.build_learning_spec(p, e)

    def test_provider_not_called(self):
        with patch.object(core, 'live_parse', side_effect=AssertionError('No provider')):
            s = self.spec(); self.assertEqual(s.governance_state.model_calls, 0)

    def test_path_traversal_rejected(self):
        with self.assertRaises(core.IngestionError): self.service.read_learning_spec('../x')
