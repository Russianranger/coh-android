"""Replay the five host suites and bind retained full-source evidence. No build."""
import argparse,gzip,hashlib,io,json,subprocess,sys,zipfile
from pathlib import Path
import manual_atlas_full_recipe as r


def qualify(root,stage,donor):
    evidence=r.MANIFEST.parent
    raw=r.git(root,'show','HEAD:docs/android-evidence/client-saved-map-reopen-0.13.34-publication.json')
    publication=json.loads(raw);reference=publication['donor'];archive=donor.read_bytes()
    if r.base.sha(archive)!=reference['build_report_artifact_zip']['sha256'] or len(archive)!=reference['build_report_artifact_zip']['bytes']:
        raise ValueError('manual_donor_archive_identity')
    with zipfile.ZipFile(io.BytesIO(archive)) as outer:
        apk=outer.read('COH-Atlas-Gameplay-0.13.33.apk')
        if r.base.sha(apk)!=reference['apk']['sha256'] or len(apk)!=reference['apk']['bytes']:raise ValueError('manual_donor_apk_identity')
        with zipfile.ZipFile(io.BytesIO(apk)) as inner:
            manifest=inner.read('assets/runtime/startup-dbserver-manifest.json');pe=inner.read('assets/runtime/startup-dbserver.exe')
    if manifest!=r.MANIFEST.read_bytes():raise ValueError('manual_retained_manifest_donor_mismatch')
    m=r.load_manifest();record=m['files']['DbServer.exe']
    if r.base.sha(pe)!=record['sha256'] or len(pe)!=record['bytes']:raise ValueError('manual_retained_pe_donor_mismatch')
    recipe=json.loads((evidence/'source-recipe.json').read_bytes());compressed=(evidence/recipe['source_maps_file']).read_bytes()
    if r.base.sha(compressed)!=recipe['source_maps_sha256']:raise ValueError('manual_source_map_archive_identity')
    maps=json.loads(gzip.decompress(compressed))
    if set(maps)!= {'original','accepted_manual_lineage','checksum_candidate'}:raise ValueError('manual_source_map_kinds')
    r.verify_complete_source(stage,maps['checksum_candidate'])
    plan=r.build_plan(stage,'NEW_EXTERNAL_BUILD','EXACT_PATCH_EXECUTABLE',maps['checksum_candidate'])
    result=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(r.HERE),'-p','test_manual_atlas_full_recipe.py','-v'],capture_output=True,text=True,timeout=180)
    if result.returncode or 'Ran 5 tests' not in result.stderr or not result.stderr.rstrip().endswith('OK'):raise ValueError('manual_host_suites_failed')
    (evidence/'host-tests.txt').write_text(result.stdout+result.stderr)
    (evidence/'static-build-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (evidence/'recovery.json').write_text(json.dumps({'schema':'coh-manual-atlas-donor-recovery-v1','passed':True,
        'publication_path':'docs/android-evidence/client-saved-map-reopen-0.13.34-publication.json','publication_sha256':r.base.sha(raw),
        'donor':reference,'manifest_sha256':r.base.sha(manifest),'manual_pe':record,
        'pe_executed':False,'apk_installed':False,'shipping_profile_modified':False},indent=2)+'\n')
    names=['manual_atlas_full_recipe.py','test_manual_atlas_full_recipe.py','qualify_manual_atlas_full_recipe.py','MANUAL-ATLAS-FULL-RECIPE.md',
           'pg_wine_checksum_recipe.py','hosted_db_checksum_candidate.py','hosted_auth_stage.py','source_audit.py',
           'checksum_candidate.py','generate_odbc.py','admit_schema.py','source-pins.json','../source_oracle.py']
    local={str((r.HERE/n).resolve().relative_to(root)):r.base.sha((r.HERE/n).read_bytes()) for n in names}
    retained={p.name:r.base.sha(p.read_bytes()) for p in evidence.iterdir() if p.is_file() and p.name!='qualification.json'}
    return {'schema':'coh-manual-atlas-full-source-host-qualification-v1','passed':True,'suites':5,'skips':0,
            'local_inputs':local,'retained_evidence':retained,'original_files':5995,'manual_files':6007,'candidate_files':6007,
            'static_declared_cmake_inputs':504,'external_CPM_dependencies_materialized':False,'build_executed':False,
            'service_executed':False,'android_or_thor_executed':False,'sanitizers':'not_applicable_python_source_composition',
            'shipping_runtime_replacement_permit':False,'live_authenticated_db_login_verified':False}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--donor',type=Path,required=True);a=p.parse_args()
 result=qualify(a.root.resolve(),a.stage.resolve(),a.donor.resolve());(r.MANIFEST.parent/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'suites':5,'build_executed':False}))
