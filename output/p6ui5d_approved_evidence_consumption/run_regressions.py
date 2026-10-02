import sys,json,unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()));sys.path.append('tmp/p6ui-deps')
out=Path('output/p6ui5d_approved_evidence_consumption')
modules=['tests_p0.test_approved_pedagogical_consumption']
for name in ('backend-tests','upstream-tests'):
 modules+=json.loads(Path('output/p6ui5a_pedagogical_evidence',name+'.json').read_text(encoding='utf-8'))['modules']
with (out/'backend-tests.txt').open('x',encoding='utf-8') as stream:
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
data=dict(total=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),successful=result.wasSuccessful(),modules=modules,model_calls=0)
(out/'backend-tests.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(data,indent=2))

sys.exit(0 if result.wasSuccessful() else 1)
