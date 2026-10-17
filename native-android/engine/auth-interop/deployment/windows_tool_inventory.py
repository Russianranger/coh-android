"""Read-only Windows tool inventory. Never invokes a compiler, CMake or service."""
import argparse,ctypes,hashlib,json,os,re,shutil
from pathlib import Path
import hosted_auth_stage as host

HERE=Path(__file__).resolve().parent
VERSION=re.compile(r'10\.0\.\d+\.\d+')


def file_record(path):
    if path.is_symlink():raise ValueError('inventory_linked_tool_refused')
    path=path.resolve()
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=256*1024*1024:raise ValueError('inventory_regular_bounded_tool_required')
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':host.sha(path)}


def fixed_file_version(path):
    """Read VS_FIXEDFILEINFO using Windows version resources, no tool process."""
    from ctypes import wintypes
    library=ctypes.WinDLL('version',use_last_error=True)
    size_api=library.GetFileVersionInfoSizeW;size_api.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(wintypes.DWORD)];size_api.restype=wintypes.DWORD
    ignored=wintypes.DWORD();size=size_api(str(path),ctypes.byref(ignored))
    if not size:return None
    if size>4*1024*1024:raise ValueError('inventory_version_resource_budget')
    buffer=ctypes.create_string_buffer(size)
    get=library.GetFileVersionInfoW;get.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p];get.restype=wintypes.BOOL
    query=library.VerQueryValueW;query.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(wintypes.UINT)];query.restype=wintypes.BOOL
    pointer=ctypes.c_void_p();length=wintypes.UINT()
    if not get(str(path),0,size,buffer) or not query(buffer,'\\',ctypes.byref(pointer),ctypes.byref(length)) or length.value<52:
        raise ValueError('inventory_version_resource_read')
    # VS_FIXEDFILEINFO is 13 DWORDs. Read only the fixed file-version pair.
    base=ctypes.addressof(buffer)
    if not base<=pointer.value<=base+size-52:raise ValueError('inventory_version_resource_owner')
    values=ctypes.cast(pointer,ctypes.POINTER(wintypes.DWORD*13)).contents
    if values[0]!=0xFEEF04BD:raise ValueError('inventory_version_resource_signature')
    return '.'.join(str(x) for x in (values[2]>>16,values[2]&65535,values[3]>>16,values[3]&65535))


def sdk_root():
    import winreg
    roots=set()
    for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Windows Kits\Installed Roots',0,winreg.KEY_READ|view) as key:
                value,kind=winreg.QueryValueEx(key,'KitsRoot10')
            if kind==winreg.REG_SZ and Path(value).is_dir():roots.add(str(Path(value).resolve()))
        except FileNotFoundError:pass
    if len(roots)!=1:raise ValueError('inventory_unique_sdk_root_required')
    return Path(next(iter(roots)))


def discover(vs_parent,git_path,kits,explicit_vs=None):
    if not vs_parent.is_dir():raise ValueError('inventory_vs18_root_missing')
    candidates=[p for p in vs_parent.iterdir() if (p/'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt').is_file()]
    if len(candidates)>8:raise ValueError('inventory_vs_instance_budget')
    if explicit_vs is not None:
        candidates=[p for p in candidates if p.resolve()==explicit_vs.resolve()]
    if len(candidates)!=1:raise ValueError('inventory_unique_vs18_instance_required')
    vs=candidates[0].resolve();default=vs/'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt'
    if default.stat().st_size>1024:raise ValueError('inventory_toolset_marker_budget')
    toolset=default.read_text(encoding='utf-8-sig').strip()
    if not re.fullmatch(r'14\.\d+\.\d+',toolset):raise ValueError('inventory_exact_default_toolset_required')
    common={'cl':vs/('VC/Tools/MSVC/'+toolset+'/bin/Hostx64/x86/cl.exe'),
            'link':vs/('VC/Tools/MSVC/'+toolset+'/bin/Hostx64/x86/link.exe'),
            'ml':vs/('VC/Tools/MSVC/'+toolset+'/bin/Hostx64/x86/ml.exe'),
            'msbuild':vs/'MSBuild/Current/Bin/MSBuild.exe','git':git_path}
    patches={p/'usr/bin/patch.exe' for p in list(git_path.parents)[:4] if (p/'usr/bin/patch.exe').is_file()}
    if len(patches)!=1:raise ValueError('inventory_unique_git_patch_required')
    common['patch']=next(iter(patches))
    versions=[p.name for p in (kits/'Lib').iterdir() if p.is_dir() and VERSION.fullmatch(p.name)]
    if not 1<=len(versions)<=16:raise ValueError('inventory_sdk_version_budget')
    sdks={}
    for version in sorted(versions):
        required={'rc':kits/('bin/'+version+'/x64/rc.exe'),'kernel32':kits/('Lib/'+version+'/um/x86/kernel32.lib'),
                  'ucrt':kits/('Lib/'+version+'/ucrt/x86/ucrt.lib'),'windows_header':kits/('Include/'+version+'/um/Windows.h')}
        # Partial SDK installations are retained as concrete missing-input names;
        # they do not receive proposed lock candidates.
        sdks[version]={'paths':required,'missing':[n for n,p in required.items() if not p.is_file()]}
    return vs,toolset,default,common,sdks


