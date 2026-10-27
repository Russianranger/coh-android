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
import server_fx_catalog
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
POWER_DELTA_LIMIT = 128
BOOST_FIELDS = ('containerid', 'subid', 'powerid', 'idx', 'categoryname',
    'powersetname', 'boostname', 'level', 'numcombines', 'var0', 'var1', 'var2', 'var3',
    'slottedpowerupsmask', *(field for index in range(10)
        for field in (f'powerupslottype{index}', f'powerupslotid{index}')))
BOOST_ZERO_DEFAULT_SOURCE = {
    'Common/container/dbcontainerpack.c': '8b4e5b0a65aac6ad79c088cb4367c47118baf1e771b4fbd24cc2155b3b628ecb',
    'DBServer/src/container_sql.c': 'fdb1c9d3540c0cbb0fb64b219f02fc1a852ce3c1c54255227237788f8bad078f',
    'MapServer/src/container/containerloadsave.c': '53eac63aab1577956d85a7cfacbe55fb63c856f6b185d9cb8e2b985117920aa8',
}
COMMUTER_POWER = 'Temporary_Powers.Day_Job_Powers.Day_Job_Movement_Increase_Lesser'
# These pins describe the stock candidate, never evidence that this session
# actually satisfied its time, material-volume and badge predicates.
STOCK_DAYJOB_NATIVE_INPUTS = {
    'MapServer/src/gameSys/DayJob.c': '0d2aeddac19f1ba1b9e91eb660a5d65537ba9fddb7c84a3fe59fabca194a2330',
    'MapServer/src/entity/character_db.c': '688fa8a8678fa639457752dd2359980d248b4da3a9c2357af27f7bce47627f1d',
    'MapServer/src/container/containercallbacks.c': '56b484eded5a1ac2148369c4fac51084cad6ad9c55de6cfec4cbcb2dda90fb73',
    'MapServer/src/container/containerloadsave.c': '53eac63aab1577956d85a7cfacbe55fb63c856f6b185d9cb8e2b985117920aa8',
}
STOCK_DAYJOB_DATA_INPUTS = {
    'data/defs/generic/jobs.dayjobs': '623310c40fc42f96ed32ade02abe82f04c41ca2399fdccffd19bb0e49202215e',
    'data/defs/powers/temporary_powers_day_job_powers.powers': 'ad89404d95756799f6f7a553e11c365aa5f12ff9f2d4357fcf3f48980a65e406',
}


# The accepted native consumer explicitly excludes this folder before loading
# data. This projection is scoped to those exact already-qualified bytes; a
# different future consumer keeps the complete mirror until separately proved.
SERVER_TEXTURE_EXCLUSION_MAP = 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'
SERVER_TEXTURE_EXCLUSION_SOURCE = '2048c22f8380931514cefb429790552295e52dd72e03617973820936e116639d'



def LOCAL_CLIENT_LINK_OPTIONS():
    """Keep the single local client's link while it loads the zone.

    On the Thor the ARM64 client's first Atlas load took over two minutes
    without servicing its link (0.13.37 report 2026-10-27); the MapServer
    disconnected it on netlink overflow and the client returned to login.
    The original -notimeout option (svr_init.c) keeps local links through
    overflow/logout timers. Used only for the ARM64 client option.
    """
    return ['-notimeout'] if os.environ.get('COH_CLIENT_ARCH', 'x86') == 'arm64' else []

def server_input_projection(package):
    if (not isinstance(package, dict) or package.get('source_commit') != device.SOURCE_COMMIT
            or package.get('files', {}).get('MapServer.exe', {}).get('sha256') != SERVER_TEXTURE_EXCLUSION_MAP):
        return None
    return {'policy': 'exact_native_excluded_texture_directory_v1',
            'excluded_top_level_directories': ['texture_library'],
            'native_consumer_sha256': SERVER_TEXTURE_EXCLUSION_MAP,
            'native_source_path': 'MapServer/src/svr/svr_init.c',
            'native_source_sha256': SERVER_TEXTURE_EXCLUSION_SOURCE,
            'client_inputs_modified': False, 'native_bytes_changed': False}


def stock_power_delta(previous, current, attributes):
    """Describe a bounded selected-row difference; this cannot accept a save.

    Positive UniqueID, rather than a mutable native packing index, identifies
    each original power. The exact Commuter shape is only a stock-compatible
    candidate: the retained MapServer emits no authoritative DayJob witness.
    """
    result = {'format': 1, 'optional': True, 'status': 'unavailable',
        'save_acceptance_changed': False, 'dayjob_grant_verified': False,
        'login_eligibility_verified': False, 'spatial_predicates_verified': False,
        'badge_predicates_verified': False, 'sql_game_mutations_performed': False}
    fields = set(evidence.SELECTED['powers'])
    if not (type(previous) is list and type(current) is list
            and 0 < len(previous) <= POWER_DELTA_LIMIT and 0 < len(current) <= POWER_DELTA_LIMIT
            and type(attributes) is list and len(attributes) <= 100000):
        return dict(result, reason='Power delta input exceeds the finite typed diagnostic scope')
    names = {}
    for attribute in attributes:
        if not (type(attribute) is dict and type(attribute.get('id')) is int
                and attribute['id'] > 0 and attribute['id'] not in names
                and type(attribute.get('name')) is str and attribute['name'].isascii()
                and 0 < len(attribute['name']) <= 255):
            return dict(result, reason='Attribute mapping is not unique and typed')
        names[attribute['id']] = attribute['name']
    indexes = []
    for rows in (previous, current):
        index = {}
        for row in rows:
            if not (type(row) is dict and set(row) == fields
                    and type(row['containerid']) is int and row['containerid'] == 1
                    and type(row['uniqueid']) is int and 0 < row['uniqueid'] <= 0x7fffffff
                    and row['uniqueid'] not in index
                    and type(row['subid']) is int and 0 <= row['subid'] < POWER_DELTA_LIMIT
                    and type(row['powerid']) is int and 0 < row['powerid'] <= POWER_DELTA_LIMIT
                    and all(type(row[key]) is int and row[key] in names
                            for key in ('categoryname', 'powersetname', 'powername'))
                    and all(row[key] is None or type(row[key]) is int and 0 <= row[key] <= 0x7fffffff
                            for key in ('powerlevelbought', 'powernumboostsbought',
                                        'powersetlevelbought', 'buildnum'))):
                return dict(result, reason='Power rows lack unique positive identity or typed selected fields')
            index[row['uniqueid']] = row
        indexes.append(index)
    before, after = indexes
    semantic = fields - {'subid', 'powerid'}
    deleted = sorted(set(before) - set(after))
    changed = []
    for uid in sorted(set(before) & set(after)):
        differences = sorted(key for key in semantic if not evidence._same(before[uid][key], after[uid][key]))
        if differences:
            changed.append({'uniqueid': uid, 'changed_fields': differences})
    added = []
    for row in current:
        if row['uniqueid'] not in before:
            added.append({'uniqueid': row['uniqueid'], 'selected_row': row.copy(),
                'resolved_power': '.'.join(names[row[key]] for key in ('categoryname', 'powersetname', 'powername'))})
    contiguous = all(row['subid'] == i and row['powerid'] == i + 1 for i, row in enumerate(current))
    preserved = not deleted and not changed
    result.update(status='observed', before_power_count=len(previous), after_power_count=len(current),
        before_power_rows_sha256=digest_json(previous), after_power_rows_sha256=digest_json(current),
        attribute_mapping_sha256=digest_json(attributes), prior_powers_preserved_by_uniqueid=preserved,
        all_prior_semantic_fields_preserved=preserved, current_native_indexes_contiguous=contiguous,
        deleted_uniqueids=deleted, changed_prior_powers=changed, added_powers=added)
    if (preserved and contiguous and len(added) == 1
            and added[0]['resolved_power'].casefold() == COMMUTER_POWER.casefold()
            and type(added[0]['selected_row']['powerlevelbought']) is int
            and added[0]['selected_row']['powerlevelbought'] == 1
            and all(added[0]['selected_row'][key] is None
                    for key in ('powernumboostsbought', 'powersetlevelbought', 'buildnum'))):
        result.update(stock_compatible_candidate=COMMUTER_POWER,
            stock_candidate_native_source_sha256=STOCK_DAYJOB_NATIVE_INPUTS.copy(),
            stock_candidate_data_source_sha256=STOCK_DAYJOB_DATA_INPUTS.copy(),
            unproved_predicates=['current_login_offline_time_over_120_seconds',
                'live_material_volume_DJ_TrainStation', 'DJ_Commuter_badge_not_owned',
                'native_DayJob_grant_and_current_owner_lifecycle'],
            reason='Exact stock-compatible Commuter addition; no native grant or spatial witness, so strict save verification remains required')
    return result


def enhancement_semantics(boosts, powers, attributes):
    """Normalize native indexes/defaults; preserve nonzero boost payloads.

    convertPowerBoosts stores the current packed PowerID. Resolve that relation
    through the stable UniqueID before comparing attachments across repacking.
    Inventory index and slotted enhancement index remain exact.
    The pinned PACKTYPE_INT/FLOAT serializer omits zeros; the SQL reader skips
    both NULL and zero. Those known numeric payload defaults alone are equal.
    Required attribute IDs, attachment identity and every raw row are retained.
    This bounded current-character scope covers 128 powers, six slots per
    power, and 70 inventory slots; it does not qualify larger endgame profiles
    or independently authorize loot, equipping, combining or enhancement loss.
    """
    require(type(boosts) is list and len(boosts) <= 6010
            and type(powers) is list and 0 < len(powers) <= POWER_DELTA_LIMIT,
            'Enhancement/power inventory exceeds bounded preservation scope')
    known = {row['id'] for row in attributes}
    ids, unique = {}, set()
    for row in powers:
        pid, uid = row.get('powerid'), row.get('uniqueid')
        require(type(pid) is int and 0 < pid <= POWER_DELTA_LIMIT and pid not in ids
                and type(uid) is int and 0 < uid <= 0x7fffffff and uid not in unique,
                'Enhancement attachment has ambiguous power identity')
        ids[pid] = {key: row[key] for key in ('uniqueid', 'buildnum', 'categoryname', 'powersetname', 'powername')}
        unique.add(uid)
    result, subids, locations = [], set(), set()
    for row in boosts:
        require(type(row) is dict and set(row) == set(BOOST_FIELDS)
                and type(row['containerid']) is int and row['containerid'] == 1
                and type(row['subid']) is int and 0 <= row['subid'] < 6010
                and row['subid'] not in subids and type(row['powerid']) is int,
                'Incomplete, duplicate or foreign enhancement row')
        subids.add(row['subid'])
        index = 0 if row['idx'] is None else row['idx']
        require(type(index) is int and index >= 0, 'Invalid enhancement slot index')
        if row['powerid'] == -1:
            require(index < 70, 'Inventory enhancement slot exceeds native bound')
            location = {'inventory_index': index}
        else:
            require(row['powerid'] in ids and index < 6, 'Enhancement has no exact power/slot relation')
            location = {'power': ids[row['powerid']], 'slot_index': index}
        key = digest_json(location)
        require(key not in locations, 'Duplicate enhancement attachment')
        locations.add(key)
        payload = {key: row[key] for key in BOOST_FIELDS[4:]}
        for key, value in payload.items():
            if key in ('categoryname', 'powersetname', 'boostname'):
                require(type(value) is int and value > 0 and value in known,
                        'Enhancement attribute is absent from authenticated mapping')
            elif key in ('var0', 'var1', 'var2', 'var3'):
                require(value is None or type(value) in (int, float) and math.isfinite(value),
                        'Enhancement floating value is invalid')
                if value is None or value == 0:
                    payload[key] = 0.0
            else:
                require(value is None or type(value) is int and 0 <= value <= 0x7fffffff,
                        'Enhancement integer value is invalid')
                if value is None:
                    payload[key] = 0
        result.append({'location': location, 'payload': payload})
    return sorted(result, key=digest_json)


