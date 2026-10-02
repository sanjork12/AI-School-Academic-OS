"""TEST ONLY source-ticket workflow; never opens the real operator database."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests_p0.bundle_fixtures import seed, approve_core
from academic_os.source_bundles import SOURCE_BUNDLES


def main():
    with tempfile.TemporaryDirectory(prefix='academic-p1b1-TEST-ONLY-') as directory:
        store, service = seed(directory)
        try:
            def status():
                r = service.check_target('Q2-CORE')
                return {k: r[k] for k in ('source_verified', 'human_approved', 'publishable')}

            def cli(*args):
                result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'academic_os',
                    '--db', str(store.path), *args], cwd=ROOT,
                    capture_output=True, text=True, encoding='utf-8', check=True)
                return json.loads(result.stdout)

            report = dict(notice='TEST ONLY copied PDFs and temporary database; no real decisions',
                          before=status(), source_decisions=[])
            for bid in SOURCE_BUNDLES:
                ticket = str(Path(directory)/(bid+'.ticket'))
                view = cli('review-source', bid, '--save-ticket', ticket, '--json')
                receipt = cli('decide-source', bid, 'verify', '--ticket', ticket,
                    '--reason', 'TEST ONLY isolated copied corpus, not a real verification',
                    '--request-id', 'TEST-DEMO-'+bid)
                assert service.review_source(bid)['source_verified']
                report['source_decisions'].append(dict(bundle_id=bid,
                    ticket=view['review_ticket'], receipt=receipt))
            report['after_sources'] = status()
            assert report['after_sources'] == dict(source_verified=True, human_approved=False, publishable=False)
            approve_core(service)
            report['after_academic'] = status()
            report['publication'] = service.publish_target('Q2-CORE')
            snapshot = service.snapshot(report['publication']['snapshot_id'])
            report['snapshot_usable'] = snapshot['usable']
            report['optional_candidate_state'] = service.inspect('part_mapping:MAP-Q2-c-CONTEXT-INFER')['state']
            assert snapshot['usable'] and report['optional_candidate_state'] == 'pending'
        finally:
            store.close()
    output = ROOT/'output/p1b1_source_review/temporary-demo.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('TEST ONLY: source tickets -> explicit verification -> academic review -> trusted snapshot passed.')
    print('Real operator database was never opened. Report:', output)


if __name__ == '__main__':
    main()
