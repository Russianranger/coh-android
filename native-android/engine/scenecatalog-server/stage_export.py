#!/usr/bin/env python3
"""Opt-in NONSHIPPING MapServer source overlay; never deploys or runs a server."""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
GROUP = 'MapServer/src/group/groupnetsend.c'
INIT = 'MapServer/src/svr/svr_init.c'
EXPORT = 'MapServer/src/group/coh_source_catalog_export.inc'
SINK = 'MapServer/src/group/coh_source_catalog_sink.inc'
PRIOR = 'map-startup-build-input.json'
RECEIPT = 'native-scene-catalog-server-build-input.json'
ROLE = 'nonshipping_startup_native_scene_catalog_export'
GROUP_LF_SHA256 = 'cd739e2a1b424bf089017be73d3c42adef0f23aca7563e8577cfc98ecdfebff9'
NORMAL = (b'        groupLoadMap(db_state.map_name,0,!server_state.beaconProcessOnLoad);\n'
          b'        dbSetupMap();\n        dbReadyForPlayers();\n')
NORMAL_PROGRESS = (
    b'        groupLoadMap(db_state.map_name,0,!server_state.beaconProcessOnLoad);\n'
    b'        cohMapProgressMark(COH_MAP_STAGE_DB_SETUP);\n'
    b'        dbSetupMap();\n'
    b'        cohMapProgressMark(COH_MAP_STAGE_READY_PUBLISH);\n'
    b'        dbReadyForPlayers();\n')
HOOK = b'        coh_source_catalog_export_startup();\n'
PROTOTYPE = b'void coh_source_catalog_export_startup(void);\n'
TAIL = (b'\n/* NONSHIPPING: explicit private startup catalog output only. */\n'
        b'#include "coh_source_catalog_export.inc"\n'
        b'#include "coh_source_catalog_sink.inc"\n')
CONTRACT = {
    'nonshipping': True, 'shipping_executable': False,
    'disabled_without_explicit_output_and_nonzero_u32_generation': True,
    'output_environment': 'COH_NATIVE_SCENE_CATALOG_OUTPUT',
    'generation_environment': 'COH_NATIVE_SCENE_CATALOG_GENERATION',
    'owner_hook': 'normal_map_startup_after_groupLoadMap_dbSetupMap_before_dbReadyForPlayers',
    'same_translation_unit_after_unchanged_groupnetsend': True,
    'private_exclusively_owned_parent_required': True,
    'stable_exclusive_group_and_property_serialization_required': True,
    'create_new_partial_flush_close_rename_without_replace': True,
    'maximum_output_bytes': 32 * 1024 * 1024,
    'hard_process_heap_cap_established': False,
    'process_exit_or_server_state_change': False,
    'network_session_or_persistence_hook': False,
    'runtime_executed': False, 'android_executed': False,
    'deployed': False, 'apk_changed': False,
}


def require(value, code):
    if not value:
        raise ValueError('COH_SCENE_CATALOG_STAGE_' + str(code))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def json_equal(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(json_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    return left == right


def safe_path(path, code=1):
    path = Path(os.path.abspath(path))
    require(not any(p.is_symlink() for p in (path, *path.parents)), code)
    return path


def regular(path, code=2):
    path = safe_path(path, code)
    require(path.is_file() and path.stat().st_nlink == 1, code)
    return path


def lf(raw):
    value = raw.replace(b'\r\n', b'\n')
    require(b'\r' not in value, 3)
    return value


def restore_newlines(raw, original):
    # Keep inherited startup bytes intact, including a uniform Windows checkout.
    if b'\r\n' in original:
        require(original.count(b'\r\n') == original.count(b'\n'), 4)
        return raw.replace(b'\n', b'\r\n')
    return raw


def read_json(path):
    with regular(path, 5).open('rb') as source:
        raw = source.read(8 * 1024 * 1024 + 1)
    require(len(raw) <= 8 * 1024 * 1024, 6)
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 7)
            out[key] = value
        return out
    def finite(value):
        parsed = float(value)
        require(math.isfinite(parsed), 8)
        return parsed
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda _: require(False, 8), parse_float=finite)
    except (UnicodeError, ValueError, RecursionError):
        require(False, 8)
    require(type(value) is dict, 9)
    return value


