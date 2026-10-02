"""Live P5C gate and profile adapter; protected inputs are read only."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from .profiled_content_service import ProfiledContentService
from .profiled_validation_service import ProfiledContentValidationService
from .lesson_profile_service import LessonProfileService
from .authored_service import AuthoredTeachingService
from .content_validation_service import AuthoredContentValidationService
from .learning_service import LearningSpecificationService
from .pedagogical_core import build_pedagogical_specification
from .presentation_service import runtime, ROOT
from .profile_presentation import ProfileInputs, build_profile_manifest, same_scope, profile_teacher_solutions
from .profile_presentation_layout import profile_layout
from .profile_presentation_validation import validate_profile_artifact


class ProfilePresentationService:
    def __init__(self,database):
        self.database=database

    def read_profiles(self,topic_key,snapshot_ids):
        p5c=ProfiledContentValidationService(self.database).read_profiles(topic_key,snapshot_ids)
        content=ProfiledContentService(self.database).read_profiles(topic_key,snapshot_ids)
        profiles=LessonProfileService(self.database).read_profiles(topic_key,snapshot_ids)
        authored=AuthoredTeachingService(self.database).read_topic(topic_key,snapshot_ids)
        p4b=AuthoredContentValidationService(self.database).read_topic(topic_key,snapshot_ids)
        learning=LearningSpecificationService(self.database).read_topic(topic_key,snapshot_ids)
        if (p5c.provenance['upstream']!=content.provenance or content.provenance['upstream']!=profiles.provenance
            or content.provenance['source_p4b']!=p4b.provenance or p4b.provenance['upstream']!=authored.provenance
            or profiles.provenance['upstream']!=learning.provenance):
            raise ValueError('Upstream changed between render reads; retry')
        inputs={key:ProfileInputs(package,p5c.reports[key],profiles.profiles[key],profiles.views[key],
            authored.view,p4b.view,learning.view,build_pedagogical_specification(learning.view)) for key,package in content.packages.items()}
        if set(inputs)!={'focused-review','standard-lesson'}:raise ValueError('Both supported profiles required')
        same_scope(inputs)
        # No output paths are opened until both current gates succeed.
        for i in inputs.values():build_profile_manifest(i)
        return inputs,p5c.provenance

    def render(self,topic_key,snapshot_ids,output_dir):
        inputs,provenance=self.read_profiles(topic_key,snapshot_ids)
        return {key:self._render_one(i,provenance,Path(output_dir)/key) for key,i in inputs.items()}

    def _render_one(self,i,provenance,out):
        manifest=build_profile_manifest(i);plan=profile_layout(manifest,i)
        teacher=profile_teacher_solutions(i,manifest)
        out=out.resolve();destination=out/('Standard_Deviation_'+manifest.profile_key+'.pptx')
        payloads={'presentation_manifest.json':manifest.serialize(),
            'teacher_solutions.json':json.dumps(teacher,ensure_ascii=False,sort_keys=True,indent=2)+'\n'}
        if destination.exists():
            for name,payload in payloads.items():
                if not (out/name).is_file() or (out/name).read_bytes()!=payload.encode():raise ValueError('Existing profile artifact has different inputs')
            report=validate_profile_artifact(destination,manifest,i)
            if not report.valid or (out/'artifact_render_validation.json').read_bytes()!=report.serialize().encode():raise ValueError('Existing profile artifact failed current validation')
            return dict(pptx=str(destination),slides=len(manifest.slides),valid=True,reused=True)
        if out.exists() and any((out/name).exists() for name in (*payloads,'artifact_render_validation.json','provenance.json')):
            raise ValueError('Existing output files; select a new directory')
        node,modules,python,skill=runtime()
        build_parent=out/'.build';build_parent.mkdir(parents=True,exist_ok=True)
        build=Path(tempfile.mkdtemp(prefix='render-',dir=build_parent))
        plan_path=build/'render_plan.json';plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        final=build/'final'/destination.name
        env=os.environ.copy();env['RUNTIME_NODE_MODULES']=str(modules)
        run=subprocess.run([str(node),str(Path(__file__).with_name('profile_presentation_renderer.mjs')),str(plan_path),str(build),str(final),str(skill),str(python)],
            cwd=ROOT,env=env,encoding='utf-8',errors='replace',capture_output=True)
        (build/'renderer.log').write_text(run.stdout+'\n'+run.stderr,encoding='utf-8')
        if run.returncode:raise ValueError('Profile backend failed; inspect '+str(build/'renderer.log'))
        report=validate_profile_artifact(final,manifest,i)
        (build/'artifact_render_validation.json').write_text(report.serialize(),encoding='utf-8')
        if not report.valid:raise ValueError('Profile artifact failed preservation checks: '+str(build))
        payloads['artifact_render_validation.json']=report.serialize()
        payloads['provenance.json']=json.dumps(dict(upstream=provenance,build_directory=str(build)),ensure_ascii=False,sort_keys=True,indent=2)+'\n'
        for name,payload in payloads.items():
            with (out/name).open('xb') as stream:stream.write(payload.encode())
        with destination.open('xb') as stream:stream.write(final.read_bytes())
        return dict(pptx=str(destination),slides=len(manifest.slides),valid=True,reused=False,preview_directory=str(build/'preview'))