def observe(common,sdks,version_reader=None):
    if version_reader is None:version_reader=fixed_file_version
    records={name:file_record(p) for name,p in common.items()}
    versions={name:version_reader(Path(row['path'])) for name,row in records.items()}
    sdk_records={}
    for version,row in sdks.items():
        sdk_records[version]={'missing':row['missing'],'files':{n:file_record(p) for n,p in row['paths'].items() if n not in row['missing']}}
    return {'tools':records,'file_versions':versions,'sdks':sdk_records}


def observed_locks(value,vs,toolset,environ):
    versions=value['file_versions'];compiler=versions.get('cl');cmake=versions.get('cmake')
    if not compiler or not re.fullmatch(r'19\.\d+\.\d+\.\d+',compiler) or not cmake or not re.fullmatch(r'\d+\.\d+\.\d+\.0',cmake):return []
    locks=[]
    for sdk,row in value['sdks'].items():
        if row['missing']:continue
        tools=dict(value['tools']);tools['rc']=row['files']['rc']
        locks.append({'schema':'coh-observed-windows-build-tool-lock-v1','requires_independent_review':True,
          'image_os':environ.get('ImageOS'),'image_version':environ.get('ImageVersion'),'generator':'Visual Studio 18 2026','architecture':'Win32',
          'vs_installation':str(vs),'vc_toolset_version':toolset,'windows_sdk_version':sdk,'compiler_version':compiler,'cmake_version':cmake[:-2],
          'tools':tools})
    return locks


def input_state(root):
    return {'commit':host.capture(['git','-C',root,'rev-parse','HEAD']),
            'tracked_dirty':host.capture(['git','-C',root,'status','--porcelain','--untracked-files=no']),
            'helper_inputs':{str(p.relative_to(HERE.parent)):host.sha(p) for p in list(HERE.glob('*.py'))+[HERE.parent/'source_oracle.py']}}


def collect(args):
    root=args.source_root.resolve();output=args.output.resolve();identity=host.require_hosted(root,output,args.expected_commit)
    initial=input_state(root);output.mkdir(parents=True)
    proof=dict(identity,schema='coh-readonly-windows-build-tool-inventory-v1',passed=False,input_state_before=initial,
        compiler_executed=False,cmake_executed=False,source_patched=False,dependencies_fetched=False,service_executed=False,
        toolchain_reviewed=False,compile_permit=False,shipping_runtime_replacement_permit=False)
    try:
        git=shutil.which('git');cmake=shutil.which('cmake')
        if not git or not cmake:raise ValueError('inventory_git_cmake_path_missing')
        parent=Path(os.environ['ProgramFiles'])/'Microsoft Visual Studio/18'
        vs,toolset,default,common,sdks=discover(parent,Path(git).resolve(),sdk_root(),args.vs_installation)
        common['cmake']=Path(cmake).resolve();marker=file_record(default)
        first=observe(common,sdks);proof['observation_before']=first;proof['default_toolset_marker']=marker
        last=observe(common,sdks)
        proof.update(observation_before=first,observation_after=last,default_toolset_marker=marker,
                     vs_installation=str(vs),vc_toolset_version=toolset,all_tool_inputs_stable=first==last and marker==file_record(default))
        proof['observed_lock_candidates']=observed_locks(first,vs,toolset,os.environ)
        proof['passed']=proof['all_tool_inputs_stable']
    except Exception as error:proof['failure']=str(error) if isinstance(error,ValueError) else type(error).__name__
    finally:
        try:
            proof['input_state_after']=input_state(root);proof['source_inputs_unchanged']=initial==proof['input_state_after'] and not initial['tracked_dirty']
        except Exception:proof['source_inputs_unchanged']=False
        proof['passed']=proof['passed'] and proof['source_inputs_unchanged']
        raw=json.dumps(proof,indent=2)+'\n'
        if len(raw)>1024*1024:raise ValueError('inventory_receipt_budget')
        (output/'receipt.json').write_text(raw)
    return proof


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--expected-commit',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--vs-installation',type=Path);a=p.parse_args();result=collect(a)
    print(json.dumps({'passed':result['passed'],'failure':result.get('failure'),'compiler_executed':False,'service_executed':False}));raise SystemExit(0 if result['passed'] else 1)
