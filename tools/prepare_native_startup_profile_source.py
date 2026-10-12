#!/usr/bin/env python3
"""Stage a bounded, active native startup profiler after the .32 MapServer overlay.

This isolated diagnostic source does not authorize shipping, change freshness,
or certify a reusable BIN. UtilitiesLib's parser observer is activated locally
in its own translation unit; MapServer's private SERVER define is insufficient.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import map_startup_namespace_certificate as namespace
import prepare_map_startup_observer_source as freshness

ROOT = Path(__file__).resolve().parents[1]
PARSER = freshness.SOURCE
SEQUENCER = 'Common/seq/seqload.c'
HEADER = 'coh_native_startup_profile.h'
OVERLAY = 'database/native-startup-profile/overlay/' + HEADER
RECEIPT = 'native-startup-profile-build-input.json'


def replace(text, old, new):
    namespace.require(text.count(old) == 1, 'Startup profiler source anchor differs: ' + old[:90])
    return text.replace(old, new, 1)


def parser_source(original):
    text = freshness.patch_source(original).decode()
    # Source-local activation changes only this isolated parser translation unit.
    text = replace(text, '#include "coh_map_bin_observer.h"\n', '')
    # Keep the project's Winsock/wininclude order before the observer Windows API.
    text = replace(text, '#undef ParserAllocStruct\n',
                   '#define COH_NATIVE_STARTUP_PROFILE 1\n'
                   '#include "coh_map_bin_observer.h"\n#include "' + HEADER + '"\n\n'
                   '#undef ParserAllocStruct\n')
    signature = 'int ParserReadBinaryFile('
    body = namespace.function(text, signature)
    observed = replace(body, '    long loc, endloc;\n',
                       '    long loc, endloc;\n    COH_NATIVE_PROFILE_DECLARE(decode);\n'
                       '    COH_NATIVE_PROFILE_BEGIN(decode, "bin_decode", filename);\n')
    observed = replace(observed, '    if (!file) return 0;  // no file, or failed crc number\n',
                       '    if (!file) { COH_NATIVE_PROFILE_END(decode, 0); return 0; }  // no file, or failed crc number\n')
    observed = replace(observed, '        return 0; // couldn\'t read file table\n',
                       '        COH_NATIVE_PROFILE_END(decode, 0);\n        return 0; // couldn\'t read file table\n')
    observed = replace(observed, '    return success;\n',
                       '    COH_NATIVE_PROFILE_END(decode, success);\n    return success;\n')
    return replace(text, body, observed).encode()


def sequencer_source(original):
    text = original.decode()
    # The .32 source compilation already supplies SERVER on this MapServer TU.
    anchor = '#include <utilitieslib/components/SharedHeap.h>\n'
    text = replace(text, anchor, anchor + '#ifdef SERVER\n#define COH_NATIVE_STARTUP_PROFILE 1\n#endif\n'
                   '#include "' + HEADER + '"\n')
    signature = 'static bool seqPreloadSeqInfoPostProcessor('
    body = namespace.function(text, signature)
    observed = replace(body, '    int num_structs, i;\n',
                       '    int num_structs, i;\n    COH_NATIVE_PROFILE_DECLARE(post);\n'
                       '    COH_NATIVE_PROFILE_BEGIN(post, "sequencer_postprocess", "sequencers.bin");\n')
    observed = replace(observed, '    return true;\n',
                       '    COH_NATIVE_PROFILE_END(post, 1);\n    return true;\n')
    text = replace(text, body, observed)
    signature = 'static bool seqPreloadSeqInfoFinalProcessor('
    body = namespace.function(text, signature)
    observed = replace(body, '    int num_structs, i;\n',
                       '    int num_structs, i;\n    COH_NATIVE_PROFILE_DECLARE(final);\n'
                       '    COH_NATIVE_PROFILE_BEGIN(final, "sequencer_finalize", "sequencers.bin");\n')
    observed = replace(observed, '    return true;\n',
                       '    COH_NATIVE_PROFILE_END(final, 1);\n    return true;\n')
    text = replace(text, body, observed)
    signature = 'void seqPreloadSeqInfos('
    body = namespace.function(text, signature)
    observed = replace(body, 'void seqPreloadSeqInfos()\n{\n',
                       'void seqPreloadSeqInfos()\n{\n    COH_NATIVE_PROFILE_DECLARE(total);\n'
                       '    COH_NATIVE_PROFILE_BEGIN(total, "sequencer_total", "sequencers.bin");\n')
    observed = observed[:-1] + '    COH_NATIVE_PROFILE_END(total, 1);\n}'
    return replace(text, body, observed).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_bytes(name, root=ROOT):
    return (Path(root) / 'upstream/ouroboros' / name).read_bytes().replace(b'\r\n', b'\n')


def expected_receipt(root=ROOT):
    originals = {name: source_bytes(name, root) for name in (PARSER, SEQUENCER)}
    header = (Path(root) / OVERLAY).read_bytes()
    old_header = (Path(root) / freshness.OVERLAY).read_bytes()
    activated = old_header.replace(b'#ifdef SERVER\n', b'#ifdef COH_NATIVE_STARTUP_PROFILE\n', 1)
    namespace.require(activated != old_header, 'Freshness profiler activation anchor differs')
    return {'format': 1, 'role': 'isolated_native_startup_profile', 'publication_allowed': False,
        'source_sha256': {name: digest(data) for name, data in originals.items()},
        'patched_sha256': {PARSER: digest(parser_source(originals[PARSER])),
                           SEQUENCER: digest(sequencer_source(originals[SEQUENCER]))},
        'header_sha256': digest(header), 'activated_freshness_header_sha256': digest(activated),
        'parser_activation': 'source_local_COH_NATIVE_STARTUP_PROFILE_not_inherited_SERVER',
        'phases': ['bin_freshness_six_subphases', 'bin_decode', 'sequencer_postprocess',
                   'sequencer_finalize', 'sequencer_total'],
        'decode_scope': 'file_dependency_table_plus_unchanged_binary_decoder_and_close',
        'postprocess_scope': 'move_validation_and_full_animation_attachment_including_base_skeletons',
        'clock': 'QueryPerformanceCounter_wall_time_not_CPU_time',
        'maximum_profile_rows_per_translation_unit': 256,
        'maximum_freshness_rows': 256,
        'native_windows_executed': False, 'native_wine_executed': False,
        'physical_device_executed': False, 'provider_authority_created': False,
        'freshness_bypass_enabled': False, 'animation_payload_or_validation_changed': False,
        'persistent_cache_payload_added': False}


def stage(source, root=ROOT):
    source = Path(source).absolute()
    root = Path(root).resolve()
    namespace.require(not any(p.is_symlink() for p in (source, *source.parents)), 'Linked startup profile staging refused')
    source = source.resolve()
    namespace.require(source != root and source not in root.parents and root / 'upstream' not in (source, *source.parents),
                      'Repository or immutable upstream startup profiling refused')
    namespace.require((source / 'map-startup-build-input.json').is_file(),
                      'Apply the retained animation/monorail startup source overlay first')
    receipt = expected_receipt(root)
    writes = {PARSER: parser_source(source_bytes(PARSER, root)), SEQUENCER: sequencer_source(source_bytes(SEQUENCER, root))}
    header = (root / OVERLAY).read_bytes()
    writes.update({str(Path(PARSER).parent / HEADER): header, str(Path(SEQUENCER).parent / HEADER): header,
                   freshness.TARGET: (root / freshness.OVERLAY).read_bytes().replace(
                       b'#ifdef SERVER\n', b'#ifdef COH_NATIVE_STARTUP_PROFILE\n', 1)})
    # Check all sources and outputs before the first write.
    for name, pin in receipt['source_sha256'].items():
        path = freshness.safe_staging_file(source, name)
        namespace.require(path.is_file() and digest(path.read_bytes()) == pin, 'Startup profiler exact source differs: ' + name)
    for name in (*writes, RECEIPT):
        path = freshness.safe_staging_file(source, name)
        if name not in receipt['source_sha256']:
            namespace.require(not path.exists(), 'Startup profiler output already exists: ' + name)
    for name, data in writes.items():
        (source / name).write_bytes(data)
    (source / RECEIPT).write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-staging', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.source_staging)))


if __name__ == '__main__':
    main()
