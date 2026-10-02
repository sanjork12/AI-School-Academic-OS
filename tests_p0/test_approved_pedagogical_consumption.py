"""Real approved-pack consumption; no review writes or provider access."""
import sys,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.append(str(ROOT/'tmp/p6ui-deps'))
from academic_os.curriculum_ingestion.service import IngestionService,serial
from academic_os.curriculum_capability.service import AcademicCapabilityService
from academic_os.governed_learning.service import GovernedLearningService
from academic_os.pedagogy_evidence.service import PedagogicalEvidenceService
from academic_os.pedagogy_evidence.models import Pack
from academic_os.pedagogy_evidence.validation import hash_of
from academic_os.governed_pedagogy.service import GovernedPedagogyService
from academic_os.governed_pedagogy.consumer import consume,validate_consumed
from academic_os.governed_pedagogy import authoring

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def real_context():
    module_spec=importlib.util.spec_from_file_location('historical_human_review_gateway',ROOT/'output/p6ui5c_human_pedagogical_review/record_review.py')
    gateway=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(gateway)
    key=gateway.dpapi(gateway.KEY.read_bytes(),True)
    ingestion=IngestionService();learning=GovernedLearningService(AcademicCapabilityService(ingestion),ROOT/'output/p6ui4_learning_specification/specifications')
    authority=PedagogicalEvidenceService(learning,ROOT/'output/p6ui5c_human_pedagogical_review/review-store',reviewer_keys={gateway.REVIEWER:key},domain='HUMAN_REVIEW')
    pack=Pack.model_validate(read(ROOT/'output/p6ui5c_human_pedagogical_review/approved-evidence-pack.json'))
    spec=learning.read_learning_spec(pack.proposal.brief.learning_spec_hash)
    return ingestion,learning,authority,pack,spec

MUTATIONS={
 'wrong-target':(['proposal','source_id'],'EDX-4MA1-F-2.8-E'),
 'wrong-tier':(['proposal','tier'],'Higher'),
 'stale-learning-hash':(['proposal','brief','learning_spec_hash'],'0'*64),
 'another-proposal':(['review_receipt','review','proposal_hash'],'0'*64),
 'review-hash':(['review_receipt','semantic_hash'],'0'*64),
 'component-rejected':(['review_receipt','review','decisions',0,'decision'],'REJECT'),
 'component-revise':(['review_receipt','review','decisions',0,'decision'],'REVISE'),
 'success-criterion':(['proposal','success_criteria',0,'quality_or_completion_rule'],'SYMBOL_MATCHES_STATED_RELATION'),
 'activity-constraint':(['proposal','activity_scope',0,'response_mode'],'SYMBOL_SELECTION'),
 'check-alignment':(['proposal','check_alignment',0,'criterion_id'],'SC-99'),
 'adapter':(['proposal','pedagogical_adapter','action_meaning'],'Calculate standard deviation'),
 'unsupported-family':(['proposal','pedagogical_adapter','candidate_role_families'],['CALCULATION_CHECK']),
 'warning-removed':(['proposal','brief','source_learning_spec','warnings'],[]),
 'forged-pack':(['evidence_identity'],'0'*64),
 'signature-forged':(['review_receipt','signature'],'0'*64),
}
def mutations(pack):
    for name,(path,value) in MUTATIONS.items():
        raw=pack.model_dump(mode='json');node=raw
        for k in path[:-1]:node=node[k]
        node[path[-1]]=value
        yield name,raw

class ConsumptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.net=patch('socket.socket.connect',side_effect=AssertionError('No network'));cls.net.start()
        cls.ingestion,cls.learning,cls.authority,cls.pack,cls.spec=real_context()
    @classmethod
    def tearDownClass(cls):cls.ingestion.close();cls.net.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'tmp');self.addCleanup(self.temp.cleanup)
        self.s=GovernedPedagogyService(self.learning,self.temp.name,evidence_service=self.authority)
    def built(self):
        e=self.s.evaluate_pedagogical_spec_eligibility(self.spec,approved_pack=self.pack)
        return self.s.build_pedagogical_spec(self.spec,e,approved_pack=self.pack)
    def test_real_pack_valid(self):self.assertTrue(self.authority.validate_pedagogical_evidence_pack(self.pack)['valid'])
    def test_consumer_exact_and_independent(self):
        c=consume(self.spec,self.pack,self.authority)
        with patch('academic_os.governed_pedagogy.consumer.consume',side_effect=AssertionError('No constructor')):
            self.assertEqual(validate_consumed(c,self.spec,self.authority),c)
        for k in ('success_criteria','activity_scope','check_alignment','pedagogical_adapter'):self.assertEqual(getattr(c,k),getattr(self.pack.proposal,k))
    def test_four_required_evidence_and_warnings(self):
        e=self.s.evaluate_pedagogical_spec_eligibility(self.spec,approved_pack=self.pack)
        self.assertEqual(e.status,'ELIGIBLE_WITH_WARNINGS');self.assertEqual(e.missing_requirements,[])
        for r in e.requirements:
            if r.key in ('success_criteria','activity_scope','check_alignment','pedagogical_adapter'):
                self.assertTrue(r.required);self.assertEqual(r.status,'AVAILABLE');self.assertIn('APPROVED_PEDAGOGICAL_EVIDENCE',r.provenance.classifications)
        self.assertEqual(e.warnings[:len(self.spec.warnings)],self.spec.warnings)
        self.assertTrue(self.s.validate_pedagogical_eligibility(e,self.spec,approved_pack=self.pack).valid)
    def test_no_pack_still_review_required(self):self.assertEqual(self.s.evaluate_pedagogical_spec_eligibility(self.spec).status,'REVIEW_REQUIRED')
    def test_negative_packs(self):
        for name,value in mutations(self.pack):
            with self.subTest(name=name):self.assertEqual(self.s.evaluate_pedagogical_spec_eligibility(self.spec,approved_pack=value).status,'BLOCKED')
    def test_cross_target_reuse(self):
        other=self.learning.read_learning_spec('3a9e88369d5e66e1ce7b9aee74526bc75e474b16499ddcf1ada5870802515584')
        self.assertEqual(self.s.evaluate_pedagogical_spec_eligibility(other,approved_pack=self.pack).status,'BLOCKED')
    def test_validation_boolean_bypass(self):
        bad=dict(mutations(self.pack))['signature-forged']
        with patch.object(self.authority,'validate_pedagogical_evidence_pack',return_value={'valid':True}):
            self.assertEqual(self.s.evaluate_pedagogical_spec_eligibility(self.spec,approved_pack=bad).status,'BLOCKED')
    def test_no_authority(self):self.assertEqual(GovernedPedagogyService(self.learning).evaluate_pedagogical_spec_eligibility(self.spec,approved_pack=self.pack).status,'BLOCKED')
    def test_stale_eligibility_cannot_construct(self):
        old=self.s.evaluate_pedagogical_spec_eligibility(self.spec)
        with self.assertRaises(Exception):self.s.build_pedagogical_spec(self.spec,old,approved_pack=self.pack)
    def test_deterministic_and_replay(self):
        a=self.built();b=self.built();self.assertEqual(serial(a),serial(b))
        identity=self.s.persist_pedagogical_spec(a);self.assertEqual(self.s.read_constructed_spec(identity),a)
    def test_independent_spec_validator(self):
        spec=self.built()
        with patch.object(self.s,'build_pedagogical_spec',side_effect=AssertionError('No construction')),patch('academic_os.governed_pedagogy.consumer.consume',side_effect=AssertionError('No consumer construction')):
            self.assertTrue(self.s.validate_pedagogical_spec(spec).valid)
    def test_invented_role_mapping(self):
        raw=self.built().model_dump(mode='json');raw['role_contract']['roles'][-1]['legacy_role_ids']=['SL-13']
        self.assertFalse(self.s.validate_pedagogical_spec(raw).valid)
    def test_spec_warning_removed(self):
        raw=self.built().model_dump(mode='json');raw['warnings']=[]
        self.assertFalse(self.s.validate_pedagogical_spec(raw).valid)
    def test_consumer_component_tamper(self):
        raw=self.built().model_dump(mode='json');raw['approved_evidence']['check_alignment'][0]['criterion_id']='SC-99'
        self.assertFalse(self.s.validate_pedagogical_spec(raw).valid)
    def test_authoring_gate_independent(self):
        spec=self.built();gate=self.s.evaluate_lesson_authoring_eligibility(spec)
        self.assertEqual(gate.status,'BLOCKED');self.assertIn('UNSUPPORTED_REQUIRED_ROLE:scope_framing',gate.missing_requirements)
        self.assertNotIn('REPRESENTATION_CONTENT_VALIDATOR',gate.missing_requirements);self.assertNotIn('CONCEPT_CHECK_CONTENT_VALIDATOR',gate.missing_requirements)
        self.assertTrue(self.s.validate_lesson_authoring_eligibility(gate,spec)['valid'])
        changed=gate.model_copy(update={'status':'ELIGIBLE'})
        self.assertFalse(self.s.validate_lesson_authoring_eligibility(changed,spec)['valid'])
    def test_role_contract_bounded(self):
        spec=self.built();roles=[r for r in spec.role_contract.roles if r.role_key.startswith('approved_')]
        self.assertEqual({r.family for r in roles},{'REPRESENTATION','CONCEPT_CHECK'})
        self.assertTrue(all(not r.enabled_for_authoring and not r.legacy_role_ids for r in roles))
        self.assertFalse(spec.teaching_phases)
    def test_consumer_hash_tamper(self):
        c=consume(self.spec,self.pack,self.authority).model_dump(mode='json');c['review_hash']='0'*64
        with self.assertRaises(ValueError):validate_consumed(c,self.spec,self.authority)
    def test_eligibility_tamper(self):
        e=self.s.evaluate_pedagogical_spec_eligibility(self.spec,approved_pack=self.pack).model_dump(mode='json');e['requirements'][3]['required']=False
        self.assertFalse(self.s.validate_pedagogical_eligibility(e,self.spec,approved_pack=self.pack).valid)

if __name__=='__main__':unittest.main()
