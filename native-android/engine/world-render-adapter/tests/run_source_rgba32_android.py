#!/usr/bin/env python3
"""Build source-bound standalone fixtures; execute only the Android13 x86_64 test."""
import argparse,hashlib,importlib.util,json,os,re,secrets,shlex,struct,subprocess,sys,tempfile
from pathlib import Path

sys.dont_write_bytecode=True
RELATIVE=Path('native-android/engine/world-render-adapter')
ABI={'arm64-v8a':('aarch64-linux-android26-clang','aarch64-linux-android',183),
     'x86_64':('x86_64-linux-android26-clang','x86_64-linux-android',62)}
FIXTURES=('grey.texture','pattern.texture','legacy.texture','source_rgba32_fixture.h')
PLATFORM=('/system/lib64/libEGL.so','/system/lib64/libGLESv3.so','/system/lib64/libz.so')
FALSE_SCOPE={'current_namespace_admitted':False,'current_generation_admitted':False,
 'default_identity_admitted':False,'material_authority':False,'actor_authority':False,
 'world_authority':False,'production_prepare_executed':False,
 'nine_world_prerequisites_admitted':False,'application_or_apk_built':False,
 'application_context_adopted':False,'physical_android_device_executed':False,
 'android_sanitizers_enabled':False,'platform_loaded_mapping_verified':False,
 'platform_driver_sanitized':False,'finite_fixture_digest_is_general_sha256':False,
 'RSS_or_global_budget_claim':False}

def need(ok,code):
 if not ok:raise ValueError(code)
