#!/usr/bin/env python3
"""Qualify immutable retained source imports using the exact captured archive."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile
HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent
CAPTURE_SHA='8763048abd0d55070159955f02ae9d72e452aa44d1da6e6603a22637732d764d'

def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture-zip',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    if a.output.exists():raise ValueError('New output required')
    archive=a.capture_zip.read_bytes()
    if sha(archive)!=CAPTURE_SHA:raise ValueError('Capture archive identity differs')
    sources=[HERE/'tests/test_catalog_snapshot.c',HERE/'coh_catalog_snapshot.c',HERE/'coh_catalog_owner.c',HERE/'coh_scenecatalog.c',ENGINE/'scenegraph/runtime_snapshot.c',ENGINE/'scenegraph/tests/runtime_matrix_bridge.c',ENGINE/'replication/coh_replication.c',ENGINE/'replication/coh_groups.c']
    headers=[HERE/'coh_catalog_snapshot.h',HERE/'coh_catalog_owner.h',HERE/'coh_scenecatalog.h',ENGINE/'scenegraph/runtime_snapshot.h',ENGINE/'scenegraph/runtime_graph.h',ENGINE/'scenegraph/coh_scenegraph.c',ENGINE/'scenegraph/coh_scenegraph.h',ENGINE/'replication/coh_replication.h',ENGINE/'replication/coh_groups.h',ENGINE/'coh_contracts.h',Path(__file__)]
    pins={str(f.relative_to(ENGINE.parent.parent)):sha(f.read_bytes()) for f in sources+headers}
    outcomes={}
    with tempfile.TemporaryDirectory(prefix='coh-snapshot-owner-') as tmp:
        tmp=Path(tmp)
        with zipfile.ZipFile(a.capture_zip) as z:
            if z.testzip():raise ValueError('Capture ZIP CRC failure')
            for name,pin in [('catalog.cohcat','61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763'),('runtime.cohrts','c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02')]:
                data=z.read('capture/'+name)
                if sha(data)!=pin:raise ValueError('Capture payload changed')
                (tmp/name).write_bytes(data)
        for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            binary=tmp/mode
            command=['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(HERE),*flags,*map(str,sources),'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lcrypto','-lm','-o',str(binary)]
            subprocess.run(command,check=True,capture_output=True,text=True,timeout=180)
            env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
            run=subprocess.run([binary,tmp/'catalog.cohcat',tmp/'runtime.cohrts'],capture_output=True,text=True,env=env,timeout=180)
            if run.returncode:raise RuntimeError(mode+': '+run.stdout+run.stderr)
            outcomes[mode]={'result':json.loads(run.stdout),'binary_sha256':sha(binary.read_bytes())}
    if any(sha(f.read_bytes())!=pins[str(f.relative_to(ENGINE.parent.parent))] for f in sources+headers):raise ValueError('Source changed during qualification')
    if sha(a.capture_zip.read_bytes())!=CAPTURE_SHA:raise ValueError('Capture changed during qualification')
    result={'schema':1,'passed':True,'leak_sanitizer':False,'allocation_balance_controls':True,'leak_sanitizer_unavailable_reason':'LSan fatal: cannot open /proc task in sandbox; explicit wrapped allocation balance verified','source_sha256':pins,'capture_zip_sha256':CAPTURE_SHA,'modes':outcomes,'source_snapshot_only':True,'live_groups_transaction':False,'android_executed':False,'physical_thor_accepted':False,'graph_published':False,'world_authority':False,'provenance_receipts_independently_admitted':False,'scope':'Immutable byte lifetime, structural diagnostic closure and exact named aggregate budget. Fixture inventory label is not inventory admission. No live generation or publication permit.'}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'passed':True,'checks':outcomes}))
if __name__=='__main__':main()
