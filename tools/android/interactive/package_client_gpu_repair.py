#!/usr/bin/env python3
"""Replace only the WGL probe over the published, ABI-qualified .20 GPU archive.

The complete original producer proof remains nested in the repair receipt. Mesa
and the ARM64 Vulkan probe are retained, never relabelled as current compilations.
"""
from __future__ import annotations
import argparse
import copy
import os
from pathlib import Path
import re
import stat
import tempfile
import zipfile

import package_client_gpu_runtime as old

ROOT = old.ROOT
require, pin, file_pin, encoded, read_json = old.require, old.pin, old.file_pin, old.encoded, old.read_json
ARCHIVE, MANIFEST, RECEIPT = old.ARCHIVE, 'client-gpu-repair-manifest.json', 'client-gpu-repair-build-input.json'
DONOR_COMMIT = '5a592380a5272a187248a1f971d9798a298ca5c0'
DONOR_RUN = 'https://github.com/Russianranger/coh-android/actions/runs/37788954170'
DONOR_ARCHIVE = {'bytes': 2854913, 'sha256': '5dff0392ddf724b43a6f3da900dfe8edc2926c116d8e190b1c75125c202df17d'}
DONOR_MANIFEST = {'bytes': 63643, 'sha256': '4df16f191f8abad428206487b6b98133d1e643a471ee246b997ef0ddd4341593'}
RETAINED = frozenset({old.DRIVER, old.VULKAN_PROBE, old.NOTICES})
SOURCE_FILES = ('tools/android/interactive/package_client_gpu_repair.py',
    'tools/android/interactive/test_client_gpu_repair_package.py',
    'android/native/coh-gpu-probe.c', 'tools/android/interactive/test_coh_gpu_probe_native.py')
RECEIPT_FIELDS = frozenset({'format', 'role', 'repository_commit', 'run_url', 'source_files',
    'retained_gpu_producer', 'donor_archive', 'retained_members', 'pe32_checks',
    'pe32_helper_files', 'binary_checks', 'mesa_driver_compiled_in_current_run',
    'native_vulkan_probe_compiled_in_current_run', 'wgl_probe_compiled_in_current_run',
    'physical_hardware_validated', 'physical_performance_validated'})


def checked(path, expected):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and file_pin(path) == expected, 'GPU repair pin differs: '+path.name)


def validate_donor(directory):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink()
        and {p.name for p in directory.iterdir()} == {old.ARCHIVE, old.MANIFEST, old.RECEIPT}
        and all(p.is_file() and not p.is_symlink() for p in directory.iterdir()), 'Exact .20 GPU donor inventory required')
    checked(directory/old.ARCHIVE, DONOR_ARCHIVE); checked(directory/old.MANIFEST, DONOR_MANIFEST)
    producer = read_json(directory/old.MANIFEST)
    contents = old.archive_contents(directory/ARCHIVE)
    inner, receipt = old.json_value(contents[old.INNER_MANIFEST]), old.json_value(contents[old.INNER_RECEIPT])
    old.validate_inner(inner, contents, DONOR_COMMIT)
    require(producer.get('format') == 1 and producer.get('repository_commit') == DONOR_COMMIT
        and producer.get('run_url') == DONOR_RUN and producer.get('hardware_manifest') == inner
        and producer.get('source_build') == receipt == read_json(directory/old.RECEIPT)
        and producer.get('files') == {ARCHIVE: DONOR_ARCHIVE}
        and producer.get('physical_hardware_validated') is False
        and producer.get('physical_performance_validated') is False, 'Frozen .20 GPU provenance differs')
    # Independently inspect actual retained ELF/PE bytes and their exact base ABI.
    with tempfile.TemporaryDirectory(prefix='coh-retained-gpu-abi-') as temporary:
        for name in (old.DRIVER, old.VULKAN_PROBE, old.PE32_PROBE):
            (Path(temporary)/name).write_bytes(contents[name])
        checks = old.binary_checks(temporary)
    require(checks == producer.get('binary_checks') == receipt.get('binary_checks'), 'Retained GPU binary/ABI proof differs')
    for name, expected in receipt.get('source_files', {}).items():
        require(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts
            and chr(92) not in name, 'Unsafe retained GPU source')
        if name not in {'android/native/coh-gpu-probe.c', 'tools/android/interactive/test_coh_gpu_probe_native.py'}:
            checked(ROOT/name, expected)
    return producer, contents


def source_pins():
    return {name: file_pin(ROOT/name) for name in SOURCE_FILES}


def validate_current_proof(checks, commit, run_url, production, proof_directory):
    old.validate_pe32_checks(checks, commit, run_url, production)
    return old.validate_pe32_helpers(checks, proof_directory)


def binary_checks(contents):
    with tempfile.TemporaryDirectory(prefix='coh-gpu-repair-binaries-') as temporary:
        for name in (old.DRIVER, old.VULKAN_PROBE, old.PE32_PROBE):
            (Path(temporary)/name).write_bytes(contents[name])
        return old.binary_checks(temporary)


