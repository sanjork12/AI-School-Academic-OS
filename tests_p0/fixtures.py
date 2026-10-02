"""TEST ONLY generated PDFs and TEST-ONLY reviewer. Never approve real materials."""
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
from academic_os.sources import register_candidate,extract_candidate
from academic_os.models import normalise

ROOT='part_mapping:MAP-TEST'

def pdf(path,text):
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(('BT /F1 12 Tf 50 700 Td ('+text+') Tj ET').encode('ascii'))
    page[NameObject('/Contents')]=writer._add_object(stream)
    with Path(path).open('wb') as f:writer.write(f)

def candidates(directory):
    rows=[]
    for sid,kind in [('PAPER','official_past_paper'),('SCHEME','official_mark_scheme'),('SPEC','official_syllabus')]:
        path=Path(directory)/(sid+'.pdf');pdf(path,'TEST ONLY - not official - mean and SD fixture '+sid)
        raw=register_candidate(sid,path,'TEST ONLY '+sid,kind,'TEST ONLY curriculum','TEST v1','TEST ONLY generated temporary PDF; no Pearson identity claim')
        rows.append(raw);_,version,source=normalise(raw)
        rows.append(extract_candidate(source,version,'LOC-'+sid,1,'TEST page','TEST ONLY controlled summary',
                                      assessment_part_id='PART' if sid!='SPEC' else None,assessment_question_id='Q' if sid!='SPEC' else None))
    def prov(loc='SPEC'):return dict(origin='real',creation_method='rule',source_references=['locator:LOC-'+loc])
    def add(k,p,refs=()):rows.append(dict(kind=k,payload=p,judgment_refs=list(refs)))
    add('context',dict(context_id='CTX',exam_board='TEST ONLY',qualification='TEST ONLY',subject='Mathematics',provenance=prov()))
    add('competency',dict(canonical_id='CAN-MEAN',subject_domain='Statistics',skill_name='TEST calculate mean',description='TEST initial definition',provenance=prov()))
    add('question',dict(question_id='Q',paper_source_id='PAPER',label='TEST Q',source_locator_id='LOC-PAPER',curriculum_context_id='CTX',provenance=prov('PAPER')))
    add('question_part',dict(part_id='PART',question_id='Q',label='TEST part',node_kind='assessable',source_locator_id='LOC-PAPER',provenance=prov('PAPER')),['condition:COND'])
    add('condition',dict(condition_id='COND',question_id='Q',kind='input_form',description='TEST supplied summary',availability='given_in_question',provenance=prov('PAPER')))
    add('scope',dict(scope_id='SCOPE',context_id='CTX',description='TEST scope',locator_ids=['LOC-SPEC']))
    for sid in ['PAPER','SCHEME']:
        add('evidence',dict(evidence_id='EV-'+sid,source_locator_ids=['LOC-'+sid],target={'kind':'part_mapping','id':'MAP-TEST'},
            observation='TEST ONLY candidate interpretation',content_kind='interpretation',evidence_role='supports',observation_status='observed',provenance=prov(sid)))
    add('part_mapping',dict(mapping_id='MAP-TEST',part_id='PART',canonical_id='CAN-MEAN',role='assessed',assessment_extent='partial',
        rationale='TEST ONLY mapping',evidence_ids=['EV-PAPER','EV-SCHEME'],mapping_method='rule',provenance=prov('PAPER')),['scope:SCOPE'])
    return rows
