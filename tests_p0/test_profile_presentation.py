"""P5D tests use isolated mutations, never mutate trusted artifacts."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from xml.etree import ElementTree as ET

from academic_os.profile_presentation import build_profile_manifest, validate_profile_manifest, same_scope, profile_teacher_solutions
from academic_os.profile_presentation_layout import profile_layout, PROFILE_LABELS
from academic_os.profile_presentation_service import ProfilePresentationService
from academic_os.profile_presentation_validation import validate_profile_artifact
from academic_os.profiled_content_models import ProfiledAuthoredPackage
from academic_os.profiled_content_validation import validate_profiled_content
from academic_os.presentation_manifest import build_manifest
from academic_os.presentation_layout import layout_plan
from academic_os.presentation_design import LABELS
from academic_os.presentation_validation import NS
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state

OUT=Path('output/p5d_profiled_presentation')


class ProfilePresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=state()
        cls.inputs,_=ProfilePresentationService('var/p0_q2.sqlite3').read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
        cls.manifests={k:build_profile_manifest(i) for k,i in cls.inputs.items()}
        cls.plans={k:profile_layout(cls.manifests[k],i) for k,i in cls.inputs.items()}

    @classmethod
    def tearDownClass(cls):
        assert cls.before==state()

    def test_01_current_gates(self):
        self.assertTrue(all(i.report.renderer_readiness.ready_for_rendering for i in self.inputs.values()))

    def test_02_academic_invariance(self):
        same_scope(self.inputs)
        self.assertEqual(len({m.academic_scope_fingerprint for m in self.manifests.values()}),1)

    def test_03_all_roles(self):
        for k,n in (('focused-review',9),('standard-lesson',15)):
            self.assertEqual(len(self.manifests[k].role_coverage),n)
            self.assertTrue(all(self.manifests[k].role_coverage.values()))

    def test_04_density_drives_length(self):
        self.assertGreater(len(self.manifests['standard-lesson'].slides),len(self.manifests['focused-review'].slides))

    def test_05_focused_semantic_regression(self):
        i=self.inputs['focused-review'];old=build_manifest(i.authored,i.p4b,i.learning,'standard-deviation-classroom/2')
        new=self.manifests['focused-review']
        self.assertEqual([(s.content_refs,s.teacher_only_refs,s.learning_requirement_refs) for s in old.slides],[(s.content_refs,s.teacher_only_refs,s.learning_requirement_refs) for s in new.slides])
        old_plan=layout_plan(old,i.authored,i.p4b,i.learning)
        extract=lambda plan:[[(e['source_ref'],e['source_field'],e['text']) for e in p['elements'] if e.get('text_class')=='upstream_content' and e['source_ref']!='focused-review'] for p in plan['slides']]
        self.assertEqual(extract(old_plan),extract(self.plans['focused-review']))

    def test_06_composite_children(self):
        m=self.manifests['standard-lesson'];i=self.inputs['standard-lesson']
        d=next(d for d in i.package.role_decisions if d.role_key=='SL-12')
        pages=[s for s in m.slides if d.role_ref in s.profile_role_refs]
        self.assertEqual(len(pages),3)
        self.assertTrue(set(d.reused_content_refs+d.new_content_refs)<=set(r for s in pages for r in s.content_refs))

    def test_07_exit_split(self):
        m=self.manifests['standard-lesson']
        self.assertEqual([s.slide_type for s in m.slides[-3:]],['exit_concept','exit_calculation','learning_summary'])

    def test_08_false_gate(self):
        i=self.inputs['standard-lesson'];report=i.report.model_copy(update={'renderer_readiness':i.report.renderer_readiness.model_copy(update={'ready_for_rendering':False})})
        with self.assertRaises(ValueError):build_profile_manifest(replace(i,report=report))

    def test_09_spoofed_stale_report(self):
        i=self.inputs['standard-lesson'];p=i.package.model_copy(update={'academic_scope_fingerprint':'0'*64})
        with self.assertRaises(ValueError):build_profile_manifest(replace(i,package=p))

    def test_10_scope_difference(self):
        i=self.inputs['standard-lesson'];p=i.package.model_copy(update={'academic_scope_fingerprint':'0'*64})
        with self.assertRaises(ValueError):same_scope(dict(self.inputs,**{'standard-lesson':replace(i,package=p)}))

    def test_11_minimum_target_subset(self):
        i=self.inputs['standard-lesson'];d=i.package.model_dump(mode='json')
        q=next(q for q in d['new_content'] if q['semantic_role']=='independent_practice');s=next(s for s in d['new_solutions'] if s['item_ref']==q['ref'])
        d['new_content'].remove(q);d['new_solutions'].remove(s)
        role=next(r for r in d['role_decisions'] if r['role_key']=='SL-12')
        role['new_content_refs'].remove(q['ref']);role['solution_refs'].remove(s['ref']);role['decision']='reuse'
        package=ProfiledAuthoredPackage.model_validate(d)
        report=validate_profiled_content(package,i.profile,i.pedagogy,i.authored,i.p4b,i.learning,i.base)
        m=build_profile_manifest(replace(i,package=package,report=report))
        self.assertFalse(m.target_density_attained)
        self.assertEqual(len(m.slides),len(self.manifests['standard-lesson'].slides)-1)
        self.assertNotIn(q['ref'],m.content_coverage)

    def test_12_manifest_drop_role(self):
        m=self.manifests['standard-lesson']
        with self.assertRaises(ValueError):validate_profile_manifest(m.model_copy(update={'slides':m.slides[:-2]}),self.inputs['standard-lesson'])

    def test_13_manifest_answer_visibility(self):
        m=self.manifests['standard-lesson'];slides=list(m.slides);n=next(n for n,s in enumerate(slides) if s.teacher_only_refs)
        slides[n]=slides[n].model_copy(update={'content_refs':slides[n].content_refs+slides[n].teacher_only_refs})
        with self.assertRaises(ValueError):validate_profile_manifest(m.model_copy(update={'slides':tuple(slides)}),self.inputs['standard-lesson'])

    def test_14_manifest_profile_identity(self):
        m=self.manifests['standard-lesson']
        with self.assertRaises(ValueError):validate_profile_manifest(m.model_copy(update={'profile_key':'focused-review'}),self.inputs['standard-lesson'])

    def test_15_solution_sources_not_visible(self):
        for k,m in self.manifests.items():
            for s,p in zip(m.slides,self.plans[k]['slides']):
                self.assertFalse(set(s.teacher_only_refs)&{e['source_ref'] for e in p['elements']})

    def test_16_exact_teacher_objects(self):
        for k,i in self.inputs.items():
            actual=profile_teacher_solutions(i,self.manifests[k]);original={s.ref:s.model_dump(mode='json') for s in (*i.authored.solutions,*i.package.new_solutions)}
            for ref,data in actual['solutions'].items():
                self.assertEqual(data['solution'],original[ref]);self.assertTrue(data['profile_role_refs'])

    def test_17_scaffolding_preserved(self):
        i=self.inputs['standard-lesson'];plan=self.plans['standard-lesson']
        for q in i.package.new_content:
            if q.semantic_role=='guided_practice':
                actual=[e['text'] for p in plan['slides'] for e in p['elements'] if e['source_ref']==q.ref and e['source_field'].startswith('scaffolding/')]
                self.assertEqual(actual,list(q.scaffolding))

    def test_18_guided_independent_distinct(self):
        plan=self.plans['standard-lesson'];guided=[p for p in plan['slides'] if p['layout_family']=='guided_practice']
        independent=[p for p in plan['slides'] if p['layout_family']=='profile_practice']
        self.assertTrue(guided and independent)
        self.assertTrue(all(any(e['component']=='guided_working_space' for e in p['elements']) for p in guided))
        self.assertTrue(all(not any(e['source_field'].startswith('scaffolding/') for e in p['elements']) for p in independent))

    def test_19_raw_example_actual_values(self):
        i=self.inputs['standard-lesson'];q=next(q for q in i.package.new_content if q.raw_values)
        texts=[e['text'] for p in self.plans['standard-lesson']['slides'] for e in p['elements'] if e['source_ref']==q.ref]
        self.assertIn(', '.join(q.raw_values),texts)

    def test_20_labels_classified(self):
        for plan in self.plans.values():
            for page in plan['slides']:
                for e in page['elements']:
                    if e['kind']!='text':continue
                    if e['text_class']=='renderer_label':self.assertIn(e['text'],LABELS)
                    elif e['text_class']=='profile_renderer_label':self.assertIn(e['text'],PROFILE_LABELS)
                    elif e['text_class']=='upstream_content':self.assertTrue(e['source_ref'])
                    else:self.assertIn(e['text_class'],('footer','slide_number'))

    def test_21_determinism(self):
        for k,i in self.inputs.items():self.assertEqual(build_profile_manifest(i).serialize(),self.manifests[k].serialize())

    def test_22_live_failure_no_output(self):
        with tempfile.TemporaryDirectory() as temp,patch('academic_os.profile_presentation_service.ProfiledContentValidationService.read_profiles',side_effect=ValueError('revoked')):
            with self.assertRaises(ValueError):ProfilePresentationService('var/p0_q2.sqlite3').render('standard-deviation',PROTECTED_SNAPSHOTS,temp)
            self.assertEqual(list(Path(temp).iterdir()),[])

    def test_23_final_artifacts_valid(self):
        for k,i in self.inputs.items():
            p=OUT/k/('Standard_Deviation_'+k+'.pptx')
            r=validate_profile_artifact(p,self.manifests[k],i)
            self.assertTrue(r.valid,r.violations)
            self.assertEqual(r.serialize(),(OUT/k/'artifact_render_validation.json').read_text(encoding='utf-8'))

    def mutate_artifact(self,mode):
        key='standard-lesson';source=OUT/key/('Standard_Deviation_'+key+'.pptx')
        m=self.manifests[key];n=next(n for n,s in enumerate(m.slides,1) if s.slide_type=='guided_practice')
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'tampered.pptx'
            with zipfile.ZipFile(source) as original,zipfile.ZipFile(target,'w') as changed:
                for name in original.namelist():
                    data=original.read(name)
                    if name==f'ppt/slides/slide{n}.xml':
                        root=ET.fromstring(data);texts=root.findall('.//a:t',NS)
                        if mode=='answer':next(t for t in texts if 'Calculate' in (t.text or ' population')).text+=' Answer: 2.'
                        elif mode=='data':next(t for t in texts if 'Σx =' in (t.text or '')).text='Σx = 999'
                        else:
                            tree=root.find('p:cSld/p:spTree',NS);tree.remove(list(tree)[-1])
                        data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
                    changed.writestr(name,data)
            return validate_profile_artifact(target,m,self.inputs[key])

    def test_24_actual_answer_leak(self):self.assertFalse(self.mutate_artifact('answer').checks['question_solution_separation'])
    def test_25_actual_number_tamper(self):self.assertFalse(self.mutate_artifact('data').checks['source_text_preservation'])
    def test_26_actual_object_removed(self):self.assertFalse(self.mutate_artifact('remove').valid)

    def test_27_preserved_foundation(self):
        before=json.loads((OUT/'before.json').read_text(encoding='utf-8'));self.assertEqual(state(),before['database'])
        from academic_os.ai_qualification.reference_baseline import verify_reference
        current=verify_reference('.')
        self.assertTrue(current['valid'],current['errors'])
        # Keep the P5D artifact assertion independent of the active source revision.
        for path,digest in before['files'].items():
            if Path(path).parts[0]=='output':
                self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(),digest,path)

    def test_28_same_closure(self):
        a,b=self.manifests.values();self.assertEqual(a.slides[-1].learning_requirement_refs,b.slides[-1].learning_requirement_refs)

    def test_29_no_new_content(self):
        for k,i in self.inputs.items():
            known={o.ref for o in (*i.authored.content_blocks,*i.authored.instructional_formulas,*i.authored.worked_examples,*i.authored.practice_items,*i.authored.learning_checks,*i.authored.solutions,*i.package.new_content,*i.package.new_solutions)}
            self.assertTrue(set(self.manifests[k].content_coverage)<=known)

    def test_30_profile_context(self):
        for k,m in self.manifests.items():
            texts=[e['text'] for e in self.plans[k]['slides'][0]['elements']]
            self.assertIn(f'{m.profile_title} · {m.target_duration_minutes} min target',texts)


if __name__=='__main__':unittest.main()
