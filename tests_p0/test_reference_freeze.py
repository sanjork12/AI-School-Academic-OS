"""Focused engineering freeze assertions, no new production semantics."""
import ast
import builtins
import io
from pathlib import Path
import unittest
from unittest.mock import patch
from tests_p0.reference_freeze import OUT,DOC,ReferenceManifest,read,sha,snapshot_status,production_dependencies,state,counts


class ReferenceFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=read(OUT/'reference_manifest.json');cls.before=read(OUT/'before.json')
        cls.current=state();cls.counts=counts();cls.snapshots=snapshot_status()

    def test_01_architecture_exists(self):self.assertTrue(DOC.is_file())
    def test_02_schema_valid(self):ReferenceManifest.model_validate(self.data)
    def test_03_pre_ai_identity(self):self.assertEqual(self.data['freeze_kind'],'Pre-AI Reference Implementation')
    def test_04_q2_id(self):self.assertEqual(self.data['protected_snapshots'][0]['snapshot_id'],'04765fa526fc03ee889f8e0691a23e07de4dcbd5486a779317a928c0809a7070')
    def test_05_q3_id(self):self.assertEqual(self.data['protected_snapshots'][1]['snapshot_id'],'4c48326cc3b4e3315118d8dc675764a1cff2d8e0c7d37a2f741bc26d928fe826')
    def test_06_current_snapshots(self):self.assertEqual(self.snapshots,self.before['snapshots'])
    def contract(self,name):self.assertIn(name,{c['schema_version'] for c in self.data['contracts']})
    def test_07_teacher(self):self.contract('teacher-topic/2')
    def test_08_assessment(self):self.contract('assessment-intelligence/1')
    def test_09_learning(self):self.contract('learning-specification/1')
    def test_10_pedagogy(self):self.contract('pedagogical-specification/1')
    def test_11_pedagogical_validation(self):self.contract('pedagogical-validation/1')
    def test_12_authored(self):self.contract('authored-teaching-content/1')
    def test_13_authored_validation(self):self.contract('authored-content-validation/1')
    def test_14_profile(self):self.contract('lesson-profile/1')
    def test_15_profiled_pedagogy(self):self.contract('profiled-pedagogical-specification/1')
    def test_16_profiled_authored(self):self.contract('profiled-authored-teaching-content/1')
    def test_17_profiled_validation(self):self.contract('profiled-content-validation/1')
    def profile(self,key):return next(p for p in self.data['lesson_profiles'] if p['profile_key']==key)
    def test_18_focused(self):self.assertEqual(self.profile('focused-review')['substantive_roles'],9)
    def test_19_standard(self):self.assertEqual(self.profile('standard-lesson')['pedagogical_roles'],15)
    def test_20_focused_duration(self):self.assertEqual(self.profile('focused-review')['duration']['target_minutes'],25)
    def test_21_standard_duration(self):self.assertEqual(self.profile('standard-lesson')['duration']['target_minutes'],60)
    def test_22_same_scope(self):self.assertEqual(len({p['academic_scope_fingerprint'] for p in self.data['lesson_profiles']}),1)
    def test_23_focused_ppt(self):self.assertTrue(Path(self.profile('focused-review')['pptx']).is_file())
    def test_24_standard_ppt(self):self.assertTrue(Path(self.profile('standard-lesson')['pptx']).is_file())
    def test_25_ppt_hashes(self):
        artifacts={str(Path(a['path'])):a['sha256'] for a in self.data['reference_artifacts']}
        for p in self.data['lesson_profiles']:self.assertEqual(artifacts[str(Path(p['pptx']))],sha(p['pptx']))
    def test_26_no_gold_import(self):self.assertEqual(production_dependencies(),[])
    def test_27_not_runtime_authority(self):self.assertFalse(self.data['trust_authority']);self.assertEqual(production_dependencies(),[])
    def test_28_db_hash(self):self.assertEqual(self.current['sha256'],self.before['database']['sha256'])
    def test_29_reviews(self):self.assertEqual(self.counts['review_decisions'],self.before['counts']['review_decisions'])
    def test_30_governance(self):self.assertEqual(self.counts['governance_decisions'],self.before['counts']['governance_decisions'])
    def test_31_snapshots(self):self.assertEqual(self.counts['snapshots'],self.before['counts']['snapshots'])
    def test_32_snapshot_rows(self):self.assertEqual(self.current['tables']['snapshots'],self.before['database']['tables']['snapshots'])
    def test_33_all_decisions_requests(self):self.assertEqual(self.counts,self.before['counts']);self.assertEqual(self.current,self.before['database'])
    def test_34_frozen_hashes(self):
        # Historical v1 artifacts stay immutable; current implementation uses the explicitly selected revision.
        from academic_os.ai_qualification.reference_baseline import verify_reference
        result=verify_reference('.', 'v1')
        self.assertTrue(result['valid'],result['errors'])
    def test_35_no_production_dependency_change(self):
        from academic_os.ai_qualification.reference_baseline import verify_reference
        result=verify_reference('.')
        self.assertTrue(result['valid'],result['errors'])
    def test_36_actual_gold_inventory(self):
        for g in self.data['gold_standards']:self.assertEqual(sha(g['path']),g['sha256'])
    def test_37_versions_observed(self):
        for c in self.data['contracts']:
            data=read(c['example_artifact']);self.assertEqual(data.get('schema_version',data.get('format')),c['schema_version'])
    def test_38_three_learning_requirements(self):self.assertEqual(len(self.data['academic_scope']['learning_requirements']),3)
    def test_39_two_examples(self):self.assertEqual([(e['year'],e['question_part']) for e in self.data['academic_scope']['assessment_evidence']],[(2025,'Q2(b)'),(2023,'Q3(b)(ii)')])
    def test_40_live_generation_without_gold_or_manifest(self):
        # Fail on actual attempts to read the oracle directory/reference manifest.
        # This complements static imports; it is not a claim about arbitrary code.
        from academic_os.profiled_content_service import ProfiledContentService
        from academic_os.product_catalog import PROTECTED_SNAPSHOTS
        def wrap(original):
            def guarded(file,*args,**kwargs):
                value=str(file).replace('\\','/').lower()
                if 'tests_p0/fixtures' in value or 'reference_manifest.json' in value:raise AssertionError('Production read acceptance oracle: '+value)
                return original(file,*args,**kwargs)
            return guarded
        with patch('builtins.open',wrap(builtins.open)),patch('io.open',wrap(io.open)):
            current=ProfiledContentService('var/p0_q2.sqlite3').read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
        self.assertEqual(set(current.packages),{'focused-review','standard-lesson'})
        self.assertEqual(state(),self.before['database'])


if __name__=='__main__':unittest.main()
