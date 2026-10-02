"""Independent OOXML preservation checks, not another academic validator."""
import hashlib
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from .presentation_layout import layout_plan
from .presentation_manifest import sha
from .presentation_models import ArtifactRenderValidation

NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def inspect_pptx(path):
    with zipfile.ZipFile(path) as z:
        presentation=ET.fromstring(z.read('ppt/presentation.xml'))
        size=presentation.find('p:sldSz',NS)
        rels=ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
        targets={r.attrib['Id']:posixpath.normpath(posixpath.join('ppt',r.attrib['Target'])).lstrip('/') for r in rels}
        pages=[]
        for identifier in presentation.findall('p:sldIdLst/p:sldId',NS):
            target=targets[identifier.attrib['{'+NS['r']+'}id']]
            root=ET.fromstring(z.read(target));elements=[]
            if root.attrib.get('show')=='0':raise ValueError('Hidden slide is not permitted')
            tree=root.find('p:cSld/p:spTree',NS)
            for shape in tree:
                tag=shape.tag.rsplit('}',1)[-1]
                if tag in ('nvGrpSpPr','grpSpPr'):continue
                if tag!='sp':raise ValueError('Unsupported or unexpected non-shape slide content: '+tag)
                prop=shape.find('p:nvSpPr/p:cNvPr',NS);xfrm=shape.find('p:spPr/a:xfrm',NS)
                off=xfrm.find('a:off',NS);ext=xfrm.find('a:ext',NS)
                paragraphs=[''.join(t.text or '' for t in p.findall('.//a:t',NS)) for p in shape.findall('p:txBody/a:p',NS)]
                runs=shape.findall('.//a:rPr',NS)
                fonts={r.find('a:latin',NS).attrib.get('typeface') for r in runs if r.find('a:latin',NS) is not None}
                sizes={int(r.attrib['sz']) for r in runs if 'sz' in r.attrib}
                if prop.attrib.get('hidden') in ('1','true') or xfrm.attrib.get('rot','0')!='0' or any(alpha.attrib.get('val')!='100000' for alpha in shape.findall('.//a:alpha',NS)):raise ValueError('Hidden, rotated or transparent authored content is unsupported')
                colors={r.find('a:solidFill/a:srgbClr',NS).attrib['val'] for r in runs if r.find('a:solidFill/a:srgbClr',NS) is not None}
                bolds={r.attrib.get('b','0') in ('1','true') for r in runs}
                geometry=shape.find('p:spPr/a:prstGeom',NS)
                fill=shape.find('p:spPr/a:solidFill/a:srgbClr',NS)
                elements.append(dict(name=prop.attrib.get('name'),text='\n'.join(paragraphs),x=int(off.attrib['x']),y=int(off.attrib['y']),w=int(ext.attrib['cx']),h=int(ext.attrib['cy']),fonts=fonts,sizes=sizes,
                    colors=colors,bolds=bolds,geometry=geometry.attrib.get('prst') if geometry is not None else None,fill=fill.attrib['val'] if fill is not None else None))
            pages.append(elements)
        # Answers are kept in a separate sidecar, so no speaker-note text or hidden slides are expected.
        notes=[]
        for name in z.namelist():
            if name.startswith('ppt/notesSlides/notesSlide') and name.endswith('.xml'):
                root=ET.fromstring(z.read(name));notes.extend(t.text or '' for t in root.findall('.//a:t',NS))
            if name.startswith(('ppt/slideMasters/slideMaster','ppt/slideLayouts/slideLayout')) and name.endswith('.xml'):
                root=ET.fromstring(z.read(name))
                if any(t.text for t in root.findall('.//a:t',NS)) or root.findall('.//p:pic',NS):raise ValueError('Unexpected visible master/layout content')
            if name.endswith('.rels') and any(r.attrib.get('TargetMode')=='External' for r in ET.fromstring(z.read(name))):raise ValueError('External artifact relationship is unsupported')
        return dict(size=(int(size.attrib['cx']),int(size.attrib['cy'])),pages=pages,notes=notes)


