#!/usr/bin/env python3
"""Build original AuthServer and qualify disposable LocalDB bindings on hosted Windows.

This stage never starts AuthServer, DbServer or MapServer. It never authenticates
an account. A later explicitly versioned deployment is required for that test.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import struct
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

import checksum_candidate
import generate_odbc
from source_audit import pinned_sources

HERE = Path(__file__).resolve().parent
ORIGINAL_TREE = 'f634e21e230009fa8edc91d15429cd4da69eee8c'
LOG_LIMIT = 64 * 1024 * 1024


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def capture(command, cwd=None):
    result = subprocess.run(list(map(str, command)), cwd=cwd, capture_output=True, timeout=30)
    if result.returncode or len(result.stdout) > 1024 * 1024:
        raise ValueError('bounded_inspection_command_failed')
    return result.stdout.decode('utf-8-sig').strip()


def require_hosted(root, output, expected_commit, environ=None, system=None):
    env = os.environ if environ is None else environ
    if (os.name if system is None else system) != 'nt' or env.get('RUNNER_ENVIRONMENT') != 'github-hosted' or env.get('GITHUB_ACTIONS') != 'true' or env.get('RUNNER_OS') != 'Windows':
        raise ValueError('fresh_github_hosted_windows_required')
    if not re.fullmatch(r'[0-9a-f]{40}', expected_commit):
        raise ValueError('exact_repository_commit_required')
    temporary = Path(env.get('RUNNER_TEMP', '')).resolve()
    if not env.get('RUNNER_TEMP') or output == temporary or not output.is_relative_to(temporary) or output.exists():
        raise ValueError('new_output_directory_under_runner_temp_required')
    head = capture(['git', '-C', root, 'rev-parse', 'HEAD'])
    if head != expected_commit or capture(['git', '-C', root, 'rev-parse', 'HEAD:upstream/ouroboros']) != ORIGINAL_TREE:
        raise ValueError('source_identity_mismatch')
    if capture(['git', '-C', root, 'status', '--porcelain', '--untracked-files=no', '--', 'upstream/ouroboros', 'native-android/engine/auth-interop']):
        raise ValueError('tracked_source_inputs_modified')
    pinned_sources(root)
    return {'repository_commit': head, 'repository_tree': capture(['git', '-C', root, 'rev-parse', 'HEAD^{tree}']),
            'original_source_tree': ORIGINAL_TREE, 'github_run_id': env.get('GITHUB_RUN_ID'),
            'image_os': env.get('ImageOS'), 'image_version': env.get('ImageVersion')}


def pe_identity(path, subsystem):
    if path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('pe_size_limit')
    with path.open('rb') as stream:
        dos = stream.read(64)
        if len(dos) != 64 or dos[:2] != b'MZ':
            raise ValueError('pe_dos_header')
        offset = struct.unpack_from('<I', dos, 60)[0]
        if offset < 64 or offset > 1024 * 1024:
            raise ValueError('pe_header_offset')
        stream.seek(offset)
        header = stream.read(96)
    actual_subsystem = struct.unpack_from('<H', header, 92)[0] if len(header) == 96 else None
    if (len(header) != 96 or header[:4] != b'PE\0\0' or struct.unpack_from('<H', header, 4)[0] != 0x14c
            or struct.unpack_from('<H', header, 24)[0] != 0x10b
            or actual_subsystem not in ((2, 3) if subsystem is None else (subsystem,))):
        raise ValueError('win32_pe_identity_mismatch')
    return {'sha256': sha(path), 'bytes': path.stat().st_size, 'machine': 'I386', 'format': 'PE32',
            'subsystem': actual_subsystem, 'header_identity_only': True, 'executed': False}


def admit_original_reuse(directory, current_original_tree):
    """Admit only the pinned successful original target from a failed stage.

    Full repository HEAD differs when only the harness changes. The imported
    original subtree, exact prior receipt, build inputs/logs and binary must not.
    The coordinator independently verifies the outer archive identity.
    """
    pins = json.loads((HERE / 'original-build-reuse-pins.json').read_text())
    if current_original_tree != ORIGINAL_TREE or pins['original_source_tree'] != current_original_tree:
        raise ValueError('reused_original_source_tree_mismatch')
    for name, expected in pins['files'].items():
        file = directory / name
        if (file.is_symlink() or not file.is_file() or file.stat().st_size != expected['bytes']
                or expected['bytes'] > LOG_LIMIT or sha(file) != expected['sha256']):
            raise ValueError('reused_original_file_identity_mismatch')
    receipt = json.loads((directory / 'receipt.json').read_text())
    if (receipt.get('schema') != 'coh-hosted-auth-stage-v1'
            or receipt.get('repository_commit') != pins['repository_commit']
            or receipt.get('original_source_tree') != current_original_tree
            or receipt.get('source_inputs_unchanged') is not True
            or receipt.get('passed') is not False
            or receipt.get('failure') != 'stage_command_failed_build-controls'
            or any(receipt.get(key) is not False for key in ('original_authserver_started', 'patched_dbserver_built',
                    'real_account_login_verified', 'authenticated_db_map_handoff_verified', 'native_live_world',
                    'physical_thor_accepted', 'owned_localdb_created', 'owned_localdb_creation_attempted'))):
        raise ValueError('reused_original_receipt_scope_mismatch')
    for name in ('configure-original-authserver', 'build-original-authserver'):
        records = [row for row in receipt.get('commands', []) if row.get('name') == name]
        if (len(records) != 1 or type(records[0].get('returncode')) is not int or records[0]['returncode'] != 0
                or records[0].get('log_sha256') != pins['files'][name + '.log']['sha256']
                or records[0].get('log_truncated') is not False):
            raise ValueError('reused_original_target_not_qualified')
    binary = pe_identity(directory / 'AuthServer-original.exe', 2)
    if receipt.get('original_authserver') != binary:
        raise ValueError('reused_original_binary_receipt_mismatch')
    return {'run_id': pins['run_id'], 'artifact_id': pins['artifact_id'], 'archive_sha256': pins['archive_sha256'],
            'original_repository_commit': pins['repository_commit'], 'original_source_tree': current_original_tree,
            'files': pins['files'], 'original_authserver': binary,
            'scope': 'Reuse of exact original target build only; prior overall stage failed before SQL and never ran AuthServer.',
            'rebuilt': False, 'authserver_executed': False, 'sql_qualification_inherited': False,
            'real_account_login_verified': False}


def admit_control_reuse(directory, generated, current_original_tree):
    """Bind exact compiled controls, then execute them afresh in this stage."""
    pins = json.loads((HERE / 'control-build-reuse-pins.json').read_text())
    if current_original_tree != ORIGINAL_TREE or pins['original_source_tree'] != current_original_tree:
        raise ValueError('reused_control_source_tree_mismatch')
    for name, expected in pins['files'].items():
        file = directory / name
        if (file.is_symlink() or not file.is_file() or file.stat().st_size != expected['bytes']
                or expected['bytes'] > LOG_LIMIT or sha(file) != expected['sha256']):
            raise ValueError('reused_control_file_identity_mismatch')
    # Generated source is normalized only for the platform's LF/CRLF writing.
    # Exact retained bytes remain independently pinned above.
    for name in pins['generated_sources']:
        if (generated / name).read_text(encoding='utf-8') != (directory / name).read_text(encoding='utf-8'):
            raise ValueError('reused_control_generated_source_mismatch')
    receipt = json.loads((directory / 'receipt.json').read_text())
    if (receipt.get('schema') != 'coh-hosted-auth-stage-v1'
            or receipt.get('repository_commit') != pins['repository_commit']
            or receipt.get('original_source_tree') != current_original_tree
            or receipt.get('source_inputs_unchanged') is not True or receipt.get('passed') is not False
            or receipt.get('failure') != 'stage_command_failed_schema-metadata'
            or receipt.get('owned_localdb_cleanup_complete') is not True
            or any(receipt.get(key) is not False for key in ('original_authserver_started', 'patched_dbserver_built',
                    'real_account_login_verified', 'authenticated_db_map_handoff_verified', 'native_live_world',
                    'physical_thor_accepted'))):
        raise ValueError('reused_control_receipt_scope_mismatch')
    for name in ('configure-controls', 'build-controls'):
        records = [row for row in receipt.get('commands', []) if row.get('name') == name]
        if (len(records) != 1 or type(records[0].get('returncode')) is not int or records[0]['returncode'] != 0
                or records[0].get('log_sha256') != pins['files'][name + '.log']['sha256']
                or records[0].get('log_truncated') is not False):
            raise ValueError('reused_control_target_not_qualified')
    binaries = {}
    for name in ('original-policy', 'candidate-policy', 'original-odbc'):
        binaries[name] = pe_identity(directory / (name + '.exe'), 3)
        expected = dict(receipt.get('control_executions', {}).get(name, {}))
        if name != 'original-odbc':
            result = expected.pop('result', {})
            if (expected.get('executed') is not True or result.get('passed') is not True
                    or result.get('checks') != 135 or result.get('network_execution') is not False
                    or result.get('real_account_login_verified') is not False):
                raise ValueError('reused_control_execution_scope_mismatch')
            expected['executed'] = False
        if expected != binaries[name]:
            raise ValueError('reused_control_binary_receipt_mismatch')
    return {'run_id': pins['run_id'], 'artifact_id': pins['artifact_id'], 'archive_sha256': pins['archive_sha256'],
            'original_repository_commit': pins['repository_commit'], 'original_source_tree': current_original_tree,
            'files': pins['files'], 'binaries': binaries, 'rebuilt': False,
            'scope': 'Exact compiled controls; execute anew. Prior stage did not execute ODBC.',
            'odbc_qualification_inherited': False, 'real_account_login_verified': False}


def materialize_control(binary, output, name):
    """Use one verified, conventional output path for fresh and reused controls."""
    if name not in ('original-policy', 'candidate-policy', 'original-odbc'):
        raise ValueError('unknown_control_name')
    identity = pe_identity(binary, 3)
    destination = output / (name + '.exe')
    shutil.copy2(binary, destination)
    if pe_identity(destination, 3) != identity:
        raise ValueError('control_changed_during_copy')
    return destination


class Commands:
    def __init__(self, output):
        self.output, self.records = output, []

    def run(self, name, command, cwd=None, timeout=120, allowed=(0,)):
        # Inputs contain only public build/config data. Never accept credentials.
        path = self.output / (name + '.log')
        with path.open('xb') as log:
            process = subprocess.Popen(list(map(str, command)), cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
            start, failed = time.monotonic(), None
            termination = {'attempted': False, 'observed': False}
            while process.poll() is None:
                if time.monotonic() - start > timeout or path.stat().st_size > LOG_LIMIT:
                    failed = 'command_timeout_or_log_limit'
                    termination['attempted'] = True
                    try:
                        result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                        termination['taskkill_returncode'] = result.returncode
                    except Exception as error:
                        termination['taskkill_error'] = type(error).__name__
                    try:
                        process.wait(timeout=15)
                    except Exception:
                        # Fall back to the directly owned child. This does not
                        # prove descendants exited if taskkill failed.
                        try:
                            process.kill()
                            process.wait(timeout=5)
                        except Exception as error:
                            termination['direct_child_stop_error'] = type(error).__name__
                    termination['observed'] = process.poll() is not None
                    break
                time.sleep(.2)
        original_size = path.stat().st_size
        if original_size > LOG_LIMIT:
            failed = failed or 'completed_command_log_limit'
            # A short-lived child can exceed the cap before the next poll. Keep
            # a declared bounded prefix, never hash/upload the unbounded tail.
            if process.poll() is not None:
                with path.open('r+b') as log:
                    log.truncate(LOG_LIMIT)
        stored_size = path.stat().st_size
        self.records.append({'name': name, 'returncode': process.returncode, 'elapsed_seconds': round(time.monotonic() - start, 3),
                             'log_sha256': sha(path) if stored_size <= LOG_LIMIT else None, 'log_bytes': stored_size,
                             'log_original_bytes': original_size, 'log_truncated': stored_size != original_size,
                             'termination': termination})
        if failed or process.returncode not in allowed:
            raise ValueError(failed or 'stage_command_failed_' + name)
        return process.returncode


def cleanup_owned_instance(runner, sqlcmd, localdb, instance):
    if not re.fullmatch(r'cohauth-ci-[0-9a-f]{24}', instance):
        raise ValueError('owned_instance_name_invalid')
    complete = True
    operations = [
        ('localdb-drop-owned-schema', [sqlcmd, '-S', '(localdb)\\' + instance, '-E', '-C', '-b', '-l', '20', '-t', '30', '-Q', "IF DB_ID('cohauth') IS NOT NULL BEGIN ALTER DATABASE cohauth SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE cohauth; END"], 45),
        ('localdb-stop-owned-instance', [localdb, 'stop', instance, '-k'], 60),
        ('localdb-delete-owned-instance', [localdb, 'delete', instance], 60)]
    for name, command, timeout in operations:
        try:
            runner.run(name, command, timeout=timeout)
        except Exception:
            complete = False
    return complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-auth-stage', type=Path,
                        help='Extracted exact pinned run38943674226 artifact12064402579; never rebuild original target')
    parser.add_argument('--reuse-controls-stage', type=Path,
                        help='Extracted exact pinned run38946462964 artifact12066431903; never rebuild unchanged controls')
    args = parser.parse_args()
    root, output = args.source_root.resolve(), args.output.resolve()
    identity = require_hosted(root, output, args.expected_commit)
    reused = admit_original_reuse(args.reuse_auth_stage.resolve(), identity['original_source_tree']) if args.reuse_auth_stage else None
    output.mkdir(parents=True)
    runner = Commands(output)
    proof = {'schema': 'coh-hosted-auth-stage-v1', **identity, 'passed': False,
             'original_authserver_started': False, 'patched_dbserver_built': False,
             'real_account_login_verified': False, 'authenticated_db_map_handoff_verified': False,
             'native_live_world': False, 'physical_thor_accepted': False, 'commands': runner.records,
             'owned_localdb_created': False}
    instance = 'cohauth-ci-' + secrets.token_hex(12)
    created, cleanup_ok, localdb, sqlcmd = False, False, None, None
    try:
        # These installed components must actually exist; image documentation is
        # feasibility evidence, not proof of this runner's environment.
        candidates = sorted(Path(os.environ['ProgramFiles']).glob('Microsoft SQL Server/*/Tools/Binn/SqlLocalDB.exe'), reverse=True)
        localdb = Path(shutil.which('SqlLocalDB.exe') or (str(candidates[0]) if candidates else ''))
        sqlcmd_candidates = sorted(Path(os.environ['ProgramFiles']).glob('Microsoft SQL Server/Client SDK/ODBC/*/Tools/Binn/SQLCMD.EXE'), reverse=True)
        sqlcmd_name = shutil.which('sqlcmd.exe') or (str(sqlcmd_candidates[0]) if sqlcmd_candidates else None)
        if not localdb.is_file() or not sqlcmd_name:
            raise ValueError('localdb_or_sqlcmd_unavailable')
        sqlcmd = Path(sqlcmd_name)
        drivers = json.loads(capture(['pwsh', '-NoProfile', '-NonInteractive', '-Command', "ConvertTo-Json -InputObject @((Get-OdbcDriver -Platform '32-bit').Name) -Compress"]))
        if not isinstance(drivers, list) or any(not isinstance(name, str) for name in drivers):
            raise ValueError('driver_inventory_shape')
        driver = next((name for name in ('ODBC Driver 17 for SQL Server', 'ODBC Driver 18 for SQL Server') if name in drivers), None)
        if not driver:
            raise ValueError('x86_sql_server_odbc_driver_unavailable')
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\ODBC\\ODBCINST.INI\\' + driver, 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
            driver_path = Path(os.path.expandvars(winreg.QueryValueEx(key, 'Driver')[0]))
        driver_identity = pe_identity(driver_path, None)
        proof['tools'] = {'localdb_sha256': sha(localdb), 'sqlcmd_sha256': sha(sqlcmd), 'x86_odbc_driver': driver,
                          'x86_odbc_driver_binary': driver_identity,
                          'cmake_version': capture(['cmake', '--version']).splitlines()[0]}
        with tempfile.TemporaryDirectory(prefix='coh-auth-stage-', dir=os.environ['RUNNER_TEMP']) as temporary:
            temporary = Path(temporary)
            archive = temporary / 'source.tar'
            runner.run('archive-original-source', ['git', '-C', root, 'archive', '--format=tar', '--output=' + str(archive), args.expected_commit, 'upstream/ouroboros'])
            with tarfile.open(archive) as tar:
                tar.extractall(temporary / 'source', filter='data')
            source = temporary / 'source/upstream/ouroboros'
            if reused:
                for name, expected in reused['files'].items():
                    destination = output / ('reused-original-receipt.json' if name == 'receipt.json' else name)
                    shutil.copy2(args.reuse_auth_stage / name, destination)
                    if destination.stat().st_size != expected['bytes'] or sha(destination) != expected['sha256']:
                        raise ValueError('reused_original_changed_during_copy')
                proof['original_build_reuse'] = reused
                proof['original_authserver'] = pe_identity(output / 'AuthServer-original.exe', 2)
            else:
                build = temporary / 'build'
                patch_tool = Path(os.environ['ProgramFiles']) / 'Git/usr/bin/patch.exe'
                if not patch_tool.is_file():
                    raise ValueError('qualified_patch_tool_unavailable')
                runner.run('configure-original-authserver', ['cmake', '-S', source, '-B', build, '-G', 'Visual Studio 18 2026', '-A', 'Win32',
                           '-DCOX_BUILD_MAPSERVER=OFF', '-DCOX_BUILD_BEACONSERVER=OFF', '-DPATCH_EXECUTABLE=' + str(patch_tool)], timeout=900)
                runner.run('build-original-authserver', ['cmake', '--build', build, '--config', 'OptDebug', '--parallel', '2', '--target', 'AuthServer'], timeout=1500)
                authserver = build / 'bin/OptDebug/AuthServer.exe'
                proof['original_authserver'] = pe_identity(authserver, 2)
                shutil.copy2(authserver, output / 'AuthServer-original.exe')
                shutil.copy2(build / 'CMakeCache.txt', output / 'original-CMakeCache.txt')
            harness = temporary / 'harness'
            harness.mkdir()
            proof['checksum_candidate'] = checksum_candidate.prepare(root, harness)
            proof['original_odbc'] = generate_odbc.prepare(root, harness)
            for file in harness.iterdir():
                shutil.copy2(file, output / file.name)
            auth_include = (source / 'AuthServer/src').as_posix()
            (harness / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.24)\nproject(AuthStageControls C CXX)\n'
                'set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)\nset(CMAKE_C_STANDARD 11)\nset(CMAKE_CXX_STANDARD 17)\n'
                'add_executable(original-policy original-policy.c)\nadd_executable(candidate-policy candidate-policy.c)\n'
                'add_executable(original-odbc original-odbc.cpp)\ntarget_link_libraries(original-odbc PRIVATE odbc32)\n'
                f'target_include_directories(original-odbc PRIVATE "{auth_include}")\n')
            hb = temporary / 'harness-build'
            if args.reuse_controls_stage:
                reused_controls = admit_control_reuse(args.reuse_controls_stage.resolve(), harness, identity['original_source_tree'])
                for name, expected in reused_controls['files'].items():
                    destination = output / ('reused-controls-receipt.json' if name == 'receipt.json' else 'reused-controls-' + name)
                    shutil.copy2(args.reuse_controls_stage / name, destination)
                    if destination.stat().st_size != expected['bytes'] or sha(destination) != expected['sha256']:
                        raise ValueError('reused_control_changed_during_copy')
                proof['control_build_reuse'] = reused_controls
            else:
                runner.run('configure-controls', ['cmake', '-S', harness, '-B', hb, '-G', 'Visual Studio 18 2026', '-A', 'Win32'], timeout=180)
                runner.run('build-controls', ['cmake', '--build', hb, '--config', 'Release', '--parallel', '2'], timeout=180)
            proof['control_executions'] = {}
            for name in ('original-policy', 'candidate-policy', 'original-odbc'):
                binary = (output / ('reused-controls-' + name + '.exe') if args.reuse_controls_stage
                          else hb / 'Release' / (name + '.exe'))
                binary = materialize_control(binary, output, name)
                proof['control_executions'][name] = pe_identity(binary, 3)
                if name != 'original-odbc':
                    runner.run(name, [binary], timeout=30)
                    record = json.loads((output / (name + '.log')).read_text())
                    if record.get('passed') is not True or record.get('checks') != 135 or record.get('real_account_login_verified') is not False:
                        raise ValueError('source_policy_controls_failed')
                    proof['control_executions'][name].update(executed=True, result=record)
            if instance.casefold() in {name.strip().casefold() for name in capture([localdb, 'info']).splitlines()}:
                raise ValueError('generated_instance_already_exists')
            # Ownership is established by absence plus our fresh 96-bit name.
            # Clean up even if creation times out after creating the instance.
            created = True
            runner.run('localdb-create', [localdb, 'create', instance], timeout=60)
            proof['owned_localdb_created'] = True
            runner.run('localdb-start', [localdb, 'start', instance], timeout=60)
            server = '(localdb)\\' + instance
            sql = [sqlcmd, '-S', server, '-E', '-C', '-b', '-l', '20', '-t', '120']
            runner.run('localdb-version', [*sql, '-Q', "SET NOCOUNT ON;SELECT CONVERT(varchar(100),SERVERPROPERTY('ProductVersion')) AS product_version,CONVERT(varchar(100),SERVERPROPERTY('Edition')) AS edition;"], timeout=150)
            runner.run('localdb-memory-bound', [*sql, '-Q', "EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'max server memory (MB)',256;RECONFIGURE;"], timeout=150)
            schema = source / 'Assets/DBSchemas/cohauth.sql'
            proof['schema_sha256'] = sha(schema)
            runner.run('original-schema', [*sql, '-i', schema], timeout=150)
            runner.run('binding-fixture', [*sql, '-i', harness / 'odbc-fixture.sql'], timeout=150)
            # Raw metadata stays diagnostic; known conversion differences remain
            # refused by admit_schema.py until independent results are reviewed.
            runner.run('schema-metadata', [*sql, '-d', 'cohauth', '-i', HERE / 'inspect_schema.sql', '-y', '0', '-w', '65535'], timeout=150)
            runner.run('original-odbc', [output / 'original-odbc.exe', instance, driver], timeout=120, allowed=(0, 1, 3))
            record = json.loads((output / 'original-odbc.log').read_text())
            proof['control_executions']['original-odbc'].update(executed=True, result=record)
            if record.get('passed') is not True:
                raise ValueError('original_odbc_runtime_controls_failed')
            proof['passed'] = True
    except Exception as error:
        # Do not export exception command/output or account-bearing ODBC errors.
        proof['failure'] = str(error) if isinstance(error, ValueError) else type(error).__name__
    finally:
        if created:
            cleanup_ok = cleanup_owned_instance(runner, sqlcmd, localdb, instance)
            if not cleanup_ok:
                proof['cleanup_failure'] = 'owned_localdb_cleanup_incomplete'
        else:
            cleanup_ok = True
        proof['owned_localdb_creation_attempted'] = created
        proof['owned_localdb_cleanup_complete'] = cleanup_ok
        proof['passed'] = proof['passed'] and cleanup_ok
        try:
            proof['source_inputs_unchanged'] = not capture(['git', '-C', root, 'status', '--porcelain', '--untracked-files=no', '--', 'upstream/ouroboros', 'native-android/engine/auth-interop'])
        except Exception:
            proof['source_inputs_unchanged'] = False
        proof['passed'] = proof['passed'] and proof['source_inputs_unchanged']
        (output / 'receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'passed': proof['passed'], 'failure': proof.get('failure'), 'real_account_login_verified': False}))
    return 0 if proof['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
