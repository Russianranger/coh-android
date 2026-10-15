"""Independent wire fixtures and rejection checks for the native text cache."""
import importlib.util
from pathlib import Path
import struct
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'server_message_cache_format_under_test',
    ROOT / 'android/guest/server_message_cache_format.py')
format_reader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(format_reader)


# Version20090521; message table [hello, help]; variable table [Hero, s];
# one record ID=GREETING, message=0, help=1, variable-name index=0.
# This literal is independent of the inspector and its private Reader class.
GOLDEN = bytes.fromhex(
    '998e3201'
    '020000000b00000068656c6c6f0068656c7000'
    '02000000070000004865726f007300'
    '01000000'
    '080000004752454554494e4700000000010000000100000000000000')


def table(strings):
    packed = b''.join(value + b'\0' for value in strings)
    return struct.pack('<II', len(strings), len(packed)) + packed


def record(message_id, message=0, help_index=0, variables=()):
    return (struct.pack('<I', len(message_id)) + message_id
            + struct.pack('<III', message, help_index, len(variables))
            + b''.join(struct.pack('<I', index) for index in variables))


def cache(strings=(b'text',), types=(), records=None):
    rows = [record(b'Message')] if records is None else records
    return (struct.pack('<I', 20090521) + table(strings) + table(types)
            + struct.pack('<I', len(rows)) + b''.join(rows))


class MessageStoreFormatTests(unittest.TestCase):
    def inspect(self, data):
        return format_reader.inspect_message_store(data)

    def reject(self, data, reason=None):
        with self.assertRaisesRegex(format_reader.MessageStoreFormatError, reason or 'MessageStore'):
            self.inspect(data)

    def test_fixed_native_layout_with_help_and_named_type(self):
        self.assertEqual(self.inspect(GOLDEN), {
            'format': 'MessageStore20090521', 'schema_version': 20090521,
            'bytes': 70, 'string_count': 2, 'string_bytes': 11,
            'type_count': 2, 'type_bytes': 7, 'variable_definition_count': 1,
            'id_count': 1, 'message_record_count': 1, 'variable_reference_count': 1})

    def test_general_story_and_static_store_layouts(self):
        rows = [record(b'v_ContactDialog', 1, 0, (0, 2)),
                record(b'ContactDialog', 2, 0, (2,)), record(b'', 0)]
        result = self.inspect(cache((b'', b'Welcome {Hero}', b'Help\r\nline'),
                                    (b'Hero', b's', b'Level', b'd'), rows))
        self.assertEqual(result['message_record_count'], 3)
        self.assertEqual(result['variable_reference_count'], 3)
        self.assertEqual(result['variable_definition_count'], 2)

    def test_no_types_and_zero_default_help_index_are_valid(self):
        result = self.inspect(cache())
        self.assertEqual(result['type_count'], 0)
        self.assertEqual(result['variable_reference_count'], 0)

    def test_utf8_text_and_id_bytes_are_preserved(self):
        data = cache(('Привет'.encode(),), records=[record('é'.encode())])
        self.assertEqual(self.inspect(data)['id_count'], 1)

    def test_every_proper_prefix_is_rejected(self):
        for end in range(len(GOLDEN)):
            with self.subTest(end=end):
                self.reject(GOLDEN[:end])

    def test_wrong_version_and_big_endian_are_rejected(self):
        self.reject(struct.pack('<I', 20090522) + GOLDEN[4:], 'schema version')
        self.reject(struct.pack('>I', 20090521) + GOLDEN[4:], 'schema version')
        self.reject(b'Parse6\0\0' + GOLDEN[8:])

    def test_table_count_and_bytes_must_match_all_nul_boundaries(self):
        for count, packed in ((0, b'x\0'), (1, b''), (2, b'a\0'),
                              (1, b'a\0b\0'), (1, b'abc'), (1, b'a\0tail')):
            data = (struct.pack('<III', 20090521, count, len(packed)) + packed
                    + table(()) + struct.pack('<I', 1) + record(b'ID'))
            with self.subTest(count=count, packed=packed):
                self.reject(data)

    def test_string_table_allocations_are_bounded_before_read(self):
        for count, size in ((0xffffffff, 0xffffffff), (0, 0xffffffff),
                            (format_reader.MAX_STRINGS + 1, 0xffffffff)):
            self.reject(struct.pack('<III', 20090521, count, size) + b'\0' * 12)

    def test_duplicate_ids_follow_native_case_insensitive_stash(self):
        for pair in ((b'Hello', b'Hello'), (b'Hello', b'hELLO'), (b'', b'')):
            with self.subTest(pair=pair):
                self.reject(cache(records=[record(value) for value in pair]), 'Duplicate')

    def test_id_length_and_embedded_nul_are_rejected(self):
        self.reject(cache(records=[record(b'Name\0Extra')]), 'Embedded NUL')
        row = struct.pack('<I', 0xffffffff) + b'x' * 16
        self.reject(cache(records=[row]), 'Oversized')

    def test_message_and_help_indexes_are_bounded(self):
        for message, help_index in ((1, 0), (0, 1), (0xffffffff, 0), (0, 0xffffffff)):
            with self.subTest(message=message, help=help_index):
                self.reject(cache(records=[record(b'ID', message, help_index)]), 'index')
        self.reject(cache(strings=()), 'index')

    def test_variable_name_type_adjacency_is_required(self):
        self.reject(cache(types=(b'Hero',)), 'Unpaired')
        for index in (1, 2, 0xffffffff):
            with self.subTest(index=index):
                self.reject(cache(types=(b'Hero', b's'),
                                  records=[record(b'ID', variables=(index,))]), 'name/type')
        self.reject(cache(records=[record(b'ID', variables=(0,))]), 'name/type')

    def test_variable_counts_and_record_counts_are_bounded(self):
        row = struct.pack('<I', 2) + b'ID' + struct.pack('<III', 0, 0, 0xffffffff)
        self.reject(cache(types=(b'Hero', b's'), records=[row]), 'reference count')
        prefix = struct.pack('<I', 20090521) + table((b'text',)) + table(())
        for count in (0, 2, 0xffffffff):
            with self.subTest(count=count):
                self.reject(prefix + struct.pack('<I', count) + record(b'ID'), 'record count')

    def test_aggregate_references_have_an_independent_bound(self):
        data = cache(types=(b'Hero', b's'),
                     records=[record(b'A', variables=(0,)), record(b'B', variables=(0,))])
        with mock.patch.object(format_reader, 'MAX_VARIABLE_REFERENCES', 1):
            self.reject(data, 'reference count')

    def test_trailing_bytes_and_file_bounds_are_rejected(self):
        for extra in (b'\0', b'extra record', GOLDEN):
            self.reject(GOLDEN + extra, 'Trailing')
        with mock.patch.object(format_reader, 'MAX_FILE_BYTES', len(GOLDEN) - 1):
            self.reject(GOLDEN, 'file size')
        for data in (None, '', bytearray(GOLDEN), memoryview(GOLDEN)):
            with self.subTest(data_type=type(data).__name__):
                self.reject(data, 'byte type')


if __name__ == '__main__':
    unittest.main()
