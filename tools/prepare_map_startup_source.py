#!/usr/bin/env python3
"""Stage byte-certified animation checks after the retained monorail source.

Only Common/seq/animtrack.c is patched, all additions are guarded by SERVER,
and the only build target is MapServer. Game and renderer are not rebuilt.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import prepare_monorail_source as monorail
import map_startup_animation_certificate as certificate
import map_startup_monorail_budget as station_budget
from prepare_runtime import require, sha256
from prepare_resume_client_source import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'map-startup-build-input.json'
SOURCE = 'Common/seq/animtrack.c'
OVERLAY = 'database/map-startup/overlay/Common/seq/coh_animation_certificate.h'
TARGET = 'Common/seq/coh_animation_certificate.h'
TABLE = 'Common/seq/' + certificate.HEADER
RETAINED_SOURCES = ('Common/fxinfo.c', 'Common/seq/seqload.c', 'Common/seq/animtrackanimate.c',
    'libs/UtilitiesLib/src/utils/textparser.c', 'libs/UtilitiesLib/src/utils/file.c',
    'libs/UtilitiesLib/src/utils/FolderCache.c', 'libs/UtilitiesLib/src/utils/FolderCacheNode.c',
    'libs/UtilitiesLib/src/utils/piglib.c', 'libs/UtilitiesLib/src/utils/PigFileWrapper.c')
CONTRACT = {'format': 1, 'policy': 'actual_opened_pig_raw_bytes_full_sha256_before_pointer_fixup',
    'server_only': True, 'build_targets': ['MapServer'],
    'certified_tracks': 5878, 'certificate_schema': certificate.SCHEMA,
    'validator_version': certificate.VALIDATOR,
    'bounded_structure_and_offsets_always_checked': True,
    'full_position_and_rotation_payloads_retained': True, 'base_skeleton_linking_retained': True,
    'stock_key_validation_fallback': ['loose_input', 'unknown_name', 'changed_bytes', 'crypto_failure', 'header_only'],
    'client_or_renderer_changes': False, 'environment_trust_switch': False,
    'physical_startup_timing_validated': False, 'native_station_prepare_seconds': 720,
    'historical_station_prepare_seconds': 600}


def patch_source(original):
    """Exact occurrence guards prevent silent rebase or altered stock validators."""
    text = original.decode('utf-8')
    replacements = (
        ('#include <utilitieslib/utils/timing.h>\n', '#include <utilitieslib/utils/timing.h>\n'
            '#ifdef SERVER\n#include "coh_animation_certificate.h"\n#endif\n'),
        ('    int file_size, i;\n', '    int file_size, i;\n#ifdef SERVER\n'
            '    int cohTotalBytes, cohCertified = 0;\n'
            '    unsigned __int64 cohStockStart = 0;\n#endif\n'),
        ('    if( load_type == LOAD_ALL || load_type == LOAD_ALL_SHARED )\n    {\n        file_size = fileGetSize( file );\n',
            '#ifdef SERVER\n    cohTotalBytes = fileGetSize( file );\n'
            '    if (cohTotalBytes < 596 || cohTotalBytes > 8 * 1024 * 1024)\n'
            '        FatalErrorFilenamef(fileName, "Invalid bounded animation file length");\n#endif\n'
            '    if( load_type == LOAD_ALL || load_type == LOAD_ALL_SHARED )\n    {\n        file_size = fileGetSize( file );\n'),
        ('        fread( &file_size, sizeof( int ), 1, file );    \n',
            '#ifdef SERVER\n        if (fread(&file_size, sizeof(int), 1, file) != 1)\n'
            '            FatalErrorFilenamef(fileName, "Incomplete bounded animation size header");\n'
            '#else\n        fread( &file_size, sizeof( int ), 1, file );    \n#endif\n'),
        ('    if ( load_type == LOAD_ALL_SHARED )\n    {\n        bool bSuccess = sharedHeapAlloc( pHandle, file_size );\n',
            '#ifdef SERVER\n    if (file_size < 596 || file_size > cohTotalBytes)\n'
            '        FatalErrorFilenamef(fileName, "Invalid bounded animation allocation length");\n#endif\n'
            '    if ( load_type == LOAD_ALL_SHARED )\n    {\n        bool bSuccess = sharedHeapAlloc( pHandle, file_size );\n'),
        ('    assert( skeleton );\n    fread( skeleton, 1, file_size, file );\n    skeleton->backupAnimTrack = NULL;\n',
            '    assert( skeleton );\n#ifdef SERVER\n'
            '    if (file_size < 596 || file_size > cohTotalBytes || fread(skeleton, 1, file_size, file) != (intptr_t)file_size\n'
            '        || !cohAnimationRawBounds((const unsigned char *)skeleton, (unsigned int)file_size, (unsigned int)cohTotalBytes))\n'
            '        FatalErrorFilenamef(fileName, "Invalid bounded animation raw structure");\n'
            '    if (load_type == LOAD_ALL || load_type == LOAD_ALL_SHARED) {\n'
            '        cohCertified = cohAnimationCertificateMatch(fileName, (const unsigned char *)skeleton, (unsigned int)file_size, file->iomode == IO_PIG);\n'
            '        cohAnimationCertificateCountKeys((const unsigned char *)skeleton, cohCertified);\n'
            '        if (!cohCertified) cohStockStart = cohAnimationClockMicroseconds();\n'
            '    }\n#else\n    fread( skeleton, 1, file_size, file );\n#endif\n'
            '    skeleton->backupAnimTrack = NULL;\n'),
        ('            animDebugCheckBoneTrackOnLoad( bt, fileName );\n',
            '#ifdef SERVER\n            if (!cohCertified)\n#endif\n'
            '            animDebugCheckBoneTrackOnLoad( bt, fileName );\n'),
        ('    if( skeleton->skeletonHeirarchy )\n        skeleton->skeletonHeirarchy = (void*)((size_t)skeleton->skeletonHeirarchy + (size_t)skeleton);\n\n    if ( load_type == LOAD_ALL_SHARED )\n',
            '    if( skeleton->skeletonHeirarchy )\n        skeleton->skeletonHeirarchy = (void*)((size_t)skeleton->skeletonHeirarchy + (size_t)skeleton);\n\n'
            '#ifdef SERVER\n    if (cohStockStart) {\n'
            '        unsigned __int64 end = cohAnimationClockMicroseconds();\n'
            '        if (end >= cohStockStart) cohAnimationCertificateCounters.stock_microseconds += end - cohStockStart;\n'
            '    }\n    if (cohAnimationCertificateCounters.opened && cohAnimationCertificateCounters.opened % 1024 == 0)\n'
            '        cohAnimationCertificatePrint();\n#endif\n'
            '    if ( load_type == LOAD_ALL_SHARED )\n'),
    )
    for old, new in replacements:
        require(text.count(old) == 1, 'Animation source patch anchor differs: ' + old[:80])
        text = text.replace(old, new, 1)
    return text.encode('utf-8')


def expected_receipt(animation_certificate, root=ROOT, monorail_build_input=None):
    root = Path(root)
    base = monorail.expected_receipt(root, None if monorail_build_input is None else monorail_build_input.get('events_build_input'))
    require(monorail_build_input is None or monorail_build_input == base, 'Map startup monorail prerequisite differs')
    certificate.validate_receipt(animation_certificate, root)
    original = (root / 'upstream/ouroboros' / SOURCE).read_bytes().replace(b'\r\n', b'\n')
    overlay = (root / OVERLAY).read_bytes().replace(b'\r\n', b'\n')
    budget = station_budget.expected_receipt(root)
    return {'schema_version': 1, 'build_role': 'map_startup_certified_animation',
        'source_commit': base['source_commit'], 'monorail_build_input': base,
        'monorail_build_input_canonical_sha256': canonical_hash(base),
        'source_sha256': {SOURCE: hashlib.sha256(original).hexdigest(), **budget['source_sha256']},
        'patched_sha256': {SOURCE: hashlib.sha256(patch_source(original)).hexdigest(), **budget['patched_sha256']},
        'overlay_sha256': {TARGET: hashlib.sha256(overlay).hexdigest(), TABLE: animation_certificate['generated_table']['sha256']},
        'retained_sources_sha256': {name: sha256(root / 'upstream/ouroboros' / name) for name in RETAINED_SOURCES},
        'animation_certificate': animation_certificate,
        'animation_certificate_canonical_sha256': canonical_hash(animation_certificate),
        'monorail_budget': budget, 'monorail_budget_canonical_sha256': canonical_hash(budget),
        'contract': CONTRACT, 'build_targets': ['MapServer'], 'runtime_validation': 'unverified'}


def apply_startup_overlay(source, animations_pigg, animation_manifest, root=ROOT):
    source, root = Path(source).resolve(), Path(root).resolve()
    require(source != root and root / 'upstream' not in (source, *source.parents), 'Immutable startup staging refused')
    require(not (source / RECEIPT).exists() and not (source / RECEIPT).is_symlink(), 'Map startup overlay already staged')
    previous = source / monorail.RECEIPT
    require(previous.is_file() and not previous.is_symlink(), 'Missing monorail startup prerequisite')
    table, document = certificate.generate(animations_pigg, animation_manifest)
    expected = expected_receipt(document, root, json.loads(previous.read_text()))
    for name, digest in {**expected['monorail_build_input']['patched_sha256'],
                         **expected['monorail_build_input']['overlay_sha256'],
                         **expected['monorail_build_input']['retained_collision_sources'],
                         **expected['retained_sources_sha256']}.items():
        target = source / name
        require(target.is_file() and not target.is_symlink() and not any(p.is_symlink() for p in target.parents)
                and sha256(target) == digest, 'Map startup retained source differs: ' + name)
    require(sha256(source / SOURCE) == expected['source_sha256'][SOURCE], 'Animation source input differs')
    for name, data in ((TARGET, (root / OVERLAY).read_bytes().replace(b'\r\n', b'\n')), (TABLE, table)):
        target = source / name
        require(not target.exists() and not target.is_symlink(), 'Map startup overlay target exists: ' + name)
        require(not any(p.is_symlink() for p in target.parents), 'Map startup overlay parent is linked')
        target.write_bytes(data)
    target = source / SOURCE
    require(not target.is_symlink() and not any(p.is_symlink() for p in target.parents), 'Map startup source is linked')
    target.write_bytes(patch_source(target.read_bytes()))
    require(sha256(target) == expected['patched_sha256'][SOURCE], 'Map startup patched source differs')
    require(station_budget.apply_budget_overlay(source, root) == expected['monorail_budget'],
            'Map startup native station budget differs')
    (source / RECEIPT).write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    return expected


def prepare(output, animations_pigg, animation_manifest, root=ROOT):
    monorail.prepare(output, root)
    return apply_startup_overlay(output, animations_pigg, animation_manifest, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--animations-pigg', required=True, type=Path)
    parser.add_argument('--animation-manifest', required=True, type=Path)
    args = parser.parse_args()
    receipt = prepare(args.output, args.animations_pigg, args.animation_manifest)
    print(json.dumps({'status': 'staged_mapserver_only', 'build_targets': receipt['build_targets'],
                      'certificate_tracks': receipt['animation_certificate']['validated_track_count']}))


if __name__ == '__main__':
    main()
