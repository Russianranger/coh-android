#!/usr/bin/env python3
"""Run unchanged legacy deep assertions on an explicit test-only view, and independently qualify every exact bounded shipping report."""
from pathlib import Path
import argparse,hashlib,json,os,re,shlex,shutil,subprocess,gzip,sys
BASE=Path('native-android/combined-client/diagnostics/interop-adapter-20261018')
SOURCE=Path('native-android/combined-client/app/src/main/cpp/interop_network.c')
ROLE=Path('native-android/combined-client/diagnostics/interop-report-adapter-20261020')
JAVA=Path('native-android/combined-client/app/src/main/java/org/coh/nativecombined/InteropNative.java')
def need(value,message):
 if not value:raise ValueError(message)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(command,root,env=None):return subprocess.run(list(map(str,command)),cwd=root,env=env,capture_output=True,timeout=40)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 root,out=args.source_root.resolve(),args.output.resolve();need(not out.exists()and root not in out.parents,'fresh external output required');out.mkdir()
 compiler=Path(shutil.which(os.environ.get('CC','cc'))).resolve();flags=[str(compiler),'-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fno-pie','-no-pie','-fstack-usage','-DCOH_INTEROP_REQUEST_TX=1',
  '-I',str(BASE/'test-include'),'-I','native-android/engine/initial-capture','-I','native-android/engine/entities','-I','native-android/engine/session','-I','native-android/include']
 sources=[ROLE/'test_bounded_adapter.c',Path('native-android/engine/initial-capture/coh_initial_create_probe.c'),Path('native-android/engine/initial-capture/coh_initial_pose_probe.c'),Path('native-android/engine/initial-capture/coh_initial_sequence_probe.c'),Path('native-android/engine/initial-capture/coh_initial_triggered_probe.c'),Path('native-android/engine/initial-capture/coh_initial_aianim_probe.c'),Path('native-android/engine/initial-capture/coh_initial_netfx_probe.c'),Path('native-android/engine/initial-capture/coh_initial_costume_probe.c'),Path('native-android/engine/initial-capture/coh_initial_reward_probe.c'),Path('native-android/engine/initial-capture/coh_initial_reward_list_probe.c'),Path('native-android/engine/initial-capture/coh_initial_costume_slots_probe.c'),Path('native-android/engine/initial-capture/coh_initial_costume_body_probe.c'),Path('native-android/engine/initial-capture/coh_initial_appearance_probe.c'),Path('native-android/engine/initial-capture/coh_initial_sgcolors_probe.c'),Path('native-android/engine/initial-capture/coh_initial_scales_probe.c'),Path('native-android/engine/initial-capture/coh_initial_partcount_probe.c'),Path('native-android/engine/initial-capture/coh_local_bodypart_default.c'),Path('native-android/engine/entities/coh_original_costume_receive.c'),Path('native-android/engine/entities/coh_entities.c'),Path('native-android/engine/replication/coh_replication.c')];dep=run([*flags,'-M',*sources],root);(out/'dependencies.stdout').write_bytes(dep.stdout);(out/'dependencies.stderr').write_bytes(dep.stderr);need(dep.returncode==0 and not dep.stderr,'dependencies refused')
 project={BASE/'check_adapter.py',BASE/'test_interop_adapter.c',ROLE/'check_bounded_adapter.py',JAVA,Path('native-android/combined-client/tools/interop_package_audit.py')};system={compiler}
 for line in dep.stdout.decode().replace('\\\n',' ').splitlines():
  for token in shlex.split(line.split(':',1)[1]):
   p=Path(token);p=(p if p.is_absolute()else root/p).resolve();need(p.is_file(),'nonregular dependency')
   if p.is_relative_to(root):project.add(p.relative_to(root))
   else:system.add(p)
 before={str(p):sha(root/p)for p in sorted(project)};sysbefore={str(p):sha(p)for p in sorted(system)}
 (out/'source-before.json').write_text(json.dumps(before,indent=2,sort_keys=True)+'\n');(out/'compiler-header-before.json').write_text(json.dumps(sysbefore,indent=2,sort_keys=True)+'\n')
 version=run([compiler,'--version'],root);(out/'compiler-version.txt').write_bytes(version.stdout+version.stderr)
 head=run(['git','rev-parse','HEAD'],root).stdout.decode().strip();commands=[];results={};binaries={};libraries={};stacks={}
 environment={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}
 for mode,options in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=out/('adapter-'+mode);command=[*flags,*options,*sources,'-Wl,--wrap=calloc','-Wl,--wrap=free','-lcrypto','-lm','-o',binary];commands.append(list(map(str,command)));c=run(command,root)
  (out/(mode+'-compile.stdout')).write_bytes(c.stdout);(out/(mode+'-compile.stderr')).write_bytes(c.stderr);need(c.returncode==0 and not c.stderr,'compile refused '+mode)
  binaries[mode]={'bytes':binary.stat().st_size,'sha256':sha(binary),'retained_gzip':binary.name+'.gz'}
  (out/(binary.name+'.gz')).write_bytes(gzip.compress(binary.read_bytes(),mtime=0))
  linked=run(['ldd',binary],root);(out/(mode+'-ldd.txt')).write_bytes(linked.stdout+linked.stderr);need(linked.returncode==0,'ldd refused')
  for value in re.findall(rb'/[^\s()]+',linked.stdout):
   p=Path(os.fsdecode(value)).resolve();need(p.is_file(),'nonregular link dependency');libraries[str(p)]=sha(p)
  child=run([binary],root,environment);(out/(mode+'-child.stdout')).write_bytes(child.stdout);(out/(mode+'-child.stderr')).write_bytes(child.stderr);need(child.returncode==0 and not child.stderr,'new adapter child refused '+mode)
  text=child.stdout.decode();records=[];decoder=json.JSONDecoder()
  while text.strip():
   text=text.lstrip();value,end=decoder.raw_decode(text);records.append(value);text=text[end:]
  busy=[v['shipping_busy_report']for v in records if 'shipping_busy_report'in v];need(len(busy)==1 and busy[0]['phase']=='OWNER_BUSY'and busy[0]['initial_observation_known']is False and busy[0]['initial_observed']is None,'busy observation unknown')
  shipping=[v for v in records if 'shipping_report'in v];result=records[-2];coverage=records[-1]
  need(coverage['historical_assertions_executed_unchanged']is True and coverage['production_or_original_fixture_modified']is False and coverage['bounded_shipping_reports']==len(shipping) and coverage['shipping_reports_with_omissions']>0,'shipping coverage')
  names=['first_create','first_record_pose','first_record_sequence','first_record_triggered_moves','first_record_ai_animation','first_record_netfx','first_record_costume_prefix','first_reward_string','first_reward_progress']
  for record in shipping:
   r=record['shipping_report'];need(record['shipping_report_bytes']<7168 and r['report_limit_bytes']==7168,'shipping cap')
   need(r['phase']not in('REPORT_LIMIT','OWNER_BUSY')and not r.get('report_core_limit'),'shipping phase')
   need(r['report_invalid_mask']==0 and r['report_omitted_mask']<256,'unexpected serialization failure')
   expected=[k for i,k in enumerate(names)if r['report_omitted_mask']&(1<<i)]
   need(r['report_omitted_fields']==expected and r['report_truncated']==bool(expected),'shipping omission metadata')
   for name in expected:need(r[name]is None,'omission is not null')
   need('test_only_full_detail_view'not in r and 'test_only_omitted_probe_projection'not in r,'shipping pollution')
   need(r['owner_present']is True and r['initial_observation_known']is True and isinstance(r['receive_diagnostics'],dict),'shipping core')
   need(r['world_authority']is False and r['ack_permitted']is False and r['packet_copy_retained']is False,'shipping protection')
  result['independent_bounded_shipping_coverage']=coverage
  need(result['passed']is True and result['JNI_and_initial_capture_explicit_doubles']is True and result['actual_Android_or_protocol_or_original_server']is False and result['world_authority']is False,'scope drift');results[mode]=result
  frames=[]
  for p in out.glob(binary.name+'-*.su'):
   for line in p.read_text().splitlines():
    where,size,kind=line.split('\t');need('unbounded'not in kind,'unbounded frame');frames.append({'function':where.rsplit(':',1)[-1],'bytes':int(size),'kind':kind})
  stacks[mode]=frames
 need(all(v==results['release']for v in results.values()),'cross-mode controls differ')
 (out/'source-after.json').write_text(json.dumps({str(p):sha(root/p)for p in sorted(project)},indent=2,sort_keys=True)+'\n')
 need(before=={str(p):sha(root/p)for p in sorted(project)},'source changed');need(sysbefore=={str(p):sha(p)for p in sorted(system)},'compiler/header changed')
 need(all(sha(out/('adapter-'+m))==v['sha256']for m,v in binaries.items()),'binary changed');need(all(sha(Path(p))==v for p,v in libraries.items()),'linked dependency changed')
 sys.path.insert(0,str(root/'native-android/combined-client/tools'))
 from interop_package_audit import required_methods
 methods=re.findall(r'public static native ([^;]+);',(root/JAVA).read_text());names=[re.search(r'\b(\w+)\s*\(',method).group(1)for method in methods]
 need(len(names)==len(set(names)) and set(names)==required_methods(continuation_diagnostic=True) and {'int controlState(long handle)','int configureBodyPartsCache(String absolutePath)','byte[] observedSelfPose(long handle)'}.issubset(methods),'Java API shape');need('System.loadLibrary("coh_combined_interop")'in(root/JAVA).read_text(),'DSO name')
 projection_bound={'shipping_report_limit_including_nul':7168,'full_detail_view_is_TEST_ONLY':True,'every_original_deep_assertion_executed':True,'shipping_JSON_never_enriched':True}
 receipt={'schema':'coh-bounded-shipping-and-test-only-deep-adapter-qualification-v1','passed':True,'head_read':head,'project_source_sha256':before,'compiler_and_headers_sha256':sysbefore,'ldd_resolved_dependency_sha256':libraries,'commands':commands,'results':results,'executables':binaries,'host_stack_frames':stacks,'Java_native_declarations':methods,
  'JNI_initial_controller_crypto_provider_and_request_witness_explicit_doubles':True,'historical_adapter_assertions_executed_unchanged_on_explicit_TEST_ONLY_view':True,'original_fixture_and_checker_preserved':True,'shipping_report_independently_qualified_before_test_only_view':True,'Android_NDK_JNI_ABI_or_Thor_execution':False,'actual_socket_or_original_server_transaction':False,'packet_copy_or_private_identity_export':False,'global_memory_or_RSS_fit':False,'LeakSanitizer_enabled':False,'reward_slot_body_appearance_sg_scales_partcount_projection_bound':projection_bound,'world_authority':False}
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':True,'source_inputs':len(before),'system_inputs':len(sysbefore),'modes':list(results),'checks_each':results['release']['checks'],'scenarios_each':results['release']['scenarios']}))
if __name__=='__main__':main()
