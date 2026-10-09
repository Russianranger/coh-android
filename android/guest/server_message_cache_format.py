"""Bounded inspection of the native MessageStore 20090521 binary format.

The wire layout comes from MessageStore.c msWriteBin, StringTable.c
WriteStringTable, and SimpleBufWriteU32. It is not a Parse6 envelope. Source,
locale, executable, mtime and native-consumption proof belong to the package
receipt; this module validates only the complete binary representation.
"""
import struct


FORMAT = 'MessageStore20090521'
SCHEMA_VERSION = 20090521
MAX_FILE_BYTES = 256 * 1024**2
MAX_STRINGS = 4_000_000
MAX_RECORDS = 1_000_000
MAX_ID_BYTES = 64 * 1024
MAX_VARIABLE_REFERENCES = 4_000_000


class MessageStoreFormatError(ValueError):
    """The cache is not a bounded, complete native MessageStore binary."""


class _Reader:
    def __init__(self, data):
        self.data = data
        self.position = 0

    def take(self, size, field):
        if size > len(self.data) - self.position:
            raise MessageStoreFormatError('Truncated MessageStore ' + field)
        start = self.position
        self.position += size
        return self.data[start:self.position]

    def u32(self, field):
        return struct.unpack('<I', self.take(4, field))[0]

    def string_table(self, field):
        count = self.u32(field + ' count')
        size = self.u32(field + ' bytes')
        # Each string, including an empty one, contributes its NUL terminator.
        if count > MAX_STRINGS or count > size:
            raise MessageStoreFormatError('Invalid MessageStore ' + field + ' count')
        packed = self.take(size, field)
        if (bool(count) != bool(size) or (size and packed[-1] != 0)
                or packed.count(b'\0') != count):
            raise MessageStoreFormatError('Invalid MessageStore ' + field + ' boundaries')
        return count, size


def inspect_message_store(data: bytes) -> dict:
    """Inspect all fields without decoding or changing the stored text bytes.

    The native ID stash is case-insensitive. ASCII folding matches its English
    ID convention while leaving UTF-8/multibyte bytes untouched; native second
    pass loading and formatted-output checks remain required by the package.
    Variable references point to an adjacent name/type pair, not a message.
    """
    if not isinstance(data, bytes) or not 24 <= len(data) <= MAX_FILE_BYTES:
        raise MessageStoreFormatError('Invalid MessageStore file size or byte type')
    reader = _Reader(data)
    version = reader.u32('version')
    if version != SCHEMA_VERSION:
        raise MessageStoreFormatError('Unsupported MessageStore schema version')
    string_count, string_bytes = reader.string_table('message strings')
    type_count, type_bytes = reader.string_table('variable strings')
    if type_count % 2:
        raise MessageStoreFormatError('Unpaired MessageStore variable strings')
    records = reader.u32('record count')
    # A record has four U32 fields before any ID bytes or variable references.
    if not 0 < records <= MAX_RECORDS or records > (len(data) - reader.position) // 16:
        raise MessageStoreFormatError('Invalid MessageStore record count')
    ids = set()
    variable_references = 0
    for _ in range(records):
        size = reader.u32('ID length')
        if size > MAX_ID_BYTES:
            raise MessageStoreFormatError('Oversized MessageStore ID')
        message_id = reader.take(size, 'ID')
        if b'\0' in message_id:
            raise MessageStoreFormatError('Embedded NUL in MessageStore ID')
        folded_id = message_id.lower()
        if folded_id in ids:
            raise MessageStoreFormatError('Duplicate MessageStore ID')
        ids.add(folded_id)
        message_index = reader.u32('message index')
        help_index = reader.u32('help index')
        if message_index >= string_count or help_index >= string_count:
            raise MessageStoreFormatError('Invalid MessageStore message or help index')
        count = reader.u32('variable reference count')
        variable_references += count
        if (variable_references > MAX_VARIABLE_REFERENCES
                or count > (len(data) - reader.position) // 4):
            raise MessageStoreFormatError('Invalid MessageStore variable reference count')
        for _ in range(count):
            index = reader.u32('variable reference')
            if index % 2 or index + 1 >= type_count:
                raise MessageStoreFormatError('Invalid MessageStore variable name/type index')
    if reader.position != len(data):
        raise MessageStoreFormatError('Trailing bytes in MessageStore')
    return {'format': FORMAT, 'schema_version': version, 'bytes': len(data),
            'string_count': string_count, 'string_bytes': string_bytes,
            'type_count': type_count, 'type_bytes': type_bytes,
            'variable_definition_count': type_count // 2,
            'id_count': len(ids), 'message_record_count': records,
            'variable_reference_count': variable_references}
