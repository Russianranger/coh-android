"""Authenticate one staged metrics binary before using its exact old ancestry.

The binding is an APK/runtime-owned asset produced only after repository-side
source, fixture-report and package validation. The runtime inventory pins it,
the game archive and the helper; it is not accepted from the imported data pack.
This reader checks those identities; it does not execute native fixtures.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re
import struct

WRAPPER = 'armport_server_metrics'
BINDING = 'armport-server-metrics-binding.json'
ROLE = 'armport_server_metrics_runtime_binding'
ASSETS = Path(__file__).resolve().parent
MAX_JSON = 16 * 1024 * 1024
MAX_PE = 64 * 1024 * 1024
VARIANTS = {'retained_progress', 'thor_certified_startup'}
SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
PATCH = '49c0f73d9ea0a0ecb8d2f1de9a48ec1d5b20dc3c641e058bc8c1a5947440c387'
RETAINED_MAP = '52f85c9e2cccfe88eb92f0a2c379a45b14eb997339ce902ed7ba5d470f3690fb'
THOR_MAP = 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(raw):
    return {'bytes': len(raw), 'sha256': digest(raw)}


def read_file(path, maximum=MAX_JSON):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= maximum,
            'Missing, linked or oversized metrics binding/input: ' + path.name)
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    require(0 < len(raw) <= maximum and len(raw) == before.st_size
            and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            'Metrics binding/input changed while reading')
    return raw


def parse(raw):
    require(0 < len(raw) <= MAX_JSON, 'Metrics JSON exceeds bound')
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'Duplicate metrics JSON key')
            value[key] = item
        return value
    def reject(value):
        raise ValueError('Nonfinite metrics JSON value')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)
    require(isinstance(value, dict), 'Metrics JSON object required')
    return value


def summary(binding):
    build = parse(binding['build_manifest_utf8'].encode())
    return {'format': 1, 'variant': build['variant'], 'repository_commit': build['repository_commit'],
        'run_id': build['run_id'], 'server_package': binding['server_package'],
        'game_archive': binding['game_archive'], 'build_manifest': binding['build_manifest'],
        'source_report': binding['source_report'], 'source_receipt_sha256': digest(canonical(build['build_input'])),
        'mapserver': {key: build['files']['MapServer.exe'][key] for key in ('bytes', 'sha256')},
        'runtime_execution_validated': False, 'physical_device_validated': False}


def validate_binding(value):
    require(isinstance(value, dict) and set(value) == {'format', 'role', 'server_package', 'game_archive',
            'build_manifest', 'build_manifest_utf8', 'previous_manifest', 'previous_manifest_utf8',
            'source_report', 'source_report_utf8'} and type(value.get('format')) is int
            and value['format'] == 1 and value['role'] == ROLE, 'Metrics binding shape differs')
    documents = []
    for name in ('build_manifest', 'previous_manifest', 'source_report'):
        require(isinstance(value[name + '_utf8'], str), 'Metrics embedded raw document missing')
        raw = value[name + '_utf8'].encode()
        require(pin(raw) == value[name], 'Metrics embedded raw document pin differs')
        documents.append(parse(raw))
    build, previous, report = documents
    require(build.get('role') == WRAPPER and type(build.get('format')) is int and build['format'] == 1
            and build.get('variant') in VARIANTS
            and re.fullmatch(r'[a-f0-9]{40}', str(build.get('repository_commit')))
            and type(build.get('run_id')) is int and build['run_id'] > 0
            and build.get('run_url') == 'https://github.com/Russianranger/coh-android/actions/runs/' + str(build['run_id'])
            and build.get('source_commit') == previous.get('source_commit') == SOURCE
            and build.get('data_commit') == previous.get('data_commit') == DATA
            and build.get('architecture') == 'Win32' and build.get('configuration') == 'OptDebug'
            and build.get('build_targets') == ['MapServer']
            and all(build.get(key) is False for key in ('postgresql_persistence_fixture', 'shipping_binary_executed',
                'runtime_execution_validated', 'physical_device_validated')),
            'Metrics build identity or validation scope differs')
    require(value['build_manifest_utf8'].encode() == canonical(build)
            and build.get('source_test_report') == value['source_report']
            and build.get('source_test_report_validation') == 'exact_prepared_source_and_unpatched_control_report',
            'Metrics build/source report binding differs')
    source = build.get('build_input', {})
    require(source.get('variant') == build['variant'] and source.get('role') == WRAPPER
            and source.get('source_commit') == SOURCE and source.get('build_targets') == ['MapServer']
            and source.get('patch') == {'path': 'armport/patches/0119-armport-server-tick-file-metrics.patch', 'sha256': PATCH}
            and source.get('native_execution_validated') is False
            and source.get('contract', {}).get('gameplay_decisions_changed') is False
            and source.get('contract', {}).get('disabled_by_default') is True
            and report.get('role') == 'armport_server_metrics_source_checks' and report.get('status') == 'passed'
            and report.get('variant') == build['variant']
            and report.get('build_input_sha256') == digest(canonical(source))
            and report.get('source_sha256') == source.get('patched_sha256')
            and report.get('unpatched_control_failed') is True and report.get('shipping_binary_executed') is False,
            'Metrics source scope or extracted-source report differs')
    require(WRAPPER not in previous and build.get('predecessor') == {
        'manifest': value['previous_manifest'], 'canonical_sha256': digest(canonical(previous)),
        'mapserver': previous.get('files', {}).get('MapServer.exe')}, 'Metrics exact predecessor differs')
    old = previous['files']['MapServer.exe']; current = build.get('files', {}).get('MapServer.exe', {})
    expected_old = RETAINED_MAP if build['variant'] == 'retained_progress' else THOR_MAP
    require(set(build.get('files', {})) == {'MapServer.exe'} and old.get('sha256') == expected_old
            and set(current) == {'bytes', 'sha256', 'pe_machine', 'imports', 'delay_imports'}
            and type(current['bytes']) is int and 0 < current['bytes'] <= MAX_PE
            and re.fullmatch(r'[a-f0-9]{64}', str(current['sha256']))
            and current['sha256'] != old['sha256'] and current['pe_machine'] == 0x14c
            and current['imports'] == old['imports'] and current['delay_imports'] == old['delay_imports'],
            'Metrics MapServer changed architecture or dependency closure')
    return build, previous, report


def load_binding():
    raw = read_file(ASSETS / BINDING)
    value = parse(raw)
    build, previous, report = validate_binding(value)
    runtime = parse(read_file(ASSETS / 'runtime-manifest.json'))
    require(runtime.get('files', {}).get(BINDING) == pin(raw)
            and runtime['files'].get('game-package.tar.gz') == value['game_archive']
            and runtime.get('repository_commit') == build['repository_commit']
            and canonical(runtime.get(WRAPPER)) == canonical(summary(value)),
            'Metrics binding differs from the authenticated runtime inventory')
    return value, build, previous, report


def verify_archive(path):
    value, _, _, _ = load_binding()
    require(pin(read_file(path, 512 * 1024 * 1024)) == value['game_archive'],
            'Metrics game archive differs from the admitted candidate')
    return value


def _authenticate(path, package):
    value, build, previous, _ = load_binding()
    wrapper = package.get(WRAPPER) if isinstance(package, dict) else None
    require(isinstance(wrapper, dict) and set(wrapper) == {'receipt', 'receipt_sha256'}
            and canonical(wrapper['receipt']) == canonical(build)
            and wrapper['receipt_sha256'] == digest(canonical(build))
            and package.get('files', {}).get('MapServer.exe') == build['files']['MapServer.exe'],
            'Metrics package differs from the admitted build/run/head')
    # Do not expose predecessor metadata until the actual current PE is checked.
    raw = read_file(path, MAX_PE)
    current = build['files']['MapServer.exe']
    require(pin(raw) == {key: current[key] for key in ('bytes', 'sha256')}, 'Current metrics MapServer bytes differ')
    require(len(raw) >= 64 and raw[:2] == b'MZ', 'Current metrics executable has no DOS header')
    offset = struct.unpack_from('<I', raw, 60)[0]
    require(offset <= len(raw) - 26 and raw[offset:offset + 4] == b'PE\0\0'
            and struct.unpack_from('<H', raw, offset + 4)[0] == 0x14c
            and struct.unpack_from('<H', raw, offset + 24)[0] == 0x10b,
            'Current metrics executable is not Win32 PE32')
    reconstructed = copy.deepcopy(package)
    reconstructed.pop(WRAPPER)
    reconstructed['files']['MapServer.exe'] = copy.deepcopy(build['predecessor']['mapserver'])
    require(canonical(reconstructed) == canonical(previous), 'Metrics package changed retained native ancestry')
    if build['variant'] == 'retained_progress':
        import game_device_diagnostic as retained
        require(value['previous_manifest']['sha256'] == retained.MAP_PROGRESS_PACKAGE_SHA256
                and retained.game.mapserver_progress_contract(previous)['producer'] == retained.MAP_PROGRESS_PRODUCER,
                'Metrics retained progress donor changed')
        baseline = previous['inputs']['mapserver_progress']['manifest']['build_input']
    else:
        import native_map_startup_contract as startup
        baseline = startup.embedded_receipt(previous)['build_input']
    require(canonical(build['build_input']['baseline_receipt']) == canonical(baseline),
            'Metrics source baseline does not match retained ancestry')
    return previous, _proof(value, build, previous)


def _proof(value, build, previous):
    return dict(summary(value), policy='authenticated_metrics_only_overlay',
        actual_mapserver_sha256=build['files']['MapServer.exe']['sha256'],
        previous_mapserver_sha256=previous['files']['MapServer.exe']['sha256'],
        package_receipt_sha256=digest(canonical(build)),
        source_receipt_sha256=digest(canonical(build['build_input'])),
        native_changed_source_sha256=build['build_input']['patched_sha256'],
        parser_or_definition_sources_changed=False, gameplay_decisions_changed=False)


def verified_previous(path, package):
    return _authenticate(Path(path), package)


def verify_current_map(path, package):
    return _authenticate(Path(path), package)[1]


def producer_matches(producer, historical_sha256):
    """Bind exported compatibility evidence to this runtime's admitted build."""
    if producer.get('mapserver_sha256') == historical_sha256:
        return True
    try:
        value, build, previous, _ = load_binding()
        proof = producer.get(WRAPPER, {})
        return (build['variant'] == 'thor_certified_startup'
            and previous['files']['MapServer.exe']['sha256'] == historical_sha256
            and producer.get('mapserver_sha256') == build['files']['MapServer.exe']['sha256']
            and producer.get('repository_commit') == build['repository_commit']
            and producer.get('run_id') == build['run_id']
            and canonical(proof) == canonical(_proof(value, build, previous)))
    except (OSError, ValueError, KeyError, TypeError):
        return False
