"""TEST ONLY: exercise review/publication exclusively in a fresh temporary DB.

There is deliberately no --db option. The real operator database is never opened.
"""
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests_p0.bundle_fixtures import seed,scenario


def main():
    with tempfile.TemporaryDirectory(prefix='academic-p1b-TEST-ONLY-') as directory:
        store,service=seed(directory)
        try:
            report=scenario(service)
            assert report['after_core_academic_approval']['publishable']
            assert report['optional_candidate_status']=='pending'
            assert report['optional_candidates_excluded'] and report['snapshot_usable']
        finally:store.close()
    output=ROOT/'output/p1b_review/temporary-publication-test.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('TEST ONLY: verified sources -> core academic approval -> trusted snapshot succeeded.')
    print('Optional secondary stayed pending and was excluded. Real operator DB was never opened.')
    print(output)


if __name__=='__main__':main()