def expected_prior(root, prior):
    # Reconstruct the exact trusted existing prerequisite rather than accepting
    # a self-described role or a caller-generated hash inventory.
    sys.path.insert(0, str(Path(root) / 'tools'))
    try:
        startup = importlib.import_module('prepare_map_startup_source')
        return startup.expected_receipt(prior['animation_certificate'], root,
                                        prior['monorail_build_input'])
    except (KeyError, TypeError, ValueError, OSError, AssertionError,
            ImportError, subprocess.SubprocessError, RuntimeError):
        require(False, 10)
    finally:
        sys.path.pop(0)


def inherited_hashes(prior):
    result = {}
    def visit(node):
        if type(node) is not dict:
            return
        for value in node.values():
            if type(value) is dict:
                visit(value)
        for field in ('retained_sources_sha256', 'retained_collision_sources',
                      'overlay_sha256', 'patched_sha256'):
            values = node.get(field, {})
            require(type(values) is dict, 11)
            for name, digest in values.items():
                require(type(name) is str and not Path(name).is_absolute() and
                        '\\' not in name and '..' not in Path(name).parts and
                        type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest), 12)
                result[name] = digest
    visit(prior)
    return result


def validate_prior(root, stage):
    prior = read_json(Path(stage) / PRIOR)
    require(type(prior.get('schema_version')) is int and prior['schema_version'] == 1 and
            prior.get('build_role') == 'map_startup_certified_animation' and
            prior.get('build_targets') == ['MapServer'], 13)
    require(json_equal(prior, expected_prior(root, prior)), 14)
    for name, digest in inherited_hashes(prior).items():
        require(sha(regular(Path(stage) / name, 15).read_bytes()) == digest, 16)
    return prior


def overlay_bytes(root):
    producer = regular(Path(root) / 'native-android/engine/scenecatalog/source_export.inc', 17)
    sink = regular(HERE / 'source_sink.inc', 18)
    return {EXPORT: lf(producer.read_bytes()), SINK: lf(sink.read_bytes())}


def transform(group, init):
    require(sha(lf(group)) == GROUP_LF_SHA256, 19)
    text = lf(init)
    anchor = b'#include <conio.h>\n'
    normal = [value for value in (NORMAL, NORMAL_PROGRESS) if text.count(value) == 1]
    require(text.count(anchor) == 1 and len(normal) == 1 and
            sum(text.count(value) for value in (NORMAL, NORMAL_PROGRESS)) == 1 and
            b'coh_source_catalog_export_startup' not in text, 20)
    patched = text.replace(anchor, anchor + PROTOTYPE, 1)
    patched = patched.replace(normal[0], normal[0].replace(b'        dbSetupMap();\n',
                                                         b'        dbSetupMap();\n' + HOOK), 1)
    return {GROUP: group + restore_newlines(TAIL, group),
            INIT: restore_newlines(patched, init)}


def transformed_sources(root, init_bytes=None):
    root = safe_path(root)
    group = regular(root / 'upstream/ouroboros' / GROUP, 21).read_bytes()
    init = (regular(root / 'upstream/ouroboros' / INIT, 22).read_bytes()
            if init_bytes is None else init_bytes)
    original = {GROUP: group, INIT: init}
    return original, transform(group, init)


def expected_receipt(prior, original, output, overlays):
    return {
        'schema_version': 1, 'build_role': ROLE, 'build_targets': ['MapServer'],
        'prior_build_input': prior, 'prior_build_input_canonical_sha256': canonical(prior),
        'original_groupnetsend_lf_sha256': GROUP_LF_SHA256,
        'source_sha256': {n: sha(b) for n, b in original.items()},
        'patched_sha256': {n: sha(b) for n, b in output.items()},
        'overlay_sha256': {n: sha(b) for n, b in overlays.items()},
        'stager_sha256': sha(Path(__file__).read_bytes()),
        'contract': CONTRACT, 'runtime_validation': 'not_executed_compile_only',
    }


