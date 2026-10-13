#!/usr/bin/env python3
"""Append Cg source/object and driver-load timing to an isolated retained Game.

This diagnostic cannot change shader cache acceptance, program inputs, returned
handles, compile flags or driver calls. It is never a shipping qualification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import map_startup_namespace_certificate as namespace
import prepare_map_startup_observer_source as safe
from prepare_native_startup_profile_source import replace

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'Game/src/render/thread/rt_cgfx.c'
HEADER = 'coh_native_cg_profile.h'
OVERLAY = 'database/native-startup-profile/overlay/' + HEADER
TARGET = str(Path(SOURCE).parent / HEADER)
RECEIPT = 'native-cg-profile-build-input.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_bytes(root=ROOT):
    return (Path(root)/'upstream/ouroboros'/SOURCE).read_bytes().replace(b'\r\n', b'\n')


def patch_source(original):
    text = original.decode('latin-1')
    text = replace(text, '#include "graphics/failtext.h"\n',
                   '#include "graphics/failtext.h"\n#include "' + HEADER + '"\n')
    before = namespace.function(text, 'CGprogram rt_cgCreateProgramFromBuffer(')
    after = replace(before, '    CGprogram pgmHandle = NULL;\n',
                    '    CGprogram pgmHandle = NULL;\n    CohNativeCgProfile profile_observation;\n')
    after = replace(after, '    pgmHandle = cgCreateProgram(',
                    '    cohCgBegin(&profile_observation, program_type == CG_SOURCE ? 1u : program_type == CG_OBJECT ? 2u : 0u, szProgramName);\n'
                    '    pgmHandle = cgCreateProgram(')
    after = replace(after, '    nError = ReviewShaderCompileResults( szProgramName, pgmHandle );\n',
                    '    cohCgElapsed(&profile_observation, &profile_observation.create_us);\n'
                    '    nError = ReviewShaderCompileResults( szProgramName, pgmHandle );\n')
    after = replace(after, '            cgGLLoadProgram( pgmHandle );\n',
                    '            cohCgLoadBegin(&profile_observation);\n'
                    '            cgGLLoadProgram( pgmHandle );\n'
                    '            cohCgElapsed(&profile_observation, &profile_observation.load_us);\n')
    after = replace(after, '    return pgmHandle;\n',
                    '    cohCgEnd(&profile_observation, pgmHandle != NULL);\n    return pgmHandle;\n')
    return replace(text, before, after).encode('latin-1')


def expected_receipt(root=ROOT):
    original = source_bytes(root)
    return {'format': 1, 'role': 'isolated_native_cg_startup_profile', 'publication_allowed': False,
        'source_sha256': {SOURCE: digest(original)},
        'patched_sha256': {SOURCE: digest(patch_source(original))},
        'overlay_sha256': {TARGET: digest((Path(root)/OVERLAY).read_bytes())},
        'row_prefix': 'COH_NATIVE_CG_PROFILE_V1', 'maximum_rows': 1024,
        'kind': {'1': 'CG_SOURCE', '2': 'CG_OBJECT', '0': 'other'},
        'clock': 'QueryPerformanceCounter_wall_time_not_CPU_time',
        'create_scope': 'cgCreateProgram_only', 'driver_scope': 'cgGLLoadProgram_only',
        'object_does_not_prove_gpu_driver_cache_hit': True,
        'cache_acceptance_changed': False, 'graphics_profile_changed': False,
        'native_windows_executed': False, 'native_game_executed': False, 'physical_device_executed': False}


def stage(source, root=ROOT):
    source, root = Path(source).absolute(), Path(root).resolve()
    namespace.require(not any(p.is_symlink() for p in (source, *source.parents)), 'Linked Cg staging refused')
    source = source.resolve()
    namespace.require(source != root and source not in root.parents and root/'upstream' not in (source, *source.parents),
                      'Repository or immutable upstream Cg profiling refused')
    sys.path.insert(0, str(root/'tools/android/interactive'))
    import package_client_render_queue_native as retained
    retained.validate_source(source)
    receipt = expected_receipt(root)
    original = safe.safe_staging_file(source, SOURCE)
    namespace.require(original.is_file() and digest(original.read_bytes()) == receipt['source_sha256'][SOURCE],
                      'Cg exact retained source differs')
    for name in (TARGET, RECEIPT):
        namespace.require(not safe.safe_staging_file(source, name).exists(), 'Cg profile output already exists')
    original.write_bytes(patch_source(original.read_bytes()))
    (source/TARGET).write_bytes((root/OVERLAY).read_bytes())
    (source/RECEIPT).write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-staging', type=Path, required=True)
    print(json.dumps(stage(parser.parse_args().source_staging)))
