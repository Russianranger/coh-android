"""Disposable full manual PG/Wine checksum build; never starts any server.

Requires an externally pinned exact host-tool lock. An observation alone is not
admission. No package, persistence profile, account or shipping file is changed.
"""
import argparse,base64,gzip,hashlib,json,os,re,shutil,struct,subprocess,tempfile,time
from pathlib import Path,PurePosixPath,PureWindowsPath
import manual_atlas_full_recipe as recipe
import hosted_db_checksum_candidate as db
import hosted_auth_stage as host

HERE=Path(__file__).resolve().parent
SCHEMA='coh-full-manual-atlas-compile-v1'
UNSAFE_ENV={'CMAKE_TOOLCHAIN_FILE','CMAKE_PROJECT_TOP_LEVEL_INCLUDES','CC','CXX','CFLAGS','CXXFLAGS','CPPFLAGS','LDFLAGS','CL','_CL_','LINK','_LINK_',
            'CMAKE_PREFIX_PATH','CPM_USE_LOCAL_PACKAGES','CPM_SOURCE_CACHE','GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_CONFIG_COUNT'}
TOOLS={'cmake','git','patch','cl','link','ml','rc','msbuild'}
FALSES=('service_executed','shipping_runtime_replacement_permit','live_authenticated_db_login_verified',
        'actual_persistence_verified','nondevelopment_version_observed','manual_wait_skip_permitted_for_real_auth')


def digest(value):return hashlib.sha256(value).hexdigest()


def checked_json(path,expected,limit=4*1024*1024):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit or host.sha(path)!=expected:raise ValueError('manual_pinned_input_identity')
    return json.loads(path.read_bytes())


def tool_lock(path,expected,environ=None):
    env=os.environ if environ is None else environ;lock=checked_json(path,expected)
    if (lock.get('schema')!='coh-reviewed-windows-build-tool-lock-v1' or lock.get('image_os')!=env.get('ImageOS')
            or lock.get('image_version')!=env.get('ImageVersion') or not lock.get('image_version')
            or lock.get('generator')!='Visual Studio 18 2026' or lock.get('architecture')!='Win32'
            or set(lock.get('tools',{}))!=TOOLS or not re.fullmatch(r'14\.\d+\.\d+',lock.get('vc_toolset_version',''))
            or not re.fullmatch(r'10\.0\.\d+\.\d+',lock.get('windows_sdk_version',''))
            or not re.fullmatch(r'19\.\d+\.\d+\.\d+',lock.get('compiler_version',''))
            or not re.fullmatch(r'\d+\.\d+\.\d+',lock.get('cmake_version',''))):raise ValueError('manual_exact_tool_profile')
    installation=Path(lock.get('vs_installation',''))
    if not installation.is_absolute() or not installation.is_dir():raise ValueError('manual_vs_installation')
    for name,row in lock['tools'].items():
        p=Path(row.get('path',''))
        if (not p.is_absolute() or p.is_symlink() or not p.is_file() or not 0<p.stat().st_size<=256*1024*1024
                or row!={'path':str(p),'bytes':p.stat().st_size,'sha256':host.sha(p)}):raise ValueError('manual_exact_tool_identity')
    representatives=lock.get('sdk_representatives')
    if representatives is not None:
        if set(representatives)!={'kernel32','ucrt','windows_header'}:raise ValueError('manual_sdk_representative_domain')
        kits=PureWindowsPath(lock['tools']['rc']['path']).parents[3];sdk=lock['windows_sdk_version']
        wanted={'kernel32':kits/('Lib/'+sdk+'/um/x86/kernel32.lib'),'ucrt':kits/('Lib/'+sdk+'/ucrt/x86/ucrt.lib'),
                'windows_header':kits/('Include/'+sdk+'/um/Windows.h')}
        for name,row in representatives.items():
            p=Path(row.get('path',''))
            if (PureWindowsPath(row.get('path',''))!=wanted[name] or p.is_symlink() or not p.is_file()
                    or not 0<p.stat().st_size<=256*1024*1024 or row!={'path':str(p),'bytes':p.stat().st_size,'sha256':host.sha(p)}):
                raise ValueError('manual_sdk_representative_identity')
    # The VS compiler, assembler, linker and MSBuild must belong to the pinned
    # installation; SDK rc and Git/CMake may live in their own installations.
    for name in ('cl','link','ml','msbuild'):
        if not Path(lock['tools'][name]['path']).is_relative_to(installation):raise ValueError('manual_vs_tool_owner')
    if Path(shutil.which('git') or '').resolve()!=Path(lock['tools']['git']['path']).resolve():raise ValueError('manual_git_path_owner')
    return lock


