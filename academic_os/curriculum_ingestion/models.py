from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class DTO(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Warning(DTO):
    code:str
    message:str
    page:int|None=None

class CurriculumDocument(DTO):
    document_id:str
    original_filename:str
    sha256:str
    byte_size:int
    page_count:int
    uploaded_at:str
    profile:str|None
    status:Literal['UPLOADED','UNSUPPORTED_CURRICULUM_PROFILE']
    trust:Literal['UNTRUSTED / REVIEWABLE CURRICULUM EVIDENCE']='UNTRUSTED / REVIEWABLE CURRICULUM EVIDENCE'

class ExtractRequest(DTO):
    profile:str='edexcel-4ma1-topic2-2017/1'
    tier:Literal['foundation','higher']
    start_page:int=Field(ge=1)
    end_page:int=Field(ge=1)

class ParseRequest(DTO):
    extraction_run_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    mode:Literal['preserved','live']
    confirm_model_call:bool=False

class PageText(DTO):
    page_number:int
    text:str
    warnings:list[Warning]

class Extraction(DTO):
    source_sha256:str
    start_page:int
    end_page:int
    extractor:str
    pages:list[PageText]
    text:str
    warnings:list[Warning]

class Validation(DTO):
    status:str
    structure_valid:bool
    errors:list[str]
    warnings:list[str]
    parser_warnings:list[str]
    objective_count:int
    subtopic_count:int
    source_ids_valid:bool
    validated_source_ids:int
    official_text_confirmed:Literal[False]=False

class CanonicalMappingStatus(DTO):
    status:Literal['mapped','unmapped']='unmapped'
    mapping_id:str|None=None
    review_status:str|None=None
    reason:str='No governed mapping for this uploaded document version'

class Objective(DTO):
    objective_code:str
    official_text:str
    source_id:str
    canonical:CanonicalMappingStatus=Field(default_factory=CanonicalMappingStatus)

class Subtopic(DTO):
    subtopic_code:str
    subtopic_name:str
    objectives:list[Objective]
    notes:list[str]

class Topic(DTO):
    topic_code:str
    topic_name:str
    subtopics:list[Subtopic]

class CurriculumTier(DTO):
    document_id:str
    source_sha256:str
    run_id:str
    profile:str
    tier:str
    topics:list[Topic]
    warnings:list[Warning]
    validation:Validation
    provenance_mode:str

class IngestionRun(DTO):
    run_id:str
    operation:Literal['extract','parse']
    document_id:str
    source_sha256:str
    profile:str
    tier:str
    start_page:int
    end_page:int
    extraction_run_id:str|None=None
    mode:str='no-model'
    status:Literal['queued','running','succeeded','failed','blocked']='queued'
    stages:dict[str,str]=Field(default_factory=lambda:dict(extraction='NOT_EVALUATED',parsing='NOT_EVALUATED',validation='NOT_EVALUATED'))
    parser_configuration:dict=Field(default_factory=dict)
    model_calls:int=0
    outputs:dict[str,str]=Field(default_factory=dict)
    warnings:list[Warning]=Field(default_factory=list)
    errors:list[Warning]=Field(default_factory=list)
    started_at:str
    ended_at:str|None=None

class SelectedCurriculumTarget(DTO):
    schema_version:Literal['selected-curriculum-target/2']='selected-curriculum-target/2'
    target_id:str
    document_id:str
    source_sha256:str
    run_id:str
    parsed_sha256:str
    validation_sha256:str
    tree_sha256:str
    run_sha256:str
    profile:str
    specification:str='4MA1'
    tier:str
    topic_code:str
    topic_name:str
    subtopic_code:str|None
    subtopic_name:str|None
    objective_codes:list[str]
    source_ids:list[str]
    validation_state:str
    academically_approved:Literal[False]=False

class CurriculumCapabilityPackage(DTO):
    target:SelectedCurriculumTarget
    CURRICULUM_BROWSABLE:bool
    LESSON_GENERATION_SUPPORTED:Literal[False]=False
    QUESTION_GENERATION_SUPPORTED:Literal[False]=False
    PRESENTATION_SUPPORTED:Literal[False]=False
    reason:str='No topic-to-learning/pedagogy adapter; uploaded 4MA1 never routes to Standard Deviation.'
