"""Owned post-cleanup collection of the fixed original Map numeric ledger.

The existing source probe supplies only file/child/stream ownership primitives.
Its parser and public schema are not reused for this distinct observer role.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

MAXIMUM = 4096
BASENAME = 'server-initial-ledger.json'
ENVIRONMENT = 'COH_NATIVE_INITIAL_SEND_LEDGER_OUTPUT'
WINDOWS_PATH = r'C:\coh-native-catalog\server-initial-ledger.json'
PUBLIC_SCHEMA = 'coh-server-initial-ledger-admission-v1'
FALSE = ('normal_authentication_qualified', 'source_generation_admitted',
         'actor_publication', 'ack_permitted', 'world_authority')
CONTEXT = ('process_started', 'process_closed', 'handles_closed',
           'owned_cleanup_verified', 'same_groups_transaction_verified',
           'successful_groups_commit_latched', 'same_precreated_file_verified', 'producer_bytes_unchanged')


def require(value):
    if not value:
        raise ValueError('SERVER_INITIAL_LEDGER_REFUSED')


def empty(state='UNAVAILABLE'):
    require(state in ('UNAVAILABLE', 'REFUSED', 'VALID'))
    return {'schema': PUBLIC_SCHEMA, 'state': state, 'diagnostic_only': True,
            **{name: False for name in CONTEXT}, 'ledger': None,
            **{name: False for name in FALSE}}


def paired(report):
    require(type(report) is dict and report.get('schema') == 'coh-private-original-native-groups-run-v1'
            and report.get('passed') is True and report.get('matching_groups_transaction_captured') is True
            and report.get('cleanup_verified') is True and report.get('owned_process_groups_absent') is True
            and report.get('private_character_state') is True and report.get('public_upload_permitted') is False
            and report.get('source_generation_admitted') is False and report.get('world_authority') is False)
    pair = report.get('pair')
    require(type(pair) is dict and pair.get('schema') == 'coh-original-native-groups-pair-v1'
            and pair.get('passed') is True
            and all(pair.get(name) is True for name in ('exact_logical_packet_verified',
                    'same_source_selected_dbid_verified', 'actual_native_owned_receive_verified')))
    return True


def public(value, parse):
    """Reconstruct all fields; arbitrary caller keys and strings never escape."""
    require(type(value) is dict and set(value) == set(empty())
            and value.get('schema') == PUBLIC_SCHEMA
            and value.get('state') in ('UNAVAILABLE', 'REFUSED', 'VALID')
            and value.get('diagnostic_only') is True)
    for name in (*CONTEXT, *FALSE):
        require(type(value[name]) is bool)
    require(all(value[name] is False for name in FALSE))
    result = empty(value['state'])
    result.update({name: value[name] for name in CONTEXT})
    if value['state'] == 'VALID':
        require(all(value[name] for name in CONTEXT))
        # parse owns the separately pinned producer whitelist and invariants.
        import json
        result['ledger'] = parse(json.dumps(value['ledger'], allow_nan=False).encode('ascii'))
    else:
        require(value['ledger'] is None
                and value['successful_groups_commit_latched'] is False
                and value['same_precreated_file_verified'] is False
                and value['producer_bytes_unchanged'] is False)
    return result


def collect(probe, parse, owner, child, report):
    """Read only after the actual Map child and registered streams are closed.

    UNAVAILABLE means no producer bytes. REFUSED means ownership, schema,
    same-GROUPS binding or cleanup was not admitted. A valid ACTIVE snapshot
    remains ACTIVE; process termination never invents a producer final state.
    """
    result = empty()
    result['process_started'] = child is not None
    if child is not None:
        result['process_closed'] = child.poll() is not None
    try:
        result['owned_cleanup_verified'] = report.get('cleanup_verified') is True
        result['same_groups_transaction_verified'] = paired(report)
        if owner is None:
            return public(result, parse), None, None
        require(type(owner) is probe.ProbeOwner and owner.binding is not None)
        result['handles_closed'] = all(stream.closed for stream in owner.binding.streams)
        probe._closed(owner, child)
        raw = probe._read_owned(owner)
        require(len(raw) <= MAXIMUM)
        if not raw:
            return public(result, parse), None, None
        value = parse(raw)
        # This source flag is set only by A's successful same-owner GROUPS
        # commit hook. Merely sharing a filename or a process is insufficient.
        require(value.get('groups_owner_bound') is True)
        probe._closed(owner, child)
        require(probe._read_owned(owner) == raw)
        result.update(state='VALID', successful_groups_commit_latched=True, same_precreated_file_verified=True,
                      producer_bytes_unchanged=True, ledger=value)
        private = {'schema': 'coh-private-server-initial-ledger-binding-v1',
                   'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                   'owned_child_pid': owner.binding.pid,
                   'file_device': owner.file_key[0], 'file_inode': owner.file_key[1],
                   'file_uid': owner.file_key[2],
                   'retained_after_owned_cleanup': True,
                   'public_upload_permitted': False}
        return public(result, parse), private, raw
    except Exception:
        refused = empty('REFUSED')
        refused.update({name: result[name] for name in CONTEXT[:5]})
        return public(refused, parse), None, None


def retain(path, raw, read_private):
    """Create one new private fixed-name receipt; roll back only our inode."""
    path = Path(path)
    require(path.name == BASENAME and type(raw) is bytes and 0 < len(raw) <= MAXIMUM)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    key = None
    success = False
    try:
        info = os.fstat(descriptor)
        key = (info.st_dev, info.st_ino, info.st_uid)
        with os.fdopen(descriptor, 'wb') as stream:
            descriptor = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        require(read_private(path, MAXIMUM) == raw)
        success = True
    finally:
        cleanup_error = None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as error:
                cleanup_error = error
        if not success and key is not None:
            try:
                info = path.lstat()
                if (info.st_dev, info.st_ino, info.st_uid) == key:
                    path.unlink()
            except OSError as error:
                if cleanup_error is None:
                    cleanup_error = error
        if cleanup_error is not None:
            raise cleanup_error
