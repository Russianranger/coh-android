#!/usr/bin/env python3
"""Strict immutable source-owner/resource association, with no resource authority."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile,zipfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ENGINE=HERE.parent
CAPTURE_SHA='8763048abd0d55070159955f02ae9d72e452aa44d1da6e6603a22637732d764d'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kw):
    p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=180,**kw)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture-zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('New output required')
    if sha(a.capture_zip)!=CAPTURE_SHA:raise ValueError('Capture archive SHA differs')
    sources=[HERE/'tests/test_resource_join.c',HERE/'coh_resource_join.c',HERE/'coh_resource_index.c',HERE/'coh_resource_geo_source.c',HERE/'coh_catalog_snapshot.c',HERE/'coh_catalog_owner.c',HERE/'coh_scenecatalog.c',ENGINE/'scenegraph/runtime_snapshot.c',ENGINE/'scenegraph/tests/runtime_matrix_bridge.c',ENGINE/'replication/coh_replication.c',ENGINE/'replication/coh_groups.c',ENGINE/'assets/coh_asset_loader.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
    headers=[HERE/'coh_resource_join.h',HERE/'coh_resource_index.h',HERE/'coh_resource_geo_source.h',HERE/'coh_catalog_snapshot.h',HERE/'coh_catalog_owner.h',HERE/'coh_scenecatalog.h',ENGINE/'scenegraph/runtime_graph.h',ENGINE/'scenegraph/runtime_snapshot.h',ENGINE/'scenegraph/coh_scenegraph.c',ENGINE/'scenegraph/coh_scenegraph.h',ENGINE/'replication/coh_replication.h',ENGINE/'replication/coh_groups.h',ENGINE/'assets/coh_asset_loader.h',ENGINE/'assets/coh_asset_geo.h',ENGINE/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',Path(__file__)]
    fixtures=[ENGINE/'scenecatalog-server/evidence/runtime-snapshot-20261016/fixtures'/('snapshot-6.'+suffix) for suffix in ('cohcat','cohrts')]
    pins={str(f.relative_to(ROOT)):sha(f) for f in sources+headers+fixtures}
    modes={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
    with tempfile.TemporaryDirectory(prefix='coh-resource-join-') as directory:
        tmp=Path(directory)
        with zipfile.ZipFile(a.capture_zip) as z:
            if z.testzip():raise ValueError('Capture archive CRC failure')
            for name,digest in [('catalog.cohcat','61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763'),('runtime.cohrts','c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02')]:
                raw=z.read('capture/'+name)
                if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Captured input SHA differs')
                (tmp/name).write_bytes(raw)
            source=z.read('capture/source-identity.json');binding=json.loads(z.read('capture/snapshot-binding.json'))
            if hashlib.sha256(source).hexdigest()!=binding['source_identity']['sha256']:raise ValueError('Source identity differs')
            if json.loads(source)['runtime_inventory']['ordered_inventory_sha256']!='5affc1a2f00960732f55f3d88d83af8aa60e8dbc1b5b360cc606cb8095262ba1':raise ValueError('Inventory differs')
        for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            binary=tmp/mode
            run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),*flags,*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lcrypto','-lz','-lm','-o',binary])
            actual=json.loads(run([binary,tmp/'catalog.cohcat',tmp/'runtime.cohrts'],env=env))
            small=json.loads(run([binary,*fixtures,'--small'],env=env))
            if actual['rows']!=40232 or actual['models']!=9611 or not actual['synthetic_resource_observations'] or actual['assets_admitted']:raise ValueError('Actual owner-association boundary differs')
            if small['rows']!=4 or small['models'] or small['actual_catalog']:raise ValueError('Small original source fixture differs')
            modes[mode]={'actual_catalog_structural_join':actual,'zero_model_source_fixture_join_and_retained_index':small,'binary_sha256':sha(binary)}
    if pins!={str(f.relative_to(ROOT)):sha(f) for f in sources+headers+fixtures}:raise ValueError('Source/fixture changed during qualification')
    if sha(a.capture_zip)!=CAPTURE_SHA:raise ValueError('Capture changed during qualification')
    result={'schema':1,'passed':True,'source_sha256':pins,'capture_zip_sha256':CAPTURE_SHA,'modes':modes,'scope':'Exact real catalog/root/future owner association using explicit in-memory synthetic resource observations, not a runtime resource capture. No GEO asset path is inferred or admitted.','resource_observations_synthetic':True,'actual_resource_capture':False,'assets_admitted':False,'client_materials_admitted':False,'world_authority':False,'android_executed':False,'leak_sanitizer':False,'allocation_balance_controls':True,'memory_scope':'Named unique owners+graphs, old/new joins, caller input/reserves and streaming scratch; no process RSS/GPU claim'}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'passed':True,'modes':modes}))
if __name__=='__main__':main()
