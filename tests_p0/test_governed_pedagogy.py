"""Real Topic 2 qualification and invalid contract fixtures; no generated content."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.service import IngestionService, serial
from academic_os.curriculum_capability.service import AcademicCapabilityService
from academic_os.governed_learning.service import GovernedLearningService
from academic_os.governed_pedagogy.service import GovernedPedagogyService
from academic_os.governed_pedagogy.models import GovernedPedagogicalSpecification, Governance
from academic_os.governed_pedagogy.policy import VERSION

ROOT = Path(__file__).resolve().parents[1]
LEARNING_ROOT = ROOT / 'output/p6ui4_learning_specification'


class PedagogyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        cls.ingestion = IngestionService()
        cls.learning = GovernedLearningService(AcademicCapabilityService(cls.ingestion), LEARNING_ROOT / 'specifications')
        acceptance = json.loads((LEARNING_ROOT / 'offline-acceptance.json').read_text(encoding='utf-8'))
        cls.spec_id = acceptance['scopes']['first-objective']['receipt']['spec_id']
        cls.spec = cls.learning.read_learning_spec(cls.spec_id)
        cls.service = GovernedPedagogyService(cls.learning, cls.temp.name)
        cls.net = patch('socket.socket.connect', side_effect=AssertionError('No network')); cls.net.start()
        cls.db = core.digest((ROOT / 'var/p0_q2.sqlite3').read_bytes())

    @classmethod
    def tearDownClass(cls):
        cls.net.stop(); cls.ingestion.close(); cls.temp.cleanup()
        assert cls.db == core.digest((ROOT / 'var/p0_q2.sqlite3').read_bytes())

    def qualification(self): return self.service.qualify(self.spec)

    def invalid_spec_fixture(self):
        """TEST ONLY: never a constructed/accepted pedagogical specification."""
        q = self.qualification()
        return GovernedPedagogicalSpecification(learning_spec_hash=q.eligibility.learning_spec_hash,
            source_learning_spec=self.spec, eligibility=q.eligibility, policy_version=VERSION,
            learning_scope=self.spec.curriculum_scope,
            instructional_goal_refs=[i.intention_id for i in self.spec.learning_intentions], teaching_phases=[],
            role_contract=q.eligibility.role_contract, activity_constraints=q.eligibility.requirements,
            warnings=q.eligibility.warnings, governance_state=Governance()).model_dump(mode='json')

    def bad_learning(self, change):
        s = self.spec.model_dump(mode='json'); change(s)
        self.assertIn(self.service.evaluate_pedagogical_spec_eligibility(s).status, ('BLOCKED', 'UNSUPPORTED'))

    def bad_qualification(self, change, code=None):
        q = self.qualification().model_dump(mode='json'); change(q)
        result = self.service.validate_qualification(q)
        self.assertFalse(result.valid)
        if code: self.assertIn(code, result.errors)

    def test_primary_real_scope_requires_review(self):
        e = self.service.evaluate_pedagogical_spec_eligibility(self.spec)
        self.assertEqual(e.status, 'REVIEW_REQUIRED'); self.assertTrue(e.binding_valid)
        self.assertEqual(self.spec.curriculum_scope.source_ids, ['EDX-4MA1-F-2.8-A'])
        self.assertEqual(e.missing_requirements, ['SUCCESS_CRITERIA_REQUIRED', 'ACTIVITY_SCOPE_REQUIRED', 'CHECK_ALIGNMENT_REQUIRED', 'PEDAGOGICAL_AUTHORING_REQUIRED'])

    def test_optional_inputs_not_mandatory(self):
        e = self.service.evaluate_pedagogical_spec_eligibility(self.spec)
        rows = {r.key: r for r in e.requirements}
        for key in ('prerequisites', 'misconceptions', 'assessment_examples', 'concept_knowledge'):
            self.assertFalse(rows[key].required)
            self.assertEqual(rows[key].status, 'OPTIONAL_UNAVAILABLE')

    def test_no_forced_construction(self):
        e = self.service.evaluate_pedagogical_spec_eligibility(self.spec)
        with self.assertRaises(core.IngestionError) as exc: self.service.build_pedagogical_spec(self.spec, e)
        self.assertEqual(exc.exception.code, 'PEDAGOGICAL_INPUTS_INCOMPLETE')

    def test_action_preserved_not_calculation_inferred(self):
        e = self.service.evaluate_pedagogical_spec_eligibility(self.spec)
        self.assertEqual(e.actions[0].action_meaning, self.spec.canonical_semantics[0].description)
        self.assertEqual(e.actions[0].semantic_role, 'REVIEWED_CAPABILITY_MEANING_NOT_A_TASK_GRAPH')

    def test_role_partition(self):
        r = self.qualification().eligibility.role_contract
        self.assertEqual(r.required_roles, ['scope_framing'])
        self.assertEqual(r.optional_roles, ['non_assessing_summary'])
        self.assertEqual(len(r.legacy_role_compatibility), 15)
        self.assertTrue(all(v.startswith('UNSUPPORTED') for v in r.legacy_role_compatibility.values()))
        self.assertTrue(all(not x.enabled_for_authoring for x in r.roles)); self.assertEqual(r.mandatory_sequence, [])

    def test_warning_propagation(self):
        q = self.qualification()
        self.assertEqual(q.eligibility.warnings[:len(self.spec.warnings)], self.spec.warnings)
        self.assertEqual(q.lesson_authoring_eligibility.warnings, q.eligibility.warnings)

    def test_authoring_gate(self):
        e = self.service.evaluate_lesson_authoring_eligibility(learning_spec=self.spec)
        self.assertEqual(e.status, 'BLOCKED'); self.assertIsNone(e.pedagogical_spec_hash)
        self.assertIn('ROLE_SPECIFIC_CONTENT_VALIDATORS_REQUIRED', e.missing_requirements)

    def test_deterministic_bytes_hash(self):
        a = self.qualification(); b = self.qualification()
        self.assertEqual(serial(a), serial(b))
        self.assertEqual(self.service.validate_qualification(a), self.service.validate_qualification(b))

    def test_independent_validator(self):
        q = self.qualification()
        with patch.object(self.service, 'qualify', side_effect=AssertionError('No constructor')):
            self.assertTrue(self.service.validate_qualification(q).valid)

    def test_receipt_restart_no_overwrite(self):
        q = self.qualification(); receipt = self.service.persist_qualification(q)
        self.assertEqual(receipt, self.service.persist_qualification(q))
        other = GovernedPedagogyService(self.learning, self.temp.name)
        self.assertEqual(other.read_qualification(receipt['qualification_id']), q)
        with self.assertRaises(core.IngestionError) as e: other.read_pedagogical_spec(receipt['qualification_id'])
        self.assertEqual(e.exception.code, 'NOT_CONSTRUCTED')
        self.assertFalse(self.service.storage.safe(receipt['qualification_id'], 'pedagogical-specification.json').exists())

    def test_stale_learning_hash(self):
        e = self.service.evaluate_pedagogical_spec_eligibility(self.spec, '0' * 64)
        self.assertEqual(e.status, 'BLOCKED'); self.assertEqual(e.reason_codes, ['STALE_LEARNING_HASH'])

    def test_wrong_tier(self): self.bad_learning(lambda s: s['curriculum_scope'].update(tier='Higher'))
    def test_objective_substitution(self): self.bad_learning(lambda s: s['learning_objectives'][0].update(source_id='EDX-4MA1-H-2.8-B'))
    def test_invented_success_criteria(self): self.bad_learning(lambda s: s['success_criteria'].update(claims=['Recognise 5 of 5 symbols']))
    def test_invented_misconception(self): self.bad_learning(lambda s: s['known_misconceptions'].update(claims=['Reverse inequality signs']))
    def test_invented_prerequisite(self): self.bad_learning(lambda s: s['prerequisites'].update(claims=['Must know algebra']))
    def test_invented_activity_relation(self): self.bad_learning(lambda s: s['concept_skill_task_relations'].update(claims=['Sort cards then calculate']))

    def test_missing_eligibility(self):
        with self.assertRaises(core.IngestionError): self.service.build_pedagogical_spec(self.spec, None)

    def test_forged_eligible_status(self):
        e = self.service.evaluate_pedagogical_spec_eligibility(self.spec).model_copy(update={'status': 'ELIGIBLE', 'missing_requirements': []})
        with self.assertRaises(core.IngestionError) as exc: self.service.build_pedagogical_spec(self.spec, e)
        self.assertEqual(exc.exception.code, 'STALE_ELIGIBILITY')

    def test_sd_role_copied(self):
        self.bad_qualification(lambda q: q['eligibility']['role_contract']['legacy_role_compatibility'].update({'SL-11': 'SUPPORTED'}), 'UNSUPPORTED_STANDARD_DEVIATION_ROLE')

    def test_role_substitution(self):
        self.bad_qualification(lambda q: q['eligibility']['role_contract']['roles'][0].update(role_key='calculation_method'), 'ROLE_SUBSTITUTION_OR_OMISSION')

    def test_required_role_removed(self):
        self.bad_qualification(lambda q: q['eligibility']['role_contract'].update(required_roles=[]), 'ROLE_PARTITION_CHANGED')

    def test_optional_role_promoted(self):
        self.bad_qualification(lambda q: q['eligibility']['role_contract']['roles'][1].update(requirement='required'), 'ROLE_REQUIREMENT_CHANGED')

    def test_forged_provenance(self):
        self.bad_qualification(lambda q: q['eligibility']['role_contract']['roles'][0]['provenance'].update(classifications=['TRUSTED_REFERENCE']))

    def test_policy_version_mismatch(self):
        self.bad_qualification(lambda q: q['eligibility'].update(policy_version='other'))

    def test_missing_evidence_hidden(self):
        self.bad_qualification(lambda q: q['eligibility'].update(missing_requirements=[]))

    def test_warning_removed(self): self.bad_qualification(lambda q: q['eligibility'].update(warnings=[]))
    def test_authoring_enabled(self): self.bad_qualification(lambda q: q['lesson_authoring_eligibility'].update(status='ELIGIBLE'))

    def test_pedagogical_spec_fixture_rejected(self):
        result = self.service.validate_pedagogical_spec(self.invalid_spec_fixture())
        self.assertFalse(result.valid); self.assertIn('PEDAGOGICAL_INPUTS_INCOMPLETE', result.errors)

    def test_pedagogical_spec_hash_tampering(self):
        s = self.invalid_spec_fixture(); s['learning_spec_hash'] = '0' * 64
        self.assertIn('LEARNING_HASH_MISMATCH', self.service.validate_pedagogical_spec(s).errors)

    def test_pedagogical_spec_tier_tampering(self):
        s = self.invalid_spec_fixture(); s['learning_scope']['tier'] = 'Higher'
        self.assertIn('SOURCE_TIER_SCOPE_MISMATCH', self.service.validate_pedagogical_spec(s).errors)

    def test_pedagogical_spec_role_tampering(self):
        s = self.invalid_spec_fixture(); s['role_contract']['required_roles'] = []
        self.assertIn('ROLE_PARTITION_CHANGED', self.service.validate_pedagogical_spec(s).errors)

    def test_unsupported_teaching_phases(self):
        s = self.invalid_spec_fixture()
        s['teaching_phases'] = [dict(phase_key='sd-calculation', role_refs=['SL-11'], learning_intention_ids=s['instructional_goal_refs'], provenance=s['role_contract']['roles'][0]['provenance'])]
        self.assertIn('UNSUPPORTED_TEACHING_PHASES', self.service.validate_pedagogical_spec(s).errors)

    def test_pedagogical_spec_cannot_open_authoring(self):
        self.assertEqual(self.service.evaluate_lesson_authoring_eligibility(self.invalid_spec_fixture()).status, 'BLOCKED')

    def test_stored_tamper(self):
        receipt = self.service.persist_qualification(self.qualification())
        path = self.service.storage.safe(receipt['qualification_id'], 'qualification.json'); original = path.read_bytes()
        try:
            path.write_bytes(original + b' ')
            with self.assertRaises(core.IngestionError): self.service.read_qualification(receipt['qualification_id'])
        finally: path.write_bytes(original)

    def test_path_escape(self):
        with self.assertRaises(core.IngestionError): self.service.read_qualification('../escape')

    def test_no_provider_or_parse(self):
        with patch.object(core, 'live_parse', side_effect=AssertionError('No model')), patch.object(self.ingestion, 'submit_parse', side_effect=AssertionError('No parse')):
            self.assertEqual(self.qualification().governance_state.model_calls, 0)

    def test_unsupported_schema(self):
        s = self.spec.model_dump(mode='json'); s['schema_version'] = 'other/1'
        self.assertEqual(self.service.evaluate_pedagogical_spec_eligibility(s).status, 'UNSUPPORTED')
