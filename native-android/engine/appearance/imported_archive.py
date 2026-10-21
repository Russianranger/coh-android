"""Bounded host access to original members through an available archive FD.

The Android importer remains responsible for complete archive identity. This
adapter does not turn a supplied FD or a newly computed member hash into an
import receipt. It scans ZIP32 records without retaining the archive catalog,
and reads one selected source body under the existing 4 MiB loader limit.
"""
from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import PurePosixPath
import stat
import struct
import zlib

CHUNK = 65536
BODY_LIMIT = 4 << 20
REQUEST_LIMIT = 64


def safe_path(name):
    return (isinstance(name, str) and 0 < len(name) <= 255 and name.isascii()
            and all(32 <= ord(char) < 127 for char in name)
            and not name.startswith('/') and '\\' not in name and ':' not in name
            and all(part not in ('', '.', '..') for part in name.split('/')))


@dataclass(frozen=True)
class Member:
    name: str
    size: int
    stored: int
    crc32: int
    method: int
    flags: int
    local: int
    owner: object


class ImportedArchive:
    """Own a dup of an already available read-only archive FD/span.

    lookup returns matching entries in archive order, retaining only requested
    paths. Texture probes return all basename matches, so the caller can detect
    ambiguity instead of silently choosing another directory or donor table.
    """
    def __init__(self, fd, offset=0, length=None):
        self.fd = -1
        self.members = {}
        self.read_bytes = 0
        if fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY:
            raise ValueError('Archive FD is not read-only')
        identity = os.fstat(fd)
        length = identity.st_size - offset if length is None else length
        if (not stat.S_ISREG(identity.st_mode) or offset < 0 or length < 22
                or length > 0xffffffff or offset > identity.st_size
                or length > identity.st_size - offset):
            raise ValueError('Archive FD span differs')
        self.fd = fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, 0)
        self.offset, self.length = offset, length
        self.identity = self.fingerprint(identity)
        try:
            self.stable()
            tail = self.read(max(0, length - 65557), min(length, 65557))
            end = tail.rfind(b'PK\x05\x06')
            if end < 0 or end + 22 > len(tail):
                raise ValueError('ZIP32 directory missing')
            disk, other, count_here, count, size, start, comment = struct.unpack_from('<4H2IH', tail, end + 4)
            if (disk or other or count_here != count or not 0 < count < 65535
                    or end + 22 + comment != len(tail)
                    or start + size != length - len(tail) + end):
                raise ValueError('ZIP32 directory span differs')
            self.central, self.central_end, self.count = start, start + size, count
        except BaseException:
            self.close()
            raise

    @staticmethod
    def fingerprint(value):
        return (value.st_dev, value.st_ino, value.st_size, value.st_mode, value.st_uid,
                value.st_gid, value.st_nlink, value.st_mtime_ns, value.st_ctime_ns)

    def stable(self):
        if self.fd < 0 or self.fingerprint(os.fstat(self.fd)) != self.identity:
            raise ValueError('Archive FD identity changed')

    def read(self, offset, size):
        if offset < 0 or size < 0 or size > 65557 or offset > self.length or size > self.length - offset:
            raise ValueError('Archive read exceeds bounded span')
        self.stable()
        raw = os.pread(self.fd, size, self.offset + offset)
        if len(raw) != size:
            raise ValueError('Archive read truncated')
        self.read_bytes += len(raw)
        self.stable()
        return raw

    def lookup(self, paths=(), texture_names=()):
        if len(paths) + len(texture_names) > REQUEST_LIMIT or any(not safe_path(path) for path in paths):
            raise ValueError('Requested source paths exceed bounded lookup')
        if any(not isinstance(name, str) or not safe_path(name) or '/' in name for name in texture_names):
            raise ValueError('Texture probe is not a basename')
        wanted = {path.casefold() for path in paths}
        textures = {PurePosixPath(name).stem.casefold() for name in texture_names}
        if any(not name or '/' in name or '\\' in name for name in textures):
            raise ValueError('Texture probe is not a basename')
        cursor = self.central
        found = []
        selected = set()
        candidate = dict(self.members)
        for _ in range(self.count):
            if cursor > self.central_end - 46:
                raise ValueError('ZIP directory entry truncated')
            header = self.read(cursor, 46)
            names, extra, comment, disk = struct.unpack_from('<4H', header, 28)
            following = cursor + 46 + names + extra + comment
            if header[:4] != b'PK\x01\x02' or disk or following > self.central_end:
                raise ValueError('ZIP directory entry span differs')
            if 0 < names <= 255:
                encoded = self.read(cursor + 46, names)
                try:
                    name = encoded.decode('ascii')
                except UnicodeDecodeError:
                    name = ''
                low = name.casefold()
                texture = (low.startswith(('texture_library/', 'data/texture_library/', 'assets/texture_library/'))
                           and low.endswith('.texture') and PurePosixPath(low).stem in textures)
                if low in wanted or texture:
                    if not safe_path(name) or low in selected or len(found) >= REQUEST_LIMIT:
                        raise ValueError('Duplicate or oversized selected ZIP paths')
                    flags, method = struct.unpack_from('<2H', header, 8)
                    crc, stored, size = struct.unpack_from('<3I', header, 16)
                    local = struct.unpack_from('<I', header, 42)[0]
                    if (flags & ~0x0808 or method not in (0, 8) or not 0 < size <= BODY_LIMIT
                            or not 0 < stored <= BODY_LIMIT or method == 0 and size != stored):
                        raise ValueError('Selected source member exceeds existing loader bounds')
                    entry = Member(name, size, stored, crc, method, flags, local, self)
                    previous = candidate.get(low)
                    if previous is not None and previous != entry:
                        raise ValueError('Selected member identity changed')
                    candidate[low] = entry
                    found.append(entry)
                    selected.add(low)
            cursor = following
        if cursor != self.central_end or len(candidate) > REQUEST_LIMIT:
            raise ValueError('ZIP directory boundary or retained request count differs')
        self.members = candidate
        return found

    def stream(self, member, sink, expected_sha256=None):
        """Write into caller staging; publish it only after this returns success."""
        if member.owner is not self or self.members.get(member.name.casefold()) != member:
            raise ValueError('Member belongs to another archive')
        header = self.read(member.local, 30)
        names, extra = struct.unpack_from('<2H', header, 26)
        flags, method = struct.unpack_from('<2H', header, 6)
        data = member.local + 30 + names + extra
        if (header[:4] != b'PK\x03\x04' or flags != member.flags or method != member.method
                or names != len(member.name) or data > self.central
                or member.stored > self.central - data
                or self.read(member.local + 30, names) != member.name.encode('ascii')):
            raise ValueError('Selected local ZIP identity differs')
        if not flags & 8 and struct.unpack_from('<3I', header, 14) != (member.crc32, member.stored, member.size):
            raise ValueError('Selected local ZIP sizes/CRC differ')
        digest, crc, produced = hashlib.sha256(), 0, 0
        decoder = zlib.decompressobj(-15) if method == 8 else None

        def emit(raw):
            nonlocal crc, produced
            if len(raw) > member.size - produced:
                raise ValueError('Decoded source body exceeds declared size')
            if raw:
                sink(raw)
                digest.update(raw)
                crc = zlib.crc32(raw, crc)
                produced += len(raw)

        consumed = 0
        while consumed < member.stored:
            raw = self.read(data + consumed, min(CHUNK, member.stored - consumed))
            consumed += len(raw)
            if decoder is None:
                emit(raw)
            else:
                while raw:
                    before = len(raw)
                    decoded = decoder.decompress(raw, CHUNK)
                    emit(decoded)
                    raw = decoder.unconsumed_tail
                    if decoder.eof:
                        if decoder.unused_data or raw or consumed != member.stored:
                            raise ValueError('Deflate source has trailing data')
                        break
                    if not decoded and len(raw) == before:
                        raise ValueError('Deflate source made no progress')
        if decoder is not None:
            while not decoder.eof:
                raw = decoder.decompress(b'', CHUNK)
                if not raw and not decoder.eof:
                    raise ValueError('Deflate source ended early')
                emit(raw)
        value = digest.hexdigest()
        if produced != member.size or crc != member.crc32 or expected_sha256 is not None and value != expected_sha256:
            raise ValueError('Decoded source size/CRC/SHA differs')
        self.stable()
        return {'bytes': produced, 'sha256': value, 'original_name': member.name,
                'whole_archive_identity': 'caller existing import responsibility'}

    def read_body(self, member, pin=None):
        if pin is not None and pin['bytes'] != member.size:
            raise ValueError('Pinned source size differs')
        body = bytearray(member.size)
        cursor = 0

        def write(raw):
            nonlocal cursor
            body[cursor:cursor + len(raw)] = raw
            cursor += len(raw)

        self.stream(member, write, None if pin is None else pin['sha256'])
        return body

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