def sha(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def regular(path,maximum=32*1024**2):
 path=Path(path);need(not path.is_symlink() and path.is_file() and 0<=path.stat().st_size<=maximum,'REGULAR_BOUNDED_INPUT');return path
def identity(path):
 path=regular(path);return {'bytes':path.stat().st_size,'sha256':sha(path)}
def emit(path,value):
 with Path(path).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def fresh(path):
 path=Path(path).absolute();need(not path.exists() and not path.is_symlink(),'FRESH_OUTPUT_REQUIRED');path.mkdir(parents=True);return path
def command(args,timeout=180,logs=None):
 process=subprocess.run(list(map(str,args)),capture_output=True,timeout=timeout)
 need(len(process.stdout)+len(process.stderr)<=4*1024**2,'BOUNDED_CHILD_OUTPUT')
 if logs is not None:
  Path(str(logs)+'.stdout').write_bytes(process.stdout);Path(str(logs)+'.stderr').write_bytes(process.stderr)
 need(process.returncode==0,'CHILD_OPERATION_FAILED');return process.stdout
def git(root,*args):return command(['git','-C',root,*args],30).decode().strip()
def source_pin(root,path):
 path=Path(path).absolute();regular(path);name=path.relative_to(root).as_posix()
 need(path.resolve()==path,'CANONICAL_PROJECT_FILE');return name,sha(path)
def same_checkout(root,revision):
 need(git(root,'rev-parse','HEAD')==revision,'SOURCE_REVISION_CHANGED')
 if os.environ.get('GITHUB_SHA'):need(os.environ['GITHUB_SHA']==revision,'EXACT_CI_CHECKOUT')
def load_checker(root):
 need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'),'ASSERTIONS_REQUIRED')
 root=root.resolve();driver=root/RELATIVE/'tests/run_source_rgba32_android.py';checker=root/RELATIVE/'check_source_rgba32_gpu.py'
 need(Path(__file__).resolve()==driver,'SOURCE_OWNED_DRIVER')
 revision=git(root,'rev-parse','HEAD');same_checkout(root,revision)
 pins=dict(source_pin(root,path) for path in (driver,checker))
 for name,digest in pins.items():
  need(hashlib.sha256(command(['git','-C',root,'show',revision+':'+name],30)).hexdigest()==digest,'COMMITTED_DRIVER_AND_CHECKER')
 raw=checker.read_bytes();need(hashlib.sha256(raw).hexdigest()==pins[checker.relative_to(root).as_posix()],'CHECKER_BEFORE_IMPORT')
 spec=importlib.util.spec_from_file_location('source_rgba32_android_checker',checker);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
 exec(compile(raw,str(checker),'exec'),module.__dict__)
 module.committed_sources(root,pins,revision);same_checkout(root,revision)
 return root,module,revision,pins
def elf(path,machine):
 raw=regular(path,16*1024**2).read_bytes()
 need(len(raw)>=64 and raw[:7]==b'\x7fELF\x02\x01\x01' and struct.unpack_from('<HHI',raw,16)==(3,machine,1)
      and struct.unpack_from('<H',raw,52)[0]==64,'ANDROID_ABI_PIE')
 offset=struct.unpack_from('<Q',raw,32)[0];size,count=struct.unpack_from('<HH',raw,54)
 need(size==56 and 2<=count<=128 and offset<=len(raw)-size*count,'ELF_PROGRAM_HEADERS')
 kinds=set();interpreters=[]
 for i in range(count):
  at=offset+i*size;kind=struct.unpack_from('<I',raw,at)[0];start=struct.unpack_from('<Q',raw,at+8)[0];files,memory=struct.unpack_from('<QQ',raw,at+32)
  need(start<=len(raw) and files<=len(raw)-start and (kind!=1 or files<=memory),'ELF_SEGMENT_BOUNDS');kinds.add(kind)
  if kind==3:interpreters.append(raw[start:start+files])
 need({1,2,3}<=kinds and interpreters==[b'/system/bin/linker64\0'],'ANDROID_LINKER64')
def ndk_pins(root,ndk):
 ndk=ndk.resolve();tool=ndk/'toolchains/llvm/prebuilt/linux-x86_64'
 need('Pkg.Revision = 28.2.13676358' in regular(ndk/'source.properties',16384).read_text(),'NDKR28C_REQUIRED')
 header_names=json.loads(regular(root/RELATIVE/'egl-host-header-pins.json',65536).read_bytes())
 paths=[ndk/'source.properties']+[tool/'bin'/name for name in ('clang','ld.lld','llvm-readelf')]
 paths += [tool/'bin'/item[0] for item in ABI.values()]
 paths += [tool/'sysroot/usr/include'/name for name in header_names]
 for _,triplet,_ in ABI.values():
  paths += [tool/'sysroot/usr/lib'/triplet/'26'/name for name in ('libEGL.so','libGLESv3.so','libz.so','libm.so','libc.so','libdl.so')]
 result={}
 for path in paths:
  resolved=path.resolve();need(resolved.is_relative_to(ndk),'NDK_TOOLCHAIN_CONTAINMENT');regular(resolved,256*1024**2)
  result[path.relative_to(ndk).as_posix()]=sha(resolved)
  result[resolved.relative_to(ndk).as_posix()]=sha(resolved)
 return result
def fixture_admit(directory,fixture):
 need(type(fixture)is dict and set(fixture['files'])==set(FIXTURES),'FIXED_FIXTURE_INVENTORY')
 need({p.name for p in directory.iterdir()}==set(FIXTURES),'FIXED_FIXTURE_DIRECTORY')
 for name in FIXTURES:need(identity(directory/name)==fixture['files'][name],'FIXTURE_BYTES_CHANGED')
 expected=fixture['expected_readback']
 need(set(expected)=={'bytes','sha256'} and type(expected['bytes'])is int and 0<expected['bytes']<=16*1024**2
      and type(expected['sha256'])is str and re.fullmatch('[0-9a-f]{64}',expected['sha256']),'READBACK_EXPECTATION')
def dependency_pins(raw,root,header,ndk):
 project={};system={}
 for line in raw.decode().replace('\\\n',' ').splitlines():
  need(':' in line,'COMPILER_DEPENDENCY_SHAPE')
  for name in shlex.split(line.split(':',1)[1]):
   path=Path(name).resolve()
   if path==header:continue
   if path.is_relative_to(root):project.update([source_pin(root,path)])
   else:
    need(path.is_relative_to(ndk),'COMPILER_DEPENDENCY_BOUNDARY');regular(path,256*1024**2);system[path.relative_to(ndk).as_posix()]=sha(path)
 return project,system
def build(root,module,revision,driver_pins,args):
 output=fresh(args.output);receipt={'schema':'coh-source-rgba32-android-build-v1','passed':False,'source_revision':revision,**FALSE_SCOPE}
 try:
  ndk=args.ndk.resolve();tool=ndk/'toolchains/llvm/prebuilt/linux-x86_64';ndk_before=ndk_pins(root,ndk)
  archive=regular(args.actual_defaults_zip,12308);archive_pin=identity(archive)
  need(archive_pin=={'bytes':12308,'sha256':'87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24'},'EXACT_RETAINED_DEFAULT_ARTIFACT')
  with archive.open('rb') as stream:archive_bytes=stream.read(12309)
  need(len(archive_bytes)==archive_pin['bytes'] and hashlib.sha256(archive_bytes).hexdigest()==archive_pin['sha256'],'SOURCE_ARTIFACT_COPY')
  retained=output/'actual-defaults.zip';retained.write_bytes(archive_bytes)
  fixture=module.prepare_fixture(retained,output/'input');fixture_admit(output/'input',fixture)
  sources=[Path(p).resolve() for p in module.project_sources(root)]
  need(len(sources)==10 and len(set(sources))==10,'TEN_REAL_TRANSLATION_UNITS')
  expected=[root/RELATIVE/name for name in ('coh_wr_gpu_lease.c','coh_wr_gpu_texture.c','coh_wr_texture.c','coh_wr_sampler.c','coh_wr_tex_rgba32.c','coh_wr_tex_namespace.c','tests/test_source_rgba32_gpu.c')]
  expected += [root/'native-android/engine/assets/coh_asset_loader.c',root/'native-android/src/coh_assets.c',root/'native-android/src/coh_dds.c']
  need(set(sources)==set(expected),'EXACT_PRODUCTION_AND_TEST_SOURCES')
  pins=dict(driver_pins);pins.update(source_pin(root,p) for p in sources);pins.update([source_pin(root,root/RELATIVE/'egl-host-header-pins.json')])
  module.committed_sources(root,pins,revision);same_checkout(root,revision)
  header=(output/'input/source_rgba32_fixture.h').resolve();android={};system_dependencies={}
  common=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fno-fast-math','-ffp-contract=off','-O2','-fPIE',
          '-I'+str(root/'native-android/include'),'-I'+str(header.parent)]
  for abi,(compiler,_,machine) in ABI.items():
   cc=tool/'bin'/compiler;directory=output/'android'/abi;directory.mkdir(parents=True)
   dependencies=command([cc,*common,'-MM',*sources],logs=directory/'dependencies')
   project,system=dependency_pins(dependencies,root,header,ndk);pins.update(project);system_dependencies.update(system)
   same_checkout(root,revision);module.committed_sources(root,pins,revision);fixture_admit(output/'input',fixture)
   need(ndk_pins(root,ndk)==ndk_before,'PRECOMPILE_NDK_BYTES')
   binary=directory/'coh_source_rgba32_gpu';argv=[cc,*common,'-pie',*sources,'-Wl,--wrap=calloc','-Wl,--wrap=free','-lEGL','-lGLESv3','-lz','-lm','-o',binary]
   command(argv,logs=directory/'compile');elf(binary,machine)
   dynamic=command([tool/'bin/llvm-readelf','--dynamic',binary]);(directory/'dynamic.txt').write_bytes(dynamic)
   needed=sorted(re.findall(r'Shared library: \[([^\]]+)\]',dynamic.decode()))
   need({'libEGL.so','libGLESv3.so','libz.so','libc.so'}<=set(needed)
        and set(needed)<={'libEGL.so','libGLESv3.so','libz.so','libm.so','libc.so','libdl.so'},'PLATFORM_ONLY_DYNAMIC_LIBRARIES')
   android[abi]={'built':True,'executed':False,'binary':identity(binary),'elf_machine':machine,
                 'compile_command':list(map(str,argv)),'needed_libraries':needed,'project_dependencies_sha256':project}
   module.committed_sources(root,pins,revision);same_checkout(root,revision)
  need(ndk_pins(root,ndk)==ndk_before,'POSTCOMPILE_NDK_BYTES')
  for name,pin in system_dependencies.items():need(sha(ndk/name)==pin,'NDK_DEPENDENCY_CHANGED')
  fixture_admit(output/'input',fixture);need(identity(archive)==archive_pin and identity(retained)==archive_pin,'SOURCE_ARTIFACT_CHANGED');module.committed_sources(root,pins,revision)
  receipt.update({'passed':True,'source_tree':git(root,'rev-parse','HEAD^{tree}'),'source_sha256':pins,
    'fixture':fixture,'actual_default_artifact':archive_pin,'api_level':26,'ndk_revision':'28.2.13676358',
    'ndk_files_sha256':ndk_before,'ndk_dependency_files_sha256':system_dependencies,
    'android':android,'android_executed':False,'host_GLES_executed':False})
 except Exception:
  receipt['failure_code']='SOURCE_RGBA32_ANDROID_BUILD_REFUSED';raise
 finally:emit(output/'build.json',receipt)
 print(json.dumps({'passed':True,'android_built':list(ABI),'android_executed':False,'world_authority':False}))
