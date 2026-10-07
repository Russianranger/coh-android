#!/usr/bin/env python3
"""Validate the explicitly unaccepted 0.11.5 native derivative.

The enclosing signed APK inventories pin this receipt. It never promotes the
candidate executable to the stock reference or rewrites prepared-cache history.
"""
import copy
import hashlib
import json
import math
import re

SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
ROLE = 'native_responsiveness_candidate'
EXECUTABLES = {'CityOfHeroes.exe', 'MapServer.exe', 'client-launcher.exe'}
HEX64 = re.compile(r'[0-9a-f]{64}')


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical_sha(value):
    return hashlib.sha256((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()).hexdigest()


def scene_source_inputs_equivalent(received, accepted):
    """Allow only the two already proven PG C/H checkout encodings for this layer.

    Preserve both raw histories. Each enclosing compact source-receipt digest is
    verified before comparing normalized copies; all other receipt fields must
    remain identical to the accepted producer. Older layers keep exact equality.
    """
    encodings = {
        'Common/sql/pg_compat.h': (
            '2ca4c8befd57a07f16d71b4f6eeeec4ba0acde601883c1c50907c48769d137e7',
            '119ee1649b56cd859145a582e4d042bd3b3721831cba7c3b5acf9086a447e04e'),
        'DBServer/src/pg_persistence_test.c': (
            'c822b932db21a81cb97b951f00011c461d0d88a55f1f93ba8738df6326741433',
            '30fbf6ac294cc0c104287ea1450d579d31d61b6a03fc49dceadbf5aaa9cbd3c2')}

    def source_sha(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def normalized(inputs):
        require(isinstance(inputs, dict) and set(inputs) == {'character_events', 'client_texture', 'graphics_profile'},
            'Scene/frame retained source input inventory differs')
        result = copy.deepcopy(inputs)
        events = result['character_events']
        require(isinstance(events, dict) and isinstance(events.get('progress_build_input'), dict),
            'Scene/frame missing retained progress source receipt')
        progress = events['progress_build_input']
        require(isinstance(progress.get('game_build_input'), dict), 'Scene/frame missing retained game source receipt')
        game = progress['game_build_input']
        require(isinstance(game.get('postgresql_build_input'), dict), 'Scene/frame missing retained PG source receipt')
        pg = game['postgresql_build_input']
        require(isinstance(pg.get('overlay_sha256'), dict) and set(pg['overlay_sha256']) == set(encodings)
            and all(pg['overlay_sha256'][name] in variants for name, variants in encodings.items()),
            'Scene/frame PG source encoding is not an independently proven LF/CRLF variant')
        require(game.get('postgresql_build_input_canonical_sha256') == source_sha(pg)
            and progress.get('game_build_input_canonical_sha256') == source_sha(game)
            and events.get('progress_build_input_canonical_sha256') == source_sha(progress),
            'Scene/frame retained source ancestry digest differs')
        for name, variants in encodings.items(): pg['overlay_sha256'][name] = variants[0]
        game['postgresql_build_input_canonical_sha256'] = source_sha(pg)
        progress['game_build_input_canonical_sha256'] = source_sha(game)
        events['progress_build_input_canonical_sha256'] = source_sha(progress)
        return result

    require(normalized(received) == normalized(accepted), 'Scene/frame retained source ancestry differs')
    return True


def pe_record(record):
    size = record.get('size', record.get('bytes')) if isinstance(record, dict) else None
    require(isinstance(record, dict) and type(size) is int
            and 0 < size <= 64 * 1024 * 1024
            and HEX64.fullmatch(str(record.get('sha256', '')))
            and record.get('pe_machine') == 0x14c
            and all(isinstance(record.get(key), list)
                    and all(isinstance(item, str) and re.fullmatch(r'[A-Za-z0-9_.-]+', item)
                            for item in record[key]) for key in ('imports', 'delay_imports')),
            'Invalid candidate Win32 executable record')
    return record


def validate_receipt(receipt):
    require(isinstance(receipt, dict) and receipt.get('format') == 1 and receipt.get('role') == ROLE
            and re.fullmatch(r'[0-9a-f]{40}', str(receipt.get('repository_commit', '')))
            and receipt.get('source_commit') == SOURCE and receipt.get('data_commit') == DATA
            and receipt.get('configuration') == 'OptDebug' and receipt.get('architecture') == 'Win32'
            and receipt.get('runtime_execution_validated') is False
            and receipt.get('postgresql_persistence_fixture') is False
            and set(receipt.get('files', {})) == EXECUTABLES,
            'Native responsiveness candidate identity differs')
    for record in receipt['files'].values():
        pe_record(record)
    inputs = receipt.get('build_inputs', {})
    require(set(inputs) == {'character_events', 'client_texture', 'graphics_profile'}
            and all(isinstance(value, dict) and value.get('source_commit') == SOURCE
                    for value in inputs.values())
            and all(inputs[key].get('runtime_validation') == 'unverified'
                    for key in ('character_events', 'graphics_profile'))
            and inputs['client_texture'].get('runtime_performance_validated') is False
            and inputs['client_texture'].get('parse6_schema_changes') is False
            and inputs['client_texture'].get('role') == 'opt_in_client_texture_header_index',
            'Native responsiveness source receipts are incomplete')
    require(inputs['character_events'].get('build_role') == 'character_events'
            and inputs['character_events'].get('progress_build_input', {}).get('build_role') == 'mapserver_progress',
            'Native responsiveness must retain the original progress producer')
    cache = receipt.get('retained_cache', {})
    require(cache.get('schema_changed') is False
            and HEX64.fullmatch(str(cache.get('executable_sha256', '')))
            and cache['executable_sha256'] != receipt['files']['CityOfHeroes.exe']['sha256']
            and isinstance(cache.get('archive'), dict)
            and set(cache['archive']) == {'bytes', 'sha256'}
            and type(cache['archive']['bytes']) is int and cache['archive']['bytes'] > 0
            and HEX64.fullmatch(str(cache['archive']['sha256']))
            and isinstance(cache.get('schema_sources_sha256'), dict) and cache['schema_sources_sha256'],
            'Prepared cache donor history or schema compatibility proof differs')
    retained = receipt.get('retained_native_files', {})
    require(set(retained) == {'client', 'game'} and retained['client'] and retained['game'],
            'Retained native dependency receipts are incomplete')
    for group in retained.values():
        require(isinstance(group, dict), 'Invalid retained native dependency group')
        for name, record in group.items():
            require(re.fullmatch(r'[A-Za-z0-9_.-]+', name), 'Unsafe retained native dependency')
            pe_record(record)
    return receipt


def embedded_receipt(package):
    wrapper = package.get('native_responsiveness', {})
    receipt = validate_receipt(wrapper.get('receipt'))
    require(wrapper.get('receipt_sha256') == canonical_sha(receipt)
            and package.get('repository_commit') == receipt['repository_commit'],
            'Native candidate embedded receipt or checkout differs')
    return receipt


def client_contract(package, receipt=None):
    candidate = embedded_receipt(package)
    require(receipt is None or candidate == validate_receipt(receipt),
            'Client package and installed candidate receipts differ')
    expected = dict(candidate['retained_native_files']['client'])
    executable = candidate['files']['CityOfHeroes.exe']
    if 'startup_bundle_client' in package:
        executable = startup_bundle_client_contract(package, candidate)
    if 'client_loading' in package:
        executable = client_loading_contract(package, candidate)
    if 'client_startup_followup' in package:
        executable = client_startup_followup_contract(package, candidate)
    if 'client_scene_performance' in package:
        executable = client_scene_performance_contract(package, candidate)
    expected['CityOfHeroes.exe'] = executable
    require(package.get('files') == expected and len(expected) == 21
            and package.get('source_commit') == SOURCE and package.get('data_commit') == DATA
            and package.get('android_execution_validated') is False and package.get('gameplay_validated') is False,
            'Client candidate changed its retained DLL closure')
    return executable


def client_scene_performance_contract(package, candidate=None):
    """Preserve the accepted Game ancestry, schema and every DLL dependency."""
    candidate = embedded_receipt(package) if candidate is None else validate_receipt(candidate)
    previous = client_startup_followup_contract(package, candidate)
    accepted = package['client_startup_followup']
    wrapper = package.get('client_scene_performance')
    require(isinstance(wrapper, dict) and set(wrapper) == {'manifest', 'manifest_sha256',
        'base_client_startup_followup_manifest_sha256', 'base_client_executable'}
        and wrapper['base_client_startup_followup_manifest_sha256'] == accepted['manifest_sha256']
        and wrapper['base_client_executable'] == previous, 'Scene/frame must retain the exact accepted Game producer')
    manifest = wrapper['manifest']
    require(isinstance(manifest, dict) and wrapper['manifest_sha256'] == canonical_sha(manifest)
        and manifest.get('format') == 1 and manifest.get('role') == 'bounded_client_scene_and_frame_performance'
        and re.fullmatch(r'[0-9a-f]{40}', str(manifest.get('repository_commit', '')))
        and manifest.get('source_commit') == SOURCE and manifest.get('data_commit') == DATA
        and manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32'
        and manifest.get('build_targets') == ['Game'] and manifest.get('postgresql_persistence_fixture') is False
        and manifest.get('retained_native_dependencies_changed') is False
        and scene_source_inputs_equivalent(manifest.get('retained_source_inputs'), candidate['build_inputs'])
        and manifest.get('schema_sources_sha256') == candidate['retained_cache']['schema_sources_sha256']
        and manifest.get('base_client_executable') == previous
        and manifest.get('cache_encoding_changed') is False and manifest.get('runtime_execution_validated') is False
        and manifest.get('replacement_scope') == 'CityOfHeroes.exe_only'
        and set(manifest.get('files', {})) == {'CityOfHeroes.exe'}, 'Scene/frame changed native dependency or cache ancestry')
    build = manifest.get('build_input', {})
    files = {'Game/src/game.c', 'Game/src/graphics/gfx.c', 'Game/src/clientcomm/clientcomm.c',
        'Game/src/group/groupnetrecv.c', 'Common/seq/gfxtree.c', 'Common/seq/gfxtree.h',
        'Game/src/render/thread/rt_win_init.c'}
    patches = {'patches/client-scene-performance/0001-scene-loading-phase-and-preload.patch',
        'patches/client-scene-performance/0002-native-frame-timing.patch'}
    controls = {
        'scene_profile': {'environment_variable': 'COH_CLIENT_SCENE_PROFILE', 'enabled_value': '1',
            'disabled_by_default': True, 'record_prefix': 'COH_CLIENT_SCENE_PHASE_V1', 'bounded': True},
        'discarded_fx_preload': {'environment_variable': 'COH_CLIENT_DEFER_DISCARDED_FX_PRELOAD',
            'enabled_value': '1', 'disabled_by_default': True, 'stock_fallback_preserved': True,
            'surviving_post_invalidation_preload_preserved': True},
        'frame_profile': {'environment_variable': 'COH_CLIENT_FRAME_TIMING', 'enabled_value': '1',
            'disabled_by_default': True, 'record_prefix': 'COH_CLIENT_FRAME_TIMING_V1',
            'aggregate_only': True, 'bounded': True}}
    require(isinstance(build, dict) and set(build) == {'format', 'role', 'source_commit',
        'base_client_startup_followup_build_input', 'patches_sha256', 'source_sha256', 'patched_sha256',
        'overlay_sha256', 'reverse_patch_exact_base_verified', 'controls', 'build_targets', 'configuration',
        'architecture', 'cache_encoding_changed', 'parse6_schema_changes', 'source_freshness_changed',
        'graphics_profile_changes', 'renderer_changed', 'gameplay_validation_changes', 'runtime_execution_validated'}
        and build.get('format') == 1 and build.get('role') == manifest['role'] and build.get('source_commit') == SOURCE
        and build.get('base_client_startup_followup_build_input') == accepted['manifest']['build_input']
        and build.get('reverse_patch_exact_base_verified') is True and build.get('controls') == controls
        and build.get('build_targets') == ['Game'] and build.get('configuration') == 'OptDebug'
        and build.get('architecture') == 'Win32'
        and all(build.get(key) is False for key in ('cache_encoding_changed', 'parse6_schema_changes',
            'source_freshness_changed', 'graphics_profile_changes', 'renderer_changed',
            'gameplay_validation_changes', 'runtime_execution_validated')), 'Scene/frame native recipe changed correctness or renderer')
    for field, names in (('patches_sha256', patches), ('source_sha256', files), ('patched_sha256', files),
            ('overlay_sha256', {'Game/src/cohClientSceneTiming.h', 'Game/src/cohClientFrameTiming.h'})):
        require(isinstance(build.get(field), dict) and set(build[field]) == names
            and all(HEX64.fullmatch(str(value)) for value in build[field].values()), 'Scene/frame native source inventory differs')
    require(all(build['source_sha256'][name] != build['patched_sha256'][name] for name in files), 'Scene/frame recipe did not change declared sources')
    checks = manifest.get('windows_qualification', {})
    require(isinstance(checks, dict) and set(checks) == {'format', 'status', 'platform', 'architecture',
        'configuration', 'build_input', 'scene', 'frame'} and checks.get('format') == 1
        and checks.get('status') == 'passed' and checks.get('platform') == 'windows'
        and checks.get('architecture') == 'Win32' and checks.get('configuration') == 'OptDebug'
        and checks.get('build_input') == build, 'Scene/frame real Win32 proof differs')
    for role in ('scene', 'frame'):
        proof = checks.get(role, {})
        require(isinstance(proof, dict) and proof.get('format') == 1 and proof.get('status') == 'passed'
            and proof.get('platform') == 'windows' and proof.get('architecture') == 'Win32'
            and proof.get('configuration') == 'OptDebug' and proof.get('compiler_options') == ['/O2', '/Oy-', '/MT', '/TC']
            and HEX64.fullmatch(str(proof.get('harness_sha256', ''))), 'Scene/frame source-bound Win32 harness proof missing')
        patch = ('patches/client-scene-performance/0001-scene-loading-phase-and-preload.patch' if role == 'scene'
            else 'patches/client-scene-performance/0002-native-frame-timing.patch')
        header = 'Game/src/cohClientSceneTiming.h' if role == 'scene' else 'Game/src/cohClientFrameTiming.h'
        require(proof.get('patch_sha256') == build['patches_sha256'][patch]
            and proof.get('header_sha256') == build['overlay_sha256'][header], 'Scene/frame harness source differs from Game source')
    require(all(checks['scene'].get(name) is True for name in ('baseline_fallback_verified',
        'discarded_preload_elision_verified', 'surviving_preload_and_invalidation_verified',
        'scene_phase_bound_verified', 'scene_failure_and_wait_paths_preserved'))
        and checks['scene'].get('physical_scene_savings_validated') is False,
        'Scene Win32 proof did not preserve surviving preload, fallback or waits')
    require(all(checks['frame'].get(name) is True for name in ('wall_pacing_and_submission_separation_verified',
        'presentation_swap_wall_verified', 'histogram_upper_bounds_verified',
        'menu_loading_gameplay_mixed_states_verified', 'report_rate_and_120_report_cap_verified',
        'disabled_without_clock_cpu_or_logging_verified', 'clock_failure_nonfatal_verified',
        'fixed_buffer_full_state_format_verified', 'genuine_win32_qpc_and_thread_cpu_verified',
        'genuine_win32_tls_and_concurrent_json_verified'))
        and HEX64.fullmatch(str(checks['frame'].get('production_harness_sha256', '')))
        and checks['frame'].get('physical_frame_rate_or_gpu_latency_validated') is False,
        'Frame Win32 proof did not preserve bounded aggregate diagnostics')
    record = manifest['files']['CityOfHeroes.exe']; pe_record(record)
    require(record != previous and record['pe_machine'] == previous['pe_machine']
        and record['imports'] == previous['imports'] and record['delay_imports'] == previous['delay_imports'],
        'Scene/frame Game imports exceed retained DLL closure')
    return record


def startup_bundle_client_contract(package, candidate=None):
    """A new client producer wraps the frozen receipt; MapServer stays frozen."""
    candidate = embedded_receipt(package) if candidate is None else validate_receipt(candidate)
    wrapper = package.get('startup_bundle_client')
    require(isinstance(wrapper, dict) and set(wrapper) == {'manifest', 'manifest_sha256',
            'base_responsiveness_receipt_sha256', 'base_client_executable'}
            and wrapper['base_responsiveness_receipt_sha256'] == canonical_sha(candidate)
            and wrapper['base_client_executable'] == candidate['files']['CityOfHeroes.exe'],
            'Startup client must retain the exact frozen native producer')
    manifest = wrapper['manifest']
    require(isinstance(manifest, dict) and wrapper['manifest_sha256'] == canonical_sha(manifest)
            and manifest.get('format') == 1
            and manifest.get('role') == 'verified_root_client_startup_supplement'
            and re.fullmatch(r'[0-9a-f]{40}', str(manifest.get('repository_commit', '')))
            and manifest.get('source_commit') == SOURCE and manifest.get('data_commit') == DATA
            and manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32'
            and manifest.get('build_targets') == ['Game']
            and manifest.get('postgresql_persistence_fixture') is False
            and manifest.get('runtime_execution_validated') is False
            and manifest.get('replacement_scope') == 'CityOfHeroes.exe_only'
            and manifest.get('retained_native_dependencies_changed') is False
            and manifest.get('retained_source_inputs') == candidate['build_inputs']
            and manifest.get('schema_sources_sha256') == candidate['retained_cache']['schema_sources_sha256']
            and set(manifest.get('files', {})) == {'CityOfHeroes.exe'},
            'Startup client source, dependency or cache provenance differs')
    build = manifest.get('build_input', {})
    require(isinstance(build, dict) and build.get('format') == 1
            and build.get('role') == manifest['role'] and build.get('source_commit') == SOURCE
            and build.get('base_texture_build_input') == candidate['build_inputs']['client_texture']
            and candidate['build_inputs']['client_texture'].get('texture_header_struct_bytes') == 32
            and build.get('build_targets') == ['Game']
            and build.get('configuration') == 'OptDebug' and build.get('architecture') == 'Win32'
            and all(build.get(key) is False for key in ('parse6_schema_changes', 'full_texture_asset_changes',
                'graphics_profile_changes', 'gameplay_validation_changes', 'runtime_execution_validated'))
            and build.get('verified_root_environment') == 'COH_TEXTURE_HEADER_ROOT'
            and build.get('missing_texture_reporting') == {'environment_variable': 'COH_STARTUP_DIAGNOSTIC_BOUND',
                'enabled_value': '1', 'disabled_by_default': True, 'sample_limit_per_stage': 1024,
                'retained_key_limit_per_stage': 8192, 'all_validation_retained': True}
            and build.get('source_sha256') == {'Game/src/render/tex.c':
                candidate['build_inputs']['client_texture'].get('patched_sha256', {}).get('Game/src/render/tex.c')}
            and set(build.get('patched_sha256', {})) == {'Game/src/render/tex.c'}
            and set(build.get('overlay_sha256', {})) == {'Game/src/render/coh_texture_header_root.h'}
            and all(HEX64.fullmatch(str(value)) for field in ('patched_sha256', 'overlay_sha256')
                    for value in build[field].values())
            and HEX64.fullmatch(str(build.get('patch_sha256', ''))),
            'Startup client layer changed validation or native source scope')
    record = pe_record(manifest['files']['CityOfHeroes.exe'])
    require(record != candidate['files']['CityOfHeroes.exe'], 'Startup client derivative is unchanged')
    return record


def client_loading_contract(package, candidate=None):
    """Wrap the exact startup producer without rewriting its schema history."""
    candidate = embedded_receipt(package) if candidate is None else validate_receipt(candidate)
    previous = startup_bundle_client_contract(package, candidate)
    startup = package['startup_bundle_client']
    wrapper = package.get('client_loading')
    require(isinstance(wrapper, dict) and set(wrapper) == {'manifest', 'manifest_sha256',
            'base_startup_client_manifest_sha256', 'base_client_executable'}
            and wrapper['base_startup_client_manifest_sha256'] == startup['manifest_sha256']
            and wrapper['base_client_executable'] == previous,
            'Client loading must retain the exact immediate startup producer')
    manifest = wrapper['manifest']
    require(isinstance(manifest, dict) and wrapper['manifest_sha256'] == canonical_sha(manifest)
            and manifest.get('format') == 1 and manifest.get('role') == 'bounded_client_binary_loading'
            and re.fullmatch(r'[0-9a-f]{40}', str(manifest.get('repository_commit', '')))
            and manifest.get('source_commit') == SOURCE and manifest.get('data_commit') == DATA
            and manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32'
            and manifest.get('build_targets') == ['Game']
            and manifest.get('postgresql_persistence_fixture') is False
            and manifest.get('runtime_execution_validated') is False
            and manifest.get('replacement_scope') == 'CityOfHeroes.exe_only'
            and manifest.get('retained_native_dependencies_changed') is False
            and manifest.get('retained_source_inputs') == candidate['build_inputs']
            and manifest.get('schema_sources_sha256') == candidate['retained_cache']['schema_sources_sha256']
            and manifest.get('base_client_executable') == previous
            and manifest.get('cache_encoding_changed') is False
            and set(manifest.get('files', {})) == {'CityOfHeroes.exe'},
            'Client loading source, dependency or cache provenance differs')
    build = manifest.get('build_input', {})
    path = 'libs/UtilitiesLib/src/utils/textparser.c'
    copy = {'environment_variable': 'COH_CLIENT_KNOWN_STRING_COPY', 'enabled_value': '1',
        'disabled_by_default': True, 'negative_length_only': True,
        'explicit_length_secure_crt_preserved': True, 'allocation_and_free_behavior_preserved': True}
    profile = {'environment_variable': 'COH_CLIENT_BIN_PROFILE', 'enabled_value': '1',
        'disabled_by_default': True, 'record_prefix': 'COH_CLIENT_BIN_PROFILE_V1',
        'phases': ['open', 'freshness', 'decode'], 'thread_local_flags_and_counters': True,
        'stock_freshness_and_crc_preserved': True, 'clock': 'GetTickCount_unsigned_wrap'}
    require(isinstance(build, dict) and set(build) == {'format', 'role', 'source_commit',
            'base_startup_client_build_input', 'patch', 'patch_sha256', 'source_sha256',
            'patched_sha256', 'preserved_functions_sha256', 'reverse_patch_exact_base_verified',
            'known_length_copy', 'bin_profile', 'build_targets', 'configuration', 'architecture',
            'cache_encoding_changed', 'parse6_schema_changes', 'source_freshness_changed',
            'graphics_profile_changes', 'runtime_execution_validated'}
            and build.get('format') == 1 and build.get('role') == manifest['role']
            and build.get('source_commit') == SOURCE
            and build.get('base_startup_client_build_input') == startup['manifest']['build_input']
            and build.get('patch') == 'patches/client-loading/0001-known-length-string-copy-and-profile.patch'
            and HEX64.fullmatch(str(build.get('patch_sha256', '')))
            and build.get('source_sha256') == {path: manifest['schema_sources_sha256'].get(path)}
            and isinstance(build.get('patched_sha256'), dict) and set(build['patched_sha256']) == {path}
            and all(HEX64.fullmatch(str(value)) for value in build['source_sha256'].values())
            and all(HEX64.fullmatch(str(value)) for value in build['patched_sha256'].values())
            and build['patched_sha256'] != build['source_sha256']
            and manifest.get('decoder_source_sha256') == build['patched_sha256']
            and isinstance(build.get('preserved_functions_sha256'), dict)
            and set(build['preserved_functions_sha256']) == {'int ParseTableCRC(', 'int ParserReadBinaryTable(',
                'void*    StructAllocRawDbg(', 'void    StructFree(', 'void StructFreeString(',
                'static FileScanAction DateCheckCallback('}
            and all(HEX64.fullmatch(str(value)) for value in build['preserved_functions_sha256'].values())
            and build.get('reverse_patch_exact_base_verified') is True
            and build.get('known_length_copy') == copy and build.get('bin_profile') == profile
            and build.get('build_targets') == ['Game']
            and build.get('configuration') == 'OptDebug' and build.get('architecture') == 'Win32'
            and all(build.get(key) is False for key in ('cache_encoding_changed', 'parse6_schema_changes',
                'source_freshness_changed', 'graphics_profile_changes', 'runtime_execution_validated')),
            'Client loading changed encoding, freshness, memory ownership or source scope')
    checks = manifest.get('windows_qualification', {})
    require(isinstance(checks, dict) and checks.get('format') == 1 and checks.get('status') == 'passed'
            and checks.get('platform') == 'windows' and checks.get('architecture') == 'Win32'
            and checks.get('configuration') == 'OptDebug' and checks.get('build_input') == build
            and checks.get('compiler_options') == ['/O2', '/Oy-', '/MT', '/TC']
            and all(checks.get(key) is True for key in ('equivalence_verified', 'explicit_length_behavior_verified',
                'thread_local_flags_verified', 'opt_in_and_fallback_verified',
                'known_length_path_secure_crt_call_eliminated'))
            and all(HEX64.fullmatch(str(checks.get(key, ''))) for key in ('assembly_sha256', 'harness_sha256'))
            and checks.get('physical_startup_savings_validated') is False,
            'Client loading requires source-bound Win32 equivalence checks')
    benchmarks = checks.get('benchmarks')
    require(isinstance(benchmarks, list) and len(benchmarks) == 5
            and all(isinstance(row, dict) and type(row.get('length')) is int
                and row['length'] in (8, 48, 128, 512, 11999)
                and type(row.get('rounds')) is int and row['rounds'] == 5
                and all(type(row.get(key)) in (int, float) and math.isfinite(row[key]) and row[key] > 0
                    for key in ('stock_seconds', 'candidate_seconds')) for row in benchmarks)
            and sorted(row['length'] for row in benchmarks) == [8, 48, 128, 512, 11999]
            and sum(row['candidate_seconds'] for row in benchmarks if row['length'] <= 512)
                < sum(row['stock_seconds'] for row in benchmarks if row['length'] <= 512),
            'Client loading representative Win32 copy benchmark did not improve')
    record = pe_record(manifest['files']['CityOfHeroes.exe'])
    require(record != previous and record != candidate['files']['CityOfHeroes.exe'],
            'Client loading derivative is unchanged or regressed to its ancestor')
    return record


def events_progress_contract(package):
    receipt = embedded_receipt(package)
    expected = dict(receipt['retained_native_files']['game'])
    record = receipt['files']['MapServer.exe']
    expected['MapServer.exe'] = dict(record, bytes=record['size'])
    del expected['MapServer.exe']['size']
    require(package.get('files') == expected
            and package.get('postgresql_persistence_fixture') is False
            and package.get('runtime_execution_validated') is False,
            'Native candidate changed the retained DbServer or game dependency closure')
    donor = package.get('inputs', {}).get('mapserver_progress', {})
    manifest = donor.get('manifest', {})
    build = receipt['build_inputs']['character_events']
    require(manifest.get('build_role') == 'character_events' and manifest.get('build_input') == build
            and manifest.get('files', {}).get('MapServer.exe') == record
            and manifest.get('progress_contract') == build.get('progress_contract')
            and manifest.get('events_contract') == build.get('events_contract')
            and package.get('character_events_contract') == build.get('events_contract')
            and donor.get('repository_commit') == manifest.get('repository_commit') == receipt['repository_commit'],
            'Candidate native events producer differs from its source receipt')
    encoded = (json.dumps(manifest, indent=2) + '\n').encode()
    require(donor.get('manifest_sha256') == hashlib.sha256(encoded).hexdigest(),
            'Candidate MapServer producer manifest differs')
    return {'contract': build['progress_contract'], 'producer': {
        'repository_commit': receipt['repository_commit'], 'manifest_sha256': donor['manifest_sha256'],
        'mapserver_sha256': record['sha256']}}


def client_startup_followup_contract(package, candidate=None):
    """Keep accepted producers intact; only schedule stock metadata lookups."""
    candidate = embedded_receipt(package) if candidate is None else validate_receipt(candidate)
    previous = client_loading_contract(package, candidate)
    loading = package['client_loading']
    wrapper = package.get('client_startup_followup')
    require(isinstance(wrapper, dict) and set(wrapper) == {'manifest', 'manifest_sha256',
            'base_client_loading_manifest_sha256', 'base_client_executable'}
            and wrapper['base_client_loading_manifest_sha256'] == loading['manifest_sha256']
            and wrapper['base_client_executable'] == previous,
            'Startup followup must retain the exact accepted loading producer')
    manifest = wrapper['manifest']
    require(isinstance(manifest, dict) and wrapper['manifest_sha256'] == canonical_sha(manifest)
            and manifest.get('format') == 1 and manifest.get('role') == 'bounded_client_dependency_preload'
            and re.fullmatch(r'[0-9a-f]{40}', str(manifest.get('repository_commit', '')))
            and manifest.get('source_commit') == SOURCE and manifest.get('data_commit') == DATA
            and manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32'
            and manifest.get('build_targets') == ['Game'] and manifest.get('postgresql_persistence_fixture') is False
            and manifest.get('retained_native_dependencies_changed') is False
            and manifest.get('retained_source_inputs') == candidate['build_inputs']
            and manifest.get('schema_sources_sha256') == candidate['retained_cache']['schema_sources_sha256']
            and manifest.get('base_client_executable') == previous
            and manifest.get('cache_encoding_changed') is False and manifest.get('runtime_execution_validated') is False
            and manifest.get('replacement_scope') == 'CityOfHeroes.exe_only'
            and set(manifest.get('files', {})) == {'CityOfHeroes.exe'},
            'Startup followup changed its frozen native dependency closure')
    build = manifest.get('build_input', {})
    path = 'libs/UtilitiesLib/src/utils/textparser.c'
    preload = {'environment_variable': 'COH_CLIENT_DEPENDENCY_PRELOAD', 'enabled_value': '1',
        'disabled_by_default': True,
        'requests': [{'persistfile': 'bin/powers.bin', 'directory': 'defs/powers/', 'filemask': '.powers', 'requested_tree': 'Menu'},
            {'persistfile': 'bin/sequencers.bin', 'directory': 'sequencers', 'filemask': '.txt',
             'requested_tree': 'player_library/animations'}],
        'scope': 'ordinary_FolderCache_metadata_only', 'source_freshness_preserved': True,
        'crc_validation_preserved': True, 'cache_encoding_changed': False,
        'full_asset_bytes_preloaded': False, 'native_fallback_preserved': True,
        'record_prefix': 'COH_CLIENT_DEPENDENCY_PRELOAD_V1'}
    require(isinstance(build, dict) and set(build) == {'format', 'role', 'source_commit',
            'base_client_loading_build_input', 'patch', 'patch_sha256', 'source_sha256', 'patched_sha256',
            'preserved_functions_sha256', 'reverse_patch_exact_base_verified',
            'freshness_body_exact_except_preload_call', 'native_callsite_sources_sha256', 'dependency_preload', 'build_targets',
            'configuration', 'architecture', 'cache_encoding_changed', 'parse6_schema_changes',
            'source_freshness_changed', 'graphics_profile_changes', 'runtime_execution_validated'}
            and build.get('format') == 1 and build.get('role') == manifest['role']
            and build.get('source_commit') == SOURCE
            and build.get('base_client_loading_build_input') == loading['manifest']['build_input']
            and build.get('patch') == 'patches/client-startup-followup/0001-preload-power-dependency-tree.patch'
            and HEX64.fullmatch(str(build.get('patch_sha256', '')))
            and build.get('source_sha256') == loading['manifest']['decoder_source_sha256']
            and isinstance(build.get('patched_sha256'), dict) and set(build['patched_sha256']) == {path}
            and all(HEX64.fullmatch(str(value)) for value in build['patched_sha256'].values())
            and build['patched_sha256'] != build['source_sha256']
            and manifest.get('preload_source_sha256') == build['patched_sha256']
            and isinstance(build.get('preserved_functions_sha256'), dict)
            and set(build['preserved_functions_sha256']) == {'int ParseTableCRC(', 'int ParserReadBinaryTable(',
                'int ParserReadBinaryFile(', 'char* StructAllocStringLenDbg(', 'static FileScanAction DateCheckCallback(',
                'void*    StructAllocRawDbg(', 'void    StructFree(', 'void StructFreeString('}
            and all(HEX64.fullmatch(str(value)) for value in build['preserved_functions_sha256'].values())
            and build.get('reverse_patch_exact_base_verified') is True
            and build.get('freshness_body_exact_except_preload_call') is True
            and build.get('native_callsite_sources_sha256') == {'Common/entity/load_def.c': 'b0d9683471b93194cf40dfe673ca8b2948ef4ebcd05a8ec240062a6e4c3220e5', 'Common/entity/powers_load.c': 'c5b7bbf32621922a36ba097d566840bdd9d4afc692d8e3baacd0e207dc1e12b8', 'Common/seq/seqload.c': '8c2761ceeabcc564f89d943780579a4f401ffb344f9ad6e7f5e73660c2b9b60f', 'libs/UtilitiesLib/src/utils/FolderCacheNode.c': '36faafa73afd83361fb8e4f25e340961fae5fb9d33c298b1200be9a4b2a48524', 'libs/UtilitiesLib/src/utils/file.c': '8ad08c34d2fed652578e26f0ec1fab79419b40414644c6b8e1ccbc58694733e1', 'libs/UtilitiesLib/src/utils/FolderCache.c': '93aac8a9e1a59ca47ab5a067580c36f7ed884db51038577b0453756f55af1d4c'}
            and build.get('dependency_preload') == preload and build.get('build_targets') == ['Game']
            and build.get('configuration') == 'OptDebug' and build.get('architecture') == 'Win32'
            and all(build.get(key) is False for key in ('cache_encoding_changed', 'parse6_schema_changes',
                'source_freshness_changed', 'graphics_profile_changes', 'runtime_execution_validated')),
            'Startup followup changed source freshness, CRC, decoder, cache or preload scope')
    checks = manifest.get('windows_qualification', {})
    require(isinstance(checks, dict) and checks.get('format') == 1 and checks.get('status') == 'passed'
            and checks.get('platform') == 'windows' and checks.get('architecture') == 'Win32'
            and checks.get('configuration') == 'OptDebug' and checks.get('build_input') == build
            and checks.get('compiler_options') == ['/O2', '/Oy-', '/MT', '/TC']
            and all(checks.get(key) is True for key in ('equivalence_verified', 'opt_in_and_fallback_verified',
                'exact_scope_verified', 'freshness_failure_branches_verified',
                'metadata_lookup_reduction_verified', 'ordinary_source_mutation_detection_verified'))
            and HEX64.fullmatch(str(checks.get('harness_sha256', '')))
            and checks.get('individual_fallback_queries') == 4539 and checks.get('candidate_tree_requests') == 1
            and checks.get('physical_startup_savings_validated') is False,
            'Startup followup requires source-bound Win32 freshness equivalence checks')
    record = pe_record(manifest['files']['CityOfHeroes.exe'])
    require(record != previous and record != candidate['files']['CityOfHeroes.exe'],
            'Startup followup executable is unchanged or regressed')
    return record
