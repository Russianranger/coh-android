#!/usr/bin/env python3
"""Independent host-only admission review; synthetic executor never runs Android."""
import argparse,contextlib,hashlib,importlib,io,json,subprocess,sys,tempfile
from pathlib import Path

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('New receipt path required')
    repo=args.source_root.resolve();entities=repo/'native-android/engine/entities';sys.path.insert(0,str(entities))
    fixture_module=importlib.import_module('test_run_wire_android');runner=fixture_module.runner
    paths=set().union(*(runner.required_sources(module)[0] for module in runner.MODULES))
    pins={name:sha(repo/name) for name in paths};revision=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if revision!='d9266213d8b95d15ab32008474f53cdfe36c1db1':raise ValueError('Pinned reviewed commit required')
    source_state=runner.c.git_state(repo)
    if source_state['source_git_status_porcelain']:raise ValueError('Clean review checkout required')
    run=subprocess.run([sys.executable,str(entities/'test_run_wire_android.py')],check=True,capture_output=True,text=True,timeout=180)
    original_controls=runner.c.loads(run.stdout);assert original_controls['passed'] and original_controls['test_methods']==9
    checks=[]
    def refused(call,label):
        try:call()
        except (ValueError,OSError):checks.append(label)
        else:raise AssertionError('Accepted '+label)
    def fixture(tmp,module):return fixture_module.Artifacts(Path(tmp),module)
    for module in runner.MODULES:
        for abi in runner.c.ABIS:
            with tempfile.TemporaryDirectory() as tmp:
                f=fixture(tmp,module);p=f.proof['android'][abi];binary=f.artifacts/'android'/abi/p['binary'];raw=bytearray(binary.read_bytes());raw[4]=1;binary.write_bytes(raw);p['binary_sha256']=sha(binary);f.write()
                refused(lambda:runner.validate(f.artifacts,f.proof,module),module+'/'+abi+'/wrong-ELF-class-despite-repin')
        for dep in (runner.RUNNER_PATH,runner.ADAPTER_PATH,runner.COMMON_PATH):
            with tempfile.TemporaryDirectory() as tmp:
                f=fixture(tmp,module);del f.sources[dep];f.write()
                refused(lambda:runner.validate(f.artifacts,f.proof,module),module+'/missing-dependency/'+dep)
        with tempfile.TemporaryDirectory() as tmp:
            f=fixture(tmp,module);p=f.root/'prior-evidence';p.mkdir();marker=p/'keep.txt';marker.write_text('prior evidence preserved');fake=fixture_module.FakeADB(f,'normal')
            with contextlib.redirect_stderr(io.StringIO()):
                try:runner.main(['--module',module,'--source-root',str(f.repo),'--adb','/synthetic/adb','--serial','fixture','--artifacts',str(f.artifacts),'--output',str(p/'new.json')],executor=fake)
                except SystemExit as error:assert error.code==2
                else:raise AssertionError('Reused occupied evidence directory')
            assert marker.read_text()=='prior evidence preserved' and list(p.iterdir())==[marker] and not fake.commands;checks.append(module+'/prior-evidence-untouched')
        with tempfile.TemporaryDirectory() as tmp:
            f=fixture(tmp,module);f.proof['source_tree']='0'*40
            refused(lambda:runner.validate_checkout(f.repo,f.proof,module),module+'/wrong-source-tree')
        scope=runner.MODULES[module]['scope']
        for key,value in [('fixtures',True),('checks',True),(scope,True),('extra',False)]:
            native={'fixtures':1,'checks':1,scope:False};native[key]=value
            refused(lambda:runner.native_result(native,module),module+'/strict-native/'+key)
    for text in ('{"checks":1,"checks":2}','{"checks":NaN}','{"checks":1e999}'):
        refused(lambda:runner.c.loads(text),'strict-JSON/'+text)
    if pins!={name:sha(repo/name) for name in paths} or source_state!=runner.c.git_state(repo):raise ValueError('Source changed during independent review')
    result={'schema':'coh-independent-wire-runner-review-v1','passed':True,'reviewed_commit':revision,'source_sha256':pins,'source_stable':True,'existing_control_suite':original_controls,'additional_checks':checks,'review_driver_sha256':sha(Path(__file__)),'synthetic_executor_only':True,'android_executed':False,'emulator_qualified':False,'native_binary_executed':False,'actor_publication':False,'acknowledgments_enabled':False}
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'additional_checks':len(checks),'android_executed':False}))
if __name__=='__main__':main()
