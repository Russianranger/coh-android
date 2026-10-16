#!/usr/bin/env python3
"""Execute an isolated, exact-original AuthServer encrypted account experiment.

This is an AuthServer-only milestone: no shard, DbServer, MapServer, checksum
exception, production account or accepted Android runtime is admitted.
"""
import argparse
import ctypes
import hashlib
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

HERE = Path(__file__).resolve().parent
CASES = ('valid', 'wrong-password', 'missing-account', 'corrupt-frame')
OPENSSL_SHA256 = '603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a'
ODBC_IDENTITY = HERE.parent / 'evidence/hosted-odbc-38948147656/artifact-identity.json'


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


def inspect_listeners(pid):
    expression = ("ConvertTo-Json -Compress -InputObject @((Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
                  "Where-Object OwningProcess -eq " + str(int(pid)) + ").LocalPort)")
    values = json.loads(prior.capture(['pwsh', '-NoProfile', '-NonInteractive', '-Command', expression]))
    if not isinstance(values, list) or any(type(value) is not int for value in values):
        raise ValueError('listener_inventory_shape')
    return set(values)


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
    parser.add_argument('--openssl-archive', type=Path, required=True)
    args = parser.parse_args()
    root, output = args.source_root.resolve(), args.output.resolve()
    identity = prior.require_hosted(root, output, args.expected_commit)
    if prior.capture(['git', '-C', root, 'status', '--porcelain', '--untracked-files=no', '--', 'upstream/ouroboros', 'native-android']):
        raise ValueError('tracked_native_source_inputs_modified')
    original = prior.admit_original_reuse(args.reuse_auth_stage.resolve(), identity['original_source_tree'])
    odbc = admit_odbc_receipt(args.reuse_odbc_stage.resolve())
    openssl = admit_openssl(args.openssl_archive)
    output.mkdir(parents=True)
    runner = prior.Commands(output)
    proof = {'schema': 'coh-hosted-auth-only-login-v1', **identity, 'passed': False,
             'original_build_reuse': original, 'qualified_odbc_reuse': odbc, 'openssl_source': openssl,
             'original_authserver_launch_attempted': False, 'original_authserver_started': False,
             'encrypted_account_login_verified': False,
             'authenticated_db_map_handoff_verified': False, 'db_checksum_policy_modified': False,
             'native_live_world': False, 'physical_thor_accepted': False, 'commands': runner.records,
             'probe_results': {}, 'private_service_logs_exported': False, 'private_credential_files_exported': False,
             'probe_contains_public_disposable_fixture': True}
    instance = 'cohauth-ci-' + secrets.token_hex(12)
    created, firewall_attempted, child, job = False, False, None, None
    localdb, sqlcmd = None, None
    cleanup_ok = True
    temporary = Path(tempfile.mkdtemp(prefix='coh-auth-only-', dir=os.environ['RUNNER_TEMP']))
    try:
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
                ('configure-openssl', [str(perl), 'Configure', 'VC-WIN64A', 'no-shared', 'no-asm', 'no-tests', 'no-module'], 180),
                ('build-openssl', ['nmake', '/nologo', 'build_libs'], 900)):
            script = temporary / (name + '.cmd')
            command_script(script, vcvars, arguments)
            runner.run(name, ['cmd.exe', '/d', '/c', script], cwd=ssl_source, timeout=timeout)
        proof['openssl_static_library_sha256'] = prior.sha(ssl_source / 'libcrypto.lib')
        project = temporary / 'probe-project'
        inputs = prepare_probe_project(root, project, ssl_source)
        build = temporary / 'probe-build'
        runner.run('configure-native-probe', ['cmake', '-S', project, '-B', build, '-G', 'Visual Studio 18 2026', '-A', 'x64'], timeout=180)
        runner.run('build-native-probe', ['cmake', '--build', build, '--config', 'Release', '--parallel', '2'], timeout=180)
        probe = build / 'Release/coh-auth-only.exe'
        proof['native_probe'] = probe_identity(probe)
        proof['native_probe_inputs_sha256'] = {str(path.relative_to(root)): prior.sha(path) for path in inputs}
        shutil.copy2(probe, output / 'coh-auth-only.exe')
        shutil.copy2(build / 'CMakeCache.txt', output / 'native-probe-CMakeCache.txt')
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
        proof['original_authserver_launch_attempted'] = True
        child = subprocess.Popen([str(auth)], cwd=runtime, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proof['original_authserver_started'] = True
        proof['authserver_process_id'] = child.pid
        job.assign(child)
        deadline = time.monotonic() + 90
        while True:
            private_logs_bounded(runtime / 'logs')
            if child.poll() is not None:
                raise ValueError('original_authserver_exited_before_readiness')
            listening = inspect_listeners(child.pid)
            if listening == set(ports):
                break
            if listening - set(ports):
                raise ValueError('unexpected_authserver_listener')
            if time.monotonic() >= deadline:
                raise ValueError('original_authserver_listener_deadline')
            time.sleep(.25)
        proof['owned_listener_ports'] = ports
        for case in CASES:
            private_logs_bounded(runtime / 'logs')
            if child.poll() is not None or inspect_listeners(child.pid) != set(ports):
                raise ValueError('original_authserver_lost_listener_ownership')
            name = 'probe-' + case
            runner.run(name, [probe, str(ports[1]), case], cwd=runtime, timeout=25, allowed=(0, 1, 2, 3))
            result = json.loads((output / (name + '.log')).read_text())
            proof['probe_results'][case] = admit_probe_result(result, case)
            if case == 'valid':
                if child.poll() is not None or inspect_listeners(child.pid) != set(ports):
                    raise ValueError('original_authserver_failed_during_positive_login')
                # Preserve an actual positive exchange even if a later negative
                # control exposes a separate server failure. Overall passed
                # remains false until all controls and cleanup finish.
                proof['encrypted_account_login_verified'] = True
        if child.poll() is not None or inspect_listeners(child.pid) != set(ports):
            raise ValueError('original_authserver_failed_after_probes')
        proof['passed'] = True
    except Exception as error:
        # Only our symbolic ValueError codes are exportable. Never serialize a
        # subprocess exception, command output, credential row or driver message.
        proof['failure'] = str(error) if isinstance(error, ValueError) and re.fullmatch('[a-z0-9_]+', str(error)) else type(error).__name__
    finally:
        if child is not None:
            try:
                cleanup_ok = job.stop(child) and not inspect_listeners(child.pid)
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
        (output / 'receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'passed': proof['passed'], 'failure': proof.get('failure'),
                      'encrypted_account_login_verified': proof['encrypted_account_login_verified'],
                      'authenticated_db_map_handoff_verified': False}))
    return 0 if proof['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
