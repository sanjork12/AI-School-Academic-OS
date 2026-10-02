"""Capture exact unittest results without changing any existing test policy."""
import json
from pathlib import Path
import sys
import unittest

mode=sys.argv[1]
suite=unittest.defaultTestLoader.discover('.') if mode=='full' else unittest.defaultTestLoader.loadTestsFromName('tests_p0.test_reference_freeze')
out=Path('output/reference_freeze')
with (out/(mode+'-tests.txt')).open('x',encoding='utf-8') as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
data=dict(total=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped)-len(result.expectedFailures)-len(result.unexpectedSuccesses),
    failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses),
    successful=result.wasSuccessful(),error_details=[dict(test=str(t),traceback=s) for t,s in result.errors],
    failure_details=[dict(test=str(t),traceback=s) for t,s in result.failures],log=str(out/(mode+'-tests.txt')))
with (out/(mode+'-results.json')).open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2)
print(json.dumps(data,indent=2));sys.exit(0 if result.wasSuccessful() else 1)
