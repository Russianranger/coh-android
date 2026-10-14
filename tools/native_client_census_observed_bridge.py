#!/usr/bin/env python3
"""Pure bounded observation decoding/parity; no provider or replay authority.

COHCNS1 validation follows the frozen native decoder. One immutable packet and
the bounded directory index remain resident; row projections are yielded.
The caller owns source/runtime/PID/session custody and actual native execution.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import struct

MAGIC = b'COHCNS1\0'
MAX_BYTES, MAX_DIRS, MAX_ROWS = 64 * 1024**2, 16384, 200000
HEADER_BYTES, ROW_BYTES, WFD_BYTES = 64, 328, 320
BRANCHES = ('texture_library', 'object_library', 'fx', 'scripts', 'scripts.loc')
ATTR_MASK = 1 | 2 | 4 | 16
STAT_MARKER = 'COH_NATIVE_FOLDER_STAT_COUNTS_V1'
STAT_SCOPE = 'cumulative_all_thread_local_FolderCache_override_calls_after_PIG_capture_begin'
STAT_FIELDS = ('calls', 'returns_ok', 'returns_failed', 'create_calls', 'create_ok', 'info_calls', 'info_ok')
DECODER_SOURCE_SHA256 = '1748606b4aad4a92fe4aad11c931b3bff35594cb7c70c09fb778f61b4fbcc601'
TIMESTAMP_SOURCE = 'libs/UtilitiesLib/src/utils/winfiletime.c'
TIMESTAMP_HISTORICAL_SOURCE_SHA256 = 'bd1f419d6dda2517ff4a588a0c70f2500d69f7fc6390d5d58da31b54733deb56'
_NO_AUTHORITY = {'provider_authority': False, 'native_registration_allowed': False,
                 'native_replay_allowed': False, 'publication_allowed': False}


def require(value, message):
    if not value:
        raise ValueError(message)


def _uint(value, bits=32):
    return type(value) is int and 0 <= value < 1 << bits


def _token(value, size):
    return type(value) is str and re.fullmatch('[0-9a-f]{' + str(size) + '}', value) is not None


def _component(value):
    return (type(value) is str and 0 < len(value) <= 259 and value.isascii()
            and all(32 <= ord(c) <= 126 for c in value)
            and not any(c in value for c in '/\\:*?"<>|'))


def _path(value):
    return (type(value) is str and len(value) <= 259 and (not value or
            all(_component(part) and part not in ('.', '..') for part in value.split('/'))))


def _string(data, required):
    raw = bytes(data)
    end = raw.find(b'\0')
    require(end >= 0 and (not required or end > 0) and not any(raw[end:]),
            'Canonical native string terminator/tail differs')
    value = raw[:end].decode('ascii')
    require(not value or _component(value), 'Unsupported native component')
    return value


def _projection(data):
    require(len(data) == WFD_BYTES and not any(data[36:44]) and not any(data[318:]),
            'Canonical WFD reserved/padding differs')
    attributes, creation, access, write, high, low = struct.unpack_from('<IQQQII', data)
    return {'name': _string(data[44:304], True), 'alternate': _string(data[304:318], False),
            'attributes': attributes, 'creation_filetime': creation, 'access_filetime': access,
            'write_filetime': write, 'size_high': high, 'size_low': low}


def _consumed(row):
    return {'attributes': row['attributes'] & ATTR_MASK, 'size_low': row['size_low'],
            'write_filetime': row['write_filetime']}


@dataclass(frozen=True, slots=True)
class CensusDirectory:
    path: str
    first: int
    count: int
    ordinal: int


@dataclass(frozen=True, slots=True)
class CensusView:
    packet: bytes
    generation: str
    directories: tuple[CensusDirectory, ...]
    row_count: int
    record_offset: int

    def rows(self, directory):
        require(type(directory) is int and 0 <= directory < len(self.directories),
                'Exact decoded directory ordinal required')
        entry = self.directories[directory]
        for arrival in range(entry.count):
            offset = self.record_offset + (entry.first + arrival) * ROW_BYTES
            yield dict(_projection(memoryview(self.packet)[offset + 8:offset + ROW_BYTES]),
                       directory=directory, arrival=arrival)

    def summary(self):
        return {'format': 1, 'role': 'bounded_source_projected_COHCNS1_view',
                'generation': self.generation, 'bytes': len(self.packet),
                'directories': len(self.directories), 'rows': self.row_count,
                'native_decoder_source_sha256': DECODER_SOURCE_SHA256,
                'decoder_or_native_consumer_executed_by_this_module': False, **_NO_AUTHORITY}


def decode(packet, generation=None):
    """Validate the full native layout/graph; a token is opaque, not authority."""
    require(type(packet) is bytes and HEADER_BYTES <= len(packet) <= MAX_BYTES,
            'Bounded immutable COHCNS1 packet required')
    require(packet[:8] == MAGIC, 'Native census magic differs')
    version, total, directory_count, row_count, record_offset, flags = struct.unpack_from('<6I', packet, 8)
    require(version == 1 and total == len(packet) and flags == 0, 'Native census header differs')
    require(0 < directory_count <= MAX_DIRS and row_count <= MAX_ROWS
            and HEADER_BYTES <= record_offset <= len(packet) and record_offset % 4 == 0
            and row_count * ROW_BYTES == len(packet) - record_offset, 'Native census bounds differ')
    token = packet[32:64].hex()
    if generation is not None:
        require(_token(generation, 64) and generation == token, 'Current opaque generation differs')
    directories, offset, first, previous = [], HEADER_BYTES, 0, None
    for ordinal in range(directory_count):
        require(record_offset - offset >= 16, 'Truncated directory table')
        length, reserved, observed_first, count, observed_ordinal = struct.unpack_from('<HHIII', packet, offset)
        require(length <= 259 and reserved == 0 and observed_first == first and observed_ordinal == ordinal
                and length <= record_offset - offset - 16 and count <= row_count - first,
                'Native directory index/bounds differs')
        path = packet[offset + 16:offset + 16 + length].decode('ascii')
        require(_path(path), 'Native directory path differs')
        require(previous is None or previous.lower() < path.lower(), 'Case-aliased/unordered directories')
        next_offset = (offset + 16 + length + 3) & ~3
        require(next_offset <= record_offset and not any(packet[offset + 16 + length:next_offset]),
                'Native directory padding differs')
        directories.append(CensusDirectory(path, first, count, ordinal))
        offset, first, previous = next_offset, first + count, path
    require(offset == record_offset and first == row_count, 'Native directory closure differs')
    view = CensusView(packet, token, tuple(directories), row_count, record_offset)
    lookup = {entry.path.lower(): entry.ordinal for entry in directories}
    seen = set()
    for entry in directories:
        for arrival, row in enumerate(view.rows(entry.ordinal)):
            raw_offset = record_offset + (entry.first + arrival) * ROW_BYTES
            require(struct.unpack_from('<II', packet, raw_offset) == (entry.ordinal, arrival),
                    'Native row directory/arrival differs')
            if row['name'] in ('.', '..'):
                continue
            child = entry.path + ('/' if entry.path else '') + row['name']
            require(len(child) <= 259, 'Native child path exceeds bound')
            child_ordinal = lookup.get(child.lower())
            if child_ordinal is not None:
                require(row['attributes'] & 16 and child_ordinal not in seen,
                        'Ambiguous native directory membership')
                seen.add(child_ordinal)
            else:
                require(not row['attributes'] & 16, 'Native directory child missing')
    require(0 not in seen and seen == set(range(1, directory_count)), 'Native directory graph has orphan/root edge')
    return view


def _hex(value, size):
    require(_token(value, size * 2), 'Canonical raw observation bytes required')
    return bytes.fromhex(value)


def _readable(value):
    keys = {'attempted', 'create_ok', 'create_error', 'information_ok', 'information_error',
            'close_ok', 'close_error', 'information', 'readable'}
    require(type(value) is dict and set(value) == keys
            and all(type(value[key]) is bool for key in ('attempted', 'create_ok', 'information_ok', 'close_ok', 'readable'))
            and all(_uint(value[key]) for key in ('create_error', 'information_error', 'close_error')),
            'Exact typed native readability observation required')
    raw = _hex(value['information'], 52)
    require(value['readable'] and all(value[key] for key in ('attempted', 'create_ok', 'information_ok', 'close_ok'))
            and not any(value[key] for key in ('create_error', 'information_error', 'close_error')),
            'Positive native readability unavailable')
    return raw


def _observed(observed, generation):
    keys = {'format', 'role', 'status', 'windows_pid', 'windows_thread', 'operation', 'generation', 'ABI',
            'ci_deadline_seconds', 'root', 'directories', 'directory_ends', 'footer', 'provider_authority',
            'native_registration_allowed', 'publication_allowed'}
    require(type(observed) is dict and set(observed) == keys and type(observed['format']) is int
            and observed['format'] == 1 and observed['role'] == 'bounded_native_ANSI_WFD_and_by_handle_observation'
            and observed['status'] == 'complete_observation' and _token(observed['generation'], 64) and observed['generation'] == generation
            and _token(observed['operation'], 32)
            and all(_uint(observed[key]) and observed[key] > 0 for key in ('windows_pid', 'windows_thread'))
            and _uint(observed['ci_deadline_seconds']) and 1 <= observed['ci_deadline_seconds'] <= 900
            and all(observed[key] is False for key in ('provider_authority', 'native_registration_allowed', 'publication_allowed')),
            'Complete typed bound WFD observation required')
    require(type(observed['ABI']) is dict and set(observed['ABI']) == {'pointer_bits', 'WFD_bytes', 'by_handle_bytes', 'header_bytes'}
            and all(type(value) is int for value in observed['ABI'].values())
            and observed['ABI'] == {'pointer_bits': 32, 'WFD_bytes': 320, 'by_handle_bytes': 52, 'header_bytes': 160},
            'Actual native observation ABI differs')
    root = observed['root']
    require(type(root) is dict and set(root) == {'root', 'partial_anchor', 'enumeration_authority', 'by_handle'}
            and type(root['root']) is str and 4 <= len(root['root']) < 260 and root['root'].isascii()
            and re.fullmatch(r'[A-Za-z]:/.*', root['root']) and _path(root['root'][3:])
            and all(not part.endswith(('.', ' ')) for part in root['root'][3:].split('/'))
            and root['partial_anchor'] is True and root['enumeration_authority'] is False
            and struct.unpack_from('<I', _readable(root['by_handle']))[0] & 16,
            'Readable partial native root anchor required')
    directories, ends, footer = observed['directories'], observed['directory_ends'], observed['footer']
    require(type(directories) is list and 5 <= len(directories) <= MAX_DIRS and type(ends) is list
            and len(ends) == len(directories), 'Bounded complete native directory list required')
    require(type(footer) is dict and set(footer) == {'directories', 'rows', 'issues', 'enumeration_complete', 'readability_complete', 'elapsed_ms'}
            and all(_uint(footer[key]) for key in ('directories', 'rows', 'issues')) and _uint(footer['elapsed_ms'], 64)
            and footer['directories'] == len(directories) and footer['rows'] <= MAX_ROWS and footer['issues'] == 0
            and footer['enumeration_complete'] is True and footer['readability_complete'] is True,
            'Complete native footer required')
    result, expected_children, folded_directories, identities, total = {}, set(BRANCHES), set(), set(), 0
    for ordinal, (entry, end) in enumerate(zip(directories, ends)):
        require(type(entry) is dict and set(entry) == {'ordinal', 'parent', 'branch', 'relative', 'by_handle', 'entries'}
                and _uint(entry['ordinal']) and entry['ordinal'] == ordinal and _uint(entry['parent'])
                and _uint(entry['branch']) and entry['branch'] < 5 and _path(entry['relative']) and entry['relative']
                and all(not part.endswith(('.', ' ')) for part in entry['relative'].split('/')),
                'Native directory identity differs')
        path = entry['relative']
        require(path.lower() not in folded_directories, 'Case-aliased native directories')
        folded_directories.add(path.lower())
        if ordinal < 5:
            require(entry['parent'] == 0xffffffff and entry['branch'] == ordinal and path == BRANCHES[ordinal],
                    'Exact native branch roots required')
        else:
            require(entry['parent'] < ordinal and entry['branch'] == directories[entry['parent']]['branch']
                    and path.rpartition('/')[0] == directories[entry['parent']]['relative'],
                    'Native parent membership differs')
        handle_information = _readable(entry['by_handle'])
        attributes = struct.unpack_from('<I', handle_information)[0]
        require(attributes & 16 and not attributes & 1024, 'Unsupported native directory mapping')
        handle_identity = (struct.unpack_from('<I', handle_information, 28)[0],
                           *struct.unpack_from('<II', handle_information, 44))
        require(handle_identity not in identities, 'Native directory identity alias/cycle')
        identities.add(handle_identity)
        require(type(entry['entries']) is list and len(entry['entries']) <= MAX_ROWS - total,
                'Bounded native row list required')
        require(type(end) is dict and set(end) == {'directory', 'rows', 'first_error', 'next_error', 'find_closed', 'close_error'}
                and all(_uint(end[key]) for key in ('directory', 'rows', 'first_error', 'next_error', 'close_error'))
                and type(end['find_closed']) is bool and end['directory'] == ordinal and end['rows'] == len(entry['entries'])
                and ((end['first_error'] == 2 and not end['rows'] and not end['next_error'] and not end['find_closed'] and not end['close_error'])
                    or (end['first_error'] == 0 and end['next_error'] == 18 and end['find_closed'] and not end['close_error'])),
                'Native enumeration completion differs')
        rows, arrivals, folded = {}, [], set()
        for arrival, row in enumerate(entry['entries']):
            require(type(row) is dict and set(row) == {'directory', 'arrival', 'flags', 'wfd', 'by_handle'}
                    and _uint(row['directory']) and row['directory'] == ordinal and _uint(row['arrival']) and row['arrival'] == arrival
                    and _uint(row['flags']) and row['flags'] <= 31, 'Native row attribution/arrival differs')
            wfd = row['wfd']
            require(type(wfd) is dict and set(wfd) == {'name', 'alternate', 'attributes', 'projection', 'mapping_supported',
                    'traversal_alias', 'directory_reparse', 'readonly_required_failed', 'malformed'}
                    and all(type(wfd[key]) is bool for key in ('mapping_supported', 'traversal_alias', 'directory_reparse', 'readonly_required_failed', 'malformed')),
                    'Typed native projection required')
            projected = _projection(_hex(wfd['projection'], 320))
            alias = projected['name'] in ('.', '..')
            require(type(wfd['name']) is str and type(wfd['alternate']) is str and _uint(wfd['attributes'])
                    and all(wfd[key] == projected[key] for key in ('name', 'alternate', 'attributes'))
                    and wfd['mapping_supported'] and not wfd['malformed'] and not wfd['directory_reparse']
                    and not wfd['readonly_required_failed'] and wfd['traversal_alias'] == alias
                    and row['flags'] == (3 if alias else 1)
                    and (alias or not projected['name'].endswith(('.', ' ')))
                    and not (projected['attributes'] & 16 and projected['attributes'] & 1024)
                    and (projected['attributes'] & 16 or projected['attributes'] & 1),
                    'Native projection mapping/flags differs')
            _readable(row['by_handle'])
            if alias:
                continue
            require(projected['name'].lower() not in folded, 'Case-aliased native row membership')
            folded.add(projected['name'].lower())
            rows[projected['name']] = _consumed(projected)
            arrivals.append(projected['name'])
            if projected['attributes'] & 16:
                expected_children.add(path + '/' + projected['name'])
        total += len(entry['entries'])
        result[path] = (rows, arrivals)
    require(total == footer['rows'] and set(result) == expected_children, 'Complete native graph/cardinality differs')
    return result


def compare(packet, observed, generation):
    """Compare only observed consumed fields; retain bounded diagnostics."""
    require(_token(generation, 64), 'Exact comparison generation required')
    view = decode(packet, generation)
    native = _observed(observed, generation)
    projected = {entry.path: entry for entry in view.directories if entry.path}
    mismatches, orders, mismatch_count, order_count = [], [], 0, 0
    def difference(path, field, expected, actual):
        nonlocal mismatch_count
        mismatch_count += 1
        if len(mismatches) < 128:
            mismatches.append({'path': path, 'field': field, 'projected': expected, 'observed': actual})
    for path in sorted(set(projected) ^ set(native)):
        difference(path, 'directory_membership', path in projected, path in native)
    named_dot = nontexture = empty = compared = projected_noncanonical = 0
    for path in sorted(set(projected) & set(native)):
        rows, arrivals, folded = {}, [], set()
        for row in view.rows(projected[path].ordinal):
            if row['name'] in ('.', '..'):
                continue
            require(row['name'].lower() not in folded, 'Case-aliased projected row membership')
            folded.add(row['name'].lower())
            rows[row['name']] = row
            arrivals.append(row['name'])
        actual, native_arrivals = native[path]
        empty += not rows
        named_dot += sum(name.startswith('.') for name in rows)
        nontexture += sum(not row['attributes'] & 16 and not name.lower().endswith('.texture') for name, row in rows.items())
        projected_noncanonical += arrivals != sorted(arrivals, key=str.lower)
        if arrivals != native_arrivals:
            order_count += 1
            if len(orders) < 128:
                orders.append({'directory': path, 'projected_first_names': arrivals[:16],
                               'native_first_names': native_arrivals[:16], 'projected_rows': len(arrivals), 'native_rows': len(native_arrivals)})
        for name in sorted(set(rows) ^ set(actual)):
            difference(path + '/' + name, 'row_membership', name in rows, name in actual)
        for name in sorted(set(rows) & set(actual)):
            compared += 1
            expected_fields, actual_fields = _consumed(rows[name]), actual[name]
            for field in expected_fields:
                if expected_fields[field] != actual_fields[field]:
                    difference(path + '/' + name, field, expected_fields[field], actual_fields[field])
    return {'format': 1, 'role': 'source_projection_vs_observed_native_consumed_fields',
            'status': 'matched_consumed_fields' if mismatch_count == 0 else 'consumed_field_mismatch',
            'generation': generation, 'operation': observed['operation'], 'windows_pid': observed['windows_pid'],
            'compared_rows': compared, 'compared_directories': len(set(projected) & set(native)),
            'mismatch_count': mismatch_count, 'mismatches': mismatches, 'mismatches_omitted': max(0, mismatch_count - 128),
            'root_is_partial_anchor': True, 'root_WFD_parity_qualified': False,
            'root_projected_rows_not_compared': sum(entry.count for entry in view.directories if not entry.path),
            'named_dot_entries_retained': named_dot, 'nontexture_files_retained': nontexture, 'empty_directories_retained': empty,
            'native_arrival_preserved_in_observation': True, 'directory_order_matches_canonical_table': list(native) == list(projected),
            'row_order_different_directories': order_count, 'row_order_differences': orders,
            'row_order_differences_omitted': max(0, order_count - 128), 'projected_noncanonical_row_directories': projected_noncanonical,
            'native_enumeration_order_parity_qualified': False,
            'compared_fields': ['name', 'directory_readonly_hidden_system_attributes', 'size_low', 'write_FILETIME'],
            'current_creation_access_shortname_parity_claimed': False,
            'native_timestamp_conversion': {'source': TIMESTAMP_SOURCE, 'historical_source_sha256': TIMESTAMP_HISTORICAL_SOURCE_SHA256,
                'function': '_FileTimeToUnixTime(..., FALSE)', 'separately_executed': False,
                'current_native_source_closure_verified_by_this_module': False},
            'native_execution_or_console_ownership_verified_by_this_module': False, **_NO_AUTHORITY}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate native stat JSON field')
        result[key] = value
    return result


def parse_stat_counts(console):
    """Parse individually atomic cumulative fields, never coherent sums."""
    require(type(console) is str and len(console) <= 48 * 1024**2
            and len(console.encode('utf-8')) <= 48 * 1024**2, 'Bounded original native console required')
    rows, snapshots, previous = [], [], {}
    keys = {'snapshot', 'branch', 'scope', 'cached_stat_reuse', *STAT_FIELDS}
    for line in console.splitlines():
        if STAT_MARKER not in line:
            continue
        require(line.startswith(STAT_MARKER + ' ') and line.count(STAT_MARKER) == 1
                and len(line.encode('utf-8')) < 2048 and '\0' not in line, 'Complete marker-leading stat row required')
        row = json.loads(line[len(STAT_MARKER) + 1:], object_pairs_hook=_unique,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite native stat field')))
        require(type(row) is dict and set(row) == keys and _uint(row['snapshot']) and 1 <= row['snapshot'] <= 16
                and type(row['branch']) is str and row['scope'] == STAT_SCOPE and type(row['scope']) is str
                and row['cached_stat_reuse'] is False and all(_uint(row[field], 64) for field in STAT_FIELDS),
                'Typed bounded native stat row required')
        ordinal = len(rows)
        require(ordinal < 80 and row['snapshot'] == ordinal // 5 + 1 and row['branch'] == BRANCHES[ordinal % 5],
                'Exact dense five-branch stat groups required')
        if row['branch'] in previous:
            require(all(row[field] >= previous[row['branch']][field] for field in STAT_FIELDS),
                    'Native cumulative stat field decreased')
        previous[row['branch']] = row
        rows.append(row)
        if len(rows) % 5 == 0:
            snapshots.append({'snapshot': row['snapshot'], 'branches': rows[-5:]})
    require(rows and len(rows) % 5 == 0, 'Complete current native stat snapshots missing')
    return {'format': 1, 'role': 'bounded_observed_native_FolderCache_stat_counts', 'status': 'complete_snapshot_groups',
            'snapshot_count': len(snapshots), 'snapshots': snapshots,
            'fields_individually_atomic_and_may_be_in_flight': True, 'coherent_counter_sums_required': False,
            'final_all_thread_totals_claimed': False, 'console_PID_session_attribution_verified_by_this_module': False,
            'cached_stat_reuse': False, **_NO_AUTHORITY}
