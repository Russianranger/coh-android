#!/usr/bin/env python3
"""Stage a nonshipping SERVER BIN-freshness observer in an isolated native tree.

This source/algorithm prerequisite does not build or change the published APK.
The observer leaves every stock loader operation, freshness decision and decoder
unchanged. Native Windows/Wine timing and physical Thor evidence remain required.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import map_startup_namespace_certificate as namespace

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'libs/UtilitiesLib/src/utils/textparser.c'
TARGET = 'libs/UtilitiesLib/src/utils/coh_map_bin_observer.h'
OVERLAY = 'database/map-startup-observer/overlay/' + TARGET
RECEIPT = 'map-startup-observer-build-input.json'
SIGNATURE = 'SimpleBufHandle ParserIsPersistNewer('
RETAINED = (
    'libs/UtilitiesLib/src/utils/FolderCache.c',
    'libs/UtilitiesLib/src/utils/FolderCacheNode.c',
    'libs/UtilitiesLib/src/utils/file.c',
    'libs/UtilitiesLib/src/utils/structInternals.c',
    'Common/seq/seqload.c', 'Common/fxinfo.c',
)
CONTRACT = {
    'format': 1, 'role': 'nonshipping_server_bin_freshness_observation_prerequisite',
    'server_only': True, 'shipping_workflow_referenced': False,
    'observation_limit': 256, 'rows_per_observed_call': 1,
    'additional_filesystem_reads': 0, 'additional_explicit_heap_allocations': 0,
    'logging_crt_allocations_and_overhead_measured': False,
    'native_observer_activation_integrated': False,
    'native_activation_required': 'isolated_textparser_translation_unit_SERVER_definition_and_actual_rows',
    'phases': ['schema_and_open', 'dependency_table_read', 'top_level_membership_scan',
               'dependency_dates', 'optional_prefix_presence_and_membership', 'cleanup_and_seek'],
    'diagnostic_input_token_is_integrity_proof': False,
    'clock_failure_or_regression': 'clock_valid=0_and_all_phase_times_zero',
    'production_mode_behavior_changed': False, 'freshness_bypass_enabled': False,
    'effective_provider_generation_created': False, 'per_bin_certificate_created': False,
    'decoder_byte_retained': True, 'decode_or_text_fallback_timing_observed': False,
    'native_windows_wine_qualified': False, 'physical_device_qualified': False,
    'startup_savings_measured': False,
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bytes_lf(path):
    return Path(path).read_bytes().replace(b'\r\n', b'\n')


def patch_function(original):
    """Insert observations only; every original statement is retained in order."""
    replacements = (
        ('    // open the bin file\n',
         '    COH_MAP_BIN_DECLARE();\n    COH_MAP_BIN_BEGIN(persistfile, dir, filemask);\n\n    // open the bin file\n'),
        ('        return 0; // don\'t have bin file or crc wrong\n',
         '        COH_MAP_BIN_FINISH("open_rejected");\n        return 0; // don\'t have bin file or crc wrong\n'),
        ('    if(isProductionMode())\n        return binfile;\n',
         '    if(isProductionMode()) {\n        COH_MAP_BIN_FINISH("production_assumed");\n        return binfile;\n    }\n'
         '    COH_MAP_BIN_PHASE(1);\n'),
        ('    // assemble file list from directories\n',
         '    COH_MAP_BIN_PHASE(2);\n\n    // assemble file list from directories\n'),
        ('    // compare lists -\n', '    COH_MAP_BIN_PHASE(3);\n\n    // compare lists -\n'),
        ('    // check that top-level files are in or not in bin file appropriately\n',
         '    COH_MAP_BIN_PHASE(4);\n\n    // check that top-level files are in or not in bin file appropriately\n'),
        ('    // ok then..\n', '    COH_MAP_BIN_PHASE(5);\n\n    // ok then..\n'),
        ('    SimpleBufSeek(binfile, savedpos, SEEK_SET);\n    return binfile;\n',
         '    SimpleBufSeek(binfile, savedpos, SEEK_SET);\n    COH_MAP_BIN_FINISH("freshness_accepted");\n    return binfile;\n'),
        ('IsPersist_Fail:\n', 'IsPersist_Fail:\n    COH_MAP_BIN_PHASE(5);\n'),
        ('    SerializeClose(binfile);\n    return 0;\n',
         '    SerializeClose(binfile);\n    COH_MAP_BIN_FINISH("freshness_rejected");\n    return 0;\n'),
    )
    text = original
    for old, new in replacements:
        namespace.require(text.count(old) == 1, 'BIN observer stock function anchor differs: ' + old[:72])
        text = text.replace(old, new, 1)
    return text


def patch_source(original):
    text = original.decode('utf-8')
    function = namespace.function(text, SIGNATURE)
    text = text.replace(function, patch_function(function), 1)
    anchor = '#include "utilitieslib/utils/textparser.h"\n'
    namespace.require(text.count(anchor) == 1, 'BIN observer include anchor differs')
    return text.replace(anchor, anchor + '#include "coh_map_bin_observer.h"\n', 1).encode('utf-8')


def expected_receipt(root=ROOT):
    root = Path(root)
    stock = bytes_lf(root / 'upstream/ouroboros' / SOURCE)
    overlay = bytes_lf(root / OVERLAY)
    decoder = namespace.function(stock.decode(), 'int ParserReadBinaryFile(')
    patched = patch_source(stock)
    namespace.require(namespace.function(patched.decode(), 'int ParserReadBinaryFile(') == decoder,
                      'BIN observer unexpectedly changed stock decoder')
    return {'schema_version': 1, 'build_role': CONTRACT['role'],
            'source_sha256': {SOURCE: digest(stock)},
            'patched_sha256': {SOURCE: digest(patched)},
            'overlay_sha256': {TARGET: digest(overlay)},
            'retained_sources_sha256': {name: digest(bytes_lf(root / 'upstream/ouroboros' / name))
                                       for name in RETAINED},
            'retained_decoder_sha256': digest(decoder.encode()),
            'contract': CONTRACT, 'runtime_validation': 'unverified',
            'publication_allowed': False}


def safe_staging_file(source, name):
    path = source / name
    namespace.require(not any(parent.is_symlink() for parent in (path, *path.parents)),
                      'BIN observer linked staging path refused: ' + name)
    return path


def apply_observer_overlay(source, root=ROOT):
    root = Path(root).resolve()
    original_source = Path(source).absolute()
    namespace.require(not any(parent.is_symlink() for parent in (original_source, *original_source.parents)),
                      'BIN observer linked staging root refused')
    source = original_source.resolve()
    namespace.require(source != root and root / 'upstream' not in (source, *source.parents)
                      and root != source and source not in root.parents,
                      'BIN observer immutable or repository ancestor staging refused')
    receipt = safe_staging_file(source, RECEIPT)
    target = safe_staging_file(source, TARGET)
    namespace.require(not receipt.exists() and not target.exists(), 'BIN observer already staged')
    expected = expected_receipt(root)
    for name, pin in {**expected['source_sha256'], **expected['retained_sources_sha256']}.items():
        path = safe_staging_file(source, name)
        namespace.require(path.is_file() and digest(path.read_bytes()) == pin,
                          'BIN observer exact staging source differs: ' + name)
    patched = patch_source((source / SOURCE).read_bytes())
    namespace.require(digest(patched) == expected['patched_sha256'][SOURCE], 'BIN observer patched bytes differ')
    target.write_bytes(bytes_lf(root / OVERLAY))
    (source / SOURCE).write_bytes(patched)
    receipt.write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-staging', type=Path, required=True,
                        help='Existing isolated source tree; never immutable upstream or repository root')
    args = parser.parse_args()
    value = apply_observer_overlay(args.source_staging)
    print(json.dumps({'status': 'nonshipping_observer_staged',
                      'publication_allowed': value['publication_allowed'],
                      'physical_device_qualified': False}))


if __name__ == '__main__': main()
