"""Controlled original receiver/callback schedules with real frame crypto.

Only local source oracle binaries are built. Existing AuthServer/probe binaries,
SQL profiles, accounts and live services are never rebuilt or executed.
"""
import argparse,hashlib,json,os,re,subprocess,tempfile,sys,importlib.abc,importlib.util
from types import ModuleType
from pathlib import Path

HERE=Path(__file__).resolve().parent
INPUT_COMMIT='d6ef33b3306c496e6d6a9ee2f8c9ab12ffdfbc05'
PINS=HERE/'controlled-completion-source-pins.json'
UTIL='upstream/ouroboros/AuthServer/src/util.cpp'
PACKET='upstream/ouroboros/AuthServer/src/PacketServerEx.cpp'
GLOBAL='upstream/ouroboros/AuthServer/src/GlobalAuth.cpp'
NATIVE=['native-android/src/coh_blowfish.c','native-android/src/byte_reader.h','native-android/include/coh_native_core.h']
BUFFER='upstream/ouroboros/AuthServer/src/IOBuffer.h'
FILES=[BUFFER,'upstream/ouroboros/AuthServer/src/SocketServerEx.cpp','upstream/ouroboros/AuthServer/src/IOSocket.cpp',UTIL,PACKET,GLOBAL,'upstream/ouroboros/AuthServer/src/Protocol.h',*NATIVE]
EXPECTED_RESULT={'passed':True,'checks':811226,'controlled_completion_schedules':16776,'incomplete_prefix_cases':16728,
  'malformed_cases':28,'completion_callbacks':129420,'maximum_ciphertext_bytes':8192,'real_cipher_checksum':True,
  'aligned_crypto_adapter':True,'original_packet_callback':True,'live_receiver_controlled':False,'general_tcp_segmentation_accepted':False}


def sha(data):return hashlib.sha256(data).hexdigest()


def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],timeout=30)


# No project imports occur above this point. Every project module is compiled
# directly from the Git-checked frozen bytes; neither existing sys.modules nor
# Python's bytecode cache may provide executed helper code.
class FrozenSourceLoader(importlib.abc.Loader):
    def __init__(self,path,raw,executed):self.path,self.raw,self.executed=path,raw,executed
    def create_module(self,spec):return None
    def exec_module(self,module):
        module.__file__=str(self.path);module.__cached__=None
        self.executed[str(self.path)]=sha(self.raw)
        exec(compile(self.raw,str(self.path),'exec'),module.__dict__)
class FrozenSourceFinder(importlib.abc.MetaPathFinder):
    def __init__(self,modules,executed):self.modules,self.executed=modules,executed
    def find_spec(self,fullname,path=None,target=None):
        if fullname not in self.modules:return None
        location,raw=self.modules[fullname]
        return importlib.util.spec_from_loader(fullname,FrozenSourceLoader(location,raw,self.executed))
_CHECKED=None

def freeze_inputs(root,commit):
    root=root.resolve()
    if git(root,'rev-parse','HEAD').decode().strip()!=commit:raise ValueError('controlled_checked_head')
    paths=[*HERE.glob('*.py'),HERE.parent/'source_oracle.py',HERE/'controlled_completion_fixture.cpp',PINS]
    baseline=HERE.parent/'evidence/auth-success-38996587760'
    paths.extend(baseline/name for name in ('receipt.json','artifact.zip','source-binder.json'))
    frozen={}
    for path in paths:
        relative=path.resolve().relative_to(root).as_posix()
        if path.is_symlink():raise ValueError('controlled_checked_symlink')
        raw=path.read_bytes()
        if raw!=git(root,'show',commit+':'+relative):raise ValueError('controlled_checked_git_bytes')
        frozen[relative]=raw
    return {'root':root,'commit':commit,'frozen':frozen,'executed':{},'python_modules':sorted(p.name for p in HERE.glob('*.py'))}

