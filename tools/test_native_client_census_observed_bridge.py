"""Synthetic source-only observations; no SDK, Wine or Game execution."""
from __future__ import annotations

import copy
import dataclasses
import json
import struct
import types
import unittest

import native_client_census_observed_bridge as bridge
import test_native_client_wfd_probe as wfd

GENERATION = wfd.GENERATION


def projection(name, attributes=1, size=99, write=13, alternate=''):
    raw = bytearray(wfd.fixture_projection(name, attributes))
    struct.pack_into('<Q', raw, 20, write)
    struct.pack_into('<I', raw, 32, size)
    raw[304:304 + len(alternate)] = alternate.encode('ascii')
    return bytes(raw)


def handle(attributes=16, identity=777):
    raw = bytearray(wfd.fixture_stat(attributes))
    struct.pack_into('<I', raw, 76, identity)
    return bytes(raw)


def observations(extra_files=0):
    """Generate raw fixtures, then use the frozen bounded COHWFD1 parser."""
    paths = list(bridge.BRANCHES) + ['texture_library/_excluded', 'texture_library/.named-dir']
    children = {path: [] for path in paths}
    children['texture_library'] = [projection('z.texture'), projection('.', 16, 0),
        projection('.named-file', 3), projection('_excluded', 16, 0), projection('a.texture'),
        projection('..', 16, 0), projection('.named-dir', 16, 0)]
    children['object_library'] = [projection('nontexture.geo')]
    children['scripts'] = [projection('local.txt')]
    children['texture_library/_excluded'] = [projection('nontexture.geo')]
    children['texture_library/.named-dir'] = [projection('.hidden.texture', 3)]
    children['scripts.loc'] = [projection('entry%03d.txt' % i) for i in range(extra_files)]
    header = bytearray(160)
    header[:8] = wfd.MAGIC
    struct.pack_into('<10I', header, 8, 1, 160, 320, 52, 312, 77, 3, 5, 60, wfd.MAX_BYTES)
    header[48:112], header[112:144] = GENERATION.encode(), wfd.OPERATION.encode()
    pieces, sequence, row_count = [], 0, 0
    def emit(kind, body):
        nonlocal sequence
        pieces.append(struct.pack('<III', kind, len(body), sequence) + body)
        sequence += 1
    root = 'C:/controlled/data'
    emit(1, struct.pack('<I', len(root)) + handle(identity=999) + root.encode())
    for ordinal, path in enumerate(paths):
        parent = 0xffffffff if ordinal < 5 else 0
        branch = ordinal if ordinal < 5 else 0
        emit(2, struct.pack('<4I', ordinal, parent, branch, len(path)) + handle(identity=ordinal + 1) + path.encode())
        for arrival, raw in enumerate(children[path]):
            name = raw[44:304].split(b'\0', 1)[0].decode()
            attributes = struct.unpack_from('<I', raw)[0]
            emit(3, struct.pack('<3I', ordinal, arrival, 3 if name in ('.', '..') else 1) + raw + handle(attributes, identity=1000 + row_count))
            row_count += 1
        count = len(children[path])
        emit(4, struct.pack('<6I', ordinal, count, 0 if count else 2, 18 if count else 0, int(bool(count)), 0))
    emit(5, struct.pack('<9I', len(paths), len(paths), row_count, 0, 1, 1, 123, 0, 0))
    native = wfd.parse(bytes(header) + b''.join(pieces), GENERATION, wfd.OPERATION, root, 312)
    canonical = {'': [projection(branch, 16, 0) for branch in bridge.BRANCHES]}
    for path, rows in children.items():
        canonical[path] = sorted((raw for raw in rows if raw[44:304].split(b'\0', 1)[0] not in (b'.', b'..')),
                                 key=lambda raw: raw[44:304].split(b'\0', 1)[0].lower())
    return census(canonical), native


def census(directories, token=GENERATION):
    table, rows, first = bytearray(), bytearray(), 0
    for ordinal, path in enumerate(sorted(directories, key=str.lower)):
        raw = path.encode('ascii')
        current = directories[path]
        table += struct.pack('<HHIII', len(raw), 0, first, len(current), ordinal) + raw
        table += bytes((-len(table)) % 4)
        for arrival, projected in enumerate(current):
            rows += struct.pack('<II', ordinal, arrival) + projected
        first += len(current)
    total = 64 + len(table) + len(rows)
    return bridge.MAGIC + struct.pack('<6I', 1, total, len(directories), first, 64 + len(table), 0) + bytes.fromhex(token) + table + rows


def offsets(packet):
    view = bridge.decode(packet)
    return view.record_offset, {entry.path: view.record_offset + entry.first * 328 for entry in view.directories}


