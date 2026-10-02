"""Fresh profile and authored/P4B reads, with cross-chain provenance checks."""
from dataclasses import dataclass
import json
from pathlib import Path
from .lesson_profile_service import LessonProfileService
from .authored_service import AuthoredTeachingService
from .content_validation_service import AuthoredContentValidationService
from .learning_service import LearningSpecificationService
from .pedagogical_core import build_pedagogical_specification
from .profiled_pedagogy import digest
from .profiled_content import build_profiled_content,verify_profiled_package
from .profiled_sd_provider import author

@dataclass(frozen=True)
class ProfiledContentRead:
    packages:dict
    verification:dict
    provenance:dict

class ProfiledContentService:
    def __init__(self,database,provider=author):
        self._provider=provider
        self._profiles=LessonProfileService(database);self._authored=AuthoredTeachingService(database)
        self._validation=AuthoredContentValidationService(database);self._learning=LearningSpecificationService(database)
    def read_profiles(self,topic_key,snapshot_ids):
        profiles=self._profiles.read_profiles(topic_key,snapshot_ids)
        authored=self._authored.read_topic(topic_key,snapshot_ids)
        validation=self._validation.read_topic(topic_key,snapshot_ids)
        learning=self._learning.read_topic(topic_key,snapshot_ids)
        if validation.provenance['upstream']!=authored.provenance or authored.provenance['upstream']['upstream']['upstream']!=learning.provenance or profiles.provenance['upstream']!=learning.provenance:
            raise ValueError('Upstream changed between profiled authoring reads; retry')
        base=build_pedagogical_specification(learning.view)
        packages={k:build_profiled_content(p,authored.view,validation.view,learning.view,base,self._provider) for k,p in profiles.views.items()}
        checks={k:verify_profiled_package(v,profiles.views[k],authored.view,validation.view,learning.view,base,self._provider) for k,v in packages.items()}
        if not all(v['valid'] for v in checks.values()):raise ValueError('P5B package integrity verification failed')
        return ProfiledContentRead(packages,checks,dict(upstream=profiles.provenance,source_p4b=validation.provenance,current_upstream_validated=True,
            trust_boundary='Candidate content only; no academic approval, completed P5C validation or rendering eligibility.'))

def save_profiled_content(result,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    payloads={k+'.profiled-authored.json':v.serialize() for k,v in result.packages.items()}
    for name,value in [('verification',result.verification),('provenance',result.provenance)]:payloads[name+'.json']=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    for name,data in payloads.items():
        p=out/name
        if p.exists() and p.read_bytes()!=data.encode():raise ValueError('Different existing output: '+str(p))
    for name,data in payloads.items():
        p=out/name
        if not p.exists():
            with p.open('xb') as stream:stream.write(data.encode())
    return [str(out/name) for name in payloads]
