"""Read-only live upstream boundary for lesson profile planning. No PPT/P4A reads."""
from dataclasses import dataclass
import json
from pathlib import Path
from .learning_service import LearningSpecificationService
from .pedagogical_core import build_pedagogical_specification
from .lesson_profiles import KEYS,lesson_profile
from .profiled_pedagogy import build_profiled_pedagogy,validate_profiled_pedagogy,digest

@dataclass(frozen=True)
class ProfileRead:
    profiles:dict
    views:dict
    validations:dict
    provenance:dict

class LessonProfileService:
    def __init__(self,database):self._learning=LearningSpecificationService(database)
    def read_profiles(self,topic_key,snapshot_ids):
        current=self._learning.read_topic(topic_key,snapshot_ids)
        base=build_pedagogical_specification(current.view)
        profiles={k:lesson_profile(k) for k in KEYS}
        views={k:build_profiled_pedagogy(current.view,base,p) for k,p in profiles.items()}
        validations={k:validate_profiled_pedagogy(views[k],current.view,base,p) for k,p in profiles.items()}
        if not all(v.valid for v in validations.values()):raise ValueError('Profile planning validation failed')
        return ProfileRead(profiles,views,validations,dict(upstream=current.provenance,current_upstream_validated=True,
            source_learning_sha256=digest(current.view),source_base_pedagogy_sha256=digest(base),
            trust_boundary='Product planning only. Gold configuration reflects user-specified design, not a new academic approval. Content remains unpopulated; P5B must author or validate reuse before rendering.'))


def save_profile_read(result,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    payloads={}
    for key in KEYS:
        for suffix,model in (('lesson-profile',result.profiles[key]),('profiled-pedagogy',result.views[key]),('validation',result.validations[key])):
            payloads[key+'.'+suffix+'.json']=model.serialize().encode()
    payloads['provenance.json']=(json.dumps(result.provenance,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    # Check every existing file before any write; immutable/idempotent output.
    for name,data in payloads.items():
        target=out/name
        if target.exists() and target.read_bytes()!=data:raise ValueError('Different existing profile output: '+str(target))
    for name,data in payloads.items():
        target=out/name
        if not target.exists():
            with target.open('xb') as stream:stream.write(data)
    return [str(out/name) for name in payloads]
