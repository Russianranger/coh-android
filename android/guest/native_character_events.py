#!/usr/bin/env python3
"""Immediate native observations from the current owned Atlas console pipe."""
import hashlib
import math
import os
import re
import time

if os.name == 'nt':
    # Windows builds qualify this portable parser and the real Win32 producer.
    # The owned Linux runtime has fcntl/proc dependencies, so it is intentionally
    # not imported here. Keep identical fail-closed guard semantics on Windows;
    # Android/Linux still raises the original diagnostic.DiagnosticError type.
    from types import SimpleNamespace

    class DiagnosticError(RuntimeError):
        pass

    def require(condition, message):
        if not condition:
            raise DiagnosticError(message)

    base = SimpleNamespace(DiagnosticError=DiagnosticError, require=require)
else:
    import diagnostic as base

ENVIRONMENT = 'COH_WINE_CHARACTER_EVENTS_SESSION'
PREFIX = 'COH_CHARACTER_EVENT_V1 '
CONTRACT = {
    'format': 1, 'environment_variable': ENVIRONMENT,
    'session_token': '32_lowercase_hex_current_launch',
    'transport': 'owned_mapserver_stdout_complete_flushed_line',
    'prefix': PREFIX.rstrip(), 'disabled_by_default': True,
    'writer': 'mapserver_main_thread', 'sequence': 'positive_u32_monotonic_no_wrap',
    'clock': 'windows_utc_milliseconds',
    'ready_callsite': 'CLIENT_READY_after_resumeCharacter_success',
    'position_callsite': 'stock_30_second_PeriodicInfo_ready_entity_not_transferring',
    'identity': {'map_id': 1, 'name': 'THORHERO', 'account': 'COHLOCAL',
                 'peer': '127.0.0.1', 'db_id': 'positive_current_character',
                 'auth_id': 'positive_current_account',
                 'process_and_thread': 'current_owned_progress_record'},
    'initialization_failure': 'requested_launch_exits_nonzero',
    'changes_native_game_state': False, 'full_collision_geometry_verified': False,
}
EVENT_LIMIT = 4096
NUMBER = r'-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
PATTERN = re.compile(r'^COH_CHARACTER_EVENT_V1 session=(?P<session>[0-9a-f]{32}) '
    r'pid=(?P<pid>[1-9][0-9]*) tid=(?P<tid>[1-9][0-9]*) '
    r'sequence=(?P<sequence>[1-9][0-9]*) kind=(?P<kind>ready|position) '
    r'utc_ms=(?P<utc_ms>[1-9][0-9]*) map_id=1 db_id=(?P<db_id>[1-9][0-9]*) '
    r'auth_id=(?P<auth_id>[1-9][0-9]*) name=THORHERO account=COHLOCAL '
    r'peer=127\.0\.0\.1:(?P<port>[0-9]+) position=<(?P<x>' + NUMBER
    + '),(?P<y>' + NUMBER + '),(?P<z>' + NUMBER + r')>$')


def validate_contract(value):
    base.require(type(value) is dict and value == CONTRACT,
                 'Immediate character native event contract differs')
    return value


def records(console, *, session, progress, launch_utc_ms, now_utc_ms, db_id, auth_id):
    """Bind complete events to the current session, native process and SQL identity.

    The pipe belongs to this launch. The independently read mapped progress
    record binds Windows PID/main thread and still proves completed live ticks.
    Event sequence/time cannot regress or duplicate; routes do not merge.
    """
    base.require(type(console) is str and len(console.encode()) <= 16 * 1024 * 1024,
                 'Immediate character console exceeded bound')
    base.require(type(session) is str and re.fullmatch(r'[0-9a-f]{32}', session)
                 and type(launch_utc_ms) is int and type(now_utc_ms) is int
                 and launch_utc_ms <= now_utc_ms
                 and type(db_id) is int and db_id > 0 and type(auth_id) is int and auth_id > 0
                 and isinstance(progress, dict) and progress.get('available') is True
                 and type(progress.get('windows_pid')) is int and progress['windows_pid'] > 0
                 and type(progress.get('main_thread_id')) is int and progress['main_thread_id'] > 0,
                 'Immediate character observer launch identity is missing')
    result, previous_sequence, previous_time = [], 0, launch_utc_ms - 1000
    for line in console[:console.rfind('\n') + 1].splitlines():
        if PREFIX.rstrip() not in line:
            continue
        match = PATTERN.fullmatch(line)
        base.require(match is not None, 'Malformed immediate native character event')
        values = {key: int(match[key]) for key in
                  ('pid', 'tid', 'sequence', 'utc_ms', 'db_id', 'auth_id', 'port')}
        base.require(match['session'] == session
                     and values['pid'] == progress['windows_pid']
                     and values['tid'] == progress['main_thread_id']
                     and values['db_id'] == db_id and values['auth_id'] == auth_id
                     and values['sequence'] == previous_sequence + 1
                     and values['sequence'] <= 0xffffffff
                     and previous_time <= values['utc_ms'] <= now_utc_ms + 1000,
                     'Immediate native character event differs from this owned launch')
        coordinates = [float(match[key]) for key in ('x', 'y', 'z')]
        base.require(all(math.isfinite(value) and abs(value) <= 1000000 for value in coordinates)
                     and (match['kind'] == 'ready' and 1 <= values['port'] <= 65535
                          and coordinates == [0, 0, 0]
                          or match['kind'] == 'position' and values['port'] == 0),
                     'Immediate native character event fields differ')
        value = dict(values, format=1, kind=match['kind'], session_id=session,
            map_id=1, name='THORHERO', account='COHLOCAL', position=coordinates,
            windows_pid=values['pid'], main_thread_id=values['tid'],
            log_timestamp=time.strftime('%y%m%d %H:%M:%S', time.localtime(values['utc_ms'] / 1000)),
            line_sha256=hashlib.sha256(line.encode()).hexdigest(),
            log_route='immediate_owned_mapserver_console',
            source='current_owned_mapserver_immediate_' + match['kind'])
        result.append(value)
        base.require(len(result) <= EVENT_LIMIT, 'Immediate native character event count exceeded bound')
        previous_sequence, previous_time = values['sequence'], values['utc_ms']
    return result


def latest_ready(values):
    for value in reversed(values):
        if value['kind'] == 'ready':
            return dict(value, loaded_world_assets=True)
    return None


def positions_after_ready(values):
    ready = latest_ready(values)
    if ready is None:
        return []
    return [value for value in values
            if value['kind'] == 'position' and value['sequence'] > ready['sequence']]
