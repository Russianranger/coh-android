#!/usr/bin/env python3
"""Check bounded FD lookup with actual retained APK and original Atlas ranges."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import struct
import tempfile
import tracemalloc
import zipfile
from imported_archive import ImportedArchive, BODY_LIMIT
from recover_huge_rig import recover

ATLAS = [
    ('data/object_library/streets/road_4lane/road_4lane.geo', 109481, '43bd2f6f192bdfc88f44328657f5c16b042d0dea9bb34b1e5e1704befeb8bcd2'),
    ('data/texture_library/world/streets/streets/street_sidewalk1.texture', 175067, 'a2bd476cc82ff8175d5c23f98f1c4ea709c70cf0ba6fe3bd2f699b168ee00dab'),
]


def opened(path, offset=0, length=None):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    try:
        return ImportedArchive(fd, offset, length)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--atlas', type=Path, required=True)
    args = parser.parse_args()
    controls = 0
    tracemalloc.start()
    with opened(args.apk) as archive:
        entries = archive.lookup(paths=['ASSETS/RIG.BIN'])
        assert len(entries) == 1
        rig = archive.read_body(entries[0])
        bodies = recover(rig)
        assert len(bodies['base.anim']) == 6171
        controls += 2
        try:
            archive.read_body(entries[0], {'bytes': len(rig), 'sha256': '0' * 64})
            raise AssertionError('Wrong member pin accepted')
        except ValueError:
            controls += 1
    with opened(args.atlas) as archive:
        entries = archive.lookup(paths=[row[0].upper() for row in ATLAS], texture_names=['street_sidewalk1.tga'])
        assert len(entries) == 2 and len(archive.members) == 2
        controls += 1
        for entry, (name, size, digest) in zip(entries, ATLAS):
            assert entry.name == name
            body = archive.read_body(entry, {'bytes': size, 'sha256': digest})
            assert len(body) == size
            controls += 2
        assert not archive.lookup(paths=['data/player_library/huge_emblem.geo'])
        controls += 1
        atlas_reads = archive.read_bytes
    # Generated format controls below contain the exact original Huge animation
    # bytes, not new geometry or textures and not original archive provenance.
    with tempfile.TemporaryDirectory(prefix='coh-imported-source-check-') as temporary:
        root = Path(temporary)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as source:
            source.writestr('assets/player_library/animations/huge/skel_ready.anim', bodies['base.anim'])
        raw = buffer.getvalue()
        path = root / 'span.bin'
        path.write_bytes(bytes(37) + raw + bytes(19))
        before = len(os.listdir('/proc/self/fd'))
        for _ in range(64):
            with opened(path, 37, len(raw)) as archive:
                entries = archive.lookup(paths=['assets/player_library/animations/huge/skel_ready.anim'])
                assert archive.read_body(entries[0]) == bodies['base.anim']
                controls += 1
        assert len(os.listdir('/proc/self/fd')) == before
        controls += 1
        with opened(path, 37, len(raw)) as archive:
            selected = archive.lookup(paths=['assets/player_library/animations/huge/skel_ready.anim'])[0]
            with opened(path, 37, len(raw)) as other:
                try:
                    other.read_body(selected)
                    raise AssertionError('Cross-owner entry accepted')
                except ValueError:
                    controls += 1
            with path.open('r+b') as changed:
                changed.seek(0)
                changed.write(b'x')
            try:
                archive.read_body(selected)
                raise AssertionError('Changed source identity accepted')
            except ValueError:
                controls += 1
        for name, edit in [('crc', 16), ('size', 24), ('flags', 8)]:
            altered = bytearray(raw)
            central = altered.index(b'PK\x01\x02')
            if name == 'size':
                struct.pack_into('<I', altered, central + edit, BODY_LIMIT + 1)
            else:
                altered[central + edit] ^= 1
            damaged = root / name
            damaged.write_bytes(altered)
            with opened(damaged) as archive:
                try:
                    entries = archive.lookup(paths=['assets/player_library/animations/huge/skel_ready.anim'])
                    archive.read_body(entries[0])
                    raise AssertionError('Invalid archive accepted: ' + name)
                except ValueError:
                    controls += 1
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(json.dumps({'passed': True, 'controls': controls, 'retained_catalog_rows': 2,
                      'original_atlas_read_bytes': atlas_reads, 'python_traced_peak_bytes': peak,
                      'whole_archive_sha_proof': False, 'scope': 'Actual retained APK rig and original Atlas partial ranges; generated format controls; no Thor CLIENT lookup'}))


if __name__ == '__main__':
    main()
