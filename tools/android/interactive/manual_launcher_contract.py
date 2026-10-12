"""Finite source/native authority for the .35 explicit manual launcher helper."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[3]
ROLE = 'current_pe32_manual_client_launcher'
SOURCE = 'android/native/client-launcher.c'
SOURCE_FILES = (SOURCE, 'tools/android/interactive/manual_launcher_contract.py',
    'tools/android/interactive/package_manual_launcher.py',
    'tools/android/interactive/qualify_manual_launcher_windows.py')
COMPILE_FLAGS = ('-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-static-libgcc', '-mconsole')
LINK_FLAGS = ('-luser32', '-lkernel32')
DLLS = frozenset(('kernel32.dll', 'msvcrt.dll', 'user32.dll'))
DONOR_HELPER = {'bytes': 246319, 'sha256': 'fd8a3724bd009d122fe98e03229e62516b5ee31245db9c093dfaceef73bd11db'}
MANIFEST_NAME = 'manual-client-launcher-build.json'
QUALIFICATION_NAME = 'manual-client-launcher-windows-qualification.json'
EXE_NAME = 'client-launcher.exe'


def require(value, message):
    if not value: raise ValueError(message)


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def file_pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Regular helper input required')
    raw = path.read_bytes()
    require(0 < len(raw) <= 16*1024**2, 'Bounded helper input required')
    return pin(raw)


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()


def exact(actual, expected):
    if type(actual) is not type(expected): return False
    if isinstance(expected, dict):
        return set(actual)==set(expected) and all(exact(actual[key],value) for key,value in expected.items())
    if isinstance(expected, (list,tuple)):
        return len(actual)==len(expected) and all(exact(a,b)for a,b in zip(actual,expected))
    return actual==expected


def source_pins(root=ROOT):
    return {name: file_pin(Path(root)/name) for name in SOURCE_FILES}


def pe32(raw):
    require(128 < len(raw) <= 1024**2 and raw[:2] == b'MZ', 'Bounded PE helper required')
    offset = struct.unpack_from('<I', raw, 0x3c)[0]
    require(offset+26 < len(raw) and raw[offset:offset+4] == b'PE\0\0'
        and struct.unpack_from('<H',raw,offset+4)[0] == 0x14c
        and struct.unpack_from('<H',raw,offset+24)[0] == 0x10b,
        'Actual Windows PE32 i386 helper required')
    return pin(raw)


def validate_build(value, executable, commit, root=ROOT):
    require(type(value) is dict and set(value) == {
        'format','status','role','repository_commit','run_id','run_url','source_files',
        'compiler','compiler_version','compile_flags','link_flags','windows_libraries',
        'executable','previous_helper','game_db_map_recompiled','native_fixture_executed',
        'physical_ayn_thor_validated'}, 'Exact native helper build receipt schema required')
    require(type(value['format']) is int and value['format'] == 1 and value['status']=='built'
        and value['role']==ROLE and value['repository_commit']==commit
        and re.fullmatch('[0-9a-f]{40}',commit) and type(value['run_id']) is int and value['run_id']>0
        and value['run_url']=='https://github.com/Russianranger/coh-android/actions/runs/'+str(value['run_id'])
        and value['source_files']==source_pins(root)
        and value['compiler']=='i686-w64-mingw32-gcc'
        and type(value['compiler_version']) is str and 0<len(value['compiler_version'].encode())<=4096
        and value['compile_flags']==list(COMPILE_FLAGS) and value['link_flags']==list(LINK_FLAGS)
        and value['windows_libraries']==sorted(DLLS)
        and value['previous_helper']==DONOR_HELPER
        and value['game_db_map_recompiled'] is False and value['native_fixture_executed'] is False
        and value['physical_ayn_thor_validated'] is False,
        'Source-bound current helper build authority differs')
    actual = file_pin(executable)
    require(actual == pe32(Path(executable).read_bytes()), 'Actual regular PE helper required')
    require(actual==value['executable'] and actual!=DONOR_HELPER, 'Current native helper bytes required')
    return value


def qualification_cases():
    return sorted(('invalid_mode_refused','invalid_session_refused','missing_game_refused',
        'manual_owned_console_child_exit','manual_owned_interruption_cleanup',
        'creation_mode_retained','local_login_mode_retained','cache_generation_mode_retained',
        'exact_source_deadline_policy_native_fixture'))


def validate_qualification(value, build, executable, commit, root=ROOT):
    validate_build(build, executable, commit, root)
    require(type(value) is dict and set(value)=={
        'format','status','role','repository_commit','run_id','run_url','build_receipt',
        'executable','source_files','executed_cases','skipped','windows_platform',
        'actual_shipping_helper_executed','actual_owned_child_console_verified',
        'deadline_policy_fixture','game_db_map_executed','physical_ayn_thor_validated'},
        'Exact native Windows helper qualification schema required')
    require(type(value['format']) is int and value['format']==1 and value['status']=='passed'
        and value['role']==ROLE and value['repository_commit']==commit
        and value['run_id']==build['run_id'] and type(value['run_id']) is int
        and value['run_url']==build['run_url'] and value['build_receipt']==pin(encoded(build))
        and value['executable']==build['executable'] and value['source_files']==source_pins(root)
        and value['executed_cases']==qualification_cases() and type(value['skipped']) is int and value['skipped']==0
        and value['windows_platform']=='genuine_windows_x86_process_and_console_api'
        and value['actual_shipping_helper_executed'] is True
        and value['actual_owned_child_console_verified'] is True
        and exact(value['deadline_policy_fixture'], {
            'actual_source_function_compiled':True,'simulated_elapsed_hours':48,
            'real_duration_48_hour_run':False,'shipping_helper_binary_modified':False})
        and value['game_db_map_executed'] is False and value['physical_ayn_thor_validated'] is False,
        'Current genuine Windows helper lifecycle proof differs')
    return value
