from pathlib import Path
from unittest.mock import patch
import copy,json,os,struct,tempfile,unittest
import hosted_manual_atlas_compile as d

class CompileControls(unittest.TestCase):
 def setUp(self):
  self.owned=tempfile.TemporaryDirectory(prefix='coh-manual-compile-controls-');self.root=Path(self.owned.name);self.addCleanup(self.owned.cleanup)
  install=self.root/'VS';install.mkdir();tools={}
  for name in d.TOOLS:
   p=install/(name+'.exe');p.write_bytes(('isolated fixture '+name).encode());tools[name]={'path':str(p),'bytes':p.stat().st_size,'sha256':d.host.sha(p)}
  self.lock={'schema':'coh-reviewed-windows-build-tool-lock-v1','image_os':'fixture','image_version':'fixture1','generator':'Visual Studio 18 2026',
             'architecture':'Win32','tools':tools,'vs_installation':str(install),'vc_toolset_version':'14.51.36231',
             'windows_sdk_version':'10.0.26100.0','compiler_version':'19.51.36260.0','cmake_version':'4.4.4'}
 def test_lock_sha_image_owner_and_every_tool_byte(self):
  p=self.root/'lock.json';p.write_text(json.dumps(self.lock));env={'ImageOS':'fixture','ImageVersion':'fixture1'}
  with patch.object(d.shutil,'which',return_value=self.lock['tools']['git']['path']):
   self.assertEqual(d.tool_lock(p,d.host.sha(p),env),self.lock)
   with self.assertRaises(ValueError):d.tool_lock(p,'0'*64,env)
   with self.assertRaises(ValueError):d.tool_lock(p,d.host.sha(p),{'ImageOS':'fixture','ImageVersion':'different'})
   for row in self.lock['tools'].values():
    tool=Path(row['path']);before=tool.read_bytes();tool.write_bytes(before+b'x')
    try:
     with self.assertRaises(ValueError):d.tool_lock(p,d.host.sha(p),env)
    finally:tool.write_bytes(before)
 def test_git_path_substitution_refused(self):
  p=self.root/'lock.json';p.write_text(json.dumps(self.lock))
  with patch.object(d.shutil,'which',return_value=str(self.root/'unlocked-git.exe')):
   with self.assertRaises(ValueError):d.tool_lock(p,d.host.sha(p),{'ImageOS':'fixture','ImageVersion':'fixture1'})
 def test_unreviewed_profile_and_relative_tool_refused(self):
  for change in ({'architecture':'x64'},{'generator':'Ninja'},{'vc_toolset_version':'latest'},{'tools':{}}):
   value=dict(self.lock,**change);p=self.root/'lock.json';p.write_text(json.dumps(value))
   with self.assertRaises(ValueError):d.tool_lock(p,d.host.sha(p),{'ImageOS':'fixture','ImageVersion':'fixture1'})
 def test_exact_new_cmake_dependency_patch(self):
  for module,(_,_,_,name) in d.recipe.DEPENDENCIES.items():
   if name:
    raw=d.recipe.git(Path(__file__).resolve().parents[4],'show','HEAD:upstream/ouroboros/'+name)
    result=d.dependency_expected({'existing.c':'1'*64},raw)
    self.assertEqual(set(result),{'existing.c','CMakeLists.txt'})
    with self.assertRaises(ValueError):d.dependency_expected({'CMakeLists.txt':'0'*64},raw)
    with self.assertRaises(ValueError):d.dependency_expected({},raw+b'not a declared patch\n')
  self.assertEqual(d.dependency_expected({'a':'x'},None),{'a':'x'})
 def test_all_existing_source_immutable_generated_domain_bounded(self):
  before={'DBServer/src/clientcomm.c':'a'};after=dict(before,**{'DBServer/src/AutoGen/DbServer_commands_autogen.c':'b'})
  self.assertEqual(d.check_post_source(before,after),{'DBServer/src/AutoGen/DbServer_commands_autogen.c':'b'})
  for bad in ({},dict(after,**{'DBServer/src/clientcomm.c':'changed'}),dict(before,**{'Common/other.c':'b'}),dict(before,**{'Common/AutoGen/evil.exe':'b'})):
   with self.assertRaises(ValueError):d.check_post_source(before,bad)
 def test_full_file_mapping_detects_links(self):
  p=self.root/'source';p.mkdir();(p/'a.c').write_bytes(b'original');expected={'a.c':d.digest(b'original')}
  self.assertEqual(d.bounded_map(p),expected);(p/'alias.c').symlink_to(p/'a.c')
  with self.assertRaises(ValueError):d.bounded_map(p)
 def test_compile_argv_offline_exact_sources_toolchain_and_only_db(self):
  plan={'commands':[['cmake','-S','old-source','-B','old-build','-G','Visual Studio 18 2026','-A','Win32','-DPATCH_EXECUTABLE=old'],
                    ['cmake','--build','old-build','--config','OptDebug','--parallel','2','--target','DbServer']]}
  commands=d.command_argv(plan,'new-source','new-build','new-patch',self.lock,{'cryptopp':'new-crypto'})
  self.assertEqual(commands[0][0],self.lock['tools']['cmake']['path']);self.assertEqual(commands[0][2],'new-source')
  self.assertIn('-DCPM_cryptopp_SOURCE=new-crypto',commands[0]);self.assertIn('-DFETCHCONTENT_FULLY_DISCONNECTED=ON',commands[0])
  self.assertIn('-DCMAKE_SYSTEM_VERSION=10.0.26100.0',commands[0]);self.assertEqual(commands[1][-4:],['--target','DbServer','--','/nr:false'])
  self.assertEqual(plan['commands'][0][2],'old-source')
 def valid_cache(self):
  values={'CMAKE_GENERATOR':'Visual Studio 18 2026','CMAKE_GENERATOR_PLATFORM':'Win32','COH_PG_PERSISTENCE_TESTS':'OFF',
          'COX_BUILD_COMMON':'ON','COX_BUILD_DBSERVER':'ON','COX_BUILD_MAPSERVER':'OFF','COX_BUILD_BEACONSERVER':'OFF','COX_BUILD_AUTHserver':'OFF',
          'CMAKE_GENERATOR_INSTANCE':self.lock['vs_installation'],'CMAKE_GENERATOR_TOOLSET':'version=14.51.36231,host=x64',
          'CMAKE_SYSTEM_VERSION':'10.0.26100.0','CMAKE_CACHE_MAJOR_VERSION':'4','CMAKE_CACHE_MINOR_VERSION':'4','CMAKE_CACHE_PATCH_VERSION':'4'}
  values.update({key:self.lock['tools'][tool]['path'] for key,tool in (('CMAKE_MAKE_PROGRAM','msbuild'),('CMAKE_LINKER','link'),('CMAKE_RC_COMPILER','rc'),('CMAKE_ASM_MASM_COMPILER','ml'))})
  return values
 def test_cache_refuses_fixture_wrong_version_unexpected_target(self):
  p=self.root/'CMakeCache.txt';values=self.valid_cache()
  def write(v):p.write_text(''.join(k+':STRING='+x+'\n' for k,x in v.items()))
  write(values);self.assertEqual(d.cache_profile(p,self.lock)['COH_PG_PERSISTENCE_TESTS'],'OFF')
  for key,value in (('COH_PG_PERSISTENCE_TESTS','ON'),('COX_BUILD_GAME','ON'),('CMAKE_CACHE_PATCH_VERSION','5'),('CMAKE_GENERATOR_PLATFORM','x64')):
   changed=dict(values);changed[key]=value;write(changed)
   with self.assertRaises(ValueError):d.cache_profile(p,self.lock)
 def test_generated_compiler_exact_path_abi_and_version(self):
  p=self.root/'CMakeFiles/4.4.4';p.mkdir(parents=True)
  for lang in ('C','CXX'):
   values={'COMPILER':self.lock['tools']['cl']['path'],'COMPILER_VERSION':self.lock['compiler_version'],'COMPILER_ID':'MSVC','SIZEOF_DATA_PTR':'4'}
   (p/('CMake'+lang+'Compiler.cmake')).write_text(''.join('set(CMAKE_'+lang+'_'+k+' "'+v+'")\n' for k,v in values.items()))
  self.assertEqual(set(d.compiler_profile(self.root,self.lock)),{'C','CXX'})
  path=p/'CMakeCCompiler.cmake';original=path.read_text()
  for change in (original.replace('19.51.36260.0','19.99.1.0'),original.replace('"4"','"8"'),original.replace('cl.exe','other.exe')):
   path.write_text(change)
   with self.assertRaises(ValueError):d.compiler_profile(self.root,self.lock)
 def fixture_pe(self):
  data=bytearray(1024);data[:2]=b'MZ';struct.pack_into('<I',data,60,64);data[64:68]=b'PE\0\0'
  struct.pack_into('<HHIIIHH',data,68,0x14c,1,0,0,0,224,0);struct.pack_into('<H',data,88,0x10b)
  struct.pack_into('<I',data,88+92,16);struct.pack_into('<II',data,88+104,0x1000,40);struct.pack_into('<IIII',data,88+224+8,512,0x1000,512,512)
  struct.pack_into('<IIIII',data,512,1,0,0,0x1080,1);data[640:653]=b'KERNEL32.dll\0';struct.pack_into('<H',data,156,3)
  return data
 def test_pure_pe_import_ranges_and_win32(self):
  data=self.fixture_pe();p=self.root/'candidate.exe';p.write_bytes(data)
  self.assertEqual(d.pe_imports(p),['kernel32.dll'])
  for offset,value in ((68,0x8664),(88,0x20b)):
   corrupt=bytearray(data);struct.pack_into('<H',corrupt,offset,value);p.write_bytes(corrupt)
   with self.assertRaises(ValueError):d.pe_imports(p)

 def test_compilation_admission_scope_commands_and_source_mutations(self):
  import gzip
  artifact=self.root/'artifact';artifact.mkdir();commit='1'*40;source='C:/owned/source';build='C:/owned/build'
  self.lock['vs_installation']='C:/VS';self.lock['tools']={n:dict(row,path='C:/VS/'+n+'.exe') for n,row in self.lock['tools'].items()}
  plan={'commands':[['cmake','-S','old-source','-B','old-build','-G','Visual Studio 18 2026','-A','Win32','-DPATCH_EXECUTABLE=old'],
                    ['cmake','--build','old-build','--config','OptDebug','--parallel','2','--target','DbServer']]}
  candidate={'Common/ClientLogin/clientcommLogin.c':'a'*64};candidate.update({'unchanged/source'+str(i)+'.c':'b'*64 for i in range(6006)});maps={'source_before':candidate,'source_after_configure':dict(candidate),
   'source_after_build':dict(candidate),'source_at_cleanup':dict(candidate),'generated_source':{},'dependencies':{}}
  deps={};commands=[];blobs={'deployment/hosted_manual_atlas_compile.py':b'fixture driver',
    'evidence/manual-atlas-full-recipe-20261017/source-recipe.source-maps.json.gz':gzip.compress(json.dumps({'checksum_candidate':candidate}).encode()),
    'evidence/manual-atlas-full-recipe-20261017/static-build-plan.json':json.dumps(plan).encode()}
  for _,(name,repo,pin,patchname) in d.recipe.DEPENDENCIES.items():
   destination='C:/owned/dependencies/'+name;deps[name]=destination;remote=repo if repo.startswith('https://') else 'https://github.com/'+repo+'.git'
   old={'original.c':'b'*64}
   patchdata=d.recipe.git(Path(__file__).resolve().parents[4],'show','HEAD:upstream/ouroboros/'+patchname) if patchname else None
   if patchname:blobs['ORIGINAL:'+patchname]=patchdata
   expected=d.dependency_expected(old,patchdata);maps['dependencies'][name]={'repository':remote,'commit':pin,'before':old,'expected_after_cmake_patch':expected,'after':expected,'at_cleanup':expected}
   git=self.lock['tools']['git']['path']
   commands.extend([(name+'-init',[git,'init',destination]),(name+'-fetch',[git,'-C',destination,'fetch','--depth=1',remote,pin]),
                    (name+'-checkout',[git,'-C',destination,'-c','core.autocrlf=false','checkout','--detach',pin])])
   if patchname:
    for label,extra in [('patch-check',['--check']),('patch',[])]:commands.append((name+'-'+label,[git,'-C',destination,'-c','core.autocrlf=false','apply',*extra,str(Path(source)/patchname)]))
  configure,compileargv=d.command_argv(plan,source,build,self.lock['tools']['patch']['path'],self.lock,deps)
  commands.extend([('configure-full-manual',configure),('build-full-manual',compileargv)])
  rows=[]
  for name,argv in commands:
   path=artifact/(name+'.log');path.write_bytes(b'fixture successful command')
   rows.append({'name':name,'argv':argv,'returncode':0,'log_truncated':False,'log_sha256':d.host.sha(path)})
  state={'commit':commit,'tracked_dirty':'','helper_inputs':{'deployment/hosted_manual_atlas_compile.py':d.digest(b'fixture driver')},'recipe_inputs':{}}
  value={'schema':d.SCHEMA,'passed':True,'image_os':'fixture','image_version':'fixture1','repository_commit':commit,'all_existing_source_unchanged':True,'source_and_toolchain_unchanged':True,
    'final_maps_captured':True,'input_state_before':state,'input_state_after':copy.deepcopy(state),'command_paths':{'source':source,'build':build,'dependencies':deps},
    'exact_configure_argv':configure,'exact_build_argv':compileargv,'commands':rows,**{n:False for n in d.FALSES}}
  for name in ('DbServer.exe','CrashRpt.dll'):(artifact/name).write_bytes(self.fixture_pe())
  value['artifacts']={n:{'identity':d.host.pe_identity(artifact/n,None),'imports':d.pe_imports(artifact/n),'executed':False} for n in ('DbServer.exe','CrashRpt.dll')}
  (artifact/'toolchain-lock.json').write_text(json.dumps(self.lock));value['toolchain_lock_sha256']=d.host.sha(artifact/'toolchain-lock.json')
  (artifact/'host-qualification.json').write_text(json.dumps({'schema':'coh-manual-atlas-full-source-host-qualification-v1','passed':True,'suites':5,'build_executed':False,'local_inputs':{}}));value['host_qualification_sha256']=d.host.sha(artifact/'host-qualification.json')
  (artifact/'source-recipe.json').write_text(json.dumps({'schema':'coh-full-manual-atlas-checksum-source-recipe-v1','passed':True,'original_files':5995,
   'complete_source_files':6007,'sole_additional_changed_path':d.recipe.base.CHECKSUM,'build_executed':False,'accepted_manifest_sha256':d.recipe.MANIFEST_SHA}))
  (artifact/'generated-source.json.gz').write_bytes(gzip.compress(b'{}'))
  for lang in ('C','CXX'):
   observed={'COMPILER':self.lock['tools']['cl']['path'],'COMPILER_VERSION':self.lock['compiler_version'],'COMPILER_ID':'MSVC','SIZEOF_DATA_PTR':'4'}
   (artifact/('CMake'+lang+'Compiler.cmake')).write_text(''.join('set(CMAKE_'+lang+'_'+k+' "'+v+'")\n' for k,v in observed.items()))
  value['compiler_profile']=d.compiler_profile(artifact,self.lock,True)
  (artifact/'CMakeCache.txt').write_text(''.join(k+':STRING='+v+'\n' for k,v in self.valid_cache().items()))
  def persist():
   (artifact/'all-file-maps.json.gz').write_bytes(gzip.compress(json.dumps(maps).encode()));value['all_file_maps_sha256']=d.host.sha(artifact/'all-file-maps.json.gz')
   value['files']={p.name:{'bytes':p.stat().st_size,'sha256':d.host.sha(p)} for p in artifact.iterdir() if p.name!='receipt.json'}
   (artifact/'receipt.json').write_text(json.dumps(value))
  def git(root,*args):
   if args[0]=='rev-parse':return (d.recipe.base.ORIGINAL_TREE+'\n').encode()
   name=args[1].split(':',1)[1]
   if name.startswith('upstream/ouroboros/'):return blobs['ORIGINAL:'+name.removeprefix('upstream/ouroboros/')]
   return blobs[name.removeprefix('native-android/engine/auth-interop/')]
  def admit():
   return d.admit(artifact,d.host.sha(artifact/'receipt.json'),d.host.sha(artifact/'DbServer.exe'),value['toolchain_lock_sha256'],self.root)
  persist()
  with patch.object(d.recipe,'git',side_effect=git):
   self.assertTrue(admit()['admitted'])
   for name in d.FALSES:
    value[name]=True;persist()
    with self.assertRaises(ValueError):admit()
    value[name]=False
   value['commands'][-1]['argv']=list(compileargv);value['commands'][-1]['argv'][value['commands'][-1]['argv'].index('DbServer')]='AuthServer';persist()
   with self.assertRaises(ValueError):admit()
   value['commands'][-1]['argv']=compileargv
   maps['source_after_build']['Common/ClientLogin/clientcommLogin.c']='c'*64;persist()
   with self.assertRaises(ValueError):admit()
 def test_linux_cannot_start_compile_driver(self):
  from types import SimpleNamespace
  a=SimpleNamespace(source_root=self.root,output=self.root/'new',expected_commit='0'*40)
  with patch.object(d.host.os,'name','posix'):
   with self.assertRaises(ValueError):d.build(a)
  self.assertFalse(a.output.exists())

if __name__=='__main__':unittest.main()
