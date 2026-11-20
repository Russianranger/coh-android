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
PATCH = '5656eb55d3dcc7cb45ee7760a9befbf2d08bdae90e72dbd678eda6662bca085f'
RETAINED_MAP = '52f85c9e2cccfe88eb92f0a2c379a45b14eb997339ce902ed7ba5d470f3690fb'
THOR_MAP = 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'
# Opt-in ARMPORT_TRUSTED_BINS switch (patch 0120), off unless the guest sets it.
TRUSTED_PATCH = '906433c1e6266f9ee4e6fa41e426676bdde45c9efc9df26dddadfbc2e34f6779'
TEXTPARSER = 'libs/UtilitiesLib/src/utils/textparser.c'
# 0.13.75: the same switch for bin/defnames.bin (no object_library tree scan).
OBJECT_LIBRARY_PATCH = '501b4a1f2ed0fed7e7c65b907b79f380b9e8c28a296c2fefd6c9bbe09a4ad930'
GROUPFILELIB = 'Common/group/groupfilelib.c'
# 0.13.75: opt-in ARMPORT_PHYSX_CACHE (patches/mapserver-physx-cache): cooked collision
# meshes are read back at a later start instead of cooked again.
PHYSX_PATCH = '5f75cfbca88cccd12d6e7fa8417369364b89da768e5722e82c378006b1429092'
PHYSX_HEADER = 'Common/NovodeX/armport_physx_cache.h'
# 0.13.77: the trusted-bin switch for what a start reads ahead (no Defs or Menu tree
# read-ahead; prepared message bins without the listing of their source folders).
START_TREES_PATCH = '8938c02ae55b4f7cbf17c94615fa84df71281a7560d6ed46289cb56c8db07bcb'
INITCOMMON = 'Common/gameComm/initCommon.c'
MESSAGESTORE = 'libs/UtilitiesLib/src/language/MessageStore.c'
# 0.13.77: where "loading map" spends its time, with the metrics variable (measurement only).
LOAD_PROFILE_PATCH = '8de8c69b4ba6115a6b74bb08627e702306d96f18eb99849bdae742b83f312cf9'
LOAD_PROFILE_HEADER = 'Common/group/armport_map_load_profile.h'
LOAD_PROFILE_SOURCES = ('Common/group/group.c', 'Common/group/groupgrid.c', 'MapServer/src/group/groupnetdb.c')
# 0.13.78: the trusted-bin switch for the bounds file of each loaded library file (not read back).
BOUNDS_PATCH = '5fb615789a34e6df0c2fee2b203fb60c47571af32b2571838375be865357d430'
# Opt-in ARMPORT_SPARE_FILE early zone server (patches/mapserver-zone-travel), off unless
# the guest sets the variable: shared loading first, then a wait for the map id and cookie.
SPARE_PATCH = '76748e6902e5b7fdde0697f99166104c5a5f9b7479a4b099e532ac8f78efb1d3'
SPARE_HEADER = 'MapServer/src/svr/armport_spare_server.h'
GAME_ARCHIVE = 'game-package.tar.gz'
# 0.13.52: an APK may carry the admitted Thor metrics server (with the trusted
# bins switch) as a second archive beside the unchanged device-proven one. The
# guest uses it only when the launch option asks for it.
OPTION = 'armport_server_option'
OPTION_ARCHIVE = 'game-package-trusted.tar.gz'
OPTION_REQUEST = 'COH_TRUSTED_BINS'


def option_record():
    return {'format': 1, 'archive': OPTION_ARCHIVE, 'default_archive': GAME_ARCHIVE,
            'request_environment': OPTION_REQUEST, 'default_selected': False}


