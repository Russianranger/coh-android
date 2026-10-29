#!/usr/bin/env python3
"""Apply native patch 0119 to either retained Win32 MapServer source lineage.

This is a selective server producer, not the client's full ArmPort patch series.
The existing progress or certified-animation producer runs first. Its receipts
remain byte-for-byte intact; a separate receipt binds exact inputs and outputs.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = 'server-metrics-build-input.json'
PATCH = 'armport/patches/0119-armport-server-tick-file-metrics.patch'
SVR = 'MapServer/src/svr/svr_init.c'
FILE = 'libs/UtilitiesLib/src/utils/file.c'
HEADER = 'libs/UtilitiesLib/include/utilitieslib/utils/armport_server_metrics.h'
IMPL = 'libs/UtilitiesLib/src/utils/armport_server_metrics_impl.h'
FILES = (SVR, FILE, HEADER, IMPL)
VARIANTS = {'retained_progress': 'mapserver-progress-build-input.json',
            'thor_certified_startup': 'map-startup-build-input.json'}
CONTRACT = {
    'environment_variable': 'ARMPORT_SERVER_METRICS', 'enabled_value': '1',
    'disabled_by_default': True, 'record_prefix': 'ARMPORT_SERVER_METRICS_V1',
    'window_seconds': 5, 'emit_at': 'first_completed_loop_at_or_after_window',
    'identity': ['map_id', 'pid'], 'clock': 'QueryPerformanceCounter',
    'scope': 'post_ready_main_thread_outer_filealloc',
    'max_tick_ms': 'main_loop_work_before_sleep',
    'max_loop_ms': 'main_loop_work_plus_sleep_excluding_metrics_output',
    'filealloc_ms': 'inclusive_outer_fileAlloc_or_fileAllocEx_wall_time_in_work',
    'filealloc_calls': 'outer_attempts_including_failures',
    'excluded': ['startup', 'background_threads', 'direct_fread', 'other_file_apis'],
    'disk_only_measurement': False, 'wineserver_request_counts': False,
    'clock_failure': 'disable_metrics_only_with_status_record',
    'gameplay_decisions_changed': False,
}
CHILD_RECEIPTS = {
    'postgresql_build_input': 'postgresql-build-input.json',
    'game_build_input': 'game-loopback-build-input.json',
    'progress_build_input': 'mapserver-progress-build-input.json',
    'events_build_input': 'character-events-build-input.json',
    'monorail_build_input': 'monorail-build-input.json',
    'monorail_budget': 'map-startup-monorail-budget.json',
}
FINAL_HASH_MAPS = ('patched_sha256', 'overlay_sha256', 'progress_overlay_sha256',
                   'events_overlay_sha256', 'retained_collision_sources',
                   'retained_sources_sha256')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def modules(upstream_root):
    root = Path(upstream_root).resolve()
    sys.path.insert(0, str(root / 'tools'))
    progress = importlib.import_module('prepare_mapserver_progress_source')
    startup = importlib.import_module('prepare_map_startup_source')
    return progress, startup


def patch_bytes():
    data = (ROOT / PATCH).read_bytes().replace(b'\r\n', b'\n')
    names = [line[6:] for line in data.decode().splitlines() if line.startswith('+++ b/')]
    require(len(names) == 4 and set(names) == set(FILES), 'Native metric patch file set differs')
    return data


def patch_loop(data):
    """Rebase only 0119's four guarded insertions over existing progress hooks."""
    pre_tick = b'        cohMapProgressMark(COH_MAP_STAGE_LOOP_PRE_TICK);\n'
    sleep_done = b'        cohMapProgressMark(COH_MAP_STAGE_SLEEP_DONE);\n'
    has_progress = pre_tick in data or sleep_done in data
    require(not has_progress or (data.count(pre_tick) == 1 and data.count(sleep_done) == 1),
            'Incomplete retained progress loop markers')
    begin = pre_tick if has_progress else b'        timerTickBegin();\n'
    replacements = (
        (b'#include <utilitieslib/utils/file.h>\n',
         b'#include <utilitieslib/utils/file.h>\n#include <utilitieslib/utils/armport_server_metrics.h>\n'),
        (b'    if (coll_test)\n        gridCollPerfTest();\n\n',
         b'    if (coll_test)\n        gridCollPerfTest();\n\n    armportServerMetricsInit(db_state.map_id);\n'),
        (begin, b'        armportServerMetricsTickBegin();\n' + begin),
        (b'        sleepAndCalcTimers();\n',
         b'        armportServerMetricsTickEnd();\n        sleepAndCalcTimers();\n'
         + (b'' if has_progress else b'        armportServerMetricsLoopEnd();\n')),
    )
    if has_progress:
        replacements += ((sleep_done, sleep_done + b'        armportServerMetricsLoopEnd();\n'),)
    for old, new in replacements:
        require(data.count(old) == 1, 'Native metric loop anchor differs')
        data = data.replace(old, new, 1)
    return data


