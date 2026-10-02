"""Explicit P6A CLI kept separate from the frozen pre-AI command dispatcher."""
import argparse
from .provenance import POLICY
from pathlib import Path
from .brief import ROLE, compile_brief, serial
from .service import read_inputs, run_once, save


def main(argv=None):
    parser = argparse.ArgumentParser(description='P6A: one untrusted SL-10 candidate; --live makes one paid API attempt.')
    parser.add_argument('--db', type=Path, default=Path('var/p0_q2.sqlite3'))
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('ai-author-slot')
    p.add_argument('topic', choices=['standard-deviation'])
    p.add_argument('--profile', choices=['standard-lesson'], required=True)
    p.add_argument('--role', choices=[ROLE], required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--show-brief', action='store_true')
    mode.add_argument('--live', action='store_true', help='Explicitly permit one paid generation attempt (no retry)')
    p.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.live and args.output_dir is None: parser.error('--live requires --output-dir for the audit record')
    try:
        inputs = read_inputs(args.db)
        if args.show_brief:
            print(serial(compile_brief(inputs, policy=POLICY)))
            return 0
        from .provider import OpenAICandidateAuthor
        author = OpenAICandidateAuthor.from_environment()
        try:
            audit = run_once(inputs, author, refresh=lambda: read_inputs(args.db), policy=POLICY)
        finally:
            author.client.close()
        path = save(audit, args.output_dir)
        print(serial({'status': 'ACCEPTED_CANDIDATE' if audit['validation']['accepted'] else 'REJECTED',
            'audit': str(path), 'violations': audit['validation']['violations'], 'provider_error_code': audit['provider_error_code']}))
        return 0 if audit['validation']['accepted'] else 2
    except Exception:
        # Avoid SDK exception/header/configuration leakage to terminal/logs.
        print('P6A failed closed. Check current source gates, explicit model configuration, credentials and output permissions. No automatic retry.')
        return 2


if __name__ == '__main__': raise SystemExit(main())
