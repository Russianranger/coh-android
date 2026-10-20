#!/usr/bin/env python3
"""Recover byte-exact original Huge animations retained inside a COHRIG01 asset.

No animation is regenerated: source spans must match the existing original
fixture pins. The output is suitable for building a palette for another genuine
Huge mesh, independently of the older fixture mesh that carried this container.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import struct
import tempfile
import zipfile

NATIVE = Path(__file__).resolve().parents[2]
MAX_RIG = 2 << 20


def recover(raw):
    if len(raw) < 128 or len(raw) > MAX_RIG:
        raise ValueError('Retained rig size differs')
    magic, version, header, base, base_bytes, motion, motion_bytes, palette, count, socket, reserved = struct.unpack_from('<8s10I', raw)
    total = struct.unpack_from('<I', raw, 60)[0]
    if (magic != b'COHRIG01' or version != 1 or header != 128 or base != header
            or motion != base + base_bytes or palette != motion + motion_bytes
            or not 0 < count <= 99 or socket >= 99 or reserved
            or palette + count * 4 != len(raw) or total != len(raw)):
        raise ValueError('Retained rig span framing differs')
    pins = json.loads((NATIVE / 'tools/animation_fixture/pins.json').read_text())
    path = NATIVE / 'tools/animation_fixture/prepare.py'
    spec = importlib.util.spec_from_file_location('huge_original_animation_format', path)
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    result = {}
    for identity, offset, size in [('base', base, base_bytes), ('motion', motion, motion_bytes)]:
        pin = next(item for item in pins['records'] if item['id'] == identity)
        body = raw[offset:offset + size]
        if len(body) != pin['size'] or hashlib.sha256(body).hexdigest() != pin['sha256']:
            raise ValueError('Retained original Huge animation SHA differs: ' + identity)
        metadata, _ = source.inspect_animation(body)
        expected = 'huge/skel_ready' if identity == 'base' else 'huge/run'
        if metadata['name'].casefold() != expected or metadata['base_anim_name'].casefold() != 'huge/skel_ready':
            raise ValueError('Original Huge animation identity differs')
        result[pin['file_name']] = body
    return result


def read_rig(path, apk=False):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Retained rig input must be a regular file')
    if not apk:
        if path.stat().st_size > MAX_RIG:
            raise ValueError('Retained rig exceeds its original animation bound')
        return path.read_bytes()
    # The APK is a bounded package inventory, not the large game archive index.
    # Inspect its central-directory bound before zipfile materializes that list.
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size - 65557))
        tail = stream.read(65557)
    offset = tail.rfind(b'PK\x05\x06')
    if offset < 0 or offset + 22 > len(tail):
        raise ValueError('APK ZIP32 directory missing')
    disk, directory_disk, disk_count, count, directory_bytes, _, comment = struct.unpack_from('<4H2IH', tail, offset + 4)
    if disk or directory_disk or disk_count != count or count > 4096 or directory_bytes > 1 << 20 or offset + 22 + comment != len(tail):
        raise ValueError('APK directory exceeds the bounded package inventory')
    with zipfile.ZipFile(path) as archive:
        entry = archive.getinfo('assets/rig.bin')
        if entry.file_size > MAX_RIG or entry.flag_bits & 1 or entry.compress_type not in (0, 8):
            raise ValueError('APK retained rig envelope differs')
        return archive.read(entry)


def publish(source, output, apk=False):
    bodies = recover(read_rig(source, apk))
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Recovered source output already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-huge-original-', dir=output.parent) as temporary:
        stage = Path(temporary)
        for name, body in bodies.items():
            (stage / name).write_bytes(body)
        os.rename(stage, output)
    return {name: {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()} for name, body in bodies.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--rig', type=Path)
    inputs.add_argument('--apk', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps({'original_bytes_recovered': True, 'regenerated': False,
                      'assets': publish(args.apk or args.rig, args.output, args.apk is not None)}))


if __name__ == '__main__':
    main()
