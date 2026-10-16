#!/usr/bin/env python3
"""Read-only admission of critical AuthServer ODBC interfaces; never a login proof.

Consumes only the metadata emitted by inspect_schema.sql. No DB connection,
procedure execution, credentials, account rows, or deployment mutation occurs.
"""
import argparse
import hashlib
import json
from pathlib import Path

MAX_INPUT_BYTES = 1024 * 1024
MAX_ROWS = 1024

# CAccount::LoadPassword / Load parameter order, not procedure parameter names.
# SQL binary lengths are bytes. datetime is SQL Server's 8-byte storage type.
PARAMETERS = {
    'ap_GPwd': [('varchar', 14, False), ('binary', 128, True),
                ('tinyint', 1, True), ('int', 4, True)],
    'ap_GStat': [('varchar', 14, False), *[('int', 4, True)] * 7,
                ('tinyint', 1, True), ('datetime', 8, True),
                ('int', 4, True), ('int', 4, True), ('int', 4, True)],
    'get_server_groups': [('int', 4, False)],
}

# Direct reads needed by password loading, account stats, and 128-byte user data.
# This is deliberately a critical subset, not all login/logging/logout tables.
COLUMNS = {
    ('user_auth', 'account'): ('varchar', 14),
    ('user_auth', 'password'): ('binary', 128),
    ('user_auth', 'hash_type'): ('tinyint', 1),
    ('user_auth', 'salt'): ('int', 4),
    ('user_account', 'uid'): ('int', 4),
    ('user_account', 'account'): ('varchar', 14),
    ('user_account', 'queue_level'): ('int', 4),
    ('user_account', 'loyalty_points'): ('int', 4),
    ('user_account', 'loyalty_legacy_points'): ('int', 4),
    ('user_data', 'uid'): ('int', 4),
    ('user_data', 'user_data'): ('binary', 16),
    ('user_data', 'user_data_new'): ('binary', 112),
    ('user_data', 'user_game_data'): ('binary', 16),
    ('user_data', 'user_game_data_new'): ('binary', 112),
    ('user_server_group', 'uid'): ('int', 4),
    ('user_server_group', 'server_group_id'): ('int', 4),
    ('server', 'server_group_id'): ('int', 4),
}


class AdmissionError(ValueError):
    """Only fixed reason codes may cross the diagnostic boundary."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AdmissionError('duplicate_json_key')
        result[key] = value
    return result


def read_metadata(path):
    # read(limit+1) also bounds a file that grows after inspection. No symlink or
    # regular-file policy is claimed: this read-only CLI is run by its operator.
    with path.open('rb') as stream:
        payload = stream.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise AdmissionError('metadata_too_large')
    try:
        data = json.loads(payload, object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(AdmissionError('nonfinite_json')))
    except AdmissionError:
        raise
    except (UnicodeError, ValueError, RecursionError):
        raise AdmissionError('invalid_json') from None
    return data, hashlib.sha256(payload).hexdigest()


def shape(row, keys):
    if not isinstance(row, dict) or set(row) != set(keys):
        raise AdmissionError('metadata_shape')


def string(value, limit=128):
    if not isinstance(value, str) or not 1 <= len(value) <= limit or not value.isascii():
        raise AdmissionError('metadata_string')
    if any(ord(c) < 32 or ord(c) > 126 for c in value):
        raise AdmissionError('metadata_string')
    return value


def integer(value, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise AdmissionError('metadata_integer')
    return value


def boolean(value):
    if type(value) is not bool:
        raise AdmissionError('metadata_boolean')
    return value


def admit(data):
    shape(data, ('schema', 'parameters', 'columns'))
    if data['schema'] != 'coh-auth-critical-schema-v1':
        raise AdmissionError('metadata_version')
    for name in ('parameters', 'columns'):
        if not isinstance(data[name], list) or len(data[name]) > MAX_ROWS:
            raise AdmissionError('metadata_rows')
    procedures = {}
    for row in data['parameters']:
        shape(row, ('schema', 'procedure', 'ordinal', 'type', 'max_length', 'scale', 'output', 'user_defined'))
        owner = string(row['schema'])
        name = string(row['procedure'])
        ordinal = integer(row['ordinal'], 1, MAX_ROWS)
        kind = string(row['type'])
        length = integer(row['max_length'], -1, 32767)
        scale = integer(row['scale'], 0, 38)
        direction = boolean(row['output'])
        alias = boolean(row['user_defined'])
        if owner != 'dbo' or name not in PARAMETERS:
            raise AdmissionError('unexpected_procedure')
        key = (name, ordinal)
        if key in procedures:
            raise AdmissionError('duplicate_parameter')
        procedures[key] = (kind, length, direction, alias, scale)
    columns = {}
    for row in data['columns']:
        shape(row, ('schema', 'table', 'column', 'type', 'max_length', 'user_defined'))
        owner = string(row['schema'])
        key = (string(row['table']), string(row['column']))
        value = (string(row['type']), integer(row['max_length'], -1, 32767), boolean(row['user_defined']))
        if owner != 'dbo' or key not in COLUMNS:
            raise AdmissionError('unexpected_column')
        if key in columns:
            raise AdmissionError('duplicate_column')
        columns[key] = value
    failures = []
    for name, expected in PARAMETERS.items():
        observed = [key for key in procedures if key[0] == name]
        if len(observed) != len(expected):
            failures.append({'code': 'parameter_count', 'interface': name,
                             'expected': len(expected), 'observed': len(observed)})
        for ordinal, value in enumerate(expected, 1):
            actual = procedures.get((name, ordinal))
            if actual != (*value, False, 3 if value[0] == 'datetime' else 0):
                conversion = (name == 'ap_GPwd' and ordinal == 3 and actual == ('int', 4, True, False, 0)) or (
                    name == 'ap_GStat' and ordinal == 10 and actual is not None and
                    actual[0] == 'datetime2' and actual[2:] == (True, False, 3))
                failures.append({'code': 'odbc_conversion_unqualified' if conversion else 'parameter_contract',
                                 'interface': name, 'ordinal': ordinal})
    for key, value in COLUMNS.items():
        if columns.get(key) != (*value, False):
            failures.append({'code': 'column_contract', 'table': key[0], 'column': key[1]})
    return {
        'schema': 'coh-auth-critical-schema-admission-v1',
        'critical_interfaces_compatible': not failures,
        'failures': failures,
        'metadata_only': True,
        'procedure_bodies_verified': False,
        'account_or_server_rows_read': False,
        'complete_schema_compatible': False,
        'deployment_ready': False,
        'real_account_login_verified': False,
        'db_map_handoff_verified': False,
        'native_live_world': False,
        'remaining_checks': ['procedure_body_and_result_semantics', 'full_schema_and_permissions',
                             'x86_odbc_driver_and_connection', 'account_and_shard_registration',
                             'source_binary_config_identity', 'checksum_negative_control',
                             'identified_encrypted_session_and_db_map_handoff'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        data, digest = read_metadata(args.metadata)
        report = admit(data)
        report['metadata_sha256'] = digest
    except (OSError, AdmissionError) as error:
        report = {'schema': 'coh-auth-critical-schema-admission-v1',
                  'critical_interfaces_compatible': False, 'deployment_ready': False,
                  'real_account_login_verified': False,
                  'error': str(error) if isinstance(error, AdmissionError) else 'metadata_io'}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'critical_interfaces_compatible': report['critical_interfaces_compatible'],
                      'deployment_ready': False, 'real_account_login_verified': False}))
    return 0 if report['critical_interfaces_compatible'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
