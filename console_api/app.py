"""Small localhost API; explicit bounded ingestion, no generic execution or trusted writes."""
import copy
import json
import secrets
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from .models import *
from . import adapter as a
from .syllabi import router as syllabi_router
from academic_os.curriculum_ingestion.service import IngestionService
from academic_os.curriculum_ingestion.core import IngestionError, MAX_UPLOAD

ORIGINS = ['http://127.0.0.1:3000','http://localhost:3000']
STAGES=[('source','Source / snapshot available'),('assessment','Assessment evidence available'),('learning','Learning specification available'),('pedagogy','Pedagogical specification available'),('profile','Profile available'),('authored','Deterministic content assembled'),('p4b','Authored content validation'),('content','Profiled content assembled'),('p5c','Profiled content validation')]
def now(): return datetime.now(timezone.utc).isoformat()

class Session(DTO):
    token: str

class Manager:
    def __init__(self):
        self.registry=a.Registry();self.lock=threading.RLock();self.pool=ThreadPoolExecutor(max_workers=1)
        self.capacity=threading.BoundedSemaphore(2);self.runs={};self.payloads={};self.token=secrets.token_urlsafe(32)
        self.tree=a.curriculum(self.registry);self.history=a.historical(self.registry)
        base=a.ROOT/'output/p5d_profiled_presentation/standard-lesson'
        frozen=a.read(a.ROOT/'output/reference_freeze_v1_7/reference_manifest.json')['files']
        for name in ('Standard_Deviation_standard-lesson.pptx','presentation_manifest.json','teacher_solutions.json','artifact_render_validation.json'):
            p=base/name
            if p.is_file() and frozen.get(p.relative_to(a.ROOT).as_posix())==a.sha(p):
                self.registry.add(p,'P5 deterministic / validated presentation · '+name,'presentation')
    def persist(self,run):
        directory=a.ROOT/'output/p6ui2/runs'/run.id;directory.mkdir(parents=True,exist_ok=True)
        target=directory/'run.json';temp=directory/'run.tmp'
        temp.write_text(run.model_dump_json(indent=2),encoding='utf-8');temp.replace(target)
    def submit(self,selection):
        if not self.capacity.acquire(blocking=False): raise HTTPException(429,'Local task queue is full')
        run=Run(id=uuid.uuid4().hex,selection=selection,database=str(a.DATABASE),snapshots=a.SNAPSHOTS,started_at=now(),status='queued',stages=[Evidence(id=k,label=l,status='NOT_EVALUATED') for k,l in STAGES])
        with self.lock:self.runs[run.id]=run;self.persist(run);response=run.model_copy(deep=True)
        self.pool.submit(self.execute,run.id)
        return response
    def execute(self,identity):
        with self.lock:run=self.runs[identity];run.status='running';self.persist(run)
        before=a.sha(a.DATABASE)
        try:
            def stage(evidence):
                with self.lock:
                    run.stages=[evidence if e.id==evidence.id else e for e in run.stages];self.persist(run)
            result=a.assembly(stage);lesson,questions,solutions=a.lesson_views(result,self.history)
            trust=a.dump(result['source'].view)['trust_summary']
            extra=[Evidence(id='curriculum_verified',label='Curriculum verified',status='PASS' if trust['curriculum_verified'] else 'FAIL',details=trust),
                Evidence(id='curriculum_association_confirmed',label='Curriculum association confirmed',status='PASS' if trust['curriculum_association_confirmed'] else 'NOT_EVALUATED',details={'value':trust['curriculum_association_confirmed']}),
                Evidence(id='approval',label='Academic approval of assembled content',status='NOT_EVALUATED',details={'approval_granted_by_console':False}),
                Evidence(id='renderer',label='P5 renderer eligibility · no render requested',status='PASS' if result['p5c'].reports[a.PROFILE].renderer_readiness.ready_for_rendering else 'BLOCKED',details=a.dump(result['p5c'].reports[a.PROFILE].renderer_readiness)),
                Evidence(id='p6',label='P6 qualification in this run',status='NOT_APPLICABLE',details={'model_calls':0,'candidate_overlay':False}),
                Evidence(id='published',label='Publication',status='NOT_APPLICABLE',details={'publication_requested':False})]
            payload={'lesson':a.dump(lesson),'questions':[a.dump(q) for q in questions],'solutions':[a.dump(s) for s in solutions]}
            with self.lock:
                run.stages.extend(extra)
                for key,value in payload.items():
                    p=a.ROOT/'output/p6ui2/runs'/identity/(key+'.json');p.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
                    run.artifact_ids.append(self.registry.add(p,key,'run',False))
                evidence=a.ROOT/'output/p6ui2/runs'/identity/'evidence.json';evidence.write_text(json.dumps([a.dump(e) for e in run.stages],indent=2),encoding='utf-8')
                run.artifact_ids.append(self.registry.add(evidence,'Current validation evidence','run',False))
                self.payloads[identity]=payload;run.warnings=[w.model_dump_json() if hasattr(w,'model_dump_json') else str(w) for w in result['p5c'].reports[a.PROFILE].warnings]
                if a.sha(a.DATABASE)!=before: raise ValueError('Trusted database integrity changed')
                run.status='succeeded'
        except Exception as exc:
            with self.lock:
                failed=next((e for e in run.stages if e.status=='NOT_EVALUATED' and e.id in dict(STAGES)),None)
                if failed:failed.status='FAIL';failed.details={'error_type':type(exc).__name__}
                run.status='failed';run.errors.append({'code':'assembly_failed','message':'Assembly or validation failed. Inspect completed stage evidence.','error_type':type(exc).__name__})
                self.payloads.pop(identity,None)
        finally:
            with self.lock:run.ended_at=now();self.persist(run)
            self.capacity.release()
    def get(self,identity):
        with self.lock:
            if identity not in self.runs:raise HTTPException(404,'Unknown run ID')
            return self.runs[identity].model_copy(deep=True)

