#!/usr/bin/env python3
"""Measure composed immutable catalog owner plus compact audit; strict refusal remains."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import check as catalog
from check_file import admit_capture, CAPTURE_MANIFEST

HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--source-revision',required=True)
    p.add_argument('--capture-directory',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();root=a.source_root.resolve()
    if a.output.exists():raise ValueError('New output required')
    revision=subprocess.check_output(['git','rev-parse',a.source_revision+'^{commit}'],cwd=root,text=True).strip()
    path,manifest=admit_capture(a.capture_directory)
    cpp=['scenecatalog/coh_catalog_owner.c','scenecatalog/coh_scenecatalog.c',
         'scenegraph/coh_scene_compact.c','scenegraph/coh_scenegraph.c','replication/coh_replication.c','replication/coh_groups.c']
    headers=['scenecatalog/coh_catalog_owner.h','scenecatalog/coh_scenecatalog.h',
             'scenegraph/coh_scene_compact.h','scenegraph/coh_scenegraph.h',
             'replication/coh_replication.h','replication/coh_groups.h','coh_contracts.h']
    relative=['native-android/engine/'+f for f in cpp+headers]
    pins={}
    def verify():
        for rel in relative:
            original=subprocess.check_output(['git','show',revision+':'+rel],cwd=root)
            actual=(root/rel).read_bytes()
            if actual!=original:raise ValueError('Pinned dependency changed: '+rel)
            pins[rel]=hashlib.sha256(actual).hexdigest()
    verify()
    source_pin=hashlib.sha256(CAPTURE_MANIFEST.read_bytes()).hexdigest()
    args=[path,str(manifest['catalog']['generation']),manifest['catalog']['sha256'],source_pin,
          manifest['source_runtime_inventory']['ordered_inventory_sha256']]
    sources=[HERE/'tests/test_owner_compact.c',*[root/rel for rel in relative[:len(cpp)]]]
    driver=[HERE/'tests/test_owner_compact.c',HERE/'check_owner_compact.py',HERE/'check_file.py',HERE/'check.py',CAPTURE_MANIFEST]
    driver_pins={str(f.relative_to(HERE.parents[2])):hashlib.sha256(f.read_bytes()).hexdigest() for f in driver}
    outcomes={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
    with tempfile.TemporaryDirectory(prefix='coh-owner-compact-') as temporary:
        tmp=Path(temporary)
        for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),
                           ('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            binary=tmp/mode
            command=['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-Wno-deprecated-declarations',
                     '-I'+str(root/'native-android/engine/scenecatalog'),'-I'+str(root/'native-android/engine/scenegraph'),
                     '-Wl,--wrap=malloc,--wrap=calloc,--wrap=free',*flags,*sources,'-lcrypto','-lm','-o',binary]
            catalog.run(command)
            result=json.loads(catalog.run([binary,*args],env=env).stdout)
            outcomes[mode]={'measurement':result,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
    verify()
    if admit_capture(a.capture_directory)[1]!=manifest:raise ValueError('Capture changed')
    measurements=[row['measurement'] for row in outcomes.values()]
    if any(row!=measurements[0] for row in measurements[1:]):raise ValueError('Mode measurements differ')
    if driver_pins!={str(f.relative_to(HERE.parents[2])):hashlib.sha256(f.read_bytes()).hexdigest() for f in driver}:
        raise ValueError('Composition driver changed during qualification')
    result=dict(schema=1,passed=True,source_revision=revision,dependency_sha256=pins,
                driver_sha256=driver_pins,
                catalog_sha256=manifest['catalog']['sha256'],source_evidence_sha256=source_pin,checks=outcomes,
                scope='host allocator-tracked native named payload plus declared stack/harness reservations; no process RSS/driver/server/allocator-metadata claim',
                owner_indexes_charged_once=True,existing_stream_implementation_unchanged=True,
                server_started=False,android_executed=False,physical_thor_accepted=False,graph_published=False,
                immutable_owner_map_binding_present=False,matching_root_transaction_present=False,
                leak_sanitizer=False,allocation_tracking=True,
                compiler_version=catalog.run(['cc','--version']).stdout.splitlines()[0],
                openssl_version=catalog.run(['openssl','version']).stdout.strip())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'passed':True,'measurements':measurements[0]}))


if __name__=='__main__':main()
