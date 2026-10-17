#!/usr/bin/env python3
"""Execute an isolated, exact-original AuthServer encrypted account experiment.

This is an AuthServer-only milestone: no shard, DbServer, MapServer, checksum
exception, production account or accepted Android runtime is admitted.
"""
import argparse
import ctypes
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import struct
import subprocess
import tarfile
import tempfile
import time

import auth_service_profile as profile
import hosted_auth_stage as prior
import password_fixture
import candidate_service

HERE = Path(__file__).resolve().parent
CASES = ('valid', 'wrong-password', 'missing-account', 'corrupt-frame')
OPENSSL_SHA256 = '603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a'
ODBC_IDENTITY = HERE.parent / 'evidence/hosted-odbc-38948147656/artifact-identity.json'
PROBE_BUILD_POLICY = {
    'openssl_configuration': ['VC-WIN64A', 'no-shared', 'no-asm', 'no-tests', 'no-module'],
    'openssl_build': ['nmake', '/nologo', 'build_libs'],
    'cmake_generator': 'Visual Studio 18 2026', 'architecture': 'x64',
    'configuration': 'Release', 'parallel': '2',
}



def admit_odbc_receipt(directory):
    """Reuse completed binding evidence, never execute the SQL-only job again."""
    pins = json.loads(ODBC_IDENTITY.read_text())
    for name, expected in pins['files'].items():
        path = directory / name
        if (path.is_symlink() or not path.is_file() or path.stat().st_size != expected['bytes']
                or prior.sha(path) != expected['sha256']):
            raise ValueError('odbc_receipt_identity_mismatch')
    receipt = json.loads((directory / 'receipt.json').read_text())
    result = receipt.get('control_executions', {}).get('original-odbc', {}).get('result', {})
    if (receipt.get('passed') is not True or receipt.get('original_source_tree') != prior.ORIGINAL_TREE
            or receipt.get('owned_localdb_cleanup_complete') is not True
            or receipt.get('source_inputs_unchanged') is not True
            or receipt.get('original_authserver_started') is not False
            or receipt.get('real_account_login_verified') is not False
            or any(result.get(key) is not True for key in ('passed', 'connection_succeeded',
                'password_output_conversion', 'zero_hash_output_conversion', 'missing_password_rejected',
                'stats_outputs', 'timestamp_conversion', 'missing_stats_rejected'))):
        raise ValueError('odbc_receipt_scope_mismatch')
    return {'run_id': pins['run_id'], 'artifact_id': pins['artifact_id'],
            'archive_sha256': pins['artifact_sha256'], 'receipt_sha256': prior.sha(directory / 'receipt.json'),
            'sql_only_controls_repeated': False, 'previous_real_login_inherited': False}


def admit_openssl(archive):
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size > 64 * 1024 * 1024 or prior.sha(archive) != OPENSSL_SHA256:
        raise ValueError('openssl_archive_identity_mismatch')
    return {'version': '3.5.9', 'sha256': OPENSSL_SHA256, 'bytes': archive.stat().st_size}


def probe_identity(path):
    if path.is_symlink() or path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('probe_binary_admission_failed')
    data = path.read_bytes()
    if len(data) < 128 or data[:2] != b'MZ':
        raise ValueError('probe_dos_header')
    offset = struct.unpack_from('<I', data, 60)[0]
    if (offset < 64 or offset + 96 > len(data) or data[offset:offset+4] != b'PE\0\0'
            or struct.unpack_from('<H', data, offset+4)[0] != 0x8664
            or struct.unpack_from('<H', data, offset+24)[0] != 0x20b
            or struct.unpack_from('<H', data, offset+92)[0] != 3):
        raise ValueError('probe_x64_console_identity_mismatch')
    return {'sha256': prior.sha(path), 'bytes': len(data), 'machine': 'AMD64', 'format': 'PE32+',
            'subsystem': 3, 'header_identity_only': True}


def admit_probe_source(root, pins):
    """Bind every transitive local header, profile, fixture and build policy."""
    for name, expected in pins['source_files_sha256'].items():
        path = root / name
        if path.is_symlink() or not path.is_file() or prior.sha(path) != expected:
            raise ValueError('reused_probe_source_identity_mismatch')
    generated = {
        'fixture_header_sha256': hashlib.sha256(profile.fixture_header().encode()).hexdigest(),
        'project_generator_sha256': hashlib.sha256(inspect.getsource(prepare_probe_project).encode()).hexdigest(),
        'build_policy': PROBE_BUILD_POLICY, 'openssl_archive_sha256': OPENSSL_SHA256,
    }
    if generated != pins['generated_inputs']:
        raise ValueError('reused_probe_generated_input_mismatch')
    return generated


def admit_probe_reuse(directory, root):
    """Reuse this exact built probe; preserve the failed service admission scope."""
    pins = json.loads((HERE / 'probe-build-reuse-pins.json').read_text())
    for name, expected in pins['files'].items():
        path = directory / name
        if (path.is_symlink() or not path.is_file() or path.stat().st_size != expected['bytes']
                or path.stat().st_size > prior.LOG_LIMIT or prior.sha(path) != expected['sha256']):
            raise ValueError('reused_probe_file_identity_mismatch')
    generated = admit_probe_source(root, pins)
    receipt = json.loads((directory / 'receipt.json').read_text())
    if (receipt.get('schema') != 'coh-hosted-auth-only-login-v1'
            or receipt.get('repository_commit') != pins['repository_commit']
            or receipt.get('original_source_tree') != prior.ORIGINAL_TREE
            or receipt.get('passed') is not False or receipt.get('failure') != 'listener_inventory_shape'
            or receipt.get('original_authserver_started') is not True
            or receipt.get('encrypted_account_login_verified') is not False
            or receipt.get('authenticated_db_map_handoff_verified') is not False
            or receipt.get('owned_authserver_cleanup_complete') is not False
            or receipt.get('owned_localdb_cleanup_complete') is not True
            or receipt.get('owned_firewall_cleanup_complete') is not True
            or receipt.get('private_files_removed') is not True
            or receipt.get('source_inputs_unchanged') is not True or receipt.get('probe_results') != {}):
        raise ValueError('reused_probe_receipt_scope_mismatch')
    for name in ('configure-openssl','build-openssl','configure-native-probe','build-native-probe'):
        records = [row for row in receipt.get('commands', []) if row.get('name') == name]
        if (len(records) != 1 or type(records[0].get('returncode')) is not int or records[0]['returncode'] != 0
                or records[0].get('log_sha256') != pins['files'][name + '.log']['sha256']
                or records[0].get('log_truncated') is not False):
            raise ValueError('reused_probe_build_not_qualified')
    normalize = lambda rows: {name.replace('\\', '/'): value for name, value in rows.items()}
    if (normalize(receipt.get('native_probe_inputs_sha256', {})) != pins['probe_c_inputs_sha256']
            or normalize(receipt.get('profile', {}).get('native_source_sha256', {})) != pins['profile_native_inputs_sha256']
            or {key: value for key, value in receipt.get('profile', {}).items() if key != 'native_source_sha256'} != pins['original_profile']):
        raise ValueError('reused_probe_profile_source_mismatch')
    for name, expected in {**pins['probe_c_inputs_sha256'], **pins['profile_native_inputs_sha256']}.items():
        if pins['source_files_sha256'].get(name) != expected:
            raise ValueError('reused_probe_source_closure_incomplete')
    binary = probe_identity(directory / 'coh-auth-only.exe')
    if binary != receipt.get('native_probe') or receipt.get('openssl_source', {}).get('sha256') != OPENSSL_SHA256:
        raise ValueError('reused_probe_binary_receipt_mismatch')
    return {'run_id': pins['run_id'], 'artifact_id': pins['artifact_id'], 'archive_sha256': pins['archive_sha256'],
            'repository_commit': pins['repository_commit'], 'files': pins['files'], 'native_probe': binary,
            'native_probe_inputs_sha256': receipt['native_probe_inputs_sha256'],
            'openssl_static_library_sha256': receipt['openssl_static_library_sha256'],
            'openssl_source': receipt['openssl_source'],
            'original_probe_build_tools': receipt['probe_build_tools'], 'rebuilt': False,
            'source_files_sha256': pins['source_files_sha256'], 'generated_inputs': generated,
            'original_build_driver_sha256': pins['original_build_driver_sha256'],
            'prior_probe_executed': False, 'prior_original_authserver_started': True,
            'prior_service_cleanup_verified': False, 'real_login_qualification_inherited': False}


