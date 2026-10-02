"""Explicit live legacy CLI; the ingestion HTTP API supplies immutable run contexts."""
from pathlib import Path
import json
from academic_os.curriculum_ingestion.core import PROFILE, parse_curriculum, model_configuration, live_parse, IngestionError
from academic_os.curriculum_ingestion.validation import validate_curriculum

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--tier',required=True,choices=['foundation','higher']);p.add_argument('--input',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--live',action='store_true')
    args=p.parse_args(argv)
    if not args.live:p.error('Explicit --live is required for paid model parsing.')
    if args.output.exists():p.error('Choose a new output file; historical artifacts cannot be overwritten.')
    try:
        config=model_configuration();text=(args.input or Path(f'output/topic2_{args.tier}_raw.txt')).read_text(encoding='utf-8')
        result=parse_curriculum(text,args.tier,PROFILE,lambda text,tier:live_parse(text,tier,config))
        report=validate_curriculum(result,args.tier)
        with args.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
        print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['structure_valid'] else 1
    except IngestionError as e:print(e.code+': '+e.message);return 1

if __name__=='__main__':raise SystemExit(main())
