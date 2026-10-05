#!/usr/bin/env python3
"""Owned Atlas service and read-only proof of one graphical character save."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import time
import zipfile

import local_login_server as login
import game_device_diagnostic as device
import game_evidence as evidence
import game_map_progress as progress
import atlas_world_assets as world
import character_avatar_assets as avatar
import character_server_data_cache as server_data_cache
import server_cache_package
import native_character_events as character_events

base, game, dbserver, require = login.base, login.game, login.dbserver, login.require
PROFILE, ACCOUNT, CHARACTER = login.PROFILE, login.ACCOUNT, 'THORHERO'
POLL_SECONDS = 15
MAP_STARTUP_SECONDS = 2400
SNAPSHOT_LIMIT = 2 * 1024 * 1024
LOGOUT_RECEIPT_LIMIT = 512
LOGOUT_MAX_AGE_MS = 120000
RELOCATION_MAX_AGE_MS = 600000
SERVER_LOG_FILE_LIMIT = 16 * 1024 * 1024
SERVER_LOG_TOTAL_LIMIT = 64 * 1024 * 1024
SERVER_LOG_COUNT_LIMIT = 128
# entworldcoll.c:GroundHeight uses min(-2000, scene_info.minHeight) as a
# synthetic floor when the downward geometry query misses. Atlas also has
# real interiors below Y=0 (City Hall is around -768). Absolute altitude is
# not ground contact; reject the fallback floor while retaining the existing
# two fresh, stable native observations and the separate physical collision gate.
NATIVE_FALL_FLOOR_Y = -2000.0
FALL_FLOOR_CLEARANCE = 1.0
MANUAL_ATLAS_ENVIRONMENT = 'COH_WINE_DB_MANUAL_ATLAS'
MANUAL_ATLAS_ACK = ('COH_WINE_DB_MANUAL_ATLAS=1 active: unused Launcher connection wait skipped; '
                    'manual Atlas launch; ordinary DbServer readiness required')


def manual_atlas_wait_contract():
    return {'environment_variable': MANUAL_ATLAS_ENVIRONMENT, 'enabled_value': '1',
        'disabled_by_default': True, 'startup_acknowledgement': MANUAL_ATLAS_ACK,
        'required_native_configuration': {'start_static': 0, 'fake_auth': True,
            'auth_server_present': False, 'queue_server': False, 'use_logserver': 0,
            'launcher_count': 0, 'launchers_connecting': False,
            'COH_WINE_DB_FIXED_INPUTS': '1', 'COH_WINE_DB_LOOPBACK_ONLY': '1'},
        'activation': 'after_launcher_listener_before_connection_wait',
        'skipped_operation': 'unused_launcher_connection_wait_only',
        'original_minimum_wait_seconds': 15,
        'preserved': ['launcher_listener', 'server_auto_start', 'static_map_list_initialization',
            'remaining_db_init', 'sql_fifo_finish', 'dispatch_main_loop', 'mapserver_readiness'],
        'invalid_request': 'exit_2_before_launcher_wait', 'android_execution_validated': False}



STARTUP_BUNDLE_ROLE = 'manual_atlas_dbserver_startup_bundle'
STARTUP_BUNDLE_BASE_EXECUTABLE = {'bytes': 1663488,
    'sha256': '539afab70c6d57aef4b2230e607e218c7a77d31de7ad10ad89f0253f5c1a09d3'}
STARTUP_BUNDLE_BASE_BUILD_INPUT_SHA256 = '12f42bdb973c2f5712408f7717bee631e23c9cf73e1e38b2f2be4d2cb943a9c2'


def startup_bundle_save_contract():
    return {'provider': 'PostgreSQL', 'table_type': 'TT_SUBCONTAINER',
        'scope': 'cancelled_provisional_child_INSERT_only',
        'match': 'next_command_with_identical_table_pointer_and_SubId_is_DELETE',
        'retained': ['matched_DELETE', 'all_other_row_commands', 'all_column_updates',
            'DELETE_then_INSERT_order', 'SQL_Server_provider', 'parent_container_inserts',
            'FIFO_transaction_commit_before_completion', 'save_ACK_after_SQL_completion',
            'permanent_failure_rollback_and_exit_without_ACK'],
        'ignored_SQL_failures': False, 'UPSERT': False, 'schema_migration': False,
        'profile_reset': False, 'android_execution_validated': False}


def startup_bundle_build_input(build_input):
    """Bind the new row-emitter layer to the exact retained native ancestry."""
    require(digest_json(build_input) == STARTUP_BUNDLE_BASE_BUILD_INPUT_SHA256,
            'Startup bundle changed the retained manual Atlas build input')
    return {'format': 1, 'build_role': STARTUP_BUNDLE_ROLE,
        'source_commit': build_input['source_commit'],
        'base_startup_build_input_canonical_sha256': digest_json(build_input),
        'patch': 'patches/startup-bundle/0001-pg-cancelled-child-insert.patch',
        'patch_sha256': '36ee0b86fad6207166b6a46a6334b0e9846f90d81140fec49dc187d2fb45a600',
        'source_sha256': {'DBServer/src/container_sql.c':
            build_input['base_wine_build_input']['postgresql_build_input']['patched_sha256']['DBServer/src/container_sql.c']},
        'patched_sha256': {'DBServer/src/container_sql.c':
            '0becda9957c9cbe35b11fa28d4c62ad63af5f08faf492bd0013746dadfbec4fc'},
        'unchanged_merger_sha256': '45849f2b9c2ff92db6aadb6e6dcbcfe412b55f57971647e49dbec4ff486e307e',
        'built_target': 'DbServer', 'configuration': 'OptDebug', 'architecture': 'Win32',
        'postgresql_persistence_fixture': False, 'save_contract': startup_bundle_save_contract(),
        'runtime_validation': 'unverified'}



LEVELUP_UI_REPAIR_ROLE = 'manual_atlas_dbserver_levelup_ui_repair'
LEVELUP_UI_REPAIR_BASE_EXECUTABLE = {'bytes': 1664000, 'sha256': 'baf97a253ddccf29575801f66ef56cb7ce75f168062bb0c4ffef796b419c2029'}
LEVELUP_UI_REPAIR_BASE_BUNDLE_SHA256 = '3c8e2fb700eeb086edd96bc28fec274e0a87d44c1d033f5a3141ccbc287c850a'


def levelup_ui_repair_build_input(build_input, bundle):
    """Require the complete current read layer above both frozen save producers."""
    require(digest_json(build_input) == STARTUP_BUNDLE_BASE_BUILD_INPUT_SHA256
            and digest_json(bundle) == LEVELUP_UI_REPAIR_BASE_BUNDLE_SHA256
            and bundle == startup_bundle_build_input(build_input),
            'Level-up read repair changed its retained native ancestry')
    return {'format': 1,
 'build_role': 'manual_atlas_dbserver_levelup_ui_repair',
 'source_commit': '0b75ade0c801735e10c5798f641948a45cc50488',
 'base_startup_build_input_canonical_sha256': '12f42bdb973c2f5712408f7717bee631e23c9cf73e1e38b2f2be4d2cb943a9c2',
 'base_startup_bundle_build_input_canonical_sha256': '3c8e2fb700eeb086edd96bc28fec274e0a87d44c1d033f5a3141ccbc287c850a',
 'patch': 'patches/levelup-ui-repair/0001-pg-empty-row-witness.patch',
 'patch_sha256': 'e686142af836ffe2216e8e30ac7a170f86ef3514216b434378ac16a388b20519',
 'source_sha256': {'DBServer/src/container_sql.c': '0becda9957c9cbe35b11fa28d4c62ad63af5f08faf492bd0013746dadfbec4fc'},
 'patched_sha256': {'DBServer/src/container_sql.c': '8eaae13bf59dbee9b76ee0c3dff447eef080eb83e943f546ba0da70d0b42c295'},
 'unchanged_merger_sha256': '45849f2b9c2ff92db6aadb6e6dcbcfe412b55f57971647e49dbec4ff486e307e',
 'unchanged_fifo_sha256': '73b7f30ab56f3deb58066477ea4fb716e7c7094fda3505baede091eb7d4c04aa',
 'built_target': 'DbServer',
 'configuration': 'OptDebug',
 'architecture': 'Win32',
 'postgresql_persistence_fixture': False,
 'save_contract': {'provider': 'PostgreSQL',
                   'table_type': 'TT_SUBCONTAINER',
                   'scope': 'physical_child_row_read_witness_and_order_only',
                   'match': 'row_read_appends_no_non_default_field_compared_with_its_initial_line_count',
                   'effect': 'retain_FAKE_STR_IDX_row_witness_before_later_diff_merge',
                   'row_order': 'ORDER_BY_SubId_on_PostgreSQL_subcontainer_single_container_select_only',
                   'retained': ['non_default_column_reads',
                                'SQL_Server_provider',
                                'parent_container_read_policy',
                                'all_row_and_column_commands',
                                'cancelled_provisional_child_INSERT_filter',
                                'FIFO_transaction_commit_before_completion',
                                'save_ACK_after_SQL_completion',
                                'permanent_failure_rollback_and_exit_without_ACK'],
                   'ignored_SQL_failures': False,
                   'UPSERT': False,
                   'schema_migration': False,
                   'profile_reset': False,
                   'android_execution_validated': False},
 'runtime_validation': 'unverified'}


def install_manual_atlas_dbserver(assets, runtime, package):
    """Replace only the fresh owned DbServer after verifying its donor closure."""
    binary = assets / 'startup-dbserver.exe'
    manifest = assets / 'startup-dbserver-manifest.json'
    if not binary.exists() and not manifest.exists():
        return None
    require(binary.is_file() and not binary.is_symlink() and manifest.is_file()
            and not manifest.is_symlink(), 'Incomplete or linked manual Atlas DbServer supplement')
    value = dbserver.load_json(manifest, 2 * 1024 * 1024)
    require(value.get('format') == 1 and value.get('role') in
            ('manual_atlas_dbserver_startup_supplement', STARTUP_BUNDLE_ROLE, LEVELUP_UI_REPAIR_ROLE)
            and dbserver.COMMIT.fullmatch(value.get('repository_commit', ''))
            and value.get('source_commit') == package['source_commit']
            and value.get('base_package_manifest_sha256') == dbserver.DEVICE_PACKAGE_MANIFEST
            and value.get('replacement_scope') == 'fresh_owned_manual_atlas_runtime_DbServer.exe_only'
            and value.get('base_package_archive_changed') is False
            and value.get('architecture') == 'Win32' and value.get('configuration') == 'OptDebug'
            and value.get('postgresql_persistence_fixture') is False
            and value.get('android_execution_validated') is False and value.get('gameplay_validated') is False,
            'Manual Atlas DbServer provenance or build mode differs')
    original = package['variants']['normal']
    retained = {name: record for name, record in original['files'].items() if name != 'DbServer.exe'}
    require(value.get('retained_normal_files') == retained
            and value.get('base_normal_executable') == original['files']['DbServer.exe']
            and value.get('base_normal_cmake_cache_sha256') == original['cmake_cache_sha256'],
            'Manual Atlas DbServer changed the accepted dependency closure')
    build_input = value.get('build_input', {})
    require(build_input.get('format') == 1
            and build_input.get('build_role') == 'manual_atlas_dbserver_startup_supplement'
            and build_input.get('source_commit') == package['source_commit']
            and build_input.get('base_wine_build_input') == package['wine_build_input']
            and build_input.get('base_wine_build_input_canonical_sha256') == digest_json(package['wine_build_input'])
            and dbserver.exact_contract(build_input.get('launcher_wait'), manual_atlas_wait_contract())
            and build_input.get('built_target') == 'DbServer'
            and build_input.get('postgresql_persistence_fixture') is False,
            'Manual Atlas DbServer source or native wait contract differs')
    require(set(build_input.get('patched_sha256', {})) == {'DBServer/CMakeLists.txt', 'DBServer/src/dbinit.c'}
            and build_input.get('source_sha256') == {name: package['wine_build_input']['patched_sha256'][name]
                for name in ('DBServer/CMakeLists.txt', 'DBServer/src/dbinit.c')}
            and build_input.get('patch') == 'patches/startup-dbserver/0001-manual-atlas-launcher-wait.patch'
            and set(build_input.get('overlay_sha256', {})) == {'DBServer/src/wine_manual_atlas.c',
                                                              'DBServer/src/wine_manual_atlas.h'}
            and all(isinstance(digest, str) and re.fullmatch(r'[a-f0-9]{64}', digest)
                    for digest in [build_input.get('patch_sha256'),
                                   *build_input['patched_sha256'].values(),
                                   *build_input['overlay_sha256'].values()]),
            'Manual Atlas DbServer source hashes differ')
    if value['role'] in (STARTUP_BUNDLE_ROLE, LEVELUP_UI_REPAIR_ROLE):
        require(value.get('base_startup_executable') == STARTUP_BUNDLE_BASE_EXECUTABLE
                and dbserver.exact_contract(value.get('startup_bundle_build_input'),
                    startup_bundle_build_input(build_input)),
                'Startup bundle save layer or retained executable differs')
    else:
        require('startup_bundle_build_input' not in value,
                'Legacy manual Atlas supplement contains an unqualified save layer')
    if value['role'] == LEVELUP_UI_REPAIR_ROLE:
        require(value.get('base_startup_bundle_executable') == LEVELUP_UI_REPAIR_BASE_EXECUTABLE
                and dbserver.exact_contract(value.get('levelup_ui_repair_build_input'),
                    levelup_ui_repair_build_input(build_input, value['startup_bundle_build_input'])),
                'Level-up read repair layer or retained executable differs')
    else:
        require('levelup_ui_repair_build_input' not in value
                and 'base_startup_bundle_executable' not in value,
                'Legacy manual Atlas supplement contains an unqualified read layer')
    files = value.get('files', {})
    require(set(files) == {'DbServer.exe'}, 'Manual Atlas supplement contains another native target')
    record = files['DbServer.exe']
    require(type(record.get('bytes')) is int and 0 < record['bytes'] <= 200 * 1024 * 1024
            and binary.stat().st_size == record['bytes'] and base.file_hash(binary) == record.get('sha256')
            and record['sha256'] != original['files']['DbServer.exe']['sha256']
            and value.get('dependency_report', {}).get('unresolved') == [],
            'Manual Atlas executable bytes or imports differ')
    if value['role'] in (STARTUP_BUNDLE_ROLE, LEVELUP_UI_REPAIR_ROLE):
        require(record['sha256'] != STARTUP_BUNDLE_BASE_EXECUTABLE['sha256'],
                'Startup bundle executable is unchanged from the retained startup supplement')
    if value['role'] == LEVELUP_UI_REPAIR_ROLE:
        require(record['sha256'] != LEVELUP_UI_REPAIR_BASE_EXECUTABLE['sha256'],
                'Level-up read executable is unchanged from the retained startup bundle')
    require(set(value.get('odbc_imports', [])) >= {'SQLDriverConnect', 'SQLExecDirect', 'SQLPrepare',
            'SQLGetDiagRecA', 'SQLGetInfoW', 'SQLColumnsW', 'SQLTablesW', 'SQLForeignKeysW'}
            and not set(value['odbc_imports']).intersection({'SQLDriverConnectA', 'SQLExecDirectA',
                'SQLPrepareA', 'SQLGetInfo', 'SQLGetInfoA', 'SQLColumns', 'SQLColumnsA',
                'SQLTables', 'SQLTablesA', 'SQLForeignKeys', 'SQLForeignKeysA'}),
            'Manual Atlas executable lost accepted ODBC imports')
    base.verify_pe32(binary)
    target = runtime / 'DbServer.exe'
    require(target.is_file() and not target.is_symlink()
            and base.file_hash(target) == original['files']['DbServer.exe']['sha256'],
            'Manual Atlas replacement requires the fresh accepted DbServer')
    for name, retained_record in retained.items():
        path = runtime / name
        require(path.is_file() and not path.is_symlink() and base.file_hash(path) == retained_record['sha256'],
                'Manual Atlas retained runtime library differs: ' + name)
    shutil.copyfile(binary, target)
    require(base.file_hash(target) == record['sha256'], 'Installed manual Atlas executable differs')
    installed = {'enabled': True, 'native_ack_observed': False,
        'manifest_sha256': base.file_hash(manifest), 'executable_sha256': record['sha256'],
        'repository_commit': value['repository_commit'], 'contract': build_input['launcher_wait'],
        'base_package_archive_changed': False, 'other_native_targets_changed': False,
        'ordinary_fixed_inputs_loopback_dispatch_and_map_readiness_required': True}
    if value['role'] in (STARTUP_BUNDLE_ROLE, LEVELUP_UI_REPAIR_ROLE):
        installed['startup_bundle_save'] = value['startup_bundle_build_input']['save_contract']
        installed['startup_bundle_build_input_sha256'] = digest_json(value['startup_bundle_build_input'])
    if value['role'] == LEVELUP_UI_REPAIR_ROLE:
        installed['levelup_ui_repair_save'] = value['levelup_ui_repair_build_input']['save_contract']
        installed['levelup_ui_repair_build_input_sha256'] = digest_json(value['levelup_ui_repair_build_input'])
    return installed


def above_native_fall_floor(y):
    return NATIVE_FALL_FLOOR_Y + FALL_FLOOR_CLEARANCE < y < 10000


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read_logout_delivery(path, session, client_pid, character_id, ready_utc_ms, now_utc_ms, *,
                         action='quittologin', max_age_ms=LOGOUT_MAX_AGE_MS):
    """Read the input sender's receipt; this is not a network-packet receipt."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
                and info.st_nlink == 1 and 0 < info.st_size <= LOGOUT_RECEIPT_LIMIT,
                'Invalid character logout delivery file')
        with os.fdopen(fd, 'rb', closefd=False) as source:
            raw = source.read(LOGOUT_RECEIPT_LIMIT + 1)
        after = os.fstat(fd)
        require(len(raw) == info.st_size and len(raw) <= LOGOUT_RECEIPT_LIMIT
                and (after.st_size, after.st_mtime_ns, after.st_nlink)
                    == (info.st_size, info.st_mtime_ns, info.st_nlink),
                'Character logout delivery changed or exceeded bound')
    finally:
        os.close(fd)
    value = json.loads(raw.decode('utf-8'))
    require(isinstance(value, dict) and set(value) == {
                'format', 'session_id', 'client_pid', 'character_id', 'action', 'sent_utc_ms'}
            and type(value['format']) is int and value['format'] == 1
            and isinstance(value['session_id'], str) and re.fullmatch(r'[0-9a-f]{32}', value['session_id'])
            and value['session_id'] == session
            and type(value['client_pid']) is int and value['client_pid'] > 0 and value['client_pid'] == client_pid
            and type(value['character_id']) is int and value['character_id'] > 0
            and value['character_id'] == character_id and value['action'] == action
            and type(value['sent_utc_ms']) is int and type(ready_utc_ms) is int
            and ready_utc_ms <= value['sent_utc_ms']
            and 0 <= now_utc_ms - value['sent_utc_ms'] <= max_age_ms,
            'Character logout delivery does not match this ready client or its save window')
    return value