def bounded_map(directory,exclude_git=False):
    result={};total=0
    for p in directory.rglob('*'):
        relative=p.relative_to(directory)
        if exclude_git and '.git' in relative.parts:continue
        if p.is_symlink():raise ValueError('manual_build_input_link')
        if p.is_file():
            size=p.stat().st_size;total+=size
            if size>128*1024*1024 or total>1024*1024*1024 or len(result)>=30000:raise ValueError('manual_build_input_budget')
            result[relative.as_posix()]=host.sha(p)
    return result


def dependency_expected(original,patch):
    # Both pinned patches add exactly one new CMakeLists.txt. No generic patch
    # interpretation is admitted here; the full first-party map pins the bytes.
    if patch is None:return dict(original)
    text=patch.decode();match=re.search(r'^@@ -0,0 \+1,(\d+) @@\n((?:\+[^\n]*\n)+)\Z',text,re.M)
    if match is None or text[:match.start()].splitlines()[-2:]!=['--- /dev/null','+++ b/CMakeLists.txt'] or 'CMakeLists.txt' in original:
        raise ValueError('manual_cpm_single_new_cmake_patch')
    lines=match[2].splitlines(True)
    if len(lines)!=int(match[1]):raise ValueError('manual_cpm_patch_line_domain')
    result=dict(original);result['CMakeLists.txt']=digest(''.join(line[1:] for line in lines).encode());return result


def check_post_source(before,after):
    if any(after.get(n)!=h for n,h in before.items()):raise ValueError('manual_existing_source_changed')
    additions={n:h for n,h in after.items() if n not in before}
    for name in additions:
        parts=PurePosixPath(name)
        # Source-owned StructParser writes C/C++/header sidecars only in these
        # exact consumer directories. New files are retained/hash-bound too.
        if (parts.parent.as_posix() not in ('DBServer/src/AutoGen','Common/AutoGen','libs/UtilitiesLib/src/AutoGen')
                or parts.suffix not in ('.c','.cpp','.h') or len(parts.name)>160):raise ValueError('manual_unexpected_generated_source')
    return additions


