#!/usr/bin/env python3
"""Run unchanged PostgreSQL network-ACK tests with one authenticated MapServer.

Original reference/schema receipts stay intact. The sole execution substitution
is the independently admitted modern MapServer in the returned binary mapping;
the reference DbServer, DLLs, SQL templates and all ACK/commit guards are reused.
Only the evidence directory is publishable. Private disposable work is not.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import zipfile

import modern_wait_upstream as upstream
import modern_validation as validation

SOURCE = '1f75894db9117f3567b76d087d7cc5ddce87b3e6'
BUILD_RUN = 41378036783
VARIANT = 'thor_certified_startup'
REFERENCE_ARCHIVE = 'dd551750de26765297a45310bba51817b36a942d23f97d4da7f0d1365f49d3aa'
ACK_MARKER = b'COH_DBQUERY_CONTAINER_ACK'
require = validation.require


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Regular ACK input required: ' + path.name)
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def load_candidate(root):
    root = Path(root).resolve()
    sys.path[:0] = [str(root / name) for name in ('armport/app', 'armport/scripts',
        'tools', 'tools/android/dbserver', 'database/postgresql/tests', 'database/postgresql', 'android/guest')]
    names = ('server_pipeline', 'run_network_ack', 'prepare_runtime', 'package_reference_runtime',
             'prepare_dbserver_schema', 'verify_server_donors')
    modules = [importlib.import_module(name) for name in names]
    require(all(Path(module.__file__).resolve().is_relative_to(root) for module in modules),
            'ACK production helper came from another checkout')
    return modules


def wait_build(*, api, clock=time.monotonic, sleeper=time.sleep, timeout=198 * 60):
    deadline = clock() + timeout
    while True:
        require(clock() < deadline, 'Exact native build wait exceeded bound')
        try:
            run = api('/actions/runs/' + str(BUILD_RUN))
            if upstream.validate_run(run, BUILD_RUN, upstream.NATIVE_WORKFLOW, SOURCE, upstream.BRANCH):
                return run
        except upstream.RetryableApiError:
            pass
        remaining = deadline - clock()
        require(remaining > 0, 'Exact native build wait exceeded bound')
        sleeper(min(30, remaining))


def extract_reference(donors, destination, root, verifier):
    manifest = json.loads((root / 'armport/server/donor-inventory.json').read_text())
    receipt = verifier.verify(Path(donors), manifest)
    archive = Path(donors) / 'reference-artifact/coh-reference-win32.zip'
    require(pin(archive)['sha256'] == REFERENCE_ARCHIVE, 'Preserved reference archive differs')
    require(not destination.exists(), 'Fresh reference extraction required')
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        names = [entry.filename for entry in entries]
        require(len(names) == len(set(names)) == len({name.casefold() for name in names})
                and all(re.fullmatch('[A-Za-z0-9_.-]+', name) and name not in ('.', '..') for name in names)
                and all(not entry.is_dir() and not entry.flag_bits & 1
                        and (entry.external_attr >> 16) & 0o170000 != 0o120000 for entry in entries),
                'Preserved reference ZIP namespace differs')
        destination.mkdir()
        for entry in entries:
            (destination / entry.filename).write_bytes(package.read(entry))
    return receipt


class Overlay:
    """Authenticate the original inputs first; never forge build-info.json."""
    def __init__(self, original, native, pe, server_archive, baseline, destination):
        self.original, self.native, self.pe = original, native, pe
        self.archive, self.baseline, self.destination = Path(server_archive), baseline, Path(destination)
        self.calls, self.proof, self.original_result = 0, None, None

    def __call__(self, *args, **kwargs):
        require(self.calls == 0, 'Unexpected repeated ACK input admission')
        original = self.original(*args, **kwargs)
        files, tables, attributes, optional, package, binaries, hashes = original
        build, _, members = self.native.read_package(self.archive, variant=VARIANT,
            repository_commit=SOURCE, run_id=BUILD_RUN, upstream_root=self.baseline)
        raw = members['MapServer.exe']
        record = {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), **self.pe.pe_info(raw)}
        declared = build['files']['MapServer.exe']
        require(record['size'] == declared['bytes'] and record['sha256'] == declared['sha256']
                and ACK_MARKER in raw, 'Candidate ACK executable bytes or receive marker differ')
        require(package.get('postgresql_persistence_fixture') is False and 'DbServer.exe' in binaries
                and 'MapServer.exe' in binaries and hashes['MapServer.exe'] != record['sha256'],
                'Original fixture-OFF reference identities are required')
        merged = copy.deepcopy(package['files'])
        merged['MapServer.exe'] = record
        closure = self.pe.dependency_report(merged)
        require(not closure['unresolved'], 'Candidate imports do not close against unchanged reference DLLs')
        require(not self.destination.exists() and not self.destination.is_symlink(), 'Fresh candidate PE path required')
        self.destination.write_bytes(raw)
        require(pin(self.destination) == {'bytes': record['size'], 'sha256': record['sha256']}, 'Candidate PE staging changed')
        selected, selected_hashes = dict(binaries), dict(hashes)
        selected['MapServer.exe'], selected_hashes['MapServer.exe'] = self.destination, record['sha256']
        require({name: path for name, path in selected.items() if name != 'MapServer.exe'} ==
                {name: path for name, path in binaries.items() if name != 'MapServer.exe'}, 'Non-MapServer substitution refused')
        self.calls += 1
        self.original_result = original
        self.proof = {'format': 1, 'policy': 'original_reference_verified_then_exact_MapServer_mapping_only',
            'candidate_repository_commit': SOURCE, 'native_build_run_id': BUILD_RUN, 'variant': VARIANT,
            'native_archive': pin(self.archive), 'native_build_manifest': self.native.pin(members[self.native.BUILD]),
            'native_source_receipt_sha256': self.native.digest(self.native.canonical(build['build_input'])),
            'candidate_mapserver': {'bytes': record['size'], 'sha256': record['sha256']},
            'original_mapserver_sha256': hashes['MapServer.exe'], 'unchanged_dbserver_sha256': hashes['DbServer.exe'],
            'original_reference_repository_commit': package['repository_commit'],
            'original_reference_receipt_preserved': True, 'original_schema_and_templates_preserved': True,
            'candidate_import_closure': closure, 'test_guards_modified': False}
        return files, tables, attributes, optional, package, selected, selected_hashes

    def after(self, work, report, accepted_args, accepted_kwargs):
        require(self.calls == 1 and self.proof is not None, 'Candidate was not admitted by the actual test')
        # Re-run the unchanged original receipt/hash checks after all processes
        # stop, then verify the bytes actually copied into the exercised runtime.
        original = self.original(*accepted_args, **accepted_kwargs)
        require(original[4] == self.original_result[4] and original[6] == self.original_result[6],
                'Original accepted binary receipt or bytes changed during ACK execution')
        expected = dict(original[6], **{'MapServer.exe': self.proof['candidate_mapserver']['sha256']})
        for name in original[5]:
            if name in ('DbServer.exe', 'MapServer.exe') or name.casefold().endswith('.dll'):
                require(pin(Path(work) / 'runtime' / name)['sha256'] == expected[name],
                        'Exercised ACK binary changed: ' + name)
        require(report.get('mapserver_sha256') == expected['MapServer.exe']
                and report.get('dbserver_sha256') == expected['DbServer.exe'], 'ACK report executed another server')
        return dict(self.proof, original_reference_reverified_after_execution=True,
                    exercised_binary_hashes_reverified_after_execution=True)


def execute(args):
    require(os.name == 'nt', 'Native Windows runtime required for this ACK job')
    root = validation.verify_candidate_checkout(args.candidate_root, SOURCE)
    pipeline, network, staging, pe, schemas, donors = load_candidate(root)
    pipeline.check_build_run(json.loads(args.native_run_json.read_text()), repository_commit=SOURCE,
        server_run_id=BUILD_RUN, client_run_id=BUILD_RUN, data_run_id=BUILD_RUN)
    baseline = pipeline.native.baseline_root(args.baseline_root)
    require(not args.work.exists() and not args.output.exists(), 'Fresh isolated ACK work and evidence required')
    require(args.work.resolve() != args.output.resolve() and args.work.resolve() not in args.output.resolve().parents
            and args.output.resolve() not in args.work.resolve().parents, 'Private work must not overlap public evidence')
    args.work.mkdir(parents=True)
    result = {'format': 1, 'scope': 'exact_modern_MapServer_dbquery_with_unchanged_reference_DbServer',
        'candidate_repository_commit': SOURCE, 'native_build_run_id': BUILD_RUN, 'passed': False,
        'app_DbServer_runtime_validated': False, 'character_persistence_validated': False,
        'asset_complete_mapserver_startup_validated': False, 'physical_device_validated': False,
        'thor_60_second_target_proven': False}
    result['supporting_repository_commit'] = os.environ.get('GITHUB_SHA')
    result['supporting_scripts'] = {name: pin(Path(__file__).with_name(name)) for name in
        ('network_ack_candidate.py', 'modern_validation.py', 'modern_wait_upstream.py')}
    original, overlay = network.accepted_inputs, None
    try:
        result['host_postgresql_version'] = subprocess.check_output(
            [str(Path(args.pg_bin) / 'postgres.exe'), '--version'], text=True, timeout=15).strip()
        reference = args.work / 'reference'
        result['preserved_donors'] = extract_reference(args.donors, reference, root, donors)
        _, _, report_raw, schema_raw, _ = schemas.accepted_payloads(root)
        schema_dir = args.work / 'accepted-schema'; schema_dir.mkdir()
        schema_report, schema_archive = schema_dir / 'schema-generation-report.json', schema_dir / 'schema-outputs.zip'
        schema_report.write_bytes(report_raw); schema_archive.write_bytes(schema_raw)
        result['accepted_schema_report'], result['accepted_schema_archive'] = pin(schema_report), pin(schema_archive)
        runtime = args.work / 'text-runtime'
        staging.stage(runtime, root=root)
        overlay = Overlay(original, pipeline.native, pe, args.server_archive, baseline, args.work / 'MapServer.exe')
        network.accepted_inputs = overlay
        exercise = args.work / 'exercise'
        report = network.run(runtime, schema_report, reference, exercise, args.output,
            args.pg_bin, args.driver, timeout=600, root=root, schema_archive=schema_archive)
        result['network_ack_status'] = report.get('status')
        result['native_overlay'] = overlay.after(exercise, report,
            (runtime, schema_report, reference, root, schema_archive), {})
        require(report.get('status') == network.SUCCESS and report.get('failures') == []
                and report.get('multi_container_batch_validated') is True,
                'Unchanged network ACK/commit acceptance failed')
        validation.verify_candidate_checkout(root, SOURCE)
        result['passed'] = True
    except Exception as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        network.accepted_inputs = original
        if overlay is not None and overlay.proof is not None:
            result.setdefault('native_overlay', overlay.proof)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / 'candidate-network-ack-report.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('wait')
    run = commands.add_parser('run')
    for name in ('candidate-root', 'baseline-root', 'native-run-json', 'donors', 'server-archive', 'work', 'output'):
        run.add_argument('--' + name, type=Path, required=True)
    run.add_argument('--pg-bin', required=True)
    run.add_argument('--driver', required=True)
    args = parser.parse_args()
    if args.command == 'wait':
        require(os.environ.get('GITHUB_REPOSITORY') == upstream.REPOSITORY, 'Assigned repository required')
        result = wait_build(api=upstream.GitHubReadOnly(upstream.REPOSITORY, os.environ.get('GH_TOKEN')))
        print(json.dumps({'native_build_run_id': result['id'], 'candidate_commit': result['head_sha'], 'passed': True}))
        return 0
    return execute(args)


if __name__ == '__main__':
    raise SystemExit(main())
