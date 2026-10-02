"""Design profile regression: presentation changes only, real PPTX preservation."""
import hashlib,json,tempfile,unittest,copy,zipfile
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
from academic_os.presentation_service import PresentationService,teacher_solutions
from academic_os.presentation_manifest import build_manifest,validate_manifest
from academic_os.presentation_layout import layout_plan,equation,SYMBOLS
from academic_os.presentation_design import scale_position,Components,LABELS,TYPE
from academic_os.presentation_validation import validate_artifact,inspect_pptx,NS
from academic_os.product_catalog import PROTECTED_SNAPSHOTS

OUT=Path('output/p4c1_presentation_design');PPTX=OUT/'Standard_Deviation_v2.pptx'

class PresentationDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=PresentationService(Path('var/p0_q2.sqlite3'))
        cls.i=cls.service.read_topic('standard-deviation',PROTECTED_SNAPSHOTS,'standard-deviation-classroom/2')
        cls.plan=layout_plan(cls.i.manifest,cls.i.authored,cls.i.validation,cls.i.learning)
        cls.old=build_manifest(cls.i.authored,cls.i.validation,cls.i.learning)
    def page(self,n):return self.plan['slides'][n-1]
    def text(self,n):return '\n'.join(e['text'] for e in self.page(n)['elements'] if e['kind']=='text')
    def report(self,path=PPTX):return validate_artifact(path,self.i.manifest,self.i.authored,self.i.validation,self.i.learning)
    def test_01_eleven_slides(self):self.assertEqual(len(self.plan['slides']),11)
    def test_02_student_content_refs(self):
        self.assertTrue(self.report().valid)
        for s in self.i.manifest.slides:
            for r in s.content_refs:self.assertIn(s.ref,self.report().content_coverage[r])
    def test_03_three_learning_requirements(self):self.assertEqual(set(self.report().learning_requirement_refs),{r.ref for r in self.i.learning.learning_requirements})
    def test_04_formulas_preserved(self):
        for f in self.i.authored.instructional_formulas:
            self.assertTrue(any(e['text']=='σ = '+equation(f.expression) and e['source_ref']==f.ref for s in self.plan['slides'] for e in s['elements']))
    def test_05_all_questions_and_inputs_unchanged(self):
        for q in (*self.i.authored.worked_examples,*self.i.authored.practice_items,*self.i.authored.learning_checks):
            elems=[e for s in self.plan['slides'] for e in s['elements'] if e['source_ref']==q.ref]
            self.assertIn(q.question,[e['text'] for e in elems])
            if q.summary:
                for k in ('n','sum_x','sum_x2'):self.assertIn(SYMBOLS[k]+' = '+str(getattr(q.summary,k)),[e['text'] for e in elems])
    def test_06_worked_answer_unchanged(self):
        s=next(s for s in self.i.authored.solutions if 'worked' in s.ref)
        self.assertIn('σ ≈ '+s.display_answer,self.text(6))
    def test_07_dataset_a(self):self.assertEqual(self.page(3)['metadata']['plots'][0]['values'],['8','9','10','11','12'])
    def test_08_dataset_b(self):self.assertEqual(self.page(3)['metadata']['plots'][1]['values'],['2','6','10','14','18'])
    def test_09_shared_scale(self):
        a,b=self.page(3)['metadata']['plots']
        for k in ('minimum','maximum','left','width'):self.assertEqual(a[k],b[k])
    def test_10_both_means(self):self.assertTrue(all(p['mean']=='10' for p in self.page(3)['metadata']['plots']))
    def test_11_proportional_positions(self):
        for label,p in zip('AB',self.page(3)['metadata']['plots']):
            points=[e for e in self.page(3)['elements'] if e['kind']=='ellipse' and '/'+label+'/' in e['source_field']]
            for value,e in zip(p['values'],points):self.assertAlmostEqual(e['x']+e['w']/2,scale_position(value,p['minimum'],p['maximum'],p['left'],p['width']),places=3)
        self.assertEqual(scale_position(10,2,18,248,904),700)
        self.assertEqual(scale_position(6,2,18,248,904)-248,226)
    def test_12_visual_spread_b_exceeds_a(self):
        spreads=[]
        for label in 'AB':
            x=[e['x'] for e in self.page(3)['elements'] if e['kind']=='ellipse' and '/'+label+'/' in e['source_field']];spreads.append(max(x)-min(x))
        self.assertEqual(spreads[1],4*spreads[0])
    def definition(self,key):
        b=next(b for b in self.i.authored.content_blocks if b.kind=='summary_statistics_method')
        self.assertIn(b.instructional_inputs[key],self.text(5))
    def test_13_n_definition(self):self.definition('n')
    def test_14_sum_definition(self):self.definition('sum_x')
    def test_15_squares_definition(self):self.definition('sum_x2')
    def test_16_task_formula(self):
        b=next(b for b in self.i.authored.content_blocks if b.kind=='summary_statistics_method')
        f=next(f for f in self.i.authored.instructional_formulas if f.ref in b.formula_refs)
        self.assertIn('σ = '+equation(f.expression),self.text(5))
    def test_17_given_formula_calculate_order(self):
        positions={e['text']:e['y'] for e in self.page(5)['elements']}
        self.assertLess(positions['WHAT YOU ARE GIVEN'],positions['SUBSTITUTE INTO']);self.assertLess(positions['SUBSTITUTE INTO'],positions['CALCULATE σ'])
    def test_18_identify_stage(self):self.assertIn('IDENTIFY',self.text(6))
    def test_19_substitute_stage(self):self.assertIn('SUBSTITUTE',self.text(6))
    def test_20_simplify_stage(self):self.assertIn('SIMPLIFY',self.text(6))
    def test_21_answer_stage(self):self.assertIn('ANSWER',self.text(6))
    def test_22_final_answer(self):self.assertIn('σ ≈ 3.16',self.text(6))
    def no_solution(self,n):
        refs=set(self.i.manifest.slides[n-1].teacher_only_refs)
        self.assertFalse(refs & {e['source_ref'] for e in self.page(n)['elements']})
        for s in self.i.authored.solutions:
            if s.ref in refs:
                for value in (s.display_answer,s.expected_meaning,*s.method_steps):
                    if value:self.assertNotIn(value,self.text(n))
        self.assertNotIn('√',self.text(n));self.assertNotIn('σ =',self.text(n));self.assertNotIn('σ ≈',self.text(n))
    def test_23_practice_one_no_answer(self):
        self.no_solution(7);self.assertNotIn('2',[e['text'] for e in self.page(7)['elements']])
    def test_24_practice_two_no_answer(self):self.no_solution(8)
    def test_25_concept_no_answer(self):self.no_solution(9)
    def test_26_calculation_no_answer(self):self.no_solution(10)
    def test_27_teacher_file_unchanged(self):self.assertEqual((OUT/'teacher_solutions.json').read_bytes(),Path('output/p4c_presentation/teacher_solutions.json').read_bytes())
    def test_28_text_classification(self):
        for s in self.plan['slides']:
            for e in s['elements']:
                if e['kind']=='text':
                    self.assertIn(e['text_class'],('upstream_content','renderer_label','footer','slide_number'))
                    if e['text_class']=='upstream_content':self.assertTrue(e['source_ref']);self.assertTrue(e['source_field'])
                    if e['text_class']=='renderer_label':self.assertIn(e['text'],LABELS)
    def test_29_unsupported_label_rejected(self):
        c=Components(self.i.manifest.slides[0],self.i.authored.identity)
        with self.assertRaises(ValueError):c.label(0,0,500,'Memorise this formula for the exam')
    def test_30_manifest_refs_unchanged(self):
        for a,b in zip(self.old.slides,self.i.manifest.slides):
            for k in ('content_refs','learning_requirement_refs','teacher_only_refs','visual_refs','slide_type','slide_number'):self.assertEqual(getattr(a,k),getattr(b,k))
        self.assertEqual(self.old.source_validation,self.i.manifest.source_validation)
    def test_31_deterministic_layout(self):self.assertEqual(self.plan,layout_plan(self.i.manifest,self.i.authored,self.i.validation,self.i.learning))
    def test_32_invalid_scale(self):
        for args in ((1,2,2,0,500),(20,2,18,0,500)):
            with self.assertRaises(ValueError):scale_position(*args)
    def test_33_nine_layout_families(self):self.assertGreaterEqual(len({p['layout_family'] for p in self.plan['slides']}),9)
    def test_34_meaningful_working_space(self):
        for n in (7,8,9,10):
            lines=[e for e in self.page(n)['elements'] if e['component']=='working_space' and e['kind']=='rect']
            self.assertEqual(len(lines),3);self.assertGreater(min(e['w'] for e in lines),1000);self.assertGreater(max(e['y'] for e in lines)-min(e['y'] for e in lines),100)
    def test_35_typography_roles(self):self.assertEqual(len(TYPE),8)
    def test_36_actual_pptx_valid(self):self.assertTrue(self.report().valid,self.report().violations)
    def test_37_saved_report_matches(self):self.assertEqual(self.report().serialize().encode(),(OUT/'artifact_render_validation.json').read_bytes())
    def test_38_old_files_frozen(self):
        before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
        for file,h in before['files'].items():self.assertEqual(hashlib.sha256(Path(file).read_bytes()).hexdigest(),h,file)
    def test_39_database_frozen(self):
        from tests_p0.teacher_product_acceptance import state
        self.assertEqual(state(),json.loads((OUT/'before.json').read_text(encoding='utf-8'))['database'])
    def test_40_unknown_profile_fails_closed(self):
        with self.assertRaises(ValueError):build_manifest(self.i.authored,self.i.validation,self.i.learning,'invented')
    def test_41_no_inferred_worked_steps(self):
        fields={e['source_field'] for e in self.page(6)['elements'] if 'worked-solution' in str(e['source_ref'])}
        self.assertTrue({f'method_steps/{i}' for i in range(4)}<=fields)
        self.assertNotIn('110 − 100',self.text(6))
    def test_42_student_package_has_no_notes(self):self.assertFalse(inspect_pptx(PPTX)['notes'])
    def test_43_repeat_checks_live_inputs(self):
        with patch.object(self.service,'read_topic',return_value=self.i) as read:
            self.assertTrue(self.service.render('standard-deviation',PROTECTED_SNAPSHOTS,OUT,'classroom-v2')['reused'])
            read.assert_called_once_with('standard-deviation',PROTECTED_SNAPSHOTS,'standard-deviation-classroom/2')
    def test_44_actual_answer_injection_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.pptx'
            with zipfile.ZipFile(PPTX) as source,zipfile.ZipFile(path,'w') as target:
                for item in source.infolist():
                    data=source.read(item.filename)
                    if item.filename=='ppt/slides/slide7.xml':
                        root=ET.fromstring(data);root.find('.//a:t',NS).text='Answer: 2';data=ET.tostring(root)
                    target.writestr(item,data)
            self.assertFalse(self.report(path).valid)

if __name__=='__main__':unittest.main()
