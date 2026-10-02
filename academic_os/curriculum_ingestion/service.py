"""Immutable documents, append-only task evidence, bounded ingestion worker."""
import json
import re
import threading
import uuid
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import core
from .models import *
from .validation import validate_curriculum

def now():return datetime.now(timezone.utc).isoformat()
def serial(value):
    if hasattr(value,'model_dump'):value=value.model_dump(mode='json')
    return json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2).encode('utf-8')

class Storage:
    def __init__(self,root):self.root=Path(root).absolute();self.safe()
    def safe(self,*parts):
        p=self.root.joinpath(*parts)
        if not p.resolve().is_relative_to(self.root) or p.resolve()!=p.absolute():raise core.IngestionError('PATH_REJECTED','Runtime path is not contained.')
        for item in (p,*p.parents):
            if item.is_symlink() or item.is_junction():raise core.IngestionError('PATH_REJECTED','Links and junctions are not allowed in ingestion storage.')
        return p
    def identity(self,value):
        if not re.fullmatch(r'[a-f0-9]{32}',value):raise core.IngestionError('NOT_FOUND','Unknown document or run ID.')
        return value
    def write(self,parts,data):
        path=self.safe(*parts);path.parent.mkdir(parents=True,exist_ok=True);self.safe(*parts)
        with path.open('xb') as f:f.write(data)
        return core.digest(data)
    def read(self,*parts):return self.safe(*parts).read_bytes()

