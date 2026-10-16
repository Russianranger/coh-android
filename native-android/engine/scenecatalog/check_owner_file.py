#!/usr/bin/env python3
"""Replay the retained authentic catalog through immutable owner; never start a server."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import check as catalog
from check_file import admit_capture, CAPTURE_MANIFEST

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture-directory', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    path, manifest = admit_capture(a.capture_directory)
    if a.output.exists(): raise ValueError('New output required')
    source_pin = hashlib.sha256(CAPTURE_MANIFEST.read_bytes()).hexdigest()
    inventory_pin = manifest['source_runtime_inventory']['ordered_inventory_sha256']
    argv = [str(path), str(manifest['catalog']['generation']), manifest['catalog']['sha256'], source_pin, inventory_pin]
    sources = [HERE/'validate_owner_file.c', HERE/'coh_catalog_owner.c', HERE/'coh_scenecatalog.c',
               HERE.parent/'scenegraph/coh_scenegraph.c', HERE.parent/'replication/coh_replication.c',
               HERE.parent/'replication/coh_groups.c']
    included = sources + [HERE/'coh_catalog_owner.h', HERE/'coh_scenecatalog.h', HERE/'check_owner_file.py',
                          HERE/'check_file.py', CAPTURE_MANIFEST]
    outcomes = {}
    # Managed executor cannot expose /proc/<pid>/task to LeakSanitizer. Owner
    # fixture suite independently tracks all malloc/calloc/free ownership.
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
    with tempfile.TemporaryDirectory(prefix='coh-owner-') as temporary:
        tmp = Path(temporary)
        for mode, flags in [('release', ['-O2']), ('asan', ['-O1','-g','-fsanitize=address','-no-pie']),
                            ('ubsan', ['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            exe = tmp/mode
            catalog.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-Wno-deprecated-declarations',
                         *flags,*sources,'-lcrypto','-lm','-o',exe])
            result = json.loads(catalog.run([exe,*argv], env=env).stdout)
            for k in ('files','slots','definitions','children'):
                if result[k] != manifest['observations'][k]: raise ValueError('Owner count mismatch')
            if result['status'] or not result['owner_created'] or result['map_binding_present']:
                raise ValueError('Owner scope mismatch')
            rejected = 0
            for i, replacement in [(1,'0'),(1,'-1'),(1,'20261017'),(1,'4294967296'),
                                   (2,'0'*64),(2,'f'*64),(3,'0'*64),(4,'0'*64)]:
                args = argv.copy(); args[i] = replacement
                refusal = subprocess.run([str(exe),*args], env=env, text=True, capture_output=True, timeout=30)
                if refusal.returncode != 2 or json.loads(refusal.stdout)['owner_created']:
                    raise ValueError('Owner malformed CLI/pin accepted')
                rejected += 1
            outcomes[mode] = {'authentic_owner':result,'negative_controls':rejected,
                              'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
    if admit_capture(a.capture_directory)[1] != manifest: raise ValueError('Source changed')
    result = dict(schema=1, passed=True, authentic_catalog_sha256=manifest['catalog']['sha256'],
                  source_evidence_sha256=source_pin, inventory_sha256=inventory_pin, checks=outcomes,
                  source_sha256={str(x.relative_to(HERE.parents[2])):hashlib.sha256(x.read_bytes()).hexdigest() for x in included},
                  openssl_version=catalog.run(['openssl','version']).stdout.strip(),
                  digest_provider='explicit host OpenSSL SHA256_Init/Update/Final; not an Android/library dependency',
                  leak_sanitizer=False, map_binding_present=False, matching_groups_captured=False, android_executed=False,
                  server_started=False, graph_published=False, renderer_authorized=False, physical_thor_accepted=False)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f: json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'passed':True,'checks':outcomes}))


if __name__ == '__main__': main()
