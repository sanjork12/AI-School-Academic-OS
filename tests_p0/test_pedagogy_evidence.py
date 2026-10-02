"""Synthetic contract tests. Test credentials never establish a human review."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]/'tmp/p6ui-deps'))
import copy
import tempfile
import unittest
from unittest.mock import patch
from academic_os.curriculum_ingestion.service import IngestionService
from academic_os.curriculum_capability.service import AcademicCapabilityService
from academic_os.governed_learning.service import GovernedLearningService
from academic_os.governed_pedagogy.service import GovernedPedagogyService
from academic_os.pedagogy_evidence.service import PedagogicalEvidenceService, signature
from academic_os.pedagogy_evidence.models import Proposal, Review
from academic_os.pedagogy_evidence.validation import hash_of, COMPONENTS
from academic_os.pedagogy_evidence.integration import consume_approved_evidence

ROOT = Path(__file__).resolve().parents[1]
SPEC_ID = '263509477cf795f3c47a4ab68edc2a34e379a664880c6cab4254ad87b9b4cd1e'
TEST_KEY = b'SYNTHETIC-TEST-ONLY-NOT-A-HUMAN-KEY'

def fixture(brief):
    b=brief.model_dump(mode='json'); s=brief.source_learning_spec; obj=s.learning_objectives[0]; i=s.learning_intentions[0]; c=s.canonical_semantics[0]
    basis=dict(origin='SYNTHETIC_OFFLINE',brief_hash=hash_of(brief),source_id=obj.source_id,intention_id=i.intention_id)
    return Proposal(brief=b,source_id=obj.source_id,tier=obj.tier,source_wording=obj.official_text,
        success_criteria=[dict(criterion_id='SC-1',linked_learning_intention=i.intention_id,observable_student_action='INTERPRET_SYMBOL',scope='REVIEWED_INEQUALITY_SYMBOLS_ONLY',conditions='SYMBOL_REPRESENTATION',quality_or_completion_rule='MEANING_MATCHES_REVIEWED_SYMBOL',evidence_basis=basis)],
        activity_scope=[dict(activity_id='ACT-1',category='REPRESENTATION',criterion_ids=['SC-1'],response_mode='SYMBOL_INTERPRETATION',scope='REVIEWED_INEQUALITY_SYMBOLS_ONLY',evidence_basis=basis)],
        check_alignment=[dict(check_id='CHK-1',intention_id=i.intention_id,criterion_id='SC-1',activity_id='ACT-1',evidence_form='SYMBOL_INTERPRETATION',prohibited_shortcut='NO_COMPLETION_WITHOUT_OBSERVABLE_RESPONSE',evidence_basis=basis)],
        pedagogical_adapter=dict(canonical_id=c.canonical_id,action_meaning=c.description,criterion_ids=['SC-1'],activity_ids=['ACT-1'],check_ids=['CHK-1'],candidate_role_families=['REPRESENTATION','CONCEPT_CHECK'],evidence_basis=basis))

def negatives(p):
    mutations={
        'vague-success-criterion':(['success_criteria',0,'observable_student_action'],'Students should understand inequalities.'),
        'wrong-objective':(['source_id'],'EDX-4MA1-F-2.8-E'),
        'wrong-tier':(['tier'],'higher'),
        'unsupported-activity':(['activity_scope',0,'category'],'CALCULATION'),
        'check-without-criterion':(['check_alignment',0,'criterion_id'],'SC-99'),
        'criterion-without-intention':(['success_criteria',0,'linked_learning_intention'],''),
        'forged-source-provenance':(['success_criteria',0,'evidence_basis','classification'],'SOURCE_DERIVED'),
        'forged-approval':(['status'],'APPROVED'),
        'unsupported-role':(['pedagogical_adapter','candidate_role_families'],['SL-05']),
        'sd-method':(['pedagogical_adapter','action_meaning'],'Calculate standard deviation using summary statistics'),
        'stale-learning-hash':(['brief','learning_spec_hash'],'0'*64),
        'changed-source':(['source_wording'],'Understand and use symbols'),
        'canonical-as-official':(['source_wording'],p.brief.source_learning_spec.canonical_semantics[0].description),
        'criterion-rule-mismatch':(['success_criteria',0,'quality_or_completion_rule'],'SYMBOL_MATCHES_STATED_RELATION'),
        'check-mode-mismatch':(['check_alignment',0,'evidence_form'],'SYMBOL_SELECTION'),
        'activity-mode-mismatch':(['activity_scope',0,'response_mode'],'SYMBOL_SELECTION'),
        'lesson-prose':(['activity_scope',0,'lesson_content'],'Teach the class...'),
        'forged-approval-field':(['approved'],True),
        'duplicate-role':(['pedagogical_adapter','candidate_role_families'],['REPRESENTATION','CONCEPT_CHECK','CONCEPT_CHECK']),
    }
    result={}
    for name,(path,value) in mutations.items():
        raw=p.model_dump(mode='json'); node=raw
        for key in path[:-1]: node=node[key]
        node[path[-1]]=value; result[name]=raw
    return result

def review_for(p, decision='APPROVE', domain='SYNTHETIC_TEST_ONLY'):
    return Review(proposal_hash=hash_of(p),reviewer_id='offline-test-reviewer',domain=domain,
        decisions=[dict(component=c,decision=decision,rationale='Synthetic contract test only; not a real pedagogical review.') for c in COMPONENTS])

class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.net=patch('socket.socket.connect',side_effect=AssertionError('No network')); cls.net.start()
        cls.ingestion=IngestionService()
        cls.learning=GovernedLearningService(AcademicCapabilityService(cls.ingestion),ROOT/'output/p6ui4_learning_specification/specifications')
        cls.spec=cls.learning.read_learning_spec(SPEC_ID)
    @classmethod
    def tearDownClass(cls): cls.ingestion.close(); cls.net.stop()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'tmp'); self.addCleanup(self.tmp.cleanup)
        self.s=PedagogicalEvidenceService(self.learning,self.tmp.name,reviewer_keys={'offline-test-reviewer':TEST_KEY},domain='SYNTHETIC_TEST_ONLY')
        self.b=self.s.build_pedagogical_authoring_brief(self.spec); self.p=fixture(self.b)
    def approve(self,p=None):
        p=p or self.p; r=review_for(p)
        receipt=self.s.record_pedagogical_review(p,r,reviewer_signature=signature(r,TEST_KEY))
        return self.s.build_approved_pedagogical_evidence_pack(p,receipt)
    def test_deterministic_brief(self): self.assertEqual(self.b,self.s.build_pedagogical_authoring_brief(self.spec))
    def test_positive_and_presentation(self):
        self.assertTrue(self.s.validate_pedagogical_proposal(self.p,self.b)['valid'])
        self.assertEqual(self.s.present_for_review(self.p)['status'],'AWAITING_HUMAN_REVIEW')
    def test_negative_fixtures(self):
        for name,p in negatives(self.p).items():
            with self.subTest(name=name): self.assertFalse(self.s.validate_pedagogical_proposal(p,self.b)['valid'])
    def test_changed_learning_after_brief(self):
        b=self.b.model_dump(mode='json'); b['source_learning_spec']['learning_objectives'][0]['official_text']='Changed'
        self.assertFalse(self.s.validate_pedagogical_proposal(self.p,b)['valid'])
    def test_criterion_modified_after_validation(self):
        self.assertTrue(self.s.validate_pedagogical_proposal(self.p,self.b)['valid'])
        p=negatives(self.p)['criterion-rule-mismatch']
        with self.assertRaises(ValueError): self.s.present_for_review(p)
    def test_pack_and_integration(self):
        pack=self.approve(); self.assertTrue(self.s.validate_pedagogical_evidence_pack(pack)['valid'])
        integrated=consume_approved_evidence(self.spec,pack,self.s,GovernedPedagogyService(self.learning))
        self.assertEqual(set(integrated['supplied_requirements']),set(COMPONENTS))
        self.assertEqual(integrated['lesson_authoring'],'BLOCKED')
        self.assertEqual(integrated['existing_p6ui5_eligibility']['status'],'REVIEW_REQUIRED')
    def test_review_decisions(self):
        for decision in ('REJECT','REVISE','DEFER'):
            r=review_for(self.p,decision); receipt=self.s.record_pedagogical_review(self.p,r,reviewer_signature=signature(r,TEST_KEY))
            with self.assertRaises(ValueError): self.s.build_approved_pedagogical_evidence_pack(self.p,receipt)
    def test_mixed_components(self):
        r=review_for(self.p).model_dump(mode='json'); r['decisions'][1]['decision']='REVISE'; r=Review.model_validate(r)
        receipt=self.s.record_pedagogical_review(self.p,r,reviewer_signature=signature(r,TEST_KEY))
        with self.assertRaises(ValueError): self.s.build_approved_pedagogical_evidence_pack(self.p,receipt)
    def test_forged_review(self):
        with self.assertRaises(ValueError): self.s.record_pedagogical_review(self.p,review_for(self.p),reviewer_signature='0'*64)
    def test_review_wrong_hash(self):
        r=review_for(self.p).model_copy(update={'proposal_hash':'0'*64})
        with self.assertRaises(ValueError): self.s.record_pedagogical_review(self.p,r,reviewer_signature=signature(r,TEST_KEY))
    def test_changed_proposal_after_review(self):
        pack=self.approve(); raw=self.p.model_dump(mode='json'); raw['activity_scope'][0]['category']='CONCEPT_CHECK'
        # Still structurally valid; the exact approved bytes must nevertheless match.
        self.assertTrue(self.s.validate_pedagogical_proposal(raw,self.b)['valid'])
        with self.assertRaises(ValueError): self.s.build_approved_pedagogical_evidence_pack(raw,pack.review_receipt)
    def test_pack_mutations(self):
        pack=self.approve()
        for path,value in [(['evidence_identity'],'0'*64),(['proposal','check_alignment',0,'evidence_form'],'SYMBOL_SELECTION'),(['review_receipt','recorded_at'],'forged'),(['proposal','pedagogical_adapter','candidate_role_families'],['METHOD_INSTRUCTION'])]:
            raw=pack.model_dump(mode='json'); node=raw
            for k in path[:-1]: node=node[k]
            node[path[-1]]=value
            self.assertFalse(self.s.validate_pedagogical_evidence_pack(raw)['valid'])
    def test_no_review_authority_default(self):
        s=PedagogicalEvidenceService(self.learning,Path(self.tmp.name)/'real')
        with self.assertRaises(ValueError): s.record_pedagogical_review(self.p,review_for(self.p),reviewer_signature=signature(review_for(self.p),TEST_KEY))
    def test_synthetic_receipt_cannot_cross_domain(self):
        pack=self.approve(); s=PedagogicalEvidenceService(self.learning,self.tmp.name,reviewer_keys={'offline-test-reviewer':TEST_KEY})
        self.assertFalse(s.validate_pedagogical_evidence_pack(pack)['valid'])
        r=review_for(self.p,domain='HUMAN_REVIEW')
        with self.assertRaises(ValueError): s.record_pedagogical_review(self.p,r,reviewer_signature=signature(r,TEST_KEY))
    def test_semantic_identity_excludes_receipt_time(self):
        pack=self.approve()
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as other:
            s=PedagogicalEvidenceService(self.learning,other,reviewer_keys={'offline-test-reviewer':TEST_KEY},domain='SYNTHETIC_TEST_ONLY')
            r=review_for(self.p); receipt=s.record_pedagogical_review(self.p,r,reviewer_signature=signature(r,TEST_KEY))
            self.assertEqual(pack.evidence_identity,s.build_approved_pedagogical_evidence_pack(self.p,receipt).evidence_identity)
    def test_validator_does_not_call_builder(self):
        with patch.object(self.s,'build_pedagogical_authoring_brief',side_effect=AssertionError('builder')):
            self.assertTrue(self.s.validate_pedagogical_proposal(self.p,self.b)['valid'])
    def test_pack_validator_does_not_call_pack_builder(self):
        pack=self.approve()
        with patch.object(self.s,'build_approved_pedagogical_evidence_pack',side_effect=AssertionError('builder')):
            self.assertTrue(self.s.validate_pedagogical_evidence_pack(pack)['valid'])
    def test_pack_persistence_and_replay(self):
        pack=self.approve(); identity=self.s.persist_evidence_pack(pack)
        self.assertEqual(self.s.read_evidence_pack(identity),pack)
        self.assertEqual(self.s.persist_evidence_pack(pack),identity)
        path=Path(self.tmp.name)/'packs'/(identity+'.json')
        raw=pack.model_dump(mode='json'); raw['proposal']['source_wording']='changed'
        import json
        path.write_text(json.dumps(raw),encoding='utf-8')
        with self.assertRaises(ValueError): self.s.read_evidence_pack(identity)
    def test_review_requires_all_components(self):
        r=review_for(self.p).model_copy(update={'decisions':review_for(self.p).decisions[:3]})
        with self.assertRaises(ValueError): self.s.record_pedagogical_review(self.p,r,reviewer_signature=signature(r,TEST_KEY))
    def test_recorded_receipt_cannot_be_fabricated(self):
        pack=self.approve()
        other=PedagogicalEvidenceService(self.learning,Path(self.tmp.name)/'other',reviewer_keys={'offline-test-reviewer':TEST_KEY},domain='SYNTHETIC_TEST_ONLY')
        self.assertFalse(other.validate_pedagogical_evidence_pack(pack)['valid'])

if __name__=='__main__': unittest.main()
