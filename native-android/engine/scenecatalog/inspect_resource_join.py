#!/usr/bin/env python3
"""Revalidate a real resource-capture binding, then run strict native source association."""
from pathlib import Path
import argparse,hashlib,importlib,json,os,re,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ENGINE=HERE.parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(command,**kwargs):
    result=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=180,**kwargs)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-directory',type=Path,required=True)
    parser.add_argument('--binding-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('New output required')
    if not re.fullmatch('[0-9a-f]{64}',args.binding_sha256):raise ValueError('Trusted binding pin required')
    capture=args.capture_directory.resolve()
    sys.path.insert(0,str(ENGINE/'scenecatalog-server'))
    validator=importlib.import_module('capture_resources');d=validator.d
    binding_path=d.regular(capture/'resource-binding.json')
    if d.hash_file(binding_path,8*1024**2)[1]!=args.binding_sha256:raise ValueError('Resource binding SHA differs')
    binding=d.json_object(d.read(binding_path,8*1024**2))
    report=d.json_object(d.read(capture/'capture-receipt.json',8*1024**2))
    if validator.build_binding(capture,report,binding['asset_generation'])!=binding:raise ValueError('Revalidated binding differs')
    source=d.json_object(d.read(capture/'source-identity.json',8*1024**2))
    inventory=source['runtime_inventory']['ordered_inventory_sha256']
    if not re.fullmatch('[0-9a-f]{64}',inventory):raise ValueError('Inventory digest invalid')
    sources=[HERE/'validate_resource_join.c',HERE/'coh_resource_join.c',HERE/'coh_resource_index.c',HERE/'coh_catalog_snapshot.c',HERE/'coh_catalog_owner.c',HERE/'coh_scenecatalog.c',ENGINE/'scenegraph/runtime_snapshot.c',ENGINE/'scenegraph/tests/runtime_matrix_bridge.c',ENGINE/'replication/coh_replication.c',ENGINE/'replication/coh_groups.c',ENGINE/'assets/coh_asset_loader.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
    dependencies=sources+[HERE/'coh_resource_join.h',HERE/'coh_resource_index.h',HERE/'coh_catalog_snapshot.h',HERE/'coh_catalog_owner.h',HERE/'coh_scenecatalog.h',ENGINE/'scenegraph/runtime_graph.h',ENGINE/'scenegraph/runtime_snapshot.h',ENGINE/'scenegraph/coh_scenegraph.c',ENGINE/'scenegraph/coh_scenegraph.h',ENGINE/'replication/coh_replication.h',ENGINE/'replication/coh_groups.h',ENGINE/'assets/coh_asset_loader.h',ENGINE/'assets/coh_asset_geo.h',ENGINE/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',Path(__file__),Path(validator.__file__),ENGINE/'scenecatalog-server/resource_oracle.py',ENGINE/'scenecatalog-server/capture_snapshot.py',ENGINE/'scenecatalog-server/delivery.py']
    local_modules={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(Path(m.__file__).resolve()).startswith(str(ROOT)+'/') and str(m.__file__).endswith('.py')}
    dependencies=list(dict.fromkeys([*dependencies,*sorted(local_modules)]))
    pins={str(p.relative_to(ROOT)):sha(p) for p in dependencies}
    records=[binding_path,capture/'capture-receipt.json',capture/'source-identity.json',capture/'run-identity.json',capture/'catalog.cohcat',capture/'runtime.cohrts',capture/'resources.cohres']
    inputs={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in records}
    arguments=[capture/'catalog.cohcat',capture/'runtime.cohrts',capture/'resources.cohres',binding['source_identity']['sha256'],binding['run_identity']['sha256'],inventory,binding['snapshot']['sha256'],binding['resources']['sha256'],args.binding_sha256]
    modes={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
    with tempfile.TemporaryDirectory(prefix='coh-actual-resource-join-') as temporary:
        temporary=Path(temporary)
        for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            binary=temporary/mode
            run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),*flags,*sources,'-lcrypto','-lz','-lm','-o',binary])
            result=json.loads(run([binary,*arguments],env=env))
            if not result['source_association_verified'] or result['assets_admitted'] or result['world_authority'] or result['fixture_slab_allocated']:raise ValueError('Native source-only boundary differs')
            modes[mode]={'result':result,'binary_sha256':sha(binary)}
    if pins!={str(p.relative_to(ROOT)):sha(p) for p in dependencies}:raise ValueError('Native/validator source changed')
    if inputs!={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in records}:raise ValueError('Capture changed during decoding')
    if validator.build_binding(capture,report,binding['asset_generation'])!=binding:raise ValueError('Capture post-validation differs')
    values=[row['result'] for row in modes.values()]
    if values[1:]!=values[:-1]:raise ValueError('Native mode diagnostics differ')
    result={'schema':1,'passed':True,'source_sha256':pins,'capture_input_identity':inputs,'trusted_binding_sha256':args.binding_sha256,'modes':modes,'source_snapshot_only':True,'actual_resource_capture':True,'native_source_association_completed':True,'resource_indices_built':False,'assets_admitted':False,'client_materials_available':False,'client_lods_available':False,'live_groups_transaction':False,'world_authority':False,'android_executed':False,'leak_sanitizer':False,'scope':'Copied authenticated source-observation association only; no asset/GEO material or runtime-row-to-disk-row admission. Named native transaction budgets exclude Python process RSS.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'passed':True,'modes':modes,'assets_admitted':False}))
if __name__=='__main__':main()
