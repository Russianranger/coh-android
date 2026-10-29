#!/usr/bin/env python3
"""Bind optional server artifacts to the serialized build/runtime/APK pipeline.

The retained guest executes only the retained_progress server. The Thor server
has build/source checks until a separate device or modern-runtime test runs.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import shutil

import server_package as native

REPOSITORY = 'Russianranger/coh-android'
QUALIFICATION = 'server-metrics-qualification.json'
SCOPE = 'retained_server_creation_reopen_thor_server_build_only'
PACKAGES = {
    'retained_progress': 'server-metrics-retained-progress.zip',
    'thor_certified_startup': 'server-metrics-thor-certified-startup.zip',
}
require = native.require


def positive(value):
    return type(value) is int and value > 0


def check_build_run(value, *, repository_commit, server_run_id, client_run_id, data_run_id):
    require(all(positive(item) for item in (server_run_id, client_run_id, data_run_id))
            and server_run_id == client_run_id == data_run_id,
            'Client, data and server must come from the same exact build run')
    require(re.fullmatch('[a-f0-9]{40}', repository_commit)
            and type(value.get('id')) is int and value['id'] == server_run_id
            and value.get('path') == '.github/workflows/armport-build.yml'
            and value.get('event') == 'workflow_dispatch'
            and value.get('status') == 'completed' and value.get('conclusion') == 'success'
            and value.get('head_sha') == repository_commit
            and value.get('repository', {}).get('full_name') == REPOSITORY
            and value.get('head_repository', {}).get('full_name') == REPOSITORY,
            'Server build must be a successful explicit run at this exact repository head')


def native_inputs(directory, repository_commit, run_id, upstream_root=native.ROOT):
    """Read both ZIPs through the complete source/donor/actual-PE validator."""
    require(positive(run_id), 'Exact server build run required')
    result = {}
    for variant, filename in PACKAGES.items():
        path = Path(directory) / filename
        build, _, members = native.read_package(path, variant=variant,
            repository_commit=repository_commit, run_id=run_id, upstream_root=upstream_root)
        result[variant] = {'filename': filename, **native.pin(native.read_file(path,
            native.MAX_FILE + 3 * native.MAX_JSON)),
            'mapserver': {key: build['files']['MapServer.exe'][key] for key in ('bytes', 'sha256')},
            'build_manifest_sha256': native.digest(members[native.BUILD]),
            'source_receipt_sha256': native.digest(native.canonical(build['build_input'])),
            'package_receipt_sha256': native.digest(native.canonical(build)),
            'previous_mapserver_sha256': build['predecessor']['mapserver']['sha256']}
    return result


def guest_admission(report, runtime_manifest):
    """Check the actual guest PE admission before any legacy report projection."""
    expected = runtime_manifest.get('armport_server_metrics')
    if expected is None:
        return None
    build = runtime_manifest['armport_server_metrics_build']
    report_key = {'actual_character_creation_guest': 'character_creation',
                  'actual_character_reopen_guest': 'character_reopen'}.get(report.get('scope'))
    session = report.get('session_id')
    character = report.get(report_key, {})
    require(isinstance(session, str) and re.fullmatch('[a-f0-9]{32}', session)
            and report_key is not None and isinstance(character, dict)
            and character.get('session_id') == session,
            'Guest metrics admission requires the actual character session identity')
    producer = character.get('mapserver_producer', {})
    proof = producer.get('armport_server_metrics', {})
    require(expected.get('variant') == 'retained_progress'
            and native.canonical({key: proof.get(key) for key in expected}) == native.canonical(expected)
            and producer.get('mapserver_sha256') == expected['mapserver']['sha256']
            and producer.get('repository_commit') == expected['repository_commit']
            and type(producer.get('run_id')) is int and producer['run_id'] == expected['run_id']
            and producer.get('manifest_sha256') == expected['build_manifest']['sha256']
            and proof.get('policy') == 'authenticated_metrics_only_overlay'
            and proof.get('actual_mapserver_sha256') == expected['mapserver']['sha256']
            and proof.get('previous_mapserver_sha256') == build['predecessor']['mapserver']['sha256']
            and proof.get('package_receipt_sha256') == native.digest(native.canonical(build))
            and proof.get('parser_or_definition_sources_changed') is False
            and proof.get('gameplay_decisions_changed') is False,
            'Guest metrics MapServer admission differs from the staged native build')
    return {'session_id': session, 'producer': copy.deepcopy(proof)}


def check_sessions(sessions, packages, repository_commit, run_id, *,
                   creation_session_id, reopen_session_id):
    require(isinstance(sessions, dict) and set(sessions) == {'creation', 'reopen'},
            'Both retained metrics guest sessions are required')
    identities = {'creation': creation_session_id, 'reopen': reopen_session_id}
    require(all(isinstance(value, str) and re.fullmatch('[a-f0-9]{32}', value)
                for value in identities.values()) and creation_session_id != reopen_session_id,
            'Distinct actual creation and reopen session identities are required')
    expected = packages['retained_progress']
    for phase, receipt in sessions.items():
        require(isinstance(receipt, dict) and set(receipt) == {'session_id', 'producer'}
                and receipt['session_id'] == identities[phase],
                'Retained metrics receipt belongs to another guest session')
        proof = receipt['producer']
        require(isinstance(proof, dict) and type(proof.get('format')) is int and proof['format'] == 1
                and proof.get('variant') == 'retained_progress'
                and proof.get('repository_commit') == repository_commit
                and type(proof.get('run_id')) is int and proof['run_id'] == run_id
                and proof.get('server_package') == {key: expected[key] for key in ('bytes', 'sha256')}
                and proof.get('mapserver') == expected['mapserver']
                and proof.get('build_manifest', {}).get('sha256') == expected['build_manifest_sha256']
                and proof.get('source_receipt_sha256') == expected['source_receipt_sha256']
                and proof.get('package_receipt_sha256') == expected['package_receipt_sha256']
                and proof.get('actual_mapserver_sha256') == expected['mapserver']['sha256']
                and proof.get('previous_mapserver_sha256') == expected['previous_mapserver_sha256']
                and proof.get('policy') == 'authenticated_metrics_only_overlay'
                and all(proof.get(key) is False for key in ('runtime_execution_validated',
                    'physical_device_validated', 'parser_or_definition_sources_changed',
                    'gameplay_decisions_changed')),
                'Retained session evidence does not bind the exact metrics server')


def qualification(host, packages, *, repository_commit, run_id, runtime_run_id):
    require(positive(run_id) and positive(runtime_run_id) and runtime_run_id != run_id,
            'Separate successful runtime stage required')
    require(host.get('scope') == 'arm64_app_guest_creation_and_reopen'
            and host.get('repository_commit') == repository_commit
            and host.get('passed') is True and host.get('same_persistent_profile') is True
            and host.get('same_character_id') is True and host.get('error') is None
            and host.get('android_surface_validated') is False and host.get('m4_complete') is False
            and all(positive(host.get('armport_client', {}).get(key))
                    and host['armport_client'][key] == run_id
                    for key in ('client_run_id', 'data_run_id')),
            'Server qualification requires the successful same-build creation/reopen host report')
    require(host.get('guest_failures') == {phase: {'failures': [], 'failed_stages': [],
            'client_faults': []} for phase in ('creation', 'reopen')},
            'Server qualification requires complete guest evidence without failures or faults')
    sessions = host.get('server_metrics_native_execution')
    identities = {key: host.get(key) for key in ('creation_session_id', 'reopen_session_id')}
    check_sessions(sessions, packages, repository_commit, run_id, **identities)
    return {'format': 1, 'scope': SCOPE, 'repository_commit': repository_commit,
        'native_build_run_id': run_id, 'runtime_run_id': runtime_run_id,
        **identities,
        'packages': copy.deepcopy(packages), 'retained_sessions': copy.deepcopy(sessions),
        'runtime_passed': True, 'retained_runtime_executed': True,
        'thor_runtime_executed': False, 'physical_device_validated': False}


def validate_qualification(value, packages, *, repository_commit, runtime_run_id):
    require(isinstance(value, dict) and set(value) == {'format', 'scope', 'repository_commit',
            'native_build_run_id', 'runtime_run_id', 'packages', 'retained_sessions',
            'creation_session_id', 'reopen_session_id',
            'runtime_passed', 'retained_runtime_executed', 'thor_runtime_executed', 'physical_device_validated'}
            and type(value.get('format')) is int and value['format'] == 1 and value.get('scope') == SCOPE
            and value.get('repository_commit') == repository_commit
            and positive(value.get('native_build_run_id'))
            and positive(runtime_run_id) and type(value.get('runtime_run_id')) is int
            and value['runtime_run_id'] == runtime_run_id != value['native_build_run_id']
            and native.canonical(value.get('packages')) == native.canonical(packages)
            and value.get('runtime_passed') is True and value.get('retained_runtime_executed') is True
            and value.get('thor_runtime_executed') is False and value.get('physical_device_validated') is False,
            'Server qualification identity, artifact pins or execution scope differs')
    check_sessions(value['retained_sessions'], packages, repository_commit, value['native_build_run_id'],
        creation_session_id=value['creation_session_id'], reopen_session_id=value['reopen_session_id'])
    return value


def read_qualification(directory, repository_commit, runtime_run_id, upstream_root=native.ROOT):
    directory = Path(directory)
    value = native.parse_json(native.read_file(directory / QUALIFICATION, 256 * 1024))
    packages = native_inputs(directory, repository_commit, value.get('native_build_run_id'), upstream_root)
    return validate_qualification(value, packages, repository_commit=repository_commit,
                                  runtime_run_id=runtime_run_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check-run')
    publish = sub.add_parser('qualify')
    for item in (check, publish):
        item.add_argument('--build-run-json', type=Path, required=True)
        for name in ('server-run-id', 'client-run-id', 'data-run-id'):
            item.add_argument('--' + name, type=int, required=True)
    publish.add_argument('--host-report', type=Path, required=True)
    publish.add_argument('--source', type=Path, required=True)
    publish.add_argument('--output', type=Path, required=True)
    read = sub.add_parser('check')
    read.add_argument('--source', type=Path, required=True)
    for item in (publish, read):
        item.add_argument('--runtime-run-id', type=int, required=True)
        item.add_argument('--baseline-root', type=Path, required=True)
    for item in (check, publish, read):
        item.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    baseline = native.baseline_root(args.baseline_root) if args.command != 'check-run' else None
    if args.command == 'check':
        result = read_qualification(args.source, args.repository_commit, args.runtime_run_id, baseline)
    else:
        check_build_run(native.parse_json(native.read_file(args.build_run_json)),
            repository_commit=args.repository_commit, server_run_id=args.server_run_id,
            client_run_id=args.client_run_id, data_run_id=args.data_run_id)
        result = {'native_build_run_id': args.server_run_id}
        if args.command == 'qualify':
            packages = native_inputs(args.source, args.repository_commit, args.server_run_id, baseline)
            result = qualification(native.parse_json(native.read_file(args.host_report)), packages,
                repository_commit=args.repository_commit, run_id=args.server_run_id,
                runtime_run_id=args.runtime_run_id)
            require(not args.output.exists(), 'Fresh qualification directory required')
            args.output.mkdir(parents=True)
            try:
                for filename in PACKAGES.values():
                    shutil.copyfile(args.source / filename, args.output / filename)
                (args.output / QUALIFICATION).write_bytes(native.canonical(result) + b'\n')
                read_qualification(args.output, args.repository_commit, args.runtime_run_id, baseline)
            except Exception:
                shutil.rmtree(args.output)
                raise
    print(json.dumps({'native_build_run_id': result['native_build_run_id']}))


if __name__ == '__main__':
    main()
