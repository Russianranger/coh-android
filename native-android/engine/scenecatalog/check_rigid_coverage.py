#!/usr/bin/env python3
"""Actual retained GEO metadata gates for the conservative source rigid adapter.
A metadata candidate is not a decoded mesh, material, budget or world permit.
"""
import argparse, collections, hashlib, json, os, subprocess, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ENGINE=HERE.parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def reasons(m):
    result=[]
    if m['version'] not in (0,8): result.append('unsupported_version')
    if m['zero']: result.append('zero_draw_owner')
    if m['version']<3:
        if m['legacy_invalid_pointers']: result.append('invalid_legacy_runtime_pointer')
        if m['legacy_flags']: result.append('legacy_flags')
        if m['legacy_alternate']: result.append('alternate_pivot')
    else:
        if m['reflections']: result.append('reflection_quads')
        if m['alternate']: result.append('alternate_pivot')
    if m['bone_info']: result.append('bone_info')
    if not m['unit_scale']: result.append('nonunit_scale')
    for p in (4,5,6,9):
        if m['packs'][p]: result.append('unsupported_pack_'+str(p))
    for p in range(4):
        if not m['packs'][p]: result.append('missing_required_pack_'+str(p))
    return result

def run(args, **kw):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
    if p.returncode: raise RuntimeError(str(args)+'\n'+p.stdout+p.stderr)
    return p.stdout

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('body-directory','renderer-source-root','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();e=a.renderer_source_root/'native-android/engine/world-render-adapter';ep=HERE/'evidence'
    candidates=ep/'actual-resource-manifest-candidates-38994607354-verified.json'
    complete=ep/'actual-resource-bodies-source-adapter-sealed-38994607354.json'
    closure=ep/'actual-resource-root-closure-38994607354-model-ordinals.json'
    c=json.loads(candidates.read_text());b=json.loads(complete.read_text());r=json.loads(closure.read_text())
    assert c['passed'] and b['passed'] and r['passed'] and b['all391_bodies_acquired']
    roots=set(r['reachable_model_ordinals']);assert len(roots)==3083
    files={f['source_geo_name']:f for f in b['files']};assert len(files)==391
    sources=[HERE/'inspect_rigid_coverage.c',HERE/'coh_resource_geo_source.c',ENGINE/'assets/coh_asset_geo.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
    deps=sources+[HERE/'coh_resource_geo_source.h',ENGINE/'assets/coh_asset_geo.h',ENGINE/'assets/coh_asset_loader.h',ROOT/'native-android/include/coh_native_core.h',ENGINE/'coh_contracts.h',Path(__file__),e/'coh_wr_rigid.c',e/'coh_wr_rigid_source.c']
    pins={str(f):sha(f) for f in deps};inputs={str(f):sha(f) for f in (candidates,complete,closure)}
    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
    outputs={};binaries={};negative_controls={}
    with tempfile.TemporaryDirectory(prefix='coh-rigid-coverage-') as td:
        for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            binary=Path(td)/mode
            run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(ROOT/'native-android/include'),*flags,*sources,'-lz','-lm','-o',binary]);binaries[mode]=sha(binary)
            observations=[]
            for f in c['files']:
                full=files[f['source_geo_name']];path=a.body_directory/full['asset_path'];assert path.stat().st_size==full['bytes'] and sha(path)==full['sha256']
                native=[json.loads(line) for line in run([binary,path],env=env).splitlines()]
                assert native and len(native)<=65536 and len({v['name'] for v in native})==len(native)
                byname={v['name']:v for v in native}
                for model in f['models']:
                    observed=[o for o in model['source_observations'] if o['resource_ordinal'] in roots]
                    assert observed
                    m=byname[model['exact_model_name']]
                    assert all(o['geo_version']==m['version'] for o in observed)
                    why=reasons(m)
                    observations.append(dict(source_geo_name=f['source_geo_name'],asset_path=full['asset_path'],body_sha256=full['sha256'],source_ordinals=[o['resource_ordinal'] for o in observed],metadata=m,metadata_refusals=why,metadata_candidate=not why,grid_metadata_present=bool(m['packs'][7]),reduction_metadata_present=bool(m['packs'][8])))
            assert len(observations)==2916 and sum(len(m['source_ordinals']) for m in observations)==3083
            outputs[mode]=observations
            negative_controls[mode]=0
            for label,raw in [('empty',b''),('short-envelope',b'\0'*4),('invalid-envelope',b'\0'*24)]:
                malformed=Path(td)/label;malformed.write_bytes(raw)
                refused=subprocess.run([str(binary),str(malformed)],capture_output=True,env=env,timeout=10)
                assert refused.returncode==2 and not refused.stdout and not refused.stderr
                negative_controls[mode]+=1
            print(mode,'metadata pairs',len(observations),flush=True)
    assert outputs['release']==outputs['asan']==outputs['ubsan']
    assert pins=={str(f):sha(f) for f in deps};assert inputs=={str(f):sha(f) for f in (candidates,complete,closure)}
    models=outputs['release'];summary={}
    for label,weight in [('unique_models',lambda m:1),('model_owner_references',lambda m:len(m['source_ordinals']))]:
        versions=collections.Counter();first=collections.Counter();allreasons=collections.Counter();candidates_count=0
        for m in models:
            n=weight(m);versions[str(m['metadata']['version'])]+=n;candidates_count+=n*m['metadata_candidate']
            if m['metadata_refusals']: first[m['metadata_refusals'][0]]+=n
            for reason in m['metadata_refusals']:allreasons[reason]+=n
        summary[label]=dict(total=sum(versions.values()),versions=dict(versions),metadata_candidates=candidates_count,first_metadata_refusals=dict(first),all_metadata_refusals=dict(allreasons),grid_metadata_present=sum(weight(m) for m in models if m['grid_metadata_present']),reduction_metadata_present=sum(weight(m) for m in models if m['reduction_metadata_present']))
    result=dict(passed=True,scope='Read-only actual retained full-body model metadata gates against current conservative source rigid entry; candidate does not prove stream/CPU/material/budget support',source_sha256=pins,input_sha256=inputs,binary_sha256=binaries,modes=['release','asan','ubsan'],files=391,file_versions=dict(collections.Counter(str(m['metadata']['version']) for m in {m['asset_path']:m for m in models}.values())),native_refusal_controls=negative_controls,summary=summary,models=models,cpu_geometry_decoded=False,materials_admitted=False,assets_admitted=False,live_generation_admitted=False,world_authority=False,android_executed=False,leak_sanitizer=False)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
