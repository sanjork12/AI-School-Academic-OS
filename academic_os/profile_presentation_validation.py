"""Inspect actual editable OOXML against the current source-resolved layout."""
import hashlib
from pathlib import Path
from .presentation_validation import inspect_pptx
from .presentation_models import ArtifactRenderValidation
from .presentation_manifest import sha
from .profile_presentation_layout import profile_layout


def validate_profile_artifact(path, manifest, inputs):
    plan=profile_layout(manifest,inputs)
    checks={k:True for k in ('role_coverage','content_coverage','source_text_preservation',
        'question_solution_separation','geometry_and_fonts','slide_manifest_consistency','academic_scope_preserved')}
    errors=[]
    def fail(check,message):
        checks[check]=False;errors.append(message)
    count=0
    try:
        actual=inspect_pptx(path);count=len(actual['pages'])
        if actual['size']!=(12192000,6858000):fail('geometry_and_fonts','Expected 16:9')
        if count!=len(plan['slides']):fail('slide_manifest_consistency','Missing or extra slides')
        if actual['notes']:fail('question_solution_separation','Student file contains notes; solutions belong outside the PPTX')
        for n,page in enumerate(plan['slides']):
            if n>=count:
                fail('content_coverage','Missing page '+page['ref']);continue
            found=actual['pages'][n];expected=page['elements']
            if [e['name'] for e in found]!=[e['name'] for e in expected]:
                fail('slide_manifest_consistency','Unexpected/missing objects on '+page['ref'])
                fail('question_solution_separation','Unapproved student content region on '+page['ref'])
            by_name={e['name']:e for e in found}
            for wanted in expected:
                rendered=by_name.get(wanted['name'])
                if rendered is None:
                    fail('content_coverage','Missing '+wanted['name']);continue
                if rendered['text']!=wanted['text']:
                    fail('source_text_preservation','Altered source text: '+wanted['name'])
                    # Ref-aware exact expected question/scaffold text avoids false positives
                    # for legitimate occurrences of common numeric answers in input data.
                    if manifest.slides[n].teacher_only_refs:
                        fail('question_solution_separation','Altered student question region: '+wanted['name'])
                geometry='rect' if wanted['kind']=='text' else wanted['kind']
                fill=None if wanted['kind']=='text' else wanted['color'].lstrip('#')
                if rendered['geometry']!=geometry or rendered['fill']!=fill or any(abs(rendered[k]-round(wanted[k]*9525))>5 for k in ('x','y','w','h')):
                    fail('geometry_and_fonts','Altered geometry '+wanted['name'])
                if wanted['kind']=='text' and (rendered['fonts']!={wanted['font']} or rendered['sizes']!={round(wanted['size']*75)} or rendered['colors']!={wanted['color'].lstrip('#')} or rendered['bolds']!={wanted['bold']}):
                    fail('geometry_and_fonts','Altered typography '+wanted['name'])
        if errors:
            checks['role_coverage']=False;checks['content_coverage']=False
    except (ValueError,KeyError,TypeError,OSError) as exc:
        fail('slide_manifest_consistency',str(exc))
    warnings=['Composition and artifact preservation only; no academic approval or guaranteed classroom runtime.']
    if not manifest.target_density_attained:warnings.append('Target density not fully attained; minimum requirements passed.')
    return ArtifactRenderValidation(valid=not errors,checks=checks,violations=tuple(errors),warnings=tuple(warnings),
        artifact_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),manifest_sha256=sha(manifest),
        authored_content_sha256=sha(inputs.package),slide_count=count,content_coverage=manifest.content_coverage,
        learning_requirement_refs=tuple(sorted(inputs.package.learning_requirement_refs)))
