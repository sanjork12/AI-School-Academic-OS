"""Legacy CLI backed by reusable structured validation; no import-time IO."""
from pathlib import Path
import json
from academic_os.curriculum_ingestion.validation import validate_curriculum, EXPECTED

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--tier',required=True,choices=['foundation','higher']);p.add_argument('--input',type=Path)
    args=p.parse_args(argv);path=args.input or Path(f'output/topic2_{args.tier}_parsed.json')
    try:result=validate_curriculum(json.loads(path.read_text(encoding='utf-8')),args.tier)
    except (OSError,ValueError):print('FAIL: Unable to read curriculum JSON.');return 1
    print('STRUCTURE VALIDATION PASSED' if result['structure_valid'] else 'VALIDATION FAILED')
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['structure_valid'] else 1

if __name__=='__main__':raise SystemExit(main())