def admit_probe_result(result, case):
    """Only an exact redacted native receipt can advance this narrow milestone."""
    expected_keys = {'schema', 'passed', 'case', 'state', 'protocol', 'shards', 'received_frames',
                     'sent_bytes', 'failure_command', 'failure_reason', 'system_error', 'elapsed_ms',
                     'socket_cleanup_complete', 'password_retained_after_close', 'db_handoff_attempted',
                     'real_server_provenance_verified_by_probe', 'openssl_runtime'}
    integers = ('state', 'protocol', 'shards', 'received_frames', 'sent_bytes', 'failure_command',
                'failure_reason', 'system_error', 'elapsed_ms')
    if (case not in CASES or not isinstance(result, dict) or set(result) != expected_keys
            or result.get('schema') != 'coh-auth-only-probe-v1' or result.get('case') != case
            or result.get('passed') is not True
            or any(type(result.get(key)) is not int for key in integers)
            or result.get('protocol') != profile.PROTOCOL or result.get('shards') != 0
            or not 0 <= result.get('elapsed_ms', -1) <= 20000
            or result.get('sent_bytes', 0) <= 0 or result.get('sent_bytes', 0) > 4096
            or result.get('socket_cleanup_complete') is not True
            or any(result.get(key) is not False for key in ('password_retained_after_close',
                    'db_handoff_attempted', 'real_server_provenance_verified_by_probe'))
            or not re.fullmatch(r'OpenSSL 3\.5\.9 [A-Za-z0-9 -]{1,32}', str(result.get('openssl_runtime', '')))):
        raise ValueError('native_probe_scope_mismatch')
    # CohLoginState values belong to the unchanged qualified native header.
    if case == 'valid':
        if result['state'] != 5 or result['received_frames'] != 3 or result['failure_command'] or result['failure_reason'] or result['system_error']:
            raise ValueError('native_positive_login_not_complete')
    elif case in ('wrong-password', 'missing-account'):
        if result['state'] != 12 or result['received_frames'] != 1 or result['failure_command'] != 1 or result['failure_reason'] != (3 if case == 'wrong-password' else 2):
            raise ValueError('native_account_negative_control_failed')
    elif result['state'] != 12 or result['received_frames'] != 1 or result['failure_command'] != 0:
        raise ValueError('native_corrupt_frame_control_failed')
    return result


def command_script(path, vcvars, arguments):
    """Create a build-only batch script; all arguments are public paths/options."""
    if any(any(c in str(value) for c in ('\r', '\n', '%', '!', '"', '&', '|', '<', '>')) for value in (path, vcvars, *arguments)):
        raise ValueError('unsafe_build_command_path')
    line = subprocess.list2cmdline(list(map(str, arguments)))
    path.write_text('@echo off\r\ncall "' + str(vcvars) + '" x64 >nul\r\nif errorlevel 1 exit /b 1\r\n'
                    + line + '\r\nexit /b %errorlevel%\r\n', encoding='ascii')


def select_native_perl(candidates):
    # OpenSSL's MSVC configuration rejects MSYS/Cygwin Perl even when `perl`
    # exists on PATH. Admit the actual interpreter, not its filename alone.
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            try:
                if prior.capture([candidate, '-MConfig', '-e', 'print $Config{osname};']) == 'MSWin32':
                    return Path(candidate)
            except ValueError:
                pass
    raise ValueError('native_windows_perl_required')


def prepare_probe_project(root, directory, openssl_source):
    """Keep original login/auth C files byte-identical; wrap only host syscalls."""
    directory.mkdir()
    (directory / 'fixture_constants.h').write_text(profile.fixture_header(), encoding='ascii')
    native = root / 'native-android'
    windows = HERE / 'windows'
    sources = [windows / 'auth_only_probe.c', windows / 'winsock_compat.c', windows / 'wrapped_login.c',
               native / 'engine/auth/coh_auth.c', native / 'engine/auth/coh_auth_openssl.c',
               native / 'src/coh_blowfish.c', native / 'protocol/coh_protocol.c']
    def quoted(path):
        return '"' + path.as_posix().replace('"', '') + '"'
    (directory / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.24)\nproject(CohAuthOnly C)\nset(CMAKE_C_STANDARD 11)\n'
        'set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)\nadd_executable(coh-auth-only\n'
        + '\n'.join(quoted(path) for path in sources) + ')\n'
        + 'target_compile_definitions(coh-auth-only PRIVATE _CRT_SECURE_NO_WARNINGS WIN32_LEAN_AND_MEAN _WIN32_WINNT=0x0601 WINVER=0x0601)\n'
        + 'target_include_directories(coh-auth-only PRIVATE ' + ' '.join(quoted(path) for path in
            (directory, windows / 'compat', openssl_source / 'include', native / 'include')) + ')\n'
        + 'target_link_libraries(coh-auth-only PRIVATE ' + quoted(openssl_source / 'libcrypto.lib')
        + ' ws2_32 gdi32 crypt32 bcrypt advapi32 user32)\n', encoding='utf-8')
    return sources


