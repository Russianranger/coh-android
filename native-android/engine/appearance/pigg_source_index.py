"""Bounded selected rows from an existing independently pinned PIGG prefix.

Only the original metadata prefix is read. Filename and cached-header pools are
walked on disk; no complete donor catalog or payload archive is copied to RAM.
"""
import fcntl
import hashlib
import os
import stat
import struct
from imported_archive import ImportedArchive, BODY_LIMIT, CHUNK, safe_path

ENTRY = struct.Struct('<IiIIIIi16sI')


class PiggSourceIndex:
    def __init__(self, fd, identity):
        self.fd = -1
        self.identity = dict(identity)
        self.size = identity['source_metadata_bytes']
        before = os.fstat(fd)
        if (fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY
                or not stat.S_ISREG(before.st_mode) or not 16 <= self.size <= BODY_LIMIT
                or self.size > before.st_size):
            raise ValueError('Original metadata FD/span differs')
        self.fingerprint = ImportedArchive.fingerprint(before)
        self.fd = fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, 0)
        try:
            digest = hashlib.sha256()
            for offset in range(0, self.size, CHUNK):
                digest.update(self.read(offset, min(CHUNK, self.size - offset)))
            if digest.hexdigest() != identity['source_metadata_sha256']:
                raise ValueError('Original metadata SHA differs')
            magic, creator, reader, header, entry, count = struct.unpack('<IHHHHI', self.read(0, 16))
            if (magic != 0x123 or creator != 2 or reader > 2 or header != 16 or entry != ENTRY.size
                    or count == 0 or count * entry > self.size - 16):
                raise ValueError('Original PIGG entry layout differs')
            self.count = count
        except BaseException:
            self.close()
            raise

    def read(self, offset, size):
        if (size < 0 or size > CHUNK or offset < 0 or offset > self.size or size > self.size - offset
                or self.fd < 0 or ImportedArchive.fingerprint(os.fstat(self.fd)) != self.fingerprint):
            raise ValueError('Original metadata read/identity differs')
        raw = os.pread(self.fd, size, offset)
        if len(raw) != size or ImportedArchive.fingerprint(os.fstat(self.fd)) != self.fingerprint:
            raise ValueError('Original metadata read changed')
        return raw

    def rows(self, wanted):
        if not 0 < len(wanted) <= 64 or any(not safe_path(name) for name in wanted):
            raise ValueError('Selected original metadata request differs')
        requested = {name.casefold(): pin for name, pin in wanted.items()}
        cursor = 16 + self.count * ENTRY.size
        flag, count, size = struct.unpack('<3I', self.read(cursor, 12))
        cursor += 12
        names_end = cursor + size
        if flag != 0x6789 or count != self.count or names_end > self.size:
            raise ValueError('Original filename pool differs')
        names = {}
        for index in range(count):
            length = struct.unpack('<I', self.read(cursor, 4))[0]
            cursor += 4
            if not length or length > names_end - cursor:
                raise ValueError('Original filename span differs')
            if length <= 256:
                raw = self.read(cursor, length)
                if raw.endswith(b'\0') and b'\0' not in raw[:-1]:
                    name = raw[:-1].decode('utf-8').replace('\\', '/')
                    canonical = 'data/' + name.casefold()
                    if canonical in requested:
                        if canonical in (value[0] for value in names.values()):
                            raise ValueError('Ambiguous original selected filename')
                        names[index] = (canonical, name)
            cursor += length
        if cursor != names_end:
            raise ValueError('Original filename pool boundary differs')
        flag, header_count, header_size = struct.unpack('<3I', self.read(cursor, 12))
        cursor += 12
        if flag != 0x9abc or cursor + header_size != self.size:
            raise ValueError('Original cached-header pool differs')
        headers_start = cursor
        result = {}
        headers = {}
        for row in range(self.count):
            values = ENTRY.unpack(self.read(16 + row * ENTRY.size, ENTRY.size))
            flag, name_id, size, _timestamp, offset, reserved, header_id, md5, packed = values
            if name_id not in names:
                continue
            canonical, original = names[name_id]
            pin = requested[canonical]
            if (flag != 0x3456 or reserved or size != pin['bytes'] or not 0 < size <= BODY_LIMIT
                    or not 0 < (packed or size) <= BODY_LIMIT or offset < self.size
                    or (packed or size) > self.identity['source_archive_bytes'] - offset
                    or not -1 <= header_id < header_count or canonical in result):
                raise ValueError('Selected original donor row differs')
            record = {'path': original, 'bytes': size, 'offset': offset, 'stored_bytes': packed or size,
                      'compressed': bool(packed), 'md5_table': md5.hex(), 'sha256': pin['sha256'],
                      'source_archive': self.identity['archive'],
                      'source_url': 'https://dists.thunderspy.org/piggs/' + self.identity['archive'],
                      **{key: self.identity[key] for key in ('source_archive_bytes', 'source_etag', 'source_metadata_sha256')},
                      'stored_sha256_provenance': 'unavailable independently; observe during selected read'}
            result[canonical] = record
            if header_id >= 0:
                headers.setdefault(header_id, []).append(record)
            else:
                record.update(cached_header_bytes=0, cached_header_sha256=hashlib.sha256(b'').hexdigest())
        cursor = headers_start
        for index in range(header_count):
            length = struct.unpack('<I', self.read(cursor, 4))[0]
            cursor += 4
            if length > self.size - cursor:
                raise ValueError('Original cached header span differs')
            if index in headers:
                digest = hashlib.sha256()
                for position in range(0, length, CHUNK):
                    digest.update(self.read(cursor + position, min(CHUNK, length - position)))
                for record in headers[index]:
                    record.update(cached_header_bytes=length, cached_header_sha256=digest.hexdigest())
            cursor += length
        if cursor != self.size:
            raise ValueError('Original metadata end differs')
        return result

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