def stat_rows(snapshots=2, incoherent=False):
    rows = []
    for snapshot in range(1, snapshots + 1):
        for branch in bridge.BRANCHES:
            row = {'snapshot': snapshot, 'branch': branch, 'scope': bridge.STAT_SCOPE, 'cached_stat_reuse': False}
            row.update({name: snapshot * (index + 2 if incoherent else 1) for index, name in enumerate(bridge.STAT_FIELDS)})
            rows.append(row)
    return rows


def console(rows):
    return 'ordinary native row\n' + '\n'.join(bridge.STAT_MARKER + ' ' + json.dumps(row) for row in rows)


class CensusBridgeTests(unittest.TestCase):
    def test_decode_borrows_immutable_packet_and_streams_rows(self):
        packet, _ = observations()
        value = bridge.decode(packet, GENERATION)
        self.assertIs(value.packet, packet)
        self.assertIsInstance(value.rows(0), types.GeneratorType)
        self.assertEqual({field.name for field in dataclasses.fields(value)},
                         {'packet', 'generation', 'directories', 'row_count', 'record_offset'})
        self.assertFalse(value.summary()['provider_authority'])
        self.assertFalse(value.summary()['decoder_or_native_consumer_executed_by_this_module'])

    def test_complete_consumed_fields_preserve_named_dot_nontexture_empty_and_order(self):
        packet, observed = observations()
        value = bridge.compare(packet, observed, GENERATION)
        self.assertEqual(value['status'], 'matched_consumed_fields')
        self.assertGreater(value['named_dot_entries_retained'], 0)
        self.assertGreater(value['nontexture_files_retained'], 0)
        self.assertGreater(value['empty_directories_retained'], 0)
        self.assertGreater(value['row_order_different_directories'], 0)
        self.assertTrue(value['root_is_partial_anchor'])
        self.assertFalse(value['root_WFD_parity_qualified'])
        self.assertFalse(value['native_enumeration_order_parity_qualified'])
        self.assertFalse(value['native_timestamp_conversion']['separately_executed'])
        self.assertFalse(value['native_execution_or_console_ownership_verified_by_this_module'])
        for field in ('provider_authority', 'native_registration_allowed', 'native_replay_allowed', 'publication_allowed'):
            self.assertIs(value[field], False)

    def test_unconsumed_creation_access_shortname_and_high_size_do_not_grant_parity(self):
        packet, observed = observations()
        _, rows = offsets(packet)
        changed = bytearray(packet)
        row = rows['object_library'] + 8
        struct.pack_into('<Q', changed, row + 4, 900)
        struct.pack_into('<Q', changed, row + 12, 901)
        struct.pack_into('<I', changed, row + 28, 99)
        changed[row + 304:row + 309] = b'SHORT'
        value = bridge.compare(bytes(changed), observed, GENERATION)
        self.assertEqual(value['status'], 'matched_consumed_fields')
        self.assertFalse(value['current_creation_access_shortname_parity_claimed'])

    def test_each_consumed_field_mutation_is_reported(self):
        packet, observed = observations()
        _, rows = offsets(packet)
        for relative_offset, raw, field in [(0, struct.pack('<I', 3), 'attributes'),
            (32, struct.pack('<I', 100), 'size_low'), (20, struct.pack('<Q', 14), 'write_filetime')]:
            changed = bytearray(packet)
            start = rows['object_library'] + 8 + relative_offset
            changed[start:start + len(raw)] = raw
            value = bridge.compare(bytes(changed), observed, GENERATION)
            with self.subTest(field=field):
                self.assertEqual(value['status'], 'consumed_field_mismatch')
                self.assertEqual(value['mismatch_count'], 1)
                self.assertEqual(value['mismatches'][0]['field'], field)

    def test_exact_case_name_membership_is_compared(self):
        packet, observed = observations()
        _, rows = offsets(packet)
        changed = bytearray(packet)
        changed[rows['object_library'] + 8 + 44] = ord('N')
        value = bridge.compare(bytes(changed), observed, GENERATION)
        self.assertEqual(value['status'], 'consumed_field_mismatch')
        self.assertEqual(value['mismatch_count'], 2)
        self.assertTrue(all(row['field'] == 'row_membership' for row in value['mismatches']))

    def test_header_bounds_flags_tokens_and_input_types_refused(self):
        packet, _ = observations()
        values = [bytearray(packet), memoryview(packet), None, packet[:63], packet[:-1], packet + b'X']
        for offset, value in [(8, 2), (12, len(packet) + 1), (16, 0), (16, bridge.MAX_DIRS + 1),
                              (20, bridge.MAX_ROWS + 1), (24, 65), (28, 1)]:
            changed = bytearray(packet); struct.pack_into('<I', changed, offset, value); values.append(bytes(changed))
        values.append(b'BADMAGIC' + packet[8:])
        for value in values:
            with self.subTest(value_type=type(value).__name__), self.assertRaises(ValueError): bridge.decode(value)
        for generation in ('3' * 64, GENERATION.upper().replace('1', 'A'), True, None):
            if generation is None:
                continue
            with self.subTest(generation=generation), self.assertRaises(ValueError): bridge.decode(packet, generation)

    def test_directory_padding_indexes_sort_and_graph_mutations_refused(self):
        packet, _ = observations()
        first_directory = 64
        mutations = [(first_directory + 2, b'\1'), (first_directory + 4, struct.pack('<I', 1)),
                     (first_directory + 12, struct.pack('<I', 1))]
        # Root entry is16bytes; the next directory is fx (two-byte path plus padding).
        mutations += [(80 + 18, b'X'), (80 + 16, b'FX'), (80, struct.pack('<H', 260)),
                      (80 + 16, b'zx'), (80 + 16, b'..')]
        for offset, raw in mutations:
            changed = bytearray(packet); changed[offset:offset + len(raw)] = raw
            if offset == 96 and raw == b'FX':  # case-only first directory remains native-valid.
                self.assertEqual(bridge.decode(bytes(changed)).directories[1].path, 'FX')
            else:
                with self.subTest(offset=offset), self.assertRaises(ValueError): bridge.decode(bytes(changed))
        malformed = {'': [projection('fx', 16, 0)], 'fx': [], 'orphan': []}
        with self.assertRaisesRegex(ValueError, 'orphan'): bridge.decode(census(malformed))
        malformed = {'': [projection('fx')], 'fx': []}
        with self.assertRaisesRegex(ValueError, 'membership'): bridge.decode(census(malformed))
        malformed = {'fx': [projection('missing', 16, 0)]}
        with self.assertRaisesRegex(ValueError, 'child missing'): bridge.decode(census(malformed))
        malformed = {'': [projection('a', 16, 0), projection('A', 16, 0)], 'A': [], 'a': []}
        with self.assertRaisesRegex(ValueError, 'Case-aliased'): bridge.decode(census(malformed))

    def test_rows_reserved_strings_ordinal_and_arrival_mutations_refused(self):
        packet, _ = observations()
        _, rows = offsets(packet); start = rows['object_library']
        mutations = [(0, struct.pack('<I', 999)), (4, struct.pack('<I', 1)), (8 + 36, b'X'),
                     (8 + 40, b'X'), (8 + 318, b'X'), (8 + 44, b'\0'), (8 + 44 + 15, b'X'),
                     (8 + 304, b'/' )]
        for relative, raw in mutations:
            changed = bytearray(packet); changed[start + relative:start + relative + len(raw)] = raw
            with self.subTest(relative=relative), self.assertRaises(ValueError): bridge.decode(bytes(changed))

    def test_native_valid_traversal_aliases_decode_but_never_become_members(self):
        packet = census({'fx': [projection('.', 16, 0), projection('..', 16, 0)]})
        self.assertEqual(bridge.decode(packet).row_count, 2)
        with self.assertRaises(ValueError): bridge.decode(census({'fx': [projection('child', 16, 0)], 'fx/.': []}))

    def test_observed_field_type_flags_mapping_readability_and_identity_mutations_refused(self):
        packet, observed = observations()
        mutations = [lambda v: v.update(windows_pid=True), lambda v: v.update(generation='3' * 64),
            lambda v: v.update(provider_authority=True), lambda v: v['ABI'].update(pointer_bits=True),
            lambda v: v['footer'].update(readability_complete=False), lambda v: v['root'].update(partial_anchor=False),
            lambda v: v['root'].update(root='C:/controlled/../data'),
            lambda v: v['directories'][0]['entries'][0].update(arrival=1),
            lambda v: v['directories'][0]['entries'][0]['wfd'].update(mapping_supported=False),
            lambda v: v['directories'][0]['entries'][0]['wfd'].update(attributes=3),
            lambda v: v['directories'][0]['entries'][0]['by_handle'].update(readable=False),
            lambda v: v['directories'][0]['entries'][0]['by_handle'].update(create_ok=1),
            lambda v: v['directories'][0]['entries'][0].update(flags=17),
            lambda v: v['directories'][1].update(parent=0),
            lambda v: v['directories'][1].update(by_handle=copy.deepcopy(v['directories'][0]['by_handle']))]
        for mutation in mutations:
            changed = copy.deepcopy(observed); mutation(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): bridge.compare(packet, changed, GENERATION)
        for name, attributes in [('unknown.', 1), ('unknown ', 1), ('child', 16 | 1024)]:
            changed = copy.deepcopy(observed)
            raw = projection(name, attributes)
            row = changed['directories'][1]['entries'][0]
            row['wfd'].update(name=name, attributes=attributes, projection=raw.hex())
            with self.subTest(name=name, attributes=attributes), self.assertRaisesRegex(ValueError, 'mapping/flags'):
                bridge.compare(packet, changed, GENERATION)

    def test_ambiguous_ordinary_row_names_refused_by_comparison(self):
        packet, observed = observations()
        changed = copy.deepcopy(observed)
        first = changed['directories'][0]['entries'][0]
        changed['directories'][0]['entries'][4]['wfd'] = copy.deepcopy(first['wfd'])
        with self.assertRaisesRegex(ValueError, 'Case-aliased'): bridge.compare(packet, changed, GENERATION)
        source = census({'': [projection(branch, 16, 0) for branch in bridge.BRANCHES],
                         **{branch: [] for branch in bridge.BRANCHES},
                         'object_library': [projection('same.geo'), projection('SAME.geo')]})
        bridge.decode(source)  # Native decoder accepts ordinary duplicates; matching must refuse.
        with self.assertRaisesRegex(ValueError, 'Case-aliased'): bridge.compare(source, observed, GENERATION)

    def test_comparison_diagnostics_have_explicit_omission_bound(self):
        packet, observed = observations(extra_files=130)
        view = bridge.decode(packet); changed = bytearray(packet)
        entry = next(row for row in view.directories if row.path == 'scripts.loc')
        for arrival in range(entry.count):
            struct.pack_into('<Q', changed, view.record_offset + (entry.first + arrival) * 328 + 8 + 20, 99)
        value = bridge.compare(bytes(changed), observed, GENERATION)
        self.assertEqual(value['mismatch_count'], 130)
        self.assertEqual(len(value['mismatches']), 128)
        self.assertEqual(value['mismatches_omitted'], 2)


