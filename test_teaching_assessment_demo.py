import copy
import json
import tempfile
import unittest
from pathlib import Path
from statistics import mean,pvariance,pstdev
from build_teaching_assessment_demo import build_core,derive
from validate_teaching_assessment_demo import validate_core,validate_outputs
from teaching_assessment_content import OUT,cid

class TeachingDemoTests(unittest.TestCase):
    def setUp(self):self.core=build_core()
    def rejects(self,edit):
        edit(self.core)
        with self.assertRaises(ValueError):validate_core(self.core)
    def test_01_9ma0_context(self):self.assertEqual(validate_core(self.core)['context']['qualification_code'],'9MA0')
    def test_02_no_ial_igcse(self):
        for value in ['International GCSE','International A Level','A Level Statistics']:
            with self.subTest(value=value):
                c=copy.deepcopy(self.core);c['context']['qualification']=value
                with self.assertRaises(ValueError):validate_core(c)
    def test_03_independent_ids(self):self.rejects(lambda c:c['competencies'][0].update(competency_id='CAN-ALEVEL-9MA0-TYPE'))
    def test_04_teaching_references(self):self.rejects(lambda c:c['slides'][3]['competency_ids'].append('missing'))
    def test_05_assessment_references(self):self.rejects(lambda c:c['questions'][0]['parts'][0].update(primary_competency='missing'))
    def test_06_mark_scheme_complete(self):
        d=derive(self.core);self.assertEqual({p['part_id'] for q in self.core['questions'] for p in q['parts']},{p['part_id'] for p in d['mark_scheme']['entries']})
    def test_07_mapping_complete(self):self.assertEqual(len(derive(self.core)['question_competency_mapping']['mappings']),21)
    def test_08_marks(self):self.rejects(lambda c:c['questions'][0]['parts'][0].update(marks=3))
    def test_09_difficulty_task_only(self):self.rejects(lambda c:c['competencies'][0].update(predicted_difficulty=3))
    def test_10_repeated_competency(self):
        qs=[q['question_id'] for q in self.core['questions'] if any(p['primary_competency']==cid('MEAN-CALCULATE') for p in q['parts'])]
        self.assertGreaterEqual(len(qs),2)
    def test_11_multi_skill_part(self):self.assertTrue(any(len(p['supporting_competencies'])>=2 for q in self.core['questions'] for p in q['parts']))
    def test_12_exclusive_coverage(self):
        d=derive(self.core)['assessment_coverage_report'];self.assertEqual(sum(d['marks_by_competency'].values()),48)
        self.assertEqual(d['marks_by_topic_group'],dict(data_types=6,location=11,spread=11,comparison=11,lds=9))
    def test_13_alignment_valid(self):
        a=derive(self.core)['teaching_assessment_alignment']['alignment']
        for item in a:
            if item['assessment_parts']:self.assertTrue(item['teaching_slides'] and item['practice_ids'])
    def test_14_nonofficial_notice(self):self.rejects(lambda c:c.update(mark_scheme_notice='Official Pearson mark scheme'))
    def test_15_v02_unchanged(self):self.assertGreaterEqual(validate_outputs()['stable_files_unchanged'],58)
    def test_16_v01_unchanged(self):
        from test_academic_knowledge_v02 import V01_SHA256
        import hashlib
        from teaching_assessment_content import ROOT
        for path,h in V01_SHA256.items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),h,path)
    def test_17_no_promotion(self):self.rejects(lambda c:c['competencies'][0].update(review_status='approved'))
    def test_18_duplicate_id(self):self.rejects(lambda c:c['competencies'].append(c['competencies'][0]))
    def test_19_invalid_marks(self):self.rejects(lambda c:c['questions'][0]['parts'][0].update(marks=0))
    def test_20_demand_range(self):self.rejects(lambda c:c['questions'][0]['parts'][0].update(predicted_difficulty=6))
    def test_21_synthetic_provenance(self):self.rejects(lambda c:c['questions'][0].update(data_provenance='official'))
    def test_22_section_alignment(self):self.rejects(lambda c:c['sections'][0]['slide_ids'].append(99))
    def test_23_tampered_reports_rejected(self):
        import shutil
        for name,key in [('mark_scheme','entries'),('question_competency_mapping','mappings'),('teaching_assessment_alignment','alignment')]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as td:
                for p in OUT.glob('*.json'):shutil.copyfile(p,Path(td)/p.name)
                p=Path(td)/(name+'.json');d=json.loads(p.read_text(encoding='utf-8'));d[key].pop();p.write_text(json.dumps(d),encoding='utf-8')
                with self.assertRaises(ValueError):validate_outputs(td,check_stable=False)
    def test_24_numeric_answers_independent(self):
        self.assertEqual(mean([4,6,7,8,9,13,30]),11)
        self.assertEqual((10*5+20*15+10*25)/40,15)
        x=[47,47,47,47,53,53,53,53]
        self.assertEqual(sum(x),400);self.assertEqual(sum(v*v for v in x),20072)
        self.assertEqual(pvariance(x),9);self.assertEqual(pstdev(x),3)
        self.assertEqual((180-54)/9,14);self.assertAlmostEqual((0+1.2+0+0+4.8)/5,1.2)
    def test_25_unassessed_explicit(self):self.assertEqual(derive(self.core)['assessment_coverage_report']['unassessed_competencies'],[cid('MODE-IDENTIFY'),cid('PURPOSE')])
    def test_26_builder_reproducible(self):self.assertEqual(build_core(),self.core)

if __name__=='__main__':unittest.main()
