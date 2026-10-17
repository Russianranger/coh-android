#!/usr/bin/env python3
"""Execute original shard/UserData SQL prerequisites in fresh hosted LocalDB.

Builds one diagnostic x86 harness, never an AuthServer, DbServer or accepted APK.
Reuses the sealed successful Auth-only receipt without replaying account login.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile

import auth_readiness
import hosted_auth_stage as prior
import hosted_candidate_login as service
import shard_userdata_fixture as fixture
from sql_readiness_diagnostic import RedactedCommands
from verify_auth_acceptance import authenticated_handoff_prerequisite

HERE = Path(__file__).resolve().parent


def safe_failure(error):
    text = str(error)
    return text if isinstance(error, ValueError) and re.fullmatch('[a-z0-9_]+', text) else type(error).__name__


def run(args):
    root, output = args.source_root.resolve(), args.output.resolve()
    identity = prior.require_hosted(root, output, args.expected_commit)
    prerequisite = authenticated_handoff_prerequisite(root, args.auth_success_archive.resolve())
    helper_names = ('hosted_shard_userdata.py', 'shard_userdata_fixture.py', 'shard_userdata_fixture.cpp')
    helpers = {name: prior.sha(HERE / name) for name in helper_names}
    output.mkdir(parents=True)
    runner = prior.Commands(output)
    proof = dict(identity, schema='coh-hosted-original-shard-userdata-v1', passed=False,
                 prior_auth_qualification=asdict(prerequisite), commands=runner.records,
                 helpers_sha256=helpers, sql_executed=False, diagnostic_executed=False,
                 original_authserver_started=False, dbserver_started=False,
                 auth_only_login_repeated=False, no_existing_profile_modified=True,
                 real_selected_shard_play_verified=False, authenticated_db_map_handoff_verified=False,
                 native_live_world=False, private_console_exported=False)
    temporary = Path(tempfile.mkdtemp(prefix='coh-shard-userdata-', dir=os.environ['RUNNER_TEMP']))
    sql_runner = RedactedCommands(runner.records, temporary)
    instance = 'cohauth-ci-' + secrets.token_hex(12)
    created, localdb, sqlcmd = False, None, None
    try:
        localdb, sqlcmd, proof['x86_odbc_driver'] = service.tools()
        project = temporary / 'project'
        project.mkdir()
        proof['generated_source'] = fixture.prepare(root, project)
        # Retain public source controls, never SQL/ODBC diagnostic console text.
        for name in ('original-shard-userdata.cpp', 'shard-userdata.sql'):
            shutil.copy2(project / name, output / name)
        (project / 'CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.24)\nproject(CohShardUserdata CXX)\n'
            'set(CMAKE_CXX_STANDARD 17)\nset(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)\n'
            'add_executable(original-shard-userdata original-shard-userdata.cpp)\n'
            'target_compile_definitions(original-shard-userdata PRIVATE _CRT_SECURE_NO_WARNINGS _WINSOCK_DEPRECATED_NO_WARNINGS)\n'
            'target_link_libraries(original-shard-userdata PRIVATE odbc32 ws2_32)\n', encoding='ascii')
        build = temporary / 'build'
        runner.run('configure-shard-userdata', ['cmake', '-S', project, '-B', build,
                    '-G', 'Visual Studio 18 2026', '-A', 'Win32'], timeout=180)
        runner.run('build-shard-userdata', ['cmake', '--build', build, '--config', 'Release',
                    '--target', 'original-shard-userdata', '--parallel', '2'], timeout=180)
        executable = output / 'original-shard-userdata.exe'
        shutil.copy2(build / 'Release/original-shard-userdata.exe', executable)
        proof['diagnostic_binary'] = prior.pe_identity(executable, 3)
        for name, path in (('CMakeLists.txt', project / 'CMakeLists.txt'), ('CMakeCache.txt', build / 'CMakeCache.txt')):
            shutil.copy2(path, output / name)
        if instance.casefold() in {v.strip().casefold() for v in prior.capture([localdb, 'info']).splitlines()}:
            raise ValueError('generated_instance_already_exists')
        created = True
        sql_runner.run('localdb-create', [localdb, 'create', instance], timeout=60)
        sql_runner.run('localdb-start', [localdb, 'start', instance], timeout=60)
        sql = [sqlcmd, '-S', '(localdb)\\' + instance, '-E', '-C', '-b', '-l', '20', '-t', '120']
        proof['localdb_version'] = sql_runner.numeric('localdb-version', [*sql, '-h', '-1', '-W', '-Q',
             "SET NOCOUNT ON;SELECT CONVERT(varchar(100),SERVERPROPERTY('ProductVersion'));"], kind='version')
        sql_runner.run('localdb-memory-bound', [*sql, '-Q',
             "EXEC sp_configure 'show advanced options',1;RECONFIGURE;EXEC sp_configure 'max server memory (MB)',1024;RECONFIGURE;"], timeout=150)
        # Load exact original schema bytes from the pinned tree, not an untracked local file.
        schema = subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), 'show',
             'HEAD:upstream/ouroboros/Assets/DBSchemas/cohauth.sql'], timeout=30)
        if hashlib.sha256(schema).hexdigest() != proof['generated_source']['source_sha256']['upstream/ouroboros/Assets/DBSchemas/cohauth.sql']:
            raise ValueError('userdata_schema_changed')
        schema_path = temporary / 'cohauth.sql'
        schema_path.write_bytes(schema)
        sql_runner.run('load-original-schema', [*sql, '-i', schema_path], timeout=150)
        sql_runner.run('load-shard-userdata-fixture', [*sql, '-i', project / 'shard-userdata.sql'], timeout=150)
        proof['sql_executed'] = True
        pid = sql_runner.numeric('localdb-pid', [*sql, '-h', '-1', '-W', '-Q',
             "SET NOCOUNT ON;SELECT CONVERT(int,SERVERPROPERTY('ProcessID'));"], kind='pid')
        proof['x86_readiness'] = auth_readiness.observe(instance, pid)
        if proof['x86_readiness']['healthy'] is not True:
            raise ValueError('userdata_fresh_x86_sql_not_ready')
        # Only this harness emits a strictly redacted boolean receipt. Driver and
        # schema error consoles are always suppressed by RedactedCommands.
        runner.run('original-shard-userdata', [executable, instance, 'ODBC Driver 17 for SQL Server'],
                   timeout=90, allowed=(0, 1, 2, 3, 4))
        proof['diagnostic_executed'] = True
        proof['runtime_result'] = fixture.admit_result(json.loads((output / 'original-shard-userdata.log').read_text()))
        proof['passed'] = True
    except Exception as error:
        proof['failure'] = safe_failure(error)
    finally:
        try:
            proof['owned_localdb_cleanup_complete'] = not created or prior.cleanup_owned_instance(sql_runner, sqlcmd, localdb, instance)
        except Exception:
            proof['owned_localdb_cleanup_complete'] = False
        try:
            shutil.rmtree(temporary)
            proof['private_files_removed'] = not temporary.exists()
        except Exception:
            proof['private_files_removed'] = False
        try:
            proof['source_inputs_unchanged'] = (
                prior.capture(['git', '-C', root, 'rev-parse', 'HEAD']) == args.expected_commit
                and not prior.capture(['git', '-C', root, 'status', '--porcelain', '--untracked-files=no', '--', 'upstream/ouroboros', 'native-android'])
                and helpers == {name: prior.sha(HERE / name) for name in helper_names}
                and fixture.inputs(root)[1] == proof.get('generated_source', {}).get('source_sha256'))
        except Exception:
            proof['source_inputs_unchanged'] = False
        proof['passed'] = proof['passed'] and all(proof.get(key) is True for key in (
            'owned_localdb_cleanup_complete', 'private_files_removed', 'source_inputs_unchanged'))
        (output / 'receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'output', 'auth-success-archive'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    value = run(parser.parse_args())
    print(json.dumps({key: value.get(key) for key in ('passed', 'failure', 'sql_executed',
                     'diagnostic_executed', 'real_selected_shard_play_verified', 'authenticated_db_map_handoff_verified')}))
    raise SystemExit(0 if value['passed'] else 1)
