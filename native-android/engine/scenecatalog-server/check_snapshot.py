#!/usr/bin/env python3
"""Qualify the new source sidecar, paired sink and deployment refusal controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import snapshot_oracle as oracle

HERE=Path(__file__).resolve().parent
FILES=('source_snapshot.inc','source_snapshot_sink.inc','snapshot_oracle.py','test_snapshot.c',
    'test_snapshot_sink.c','test_snapshot_controls.py','stage_snapshot.py','record_snapshot_compile.py',
    'admit_snapshot.py','capture_snapshot.py','check_snapshot.py','stage_export.py','source_sink.inc','capture_disposable.py','delivery.py')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixtures-output',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
    if a.output.exists():raise ValueError('New output required')
    root=a.source_root.resolve()
    paths={n:HERE/n for n in FILES}
    paths['catalog/source_export.inc']=HERE.parent/'scenecatalog/source_export.inc'
    for name in ('native-android/engine/replication/groups_oracle.py','native-android/engine/replication/groups-source-pins.json',
        'native-android/engine/replication/tests/groups_oracle_shim.h','native-android/engine/replication/tests/groups_oracle_harness.c',
        'native-android/tools/protocol_fixture/prepare.py'):
        paths['dependency/'+name]=root/name
    pins={n:hashlib.sha256(path.read_bytes()).hexdigest() for n,path in paths.items()}
    source_revision=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    def original_pins():
        expected=json.loads((root/'native-android/engine/replication/groups-source-pins.json').read_bytes())['sha256_lf']
        names=[*expected,'Common/group/group.h']
        values={}
        for name in names:
            path=root/'upstream/ouroboros'/name
            raw=path.read_bytes() if path.is_file() else subprocess.check_output(['git','-C',str(root),'show','HEAD:upstream/ouroboros/'+name])
            values[name]=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()
        return values
    original_before=original_pins()
    outcome=oracle.run(['python3',HERE/'test_snapshot_controls.py'])
    count=int(re.search(r'Ran ([0-9]+) tests',outcome.stderr)[1])
    modes=[('release',['-O0'])]
    if a.sanitize:modes += [('asan',['-O0','-g','-fsanitize=address','-no-pie']),('ubsan',['-O0','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
    results=[]
    with tempfile.TemporaryDirectory(prefix='coh-runtime-snapshot-source-') as tmp:
        tmp=Path(tmp);src,original=oracle.prepare(a.source_root.resolve(),tmp)
        for name,flags in modes:
            exe=tmp/('producer-'+name);sink=tmp/('sink-'+name)
            oracle.run(['cc','-std=c99','-fno-strict-aliasing','-w',*flags,'-I'+str(HERE),'-I'+str(a.source_root/'native-android/include'),src,'-lm','-lz','-o',exe])
            env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'}
            producer=json.loads(oracle.run([exe,tmp],env=env).stdout)
            oracle.run(['cc','-std=c89','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(HERE),HERE/'test_snapshot_sink.c','-o',sink])
            sink_result=json.loads(oracle.run([sink],env=env).stdout)
            results.append({'mode':name,'producer':producer,'sink':sink_result})
        fixtures={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in tmp.iterdir() if p.suffix in ('.cohcat','.cohrts') or p.name=='fixture-expected.json'}
        if a.fixtures_output:
            a.fixtures_output.mkdir(parents=True,exist_ok=True)
            for name in fixtures:
                with (tmp/name).open('rb') as src,(a.fixtures_output/name).open('xb') as dst:shutil.copyfileobj(src,dst)
    if any(hashlib.sha256(paths[n].read_bytes()).hexdigest()!=sha for n,sha in pins.items()) or original_pins()!=original_before or subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()!=source_revision:
        raise ValueError('Source changed during tests')
    result={'schema':'coh-runtime-snapshot-host-v1','passed':True,'source_sha256':pins,'original_source':original,
        'source_revision':source_revision,'original_sha256_lf':original_before,'source_unchanged_before_after':True,
        'control_tests':count,'modes':results,'fixtures':fixtures,'runtime_executed':False,'live_groups_transaction':False,
        'source_snapshot_only':True,'accepted_apks_rebuilt':False,'leak_sanitizer':False,
        'maximum_sidecar_bytes':16*1024**2,'maximum_external_objects':64,'hard_process_memory_cap_established':False}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'passed':True,'controls':count,'modes':results,'runtime_executed':False}))
if __name__=='__main__':main()