def prepare_intact_probe_project(root, directory, openssl_source):
    """Separate generator preserves historical project admission byte-for-byte."""
    sources = prepare_probe_project(root, directory, openssl_source)
    old, new = HERE / 'windows/auth_only_probe.c', HERE / 'windows/intact_probe.c'
    project = directory / 'CMakeLists.txt'
    text = project.read_text()
    old_line, new_line = '"' + old.as_posix() + '"', '"' + new.as_posix() + '"'
    if text.count(old_line) != 1:
        raise ValueError('intact_probe_project_source_mismatch')
    project.write_text(text.replace(old_line, new_line), encoding='utf-8')
    return [new if path == old else path for path in sources]


def build_intact_probe(root, temporary, output, archive, runner, proof):
    """Necessary new probe link; no original server or accepted APK is rebuilt."""
    with tarfile.open(archive) as value:
        value.extractall(temporary / 'openssl', filter='data')
    ssl_source = temporary / 'openssl/openssl-3.5.9'
    vswhere = Path(os.environ['ProgramFiles(x86)']) / 'Microsoft Visual Studio/Installer/vswhere.exe'
    vs = Path(prior.capture([vswhere, '-latest', '-products', '*', '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath']))
    vcvars = vs / 'VC/Auxiliary/Build/vcvarsall.bat'
    if not vcvars.is_file():
        raise ValueError('native_probe_build_tools_unavailable')
    perl = select_native_perl([shutil.which('perl'), 'C:/Strawberry/perl/bin/perl.exe'])
    build_tools = {'native_perl_sha256':prior.sha(perl), 'perl_osname':'MSWin32', 'vcvarsall_sha256':prior.sha(vcvars)}
    for name, arguments, timeout in (
            ('configure-intact-openssl', [str(perl), 'Configure', *PROBE_BUILD_POLICY['openssl_configuration']], 180),
            ('build-intact-openssl', PROBE_BUILD_POLICY['openssl_build'], 900)):
        script = temporary / (name + '.cmd')
        command_script(script, vcvars, arguments)
        runner.run(name, ['cmd.exe','/d','/c',script], cwd=ssl_source, timeout=timeout)
    project, build = temporary / 'intact-project', temporary / 'intact-build'
    prepare_intact_probe_project(root, project, ssl_source)
    runner.run('configure-intact-probe', ['cmake','-S',project,'-B',build,'-G',PROBE_BUILD_POLICY['cmake_generator'],'-A',PROBE_BUILD_POLICY['architecture']], timeout=180)
    runner.run('build-intact-probe', ['cmake','--build',build,'--config',PROBE_BUILD_POLICY['configuration'],'--parallel',PROBE_BUILD_POLICY['parallel']], timeout=180)
    binary = build / 'Release/coh-auth-only.exe'
    shutil.copy2(binary, output / 'coh-auth-intact.exe')
    if probe_identity(binary) != probe_identity(output / 'coh-auth-intact.exe'):
        raise ValueError('intact_probe_changed_during_copy')
    shutil.copy2(build / 'CMakeCache.txt', output / 'intact-probe-CMakeCache.txt')
    shutil.copy2(project / 'CMakeLists.txt', output / 'intact-probe-CMakeLists.txt')
    pins = json.loads((HERE / 'probe-build-reuse-pins.json').read_text())
    inputs = {name:prior.sha(root / name) for name in pins['source_files_sha256']}
    inputs[(HERE / 'windows/intact_probe.c').relative_to(root).as_posix()] = prior.sha(HERE / 'windows/intact_probe.c')
    details = {'binary':probe_identity(output / 'coh-auth-intact.exe'),'source_files_sha256':inputs,
        'fixture_header_sha256':prior.sha(project / 'fixture_constants.h'),
        'historical_project_generator_sha256':hashlib.sha256(inspect.getsource(prepare_probe_project).encode()).hexdigest(),
        'intact_project_generator_sha256':hashlib.sha256(inspect.getsource(prepare_intact_probe_project).encode()).hexdigest(),
        'build_function_sha256':hashlib.sha256(inspect.getsource(build_intact_probe).encode()).hexdigest(),
        'generated_project_sha256':prior.sha(project / 'CMakeLists.txt'), 'build_policy':PROBE_BUILD_POLICY,
        'openssl_source':admit_openssl(archive),'openssl_static_library_sha256':prior.sha(ssl_source / 'libcrypto.lib'),
        'build_tools':build_tools,'send_cap':1024,'receive_cap':11,'forced_partial_send_calls':False,
        'receiver_segmentation_controlled':False,'general_tcp_segmentation_accepted':False}
    retained = {'openssl-3.5.9.tar.gz':archive, 'libcrypto.lib':ssl_source / 'libcrypto.lib',
                'configdata.pm':ssl_source / 'configdata.pm'}
    retained.update({path.relative_to(ssl_source).as_posix():path for path in (ssl_source / 'include').rglob('*') if path.is_file()})
    total = sum(path.stat().st_size for path in retained.values())
    if total <= 128 * 1024 * 1024 and len(retained) <= 2048 and not any(path.is_symlink() for path in retained.values()):
        retained_root = output / 'intact-openssl-reuse'
        for name, source in retained.items():
            destination = retained_root / name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,destination)
            if prior.sha(destination) != prior.sha(source):
                raise ValueError('retained_crypto_copy_mismatch')
        manifest = {'schema':'coh-intact-openssl-build-ownership-v1','total_bytes':total,
                    'source':details['openssl_source'],'build_policy':PROBE_BUILD_POLICY,'build_tools':build_tools,
                    'files':{name:{'bytes':path.stat().st_size,'sha256':prior.sha(path)} for name,path in retained.items()},
                    'future_reuse_requires_separate_exact_admission':True}
        (retained_root / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        details['crypto_retained'] = {'retained':True,'files':len(retained),'bytes':total,'manifest_sha256':prior.sha(retained_root / 'manifest.json')}
    else:
        details['crypto_retained'] = {'retained':False,'bytes':total,'reason':'bounded_artifact_limit'}
    proof['intact_probe_build'] = details
    return output / 'coh-auth-intact.exe'


def admit_fragmented_observation(result):
    """Retain known partial-send behavior without declaring TCP support."""
    if result.get('passed') is True:
        admit_probe_result(result, 'valid')
        return {'observation':'login_under_capped_sends','receipt':result,'general_tcp_segmentation_accepted':False}
    expected = {'schema':'coh-auth-only-probe-v1','passed':False,'case':'valid','state':12,'protocol':profile.PROTOCOL,
                'shards':0,'received_frames':1,'sent_bytes':170,'failure_command':0,'failure_reason':0,'system_error':108,
                'socket_cleanup_complete':True,'password_retained_after_close':False,'db_handoff_attempted':False,
                'real_server_provenance_verified_by_probe':False}
    if (set(result) != set(expected) | {'elapsed_ms','openssl_runtime'}
            or any(type(result.get(key)) is not type(value) or result.get(key) != value for key,value in expected.items())
            or type(result.get('elapsed_ms')) is not int or not 0 <= result['elapsed_ms'] <= 20000
            or not re.fullmatch(r'OpenSSL 3\.5\.9 [A-Za-z0-9 -]{1,32}',str(result.get('openssl_runtime','')))):
        raise ValueError('fragmented_probe_observation_changed')
    return {'observation':'reset_after_encrypted_login_request','receipt':result,'general_tcp_segmentation_accepted':False}


def owned_process_snapshot(pid):
    if type(pid) is not int or not 1 <= pid <= 0xffffffff:
        raise ValueError('owned_process_id_invalid')
    code = ("$ErrorActionPreference='Stop';$p=Get-Process -Id " + str(pid) +
            " -ErrorAction SilentlyContinue; if($p){ConvertTo-Json -Compress -InputObject @{pid=[long]$p.Id;exists=$true;name=$p.ProcessName;started_utc_ticks=$p.StartTime.ToUniversalTime().Ticks}}" +
            " else {ConvertTo-Json -Compress -InputObject @{pid=" + str(pid) + ";exists=$false}}")
    value = json.loads(prior.capture(['pwsh','-NoProfile','-NonInteractive','-Command',code]))
    if not isinstance(value,dict) or type(value.get('pid')) is not int or value['pid'] != pid or type(value.get('exists')) is not bool:
        raise ValueError('owned_process_snapshot_shape')
    if value['exists']:
        if (set(value) != {'pid','exists','name','started_utc_ticks'} or type(value.get('name')) is not str or value['name'].lower() != 'sqlservr'
                or type(value['started_utc_ticks']) is not int or value['started_utc_ticks'] <= 0):
            raise ValueError('owned_sql_process_identity_mismatch')
    elif set(value) != {'pid','exists'}:
        raise ValueError('owned_process_snapshot_shape')
    return value


def decode_job_members(assigned, listed, members):
    if (type(assigned) is not int or type(listed) is not int or assigned != listed or not 0 <= listed <= 64
            or len(members) != listed or len(set(members)) != listed
            or any(type(pid) is not int or not 1 <= pid <= 0xffffffff for pid in members)):
        raise ValueError('owned_job_member_inventory_shape')
    return members


class OwnedJob:
    """Kill-on-close Job Object prevents an interrupted coordinator orphaning AuthServer."""
    def __init__(self):
        from ctypes import wintypes as w
        class Limits(ctypes.Structure):
            _fields_ = [('ProcessTime', ctypes.c_int64), ('JobTime', ctypes.c_int64), ('Flags', w.DWORD),
                        ('MinimumWorkingSet', ctypes.c_size_t), ('MaximumWorkingSet', ctypes.c_size_t),
                        ('ActiveProcessLimit', w.DWORD), ('Affinity', ctypes.c_size_t),
                        ('PriorityClass', w.DWORD), ('SchedulingClass', w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ('ReadCount','WriteCount','OtherCount','ReadBytes','WriteBytes','OtherBytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('Basic', Limits), ('IO', IO), ('ProcessMemory', ctypes.c_size_t), ('JobMemory', ctypes.c_size_t),
                        ('PeakProcessMemory', ctypes.c_size_t), ('PeakJobMemory', ctypes.c_size_t)]
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = (ctypes.c_void_p, w.LPCWSTR)
        self.kernel.CreateJobObjectW.restype = w.HANDLE
        self.kernel.SetInformationJobObject.argtypes = (w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD)
        self.kernel.AssignProcessToJobObject.argtypes = (w.HANDLE, w.HANDLE)
        self.kernel.TerminateJobObject.argtypes = (w.HANDLE, w.UINT)
        self.kernel.CloseHandle.argtypes = (w.HANDLE,)
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ValueError('auth_process_job_create_failed')
        limits = Extended()
        limits.Basic.Flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.kernel.CloseHandle(self.handle)
            self.handle = None
            raise ValueError('auth_process_job_limit_failed')

    def assign(self, process):
        if not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise ValueError('auth_process_job_assignment_failed')

    def process_ids(self):
        from ctypes import wintypes as w
        class Members(ctypes.Structure):
            _fields_ = [('assigned',w.DWORD),('listed',w.DWORD),('pids',ctypes.c_size_t*64)]
        self.kernel.QueryInformationJobObject.argtypes = (w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD))
        self.kernel.QueryInformationJobObject.restype = w.BOOL
        value, returned = Members(), w.DWORD()
        if not self.kernel.QueryInformationJobObject(self.handle,3,ctypes.byref(value),ctypes.sizeof(value),ctypes.byref(returned)):
            raise ValueError('owned_job_member_query_failed')
        return decode_job_members(value.assigned,value.listed,list(value.pids[:min(value.listed,64)]))

    def stop(self, process):
        terminated = bool(self.kernel.TerminateJobObject(self.handle, 0))
        closed = bool(self.kernel.CloseHandle(self.handle))
        self.handle = None
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            return False
        return terminated and closed and process.poll() is not None


def decode_listener_ports(value):
    values = json.loads(value)
    if (not isinstance(values, list) or len(values) > 16
            or any(type(port) is not int or not 1 <= port <= 65535 for port in values)):
        raise ValueError('listener_inventory_shape')
    return set(values)


def inspect_listeners(pid):
    # Member projection on an empty array may emit one null. Project each
    # existing pipeline object before constructing the explicit result array.
    expression = ("ConvertTo-Json -Compress -InputObject @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
                  "Where-Object OwningProcess -eq " + str(int(pid)) + " | ForEach-Object { [int]$_.LocalPort })")
    return decode_listener_ports(prior.capture(['pwsh', '-NoProfile', '-NonInteractive', '-Command', expression]))


def qualify_listener_projection():
    # Execute the real PowerShell serialization rules before starting a service.
    expression = """$ErrorActionPreference='Stop'; $empty=@();
$one=@([pscustomobject]@{LocalPort=21000});
$many=@([pscustomobject]@{LocalPort=21000},[pscustomobject]@{LocalPort=21001},[pscustomobject]@{LocalPort=21002});
ConvertTo-Json -Compress -InputObject @{
old_empty=(ConvertTo-Json -Compress -InputObject @($empty.LocalPort));
empty=(ConvertTo-Json -Compress -InputObject @($empty | ForEach-Object { [int]$_.LocalPort }));
one=(ConvertTo-Json -Compress -InputObject @($one | ForEach-Object { [int]$_.LocalPort }));
many=(ConvertTo-Json -Compress -InputObject @($many | ForEach-Object { [int]$_.LocalPort }))}
"""
    result = json.loads(prior.capture(['pwsh','-NoProfile','-NonInteractive','-Command',expression]))
    if (not isinstance(result, dict) or set(result) != {'old_empty','empty','one','many'}
            or result['old_empty'] not in ('[]','[null]')
            or decode_listener_ports(result['empty']) != set()
            or decode_listener_ports(result['one']) != {21000}
            or decode_listener_ports(result['many']) != {21000,21001,21002}):
        raise ValueError('powershell_listener_projection_controls_failed')
    return {'passed': True, 'old_empty_projection': result['old_empty'], 'explicit_pipeline_empty': result['empty'],
            'single_port_verified': True, 'three_ports_verified': True, 'real_service_started_by_control': False}


def reserve_ports():
    reservations = []
    try:
        for _ in range(3):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            # Avoid accepting an OS ephemeral port outside the admitted profile.
            for attempt in range(32):
                try:
                    sock.bind(('127.0.0.1', 20000 + secrets.randbelow(40000)))
                    break
                except OSError:
                    if attempt == 31:
                        sock.close()
                        raise ValueError('disposable_port_reservation_failed')
            reservations.append(sock)
        ports = [sock.getsockname()[1] for sock in reservations]
        if any(not 20000 <= port <= 59999 for port in ports):
            raise ValueError('disposable_port_range_unavailable')
        return ports, reservations
    except Exception:
        for sock in reservations:
            sock.close()
        raise


def private_command(command, timeout=90):
    """SQL fixture errors may repeat a row: never put their output in an artifact."""
    result = subprocess.run(list(map(str, command)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
    if result.returncode:
        raise ValueError('private_fixture_command_failed')


def private_logs_bounded(directory):
    # Monitored bound, not an OS filesystem quota. Raw service diagnostics never
    # become uploaded logs even on startup or an encrypted negative-control error.
    total = sum(path.stat().st_size for path in directory.rglob('*') if path.is_file())
    if total > 16 * 1024 * 1024:
        raise ValueError('private_authserver_log_limit')
    return total


def firewall_rule(runner, name, binary, add):
    if not re.fullmatch(r'cohauth-ci-[0-9a-f]{24}', name):
        raise ValueError('firewall_rule_name_invalid')
    if "'" in str(binary) or binary is None:
        raise ValueError('firewall_program_path_invalid')
    if add:
        code = ("$ErrorActionPreference='Stop'; if (@(Get-NetFirewallRule -Name '" + name
                + "' -ErrorAction SilentlyContinue).Count) { throw 'owned rule already exists' }; "
                "if (@(Get-NetFirewallProfile | Where-Object Enabled -eq $false).Count) { throw 'firewall inactive' }; "
                "New-NetFirewallRule -Name '" + name + "' -DisplayName '" + name
                + "' -Direction Inbound -Action Block -Program '" + str(binary)
                + "' -Protocol TCP -RemoteAddress '0.0.0.0-126.255.255.255','128.0.0.0-255.255.255.255' -Profile Any | Out-Null; "
                "if (!(Get-NetFirewallRule -Name '" + name + "' -ErrorAction Stop).Enabled) { throw 'owned rule disabled' }")
    else:
        code = ("$ErrorActionPreference='Stop'; $rule = Get-NetFirewallRule -Name '" + name
                + "' -ErrorAction SilentlyContinue; if ($rule) { "
                "if (($rule | Get-NetFirewallApplicationFilter).Program -ne '" + str(binary)
                + "' -or $rule.Direction -ne 'Inbound' -or $rule.Action -ne 'Block') { throw 'rule ownership mismatch' }; "
                "$rule | Remove-NetFirewallRule }; if (@(Get-NetFirewallRule -Name '"
                + name + "' -ErrorAction SilentlyContinue).Count) { throw 'owned rule remains' }")
    runner.run('firewall-' + ('add' if add else 'remove'), ['pwsh', '-NoProfile', '-NonInteractive', '-Command', code], timeout=45)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-auth-stage', type=Path, required=True)
    parser.add_argument('--reuse-odbc-stage', type=Path, required=True)
    parser.add_argument('--reuse-probe-stage', type=Path)
    parser.add_argument('--openssl-archive', type=Path)
    parser.add_argument('--intact-baseline', action='store_true')
    parser.add_argument('--receive-candidate-stage', type=Path)
    parser.add_argument('--candidate-receipt-sha256')
    parser.add_argument('--candidate-binary-sha256')
    parser.add_argument('--reuse-intact-stage', type=Path)
    args = parser.parse_args()
    candidate_mode = args.receive_candidate_stage is not None
    candidate_options = (args.candidate_receipt_sha256, args.candidate_binary_sha256, args.reuse_intact_stage)
    if candidate_mode:
        if not all(candidate_options) or not args.reuse_probe_stage or args.intact_baseline or args.openssl_archive:
            raise ValueError('candidate_service_requires_exact_reuse_only')
    elif any(value is not None for value in candidate_options):
        raise ValueError('candidate_service_options_without_candidate')
    root, output = args.source_root.resolve(), args.output.resolve()
    identity = prior.require_hosted(root, output, args.expected_commit)
    if prior.capture(['git', '-C', root, 'status', '--porcelain', '--untracked-files=no', '--', 'upstream/ouroboros', 'native-android']):
        raise ValueError('tracked_native_source_inputs_modified')
    original = prior.admit_original_reuse(args.reuse_auth_stage.resolve(), identity['original_source_tree'])
    odbc = admit_odbc_receipt(args.reuse_odbc_stage.resolve())
    reused_probe = admit_probe_reuse(args.reuse_probe_stage.resolve(), root) if args.reuse_probe_stage else None
    if args.intact_baseline and not reused_probe:
        raise ValueError('intact_baseline_requires_historical_probe_control')
    if (not reused_probe or args.intact_baseline) and args.openssl_archive is None:
        raise ValueError('openssl_archive_required_for_probe_build')
    openssl = admit_openssl(args.openssl_archive) if not reused_probe or args.intact_baseline else reused_probe['openssl_source']
    candidate_admission, intact_reuse = None, None
    if candidate_mode:
        candidate_admission = candidate_service.receive_build.admit(args.receive_candidate_stage.resolve(), args.candidate_receipt_sha256, args.candidate_binary_sha256)
        intact_reuse = candidate_service.admit_intact(args.reuse_intact_stage.resolve(), root)
    output.mkdir(parents=True)
    runner = prior.Commands(output)
    proof = {'schema': 'coh-hosted-auth-only-login-v1', **identity, 'passed': False,
             'original_build_reuse': original, 'qualified_odbc_reuse': odbc, 'openssl_source': openssl,
             'original_authserver_launch_attempted': False, 'original_authserver_started': False,
             'encrypted_account_login_verified': False,
             'authenticated_db_map_handoff_verified': False, 'db_checksum_policy_modified': False,
             'native_live_world': False, 'physical_thor_accepted': False, 'commands': runner.records,
             'probe_results': {}, 'private_service_logs_exported': False, 'private_credential_files_exported': False,
             'probe_contains_public_disposable_fixture': True,
             'openssl_source_archive_revalidated_this_run': reused_probe is None or args.intact_baseline,
             'intact_write_baseline_requested':args.intact_baseline,
             'general_tcp_segmentation_accepted':False,
             'receiver_segmentation_controlled':False,
             'probe_observations':{}}
    if args.intact_baseline:
        proof['schema'] = 'coh-hosted-auth-only-intact-baseline-v1'
        proof['qualification_scope'] = 'loopback_normal_send_cap_1024_only'
        proof['forced_partial_send_calls'] = False
    if candidate_mode:
        proof['schema'] = 'coh-hosted-auth-receive-candidate-login-v1'
        proof['qualification_scope'] = 'nonshipping_corrected_original_authserver_loopback_7_and_1024_send_caps'
        proof['candidate_build_admission'] = candidate_admission
        proof['intact_probe_build_reuse'] = intact_reuse
        proof['candidate_authserver_launch_attempted'] = False
        proof['candidate_authserver_started'] = False
        proof['shipping_server_modified'] = False
        proof['fragmented_and_normal_suite_complete'] = False
    instance = 'cohauth-ci-' + secrets.token_hex(12)
    created, firewall_attempted, child, job = False, False, None, None
    localdb, sqlcmd, sql_pid, fragment_probe = None, None, None, None
    cleanup_ok = True
    temporary = Path(tempfile.mkdtemp(prefix='coh-auth-only-', dir=os.environ['RUNNER_TEMP']))
    try:
        proof['listener_projection_controls'] = qualify_listener_projection()
        localdb_candidates = sorted(Path(os.environ['ProgramFiles']).glob('Microsoft SQL Server/*/Tools/Binn/SqlLocalDB.exe'), reverse=True)
        sqlcmd_candidates = sorted(Path(os.environ['ProgramFiles']).glob('Microsoft SQL Server/Client SDK/ODBC/*/Tools/Binn/SQLCMD.EXE'), reverse=True)
        localdb = Path(shutil.which('SqlLocalDB.exe') or (str(localdb_candidates[0]) if localdb_candidates else ''))
        sqlcmd = Path(shutil.which('sqlcmd.exe') or (str(sqlcmd_candidates[0]) if sqlcmd_candidates else ''))
        if not localdb.is_file() or not sqlcmd.is_file():
            raise ValueError('qualified_localdb_tools_unavailable')
        drivers = json.loads(prior.capture(['pwsh', '-NoProfile', '-NonInteractive', '-Command',
                    "ConvertTo-Json -InputObject @((Get-OdbcDriver -Platform '32-bit').Name) -Compress"]))
        if not isinstance(drivers, list) or 'ODBC Driver 17 for SQL Server' not in drivers:
            raise ValueError('qualified_x86_odbc_driver_unavailable')
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\ODBC\\ODBCINST.INI\\ODBC Driver 17 for SQL Server', 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
            driver = Path(os.path.expandvars(winreg.QueryValueEx(key, 'Driver')[0]))
        proof['x86_odbc_driver'] = prior.pe_identity(driver, None)
        if proof['x86_odbc_driver']['sha256'] != '319b6c3b0ab08dd92dc1e5ee6daf3def82503ebbc85944fc1c614cd7a1c7b729':
            raise ValueError('qualified_x86_odbc_driver_identity_changed')
        source_archive = temporary / 'original.tar'
        runner.run('archive-original-source', ['git', '-C', root, 'archive', '--format=tar', '--output=' + str(source_archive),
                   args.expected_commit, 'upstream/ouroboros'], timeout=120)
        with tarfile.open(source_archive) as archive:
            archive.extractall(temporary / 'source', filter='data')
        source = temporary / 'source/upstream/ouroboros'
        proof['profile'] = profile.audit(root, source)
        if reused_probe:
            proof['native_probe_build_reuse'] = reused_probe
            for name, expected in reused_probe['files'].items():
                destination = output / ('coh-auth-only.exe' if name == 'coh-auth-only.exe' else 'reused-probe-' + name)
                shutil.copy2(args.reuse_probe_stage / name, destination)
                if prior.sha(destination) != expected['sha256']:
                    raise ValueError('reused_probe_changed_during_copy')
            probe = output / 'coh-auth-only.exe'
            proof['native_probe'] = probe_identity(probe)
            proof['native_probe_inputs_sha256'] = reused_probe['native_probe_inputs_sha256']
            proof['openssl_static_library_sha256'] = reused_probe['openssl_static_library_sha256']
        else:
            with tarfile.open(args.openssl_archive) as archive:
                archive.extractall(temporary / 'openssl', filter='data')
            ssl_source = temporary / 'openssl/openssl-3.5.9'
            vswhere = Path(os.environ['ProgramFiles(x86)']) / 'Microsoft Visual Studio/Installer/vswhere.exe'
            vs = Path(prior.capture([vswhere, '-latest', '-products', '*', '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath']))
            vcvars = vs / 'VC/Auxiliary/Build/vcvarsall.bat'
            if not vcvars.is_file():
                raise ValueError('native_probe_build_tools_unavailable')
            perl = select_native_perl([shutil.which('perl'), 'C:/Strawberry/perl/bin/perl.exe'])
            proof['probe_build_tools'] = {'native_perl_sha256': prior.sha(perl), 'perl_osname': 'MSWin32',
                                          'vcvarsall_sha256': prior.sha(vcvars)}
            for name, arguments, timeout in (
                    ('configure-openssl', [str(perl), 'Configure', *PROBE_BUILD_POLICY['openssl_configuration']], 180),
                    ('build-openssl', PROBE_BUILD_POLICY['openssl_build'], 900)):
                script = temporary / (name + '.cmd')
                command_script(script, vcvars, arguments)
                runner.run(name, ['cmd.exe', '/d', '/c', script], cwd=ssl_source, timeout=timeout)
            proof['openssl_static_library_sha256'] = prior.sha(ssl_source / 'libcrypto.lib')
            project = temporary / 'probe-project'
            inputs = prepare_probe_project(root, project, ssl_source)
            build = temporary / 'probe-build'
            runner.run('configure-native-probe', ['cmake', '-S', project, '-B', build, '-G', PROBE_BUILD_POLICY['cmake_generator'], '-A', PROBE_BUILD_POLICY['architecture']], timeout=180)
            runner.run('build-native-probe', ['cmake', '--build', build, '--config', PROBE_BUILD_POLICY['configuration'], '--parallel', PROBE_BUILD_POLICY['parallel']], timeout=180)
            probe = build / 'Release/coh-auth-only.exe'
            proof['native_probe'] = probe_identity(probe)
            proof['native_probe_inputs_sha256'] = {str(path.relative_to(root)): prior.sha(path) for path in inputs}
            shutil.copy2(probe, output / 'coh-auth-only.exe')
            shutil.copy2(build / 'CMakeCache.txt', output / 'native-probe-CMakeCache.txt')
        if candidate_mode:
            intact_probe = output / 'coh-auth-intact.exe'
            shutil.copy2(args.reuse_intact_stage / 'coh-auth-intact.exe', intact_probe)
            if probe_identity(intact_probe) != intact_reuse['binary']:
                raise ValueError('candidate_intact_probe_copy_identity')
        if args.intact_baseline:
            fragment_probe = probe
            probe = build_intact_probe(root,temporary,output,args.openssl_archive,runner,proof)
        if instance.casefold() in {value.casefold().strip() for value in prior.capture([localdb, 'info']).splitlines()}:
            raise ValueError('generated_instance_already_exists')
        created = True
        runner.run('localdb-create', [localdb, 'create', instance], timeout=60)
        runner.run('localdb-start', [localdb, 'start', instance], timeout=60)
        sql = [sqlcmd, '-S', '(localdb)\\' + instance, '-E', '-C', '-b', '-l', '20', '-t', '120']
        runner.run('localdb-version', [*sql, '-Q', "SET NOCOUNT ON;SELECT CONVERT(varchar(100),SERVERPROPERTY('ProductVersion'));"], timeout=150)
        if '17.0.4025.3' not in (output / 'localdb-version.log').read_text(errors='replace'):
            raise ValueError('qualified_localdb_version_changed')
        runner.run('localdb-memory-bound', [*sql, '-Q', "EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'max server memory (MB)',256;RECONFIGURE;"], timeout=150)
        runner.run('original-schema', [*sql, '-i', source / 'Assets/DBSchemas/cohauth.sql'], timeout=150)
        if args.intact_baseline or candidate_mode:
            runner.run('localdb-owned-process-id', [*sql,'-h','-1','-W','-Q',"SET NOCOUNT ON;SELECT CONVERT(int,SERVERPROPERTY('ProcessID'));"],timeout=150)
            value = (output / 'localdb-owned-process-id.log').read_text().strip()
            if not re.fullmatch(r'[1-9][0-9]{0,9}',value) or int(value)>0xffffffff:
                raise ValueError('owned_sql_process_id_shape')
            sql_pid = int(value)
            proof['owned_sql_process_before_authserver'] = owned_process_snapshot(sql_pid)
            if proof['owned_sql_process_before_authserver']['exists'] is not True:
                raise ValueError('owned_sql_process_not_running')
        credentials = temporary / 'credentials'
        password_fixture.write_private_fixture(credentials)
        (credentials / 'account.sql').write_text(profile.account_sql(), encoding='ascii')
        private_command([*sql, '-i', credentials / 'credential.sql'], timeout=150)
        private_command([*sql, '-i', credentials / 'account.sql'], timeout=150)
        proof['known_disposable_account_seeded'] = True
        runtime = temporary / 'runtime'
        (runtime / 'etc').mkdir(parents=True)
        (runtime / 'logs').mkdir()
        auth = runtime / 'AuthServer.exe'
        if candidate_mode:
            candidate_service.copy_candidate(args.receive_candidate_stage.resolve(), args.candidate_receipt_sha256, args.candidate_binary_sha256, auth)
            candidate_service.observe_sql(proof, 'before_authserver', instance, sql_pid)
        else:
            shutil.copy2(args.reuse_auth_stage / 'AuthServer-original.exe', auth)
            if prior.pe_identity(auth, 2) != original['original_authserver']:
                raise ValueError('original_authserver_changed_during_copy')
        ports, reservations = reserve_ports()
        try:
            (runtime / 'etc/config.txt').write_text(profile.configuration(instance, 'ODBC Driver 17 for SQL Server', ports, runtime / 'logs'), encoding='ascii')
            proof['configuration_sha256'] = prior.sha(runtime / 'etc/config.txt')
            firewall_attempted = True
            firewall_rule(runner, instance, auth, True)
            job = OwnedJob()
        finally:
            for reservation in reservations:
                reservation.close()
        # GUI AuthServer writes only private files. No raw log or credential row
        # is archived. The probe has no arbitrary credential/endpoint arguments.
        proof['candidate_authserver_launch_attempted' if candidate_mode else 'original_authserver_launch_attempted'] = True
        child = subprocess.Popen([str(auth)], cwd=runtime, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proof['candidate_authserver_started' if candidate_mode else 'original_authserver_started'] = True
        proof['authserver_process_id'] = child.pid
        job.assign(child)
        deadline = time.monotonic() + 90
        readiness_observed = False
        while True:
            private_logs_bounded(runtime / 'logs')
            if child.poll() is not None:
                raise ValueError('original_authserver_exited_before_readiness')
            listening = inspect_listeners(child.pid)
            if candidate_mode:
                proof['last_owned_listener_ports'] = sorted(listening)
                proof['listener_readiness_poll_count'] = proof.get('listener_readiness_poll_count', 0) + 1
                if not readiness_observed:
                    candidate_service.observe_sql(proof, 'during_readiness', instance, sql_pid)
                    readiness_observed = True
            if listening - set(ports):
                raise ValueError('unexpected_authserver_listener')
            if time.monotonic() >= deadline:
                if candidate_mode:
                    proof['listener_deadline_reached'] = True
                    candidate_service.observe_sql(proof, 'listener_timeout', instance, sql_pid)
                raise ValueError('original_authserver_listener_deadline')
            if listening == set(ports):
                break
            time.sleep(.25)
        proof['owned_listener_ports'] = ports
        if candidate_mode:
            candidate_service.observe_sql(proof, 'after_listeners', instance, sql_pid)
        baseline_error = None
        try:
            if candidate_mode:
                def ensure_candidate_owned():
                    if child.poll() is not None or inspect_listeners(child.pid) != set(ports):
                        raise ValueError('candidate_service_lost_listener_ownership')
                candidate_service.run_probes(proof, runner, {'fragmented_7': probe, 'normal_1024': intact_probe},
                                             ports[1], runtime, output, ensure_candidate_owned)
            for case in (() if candidate_mode else CASES):
                private_logs_bounded(runtime / 'logs')
                if child.poll() is not None or inspect_listeners(child.pid) != set(ports):
                    raise ValueError('original_authserver_lost_listener_ownership')
                name = ('probe-intact-' if args.intact_baseline else 'probe-') + case
                runner.run(name, [probe, str(ports[1]), case], cwd=runtime, timeout=25, allowed=(0, 1, 2, 3))
                proof['authserver_exit_code_after_' + case] = child.poll()
                result = json.loads((output / (name + '.log')).read_text())
                # The numeric native output remains evidence even if it cannot
                # be admitted as a completed encrypted transaction.
                proof['probe_observations'][case] = result
                proof['probe_results'][case] = admit_probe_result(result, case)
                if case == 'valid':
                    if child.poll() is not None or inspect_listeners(child.pid) != set(ports):
                        raise ValueError('original_authserver_failed_during_positive_login')
                    proof['encrypted_account_login_verified'] = True
            if child.poll() is not None or inspect_listeners(child.pid) != set(ports):
                raise ValueError('original_authserver_failed_after_probes')
        except Exception as error:
            baseline_error = error
        if args.intact_baseline:
            try:
                if child.poll() is not None or inspect_listeners(child.pid) != set(ports):
                    raise ValueError('fragmented_control_service_unavailable')
                runner.run('probe-historical-fragmented-valid', [fragment_probe,str(ports[1]),'valid'],cwd=runtime,timeout=25,allowed=(0,1,2,3))
                result = json.loads((output / 'probe-historical-fragmented-valid.log').read_text())
                proof['historical_fragmented_probe_observation'] = admit_fragmented_observation(result)
                proof['authserver_exit_code_after_fragmented_control'] = child.poll()
                if child.poll() is not None or inspect_listeners(child.pid) != set(ports):
                    raise ValueError('original_authserver_failed_after_fragmented_control')
            except Exception as error:
                proof['fragmented_control_completed'] = False
                if baseline_error is None:
                    baseline_error = error
            else:
                proof['fragmented_control_completed'] = True
        if baseline_error is not None:
            raise baseline_error
        proof['passed'] = True
    except Exception as error:
        # Only our symbolic ValueError codes are exportable. Never serialize a
        # subprocess exception, command output, credential row or driver message.
        proof['failure'] = str(error) if isinstance(error, ValueError) and re.fullmatch('[a-z0-9_]+', str(error)) else type(error).__name__
    finally:
        if child is not None:
            proof['authserver_exit_code_before_owned_stop'] = child.poll()
            if args.intact_baseline or candidate_mode:
                try:
                    proof['authserver_owned_job_members_before_stop'] = job.process_ids()
                    if sql_pid is not None:
                        proof['owned_sql_process_before_authserver_stop'] = owned_process_snapshot(sql_pid)
                        proof['owned_sql_pid_in_authserver_job'] = sql_pid in proof['authserver_owned_job_members_before_stop']
                except Exception:
                    proof['owned_process_diagnostics_complete'] = False
                else:
                    proof['owned_process_diagnostics_complete'] = True
            try:
                proof['owned_authserver_job_stop_complete'] = job.stop(child)
                proof['owned_authserver_listeners_absent'] = not inspect_listeners(child.pid)
                cleanup_ok = proof['owned_authserver_job_stop_complete'] and proof['owned_authserver_listeners_absent']
            except Exception:
                cleanup_ok = False
                try:
                    child.kill()
                    child.wait(timeout=5)
                except Exception:
                    pass
        elif job is not None and job.handle:
            cleanup_ok = bool(job.kernel.CloseHandle(job.handle))
            job.handle = None
        proof['owned_authserver_cleanup_complete'] = cleanup_ok
        if (args.intact_baseline or candidate_mode) and sql_pid is not None:
            try:
                proof['owned_sql_process_after_authserver_stop'] = owned_process_snapshot(sql_pid)
            except Exception:
                proof['owned_process_diagnostics_complete'] = False
        if firewall_attempted:
            try:
                firewall_rule(runner, instance, auth, False)
                proof['owned_firewall_cleanup_complete'] = True
            except Exception:
                proof['owned_firewall_cleanup_complete'] = False
                cleanup_ok = False
        if created:
            sql_clean = prior.cleanup_owned_instance(runner, sqlcmd, localdb, instance)
            proof['owned_localdb_cleanup_complete'] = sql_clean
            cleanup_ok = cleanup_ok and sql_clean
        else:
            proof['owned_localdb_cleanup_complete'] = True
        if (temporary / 'runtime/logs').exists():
            raw_logs = [path for path in (temporary / 'runtime/logs').rglob('*') if path.is_file()]
            proof['private_service_log_summary'] = {'files': len(raw_logs), 'bytes': sum(path.stat().st_size for path in raw_logs), 'content_exported': False}
        try:
            shutil.rmtree(temporary)
            proof['private_files_removed'] = not temporary.exists()
        except Exception:
            proof['private_files_removed'] = False
        try:
            proof['source_inputs_unchanged'] = not prior.capture(['git', '-C', root, 'status', '--porcelain', '--untracked-files=no', '--',
                        'upstream/ouroboros', 'native-android'])
        except Exception:
            proof['source_inputs_unchanged'] = False
        proof['passed'] = proof['passed'] and cleanup_ok and proof['private_files_removed'] and proof['source_inputs_unchanged']
        if args.intact_baseline:
            proof['passed'] = proof['passed'] and proof.get('owned_process_diagnostics_complete',False) and proof.get('fragmented_control_completed',False)
        if candidate_mode:
            proof['passed'] = proof['passed'] and proof.get('owned_process_diagnostics_complete',False) and proof.get('fragmented_and_normal_suite_complete',False)
        (output / 'receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'passed': proof['passed'], 'failure': proof.get('failure'),
                      'encrypted_account_login_verified': proof['encrypted_account_login_verified'],
                      'authenticated_db_map_handoff_verified': False,
                      'intact_write_baseline':args.intact_baseline,'general_tcp_segmentation_accepted':False}))
    return 0 if proof['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