def baseline_closure(receipt, name):
    """Resolve final file identities child-first; parent overlays supersede them."""
    hashes, receipts = {}, {}
    for key, filename in CHILD_RECEIPTS.items():
        if key in receipt:
            child_hashes, child_receipts = baseline_closure(receipt[key], filename)
            hashes.update(child_hashes)
            receipts.update(child_receipts)
    for key in FINAL_HASH_MAPS:
        hashes.update(receipt.get(key, {}))
    receipts[name] = receipt
    return hashes, receipts


def expected_baseline(variant, baseline_receipt, root):
    require(variant in VARIANTS, 'Unknown server metrics source variant')
    require(isinstance(baseline_receipt, dict), 'Missing baseline source receipt')
    progress, startup = modules(root)
    if variant == 'retained_progress':
        expected = progress.expected_progress_receipt(root, baseline_receipt.get('game_build_input'))
    else:
        expected = startup.expected_receipt(baseline_receipt.get('animation_certificate'), root,
                                            baseline_receipt.get('monorail_build_input'))
    require(canonical(baseline_receipt) == canonical(expected), 'Baseline source receipt differs')
    return expected


def native_images(variant, baseline_receipt, root):
    """Reproduce 0119 from immutable input, then check its exact loop rebase."""
    progress, startup = modules(root)
    apply_patch = progress.apply_patch
    with tempfile.TemporaryDirectory(prefix='coh-server-metrics-receipt-') as directory:
        stage = Path(directory)
        for name in (SVR, FILE):
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / 'upstream/ouroboros' / name).read_bytes())
        original_loop = (stage / SVR).read_bytes()
        apply_patch(stage, patch_bytes())
        images = {name: (stage / name).read_bytes() for name in FILES}
        require(images[SVR] == patch_loop(original_loop), 'Loop rebase differs from exported native patch')
    with tempfile.TemporaryDirectory(prefix='coh-server-metrics-base-') as directory:
        stage = Path(directory)
        patches = [progress.game.patch_bytes(root), progress.patch_bytes(root)]
        if variant == 'thor_certified_startup':
            patches += [startup.monorail.events.patch_bytes(root), startup.monorail.patch_bytes(root)]
        names = {line[6:] for patch in patches for line in patch.decode().splitlines()
                 if line.startswith('+++ b/')}
        for name in names:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / 'upstream/ouroboros' / name, target)
        for patch in patches:
            apply_patch(stage, patch)
        inputs = {SVR: (stage / SVR).read_bytes(),
                  FILE: (root / 'upstream/ouroboros' / FILE).read_bytes()}
    images[SVR] = patch_loop(inputs[SVR])
    closure, _ = baseline_closure(baseline_receipt, VARIANTS[variant])
    require(closure[SVR] == digest(inputs[SVR]), 'Baseline loop preimage differs')
    require(FILE not in closure or closure[FILE] == digest(inputs[FILE]), 'Baseline file loader preimage differs')
    return inputs, images


def expected_receipt(variant, baseline_receipt, upstream_root=ROOT):
    root = Path(upstream_root).resolve()
    base = expected_baseline(variant, baseline_receipt, root)
    inputs, images = native_images(variant, base, root)
    closure, receipts = baseline_closure(base, VARIANTS[variant])
    return {'format': 1, 'role': 'armport_server_metrics', 'variant': variant,
            'source_commit': base['source_commit'], 'baseline_receipt_name': VARIANTS[variant],
            'baseline_receipt': base, 'baseline_receipt_sha256': digest(canonical(base)),
            'baseline_receipts_sha256': {name: digest(canonical(value)) for name, value in receipts.items()},
            'patch': {'path': PATCH, 'sha256': digest(patch_bytes())},
            'source_sha256': {name: digest(data) for name, data in inputs.items()},
            'patched_sha256': {name: digest(data) for name, data in images.items()},
            'retained_sha256': {name: value for name, value in closure.items() if name not in FILES},
            'contract': CONTRACT, 'build_targets': ['MapServer'],
            'native_execution_validated': False}


