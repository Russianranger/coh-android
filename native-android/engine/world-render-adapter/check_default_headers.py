#!/usr/bin/env python3
"""Qualify only the thin fixed-seven adapter with controlled staging fixtures."""
import argparse,gzip,hashlib,importlib.util,json,os,struct,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(body):return hashlib.sha256(body).hexdigest()
def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=180,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 adapter=module('controlled_source_adapter',HERE/'inspect_default_headers.py');tests=module('controlled_source_layout',HERE/'tests/test_default_headers.py')
 fixture=tests.HELPER_FIXTURE;compressed=fixture.read_bytes()
 if sha(compressed)!='8a62c21674d020ad73eed9e340a740133b9eb167ee05a0a3a45c0f15ca76e172':raise ValueError('exact public helper source fixture differs')
 helpers=json.loads(gzip.decompress(compressed))
 if set(helpers)!=set(adapter.HELPERS) or any((len(helpers[n].encode()),sha(helpers[n].encode()))!=adapter.HELPERS[n] for n in helpers):raise ValueError('pinned .31 helper source differs')
 deps=[*adapter.SOURCES,Path(__file__),HERE/'tests/test_default_headers.py',fixture];before={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in deps}
 unit=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(HERE/'tests'),'-p','test_default_headers.py','-v'],capture_output=True,timeout=180)
 if unit.returncode or b'Ran 15 tests' not in unit.stderr or not unit.stderr.rstrip().endswith(b'OK'):raise ValueError(unit.stdout.decode()+unit.stderr.decode())
 modes={};binaries={};cases=[]
 paths=json.loads(adapter.DEFAULTS.read_bytes())['required_defaults'];ordinary=[tests.texture(x['required_virtual_asset_path'][5:]) for x in paths]
 cases.append(('supported_seven',ordinary,True))
 unsupported=list(ordinary);unsupported[0]=tests.texture(paths[0]['required_virtual_asset_path'][5:],True);cases.append(('unsupported_DX10_retained_as_explicit_status',unsupported,False))
 malformed=list(ordinary);malformed[3]=b'not a valid texture';cases.append(('malformed_body_explicit_status',malformed,False))
 wrong_name=list(ordinary);wrong_name[6]=tests.texture('texture_library/other_name.texture');cases.append(('supported_DDS_wrong_owner_name_refuses_owner',wrong_name,False))
 with tempfile.TemporaryDirectory(prefix='coh-default-adapter-proof-') as raw:
  d=Path(raw);common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',ROOT/'native-android/include']
  for mode,flags in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=d/mode;run([*common,*flags,*adapter.COMPILE,'-lcrypto','-lz','-lm','-o',binary]);observed=[]
   environment=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
   for name,bodies,expected in cases:
    files=[]
    for i,body in enumerate(bodies):path=d/(str(i)+'.texture');path.write_bytes(body);files.append(path)
    result=json.loads(run([binary,*files],env=environment))
    if result['seven_header_owner_created'] is not expected or result['namespace_complete'] or result['default_identity'] or result['current_provider_generation'] or result['GPU'] or not result['owner_retired_before_exit']:raise ValueError('native inspection scope differs')
    for i,(row,body) in enumerate(zip(result['rows'],bodies)):
     if row['ordinal']!=i or row['bytes']!=len(body) or row['sha256']!=sha(body):raise ValueError('exact driver body association differs')
    if name=='unsupported_DX10_retained_as_explicit_status' and (result['rows'][0]['protected_parser_status']!=2 or result['seven_header_owner_attempted']):raise ValueError('unsupported parser route hidden')
    observed.append({'case':name,'result':result})
   missing=subprocess.run([binary],capture_output=True,env=environment,timeout=30)
   if missing.returncode!=2 or missing.stdout:raise ValueError('fixed arity refusal differs')
   (d/'0.texture').write_bytes(b'x'*16385);oversized=subprocess.run([binary,*[d/(str(i)+'.texture') for i in range(7)]],capture_output=True,env=environment,timeout=30)
   if oversized.returncode!=2 or oversized.stdout:raise ValueError('fixed body maximum refusal differs')
   modes[mode]={'passed':True,'controlled_cases':observed,'fixed_arity_and_oversize_refused':True};binaries[mode]=sha(binary.read_bytes())
  # Run the production compile-and-call adapter once as well as the three direct
  # sanitizer binaries. These input bytes remain explicitly synthetic.
  integration_dir=d/'production-driver';integration_dir.mkdir();native,integration_sha=adapter.native_inspection(ordinary,integration_dir,adapter.source_pins(False))
  if not native['seven_header_owner_created']:raise ValueError('production native bridge differs')
 if before!={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in deps}:raise ValueError('source changed after qualification')
 proof={'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':before,'controlled_staging_unit_test_methods':15,'controlled_staging_unit_test_log_sha256':sha(unit.stdout+unit.stderr),'modes':modes,'binary_sha256':binaries,'production_existing_parser_compile_call':{'passed':True,'binary_sha256':integration_sha},'pinned_public_031_helper_sha256':{n:x[1] for n,x in adapter.HELPERS.items()},'selected_pinned_read_only_functions':['import_identity','native_closure_identity','worktree_data_identity','identity_sha256','CheckedInputResolver','texture_inputs'],'isolated_original_resolver_and_typed_error_import_observers':True,'test_cold_full_import_receipt_is_controlled_not_real_staging':True,'test_default_body_pins_are_controlled_not_authentic':True,'actual_031_staging_executed':False,'seven_authentic_default_bodies_available':False,'seven_authentic_default_parser_support_known':False,'optional_retention_fixed_allowlist_commit_last_and_all_9_late_write_positions_refused':True,'controlled_final_source_changes_after_manifest_and_result_rolled_back':True,'primary_write_or_flush_failure_preserved_through_close_failure':True,'primary_directory_fsync_failure_preserved_through_close_failure':True,'rollback_continues_after_independent_unlink_failure_preserving_primary':True,'compile_execute_source_and_executable_mutation_controls':True,'actual_source_committed_gate_enabled_in_CLI_bypassed_only_by_test_fixture':True,'current_provider_generation':False,'namespace_complete':False,'default_identity':False,'GPU':False,'world_authority':False,'old_qualifiers_rerun':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'controlled_unit_methods':15,'modes':list(modes),'authentic_default_bodies_inspected':False}))
if __name__=='__main__':main()
