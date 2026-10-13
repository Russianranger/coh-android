#!/usr/bin/env python3
"""Run the installed probe's real Surface lifecycle on the hosted emulator."""
import json
import pathlib
import subprocess
import time

PACKAGE = 'org.coh.nativeprobe'
ACTIVITY = PACKAGE + '/.MainActivity'
OUTPUT = pathlib.Path('native-android/results/surface-probe')
REPORT = OUTPUT / 'emulator-surface-report.json'


def adb(*args, check=True):
    return subprocess.run(['adb', *args], check=check, capture_output=True, timeout=30)


def read_report():
    result = adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/surface-probe-report.json', check=False)
    if result.returncode != 0:
        return None
    if len(result.stdout) > 4 << 20:
        raise RuntimeError('Probe report exceeded 4 MiB evidence limit')
    try:
        report = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    REPORT.write_bytes(result.stdout)
    return report


def wait_report(predicate, label, seconds=120):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        last = read_report()
        if last is not None and predicate(last):
            return last
        time.sleep(2)
    raise RuntimeError(label + ' did not pass; latest app evidence retained at ' + str(REPORT))


def successful_runs(report):
    return [run for run in report.get('native_runs', [])
            if run.get('passed') is True and run.get('obsolete') is False]


def validate(report):
    assert report['schema'] == 'coh-native-surface-probe-v1'
    assert report['qualification_passed'] is True
    assert report['device']['sdk'] == 33
    assert report['device']['emulator_detected'] is True
    qualification = report['qualification']
    assert qualification['failed_runs'] == 0
    assert qualification['successful_surface_generations'] >= 2
    assert qualification['successful_actual_dimensions'] >= 2
    runs = successful_runs(report)
    assert len(runs) >= 3
    assert len({(run['callback_width'], run['callback_height']) for run in runs}) >= 2
    assert len({run['generation'] for run in runs}) >= 2
    for run in runs:
        native = run['native']
        assert all(native.get(key) is True for key in
                   ['passed', 'cpu_golden_match', 'context_recreation_passed',
                    'fbo_pixel_match', 'window_pixel_match'])
        assert native['surface_width'] == run['callback_width'] > 0
        assert native['surface_height'] == run['callback_height'] > 0
        assert len(native['cycles']) == 2
        for cycle in native['cycles']:
            assert cycle['completed'] is True and cycle['objects_released'] is True
            assert cycle['compared_pixels'] > 0 and cycle['mismatched_pixels'] == 0
            assert cycle['window_samples'] > 0 and cycle['window_mismatches'] == 0
            assert cycle['swap_passed'] is True and cycle['gl_errors'] == 0
    names = [event['event'] for event in report['events']]
    for name in ['resize_requested', 'surface_changed', 'surface_recreation_requested',
                 'surface_destroyed', 'surface_created', 'auto_smoke_completed']:
        assert name in names, name


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    apk = OUTPUT / 'CoH-Native-Surface-Probe-0.1.0-emulator-x86_64.apk'
    adb('install', '-r', str(apk))
    adb('logcat', '-c')
    try:
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--ez', 'autoSmoke', 'true')
        first = wait_report(lambda report: report.get('qualification_passed') is True
                            and report.get('auto_smoke_stage') == 3,
                            'Real texture, resize, and Surface recreation')
        validate(first)
        before = len(successful_runs(first))
        adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
        wait_report(lambda report: any(event['event'] == 'activity_paused'
                                      for event in report.get('events', [])),
                    'Background lifecycle callback', seconds=20)
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--es', 'probe_action', 'run')
        final = wait_report(lambda report: report.get('qualification_passed') is True
                            and len(successful_runs(report)) > before,
                            'Render after returning to foreground')
        validate(final)
        names = [event['event'] for event in final['events']]
        assert 'activity_paused' in names and names.count('activity_resumed') >= 2
        summary = {'schema': 1, 'passed': True, 'scope': 'Android 13 x86_64 hosted emulator with SwiftShader; not AYN Thor',
                   'real_fixture_sha256': final['fixture']['verified_dds_sha256'],
                   'original_win32_rgba_sha256': final['fixture']['verified_expected_rgba_sha256'],
                   'successful_runs': len(successful_runs(final)),
                   'actual_resize_verified': True, 'surface_recreation_verified': True,
                   'foreground_return_verified': True, 'thor_device_execution_verified': False}
        (OUTPUT / 'emulator-smoke-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print(json.dumps(summary))
    finally:
        (OUTPUT / 'emulator-logcat.txt').write_bytes(adb('logcat', '-d', check=False).stdout)
        screenshot = adb('exec-out', 'screencap', '-p', check=False)
        if screenshot.returncode == 0 and screenshot.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
            (OUTPUT / 'emulator-screenshot.png').write_bytes(screenshot.stdout)


if __name__ == '__main__':
    main()
