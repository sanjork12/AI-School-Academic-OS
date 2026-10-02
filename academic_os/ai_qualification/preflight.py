"""Describe a gated qualification plan, without constructing a provider."""
from ..ai_authoring.brief import ROLE, digest
from ..ai_authoring.models import Candidate
from ..ai_authoring.provenance import POLICY, LEGACY_POLICY, VERSION
from .reference_baseline import ACTIVE_REFERENCE_BASELINE


def describe(args, brief, engineering, model, stress):
    """Called only after current trusted read, compile_brief/P5C and capture."""
    baseline=engineering['engineering_baseline']
    version=Candidate.model_fields['schema_version'].default
    if (not engineering['freeze_inventory_matches'] or not baseline['valid']
        or baseline['reference_version']!=ACTIVE_REFERENCE_BASELINE
        or version!='ai-author-candidate/2' or brief.schema_version not in ('authoring-brief/2','authoring-brief/3','authoring-brief/4')):
        raise ValueError('Preflight contract/baseline mismatch')
    if args.command=='qualify-ai-author' and model!='gpt-5.6-sol':
        raise ValueError('Configured model differs from the requested experiment continuity')
    return dict(preflight_status='passed',attempt_count=len(stress) if stress else args.attempts,
        model=model,provider='openai' if model!='synthetic-no-model' else 'offline_synthetic',
        acceptance_policy=POLICY if brief.schema_version in ('authoring-brief/3','authoring-brief/4') else LEGACY_POLICY,
        provenance_verifier=VERSION,derivation_provenance_verified=False,
        provenance_verification_required=brief.schema_version in ('authoring-brief/3','authoring-brief/4'),
        candidate_contract_version=version,engineering_baseline_version=ACTIVE_REFERENCE_BASELINE,
        engineering_baseline=baseline,brief_hash=digest(brief),brief=brief.model_dump(mode='json'),
        topic=args.topic,profile=args.profile,role=args.role,slot=ROLE,
        output_location=str(args.output_dir),live_api_will_be_called=False,
        stress_cases=stress,stress_attempted=0,retry_policy='none',repair_policy='none',
        model_qualified=None,expression_semantics_verified=False,expression_verification_required=True,renderer_readiness=False,
        gates={'current_trusted_input_read':'passed','authoring_brief_and_p5c':'passed','engineering_conformance':'passed'},
        configuration_note='Model resolved through the same environment/dotenv function as the live adapter. No credential validation or provider request was performed.',
        baseline_note='The active engineering revision is explicitly selected; earlier baseline evidence remains immutable.')
