#!/usr/bin/env python3
"""Qualify exact Atlas APK assets through import and isolated ARM64 game execution.

The APK's guest adapter and runtime are exercised, but Android service, PRoot
native libraries and device lifecycle are not. Host network isolation remains
mandatory even though the accepted executables bind only to IPv4 loopback.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/android/game'))
sys.path.insert(0, str(ROOT / 'tools/android/atlas'))
import host_game_smoke as game
import host_import_smoke as importer

_spec = importlib.util.spec_from_file_location('atlas_game_device_assets', Path(__file__).with_name('prepare_device_assets.py'))
assets_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(assets_builder)
dbhost, package = game.dbhost, importer.package
require, digest = game.require, game.digest
MAX_APK_ASSETS = 1024 * 1024 * 1024
MAX_RUNTIME_FILE = 256 * 1024 * 1024


def regular_input(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Missing or linked input: ' + str(path))
    return path.resolve()


def extract_apk_assets(apk, output):
    """Allow exactly both declared asset sets; never trust ZIP extraction paths."""
    require(not output.exists() and not output.is_symlink(), 'APK asset destination must be new')
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate APK member')
        manifest_entry = archive.getinfo('assets/runtime/runtime-manifest.json')
        require(0 < manifest_entry.file_size <= 8 * 1024 * 1024, 'Oversized runtime manifest')
        manifest = json.loads(archive.read(manifest_entry))
        require(isinstance(manifest, dict) and manifest.get('format') == 1,
                'Unsupported APK runtime manifest')
        files = manifest.get('files')
        game.inventory_bounds(files, maximum_files=64, maximum_bytes=MAX_APK_ASSETS)
        require(all(len(PurePosixPath(name).parts) == 1 for name in files), 'APK runtime must be flat')
        expected = {'assets/runtime/' + name for name in (*files, 'runtime-manifest.json')}
        expected.update('assets/atlas/' + name for name in package.PACKAGE_FILES)
        require({name for name in names if name.startswith('assets/')} == expected,
                'Unexpected APK asset set')
        total = 0
        entries = []
        for name in sorted(expected):
            entry = archive.getinfo(name)
            mode = entry.external_attr >> 16
            limit = MAX_RUNTIME_FILE if name.startswith('assets/runtime/') else importer.game.MAX_BYTES
            require(not entry.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG)
                    and not entry.flag_bits & 1 and 0 < entry.file_size <= limit,
                    'Linked, encrypted, oversized or non-file APK payload')
            total += entry.file_size
            require(total <= MAX_APK_ASSETS, 'APK assets exceed extraction budget')
            entries.append((name, entry))
        output.mkdir(parents=True)
        for name, entry in entries:
            target = output / name.removeprefix('assets/')
            target.parent.mkdir(exist_ok=True)
            size = 0
            with archive.open(entry) as source, target.open('xb') as destination:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    size += len(block)
                    require(size <= entry.file_size, 'APK payload exceeds declared size')
                    destination.write(block)
            require(size == entry.file_size, 'Truncated APK payload')
    return {'runtime': output / 'runtime', 'atlas': output / 'atlas'}


def qualify_import(*, assets, archive, installation, evidence, contract, data_manifest):
    """Run the accepted Java core and independently hash its complete result."""
    require(not installation.exists() and not evidence.exists(), 'Import proof destinations must be fresh')
    installation.mkdir(parents=True)
    evidence.mkdir(parents=True)
    started = time.monotonic()
    report = {'format': 1, 'status': 'running', 'scope': 'hosted_JVM_import_of_exact_Atlas_APK_assets',
              'repository_commit': contract['repository.commit'],
              'android_execution_validated': False, 'gameplay_validated': False}
    try:
        require(archive.stat().st_size == importer.game.ASSET_ARCHIVE_BYTES
                and digest(archive) == importer.game.ASSET_ARCHIVE_SHA256,
                'Selected archive differs from the reviewed input')
        classes = installation / 'classes'
        classes.mkdir()
        core = ROOT / 'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java'
        harness = ROOT / 'tools/android/atlas/java/io/github/russianranger/cohatlas/HostImport.java'
        report['java_source_sha256'] = {str(path.relative_to(ROOT)): digest(path) for path in (core, harness)}
        report['apk_payloads'] = {name: {'bytes': (assets / name).stat().st_size, 'sha256': digest(assets / name)}
                                  for name in sorted(package.PACKAGE_FILES)}
        summary_path = evidence / 'import-summary.properties'
        with (evidence / 'host-import.log').open('w') as log:
            subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                            '-d', str(classes), str(core), str(harness)], cwd=ROOT, check=True,
                           stdout=log, stderr=subprocess.STDOUT, timeout=120)
            subprocess.run(['java', '-Xmx512m', '-cp', str(classes),
                            'io.github.russianranger.cohatlas.HostImport', str(assets), str(archive),
                            str(installation / 'installed'), str(summary_path)], cwd=ROOT, check=True,
                           stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        summary = importer.read_properties(summary_path)
        require(summary.get('status') == 'passed' and summary.get('repository.commit') == contract['repository.commit']
                and summary.get('source.commit') == importer.game.SOURCE
                and summary.get('data.commit') == importer.game.DATA
                and summary.get('count') == str(game.DATA_FILE_COUNT)
                and summary.get('bytes') == str(game.DATA_TOTAL_BYTES)
                and summary.get('recovery') == summary.get('cancel') == 'passed',
                'Java import or cancellation/recovery proof differs')
        data = Path(summary['data.directory'])
        require(data.is_dir() and not data.is_symlink(), 'Invalid imported data directory')
        data = data.resolve()
        generation = data.parent
        require(data.name == 'data' and generation.parent == installation / 'installed'
                and re.fullmatch(r'generation-[0-9a-f]{32}', generation.name),
                'Java data destination differs from its private generation')
        _, records = package.pinned_assets(ROOT)
        files, total = importer.game.checked_inventory(generation, importer.game.expected_data(ROOT, records))
        document = {'format': 1, 'scope': 'reviewed_game_data',
                    'source_commit': importer.game.SOURCE, 'data_commit': importer.game.DATA,
                    'files': files, 'file_count': len(files), 'total_bytes': total,
                    'asset_manifest_sha256': importer.game.ASSET_MANIFEST_SHA256,
                    'asset_archive_sha256': importer.game.ASSET_ARCHIVE_SHA256,
                    'android_execution_validated': False, 'gameplay_validated': False}
        manifest_sha = hashlib.sha256(importer.game.assets.canonical(document)).hexdigest()
        require(manifest_sha == assets_builder.DATA_MANIFEST_SHA256 == digest(data_manifest),
                'Imported game inventory differs from the accepted APK inventory')
        receipt = importer.read_properties(generation / 'complete.properties')
        contract_sha = digest(assets / package.PROPERTIES)
        require(receipt == {'generation': generation.name, 'contract.sha256': contract_sha,
                            'count': str(game.DATA_FILE_COUNT), 'bytes': str(game.DATA_TOTAL_BYTES)},
                'Imported generation receipt differs')
        report.update(status='passed', file_count=len(files), total_bytes=total,
                      accepted_game_data_manifest_sha256=manifest_sha,
                      imported_files_independently_rehashed=True, exact_APK_payloads_verified=True,
                      recovery_and_previous_generation_preservation=True,
                      interrupted_reimport_preserves_current=True,
                      generation=generation.name, contract_sha256=contract_sha,
                      receipt_sha256=digest(generation / 'complete.properties'))
    except Exception as failure:
        report.update(status='failed', failure_type=type(failure).__name__, failure=str(failure))
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic() - started, 6)
        (evidence / 'host-import-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return generation, document, report


def make_command(*, work, assets, package, generation, schema, data_manifest, import_contract,
                 proot, timeout_seconds):
    command = game.make_command(work=work, assets=assets, package=package, data=generation,
                                schema=schema, proot=proot, timeout_seconds=timeout_seconds)
    guest_generation = '/opt/coh-game-data/' + generation.name
    replacements = {'/opt/coh-m3/game_diagnostic.py': '/opt/coh-m3/game_device_diagnostic.py',
                    '/opt/coh-game-data': guest_generation,
                    str(generation.resolve()) + ':/opt/coh-game-data':
                        str(generation.resolve()) + ':' + guest_generation}
    command = [replacements.get(value, value) for value in command]
    command[command.index('-w'):command.index('-w')] = [
        '-b', str(data_manifest.resolve()) + ':/opt/coh-game-data-manifest.json',
        '-b', str(import_contract.resolve()) + ':/opt/coh-import-contract.properties']
    return command + ['--game-data-manifest', '/opt/coh-game-data-manifest.json',
                      '--import-contract', '/opt/coh-import-contract.properties', '--listener-policy', 'device']


def validate_adapter_report(report, *, candidate_commit, runtime, import_report):
    """Bind new adapter provenance alongside the unchanged eighteen-stage proof."""
    require(report.get('listener_policy') == 'device'
            and report.get('android_listener_binding_validated') is False,
            'Hosted adapter listener policy or device-proof scope differs')
    expected_content = {key: import_report[key] for key in ('generation', 'contract_sha256', 'receipt_sha256',
                                                           'file_count', 'total_bytes')}
    expected_content.update(private_copy_verified=True, source_generation_unchanged=True)
    require(dbhost.exact_contract(report.get('imported_content'), expected_content),
            'Guest did not preserve and independently verify the exact imported generation')
    expected_adapter = {'candidate_repository_commit': candidate_commit,
                        'accepted_runtime_manifest_sha256': dbhost.ACCEPTED_RUNTIME_MANIFEST,
                        'accepted_game_repository_commit': assets_builder.PACKAGE_COMMIT,
                        'guest_source_sha256': {name: runtime['files'][name]['sha256']
                                                for name in assets_builder.GUEST_SCRIPTS}}
    require(dbhost.exact_contract(report.get('device_adapter'), expected_adapter),
            'Guest adapter provenance differs from the exact APK')


def qualify(args):
    require(sys.platform == 'linux' and platform.machine().lower() in ('aarch64', 'arm64'),
            'Native ARM64 Linux is required')
    require(os.getuid() > 0 and os.geteuid() == os.getuid(), 'Run as the original non-root runner')
    require(60 <= args.timeout_seconds <= 7200, 'Guest timeout must be between 60 and 7200 seconds')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    require(args.repository_commit == commit, 'Candidate differs from the checked-out source')
    apk, archive = map(regular_input, (args.apk, args.archive))
    work, evidence, proot = (Path(path).resolve() for path in (args.work, args.evidence, args.proot))
    inputs_root = work.with_name(work.name + '-inputs')
    for destination in (work, evidence, inputs_root):
        require(not destination.exists(), 'Qualification output must be fresh')
        require((destination != ROOT and ROOT not in destination.parents) or destination.is_relative_to(ROOT / 'out'),
                'Qualification output overlaps source')
        require(all(destination != source and destination not in source.parents for source in (apk, archive, proot)),
                'Qualification output overlaps an input')
    require(all(a != b and a not in b.parents and b not in a.parents
                for a, b in ((work, evidence), (work, inputs_root), (evidence, inputs_root))),
            'Qualification outputs overlap')
    extracted = extract_apk_assets(apk, inputs_root / 'apk-assets')
    assets = extracted['runtime']
    runtime = assets_builder.verify_device_metadata(assets)
    require(runtime['repository_commit'] == commit, 'APK runtime candidate commit differs')
    prepared = assets_builder.extract_device_inputs(assets, inputs_root / 'runtime-inputs')
    contract = package.verify_package(extracted['atlas'], commit, verify_archive=False)
    disk = game.check_paths_and_space(work, evidence, (inputs_root, apk, archive, proot), data_bytes=game.DATA_TOTAL_BYTES)
    for name in ('proot', 'proot-loader'):
        path = regular_input(proot / name)
        path.chmod(0o755)
    setup = game.prepare_runtime(work, evidence, assets)
    # Replace even the inherited modules with the verified APK bytes.
    for name in (*assets_builder.GUEST_SCRIPTS, 'GameStackProbe.exe'):
        shutil.copyfile(assets / name, work / 'm3-tools' / name)
    setup['guest_script_sha256'] = {name: digest(work / 'm3-tools' / name) for name in assets_builder.GUEST_SCRIPTS}
    shutil.copyfile(assets / 'stack-probe-build.json', evidence / 'stack-probe-build.json')
    started = time.monotonic()
    proof = {'format': 1, 'status': 'running', 'scope': 'exact_APK_import_and_isolated_ARM64_device_adapter',
             'candidate_repository_commit': commit,
             'apk': {'bytes': apk.stat().st_size, 'sha256': digest(apk)},
             'android_execution_validated': False, 'gameplay_validated': False}
    try:
        generation, data_manifest, imported = qualify_import(
            assets=extracted['atlas'], archive=archive, installation=inputs_root / 'imported',
            evidence=evidence / 'imported', contract=contract, data_manifest=prepared['data_manifest'])
        package_manifest = game.read_json(prepared['package'] / 'game-package.json')
        schema_manifest = game.read_json(prepared['schema'] / 'schema-manifest.json')
        expected = game.make_expectations(assets, prepared['package'], prepared['data_manifest'].parent,
                                         prepared['schema'], package_manifest, schema_manifest, data_manifest)
        inputs = {'format': 1, 'scope': 'host_Atlas_device_adapter_inputs', **expected['inputs'], **setup,
                  'candidate_repository_commit': commit, 'apk': proof['apk'],
                  'accepted_package_run_id': assets_builder.PACKAGE_RUN_ID,
                  'import_contract_sha256': imported['contract_sha256'],
                  'import_receipt_sha256': imported['receipt_sha256'], 'import_generation': generation.name,
                  'disk_preflight': disk, 'runtime_commit': runtime['repository_commit'],
                  'hang_observer': assets_builder.stack_probe_receipt.verify(assets, assets_builder.PACKAGE_COMMIT),
                  'proot_sha256': digest(proot / 'proot'), 'proot_loader_sha256': digest(proot / 'proot-loader'),
                  'dbserver_profile': 'loopback', 'game_listener_profile': 'loopback',
                  'listener_policy': 'device', 'host_network_namespace_required': True,
                  'android_execution_validated': False, 'gameplay_validated': False}
        (evidence / 'host-device-inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
        (work / 'rootfs/opt/coh-game-data' / generation.name).mkdir(mode=0o700)
        (work / 'rootfs/opt/coh-game-data-manifest.json').touch()
        (work / 'rootfs/opt/coh-import-contract.properties').touch()
        command = make_command(work=work, assets=assets, package=prepared['package'], generation=generation,
                               schema=prepared['schema'], data_manifest=prepared['data_manifest'],
                               import_contract=extracted['atlas'] / package.PROPERTIES,
                               proot=proot, timeout_seconds=args.timeout_seconds)
        command, environment, network_expected = dbhost.isolate_command(command, evidence=evidence, proot=proot, work=work)
        report = game.run_guest(command, environment, work / 'state', evidence,
                                timeout_seconds=args.timeout_seconds, expected=expected)
        dbhost.validate_network_receipt(game.read_json(evidence / 'network-isolation.json'), network_expected)
        validate_adapter_report(report, candidate_commit=commit, runtime=runtime, import_report=imported)
        proof.update(status='passed', stages=len(report['stages']), full_game_captures_verified=True,
                     network_namespace_verified=True, imported_generation_verified=True,
                     accepted_package_run_id=assets_builder.PACKAGE_RUN_ID)
    except Exception as failure:
        proof.update(status='failed', failure_type=type(failure).__name__, failure=str(failure))
        raise
    finally:
        proof['elapsed_seconds'] = round(time.monotonic() - started, 6)
        (evidence / 'host-device-qualification.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof, indent=2))
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('apk', 'archive', 'proot', 'work', 'evidence'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--timeout-seconds', type=int, default=5400)
    qualify(parser.parse_args())


if __name__ == '__main__':
    main()
