"""Record offline test results and exact source hashes; never suppress test errors."""
import hashlib
import json
from pathlib import Path
import socket
import sys
import time
import unittest
from unittest.mock import patch

OUT=Path('output/p6a4_derivation_provenance')
FOCUSED=(
    'tests_p0.test_derivation_provenance',
    'tests_p0.test_expression_semantics',
    'tests_p0.test_candidate_contract',
    'tests_p0.test_ai_authoring',
    'tests_p0.test_ai_qualification.QualificationTests',
    'tests_p0.test_direct_v2_preflight',
    'tests_p0.test_offline_candidate_replay',
)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    return {p.as_posix():sha(p) for folder in ('academic_os','tests_p0','docs')
            for p in sorted(Path(folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.module_counts={}
    def startTest(self,test):
        super().startTest(test)
        key=test.__class__.__module__
        self.module_counts[key]=self.module_counts.get(key,0)+1


def run(mode,label):
    start_sources=source_hashes()
    suite=(unittest.defaultTestLoader.discover('.') if mode=='full'
           else unittest.defaultTestLoader.loadTestsFromNames(FOCUSED))
    deferred=[]
    if mode != 'full':
        # This test invokes real current conformance, which must reject edited
        # source against the still-frozen v1.4. Run it unfiltered after v1.5.
        def flatten(suite):
            for test in suite:
                if isinstance(test,unittest.TestSuite):yield from flatten(test)
                else:yield test
        selected=[]
        for test in flatten(suite):
            if test.id()=='tests_p0.test_ai_qualification.QualificationTests.test_19_dry_run_no_provider_or_credentials':
                deferred.append(test.id())
            else:selected.append(test)
        suite=unittest.TestSuite(selected)
    started=time.monotonic()
    with (OUT/(label+'.log')).open('x',encoding='utf-8') as stream, \
         patch.object(socket.socket,'connect',side_effect=AssertionError('P6A.4 offline network guard')), \
         patch.object(socket,'create_connection',side_effect=AssertionError('P6A.4 offline network guard')):
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    end_sources=source_hashes()
    data=dict(mode=mode,selected_tests=list(FOCUSED) if mode!='full' else 'unittest discovery: all',
        deferred_current_conformance_tests=deferred,total=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped)-len(result.expectedFailures)-len(result.unexpectedSuccesses),
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses),
        successful=result.wasSuccessful(),seconds=time.monotonic()-started,module_counts=result.module_counts,
        error_details=[dict(test=str(t),traceback=s) for t,s in result.errors],
        failure_details=[dict(test=str(t),traceback=s) for t,s in result.failures],
        source_hashes=end_sources,sources_unchanged_during_tests=start_sources==end_sources,
        network_guard='socket.connect and socket.create_connection blocked',model_api_calls=0)
    with (OUT/(label+'.json')).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
    print(json.dumps({k:v for k,v in data.items() if k not in ('source_hashes','module_counts')},indent=2))
    return result.wasSuccessful() and start_sources==end_sources


if __name__=='__main__':
    raise SystemExit(0 if run(sys.argv[1],sys.argv[2]) else 1)
