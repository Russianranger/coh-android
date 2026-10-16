#!/usr/bin/env python3
"""Qualify the actual opt-in sink via a local WinAPI shim and stager refusals."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def run(command, *, environment=None):
    result = subprocess.run(command, cwd=HERE, capture_output=True, text=True,
                            timeout=120, env=environment)
    if result.returncode:
        raise ValueError('HOST_CHECK_FAILED')
    return result


def qualify(root, sanitize):
    import stage_export as stage
    root = stage.safe_path(root)
    producer = stage.regular(root / 'native-android/engine/scenecatalog/source_export.inc')
    source = {name: (HERE / name).read_bytes() for name in
              ('stage_export.py', 'source_sink.inc', 'test_sink.c',
               'test_stage_export.py', 'delivery.py', 'test_delivery.py',
               'capture_disposable.py', 'test_capture_disposable.py', 'check.py')}
    source['producer/source_export.inc'] = producer.read_bytes()
    for name in (stage.GROUP, stage.INIT):
        source['original/' + name] = stage.lf(stage.regular(root / 'upstream/ouroboros' / name).read_bytes())
    stage.require(hashlib.sha256(source['original/' + stage.GROUP]).hexdigest() == stage.GROUP_LF_SHA256, 32)
    tests = run([sys.executable, 'test_stage_export.py'])
    match = re.search(r'Ran ([0-9]+) tests', tests.stderr)
    if not match or not re.search(r'^OK$', tests.stderr, re.MULTILINE):
        raise ValueError('STAGER_CHECK_FAILED')
    delivery_tests = run([sys.executable, 'test_delivery.py'])
    delivery_match = re.search(r'Ran ([0-9]+) tests', delivery_tests.stderr)
    if not delivery_match or not re.search(r'^OK$', delivery_tests.stderr, re.MULTILINE):
        raise ValueError('DELIVERY_CHECK_FAILED')
    capture_tests = run([sys.executable, 'test_capture_disposable.py'])
    capture_match = re.search(r'Ran ([0-9]+) tests', capture_tests.stderr)
    if not capture_match or not re.search(r'^OK$', capture_tests.stderr, re.MULTILINE):
        raise ValueError('CAPTURE_CONTROL_CHECK_FAILED')
    modes = [('release', ['-O2'])]
    if sanitize:
        modes += [('asan', ['-O1', '-g', '-fsanitize=address', '-fno-omit-frame-pointer', '-no-pie']),
                  ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]
    outcomes = []
    compiler = os.environ.get('CC', 'cc')
    environment = os.environ.copy()
    environment['ASAN_OPTIONS'] = 'detect_leaks=0:abort_on_error=1'
    with tempfile.TemporaryDirectory(prefix='coh-scene-catalog-sink-') as temporary:
        temporary = Path(temporary)
        for mode, flags in modes:
            binary = temporary / ('sink-' + mode)
            run([compiler, '-std=c89', '-Wall', '-Wextra', '-Werror', '-pedantic',
                 *flags, '-I.', 'test_sink.c', '-o', str(binary)])
            result = json.loads(run([str(binary)], environment=environment).stdout)
            if result.get('passed') is not True or result.get('actual_sink_include') is not True:
                raise ValueError('SINK_CHECK_FAILED')
            outcomes.append({'mode': mode, **result})
        disabled = temporary / 'disabled.c'
        disabled.write_text('#include "source_sink.inc"\nint main(void) { coh_source_catalog_export_startup(); return 0; }\n')
        binary = temporary / 'disabled'
        run([compiler, '-std=c89', '-Wall', '-Wextra', '-Werror', '-pedantic',
             '-I.', str(disabled), '-o', str(binary)])
        if run([str(binary)]).stdout:
            raise ValueError('DISABLED_CHECK_FAILED')
    return {
        'schema': 'coh-nonshipping-scene-catalog-server-host-v1', 'passed': True,
        'scope': 'actual_sink_include_with_mock_source_producer_local_winapi_shim_and_stager_refusals',
        'source_sha256': {name: hashlib.sha256(raw).hexdigest() for name, raw in source.items()},
        'stager_tests': int(match.group(1)), 'delivery_tests': int(delivery_match.group(1)),
        'capture_control_tests': int(capture_match.group(1)), 'sink_modes': outcomes,
        'nonwindows_disabled_noop_checked': True,
        'nonshipping': True, 'disabled_by_default': True,
        'maximum_output_bytes': 32 * 1024 * 1024,
        'process_peak_memory_cap_established': False,
        'leak_sanitizer': False,
        'host_shim_executed': True, 'mapserver_compiled': False,
        'mapserver_executed': False, 'windows_executed': False,
        'android_executed': False, 'physical_thor_accepted': False,
        'deployed': False, 'apk_changed': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    try:
        # Refuse output replacement and linked parents before any qualification.
        output = Path(os.path.abspath(args.output))
        if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
            raise ValueError('OUTPUT_EXISTS_OR_LINKED')
        result = qualify(args.source_root, args.sanitize)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as target:
            json.dump(result, target, indent=2, allow_nan=False)
            target.write('\n')
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print(json.dumps({'schema': 1, 'status': 1, 'passed': False}))
        return 2
    print(json.dumps({'schema': 1, 'status': 0, 'passed': True,
                      'stager_tests': result['stager_tests'],
                      'delivery_tests': result['delivery_tests'],
                      'capture_control_tests': result['capture_control_tests'],
                      'sink_checks_per_mode': [row['checks'] for row in result['sink_modes']],
                      'mapserver_executed': False, 'deployed': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