def validate_artifact(path,manifest,authored,validation,learning):
    plan=layout_plan(manifest,authored,validation,learning);errors=[]
    checks={k:True for k in ('required_content_coverage','learning_requirement_representation','question_solution_separation','mathematical_content_preservation','slide_manifest_consistency','no_unsupported_content','geometry_and_fonts')}
    def fail(check,message):checks[check]=False;errors.append(message)
    coverage={};represented=set();count=0
    try:
        actual=inspect_pptx(path);count=len(actual['pages'])
        if actual['size']!=(12192000,6858000):fail('geometry_and_fonts','Expected 16:9 slide dimensions')
        if count!=len(manifest.slides):fail('slide_manifest_consistency','Slide count differs from manifest')
        if actual['notes']:fail('question_solution_separation','Unexpected speaker note content; teacher solutions belong in the sidecar')
        for i,(expected,slide) in enumerate(zip(plan['slides'],manifest.slides)):
            if i>=count:fail('required_content_coverage','Missing slide '+slide.ref);continue
            found=actual['pages'][i]
            if [e['name'] for e in found]!=[e['name'] for e in expected['elements']]:
                fail('slide_manifest_consistency','Slide object order/identity differs: '+slide.ref)
                fail('no_unsupported_content','Unexpected or missing rendered objects: '+slide.ref)
            by_name={e['name']:e for e in found};sources=set();faithful=True
            for wanted in expected['elements']:
                rendered=by_name.get(wanted['name'])
                if rendered is None:fail('required_content_coverage','Missing element '+wanted['name']);faithful=False;continue
                if rendered['text']!=wanted['text']:
                    fail('mathematical_content_preservation','Changed text/symbols: '+wanted['name'])
                    fail('no_unsupported_content','Rendered prose is not the resolved source content: '+wanted['name']);faithful=False
                if any(abs(rendered[k]-round(wanted[k]*9525))>5 for k in ('x','y','w','h')):
                    fail('geometry_and_fonts','Changed geometry: '+wanted['name']);faithful=False
                if wanted['kind']=='text' and (rendered['fonts']!={wanted['font']} or rendered['sizes']!={round(wanted['size']*75)}):
                    fail('geometry_and_fonts','Changed typography: '+wanted['name']);faithful=False
                expected_geometry='rect' if wanted['kind']=='text' else wanted['kind']
                expected_fill=None if wanted['kind']=='text' else wanted['color'].lstrip('#')
                if rendered['geometry']!=expected_geometry or rendered['fill']!=expected_fill:
                    fail('geometry_and_fonts','Changed shape or fill: '+wanted['name']);faithful=False
                if wanted['kind']=='text' and (rendered['colors']!={wanted['color'].lstrip('#')} or rendered['bolds']!={wanted['bold']}):
                    fail('geometry_and_fonts','Changed text styling: '+wanted['name']);faithful=False
                if wanted['source_ref']:sources.add(wanted['source_ref'])
            if slide.teacher_only_refs and (not faithful or len(found)!=len(expected['elements'])):
                fail('question_solution_separation','Student question region differs from the solution-free render plan: '+slide.ref)
            if set(slide.teacher_only_refs)&sources:fail('question_solution_separation','Teacher solution mapped to student content')
            for b in authored.content_blocks:
                if b.item_ref in sources:sources.add(b.ref)
            if faithful:
                represented.update(slide.learning_requirement_refs)
                for ref in sources:coverage.setdefault(ref,[]).append(slide.ref)
            if not set(slide.content_refs)<=sources:fail('required_content_coverage','Student content not represented: '+slide.ref)
        if represented!=set(manifest.slides[0].learning_requirement_refs):fail('learning_requirement_representation','Not all included learning requirements were represented')
    except (ValueError,KeyError,AttributeError,ET.ParseError,zipfile.BadZipFile,OSError) as exc:
        for check in checks:checks[check]=False
        errors.append('Invalid or unsupported PPTX package: '+str(exc))
    path=Path(path)
    return ArtifactRenderValidation(valid=all(checks.values()),checks=checks,violations=tuple(sorted(set(errors))),
        warnings=('Structural preservation does not prove visual beauty, pedagogical effectiveness, student comprehension, accessibility perfection or teacher preference.',
            'Mathematical truth and academic boundaries are delegated to the current P4B gate; no new academic validation is performed.',
            'Editable formula text uses explicit parentheses, Unicode roots/superscripts and slash fractions; it is not an Office equation object.'),
        artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else '',manifest_sha256=sha(manifest),
        authored_content_sha256=sha(authored),slide_count=count,content_coverage={k:tuple(v) for k,v in sorted(coverage.items())},learning_requirement_refs=tuple(sorted(represented)))