class IngestionService:
    def __init__(self,root=None):
        self.storage=Storage(root or core.ROOT/'var/p6ui');self.lock=threading.RLock()
        self.pool=ThreadPoolExecutor(max_workers=1);self.capacity=threading.BoundedSemaphore(2);self.current={};self.sequence={}
    def close(self):self.pool.shutdown(wait=True)
    def upload(self,data,filename,mime):
        if mime!='application/pdf' or not filename.lower().endswith('.pdf'):raise core.IngestionError('UNSUPPORTED_FILE_TYPE','Only application/pdf files are supported.')
        if len(filename)>180 or any(c in filename for c in ('/','\\',':','\0')) or '..' in filename or any(ord(c)<32 for c in filename):raise core.IngestionError('PATH_REJECTED','Use a plain PDF filename, without path components.')
        if len(data)>core.MAX_UPLOAD:raise core.IngestionError('UPLOAD_TOO_LARGE','PDF exceeds the 10 MiB upload limit.')
        count=core.inspect_pdf(data);sha=core.digest(data);identity=uuid.uuid4().hex
        doc=CurriculumDocument(document_id=identity,original_filename=filename,sha256=sha,byte_size=len(data),page_count=count,uploaded_at=now(),profile=core.PROFILE if sha==core.KNOWN_SHA else None,status='UPLOADED' if sha==core.KNOWN_SHA else 'UNSUPPORTED_CURRICULUM_PROFILE')
        self.storage.write(('uploads',identity,'source.pdf'),data);self.storage.write(('uploads',identity,'document.json'),serial(doc))
        return doc
    def document(self,identity):
        identity=self.storage.identity(identity)
        try:
            doc=CurriculumDocument.model_validate_json(self.storage.read('uploads',identity,'document.json'))
            if core.digest(self.storage.read('uploads',identity,'source.pdf'))!=doc.sha256:raise core.IngestionError('SOURCE_CHANGED','Uploaded PDF no longer matches its immutable identity.')
            return doc
        except FileNotFoundError:raise core.IngestionError('NOT_FOUND','Unknown document ID.') from None
    def persist(self,run):
        number=self.sequence.get(run.run_id,0);self.sequence[run.run_id]=number+1
        self.storage.write(('runs',run.run_id,f'event-{number:04}.json'),serial(run))
        if run.status in ('succeeded','failed','blocked'):self.storage.write(('runs',run.run_id,'result.json'),serial(run))
    def get(self,identity):
        identity=self.storage.identity(identity)
        with self.lock:
            if identity in self.current:return self.current[identity].model_copy(deep=True)
        try:return IngestionRun.model_validate_json(self.storage.read('runs',identity,'result.json'))
        except FileNotFoundError:raise core.IngestionError('NOT_FOUND','Unknown or interrupted run; completed results remain available after restart.') from None
    def runs(self,document_id):
        self.document(document_id)
        ids=set(self.current)
        root=self.storage.safe('runs')
        if root.exists():ids.update(p.name for p in root.iterdir() if p.is_dir() and re.fullmatch('[a-f0-9]{32}',p.name))
        rows=[]
        for identity in ids:
            try:row=self.get(identity)
            except core.IngestionError:continue
            if row.document_id==document_id:rows.append(row)
        return sorted(rows,key=lambda r:r.started_at)
    def output(self,identity,name):
        run=self.get(identity)
        if name not in run.outputs:raise core.IngestionError('NOT_EVALUATED','This run has no requested output.')
        value=self.storage.read('runs',identity,name+'.json')
        if core.digest(value)!=run.outputs[name]:raise core.IngestionError('EVIDENCE_CHANGED','Run evidence changed after completion.')
        return json.loads(value)
    def save_output(self,run,name,value):
        run.outputs[name]=self.storage.write(('runs',run.run_id,name+'.json'),serial(value))
    def submit_extract(self,document_id,request):
        doc=self.document(document_id)
        run=IngestionRun(run_id=uuid.uuid4().hex,operation='extract',document_id=doc.document_id,source_sha256=doc.sha256,profile=request.profile,tier=request.tier,start_page=request.start_page,end_page=request.end_page,started_at=now())
        return self.submit(run)
    def submit_parse(self,document_id,request):
        doc=self.document(document_id);ex=self.get(request.extraction_run_id)
        if ex.operation!='extract' or ex.document_id!=doc.document_id or ex.status!='succeeded' or ex.source_sha256!=doc.sha256:
            raise core.IngestionError('EXTRACTION_FAILED','Choose a successful extraction from this document.')
        if request.mode=='live' and not request.confirm_model_call:raise core.IngestionError('MODEL_CALL_NOT_CONFIRMED','Explicit confirmation is required for a paid AI parse.')
        run=IngestionRun(run_id=uuid.uuid4().hex,operation='parse',document_id=doc.document_id,source_sha256=doc.sha256,profile=ex.profile,tier=ex.tier,start_page=ex.start_page,end_page=ex.end_page,extraction_run_id=ex.run_id,mode=request.mode,started_at=now())
        return self.submit(run)
    def submit(self,run):
        if not self.capacity.acquire(blocking=False):raise core.IngestionError('QUEUE_FULL','The bounded local ingestion queue is full.')
        try:
            with self.lock:self.current[run.run_id]=run;self.persist(run);response=run.model_copy(deep=True)
            self.pool.submit(self.execute,run.run_id)
            return response
        except Exception:self.capacity.release();raise
    def execute(self,identity):
        with self.lock:r=self.current[identity];r.status='running';self.persist(r)
        try:
            doc=self.document(r.document_id)
            if doc.profile!=core.PROFILE or r.profile!=core.PROFILE:raise core.IngestionError('UNSUPPORTED_CURRICULUM_PROFILE','Only the known 2017 4MA1 PDF edition is supported; no generic parser fallback.')
            if r.operation=='extract':
                ex=core.extract_pages(self.storage.safe('uploads',doc.document_id,'source.pdf'),r.start_page,r.end_page)
                if not any(p.text.strip() for p in ex.pages):raise core.IngestionError('EXTRACTION_FAILED','No text available; OCR is not supported.')
                self.save_output(r,'extraction',ex);r.warnings=ex.warnings;r.stages['extraction']='PASS'
            else:
                ex=Extraction.model_validate(self.output(r.extraction_run_id,'extraction'));r.stages['extraction']='PASS';r.warnings=list(ex.warnings)
                if (r.start_page,r.end_page)!=core.RANGES[r.tier]:raise core.IngestionError('UNSUPPORTED_CURRICULUM_PROFILE','This parser requires the supported tier page range.')
                if ex.source_sha256!=doc.sha256:raise core.IngestionError('SOURCE_CHANGED','Extraction is not bound to this PDF.')
                if r.mode=='preserved':
                    binding=json.loads(Path(__file__).with_name('preserved_4ma1.json').read_text());fixture=binding['tiers'][r.tier]
                    if doc.sha256!=binding['source_sha256'] or core.digest(ex.text.encode())!=fixture['extracted_text_sha256']:raise core.IngestionError('UNSUPPORTED_CURRICULUM_PROFILE','No preserved parse matches this exact source and extraction.')
                    raw=(core.ROOT/fixture['path']).read_bytes()
                    if core.digest(raw)!=fixture['sha256']:raise core.IngestionError('EVIDENCE_CHANGED','Preserved curriculum fixture changed.')
                    r.parser_configuration={'mode':'preserved parse replay','fixture_sha256':fixture['sha256'],'extracted_text_sha256':fixture['extracted_text_sha256'],'model_invoked':False}
                    parser=lambda text,tier:json.loads(raw)
                else:
                    r.parser_configuration=core.model_configuration()
                    def parser(text,tier):
                        r.model_calls+=1
                        with self.lock:self.persist(r)
                        return core.live_parse(text,tier,r.parser_configuration)
                parsed=core.parse_curriculum(ex.text,r.tier,r.profile,parser)
                self.save_output(r,'parsed',parsed);r.stages['parsing']='PASS'
                validation=Validation(**validate_curriculum(parsed,r.tier));self.save_output(r,'validation',validation)
                r.warnings.extend(Warning(code='PARSER_WARNING',message=w) for w in parsed['warnings'])
                r.warnings.extend(Warning(code='VALIDATION_WARNING',message=w) for w in validation.warnings)
                r.stages['validation']='PASS' if validation.structure_valid else 'FAIL'
                if not validation.structure_valid:raise core.IngestionError('CURRICULUM_VALIDATION_FAILED','Parsed curriculum failed structural validation. See the validation report.')
                self.save_output(r,'tree',self.build_tree(r,parsed,validation))
            if self.document(r.document_id).sha256!=r.source_sha256:raise core.IngestionError('SOURCE_CHANGED','Source changed during ingestion.')
            r.status='succeeded'
        except Exception as exc:
            error=exc if isinstance(exc,core.IngestionError) else core.IngestionError('INGESTION_FAILED','Ingestion failed; internal details withheld.')
            r.status='blocked' if error.code in ('UNSUPPORTED_CURRICULUM_PROFILE','MODEL_CONFIGURATION_MISSING') else 'failed'
            stage='extraction' if r.operation=='extract' else 'parsing' if r.stages['parsing']!='PASS' else 'validation'
            r.stages[stage]='BLOCKED' if r.status=='blocked' else 'FAIL';r.errors.append(Warning(code=error.code,message=error.message))
        finally:
            try:
                with self.lock:r.ended_at=now();self.persist(r)
            finally:self.capacity.release()
    def build_tree(self,r,parsed,validation):
        nodes=[Subtopic(subtopic_code=s['code'],subtopic_name=s['name'],notes=s['notes'],objectives=[Objective(objective_code=o['code'],official_text=o['official_text'],source_id=o['source_id']) for o in s['objectives']]) for s in parsed['subtopics']]
        return CurriculumTier(document_id=r.document_id,source_sha256=r.source_sha256,run_id=r.run_id,profile=r.profile,tier=parsed['tier_source'],topics=[Topic(topic_code=parsed['topic_code'],topic_name=parsed['topic_name'],subtopics=nodes)],warnings=r.warnings,validation=validation,provenance_mode=r.mode)
    def tree(self,identity):
        r=self.get(identity)
        if r.status!='succeeded' or r.operation!='parse':raise core.IngestionError('NOT_EVALUATED','A successfully validated parse is required for browsing.')
        if self.document(r.document_id).sha256!=r.source_sha256:raise core.IngestionError('SOURCE_CHANGED','Document identity no longer matches this run.')
        self.output(identity,'parsed');self.output(identity,'validation')
        return CurriculumTier.model_validate(self.output(identity,'tree'))
    def capabilities(self,identity,subtopic=None,objective=None):
        tree=self.tree(identity);topic=tree.topics[0];subs=[s for s in topic.subtopics if subtopic is None or s.subtopic_code==subtopic]
        if not subs or (objective and not subtopic):raise core.IngestionError('NOT_FOUND','Selection is not in this curriculum run.')
        objects=[o for s in subs for o in s.objectives if objective is None or o.objective_code==objective]
        if objective and not objects:raise core.IngestionError('NOT_FOUND','Objective is not in this subtopic.')
        fields=dict(document_id=tree.document_id,source_sha256=tree.source_sha256,run_id=tree.run_id,parsed_sha256=self.get(identity).outputs['parsed'],profile=tree.profile,tier=tree.tier,topic_code=topic.topic_code,subtopic_code=subtopic,objective_codes=[o.objective_code for o in objects],source_ids=[o.source_id for o in objects],validation_state=tree.validation.status)
        target=SelectedCurriculumTarget(target_id=core.digest(serial(fields)),**fields)
        return CurriculumCapabilityPackage(target=target,CURRICULUM_BROWSABLE=True)
