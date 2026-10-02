"""P5C isolated candidate mutations; real academic state/artifacts stay frozen."""
import copy,json,hashlib,tempfile,contextlib,io,unittest
from pathlib import Path
from unittest.mock import patch
from academic_os.lesson_profile_service import LessonProfileService
from academic_os.authored_service import AuthoredTeachingService
from academic_os.content_validation_service import AuthoredContentValidationService
from academic_os.learning_service import LearningSpecificationService
from academic_os.pedagogical_core import build_pedagogical_specification
from academic_os.profiled_content import build_profiled_content
from academic_os.profiled_content_validation import validate_profiled_content
from academic_os.profiled_validation_service import ProfiledContentValidationService,ProfiledValidationRead,save_profiled_validation
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.cli import main
from tests_p0.teacher_product_acceptance import state

OUT=Path('output/p5c_profiled_validation');DB=Path('var/p0_q2.sqlite3')
class ProfiledValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state();cls.profiles=LessonProfileService(DB).read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
        cls.a=AuthoredTeachingService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS).view
        cls.v=AuthoredContentValidationService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS).view
        cls.l=LearningSpecificationService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS).view;cls.b=build_pedagogical_specification(cls.l)
        cls.packages={k:build_profiled_content(p,cls.a,cls.v,cls.l,cls.b) for k,p in cls.profiles.views.items()}
        cls.reports={k:cls.validate(v,k) for k,v in cls.packages.items()}
    @classmethod
    def tearDownClass(cls):assert cls.before==state()
    @classmethod
    def validate(cls,data,key='standard-lesson'):return validate_profiled_content(data,cls.profiles.profiles[key],cls.profiles.views[key],cls.a,cls.v,cls.l,cls.b)
    def fixture(self,key='standard-lesson'):return self.packages[key].model_dump(mode='json')
    def decision(self,data,key):return next(d for d in data['role_decisions'] if d['role_key']==key)
    def remove_new(self,data,kind):
        q=next(q for q in data['new_content'] if q['semantic_role']==kind);ref=q['ref']
        s=next(s for s in data['new_solutions'] if s['item_ref']==ref)
        data['new_content'].remove(q);data['new_solutions'].remove(s)
        for d in data['role_decisions']:
            if ref in d['new_content_refs']:d['new_content_refs'].remove(ref);d['solution_refs'].remove(s['ref'])
        return ref
    def blocked(self,data,key='standard-lesson'):
        report=self.validate(data,key);self.assertFalse(report.renderer_readiness.ready_for_rendering);self.assertTrue(report.violations);return report
    def test_01_focused_ready(self):
        r=self.reports['focused-review'];self.assertTrue(r.renderer_readiness.ready_for_rendering,r.violations);self.assertEqual((r.role_population.populated,r.role_population.required),(9,9))
    def test_02_standard_ready(self):
        r=self.reports['standard-lesson'];self.assertTrue(r.renderer_readiness.ready_for_rendering,r.violations);self.assertEqual((r.role_population.populated,r.role_population.required),(15,15))
    def test_03_all_dimensions_pass(self):
        for r in self.reports.values():
            for k in ('profile_structure','role_population','density_validation','reuse_integrity','new_content_integrity','composite_role_validation','academic_scope_validation','boundary_compliance','unresolved_validation'):self.assertTrue(getattr(r,k).valid,k)
    def test_04_six_numerical_recomputed(self):
        r=self.reports['standard-lesson'];self.assertEqual(sum('numeric_answer_recomputed' in v['checks'] for v in r.mathematical_verification.values()),6)
    def test_05_case_a_missing_focused_practice(self):
        d=self.fixture('focused-review');d['role_decisions'].remove(self.decision(d,'FR-07'))
        r=self.blocked(d,'focused-review');self.assertFalse(r.density_validation.minimum_compliance)
    def test_06_case_b_missing_guided(self):
        d=self.fixture();role=self.decision(d,'SL-11');ref=role['new_content_refs'][0]
        d['new_content']=[q for q in d['new_content'] if q['ref']!=ref];d['new_solutions']=[s for s in d['new_solutions'] if s['item_ref']!=ref];d['role_decisions'].remove(role)
        r=self.blocked(d);self.assertFalse(r.density_validation.minimum_compliance)
    def test_07_case_c_minimum_without_target_ready(self):
        d=self.fixture();self.remove_new(d,'independent_practice');self.decision(d,'SL-12')['decision']='reuse'
        r=self.validate(d);self.assertTrue(r.renderer_readiness.ready_for_rendering,r.violations);self.assertTrue(r.density_validation.minimum_compliance);self.assertFalse(r.density_validation.target_attainment)
        row=next(x for x in r.coverage_matrix if x.role_key=='SL-12');self.assertEqual(row.actual_valid_content_count,2);self.assertEqual(row.status,'populated');self.assertTrue(any(w.code=='preferred_target_not_met' for w in r.warnings))
    def test_08_case_d_reused_numbers_digest(self):
        d=self.fixture();record=next(r for r in d['reused_content'] if 'practice-1' in r['ref']);record['dependency_hashes'][next(iter(record['dependency_hashes']))]='0'*64
        self.assertFalse(self.blocked(d).reuse_integrity.valid)
    def test_09_case_e_unknown_reuse(self):
        d=self.fixture();self.decision(d,'SL-02')['reused_content_refs']=['unknown'];self.assertFalse(self.blocked(d).reuse_integrity.valid)
    def test_10_case_f_wrong_reuse_role(self):
        d=self.fixture();role=self.decision(d,'SL-09');role['decision']='reuse';role['new_content_refs']=[];role['reused_content_refs']=self.decision(d,'SL-02')['reused_content_refs'][:]
        self.assertFalse(self.blocked(d).reuse_integrity.valid)
    def test_11_all_numeric_answer_tampering(self):
        source=self.fixture()
        for q in source['new_content']:
            if q['summary'] or q['raw_values']:
                d=copy.deepcopy(source);s=next(s for s in d['new_solutions'] if s['item_ref']==q['ref']);s['numeric_answer']='999'
                with self.subTest(ref=q['ref']):self.assertFalse(self.blocked(d).new_content_integrity.valid)
    def test_12_corrupt_rounding(self):
        d=self.fixture();next(s for s in d['new_solutions'] if s['numeric_answer'])['display_answer']='9.99';self.blocked(d)
    def test_13_raw_scope_assessed_task(self):
        d=self.fixture();next(q for q in d['new_content'] if q['raw_values'])['task_form_refs']=['task-form-summary-statistics']
        self.assertFalse(self.blocked(d).academic_scope_validation.valid)
    def test_14_unknown_task(self):
        d=self.fixture();next(q for q in d['new_content'] if q['summary'])['task_form_refs']=['raw-task'];self.assertFalse(self.blocked(d).academic_scope_validation.valid)
    def test_15_unknown_lr(self):
        d=self.fixture();d['new_content'][0]['learning_requirement_refs'].append('new-lr');self.assertFalse(self.blocked(d).academic_scope_validation.valid)
    def test_16_unknown_exit_part_lr(self):
        d=self.fixture();next(q for q in d['new_content'] if q['semantic_role']=='exit_check')['concept_learning_requirement_refs']=['new-lr'];self.assertFalse(self.blocked(d).academic_scope_validation.valid)
    def test_17_stored_scope_hash(self):
        d=self.fixture();d['academic_scope_fingerprint']='0'*64;self.assertFalse(self.blocked(d).academic_scope_validation.valid)
    def test_18_profile_mismatch(self):self.blocked(self.fixture('focused-review'))
    def test_19_missing_boundary(self):
        d=self.fixture();d['evidence_boundaries'].pop();self.assertFalse(self.blocked(d).boundary_compliance.valid)
    def test_20_guided_support_corrupt(self):
        d=self.fixture();next(q for q in d['new_content'] if q['semantic_role']=='guided_practice')['support_mode']='independent';self.blocked(d)
    def test_21_unsupported_claims(self):
        for text in ('You must memorise this formula.','This is an easy question.','This is frequently tested.','This is usually 2 marks.','Mean is a formal prerequisite.','You must use a specific calculator.','Common mistakes include this.','It will appear in the exam.','Sample standard deviation uses n - 1.'):
            d=self.fixture();d['new_content'][0]['question']+=' '+text
            with self.subTest(text=text):self.assertFalse(self.blocked(d).boundary_compliance.valid)
    def test_22_solution_in_question_extra_field(self):
        d=self.fixture();d['new_content'][0]['answer']='embedded answer';self.blocked(d)
    def test_23_answer_leak_in_prompt(self):
        d=self.fixture();next(q for q in d['new_content'] if q['semantic_role']=='independent_practice')['question']+=' Answer: 2.';self.blocked(d)
    def test_24_missing_solution(self):
        d=self.fixture();d['new_solutions'].pop();self.blocked(d)
    def test_25_duplicate_solution(self):
        d=self.fixture();d['new_solutions'].append(copy.deepcopy(d['new_solutions'][0]));self.blocked(d)
    def test_26_duplicate_role(self):
        d=self.fixture();d['role_decisions'].append(copy.deepcopy(d['role_decisions'][0]));self.blocked(d)
    def test_27_duplicate_composite_item(self):
        d=self.fixture();role=self.decision(d,'SL-12');role['reused_content_refs'].append(role['reused_content_refs'][0]);self.assertFalse(self.blocked(d).composite_role_validation.valid)
    def test_28_unresolved_despite_minimum(self):
        d=self.fixture();self.remove_new(d,'independent_practice');self.decision(d,'SL-12').update(decision='unresolved',reason='No safe provider')
        r=self.blocked(d);self.assertTrue(r.density_validation.minimum_compliance);self.assertFalse(r.unresolved_validation.valid);self.assertTrue(r.unresolved_roles)
    def test_29_framing_orientation_missing(self):
        d=self.fixture();d['framing'].pop(next(k for k in d['framing'] if k.endswith('SL-01')));self.assertFalse(self.blocked(d).role_population.valid)
    def test_30_closure_refs_mutated(self):
        d=self.fixture();d['framing'][next(k for k in d['framing'] if k.endswith('SL-15'))]=[];self.blocked(d)
    def test_31_population_flags_ignored(self):
        d=self.fixture();d.update(content_complete=False,minimum_density_met=False,target_density_met=False,ready_for_p5c=False)
        for role in d['role_decisions']:role.update(supplied_items=0,minimum_met=False,target_met=False)
        self.assertTrue(self.validate(d).renderer_readiness.ready_for_rendering)
    def test_32_verification_flags_ignored(self):
        d=self.fixture();d['mathematical_verification']={};self.assertTrue(self.validate(d).renderer_readiness.ready_for_rendering)
    def test_33_reuse_compatibility_claims_ignored(self):
        d=self.fixture();self.decision(d,'SL-02')['compatibility']={};self.assertTrue(self.validate(d).renderer_readiness.ready_for_rendering)
    def test_34_dangling_new_reference(self):
        d=self.fixture();self.decision(d,'SL-12')['new_content_refs']=['missing'];self.blocked(d)
    def test_35_stale_binding(self):
        d=self.fixture();d['source_authored_validation']['sha256']='0'*64;self.assertFalse(self.blocked(d).reuse_integrity.valid)
    def test_36_forged_reused_content_identity(self):
        d=self.fixture();d['reused_content'][0]['ref']='profile-copy';self.blocked(d)
    def test_37_orphan_new_object(self):
        d=self.fixture();q=copy.deepcopy(d['new_content'][0]);q['ref']='orphan';d['new_content'].append(q);self.blocked(d)
    def test_38_required_target_unknown_schema_rejected(self):
        p=self.profiles.profiles['standard-lesson'].model_dump(mode='json');p['density_policy']['independent_practice']['target_mandatory']=True
        r=validate_profiled_content(self.packages['standard-lesson'],p,self.profiles.views['standard-lesson'],self.a,self.v,self.l,self.b);self.assertFalse(r.renderer_readiness.ready_for_rendering)
    def test_39_lr_aggregate(self):
        for r in self.reports.values():
            self.assertEqual(len(r.learning_requirement_coverage),3)
            for row in r.learning_requirement_coverage:self.assertTrue(row.teaching_coverage);self.assertTrue(row.assessment_check_coverage)
    def test_40_original_coverage(self):
        for r in self.reports.values():self.assertEqual(len(r.coverage_requirement_coverage),2);self.assertTrue(all(r.coverage_requirement_coverage.values()))
    def test_41_deterministic(self):
        for k,p in self.packages.items():self.assertEqual(self.reports[k].serialize(),self.validate(p,k).serialize())
    def test_42_input_not_mutated(self):
        d=self.fixture();before=copy.deepcopy(d);self.validate(d);self.assertEqual(d,before)
    def test_43_frozen_state(self):
        before=json.loads((OUT/'before.json').read_text(encoding='utf-8'));self.assertEqual(state(),before['database'])
        for file,h in before['files'].items():self.assertEqual(hashlib.sha256(Path(file).read_bytes()).hexdigest(),h,file)
    def test_44_p4b_failure(self):
        v=self.v.model_copy(update={'renderer_readiness':self.v.renderer_readiness.model_copy(update={'ready_for_rendering':False})})
        r=validate_profiled_content(self.packages['standard-lesson'],self.profiles.profiles['standard-lesson'],self.profiles.views['standard-lesson'],self.a,v,self.l,self.b)
        self.assertFalse(r.renderer_readiness.ready_for_rendering);self.assertFalse(r.reuse_integrity.valid)
    def test_45_live_source_failure(self):
        s=ProfiledContentValidationService(DB)
        with patch.object(s._content,'read_profiles',side_effect=ValueError('revoked')):
            with self.assertRaisesRegex(ValueError,'revoked'):s.read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
    def test_46_cli_readonly(self):
        with patch('academic_os.cli.Store',side_effect=AssertionError('write')),patch.object(ProfiledContentValidationService,'read_profiles',return_value=ProfiledValidationRead(self.reports,{})),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['validate-profiled-content','standard-deviation']),0)
    def test_47_export_idempotent_conflict(self):
        result=ProfiledValidationRead(self.reports,{})
        with tempfile.TemporaryDirectory() as tmp:
            paths=save_profiled_validation(result,tmp);before={p:Path(p).read_bytes() for p in paths};save_profiled_validation(result,tmp)
            self.assertEqual(before,{p:Path(p).read_bytes() for p in paths});Path(paths[0]).write_text('conflict')
            with self.assertRaises(ValueError):save_profiled_validation(result,tmp)
    def test_48_no_fixed_slide_count_or_quality_score(self):
        for r in self.reports.values():self.assertNotIn('slide_count',r.serialize());self.assertFalse(r.trust_summary['quality_score_provided'])
    def test_49_numeric_exact_corruption(self):
        d=self.fixture();next(s for s in d['new_solutions'] if s['exact_answer'])['exact_answer']['radicand']='999';self.blocked(d)
    def test_50_mean_variance_corruption(self):
        for field in ('mean','variance'):
            d=self.fixture();next(s for s in d['new_solutions'] if s[field])[field]='999';self.blocked(d)

if __name__=='__main__':unittest.main()