def stock_power_preservation(previous, current, attributes, *, native_sha256, data_sha256):
    """Preserve permanent powers while recognizing one stock temporary lifecycle.

    Native packing row numbers are not power identity. Commuter is explicitly
    deletable and finite-lived in the authenticated stock definition. Observing
    its addition/expiry is not independent proof of DayJob grant eligibility.
    Unknown temporary powers and every changed/lost permanent power fail closed.
    """
    if native_sha256 != SERVER_TEXTURE_EXCLUSION_MAP or data_sha256 != STOCK_DAYJOB_DATA_INPUTS:
        return None
    delta = stock_power_delta(previous, current, attributes)
    if (delta.get('status') != 'observed' or delta.get('current_native_indexes_contiguous') is not True
            or delta['changed_prior_powers']):
        return None
    names = {row['id']: row['name'].casefold() for row in attributes}
    def temporary(row):
        return ('.'.join(names[row[key]] for key in ('categoryname', 'powersetname', 'powername'))
                == COMMUTER_POWER.casefold()
            and (row['powerlevelbought'] is None or type(row['powerlevelbought']) is int
                 and 0 <= row['powerlevelbought'] <= 49)
            and all(row[key] is None for key in ('powernumboostsbought', 'powersetlevelbought', 'buildnum')))
    before = {row['uniqueid']: row for row in previous}
    after = {row['uniqueid']: row for row in current}
    removed = [before[uid] for uid in delta['deleted_uniqueids']]
    added = [item['selected_row'] for item in delta['added_powers']]
    if (len(removed) + len(added) > 1 or any(not temporary(row) for row in removed + added)
            or any(sum(temporary(row) for row in rows) > 1 for rows in (previous, current))):
        return None
    return {'format': 1, 'verified': True,
        'scope': 'permanent_power_identity_and_authentic_stock_temporary_lifecycle',
        'before_power_rows_sha256': digest_json(previous), 'saved_power_rows_sha256': digest_json(current),
        'permanent_powers_preserved': True, 'packing_indexes_reserialized': True,
        'temporary_power': COMMUTER_POWER if removed or added else None,
        'temporary_lifecycle': 'added' if added else 'removed' if removed else 'unchanged',
        'dayjob_grant_verified': False, 'login_eligibility_verified': False,
        'spatial_predicates_verified': False, 'badge_predicates_verified': False,
        'native_mapserver_sha256': native_sha256, 'definition_sha256': data_sha256.copy(),
        'native_source_sha256': STOCK_DAYJOB_NATIVE_INPUTS.copy(),
        'added_uniqueids': [row['uniqueid'] for row in added],
        'removed_uniqueids': [row['uniqueid'] for row in removed],
        'sql_game_mutations_performed': False}


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
 'patch_sha256': '66653e01f415ba00f8e65655b8e9db1e1bbb21d76dd54b3bb4741ea13032671b',
 'source_sha256': {'DBServer/src/container_sql.c': '0becda9957c9cbe35b11fa28d4c62ad63af5f08faf492bd0013746dadfbec4fc',
                   'libs/UtilitiesLib/src/utils/utils.c': '9ed817dc9dd6233fe5e06d7d0958ff9ae87aaec9c159d0c86dd8b129f55a1ecf'},
 'patched_sha256': {'DBServer/src/container_sql.c': '8eaae13bf59dbee9b76ee0c3dff447eef080eb83e943f546ba0da70d0b42c295',
                    'libs/UtilitiesLib/src/utils/utils.c': 'ebcb8d4a08f752abc9f7e9e4cbf7434f977f4144e93f269ee15402bf62353cff'},
 'unchanged_thread_support_sha256': {'libs/UtilitiesLib/src/utils/quick_sprintf.c': '3808e4e601395e94c31a67b6acb075364e1d51c0ef3f1d3599ab06ece6d81d7b',
                                     'libs/UtilitiesLib/src/components/EString.c': 'b8aed7538139a6d910d9e6f408d13a6eefdb421a6d5fb753884a3e092d739de8',
                                     'libs/UtilitiesLib/include/utilitieslib/components/EString.h': 'a13e7b17a67c6f56bad4a6d833b8ed09625e858372be29a8c809bc336e1e664c',
                                     'libs/UtilitiesLib/include/utilitieslib/UtilsCXX/taskthread.hpp': '70a7f4bfbe172ba3a7ee7f9daf77e2d8504176e66c61016fa29d9e99c038c2de'},
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
 'startup_thread_name_contract': {'scope': 'x_beginthreadex_diagnostic_name_storage_only',
                                  'name': 'complete_source_filename_and_line',
                                  'storage': 'temporary_EString_released_after_synchronous_SetThreadName',
                                  'retained': ['CRT_thread_creation_arguments_and_result',
                                               'caller_thread_id_or_local_fallback',
                                               'assertYouMayFreezeThisThread',
                                               'SetThreadName_API',
                                               'assertion_policy',
                                               'global_quick_sprintf'],
                                  'source_path_length_limit': False,
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
        installed['startup_thread_name'] = value['levelup_ui_repair_build_input']['startup_thread_name_contract']
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


def entity_records(logs, *, map_id=1):
    """Yield IMPORTANT records from the two stock owned-server log routes.

    The embedded DbServer log server adds the Atlas map instance/host/DbServer
    prefix. If its connection fails, UtilitiesLib writes locally with level 0.
    """
    require(type(map_id) is int and map_id in (1, 5), 'Unsupported native entity log map')
    instance = 'City_01_01' if map_id == 1 else 'City_01_02'
    pattern = re.compile(r'^(?P<timestamp>\d{6} \d{2}:\d{2}:\d{2}) '
        r'(?:(?P<local_level>0)|(?P<map_instance>(?i:' + instance + r')_1):127\.0\.0\.1:127\.0\.0\.1) +'
        r'(?P<message>[^\r\n]+)$')
    for name, text in logs:
        path = Path(name)
        if path.parts[:1] == ('map-' + str(map_id),):
            path = Path(*path.parts[1:])
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


def logout_record(logs, *, map_id=1):
    """Record the owned entity's live logout timer, not its underlying cause.

    A normal CLIENT_DISCONNECT and a still-linked stalled client can both take
    this timer path. Explicit command delivery must be bound separately.
    """
    pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ \[Disconnect:Logout timer expired\] [^\r\n]+$')
    for message, record in entity_records(logs, map_id=map_id):
        if pattern.fullmatch(message):
            return dict(record, reason='Logout timer expired', account=ACCOUNT, name=CHARACTER,
                source='current_owned_server_entity_log_live_client_logout_timer')
    return None


def reopen_connection_binding(proof, session, client_pid, now_utc_ms):
    """Bind the existing native/DbServer proof, including the owned monorail lane.

    This recognizes no new readiness by itself. The bridge record must already
    have passed native process/sequence and independent DbServer status checks.
    Legacy Atlas producers retain their original contact binding contract.
    """
    import stationary_contact_evidence as contact
    ready = proof.get('client_ready_evidence') if type(proof) is dict else None
    if type(ready) is not dict or ready.get('source') != 'current_owned_mapserver_monorail_ready':
        return contact.binding(proof, session, client_pid, now_utc_ms)
    if not (type(session) is str and re.fullmatch(r'[0-9a-f]{32}', session)
            and contact.positive_int(client_pid) and type(now_utc_ms) is int
            and proof.get('session_id') == session and type(proof.get('client_pid')) is int
            and proof['client_pid'] == client_pid and type(proof.get('character_id')) is int
            and proof['character_id'] == 1 and type(proof.get('map_id')) is int
            and proof['map_id'] in (1, 5) and contact.positive_int(proof.get('auth_id'))
            and proof.get('name') == CHARACTER and proof.get('account') == ACCOUNT
            and all(proof.get(key) is True for key in ('existing_character_verified',
                'preserved_existing_identity', 'reopen_verified', 'native_client_ready_observed',
                'connected_on_supported_map', 'db_map_assignment_observed', 'monorail_enabled'))
            and type(proof.get('mapserver_producer')) is dict
            and proof['mapserver_producer'].get('mapserver_sha256') == SERVER_TEXTURE_EXCLUSION_MAP
            and type(proof.get('character_progress_guard')) is dict
            and proof['character_progress_guard'].get('passed') is True
            and type(proof.get('client_ready_observed_utc_ms')) is int
            and 0 < proof['client_ready_observed_utc_ms'] <= now_utc_ms
            and ready.get('kind') == 'ready' and ready.get('session_id') == session
            and ready.get('loaded_world_assets') is True and ready.get('name') == CHARACTER
            and ready.get('account') == ACCOUNT and ready.get('log_route') == 'immediate_owned_mapserver_console'
            and type(ready.get('db_id')) is int and ready['db_id'] == 1
            and type(ready.get('auth_id')) is int and ready['auth_id'] == proof['auth_id']
            and type(ready.get('map_id')) is int and ready['map_id'] == proof['map_id']
            and contact.positive_int(ready.get('windows_pid')) and type(ready.get('pid')) is int
            and ready['pid'] == ready['windows_pid']
            and contact.positive_int(ready.get('main_thread_id')) and type(ready.get('tid')) is int
            and ready['tid'] == ready['main_thread_id']
            and contact.positive_int(ready.get('sequence'))
            and type(ready.get('port')) is int and 0 < ready['port'] <= 65535
            and type(ready.get('request')) is int and ready['request'] == 0
            and type(ready.get('target')) is int and ready['target'] == 0
            and type(ready.get('position')) is list and len(ready['position']) == 3
            and all(type(value) in (int, float) and value == 0 for value in ready['position'])
            and type(ready.get('utc_ms')) is int
            and 0 < ready['utc_ms'] <= proof['client_ready_observed_utc_ms']
            and re.fullmatch(r'[0-9a-f]{64}', str(ready.get('line_sha256', '')))):
        return None
    return {'session_id': session, 'client_pid': client_pid, 'character_id': 1,
        'auth_id': proof['auth_id'], 'map_id': proof['map_id'], 'name': CHARACTER, 'account': ACCOUNT,
        'client_ready_observed_utc_ms': proof['client_ready_observed_utc_ms'],
        'scope': 'previously_validated_current_session_monorail_and_dbserver_connection',
        'native_log_contains_character_db_id': False, 'native_log_contains_session_or_client_pid': False,
        'native_ready_line_sha256': ready['line_sha256']}


def native_reward_windows(proof, current, logout_ms, *, session, client_pid, now_utc_ms):
    history = proof.get('reward_connection_history')
    if history is None:
        return [(current, logout_ms)]
    transfers = proof.get('reward_connection_transfers')
    if not (type(history) is list and 1 <= len(history) <= 5 and type(transfers) is list
            and len(transfers) == len(history) - 1):
        return None
    connections = [reopen_connection_binding(item, session, client_pid, now_utc_ms) for item in history]
    if (any(item is None or item['auth_id'] != current['auth_id'] for item in connections)
            or connections[-1] != current):
        return None
    windows = []
    for index, leg in enumerate(transfers):
        prior, following = connections[index:index + 2]
        if type(leg) is not dict:
            return None
        delivery = leg.get('delivery')
        depart = delivery.get('native_station_departure') if type(delivery) is dict else None
        before_ready = history[index]['client_ready_evidence']
        after_ready = history[index + 1]['client_ready_evidence']
        if not (leg.get('arrival_native_verified') is True and type(leg.get('same_client_pid')) is int
                and leg['same_client_pid'] == client_pid
                and (leg.get('from_map_id'), leg.get('to_map_id')) == (prior['map_id'], following['map_id'])
                and prior['map_id'] != following['map_id']
                and type(delivery) is dict and delivery.get('session_id') == session
                and type(delivery.get('client_pid')) is int and delivery['client_pid'] == client_pid
                and type(delivery.get('character_id')) is int and delivery['character_id'] == 1
                and (delivery.get('from_map_id'), delivery.get('to_map_id')) == (prior['map_id'], following['map_id'])
                and type(delivery.get('sent_utc_ms')) is int
                and prior['client_ready_observed_utc_ms'] <= delivery['sent_utc_ms']
                < following['client_ready_observed_utc_ms'] <= logout_ms
                and type(depart) is dict and depart.get('source') == 'current_owned_mapserver_monorail_station_departure'
                and depart.get('kind') == 'station_departure' and depart.get('session_id') == session
                and depart.get('name') == CHARACTER and depart.get('account') == ACCOUNT
                and type(depart.get('db_id')) is int and depart['db_id'] == 1
                and type(depart.get('auth_id')) is int and depart['auth_id'] == current['auth_id']
                and type(depart.get('pid')) is int and depart['pid'] == before_ready['windows_pid']
                and type(depart.get('tid')) is int and depart['tid'] == before_ready['main_thread_id']
                and type(depart.get('sequence')) is int and depart['sequence'] > before_ready['sequence']
                and type(depart.get('request')) is int and 0 < depart['request'] < depart['sequence']
                and type(depart.get('utc_ms')) is int and depart['utc_ms'] == delivery['sent_utc_ms']
                and (depart.get('map_id'), depart.get('target')) == (prior['map_id'], following['map_id'])
                and re.fullmatch(r'[0-9a-f]{64}', str(depart.get('line_sha256', '')))
                and evidence._same(leg.get('native_ready'), after_ready)):
            return None
        windows.append((prior, delivery['sent_utc_ms']))
    windows.append((current, logout_ms))
    return windows


def native_reward_credit_evidence(logs, proof, delivery, logout, *, session, client_pid, now_utc_ms):
    """Bind exact stock point credits to the already validated owned connection.

    Native reward lines have neither a character DB ID nor a session/PID. Their
    THORHERO:COHLOCAL identity and owned Atlas route are bound through the prior
    reopen/ready proof. This reads evidence only; it never awards game points.
    """
    import stationary_contact_evidence as contact
    import task_gate_evidence as task
    identity = reopen_connection_binding(proof, session, client_pid, now_utc_ms)
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
    if not identity['client_ready_observed_utc_ms'] <= end_ms <= now_utc_ms:
        return None
    windows = native_reward_windows(proof, identity, end_ms, session=session,
        client_pid=client_pid, now_utc_ms=now_utc_ms)
    if windows is None:
        return None
    credits, seen, candidate_count = [], set(), 0
    for identity, end_ms in windows:
        ready_ms = identity['client_ready_observed_utc_ms']
        values = task.records(logs, ready_ms, end_ms, map_id=identity['map_id'])
        if values is None:
            return None  # An over-bound/truncated inventory is never credit proof.
        credits.extend(value for value in values if value['kind'] == 'reward')
        # The retained task parser deduplicates logger routes. For point changes,
        # refuse repeated positive credits instead of guessing whether two identical
        # records represent one mirrored award or two real awards in one second.
        instance = 'City_01_01' if identity['map_id'] == 1 else 'City_01_02'
        route_pattern = re.compile(r'^(?P<timestamp>\d{6} \d{2}:\d{2}:\d{2}) '
            r'(?:(?P<local_level>[02])|(?P<map_instance>(?i:' + instance + r')_1):127\.0\.0\.1:127\.0\.0\.1) +'
            r'(?P<message>[^\r\n]+)$')
        for name, text in logs:
            path = Path(name)
            if path.parts[:1] == ('map-' + str(identity['map_id']),):
                path = Path(*path.parts[1:])
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
                    key = (identity['map_id'], stamp, message)
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
        'scope': 'owned_supported_map_exact_native_point_credits_before_ordinary_logout',
        'connection': identity, 'ready_utc_ms': ready_ms, 'logout_utc_ms': end_ms,
        'reward_connection_windows': [{'connection': connection, 'end_utc_ms': end}
                                      for connection, end in windows],
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


ANIMATION_COUNTER_LINE = re.compile(rb'^COH_ANIM_CERT_V1 schema=1 pack=([0-9a-f]{64}) '
    rb'opened=(\d{1,20}) certified=(\d{1,20}) fallback=(\d{1,20}) crypto_failed=(\d{1,20}) raw_bytes=(\d{1,20}) '
    rb'hash_us=(\d{1,20}) stock_us=(\d{1,20}) skipped_rot_keys=(\d{1,20}) skipped_pos_keys=(\d{1,20}) '
    rb'scanned_rot_keys=(\d{1,20}) scanned_pos_keys=(\d{1,20})$')
ANIMATION_COUNTER_KEYS = ('opened', 'certified', 'fallback', 'crypto_failed', 'raw_bytes',
    'hash_us', 'stock_us', 'skipped_rot_keys', 'skipped_pos_keys', 'scanned_rot_keys', 'scanned_pos_keys')


def observe_animation_counter_bytes(state, output):
    """Observe complete source-pinned rows from this owned console only.

    A missing/partial/malformed row is unknown evidence, never activation or
    readiness. Scan append bytes once and retain at most one bounded partial row.
    """
    import native_map_startup_contract as startup
    size, offset = len(output), state.get('offset', 0)
    if size < offset:
        state['observation'] = {'status': 'unknown_console_truncated', 'observed': False}
        state['offset'], state['tail'] = size, b''
        return True
    raw = state.get('tail', b'') + bytes(output[offset:size])
    lines = raw.split(b'\n')
    state['offset'], state['tail'] = size, lines.pop()[-4096:]
    changed = False
    for line in lines:
        match = ANIMATION_COUNTER_LINE.fullmatch(line.rstrip(b'\r'))
        if match is None or match[1].decode() != startup.PACK_SHA256:
            continue
        values = {name: int(match[index + 2]) for index, name in enumerate(ANIMATION_COUNTER_KEYS)}
        if (any(value > 2**64 - 1 for value in values.values())
                or values['certified'] + values['fallback'] > values['opened']):
            continue
        rows = state.get('rows', 0)
        if rows >= 64:
            continue
        state['rows'] = rows + 1
        state['observation'] = {'status': 'actual_owned_native_console_counter', 'observed': True,
            'pack_sha256': match[1].decode(), 'counter_rows_observed': state['rows'], **values}
        changed = True
    return changed


def observe_ready_fx_provider(runtime, prepared_runtime_identity, prepared_payload):
    """Once-only optional private FX byte observation after native readiness.

    Reads one bounded no-follow descriptor, retaining provider/ancestor ownership
    and before/after identity. This observes remaining cache bytes, not which
    provider the native loader opened. Failure is an explicit unknown receipt.
    """
    started, total = time.monotonic(), 0
    result = {'status': 'unknown', 'observed': False, 'actual_payload': None,
        'payload_bytes_hashed': 0, 'hash_elapsed_seconds': None,
        'native_provider_open_observed': False,
        'native_provider_open_status': 'unknown_without_native_io_trace',
        'projected_payload_present': None, 'full_original_payload_present': None,
        'matches_preparation_payload': None}
    descriptor = None
    try:
        if runtime is None:
            raise ValueError('Owned runtime path unavailable')
        runtime = Path(runtime)
        root = runtime.lstat()
        actual_root = {'device': root.st_dev, 'inode': root.st_ino, 'uid': root.st_uid,
                       'mode': stat.S_IMODE(root.st_mode)}
        if not stat.S_ISDIR(root.st_mode) or actual_root != prepared_runtime_identity:
            raise ValueError('Prepared private runtime identity changed')
        ancestors = {}
        for directory in (runtime, runtime / 'data', runtime / 'data/bin'):
            info = directory.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != root.st_uid:
                raise ValueError('Private FX ancestor changed or is linked')
            ancestors[directory] = server_fx_catalog._unchanged_leaf(info)
        provider = runtime / server_fx_catalog.TARGET
        descriptor = os.open(provider, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != root.st_uid
                or not 0 < info.st_size <= server_cache_package.MAX_FILE):
            raise ValueError('FX provider is not a bounded owned single-link regular file')
        before = server_fx_catalog._unchanged_leaf(info)
        if server_fx_catalog._unchanged_leaf(provider.lstat()) != before:
            raise ValueError('FX descriptor/path provider differs')
        digest = hashlib.sha256()
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            for raw in iter(lambda: source.read(1024 * 1024), b''):
                total += len(raw)
                if total > info.st_size:
                    raise ValueError('Private FX provider grew during observation')
                digest.update(raw)
        if (total != info.st_size or server_fx_catalog._unchanged_leaf(os.fstat(descriptor)) != before
                or server_fx_catalog._unchanged_leaf(provider.lstat()) != before
                or any(server_fx_catalog._unchanged_leaf(directory.lstat()) != old
                       for directory, old in ancestors.items())):
            raise ValueError('Private FX provider/ancestor changed during observation')
        pin = {'bytes': total, 'sha256': digest.hexdigest()}
        result.update(status='actual_owned_private_fx_bytes_after_native_ready', observed=True,
            actual_payload=pin, projected_payload_present=pin == server_fx_catalog.PROJECTED,
            full_original_payload_present=pin == server_fx_catalog.BASE,
            matches_preparation_payload=pin == prepared_payload)
    except (OSError, ValueError) as failure:
        result.update(status='unknown_optional_fx_observation_failed', reason=str(failure)[:200])
    finally:
        if descriptor is not None: os.close(descriptor)
        result.update(payload_bytes_hashed=total,
                      hash_elapsed_seconds=round(time.monotonic() - started, 6))
    return result


class LocalCharacterServer(login.LocalLoginServer):
    require_empty_account = False
    requires_saved_character = False
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

    def initialize(self):
        """Check the requested operation against SQL before starting Wine.

        An initialized PostgreSQL profile is not evidence that native creation
        ever saved a character. Resuming that first creation is explicit and
        never removes or replaces the persistent profile.
        """
        resume = getattr(self.owner.args, 'resume_empty_profile', False)
        require(type(resume) is bool, 'Invalid first-creation resume request')
        self.creation_report['resume_first_creation_requested'] = resume
        require(not (self.requires_saved_character and resume),
                'First-creation resume is separate from saved-character reopen')
        if not self.requires_saved_character:
            if resume:
                require(self.profile.is_dir() and not self.profile.is_symlink()
                        and login.profile_record(self.profile / 'profile.json')['initialized'] is True,
                        'Resume first character creation requires the existing initialized profile; preserve all data')
            else:
                require(not self.profile.exists() and not self.profile.is_symlink(),
                        'Character profile already exists; use Resume first character creation only if it has no characters')
        super().initialize()
        reused = self.report.get('profile_reused') is True
        require(self.requires_saved_character or reused is resume,
                'First-creation request does not match persistent profile reuse; preserve all data')
        presence = self.sql("SELECT CASE WHEN to_regclass('dbo.ents') IS NULL THEN 'missing' ELSE 'present' END;", game=True)
        require(presence in ('missing', 'present'), 'Character inventory table identity is unreadable; preserve all data')
        inventory = self.inventory() if presence == 'present' else []
        require(type(inventory) is list, 'Character inventory is unreadable; preserve all data')
        eligibility = {'format': 1, 'checked_before_wine': True,
            'operation': 'reopen_saved_character' if self.requires_saved_character else
                'resume_first_creation' if resume else 'fresh_first_creation',
            'resume_first_creation_requested': resume, 'profile_reused': reused,
            'inventory_table_present': presence == 'present', 'character_count': len(inventory),
            'empty_inventory_verified': not inventory, 'sql_game_mutations_performed': False,
            'committed_character_rows_verified': False, 'eligible': False}
        self.creation_report['profile_eligibility'] = eligibility
        self.ctx.report['character_profile_eligibility'] = eligibility
        if self.requires_saved_character:
            require(inventory,
                    'No saved THORHERO exists in this preserved profile. Use Resume first character creation, then save normally before Reopen.')
            require(all(type(row) is dict and set(row) == set(evidence.IDENTITY_FIELDS)
                        and type(row.get('name')) is str and type(row.get('authname')) is str
                        and type(row.get('containerid')) is int and row['containerid'] > 0
                        and type(row.get('authid')) is int and 0 < row['authid'] <= 4294967295
                        for row in inventory),
                    'Character inventory contains incomplete or invalid identities; preserve all data and export the report')
            candidates = [row for row in inventory
                          if row.get('name', '').casefold() == CHARACTER.casefold()
                          or row.get('containerid') == 1]
            require(len(candidates) == 1, 'Expected exactly the saved THORHERO ID 1; preserve all characters')
            identity = candidates[0]
            auth_id = identity.get('authid')
            require(type(identity.get('containerid')) is int and identity['containerid'] == 1
                    and identity.get('name') == CHARACTER and identity.get('authname') == ACCOUNT
                    and type(auth_id) is int and 0 < auth_id <= 4294967295
                    and [row for row in inventory if row.get('authid') == auth_id] == [identity],
                    'Saved THORHERO identity differs from the accepted local character; preserve all characters')
            rows = self.character_rows(1)
            parents = rows.get('ents', [])
            require(len(parents) == 1 and type(parents[0].get('logincount')) is int
                    and 0 < parents[0]['logincount'] < 2**31 - 1,
                    'Saved THORHERO has no committed login baseline; preserve all data and export the report')
            snapshot = validate_character_rows(rows, inventory, inventory,
                self.schema['expected_attributes'], auth_id,
                existing_identity=identity, expected_login_count=parents[0]['logincount'])
            require(snapshot is not None,
                    'Saved THORHERO powers or costume are incomplete; preserve all data and export the report')
            eligibility['committed_character_rows_verified'] = True
        else:
            require(not inventory,
                    'First character creation requires a completely empty inventory. Existing characters were preserved; use Reopen for saved THORHERO.')
            high_water = self.sql("SELECT dbo.coh_container_high_water('dbo.ents'::regclass);", game=True) if presence == 'present' else '0'
            require(high_water == '0',
                    'This empty profile has already allocated character IDs. Creation ID 1 cannot be qualified; preserve all data and export the report instead of resetting it.')
            eligibility.update(character_id_high_water=0, supported_first_character_id=1)
        eligibility['eligible'] = True

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
        phase_at, phases = prepared_at, {}
        self.creation_report['server_preparation_phase_seconds'] = phases

        def checkpoint(name):
            nonlocal phase_at
            now = time.monotonic()
            phases[name], phase_at = round(now - phase_at, 6), now

        super().prepare_runtime()
        checkpoint('base_schema_and_native_runtime')
        source = self.owner.work / 'data'
        require(source.is_dir() and not source.is_symlink(), 'Verified private client data is missing')
        receipt = self.ctx.report.get('client_worktree', {})
        require(receipt.get('imported_inputs_readonly') is True,
                'Atlas requires the already protected private client worktree')
        import zone_asset_package
        self.zone_asset_document = None
        self.zone_asset_exclusions = set()
        if zone_asset_package.present(self.owner.args.assets):
            self.zone_asset_document = zone_asset_package.package(self.owner.args.assets)
            self.zone_asset_exclusions = {name[5:] for name in self.zone_asset_document['files']}
            import kings_row_beacon_package
            _, kings_lock = kings_row_beacon_package.read_manifest(
                self.owner.args.assets / kings_row_beacon_package.MANIFEST,
                self.owner.args.assets / kings_row_beacon_package.LOCK)
            self.kings_row_beacon_lock = kings_lock
            self.kings_row_beacon_graph = {'verified': True, 'map_id': 5,
                'installation_deferred': True, 'native_graph_readback_qualified': True,
                'physical_zoning_verified': False, 'manifest_sha256': kings_lock['manifest']['sha256']}
            self.creation_report['kings_row_beacon_graph'] = self.kings_row_beacon_graph
            self.ctx.report['kings_row_beacon_graph'] = self.kings_row_beacon_graph
        if zone_asset_package.present(self.owner.args.assets, audio=True):
            audio_document = zone_asset_package.package(self.owner.args.assets, audio=True)
            self.zone_asset_exclusions.update(name[5:] for name in audio_document['files'])
        required_geometry = None
        if (self.owner.args.assets / 'atlas-beacons.zip').exists() or (self.owner.args.assets / 'atlas-beacon-manifest.json').exists():
            import atlas_beacon_package
            geometry_preparation = atlas_beacon_package.ensure_required_geometry(
                self.owner.work, self.owner.args.assets, self.ctx)
            required_geometry = geometry_preparation['identity']
            self.creation_report['atlas_required_geometry'] = geometry_preparation
            self.ctx.report['atlas_required_geometry'] = geometry_preparation
        checkpoint('required_original_geometry')
        # Wine FolderCache does not enumerate directory symlinks as directories.
        # Mirror actual directories as the accepted client worktree does, then
        # link individual immutable files. Keep caches/configuration private.
        source_info = source.stat()
        cache_native_package = self.data_cache_native_package()
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
                'source_commit': cache_native_package.get('source_commit', device.SOURCE_COMMIT),
                'data_commit': cache_native_package.get('data_commit', device.DATA_COMMIT),
                'files': cache_native_package['files']})).hexdigest()}
        if required_geometry is not None:
            identity['required_geometry'] = required_geometry
        projection = server_input_projection(self.map_package)
        if projection is not None:
            identity['server_input_projection'] = projection
            self.creation_report['server_input_projection'] = dict(projection)
        self.server_data_identity = identity
        self.server_data_receipt = receipt
        initial_map = self.initial_map_preparation()
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
        checkpoint('native_dependencies_and_manual_atlas')
        if initial_map == 5 or (initial_map == 1 and self.requires_saved_character
                and getattr(self, 'overlap_client_initialization', False) is True):
            # The saved location is authoritative before native startup. Both
            # supported saved worlds use the authenticated minimal DbServer
            # layout and their own map runtime. Atlas reuses the same cache
            # generation as an earlier real return trip; the live DbServer's
            # schema/configuration is never moved under the running process.
            self.atlas_preparation_deferred = True
            self.creation_report['atlas_preparation_deferred'] = {
                'reason': ('saved_character_starts_in_kings_row' if initial_map == 5 else
                           'saved_atlas_owned_map_client_initialization'), 'map_id': initial_map,
                'dbserver_layout': 'authenticated_minimal_private_runtime',
                'atlas_native_started': False, 'atlas_data_mirror_started': False,
                'atlas_graph_prepared': False, 'sql_game_mutations_performed': False}
            return
        self.prepare_atlas_data(self.runtime, identity, receipt, prepared_at, phases, checkpoint)

    def accept_added_temporary_powers(self, before, after):
        """ARM64 option: accept a reopen whose only power change is a server grant.

        Ordinary play can receive a temporary power (Thor 0.13.39 reopen:
        temporary_powers.temporary_powers.brawl_tranq). The existing delta
        resolver must show every prior power preserved by uniqueid with all
        semantic fields, contiguous native indexes, nothing deleted or changed,
        and only added rows resolving under temporary_powers. The x86 client
        keeps the original strict comparison unchanged.
        """
        if os.environ.get('COH_CLIENT_ARCH', 'x86') != 'arm64':
            return False
        delta = stock_power_delta(before['rows']['powers'], after['rows']['powers'],
            self.schema['expected_attributes']['attributes'])
        added = delta.get('added_powers') or []
        accepted = (delta.get('prior_powers_preserved_by_uniqueid') is True
            and delta.get('all_prior_semantic_fields_preserved') is True
            and delta.get('current_native_indexes_contiguous') is True
            and delta.get('deleted_uniqueids') == [] and delta.get('changed_prior_powers') == []
            and delta.get('after_power_count') == delta.get('before_power_count', -1) + len(added)
            and len(added) > 0 and all(isinstance(item.get('resolved_power'), str)
                and item['resolved_power'].startswith('temporary_powers.') for item in added))
        if accepted:
            self.creation_report['accepted_temporary_power_grants'] = {'format': 1,
                'policy': 'arm64_added_temporary_powers_only', 'power_delta': delta,
                'sql_game_mutations_performed': False}
        return accepted

    def initial_map_preparation(self):
        """Creation and the legacy Atlas reopen retain their qualified layout."""
        return 1

    def prepare_atlas_data(self, runtime, identity, receipt, prepared_at, phases, checkpoint):
        """Prepare exactly one private Atlas provider, on initial use or demand."""
        source = self.owner.work / 'data'
        self.data_cache = server_data_cache.ServerDataCache(self.owner.root, identity,
            self.owner.args.session_id, self.ctx,
            legacy_identity_validator=lambda old: self.legacy_data_identity_matches(old, identity, receipt))
        reused = self.data_cache.checkout(runtime / 'data')
        checkpoint('server_data_cache_checkout')
        if reused:
            for name in self.schema['files']:
                server_data_cache.ServerDataCache.restore_schema(self.schema_dir / name,
                                                                  runtime / name, runtime)
            staged = dict(self.data_cache.record['stats'], linked_immutable_files=0,
                          copied_private_files=0, preserved_schema_files=len(self.schema['files']))
            checkpoint('warm_schema_restore')
        else:
            staged = self.stage_map_data(source, runtime / 'data', cache_recorder=self.data_cache)
            checkpoint('cold_server_data_mirror')
            self.data_cache.seal(runtime / 'data', staged)
            checkpoint('cold_server_data_receipt_seal')
        if self.map_package.get('native_monorail') is not None:
            # A reviewed MapServer-only bridge must retain the exact parser and
            # schema ancestry before donor caches can accelerate a fresh install.
            # Fail closed on an unproved binary instead of quietly parsing cold.
            self.creation_report['server_cache_native_compatibility'] = server_cache_package.verify_mapserver_compatibility(
                runtime / 'MapServer.exe', self.map_package)
        try:
            donor_identity = server_cache_package.build_expected_identity(runtime / 'data',
                runtime / 'MapServer.exe', mapserver_package=self.map_package)
            self.creation_report['prepared_server_caches'] = server_cache_package.install(
                self.owner.args.assets / server_cache_package.ARCHIVE, runtime / 'data',
                donor_identity, context=self.ctx)
        except (ValueError, OSError) as failure:
            # Derived caches are optional. Exact native/source mismatches leave
            # existing generated bins and the ordinary loader fully in charge.
            self.creation_report['prepared_server_caches'] = {'format': 1,
                'status': 'skipped_native_fallback', 'reason': str(failure)[:300], 'installed_files': 0}
        checkpoint('prepared_server_definition_caches')
        self.creation_report['server_fx_catalog'] = server_fx_catalog.install(
            self.owner.args.assets, runtime, context=self.ctx,
            mapserver_package=self.map_package)
        self.ctx.report['server_fx_catalog'] = self.creation_report['server_fx_catalog']
        checkpoint('server_fx_catalog')
        # The stock Pig reader can consume unchanged animation bytes without
        # moving or invalidating the preserved server data/cache generation.
        # An invalid present package fails preparation; never launch a bad pig.
        animation = self.owner.args.assets / 'server-animations.pigg'
        animation_manifest = self.owner.args.assets / 'server-animation-manifest.json'
        if animation.exists() or animation_manifest.exists():
            import server_animation_package
            installed = server_animation_package.install(animation, animation_manifest,
                runtime, context=self.ctx, mapserver_package=self.map_package)
            self.creation_report['server_animation_pack'] = installed
            self.ctx.report['server_animation_pack'] = installed
        checkpoint('server_animation_pack')
        beacon_archive = self.owner.args.assets / 'atlas-beacons.zip'
        beacon_manifest = self.owner.args.assets / 'atlas-beacon-manifest.json'
        if beacon_archive.exists() or beacon_manifest.exists():
            import atlas_beacon_package
            installed = atlas_beacon_package.install(beacon_archive, beacon_manifest,
                runtime, context=self.ctx,
                imported_inputs_readonly=receipt.get('imported_inputs_readonly'),
                mapserver_package=self.map_package,
                input_proof_sink=lambda proof: setattr(self, 'atlas_collision_input_proof', proof),
                source_cache_identity=self.data_cache.identity, owner_root=self.owner.root,
                source_input_proof=getattr(self, 'kings_collision_input_proof', None),
                source_input_manifest_sha256=getattr(self, 'kings_row_beacon_lock', {}).get('manifest', {}).get('sha256'))
            self.creation_report['atlas_beacon_graph'] = installed
            self.ctx.report['atlas_beacon_graph'] = installed
        checkpoint('atlas_beacon_graph')
        self.creation_report['private_map_data'] = {'source_worktree': self.owner.work.name,
            'imported_inputs_readonly': True, 'private_server_config': True,
            'private_cache_roots': ['bin', 'geobin', 'server/bin'],
            'directory_layout': 'real_directories_with_individual_immutable_file_links',
            'preparation_elapsed_seconds': round(time.monotonic() - prepared_at, 6),
            'preparation_phase_seconds': dict(phases),
            'server_data_cache': self.data_cache.summary, **staged}
        self.record_startup_preparation(1, runtime,
            self.creation_report.get('server_fx_catalog', {}),
            self.creation_report.get('server_animation_pack', {}),
            self.creation_report.get('atlas_beacon_graph', {}),
            self.creation_report['private_map_data']['preparation_elapsed_seconds'], phases)
        # A collision certificate is useful only until the other supported
        # world has its own durable proof. Do not retain both 8,000-leaf Python
        # inventories for the gameplay lifetime once both runtimes exist.
        self.kings_collision_input_proof = None
        if getattr(self, 'kings_row_prepared', None) is not None:
            self.atlas_collision_input_proof = None

    def prepare_atlas_runtime(self):
        """Build Atlas for its selected saved startup or actual native transfer.

        The live DbServer keeps its original schema and credential paths. The
        new Atlas process receives its own data/cache/config tree; no mutable
        directory is renamed under a running native service.
        """
        if not getattr(self, 'atlas_preparation_deferred', False):
            return self.runtime
        if getattr(self, 'atlas_map_runtime', None) is not None:
            require(getattr(self, 'atlas_runtime_prepared', False),
                    'Earlier Atlas preparation did not complete; preserve data and export')
            return self.atlas_map_runtime
        target = self.runtime.with_name(self.runtime.name + '-atlas-park')
        require(not target.exists() and not target.is_symlink(), 'Atlas session runtime already exists')
        target.mkdir(mode=0o700)
        (target / 'data').mkdir(mode=0o700)
        (target / 'tools').mkdir(mode=0o700)
        # Record ownership immediately so failed preparation remains attributable
        # and only proved cleanup can return a checked-out cache generation.
        self.atlas_map_runtime = target
        for name in self.schema['files']:
            destination = target / name
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            server_data_cache.ServerDataCache.restore_schema(self.schema_dir / name, destination, target)
        self.copy_kings_native_dependencies(target)
        started = phase_at = time.monotonic()
        phases = {}
        def checkpoint(name):
            nonlocal phase_at
            now = time.monotonic()
            phases[name], phase_at = round(now - phase_at, 6), now
        self.prepare_atlas_data(target, self.server_data_identity, self.server_data_receipt,
                                started, phases, checkpoint)
        config = target / 'data/server/db/servers.cfg'
        server_data_cache.ServerDataCache.restore_schema(self.runtime / 'data/server/db/servers.cfg', config, target)
        self.atlas_runtime_prepared = True
        self.creation_report['atlas_preparation_deferred'].update(
            atlas_data_mirror_started=True, atlas_graph_prepared=True,
            completed_on_demand=True, runtime=target.name)
        return target

    def persist_startup_observation(self):
        """Retain bounded activation evidence even before character acceptance."""
        rows = self.creation_report.get('map_startup_observation')
        if not rows:
            return
        self.ctx.report['map_startup_observation'] = rows
        state = getattr(self.ctx, 'state', None)
        if state is None:  # Isolated host fixtures have no report state directory.
            return
        value = {'format': 1, 'session_id': self.owner.args.session_id,
            'status': 'observations_only', 'physical_startup_gain_validated': False,
            'maps': rows}
        try:
            raw = json.dumps(base.redacted_value(value, self.ctx.secrets), indent=2) + '\n'
            require(len(raw.encode()) <= 256 * 1024, 'Startup observation exceeded bounded receipt')
            base.private_write(Path(state) / 'map-startup-observation.json', raw)
            # Recovery already carries this normal state file. Never upgrade
            # running/failed character acceptance because observations exist.
            document = json.dumps(base.redacted_value(self.ctx.report, self.ctx.secrets), indent=2) + '\n'
            base.private_write(Path(state) / 'latest-report.json', document)
        except (OSError, base.DiagnosticError) as failure:
            self.creation_report['map_startup_observation_write_failure'] = str(failure)[:200]

    def record_startup_preparation(self, map_id, runtime, fx, animation, graph, elapsed, phases):
        runtime = Path(runtime)
        actual_map = server_cache_package.file_pin(runtime / 'MapServer.exe')
        declared_map = self.map_package['files']['MapServer.exe']
        require(actual_map['sha256'] == declared_map['sha256']
                and (declared_map.get('bytes', declared_map.get('size')) in (None, actual_map['bytes'])),
                'Startup observation found a different installed MapServer')
        provider = runtime / server_fx_catalog.TARGET
        fx_observation = {'status': fx.get('status', 'unknown'),
            'logical_provider': server_fx_catalog.TARGET, 'actual_payload': None,
            'private_owned_regular_provider': False, 'projected_payload_present': False,
            'native_provider_open_observed': False, 'native_provider_open_status': 'unknown_without_native_io_trace'}
        if os.path.lexists(provider):
            info = provider.lstat()
            if stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == runtime.lstat().st_uid:
                fx_observation['actual_payload'] = server_cache_package.file_pin(provider)
                fx_observation['private_owned_regular_provider'] = True
                fx_observation['projected_payload_present'] = fx_observation['actual_payload'] == server_fx_catalog.PROJECTED
        root_info = runtime.lstat()
        row = {'format': 1, 'map_id': map_id, 'runtime': runtime.name,
            'private_runtime_identity': {'device': root_info.st_dev, 'inode': root_info.st_ino,
                'uid': root_info.st_uid, 'mode': stat.S_IMODE(root_info.st_mode)},
            'preparation_finished_utc_ms': int(time.time() * 1000), 'preparation_elapsed_seconds': elapsed,
            'preparation_phase_seconds': dict(phases), 'actual_installed_mapserver': actual_map,
            'source_package_mapserver_pin_equal': True, 'launched': False, 'launcher_pid': None,
            'native_ready_verified': False, 'native_ready_elapsed_seconds': None,
            'server_fx_provider': fx_observation,
            'animation_storage': {'installed': animation.get('installed', False), 'payload': animation.get('pigg'),
                'native_certificate': {'status': 'unknown_until_actual_owned_console_counter', 'observed': False}},
            'collision_input_proof': {key: graph.get(key) for key in ('status', 'input_validation',
                'input_files_checked', 'input_payload_bytes_hashed', 'input_full_byte_proof_reused_files',
                'input_full_byte_proof_reused_bytes', 'input_full_byte_proof_reuse_policy',
                'input_validation_basis', 'input_full_byte_proof_reuse_basis', 'same_process_shared_certificate_exported')},
            'gameplay_or_collision_parity_certified_by_observation': False}
        self.creation_report.setdefault('map_startup_observation', {})[str(map_id)] = row
        self.persist_startup_observation()

    def sample_startup_observation(self, *, force=False):
        rows = getattr(self, 'creation_report', {}).get('map_startup_observation', {})
        if not rows:
            return
        now = time.monotonic()
        if not force and now < getattr(self, '_startup_observation_next', 0):
            return
        self._startup_observation_next = now + 10
        maps = dict(getattr(self, 'maps', {}))
        if self.map_process is not None and not maps:
            maps[1] = {'process': self.map_process, 'ready': self.creation_report.get('map_ready') is True}
        scans = getattr(self, '_startup_observation_scans', None)
        if scans is None:
            scans = self._startup_observation_scans = {}
        changed = False
        for map_id, owned in maps.items():
            row, child = rows.get(str(map_id)), owned.get('process')
            if row is None or child is None:
                continue
            runtime = (getattr(self, 'kings_row_runtime', None) if map_id == 5
                       else getattr(self, 'atlas_map_runtime', getattr(self, 'runtime', None)))
            if row['launcher_pid'] is None:
                if runtime is not None:
                    actual = server_cache_package.file_pin(Path(runtime) / 'MapServer.exe')
                    require(actual == row['actual_installed_mapserver'],
                            'Owned launched MapServer differs from the prepared byte proof')
                    row['actual_launched_mapserver'] = actual
                    arguments = getattr(child.process, 'args', None)
                    row['launch_path_binding_observed'] = (isinstance(arguments, (list, tuple))
                        and base.windows_path(Path(runtime) / 'MapServer.exe') in arguments
                        and '--chdir=' + str(runtime) in arguments)
                row.update(launched=True, launcher_pid=child.process.pid,
                    launch_utc_ms=owned.get('launch_utc_ms', getattr(self, 'map_launch_utc_ms', None)),
                    native_process_launch_binding='exact_owned_ctx_start_child_for_this_private_runtime')
                changed = True
            scan = scans.setdefault(child, {})
            if observe_animation_counter_bytes(scan, getattr(child, 'output', b'')):
                row['animation_storage']['native_certificate'] = scan['observation']
                changed = True
            if owned.get('ready') is True and row['native_ready_verified'] is False:
                row.update(native_ready_verified=True,
                    native_ready_elapsed_seconds=round(now - child.started, 6),
                    native_ready_time_scope='sampled_upper_bound_after_owned_existing_protocol_tick_gate; observer_delay_not_bounded')
                row['server_fx_provider']['post_native_ready'] = observe_ready_fx_provider(
                    runtime, row['private_runtime_identity'], row['server_fx_provider']['actual_payload'])
                changed = True
        if changed or force:
            self.persist_startup_observation()

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

    def data_cache_native_package(self):
        """Retain an authenticated data generation across this narrow overlay.

        The native startup contract proves the unchanged directory, parser,
        schema and dependency ancestry. Actual candidate bytes are checked
        independently; cache ownership and source validation still run in full.
        """
        package = self.map_package
        if 'native_map_startup' not in package:
            return package
        import native_map_startup_contract as startup
        proof = startup.verify_current_map(self.map_package_dir / 'MapServer.exe', package)
        self.creation_report['server_data_cache_native_consumer'] = dict(proof,
            cache_identity_policy='retain_authenticated_station_donor_data_generation')
        return startup.previous_package(package)

    def legacy_data_identity_matches(self, previous, current, receipt):
        """Qualify wrapper-only legacy keys without moving their source root.

        A legacy key contained the complete client/MapServer wrapper receipts.
        Bind its old client receipt to the fully checked worktree lineage, and
        prove the old native closure rather than trusting wrapper equivalence.
        The cache's normal closed-owner/immutable/private checks run afterward.
        """
        if not isinstance(previous, dict):
            return False
        if 'server_input_projection' in current and 'server_input_projection' not in previous:
            # Retain a fully authenticated closed full-tree generation. Extra
            # immutable client textures are harmless to this exact native
            # consumer, and need not force another costly cold mirror.
            current = dict(current)
            current.pop('server_input_projection')
            if previous == current:
                return True
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
            self.data_cache.release(getattr(self, 'atlas_map_runtime', self.runtime) / 'data', self.owner.cleanup_status)
        if hasattr(self, 'kings_row_data_cache'):
            self.kings_row_data_cache.release(self.kings_row_runtime / 'data', self.owner.cleanup_status)

    def copy_kings_native_dependencies(self, target):
        """Keep Atlas's qualified DbServer replacement scoped to Atlas only."""
        dependencies = {}
        manual = getattr(self, 'manual_atlas_startup', None)
        for name, pin in self.map_package['files'].items():
            source = self.runtime / name
            origin = 'owned_atlas_runtime'
            if name == 'DbServer.exe' and manual is not None:
                manifest = self.owner.args.assets / 'startup-dbserver-manifest.json'
                require(type(manual) is dict and manual.get('enabled') is True
                        and manual.get('base_package_archive_changed') is False
                        and manual.get('other_native_targets_changed') is False
                        and manifest.is_file() and not manifest.is_symlink()
                        and base.file_hash(manifest) == manual.get('manifest_sha256'),
                        'Kings preparation requires the verified Atlas-only DbServer supplement')
                document = dbserver.load_json(manifest, 2 * 1024 * 1024)
                replacement = document.get('files', {}).get(name, {})
                require(document.get('replacement_scope') == 'fresh_owned_manual_atlas_runtime_DbServer.exe_only'
                        and document.get('base_normal_executable') == pin
                        and replacement.get('sha256') == manual.get('executable_sha256')
                        and source.is_file() and not source.is_symlink()
                        and source.stat().st_size == replacement.get('bytes')
                        and base.file_hash(source) == replacement.get('sha256'),
                        'Installed Atlas manual DbServer differs from its qualified supplement')
                # Kings starts only its MapServer. Its unused DbServer member
                # retains the stock game-package closure; Atlas remains the
                # sole running DbServer with the qualified save/read repair.
                source = self.map_package_dir / name
                origin = 'verified_original_game_package'
            require(source.is_file() and not source.is_symlink()
                    and source.stat().st_size == pin['bytes'] and base.file_hash(source) == pin['sha256'],
                    'Kings native dependency differs from its qualified source: ' + name)
            destination = target / name
            require(not destination.exists() and not destination.is_symlink(), 'Kings native dependency already exists')
            shutil.copyfile(source, destination); destination.chmod(0o400)
            require(destination.stat().st_size == pin['bytes'] and base.file_hash(destination) == pin['sha256'],
                    'Copied Kings native dependency differs: ' + name)
            dependencies[name] = {'source': origin, 'bytes': pin['bytes'], 'sha256': pin['sha256']}
        return dependencies

    def prepare_kings_row_runtime(self):
        """One owned Map 5 tree, prepared on first native station request only.

        Immutable baseline inputs are linked, private caches/configuration copied,
        and precisely the 52 additional collision leaves overlaid. The full
        client supplement never enters either server's collision inventory.
        """
        if getattr(self, 'kings_row_prepared', None) is not None:
            return self.kings_row_prepared
        import zone_asset_package
        import kings_row_beacon_package
        require(getattr(self, 'zone_asset_document', None) is not None
                and getattr(self, 'kings_row_beacon_graph', {}).get('verified') is True,
                'Kings Row package and native graph qualification are required')
        started = time.monotonic()
        phase_at, phases = started, {}
        self.creation_report['kings_row_preparation_phase_seconds'] = phases

        def checkpoint(name):
            nonlocal phase_at
            now = time.monotonic()
            phases[name], phase_at = round(now - phase_at, 6), now

        target = self.runtime.with_name(self.runtime.name + '-kings-row')
        require(not target.exists() and not target.is_symlink(), 'Kings Row session runtime already exists')
        target.mkdir(mode=0o700); (target / 'data').mkdir(mode=0o700)
        self.kings_row_runtime = target
        source_identity = (self.server_data_identity if hasattr(self, 'server_data_identity')
                           else self.data_cache.identity)
        identity = dict(source_identity,
            map_id=5, kings_collision_sha256=self.zone_asset_document['kings_row_collision_files_sha256'],
            kings_graph_manifest=self.kings_row_beacon_lock['manifest'])
        receipt = getattr(self, 'server_data_receipt', self.ctx.report.get('client_worktree', {}))
        cache = server_data_cache.ServerDataCache(self.owner.root, identity,
            self.owner.args.session_id, self.ctx,
            legacy_identity_validator=lambda old: self.legacy_data_identity_matches(old, identity, receipt))
        self.kings_row_data_cache = cache
        reused = cache.checkout(target / 'data')
        checkpoint('server_data_cache_checkout')
        for name in self.schema['files']:
            destination = target / name
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            server_data_cache.ServerDataCache.restore_schema(self.schema_dir / name, destination, target)
        if reused:
            staged = dict(cache.record['stats'], linked_immutable_files=0, copied_private_files=0)
        else:
            staged = self.stage_map_data(self.owner.work / 'data', target / 'data', cache_recorder=cache)
        checkpoint('warm_schema_restore' if reused else 'cold_server_data_mirror')
        geometry = zone_asset_package.install(target, self.owner.args.assets, self.ctx, collision_only=True)
        checkpoint('required_original_collision_geometry')
        if not reused:
            known = set(cache.directory_names)
            targets = world.resolve_targets(target, self.zone_asset_document['kings_row_collision_files'], self.ctx)
            for leaf in targets.values():
                relative = leaf.relative_to(target / 'data')
                for parent in reversed(relative.parents):
                    name = '' if parent == Path('.') else parent.as_posix()
                    if name not in known:
                        cache.observe(parent, target / 'data' / parent, None, False); known.add(name)
                        staged['directories'] += 1
                # This finite overlay is owned regular data, not an immutable
                # link to the imported source; retain the strict cache validator.
                cache.private_names.append(relative.as_posix())
            staged['files'] += len(targets)
            staged['bytes'] += sum(pin['bytes'] for pin in self.zone_asset_document['kings_row_collision_files'].values())
            staged['copied_private_files'] += len(targets)
            cache.seal(target / 'data', staged)
        checkpoint('server_data_receipt_seal')
        dependencies = self.copy_kings_native_dependencies(target)
        # Preserve the current private DbServer connection, including its stock
        # logging policy. Never reuse a cached session's credential file.
        config = target / 'data/server/db/servers.cfg'
        server_data_cache.ServerDataCache.restore_schema(self.runtime / 'data/server/db/servers.cfg', config, target)
        checkpoint('native_dependencies_and_session_configuration')
        cache_compatibility = server_cache_package.verify_mapserver_compatibility(target / 'MapServer.exe', self.map_package)
        donor = server_cache_package.build_expected_identity(target / 'data', target / 'MapServer.exe',
            mapserver_package=self.map_package)
        prepared_caches = server_cache_package.install(self.owner.args.assets / server_cache_package.ARCHIVE,
            target / 'data', donor, context=self.ctx)
        checkpoint('prepared_server_definition_caches')
        fx_catalog = server_fx_catalog.install(self.owner.args.assets, target, context=self.ctx,
            mapserver_package=self.map_package)
        checkpoint('server_fx_catalog')
        import server_animation_package
        animation = server_animation_package.install(self.owner.args.assets / 'server-animations.pigg',
            self.owner.args.assets / 'server-animation-manifest.json', target, context=self.ctx,
            mapserver_package=self.map_package)
        checkpoint('server_animation_pack')
        graph = kings_row_beacon_package.install(self.owner.args.assets / kings_row_beacon_package.ARCHIVE,
            self.owner.args.assets / kings_row_beacon_package.MANIFEST, target, context=self.ctx,
            imported_inputs_readonly=True, lock_path=self.owner.args.assets / kings_row_beacon_package.LOCK,
            source_input_proof=getattr(self, 'atlas_collision_input_proof', None),
            source_cache_identity=source_identity, owner_root=self.owner.root,
            input_proof_sink=lambda proof: setattr(self, 'kings_collision_input_proof', proof))
        checkpoint('kings_row_beacon_graph')
        self.kings_row_beacon_graph = graph
        report = {'runtime': target.name, 'geometry': geometry, 'graph': graph,
            'native_dependencies': dependencies,
            'server_data_cache': cache.summary, 'prepared_server_caches': prepared_caches,
            'server_cache_native_compatibility': cache_compatibility,
            'animation': animation, 'server_fx_catalog': fx_catalog,
            'phase_seconds': dict(phases), 'elapsed_seconds': round(time.monotonic() - started, 6)}
        self.creation_report['kings_row_preparation'] = report
        self.creation_report['kings_row_beacon_graph'] = graph
        self.ctx.report['kings_row_preparation'] = report
        self.record_startup_preparation(5, target, fx_catalog, animation, graph, report['elapsed_seconds'], phases)
        self.kings_row_prepared = {'runtime': target, 'graph': graph, 'preparation': report}
        # The owned Map 5 tree now keeps its own complete durable graph proof.
        # A successful same-process preparation cannot need the Atlas leaf
        # certificate again; failure/cancellation above deliberately retains it.
        self.atlas_collision_input_proof = None
        if self.creation_report.get('atlas_beacon_graph', {}).get('status') in (
                'installed_verified_graph', 'reused_verified_graph'):
            self.kings_collision_input_proof = None
        return self.kings_row_prepared

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
        resolver = server_data_cache.CheckedInputResolver(roots, self.ctx)
        # Imported inputs and generated caches retain their accepted allowance.
        # The verified missing-only supplements are additional immutable files,
        # not generated cache entries; budget their exact pinned inventories too.
        import client_visual_assets as visual
        max_files = device.DATA_COUNT + 4096 + world.FILE_COUNT + len(avatar.ALLOWED) + visual.FILE_COUNT
        max_bytes = device.DATA_BYTES + 1024**3 + world.PAYLOAD_BYTES + avatar.PAYLOAD_BYTES + visual.PAYLOAD_BYTES
        result = {'files': 0, 'bytes': 0, 'directories': 0, 'linked_immutable_files': 0,
                  'copied_private_files': 0, 'preserved_schema_files': 0}
        projection = server_input_projection(getattr(self, 'map_package', None))
        excluded = set(projection['excluded_top_level_directories']) if projection else set()
        if projection is not None:
            self.creation_report['server_input_projection'] = dict(projection)
        pending = [(source, target)]
        next_message = time.monotonic() + 5
        while pending:
            self.ctx.check()
            current, destination = pending.pop()
            info = current.lstat()
            relative = current.relative_to(source)
            if len(relative.parts) == 1 and relative.parts[0].casefold() in excluded:
                require(stat.S_ISDIR(info.st_mode), 'Native-excluded input is not a real directory')
                # No leaf enumeration, hashing, copies or links for a folder
                # this exact MapServer excludes from its own FolderCache.
                continue
            if relative.as_posix().casefold() in getattr(self, 'zone_asset_exclusions', set()):
                # This same client tree may already contain all-zone visuals
                # from an earlier session. Atlas's strict graph proof must stay
                # identical on cold and warm starts; Map 5 overlays only its 52.
                continue
            private = force_private or bool(relative.parts and relative.parts[0] in ('server', 'bin', 'geobin'))
            if stat.S_ISDIR(info.st_mode):
                resolved = resolver.directory(current)
                require(any(root == resolved or root in resolved.parents for root in roots),
                        'Map data directory escaped verified roots')
                # The fresh child is created atomically. Only the bounded
                # schema parents already present need a destination stat;
                # avoid repeated exists/is_dir/recursive mkdir per directory.
                try:
                    if relative.parts:
                        destination.mkdir(mode=0o700)
                    else:
                        destination.mkdir(parents=True, mode=0o700)
                except FileExistsError:
                    destination_info = destination.lstat()
                    require(not stat.S_ISLNK(destination_info.st_mode), 'Linked private destination refused')
                    require(stat.S_ISDIR(destination_info.st_mode), 'Invalid private data directory')
                if cache_recorder is not None:
                    cache_recorder.observe(relative, destination, None, private)
                result['directories'] += 1
                require(result['directories'] <= max_files, 'Map directory count exceeded bound')
                with os.scandir(current) as entries:
                    pending.extend((Path(entry.path), destination / entry.name) for entry in entries)
            else:
                require(stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode), 'Nonregular map input refused')
                resolved, resolved_info = resolver.observed_leaf(current, info)
                result['files'] += 1; result['bytes'] += resolved_info.st_size
                # Include accepted prerequisites/prepared caches and bounded
                # generated client caches in addition to the imported inputs.
                require(result['files'] <= max_files and result['bytes'] <= max_bytes,
                        'Private map data exceeded bound: files=' + str(result['files']) + '/' + str(max_files)
                        + ', bytes=' + str(result['bytes']) + '/' + str(max_bytes))
                private = private or current.suffix.casefold() == '.dbidmap' or bool(resolved_info.st_mode & 0o222)
                if cache_recorder is not None:
                    cache_recorder.observe(relative, destination, resolved, private)
                try:
                    destination_info = destination.lstat()
                except FileNotFoundError:
                    destination_info = None
                if destination_info is not None:
                    require(not stat.S_ISLNK(destination_info.st_mode), 'Linked private destination refused')
                    require(stat.S_ISREG(destination_info.st_mode), 'Invalid staged schema file')
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
                self.ctx.event('stage', status='running', message='Preparing private map data directories', files=result['files'])
                next_message = time.monotonic() + 5
        # The helper is also used by isolated staging callers without a server
        # session report. Integrity verification still runs unconditionally.
        resolution = resolver.verify()
        getattr(self, 'creation_report', {})['cold_mirror_input_resolution'] = resolution
        return result

    def start(self):
        super().start()
        self.capture_baseline()
        self.start_map()

    def capture_baseline(self):
        self.baseline = self.inventory()
        require(not self.baseline,
                'First character creation requires an empty inventory; every existing character was preserved. Export this report instead of deleting it.')
        require(self.sql("SELECT dbo.coh_container_high_water('dbo.ents'::regclass);", game=True) == '0',
                'Character IDs changed before creation; preserve the profile and export the report')
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
        self.persist_startup_observation()
        self.map_process = self.ctx.start('local-character-atlas', ['/usr/bin/env', '--chdir=' + str(self.runtime),
            self.owner.args.wine, base.windows_path(self.runtime / 'MapServer.exe'),
            '-nogui', '-db', '127.0.0.1', '-nosharedmemory', '-nostats', '-udp', '7001', '-tcp', '0', '-map_id', '1',
            '-donotautogroup', *LOCAL_CLIENT_LINK_OPTIONS()],
            env=environment)
        # Use the native production grouping policy. The stock world packet
        # delivers this same flag to the client before it loads Atlas; geometry,
        # collision initialization and CLIENT_READY validation remain required.
        self.creation_report['map_autogroup_policy'] = {'native_option': '-donotautogroup',
            'configured_do_not_auto_group': True, 'policy_basis': 'native_production_default'}
        self.report['mapserver_started'] = self.ctx.report['mapserver_started'] = True
        self.sample_startup_observation(force=True)
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
                    self.sample_startup_observation(force=True)
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

    def map_crash_observation(self):
        console = self.map_process.text()
        crash = re.search(r'Program crash detected|Exception caught: EXCEPTION_[A-Z_]+', console)
        if crash is not None:
            return {'marker': crash.group(), 'console_offset': crash.start(),
                'context': console[max(0, crash.start() - 1000):crash.end() + 1000],
                'console_sha256': hashlib.sha256(console.encode()).hexdigest()}

    def health(self):
        super().health()
        self.sample_startup_observation()
        # Capture exact live leader/worker ownership while the Wine leader is
        # still readable. Android can deny the worker environment after that
        # leader exits; cleanup may then use only a previously authenticated,
        # unchanged worker identity. Sampling is bounded and observational.
        wine_owner = getattr(self.owner, 'wine_owner', None)
        observe = getattr(wine_owner, 'observe_live_lineage', None)
        if observe is not None:
            observe(min(self.ctx.deadline, time.monotonic() + 1),
                    prefix=self.owner.wine_env.get('WINEPREFIX'))
        if self.map_process is not None:
            crash = self.map_crash_observation()
            if crash is not None:
                self.creation_report['mapserver_crash'] = crash
                require(False, 'Atlas crashed: ' + crash['marker'] + '; export the server console and report')
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

    def connected_status(self, sample):
        return evidence.connected_on_atlas(sample)

    def native_logout_record(self):
        return logout_record(self.current_logs())

    def native_positions(self):
        values = self.current_native_events()
        return (native_position_records(self.current_logs()) if values is None
                else character_events.positions_after_ready(values))

    def native_terminal_position(self, delivery, ready_utc_ms, now_utc_ms):
        return native_logout_position(self.current_logs(), delivery, ready_utc_ms, now_utc_ms)

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
        if (getattr(self.owner, 'MANUAL_SESSION', False) and self.requires_saved_character
                and not self.creation_report['connected_on_atlas']):
            # Baseline SQL already authenticated the existing identity. Waiting
            # at character selection must not repeatedly spawn translated status
            # probes until their operation-count limit expires. A current native
            # READY record only triggers the unchanged full SQL/protocol proof;
            # it never grants character connection by itself.
            baseline = self.creation_report.get('baseline', {})
            require(self.creation_report.get('existing_character_verified') is True
                    and type(baseline.get('character_id')) is int
                    and baseline['character_id'] == self.CHARACTER_ID
                    and type(baseline.get('auth_id')) is int and baseline['auth_id'] == self.auth_id,
                    'Manual connection wait lacks the verified saved character identity')
            self.creation_report['character_id'] = baseline['character_id']
            if self.native_ready_record() is None:
                policy = self.ctx.report.setdefault('character_observer_metrics', {}).setdefault(
                    'manual_login_wait', {'policy': 'native_ready_triggers_full_sql_and_protocol_proof',
                        'translated_status_probes_skipped': 0, 'sql_inventory_reads_skipped': 0,
                        'baseline_identity_verified': True, 'connection_claimed': False})
                policy['translated_status_probes_skipped'] += 1
                policy['sql_inventory_reads_skipped'] += 1
                return None
        # After this session's native Atlas connection has been proved, neither
        # SQL inventory nor another translated MapServer.exe -getstatus process
        # adds gameplay liveness: owned service/process checks and current native
        # progress continue independently. Keep optional recovery/task observers
        # active, and require a valid current logout delivery before beginning
        # the unchanged full disconnected/SQL/native-position save proof below.
        # This is a phase transition, never a cached successful save result.
        if self.creation_report['connected_on_atlas']:
            current = self.sample_progress(force=True)
            if not self.live_progress(current): return None
            client_pid = self.creation_report.get('client_pid')
            if type(client_pid) is not int or client_pid <= 0: return None
            delivery = read_logout_delivery(self.owner.args.state / 'character-logout.json',
                self.owner.args.session_id, client_pid, self.creation_report['character_id'],
                self.creation_report.get('client_ready_observed_utc_ms'), int(time.time() * 1000))
            if delivery is None:
                # Retain complete current native event identity/sequence guards,
                # including late malformed or foreign lines. These owned pipe
                # reads (or retained legacy logger reads) are inexpensive; only
                # the competing translated protocol/SQL probes are omitted.
                self.native_ready_record()
                self.observe_connected_character()
                policy = self.ctx.report.setdefault('character_observer_metrics', {}).setdefault(
                    'steady_state_policy', {'policy': 'native_connection_then_delivery_triggered_save',
                        'translated_status_probes_skipped': 0, 'sql_inventory_reads_skipped': 0,
                        'current_native_progress_required': True, 'optional_action_observers_preserved': True,
                        'current_native_event_identity_checks_preserved': True,
                        'fresh_full_save_proof_required': True})
                policy['translated_status_probes_skipped'] += 1
                policy['sql_inventory_reads_skipped'] += 1
                return None
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
        if self.connected_status(sample):
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
        logout = self.native_logout_record()
        if logout is None or not logout_follows_delivery(logout, delivery): return None
        self.creation_report.update(disconnected_before_sql=True, requested_logout_observed=True,
            logout_timer_observed=True, logout_delivery=delivery, logout_timer_evidence=logout)
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
        self.sample_startup_observation(force=True)
        startup = self.creation_report.get('map_startup_observation')
        if startup:
            base.private_write(target / 'map-startup-observation.json',
                json.dumps(base.redacted_value({'format': 1, 'session_id': self.owner.args.session_id,
                    'maps': startup, 'physical_startup_gain_validated': False}, self.ctx.secrets), indent=2) + '\n')
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

    def server_log_roots(self):
        """Only runtimes created by this server session may supply native logs."""
        roots = [(self.runtime, '')] if self.runtime is not None else []
        for attribute, label in (('atlas_map_runtime', 'map-1'), ('kings_row_runtime', 'map-5')):
            path = getattr(self, attribute, None)
            if path is not None and path != self.runtime:
                require(path.parent == self.runtime.parent,
                        'Character map log runtime escaped the owned session root')
                roots.append((path, label))
        return roots

    def server_log_location(self, path):
        matches = [(root, prefix) for root, prefix in self.server_log_roots() if root in path.parents]
        require(len(matches) == 1, 'Server log path escaped its owned runtime')
        root, prefix = matches[0]
        relative = path.relative_to(root).as_posix()
        return root, (prefix + '/' + relative if prefix else relative)

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
        pending = []
        for root, _ in self.server_log_roots():
            require(not root.is_symlink(), 'Linked server log runtime refused')
            if root.exists():
                pending.append((root, False))
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
            records.append((self.server_log_location(path)[1], raw.decode('utf-8', errors='replace')))
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
                        log_root, name = self.server_log_location(path)
                        current = path.parent
                        while True:
                            require(current.is_dir() and not current.is_symlink(), 'Linked server log directory refused')
                            if current == log_root: break
                            require(log_root in current.parents, 'Server log path escaped its owned runtime')
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
    requires_saved_character = True
    CHARACTER_ID = 1

    def __init__(self, owner):
        super().__init__(owner)
        self.baseline_snapshot = None
        self.failed_after_snapshot = None
        self.baseline_enhancements = None
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
        if self.creation_report.get('mapserver_producer', {}).get('mapserver_sha256') == SERVER_TEXTURE_EXCLUSION_MAP:
            boosts = self.sql_rows('boosts', BOOST_FIELDS, ('containerid', 'subid'), 'containerid=1')
            semantic = enhancement_semantics(boosts, rows['powers'], self.schema['expected_attributes']['attributes'])
            self.baseline_enhancements = {'rows': boosts, 'semantic': semantic}
            self.creation_report['enhancement_baseline'] = {'row_count': len(boosts),
                'rows_sha256': digest_json(boosts), 'semantic_sha256': digest_json(semantic),
                'attachment_identity': 'native_PowerID_resolved_to_stable_power_UniqueID',
                'sql_game_mutations_performed': False}
        if self.stock_power_diagnostics_enabled():
            self.creation_report['stock_power_lifecycle_before_login'] = self.stock_power_lifecycle(rows)
        self.ctx.event('existing_character_ready', session_id=self.owner.args.session_id,
            character_id=self.CHARACTER_ID, auth_id=auth_id, account=ACCOUNT, name=CHARACTER,
            existing_character_verified=True, before_login_count=count)

    def stock_power_diagnostics_enabled(self):
        """Supplemental reads belong only to the fully verified new Game lane."""
        if getattr(self.owner, 'client_renderer_attribution', False) is not True:
            return False
        producer = self.ctx.report.get('client_renderer_attribution')
        return (type(producer) is dict and producer.get('verified') is True
            and re.fullmatch(r'[0-9a-f]{64}', str(getattr(self.owner, 'client_executable_sha256', ''))) is not None
            and producer.get('client_executable_sha256') == self.owner.client_executable_sha256
            and re.fullmatch(r'[0-9a-f]{64}', str(producer.get('manifest_sha256', ''))) is not None
            and re.fullmatch(r'[0-9a-f]{40}', str(producer.get('repository_commit', ''))) is not None
            and producer.get('source_freshness_preserved') is True
            and producer.get('renderer_changed') is False)

    def stock_power_lifecycle(self, rows):
        """Optional finite SQL observations; no DayJob eligibility or save pass."""
        result = {'format': 1, 'optional': True, 'status': 'unavailable',
            'dayjob_grant_verified': False, 'login_eligibility_verified': False,
            'spatial_predicates_verified': False, 'sql_game_mutations_performed': False}
        if not self.stock_power_diagnostics_enabled():
            return dict(result, reason='Current typed renderer diagnostic producer is disabled')
        try:
            require(type(rows.get('powers')) is list and 0 < len(rows['powers']) <= POWER_DELTA_LIMIT,
                    'Stock lifecycle power count exceeds finite scope')
            parent = self.sql_rows('ents', ('containerid', 'lastactive'), ('containerid',), 'containerid=1')
            extension = self.sql_rows('ents2', ('containerid', 'subid', 'lastdayjobsstart'),
                                      ('containerid', 'subid'), 'containerid=1')
            fields = ('containerid', 'subid', 'uniqueid', 'numcharges', 'usagetime', 'availabletime', 'creationtime')
            powers = self.sql_rows('powers', fields, ('containerid', 'subid'), 'containerid=1')
            require(len(parent) == 1 and set(parent[0]) == {'containerid', 'lastactive'}
                    and type(parent[0]['containerid']) is int and parent[0]['containerid'] == 1
                    and len(extension) == 1 and set(extension[0]) == {'containerid', 'subid', 'lastdayjobsstart'}
                    and type(extension[0]['containerid']) is int and extension[0]['containerid'] == 1
                    and type(extension[0]['subid']) is int and extension[0]['subid'] == 0,
                    'Stock lifecycle parent identity differs')
            timestamps = {'lastactive': parent[0]['lastactive'], 'lastdayjobsstart': extension[0]['lastdayjobsstart']}
            require(all(value is None or type(value) is str and len(value) <= 64
                    and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}'
                                     r'(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}(?::[0-9]{2})?)?', value)
                    for value in timestamps.values()), 'Stock lifecycle timestamp differs')
            require(len(powers) == len(rows['powers']) and all(type(row) is dict and set(row) == set(fields)
                    for row in powers), 'Stock lifecycle selected columns or count differ')
            for selected, observed in zip(rows['powers'], powers):
                require(all(evidence._same(selected[key], observed[key])
                        for key in ('containerid', 'subid', 'uniqueid'))
                        and all(observed[key] is None or type(observed[key]) is int
                                and 0 <= observed[key] <= 0xffffffff for key in ('numcharges', 'creationtime'))
                        and all(observed[key] is None or type(observed[key]) in (int, float)
                                and math.isfinite(observed[key]) and abs(observed[key]) <= 0x7fffffff
                                for key in ('usagetime', 'availabletime')),
                        'Stock lifecycle power identity or typed values differ')
            result.update(status='observed', timestamps=timestamps, powers=powers,
                lifecycle_rows_sha256=digest_json(powers), selected_power_rows_sha256=digest_json(rows['powers']),
                native_last_time_column='ents.lastactive', last_day_jobs_start_column='ents2.lastdayjobsstart',
                observation_only=True)
        except Exception as error:
            result['reason'] = 'Optional bounded lifecycle observation unavailable: ' + type(error).__name__
        return result

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

    def remember_reward_connection(self):
        proof = self.creation_report
        now_ms = int(time.time() * 1000)
        identity = reopen_connection_binding(proof, self.owner.args.session_id,
            proof.get('client_pid'), now_ms)
        if identity is None or proof.get('monorail_enabled') is not True:
            return
        history = proof.setdefault('reward_connection_history', [])
        if history and history[-1]['client_ready_evidence'] == proof['client_ready_evidence']:
            return
        require(len(history) < 5, 'Reward connection history exceeds the supported native zoning bound')
        keys = ('session_id', 'client_pid', 'character_id', 'auth_id', 'map_id', 'name', 'account',
            'existing_character_verified', 'preserved_existing_identity', 'reopen_verified',
            'native_client_ready_observed', 'connected_on_supported_map', 'db_map_assignment_observed',
            'monorail_enabled', 'mapserver_producer', 'character_progress_guard',
            'client_ready_observed_utc_ms', 'client_ready_evidence', 'connected_on_atlas')
        history.append(json.loads(json.dumps({key: proof[key] for key in keys})))

    def observe_connected_character(self):
        self.remember_reward_connection()
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
        self.native_power_load_normalization = None
        self.native_stock_power_preservation = None
        before = self.baseline_snapshot
        after = validate_character_rows(rows, self.baseline, inventory,
            self.schema['expected_attributes'], self.auth_id,
            existing_identity=before['identity'], expected_login_count=before['login_count'] + 1)
        if after is None:
            return None
        location = self.observe_saved_location()
        if self.baseline_enhancements is not None:
            boosts = self.sql_rows('boosts', BOOST_FIELDS, ('containerid', 'subid'), 'containerid=1')
            comparison = {'verified': False, 'status': 'incomplete',
                'before_rows': self.baseline_enhancements['rows'], 'saved_rows': boosts,
                'before_semantic_sha256': digest_json(self.baseline_enhancements['semantic']),
                'sql_game_mutations_performed': False, 'native_save_failure_proven': False,
                'native_gameplay_inventory_change_independently_verified': False,
                'attachment_identity': 'native_PowerID_resolved_to_stable_power_UniqueID',
                'scope': 'unchanged_enhancement_payload_and_stable_power_attachment',
                'numeric_default_equivalence': 'native_PACKTYPE_INT_FLOAT_NULL_equals_zero_only',
                'numeric_default_source_sha256': BOOST_ZERO_DEFAULT_SOURCE.copy(),
                'reason': 'Saved enhancement rows require typed attachment validation'}
            self.creation_report['enhancement_preservation'] = comparison
            semantic = enhancement_semantics(boosts, after['rows']['powers'], self.schema['expected_attributes']['attributes'])
            equal = evidence._same(self.baseline_enhancements['semantic'], semantic)
            comparison.update(verified=equal, status='verified' if equal else 'incomplete',
                saved_semantic_sha256=digest_json(semantic), reason=('Enhancement payload and attachment preserved'
                if equal else 'Observed enhancement change needs native loot/equipping/combining evidence; '
                    'ordinary logout and saved-location evidence are retained separately'))
            require(equal, 'Character diagnostic incomplete: saved enhancements changed; native inventory '
                    'change is not independently verified. This does not establish a failed native save.')
        if self.stock_power_diagnostics_enabled():
            self.creation_report['stock_power_lifecycle_after_logout'] = self.stock_power_lifecycle(rows)
        # Only the typed current reader repair permits the finite first-training
        # transition or exact stock level-2 auto-set load normalization. It
        # observes stock native success and committed SQL; it
        # supplies no character input and never changes database rows. The
        # authored task profile retains its original strict level/power guards.
        if (isinstance(self.manual_atlas_startup, dict)
                and self.manual_atlas_startup.get('levelup_ui_repair_save') is not None
                and self.creation_report.get('task_gate_required') is not True
                and (not evidence._same(before['rows']['ents'][0]['level'], after['rows']['ents'][0]['level'])
                    or not evidence._same(before['rows']['powers'], after['rows']['powers']))):
            import native_training_save
            now_ms = int(time.time() * 1000)
            receipt = read_logout_delivery(self.owner.args.state / 'character-logout.json',
                self.owner.args.session_id, self.creation_report.get('client_pid'), self.CHARACTER_ID,
                self.creation_report.get('client_ready_observed_utc_ms'), now_ms)
            logs = self.current_logs()
            if not evidence._same(before['rows']['ents'][0]['level'], after['rows']['ents'][0]['level']):
                self.native_training_save = native_training_save.verify(logs, self.creation_report,
                    receipt, logout_record(logs), before['rows'], after['rows'],
                    self.schema['expected_attributes']['attributes'], session=self.owner.args.session_id,
                    client_pid=self.creation_report.get('client_pid'), now_utc_ms=now_ms)
            else:
                self.native_power_load_normalization = native_training_save.verify_reopen_normalization(
                    logs, self.creation_report, receipt, logout_record(logs), before['rows'], after['rows'],
                    self.schema['expected_attributes']['attributes'], session=self.owner.args.session_id,
                    client_pid=self.creation_report.get('client_pid'), now_utc_ms=now_ms)
        if not evidence._same(before['rows']['powers'], after['rows']['powers']):
            self.native_stock_power_preservation = self.stock_power_preservation_evidence(before, after)
        for table in evidence.SELECTED:
            previous = before['rows'][table]
            current = after['rows'][table]
            if table == 'ents':
                previous = [{key: value for key, value in row.items() if key != 'logincount'} for row in previous]
                current = [{key: value for key, value in row.items() if key != 'logincount'} for row in current]
            if (table == 'powers' and not self.saved_selected_rows_match(table, previous, current)
                    and self.accept_added_temporary_powers(before, after)):
                continue
            if not self.saved_selected_rows_match(table, previous, current):
                # A typed SQL snapshot after logout is evidence of the observed
                # difference, not a successful persistence proof. Preserve it
                # even when strict selected-row comparison stops verification.
                delta = stock_power_delta(before['rows']['powers'], after['rows']['powers'],
                    self.schema['expected_attributes']['attributes'])
                failure = {'format': 1, 'status': 'failed', 'failed_table': table,
                    'save_verified': False, 'save_acceptance_changed': False,
                    'after_snapshot_sha256': digest_json(after), 'power_delta': delta}
                self.creation_report['save_comparison_failure'] = failure
                observed = {'format': 1, 'status': 'failed', 'save_verified': False,
                    'failed_table': table, 'snapshot': json.loads(json.dumps(after)),
                    'snapshot_sha256': digest_json(after),
                    'evidence_scope': 'typed_after_logout_SQL_observation_strict_save_comparison_failed'}
                if len((json.dumps(observed, indent=2) + '\n').encode()) <= SNAPSHOT_LIMIT:
                    self.failed_after_snapshot = observed
                    failure['after_snapshot_export_status'] = 'available'
                else:
                    failure['after_snapshot_export_status'] = 'exceeded_bounded_export_scope'
                require(False, 'Committed existing character rows changed after reopen: ' + table)
        self.creation_report.update(saved_position=location['saved_position'],
            saved_native_position_evidence=location['native_position_evidence'],
            committed_native_position_verified=True,
            committed_safe_position_verified=location['requested_recovery_verified'])
        return after

    def observe_saved_location(self):
        """Capture SQL/native location even when another diagnostic fails later."""
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
        positions = self.native_positions()
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
        terminal = self.native_terminal_position(logout,
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
            self.creation_report.update(ground_evidence=ground)
        observation = {'format': 1, 'saved_position': position, 'native_position_evidence': native,
            'sql_location_matches_native_logout': True, 'requested_recovery_verified': requested,
            'complete_character_save_verified': False, 'sql_game_mutations_performed': False}
        self.creation_report['post_logout_location_observation'] = observation
        return observation

    def stock_power_preservation_evidence(self, before, after):
        now_ms = int(time.time() * 1000)
        binding = reopen_connection_binding(self.creation_report, self.owner.args.session_id,
            self.creation_report.get('client_pid'), now_ms)
        if (binding is None or self.creation_report.get('task_gate_required') is True
                or self.baseline_enhancements is None
                or self.creation_report.get('enhancement_preservation', {}).get('verified') is not True):
            return None
        producer = self.creation_report.get('mapserver_producer', {})
        if producer.get('mapserver_sha256') != SERVER_TEXTURE_EXCLUSION_MAP:
            return None
        runtime = (getattr(self, 'kings_row_runtime', None) if binding['map_id'] == 5
                   else getattr(self, 'atlas_map_runtime', None) or self.runtime)
        if runtime is None:
            return None
        hashes = {}
        try:
            for name, expected in STOCK_DAYJOB_DATA_INPUTS.items():
                path = runtime / name
                observations = {}

                def parents(leaf, root):
                    parent = leaf.parent
                    while True:
                        info = parent.lstat()
                        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid(),
                                'Stock lifecycle definition parent is not owned and real')
                        observations[parent] = server_fx_catalog._unchanged_leaf(info)
                        if parent == root:
                            break
                        require(root in parent.parents, 'Stock lifecycle definition escaped its authenticated root')
                        parent = parent.parent

                parents(path, runtime)
                original = path.lstat()
                observations[path] = server_fx_catalog._unchanged_leaf(original)
                resolved = path
                if stat.S_ISLNK(original.st_mode):
                    # Production mirrors immutable leaves into real runtime
                    # directories. Permit exactly that direct link shape, not
                    # arbitrary link resolution or another source authority.
                    require(self.ctx.report.get('client_worktree', {}).get('imported_inputs_readonly') is True,
                            'Stock lifecycle linked source has no protected input receipt')
                    roots = (self.owner.work.resolve(strict=True), self.owner.args.game_data.resolve(strict=True))
                    saved_roots = getattr(self, 'server_data_identity', {}).get('source_roots')
                    require(saved_roots == [{'path': str(root),
                        'identity': server_data_cache.fingerprint(root, directory=True)} for root in roots],
                        'Stock lifecycle input root identity changed after preparation')
                    resolved = Path(os.readlink(path))
                    require(resolved.is_absolute() and '..' not in resolved.parts,
                            'Stock lifecycle source link is not the prepared absolute leaf')
                    root = next((root for root in roots if root in resolved.parents), None)
                    require(root is not None, 'Stock lifecycle source escaped the authenticated input roots')
                    parents(resolved, root)
                    leaf = resolved.lstat()
                    require(stat.S_ISREG(leaf.st_mode) and not leaf.st_mode & 0o222,
                            'Stock lifecycle source must be a readonly regular leaf')
                    observations[resolved] = server_fx_catalog._unchanged_leaf(leaf)
                else:
                    require(stat.S_ISREG(original.st_mode), 'Stock lifecycle definition is not a regular leaf')
                fd = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                try:
                    info = os.fstat(fd)
                    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
                        and 0 < info.st_size <= 2 * 1024 * 1024
                        and server_fx_catalog._unchanged_leaf(info) == observations[resolved],
                        'Stock lifecycle definition is unowned, replaced or oversized')
                    with os.fdopen(fd, 'rb', closefd=False) as source:
                        raw = source.read(info.st_size + 1)
                    final = os.fstat(fd)
                    require(server_fx_catalog._unchanged_leaf(info) == server_fx_catalog._unchanged_leaf(final)
                        and len(raw) == info.st_size
                        and all(server_fx_catalog._unchanged_leaf(item.lstat()) == observed
                                for item, observed in observations.items()),
                        'Stock lifecycle definition or input path changed while reading')
                    hashes[name] = hashlib.sha256(raw).hexdigest()
                    require(hashes[name] == expected, 'Stock lifecycle definition differs from accepted native inputs')
                finally:
                    os.close(fd)
        except (OSError, base.DiagnosticError):
            return None
        value = stock_power_preservation(before['rows']['powers'], after['rows']['powers'],
            self.schema['expected_attributes']['attributes'],
            native_sha256=producer['mapserver_sha256'], data_sha256=hashes)
        if value is not None:
            value['connection'] = binding
        return value

    def saved_selected_rows_match(self, table, previous, current):
        """Permit exact awards, first training and finite auto-set normalization."""
        if evidence._same(previous, current):
            return True
        stock = getattr(self, 'native_stock_power_preservation', None)
        if table == 'powers' and isinstance(stock, dict) and stock.get('verified') is True:
            return (digest_json(previous) == stock['before_power_rows_sha256']
                    and digest_json(current) == stock['saved_power_rows_sha256'])
        normalization = getattr(self, 'native_power_load_normalization', None)
        if (table == 'powers' and isinstance(normalization, dict) and normalization.get('verified') is True):
            return (digest_json(previous) == normalization['before_power_rows_sha256']
                    and digest_json(current) == normalization['saved_power_rows_sha256'])
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
        self.remember_reward_connection()
        proof = self.creation_report
        if 'reward_connection_history' in proof:
            proof['reward_connection_transfers'] = json.loads(json.dumps(
                getattr(self, 'zoning_report', {}).get('transfers', [])))
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
        credit = native_reward_credit_evidence(logs, proof, delivery, self.native_logout_record(),
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
                selected_non_reward_rows_preserved=False,
                native_training_values_committed_verified=True,
                native_training_save_evidence=training, saved_internal_level=1,
                saved_displayed_level=2, newly_purchased_power=training['purchased_power'])
        normalization = getattr(self, 'native_power_load_normalization', None)
        if normalization is not None:
            result.update(selected_rows_preservation_policy='strict_baseline_except_login_count_exact_native_point_credits_and_level2_auto_set_load_normalization',
                selected_non_reward_rows_preserved=False,
                native_power_load_normalization_verified=True,
                native_power_load_normalization_evidence=normalization)
        if self.creation_report.get('enhancement_preservation', {}).get('verified') is True:
            result['enhancements_preserved'] = True
        stock = getattr(self, 'native_stock_power_preservation', None)
        if stock is not None:
            result.update(selected_rows_preservation_policy='stable_permanent_power_identity_with_exact_native_rewards_and_stock_temporary_lifecycle',
                native_stock_power_preservation=stock, permanent_powers_preserved=True,
                temporary_power_lifecycle_observed=stock['temporary_lifecycle'],
                dayjob_grant_independently_verified=False)
        return result

    def collect(self, target):
        super().collect(target)
        if self.baseline_snapshot is not None:
            base.private_write(target / 'character-reopen-before-snapshot.json',
                               json.dumps(self.baseline_snapshot, indent=2) + '\n')
        if self.failed_after_snapshot is not None:
            raw = json.dumps(self.failed_after_snapshot, indent=2) + '\n'
            require(len(raw.encode()) <= SNAPSHOT_LIMIT, 'Failed character SQL snapshot exceeded export bound')
            base.private_write(target / 'character-reopen-failed-after-snapshot.json', raw)
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