def ensure_helpers(root=None,commit=None):
    global _CHECKED,candidate,decoded,extract,verify_auth_acceptance
    root=(root or HERE.parents[3]).resolve()
    commit=commit or git(root,'rev-parse','HEAD').decode().strip()
    if _CHECKED is not None:
        if root!=_CHECKED['root'] or commit!=_CHECKED['commit']:raise ValueError('controlled_checked_context_changed')
        return _CHECKED
    checked=freeze_inputs(root,commit);modules={}
    for relative,raw in checked['frozen'].items():
        path=root/relative
        if path.suffix=='.py' and path.name!=Path(__file__).name and not path.name.startswith('test_'):
            if path.stem in sys.modules:raise ValueError('controlled_helper_preimported')
            modules[path.stem]=(path,raw)
    finder=FrozenSourceFinder(modules,checked['executed']);sys.meta_path.insert(0,finder)
    _CHECKED=checked
    try:
        import receive_candidate as candidate
        from source_audit import decoded,extract
        import verify_auth_acceptance
    except BaseException:
        _CHECKED=None;raise
    return checked

def revalidate_checked(checked):
    if git(checked['root'],'rev-parse','HEAD').decode().strip()!=checked['commit']:raise ValueError('controlled_checked_head_changed')
    if sorted(p.name for p in HERE.glob('*.py'))!=checked['python_modules']:raise ValueError('controlled_checked_module_domain_changed')
    for relative,raw in checked['frozen'].items():
        path=checked['root']/relative
        if path.is_symlink() or path.read_bytes()!=raw:raise ValueError('controlled_checked_inputs_changed')
    return {'source_commit':checked['commit'],'inputs_sha256':{n:sha(b) for n,b in checked['frozen'].items()},
      'executed_project_modules_sha256':checked['executed'],'helpers_compiled_from_checked_source':True,
      'project_pyc_read':False,'preimported_project_modules_accepted':False,'inputs_unchanged':True}


def source_inputs(root):
    ensure_helpers(root)
    if git(root,'rev-parse',INPUT_COMMIT+':upstream/ouroboros').decode().strip()!=candidate.ORIGINAL_TREE:raise ValueError('controlled_original_tree')
    values={name:git(root,'show',INPUT_COMMIT+':'+name) for name in FILES}
    pins=json.loads(PINS.read_bytes())
    if pins!={'input_commit':INPUT_COMMIT,'original_source_tree':candidate.ORIGINAL_TREE,'sha256':{n:sha(b) for n,b in values.items()}}:raise ValueError('controlled_source_identity')
    for n in (candidate.SOCKET,candidate.IO):
        if sha(values[n])!=candidate.SOURCE_SHA256[n]:raise ValueError('controlled_original_receiver_source')
    return values


