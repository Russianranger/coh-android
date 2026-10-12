#!/usr/bin/env python3
"""Certify every original track before generating a SERVER-only native table.

Certificates bind opened raw bytes, not an environment switch or filename trust.
The native path still checks disk bounds and preserves full engine pointer/base
setup. Unknown, loose, changed or unhashed data retains stock per-key validation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'android/guest'))
import server_animation_package as package
from animation_format import animation_header, animation_dependency_report

SCHEMA = 1
VALIDATOR = 'original-win32-animation-loader-numeric-and-bounded-structure-v1'
HEADER = 'coh_animation_certificate_table.h'
RECEIPT = 'animation-certificate.json'
require = package.require
PACK_PIN = {'animation_count': 5878, 'bytes': 97084456, 'metadata_bytes': 8703726,
            'original_animation_bytes': 88380730,
            'sha256': '465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b'}
TABLE_PIN = {'bytes': 1363915, 'sha256': '179f8a15614dd42c9222be4d3716986bc9c0716a41d6045ef8f2ef7dc83427c4'}
DEPENDENCY_SHA256 = '03236d08d8b33300cc27e614a25cbe37f6556ebe1c35132ab230a31170db33c9'
VALIDATOR_SOURCES = ('tools/animation_format.py', 'tools/map_startup_animation_certificate.py',
    'android/guest/server_animation_package.py', 'upstream/ouroboros/Common/seq/animtrack.c',
    'upstream/ouroboros/Common/seq/animtrack.h', 'upstream/ouroboros/Common/seq/bones.h')


def pin(path):
    return package.file_pin(path)


def generate(pigg, manifest):
    document = package.verify_package(pigg, manifest)
    require(document['pigg'] == PACK_PIN, 'Animation certificate original packed identity differs')
    files = document['files']
    entries, facts = [], []
    with Path(pigg).open('rb') as stream:
        stream.seek(package.HEADER.size)
        table = stream.read(package.ENTRY.size * len(files))
        for index, name in enumerate(sorted(files, key=str.upper)):
            _, _, size, _, offset, _, _, _, _ = package.ENTRY.unpack_from(table, index * package.ENTRY.size)
            stream.seek(offset)
            body = stream.read(size)
            require(len(body) == size and hashlib.sha256(body).hexdigest() == files[name]['sha256'],
                    'Animation raw bytes differ during certification: ' + name)
            fact = animation_header(body)
            require(fact['validation_status'] == 'structural_checks_passed',
                    'Animation full key validation failed: ' + name)
            require(fact['name'].replace('\\', '/').casefold() == name[len('player_library/animations/'):-5],
                    'Animation embedded name differs: ' + name)
            facts.append(fact)
            entries.append((name, size, files[name]['sha256']))
    closure = animation_dependency_report(facts)
    require(closure['validated_track_count'] == package.ANIMATION_COUNT
            and all(not closure[key] for key in ('invalid_header_names', 'duplicate_casefolded_names',
                'missing_base_names', 'nonterminal_cycles', 'terminal_bases_without_hierarchy'))
            and closure['terminal_base_count'] > 0, 'Animation dependency closure failed')
    entries.sort()
    raw = ['/* Generated only from fully validated original animation bytes. */',
           '#ifndef COH_ANIMATION_CERTIFICATE_TABLE_H', '#define COH_ANIMATION_CERTIFICATE_TABLE_H',
           '#define COH_ANIMATION_CERTIFICATE_SCHEMA 1',
           '#define COH_ANIMATION_CERTIFICATE_PACK_SHA256 "' + document['pigg']['sha256'] + '"',
           '#define COH_ANIMATION_CERTIFICATE_INVENTORY_SHA256 "' + package.INVENTORY_SHA256 + '"',
           '#define COH_ANIMATION_CERTIFICATE_COUNT ' + str(len(entries)),
           'typedef struct CohAnimationCertificateEntry { const char *name; unsigned int bytes; unsigned char sha256[32]; } CohAnimationCertificateEntry;',
           'static const CohAnimationCertificateEntry cohAnimationCertificateEntries[] = {']
    for name, size, digest in entries:
        octets = ','.join('0x' + digest[i:i+2] for i in range(0, 64, 2))
        raw.append('    {"%s",%du,{%s}},' % (name, size, octets))
    raw.extend(('};', '#endif', ''))
    output = '\n'.join(raw).encode('ascii')
    receipt = {'format': SCHEMA, 'role': 'server_raw_animation_certificate',
               'validator_version': VALIDATOR, 'original_animation_identity': document['identity'],
               'original_animation_pack': document['pigg'], 'animation_inventory_sha256': package.INVENTORY_SHA256,
               'dependency_closure': closure, 'validated_track_count': len(entries),
               'validated_raw_bytes': sum(size for _, size, _ in entries),
               'rotation_key_count': sum(f['rotation_key_count'] for f in facts),
               'position_key_count': sum(f['position_key_count'] for f in facts),
               'validator_sources': {name: pin(ROOT / name) for name in VALIDATOR_SOURCES},
               'generated_table': {'bytes': len(output), 'sha256': hashlib.sha256(output).hexdigest()},
               'native_execution_validated': False, 'physical_startup_timing_validated': False}
    validate_receipt(receipt)
    return output, receipt


def validate_receipt(receipt, root=ROOT):
    require(isinstance(receipt, dict) and receipt.get('format') == SCHEMA
            and receipt.get('role') == 'server_raw_animation_certificate'
            and receipt.get('validator_version') == VALIDATOR
            and receipt.get('original_animation_identity') == package.identity()
            and receipt.get('original_animation_pack') == PACK_PIN
            and receipt.get('animation_inventory_sha256') == package.INVENTORY_SHA256
            and type(receipt.get('validated_track_count')) is int and receipt['validated_track_count'] == 5878
            and type(receipt.get('validated_raw_bytes')) is int and receipt['validated_raw_bytes'] == 88380730
            and type(receipt.get('rotation_key_count')) is int and receipt['rotation_key_count'] == 11894088
            and type(receipt.get('position_key_count')) is int and receipt['position_key_count'] == 2083384
            and receipt.get('generated_table') == TABLE_PIN
            and receipt.get('validator_sources') == {name: pin(Path(root) / name) for name in VALIDATOR_SOURCES}
            and receipt.get('native_execution_validated') is False
            and receipt.get('physical_startup_timing_validated') is False,
            'Animation certificate typed source/byte identity differs')
    closure = receipt.get('dependency_closure', {})
    require(hashlib.sha256(package.canonical(closure)).hexdigest() == DEPENDENCY_SHA256
            and closure.get('validated_track_count') == 5878 and closure.get('terminal_base_count') == 385
            and isinstance(closure.get('terminal_base_names'), list) and len(closure['terminal_base_names']) == 385
            and all(closure.get(key) == [] for key in ('invalid_header_names', 'duplicate_casefolded_names',
                'missing_base_names', 'nonterminal_cycles', 'terminal_bases_without_hierarchy')),
            'Animation certificate typed base closure differs')
    return receipt


def write(pigg, manifest, output):
    table, receipt = generate(pigg, manifest)
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / HEADER).write_bytes(table)
    (directory / RECEIPT).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--animations-pigg', required=True, type=Path)
    parser.add_argument('--animation-manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    receipt = write(args.animations_pigg, args.animation_manifest, args.output)
    print(json.dumps({'status': 'certified_original_track_bytes', 'tracks': receipt['validated_track_count'],
                      'raw_bytes': receipt['validated_raw_bytes'], 'generated_table': receipt['generated_table']}))


if __name__ == '__main__':
    main()