def admit_build(root,module,revision,driver_pins,directory):
 regular(directory/'build.json',2*1024**2);q=json.loads((directory/'build.json').read_bytes())
 need(q['schema']=='coh-source-rgba32-android-build-v1' and q['passed']is True and q['source_revision']==revision
      and q['source_tree']==git(root,'rev-parse','HEAD^{tree}'),'EXACT_BUILD_SOURCE')
 need(q['api_level']==26 and q['ndk_revision']=='28.2.13676358' and set(q['android'])==set(ABI)
      and q['android_executed']is False and q['host_GLES_executed']is False,'BUILD_SCOPE')
 for key,value in FALSE_SCOPE.items():need(q.get(key)is value,'BUILD_AUTHORITY_FALSE')
 for name,pin in driver_pins.items():need(q['source_sha256'].get(name)==pin,'SAME_DRIVER_CHECKER')
 same_checkout(root,revision);module.committed_sources(root,q['source_sha256'],revision);fixture_admit(directory/'input',q['fixture'])
 need(q['actual_default_artifact']=={'bytes':12308,'sha256':'87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24'},'ARTIFACT_IDENTITY')
 need(identity(directory/'actual-defaults.zip')==q['actual_default_artifact'],'RETAINED_ARTIFACT_BYTES')
 # Recreate the controlled pattern, finite fixture header and readback receipt
 # from the exact tiny source archive; a self-consistent edited JSON map alone
 # cannot substitute a different fixture. This performs no build or GL work.
 with tempfile.TemporaryDirectory(prefix='coh-rgba32-fixture-admission-') as temporary:
  regenerated=module.prepare_fixture(directory/'actual-defaults.zip',Path(temporary)/'input')
  need(regenerated==q['fixture'],'SOURCE_REGENERATED_FIXTURE_RECEIPT')
  fixture_admit(Path(temporary)/'input',regenerated)
 for abi,(_,_,machine) in ABI.items():
  item=q['android'][abi];binary=directory/'android'/abi/'coh_source_rgba32_gpu'
  need(item['built']is True and item['executed']is False and item['elf_machine']==machine and identity(binary)==item['binary'],'EXACT_TWO_ABI_EXECUTABLES');elf(binary,machine)
 return q
