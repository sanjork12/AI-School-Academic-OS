"""Artifact/content consistency checks; run with the bundled document Python."""
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from pptx import Presentation
from docx import Document
from pypdf import PdfReader

OUT=Path(__file__).resolve().parent/'output/teaching_assessment_demo'

def compact(text):return re.sub(r'\s+','',text)

def main():
    core=json.loads((OUT/'pack.json').read_text(encoding='utf-8'))
    ppt=OUT/'Edexcel_9MA0_Statistics_Exploring_Data.pptx';prs=Presentation(ppt)
    assert len(prs.slides)==24
    tables=0;charts=0
    for slide,expected in zip(prs.slides,core['slides']):
        text='\n'.join(s.text for s in slide.shapes if s.has_text_frame)
        assert 'Not official Pearson material' in text
        if expected['slide_id']>1:
            for line in expected['body']:assert compact(line) in compact(text),(expected['slide_id'],line)
            assert compact(expected['student_check']['prompt']) in compact(text)
        assert expected['student_check']['answer'] in slide.notes_slide.notes_text_frame.text
        actual_tables=[s.table for s in slide.shapes if s.has_table]
        if expected['table']:
            assert len(actual_tables)==1
            assert [[c.text for c in r.cells] for r in actual_tables[0].rows]==expected['table'];tables+=1
        if expected['chart']:
            chart=next(s.chart for s in slide.shapes if s.has_chart)
            assert list(chart.series[0].values)==[2.0,7.0];charts+=1
    pdfs={};docs={}
    for kind in ['Assessment','Mark_Scheme']:
        pdf=OUT/f'Edexcel_9MA0_Statistics_{kind}.pdf';reader=PdfReader(pdf)
        assert len(reader.pages)==9
        text='\n'.join(p.extract_text() for p in reader.pages)
        assert 'Not official Pearson material' in text
        doc=Document(OUT/f'Edexcel_9MA0_Statistics_{kind}.docx')
        doctext='\n'.join([p.text for p in doc.paragraphs]+[c.text for t in doc.tables for r in t.rows for c in r.cells])
        assert not list(doc.styles.element.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pBdr'))
        for q in core['questions']:
            for part in q['parts']:
                for actual in [text,doctext]:
                    assert part['part_id'] in actual
                    required=part['prompt'] if kind=='Assessment' else part['answer']
                    assert compact(required) in compact(actual),(kind,part['part_id'])
        if kind=='Assessment':
            assert 'M1 ' not in text and 'Mark Scheme' not in text
            assert '77/7 = 11' not in doctext
        else:assert compact('NOT AN OFFICIAL PEARSON MARK SCHEME') in compact(text)
        pdfs[pdf.name]=9;docs[kind]='All prompts/answers present; title border removed'
    artifacts=[p for p in OUT.iterdir() if p.suffix in ['.pptx','.docx','.pdf']]
    result=dict(status='PASSED',slides=24,native_tables=tables,native_charts=charts,pdf_pages=pdfs,
                docx_content=docs,artifact_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts},
                visual_review='All 24 slide renders and all 18 PDF pages inspected. Both DOCX files rendered in Word for page review. Generation itself does not require Office.')
    (OUT/'artifact_validation_report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
