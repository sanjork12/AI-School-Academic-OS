"""Real governed framing; no model or review writes."""
import unittest
from unittest.mock import patch
from tests_p0.test_generic_role_authoring import context
from academic_os.generic_role_authoring.scope import build_scope_framing,validate_scope_framing,build_lesson_authoring_plan
from academic_os.generic_role_authoring.scope_policy import identity
from academic_os.generic_role_authoring.policy import hash_of
from academic_os.generic_role_authoring.service import role_eligibility
from academic_os.governed_pedagogy.service import GovernedPedagogyService

def mutations(q):
    cases={
        'wrong-objective':(['binding','source_id'],'EDX-4MA1-F-2.8-E'),
        'wrong-tier':(['binding','tier'],'Higher'),
        'stale-learning':(['binding','learning_spec_hash'],'0'*64),
        'stale-pedagogy':(['binding','pedagogical_spec_hash'],'0'*64),
        'wrong-pack':(['binding','approved_pack_hash'],'0'*64),
        'solving':(['included_capabilities',0,'statement'],'Solve linear inequalities.'),
        'number-line':(['included_capabilities',0,'statement'],'Find number-line solution sets.'),
        'algebra':(['included_capabilities',0,'statement'],'Factor quadratic expressions.'),
        'source-repair':(['source_context','official_text'],q.reviewed_canonical.description),
        'warning-removed':(['warnings'],[]),
        'model-origin':(['provenance','lesson_scope_statement'],['MODEL_AUTHORED_CONTENT']),
        'forged-approval':(['human_approved'],True),
        'cross-objective':(['source_context','source_id'],'EDX-4MA1-F-2.8-E'),
        'altered-framing':(['lesson_scope_statement'],'Solve inequalities today.'),
        'exclusion-contradiction':(['excluded_capabilities',0,'capability'],'INTERPRET_SYMBOL'),
        'lost-exclusions':(['excluded_capabilities'],[]),
        'wrong-canonical':(['reviewed_canonical','description'],'Solve equations.'),
        'wrong-intention':(['learning_intention','intention_id'],'other'),
        'wrong-role-families':(['required_role_families'],['CALCULATION']),
        'forged-provenance':(['provenance'],{}),
        'criterion-tampered':(['included_capabilities',0,'criterion','criterion_id'],'other'),
        'pack-identity':(['binding','approved_pack_id'],'other'),
        'learning-identity':(['binding','learning_spec_id'],'other'),
    }
    for name,(path,value) in cases.items():
        raw=q.model_dump(mode='json');node=raw
        for k in path[:-1]:node=node[k]
        node[path[-1]]=value
        # Recompute identity: rejection must depend on evidence, not just checksum.
        raw['identity']=identity(raw)
        yield name,raw

class ScopeFramingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.net=patch('socket.socket.connect',side_effect=AssertionError('No network'));cls.net.start()
        cls.ingestion,cls.service,cls.spec=context();cls.q=build_scope_framing(cls.spec,cls.service)
    @classmethod
    def tearDownClass(cls):cls.ingestion.close();cls.net.stop()
    def test_real_positive(self):
        r=validate_scope_framing(self.q,self.spec,self.service);self.assertTrue(r['valid'],r)
        self.assertEqual([x.criterion for x in self.q.included_capabilities],self.spec.approved_evidence.success_criteria)
        self.assertNotEqual(self.q.source_context.official_text,self.q.reviewed_canonical.description)
        self.assertEqual(self.q.warnings,self.spec.warnings)
    def test_independent_validation(self):
        with patch('academic_os.generic_role_authoring.scope.build_scope_framing',side_effect=AssertionError('constructor forbidden')):
            self.assertTrue(validate_scope_framing(self.q,self.spec,self.service)['valid'])
    def test_negatives(self):
        for name,raw in mutations(self.q):
            with self.subTest(case=name):self.assertFalse(validate_scope_framing(raw,self.spec,self.service)['valid'])
    def test_missing_invalid_and_valid_gate(self):
        self.assertEqual(self.service.evaluate_lesson_authoring_eligibility(self.spec).status,'BLOCKED')
        self.assertEqual(self.service.evaluate_lesson_authoring_eligibility(self.spec,scope_framing={}).status,'BLOCKED')
        gate=self.service.evaluate_lesson_authoring_eligibility(self.spec,scope_framing=self.q)
        self.assertEqual(gate.status,'ELIGIBLE_WITH_WARNINGS');self.assertEqual(gate.missing_requirements,[])
        self.assertTrue(self.service.validate_lesson_authoring_eligibility(gate,self.spec,scope_framing=self.q)['valid'])
        self.assertFalse(self.service.validate_lesson_authoring_eligibility(gate,self.spec)['valid'])
    def test_after_validation_tamper(self):
        raw=self.q.model_dump(mode='json');gate=self.service.evaluate_lesson_authoring_eligibility(self.spec,scope_framing=raw)
        raw['warnings']=[];raw['identity']=identity(raw)
        self.assertEqual(self.service.evaluate_lesson_authoring_eligibility(self.spec,scope_framing=raw).status,'BLOCKED')
        self.assertFalse(self.service.validate_lesson_authoring_eligibility(gate,self.spec,scope_framing=raw)['valid'])
        with self.assertRaises(ValueError):build_lesson_authoring_plan(self.spec,raw,self.service)
    def test_deterministic_replay(self):
        r=validate_scope_framing(self.q,self.spec,self.service);p=build_lesson_authoring_plan(self.spec,self.q,self.service)
        for _ in range(2):
            self.assertEqual(hash_of(self.q),hash_of(build_scope_framing(self.spec,self.service)))
            self.assertEqual(r,validate_scope_framing(self.q.model_dump(mode='json'),self.spec,self.service))
            self.assertEqual(p,build_lesson_authoring_plan(self.spec,self.q,self.service))
    def test_role_dispositions(self):
        p=build_lesson_authoring_plan(self.spec,self.q,self.service)
        required=[r for r in p['roles'] if r['requirement']=='required']
        self.assertEqual([r['disposition'] for r in required].count('DETERMINISTIC_FRAMING'),1)
        self.assertEqual([r['disposition'] for r in required].count('AI_AUTHORABLE'),2)
        self.assertEqual(p['mandatory_sequence'],[]);self.assertFalse(p['content_generated'])
        for f in ('REPRESENTATION','CONCEPT_CHECK'):self.assertEqual(role_eligibility(self.spec,f,self.service)['status'],'ELIGIBLE_WITH_WARNINGS')
    def test_upstream_and_authority(self):
        raw=self.spec.model_dump(mode='json');raw['learning_scope']['tier']='Higher'
        self.assertFalse(validate_scope_framing(self.q,raw,self.service)['valid'])
        with self.assertRaises(ValueError):build_scope_framing(raw,self.service)
        unbound=GovernedPedagogyService(self.service.learning)
        self.assertFalse(validate_scope_framing(self.q,self.spec,unbound)['valid'])
    def test_identity_tamper(self):
        raw=self.q.model_dump(mode='json');raw['identity']='other'
        self.assertFalse(validate_scope_framing(raw,self.spec,self.service)['valid'])

if __name__=='__main__':unittest.main()
