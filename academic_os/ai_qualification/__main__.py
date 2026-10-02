"""Explicit opt-in qualification CLI. No credentials are needed for dry-run or stress fixtures."""
import argparse
from ..ai_authoring.provenance import POLICY
from ..ai_authoring.controlled import CATALOG, context
import json
import os
from pathlib import Path
from ..ai_authoring.brief import ROLE, compile_brief, digest, serial
from ..ai_authoring.service import read_inputs, contains_secret
from .integrity import capture
from .reporting import rebuild
from .runner import execute
from .stress import LIVE_SCENARIOS, cases, SyntheticStressAuthor

ROOT=Path(__file__).resolve().parents[2]


def emit(value):
    # Portable JSON for Windows consoles/pipes; escaped Unicode decodes identically.
    print(json.dumps(value,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=ROOT/'var'/'p0_q2.sqlite3')
    commands=parser.add_subparsers(dest='command',required=True)
    for command in ('qualify-ai-author','stress-ai-author'):
        p=commands.add_parser(command)
        p.add_argument('topic',choices=['standard-deviation'])
        p.add_argument('--profile',choices=['standard-lesson'],required=True)
        p.add_argument('--role',choices=[ROLE],required=True)
        p.add_argument('--output-dir',type=Path,default=ROOT/'output'/'p6a2_live_qualification')
        modes=p.add_mutually_exclusive_group(required=True)
        modes.add_argument('--live',action='store_true',help='Explicitly allow paid API calls; never retries')
        modes.add_argument('--dry-run',action='store_true',help='Inspect plan and exact normal brief without a provider')
        if command=='qualify-ai-author':
            p.add_argument('--attempts',type=int,default=10,help='Independent attempts, 1..20; default 10')
            p.add_argument('--controlled-case',choices=tuple(CATALOG),help='Application-owned fixed case; one case and one brief per run')
        else:
            modes.add_argument('--offline',action='store_true',help='Run all 16 synthetic guardrail cases without a model')
            p.add_argument('--case',action='append',choices=list(LIVE_SCENARIOS),dest='case_ids')
    p=commands.add_parser('rebuild-report');p.add_argument('run_directory',type=Path)
    args=parser.parse_args(argv)
    if args.command=='qualify-ai-author' and not 1<=args.attempts<=20:parser.error('--attempts must be 1..20; maximum is 20')
    if args.command=='stress-ai-author' and args.case_ids and len(set(args.case_ids))!=len(args.case_ids):parser.error('Duplicate stress cases are not allowed')
    try:
        if args.command=='rebuild-report':
            report,path=rebuild(args.run_directory)
            emit({'report':str(path),'status':report.status,'completed_attempts':report.attempt_count})
            return 0
        controlled=context(CATALOG[args.controlled_case]) if getattr(args,'controlled_case',None) else {}
        inputs=read_inputs(args.db)
        brief=compile_brief(inputs, policy=POLICY, **controlled)
        stress=[]
        if args.command=='stress-ai-author':
            if getattr(args,'offline',False):
                if args.case_ids:parser.error('--case selects live adversarial cases; --offline runs the synthetic catalog')
                stress=[dict(case_id=k,**v) for k,v in cases().items()]
            else:
                stress=[{'case_id':k,'expected_guardrail':'solution_valid' if k=='wrong_math' else 'boundary_valid'} for k in (args.case_ids or list(LIVE_SCENARIOS))]
        count=len(stress) if stress else args.attempts
        # Engineering conformance is separate from the live academic input gates.
        # Check before constructing a provider, also in dry-run mode.
        engineering = capture(args.db, ROOT)
        if not engineering['freeze_inventory_matches']:
            raise ValueError('Active engineering baseline mismatch')
        from ..ai_authoring.provider import configured_model
        from .preflight import describe
        model = configured_model() if args.live or args.dry_run else 'synthetic-no-model'
        plan = describe(args, brief, engineering, model, stress)
        if args.dry_run:
            emit(plan)
            return 0
        provider=None
        try:
            if args.live:
                from ..ai_authoring.provider import OpenAICandidateAuthor
                from .observer import ObservedAuthor, safe_identifier
                provider=OpenAICandidateAuthor.from_environment()
                if provider.model != model: raise ValueError('Model configuration changed after preflight')
                if safe_identifier(provider.model) is None:raise ValueError('Invalid model identifier')
                # Printed before any author call, with no credential or client repr.
                print(f'LIVE API CALLS WILL OCCUR: {count} independent attempts; model={provider.model}; no retry or repair.',flush=True)
                factory=lambda case:ObservedAuthor(provider,case['case_id'] if case else None)
                experiment='live_adversarial' if stress else 'live_normal'
                provider_name='openai';model=provider.model
            else:
                factory=lambda case:SyntheticStressAuthor(case)
                experiment='offline_synthetic_stress';provider_name='offline_synthetic';model='synthetic-no-model'
            report,path=execute(inputs,factory,attempts=count,output_dir=args.output_dir,experiment_type=experiment,
                provider=provider_name,model=model,integrity_reader=lambda:capture(args.db,ROOT),
                input_loader=(lambda:read_inputs(args.db)) if args.live else (lambda:inputs),stress_cases=stress, policy=POLICY, **controlled)
            emit({'report':str(path),'status':report.status,'completed_attempts':report.attempt_count,
                'outcomes':report.operational_outcomes,'stress':report.stress_summary,'model_qualified':None})
            return 0 if report.status=='complete' and report.stress_summary['unexpectedly_accepted']==0 else 2
        finally:
            if provider is not None:provider.client.close()
    except Exception:
        print('Qualification failed closed. Inspect saved partial runs, model configuration and source gates. No automatic retry. Sensitive exception details withheld.')
        return 2


if __name__=='__main__':raise SystemExit(main())
