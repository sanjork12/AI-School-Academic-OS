"""Independent single-call attempts; P6A alone decides candidate validation."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from ..ai_authoring.brief import ROLE, compile_brief, current_binding, digest, serial
from ..ai_authoring.service import run_once, save, contains_secret
from .models import Attempt, ControlledAttempt
from ..ai_authoring.controlled import require_context
from ..ai_authoring.provenance import POLICY, VERSION, require_policy
from .reporting import CHECKS, rebuild
from .storage import file_hash, write_new
from .stress import forbidden_observed


def now():return datetime.now(timezone.utc).isoformat()


class Probe:
    def __init__(self,author):
        self.author_impl=author;self.returned=False;self.error_code=None
    def author(self,brief):
        try:
            reply=self.author_impl.author(brief)
            self.returned=True;self.error_code=reply.error_code
            return reply
        except Exception:
            self.error_code='provider_exception'
            raise


def classify(audit,probe):
    error=audit['provider_error_code']
    if error=='current_source_refresh_failed':return 'input_validation_failure'
    if not probe.returned or probe.error_code:return 'provider_failure'
    if not audit['validation']['schema_valid']:return 'candidate_schema_failure'
    return 'candidate_accepted' if audit['validation']['accepted'] else 'candidate_validation_rejected'


def execute(inputs, author_factory, *, attempts, output_dir, experiment_type, provider, model,
            integrity_reader, input_loader, stress_cases=(), policy=POLICY,
            controlled_mode=None, controlled_case=None, controlled_case_sha256=None):
    fixed_case = require_context(controlled_mode=controlled_mode, controlled_case=controlled_case,
                                 controlled_case_sha256=controlled_case_sha256, policy=policy)
    controlled = dict(controlled_mode=controlled_mode, controlled_case=fixed_case,
                      controlled_case_sha256=controlled_case_sha256)
    if fixed_case is not None and stress_cases:
        raise ValueError('Controlled input runs cannot mix adversarial case identities')
    require_policy(policy)
    if type(attempts) is not int or not 1<=attempts<=20:raise ValueError('Attempt count must be 1..20')
    if experiment_type not in ('live_normal','offline_synthetic','live_adversarial','offline_synthetic_stress'):raise ValueError('Unknown experiment type')
    if bool(stress_cases)!=experiment_type.endswith(('stress','adversarial')):raise ValueError('Separate normal and stress runs')
    if stress_cases and len(stress_cases)!=attempts:raise ValueError('One independent attempt per stress case')
    if contains_secret(model):raise ValueError('Invalid model identifier')
    brief=compile_brief(inputs, policy=policy, **controlled);brief_hash=digest(brief);binding=current_binding(inputs)
    before=integrity_reader()
    if before.get('freeze_inventory_matches') is False:raise ValueError('Engineering baseline already differs; no API call started')
    directory=Path(output_dir)/('run-'+uuid4().hex)
    directory.mkdir(parents=True,exist_ok=False)
    run_id=directory.name
    manifest={'format':'qualification-run/1','run_id':run_id,'experiment_type':experiment_type,
        'requested_attempt_count':attempts,'provider':provider,'model':model,'created_at':now(),
        'slot':{'topic':'standard-deviation','profile':'standard-lesson','role':ROLE},
        'authoring_brief':{'ref':brief.identity,'sha256':brief_hash},'baseline_before':before,
        'candidate_contract_version':'ai-author-candidate/2', 'expression_verifier':'sl10-expression/1',
        'acceptance_policy':policy, 'provenance_verifier':VERSION,
        'configuration':{'attempt_limit':20,'retry_policy':'none','repair_policy':'none','settings_source':'Observed per attempt from actual adapter arguments'},
        'stress_cases':[{'case_id':x['case_id'],'expected_guardrail':x['expected_guardrail']} for x in stress_cases]}
    if fixed_case is not None:
        manifest.update(controlled, controlled_case=fixed_case.model_dump(mode='json'))
    write_new(directory/'run.json',manifest)
    write_new(directory/'brief.json',brief)
    completed=0;reason='All requested independent attempts completed.';status='incomplete'
    current=inputs
    try:
        for number in range(1,attempts+1):
            # Fresh current trust read BEFORE every provider construction/call,
            # in addition to the existing post-call refresh used by validation.
            try:
                current=input_loader()
                current_brief=compile_brief(current, policy=policy, **controlled)
            except Exception:
                reason='Current trusted-input preflight failed; no provider call for this attempt.';break
            if digest(current_brief)!=brief_hash or current_binding(current)!=binding:
                reason='Current trusted/product inputs changed; remaining calls not made.';break
            folder=directory/f'attempt-{number:02d}'
            folder.mkdir(exist_ok=False)
            started=now()
            case=stress_cases[number-1] if stress_cases else None
            write_new(folder/'started.json',{'attempt_id':folder.name,'started_at':started,'brief_hash':brief_hash,
                'case_id':case['case_id'] if case else None})
            author=author_factory(case)
            probe=Probe(author)
            refreshed=[]
            def refresh():
                value=input_loader();refreshed.append(value);return value
            audit=run_once(current,probe,refresh=refresh,policy=policy, **controlled)
            if refreshed:current=refreshed[0]
            try:inputs_changed=bool(refreshed and current_binding(current)!=binding)
            except (ValueError,TypeError,AttributeError):inputs_changed=True
            observation=getattr(author,'last',{})
            if observation.get('application_mutation'):
                audit['raw_response_label']='UNTRUSTED STRESS CANDIDATE; see separately preserved original model response'
            audit_path=save(audit,folder)
            write_new(folder/'brief.json',brief)
            write_new(folder/'validation.json',audit['validation'])
            original=observation.get('original_model_response',audit['raw_response'])
            if contains_secret(serial(original)):original='[WITHHELD: secret-like output]'
            write_new(folder/'raw_candidate.json',{'label':'UNTRUSTED MODEL OUTPUT' if experiment_type.startswith('live_') else 'UNTRUSTED SYNTHETIC TEST OUTPUT',
                'raw_response':original,'recoverable':bool(original)})
            safe_observation={k:v for k,v in observation.items() if k!='original_model_response'}
            if contains_secret(serial(safe_observation)):safe_observation={'withheld':'secret-like observation'}
            write_new(folder/'provider_observation.json',safe_observation)
            outcome='input_validation_failure' if inputs_changed else classify(audit,probe)
            validation=audit['validation']
            statuses=validation.get('verification_summary',{}).get('stage_status',{})
            checks={k:None if statuses.get(k)=='NOT_EVALUATED' else validation.get(k) for k in CHECKS}
            numeric_status=statuses.get('numeric_encoding','NOT_EVALUATED')
            checks['numeric_encoding_valid']=None if numeric_status=='NOT_EVALUATED' else numeric_status=='PASSED'
            violations=validation['violations']
            if outcome in ('provider_failure','input_validation_failure'):
                checks={k:None for k in CHECKS};violations=[]
            elif outcome=='candidate_schema_failure':
                checks={k:False if k=='schema_valid' else None for k in CHECKS};violations=list(validation['violations'])
                if audit['provider_error_code'] in ('secret_output_rejected','response_size_limit'):
                    violations.append(audit['provider_error_code'])
            metadata=audit['model_metadata'] or {}
            forbidden=(True if experiment_type=='offline_synthetic_stress' else forbidden_observed(case['case_id'],audit['raw_response'])) if case else None
            blocked=(forbidden and not validation['accepted'] and validation.get(case['expected_guardrail']) is False
                and outcome in ('candidate_schema_failure','candidate_validation_rejected')) if case else None
            names=[audit_path.name,'brief.json','validation.json','raw_candidate.json','provider_observation.json','started.json']
            extra = {}
            if fixed_case is not None:
                evaluated = outcome not in ('provider_failure','input_validation_failure','candidate_schema_failure')
                extra = dict(controlled,
                    returned_inputs=audit['candidate']['content']['proposed_math_inputs'] if audit['candidate'] else None,
                    controlled_input_binding_valid=validation['controlled_input_binding_valid'] if evaluated else None,
                    controlled_input_binding_status=validation['controlled_input_binding_status'] if evaluated else 'NOT_EVALUATED',
                    controlled_input_binding_reason=validation['controlled_input_binding_reason'] if evaluated else 'controlled_input_not_evaluated')
            record_type = ControlledAttempt if fixed_case is not None else Attempt
            record=record_type(**extra, attempt_id=folder.name,candidate_id=audit['candidate_id'],brief_ref=brief.identity,brief_hash=brief_hash,
                model_identifier=safe_observation.get('reported_model') or metadata.get('model',model),started_at=started,completed_at=now(),
                latency_ms=metadata['latency_seconds']*1000 if 'latency_seconds' in metadata else None,
                provider_request_id=safe_observation.get('provider_request_id'),provider_calls=safe_observation.get('call_count',0),
                provider_call_completed=(safe_observation.get('call_count',0)==1 and probe.returned and not probe.error_code),outcome=outcome,
                operational_error='current_inputs_changed' if inputs_changed else (safe_observation.get('error_code') or (audit['provider_error_code'] if outcome in ('provider_failure','input_validation_failure') else None)),
                derivation_provenance_status=(validation.get('derivation_provenance_status','NOT_EVALUATED') if outcome not in ('provider_failure','input_validation_failure','candidate_schema_failure') else 'NOT_EVALUATED'),
                acceptance_policy=policy, **checks,accepted=validation['accepted'],violations=tuple(violations),warnings=tuple(validation['warnings']),
                usage={k:metadata.get(k) for k in ('input_tokens','output_tokens','total_tokens')},
                candidate_artifact_ref=audit_path.name,artifact_hashes={n:file_hash(folder/n) for n in names},
                observed_configuration=safe_observation.get('configuration',{}),case_id=case['case_id'] if case else None,
                expected_guardrail=case['expected_guardrail'] if case else None,blocked=blocked,forbidden_behavior_observed=forbidden)
            write_new(folder/'attempt.json',record)
            completed+=1
            if outcome=='input_validation_failure':reason='Current input refresh failed; remaining calls not made.';break
        if completed==attempts:status='complete'
    except KeyboardInterrupt:
        reason='Interrupted; completed attempts preserved. No automatic resume.'
    except Exception:
        reason='Run stopped by an operational or artifact failure; inspect completed records. No retry.'
    finally:
        try:after=integrity_reader()
        except Exception:after={'error':'integrity_unavailable'}
        if after!=before:
            status='incomplete';reason='Baseline integrity changed or became unavailable.'
        write_new(directory/'completion.json',{'status':status,'reason':reason,'completed_attempt_count':completed,'baseline_after':after})
    report,path=rebuild(directory)
    return report,path
