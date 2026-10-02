"""Pack exact immutable texture headers for one verified client generation.

Only the 32-byte header, original name and original cached mip bytes are packed.
Full .texture files remain unchanged. A native failure falls back to file reads.
"""
from pathlib import Path
import hashlib
import json
import os
import stat
import struct
import time
import zlib

FORMAT = 1
MAX_RECORDS = 65536
MAX_BYTES = 64 * 1024 * 1024
MAX_HEADER = 1056
PACK = 'coh-texture-header-index.bin'
MARKER = 'coh-texture-header-index.json'


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def texture_inputs(work, context):
    data = work / 'data'
    root = data / 'texture_library'
    require(root.is_dir() and not root.is_symlink(), 'Private texture directory unavailable')
    marker = work / 'client-work.json'
    require(marker.is_file() and not marker.is_symlink(), 'Missing verified client worktree')
    client = json.loads(marker.read_bytes())
    imported = Path(client['source_data']).resolve()
    inventory, records = [], []
    for current, directories, files in os.walk(root, followlinks=False):
        context.check()
        # Match the native scanner's _ directory exclusion exactly.
        directories[:] = sorted(name for name in directories if not name.startswith('_'))
        files.sort()
        for name in directories:
            require(not (Path(current) / name).is_symlink(), 'Linked texture directory refused')
        directory = Path(current)
        info = directory.stat()
        inventory.append([directory.relative_to(data).as_posix(), info.st_ino, info.st_mtime_ns, info.st_ctime_ns])
        for name in files:
            if not name.lower().endswith('.texture') or name.startswith('_'):
                continue
            path = directory / name
            resolved = path.resolve(strict=True)
            require(resolved.is_relative_to(imported) or resolved.is_relative_to(data.resolve()),
                    'Texture link escapes verified immutable input')
            info = resolved.stat()
            require(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o222,
                    'Texture index requires readonly regular inputs')
            relative = path.relative_to(data).as_posix().lower()
            require(relative.isascii() and 25 <= len(relative) < 260 and '\\' not in relative
                    and ':' not in relative and all(p not in ('', '.', '..') for p in relative.split('/')),
                    'Texture index path exceeds native contract')
            inventory.append([relative, str(resolved), info.st_ino, info.st_size,
                              info.st_mtime_ns, info.st_ctime_ns, info.st_mode])
            records.append((relative, path))
            require(len(records) <= MAX_RECORDS, 'Texture inventory exceeds native bound')
    records.sort(key=lambda item: item[0])
    require(records and len({name for name, _ in records}) == len(records),
            'Empty or ambiguous texture inventory')
    return records, hashlib.sha256(canonical(inventory)).hexdigest(), client


def make_pack(records, identity, context):
    payload = bytearray()
    header_digest = hashlib.sha256()
    for relative, path in records:
        context.check()
        with path.open('rb') as stream:
            fixed = stream.read(32)
            require(len(fixed) == 32, 'Truncated texture header: ' + relative)
            size, data_bytes, width, height = struct.unpack_from('<IIII', fixed)
            require(32 < size <= MAX_HEADER and 0 < width <= 16384 and 0 < height <= 16384,
                    'Invalid original texture header: ' + relative)
            extra = stream.read(size - 32)
            require(len(extra) == size - 32 and b'\0' in extra and path.stat().st_size >= size + data_bytes,
                    'Invalid original texture data/name: ' + relative)
        header = fixed + extra
        encoded = relative.encode('ascii')
        payload.extend(struct.pack('<HH', len(encoded), len(header)))
        payload.extend(encoded)
        payload.extend(header)
        header_digest.update(encoded + b'\0' + header)
        require(len(payload) + 64 <= MAX_BYTES, 'Texture header pack exceeds native bound')
    envelope = b'COHTHI1\0' + struct.pack('<IIIIII', FORMAT, 32, len(records), len(payload),
                                          zlib.crc32(payload), 0) + bytes.fromhex(identity)
    return envelope + payload, header_digest.hexdigest()


def atomic_write(path, data):
    temporary = path.with_name(path.name + '.pending-' + os.urandom(8).hex())
    try:
        with temporary.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o400)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(work, import_identity, executable_sha256, context):
    """Return (timing/provenance receipt, Wine environment) after supplements.

    Inventory metadata includes inode, size, mode, mtime and ctime for every
    readonly texture and its directories. Thus ordinary content/identity changes
    invalidate the pack, including rewrites followed by restored mtime.
    """
    started = time.monotonic()
    work = Path(work)
    records, inventory_sha, client = texture_inputs(work, context)
    identity = hashlib.sha256(canonical({'format': FORMAT, 'import': import_identity,
        'client_executable_sha256': executable_sha256, 'client_work': client,
        'texture_inventory_sha256': inventory_sha})).hexdigest()
    target, marker = work / PACK, work / MARKER
    expected = {'format': FORMAT, 'identity': identity, 'records': len(records),
                'inventory_sha256': inventory_sha, 'client_executable_sha256': executable_sha256}
    saved = None
    if (marker.is_file() and not marker.is_symlink() and marker.stat().st_size < 16384
            and target.is_file() and not target.is_symlink() and 64 <= target.stat().st_size <= MAX_BYTES):
        try:
            candidate = json.loads(marker.read_bytes())
            if (all(candidate.get(key) == value for key, value in expected.items())
                    and candidate.get('bytes') == target.stat().st_size
                    and candidate.get('sha256') == hashlib.sha256(target.read_bytes()).hexdigest()):
                saved = candidate
        except (ValueError, OSError):
            pass
    reused = saved is not None
    if saved is None:
        context.event('stage', status='running', message='Indexing immutable texture headers', records=len(records))
        contents, header_sha = make_pack(records, identity, context)
        # Reject a concurrent mutation rather than publish a mixed generation.
        _, after, _ = texture_inputs(work, context)
        require(after == inventory_sha, 'Texture generation changed while indexing')
        saved = dict(expected, bytes=len(contents), sha256=hashlib.sha256(contents).hexdigest(),
                     original_header_bytes_sha256=header_sha)
        require(not target.is_symlink() and not marker.is_symlink(), 'Linked texture index output refused')
        atomic_write(target, contents)
        atomic_write(marker, canonical(saved) + b'\n')
    receipt = dict(saved, reused=reused, preparation_seconds=round(time.monotonic() - started, 3),
                   native_file_opens_avoidable=len(records), original_texture_files_unchanged=True,
                   native_fallback_available=True)
    environment = {'COH_TEXTURE_HEADER_PACK': 'Z:' + str(target).replace('/', '\\'),
                   'COH_TEXTURE_HEADER_ID': identity, 'COH_TEXTURE_DIAGNOSTIC_DEDUP': '1'}
    return receipt, environment