def native_position_records(logs):
    """Read current owned Atlas entity physics observations, including bad Y."""
    number = r'-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
    pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ PeriodicInfo pos=<('
        + number + '),(' + number + '),(' + number + r')> [^\r\n]+$')
    result = {}
    for message, record in entity_records(logs):
        match = pattern.fullmatch(message)
        if match is None:
            continue
        coordinates = [float(value) for value in match.groups()]
        require(all(math.isfinite(value) and abs(value) <= 1000000 for value in coordinates),
                'Native character position is nonfinite or out of bounds')
        utc_ms = int(time.mktime(time.strptime(record['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
        value = dict(record, position=coordinates, utc_ms=utc_ms, account=ACCOUNT, name=CHARACTER,
            source='current_owned_mapserver_periodic_entity_physics_position')
        # A local logger and embedded logserver can retain the same observation.
        # They must agree, and two routes never count as two physical samples.
        require(utc_ms not in result or result[utc_ms]['position'] == coordinates,
                'Ambiguous native character positions at one timestamp')
        result[utc_ms] = value
    return [result[key] for key in sorted(result)]


def stable_ground_evidence(logs, delivery, now_utc_ms, *, max_age_ms=180000, positions=None):
    values = [value for value in (native_position_records(logs) if positions is None else positions)
              if value['utc_ms'] >= delivery['sent_utc_ms']]
    if len(values) < 2:
        return None
    before, after = values[-2:]
    elapsed = after['utc_ms'] - before['utc_ms']
    if not (25000 <= elapsed <= 90000 and 0 <= now_utc_ms - after['utc_ms'] <= max_age_ms):
        return None
    first, last = before['position'], after['position']
    if not (all(abs(value[0]) <= 100000 and abs(value[2]) <= 100000 and above_native_fall_floor(value[1])
                for value in (first, last))
            and abs(first[1] - last[1]) <= .5
            and math.hypot(first[0] - last[0], first[2] - last[2]) <= 2):
        return None
    return {'verified': True, 'samples': [before, after], 'elapsed_ms': elapsed,
        'position': last, 'ordinary_command': 'stuck',
        'scope': 'two_current_native_physics_positions_stable_above_fall_boundary_after_ordinary_stuck',
        'full_collision_geometry_verified': False}


def logout_follows_delivery(logout, delivery):
    # The original logger uses FileTimeToLocalFileTime and one-second precision.
    try:
        timestamp = int(time.mktime(time.strptime(logout['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
    except (KeyError, OverflowError, ValueError):
        return False
    return -999 <= timestamp - delivery['sent_utc_ms'] <= LOGOUT_MAX_AGE_MS


def entity_records(logs):
    """Yield IMPORTANT records from the two stock owned-server log routes.

    The embedded DbServer log server adds the Atlas map instance/host/DbServer
    prefix. If its connection fails, UtilitiesLib writes locally with level 0.
    """
    pattern = re.compile(r'^(?P<timestamp>\d{6} \d{2}:\d{2}:\d{2}) '
        r'(?:(?P<local_level>0)|(?P<map_instance>(?i:City_01_01)_1):127\.0\.0\.1:127\.0\.0\.1) +'
        r'(?P<message>[^\r\n]+)$')
    for name, text in logs:
        path = Path(name)
        if path.parent == Path('logs/mapserver') and path.name == 'entity.log':
            route = 'local_mapserver'
        elif (path.parent == Path('logs/dbserver')
                and re.fullmatch(r'entity_[0-9][0-9_-]*\.log', path.name)):
            route = 'embedded_dbserver_logserver'
        else:
            continue
        for line in text[:text.rfind('\n') + 1].splitlines():
            match = pattern.fullmatch(line)
            if match is None or (match['local_level'] is not None) != (route == 'local_mapserver'):
                continue
            yield match['message'], {'path': name, 'line_sha256': hashlib.sha256(line.encode()).hexdigest(),
                'log_timestamp': match['timestamp'], 'log_route': route,
                'map_instance': match['map_instance']}


def logout_record(logs):
    """Record the owned entity's live logout timer, not its underlying cause.

    A normal CLIENT_DISCONNECT and a still-linked stalled client can both take
    this timer path. Explicit command delivery must be bound separately.
    """
    pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ \[Disconnect:Logout timer expired\] [^\r\n]+$')
    for message, record in entity_records(logs):
        if pattern.fullmatch(message):
            return dict(record, reason='Logout timer expired', account=ACCOUNT, name=CHARACTER,
                source='current_owned_server_entity_log_live_client_logout_timer')
    return None


def native_reward_credit_evidence(logs, proof, delivery, logout, *, session, client_pid, now_utc_ms):
    """Bind exact stock point credits to the already validated owned connection.

    Native reward lines have neither a character DB ID nor a session/PID. Their
    THORHERO:COHLOCAL identity and owned Atlas route are bound through the prior
    reopen/ready proof. This reads evidence only; it never awards game points.
    """
    import stationary_contact_evidence as contact
    import task_gate_evidence as task
    identity = contact.binding(proof, session, client_pid, now_utc_ms)
    if (identity is None or type(delivery) is not dict
            or delivery.get('session_id') != session or delivery.get('client_pid') != client_pid
            or type(delivery.get('client_pid')) is not int or delivery.get('character_id') != 1
            or type(delivery.get('character_id')) is not int or delivery.get('action') != 'quittologin'
            or type(delivery.get('sent_utc_ms')) is not int
            or not identity['client_ready_observed_utc_ms'] <= delivery['sent_utc_ms'] <= now_utc_ms
            or logout is None or not logout_follows_delivery(logout, delivery)):
        return None
    try:
        end_ms = int(time.mktime(time.strptime(logout['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
    except (KeyError, ValueError, OverflowError):
        return None
    ready_ms = identity['client_ready_observed_utc_ms']
    if not ready_ms <= end_ms <= now_utc_ms:
        return None
    values = task.records(logs, ready_ms, end_ms)
    if values is None:
        return None  # An over-bound/truncated inventory is never credit proof.
    credits = [value for value in values if value['kind'] == 'reward']
    # The retained task parser deduplicates logger routes. For point changes,
    # refuse repeated positive credits instead of guessing whether two identical
    # records represent one mirrored award or two real awards in one second.
    route_pattern = re.compile(r'^(?P<timestamp>\d{6} \d{2}:\d{2}:\d{2}) '
        r'(?:(?P<local_level>[02])|(?P<map_instance>(?i:City_01_01)_1):127\.0\.0\.1:127\.0\.0\.1) +'
        r'(?P<message>[^\r\n]+)$')
    seen, candidate_count = set(), 0
    for name, text in logs:
        path = Path(name)
        local = path.parent == Path('logs/mapserver') and path.name == 'rewards.log'
        embedded = (path.parent == Path('logs/dbserver')
            and re.fullmatch(r'rewards_[0-9][0-9_-]*\.log', path.name))
        if not local and not embedded:
            continue
        tail = text[text.rfind('\n') + 1:]
        if re.search(r'"THORHERO:COHLOCAL" -?\d+ \[Tbl\]:Rcv:Points(?: |$)', tail):
            return None  # A pending award line is not a complete credit inventory.
        for line in text[:text.rfind('\n') + 1].splitlines():
            parsed = route_pattern.fullmatch(line)
            if parsed is None or (parsed['local_level'] is not None) != local:
                continue
            message = parsed['message']
            if not re.match(contact.PREFIX + r'\[Tbl\]:Rcv:Points(?: |$)', message):
                continue
            try:
                stamp = int(time.mktime(time.strptime(parsed['timestamp'], '%y%m%d %H:%M:%S')) * 1000)
            except (ValueError, OverflowError):
                return None
            if not ready_ms <= stamp <= end_ms:
                continue
            candidate_count += 1
            match = task.PATTERNS['reward'].fullmatch(message)
            if (candidate_count > task.RECORD_LIMIT or match is None or len(message) > 2048
                    or parsed['local_level'] == '2'
                    or task._int(int(match['teamup']), -0x80000000) is None):
                return None
            if int(match['xp']) or int(match['influence']):
                key = (stamp, message)
                if key in seen:
                    return None
                seen.add(key)
    xp, influence = 0, 0
    positive = []
    for credit in credits:
        fields = credit['fields']
        points = {key: task._int(int(fields[key]))
                  for key in ('xp', 'influence', 'debt', 'prestige', 'supergroup')}
        if any(value is None for value in points.values()) or any(
                points[key] != 0 for key in ('debt', 'prestige', 'supergroup')):
            return None
        xp += points['xp']; influence += points['influence']
        if xp > 0x7fffffff or influence > 0x7fffffff:
            return None
        if points['xp'] or points['influence']:
            positive.append(credit)
    if not positive or len(positive) != len(seen):
        return None  # No native award permits no reward-field serialization drift.
    return {'format': 1, 'verified': True,
        'scope': 'owned_atlas_exact_native_point_credits_before_ordinary_logout',
        'connection': identity, 'ready_utc_ms': ready_ms, 'logout_utc_ms': end_ms,
        'logout_timer_evidence': logout, 'logout_delivery': delivery,
        'native_log_timestamp_precision_ms': 1000,
        'duplicate_positive_credit_policy': 'reject_even_mirrored_logger_routes',
        'record_limit': task.RECORD_LIMIT, 'candidate_count': candidate_count,
        'parsed_reward_count': len(credits), 'positive_credit_count': len(positive),
        'experiencepoints_delta': xp, 'influencepoints_delta': influence,
        'records': credits, 'sql_game_mutations_performed': False,
        'combat_defeat_verified': False, 'reward_source_classification_verified': False}


def native_logout_position(logs, delivery, ready_utc_ms, now_utc_ms):
    """Read the terminal position paired with this ordinary logout timer.

    The stock 30-second PeriodicInfo observation can precede the player's last
    movement. The stock logout location instead records the entity being saved.
    Keep the same owned routes/identity and require the timer and location in
    order in one route at the same native timestamp. Duplicate logger routes
    must agree; this observation alone never proves SQL commit or connection.
    """
    number = character_events.NUMBER
    timer_pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ '
        r'\[Disconnect:Logout timer expired\] [^\r\n]+$')
    position_pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ '
        r'Logout location : map (?P<map_id>[1-9][0-9]*) '
        r'\((?P<x>' + number + r') (?P<y>' + number + r') (?P<z>' + number + r')\) [^\r\n]+$')
    observations = []
    for path, text in logs:
        timer = None
        for message, route in entity_records([(path, text)]):
            if timer_pattern.fullmatch(message):
                timer = route
                continue
            match = position_pattern.fullmatch(message)
            if match is None or timer is None or match['map_id'] != '1':
                continue
            if route['log_timestamp'] != timer['log_timestamp']:
                continue
            utc_ms = int(time.mktime(time.strptime(route['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
            if not (ready_utc_ms <= utc_ms <= now_utc_ms
                    and -999 <= utc_ms - delivery['sent_utc_ms'] <= LOGOUT_MAX_AGE_MS):
                continue
            coordinates = [float(match[key]) for key in ('x', 'y', 'z')]
            require(all(math.isfinite(value) and abs(value) <= 1000000 for value in coordinates)
                    and above_native_fall_floor(coordinates[1]),
                    'Native logout position is nonfinite, out of bounds or at the fall floor')
            observations.append(dict(route, utc_ms=utc_ms, position=coordinates,
                map_id=1, account=ACCOUNT, name=CHARACTER, logout_timer_evidence=timer,
                source='current_owned_server_entity_log_ordinary_logout_position'))
    if not observations:
        return None
    first = observations[0]
    require(all(value['utc_ms'] == first['utc_ms'] and value['position'] == first['position']
                for value in observations), 'Ambiguous native character logout positions')
    return first


def ready_record(logs):
    """CLIENT_READY runs after the graphical client loads its world assets.

    The earlier DbServer connected flag only records map assignment. This
    current-session marker is emitted after resumeCharacter accepts CLIENT_READY.
    """
    pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ Connection:ResumeCharacter from '
        r'127\.0\.0\.1:(?P<port>[1-9][0-9]{0,4}) AuthName "COHLOCAL"(?: [^\r\n]*)?$')
    for message, record in entity_records(logs):
        match = pattern.fullmatch(message)
        if match and int(match['port']) <= 65535:
            return dict(record, account=ACCOUNT, name=CHARACTER,
                source='current_owned_mapserver_CLIENT_READY_resumeCharacter_success', loaded_world_assets=True)
    return None


def validate_character_rows(rows, baseline, inventory, attributes, auth_id, *,
                            existing_identity=None, expected_login_count=1):
    """Reject provisional rows and bind every child to the observed player."""
    require(isinstance(rows, dict) and set(rows) == set(evidence.SELECTED), 'Character snapshot tables differ')
    evidence.validate_attributes(attributes)
    require(type(auth_id) is int and auth_id > 0, 'Character account identity is missing')
    parents = rows['ents']
    if not parents: return None
    require(len(parents) == 1, 'Character name is ambiguous')
    parent = parents[0]
    identifier = parent.get('containerid')
    require(type(identifier) is int and identifier > 0, 'Character ID is invalid')
    if existing_identity is None:
        require(identifier not in {r['containerid'] for r in baseline},
                'Character was present before this graphical session')
    else:
        require(evidence._same({key: parent[key] for key in evidence.IDENTITY_FIELDS}, existing_identity)
                and sum(evidence._same(row, existing_identity) for row in baseline) == 1,
                'Existing character identity differs from the preserved baseline')
    require(parent.get('name') == CHARACTER and parent.get('authname') == ACCOUNT
            and parent.get('authid') == auth_id, 'Character/account SQL identity differs')
    if not parent.get('class') or not parent.get('origin') or not parent.get('logincount'):
        return None
    require(type(expected_login_count) is int and 0 < expected_login_count < 2**31
            and type(parent['logincount']) is int and parent['logincount'] == expected_login_count,
            'Character LoginCount differs from the required graphical session')
    known = {row['id'] for row in attributes['attributes']}
    for table, selected in evidence.SELECTED.items():
        fields = set(selected) | ({'logincount'} if table == 'ents' else set())
        values = rows[table]
        if not values: return None
        require(isinstance(values, list) and all(isinstance(row, dict) and set(row) == fields for row in values),
                'Character snapshot fields differ: ' + table)
        require(all(type(row['containerid']) is int and row['containerid'] == identifier for row in values),
                'Character child references another parent: ' + table)
        if table in ('ents', 'ents2'):
            require(len(values) == 1, 'Expected one character parent/extension row')
        if table != 'ents':
            keys = [row['subid'] for row in values]
            require(all(type(key) is int and key >= 0 for key in keys) and keys == sorted(set(keys)),
                    'Duplicate, unordered or invalid character child keys')
            require(table != 'ents2' or keys == [0], 'Character extension must have subid zero')
        for row in values:
            for field in evidence.ATTRIBUTE_FIELDS.get(table, ()):
                value = row[field]
                require((table == 'costumeparts' and (value is None or type(value) is int and value == 0))
                        or type(value) is int and value > 0 and value in known,
                        'Character attribute is absent from the accepted mapping: ' + table + '.' + field)
    new_identity = {key: parent[key] for key in evidence.IDENTITY_FIELDS}
    if existing_identity is None:
        current = [row for row in inventory if row['containerid'] != identifier]
        require(current == baseline and inventory == sorted(baseline + [new_identity], key=lambda r: r['containerid']),
                'Existing character identities changed or unexpected characters were created')
    else:
        require(evidence._same(inventory, baseline),
                'Character inventory changed while reopening the preserved character')
    return {'identity': new_identity, 'login_count': expected_login_count, 'rows': rows}


class LocalCharacterServer(login.LocalLoginServer):
    require_empty_account = False
    REPORT_KEY = 'character_creation'
    def __init__(self, owner):
        super().__init__(owner)
        self.map_process = None
        self.map_previous = None
        self.map_progress_next = 0
        self.character_next = 0
        self.query_count = 0
        self.baseline = None
        self.snapshot = None
        self.auth_id = None
        self.manual_atlas_startup = None
        self.creation_report = {'session_id': owner.args.session_id, 'account': ACCOUNT,
            'name': CHARACTER, 'map_id': 1, 'verified': False, 'connected_on_atlas': False,
            'committed_sql_verified': False, 'requested_logout_observed': False, 'logout_timer_observed': False,
            'disconnected_before_sql': False, 'forced_stop_before_save': False,
            'reopen_verified': False, 'gameplay_verified': False, 'map_samples': [], 'character_samples': []}
        self.ctx.report[self.REPORT_KEY] = self.creation_report

    def payloads(self):
        super().payloads()
        archive = self.owner.args.assets / 'game-package.tar.gz'
        receipt_path = self.owner.args.assets / 'native-responsiveness.json'
        candidate_receipt = dbserver.load_json(receipt_path, 4 * 1024 * 1024) if receipt_path.exists() else None
        payload_key = base.file_hash(archive) if candidate_receipt is not None else device.MAP_PROGRESS_PACKAGE_SHA256
        destination = self.owner.root / ('character-map-payload-' + payload_key[:16])
        require(not destination.is_symlink(), 'Linked Atlas payload refused')
        if not destination.exists():
            pending = self.owner.root / ('character-map-pending-' + base.secrets.token_hex(8))
            try:
                login.extract_regular(archive, pending)
                self.verify_map_payload(pending, candidate_receipt)
                pending.rename(destination)
            finally:
                if pending.exists(): shutil.rmtree(pending)
        self.map_package = self.verify_map_payload(destination, candidate_receipt)
        self.map_package_dir = destination
        self.map_manifest_sha256 = base.file_hash(destination / 'game-package.json')
        self.map_contract = game.mapserver_progress_contract(self.map_package)
        self.creation_report['mapserver_producer'] = self.map_contract['producer']

    @staticmethod
    def verify_map_payload(directory, candidate_receipt=None):
        path = directory / 'game-package.json'
        require(path.is_file() and not path.is_symlink(), 'Missing or linked Atlas package receipt')
        package = dbserver.load_json(path)
        candidate = 'native_responsiveness' in package
        if candidate:
            import native_responsiveness_contract as native_candidate
            require(candidate_receipt is not None
                    and native_candidate.embedded_receipt(package) == native_candidate.validate_receipt(candidate_receipt),
                    'Atlas candidate differs from the installed source receipt')
        else:
            require(candidate_receipt is None and base.file_hash(path) == device.MAP_PROGRESS_PACKAGE_SHA256
                    and package.get('repository_commit') == device.MAP_PROGRESS_COMMIT,
                    'Atlas package differs from the device-qualified progress donor')
        require(package.get('source_commit') == device.SOURCE_COMMIT
                and package.get('data_commit') == device.DATA_COMMIT
                and package.get('postgresql_persistence_fixture') is False,
                'Atlas package provenance or fixture mode differs')
        dbserver.verify_inventory(directory, package['files'], manifest='game-package.json', binary=True)
        game.game_loopback_contract(package)
        game.game_listener_contract(package)
        contract = game.mapserver_progress_contract(package)
        require(candidate or contract['producer'] == device.MAP_PROGRESS_PRODUCER, 'Atlas progress producer differs')
        for name in package['files']: base.verify_pe32(directory / name)
        return package

    def prepare_runtime(self):
        prepared_at = time.monotonic()
        super().prepare_runtime()
        source = self.owner.work / 'data'
        require(source.is_dir() and not source.is_symlink(), 'Verified private client data is missing')
        receipt = self.ctx.report.get('client_worktree', {})
        require(receipt.get('imported_inputs_readonly') is True,
                'Atlas requires the already protected private client worktree')
        # Wine FolderCache does not enumerate directory symlinks as directories.
        # Mirror actual directories as the accepted client worktree does, then
        # link individual immutable files. Keep caches/configuration private.
        source_info = source.stat()
        identity = {'format': 2, 'source_data': str(source.resolve(strict=True)),
            'source_device': source_info.st_dev, 'source_inode': source_info.st_ino,
            'source_roots': [{'path': str(root.resolve(strict=True)),
                              'identity': server_data_cache.fingerprint(root.resolve(strict=True), directory=True)}
                             for root in (self.owner.work, self.owner.args.game_data)],
            'client_inputs': {key: receipt[key] for key in ('import', 'cache_archive_sha256',
                'prerequisites_archive_sha256', 'prerequisites_manifest_sha256', 'normalized_mtime_epoch')},
            'world_manifest_sha256': world.MANIFEST_SHA256, 'world_archive_sha256': world.ARCHIVE_SHA256,
            'avatar_manifest_sha256': avatar.MANIFEST_SHA256, 'avatar_archive_sha256': avatar.ARCHIVE_SHA256,
            'schema_manifest_sha256': dbserver.DEVICE_SCHEMA_MANIFEST,
            'server_cache_compatibility_sha256': hashlib.sha256(
                server_data_cache.canonical(server_cache_package.compatibility_identity())).hexdigest(),
            'native_closure_sha256': hashlib.sha256(server_data_cache.canonical({
                'source_commit': self.map_package.get('source_commit', device.SOURCE_COMMIT),
                'data_commit': self.map_package.get('data_commit', device.DATA_COMMIT),
                'files': self.map_package['files']})).hexdigest()}
        self.data_cache = server_data_cache.ServerDataCache(self.owner.root, identity,
            self.owner.args.session_id, self.ctx,
            legacy_identity_validator=lambda old: self.legacy_data_identity_matches(old, identity, receipt))
        if self.data_cache.checkout(self.runtime / 'data'):
            for name in self.schema['files']:
                server_data_cache.ServerDataCache.restore_schema(self.schema_dir / name,
                                                                  self.runtime / name, self.runtime)
            staged = dict(self.data_cache.record['stats'], linked_immutable_files=0,
                          copied_private_files=0, preserved_schema_files=len(self.schema['files']))
        else:
            staged = self.stage_map_data(source, self.runtime / 'data', cache_recorder=self.data_cache)
            self.data_cache.seal(self.runtime / 'data', staged)
        for name, record in self.map_package['files'].items():
            target = self.runtime / name
            if target.exists():
                require(not target.is_symlink() and base.file_hash(target) == record['sha256'],
                        'Atlas and local DbServer dependency closures differ: ' + name)
            else:
                shutil.copyfile(self.map_package_dir / name, target)
                target.chmod(0o400)
        self.manual_atlas_startup = install_manual_atlas_dbserver(self.owner.args.assets, self.runtime, self.package)
        if self.manual_atlas_startup is not None:
            self.creation_report['manual_atlas_startup'] = self.manual_atlas_startup
        try:
            donor_identity = server_cache_package.build_expected_identity(self.runtime / 'data',
                                                                          self.runtime / 'MapServer.exe')
            self.creation_report['prepared_server_caches'] = server_cache_package.install(
                self.owner.args.assets / server_cache_package.ARCHIVE, self.runtime / 'data',
                donor_identity, context=self.ctx)
        except (ValueError, OSError) as failure:
            # Derived caches are optional. Exact native/source mismatches leave
            # existing generated bins and the ordinary loader fully in charge.
            self.creation_report['prepared_server_caches'] = {'format': 1,
                'status': 'skipped_native_fallback', 'reason': str(failure)[:300], 'installed_files': 0}
        # The stock Pig reader can consume unchanged animation bytes without
        # moving or invalidating the preserved server data/cache generation.
        # An invalid present package fails preparation; never launch a bad pig.
        animation = self.owner.args.assets / 'server-animations.pigg'
        animation_manifest = self.owner.args.assets / 'server-animation-manifest.json'
        if animation.exists() or animation_manifest.exists():
            import server_animation_package
            installed = server_animation_package.install(animation, animation_manifest,
                self.runtime, context=self.ctx)
            self.creation_report['server_animation_pack'] = installed
            self.ctx.report['server_animation_pack'] = installed
        self.creation_report['private_map_data'] = {'source_worktree': self.owner.work.name,
            'imported_inputs_readonly': True, 'private_server_config': True,
            'private_cache_roots': ['bin', 'geobin', 'server/bin'],
            'directory_layout': 'real_directories_with_individual_immutable_file_links',
            'preparation_elapsed_seconds': round(time.monotonic() - prepared_at, 6),
            'server_data_cache': self.data_cache.summary, **staged}

    def dbserver_environment(self, environment):
        environment = super().dbserver_environment(environment)
        if self.manual_atlas_startup is not None:
            environment[MANUAL_ATLAS_ENVIRONMENT] = '1'
        return environment

    def dbserver_startup_policy_ready(self, console):
        if self.manual_atlas_startup is None:
            return True
        complete_lines = console[:console.rfind('\n') + 1].splitlines()
        count = complete_lines.count(MANUAL_ATLAS_ACK)
        require(count <= 1, 'Repeated manual Atlas native acknowledgement')
        require('Waiting for launchers to link up...' not in console,
                'Manual Atlas DbServer entered the unused Launcher wait')
        self.manual_atlas_startup['native_ack_observed'] = count == 1
        return count == 1

    def legacy_data_identity_matches(self, previous, current, receipt):
        """Qualify wrapper-only legacy keys without moving their source root.

        A legacy key contained the complete client/MapServer wrapper receipts.
        Bind its old client receipt to the fully checked worktree lineage, and
        prove the old native closure rather than trusting wrapper equivalence.
        The cache's normal closed-owner/immutable/private checks run afterward.
        """
        if not isinstance(previous, dict):
            return False
        added = {'native_closure_sha256', 'server_cache_compatibility_sha256'}
        expected = set(current) - added
        expected.update(('client_work_receipt_sha256', 'map_manifest_sha256'))
        if set(previous) != expected or type(previous.get('format')) is not int or previous['format'] != 1:
            return False
        if any(previous.get(key) != value for key, value in current.items()
               if key not in added | {'format'}):
            return False
        known = receipt.get('verified_legacy_receipts', [])
        if not isinstance(known, list) or len(known) > 16 or any(
                not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value) for value in known):
            return False
        known = set(known) | {base.file_hash(self.owner.work / 'client-work.json')}
        if previous.get('client_work_receipt_sha256') not in known:
            return False
        old_manifest = previous.get('map_manifest_sha256')
        if not isinstance(old_manifest, str) or not re.fullmatch('[0-9a-f]{64}', old_manifest):
            return False
        if old_manifest == getattr(self, 'map_manifest_sha256', device.MAP_PROGRESS_PACKAGE_SHA256):
            return True  # The current payload has already passed its full pins.
        candidates = []
        for path in self.owner.root.iterdir():
            if re.fullmatch('character-map-payload-[0-9a-f]{16}', path.name):
                candidates.append(path)
                if len(candidates) > 16:
                    return False
        for path in candidates:
            self.ctx.check()
            try:
                if server_data_cache.fingerprint(path, directory=True)['uid'] != self.owner.root.stat().st_uid:
                    continue
                marker = path / 'game-package.json'
                if server_data_cache.fingerprint(marker)['bytes'] > 4 * 1024**2 or base.file_hash(marker) != old_manifest:
                    continue
                package = dbserver.load_json(marker, 4 * 1024**2)
                native = {'source_commit': package.get('source_commit'),
                          'data_commit': package.get('data_commit'), 'files': package.get('files')}
                if hashlib.sha256(server_data_cache.canonical(native)).hexdigest() != current['native_closure_sha256']:
                    continue
                dbserver.verify_inventory(path, package['files'], manifest='game-package.json', binary=True)
                return True
            except base.Cancelled:
                raise
            except (base.DiagnosticError, OSError, ValueError, TypeError, KeyError):
                continue
        return False

    def cleanup_config(self):
        super().cleanup_config()
        if hasattr(self, 'data_cache'):
            self.data_cache.release(self.runtime / 'data', self.owner.cleanup_status)

    def copy_private_data(self, source, target):
        return self.stage_map_data(source, target, force_private=True)

    def stage_map_data(self, source, target, *, force_private=False, cache_recorder=None):
        """Mirror bounded verified inputs without directory links or source writes.

        The client worktree has real directories and immutable per-file links.
        Resolve those links only within its two verified roots; each writable
        cache, server file and dbidmap receives an independent regular copy.
        """
        roots = (self.owner.work.resolve(strict=True), self.owner.args.game_data.resolve(strict=True))
        source, target = Path(source), Path(target)
        # Imported inputs and generated caches retain their accepted allowance.
        # The verified missing-only supplements are additional immutable files,
        # not generated cache entries; budget their exact pinned inventories too.
        import client_visual_assets as visual
        max_files = device.DATA_COUNT + 4096 + world.FILE_COUNT + len(avatar.ALLOWED) + visual.FILE_COUNT
        max_bytes = device.DATA_BYTES + 1024**3 + world.PAYLOAD_BYTES + avatar.PAYLOAD_BYTES + visual.PAYLOAD_BYTES
        result = {'files': 0, 'bytes': 0, 'directories': 0, 'linked_immutable_files': 0,
                  'copied_private_files': 0, 'preserved_schema_files': 0}
        pending = [(source, target)]
        next_message = time.monotonic() + 5
        while pending:
            self.ctx.check()
            current, destination = pending.pop()
            require(not destination.is_symlink(), 'Linked private destination refused')
            info = current.lstat()
            relative = current.relative_to(source)
            private = force_private or bool(relative.parts and relative.parts[0] in ('server', 'bin', 'geobin'))
            if stat.S_ISDIR(info.st_mode):
                resolved = current.resolve(strict=True)
                require(any(root == resolved or root in resolved.parents for root in roots),
                        'Map data directory escaped verified roots')
                require(not destination.exists() or destination.is_dir(), 'Invalid private data directory')
                destination.mkdir(parents=True, exist_ok=True, mode=0o700)
                if cache_recorder is not None:
                    cache_recorder.observe(relative, destination, None, private)
                result['directories'] += 1
                require(result['directories'] <= max_files, 'Map directory count exceeded bound')
                with os.scandir(current) as entries:
                    pending.extend((Path(entry.path), destination / entry.name) for entry in entries)
            else:
                require(stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode), 'Nonregular map input refused')
                resolved = current.resolve(strict=True)
                resolved_info = resolved.stat()
                require(any(root == resolved or root in resolved.parents for root in roots)
                        and stat.S_ISREG(resolved_info.st_mode), 'Private map copy escaped verified data roots')
                result['files'] += 1; result['bytes'] += resolved_info.st_size
                # Include accepted prerequisites/prepared caches and bounded
                # generated client caches in addition to the imported inputs.
                require(result['files'] <= max_files and result['bytes'] <= max_bytes,
                        'Private map data exceeded bound: files=' + str(result['files']) + '/' + str(max_files)
                        + ', bytes=' + str(result['bytes']) + '/' + str(max_bytes))
                private = private or current.suffix.casefold() == '.dbidmap' or bool(resolved_info.st_mode & 0o222)
                if cache_recorder is not None:
                    cache_recorder.observe(relative, destination, resolved, private)
                if destination.exists():
                    require(destination.is_file(), 'Invalid staged schema file')
                    require(private or base.file_hash(destination) == base.file_hash(resolved),
                            'Immutable map input conflicts with staged schema')
                    result['preserved_schema_files'] += 1
                elif private:
                    shutil.copyfile(resolved, destination)
                    destination.chmod(0o600)
                    os.utime(destination, ns=(resolved_info.st_atime_ns, resolved_info.st_mtime_ns))
                    result['copied_private_files'] += 1
                else:
                    destination.symlink_to(resolved)
                    result['linked_immutable_files'] += 1
            if time.monotonic() >= next_message:
                self.ctx.event('stage', status='running', message='Preparing Atlas data directories', files=result['files'])
                next_message = time.monotonic() + 5
        return result

    def start(self):
        super().start()
        self.capture_baseline()
        self.start_map()

    def capture_baseline(self):
        self.baseline = self.inventory()
        require(not any(row['name'].casefold() == CHARACTER.casefold() for row in self.baseline),
                'THORHERO already exists; it was preserved. Export this report instead of deleting it.')
        self.creation_report.update(baseline_character_count=len(self.baseline),
                                    baseline_identity_sha256=digest_json(self.baseline))

    def start_map(self):
        self.ctx.stage('local_atlas_startup')
        game.check_game_port(7001, socket.SOCK_DGRAM)
        baseline = evidence.parse_map_status(self.query(['-getstatus', '1', '1'], 'atlas-baseline'), allow_missing=True)
        require(not baseline.get('ready'), 'Atlas was already running before this owned launch')
        self.map_progress_path = self.runtime / 'character-atlas-progress.bin'
        require(not self.map_progress_path.exists(), 'Stale Atlas progress file')
        environment = dict(self.owner.wine_env, **{evidence.GAME_LOOPBACK_ENV: '1',
            progress.ENVIRONMENT: base.windows_path(self.map_progress_path)})
        event_contract = self.immediate_event_contract()
        if event_contract is not None:
            character_events.validate_contract(event_contract)
            environment[character_events.ENVIRONMENT] = self.owner.args.session_id
            self.creation_report['immediate_native_events'] = {'enabled': True,
                'contract': event_contract, 'legacy_sorted_logs_used_for_ready_or_ground': False}
        self.map_launch_utc_ms = int(time.time() * 1000)
        self.map_process = self.ctx.start('local-character-atlas', ['/usr/bin/env', '--chdir=' + str(self.runtime),
            self.owner.args.wine, base.windows_path(self.runtime / 'MapServer.exe'),
            '-nogui', '-db', '127.0.0.1', '-nosharedmemory', '-nostats', '-udp', '7001', '-tcp', '0', '-map_id', '1',
            '-donotautogroup'],
            env=environment)
        # Use the native production grouping policy. The stock world packet
        # delivers this same flag to the client before it loads Atlas; geometry,
        # collision initialization and CLIENT_READY validation remain required.
        self.creation_report['map_autogroup_policy'] = {'native_option': '-donotautogroup',
            'configured_do_not_auto_group': True, 'policy_basis': 'native_production_default'}
        self.report['mapserver_started'] = self.ctx.report['mapserver_started'] = True
        deadline = min(self.ctx.deadline, time.monotonic() + MAP_STARTUP_SECONDS)
        next_query = next_message = 0
        while True:
            self.ctx.check(); self.health()
            now = time.monotonic()
            require(now < deadline, 'Atlas startup timed out; export this report without another boot')
            self.sample_progress()
            bindings = evidence.game_listener_bindings(self.map_process.text(), 'atlas', pending=True)
            if bindings and now >= next_query:
                next_query = now + 60
                before = self.sample_progress(force=True)
                if not self.live_progress(before):
                    next_query = now + 5
                    continue
                sample = evidence.parse_map_status(self.query(['-getstatus', '1', '1'], 'atlas-ready'))
                after = self.sample_progress(force=True)
                guard = {'before': before, 'after': after, 'protocol': sample,
                         'requires_completed_tick_before_protocol': True}
                self.creation_report['map_startup_guard'] = guard
                self.creation_report['map_samples'].append(sample)
                if self.live_progress(after) and evidence.map_ready_current(sample):
                    progress.compare_records(after, before)
                    guard['passed'] = True
                    self.creation_report.update(map_ready=True, map_listener=bindings)
                    self.ctx.passed(atlas_ready=True, map=sample, loopback_only=True)
                    return
            if now >= next_message:
                self.ctx.event('stage', status='running', message='Preparing Atlas Park for the character session')
                next_message = now + 5
            time.sleep(.2)

    @staticmethod
    def live_progress(value):
        return (isinstance(value, dict) and value.get('available') is True
                and type(value.get('tick_completed')) is int and value['tick_completed'] > 0
                and type(value.get('unchanged_seconds')) in (int, float) and value['unchanged_seconds'] <= 20)

    def sample_progress(self, *, force=False):
        now = time.monotonic()
        if not force and now < self.map_progress_next or self.map_process is None: return None
        self.map_progress_next = now + 5
        try:
            self.map_previous = progress.read_record(self.map_progress_path, self.map_previous)
            self.creation_report['map_progress_latest'] = self.map_previous
            return self.map_previous
        except (FileNotFoundError, progress.PublicationPending):
            return

    def health(self):
        super().health()
        if self.map_process is not None:
            console = self.map_process.text()
            crash = re.search(r'Program crash detected|Exception caught: EXCEPTION_[A-Z_]+', console)
            if crash is not None:
                self.creation_report['mapserver_crash'] = {
                    'marker': crash.group(), 'console_offset': crash.start(),
                    'context': console[max(0, crash.start() - 1000):crash.end() + 1000],
                    'console_sha256': hashlib.sha256(console.encode()).hexdigest()}
                require(False, 'Atlas crashed: ' + crash.group() + '; export the server console and report')
            require(self.map_process.process.poll() is None, 'Atlas exited during character creation')
            require(not self.map_process.overflow, 'Atlas console exceeded capture bound')

    def query(self, arguments, label):
        self.query_count += 1
        require(self.query_count <= 160, 'Character protocol query budget exceeded')
        result = self.ctx.run('character-' + label, ['/usr/bin/env', '--chdir=' + str(self.runtime),
            self.owner.args.wine, base.windows_path(self.runtime / 'MapServer.exe'), '-nogui',
            '-db', '127.0.0.1', '-dbquery', '-timeout', '10000', *arguments],
            timeout=90, env=self.owner.wine_env)
        require(result['exit_code'] == 0, 'Character protocol query failed')
        return self.ctx.children[-1].text()

    def sql_rows(self, table, fields, keys, where='TRUE'):
        require(table in self.schema['expected_tables'] and all(field in self.schema['expected_tables'][table]
                and dbserver.IDENTIFIER.fullmatch(field) for field in fields), 'Character schema contract differs')
        self.sql("SELECT coalesce(json_agg(x ORDER BY " + ','.join(keys) + "),'[]'::json) FROM (SELECT "
                 + ','.join(fields) + ' FROM dbo.' + table + ' WHERE ' + where + ') x;', game=True)
        output = self.ctx.children[-1].text().strip()
        require(len(output.encode()) <= SNAPSHOT_LIMIT, 'Character SQL evidence exceeded bound')
        values = json.loads(output)
        require(isinstance(values, list) and len(values) <= 10000, 'Malformed character SQL evidence')
        return values

    def inventory(self):
        return self.sql_rows('ents', evidence.IDENTITY_FIELDS, ('containerid',))

    def login_evidence(self):
        proof = super().login_evidence()
        if proof is not None:
            self.auth_id = proof['auth_id']
        return proof

    def verify_current_identity(self, identity, inventory):
        identifier = identity['containerid']
        require(type(identifier) is int and identifier > 0 and identity.get('authname') == ACCOUNT
                and identity.get('authid') == self.auth_id
                and identifier not in {row['containerid'] for row in self.baseline},
                'Created character identity differs from this graphical session')

    def character_rows(self, identifier):
        return {table: self.sql_rows(table, tuple(fields) + (('logincount',) if table == 'ents' else ()),
                evidence.ROW_KEYS[table], 'containerid=' + str(identifier))
                for table, fields in evidence.SELECTED.items()}

    def validate_saved_rows(self, rows, inventory):
        return validate_character_rows(rows, self.baseline, inventory,
                                       self.schema['expected_attributes'], self.auth_id)

    def connection_metadata(self):
        return {}

    def saved_metadata(self, snapshot):
        return {}

    def observe_connected_character(self):
        pass

    def immediate_event_contract(self):
        package = getattr(self, 'map_package', {})
        return package.get('inputs', {}).get('mapserver_progress', {}).get('events_contract')

    def current_native_events(self):
        if self.immediate_event_contract() is None:
            return None  # Retained legacy donors keep their existing proof path.
        current = self.sample_progress(force=True)
        if not self.live_progress(current):
            return []
        require(self.map_process is not None and self.map_process.process.poll() is None,
                'Immediate native event producer is no longer owned and running')
        values = character_events.records(self.map_process.text(), session=self.owner.args.session_id,
            progress=current, launch_utc_ms=self.map_launch_utc_ms,
            now_utc_ms=int(time.time() * 1000), db_id=self.creation_report['character_id'],
            auth_id=self.auth_id)
        self.creation_report['immediate_native_events'].update(event_count=len(values),
            latest_event=values[-1] if values else None, observed_utc_ms=int(time.time() * 1000))
        return values

    def native_ready_record(self):
        values = self.current_native_events()
        return (ready_record(self.current_logs()) if values is None
                else character_events.latest_ready(values))

    def native_ground_evidence(self, delivery, *, max_age_ms=180000):
        values = self.current_native_events()
        return stable_ground_evidence(self.current_logs() if values is None else [], delivery,
            int(time.time() * 1000), max_age_ms=max_age_ms,
            positions=None if values is None else character_events.positions_after_ready(values))

    def character_evidence(self):
        if self.creation_report['verified']: return self.creation_report
        now = time.monotonic()
        if now < self.character_next: return None
        self.character_next = now + POLL_SECONDS
        self.health(); self.sample_progress()
        if self.auth_id is None: return None
        before = self.sample_progress(force=True)
        if not self.live_progress(before): return None
        inventory = self.inventory()
        candidates = [row for row in inventory if row.get('name') == CHARACTER]
        if not candidates: return None
        require(len(candidates) == 1, 'Ambiguous THORHERO identity')
        identity = candidates[0]
        identifier = identity['containerid']
        self.verify_current_identity(identity, inventory)
        sample = evidence.parse_character_status(self.query(['-getstatus', '3', str(identifier)], 'player-status'),
            identifier, CHARACTER, ACCOUNT, allow_missing=True)
        after = self.sample_progress(force=True)
        if not self.live_progress(after): return None
        progress.compare_records(after, before)
        self.creation_report['character_progress_guard'] = {'before': before, 'after': after, 'passed': True}
        self.creation_report['character_samples'].append(sample)
        self.creation_report.update(character_id=identifier, auth_id=self.auth_id)
        if evidence.connected_on_atlas(sample):
            self.creation_report['db_map_assignment_observed'] = True
            ready = self.native_ready_record()
            if ready is not None and not self.creation_report['connected_on_atlas']:
                self.creation_report.update(connected_on_atlas=True, client_ready_evidence=ready,
                    client_ready_observed_utc=base.utc(), client_ready_observed_utc_ms=int(time.time() * 1000),
                    **self.connection_metadata())
            if self.creation_report['connected_on_atlas']:
                self.observe_connected_character()
            return None
        if not self.creation_report['connected_on_atlas'] or sample.get('connected') or sample.get('in_map_transfer'):
            return None
        client_pid = self.creation_report.get('client_pid')
        if type(client_pid) is not int or client_pid <= 0: return None
        delivery = read_logout_delivery(self.owner.args.state / 'character-logout.json',
            self.owner.args.session_id, client_pid, identifier,
            self.creation_report.get('client_ready_observed_utc_ms'), int(time.time() * 1000))
        if delivery is None: return None
        logout = logout_record(self.current_logs())
        if logout is None or not logout_follows_delivery(logout, delivery): return None
        rows = self.character_rows(identifier)
        snapshot = self.validate_saved_rows(rows, inventory)
        if snapshot is None: return None
        final_progress = self.sample_progress(force=True)
        if not self.live_progress(final_progress): return None
        # SQL reads can take time; recheck the bounded receipt at the save point.
        final_delivery = read_logout_delivery(self.owner.args.state / 'character-logout.json',
            self.owner.args.session_id, client_pid, identifier,
            self.creation_report.get('client_ready_observed_utc_ms'), int(time.time() * 1000))
        require(final_delivery == delivery, 'Character logout delivery changed during save verification')
        self.snapshot = snapshot
        self.creation_report.update(verified=True, committed_sql_verified=True, disconnected_before_sql=True,
            requested_logout_observed=True, logout_timer_observed=True, forced_stop_before_save=False,
            logout_delivery=delivery, logout_timer_evidence=logout, map_progress_at_save=final_progress,
            saved_utc=base.utc(), snapshot_sha256=digest_json(snapshot),
            table_sha256={name: digest_json(value) for name, value in rows.items()},
            row_counts={name: len(value) for name, value in rows.items()},
            evidence_scope='fresh_graphical_character_ready_on_atlas_then_requested_logout_timer_and_committed_full_character_rows')
        self.creation_report.update(self.saved_metadata(snapshot))
        return self.creation_report

    def collect(self, target):
        # Atlas has substantially more diagnostics than the login-only mode.
        # Keep its bounded complete logs in one member of the outer support ZIP.
        # Do not widen the accepted login-only collector's two-MiB limit.
        if self.process is not None:
            text = base.redact(self.process.text(), self.ctx.secrets)
            require(len(text.encode()) <= 2 * 1024 * 1024, 'Server console evidence exceeded bound')
            base.private_write(target / 'local-dbserver-console.txt', text)
        if self.map_process is not None:
            raw = base.redact(self.map_process.text(), self.ctx.secrets).encode()
            require(len(raw) <= 16 * 1024 * 1024, 'Atlas console evidence exceeded export bound')
            base.private_write(target / 'character-atlas-console.txt', raw.decode())
        if self.snapshot is not None:
            base.private_write(target / 'character-saved-snapshot.json', json.dumps(self.snapshot, indent=2) + '\n')
        self.collect_server_logs(target)

    def server_log_paths(self):
        """Enumerate the owned logger tree, never the immutable game data tree.

        Both native services write below logs/. Root-level logs are retained
        too, but traversing data/ to find them made a readiness poll visit about
        177,000 unrelated files on the accepted physical 0.11.3 run.
        """
        if self.runtime is None:
            return [], {'directories': 0, 'entries': 0}
        require(not self.runtime.is_symlink(), 'Linked server log runtime refused')
        if not self.runtime.exists():
            return [], {'directories': 0, 'entries': 0}
        paths, counts = [], {'directories': 0, 'entries': 0}
        pending = [(self.runtime, False)]
        while pending:
            directory, recursive = pending.pop()
            descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                info = os.fstat(descriptor)
                require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid(),
                        'Invalid or foreign character server log directory')
                counts['directories'] += 1
                require(counts['directories'] <= SERVER_LOG_COUNT_LIMIT,
                        'Character server log directory count exceeded bound')
                with os.scandir(descriptor) as entries:
                    for entry in entries:
                        counts['entries'] += 1
                        require(counts['entries'] <= 4096,
                                'Character server log directory entries exceeded bound')
                        path = directory / entry.name
                        if entry.name.endswith('.log'):
                            paths.append(path)
                            require(len(paths) <= SERVER_LOG_COUNT_LIMIT,
                                    'Character server log count exceeded bound')
                        elif recursive or entry.name == 'logs':
                            require(not entry.is_symlink(), 'Linked server log directory refused')
                            if entry.is_dir(follow_symlinks=False):
                                pending.append((path, True))
            finally:
                os.close(descriptor)
        return sorted(paths), counts

    def current_logs(self):
        """Read bounded snapshots from the current owned native logger tree."""
        started = time.monotonic()
        paths, counts = self.server_log_paths()
        total, records = 0, []
        for path in paths:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                before = os.fstat(descriptor)
                require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                        and before.st_uid == os.geteuid() and before.st_size <= SERVER_LOG_FILE_LIMIT,
                        'Invalid or oversized character server log')
                total += before.st_size
                require(total <= SERVER_LOG_TOTAL_LIMIT, 'Character server logs exceeded bound')
                with os.fdopen(descriptor, 'rb', closefd=False) as source:
                    raw = source.read(before.st_size)
                after = os.fstat(descriptor)
                require(after.st_nlink == 1 and after.st_uid == before.st_uid
                        and len(raw) == before.st_size <= after.st_size <= SERVER_LOG_FILE_LIMIT,
                        'Character server log changed or exceeded bound while reading')
            finally:
                os.close(descriptor)
            records.append((path.relative_to(self.runtime).as_posix(), raw.decode('utf-8', errors='replace')))
        metrics = self.ctx.report.setdefault('character_observer_metrics', {}).setdefault('native_log_reads',
            {'scope': 'owned_runtime_root_and_complete_logs_subtree', 'reads': 0, 'total_ms': 0, 'max_ms': 0})
        elapsed_ms = round((time.monotonic() - started) * 1000, 3)
        metrics.update(reads=metrics['reads'] + 1, last_ms=elapsed_ms,
            total_ms=round(metrics['total_ms'] + elapsed_ms, 3), max_ms=max(metrics['max_ms'], elapsed_ms),
            last_files=len(paths), last_bytes=total, last_directories=counts['directories'],
            last_entries=counts['entries'])
        return records

    def collect_server_logs(self, target):
        require(target.is_dir() and not target.is_symlink(), 'Linked server evidence directory refused')
        paths, _ = self.server_log_paths()
        destination = target / 'character-server-logs.zip'
        require(not destination.is_symlink(), 'Linked server log archive refused')
        temporary = target / ('character-server-logs.tmp-' + base.secrets.token_hex(8))
        closed_sources = all(child is None or child.process.poll() is not None
                             for child in (self.process, self.map_process))
        manifest = {'format': 1, 'scope': 'current_owned_character_server_logs',
            'session_id': self.owner.args.session_id, 'truncated': False, 'files': {},
            'collection_phase': 'closed_server_logs' if closed_sources else 'live_snapshot'}
        source_total = exported_total = after_total = 0
        try:
            with temporary.open('xb') as output:
                os.chmod(temporary, 0o600)
                with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    for path in paths:
                        # current_logs() already rejects linked leaves; preserve
                        # that protection and also reject linked parents/owners.
                        current = path.parent
                        while True:
                            require(current.is_dir() and not current.is_symlink(), 'Linked server log directory refused')
                            if current == self.runtime: break
                            require(self.runtime in current.parents, 'Server log path escaped its owned runtime')
                            current = current.parent
                        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                        try:
                            before = os.fstat(descriptor)
                            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                                    and before.st_uid == os.geteuid() and before.st_size <= SERVER_LOG_FILE_LIMIT,
                                    'Invalid or oversized character server log')
                            with os.fdopen(descriptor, 'rb', closefd=False) as source:
                                raw = source.read(before.st_size)
                            after = os.fstat(descriptor)
                            require(after.st_nlink == 1 and after.st_uid == before.st_uid
                                    and len(raw) == before.st_size <= after.st_size <= SERVER_LOG_FILE_LIMIT
                                    and (not closed_sources or after.st_size == before.st_size),
                                    'Character server log changed or exceeded bound while reading')
                        finally:
                            os.close(descriptor)
                        # Preserve every non-secret byte, including non-UTF8
                        # legacy log text. Redaction is the only transformation.
                        redacted = base.redact(raw.decode('utf-8', errors='surrogateescape'),
                            self.ctx.secrets).encode('utf-8', errors='surrogateescape')
                        source_total += len(raw); exported_total += len(redacted); after_total += after.st_size
                        require(source_total <= SERVER_LOG_TOTAL_LIMIT
                                and after_total <= SERVER_LOG_TOTAL_LIMIT
                                and exported_total <= SERVER_LOG_TOTAL_LIMIT
                                and len(redacted) <= SERVER_LOG_FILE_LIMIT,
                                'Character server logs exceeded export bound')
                        name = path.relative_to(self.runtime).as_posix()
                        manifest['files'][name] = {'source_bytes': len(raw),
                            'source_sha256': hashlib.sha256(raw).hexdigest(), 'exported_bytes': len(redacted),
                            'exported_sha256': hashlib.sha256(redacted).hexdigest(),
                            'source_bytes_after_read': after.st_size,
                            'appended_bytes_after_snapshot': after.st_size - before.st_size,
                            'redacted': raw != redacted, 'truncated': False}
                        archive.writestr(name, redacted)
                    manifest.update(file_count=len(paths), source_bytes=source_total,
                                    source_bytes_after_read=after_total, exported_bytes=exported_total)
                    document = json.dumps(manifest, indent=2) + '\n'
                    require(len(document.encode()) <= 128 * 1024, 'Server log manifest exceeded bound')
                    archive.writestr('manifest.json', document)
                output.flush(); os.fsync(output.fileno())
            require(temporary.stat().st_size <= SERVER_LOG_TOTAL_LIMIT + 1024 * 1024,
                    'Character server log archive exceeded bound')
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        self.ctx.report['character_server_logs'] = {'path': destination.name,
            'bytes': destination.stat().st_size, 'sha256': base.file_hash(destination),
            'manifest_sha256': hashlib.sha256(document.encode()).hexdigest(),
            'file_count': len(paths), 'source_bytes': source_total, 'exported_bytes': exported_total,
            'source_bytes_after_read': after_total, 'collection_phase': manifest['collection_phase'],
            'truncated': False, 'redacted_files': sum(item['redacted'] for item in manifest['files'].values())}


class LocalCharacterReopenServer(LocalCharacterServer):
    """Reopen one preserved real player; SQL is evidence and never a game input."""
    REPORT_KEY = 'character_reopen'
    CHARACTER_ID = 1

    def __init__(self, owner):
        super().__init__(owner)
        self.baseline_snapshot = None
        self.creation_report.update(before_character_id=self.CHARACTER_ID,
            baseline_character_id=self.CHARACTER_ID, existing_character_verified=False,
            preserved_existing_identity=False, powers_preserved=False, costume_preserved=False,
            native_client_ready_observed=False, ordinary_stuck_observed=False,
            on_atlas_safe_position=False, stable_ground_verified=False,
            recovery_requested=False, recovery_verified=False,
            committed_native_position_verified=False, committed_safe_position_verified=False,
            operation='reopen_existing_character')

    def initialize(self):
        # Refuse a missing or interrupted profile before the parent can create
        # its cluster, role, compatibility schema, or marker. Creation remains
        # an explicit separate entry point and is never a reopen fallback.
        marker = self.profile / 'profile.json'
        require(not self.profile.is_symlink() and self.profile.is_dir(),
                'Existing character profile is missing; do not create a replacement')
        record = login.profile_record(marker)
        require(record['initialized'] is True and (self.profile / 'pgdata' / 'PG_VERSION').is_file()
                and not (self.profile / 'pgdata').is_symlink()
                and (self.profile / 'credentials.json').is_file()
                and not (self.profile / 'credentials.json').is_symlink(),
                'Existing character profile is incomplete; preserve it and export the report')
        super().initialize()
        require(self.report.get('profile_reused') is True,
                'Character reopen requires the reused persistent profile')

    def prepare_runtime(self):
        super().prepare_runtime()
        # The current reader repair enables a stock, read-only native purchase
        # witness. DbServer transmits this category level to its owned MapServer.
        # Retained runtime producers keep their original logging configuration.
        if (isinstance(self.manual_atlas_startup, dict)
                and self.manual_atlas_startup.get('levelup_ui_repair_save') is not None):
            config = self.runtime / 'data/server/db/servers.cfg'
            text = re.sub(r'(?im)^\s*SetLogLevel\s+entity\s+[^\r\n]*\r?\n?', '', config.read_text())
            base.private_write(config, text.rstrip() + '\nSetLogLevel entity 1\n')
            self.creation_report['native_training_logging'] = {
                'entity': 1, 'stock_purchase_records': True,
                'current_reader_repair_only': True, 'other_categories_changed': False,
                'native_dbserver_manifest_sha256': self.manual_atlas_startup['manifest_sha256']}

    def capture_baseline(self):
        self.baseline = self.inventory()
        candidates = [row for row in self.baseline
                      if row.get('name', '').casefold() == CHARACTER.casefold()
                      or row.get('containerid') == self.CHARACTER_ID]
        require(len(candidates) == 1, 'Expected exactly the existing THORHERO ID 1; preserve all characters')
        identity = candidates[0]
        auth_id = identity.get('authid')
        require(type(identity.get('containerid')) is int and identity['containerid'] == self.CHARACTER_ID
                and identity.get('name') == CHARACTER and identity.get('authname') == ACCOUNT
                and type(auth_id) is int and 0 < auth_id <= 4294967295,
                'Preserved THORHERO identity differs from the accepted local character')
        require([row for row in self.baseline if row.get('authid') == auth_id] == [identity],
                'Reopen requires exactly the existing COHLOCAL character')
        account = self.sql("SELECT containerid || '|' || authname FROM dbo.shardaccounts "
            "WHERE lower(authname)=lower('COHLOCAL') ORDER BY containerid;", game=True)
        require(account == str(auth_id) + '|' + ACCOUNT, 'Preserved character account differs from SQL')
        rows = self.character_rows(self.CHARACTER_ID)
        parents = rows.get('ents', [])
        require(len(parents) == 1 and type(parents[0].get('logincount')) is int
                and 0 < parents[0]['logincount'] < 2**31 - 1,
                'Existing character has no accepted committed login baseline')
        count = parents[0]['logincount']
        snapshot = validate_character_rows(rows, self.baseline, self.baseline,
            self.schema['expected_attributes'], auth_id, existing_identity=identity, expected_login_count=count)
        require(snapshot is not None, 'Existing character powers/costume are incomplete; do not synthesize them')
        self.baseline_snapshot = snapshot
        position = self.character_position(allow_unassigned_active_map=True)
        self.creation_report.update(existing_character_verified=True,
            baseline_character_count=len(self.baseline), baseline_identity_sha256=digest_json(self.baseline),
            before_login_count=count,
            baseline={'character_id': self.CHARACTER_ID, 'auth_id': auth_id,
                'identity_sha256': digest_json(identity), 'snapshot_sha256': digest_json(snapshot),
                'table_sha256': {name: digest_json(value) for name, value in rows.items()},
                'row_counts': {name: len(value) for name, value in rows.items()},
                'login_count': count, 'captured_utc': base.utc(), 'saved_position': position},
            sql_game_mutations_performed=False)
        self.ctx.event('existing_character_ready', session_id=self.owner.args.session_id,
            character_id=self.CHARACTER_ID, auth_id=auth_id, account=ACCOUNT, name=CHARACTER,
            existing_character_verified=True, before_login_count=count)

    def login_evidence(self):
        proof = super().login_evidence()
        if proof is not None:
            require(self.baseline_snapshot is not None
                    and proof['auth_id'] == self.baseline_snapshot['identity']['authid']
                    and proof['character_count'] == 1,
                    'Current graphical login differs from the preserved character account')
        return proof

    def verify_current_identity(self, identity, inventory):
        require(self.baseline_snapshot is not None
                and evidence._same(identity, self.baseline_snapshot['identity'])
                and evidence._same(inventory, self.baseline)
                and self.auth_id == identity['authid'],
                'Reopened character or inventory differs from its preserved baseline')

    def connection_metadata(self):
        require(self.baseline_snapshot is not None and self.creation_report['existing_character_verified'] is True,
                'Reopened connection lacks a committed existing character baseline')
        return {'reopen_verified': True, 'existing_character_verified': True,
                'preserved_existing_identity': True, 'native_client_ready_observed': True}

    def character_position(self, *, allow_unassigned_active_map=False):
        values = self.sql_rows('ents', ('containerid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz'),
                              ('containerid',), 'containerid=' + str(self.CHARACTER_ID))
        require(len(values) == 1 and set(values[0]) == {'containerid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz'},
                'Existing character position snapshot differs')
        value = values[0]
        # Before login, MapId is an active assignment and may be SQL NULL.
        # StaticMapId retains the saved Atlas destination. Only the read-only
        # baseline accepts that unassigned state; connected save still needs 1.
        assigned_to_atlas = type(value['mapid']) is int and value['mapid'] == 1
        require(type(value['containerid']) is int and value['containerid'] == self.CHARACTER_ID
                and (assigned_to_atlas or allow_unassigned_active_map and value['mapid'] is None)
                and type(value['staticmapid']) is int and value['staticmapid'] == 1
                and all(type(value[key]) in (int, float) and math.isfinite(value[key])
                        and abs(value[key]) <= 1000000 for key in ('posx', 'posy', 'posz')),
                'Existing character map or position differs from Atlas')
        return value

    def relocation_delivery(self):
        client_pid = self.creation_report.get('client_pid')
        if type(client_pid) is not int or client_pid <= 0:
            return None
        return read_logout_delivery(self.owner.args.state / 'character-relocation.json',
            self.owner.args.session_id, client_pid, self.CHARACTER_ID,
            self.creation_report.get('client_ready_observed_utc_ms'), int(time.time() * 1000),
            action='stuck', max_age_ms=RELOCATION_MAX_AGE_MS)

    def observe_connected_character(self):
        delivery = self.relocation_delivery()
        if delivery is None:
            return
        previous = self.creation_report.get('relocation_delivery')
        require(previous is None or previous == delivery,
                'Ordinary recovery delivery changed after request')
        self.creation_report.update(recovery_requested=True, relocation_delivery=delivery)
        ground = self.native_ground_evidence(delivery)
        if ground is None:
            return
        self.creation_report.update(recovery_verified=True, ordinary_stuck_observed=True, on_atlas_safe_position=True,
            stable_ground_verified=True, relocation_delivery=delivery, ground_evidence=ground)
        if 'ground_observed_utc_ms' not in self.creation_report:
            self.creation_report.update(ground_observed_utc=base.utc(),
                                        ground_observed_utc_ms=int(time.time() * 1000))

    def validate_saved_rows(self, rows, inventory):
        require(self.baseline_snapshot is not None, 'Existing character baseline is missing')
        self.native_reward_credit = None
        self.native_training_save = None
        before = self.baseline_snapshot
        after = validate_character_rows(rows, self.baseline, inventory,
            self.schema['expected_attributes'], self.auth_id,
            existing_identity=before['identity'], expected_login_count=before['login_count'] + 1)
        if after is None:
            return None
        # Only the typed current reader repair permits the finite first-training
        # transition. It observes stock native success and committed SQL; it
        # supplies no character input and never changes database rows. The
        # authored task profile retains its original strict level/power guards.
        if (isinstance(self.manual_atlas_startup, dict)
                and self.manual_atlas_startup.get('levelup_ui_repair_save') is not None
                and self.creation_report.get('task_gate_required') is not True
                and not evidence._same(before['rows']['ents'][0]['level'], after['rows']['ents'][0]['level'])):
            import native_training_save
            now_ms = int(time.time() * 1000)
            receipt = read_logout_delivery(self.owner.args.state / 'character-logout.json',
                self.owner.args.session_id, self.creation_report.get('client_pid'), self.CHARACTER_ID,
                self.creation_report.get('client_ready_observed_utc_ms'), now_ms)
            logs = self.current_logs()
            self.native_training_save = native_training_save.verify(logs, self.creation_report,
                receipt, logout_record(logs), before['rows'], after['rows'],
                self.schema['expected_attributes']['attributes'], session=self.owner.args.session_id,
                client_pid=self.creation_report.get('client_pid'), now_utc_ms=now_ms)
        for table in evidence.SELECTED:
            previous = before['rows'][table]
            current = after['rows'][table]
            if table == 'ents':
                previous = [{key: value for key, value in row.items() if key != 'logincount'} for row in previous]
                current = [{key: value for key, value in row.items() if key != 'logincount'} for row in current]
            require(self.saved_selected_rows_match(table, previous, current),
                    'Committed existing character rows changed after reopen: ' + table)
        delivery = self.relocation_delivery()
        requested = self.creation_report.get('recovery_requested') is True or delivery is not None
        self.creation_report['recovery_requested'] = requested
        ground = None
        ready_ms = self.creation_report['client_ready_observed_utc_ms']
        if requested:
            require(self.creation_report.get('recovery_verified') is True
                    and self.creation_report.get('stable_ground_verified') is True,
                    'Existing character was not observed stable after requested ordinary recovery')
            require(delivery is not None and delivery == self.creation_report.get('relocation_delivery'),
                    'Ordinary recovery delivery changed before save')
            ground = self.native_ground_evidence(delivery, max_age_ms=300000)
            require(ground is not None, 'Native character position fell or became stale before save')
            ready_ms = self.creation_report['ground_observed_utc_ms']
        logout = read_logout_delivery(self.owner.args.state / 'character-logout.json',
            self.owner.args.session_id, self.creation_report['client_pid'], self.CHARACTER_ID,
            ready_ms, int(time.time() * 1000))
        require(logout is not None, 'Save was not requested after the current native connection or optional recovery')
        values = self.current_native_events()
        positions = (native_position_records(self.current_logs()) if values is None
                     else character_events.positions_after_ready(values))
        # This proves the native position committed by ordinary logout, not
        # stable ground or collision geometry. No recovery command is needed.
        positions = [value for value in positions
                     if self.creation_report['client_ready_observed_utc_ms'] <= value['utc_ms']
                     <= logout['sent_utc_ms'] + 999]
        native = positions[-1] if positions else None
        require(native is not None and -999 <= logout['sent_utc_ms'] - native['utc_ms'] <= 180000
                and all(type(value) in (int, float) and math.isfinite(value)
                        and abs(value) <= 1000000 for value in native['position'])
                and above_native_fall_floor(native['position'][1]),
                'No fresh valid native Atlas position before ordinary logout')
        position = self.character_position()
        current_position = [position[key] for key in ('posx', 'posy', 'posz')]
        # Retain the fresh periodic/native producer gate above. Prefer the
        # actual stock logout location when it is present: it includes final
        # movement between the 30-second sample and ordinary logout. A stale
        # SQL position matching the earlier sample must still be refused.
        # Retained donors lacking that stock line keep the prior proof path.
        terminal = native_logout_position(self.current_logs(), logout,
            self.creation_report['client_ready_observed_utc_ms'], int(time.time() * 1000))
        if terminal is not None:
            terminal.update(session_id=self.owner.args.session_id,
                db_id=self.CHARACTER_ID, auth_id=self.auth_id,
                client_pid=self.creation_report['client_pid'],
                connection_binding='previously_validated_current_session_reopen_connection',
                native_log_contains_character_db_id=False,
                native_log_contains_session_or_client_pid=False,
                prior_native_position_evidence=native)
            native = terminal
        require(above_native_fall_floor(position['posy'])
                and all(abs(a-b) <= 2 for a, b in zip(current_position, native['position'])),
                'Committed character position differs from the current native Atlas observation')
        if requested:
            require(all(abs(a-b) <= 2 for a, b in zip(current_position, ground['position'])),
                    'Committed character position differs from the stable native recovery')
            self.creation_report.update(ground_evidence=ground, committed_safe_position_verified=True)
        self.creation_report.update(saved_position=position, saved_native_position_evidence=native,
                                    committed_native_position_verified=True)
        return after

    def saved_selected_rows_match(self, table, previous, current):
        """Permit exact point awards and the witnessed first trained purchase."""
        if evidence._same(previous, current):
            return True
        training = getattr(self, 'native_training_save', None)
        if isinstance(training, dict) and training.get('verified') is True:
            if table == 'powers':
                return (digest_json(previous) == training['before_power_rows_sha256']
                        and digest_json(current) == training['saved_power_rows_sha256'])
            if (table == 'ents' and len(previous) == 1 and len(current) == 1
                    and (previous[0].get('level') is None or type(previous[0].get('level')) is int
                         and previous[0]['level'] == training['before_internal_level'])
                    and type(current[0].get('level')) is int
                    and current[0]['level'] == training['saved_internal_level']):
                previous = [{key: value for key, value in previous[0].items() if key != 'level'}]
                current = [{key: value for key, value in current[0].items() if key != 'level'}]
                if evidence._same(previous, current):
                    return True
        if table != 'ents' or len(previous) != 1 or len(current) != 1:
            return False
        fields = ('experiencepoints', 'influencepoints')
        if not evidence._same(
                [{key: value for key, value in previous[0].items() if key not in fields}],
                [{key: value for key, value in current[0].items() if key not in fields}]):
            return False
        values = []
        for row in (previous[0], current[0]):
            if any(key not in row or row[key] is not None
                    and (type(row[key]) is not int or not 0 <= row[key] <= 0x7fffffff)
                    for key in fields):
                return False
            values.append({key: 0 if row[key] is None else row[key] for key in fields})
        proof = self.creation_report
        if (previous[0].get('containerid') != self.CHARACTER_ID
                or type(previous[0].get('containerid')) is not int
                or previous[0].get('authid') != proof.get('auth_id')
                or type(previous[0].get('authid')) is not int):
            return False
        now_ms = int(time.time() * 1000)
        delivery = read_logout_delivery(self.owner.args.state / 'character-logout.json',
            self.owner.args.session_id, proof.get('client_pid'), self.CHARACTER_ID,
            proof.get('client_ready_observed_utc_ms'), now_ms)
        if delivery is None:
            return False
        logs = self.current_logs()
        credit = native_reward_credit_evidence(logs, proof, delivery, logout_record(logs),
            session=self.owner.args.session_id, client_pid=proof.get('client_pid'), now_utc_ms=now_ms)
        if credit is None or any(values[1][key] != values[0][key] + credit[key + '_delta']
                                 for key in fields):
            return False
        credit['before_reward_values'] = values[0]
        credit['expected_saved_reward_values'] = values[1]
        self.native_reward_credit = credit
        return True

    def saved_metadata(self, snapshot):
        result = {'preserved_existing_identity': True, 'powers_preserved': True, 'costume_preserved': True,
            'selected_rows_preserved': True, 'login_count': snapshot['login_count'],
            'before_login_count': self.baseline_snapshot['login_count'],
            'evidence_scope': 'existing_committed_character_native_ready_then_requested_logout_and_preserved_committed_rows'}
        credit = getattr(self, 'native_reward_credit', None)
        if credit is not None:
            result.update(selected_rows_preservation_policy='strict_baseline_except_login_count_and_exact_native_point_credits',
                selected_non_reward_rows_preserved=True, native_reward_values_committed_verified=True,
                native_reward_credit_evidence=credit)
        training = getattr(self, 'native_training_save', None)
        if training is not None:
            result.update(selected_rows_preservation_policy='strict_baseline_except_login_count_exact_native_point_credits_and_first_trained_purchase',
                native_training_values_committed_verified=True,
                native_training_save_evidence=training, saved_internal_level=1,
                saved_displayed_level=2, newly_purchased_power=training['purchased_power'])
        return result

    def collect(self, target):
        super().collect(target)
        if self.baseline_snapshot is not None:
            base.private_write(target / 'character-reopen-before-snapshot.json',
                               json.dumps(self.baseline_snapshot, indent=2) + '\n')
        # Export-only optional diagnostics. No extra readiness polling, SQL
        # queries or native inputs are introduced by stationary contact proof.
        try:
            import stationary_contact_evidence as contact_evidence
            contact = contact_evidence.collect(self.current_logs(), self.creation_report,
                session=self.owner.args.session_id, client_pid=self.creation_report.get('client_pid'),
                now_utc_ms=int(time.time() * 1000))
        except Exception as error:
            contact = {'format': 1, 'optional': True, 'status': 'unavailable', 'records': [],
                'native_initiation_observed': False, 'native_response_observed': False,
                'dialogue_visual_verified': False,
                'reason': 'Optional contact collection unavailable: ' + type(error).__name__}
        contact['collection_phase'] = self.ctx.report.get('character_server_logs', {}).get(
            'collection_phase', 'unavailable')
        self.ctx.report['stationary_contact'] = contact


class LocalCharacterTaskReopenServer(LocalCharacterReopenServer):
    """One authored manual task; stock command effect and SQL are separate proof."""

    def __init__(self, owner):
        super().__init__(owner)
        import task_gate_evidence
        self.task_evidence = task_gate_evidence
        self.task_baseline = None
        self.task_accepted = None
        self.task_completed = None
        self.task_sql_next = 0
        self.task_sql_reads = 0
        self.task_saved = None
        self.creation_report['task_gate_required'] = True
        self.ctx.report['task_gate'] = task_gate_evidence._result('pending')

    def prepare_runtime(self):
        super().prepare_runtime()
        # Stock DbServer distributes these category levels to its MapServer.
        # Only entity's deprecated Storyarc:Add supplies the runtime arc handle.
        # Preserve the existing logging policy in every retained entry point.
        config = self.runtime / 'data/server/db/servers.cfg'
        text = config.read_text()
        text = re.sub(r'(?im)^\s*SetLogLevel\s+(?:entity|rewards|admin)\s+[^\r\n]*\r?\n?', '', text)
        base.private_write(config, text.rstrip() + '\nSetLogLevel entity 2\n'
            'SetLogLevel rewards 0\nSetLogLevel admin 0\n')
        self.ctx.report['task_gate']['native_logging'] = {
            'entity': 2, 'rewards': 0, 'admin': 0, 'task_profile_only': True}

    def task_rows(self):
        self.task_sql_reads += 1
        require(self.task_sql_reads <= 40, 'Task SQL observation exceeded its bounded read budget')
        return {table: self.sql_rows(table, fields,
                    ('containerid',) if table == 'ents' else ('containerid', 'subid'),
                    'containerid=' + str(self.CHARACTER_ID))
                for table, fields in self.task_evidence.SELECTED.items()}

    def capture_baseline(self):
        super().capture_baseline()
        self.task_baseline = self.task_rows()
        require(not self.task_baseline['tasks'],
            'Existing tasks were preserved; the one-task diagnostic requires an empty task journal')
        level = self.baseline_snapshot['rows']['ents'][0]['level']
        require(level is None or type(level) is int and 0 <= level <= 9,
            'The authored diagnostic contact requires the preserved level 1-10 Hero')
        self.ctx.report['task_gate'].update(baseline_task_count=0,
            baseline_sql=self.task_baseline, baseline_sql_sha256=digest_json(self.task_baseline),
            sql_game_mutations_performed=False)

    def observe_connected_character(self):
        super().observe_connected_character()
        proof = self.creation_report
        pid = proof.get('client_pid')
        if type(pid) is not int or pid <= 0 or self.task_completed is not None:
            return
        now = time.monotonic()
        if now < self.task_sql_next:
            return
        module = self.task_evidence
        identity = dict(session=self.owner.args.session_id, client_pid=pid,
                        now_utc_ms=int(time.time() * 1000))
        accepted = self.task_accepted
        receipt_path = self.owner.args.state / ('character-task-contact.json' if accepted is None
                                                else 'character-task-completion.json')
        receipt = module.read_delivery(receipt_path, proof, accepted=accepted, **identity)
        if receipt is None:
            return
        logs = self.current_logs()
        # Avoid four extra SQL subprocesses on every ordinary movement poll.
        # Query only after this session's stock native task action is visible.
        native = module.records(logs, proof['client_ready_observed_utc_ms'], identity['now_utc_ms'])
        needed = 'add' if accepted is None else 'success'
        if native is None or not any(row['kind'] == needed for row in native):
            return
        self.task_sql_next = now + POLL_SECONDS
        before = self.sample_progress(force=True)
        if not self.live_progress(before):
            return
        rows = self.task_rows()
        self.ctx.check(); self.health()
        after = self.sample_progress(force=True)
        if not self.live_progress(after):
            return
        progress.compare_records(after, before)
        identity['now_utc_ms'] = int(time.time() * 1000)
        require(module.read_delivery(receipt_path, proof, accepted=accepted, **identity) == receipt,
            'Task helper delivery changed during SQL observation')
        if accepted is None:
            observed = module.observe_acceptance(logs, proof, rows,
                baseline_rows=self.task_baseline, attributes=self.schema['expected_attributes']['attributes'],
                setup_receipt=receipt, **identity)
            if observed.get('task_accepted_verified') is True:
                self.task_accepted = observed
        else:
            observed = module.observe_completion(logs, proof, accepted, receipt, rows, **identity)
            if observed.get('task_completed_verified') is True:
                self.task_completed = observed
        self.ctx.report['task_gate'].update(observed,
            accepted=self.task_accepted, completed=self.task_completed,
            sql_observation_batches=self.task_sql_reads)

    def saved_selected_rows_match(self, table, previous, current):
        if table != 'ents':
            return super().saved_selected_rows_match(table, previous, current)
        completed = self.task_completed
        if not (isinstance(completed, dict) and completed.get('reward_credit_verified') is True
                and completed.get('task_completed_verified') is True):
            # The task profile keeps its authored exact-credit proof contract;
            # it must never fall back to the ordinary reopen reward exception.
            return evidence._same(previous, current)
        if len(previous) != 1 or len(current) != 1:
            return False
        expected = completed['expected_saved_reward_values']
        reward_fields = ('experiencepoints', 'influencepoints')
        # NULL is the stock serialization of zero. Every other selected field,
        # including level/class/origin, powers and costume, retains strict proof.
        if any(field not in current[0] or current[0][field] is not None
                and type(current[0][field]) is not int
                or (current[0].get(field) or 0) != expected[field] for field in reward_fields):
            return False
        return evidence._same(
            [{key: value for key, value in previous[0].items() if key not in reward_fields}],
            [{key: value for key, value in current[0].items() if key not in reward_fields}])

    def validate_saved_rows(self, rows, inventory):
        require(self.task_accepted is not None and self.task_completed is not None,
            'Accept and command-complete the authored task before ordinary Save')
        return super().validate_saved_rows(rows, inventory)

    def character_evidence(self):
        proof = super().character_evidence()
        if proof is None:
            return None
        if self.task_saved is None:
            rows = self.task_rows()
            saved = self.task_evidence.verify_saved(self.current_logs(), proof,
                self.task_accepted, self.task_completed, rows,
                session=self.owner.args.session_id, client_pid=proof['client_pid'],
                now_utc_ms=int(time.time() * 1000), ordinary_save_verified=proof['verified'] is True)
            self.ctx.report['task_gate'].update(saved, accepted=self.task_accepted,
                completed=self.task_completed, sql_observation_batches=self.task_sql_reads)
            require(saved.get('verified') is True,
                'Completed task was not verified in the ordinary committed save: ' + saved.get('reason', 'missing proof'))
            self.task_saved = saved
        proof['task_gate_verified'] = True
        return proof