def generated(values,original=False):
    ensure_helpers()
    patched=values[candidate.SOCKET] if original else candidate.replace_offset(values[candidate.SOCKET])
    functions={
      'CIOSocket::Read':extract(decoded(values[candidate.IO]),'CIOSocket::Read'),
      'CIOSocket::OnIOCallback':extract(decoded(values[candidate.IO]),'CIOSocket::OnIOCallback'),
      'CIOSocket::OnReadCallback':extract(decoded(values[candidate.IO]),'CIOSocket::OnReadCallback'),
      'CSocketServerEx::OnRead':extract(decoded(patched),'CSocketServerEx::OnRead'),
      'CPacketServerEx::OnIOCallback':extract(decoded(values[PACKET]),'CPacketServerEx::OnIOCallback')}
    crypto={name:extract(decoded(values[UTIL]),name) for name in ('BlowFishEncryptPacket','BlowFishDecryptPacket')}
    fixture=(HERE/'controlled_completion_fixture.cpp').read_text()
    buffer=decoded(values[BUFFER]);protocol=decoded(values['upstream/ouroboros/AuthServer/src/Protocol.h'])
    if not re.search(r'^#define BUFFER_SIZE 8192\s*$',buffer,re.M) or not re.search(r'DWORD\s+m_size\s*;',buffer):raise ValueError('controlled_original_buffer_shape')
    aq=re.search(r'enum\s*\{([^}]*\bAQ_MAX\s*,?\s*)\}',protocol,re.S)
    if not aq or re.findall(r'\bAQ_[A-Z_0-9]+\b',aq.group(1))!=['AQ_LOGIN','AQ_SERVER_LIST','AQ_ABOUT_TO_PLAY','AQ_LOGOUT','AQ_LOGIN_MD5','AQ_SERVER_LIST_EXT','AQ_MAX']:raise ValueError('controlled_original_opcode_domain')
    for shape in ('#define BUFFER_SIZE 8192','struct WSABUF {DWORD len;','DWORD m_size=0;'):
        if shape not in fixture:raise ValueError('controlled_fixture_original_win32_shape')

    for marker in ('/* EXACT_PACKET_CRYPTO */','/* EXACT_RECEIVER_FUNCTIONS */'):
        if fixture.count(marker)!=1:raise ValueError('controlled_fixture_insertion_domain')
    keyblock=re.search(r'unsigned char blowFishKey\[\]\s*=\s*\{([^}]+)\}',decoded(values[GLOBAL])).group(1)
    expected=[int(v,16) for v in re.findall(r'0x([0-9a-f]+)',keyblock)]
    localkey=re.search(r'static const uint8_t key\[\]\s*=\s*\{([^}]+)\}',fixture).group(1)
    if expected!=[int(v,16) for v in re.findall(r'0x([0-9a-f]+)',localkey)] or len(expected)!=20:raise ValueError('controlled_original_global_key')
    code=fixture.replace('/* EXACT_PACKET_CRYPTO */','\n'.join(crypto.values())).replace('/* EXACT_RECEIVER_FUNCTIONS */','\n'.join(functions.values()))
    return code,{n:sha(f.encode()) for n,f in dict(functions,**crypto).items()}


def command(argv,timeout=60,env=None):
    result=subprocess.run(list(map(str,argv)),capture_output=True,timeout=timeout,env=env)
    if result.returncode:raise ValueError('controlled_oracle_command_failed:'+result.stderr.decode(errors='replace')[:2000])
    return result


def admit_result(value):
    if json.dumps(value,sort_keys=True)!=json.dumps(EXPECTED_RESULT,sort_keys=True):raise ValueError('controlled_exact_corpus_result')
    return value


def runtime_baseline():
    ensure_helpers()
    directory=HERE.parent/'evidence/auth-success-38996587760';raw=(directory/'receipt.json').read_bytes();archive=(directory/'artifact.zip').read_bytes()
    if sha(raw)!='1b1bea257b8e29f73543cffc4c2148071f738036ee2cd5adc122417160106c94' or sha(archive)!=verify_auth_acceptance.ARCHIVE_SHA:
        raise ValueError('controlled_existing_auth_receipt_identity')
    value=verify_auth_acceptance.admit_receipt(json.loads(raw))
    return {'run_id':38996587760,'receipt_sha256':sha(raw),'archive_sha256':sha(archive),'cases':8,
      'authserver_binary_sha256':value['candidate_admission']['binary']['sha256'],
      'normal_probe_binary_sha256':value['normal_probe_admission']['binary']['sha256'],
      'capped_probe_binary_sha256':value['capped_probe_admission']['native_probe']['sha256'],
      'source_binder_sha256':sha((directory/'source-binder.json').read_bytes()),
      'receipt_verifier_sha256':sha(Path(verify_auth_acceptance.__file__).read_bytes()),
      'receiver_segmentation_controlled':value['receiver_segmentation_controlled'],
      'general_tcp_segmentation_accepted':value['general_tcp_segmentation_accepted'],
      'existing_binary_or_service_reexecuted':False}


