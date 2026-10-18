#!/usr/bin/env python3
"""Focused new receive role only. No original services or old qualifier main."""
from pathlib import Path
import argparse,copy,gzip,hashlib,importlib.util,json,os,re,shlex,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'native-android/engine/scenecatalog-server'))
spec=importlib.util.spec_from_file_location('new_receive_admission',HERE/'receive_admission.py');ad=importlib.util.module_from_spec(spec);spec.loader.exec_module(ad)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(value,reason):
 if not value:raise ValueError('RECEIVE_CHECK_'+reason)
def parser_controls(sample,jni):
 positive=negative=0
 def accept(v):
  nonlocal positive
  result=ad.parse(json.dumps(v).encode());need(result==v,'ROUNDTRIP');positive+=1
 def refuse(v):
  nonlocal negative
  try:ad.parse(json.dumps(v).encode())
  except Exception:negative+=1
  else:raise ValueError('RECEIVE_CHECK_FALSE_ADMISSION')
 accept(sample);need(sample['decode_declared_raw_bytes']>sample['decode_output_budget'],'DECLARATION_BOUNDARY');accept(jni['receive_diagnostics'])
 for k in ad.KEYS:
  v=copy.deepcopy(sample);v.pop(k);refuse(v)
 v=copy.deepcopy(sample);v['extra']=1;refuse(v)
 for k in ad.FALSE:
  v=copy.deepcopy(sample);v[k]=True;refuse(v)
 for k in (*ad.COUNTS,*ad.BOUNDS):
  v=copy.deepcopy(sample);v[k]=True;refuse(v)
  v=copy.deepcopy(sample);v[k]=(1000000 if k in ad.COUNTS else ad.BOUNDS[k])+1;refuse(v)
 for k in ad.BOOLS:
  v=copy.deepcopy(sample);v[k]=1;refuse(v)
 v=copy.deepcopy(sample);v['refusal']='OTHER';refuse(v)
 with tempfile.TemporaryDirectory(prefix='coh-receive-bridge-')as temporary:
  base=Path(temporary);native=base/'native';native.mkdir(mode=0o700)
  raw=(json.dumps(sample)+'\n').encode();path=native/'receive-counters.json';path.write_bytes(raw);path.chmod(0o600)
  report={'schema':'coh-private-original-native-groups-run-v1','passed':True,'cleanup_verified':True,'matching_groups_transaction_captured':True,'private_character_state':True,'public_upload_permitted':False,'source_generation_admitted':False,'world_authority':False,'native_tool':{'build_schema':ad.BUILD_SCHEMA,'initial_progress_compatibility_verified':True},'source_sha256':{ad.RELATIVE:sha((HERE/'receive_admission.py').read_bytes())},'receive_diagnostic':sample,'receive_private_binding':{'bytes':len(raw),'sha256':sha(raw),'retained_after_owned_cleanup':True,'public_upload_permitted':False}}
  need(ad.project(report,base)==sample,'PRIVATE_PROJECT');positive+=1
  for key in ('source_sha256','receive_private_binding','receive_diagnostic','native_tool'):
   changed=copy.deepcopy(report);changed[key]={}
   try:ad.project(changed,base)
   except Exception:negative+=1
   else:raise ValueError('RECEIVE_CHECK_PRIVATE_FALSE_ADMISSION')
  path.chmod(0o644)
  try:ad.project(report,base)
  except Exception:negative+=1
  else:raise ValueError('RECEIVE_CHECK_PRIVATE_MODE')
 need(not any(s in json.dumps(jni) for s in ('PRIVATE_','909090')),'PRIVATE_EXPORT')
 return{'positive':positive,'negative':negative,'retained_private_file_controls':True,'original_services_executed':False}