def admitted_archive_name(runtime):
    """The archive the runtime binding pins: the option archive when offered."""
    if OPTION not in runtime:
        return GAME_ARCHIVE
    require(canonical(runtime[OPTION]) == canonical(option_record()), 'Server option record differs')
    return OPTION_ARCHIVE


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
    archive = admitted_archive_name(runtime)
    # The option is only for the Thor lineage with the reviewed switch.
    require(archive == GAME_ARCHIVE or (build['variant'] == 'thor_certified_startup' and parser_changed(build)),
            'Server option requires the Thor server with the trusted bins switch')
    require(runtime.get('files', {}).get(BINDING) == pin(raw)
            and runtime['files'].get(archive) == value['game_archive']
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
    spare_server_changed(build)
    object_library_changed(build)
    physx_cache_changed(build)
    start_trees_changed(build)
    load_profile_changed(build)
    bounds_files_changed(build)
    return previous, _proof(value, build, previous)


def _proof(value, build, previous):
    return dict(summary(value), policy='authenticated_metrics_only_overlay',
        actual_mapserver_sha256=build['files']['MapServer.exe']['sha256'],
        previous_mapserver_sha256=previous['files']['MapServer.exe']['sha256'],
        package_receipt_sha256=digest(canonical(build)),
        source_receipt_sha256=digest(canonical(build['build_input'])),
        native_changed_source_sha256=build['build_input']['patched_sha256'],
        parser_or_definition_sources_changed=parser_changed(build), gameplay_decisions_changed=False)


def parser_changed(build):
    """True only for the reviewed default-off trusted-bin switch in textparser.c."""
    source = build.get('build_input', {})
    changed = TEXTPARSER in source.get('patched_sha256', {})
    require(not changed or (source.get('trusted_bins_patch') == {
                'path': 'patches/mapserver-trusted-bins/0001-trusted-prepared-bins.patch', 'sha256': TRUSTED_PATCH}
            and source.get('contract', {}).get('trusted_bins', {}).get('disabled_by_default') is True),
            'Metrics build changed the text parser outside the reviewed trusted-bin switch')
    return changed


def object_library_changed(build):
    """True only for the reviewed default-off trusted defnames.bin switch in groupfilelib.c."""
    source = build.get('build_input', {})
    changed = GROUPFILELIB in source.get('patched_sha256', {})
    require(not changed or (source.get('object_library_patch') == {
                'path': 'patches/mapserver-trusted-bins/0002-trusted-object-library-bin.patch',
                'sha256': OBJECT_LIBRARY_PATCH}
            and source.get('contract', {}).get('trusted_object_library', {}).get('disabled_by_default') is True
            and source['contract']['trusted_object_library'].get('gameplay_decisions_changed') is False),
            'Metrics build changed the object library loader outside the reviewed trusted-bin switch')
    return changed


def physx_cache_changed(build):
    """True only for the reviewed default-off cooked mesh cache layer."""
    source = build.get('build_input', {})
    changed = PHYSX_HEADER in source.get('patched_sha256', {})
    require(not changed or (source.get('physx_cache_patch') == {
                'path': 'patches/mapserver-physx-cache/0001-cooked-mesh-cache.patch', 'sha256': PHYSX_PATCH}
            and source.get('contract', {}).get('physx_cache', {}).get('disabled_by_default') is True
            and source['contract']['physx_cache'].get('gameplay_decisions_changed') is False),
            'Metrics build changed PhysX mesh loading outside the reviewed cooked mesh cache layer')
    return changed


def start_trees_changed(build):
    """True only for the reviewed default-off start tree and message bin switch."""
    source = build.get('build_input', {})
    patched = source.get('patched_sha256', {})
    changed = INITCOMMON in patched or MESSAGESTORE in patched
    contract = source.get('contract', {})
    require(not changed or (INITCOMMON in patched and MESSAGESTORE in patched
            and source.get('start_trees_patch') == {
                'path': 'patches/mapserver-trusted-bins/0003-trusted-start-trees.patch',
                'sha256': START_TREES_PATCH}
            and all(contract.get(name, {}).get('disabled_by_default') is True
                    and contract[name].get('gameplay_decisions_changed') is False
                    and contract[name].get('environment_variable') == 'ARMPORT_TRUSTED_BINS'
                    for name in ('trusted_start_trees', 'trusted_message_bins'))),
            'Metrics build changed start folder loading outside the reviewed trusted-bin switch')
    return changed


def load_profile_changed(build):
    """True only for the reviewed measurement-only map load profile."""
    source = build.get('build_input', {})
    patched = source.get('patched_sha256', {})
    names = (LOAD_PROFILE_HEADER,) + LOAD_PROFILE_SOURCES
    changed = any(name in patched for name in names)
    entry = source.get('contract', {}).get('map_load_profile', {})
    require(not changed or (all(name in patched for name in names)
            and source.get('load_profile_patch') == {
                'path': 'patches/mapserver-load-profile/0001-map-load-profile.patch',
                'sha256': LOAD_PROFILE_PATCH}
            and entry.get('disabled_by_default') is True and entry.get('measurement_only') is True
            and entry.get('gameplay_decisions_changed') is False),
            'Metrics build changed map loading outside the reviewed load profile')
    return changed


def bounds_files_changed(build):
    """True only for the reviewed default-off trusted bounds file switch in groupfilelib.c."""
    source = build.get('build_input', {})
    entry = source.get('contract', {}).get('trusted_bounds_files')
    changed = 'bounds_files_patch' in source or entry is not None
    require(not changed or (GROUPFILELIB in source.get('patched_sha256', {})
            and source.get('bounds_files_patch') == {
                'path': 'patches/mapserver-trusted-bins/0004-trusted-bounds-files.patch', 'sha256': BOUNDS_PATCH}
            and isinstance(entry, dict) and entry.get('disabled_by_default') is True
            and entry.get('environment_variable') == 'ARMPORT_TRUSTED_BINS'
            and entry.get('gameplay_decisions_changed') is False
            and object_library_changed(build)),
            'Metrics build changed library bounds loading outside the reviewed trusted-bin switch')
    return changed


def physx_cache_available():
    """Whether the admitted metrics MapServer can read cooked meshes back."""
    try:
        _, build, _, _ = load_binding()
        return physx_cache_changed(build)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def spare_server_changed(build):
    """True only for the reviewed default-off early zone server layer."""
    source = build.get('build_input', {})
    changed = SPARE_HEADER in source.get('patched_sha256', {})
    require(not changed or (source.get('spare_server_patch') == {
                'path': 'patches/mapserver-zone-travel/0001-spare-zone-server.patch', 'sha256': SPARE_PATCH}
            and source.get('contract', {}).get('spare_server', {}).get('disabled_by_default') is True
            and source['contract']['spare_server'].get('gameplay_decisions_changed') is False),
            'Metrics build changed MapServer startup outside the reviewed early zone server layer')
    return changed


def spare_server_available():
    """Whether the admitted metrics MapServer can wait for its map id and cookie."""
    try:
        _, build, _, _ = load_binding()
        return spare_server_changed(build)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def trusted_bins_available():
    """Whether the admitted metrics MapServer carries the opt-in switch."""
    try:
        _, build, _, _ = load_binding()
        return parser_changed(build)
    except (OSError, ValueError, KeyError, TypeError):
        return False


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