def qualify(root,output,expected_commit):
    checked=ensure_helpers(root,expected_commit)
    baseline=runtime_baseline();values=source_inputs(root);code,function_pins=generated(values);old_code,_=generated(values,True);executions={}
    with tempfile.TemporaryDirectory(prefix='coh-controlled-completions-') as owned:
        directory=Path(owned)
        for name in NATIVE:(directory/Path(name).name).write_bytes(values[name])
        cpp=directory/'controlled.cpp';cpp.write_text(code)
        for mode in ('release','asan','ubsan'):
            flags=['-O2'] if mode=='release' else ['-O1','-g','-fsanitize='+('address' if mode=='asan' else 'undefined'),'-fno-omit-frame-pointer','-fno-pie']
            obj=directory/(mode+'.o');binary=directory/mode
            command(['cc','-std=c11',*flags,'-I',directory,'-c',directory/'coh_blowfish.c','-o',obj])
            command(['c++','-std=c++17',*flags,*([] if mode=='release' else ['-no-pie']),'-I',directory,cpp,obj,'-o',binary])
            result=command([binary],timeout=60,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            value=admit_result(json.loads(result.stdout))
            executions[mode]={'result':value,'binary_sha256':sha(binary.read_bytes()),'cipher_object_sha256':sha(obj.read_bytes())}
        if any(executions['release']['result']!=executions[mode]['result'] for mode in ('asan','ubsan')):raise ValueError('controlled_sanitizer_corpus_equality')
        cpp.write_text(old_code);binary=directory/'original-offset-regression'
        command(['c++','-std=c++17','-O2','-I',directory,cpp,directory/'release.o','-o',binary])
        result=subprocess.run([binary],capture_output=True,timeout=30)
        if result.returncode!=1 or b'controlled completion check' not in result.stderr:raise ValueError('controlled_original_offset_regression_not_reproduced')
    proof={'schema':'coh-controlled-source-receive-completion-qualification-v1','passed':True,'input_commit':INPUT_COMMIT,
      'checked_import_provenance':revalidate_checked(checked),
      'original_source_tree':candidate.ORIGINAL_TREE,'source_sha256':{n:sha(b) for n,b in values.items()},'function_sha256':function_pins,
      'fixture_sha256':sha((HERE/'controlled_completion_fixture.cpp').read_bytes()),'qualifier_sha256':sha(Path(__file__).read_bytes()),
      'source_pins_sha256':sha(PINS.read_bytes()),'generated_oracle_sha256':sha(code.encode()),'executions':executions,
      'original_offset_regression_reproduced':True,'source_receiver_completion_sizes_controlled':True,
      'crypto_alignment_adapter':'Copy bounded ciphertext to aligned scratch before exact original packet decrypt, then copy accepted plaintext back.',
      'platform_boundary':'Fixture WSARecv/IOCP/pool/socket refs; original Read/callback/OnRead/packet callback functions execute. Native qualified Blowfish kernel replaces Windows global Blowfish primitive.',
      'source_buffer_bytes':8192,'win32_dword_and_wsabuf_length_bytes':4,
      'scope':'Synthetic global-frame payloads, immediate/deferred capture handlers. No RSA/password/account handler, real socket, Windows IOCP or server execution.',
      'existing_auth_runtime_baseline':baseline,
      'existing_authserver_or_probe_rebuilt':False,'windows_service_executed':False,'live_receiver_segmentation_controlled':False,
      'general_tcp_segmentation_accepted':False,'encrypted_account_login_verified_by_this_oracle':False,'leak_sanitizer_enabled':False}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(proof,indent=2)+'\n');return proof


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--expected-commit',required=True);a=p.parse_args();q=qualify(a.source_root,a.output,a.expected_commit)
    print(json.dumps({'passed':True,'result':q['executions']['release']['result'],'general_tcp_segmentation_accepted':False}))
