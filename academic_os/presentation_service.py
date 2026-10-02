"""Live gate -> referenced manifest -> editable PPTX -> independent preservation gate."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from .authored_service import AuthoredTeachingService
from .content_validation_service import AuthoredContentValidationService
from .learning_service import LearningSpecificationService
from .presentation_manifest import build_manifest,sha
from .presentation_layout import layout_plan
from .presentation_validation import validate_artifact

ROOT=Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PresentationInputs:
    authored:object
    validation:object
    learning:object
    manifest:object
    provenance:dict


def runtime():
    node=Path(os.environ.get('P4C_NODE') or shutil.which('node') or '')
    modules=Path(os.environ.get('RUNTIME_NODE_MODULES') or node.parent.parent/'node_modules')
    python=Path(os.environ.get('P4C_PYTHON') or node.parent.parent.parent/'python/python.exe')
    skills=list((Path.home()/'.codex/plugins/cache/openai-primary-runtime/presentations').glob('*/skills/presentations'))
    skill=Path(os.environ['P4C_SKILL_DIR']) if os.environ.get('P4C_SKILL_DIR') else (sorted(skills)[-1] if skills else Path('__missing_skill__'))
    if not node.is_file() or not python.is_file() or not (modules/'@oai/artifact-tool').is_dir() or not (skill/'container_tools/artifact_tool_utils.mjs').is_file():
        raise ValueError('P4C requires the installed Artifact Tool runtime and presentation finalizer; configure P4C_NODE, RUNTIME_NODE_MODULES, P4C_PYTHON and P4C_SKILL_DIR. No substitutes are installed automatically.')
    return node.resolve(),modules.resolve(),python.resolve(),skill.resolve()


def teacher_solutions(inputs):
    return dict(schema_version='presentation-teacher-solutions/1',authored_content_sha256=sha(inputs.authored),
        solutions={s.ref:s.model_dump(mode='json') for s in inputs.authored.solutions if inputs.manifest.solution_visibility[s.ref]=='teacher_sidecar_only'})


class PresentationService:
    def __init__(self,database):
        self._authored=AuthoredTeachingService(database);self._validation=AuthoredContentValidationService(database);self._learning=LearningSpecificationService(database)

    def read_topic(self,topic_key,snapshot_ids,profile='standard-deviation-classroom/1'):
        authored=self._authored.read_topic(topic_key,snapshot_ids)
        validation=self._validation.read_topic(topic_key,snapshot_ids)
        learning=self._learning.read_topic(topic_key,snapshot_ids)
        if validation.provenance['upstream']!=authored.provenance or authored.provenance['upstream']['upstream']['upstream']!=learning.provenance:
            raise ValueError('Upstream changed between presentation reads; retry')
        manifest=build_manifest(authored.view,validation.view,learning.view,profile)
        return PresentationInputs(authored.view,validation.view,learning.view,manifest,dict(upstream=validation.provenance,current_upstream_validated=True))

    def render(self,topic_key,snapshot_ids,output_dir,design='classic'):
        if design not in ('classic','classroom-v2'):raise ValueError('Unsupported presentation design')
        inputs=self.read_topic(topic_key,snapshot_ids) if design=='classic' else self.read_topic(topic_key,snapshot_ids,'standard-deviation-classroom/2')
        out=Path(output_dir).resolve();out.mkdir(parents=True,exist_ok=True)
        destination=out/('student/Standard_Deviation.pptx' if design=='classic' else 'Standard_Deviation_v2.pptx')
        manifest_path=out/'presentation_manifest.json';sidecar=out/'teacher_solutions.json'
        serial=inputs.manifest.serialize();teacher=json.dumps(teacher_solutions(inputs),ensure_ascii=False,sort_keys=True,indent=2)+'\n'
        if destination.exists():
            if not manifest_path.exists() or manifest_path.read_bytes()!=serial.encode() or not sidecar.exists() or sidecar.read_bytes()!=teacher.encode():raise ValueError('Existing output belongs to different or incomplete inputs; choose a new output directory')
            report=validate_artifact(destination,inputs.manifest,inputs.authored,inputs.validation,inputs.learning)
            if not report.valid:raise ValueError('Existing artifact failed validation: '+ '; '.join(report.violations))
            receipt=out/'artifact_render_validation.json'
            if not receipt.is_file() or receipt.read_bytes()!=report.serialize().encode():raise ValueError('Existing artifact receipt is missing or differs from current validation')
            return dict(pptx=str(destination),manifest=str(manifest_path),validation=str(out/'artifact_render_validation.json'),reused=True,valid=True)
        # All final public files are protected from replacement, including failed partial runs.
        targets=[manifest_path,sidecar,out/'artifact_render_validation.json',out/'provenance.json']
        if any(p.exists() for p in targets):raise ValueError('Output artifact paths already exist; choose a new directory')
        node,modules,python,skill=runtime()
        build_parent=out/'.build';build_parent.mkdir(exist_ok=True)
        build=Path(tempfile.mkdtemp(prefix='render-',dir=build_parent))
        plan=layout_plan(inputs.manifest,inputs.authored,inputs.validation,inputs.learning)
        plan_path=build/'render_plan.json';plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        final=build/'final/Standard_Deviation.pptx'
        env=os.environ.copy();env['RUNTIME_NODE_MODULES']=str(modules)
        run=subprocess.run([str(node),str(Path(__file__).with_name('presentation_renderer.mjs')),str(plan_path),str(build),str(final),str(skill),str(python)],cwd=ROOT,env=env,encoding='utf-8',errors='replace',capture_output=True)
        (build/'renderer.log').write_text(run.stdout+'\n'+run.stderr,encoding='utf-8')
        if run.returncode:raise ValueError('Presentation backend failed; inspect '+str(build/'renderer.log'))
        report=validate_artifact(final,inputs.manifest,inputs.authored,inputs.validation,inputs.learning)
        (build/'artifact_render_validation.json').write_text(report.serialize(),encoding='utf-8')
        if not report.valid:raise ValueError('Rendered preservation checks failed; inspect '+str(build/'artifact_render_validation.json'))
        destination.parent.mkdir(exist_ok=True)
        # Exclusive publication. Public PPTX is written last after all gates pass.
        for path,payload in [(manifest_path,serial),(sidecar,teacher),(out/'artifact_render_validation.json',report.serialize()),
            (out/'provenance.json',json.dumps(dict(**inputs.provenance,build_directory=str(build)),ensure_ascii=False,sort_keys=True,indent=2)+'\n')]:
            with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(payload)
        with destination.open('xb') as stream:stream.write(final.read_bytes())
        return dict(pptx=str(destination),manifest=str(manifest_path),validation=str(out/'artifact_render_validation.json'),preview_directory=str(build/'preview'),reused=False,valid=True)
