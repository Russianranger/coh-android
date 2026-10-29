#!/usr/bin/env python3
"""Build and stage a MapServer-only metrics overlay for one exact donor.

This is a repository-side producer/stager, not a guest compatibility bypass.
The caller must authenticate the outer donor (retained 0.10 or pinned Thor APK)
first and pass its exact game-package.json pin. Old source receipts are retained
unchanged. A retained-progress qualification cannot qualify the Thor variant.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'android/guest'), str(ROOT / 'armport/scripts')]
from package_reference_runtime import dependency_report, pe_info

VARIANTS = frozenset({'retained_progress', 'thor_certified_startup'})
BASELINE_COMMIT = 'c86a57962363dbe2dc2091dadde6abdfaa2e1e1c'
ROLE = 'armport_server_metrics'
WRAPPER = ROLE
BUILD = 'server-metrics-build.json'
PREVIOUS = 'previous-game-package.json'
CHECKS = 'server-metrics-source-checks.json'
MEMBERS = frozenset({'MapServer.exe', BUILD, PREVIOUS, CHECKS})
SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
MAX_FILE = 64 * 1024 * 1024
MAX_JSON = 16 * 1024 * 1024
MAX_SYMBOLS = 256 * 1024 * 1024
# .32's accepted startup binary is retained by the pinned .36 APK. Its raw
# manifest still comes from that authenticated outer donor at packaging time.
THOR_PREDECESSOR_MAPSERVER = {'bytes': 7475200,
    'sha256': 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'}
MAX_GAME = 512 * 1024 * 1024
HEX64 = re.compile(r'[a-f0-9]{64}')
COMMIT = re.compile(r'[a-f0-9]{40}')
NAME = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.-]*')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def baseline_root(path):
    """Use the exact clean historical producer checkout, never guest code."""
    path = Path(path)
    require(path.is_dir() and not path.is_symlink(), 'Historical baseline must be a real checkout')
    path = path.resolve()
    def git(*arguments):
        result = subprocess.run(['git', '-C', str(path), *arguments], capture_output=True, text=True, timeout=30)
        require(result.returncode == 0, 'Historical baseline git identity is unavailable')
        return result.stdout.strip()
    require(Path(git('rev-parse', '--show-toplevel')).resolve() == path
            and git('rev-parse', 'HEAD') == BASELINE_COMMIT,
            'Historical baseline must be exactly ' + BASELINE_COMMIT)
    require(git('status', '--porcelain', '--untracked-files=normal') == '',
            'Historical baseline checkout has modified or untracked inputs')
    return path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(raw):
    return {'bytes': len(raw), 'sha256': digest(raw)}


def valid_pin(value, maximum=MAX_FILE):
    require(isinstance(value, dict) and set(value) == {'bytes', 'sha256'}
            and type(value['bytes']) is int and 0 < value['bytes'] <= maximum
            and HEX64.fullmatch(str(value['sha256'])), 'Invalid byte pin')
    return value


def read_file(path, maximum=MAX_FILE):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Regular input file required: ' + str(path))
    require(0 < path.stat().st_size <= maximum, 'Input file exceeds size bounds: ' + path.name)
    data = path.read_bytes()
    require(0 < len(data) <= maximum, 'Input file changed outside size bounds: ' + path.name)
    return data


def parse_json(raw):
    require(0 < len(raw) <= MAX_JSON, 'JSON size exceeds bound')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('Nonfinite JSON number: ' + value)
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    require(isinstance(value, dict), 'JSON object required')
    return value


def executable_record(raw):
    require(0 < len(raw) <= MAX_FILE, 'Executable exceeds size bound')
    return dict(pin(raw), **pe_info(raw))


def source_module():
    # Lazy import keeps byte/archive validation independently testable.
    import prepare_server_metrics_source
    return prepare_server_metrics_source


def validate_source(value, upstream_root=ROOT):
    return source_module().validate_receipt(value, upstream_root=baseline_root(upstream_root))


def validate_predecessor(raw, variant):
    """Run the historical contract, without teaching it any new binary hash."""
    require(variant in VARIANTS, 'Unknown server variant')
    value = parse_json(raw)
    require(WRAPPER not in value and value.get('source_commit') == SOURCE
            and value.get('data_commit') == DATA, 'Wrong predecessor identity or already wrapped')
    records = value.get('files')
    require(isinstance(records, dict) and 'MapServer.exe' in records
            and len(records) <= 64 and len({name.casefold() for name in records}) == len(records),
            'Invalid predecessor inventory')
    for name, record in records.items():
        require(NAME.fullmatch(name) and name not in {'.', '..', 'game-package.json'}, 'Unsafe native member name')
        require(isinstance(record, dict), 'Native record must be an object')
        valid_pin({'bytes': record.get('bytes'), 'sha256': record.get('sha256')})
    if variant == 'retained_progress':
        import game_device_diagnostic as accepted
        require(digest(raw) == accepted.MAP_PROGRESS_PACKAGE_SHA256
                and not any(name in value for name in ('native_responsiveness', 'native_monorail', 'native_map_startup')),
                'Exact retained 0.10 progress donor required')
        proof = accepted.game.mapserver_progress_contract(value)
        require(proof['producer'] == accepted.MAP_PROGRESS_PRODUCER, 'Retained progress producer changed')
        baseline = value['inputs']['mapserver_progress']['manifest']['build_input']
    else:
        import native_map_startup_contract as accepted
        receipt = accepted.embedded_receipt(value)
        marker = parse_json(read_file(ROOT / 'tools/android/interactive/release-client-map-startup-0.13.32.json', MAX_JSON))
        producer = marker['native_component_inputs']['native']
        require(receipt['native_build_repository_commit'] == producer['repository_commit']
                and accepted.pin_record(receipt['mapserver']) == THOR_PREDECESSOR_MAPSERVER,
                'Thor startup native producer changed')
        baseline = receipt['build_input']
    return value, baseline


def validate_build(value, previous_raw, *, variant=None, repository_commit=None, run_id=None, upstream_root=ROOT):
    expected_keys = {'format', 'role', 'variant', 'repository_commit', 'source_commit', 'data_commit',
        'run_id', 'run_url', 'configuration', 'architecture', 'build_targets', 'build_input',
        'predecessor', 'files', 'symbols', 'cmake_cache', 'source_test_report',
        'source_test_report_validation', 'postgresql_persistence_fixture', 'shipping_binary_executed',
        'runtime_execution_validated', 'physical_device_validated'}
    require(isinstance(value, dict) and set(value) == expected_keys
            and type(value.get('format')) is int and value['format'] == 1 and value['role'] == ROLE
            and value.get('variant') in VARIANTS and (variant is None or value['variant'] == variant)
            and COMMIT.fullmatch(str(value.get('repository_commit')))
            and (repository_commit is None or value['repository_commit'] == repository_commit)
            and type(value.get('run_id')) is int and value['run_id'] > 0
            and (run_id is None or value['run_id'] == run_id)
            and value['run_url'] == 'https://github.com/Russianranger/coh-android/actions/runs/' + str(value['run_id'])
            and value['source_commit'] == SOURCE and value['data_commit'] == DATA
            and value['configuration'] == 'OptDebug' and value['architecture'] == 'Win32'
            and value['build_targets'] == ['MapServer']
            and all(value[key] is False for key in ('postgresql_persistence_fixture', 'shipping_binary_executed',
                'runtime_execution_validated', 'physical_device_validated')),
            'Server build identity, lineage or validation scope differs')
    previous, baseline = validate_predecessor(previous_raw, value['variant'])
    require(value['predecessor'] == {'manifest': pin(previous_raw), 'canonical_sha256': digest(canonical(previous)),
                'mapserver': previous['files']['MapServer.exe']}, 'Exact predecessor binding differs')
    validate_source(value['build_input'], upstream_root)
    require(value['build_input']['variant'] == value['variant']
            and canonical(value['build_input']['baseline_receipt']) == canonical(baseline),
            'Prepared server baseline differs from its donor')
    records = value['files']
    require(isinstance(records, dict) and set(records) == {'MapServer.exe'}, 'Only MapServer may be replaced')
    record = records['MapServer.exe']; old = previous['files']['MapServer.exe']
    require(isinstance(record, dict) and set(record) == {'bytes', 'sha256', 'pe_machine', 'imports', 'delay_imports'},
            'Unexpected MapServer record fields')
    valid_pin({'bytes': record['bytes'], 'sha256': record['sha256']})
    require(record['pe_machine'] == 0x14c and record['sha256'] != old['sha256']
            and record['imports'] == old['imports'] and record['delay_imports'] == old['delay_imports'],
            'MapServer architecture or retained import closure changed')
    require(isinstance(value['symbols'], dict) and set(value['symbols']) == {'MapServer.pdb'}, 'Exact MapServer symbols required')
    valid_pin(value['symbols']['MapServer.pdb'], MAX_SYMBOLS)
    valid_pin(value['cmake_cache'], MAX_JSON)
    valid_pin(value['source_test_report'], MAX_JSON)
    require(value['source_test_report_validation'] == 'exact_prepared_source_and_unpatched_control_report',
            'Source evidence validation scope differs')
    return value, previous


def make_manifest(executable, symbols, source_receipt, previous_raw, cache, report, *,
                  variant, repository_commit, run_id, upstream_root=ROOT):
    previous, _ = validate_predecessor(previous_raw, variant)
    # The source fixture executes POSIX shims, never the shipping Windows PE.
    # CI must run it and retain logs; validating a receipt is not executing it.
    require(parse_json(report).get('shipping_binary_executed') is False,
            'Source report must distinguish the shipping binary from extracted code')
    source_module().validate_test_report(parse_json(report), source_receipt, upstream_root=upstream_root)
    require(re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$', cache.decode('utf-8-sig'), re.M) == ['OFF'],
            'Shipping MapServer requires persistence fixture mode OFF')
    result = {'format': 1, 'role': ROLE, 'variant': variant, 'repository_commit': repository_commit,
        'source_commit': SOURCE, 'data_commit': DATA, 'run_id': run_id,
        'run_url': 'https://github.com/Russianranger/coh-android/actions/runs/' + str(run_id),
        'configuration': 'OptDebug', 'architecture': 'Win32', 'build_targets': ['MapServer'],
        'build_input': source_receipt,
        'predecessor': {'manifest': pin(previous_raw), 'canonical_sha256': digest(canonical(previous)),
                        'mapserver': previous['files']['MapServer.exe']},
        'files': {'MapServer.exe': executable_record(executable)}, 'symbols': {'MapServer.pdb': pin(symbols)},
        'cmake_cache': pin(cache), 'source_test_report': pin(report),
        'source_test_report_validation': 'exact_prepared_source_and_unpatched_control_report',
        'postgresql_persistence_fixture': False, 'shipping_binary_executed': False,
        'runtime_execution_validated': False, 'physical_device_validated': False}
    return validate_build(result, previous_raw, upstream_root=upstream_root)[0]


def read_package(path, *, variant=None, repository_commit=None, run_id=None, upstream_root=ROOT):
    raw = read_file(path, MAX_FILE + 3 * MAX_JSON)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        require(len(entries) == len(MEMBERS) and {entry.filename for entry in entries} == MEMBERS,
                'Server ZIP member closure differs')
        for entry in entries:
            limit = MAX_FILE if entry.filename == 'MapServer.exe' else MAX_JSON
            mode = entry.external_attr >> 16
            require(0 < entry.file_size <= limit and not entry.flag_bits & 1
                    and stat.S_IFMT(mode) in (0, stat.S_IFREG), 'Linked, encrypted or oversized ZIP member')
        contents = {entry.filename: archive.read(entry) for entry in entries}
    value, previous = validate_build(parse_json(contents[BUILD]), contents[PREVIOUS],
        variant=variant, repository_commit=repository_commit, run_id=run_id, upstream_root=upstream_root)
    require(executable_record(contents['MapServer.exe']) == value['files']['MapServer.exe'],
            'Packaged MapServer bytes or imports differ')
    require(pin(contents[CHECKS]) == value['source_test_report']
            and parse_json(contents[CHECKS]).get('shipping_binary_executed') is False,
            'Source test evidence bytes or scope differ')
    source_module().validate_test_report(parse_json(contents[CHECKS]), value['build_input'], upstream_root=upstream_root)
    return value, previous, contents


def _write_new(path, writer):
    path = Path(path)
    require(not path.exists() and not path.is_symlink(), 'Output must be a new path')
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + '.', delete=False) as temporary:
        staged = Path(temporary.name)
    try:
        writer(staged)
        require(not path.exists() and not path.is_symlink(), 'Output appeared while staging')
        staged.replace(path)
    finally:
        staged.unlink(missing_ok=True)


def package(binary_directory, prepared_source, cmake_cache, predecessor_manifest, source_report, output,
            *, variant, repository_commit, run_id, expected_predecessor_pin, upstream_root=ROOT):
    """Produce a deterministic ZIP; PDB stays in the separate symbol artifact."""
    upstream_root = baseline_root(upstream_root)
    source = source_module()
    receipt = source.verify_prepared(Path(prepared_source), upstream_root=upstream_root)
    previous_raw = read_file(predecessor_manifest, MAX_JSON)
    require(pin(previous_raw) == valid_pin(expected_predecessor_pin, MAX_JSON), 'Authenticated donor manifest differs')
    binary_directory = Path(binary_directory)
    executable = read_file(binary_directory / 'MapServer.exe')
    report = read_file(source_report, MAX_JSON)
    value = make_manifest(executable, read_file(binary_directory / 'MapServer.pdb', MAX_SYMBOLS), receipt, previous_raw,
        read_file(cmake_cache, MAX_JSON), report, variant=variant, repository_commit=repository_commit,
        run_id=run_id, upstream_root=upstream_root)
    contents = {'MapServer.exe': executable, BUILD: canonical(value), PREVIOUS: previous_raw, CHECKS: report}
    def write(target):
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, raw in sorted(contents.items()):
                info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, raw)
        read_package(target, variant=variant, repository_commit=repository_commit, run_id=run_id,
                     upstream_root=upstream_root)
    _write_new(output, write)
    return value


def read_game_archive(path):
    require(Path(path).is_file() and not Path(path).is_symlink() and Path(path).stat().st_size <= MAX_GAME,
            'Invalid or oversized game archive')
    files, total = {}, 0
    with tarfile.open(path, 'r:gz') as archive:
        for entry in archive:
            require(entry.isfile() and NAME.fullmatch(entry.name) and entry.name not in {'.', '..'}
                    and entry.name.casefold() not in {name.casefold() for name in files},
                    'Unsafe, duplicate or linked game archive member')
            limit = MAX_JSON if entry.name == 'game-package.json' else MAX_FILE
            total += entry.size
            require(0 < entry.size <= limit and total <= MAX_GAME and len(files) < 65,
                    'Game archive exceeds member or size bounds')
            files[entry.name] = archive.extractfile(entry).read()
    require('game-package.json' in files, 'Game manifest missing')
    game = parse_json(files['game-package.json'])
    require(set(files) == set(game.get('files', {})) | {'game-package.json'}, 'Game archive inventory differs')
    for name, row in game['files'].items():
        require(pin(files[name]) == {'bytes': row.get('bytes'), 'sha256': row.get('sha256')},
                'Game archive member bytes differ: ' + name)
        if name.lower().endswith(('.exe', '.dll')):
            require(executable_record(files[name]) == row, 'Game archive PE record differs: ' + name)
    return game, files


def previous_package(game):
    """Metadata projection only; callers must separately authenticate current PE."""
    previous = copy.deepcopy(game)
    wrapper = previous.pop(WRAPPER, None)
    require(isinstance(wrapper, dict) and set(wrapper) == {'receipt', 'receipt_sha256'}
            and wrapper['receipt_sha256'] == digest(canonical(wrapper['receipt'])), 'Metrics wrapper digest differs')
    build = wrapper['receipt']
    require(previous.get('files', {}).get('MapServer.exe') == build.get('files', {}).get('MapServer.exe'),
            'Metrics wrapper does not name the current MapServer')
    previous['files']['MapServer.exe'] = copy.deepcopy(build.get('predecessor', {}).get('mapserver'))
    require(digest(canonical(previous)) == build.get('predecessor', {}).get('canonical_sha256'),
            'Metrics wrapper changed retained package ancestry')
    return previous


def write_game_archive(path, files):
    with Path(path).open('wb') as target:
        with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for name, raw in sorted(files.items()):
                    entry = tarfile.TarInfo(name)
                    entry.size = len(raw); entry.mode = 0o644; entry.mtime = 0
                    archive.addfile(entry, io.BytesIO(raw))


def patch_game(game_archive, server_archive, output, *, variant, repository_commit, run_id, upstream_root=ROOT):
    """Create a new archive, altering only MapServer.exe and game-package.json."""
    build, previous, native = read_package(server_archive, variant=variant, repository_commit=repository_commit,
        run_id=run_id, upstream_root=upstream_root)
    game, files = read_game_archive(game_archive)
    require(files['game-package.json'] == native[PREVIOUS] and game == previous,
            'Staging donor differs from the exact build predecessor')
    require(WRAPPER not in game, 'Metrics overlay already installed')
    original = copy.deepcopy(game)
    game[WRAPPER] = {'receipt': build, 'receipt_sha256': digest(canonical(build))}
    game['files']['MapServer.exe'] = copy.deepcopy(build['files']['MapServer.exe'])
    # Import lists are byte-for-byte identical, so retain the old dependency
    # receipt too. Independently check that the new executable resolves.
    require(not dependency_report(game['files'])['unresolved'], 'MapServer imports exceed retained closure')
    require(previous_package(game) == original, 'Metrics overlay changed retained metadata')
    files['MapServer.exe'] = native['MapServer.exe']
    # Some retained receipts bind json.dumps(indent=2) in insertion order.
    # Sorting the whole manifest would silently invalidate their raw digests.
    files['game-package.json'] = (json.dumps(game, indent=2, allow_nan=False) + '\n').encode()
    def write(target):
        write_game_archive(target, files)
        read_game_archive(target)
    _write_new(output, write)
    return game


def runtime_binding(server_archive, game_archive, *, variant, repository_commit, run_id, upstream_root=ROOT):
    """Create a runtime-owned binding after the full source/package gates."""
    import armport_server_metrics_contract as guest
    build, previous, native = read_package(server_archive, variant=variant,
        repository_commit=repository_commit, run_id=run_id, upstream_root=upstream_root)
    game, _ = read_game_archive(game_archive)
    require(game.get(WRAPPER) == {'receipt': build, 'receipt_sha256': digest(canonical(build))}
            and previous_package(game) == previous, 'Staged game differs from the admitted metrics package')
    value = {'format': 1, 'role': guest.ROLE,
        'server_package': pin(read_file(server_archive, MAX_FILE + 3 * MAX_JSON)),
        'game_archive': pin(read_file(game_archive, MAX_GAME)),
        'build_manifest': pin(native[BUILD]), 'build_manifest_utf8': native[BUILD].decode('utf-8'),
        'previous_manifest': pin(native[PREVIOUS]), 'previous_manifest_utf8': native[PREVIOUS].decode('utf-8'),
        'source_report': pin(native[CHECKS]), 'source_report_utf8': native[CHECKS].decode('utf-8')}
    guest.validate_binding(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('package')
    for name in ('binary-directory', 'prepared-source', 'cmake-cache', 'predecessor-manifest', 'source-report', 'output'):
        build.add_argument('--' + name, type=Path, required=True)
    build.add_argument('--predecessor-bytes', type=int, required=True)
    build.add_argument('--predecessor-sha256', required=True)
    stage = sub.add_parser('patch-game')
    for name in ('game-archive', 'server-archive', 'output'):
        stage.add_argument('--' + name, type=Path, required=True)
    for command in (build, stage):
        command.add_argument('--variant', choices=sorted(VARIANTS), required=True)
        command.add_argument('--repository-commit', required=True)
        command.add_argument('--run-id', type=int, required=True)
        command.add_argument('--upstream-root', type=Path, default=ROOT)
    args = vars(parser.parse_args()); command = args.pop('command')
    if command == 'package':
        args['expected_predecessor_pin'] = {'bytes': args.pop('predecessor_bytes'), 'sha256': args.pop('predecessor_sha256')}
        result = package(**args)
    else:
        result = patch_game(**args)
    print(json.dumps({'status': 'packaged_runtime_unverified', 'variant': result.get('variant',
        result.get(WRAPPER, {}).get('receipt', {}).get('variant'))}))


if __name__ == '__main__':
    main()