def create_app(ingestion_root=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.manager=Manager()
        app.state.ingestion=IngestionService(ingestion_root)
        yield
        app.state.ingestion.close()
        app.state.manager.pool.shutdown(wait=True)
    app=FastAPI(title='Academic OS local console',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    app.include_router(syllabi_router)
    @app.exception_handler(IngestionError)
    async def ingestion_error(request,exc):
        status=404 if exc.code=='NOT_FOUND' else 413 if exc.code=='UPLOAD_TOO_LARGE' else 429 if exc.code=='QUEUE_FULL' else 409 if exc.code in ('NOT_EVALUATED','SOURCE_CHANGED','EVIDENCE_CHANGED') else 400
        return JSONResponse({'error':{'code':exc.code,'message':exc.message}},status_code=status)
    app.add_middleware(CORSMiddleware,allow_origins=ORIGINS,allow_methods=['GET','POST'],allow_headers=['Content-Type','X-Console-Token'])
    @app.middleware('http')
    async def local_boundary(request:Request,call_next):
        if request.headers.get('host') not in ('127.0.0.1:8765','localhost:8765','testserver'):
            return JSONResponse({'detail':'Local host required'},status_code=403)
        origin=request.headers.get('origin')
        if origin is not None and origin not in ORIGINS:return JSONResponse({'detail':'Origin not allowed'},status_code=403)
        if request.method=='POST':
            if origin not in ORIGINS or request.headers.get('x-console-token')!=request.app.state.manager.token:
                return JSONResponse({'detail':'Local session required'},status_code=403)
            try:length=int(request.headers.get('content-length','0'))
            except ValueError:return JSONResponse({'detail':'Invalid content length'},status_code=400)
            upload=request.url.path=='/api/syllabi'
            limit=MAX_UPLOAD if upload else 2048
            expected='application/pdf' if upload else 'application/json'
            if length>limit:
                return JSONResponse({'error':{'code':'UPLOAD_TOO_LARGE','message':'Request exceeds the size limit.'}},status_code=413)
            if not request.headers.get('content-type','').startswith(expected):
                return JSONResponse({'error':{'code':'UNSUPPORTED_FILE_TYPE','message':expected+' is required.'}},status_code=415)
            chunks=[];size=0
            async for chunk in request.stream():
                size+=len(chunk)
                if size>limit:return JSONResponse({'error':{'code':'UPLOAD_TOO_LARGE','message':'Request exceeds the size limit.'}},status_code=413)
                chunks.append(chunk)
            request._body=b''.join(chunks)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store';response.headers['X-Content-Type-Options']='nosniff'
        return response
    def manager(request:Request):return request.app.state.manager
    @app.get('/api/health',response_model=Health)
    def health():return Health(database=str(a.DATABASE))
    @app.get('/api/session',response_model=Session)
    def session(request:Request):return Session(token=manager(request).token)
    @app.get('/api/sources',response_model=list[Source])
    def sources():return a.sources()
    @app.get('/api/curriculum/topic2',response_model=list[Curriculum])
    def curriculum(request:Request):return manager(request).tree
    @app.get('/api/topics/standard-deviation',response_model=Topic)
    def topic():
        value=a.AcademicProductService(a.DATABASE).read_topic('standard-deviation',a.SNAPSHOTS)
        return Topic(source=a.sources()[0],trust=a.dump(value.view)['trust_summary'],provenance=value.provenance)
    @app.post('/api/runs/assemble-standard-lesson',response_model=Run,status_code=202)
    def submit(selection:RunRequest,request:Request):return manager(request).submit(selection)
    @app.get('/api/runs/{identity}',response_model=Run)
    def run(identity:str,request:Request):return manager(request).get(identity)
    def payload(identity,request,key):
        m=manager(request)
        if m.get(identity).status!='succeeded':raise HTTPException(409,'Run has not succeeded')
        with m.lock:return copy.deepcopy(m.payloads[identity][key])
    @app.get('/api/runs/{identity}/lesson',response_model=Lesson)
    def lesson(identity:str,request:Request):return payload(identity,request,'lesson')
    @app.get('/api/runs/{identity}/questions',response_model=list[Question])
    def questions(identity:str,request:Request):return payload(identity,request,'questions')
    @app.get('/api/runs/{identity}/solutions',response_model=list[Solution])
    def solutions(identity:str,request:Request):return payload(identity,request,'solutions')
    @app.get('/api/runs/{identity}/evidence',response_model=list[Evidence])
    def evidence(identity:str,request:Request):return manager(request).get(identity).stages
    @app.get('/api/history',response_model=list[Historical])
    def history(request:Request):return manager(request).history
    @app.get('/api/artifacts',response_model=list[Artifact])
    def artifacts(request:Request):
        m=manager(request)
        with m.lock:return m.registry.list()
    @app.get('/api/artifacts/{identity}')
    def artifact(identity:str,request:Request):
        try:
            m=manager(request)
            with m.lock:path,dto=m.registry.get(identity)
        except (KeyError,ValueError,OSError):raise HTTPException(404,'Artifact unavailable or changed')
        return FileResponse(path,filename=path.name,media_type='application/octet-stream')
    return app

app=create_app()
