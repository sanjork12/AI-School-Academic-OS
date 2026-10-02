import copy,json,hashlib,tempfile,unittest,contextlib,io
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from academic_os.lesson_profile_service import LessonProfileService
from academic_os.authored_service import AuthoredTeachingService
from academic_os.content_validation_service import AuthoredContentValidationService
from academic_os.learning_service import LearningSpecificationService
from academic_os.pedagogical_core import build_pedagogical_specification
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.profiled_content import build_profiled_content,verify_profiled_package,compatibility,analyze_role
from academic_os.profiled_sd_provider import author,verify_new_content
from academic_os.profiled_content_service import ProfiledContentService,save_profiled_content
from academic_os.cli import main
from tests_p0.teacher_product_acceptance import state

OUT=Path('output/p5b_profiled_authoring');DB=Path('var/p0_q2.sqlite3')
class ProfiledContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state();cls.profiles=LessonProfileService(DB).read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
        cls.a=AuthoredTeachingService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS).view
        cls.v=AuthoredContentValidationService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS).view
        cls.l=LearningSpecificationService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS).view;cls.b=build_pedagogical_specification(cls.l)
        cls.packages={k:cls.build(k) for k in cls.profiles.views}
        cls.gold=json.loads(Path('tests_p0/fixtures/profiled_content_gold.json').read_text(encoding='utf-8-sig'))
    @classmethod
    def build(cls,key='standard-lesson',provider=author):return build_profiled_content(cls.profiles.views[key],cls.a,cls.v,cls.l,cls.b,provider)
    @classmethod
    def tearDownClass(cls):assert state()==cls.before
    def check(self,data,key='standard-lesson'):return verify_profiled_package(data,self.profiles.views[key],self.a,self.v,self.l,self.b)
    def test_01_focused_gold(self):
        p=self.packages['focused-review'];counts=Counter(d.decision for d in p.role_decisions)
        for k,v in self.gold['decisions']['focused-review'].items():self.assertEqual(counts[k],v)
        self.assertFalse(p.new_content);self.assertEqual(len(p.reused_content),9)
    def test_02_standard_gold(self):
        counts=Counter(d.decision for d in self.packages['standard-lesson'].role_decisions)
        for k,v in self.gold['decisions']['standard-lesson'].items():self.assertEqual(counts[k],v)
    def test_03_seven_new_items(self):self.assertEqual(len(self.packages['standard-lesson'].new_content),7)
    def test_04_reused_identity_shared_across_profiles(self):
        a={r.ref for r in self.packages['focused-review'].reused_content};b={r.ref for r in self.packages['standard-lesson'].reused_content}
        self.assertEqual(a,b)
    def test_05_reuse_not_cloned(self):
        for p in self.packages.values():self.assertFalse({r.ref for r in p.reused_content}&{q.ref for q in p.new_content})
    def test_06_practice_composite(self):
        d=next(d for d in self.packages['standard-lesson'].role_decisions if d.role_key=='SL-12')
        self.assertEqual((d.decision,len(d.reused_content_refs),len(d.new_content_refs),d.minimum_items,d.target_items),('author_new',2,1,2,3))
    def test_07_orientation_framing(self):
        p=self.packages['standard-lesson'];self.assertEqual(len(p.role_decisions),14);self.assertEqual(len(p.framing),2)
    def test_08_scope_same(self):self.assertEqual(self.packages['focused-review'].academic_scope_fingerprint,self.packages['standard-lesson'].academic_scope_fingerprint)
    def test_09_boundaries_same(self):
        for p in self.packages.values():self.assertEqual(p.evidence_boundaries,self.l.evidence_boundaries);self.assertEqual(p.content_boundaries,self.a.content_boundaries)
    def test_10_new_content_not_profile_named(self):
        for q in self.packages['standard-lesson'].new_content:self.assertNotIn('standard-lesson',q.ref)
    def test_11_numeric_oracle(self):
        p=self.packages['standard-lesson'];solutions={s.item_ref:s for s in p.new_solutions}
        for q in p.new_content:
            if q.summary or q.raw_values:
                key=q.semantic_role+('-'+q.ref.rsplit('-',1)[1] if q.semantic_role=='guided_practice' else '')
                s=solutions[q.ref];self.assertEqual([s.mean,s.variance,s.display_answer],self.gold['numerical'][key])
    def test_12_raw_data_instructional_only(self):
        q=next(q for q in self.packages['standard-lesson'].new_content if q.raw_values)
        self.assertEqual(q.raw_values,('2','4','4','6'));self.assertTrue(q.instructional_demonstration_only);self.assertFalse(q.task_form_refs);self.assertFalse(q.assesses_learning_requirement_refs)
    def test_13_raw_deviations(self):
        s=next(s for s in self.packages['standard-lesson'].new_solutions if s.deviations)
        self.assertEqual(s.deviations,('-2','0','0','2'));self.assertEqual(s.squared_deviations,('4','0','0','4'))
    def test_14_questions_separate(self):
        p=self.packages['standard-lesson'];self.assertEqual({q.ref for q in p.new_content},{s.item_ref for s in p.new_solutions})
        for q in p.new_content:
            data=q.model_dump();self.assertNotIn('numeric_answer',data);self.assertNotIn('expected_meaning',data)
    def test_15_guided_support(self):
        q=[q for q in self.packages['standard-lesson'].new_content if q.semantic_role=='guided_practice']
        self.assertEqual([len(x.scaffolding) for x in q],[4,1]);self.assertTrue(all(x.support_mode=='guided' for x in q))
    def test_16_independent_no_scaffold(self):self.assertFalse(next(q for q in self.packages['standard-lesson'].new_content if q.semantic_role=='independent_practice').scaffolding)
    def test_17_exit_parts(self):
        q=next(q for q in self.packages['standard-lesson'].new_content if q.semantic_role=='exit_check')
        self.assertEqual(len(q.concept_learning_requirement_refs),1);self.assertEqual(len(q.calculation_learning_requirement_refs),2)
        self.assertEqual(set(q.concept_learning_requirement_refs+q.calculation_learning_requirement_refs),set(q.assesses_learning_requirement_refs))
    def test_18_semantic_not_exact_grading(self):
        for s in self.packages['standard-lesson'].new_solutions:
            if s.expected_meaning:self.assertTrue(s.key_semantic_elements);self.assertFalse(s.exact_string_matching_required)
    def test_19_corrupt_every_numeric_answer(self):
        p=self.packages['standard-lesson'];solutions={s.item_ref:s for s in p.new_solutions}
        for q in p.new_content:
            if q.summary or q.raw_values:
                with self.subTest(q=q.ref):self.assertEqual(verify_new_content(q,solutions[q.ref].model_copy(update={'numeric_answer':'999'})).status,'failed')
    def test_20_corrupt_every_rounding(self):
        p=self.packages['standard-lesson'];solutions={s.item_ref:s for s in p.new_solutions}
        for q in p.new_content:
            if q.summary or q.raw_values:self.assertEqual(verify_new_content(q,solutions[q.ref].model_copy(update={'display_answer':'999'})).status,'failed')
    def test_21_corrupt_exact_mean_variance_steps(self):
        p=self.packages['standard-lesson'];q=next(q for q in p.new_content if q.summary);s=next(s for s in p.new_solutions if s.item_ref==q.ref)
        for update in ({'mean':'999'},{'variance':'999'},{'exact_answer':{'op':'sqrt','radicand':'999'}},{'method_steps':('forged',)}):self.assertEqual(verify_new_content(q,s.model_copy(update=update)).status,'failed')
    def test_22_invalid_summaries_and_nonfinite(self):
        p=self.packages['standard-lesson'];q=next(q for q in p.new_content if q.summary);s=next(s for s in p.new_solutions if s.item_ref==q.ref)
        for update in ({'sum_x2':'-1'},{'sum_x':'NaN'},{'n':0}):self.assertEqual(verify_new_content(q.model_copy(update={'summary':q.summary.model_copy(update=update)}),s).status,'failed')
    def test_23_corrupt_raw_deviations(self):
        p=self.packages['standard-lesson'];q=next(q for q in p.new_content if q.raw_values);s=next(s for s in p.new_solutions if s.item_ref==q.ref)
        self.assertEqual(verify_new_content(q,s.model_copy(update={'deviations':('0',)})).status,'failed')
    def test_24_unresolved_provider_missing(self):
        p=self.build(provider=lambda *args:None);self.assertFalse(p.content_complete);self.assertTrue(p.unresolved_role_refs);self.assertFalse(p.ready_for_p5c)
    def test_25_minimum_target_distinct(self):
        p=self.build(provider=lambda *args:None);d=next(d for d in p.role_decisions if d.role_key=='SL-12')
        self.assertTrue(d.minimum_met);self.assertFalse(d.target_met);self.assertEqual(d.decision,'unresolved')
    def test_26_bad_provider_math_unresolved(self):
        def provider(*args):
            q,s=author(*args);return q,s.model_copy(update={'numeric_answer':'999'}) if q.summary or q.raw_values else s
        p=self.build(provider=provider);self.assertFalse(p.content_complete);self.assertTrue(p.unresolved_role_refs)
    def test_27_reuse_not_title_based(self):
        role=self.profiles.views['focused-review'].profiled_roles[0]
        a=analyze_role(role,self.a,self.l)[0];b=analyze_role(role.model_copy(update={'title':'Completely different label'}),self.a,self.l)[0]
        self.assertEqual(a,b)
    def test_28_wrong_type_not_reused(self):
        role=self.profiles.views['focused-review'].profiled_roles[4];block=next(b for b in self.a.content_blocks if b.kind=='concept_explanation')
        self.assertFalse(compatibility(role,block,self.a,self.l)['content_type'])
    def test_29_wrong_task_not_reused(self):
        role=self.profiles.views['focused-review'].profiled_roles[4];block=next(b for b in self.a.content_blocks if b.kind=='worked_example')
        altered=self.a.model_copy(update={'worked_examples':tuple(q.model_copy(update={'task_form_refs':()}) for q in self.a.worked_examples)})
        self.assertFalse(compatibility(role,block,altered,self.l)['task_form'])
    def test_30_unknown_alignment_unresolved_analysis(self):
        role=self.profiles.views['focused-review'].profiled_roles[0].model_copy(update={'learning_requirement_refs':('fake',)})
        selected,checks,reason=analyze_role(role,self.a,self.l);self.assertFalse(selected);self.assertTrue(reason)
    def test_31_old_approval_flag_insufficient(self):
        a=self.a.model_copy(update={'content_blocks':self.a.content_blocks[1:]})
        with self.assertRaises(ValueError):build_profiled_content(self.profiles.views['focused-review'],a,self.v,self.l,self.b)
    def test_32_p4b_closed(self):
        v=self.v.model_copy(update={'renderer_readiness':self.v.renderer_readiness.model_copy(update={'ready_for_rendering':False})})
        with self.assertRaises(ValueError):build_profiled_content(self.profiles.views['focused-review'],self.a,v,self.l,self.b)
    def test_33_package_verification(self):
        for k,p in self.packages.items():self.assertTrue(self.check(p,k)['valid'])
    def test_34_forged_verification_labels_rejected(self):
        d=self.packages['standard-lesson'].model_dump(mode='json');d['new_solutions'][1]['numeric_answer']='999'
        self.assertFalse(self.check(d)['valid'])
    def test_35_tampered_prompt_rejected(self):
        d=self.packages['standard-lesson'].model_dump(mode='json');d['new_content'][0]['question']='New unsupported academic claim'
        self.assertFalse(self.check(d)['valid'])
    def test_36_reuse_hash_rejected(self):
        d=self.packages['standard-lesson'].model_dump(mode='json');d['reused_content'][0]['content_sha256']='0'*64
        self.assertFalse(self.check(d)['valid'])
    def test_37_no_render_claim(self):
        for p in self.packages.values():self.assertTrue(p.content_complete);self.assertTrue(p.ready_for_p5c);self.assertFalse(p.ready_for_rendering)
    def test_38_deterministic(self):
        for k,p in self.packages.items():self.assertEqual(p.serialize(),self.build(k).serialize())
    def test_39_no_profile_identity_in_new_ref(self):self.assertTrue(all('SL-' not in q.ref for q in self.packages['standard-lesson'].new_content))
    def test_40_frozen(self):
        before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
        for file,h in before['files'].items():self.assertEqual(hashlib.sha256(Path(file).read_bytes()).hexdigest(),h,file)
    def test_41_service_rejects_stale_chain(self):
        s=ProfiledContentService(DB)
        with patch.object(s._profiles,'read_profiles',side_effect=ValueError('revoked')):
            with self.assertRaisesRegex(ValueError,'revoked'):s.read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
    def test_42_cli_readonly(self):
        from academic_os.profiled_content_service import ProfiledContentRead
        result=ProfiledContentRead(self.packages,{}, {})
        with patch('academic_os.cli.Store',side_effect=AssertionError('write')),patch.object(ProfiledContentService,'read_profiles',return_value=result),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['author-profiled-content','standard-deviation']),0)
    def test_43_export_idempotent(self):
        from academic_os.profiled_content_service import ProfiledContentRead
        result=ProfiledContentRead(self.packages,{}, {})
        with tempfile.TemporaryDirectory() as tmp:
            paths=save_profiled_content(result,tmp);before={p:Path(p).read_bytes() for p in paths};save_profiled_content(result,tmp)
            self.assertEqual(before,{p:Path(p).read_bytes() for p in paths})
            Path(paths[0]).write_text('conflict')
            with self.assertRaises(ValueError):save_profiled_content(result,tmp)
    def test_44_unresolved_is_valid_safety_state(self):
        provider=lambda *args:None
        p=self.build(provider=provider)
        report=verify_profiled_package(p,self.profiles.views['standard-lesson'],self.a,self.v,self.l,self.b,provider)
        self.assertTrue(report['valid']);self.assertFalse(p.content_complete);self.assertFalse(p.ready_for_rendering)
    def test_45_provider_task_scope_rejected(self):
        def provider(*args):
            q,s=author(*args);return q.model_copy(update={'task_form_refs':('unsupported-task',)}),s
        self.assertTrue(self.build(provider=provider).unresolved_role_refs)

if __name__=='__main__':unittest.main()