def git_config_environment(environ=None):
    env=os.environ if environ is None else environ
    actual={k:v for k,v in env.items() if k.startswith('GIT_CONFIG_')}
    accepted={'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'core.autocrlf','GIT_CONFIG_VALUE_0':'false'}
    if actual and actual!=accepted:raise ValueError('manual_git_environment_override_refused')
    return actual


def source_state(root):
    return {'commit':host.capture(['git','-C',root,'rev-parse','HEAD']),
            'tracked_dirty':host.capture(['git','-C',root,'status','--porcelain','--untracked-files=no']),
            'git_config_environment':git_config_environment(),
            'helper_inputs':{p.relative_to(HERE.parent).as_posix():host.sha(p) for p in list(HERE.glob('*.py'))+[HERE.parent/'source_oracle.py']},
            'recipe_inputs':{p.name:host.sha(p) for p in recipe.MANIFEST.parent.iterdir() if p.is_file()}}


def commands(source,build,patch,expected,lock,dependencies):
    plan=recipe.build_plan(source,build,patch,expected)
    return command_argv(plan,source,build,patch,lock,dependencies)


def command_argv(plan,source,build,patch,lock,dependencies):
    configure,compile_command=[list(argv) for argv in plan['commands']]
    configure[2]=str(source);configure[4]=str(build);compile_command[2]=str(build)
    configure=[('-DPATCH_EXECUTABLE='+str(patch)) if arg.startswith('-DPATCH_EXECUTABLE=') else arg for arg in configure]
    configure[0]=lock['tools']['cmake']['path'];compile_command[0]=configure[0];compile_command+=['--','/nr:false']
    configure+=['-DCMAKE_GENERATOR_INSTANCE='+lock['vs_installation'],
                '-T','version='+lock['vc_toolset_version']+',host=x64',
                '-DCMAKE_SYSTEM_VERSION='+lock['windows_sdk_version'],'-DCPM_SOURCE_CACHE=OFF','-DCPM_USE_LOCAL_PACKAGES=OFF',
                '-DCPM_DOWNLOAD_ALL=ON','-DFETCHCONTENT_FULLY_DISCONNECTED=ON','-DFETCHCONTENT_UPDATES_DISCONNECTED=ON']
    configure+=['-D'+key+'='+lock['tools'][tool]['path'] for key,tool in (('CMAKE_MAKE_PROGRAM','msbuild'),('CMAKE_LINKER','link'),('CMAKE_RC_COMPILER','rc'),('CMAKE_ASM_MASM_COMPILER','ml'))]
    configure+=['-DCPM_'+name+'_SOURCE='+str(path) for name,path in dependencies.items()]
    return [configure,compile_command]


def cache_profile(path,lock):
    cache={}
    for line in path.read_text().splitlines():
        match=re.fullmatch(r'([^#/:][^:]*):[^=]+=(.*)',line)
        if match:cache[match[1]]=match[2]
    expected={'CMAKE_GENERATOR':'Visual Studio 18 2026','CMAKE_GENERATOR_PLATFORM':'Win32','COH_PG_PERSISTENCE_TESTS':'OFF',
              'COX_BUILD_COMMON':'ON','COX_BUILD_DBSERVER':'ON','COX_BUILD_MAPSERVER':'OFF','COX_BUILD_BEACONSERVER':'OFF',
              'CMAKE_GENERATOR_INSTANCE':lock['vs_installation'],'CMAKE_GENERATOR_TOOLSET':'version='+lock['vc_toolset_version']+',host=x64',
              'CMAKE_SYSTEM_VERSION':lock['windows_sdk_version']}
    expected.update({key:lock['tools'][tool]['path'] for key,tool in (('CMAKE_MAKE_PROGRAM','msbuild'),('CMAKE_LINKER','link'),('CMAKE_RC_COMPILER','rc'),('CMAKE_ASM_MASM_COMPILER','ml'))})
    for name,value in expected.items():
        if cache.get(name,'').replace('\\','/')!=value.replace('\\','/'):raise ValueError('manual_generated_cache_profile')
    actual='.'.join(cache.get('CMAKE_CACHE_'+part+'_VERSION','') for part in ('MAJOR','MINOR','PATCH'))
    if actual!=lock['cmake_version']:raise ValueError('manual_generated_cmake_version')
    for key,value in cache.items():
        if key.startswith('COX_BUILD_') and key not in ('COX_BUILD_COMMON','COX_BUILD_DBSERVER') and value!='OFF':raise ValueError('manual_unexpected_enabled_project')
    return expected


def compiler_profile(build,lock,direct=False):
    directory=build if direct else build/'CMakeFiles'/lock['cmake_version']
    observations={}
    for lang in ('C','CXX'):
        data=(directory/('CMake'+lang+'Compiler.cmake')).read_text()
        for key,expected in (('COMPILER',lock['tools']['cl']['path']),('COMPILER_VERSION',lock['compiler_version']),('COMPILER_ID','MSVC'),('SIZEOF_DATA_PTR','4')):
            match=re.search(r'set\(CMAKE_'+lang+'_'+key+r' "?([^"\)]+)"?\)',data)
            if match is None or match[1].replace('\\','/')!=expected.replace('\\','/'):raise ValueError('manual_generated_compiler_profile')
        observations[lang]=digest(data.encode())
    return observations


def pe_imports(path):
    data=path.read_bytes()
    if len(data)<256 or len(data)>128*1024*1024 or data[:2]!=b'MZ':raise ValueError('manual_pe_size_header')
    pe=struct.unpack_from('<I',data,60)[0]
    if pe<64 or pe+248>len(data) or data[pe:pe+4]!=b'PE\0\0':raise ValueError('manual_pe_header_range')
    machine,count,_,_,_,optional,_=struct.unpack_from('<HHIIIHH',data,pe+4);op=pe+24
    if machine!=0x14c or not 1<=count<=96 or optional<112 or struct.unpack_from('<H',data,op)[0]!=0x10b or struct.unpack_from('<I',data,op+92)[0]<2:raise ValueError('manual_pe32_sections')
    sections=op+optional
    if sections+count*40>len(data):raise ValueError('manual_pe_section_range')
    def rva(address,length):
        hits=[]
        for i in range(count):
            _,virtual,rawsize,raw=struct.unpack_from('<IIII',data,sections+i*40+8)
            if virtual<=address and address+length<=virtual+rawsize and raw+address-virtual+length<=len(data):hits.append(raw+address-virtual)
        if len(hits)!=1:raise ValueError('manual_pe_rva_ownership')
        return hits[0]
    address,size=struct.unpack_from('<II',data,op+104)
    if not address or not 20<=size<=20*4096:raise ValueError('manual_pe_import_directory')
    names=[]
    for offset in range(0,size-19,20):
        descriptor=struct.unpack_from('<IIIII',data,rva(address+offset,20))
        if not any(descriptor):return sorted(set(names))
        start=rva(descriptor[3],1);end=data.find(b'\0',start,min(start+129,len(data)))
        if end<0:raise ValueError('manual_pe_import_name_bound')
        if rva(descriptor[3],end-start+1)!=start:raise ValueError('manual_pe_import_string_owner')
        name=data[start:end].decode('ascii')
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}\.dll',name,re.I):raise ValueError('manual_pe_import_name')
        names.append(name.lower())
    raise ValueError('manual_pe_import_terminator')