def validate_package(directory, commit, donor_directory, probe_directory):
    directory, probe_directory = Path(directory), Path(probe_directory)
    require(re.fullmatch(r'[0-9a-f]{40}', commit or ''), 'Exact repair source required')
    require(directory.is_dir() and not directory.is_symlink()
        and {p.name for p in directory.iterdir()} == {ARCHIVE, MANIFEST, RECEIPT}
        and all(p.is_file() and not p.is_symlink() for p in directory.iterdir()), 'Exact repair artifact inventory required')
    donor, original = validate_donor(donor_directory)
    outer, receipt = read_json(directory/MANIFEST), read_json(directory/RECEIPT)
    contents = old.archive_contents(directory/ARCHIVE)
    inner = old.json_value(contents[old.INNER_MANIFEST]); old.validate_inner(inner, contents, commit)
    require(set(receipt) == RECEIPT_FIELDS and old.json_value(contents[old.INNER_RECEIPT]) == receipt
        and receipt.get('format') == 1 and receipt.get('role') == 'client_hardware_renderer_probe_repair'
        and receipt.get('repository_commit') == commit and receipt.get('run_url') == inner['run_url']
        and receipt.get('source_files') == source_pins() and receipt.get('retained_gpu_producer') == donor
        and receipt.get('donor_archive') == DONOR_ARCHIVE
        and receipt.get('retained_members') == {name: pin(original[name]) for name in sorted(RETAINED)}
        and receipt.get('mesa_driver_compiled_in_current_run') is False
        and receipt.get('native_vulkan_probe_compiled_in_current_run') is False
        and receipt.get('wgl_probe_compiled_in_current_run') is True
        and receipt.get('physical_hardware_validated') is False
        and receipt.get('physical_performance_validated') is False, 'GPU repair provenance/claim differs')
    require(all(contents[name] == original[name] for name in RETAINED)
        and contents[old.PE32_PROBE] != original[old.PE32_PROBE], 'Only the WGL probe may change')
    checked(probe_directory/old.PE32_PROBE, pin(contents[old.PE32_PROBE]))
    checks = read_json(probe_directory/'coh-gpu-probe-native-checks.json')
    require(receipt.get('pe32_checks') == checks
        and receipt.get('pe32_helper_files') == validate_current_proof(checks, commit,
            inner['run_url'], contents[old.PE32_PROBE], probe_directory), 'Current Win32 guard proof differs')
    actual = binary_checks(contents)
    require(all(actual[name] == donor['binary_checks'][name] for name in (old.DRIVER, old.VULKAN_PROBE))
        and receipt.get('binary_checks') == actual, 'Retained ABI/current WGL binary checks differ')
    expected = {'format': 1, 'role': old.ROLE, 'repository_commit': commit, 'run_url': inner['run_url'],
        'files': {ARCHIVE: file_pin(directory/ARCHIVE)}, 'hardware_manifest': inner,
        'probe_repair': receipt, 'binary_checks': actual,
        'physical_hardware_validated': False, 'physical_performance_validated': False}
    require(outer == expected, 'Exact outer repair receipt differs')
    if os.environ.get('GITHUB_RUN_ID'):
        require(inner['run_url'] == 'https://github.com/Russianranger/coh-android/actions/runs/'+os.environ['GITHUB_RUN_ID'],
            'Probe repair must be produced in this current run')
    return outer


def package(args):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit or '')
        and re.fullmatch(old.RUN, args.run_url or ''), 'Current source/run required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh GPU repair output required')
    donor, contents = validate_donor(args.donor_directory)
    checks = read_json(args.probe_directory/'coh-gpu-probe-native-checks.json')
    production = args.probe_directory/old.PE32_PROBE
    require(production.is_file() and not production.is_symlink() and 0 < production.stat().st_size <= 16*1024**2,
        'Actual bounded production WGL PE32 required')
    new_probe = production.read_bytes()
    helper_pins = validate_current_proof(checks, args.repository_commit, args.run_url, new_probe, args.probe_directory)
    require(new_probe != contents[old.PE32_PROBE], 'WGL probe repair did not change production bytes')
    retained_members = {name: pin(contents[name]) for name in sorted(RETAINED)}
    contents[old.PE32_PROBE] = new_probe
    receipt = {'format': 1, 'role': 'client_hardware_renderer_probe_repair',
        'repository_commit': args.repository_commit, 'run_url': args.run_url,
        'source_files': source_pins(), 'retained_gpu_producer': donor, 'donor_archive': DONOR_ARCHIVE,
        'retained_members': retained_members, 'pe32_checks': checks, 'pe32_helper_files': helper_pins,
        'binary_checks': binary_checks(contents), 'mesa_driver_compiled_in_current_run': False,
        'native_vulkan_probe_compiled_in_current_run': False, 'wgl_probe_compiled_in_current_run': True,
        'physical_hardware_validated': False, 'physical_performance_validated': False}
    contents[old.INNER_RECEIPT] = encoded(receipt)
    inner = copy.deepcopy(donor['hardware_manifest'])
    inner.update(repository_commit=args.repository_commit, run_url=args.run_url,
        files={name: dict(pin(contents[name]), mode=mode) for name, mode in old.MODES.items()})
    contents[old.INNER_MANIFEST] = encoded(inner)
    args.output.mkdir(parents=True)
    with zipfile.ZipFile(args.output/ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(contents):
            entry = zipfile.ZipInfo(name, (2026, 10, 8, 0, 0, 0)); entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | old.MODES.get(name, 0o644)) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED; archive.writestr(entry, contents[name])
    (args.output/RECEIPT).write_bytes(encoded(receipt))
    outer = {'format': 1, 'role': old.ROLE, 'repository_commit': args.repository_commit, 'run_url': args.run_url,
        'files': {ARCHIVE: file_pin(args.output/ARCHIVE)}, 'hardware_manifest': inner,
        'probe_repair': receipt, 'binary_checks': receipt['binary_checks'],
        'physical_hardware_validated': False, 'physical_performance_validated': False}
    (args.output/MANIFEST).write_bytes(encoded(outer))
    return validate_package(args.output, args.repository_commit, args.donor_directory, args.probe_directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('donor-directory', 'probe-directory', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True); parser.add_argument('--run-url', required=True)
    result = package(parser.parse_args()); print('Qualified probe repair:', result['files'][ARCHIVE])


if __name__ == '__main__': main()
