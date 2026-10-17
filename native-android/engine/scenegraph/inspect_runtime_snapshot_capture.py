#!/usr/bin/env python3
"""Inspect the retained 38977202310 artifact; reuse its qualified C decoder.

This reads only bounded container framing and explicit scalar observations. It
does not implement sendDef/sendMat4, admit assets, or construct a live graph.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import math
import struct
import subprocess
import zipfile
import zlib

REVISION = '3e8b5c9f5b794b58a66c6d8c62a593b926a10873'
ARCHIVE_SHA = '8763048abd0d55070159955f02ae9d72e452aa44d1da6e6603a22637732d764d'
CATALOG_SHA = '61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763'
SNAPSHOT_SHA = 'c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02'
NAMES = ('_cot_warpgate_base', '_cot_warpgate_glow', '_mmayhem_curtain_8_01c',
         '_mmayhem_curtain_8_02c', '_mmayhem_curtain_8_03c',
         '_mmayhem_curtain_16_01c', '_mmayhem_curtain_16_02c')
FLAGS = ('breakable', 'child_breakable', 'is_tray', 'child_tray', 'has_ambient',
         'child_ambient', 'has_light', 'child_light', 'has_cubemap', 'child_cubemap',
         'has_fog', 'child_has_fog', 'has_volume', 'child_volume', 'has_beacon',
         'child_beacon', 'open_tracker', 'has_properties', 'child_properties',
         'no_fog_clip', 'child_no_fog_clip', 'is_autogroup', 'child_volume_trigger',
         'no_coll', 'do_welding', 'editor_visible_only')


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, maximum=16 * 1024**2):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum,
            'Invalid or oversized input: ' + str(path))
    return path.read_bytes()


def document(path):
    return json.loads(read(path, 1024**2))


class Framing:
    def __init__(self, raw, offset=0):
        self.raw, self.at = raw, offset

    def take(self, count):
        require(0 <= count <= len(self.raw) - self.at, 'Truncated framing')
        result = self.raw[self.at:self.at + count]
        self.at += count
        return result

    def integers(self, count):
        return struct.unpack('<' + 'I' * count, self.take(count * 4))

    def string(self, count):
        raw = self.take(count)
        require(2 <= count <= 256 and raw[-1] == 0 and
                all(32 <= value <= 126 for value in raw[:-1]), 'Invalid string')
        return raw[:-1].decode('ascii')


def catalog_files(raw):
    require(raw[:8] == b'COHCAT01', 'Catalog magic')
    values = struct.unpack_from('<10I', raw, 8)
    require(values[:5] == (1, 48, len(raw), 20261016, 508), 'Catalog header')
    cursor, files, slots, records = Framing(raw, 48), [], 0, 0
    for index in range(508):
        actual, checksum, count, allocated, length = cursor.integers(5)
        require(actual == index and allocated <= count <= 65536, 'Catalog file order')
        files.append({'index': index, 'path': cursor.string(length),
                      'slots': count, 'bounds_checksum': checksum})
        last = -1
        for _ in range(allocated):
            slot, bits, size, aligned = cursor.integers(4)
            require(last < slot < count and bits == size * 8 and aligned == 1,
                    'Catalog record framing')
            cursor.take(size)
            last = slot
        slots += count
        records += allocated
    require(cursor.at == len(raw) and slots == records == 40225, 'Catalog closure')
    return files


def bounds(raw):
    values = struct.unpack('<13f2I', raw)
    require(all(math.isfinite(value) for value in values[:13]), 'Nonfinite bounds')
    require(values[13] <= 0x7fffffff and values[14] < 1 << 26, 'Bounds integers')
    return {'min': list(values[0:3]), 'max': list(values[3:6]), 'mid': list(values[6:9]),
            'vis_dist': values[9], 'radius': values[10], 'lod_scale': values[11],
            'shadow_dist': values[12], 'recursive_count': values[13],
            'flags_in_original_declaration_order': values[14],
            'active_flags': [name for bit, name in enumerate(FLAGS) if values[14] & (1 << bit)],
            'sha256': sha(raw)}


def inspect(raw, files, native):
    require(raw[:8] == b'COHRTS01', 'Snapshot magic')
    fields = struct.unpack_from('<18I', raw, 8)
    require(fields == (1, 80, 6585, 20261016, 12179670, 508, 40225, 40225,
                       130314, 33, 33, 7, 3173822562, 3649375123, 0, 0, 0, 0),
            'Exact snapshot header')
    cursor, roots, external = Framing(raw, 80), [], []
    for ordinal in range(33):
        slot, present, kind, file_index, definition, name_bytes, bits, size = cursor.integers(8)
        require(slot == ordinal and present == kind == 1 and file_index < len(files),
                'Actual root identity')
        require(definition < files[file_index]['slots'] and bits == size * 8 and size <= 256,
                'Root bounds')
        name, matrix = cursor.string(name_bytes), cursor.take(48)
        values = struct.unpack('<12f', matrix)
        require(all(map(math.isfinite, values)), 'Root finite matrix')
        wire = cursor.take(size)
        roots.append({'root_slot': slot, 'file': file_index,
                      'file_path': files[file_index]['path'], 'definition_slot': definition,
                      'name': name, 'matrix_columns': [list(values[i:i+3]) for i in range(0, 12, 3)],
                      'source_matrix_sha256': sha(matrix), 'wire_bytes': size,
                      'source_wire_sha256': sha(wire), 'native_matrix_pair_verified': True})
    for ordinal in range(7):
        actual, original_id, ownership, model, length, bits, size, found, path_bytes = cursor.integers(9)
        require(actual == ordinal and original_id == 0 and ownership == 15 and
                model == found == path_bytes == 0 and bits == size * 8, 'Actual future identity')
        live, lookup = bounds(cursor.take(60)), bounds(cursor.take(60))
        name = cursor.string(length)
        wire = cursor.take(size)
        require(name == NAMES[ordinal] == native['external'][ordinal]['name'], 'Future ordering')
        external.append({'ordinal': ordinal, 'name': name, 'original_id': original_id,
                         'source_ownership_bits': ownership, 'live_bounds': live,
                         'scratch_lookup_bounds': lookup, 'wire_bytes': size,
                         'source_wire_sha256': sha(wire), **native['external'][ordinal]})
    require(cursor.at == len(raw), 'Snapshot trailing bytes')
    return roots, external


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', required=True, type=Path)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root, extracted = args.artifact_root, args.artifact_root / 'files'
    archive = read(root / 'artifact.zip')
    require(len(archive) == 2024961 and sha(archive) == ARCHIVE_SHA, 'Artifact pin')
    members = document(root / 'artifact-members.json')
    expected = {item['file']: item for item in members}
    with zipfile.ZipFile(root / 'artifact.zip') as zipped:
        require(len(zipped.infolist()) == len(expected) == 34, 'Artifact members')
        expanded = 0
        for item in zipped.infolist():
            path = PurePosixPath(item.filename)
            require(not path.is_absolute() and '..' not in path.parts and
                    item.filename in expected and item.file_size <= 16 * 1024**2, 'Unsafe member')
            raw = zipped.read(item)
            proof = expected[item.filename]
            require(proof == {'file': item.filename, 'bytes': len(raw), 'sha256': sha(raw),
                              'zip_crc32': format(zlib.crc32(raw), '08x')}, 'ZIP receipt mismatch')
            require(raw == read(extracted / item.filename), 'Extracted member changed')
            expanded += len(raw)
        require(expanded == 12324476, 'Expanded size')
    capture = extracted / 'capture'
    binding = document(capture / 'snapshot-binding.json')
    receipt = document(capture / 'capture-receipt.json')
    source = document(capture / 'source-identity.json')
    run = document(capture / 'run-identity.json')
    qualified = document(extracted / 'runtime-graph-diagnostic.json')
    require(binding['schema'] == 'coh-runtime-snapshot-binding-v1' and
            binding['source_snapshot_only'] is True and binding['cleanup_verified'] is True and
            binding['live_groups_transaction'] is False and binding['asset_generation'] == 20261016,
            'Binding scope')
    for key, filename in [('catalog', 'catalog.cohcat'), ('snapshot', 'runtime.cohrts')]:
        raw = read(capture / filename)
        require(binding[key] == {'bytes': len(raw), 'sha256': sha(raw)} == receipt[key], 'Pair pin')
    require(binding['catalog']['sha256'] == CATALOG_SHA and binding['snapshot']['sha256'] == SNAPSHOT_SHA,
            'Preserved catalog/snapshot identity')
    for key, filename in [('source_identity', 'source-identity.json'), ('run_identity', 'run-identity.json')]:
        require(binding[key] == {'file': filename, 'sha256': sha(read(capture / filename))}, 'Identity pin')
    require(source['exporter_source_revision'] == run['orchestration_source_revision'] == REVISION,
            'Source revision')
    require(run['source_identity_sha256'] == binding['source_identity']['sha256'], 'Run/source binding')
    require(receipt['passed'] is True and receipt['catalog_exact_equality'] is True and
            receipt['source_runtime_unchanged'] is True and receipt['cleanup_verified'] is True and
            receipt['owned_process_groups_absent'] is True and receipt['matching_groups_transaction_captured'] is False,
            'Capture/cleanup receipt')
    for key, filename in [('exporter', 'MapServer.exe')]:
        raw = read(args.candidate / filename)
        require(source[key] == {'bytes': len(raw), 'sha256': sha(raw)}, 'Exact exporter')
    for key, filename in [('compile_receipt_sha256', 'compile-only-receipt.json'),
                          ('stage_receipt_sha256', 'native-runtime-snapshot-server-build-input.json')]:
        require(source[key] == sha(read(args.candidate / filename)), 'Exporter receipt')
    maps = {key: qualified[key] for key in ('native_source_sha256', 'producer_source_sha256', 'original_helper_sha256')}
    maps['orchestration_source_sha256'] = source['orchestration_source_sha256']
    for entries in maps.values():
        for path, digest in entries.items():
            raw = subprocess.check_output(['git', '-C', str(args.source_root), 'show', REVISION + ':' + path])
            require(sha(raw) == digest, 'Source Git blob: ' + path)
    originals = dict(qualified['source_oracle']['original_source']['sha256_lf'])
    originals['Common/group/group.h'] = qualified['source_oracle']['original_group_header_sha256_lf']
    for path, digest in originals.items():
        raw = subprocess.check_output(['git', '-C', str(args.source_root), 'show',
                                       REVISION + ':upstream/ouroboros/' + path])
        require(sha(raw.replace(b'\r\n', b'\n')) == digest, 'Original Git blob: ' + path)
    require(qualified['passed'] is True and qualified['actual_snapshot_qualified'] is True, 'Hosted decoder')
    require(qualified['capture_pins'] == {'asset_generation': 20261016, 'catalog_sha256': CATALOG_SHA,
            'snapshot_sha256': SNAPSHOT_SHA, 'source_sha256': binding['source_identity']['sha256'],
            'run_sha256': binding['run_identity']['sha256']}, 'Decoder pins')
    native = qualified['captured']['release']
    require(set(qualified['captured']) == {'release', 'asan', 'ubsan'} and
            all(value == native for value in qualified['captured'].values()), 'Qualification modes')
    require(native['definitions_crc_verified'] == native['references_crc_verified'] == 1 and
            native['root_matrices_verified'] == 33, 'CRC/matrix verification')
    require([item['reachable'] for item in native['external']] == [0, 0, 1, 0, 0, 0, 0], 'Reachability result')
    for name in ('graph_published', 'assets_admitted', 'groups_received', 'actor_admitted', 'world_authority'):
        require(native[name] is False and qualified[name] is False, 'Unexpected authority')
    roots, external = inspect(read(capture / 'runtime.cohrts'), catalog_files(read(capture / 'catalog.cohcat')), native)
    result = {'schema': 'coh-captured-runtime-snapshot-inspection-v1', 'passed': True,
              'source_revision': REVISION, 'run_id': 38977202310, 'artifact_id': 12079509924,
              'artifact_sha256': ARCHIVE_SHA, 'artifact_bytes': len(archive), 'zip_members_verified': 34,
              'expanded_bytes': expanded, 'source_hash_counts': {key: len(value) for key, value in maps.items()},
              'original_full_file_lf_hashes_verified': len(originals), 'binding': binding,
              'hosted_diagnostic_sha256': sha(read(extracted / 'runtime-graph-diagnostic.json')),
              'qualified_native_result': native, 'roots': roots, 'external_observations': external,
              'analysis_driver_sha256': sha(Path(__file__).read_bytes()),
              'new_native_test_runs': 0, 'server_restarts': 0, 'source_snapshot_only': True,
              'graph_published': False, 'live_groups_transaction': False, 'world_authority': False,
              'android_executed': False, 'physical_thor_accepted': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'passed': True, 'roots': len(roots), 'external': len(external),
                      'reachable_future': NAMES[2], 'output': str(args.output)}))


if __name__ == '__main__':
    main()
