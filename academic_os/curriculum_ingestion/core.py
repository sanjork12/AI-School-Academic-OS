"""Explicit extraction and parsing boundaries; no files or clients at import time."""
import copy
import hashlib
import os
import re
from pathlib import Path
from curriculum_schema import CurriculumTopic
from .models import Extraction,PageText,Warning
from .prompt import instructions

PROFILE='edexcel-4ma1-topic2-2017/1'
KNOWN_SHA='d58830e570d58aeccd7146f5465b3c117378c42d08d663f18478f2793c7e737b'
RANGES={'foundation':(21,22),'higher':(37,38)}
MAX_UPLOAD=10*1024*1024
MAX_PAGES=200
MAX_EXTRACTED_CHARS=100000
ROOT=Path(__file__).resolve().parents[2]

class IngestionError(Exception):
    def __init__(self,code,message):self.code,self.message=code,message;super().__init__(message)

def digest(data):return hashlib.sha256(data).hexdigest()
def inspect_pdf(data):
    if not data or not data.startswith(b'%PDF-'):raise IngestionError('INVALID_PDF','A nonempty PDF file is required.')
    try:
        import pymupdf
        with pymupdf.open(stream=data,filetype='pdf') as doc:
            if doc.needs_pass or doc.is_repaired or not 1<=len(doc)<=MAX_PAGES:raise ValueError('Unsupported PDF container')
            return len(doc)
    except Exception:raise IngestionError('INVALID_PDF','PDF is invalid, encrypted, repaired, or exceeds the page limit.') from None

def extract_pages(pdf_path,start_page,end_page):
    data=Path(pdf_path).read_bytes();count=inspect_pdf(data)
    if not 1<=start_page<=end_page<=count or end_page-start_page>=10:
        raise IngestionError('EXTRACTION_FAILED','Choose a valid range of at most 10 PDF pages.')
    import pymupdf
    pages=[];warnings=[];text=[]
    try:
        with pymupdf.open(stream=data,filetype='pdf') as doc:
            for number in range(start_page,end_page+1):
                value=doc[number-1].get_text('text');pw=[]
                if not value.strip():pw.append(Warning(code='TEXT_NOT_AVAILABLE',message='No text was extracted; OCR is not supported.',page=number))
                if any(c=='\ufffd' or '\ue000'<=c<='\uf8ff' for c in value):
                    pw.append(Warning(code='SYMBOL_EXTRACTION_WARNING',message='Extracted symbols require comparison with the PDF; no repair was attempted.',page=number))
                pages.append(PageText(page_number=number,text=value,warnings=pw));warnings.extend(pw)
                text.append(f"\n{'='*60}\nPDF PAGE {number}\n{'='*60}\n{value}")
        joined='\n'.join(text)
        if len(joined)>MAX_EXTRACTED_CHARS:raise ValueError('Too much text')
        return Extraction(source_sha256=digest(data),start_page=start_page,end_page=end_page,extractor='PyMuPDF/'+pymupdf.VersionBind,pages=pages,text=joined,warnings=warnings)
    except IngestionError:raise
    except Exception:raise IngestionError('EXTRACTION_FAILED','Text extraction failed or exceeded the text limit.') from None

def assign_source_ids(data):
    data=copy.deepcopy(data);tier={'Foundation':'F','Higher':'H'}[data['tier_source']]
    for sub in data['subtopics']:
        for obj in sub['objectives']:obj['source_id']=f"EDX-{data['specification_code']}-{tier}-{sub['code']}-{obj['code']}"
    return data

def model_configuration():
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env',override=False)
    model=os.environ.get('ACADEMIC_OS_CURRICULUM_MODEL','').strip()
    if not re.fullmatch(r'[A-Za-z0-9._:/-]{1,160}',model) or model.startswith('sk-') or not os.environ.get('OPENAI_API_KEY'):
        raise IngestionError('MODEL_CONFIGURATION_MISSING','Set the approved curriculum model and backend credentials before explicit AI parsing.')
    return {'model':model,'prompt_version':'4ma1-topic2-historical/1','max_retries':0,'timeout_seconds':60}

def live_parse(text,tier,configuration):
    # One explicit call, no fallback model and no raw exception/response persistence.
    try:
        from openai import OpenAI
        with OpenAI(max_retries=0,timeout=60) as client:
            response=client.responses.parse(model=configuration['model'],store=False,
                instructions=instructions(tier.title()),input=text,text_format=CurriculumTopic)
            if response.status!='completed' or response.output_parsed is None:raise ValueError('Incomplete parse')
            return response.output_parsed.model_dump()
    except Exception:raise IngestionError('PARSER_FAILED','The parser did not complete. Provider details were withheld; no automatic retry.') from None

def parse_curriculum(text,tier,profile,parser):
    if profile!=PROFILE or tier not in RANGES:raise IngestionError('UNSUPPORTED_CURRICULUM_PROFILE','Only the known 4MA1 Topic 2 profile is supported.')
    if not text.strip():raise IngestionError('EXTRACTION_FAILED','No extracted text is available.')
    try:
        parsed=CurriculumTopic.model_validate(parser(text,tier)).model_dump()
        return assign_source_ids(parsed)
    except IngestionError:raise
    except Exception:raise IngestionError('PARSER_FAILED','Parser output does not match the curriculum schema.') from None
