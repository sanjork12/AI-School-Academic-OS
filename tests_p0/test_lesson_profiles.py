"""P5A scope, density, trust and no-authoring regressions."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from academic_os.lesson_profiles import lesson_profile,validate_lesson_profile,KEYS,DENSITY_KEYS
from academic_os.lesson_profile_models import LessonProfile,ProfiledPedagogicalSpecification
from academic_os.lesson_profile_service import LessonProfileService,save_profile_read
from academic_os.learning_service import LearningSpecificationService
from academic_os.pedagogical_core import build_pedagogical_specification
from academic_os.profiled_pedagogy import build_profiled_pedagogy,validate_profiled_pedagogy,scope_fingerprint
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.cli import main
from tests_p0.teacher_product_acceptance import state

OUT=Path('output/p5a_lesson_profiles');DB=Path('var/p0_q2.sqlite3')
class LessonProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state();cls.learning=LearningSpecificationService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS).view
        cls.base=build_pedagogical_specification(cls.learning)
        cls.profiles={k:lesson_profile(k) for k in KEYS}
        cls.views={k:build_profiled_pedagogy(cls.learning,cls.base,p) for k,p in cls.profiles.items()}
    @classmethod
    def tearDownClass(cls):assert cls.before==state()
    def bad(self,change,key='standard-lesson'):
        data=self.views[key].model_dump(mode='json');change(data)
        report=validate_profiled_pedagogy(data,self.learning,self.base,self.profiles[key])
        self.assertFalse(report.valid);self.assertTrue(report.violations);self.assertFalse(report.ready_for_rendering)
    def test_01_profile_identity(self):
        for k in KEYS:self.assertEqual(self.profiles[k].identity.profile_key,k)
    def test_02_duration(self):
        for k,target,lo,hi in [('focused-review',25,20,30),('standard-lesson',60,50,60)]:
            d=self.profiles[k].duration;self.assertEqual((d.target_minutes,d.acceptable_range_minutes.min,d.acceptable_range_minutes.max),(target,lo,hi))
    def test_03_focused_density(self):self.assertEqual([getattr(self.profiles[KEYS[0]].density_policy,k).target for k in DENSITY_KEYS],[1,1,0,1,0,1,1,0,2,1,1,0])
    def test_04_standard_density(self):self.assertEqual([getattr(self.profiles[KEYS[1]].density_policy,k).target for k in DENSITY_KEYS],[1,1,1,1,1,1,2,2,3,1,1,1])
    def test_05_independent_minimum_target(self):
        count=self.profiles[KEYS[1]].density_policy.independent_practice;self.assertEqual((count.minimum,count.target),(2,3))
    def test_06_focused_nine_roles(self):self.assertEqual([r.role_key for r in self.views[KEYS[0]].profiled_roles],[f'FR-{n:02}' for n in range(1,10)])
    def test_07_standard_fifteen_roles(self):self.assertEqual([r.role_key for r in self.views[KEYS[1]].profiled_roles],[f'SL-{n:02}' for n in range(1,16)])
    def test_08_same_learning_refs(self):
        refs=tuple(sorted(r.ref for r in self.learning.learning_requirements))
        for v in self.views.values():self.assertEqual(v.learning_requirement_refs,refs)
    def test_09_same_coverage_refs(self):
        refs=tuple(sorted(r.ref for r in self.learning.coverage_requirements))
        for v in self.views.values():self.assertEqual(v.coverage_requirement_refs,refs)
    def test_10_same_scope_fingerprint(self):self.assertEqual(self.views[KEYS[0]].academic_scope_fingerprint,self.views[KEYS[1]].academic_scope_fingerprint)
    def test_11_scope_binds_definition_content(self):
        d=self.learning.model_dump(mode='json');d['learning_requirements'][0]['statement']+=' changed'
        self.assertNotEqual(scope_fingerprint(d),scope_fingerprint(self.learning))
    def test_12_scope_excludes_profile_time(self):
        self.assertEqual(self.views[KEYS[0]].source_learning_specification,self.views[KEYS[1]].source_learning_specification)
        self.assertNotEqual(self.profiles[KEYS[0]].duration,self.profiles[KEYS[1]].duration)
    def test_13_evidence_boundaries_verbatim(self):
        for v in self.views.values():self.assertEqual(v.evidence_boundaries,self.learning.evidence_boundaries)
    def test_14_lineage_resolves(self):
        refs={b.ref for b in self.base.teaching_blocks}
        for v in self.views.values():
            for r in v.profiled_roles:
                if r.base_teaching_block_ref:self.assertIn(r.base_teaching_block_ref,refs)
    def test_15_worked_expansion_lineage(self):
        a,b=self.views[KEYS[1]].profiled_roles[7:9]
        self.assertEqual(a.base_teaching_block_ref,b.base_teaching_block_ref);self.assertEqual(b.origin,'profile_density_expansion')
    def test_16_guided_is_support_mode(self):
        roles=self.views[KEYS[1]].profiled_roles[9:11]
        self.assertEqual([r.support_mode for r in roles],['guided','guided'])
    def test_17_no_difficulty_prerequisites_history(self):
        for p in self.profiles.values():self.assertEqual((p.difficulty_policy,p.prerequisite_policy,p.learner_history_policy),('not_asserted',)*3)
    def test_18_no_slide_count(self):
        for p in self.profiles.values():self.assertEqual(p.renderer_policy.duration_to_slide_count,'prohibited')
        for v in self.views.values():
            data=v.serialize()
            for field in ('slide_count','target_slides','student_level','difficulty_level'):self.assertNotIn('"'+field+'"',data)
    def test_19_no_content_authored(self):
        for v in self.views.values():
            self.assertTrue(all(a.status=='unpopulated' for a in v.authoring_requirements))
            for forbidden in ('question','answer','numbers','formula','dataset'):self.assertNotIn('"'+forbidden+'"',v.serialize())
    def test_20_new_authoring_slots(self):
        v=self.views[KEYS[1]];keys={r.ref:r.role_key for r in v.profiled_roles}
        self.assertEqual({keys[a.role_ref] for a in v.authoring_requirements if a.reuse_hint=='new_authoring_required'},{'SL-04','SL-06','SL-09','SL-10','SL-11','SL-15'})
        self.assertEqual(next(a.additional_target_items for a in v.authoring_requirements if keys[a.role_ref]=='SL-12'),1)
    def test_21_reuse_not_completion(self):
        for v in self.views.values():
            self.assertFalse(v.scope_validation.ready_as_authored_content);self.assertFalse(v.scope_validation.ready_for_rendering)
            self.assertTrue(all(a.reuse_is_not_validated for a in v.authoring_requirements))
    def test_22_time_ranges_not_sum_gate(self):
        p=self.profiles[KEYS[1]];self.assertGreater(sum(x.suggested_range_minutes.max for x in p.time_plan.phases),p.duration.target_minutes)
        self.assertTrue(validate_profiled_pedagogy(self.views[KEYS[1]],self.learning,self.base,p).valid)
    def test_23_focused_framing_not_counted(self):self.assertTrue(all(r.substantive for r in self.views[KEYS[0]].profiled_roles))
    def test_24_standard_orientation_framing(self):
        r=self.views[KEYS[1]].profiled_roles[0];self.assertFalse(r.substantive);self.assertEqual(r.items.target,0)
    def test_25_mini_example_only_calculation(self):
        r=self.views[KEYS[1]].profiled_roles[5];self.assertEqual(r.learning_requirement_refs,tuple(x.ref for x in self.learning.learning_requirements if x.type=='capability'))
    def test_26_exit_assesses_all(self):self.assertEqual(self.views[KEYS[1]].profiled_roles[-1].assesses_learning_requirement_refs,self.views[KEYS[1]].learning_requirement_refs)
    def test_27_role_order(self):self.bad(lambda d:d['profiled_roles'].reverse())
    def test_28_lr_clone_rejected(self):self.bad(lambda d:d['learning_requirement_refs'].append('new-profile-lr'))
    def test_29_boundary_weakened(self):self.bad(lambda d:d['evidence_boundaries'].pop())
    def test_30_density_reduced(self):self.bad(lambda d:d['density_summary']['guided_practice'].update(target=1))
    def test_31_fingerprint_forgery(self):self.bad(lambda d:d.update(academic_scope_fingerprint='0'*64))
    def test_32_lineage_forgery(self):self.bad(lambda d:d['profiled_roles'][1].update(base_teaching_block_ref='fake'))
    def test_33_role_scope_expansion(self):self.bad(lambda d:d['profiled_roles'][5]['learning_requirement_refs'].append('sample-sd'))
    def test_34_content_payload_rejected(self):self.bad(lambda d:d['authoring_requirements'][0].update(question='New generated question'))
    def test_35_false_ready_rejected(self):self.bad(lambda d:d['scope_validation'].update(ready_for_rendering=True))
    def test_36_unknown_profile(self):
        with self.assertRaises(ValueError):lesson_profile('advanced')
    def test_37_profile_policy_tampering(self):
        for field,value in [('academic_scope_policy','expand'),('prerequisite_policy','mean'),('difficulty_policy','easy')]:
            data=self.profiles[KEYS[0]].model_dump(mode='json');data[field]=value
            with self.assertRaises(ValueError):validate_lesson_profile(data)
    def test_38_gold_density_tampering(self):
        data=self.profiles[KEYS[1]].model_dump(mode='json');data['density_policy']['independent_practice']['target']=99
        with self.assertRaises(ValueError):validate_lesson_profile(data)
    def test_39_profile_duration_invalid(self):
        data=self.profiles[KEYS[0]].model_dump(mode='json');data['duration']['acceptable_range_minutes']['max']=10
        with self.assertRaises(ValueError):validate_lesson_profile(data)
    def test_40_stale_base_rejected(self):
        data=self.learning.model_dump(mode='json');data['learning_requirements'][0]['statement']+=' changed'
        with self.assertRaises(ValueError):build_profiled_pedagogy(data,self.base,self.profiles[KEYS[0]])
    def test_41_determinism(self):
        for k in KEYS:self.assertEqual(build_profiled_pedagogy(self.learning,self.base,lesson_profile(k)).serialize(),self.views[k].serialize())
    def test_42_role_counts_equal_density(self):
        for v in self.views.values():
            for kind in DENSITY_KEYS:self.assertEqual(sum(r.items.target for r in v.profiled_roles if r.kind==kind),getattr(v.density_summary,kind).target)
    def test_43_frozen_files(self):
        before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
        for p,h in before['files'].items():self.assertEqual(hashlib.sha256(Path(p).read_bytes()).hexdigest(),h,p)
    def test_44_live_service(self):
        result=LessonProfileService(DB).read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
        for k in KEYS:self.assertEqual(result.views[k],self.views[k])
    def test_45_source_failure_propagates(self):
        s=LessonProfileService(DB)
        with patch.object(s._learning,'read_topic',side_effect=ValueError('source revoked')):
            with self.assertRaisesRegex(ValueError,'revoked'):s.read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
    def test_46_json_not_trusted_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fake.json';path.write_text('{"approved":true}')
            with self.assertRaises(Exception):LessonProfileService(path).read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
    def test_47_export_idempotent_conflict(self):
        result=LessonProfileService(DB).read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
        with tempfile.TemporaryDirectory() as tmp:
            paths=save_profile_read(result,tmp);before={p:Path(p).read_bytes() for p in paths}
            save_profile_read(result,tmp);self.assertEqual(before,{p:Path(p).read_bytes() for p in paths})
            Path(paths[0]).write_text('conflict')
            with self.assertRaisesRegex(ValueError,'Different existing'):save_profile_read(result,tmp)
    def test_48_cli_does_not_open_writable_store(self):
        import contextlib,io
        with patch('academic_os.cli.Store',side_effect=AssertionError('writable store')),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['lesson-profiles']),0)
            self.assertEqual(main(['--db',str(DB),'profile-pedagogy','standard-deviation']),0)
    def test_49_no_input_mutation(self):
        before=(self.learning.serialize(),self.base.serialize())
        for k in KEYS:build_profiled_pedagogy(self.learning,self.base,self.profiles[k])
        self.assertEqual(before,(self.learning.serialize(),self.base.serialize()))
    def test_50_source_version_binding(self):self.bad(lambda d:d['source_learning_specification'].update(sha256='0'*64))

if __name__=='__main__':unittest.main()