def private_stage(root, stage):
    root, stage = safe_path(root, 23), safe_path(stage, 24)
    require(root.is_dir() and stage.is_dir() and stage != root and
            root / 'upstream' not in (stage, *stage.parents) and
            stage not in root.parents, 25)
    for name in (GROUP, INIT):
        target = regular(stage / name, 26)
        original = regular(root / 'upstream/ouroboros' / name, 27)
        require(not os.path.samefile(target, original), 28)
    require(sha(lf((root / 'upstream/ouroboros' / GROUP).read_bytes())) == GROUP_LF_SHA256, 32)
    return root, stage


def prepare(source_root, already_staged):
    root, stage = private_stage(source_root, already_staged)
    receipt_path = stage / RECEIPT
    require(not receipt_path.exists() and not receipt_path.is_symlink(), 29)
    prior = validate_prior(root, stage)
    overlays = overlay_bytes(root)
    require(set(overlays) == {EXPORT, SINK}, 30)
    originals = {n: regular(stage / n, 31).read_bytes() for n in (GROUP, INIT)}
    require(sha(lf(regular(root / 'upstream/ouroboros' / GROUP).read_bytes())) == GROUP_LF_SHA256, 32)
    outputs = transform(originals[GROUP], originals[INIT])
    for name in overlays:
        target = safe_path(stage / name, 33)
        require(target.parent.is_dir() and not target.exists() and not target.is_symlink(), 34)
    receipt = expected_receipt(prior, originals, outputs, overlays)
    created, changed = [], []
    try:
        for name, raw in overlays.items():
            with (stage / name).open('xb') as target:
                created.append(stage / name)
                target.write(raw)
        for name, raw in outputs.items():
            changed.append(name)
            (stage / name).write_bytes(raw)
        with receipt_path.open('x', encoding='utf-8', newline='\n') as target:
            created.append(receipt_path)
            json.dump(receipt, target, indent=2, allow_nan=False)
            target.write('\n')
    except OSError:
        for name in changed:
            (stage / name).write_bytes(originals[name])
        for target in reversed(created):
            target.unlink()
        require(False, 35)
    return receipt


def verify_staged(source_root, staged_root):
    root, stage = private_stage(source_root, staged_root)
    actual = read_json(stage / RECEIPT)
    require(actual.get('build_role') == ROLE, 36)
    prior = read_json(stage / PRIOR)
    require(type(prior.get('schema_version')) is int and prior['schema_version'] == 1 and
            prior.get('build_role') == 'map_startup_certified_animation' and
            prior.get('build_targets') == ['MapServer'] and
            json_equal(prior, expected_prior(root, prior)), 37)
    group, init = (regular(stage / n).read_bytes() for n in (GROUP, INIT))
    tail = restore_newlines(TAIL, group[:group.find(b'/* NONSHIPPING:')]
                            if b'/* NONSHIPPING:' in group else group)
    require(group.endswith(tail), 38)
    original_group = group[:-len(tail)]
    init_lf = lf(init)
    require(init_lf.count(HOOK) == 1 and init_lf.count(PROTOTYPE) == 1, 39)
    original_init = restore_newlines(init_lf.replace(HOOK, b'', 1).replace(PROTOTYPE, b'', 1), init)
    original = {GROUP: original_group, INIT: original_init}
    output = transform(original_group, original_init)
    overlays = overlay_bytes(root)
    expected = expected_receipt(prior, original, output, overlays)
    require(json_equal(actual, expected) and output == {GROUP: group, INIT: init}, 40)
    for name, digest in inherited_hashes(prior).items():
        data = original[name] if name in original else regular(stage / name).read_bytes()
        require(sha(data) == digest, 41)
    require(all(regular(stage / n).read_bytes() == raw for n, raw in overlays.items()), 42)
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--already-staged', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    try:
        receipt = (verify_staged if args.verify else prepare)(args.source_root, args.already_staged)
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        print(json.dumps({'schema': 1, 'status': 1, 'staged': False}))
        return 2
    print(json.dumps({'schema': 1, 'status': 0, 'staged': True,
                      'receipt': RECEIPT, 'build_role': receipt['build_role'],
                      'nonshipping': True, 'runtime_executed': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