def build(args):
    git_config_environment()
    if any(os.environ.get(name) for name in UNSAFE_ENV if name!='GIT_CONFIG_COUNT'):raise ValueError('manual_ambient_build_override_refused')
    deadline=time.monotonic()+2100
    root=args.source_root.resolve();output=args.output.resolve()
    identity=host.require_hosted(root,output,args.expected_commit)
    lock=tool_lock(args.toolchain_lock,args.expected_toolchain_sha256)
    host_receipt=checked_json(args.host_qualification,args.expected_host_qualification_sha256)
    if host_receipt.get('schema')!='coh-manual-atlas-full-source-host-qualification-v1' or host_receipt.get('passed') is not True or host_receipt.get('suites')!=5:
        raise ValueError('manual_host_source_qualification')
    for name,h in host_receipt['local_inputs'].items():
        if host.sha(root/name)!=h:raise ValueError('manual_host_helper_input')
    for name,h in host_receipt['retained_evidence'].items():
        if host.sha(recipe.MANIFEST.parent/name)!=h:raise ValueError('manual_host_retained_input')
    output.mkdir(parents=True);initial=source_state(root)
    proof=dict(identity,schema=SCHEMA,passed=False,toolchain_lock_sha256=args.expected_toolchain_sha256,
               host_qualification_sha256=args.expected_host_qualification_sha256,**{name:False for name in FALSES})
    runner=db.BuildCommands(output)
    def run(name,argv,timeout):
        remaining=int(deadline-time.monotonic())-120
        if remaining<=0:raise ValueError('manual_compile_budget_cleanup_reserve')
        return runner.run(name,argv,timeout=min(timeout,remaining))
    proof['input_state_before']=initial
    shutil.copy2(args.toolchain_lock,output/'toolchain-lock.json');shutil.copy2(args.host_qualification,output/'host-qualification.json')
    try:
        with tempfile.TemporaryDirectory(prefix='coh-manual-atlas-compile-',dir=os.environ['RUNNER_TEMP']) as temporary:
            temporary=Path(temporary);source=temporary/'source';build_dir=temporary/'build';dependencies={};dep_maps={}
            maps=None;save_maps=None
            try:
                composed=recipe.prepare(root,source);expected=composed.pop('maps');before=bounded_map(source)
                maps={'source_before':before,'dependencies':dep_maps}
                def save_maps():
                    raw=gzip.compress(json.dumps(maps,sort_keys=True).encode(),mtime=0);(output/'all-file-maps.json.gz').write_bytes(raw)
                    proof['all_file_maps_sha256']=digest(raw)
                save_maps()
                if before!=expected['checksum_candidate']:raise ValueError('manual_complete_composition_mismatch')
                (output/'source-recipe.json').write_text(json.dumps(composed,indent=2)+'\n')
                for module,(name,repository,commit,patch) in recipe.DEPENDENCIES.items():
                    destination=temporary/'dependencies'/name;destination.mkdir(parents=True)
                    remote=repository if repository.startswith('https://') else 'https://github.com/'+repository+'.git'
                    git=lock['tools']['git']['path']
                    for label,argv in [('init',[git,'init',str(destination)]),('fetch',[git,'-C',str(destination),'fetch','--depth=1',remote,commit]),
                                       ('checkout',[git,'-C',str(destination),'-c','core.autocrlf=false','checkout','--detach',commit])]:
                        run(name+'-'+label,argv,timeout=300)
                    if host.capture([git,'-C',destination,'rev-parse','HEAD'])!=commit:raise ValueError('manual_external_commit_identity')
                    original=bounded_map(destination,True);wanted=dependency_expected(original,(source/patch).read_bytes() if patch else None)
                    dep_maps[name]={'repository':remote,'commit':commit,'before':original,'expected_after_cmake_patch':wanted}
                    dependencies[name]=destination
                    if patch:
                        for label,extra in [('patch-check',['--check']),('patch',[])]:
                            run(name+'-'+label,[git,'-C',str(destination),'-c','core.autocrlf=false','apply',*extra,str(source/patch)],timeout=30)
                    if bounded_map(destination,True)!=wanted:raise ValueError('manual_external_staged_patch_mismatch')
                    save_maps()
                configure,compile_command=commands(source,build_dir,lock['tools']['patch']['path'],before,lock,dependencies)
                proof['command_paths']={'source':str(source),'build':str(build_dir),'dependencies':{n:str(p) for n,p in dependencies.items()}}
                proof['exact_configure_argv']=configure;proof['exact_build_argv']=compile_command
                run('configure-full-manual',configure,timeout=900)
                proof['cache_profile']=cache_profile(build_dir/'CMakeCache.txt',lock)
                proof['compiler_profile']=compiler_profile(build_dir,lock)
                for lang in ('C','CXX'):shutil.copy2(build_dir/'CMakeFiles'/lock['cmake_version']/('CMake'+lang+'Compiler.cmake'),output/('CMake'+lang+'Compiler.cmake'))
                configured=bounded_map(source);maps['source_after_configure']=configured;save_maps();check_post_source(before,configured)
                for name,path in dependencies.items():
                    if bounded_map(path,True)!=dep_maps[name]['expected_after_cmake_patch']:raise ValueError('manual_external_configure_changed_bytes')
                run('build-full-manual',compile_command,timeout=1800)
                after=bounded_map(source);maps['source_after_build']=after;save_maps();generated=check_post_source(before,after)
                maps['generated_source']=generated
                generated_bytes={name:base64.b64encode((source/name).read_bytes()).decode('ascii') for name in generated}
                generated_raw=json.dumps(generated_bytes,sort_keys=True).encode()
                if len(generated_raw)>32*1024*1024:raise ValueError('manual_generated_capture_budget')
                (output/'generated-source.json.gz').write_bytes(gzip.compress(generated_raw,mtime=0))
                for name,path in dependencies.items():
                    dep_maps[name]['after']=bounded_map(path,True)
                    if dep_maps[name]['after']!=dep_maps[name]['expected_after_cmake_patch']:raise ValueError('manual_external_build_changed_bytes')
                shutil.copy2(build_dir/'CMakeCache.txt',output/'CMakeCache.txt')
                artifacts={}
                for name in ('DbServer.exe','CrashRpt.dll'):
                    path=build_dir/'bin/OptDebug'/name
                    if not path.exists() and name=='CrashRpt.dll':
                        matches=list(build_dir.glob('**/OptDebug/CrashRpt.dll'))
                        if len(matches)!=1:raise ValueError('manual_crashrpt_output_owner')
                        path=matches[0]
                    artifacts[name]={'identity':host.pe_identity(path,3 if name=='DbServer.exe' else None),'imports':pe_imports(path),'executed':False}
                    shutil.copy2(path,output/name)
                save_maps()
                proof.update(artifacts=artifacts,all_existing_source_unchanged=True,passed=True)
            finally:
                try:
                    if maps is not None and save_maps is not None:
                        if source.is_dir():maps['source_at_cleanup']=bounded_map(source)
                        for name,path in dependencies.items():
                            if path.is_dir():dep_maps[name]['at_cleanup']=bounded_map(path,True)
                        save_maps();proof['final_maps_captured']=True
                        if proof['passed'] and (maps.get('source_at_cleanup')!=maps.get('source_after_build') or any(row.get('at_cleanup')!=row.get('after') for row in dep_maps.values())):
                            proof['passed']=False
                    else:proof['final_maps_captured']=False
                except Exception:
                    proof['final_maps_captured']=False;proof['passed']=False
    except Exception as error:proof['failure']=str(error) if isinstance(error,ValueError) else type(error).__name__
    finally:
        proof['commands']=runner.records
        try:
            proof['input_state_after']=source_state(root);tool_lock(args.toolchain_lock,args.expected_toolchain_sha256)
            proof['source_and_toolchain_unchanged']=initial==proof['input_state_after'] and not initial['tracked_dirty']
        except Exception:proof['source_and_toolchain_unchanged']=False
        proof['passed']=proof['passed'] and proof['source_and_toolchain_unchanged']
        proof['files']={p.name:{'bytes':p.stat().st_size,'sha256':host.sha(p)} for p in output.iterdir() if p.is_file() and p.name!='receipt.json'}
        (output/'receipt.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


def safe_map(value,limit=30000):
    if not isinstance(value,dict) or not 0<len(value)<=limit:raise ValueError('manual_map_domain')
    for name,h in value.items():
        if (type(name) is not str or not name or '\\' in name or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts
                or type(h) is not str or not re.fullmatch('[0-9a-f]{64}',h)):raise ValueError('manual_map_identity')


def admit(directory,receipt_sha,binary_sha,toolchain_sha,root):
    value=checked_json(directory/'receipt.json',receipt_sha,16*1024*1024)
    if (value.get('schema')!=SCHEMA or value.get('passed') is not True or value.get('all_existing_source_unchanged') is not True
            or value.get('source_and_toolchain_unchanged') is not True or value.get('final_maps_captured') is not True or any(value.get(name) is not False for name in FALSES)
            or value.get('toolchain_lock_sha256')!=toolchain_sha):raise ValueError('manual_compile_admission_scope')
    commit=value.get('repository_commit')
    if type(commit) is not str or not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('manual_compile_source_commit')
    blob=lambda name:recipe.git(root,'show',commit+':native-android/engine/auth-interop/'+name)
    if recipe.git(root,'rev-parse',commit+':upstream/ouroboros').decode().strip()!=recipe.base.ORIGINAL_TREE:raise ValueError('manual_compile_original_tree')
    files=value.get('files')
    if not isinstance(files,dict) or len(files)>32 or not {'DbServer.exe','CrashRpt.dll','CMakeCache.txt','all-file-maps.json.gz','toolchain-lock.json','host-qualification.json','source-recipe.json','CMakeCCompiler.cmake','CMakeCXXCompiler.cmake','generated-source.json.gz'}.issubset(files):
        raise ValueError('manual_compile_file_set')
    for name,row in files.items():
        if type(name) is not str or PurePosixPath(name).name!=name or '\\' in name:raise ValueError('manual_compile_file_name')
        path=directory/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size>128*1024*1024 or row!={'bytes':path.stat().st_size,'sha256':host.sha(path)}:raise ValueError('manual_compile_file_identity')
    state=value.get('input_state_before')
    if not isinstance(state,dict) or state!=value.get('input_state_after') or state.get('commit')!=commit or state.get('tracked_dirty')!='':raise ValueError('manual_compile_input_stability')
    git_config_environment(state.get('git_config_environment',{}))
    for name,h in state.get('helper_inputs',{}).items():
        name=name.replace('\\','/')
        if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:raise ValueError('manual_compile_helper_path')
        if digest(blob(name))!=h:raise ValueError('manual_compile_historical_helper_identity')
    if 'deployment/hosted_manual_atlas_compile.py' not in {n.replace('\\','/') for n in state.get('helper_inputs',{})}:raise ValueError('manual_compile_driver_identity')
    for name,h in state.get('recipe_inputs',{}).items():
        if digest(blob('evidence/manual-atlas-full-recipe-20261017/'+name))!=h:raise ValueError('manual_compile_historical_recipe_identity')
    lock=checked_json(directory/'toolchain-lock.json',toolchain_sha)
    if (lock.get('schema')!='coh-reviewed-windows-build-tool-lock-v1' or lock.get('image_os')!=value.get('image_os')
            or lock.get('image_version')!=value.get('image_version') or lock.get('generator')!='Visual Studio 18 2026'
            or lock.get('architecture')!='Win32' or set(lock.get('tools',{}))!=TOOLS):raise ValueError('manual_compile_admitted_tool_profile')
    host_receipt=checked_json(directory/'host-qualification.json',value.get('host_qualification_sha256'))
    if (host_receipt.get('schema')!='coh-manual-atlas-full-source-host-qualification-v1' or host_receipt.get('passed') is not True
            or host_receipt.get('suites')!=5 or host_receipt.get('build_executed') is not False):raise ValueError('manual_compile_host_scope')
    for name,h in host_receipt.get('local_inputs',{}).items():
        if digest(recipe.git(root,'show',commit+':'+name))!=h:raise ValueError('manual_compile_host_source_identity')
    maps_path=directory/'all-file-maps.json.gz'
    if host.sha(maps_path)!=value.get('all_file_maps_sha256') or maps_path.stat().st_size>8*1024*1024:raise ValueError('manual_compile_map_archive_identity')
    with gzip.open(maps_path,'rb') as stream:
        raw=stream.read(32*1024*1024+1)
    if len(raw)>32*1024*1024:raise ValueError('manual_compile_map_decode_budget')
    maps=json.loads(raw)
    retained=json.loads(gzip.decompress(blob('evidence/manual-atlas-full-recipe-20261017/source-recipe.source-maps.json.gz')))
    if maps.get('source_before')!=retained['checksum_candidate']:raise ValueError('manual_compile_complete_source_map')
    before=maps['source_before'];safe_map(before)
    if len(before)!=6007:raise ValueError('manual_compile_full_source_domain')
    composed=json.loads((directory/'source-recipe.json').read_bytes())
    if (composed.get('schema')!='coh-full-manual-atlas-checksum-source-recipe-v1' or composed.get('passed') is not True
            or composed.get('original_files')!=5995 or composed.get('complete_source_files')!=6007
            or composed.get('sole_additional_changed_path')!=recipe.base.CHECKSUM or composed.get('build_executed') is not False
            or composed.get('accepted_manifest_sha256')!=recipe.MANIFEST_SHA):raise ValueError('manual_compile_source_recipe_profile')
    for phase in ('source_after_configure','source_after_build'):
        safe_map(maps.get(phase));check_post_source(before,maps[phase])
    if maps.get('source_at_cleanup')!=maps.get('source_after_build'):raise ValueError('manual_compile_final_source_snapshot')
    if maps.get('generated_source')!=check_post_source(before,maps['source_after_build']):raise ValueError('manual_compile_generated_map')
    with gzip.open(directory/'generated-source.json.gz','rb') as stream:generated_raw=stream.read(32*1024*1024+1)
    if len(generated_raw)>32*1024*1024:raise ValueError('manual_compile_generated_decode_budget')
    generated_bytes=json.loads(generated_raw)
    if not isinstance(generated_bytes,dict) or {n:digest(base64.b64decode(data,validate=True)) for n,data in generated_bytes.items()}!=maps['generated_source']:
        raise ValueError('manual_compile_generated_source_capture')
    paths=value.get('command_paths',{});source=paths.get('source','');build_dir=paths.get('build','');deps=paths.get('dependencies',{})
    normalized=lambda p:p.replace('\\','/') if type(p) is str else ''
    prefix=normalized(source).removesuffix('/source')
    if not prefix or prefix==normalized(source) or '..' in prefix.split('/') or normalized(build_dir)!=prefix+'/build' or set(deps)!={v[0] for v in recipe.DEPENDENCIES.values()}:
        raise ValueError('manual_compile_path_ownership')
    expected_records=[]
    for module,(name,repository,pin,patch) in recipe.DEPENDENCIES.items():
        remote=repository if repository.startswith('https://') else 'https://github.com/'+repository+'.git'
        if normalized(deps[name])!=prefix+'/dependencies/'+name:raise ValueError('manual_compile_dependency_owner')
        row=maps.get('dependencies',{}).get(name,{})
        safe_map(row.get('before'));safe_map(row.get('after'))
        if row.get('repository')!=remote or row.get('commit')!=pin:raise ValueError('manual_compile_dependency_commit')
        expected=dependency_expected(row['before'],recipe.git(root,'show',commit+':upstream/ouroboros/'+patch) if patch else None)
        if row.get('expected_after_cmake_patch')!=expected or row['after']!=expected or row.get('at_cleanup')!=expected:raise ValueError('manual_compile_dependency_bytes')
        git=lock['tools']['git']['path'];destination=deps[name]
        expected_records.extend([(name+'-init',[git,'init',destination]),(name+'-fetch',[git,'-C',destination,'fetch','--depth=1',remote,pin]),
                                 (name+'-checkout',[git,'-C',destination,'-c','core.autocrlf=false','checkout','--detach',pin])])
        if patch:
            for label,extra in [('patch-check',['--check']),('patch',[])]:
                expected_records.append((name+'-'+label,[git,'-C',destination,'-c','core.autocrlf=false','apply',*extra,str(Path(source)/patch)]))
    plan=json.loads(blob('evidence/manual-atlas-full-recipe-20261017/static-build-plan.json'))
    configure,compile_command=command_argv(plan,source,build_dir,lock['tools']['patch']['path'],lock,deps)
    expected_records.extend([('configure-full-manual',configure),('build-full-manual',compile_command)])
    normal_argv=lambda argv:[str(x).replace('\\','/') for x in argv] if isinstance(argv,list) else None
    if normal_argv(value.get('exact_configure_argv'))!=normal_argv(configure) or normal_argv(value.get('exact_build_argv'))!=normal_argv(compile_command) or len(value.get('commands',[]))!=len(expected_records):raise ValueError('manual_compile_command_count_profile')
    for row,(name,argv) in zip(value['commands'],expected_records):
        if (row.get('name')!=name or normal_argv(row.get('argv'))!=normal_argv(list(map(str,argv))) or type(row.get('returncode')) is not int or row['returncode']!=0
                or row.get('log_truncated') is not False or row.get('log_sha256')!=host.sha(directory/(name+'.log'))):raise ValueError('manual_compile_exact_command_result')
    cache_profile(directory/'CMakeCache.txt',lock)
    if compiler_profile(directory,lock,True)!=value.get('compiler_profile'):raise ValueError('manual_compile_retained_compiler_profile')
    for name in ('DbServer.exe','CrashRpt.dll'):
        observed={'identity':host.pe_identity(directory/name,3 if name=='DbServer.exe' else None),'imports':pe_imports(directory/name),'executed':False}
        if value.get('artifacts',{}).get(name)!=observed:raise ValueError('manual_compile_pe_profile')
    if host.sha(directory/'DbServer.exe')!=binary_sha:raise ValueError('manual_compile_caller_binary_pin')
    return {'admitted':True,'scope':'Caller-pinned full manual PG/Wine compile only; ordinary PE import inventory, no execution or runtime dependency admission.',
            'binary_sha256':binary_sha,**{name:False for name in FALSES}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='operation',required=True)
    b=sub.add_parser('build');b.add_argument('--source-root',type=Path,required=True);b.add_argument('--expected-commit',required=True)
    b.add_argument('--output',type=Path,required=True);b.add_argument('--host-qualification',type=Path,required=True);b.add_argument('--expected-host-qualification-sha256',required=True)
    b.add_argument('--toolchain-lock',type=Path,required=True);b.add_argument('--expected-toolchain-sha256',required=True)
    a=sub.add_parser('admit');a.add_argument('--source-root',type=Path,required=True);a.add_argument('--stage',type=Path,required=True)
    a.add_argument('--expected-receipt-sha256',required=True);a.add_argument('--expected-binary-sha256',required=True);a.add_argument('--expected-toolchain-sha256',required=True)
    args=p.parse_args();result=build(args) if args.operation=='build' else admit(args.stage,args.expected_receipt_sha256,args.expected_binary_sha256,args.expected_toolchain_sha256,args.source_root)
    print(json.dumps(result if args.operation=='admit' else {'passed':result['passed'],'failure':result.get('failure'),'service_executed':False}));raise SystemExit(0 if result.get('passed',result.get('admitted',False)) else 1)