def validate_receipt(receipt, upstream_root=ROOT):
    require(isinstance(receipt, dict), 'Missing server metrics receipt')
    expected = expected_receipt(receipt.get('variant'), receipt.get('baseline_receipt'), upstream_root)
    require(canonical(receipt) == canonical(expected), 'Server metrics source receipt differs')
    return expected


def validate_test_report(document, source_receipt, upstream_root=ROOT):
    """Validate source-test identity, not authenticity of an arbitrary report.

    CI must run the fixture and retain its logs. These checks bind that evidence
    to exact inputs; they do not claim execution of the shipping Windows PE.
    """
    receipt = validate_receipt(source_receipt, upstream_root)
    require(isinstance(document, dict), 'Missing server metrics test report')
    expected = {'format': 1, 'role': 'armport_server_metrics_source_checks', 'status': 'passed',
                'variant': receipt['variant'], 'build_input_sha256': digest(canonical(receipt)),
                'source_sha256': receipt['patched_sha256'],
                'original_sha256': {name: digest((Path(upstream_root) / 'upstream/ouroboros' / name).read_bytes())
                                    for name in (SVR, FILE)},
                'test_script_sha256': digest((ROOT / 'armport/tests/server_metrics_native.py').read_bytes()),
                'execution_environment': 'posix_host_with_windows_clock_and_file_io_shims',
                'positive_cases': ['window', 'disabled', 'files', 'thread', 'slow', 'clock', 'saturation',
                                   'progress_markers'],
                'unpatched_control_failed': True,
                'unpatched_control_failure': 'runtime_missing_metrics_assertion',
                'shipping_binary_executed': False}
    require(set(document) == set(expected).union(('compiler', 'fixture_sha256')),
            'Server metrics test report keys differ')
    require(canonical({key: document[key] for key in expected}) == canonical(expected),
            'Server metrics test report identity differs')
    require(isinstance(document['compiler'], str) and document['compiler'], 'Missing host compiler identity')
    pins = document['fixture_sha256']
    require(isinstance(pins, dict) and set(pins) == {'positive', 'negative'}
            and all(isinstance(value, str) and len(value) == 64
                    and all(c in '0123456789abcdef' for c in value) for value in pins.values()),
            'Missing host fixture hashes')
    return document


def check_file(source, name, expected):
    path = source / name
    require(path.is_file() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
            'Missing or linked server source: ' + name)
    require(digest(path.read_bytes()) == expected, 'Server source hash differs: ' + name)


def check_baseline_receipts(source, receipt):
    for name, expected in receipt['baseline_receipts_sha256'].items():
        path = source / name
        require(path.is_file() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
                'Missing or linked baseline receipt: ' + name)
        require(digest(canonical(json.loads(path.read_text()))) == expected,
                'Baseline receipt changed: ' + name)
    for name in set(VARIANTS.values()).union(CHILD_RECEIPTS.values()):
        require(name in receipt['baseline_receipts_sha256'] or not (source / name).exists(),
                'Unexpected source lineage receipt: ' + name)


def verify_prepared(source, upstream_root=ROOT):
    source = Path(source).resolve()
    path = source / RECEIPT
    require(path.is_file() and not path.is_symlink(), 'Missing server metrics source receipt')
    receipt = validate_receipt(json.loads(path.read_text()), upstream_root)
    check_baseline_receipts(source, receipt)
    for name, expected in {**receipt['retained_sha256'], **receipt['patched_sha256']}.items():
        check_file(source, name, expected)
    return receipt


def apply_metrics(source, variant, upstream_root=ROOT, required_baseline_receipt=None):
    source, root = Path(source).resolve(), Path(upstream_root).resolve()
    require(source not in (root, ROOT) and root / 'upstream' not in (source, *source.parents)
            and ROOT / 'upstream' not in (source, *source.parents), 'Immutable source staging refused')
    require(variant in VARIANTS, 'Unknown server metrics source variant')
    require(not (source / RECEIPT).exists() and not (source / RECEIPT).is_symlink(),
            'Server metrics already staged')
    base_path = source / VARIANTS[variant]
    require(base_path.is_file() and not base_path.is_symlink(), 'Missing baseline receipt')
    base = json.loads(base_path.read_text())
    if required_baseline_receipt is not None:
        require(canonical(base) == canonical(required_baseline_receipt), 'Prepared source differs from donor baseline')
    receipt = expected_receipt(variant, base, root)
    check_baseline_receipts(source, receipt)
    for name, expected in {**receipt['retained_sha256'], **receipt['source_sha256']}.items():
        check_file(source, name, expected)
    for name in (HEADER, IMPL):
        path = source / name
        require(not path.exists() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
                'Native metrics addition already exists or is linked: ' + name)
    # Every precondition above is checked before any write. Native logic is from
    # the patchwork export; only the verified loop insertions are rebased.
    _, images = native_images(variant, base, root)
    for name, data in images.items():
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (source / RECEIPT).write_text(json.dumps(receipt, indent=2) + '\n')
    return verify_prepared(source, root)


