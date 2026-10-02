"""P4C preservation regressions against the actual rendered package; no new approvals."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import xml.etree.ElementTree as ET
from academic_os.presentation_service import PresentationService,teacher_solutions,runtime
from academic_os.presentation_manifest import build_manifest,validate_manifest
from academic_os.presentation_layout import layout_plan,equation
from academic_os.presentation_validation import validate_artifact,inspect_pptx,NS
from academic_os.product_catalog import PROTECTED_SNAPSHOTS

OUT=Path('output/p4c_presentation')
PPTX=OUT/'student/Standard_Deviation.pptx'

class PresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=PresentationService(Path('var/p0_q2.sqlite3'))
        cls.i=cls.service.read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
        cls.plan=layout_plan(cls.i.manifest,cls.i.authored,cls.i.validation,cls.i.learning)
    def report(self,path=PPTX):
        i=self.i
        return validate_artifact(path,i.manifest,i.authored,i.validation,i.learning)
    def bad_manifest(self,mutate):
        d=self.i.manifest.model_dump(mode='json');mutate(d)
        self.assertTrue(validate_manifest(d,self.i.authored,self.i.validation,self.i.learning))
    def tamper(self,part,mutate):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.pptx'
            with zipfile.ZipFile(PPTX) as source,zipfile.ZipFile(path,'w') as target:
                for item in source.infolist():
                    data=source.read(item.filename)
                    if item.filename==part:
                        root=ET.fromstring(data);mutate(root);data=ET.tostring(root)
                    target.writestr(item,data)
            report=self.report(path)
            self.assertFalse(report.valid,part)
            self.assertTrue(report.violations)
    def test_actual_pptx_passes(self):self.assertTrue(self.report().valid,self.report().violations)
    def test_saved_receipt_matches_current(self):self.assertEqual(self.report().serialize().encode(),(OUT/'artifact_render_validation.json').read_bytes())
    def test_eleven_slides(self):self.assertEqual(len(self.i.manifest.slides),11)
    def test_three_goals(self):self.assertEqual(len(self.i.manifest.slides[0].learning_requirement_refs),3)
    def test_all_objects_mapped(self):self.assertTrue(all(self.i.manifest.content_coverage.values()))
    def test_deterministic_manifest(self):self.assertEqual(build_manifest(self.i.authored,self.i.validation,self.i.learning),self.i.manifest)
    def test_deterministic_layout(self):self.assertEqual(layout_plan(self.i.manifest,self.i.authored,self.i.validation,self.i.learning),self.plan)
    def test_closed_gate(self):
        v=self.i.validation.model_copy(update={'renderer_readiness':self.i.validation.renderer_readiness.model_copy(update={'ready_for_rendering':False})})
        with self.assertRaises(ValueError):build_manifest(self.i.authored,v,self.i.learning)
    def test_false_dimension_cannot_bypass_gate(self):
        v=self.i.validation.model_copy(update={'reference_integrity':self.i.validation.reference_integrity.model_copy(update={'valid':False})})
        with self.assertRaises(ValueError):build_manifest(self.i.authored,v,self.i.learning)
    def test_wrong_content_version(self):
        v=self.i.validation.model_copy(update={'input_contracts':dict(self.i.validation.input_contracts,**{'authored-teaching-content/1':'0'*64})})
        with self.assertRaises(ValueError):build_manifest(self.i.authored,v,self.i.learning)
    def test_wrong_learning_version(self):
        v=self.i.validation.model_copy(update={'input_contracts':dict(self.i.validation.input_contracts,**{'learning-specification/1':'0'*64})})
        with self.assertRaises(ValueError):build_manifest(self.i.authored,v,self.i.learning)
    def test_manifest_order(self):self.bad_manifest(lambda d:d['slides'].reverse())
    def test_manifest_missing_slide(self):self.bad_manifest(lambda d:d['slides'].pop())
    def test_manifest_duplicate(self):self.bad_manifest(lambda d:d['slides'].__setitem__(1,d['slides'][0]))
    def test_manifest_unknown_ref(self):self.bad_manifest(lambda d:d['slides'][1]['content_refs'].append('invented'))
    def test_manifest_missing_lr(self):self.bad_manifest(lambda d:d['slides'][0]['learning_requirement_refs'].pop())
    def test_manifest_teacher_leak(self):self.bad_manifest(lambda d:d['slides'][6]['content_refs'].extend(d['slides'][6]['teacher_only_refs']))
    def test_manifest_new_schema(self):self.bad_manifest(lambda d:d.update(schema_version='presentation-manifest/2'))
    def test_manifest_false_coverage(self):self.bad_manifest(lambda d:d.update(content_coverage={}))
    def test_manifest_wrong_binding(self):self.bad_manifest(lambda d:d['source_validation'].update(authored_content_sha256='x'))
    def test_four_teacher_solutions_exact(self):
        solutions=teacher_solutions(self.i)['solutions'];self.assertEqual(len(solutions),4)
        for s in self.i.authored.solutions:
            if s.ref in solutions:self.assertEqual(solutions[s.ref],s.model_dump(mode='json'))
    def test_teacher_refs_never_painted(self):
        refs=set(teacher_solutions(self.i)['solutions'])
        self.assertFalse(refs & {e['source_ref'] for s in self.plan['slides'] for e in s['elements']})
    def test_no_teacher_notes(self):self.assertEqual(inspect_pptx(PPTX)['notes'],[])
    def test_no_internal_ids_visible(self):
        text=' '.join(e['text'] for s in self.plan['slides'] for e in s['elements'])
        for marker in ('sha256','CON-STAT','CAN-STAT',*PROTECTED_SNAPSHOTS):self.assertNotIn(marker,text)
    def test_unknown_formula_rejected(self):
        with self.assertRaises(ValueError):equation({'op':'invent','args':[]})
    def test_formula_substitution_not_arithmetic(self):self.assertEqual(equation({'op':'square','args':[{'op':'variable','name':'n'}]},{'n':5}),'(5)²')
    def test_plot_has_ten_editable_points(self):self.assertEqual(sum(e['kind']=='ellipse' for e in self.plan['slides'][2]['elements']),10)
    def test_changed_question(self):self.tamper('ppt/slides/slide7.xml',lambda r:setattr(r.find('.//a:t',NS),'text','Answer is 2'))
    def test_changed_formula(self):self.tamper('ppt/slides/slide5.xml',lambda r:setattr(next(t for t in r.findall('.//a:t',NS) if '√' in (t.text or '')),'text','σ = 99'))
    def test_missing_shape(self):self.tamper('ppt/slides/slide2.xml',lambda r:r.find('p:cSld/p:spTree',NS).remove(r.find('.//p:sp',NS)))
    def test_extra_answer_shape(self):self.tamper('ppt/slides/slide7.xml',lambda r:r.find('p:cSld/p:spTree',NS).append(copy.deepcopy(r.find('.//p:sp',NS))))
    def test_hidden_slide(self):self.tamper('ppt/slides/slide7.xml',lambda r:r.set('show','0'))
    def test_tiny_text(self):self.tamper('ppt/slides/slide7.xml',lambda r:r.find('.//a:rPr',NS).set('sz','1'))
    def test_white_text(self):self.tamper('ppt/slides/slide7.xml',lambda r:r.find('.//a:rPr/a:solidFill/a:srgbClr',NS).set('val','FFFFFF'))
    def test_changed_geometry(self):self.tamper('ppt/slides/slide3.xml',lambda r:r.find('.//a:xfrm/a:off',NS).set('x','0'))
    def test_changed_slide_order(self):
        def mutate(r):
            ids=r.find('p:sldIdLst',NS);first=ids[0];ids.remove(first);ids.append(first)
        self.tamper('ppt/presentation.xml',mutate)
    def test_missing_slide(self):self.tamper('ppt/presentation.xml',lambda r:r.find('p:sldIdLst',NS).remove(r.find('p:sldIdLst',NS)[-1]))
    def test_missing_package(self):self.assertFalse(self.report(Path('does-not-exist.pptx')).valid)
    def test_gate_failure_creates_no_output(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(self.service,'read_topic',side_effect=ValueError('revoked')),patch('academic_os.presentation_service.subprocess.run') as run:
            out=Path(folder)/'out'
            with self.assertRaisesRegex(ValueError,'revoked'):self.service.render('standard-deviation',PROTECTED_SNAPSHOTS,out)
            self.assertFalse(out.exists());run.assert_not_called()
    def test_repeat_reuses_exact_bytes(self):
        before=PPTX.read_bytes()
        with patch.object(self.service,'read_topic',return_value=self.i) as read,patch('academic_os.presentation_service.subprocess.run') as run:
            self.assertTrue(self.service.render('standard-deviation',PROTECTED_SNAPSHOTS,OUT)['reused']);read.assert_called_once();run.assert_not_called()
        self.assertEqual(before,PPTX.read_bytes())
    def test_missing_runtime_fails_closed(self):
        with patch.dict('os.environ',{'P4C_NODE':'__missing_node__'}):
            with self.assertRaises(ValueError):runtime()
    def test_frozen_files_unchanged(self):
        before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
        for file,h in before['files'].items():self.assertEqual(hashlib.sha256(Path(file).read_bytes()).hexdigest(),h,file)
    def test_database_unchanged(self):
        from tests_p0.teacher_product_acceptance import state
        self.assertEqual(state(),json.loads((OUT/'before.json').read_text(encoding='utf-8'))['database'])

if __name__=='__main__':unittest.main()
