"""The user's two Gold product configurations. No reviewer identity is invented."""
from .lesson_profile_models import (LessonProfile,ProfileIdentity,Duration,MinuteRange,DensityPolicy,Count,PracticePolicy,AssessmentPolicy,TimePlan,TimePhase)

KEYS=('focused-review','standard-lesson')
DENSITY_KEYS=tuple(DensityPolicy.model_fields)

def lesson_profile(key):
    if key not in KEYS:raise ValueError('Unknown lesson profile: '+str(key))
    standard=key=='standard-lesson'
    targets=(1,1,1,1,1,1,2,2,3,1,1,1) if standard else (1,1,0,1,0,1,1,0,2,1,1,0)
    density={name:Count(minimum=2 if standard and name=='independent_practice' else n,target=n) for name,n in zip(DENSITY_KEYS,targets)}
    phases=[('orientation','Orientation',3,5),('concept_development','Concept development',8,10),('calculation_development','Calculation development',8,10),('summary_method','Summary-statistics method / modelling',8,10),('worked_examples','Worked examples',8,10),('guided_practice','Guided practice',8,10),('independent_practice','Independent practice',8,10),('checks_closure','Checks + closure',5,7)] if standard else [
        ('orientation','Orientation / goals',1,2),('concept_development','Concept + visual',4,5),('calculation_development','Calculation method',3,4),('summary_method','Summary-statistics method',3,4),('worked_examples','Worked example',4,5),('independent_practice','Independent practice',5,7),('checks_closure','Checks + closure',3,4)]
    return LessonProfile(identity=ProfileIdentity(profile_key=key,title='Standard Lesson' if standard else 'Focused Review'),
        duration=Duration(target_minutes=60 if standard else 25,acceptable_range_minutes=MinuteRange(min=50 if standard else 20,max=60 if standard else 30)),
        purpose='Provide fuller development, modelling, supported application, independent practice and consolidation of the same Learning Requirements.' if standard else 'Concise consolidation/review of the existing Learning Requirements through explanation, one worked example, short practice and retrieval checks. Review is a product mode, not a claim about prior teaching.',
        density_policy=DensityPolicy(**density),practice_policy=PracticePolicy(support_modes=('guided','independent') if standard else ('independent',)),
        assessment_policy=AssessmentPolicy(exit_check_required=standard),time_plan=TimePlan(phases=tuple(TimePhase(key=k,title=t,suggested_range_minutes=MinuteRange(min=a,max=b)) for k,t,a,b in phases)))


def validate_lesson_profile(profile):
    data=profile.model_dump(mode='json') if isinstance(profile,LessonProfile) else profile
    value=LessonProfile.model_validate(data)
    if value!=lesson_profile(value.identity.profile_key):raise ValueError('Lesson profile differs from the supported Gold product configuration')
    return value
