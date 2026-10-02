"""Compatibility helper; importing never rewrites historical files."""
import json
from pathlib import Path
from academic_os.curriculum_ingestion.core import assign_source_ids

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args(argv)
    result=assign_source_ids(json.loads(args.input.read_text(encoding='utf-8')))
    with args.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    return 0

if __name__=='__main__':raise SystemExit(main())
