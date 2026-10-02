"""Current read-only P5B composition -> independent P5C readiness report."""
from dataclasses import dataclass
import json
from pathlib import Path
from .profiled_content_service import ProfiledContentService
from .lesson_profile_service import LessonProfileService
from .authored_service import AuthoredTeachingService
from .content_validation_service import AuthoredContentValidationService
from .learning_service import LearningSpecificationService
from .pedagogical_core import build_pedagogical_specification
from .profiled_content_validation import validate_profiled_content

@dataclass(frozen=True)
class ProfiledValidationRead:
    reports:dict
    provenance:dict

class ProfiledContentValidationService:
    def __init__(self,database):
        self._content=ProfiledContentService(database);self._profiles=LessonProfileService(database)
        self._authored=AuthoredTeachingService(database);self._p4b=AuthoredContentValidationService(database)
        self._learning=LearningSpecificationService(database)
    def read_profiles(self,topic_key,snapshot_ids):
        content=self._content.read_profiles(topic_key,snapshot_ids)
        profiles=self._profiles.read_profiles(topic_key,snapshot_ids)
        authored=self._authored.read_topic(topic_key,snapshot_ids)
        p4b=self._p4b.read_topic(topic_key,snapshot_ids)
        learning=self._learning.read_topic(topic_key,snapshot_ids)
        if (content.provenance['upstream']!=profiles.provenance or content.provenance['source_p4b']!=p4b.provenance or p4b.provenance['upstream']!=authored.provenance
            or profiles.provenance['upstream']!=learning.provenance or authored.provenance['upstream']['upstream']['upstream']!=learning.provenance):
            raise ValueError('Upstream changed between profile validation reads; retry')
        base=build_pedagogical_specification(learning.view)
        reports={k:validate_profiled_content(package,profiles.profiles[k],profiles.views[k],authored.view,p4b.view,learning.view,base) for k,package in content.packages.items()}
        return ProfiledValidationRead(reports,dict(upstream=content.provenance,current_upstream_validated=True,
            trust_boundary='Profile renderer eligibility only; no new academic approval, publication or student mastery claim. Refresh before rendering.'))

def save_profiled_validation(result,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    data={k+'.validation.json':v.serialize() for k,v in result.reports.items()}
    data['provenance.json']=json.dumps(result.provenance,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    for name,value in data.items():
        p=out/name
        if p.exists() and p.read_bytes()!=value.encode():raise ValueError('Different existing validation output: '+str(p))
    for name,value in data.items():
        p=out/name
        if not p.exists():
            with p.open('xb') as stream:stream.write(value.encode())
    return [str(out/name) for name in data]
