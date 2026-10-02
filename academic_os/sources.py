"""File registration and reproducible page extraction. Neither confers trust."""
import hashlib
from collections import OrderedDict
from io import BytesIO
from pathlib import Path
from threading import RLock
import pypdf
from .models import normalise
from validate_academic_knowledge_v03 import digest

def file_digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

# Computational reuse only: no locator records, reviews or usability decisions.
# Entry bounds suit the current five-file workload; they are not RSS byte limits.
_MAX_READERS = 8
_MAX_PAGES = 128
_EXTRACTION_METHOD = 'pypdf_page_text'
_EXTRACTION_OPTIONS = ()  # Immutable (keyword, value) pairs; current pypdf defaults.
_READER_POLICY = ('PdfReader', 'strict=False', 'password=None', 1)
_readers = OrderedDict()
_texts = OrderedDict()
_cache_lock = RLock()


def _clear_extraction_cache():
    """Private diagnostic/test support; ordinary callers need no lifecycle API."""
    with _cache_lock:
        _readers.clear()
        _texts.clear()


def _page_text(path, page_index, expected_digest):
    # Always read the current file, even on a cache hit. Hash and parse the same
    # bytes: neither path/mtime nor caller-supplied text can populate the cache.
    data = Path(path).read_bytes()
    content_hash = hashlib.sha256(data).hexdigest()
    if not expected_digest or content_hash != expected_digest:
        raise ValueError('source bytes changed or digest missing')
    reader_key = (content_hash, pypdf.__version__, _READER_POLICY)
    text_key = (reader_key, page_index, _EXTRACTION_METHOD, _EXTRACTION_OPTIONS)
    # pypdf readers lazily mutate during parsing/extraction. Serialize both cache
    # access and reader use; publish text only after successful extraction.
    with _cache_lock:
        if text_key in _texts:
            _texts.move_to_end(text_key)
            return _texts[text_key]
        if reader_key not in _readers:
            reader = pypdf.PdfReader(BytesIO(data))
            _readers[reader_key] = reader
            if len(_readers) > _MAX_READERS:
                _readers.popitem(last=False)
        _readers.move_to_end(reader_key)
        text = _readers[reader_key].pages[page_index].extract_text(**dict(_EXTRACTION_OPTIONS))
        _texts[text_key] = text
        if len(_texts) > _MAX_PAGES:
            _texts.popitem(last=False)
        return text

def register_candidate(source_id,path,title,source_type,curriculum,version_label,identity_basis):
    path=Path(path).resolve(strict=True)
    return dict(kind='source',payload=dict(source_id=source_id,title=title,source_type=source_type,
        origin='real',artifact_reference=str(path),content_digest=file_digest(path),
        curriculum_identity=curriculum,version_label=version_label,identity_basis=identity_basis))

def extract_candidate(source_record,source_version,locator_id,page_number,label,summary,
                      region=None,assessment_part_id=None,assessment_question_id=None):
    if page_number<1:raise ValueError('PDF page number must be >= 1')
    p=source_record['payload'];path=Path(p['artifact_reference'])
    if file_digest(path)!=p['content_digest']:raise ValueError('Source bytes changed since registration')
    pages=pypdf.PdfReader(path).pages
    if page_number>len(pages):raise ValueError('PDF page out of range')
    text=pages[page_number-1].extract_text()
    return dict(kind='locator',payload=dict(locator_id=locator_id,source_id=p['source_id'],
        locator_kind='question_part' if assessment_part_id else 'section',label=label,
        page_index=page_number-1,anchor=path.as_uri()+f'#page={page_number}',
        assessment_part_id=assessment_part_id,assessment_question_id=assessment_question_id,
        source_version=source_version,extracted_text=text,text_digest=digest(text),text_summary=summary,
        extractor_version=pypdf.__version__,visual_region=region or [0.0,0.0,1.0,1.0]))

def integrity(graph,keys):
    errors=[]
    for key in keys:
        rec=graph[key]['record'];p=rec['payload']
        try:
            if rec['kind']=='source':
                if not p['content_digest'] or file_digest(p['artifact_reference'])!=p['content_digest']:
                    errors.append(key+': source bytes changed or digest missing')
            elif rec['kind']=='locator':
                src=graph['source:'+p['source_id']];sp=src['record']['payload']
                if p['source_version']!=src['version']:raise ValueError('source version mismatch')
                text=_page_text(sp['artifact_reference'],p['page_index'],sp['content_digest'])
                if p['extracted_text']!=text or p['text_digest']!=digest(p['extracted_text']):
                    raise ValueError('official page text differs from extraction')
                if p['anchor']!=Path(sp['artifact_reference']).as_uri()+f"#page={p['page_index']+1}":
                    raise ValueError('locator return link differs from registered page')
        except (OSError,ValueError,IndexError,TypeError,KeyError) as e:errors.append(key+': '+str(e))
    return errors
