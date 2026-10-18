#!/usr/bin/env python3
"""Read-only retained-data audit; never invokes a compiler, device or ELF."""
import argparse,hashlib,importlib.util,json,os,re,shlex,stat,struct,subprocess,sys,tempfile,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
REVISION='c98bb60fe187458f328a15882089ea742ce6e853'
ARCHIVE_SHA='55eb2466fc7701c6bc49d736677321c29b2672754e673aabdb4f88c952413bea'
WR=Path('native-android/engine/world-render-adapter')
def need(value,code):
 if not value:raise ValueError(code)
def sha(data):return hashlib.sha256(data).hexdigest()
def pin(data):return {'bytes':len(data),'sha256':sha(data)}
def pairs(rows):
 out={}
 for name,value in rows:need(name not in out,'DUPLICATE_JSON');out[name]=value
 return out
def decoded(data):return json.loads(data,object_pairs_hook=pairs)
def git(root,*args):return subprocess.run(['git','-C',root,*args],check=True,capture_output=True,timeout=30).stdout
def main():
 need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'),'ASSERTIONS_REQUIRED')
 parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True);args=parser.parse_args()
 root=args.source_root.resolve();base=Path(__file__).resolve().parent;raw=(base/'retained-artifact.zip').read_bytes()
 need(pin(raw)=={'bytes':154504,'sha256':ARCHIVE_SHA},'EXACT_ARCHIVE')
 with zipfile.ZipFile(base/'retained-artifact.zip') as z:
  rows=z.infolist();need(len(rows)==92 and len({x.filename for x in rows})==92 and z.testzip() is None,'ZIP_INVENTORY_CRC')
  members={}
  for row in rows:
   path=Path(row.filename)
   need(not path.is_absolute() and '..' not in path.parts and '\\' not in row.filename and not row.flag_bits&1
        and stat.S_ISREG(row.external_attr>>16) and row.file_size<=1024*1024,'SAFE_MEMBER')
   members[row.filename]=z.read(row)
 manifest=decoded((base/'archive-members.json').read_bytes())
 need(manifest['archive']==pin(raw) and set(manifest['members'])==set(members),'MEMBER_MANIFEST')
 for name,data in members.items():need(pin(data)=={k:manifest['members'][name][k] for k in ('bytes','sha256')},'EVERY_MEMBER_HASH')
 q=decoded(members['build/build.json']);e=decoded(members['execution/receipt.json'])
 metadata=decoded((base/'github-artifacts.json').read_bytes())['artifacts'];jobs=decoded((base/'github-jobs.json').read_bytes())['jobs']
 need(len(metadata)==len(jobs)==1,'ONE_ACTUAL_ARTIFACT_JOB');artifact=metadata[0];job=jobs[0]
 need(artifact['id']==12119502992 and artifact['size_in_bytes']==len(raw) and artifact['digest']=='sha256:'+ARCHIVE_SHA
      and artifact['workflow_run']['id']==39083677877 and artifact['workflow_run']['head_sha']==REVISION
      and artifact['workflow_run']['head_branch']=='native-android' and artifact['expired'] is False,'API_ARTIFACT_BINDING')
 need(job['id']==117545684612 and job['run_id']==39083677877 and job['status']=='completed' and job['conclusion']=='success'
      and all(x['status']=='completed' and x['conclusion']=='success' for x in job['steps']),'ACTUAL_SUCCESS_JOB')
 need(q['schema']=='coh-source-rgba32-android-build-v1' and q['passed'] is True and q['source_revision']==REVISION
      and q['source_tree']==git(root,'rev-parse',REVISION+'^{tree}').decode().strip(),'BUILD_SOURCE_REVISION_TREE')
 source=q['source_sha256'];need(len(source)==28,'EXACT_SOURCE_PIN_COUNT')
 for name,digest in source.items():
  need(sha((root/name).read_bytes())==digest==sha(git(root,'show',REVISION+':'+name)),'CURRENT_AND_COMMITTED_SOURCE')
 # Import only exact admitted helpers. Their main functions are not called.
 modules={}
 for short,name in [('checker','check_source_rgba32_gpu.py'),('driver','tests/run_source_rgba32_android.py')]:
  path=root/WR/name;data=path.read_bytes();need(sha(data)==source[(WR/name).as_posix()],'HELPER_BEFORE_IMPORT')
  spec=importlib.util.spec_from_file_location('retained_rgba32_'+short,path);module=importlib.util.module_from_spec(spec)
  sys.modules[spec.name]=module;exec(compile(data,str(path),'exec'),module.__dict__);modules[short]=module
 checker=modules['checker'];driver=modules['driver']
 for key,value in driver.FALSE_SCOPE.items():need(q.get(key) is value and e.get(key) is value,'FALSE_AUTHORITY_SCOPE')
 need(q['api_level']==26 and q['ndk_revision']=='28.2.13676358' and q['android_executed'] is False
      and q['host_GLES_executed'] is False and set(q['android'])=={'arm64-v8a','x86_64'},'BUILD_SCOPE')
 need(q['actual_default_artifact']==pin(members['build/actual-defaults.zip'])
      =={'bytes':12308,'sha256':checker.ZIP_SHA},'RETAINED_ORIGINAL_FIXTURE')
 original=root/'native-android/combined-client/diagnostics/continuation-f-20261017/actual-groups-39078874753/default-bodies-artifact.zip'
 need(original.read_bytes()==members['build/actual-defaults.zip']==git(root,'show',REVISION+':'+original.relative_to(root).as_posix()),'TRACKED_SOURCE_ARCHIVE')
 with tempfile.TemporaryDirectory(prefix='coh-retained-rgba32-admission-') as temporary:
  archive=Path(temporary)/'actual-defaults.zip';archive.write_bytes(members['build/actual-defaults.zip'])
  fixture=checker.prepare_fixture(archive,Path(temporary)/'input');need(fixture==q['fixture'],'DETERMINISTIC_FIXTURE_REGENERATION')
  for name,expected in fixture['files'].items():need(pin(members['build/input/'+name])==expected,'ALL_FOUR_FIXTURE_BYTES')
 readback=members['execution/readback.rgba'];need((base/'readback.rgba').read_bytes()==readback,'PRESERVED_READBACK')
 native=checker.validate_result(members['execution/adb-023.stdout'],base/'readback.rgba',q['fixture'])
 need(native==e['native'] and decoded((base/'native.json').read_bytes())==native,'EXACT_NATIVE_RECORD')
 abi_results={};compiled={p.relative_to(root).as_posix() for p in checker.project_sources(root)};need(len(compiled)==10,'TEN_TRANSLATION_UNITS')
 for abi,machine in [('arm64-v8a',183),('x86_64',62)]:
  item=q['android'][abi];body=members['build/android/'+abi+'/coh_source_rgba32_gpu'];path=base/(abi+'.elf')
  need(item['built'] is True and item['executed'] is False and pin(body)==item['binary'] and path.read_bytes()==body,'BOTH_RETAINED_ELFS')
  driver.elf(path,machine);need(item['elf_machine']==machine,'ELF_MACHINE')
  phoff=struct.unpack_from('<Q',body,32)[0];entry,count=struct.unpack_from('<HH',body,54);loads=[];dynamic=[]
  for index in range(count):
   values=struct.unpack_from('<II6Q',body,phoff+index*entry);kind,_,offset,vaddr,_,size,_,_=values
   if kind==1:loads.append((vaddr,size,offset))
   if kind==2:
    for at in range(offset,offset+size,16):
     tag,value=struct.unpack_from('<qQ',body,at)
     if tag==0:break
     dynamic.append((tag,value))
  strings=[value for tag,value in dynamic if tag==5];sizes=[value for tag,value in dynamic if tag==10]
  need(len(strings)==len(sizes)==1,'ONE_DYNAMIC_STRING_TABLE');address=strings[0];length=sizes[0]
  candidates=[offset+address-vaddr for vaddr,size,offset in loads if vaddr<=address and address-vaddr+length<=size]
  need(len(candidates)==1,'DYNAMIC_STRING_TABLE_BOUNDS');table=body[candidates[0]:candidates[0]+length]
  needed=[]
  for tag,value in dynamic:
   if tag==1:
    need(value<len(table) and b'\0' in table[value:],'NEEDED_STRING_BOUNDS');needed.append(table[value:].split(b'\0',1)[0].decode('ascii'))
  needed=sorted(needed);text=members['build/android/'+abi+'/dynamic.txt'].decode()
  need(needed==item['needed_libraries']==sorted(re.findall(r'Shared library: \[([^\]]+)\]',text))
       and set(needed)=={'libEGL.so','libGLESv3.so','libc.so','libdl.so','libm.so','libz.so'},'ACTUAL_ELF_PLATFORM_LIBRARIES')
  observed=set()
  for line in members['build/android/'+abi+'/dependencies.stdout'].decode().replace('\\\n',' ').splitlines():
   for token in shlex.split(line.split(':',1)[1]):
    if token.endswith('/out/source-rgba32-android/build/input/source_rgba32_fixture.h'):continue
    need('/native-android/' in token,'PROJECT_DEPENDENCY_BOUNDARY');observed.add(os.path.normpath('native-android/'+token.split('/native-android/',1)[1]))
  need(len(observed)==25 and observed==set(item['project_dependencies_sha256']),'EXACT_COMPILER_DEPENDENCIES')
  for name,digest in item['project_dependencies_sha256'].items():need(source[name]==digest,'SAME_DEPENDENCY_SOURCE_BYTES')
  command=item['compile_command'];actual={x[x.index('native-android/'):] for x in command if x.endswith('.c')}
  need(actual==compiled and sum(x.endswith('.c') for x in command)==10
       and all(x in command for x in ('-O2','-fPIE','-pie','-Wl,--wrap=calloc','-Wl,--wrap=free')),'EXACT_COMPILED_CLOSURE')
  abi_results[abi]={'binary':pin(body),'elf_machine':machine,'ELF64_little_endian_PIE_linker64':True,'actual_needed_libraries':needed,'project_dependencies':25,'executed':abi=='x86_64'}
 need(len(q['ndk_files_sha256'])==26 and q['ndk_dependency_files_sha256']=={}
      and all(not Path(name).is_absolute() and '..' not in Path(name).parts and re.fullmatch('[0-9a-f]{64}',value) for name,value in q['ndk_files_sha256'].items()),'DECLARED_NDK_PIN_INVENTORY')
 need(e['schema']=='coh-source-rgba32-android13-execution-v1' and e['source_revision']==REVISION
      and e['build_receipt']==pin(members['build/build.json']) and e['readback']==pin(readback),'EXACT_EXECUTION_BINDING')
 for name in ('passed','android_executed','native_execution_attempted','native_process_completed','device_path_cleanup_verified',
              'native_process_cleanup_verified','device_cleanup_verified','post_source_artifact_admission_verified'):
  need(e[name] is True,'SUCCESSFUL_NATIVE_AND_CLEANUP_'+name)
 need(e['process_cleanup_unobserved'] is False and e['arm64_executed'] is False,'PROCESS_AND_ABI_SCOPE')
 need(e['platform_library_files_before']==e['platform_library_files_after'],'DECLARED_PLATFORM_FILE_STABILITY')
 for index in range(34,37):
  need(members['execution/adb-%03d.stdout'%index]==members['execution/adb-%03d.stderr'%index]==b'','SUCCESSFUL_PATH_CLEANUP_LOGS')
 for index,platform in enumerate(driver.PLATFORM,5):
  for n in (index,index+26):
   line=members['execution/adb-%03d.stdout'%n].decode().strip()
   need(line==e['platform_library_files_before'][platform]+'  '+platform,'ACTUAL_PLATFORM_FILE_LOGS')
 workflow='.github/workflows/native-source-rgba32-android.yml';workflow_bytes=git(root,'show',REVISION+':'+workflow)
 need((root/workflow).read_bytes()==workflow_bytes and b'dfb20d396df28ca02a8c708314b814a4d961dc9074f9a161932746f815aa552f' in workflow_bytes,'COMMITTED_WORKFLOW_NDK_ZIP_PIN')
 for name,digest in source.items():need(sha((root/name).read_bytes())==digest,'FINAL_SOURCE_BYTES')
 need((base/'retained-artifact.zip').read_bytes()==raw,'FINAL_ARCHIVE_BYTES')
 report={'schema':'coh-source-rgba32-android-retained-audit-v1','passed':True,'source_revision':REVISION,'source_tree':q['source_tree'],
  'workflow_run_id':39083677877,'job_id':117545684612,'artifact_id':12119502992,'artifact':pin(raw),'archive_members_verified':92,
  'current_and_committed_source_pins_verified':28,'workflow':{'path':workflow,**pin(workflow_bytes)},'abis':abi_results,
  'native_checks':native['checks'],'readbacks':native['readbacks'],'readback':pin(readback),'declared_NDK_file_pins_retained':26,
  'NDK_files_independently_rehashed_after_download':False,'fixture_regeneration_data_only':True,'native_cleanup':native['cleanup_verified'],
  'process_completion_verified':True,'path_cleanup_verified':True,'post_source_admission_verified':True,
  'platform_loaded_mapping_verified':False,'platform_driver_sanitized':False,'android_sanitizers_enabled':False,
  'application_or_apk_built':False,'application_context_adopted':False,'physical_android_device_executed':False,
  'current_namespace_admitted':False,'default_identity_admitted':False,'material_authority':False,'actor_authority':False,'world_authority':False,
  'old_qualifiers_replayed':False,'native_executables_replayed':False,'artifact_downloaded_by_this_audit':False,'audit_script':pin(Path(__file__).read_bytes())}
 with (base/'audit.json').open('x') as stream:json.dump(report,stream,indent=2,sort_keys=True);stream.write('\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