def qualify(output):
 need(not output.exists(),'NEW_OUTPUT');output.mkdir(parents=True)
 transition=ad.preservation(ROOT);pins=ad.compiler_dependencies(ROOT)
 cc=Path(subprocess.run(['which','cc'],capture_output=True,text=True,check=True).stdout.strip()).resolve()
 base=[str(cc),'-std=c11','-Wall','-Wextra','-Werror','-fno-pie','-no-pie','-fstack-usage','-I'+str(ROOT/'native-android/include'),'-I'+str(ROOT/'native-android/combined-client/tools')]
 jflags=['-DCOH_INTEROP_REQUEST_TX=1','-I'+str(ROOT/'native-android/engine/initial-capture'),'-I'+str(ROOT/'native-android/engine/session'),'-I'+str(ROOT/'native-android/combined-client/diagnostics/interop-adapter-20261018/test-include')]
 env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}
 commands=[];modes={};linked={};system={str(cc):sha(cc.read_bytes())}
 def run(label,command,expect=0):
  command=list(map(str,command));commands.append(command)
  result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=60,env=env)
  (output/(label+'.stdout')).write_bytes(result.stdout);(output/(label+'.stderr')).write_bytes(result.stderr)
  need(result.returncode==expect and not result.stderr,'COMMAND_'+label);return result
 dep=run('compiler-dependencies',[*base,*jflags,'-M',HERE/'capture_local_initial_receive.c',HERE/'test_receive.c',HERE/'test_jni_receive.c',ROOT/'native-android/combined-client/app/src/main/cpp/interop_network.c',*ad.recipe(ROOT)])
 for line in dep.stdout.decode().replace('\\\n',' ').splitlines():
  for token in shlex.split(line.split(':',1)[1]):
   p=Path(token).resolve()
   if not p.is_relative_to(ROOT):system[str(p)]=sha(p.read_bytes())
 version=run('compiler-version',[cc,'--version']);(output/'source-before.json').write_text(json.dumps(pins,sort_keys=True,indent=2)+'\n')
 for mode,options in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  flags=[*base,*options];unit=output/('receive-unit-'+mode)
  run(mode+'-unit-build',[*flags,HERE/'test_receive.c','-o',unit]);unit_result=json.loads(run(mode+'-unit',[unit]).stdout)
  need(unit_result['passed']is True and unit_result['scenarios']==8,'FOCUSED_UNIT')
  jni=output/('receive-jni-'+mode)
  run(mode+'-jni-build',[*flags,*jflags,ROOT/'native-android/combined-client/app/src/main/cpp/interop_network.c',HERE/'test_jni_receive.c','-Wl,--wrap=calloc','-Wl,--wrap=free','-o',jni])
  jni_result=json.loads(run(mode+'-jni',[jni]).stdout);need(jni_result['passed']is True and jni_result['scenarios']==2,'FOCUSED_JNI')
  controls=parser_controls(unit_result['sample'],jni_result['sample_report']);objects=[]
  for i,source in enumerate(ad.recipe(ROOT)):
   target=output/(mode+'-'+str(i)+'.o');run(mode+'-object-'+str(i),[*flags,*(['-O0']if source.name in('coh_protocol.c','coh_blowfish.c')else[]),'-c',source,'-o',target]);objects.append(target)
  binary=output/(mode+'-'+ad.BASENAME);run(mode+'-role-build',[*flags,HERE/'capture_local_initial_receive.c',*objects,'-Wl,--wrap=sendto','-lz','-lm','-lcrypto','-o',binary]);r=run(mode+'-role-noargs',[binary],2);need(not r.stdout,'NOARGS_STDOUT')
  executables={}
  for label,path in [('unit',unit),('jni',jni),('production_role',binary)]:
   executables[label]={'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())};(output/(path.name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
   linked_result=run(mode+'-'+label+'-ldd',['ldd',path])
   for token in re.findall(rb'/[^\s()]+',linked_result.stdout):
    file=Path(os.fsdecode(token)).resolve();linked[str(file)]=sha(file.read_bytes())
  modes[mode]={'focused_unit':unit_result,'focused_JNI':jni_result,'Python_projection_controls':controls,'production_role_bytes':binary.stat().st_size,'production_role_sha256':sha(binary.read_bytes()),'production_role_noargs_unchanged':True,'executables':executables}
  if mode=='release':(output/(ad.BASENAME+'.gz')).write_bytes(gzip.compress(binary.read_bytes(),mtime=0))
 need(pins==ad.compiler_dependencies(ROOT),'SOURCE_CHANGED');need(all(sha(Path(p).read_bytes())==h for p,h in system.items()),'COMPILER_HEADERS_CHANGED');need(all(sha(Path(p).read_bytes())==h for p,h in linked.items()),'LINKED_FILES_CHANGED')
 frames=[]
 for file in output.glob('*.su'):
  for line in file.read_text().splitlines():
   location,size,kind=line.split('\t');need('unbounded'not in kind,'UNBOUNDED_FRAME');frames.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'kind':kind})
 need(frames and max(v['bytes']for v in frames)<512*1024,'EXISTING_HOST_STACK_LIMIT')
 proof={'schema':ad.BUILD_SCHEMA,'passed':True,'source_revision':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip(),'source_sha256':pins,'compiler_and_headers_sha256':system,'ldd_resolved_dependencies_sha256':linked,'transition':transition,'modes':modes,'commands':commands,'host_stack_frames':frames,'old_qualifier_or_fixture_entrypoints_executed':False,'original_server_executed':False,'actual_source_protocol_session_executed':False,'default_network_map_local_initial_sources_changed':False,'complete_global_aggregate_or_RSS_fit':False,'world_authority':False,'leak_sanitizer_enabled':False,'retained_ELFs_scope':'three new-role/noargs, three new projection doubles, three new JNI projection doubles; no old main invoked'}
 (output/'qualification.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n');print(json.dumps({'passed':True,'source_pins':len(pins),'compiler_headers':len(system),'linked_files':len(linked),'modes':{k:{'unit_checks':v['focused_unit']['checks'],'JNI_checks':v['focused_JNI']['checks'],'parser':v['Python_projection_controls']}for k,v in modes.items()}}))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();qualify(args.output.resolve())
