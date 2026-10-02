"""Allowlisted ingestion routes. No document path is accepted from a browser."""
from fastapi import APIRouter,Request
from academic_os.curriculum_ingestion.models import *
router=APIRouter()
def service(request):return request.app.state.ingestion

@router.post('/api/syllabi',response_model=CurriculumDocument,status_code=201)
async def upload(request:Request,filename:str):
    return service(request).upload(await request.body(),filename,request.headers.get('content-type',''))

@router.get('/api/syllabi/{document_id}',response_model=CurriculumDocument)
def document(document_id:str,request:Request):return service(request).document(document_id)

@router.post('/api/syllabi/{document_id}/extract',response_model=IngestionRun,status_code=202)
def extract(document_id:str,body:ExtractRequest,request:Request):return service(request).submit_extract(document_id,body)

@router.post('/api/syllabi/{document_id}/parse',response_model=IngestionRun,status_code=202)
def parse(document_id:str,body:ParseRequest,request:Request):return service(request).submit_parse(document_id,body)

@router.get('/api/syllabi/{document_id}/runs',response_model=list[IngestionRun])
def runs(document_id:str,request:Request):return service(request).runs(document_id)

@router.get('/api/curriculum-runs/{run_id}',response_model=IngestionRun)
def run(run_id:str,request:Request):return service(request).get(run_id)

@router.get('/api/curriculum-runs/{run_id}/extraction',response_model=Extraction)
def extraction(run_id:str,request:Request):return service(request).output(run_id,'extraction')

@router.get('/api/curriculum-runs/{run_id}/tree',response_model=CurriculumTier)
def tree(run_id:str,request:Request):return service(request).tree(run_id)

@router.get('/api/curriculum-runs/{run_id}/validation',response_model=Validation)
def validation(run_id:str,request:Request):return service(request).output(run_id,'validation')

@router.get('/api/curriculum-runs/{run_id}/capabilities',response_model=CurriculumCapabilityPackage)
def capabilities(run_id:str,request:Request,subtopic:str|None=None,objective:str|None=None):
    return service(request).capabilities(run_id,subtopic,objective)
