"""P3A: all altered inputs are TEST ONLY fixtures; real trusted state stays read-only."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from academic_os.learning_core import build_learning_specification
from academic_os.learning_service import LearningSpecificationService
from academic_os.learning_models import LearningSpecification
from academic_os.learning_rendering import learning_specification_text
from academic_os.product_service import AcademicProductService
from academic_os.assessment_intelligence import AssessmentIntelligenceService,_derive
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_reader import UnusableSnapshot
from academic_os.storage import Store
from academic_os.service import Service
from tests_p0.teacher_product_acceptance import state

DB=Path('var/p0_q2.sqlite3');TOPIC='standard-deviation'
GOLD=Path('tests_p0/fixtures/learning_standard_deviation_gold.json')


class LearningSpecificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state()
        cls.teacher=AcademicProductService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.assessment=AssessmentIntelligenceService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.result=LearningSpecificationService(DB).read_topic(TOPIC,PROTECTED_SNAPSHOTS)
        cls.view=cls.result.view
        cls.gold=json.loads(GOLD.read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):assert cls.before==state(),'Learning reads changed real DB'

    def fixture(self):return self.teacher.view.model_dump(mode='json')
    def build(self,teacher):return build_learning_specification(teacher,_derive(teacher))

    def test_01_contract_versions(self):
        self.assertEqual(self.view.schema_version,'learning-specification/1')
        self.assertEqual(self.view.source_contracts,('teacher-topic/2','assessment-intelligence/1'))

    def test_02_reject_teacher_version(self):
        teacher=self.fixture();teacher['schema_version']='teacher-topic/999'
        with self.assertRaisesRegex(ValueError,'Unsupported teacher schema'):build_learning_specification(teacher,self.assessment.view)

    def test_03_reject_assessment_version(self):
        ai=self.assessment.view.model_dump();ai['schema_version']='assessment-intelligence/999'
        with self.assertRaisesRegex(ValueError,'Unsupported assessment schema'):build_learning_specification(self.teacher.view,ai)

    def test_04_no_upstream_mutation(self):
        teacher=self.fixture();ai=self.assessment.view.model_dump(mode='json');before=copy.deepcopy((teacher,ai))
        build_learning_specification(teacher,ai);self.assertEqual((teacher,ai),before)

    def test_05_identity_and_course(self):
        expected=self.teacher.view.identity.model_dump();expected['view_type']='learning_specification'
        self.assertEqual(self.view.identity.model_dump(),expected)
        self.assertEqual(self.view.identity.view_key,TOPIC);self.assertEqual(self.view.identity.title,'Standard deviation')

    def test_06_gold_learning_meaning(self):
        self.assertEqual(len(self.view.learning_requirements),3)
        by_type={r.type:r for r in self.view.learning_requirements}
        for expected in self.gold['learning_requirements']:
            actual=by_type[expected['type']]
            self.assertEqual(set(actual.source_refs),set(expected['source_refs']))
            for text in expected['required_meaning']:self.assertIn(text,actual.statement)

    def test_07_conceptual_basis(self):
        concept=self.teacher.view.concepts[0];basis=self.view.conceptual_basis[0]
        self.assertEqual((basis.concept_ref,basis.name,basis.description),(concept.ref,concept.name,concept.description))

    def test_08_task_evidence_both_examples(self):
        requirement=next(r for r in self.view.learning_requirements if r.type=='capability_under_task_form')
        lookup={e.ref:e for e in self.view.assessment_evidence}
        self.assertEqual({(lookup[r].year,lookup[r].question_part) for r in requirement.evidence_refs},{(2025,'Q2(b)'),(2023,'Q3(b)(ii)')})

    def test_09_gold_coverage(self):
        self.assertEqual(len(self.view.coverage_requirements),2)
        by_type={r.type:r for r in self.view.coverage_requirements}
        for expected in self.gold['coverage_requirements']:
            for text in expected['required_meaning']:self.assertIn(text,by_type[expected['type']].statement)
        self.assertFalse(set(by_type)&{r.type for r in self.view.learning_requirements})

    def test_10_ten_boundaries(self):
        self.assertEqual(len(self.view.evidence_boundaries),10)
        self.assertEqual({r.code for r in self.view.evidence_boundaries},{r['code'] for r in self.gold['evidence_boundaries']})

    def test_11_boundary_traceability(self):
        lookup={r.code:r.message for r in self.assessment.view.limitations}
        for b in self.view.evidence_boundaries:
            self.assertEqual(b.epistemic_class,'evidence_boundary');self.assertTrue(b.source_refs)
            if b.basis=='upstream_limitation':self.assertEqual(b.statement,lookup[b.code])

    def test_12_no_added_notation_or_method(self):
        text=' '.join(r.statement for r in self.view.learning_requirements).lower()
        for forbidden in ('Σx','Σx²','sigma','memor','formula','calculator','manually','square root','variance','prerequisite'):
            with self.subTest(forbidden=forbidden):self.assertNotIn(forbidden.lower(),text)

    def test_13_no_pedagogical_or_analytic_fields(self):
        data=self.view.model_dump(mode='json')
        def keys(value):
            if isinstance(value,dict):
                for k,v in value.items():yield k;yield from keys(v)
            elif isinstance(value,list):
                for v in value:yield from keys(v)
        self.assertFalse({'common_mistakes','misconceptions','student_errors','difficulty','teaching_sequence','prerequisites','formula','lesson_plan'}&set(keys(data)))

    def test_14_classifications(self):
        self.assertTrue(all(r.epistemic_class=='evidence_backed_requirement' for r in (*self.view.learning_requirements,*self.view.coverage_requirements)))
        self.assertTrue(all(e.epistemic_level=='observed_evidence' for e in self.view.assessment_evidence))

    def test_15_all_refs_resolve(self):
        products=set(self.teacher.provenance['product_refs'])
        learning={r.ref for r in self.view.learning_requirements};evidence={e.ref for e in self.view.assessment_evidence}
        for r in (*self.view.learning_requirements,*self.view.coverage_requirements):
            self.assertTrue(set(r.source_refs)<=products);self.assertTrue(set(r.evidence_refs)<=evidence)
        for r in self.view.coverage_requirements:self.assertTrue(set(r.learning_requirement_refs)<=learning)

    def test_16_production_never_reads_oracle(self):
        with patch('builtins.open',side_effect=AssertionError('Pure core attempted file read')),patch.object(Path,'read_text',side_effect=AssertionError('Oracle file read')):
            self.assertEqual(build_learning_specification(self.teacher.view,self.assessment.view).serialize(),self.view.serialize())
        for path in Path('academic_os').glob('learning_*.py'):
            text=path.read_text(encoding='utf-8')
            for token in ('LR-SD-01','learning_standard_deviation_gold','Q2(b)','Q3(b)(ii)','standard-deviation'):
                self.assertNotIn(token,text)

    def test_17_semantic_roles_generalise(self):
        data=self.fixture();data['identity']['view_key']='TEST-other-topic';data['identity']['title']='TEST unrelated topic'
        c=data['concepts'][0];c.update(ref='TEST-concept',name='TEST quantity',description='TEST conceptual definition.')
        cap=data['capabilities'][0];cap.update(ref='TEST-capability',name='TEST action',description='Perform TEST action.',concept_refs=['TEST-concept'])
        task=cap['task_forms'][0];task.update(ref='TEST-task',name='TEST condition',description='Use TEST supplied representation.')
        for e in data['assessment_evidence']:e.update(capability_ref='TEST-capability',task_form_refs=['TEST-task'],year=2040,question_part='TEST part',paper=e['paper']+'-'+str(e['year']))
        view=self.build(data)
        self.assertEqual(len(view.learning_requirements),3)
        self.assertIn('TEST conceptual definition.',view.learning_requirements[0].statement)
        self.assertTrue(all('standard deviation' not in r.statement.lower() for r in view.learning_requirements))

    def test_18_unassessed_task_not_requirement(self):
        data=self.fixture();data['capabilities'][0]['task_forms'].append(dict(ref='TEST-extra',name='TEST extra task',description='TEST no assessment evidence'))
        view=self.build(data)
        self.assertEqual(len(view.learning_requirements),3)
        self.assertFalse(any('TEST-extra' in r.source_refs for r in view.learning_requirements))

    def test_19_missing_evidence_no_task_or_connection(self):
        data=self.fixture();data['assessment_evidence']=[];data['trust_summary']['reviewed_example_count']=0
        view=self.build(data)
        self.assertEqual({r.type for r in view.learning_requirements},{'conceptual_understanding','capability'})
        self.assertEqual([r.type for r in view.coverage_requirements],['assessment_alignment'])

    def test_20_extra_concept_derived_from_role(self):
        data=self.fixture();data['concepts'].append(dict(ref='TEST-second',name='TEST second concept',description='TEST second meaning.'))
        view=self.build(data);self.assertEqual(len(view.learning_requirements),4)
        self.assertTrue(any(r.source_refs==('TEST-second',) for r in view.learning_requirements))

    def test_21_ids_stable_when_display_changes(self):
        data=self.fixture();data['identity']['title']='TEST new label';data['concepts'][0]['description']='TEST revised meaning.'
        data['capabilities'][0]['description']='TEST revised action.'
        self.assertEqual([r.ref for r in self.build(data).learning_requirements],[r.ref for r in self.view.learning_requirements])

    def test_22_evidence_wording_never_creates_requirement(self):
        data=self.fixture()
        for e in data['assessment_evidence']:e['question_wording']='TEST Σx Σx² calculator formula memorisation mean variance'
        self.assertEqual(self.build(data).learning_requirements,self.view.learning_requirements)

    def test_23_repeat_deterministic(self):
        self.assertEqual(self.build(self.fixture()).serialize(),self.view.serialize())

    def test_24_evidence_order_deterministic(self):
        data=self.fixture();data['assessment_evidence'].reverse();ai=self.assessment.view.model_dump(mode='json')
        ai['reviewed_examples'].reverse();ai['observed_patterns'].reverse()
        self.assertEqual(build_learning_specification(data,ai).serialize(),self.view.serialize())

    def test_25_snapshots_order_deterministic(self):
        other=LearningSpecificationService(DB).read_topic(TOPIC,tuple(reversed(PROTECTED_SNAPSHOTS)))
        self.assertEqual(other.view.serialize(),self.view.serialize());self.assertEqual(other.provenance,self.result.provenance)

    def test_26_frozen_upstream_artifacts(self):
        before=json.loads(Path('output/p3a_learning_specification/before.json').read_text(encoding='utf-8'))
        for file,digest in before['files'].items():self.assertEqual(hashlib.sha256(Path(file).read_bytes()).hexdigest(),digest,file)

    def test_27_inconsistent_contracts_rejected(self):
        data=self.fixture();data['concepts'][0]['description']='TEST changed meaning'
        with self.assertRaisesRegex(ValueError,'contracts disagree'):build_learning_specification(data,self.assessment.view)

    def test_28_manipulated_assessment_limitation_rejected(self):
        data=self.assessment.view.model_dump(mode='json');data['limitations'][0]['message']='TEST unsupported claim'
        with self.assertRaisesRegex(ValueError,'contracts disagree'):build_learning_specification(self.teacher.view,data)

    def test_29_no_canonical_ids_in_normal_view(self):
        text=self.view.serialize()
        for forbidden in ('CAN-STAT','CON-STAT','TC-SUMMARY',*PROTECTED_SNAPSHOTS,'LR-SD-01'):
            self.assertNotIn(forbidden,text)

    def test_30_provenance_chain(self):
        provenance=self.result.provenance
        for r in self.view.learning_requirements:
            self.assertIn(r.ref,provenance['learning_requirements'])
            for source in r.source_refs:self.assertIn(source,provenance['upstream']['upstream']['product_refs'])

    def test_31_trust_and_curriculum_preserved(self):
        self.assertEqual(self.view.trust_summary,self.assessment.view.trust_summary)
        self.assertEqual(self.view.curriculum,self.teacher.view.curriculum)
        self.assertFalse(self.view.trust_summary.upstream.curriculum_association_confirmed)

    def test_32_pending_unresolved_absent(self):
        text=self.view.serialize()
        for forbidden in ('Q3(c)(ii)','CONTEXT-INFER','underestimate'):self.assertNotIn(forbidden,text)

    def test_33_source_notes_preserved(self):
        self.assertEqual(self.view.assessment_evidence,self.assessment.view.reviewed_examples)

    def test_34_real_db_unchanged(self):self.assertEqual(state(),self.before)

    def test_35_no_raw_bypass(self):
        for name in ('learning_core.py','learning_service.py'):
            text=(Path('academic_os')/name).read_text(encoding='utf-8')
            for token in ('import sqlite3','read_usable_snapshots','from .storage','from .service import','_compose('):self.assertNotIn(token,text)

    def test_36_cli(self):
        run=subprocess.run([sys.executable,'-X','utf8','-m','academic_os','--db',str(DB),'learning-specification',TOPIC,'--json'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout),self.view.model_dump(mode='json'))

    def test_37_rendering(self):
        text=learning_specification_text(self.view)
        for label in ('What students need to understand','What students need to be able to do','Assessment evidence','Coverage requirements','Evidence boundaries'):self.assertIn(label,text)
        self.assertNotIn('CAN-STAT',text)

    def test_38_cli_never_opens_write_store(self):
        from academic_os.cli import main
        with patch('academic_os.cli.Store',side_effect=AssertionError('Write store opened')),patch('builtins.print'):
            self.assertEqual(main(['--db',str(DB),'learning-specification',TOPIC]),0)

    def test_39_next_read_revocation_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.sqlite3';source=sqlite3.connect(DB.resolve().as_uri()+'?mode=ro',uri=True);dest=sqlite3.connect(path)
            try:source.backup(dest)
            finally:source.close();dest.close()
            reader=LearningSpecificationService(path);reader.read_topic(TOPIC,PROTECTED_SNAPSHOTS)
            store=Store(path)
            try:
                service=Service(store);key='proposal:PROPOSE-Q3-2023-b-ii';i=service.inspect(key)
                service.review(key,'revoke','TEST-ONLY-OPERATOR','TEST ONLY learning revocation',i['version'],i['dependency_digest'],i['expected_decision'],'TEST-P3A-REVOKE')
            finally:store.close()
            before=path.read_bytes()
            with self.assertRaises(UnusableSnapshot):reader.read_topic(TOPIC,PROTECTED_SNAPSHOTS)
            self.assertEqual(path.read_bytes(),before)

    def test_40_saved_json_is_not_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'TEST.json';path.write_text(self.teacher.view.serialize(),encoding='utf-8')
            with self.assertRaises(sqlite3.DatabaseError):LearningSpecificationService(path).read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_41_unique_refs(self):
        refs=[r.ref for r in (*self.view.learning_requirements,*self.view.coverage_requirements,*self.view.evidence_boundaries)]
        self.assertEqual(len(refs),len(set(refs)))

    def test_42_coverage_reference_validation(self):
        data=self.view.model_dump();data['coverage_requirements'][0]['learning_requirement_refs']=('TEST-unknown',)
        with self.assertRaisesRegex(ValueError,'Coverage refs'):LearningSpecification.model_validate(data)

    def test_43_evidence_reference_validation(self):
        data=self.view.model_dump();data['learning_requirements'][2]['evidence_refs']=('TEST-unknown',)
        with self.assertRaisesRegex(ValueError,'resolving evidence'):LearningSpecification.model_validate(data)

    def test_44_two_reads_must_have_same_provenance(self):
        from academic_os.product_service import ProductRead
        service=LearningSpecificationService(DB);trace=copy.deepcopy(self.teacher.provenance);trace['TEST-change']=True
        with patch.object(service._teacher,'read_topic',return_value=ProductRead(self.teacher.view,trace)):
            with self.assertRaisesRegex(ValueError,'provenance changed'):service.read_topic(TOPIC,PROTECTED_SNAPSHOTS)

    def test_45_no_snapshot_cache(self):
        service=LearningSpecificationService(DB)
        with patch.object(service._assessment,'read_topic',return_value=self.assessment) as ai,patch.object(service._teacher,'read_topic',return_value=self.teacher) as teacher:
            service.read_topic(TOPIC,PROTECTED_SNAPSHOTS);service.read_topic(TOPIC,PROTECTED_SNAPSHOTS)
            self.assertEqual(ai.call_count,2);self.assertEqual(teacher.call_count,2)
