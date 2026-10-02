"""Deterministic rebuilding from immutable stored records; no model or DB reads."""
from collections import Counter
from pathlib import Path
from statistics import mean, median
from ..ai_authoring.brief import digest
from .models import Attempt, QualificationReport, ControlledAttempt, ControlledQualificationReport
from .controlled_replay import saved_context, verify_attempt
from ..ai_authoring.provenance import LEGACY_POLICY, POLICY, STATUSES, outcome, require_policy
from .storage import read, write_new, checked_member

CHECKS = ('schema_valid','content_complete','scaffold_valid','numeric_encoding_valid','expression_semantics_valid','derivation_provenance_valid','math_valid','solution_valid','scope_valid','boundary_valid','composition_valid')


def rebuild(directory, *, output_dir=None):
    directory=Path(directory)
    manifest=read(directory/'run.json')
    policy=require_policy(manifest.get('acceptance_policy',LEGACY_POLICY))
    brief=read(directory/'brief.json')
    case, controlled=saved_context(manifest, brief, policy)
    records=[];started=0
    for number in range(1,manifest['requested_attempt_count']+1):
        folder=directory/f'attempt-{number:02d}'
        if (folder/'started.json').exists():started+=1
        if not (folder/'attempt.json').exists():continue
        record=(ControlledAttempt if case is not None else Attempt).model_validate(read(folder/'attempt.json'))
        if record.attempt_id!=f'attempt-{number:02d}':raise ValueError('Attempt identity mismatch')
        for name,expected in record.artifact_hashes.items():checked_member(folder,name,expected)
        if record.brief_hash!=manifest['authoring_brief']['sha256']:raise ValueError('Normal brief binding differs')
        if record.candidate_artifact_ref not in record.artifact_hashes:raise ValueError('Missing candidate digest')
        audit=read(folder/record.candidate_artifact_ref)
        if (audit['candidate_id']!=record.candidate_id or audit['validation']['accepted']!=record.accepted
            or record.accepted!=(record.outcome=='candidate_accepted')):raise ValueError('Attempt outcome differs from candidate audit')
        for key in CHECKS:
            expected=audit['validation'].get(key)
            if key=='numeric_encoding_valid':
                status=audit['validation'].get('verification_summary',{}).get('stage_status',{}).get('numeric_encoding','NOT_EVALUATED')
                expected=None if status=='NOT_EVALUATED' else status=='PASSED'
            if getattr(record,key) is not None and getattr(record,key)!=expected:raise ValueError('Attempt check differs from candidate audit')
        if read(folder/'validation.json')!=audit['validation'] or digest(read(folder/'brief.json'))!=record.brief_hash:
            raise ValueError('Attempt validation or brief differs from audit')
        if record.acceptance_policy != policy:
            raise ValueError('Attempt policy differs from run policy')
        status = record.derivation_provenance_status
        if record.derivation_provenance_valid is not outcome(status):
            raise ValueError('Inconsistent provenance status/value')
        if record.outcome not in ('provider_failure','input_validation_failure','candidate_schema_failure'):
            if status != audit['validation'].get('derivation_provenance_status','NOT_EVALUATED'):
                raise ValueError('Attempt provenance status differs from candidate audit')
        if audit['validation'].get('acceptance_policy',LEGACY_POLICY) != policy:
            raise ValueError('Candidate acceptance policy differs from run')
        if policy == POLICY and record.accepted and record.derivation_provenance_valid is not True:
            raise ValueError('Provenance-required acceptance lacks a provenance pass')
        if case is not None:
            if read(folder/'brief.json') != brief:
                raise ValueError('Controlled attempt brief changed')
            verify_attempt(record, audit, manifest, brief, case)
        elif any(k.startswith('controlled_') for k in audit['validation']):
            raise ValueError('Controlled result without run context')
        records.append(record)
    finished=read(directory/'completion.json') if (directory/'completion.json').exists() else None
    normal=[r for r in records if r.case_id is None]
    stresses=[r for r in records if r.case_id is not None]
    aggregate={'attempts':len(normal),'accepted_count':sum(r.accepted for r in normal),
        'rejected_count':sum(r.outcome in ('candidate_schema_failure','candidate_validation_rejected') for r in normal)}
    for key in CHECKS:
        aggregate[key+'_count']=sum(getattr(r,key) is True for r in normal)
        aggregate[key+'_evaluated_count']=sum(getattr(r,key) is not None for r in normal)
    aggregate['derivation_provenance_status_counts']={s:sum(r.derivation_provenance_status==s for r in normal) for s in STATUSES}
    aggregate['provider_calls_completed']=sum(r.provider_call_completed is True for r in normal)
    aggregate['provider_failures']=sum(r.outcome=='provider_failure' for r in normal)
    rejection=Counter(code for r in normal if r.outcome in ('candidate_schema_failure','candidate_validation_rejected') for code in r.violations)
    usage={'cost_status':'not_computed'}
    for key in ('input_tokens','output_tokens','total_tokens'):
        values=[r.usage.get(key) for r in records if r.usage.get(key) is not None]
        usage[key]={'known_sum':sum(values) if values else None,'reported_attempts':len(values),'missing_attempts':len(records)-len(values)}
    times=[r.latency_ms for r in records if r.latency_ms is not None]
    latency={'unit':'milliseconds','measured_attempts':len(times),'min':min(times) if times else None,
        'max':max(times) if times else None,'mean':mean(times) if times else None,'median':median(times) if times else None}
    baseline={'before':manifest['baseline_before'],'after':finished['baseline_after'] if finished else None,
        'unchanged':finished['baseline_after']==manifest['baseline_before'] if finished else None,
        'engineering_only':True}
    complete=bool(finished and finished['status']=='complete' and len(records)==manifest['requested_attempt_count'])
    if case is not None:
        aggregate['controlled_input_binding_valid_count']=sum(r.controlled_input_binding_valid is True for r in normal)
        aggregate['controlled_input_binding_evaluated_count']=sum(r.controlled_input_binding_valid is not None for r in normal)
    report_type = ControlledQualificationReport if case is not None else QualificationReport
    report=report_type(**controlled, acceptance_policy=policy,identity=manifest['run_id'],experiment_type=manifest['experiment_type'],
        status='complete' if complete else 'incomplete',completion_reason=finished['reason'] if finished else 'No completion marker; inspect started attempts; never auto-resume.',
        slot=manifest['slot'],authoring_brief=manifest['authoring_brief'],provider=manifest['provider'],model=manifest['model'],
        configuration=manifest['configuration'],requested_attempt_count=manifest['requested_attempt_count'],attempt_count=len(records),
        started_attempt_count=started,attempts=tuple(normal),aggregate_validation=aggregate,rejection_summary=dict(sorted(rejection.items())),
        operational_outcomes=dict(sorted(Counter(r.outcome for r in records).items())),usage_summary=usage,latency_summary=latency,
        stress_tests=tuple(stresses),stress_summary={'attempted':len(stresses),'correctly_blocked':sum(r.blocked is True for r in stresses),
            'unexpectedly_accepted':sum(r.forbidden_behavior_observed is True and r.accepted for r in stresses),
            'inconclusive':sum(r.forbidden_behavior_observed is not True or r.outcome in ('provider_failure','input_validation_failure') for r in stresses)},
        safety_summary={'model_qualified':None,'derivation_provenance_verified':bool(normal) and all(r.derivation_provenance_valid is True for r in normal),'expression_semantics_verified':bool(normal) and all(r.expression_semantics_valid is True for r in normal),'engineering_experiment_only':True,'academic_approval':False,'model_quality_certified':False,
            'qualification_threshold_defined':False,'renderer_readiness_granted':False,'automatic_retry':False,'automatic_repair':False,
            'normal_and_adversarial_aggregates_separate':True,'live_api_requested':manifest['experiment_type'].startswith('live_'),
            'provider_calls_recorded_in_completed_attempts':sum(r.provider_calls for r in records),
            'started_without_completed_record':started-len(records)},
        baseline_integrity=baseline,limitations=('Descriptive measurements only; no production-readiness threshold.',
            'Existing scalar mathematics is unchanged; controlled expression semantics is an additional gate.',
            'Provider failures are not mathematical/scope rejections. Unknown usage stays unknown.',
            'Stress refusal/compliant responses are inconclusive for the intended forbidden case.',
            'Local experiment files are not signed credentials or academic truth; no automatic resume.',
            'SDK parse failures may prevent raw response recovery; exception bodies are never saved.'))
    path=(Path(output_dir) if output_dir is not None else directory/'reports')/('report-'+digest(report)+'.json')
    write_new(path,report,identical_ok=True)
    return report,path
