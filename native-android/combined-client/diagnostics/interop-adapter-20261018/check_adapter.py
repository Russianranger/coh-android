#!/usr/bin/env python3
"""New JNI control flow against explicit JNI/core/provider doubles, no Android."""
from pathlib import Path
import argparse,hashlib,json,os,re,shlex,shutil,subprocess,gzip
BASE=Path('native-android/combined-client/diagnostics/interop-adapter-20261018')
SOURCE=Path('native-android/combined-client/app/src/main/cpp/interop_network.c')
JAVA=Path('native-android/combined-client/app/src/main/java/org/coh/nativecombined/InteropNative.java')
def need(value,message):
 if not value:raise ValueError(message)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(command,root,env=None):return subprocess.run(list(map(str,command)),cwd=root,env=env,capture_output=True,timeout=40)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 root,out=args.source_root.resolve(),args.output.resolve();need(not out.exists()and root not in out.parents,'fresh external output required');out.mkdir()
 compiler=Path(shutil.which(os.environ.get('CC','cc'))).resolve();flags=[str(compiler),'-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fno-pie','-no-pie','-fstack-usage','-DCOH_INTEROP_REQUEST_TX=1',
  '-I',str(BASE/'test-include'),'-I','native-android/engine/initial-capture','-I','native-android/engine/session','-I','native-android/include']
 sources=[SOURCE,BASE/'test_interop_adapter.c',Path('native-android/engine/initial-capture/coh_initial_create_probe.c'),Path('native-android/engine/initial-capture/coh_initial_pose_probe.c'),Path('native-android/engine/initial-capture/coh_initial_sequence_probe.c'),Path('native-android/engine/initial-capture/coh_initial_triggered_probe.c'),Path('native-android/engine/initial-capture/coh_initial_aianim_probe.c'),Path('native-android/engine/initial-capture/coh_initial_netfx_probe.c'),Path('native-android/engine/initial-capture/coh_initial_costume_probe.c'),Path('native-android/engine/initial-capture/coh_initial_reward_probe.c'),Path('native-android/engine/initial-capture/coh_initial_reward_list_probe.c'),Path('native-android/engine/initial-capture/coh_initial_costume_slots_probe.c'),Path('native-android/engine/initial-capture/coh_initial_costume_body_probe.c'),Path('native-android/engine/initial-capture/coh_initial_appearance_probe.c'),Path('native-android/engine/initial-capture/coh_initial_sgcolors_probe.c'),Path('native-android/engine/initial-capture/coh_initial_scales_probe.c'),Path('native-android/engine/initial-capture/coh_initial_partcount_probe.c'),Path('native-android/engine/entities/coh_entities.c'),Path('native-android/engine/replication/coh_replication.c')];dep=run([*flags,'-M',*sources],root);(out/'dependencies.stdout').write_bytes(dep.stdout);(out/'dependencies.stderr').write_bytes(dep.stderr);need(dep.returncode==0 and not dep.stderr,'dependencies refused')
 project={BASE/'check_adapter.py',JAVA};system={compiler}
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
  binary=out/('adapter-'+mode);command=[*flags,*options,*sources,'-Wl,--wrap=calloc','-Wl,--wrap=free','-lm','-o',binary];commands.append(list(map(str,command)));c=run(command,root)
  (out/(mode+'-compile.stdout')).write_bytes(c.stdout);(out/(mode+'-compile.stderr')).write_bytes(c.stderr);need(c.returncode==0 and not c.stderr,'compile refused '+mode)
  binaries[mode]={'bytes':binary.stat().st_size,'sha256':sha(binary),'retained_gzip':binary.name+'.gz'}
  (out/(binary.name+'.gz')).write_bytes(gzip.compress(binary.read_bytes(),mtime=0))
  linked=run(['ldd',binary],root);(out/(mode+'-ldd.txt')).write_bytes(linked.stdout+linked.stderr);need(linked.returncode==0,'ldd refused')
  for value in re.findall(rb'/[^\s()]+',linked.stdout):
   p=Path(os.fsdecode(value)).resolve();need(p.is_file(),'nonregular link dependency');libraries[str(p)]=sha(p)
  child=run([binary],root,environment);(out/(mode+'-child.stdout')).write_bytes(child.stdout);(out/(mode+'-child.stderr')).write_bytes(child.stderr);need(child.returncode==0 and not child.stderr,'new adapter child refused '+mode)
  result=json.loads(child.stdout);need(result['passed']is True and result['JNI_and_initial_capture_explicit_doubles']is True and result['actual_Android_or_protocol_or_original_server']is False and result['world_authority']is False,'scope drift');results[mode]=result
  frames=[]
  for p in out.glob(binary.name+'-*.su'):
   for line in p.read_text().splitlines():
    where,size,kind=line.split('\t');need('unbounded'not in kind,'unbounded frame');frames.append({'function':where.rsplit(':',1)[-1],'bytes':int(size),'kind':kind})
  stacks[mode]=frames
 need(all(v==results['release']for v in results.values()),'cross-mode controls differ')
 (out/'source-after.json').write_text(json.dumps({str(p):sha(root/p)for p in sorted(project)},indent=2,sort_keys=True)+'\n')
 need(before=={str(p):sha(root/p)for p in sorted(project)},'source changed');need(sysbefore=={str(p):sha(p)for p in sorted(system)},'compiler/header changed')
 need(all(sha(out/('adapter-'+m))==v['sha256']for m,v in binaries.items()),'binary changed');need(all(sha(Path(p))==v for p,v in libraries.items()),'linked dependency changed')
 methods=re.findall(r'public static native ([^;]+);',(root/JAVA).read_text());need(len(methods)==8,'Java API shape');need('System.loadLibrary("coh_combined_interop")'in(root/JAVA).read_text(),'DSO name')
 projection_bound={}
 sample=results['release']['sample_report'];first=sample.get('first_reward_string')
 if isinstance(first,dict)and'progress'in first:
  # Bound the newly added progress and first-literal scalar domains while
  # preserving all other observed full-report fields. Not a claim about every
  # possible transport-counter combination or global RSS.
  bounds=[]
  for progress in ([4,6,2,255,256,256,4*1024*1024*8,1,6],
                   [4,13,256,256,4*1024*1024*8,40,(1<<23)-1],
                   [4,26,256,256,4*1024*1024*8,4264,(1<<27)-1],
                   [2,32,256,256,4*1024*1024*8,4352,(1<<28)-1],
                   [2,34,256,256,4*1024*1024*8,6656,(1<<28)-1],
                   [2,37,256,256,4*1024*1024*8,7616,(1<<27)-1],
                   [4,42,256,256,4*1024*1024*8,7656,(1<<29)-1]):
   worst=json.loads(json.dumps(sample));child=worst['first_reward_string']
   child.update(bit=4*1024*1024*8,bytes=259,progress=progress)
   full_bytes=len(json.dumps(worst,separators=(',',':')).encode());child_bytes=len(json.dumps(child,separators=(',',':')).encode())
   need(full_bytes<7168 and child_bytes<192,'bounded continuation projection exceeds existing report limits')
   bounds.append({'full_report_bytes':full_bytes,'child_bytes':child_bytes,'progress':progress})
  projection_bound={'variants':bounds,'total_limit_including_nul':7168,'child_limit_including_nul':192,'other_fields_are_observed_fixture_values':True}
 receipt={'schema':'coh-new-interop-jni-adapter-host-qualification-v1','passed':True,'head_read':head,'project_source_sha256':before,'compiler_and_headers_sha256':sysbefore,'ldd_resolved_dependency_sha256':libraries,'commands':commands,'results':results,'executables':binaries,'host_stack_frames':stacks,'Java_native_declarations':methods,
  'JNI_initial_controller_crypto_provider_and_request_witness_explicit_doubles':True,'original_native_qualifiers_or_fixture_entrypoints_replayed':False,'Android_NDK_JNI_ABI_or_Thor_execution':False,'actual_socket_or_original_server_transaction':False,'packet_copy_or_private_identity_export':False,'global_memory_or_RSS_fit':False,'LeakSanitizer_enabled':False,'reward_slot_body_appearance_sg_scales_partcount_projection_bound':projection_bound,'world_authority':False}
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':True,'source_inputs':len(before),'system_inputs':len(sysbefore),'modes':list(results),'checks_each':results['release']['checks'],'scenarios_each':results['release']['scenarios']}))
if __name__=='__main__':main()