class StatBridgeTests(unittest.TestCase):
    def test_typed_dense_monotonic_groups_accept_inflight_incoherent_sums(self):
        value = bridge.parse_stat_counts(console(stat_rows(incoherent=True)))
        self.assertEqual(value['snapshot_count'], 2)
        self.assertFalse(value['coherent_counter_sums_required'])
        self.assertFalse(value['final_all_thread_totals_claimed'])
        self.assertFalse(value['console_PID_session_attribution_verified_by_this_module'])
        self.assertFalse(value['provider_authority'])
        self.assertGreater(value['snapshots'][0]['branches'][0]['returns_ok'], value['snapshots'][0]['branches'][0]['calls'])

    def test_unsigned64_range_and_strict_types(self):
        for field, value in [('calls', -1), ('calls', 2**64), ('calls', True), ('calls', 1.0),
                             ('snapshot', True), ('branch', 1), ('cached_stat_reuse', 0), ('scope', 'other')]:
            rows = stat_rows(); rows[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError): bridge.parse_stat_counts(console(rows))
        rows = stat_rows(1)
        for row in rows:
            for field in bridge.STAT_FIELDS: row[field] = 2**64 - 1
        self.assertEqual(bridge.parse_stat_counts(console(rows))['snapshot_count'], 1)

    def test_missing_duplicated_reordered_or_excess_snapshot_groups_refused(self):
        original = stat_rows()
        reordered = copy.deepcopy(original); reordered[0], reordered[1] = reordered[1], reordered[0]
        duplicate = copy.deepcopy(original); duplicate[5]['snapshot'] = 1
        skipped = copy.deepcopy(original); skipped[5]['snapshot'] = 3
        for rows in ([], original[:-1], original[:4], reordered, duplicate, skipped, stat_rows(17)):
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError): bridge.parse_stat_counts(console(rows))
        self.assertEqual(bridge.parse_stat_counts(console(stat_rows(16)))['snapshot_count'], 16)

    def test_each_individual_counter_must_be_monotonic(self):
        for field in bridge.STAT_FIELDS:
            rows = stat_rows(); rows[5][field] = 0
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'decreased'): bridge.parse_stat_counts(console(rows))

    def test_original_marker_scope_duplicate_keys_and_partial_json_refused(self):
        good = console(stat_rows(1))
        bad = [good.replace(bridge.STAT_MARKER, 'prefix ' + bridge.STAT_MARKER, 1),
               good.replace(bridge.STAT_MARKER, bridge.STAT_MARKER + ' ' + bridge.STAT_MARKER, 1),
               good.replace('"calls": 1', '"calls": 1, "calls": 1', 1),
               good.replace('"calls": 1', '"calls": NaN', 1), good[:-1],
               good.replace('"calls": 1', '"extra": 1, "calls": 1', 1),
               good.replace('"calls": 1', '"calls": 1\0', 1)]
        for value in bad:
            with self.subTest(value=value[:80]), self.assertRaises(ValueError): bridge.parse_stat_counts(value)
        for value in (None, b'console', True):
            with self.assertRaises(ValueError): bridge.parse_stat_counts(value)


if __name__ == '__main__':
    unittest.main()
