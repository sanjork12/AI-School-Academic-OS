"""Exercise the public CLI with real sources, without submitting any reviews."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='var/p0_q2.sqlite3')
    parser.add_argument('--report-dir', default='output/p0_acceptance')
    args = parser.parse_args()
    report_dir = ROOT / args.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    steps = [
        ('init', ['init'], 0),
        ('registration', ['import-q2', '--request-id', 'import-real-q2-v1'], 0),
        ('q2_evidence', ['inspect', 'part_mapping:MAP-Q2-c-VARIATION-INTERPRET'], 0),
        ('publication_check', ['check'], 2),
    ]
    for name, arguments, expected_exit in steps:
        run = subprocess.run(
            [sys.executable, '-X', 'utf8', '-m', 'academic_os', '--db', args.db, *arguments],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
        )
        if run.returncode != expected_exit:
            raise RuntimeError(f'{name}: expected exit {expected_exit}, got {run.returncode}\n{run.stdout}\n{run.stderr}')
        result = json.loads(run.stdout)
        (report_dir / (name + '.json')).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
        )
        print(f'{name}: expected exit {expected_exit} confirmed')
    print('Real Q2 remains blocked. No human review was submitted by this demo.')


if __name__ == '__main__':
    main()