class Adb:
 def __init__(self,path,directory):self.path,self.directory,self.counter=path,directory,0
 def run(self,args,timeout=45):
  self.counter+=1;return command([self.path,'-s','emulator-5554',*args],timeout,self.directory/('adb-%03d'%self.counter))
 def text(self,args,timeout=45):return self.run(args,timeout).decode().strip()
 def digest(self,path):
  value=self.text(['shell','sha256sum',path]);match=re.fullmatch(r'([0-9a-f]{64})\s+\*?'+re.escape(path),value)
  need(match is not None,'DEVICE_HASH_SHAPE');return match.group(1)
def execute(root,module,revision,driver_pins,args):
 directory=args.build.resolve();q=admit_build(root,module,revision,driver_pins,directory);build_pin=identity(directory/'build.json')
 output=fresh(args.output);adb_path=regular(args.adb.resolve(),32*1024**2);adb_pin=identity(adb_path);adb=Adb(adb_path,output)
 remote='/data/local/tmp/coh-source-rgba32-'+secrets.token_hex(12);attempted=False
 result={'schema':'coh-source-rgba32-android13-execution-v1','passed':False,'source_revision':revision,
   'build_receipt':build_pin,'adb_file':adb_pin,'abi':'x86_64','arm64_executed':False,
   'native_execution_attempted':False,'native_process_completed':False,'android_executed':False,
   'device_path_cleanup_verified':False,'native_process_cleanup_verified':False,
   'process_cleanup_unobserved':False,'device_cleanup_verified':False,'post_source_artifact_admission_verified':False,
   'emulator_software_graphics_requested':True,**FALSE_SCOPE}
 try:
  properties={name:adb.text(['shell','getprop',name]) for name in ('ro.build.version.sdk','ro.product.cpu.abi','ro.kernel.qemu','ro.build.fingerprint')}
  need(properties['ro.build.version.sdk']=='33' and properties['ro.product.cpu.abi']=='x86_64' and properties['ro.kernel.qemu']=='1'
       and 0<len(properties['ro.build.fingerprint'])<512 and all(32<=ord(c)<127 for c in properties['ro.build.fingerprint']),'ANDROID13_X86_64_EMULATOR')
  result['device_properties']=properties;result['platform_library_files_before']={name:adb.digest(name) for name in PLATFORM}
  adb.run(['shell','test','!','-e',remote]);adb.run(['shell','test','!','-L',remote])
  # A failed transport can follow a successful mkdir: ownership begins at the
  # creation attempt of this already checked absent, unpredictable fixed path.
  attempted=True;adb.run(['shell','mkdir','-m','700',remote])
  transfers=[(directory/'android/x86_64/coh_source_rgba32_gpu','coh_source_rgba32_gpu',q['android']['x86_64']['binary'])]
  transfers += [(directory/'input'/name,name,q['fixture']['files'][name]) for name in FIXTURES[:3]]
  for source,name,pin in transfers:
   need(identity(source)==pin,'PRETRANSFER_BYTES');adb.run(['push',source,remote+'/'+name]);need(adb.digest(remote+'/'+name)==pin['sha256'],'TRANSFERRED_BYTES')
   adb.run(['shell','chmod','700' if name=='coh_source_rgba32_gpu' else '600',remote+'/'+name])
  result['native_execution_attempted']=True
  raw=adb.run(['shell','timeout','-s','KILL',str(args.timeout_seconds),remote+'/coh_source_rgba32_gpu',
    *[remote+'/'+name for name in FIXTURES[:3]],remote+'/readback.rgba'],args.timeout_seconds+60)
  result['native_process_completed']=True;result['android_executed']=True
  expected=q['fixture']['expected_readback'];need(adb.text(['shell','stat','-c','%s',remote+'/readback.rgba'])==str(expected['bytes'])
    and adb.digest(remote+'/readback.rgba')==expected['sha256'],'DEVICE_READBACK_BYTES')
  readback=output/'readback.rgba';adb.run(['pull',remote+'/readback.rgba',readback]);need(identity(readback)==expected,'PULLED_READBACK_BYTES')
  result['native']=module.validate_result(raw,readback,q['fixture']);need(result['native']['passed']is True,'VALIDATED_NATIVE_RESULT')
  result['readback']=identity(readback)
  for _,name,pin in transfers:need(adb.digest(remote+'/'+name)==pin['sha256'],'POSTEXECUTION_DEVICE_INPUTS')
  result['passed']=True
 except Exception:result['failure_code']='SOURCE_RGBA32_ANDROID_EXECUTION_REFUSED'
 finally:
  try:
   before=result.get('platform_library_files_before');need(before is not None,'PLATFORM_FILE_OBSERVATION_REQUIRED')
   result['platform_library_files_after']={name:adb.digest(name) for name in PLATFORM};need(before==result['platform_library_files_after'],'PLATFORM_FILES_CHANGED')
  except Exception:result['passed']=False;result['platform_file_observation_failed']=True
  try:
   if attempted:
    adb.run(['shell','rm','-rf',remote]);adb.run(['shell','test','!','-e',remote]);adb.run(['shell','test','!','-L',remote])
   result['device_path_cleanup_verified']=True
  except Exception:result['passed']=False;result['device_cleanup_failure']=True
  result['native_process_cleanup_verified']=not result['native_execution_attempted'] or result['native_process_completed']
  result['process_cleanup_unobserved']=result['native_execution_attempted'] and not result['native_process_completed']
  result['device_cleanup_verified']=result['device_path_cleanup_verified'] and result['native_process_cleanup_verified']
  try:
   admit_build(root,module,revision,driver_pins,directory);need(identity(directory/'build.json')==build_pin and identity(adb_path)==adb_pin,'POSTEXECUTION_BUILD_ADB_BYTES')
   result['post_source_artifact_admission_verified']=True
  except Exception:result['passed']=False
  result['passed']=result['passed'] and result['device_cleanup_verified'] and result['post_source_artifact_admission_verified']
  emit(output/'receipt.json',result)
 print(json.dumps({key:result[key] for key in ('passed','android_executed','device_cleanup_verified','post_source_artifact_admission_verified','world_authority')}))
 need(result['passed'],'SOURCE_RGBA32_ANDROID_EXECUTION_REFUSED')
def main():
 parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='mode',required=True)
 build_parser=sub.add_parser('build');run_parser=sub.add_parser('execute')
 for child in (build_parser,run_parser):child.add_argument('--source-root',type=Path,required=True);child.add_argument('--output',type=Path,required=True)
 build_parser.add_argument('--actual-defaults-zip',type=Path,required=True);build_parser.add_argument('--ndk',type=Path,required=True)
 run_parser.add_argument('--build',type=Path,required=True);run_parser.add_argument('--adb',type=Path,required=True);run_parser.add_argument('--timeout-seconds',type=int,default=120)
 args=parser.parse_args()
 if args.mode=='execute':need(1<=args.timeout_seconds<=600,'BOUNDED_EXECUTION_TIMEOUT')
 root,module,revision,pins=load_checker(args.source_root)
 if args.mode=='build':build(root,module,revision,pins,args)
 else:execute(root,module,revision,pins,args)
if __name__=='__main__':main()
