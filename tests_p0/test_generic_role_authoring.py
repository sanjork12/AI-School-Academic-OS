"""Offline symbolic fixtures; none are claimed to be model generated."""
import sys,unittest,copy
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.append(str(ROOT/'tmp/p6ui-deps'))
from tests_p0.test_approved_pedagogical_consumption import real_context,read
from academic_os.governed_pedagogy.service import GovernedPedagogyService
from academic_os.generic_role_authoring.models import RepresentationCandidate,ConceptCheckCandidate
from academic_os.generic_role_authoring.brief import build_brief
from academic_os.generic_role_authoring.validation import validate_candidate,validate_brief
from academic_os.generic_role_authoring.service import compose,validate_composition,role_eligibility
from academic_os.generic_role_authoring.policy import hash_of,SYMBOL_MEANINGS

def context():
    ingestion,learning,authority,pack,ls=real_context()
    service=GovernedPedagogyService(learning,ROOT/'output/p6ui5d_approved_evidence_consumption/stored',evidence_service=authority)
    spec=service.read_constructed_spec('9a7f4737e52250b8141fc8b183e0f09861290d575a393c619ed9ba427582f40e')
    return ingestion,service,spec

def positive_fixtures(brief):
    rep=brief.binding.role_family=='REPRESENTATION'
    results=[];check=brief.check_alignments[0]
    for symbol in (['>','≥','≤'] if rep else ['>','<','≥']):
        content=(dict(instruction='Interpret the displayed inequality symbol.',symbol=symbol,response_mode='SYMBOL_INTERPRETATION',expected_meaning=SYMBOL_MEANINGS[symbol]) if rep else
                 dict(instruction='Select the symbol matching the stated meaning.',stated_meaning=SYMBOL_MEANINGS[symbol],choices=['>','<','≥','≤'],response_mode='SYMBOL_SELECTION',expected_symbol=symbol))
        cls=RepresentationCandidate if rep else ConceptCheckCandidate
        results.append(cls(binding=brief.binding,brief_hash=hash_of(brief),alignment=dict(intention_id=check.intention_id,criterion_id=check.criterion_id,activity_id=check.activity_id,check_id=check.check_id),
            content_origin='OFFLINE_FIXTURE_CONTENT',field_provenance={k:'OFFLINE_FIXTURE_CONTENT' for k in content},content=content))
    return results

def negative_fixtures(rep,check):
    changes={
        'wrong-objective':('rep',['binding','source_id'],'EDX-4MA1-F-2.8-E'),
        'wrong-tier':('rep',['binding','tier'],'Higher'),
        'stale-pedagogy':('rep',['binding','pedagogical_spec_hash'],'0'*64),
        'wrong-pack':('rep',['binding','approved_pack_hash'],'0'*64),
        'unsupported-meaning':('rep',['content','expected_meaning'],'APPROXIMATELY_EQUAL'),
        'greater-as-less':('rep',['content','expected_meaning'],'LESS_THAN'),
        'inclusive-as-strict':('inclusive',['content','expected_meaning'],'GREATER_THAN'),
        'corrupted-glyph':('rep',['content','symbol'],'\uf085'),
        'solving-introduced':('rep',['content','instruction'],'Solve x + 2 > 5.'),
        'number-line-introduced':('rep',['content','instruction'],'Solve using a number line.'),
        'unrelated-algebra':('rep',['content','algebra'],'Factor x squared minus one'),
        'criterion-mismatch':('check',['alignment','criterion_id'],'SC-1'),
        'check-mismatch':('check',['alignment','check_id'],'CHK-1'),
        'no-observable-response':('check',['content','response_mode'],'READ_ONLY'),
        'ambiguous-response':('check',['content','choices'],['>','>','<']),
        'unsupported-family':('rep',['binding','role_family'],'CALCULATION'),
        'forged-human-approval':('rep',['human_approved'],True),
        'missing-provenance':('rep',['field_provenance'],{}),
        'role-substitution':('rep',['binding','role_id'],check.binding.role_id),
        'candidate-tampered':('rep',['content','symbol'],'<'),
        'wrong-expected-symbol':('check',['content','expected_symbol'],'<'),
        'wrong-intention':('rep',['alignment','intention_id'],'unknown'),
        'forged-source-content-provenance':('rep',['field_provenance','symbol'],'GOVERNED_SOURCE_CONTEXT'),
        'empty-choices':('check',['content','choices'],[]),
        'teacher-answer-leak':('rep',['content','teacher_answer'],'greater than'),
    }
    for name,(which,path,value) in changes.items():
        raw=(check if which=='check' else rep).model_dump(mode='json')
        if which=='inclusive':raw['content']['symbol']='≥';raw['content']['expected_meaning']='GREATER_THAN_OR_EQUAL_TO'
        node=raw
        for k in path[:-1]:node=node[k]
        node[path[-1]]=value
        yield name,('CONCEPT_CHECK' if which=='check' else 'REPRESENTATION'),raw

class GenericRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.net=patch('socket.socket.connect',side_effect=AssertionError('No network'));cls.net.start()
        cls.ingestion,cls.service,cls.spec=context()
        cls.briefs={f:build_brief(cls.spec,f,cls.service) for f in ('REPRESENTATION','CONCEPT_CHECK')}
        cls.fixtures={f:positive_fixtures(b) for f,b in cls.briefs.items()}
    @classmethod
    def tearDownClass(cls):cls.ingestion.close();cls.net.stop()
    def test_positive_six(self):
        for family,rows in self.fixtures.items():
            for c in rows:
                with self.subTest(family=family,content=c.content):
                    r=validate_candidate(c,self.briefs[family],self.service);self.assertTrue(r.valid,r.errors)
                    a=compose(c,self.briefs[family],self.service,validation=r)
                    self.assertTrue(validate_composition(a,self.briefs[family],self.service)['valid'])
                    self.assertFalse(a.human_approved);self.assertFalse(a.published)
    def test_negative_twenty_five(self):
        for name,family,raw in negative_fixtures(self.fixtures['REPRESENTATION'][0],self.fixtures['CONCEPT_CHECK'][0]):
            with self.subTest(case=name):self.assertFalse(validate_candidate(raw,self.briefs[family],self.service).valid)
    def test_independent_validator(self):
        with patch('academic_os.generic_role_authoring.brief.build_brief',side_effect=AssertionError('No construction')),patch('academic_os.generic_role_authoring.service.compose',side_effect=AssertionError('No composition')):
            for f in self.fixtures:self.assertTrue(validate_candidate(self.fixtures[f][0],self.briefs[f],self.service).valid)
    def test_brief_determinism(self):
        for f,b in self.briefs.items():self.assertEqual(b,build_brief(self.spec,f,self.service))
    def test_brief_mutations(self):
        for path,value in [(['warnings'],[]),(['source_context','official_text'],'Understand and use the symbols >, <, ≥ and ≤.'),(['binding','review_hash'],'0'*64),(['activity_constraints'],[]),(['provenance'],{})]:
            b=self.briefs['REPRESENTATION'].model_dump(mode='json');node=b
            for k in path[:-1]:node=node[k]
            node[path[-1]]=value
            self.assertFalse(validate_candidate(self.fixtures['REPRESENTATION'][0],b,self.service).valid)
    def test_role_substitution_across_briefs(self):
        self.assertFalse(validate_candidate(self.fixtures['REPRESENTATION'][0],self.briefs['CONCEPT_CHECK'],self.service).valid)
    def test_all_four_symbol_semantics(self):
        for symbol,meaning in SYMBOL_MEANINGS.items():
            raw=self.fixtures['REPRESENTATION'][0].model_dump(mode='json');raw['content'].update(symbol=symbol,expected_meaning=meaning)
            self.assertTrue(validate_candidate(raw,self.briefs['REPRESENTATION'],self.service).valid)
            for wrong in set(SYMBOL_MEANINGS.values())-{meaning}:
                raw['content']['expected_meaning']=wrong
                self.assertFalse(validate_candidate(raw,self.briefs['REPRESENTATION'],self.service).valid)
    def test_stale_report_even_valid_changed_content(self):
        b=self.briefs['REPRESENTATION'];c=self.fixtures['REPRESENTATION'][0];r=validate_candidate(c,b,self.service)
        raw=c.model_dump(mode='json');raw['content'].update(symbol='<',expected_meaning='LESS_THAN')
        self.assertTrue(validate_candidate(raw,b,self.service).valid)
        with self.assertRaises(ValueError):compose(raw,b,self.service,validation=r)
    def test_composition_tampering(self):
        b=self.briefs['REPRESENTATION'];a=compose(self.fixtures['REPRESENTATION'][0],b,self.service)
        for field,value in [('candidate_hash','0'*64),('validation_hash','0'*64),('student_content',{'answer':'greater than'}),('teacher_validation',{'expected_meaning':'LESS_THAN'}),('lineage',{})]:
            raw=a.model_dump(mode='json');raw[field]=value
            self.assertFalse(validate_composition(raw,b,self.service)['valid'])
    def test_composition_separation(self):
        for family in self.fixtures:
            a=compose(self.fixtures[family][0],self.briefs[family],self.service)
            self.assertNotIn('expected_symbol',a.student_content);self.assertNotIn('expected_meaning',a.student_content)
    def test_deterministic_replay_twice(self):
        for family,rows in self.fixtures.items():
            for c in rows:
                b=self.briefs[family];r=validate_candidate(c,b,self.service);a=compose(c,b,self.service)
                for _ in range(2):
                    self.assertEqual(r,validate_candidate(c.model_dump(mode='json'),b,self.service))
                    self.assertEqual(hash_of(a),hash_of(compose(c.model_dump(mode='json'),b,self.service)))
    def test_role_and_overall_eligibility(self):
        for f in self.briefs:self.assertEqual(role_eligibility(self.spec,f,self.service)['status'],'ELIGIBLE_WITH_WARNINGS')
        gate=self.service.evaluate_lesson_authoring_eligibility(self.spec)
        self.assertEqual(gate.status,'BLOCKED');self.assertIn('UNSUPPORTED_REQUIRED_ROLE:scope_framing',gate.missing_requirements)
        self.assertTrue(self.service.validate_lesson_authoring_eligibility(gate,self.spec)['valid'])
    def test_upstream_tamper(self):
        raw=self.spec.model_dump(mode='json');raw['approved_evidence']['pack_hash']='0'*64
        with self.assertRaises(ValueError):build_brief(raw,'REPRESENTATION',self.service)
    def test_missing_review_authority(self):
        unbound=GovernedPedagogyService(self.service.learning)
        self.assertFalse(validate_candidate(self.fixtures['REPRESENTATION'][0],self.briefs['REPRESENTATION'],unbound).valid)

if __name__=='__main__':unittest.main()