def prepare(output, variant, upstream_root=ROOT, animations_pigg=None,
            animation_manifest=None, required_baseline_receipt=None):
    root = Path(upstream_root).resolve()
    require(variant in VARIANTS, 'Unknown server metrics source variant')
    progress, startup = modules(root)
    if variant == 'thor_certified_startup':
        # generate() uses module globals, while the receipt-only validator
        # takes an explicit root. A host that pre-imported current guest code
        # must not silently generate a different historical certificate.
        certificate = startup.certificate
        require(Path(certificate.ROOT).resolve() == root
                and Path(certificate.__file__).resolve() == root / 'tools/map_startup_animation_certificate.py'
                and Path(certificate.package.__file__).resolve() == root / 'android/guest/server_animation_package.py',
                'Historical certificate modules were imported from another root; use a fresh producer process')
        require(animations_pigg is not None and animation_manifest is not None,
                'Certified startup requires the actual pinned animations PIGG and manifest')
    if required_baseline_receipt is not None:
        # Historical Windows producers have two explicitly accepted PG overlay
        # EOL profiles. Reproduce the donor's bytes in this new tree before its
        # unchanged overlay chain runs; never rewrite a published receipt.
        base = expected_baseline(variant, required_baseline_receipt, root)
        pg = base
        while 'postgresql_build_input' not in pg:
            key = next(key for key in ('monorail_build_input', 'events_build_input',
                                       'progress_build_input', 'game_build_input') if key in pg)
            pg = pg[key]
        pg = pg['postgresql_build_input']
        subprocess.run([sys.executable, str(root / 'tools/prepare_pg_source.py'),
                        '--output', str(Path(output).resolve())], check=True)
        output = Path(output)
        actual = json.loads((output / 'postgresql-build-input.json').read_text())
        require(progress.game.pg_receipt_matches(pg, actual, root), 'Donor PostgreSQL profile differs')
        for name, wanted in pg['overlay_sha256'].items():
            path = output / name
            original = path.read_bytes()
            if digest(original) != wanted:
                require(path.suffix.lower() in ('.c', '.h'), 'Nontext donor profile differs')
                lf = original.replace(b'\r\n', b'\n')
                choices = [data for data in (lf, lf.replace(b'\n', b'\r\n')) if digest(data) == wanted]
                require(len(choices) == 1, 'Unrecognized donor overlay profile: ' + name)
                path.write_bytes(choices[0])
        (output / 'postgresql-build-input.json').write_text(json.dumps(pg, indent=2) + '\n')
        progress.game.apply_game_overlay(output, root, variant='creation')
        progress.apply_progress_overlay(output, root)
        if variant == 'thor_certified_startup':
            startup.monorail.events.apply_events_overlay(output, root)
            startup.monorail.apply_monorail_overlay(output, root)
            startup.apply_startup_overlay(output, animations_pigg, animation_manifest, root)
    elif variant == 'retained_progress':
        progress.prepare(Path(output), root)
    else:
        startup.prepare(Path(output), animations_pigg, animation_manifest, root)
    return apply_metrics(output, variant, root, required_baseline_receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--output', type=Path)
    action.add_argument('--apply-to', type=Path)
    action.add_argument('--verify', type=Path)
    parser.add_argument('--variant', choices=VARIANTS)
    parser.add_argument('--upstream-root', type=Path, default=ROOT)
    parser.add_argument('--animations-pigg', type=Path)
    parser.add_argument('--animation-manifest', type=Path)
    parser.add_argument('--baseline-receipt', type=Path)
    args = parser.parse_args()
    baseline = None if args.baseline_receipt is None else json.loads(args.baseline_receipt.read_text())
    if args.verify:
        receipt = verify_prepared(args.verify, args.upstream_root)
    elif args.apply_to:
        receipt = apply_metrics(args.apply_to, args.variant, args.upstream_root, baseline)
    else:
        receipt = prepare(args.output, args.variant, args.upstream_root, args.animations_pigg,
                          args.animation_manifest, baseline)
    print(json.dumps({'status': 'source_verified', 'variant': receipt['variant'],
                      'receipt_sha256': digest(canonical(receipt)), 'native_execution_validated': False}))


if __name__ == '__main__':
    main()
