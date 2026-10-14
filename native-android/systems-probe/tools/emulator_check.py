#!/usr/bin/env python3
"""Qualify native systems using installed bytes and real Android callbacks.

The audio engine consumes frames in a hosted Android backend. Physical speaker
audibility and a physical controller are deliberately separate qualifications.
Packet checks are offline; this package neither requests INTERNET nor opens a
server connection.
"""
import hashlib
import json
import math
import pathlib
import struct
import subprocess
import time
import zipfile

PACKAGE = 'org.coh.systemsprobe'
ACTIVITY = PACKAGE + '/.MainActivity'
OUTPUT = pathlib.Path('native-android/results/systems-probe')
REPORT = OUTPUT / 'emulator-systems-report.json'
ASSETS = {'audio.bin', 'audio-fixture.json'}
UI_TAP_WITNESSES = []


def adb(*args, check=True):
    return subprocess.run(['adb', *args], check=check, capture_output=True, timeout=30)


def read_report():
    result = adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/systems-probe-report.json', check=False)
    if result.returncode:
        return None
    if len(result.stdout) > 4 << 20:
        raise RuntimeError('Systems report exceeds the 4 MiB evidence limit')
    try:
        parsed = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    REPORT.write_bytes(result.stdout)
    return parsed


def wait_report(predicate, label, seconds=90, interval=1):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        report = read_report()
        if report is not None and predicate(report):
            return report
        time.sleep(interval)
    raise RuntimeError(label + ' did not pass; latest evidence retained at ' + str(REPORT))


def save_report(name, report):
    (OUTPUT / name).write_text(json.dumps(report, indent=2)+'\n')


def finite_error(value, limit):
    assert isinstance(value, (float, int)) and not isinstance(value, bool)
    assert math.isfinite(value) and 0 <= value <= limit, value


def inspect_apk_inputs(apk):
    with zipfile.ZipFile(apk) as package:
        packaged = {name.removeprefix('assets/') for name in package.namelist()
                    if name.startswith('assets/') and not name.endswith('/')}
        assert packaged == ASSETS
        metadata_bytes = package.read('assets/audio-fixture.json')
        assert 0 < len(metadata_bytes) <= 256 * 1024
        metadata = json.loads(metadata_bytes)
        payload = package.read('assets/audio.bin')
    assert 64 < len(payload) <= 1 << 20
    assert payload[:8] == b'COHAUD11'
    version, header, rate, channels, frames, pcm_bytes, bits = struct.unpack_from('<7I', payload, 8)
    assert version == 1 and header == 64 and bits == 16
    assert rate == 44100 and channels == 2 and 0 < frames <= rate * 2
    assert len(payload) == 64 + pcm_bytes and pcm_bytes == frames * channels * 2
    assert payload[36:64] == bytes(28)
    assert any(payload[64:]), 'Silence cannot qualify authentic source playback'
    assert metadata['schema'] == 'coh-native-audio-fixture-v1'
    identity = {'file': 'audio.bin', 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
    assert metadata['audio'] == identity
    contract = {'sample_rate': rate, 'channels': channels, 'frames': frames, 'pcm_bytes': pcm_bytes,
                'playback_clips': 3, 'submitted_frames': frames * 3 + (rate * 15 // 100) * 2,
                'audio': identity}
    pins = json.loads((pathlib.Path(__file__).resolve().parents[2]/'tools/audio_fixture/pins.json').read_text())
    assert metadata['fixture'] == pins['decoded']
    assert all(metadata['fixture'][key] == contract[key] for key in ('sample_rate', 'channels', 'frames', 'pcm_bytes'))
    assert metadata['fixture']['pcm_sha256'] == hashlib.sha256(payload[64:]).hexdigest()
    assert metadata['source'] == pins['record'] and metadata['acquisition']['acquisition_passed'] is True
    decode = metadata['decode']
    assert decode['passed'] is True and decode['ov_read_parameters'] == [0, 2, 1]
    assert decode['memory_callbacks_unchanged'] is True and decode['ov_read_calls'] > 0
    assert all(decode[key] == contract[key] for key in ('sample_rate', 'channels', 'frames', 'pcm_bytes'))
    gain = metadata['source_gain_oracle']
    assert gain['passed'] is True and gain['source_comparisons'] == 40 and gain['maximum_source_error'] == 0
    assert gain['source_functions'] == 2 and gain['sources'] == pins['sources']
    assert len(gain['callback_sha256']) == 4 and len(gain['function_sha256']) == 2
    assert gain['android_libm_float_gain_tolerance'] == 1e-6
    return contract, metadata


def inspect_host_proofs():
    names = ['input-host-proof.json', 'input-adapter-host-proof.json', 'audio-host-proof.json', 'protocol-original-proof.json', 'protocol-host-proof.json']
    proofs = {name: json.loads((OUTPUT/name).read_text()) for name in names}
    assert all(item['passed'] is True for item in proofs.values())
    input_proof = proofs['input-host-proof.json']
    assert input_proof['schema'] == 'coh-native-input-host-proof-v1'
    assert input_proof['source_camera_cases'] == 96 and input_proof['source_key_events'] == 2048
    assert input_proof['source_joystick_integer_cases'] == 8004
    assert input_proof['failed'] == 0 and input_proof['max_source_error'] == 0
    adapter = proofs['input-adapter-host-proof.json']
    assert adapter['schema'] == 'coh-input-adapter-host-proof-v1' and adapter['checks'] == 59
    assert adapter['negative_control']['passed'] is True
    assert adapter['negative_control']['expected_failure'] == 'END-only +X direction assertion check 3'
    assert adapter['right_stick_negative_control']['passed'] is True
    assert adapter['right_stick_negative_control']['expected_failure'] == 'RX/RY sink assertion check 51'
    source = pathlib.Path(__file__).resolve().parents[1]/'app/src/main/java/org/coh/systemsprobe/InputAdapter.java'
    assert adapter['source_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    protocol = proofs['protocol-host-proof.json']
    assert protocol['schema'] == 'coh-native-protocol-host-proof-v1'
    assert protocol['pointer_bytes'] == protocol['long_bytes'] == 8
    assert protocol['fuzz_cases'] == 12000
    assert protocol['sanitizers'] == ['AddressSanitizer', 'UndefinedBehaviorSanitizer']
    original = proofs['protocol-original-proof.json']
    assert original['schema'] == 'coh-native-protocol-reference-v1'
    assert original['wire_cases'] == 32 and original['plain_source_cases'] == 16
    assert original['source_profile'] == {'debug': False, 'siblings': False, 'acks': False,
                                         'compression_allowed': False, 'ordered_allowed': False,
                                         'zero_padding_producer_policy': True}
    assert original['source_frame_bytes_compared'] > 0
    protocol_pins = json.loads((pathlib.Path(__file__).resolve().parents[2]/'tools/protocol_fixture/source-pins.json').read_text())
    assert original['source_functions'] == len(protocol_pins['functions'])
    assert original['authenticated_negative_cases'] == 8
    assert original['header_sha256'] == hashlib.sha256((pathlib.Path(__file__).resolve().parents[2]/'protocol/protocol_goldens.h').read_bytes()).hexdigest()
    audio = proofs['audio-host-proof.json']
    assert audio['schema'] == 'coh-native-audio-host-proof-v1'
    assert audio['checks'] == 38 and audio['malformed_spans_rejected'] == 83
    assert audio['pcm_scale_components'] == 145344 and audio['asan_ubsan']['passed'] is True
    assert audio['native_android_backend_executed'] is False
    return proofs


def successful_native_runs(report):
    return [run for run in report.get('native_runs', []) if run.get('passed') is True]


def successful_audio_runs(report):
    return [run for run in report.get('audio_runs', []) if run.get('passed') is True]


def validate_assets(report, contract, metadata):
    assert report['assets_verified'] is True and report['asset_metadata'] == metadata
    verified = [event for event in report['events'] if event['type'] == 'asset_verified']
    assert len(verified) == 1 and verified[0]['detail'] == contract['audio']


def validate_native(run, contract, proofs):
    assert run['passed'] is True and run['generation'] > 0 and run['width'] > 0 and run['height'] > 0
    input_proof = proofs['input-host-proof.json']
    actual = run['input']
    assert actual['passed'] is True and actual['result'] == 1 and actual['failed'] == 0
    assert actual['checks'] == input_proof['native_checks']
    assert actual['source_cases'] == input_proof['source_camera_cases']
    assert actual['adapter_cases'] == input_proof['adapter_cases']
    finite_error(actual['max_source_error'], 0)
    audio = run['audio_source']
    assert audio['passed'] is True and audio['result'] == 0
    assert all(audio[key] == contract[key] for key in ('sample_rate', 'channels', 'frames', 'pcm_bytes'))
    assert audio['checks'] == 33 and audio['source_cases'] == 15 and audio['failed'] == 0
    finite_error(audio['max_source_error'], 1e-6)
    protocol = run['protocol']
    assert protocol['passed'] is True and protocol['result'] == 0
    for key in ('checks', 'wire_cases', 'bit_cases', 'malformed_cases', 'unaligned_cases'):
        assert protocol[key] == proofs['protocol-host-proof.json'][key], key


def validate_audio(run, contract, cancelled=False):
    assert run['opened'] is run['started'] is run['stopped'] is run['closed'] is True
    assert run['backend_errors'] == 0 and run['actual_format'] == 1
    assert run['requested_rate'] == run['actual_rate'] == contract['sample_rate']
    assert run['actual_channels'] == contract['channels']
    assert run['requested_clips'] == 3
    assert run['write_calls'] > 0 and 0 <= run['partial_writes'] <= run['write_calls']
    assert run['source_volume_db'] == -443 and run['quiet_volume_db'] == -1045
    assert abs(run['source_effective_gain'] - 0.6004819869995117) <= 1e-6
    assert abs(run['quiet_effective_gain'] - 0.3002617657184601) <= 1e-6
    assert 0 < run['duration_ns'] <= 8500000000
    assert isinstance(run['timestamp_available'], bool)
    if run['timestamp_available']:
        assert run['timestamp_frame'] >= 0 and run['timestamp_ns'] > 0
    if cancelled:
        assert run['passed'] is False and run['cancelled'] is True and run['result'] == 1
        assert 0 < run['submitted_frames'] < contract['submitted_frames']
        assert 0 <= run['completed_clips'] < 3
    else:
        assert run['passed'] is True and run['cancelled'] is False and run['result'] == 0
        assert run['completed_clips'] == 3 and run['submitted_frames'] == contract['submitted_frames']
        assert run['read_frames'] >= run['submitted_frames']


def validate(report, contract, metadata, proofs, full=False, minimum_generations=2):
    assert report['schema'] == 'coh-native-systems-probe-v1'
    assert isinstance(report['session_id'], str) and 0 < len(report['session_id']) <= 128
    assert report['device']['sdk'] == 33 and report['device']['emulator_detected'] is True
    assert report['device_audible_confirmation_passed'] is False
    assert report['controller_axis_coverage_passed'] is False
    assert report['session_failures'] == 0 and report['synthetic_dispatch_passed'] is True
    assert report['pre_background_checks_passed'] is True
    assert report['qualification_passed'] is full
    assert report['input_gate_passed'] is report['audio_engine_gate_passed'] is full
    assert report['protocol_gate_passed'] is True
    validate_android_transport(report)
    runs = successful_native_runs(report)
    assert len(runs) >= 3 and len({run['generation'] for run in runs}) >= minimum_generations
    assert len({(run['width'], run['height']) for run in runs}) >= 2
    assert len({run['width'] for run in runs}) >= 2 and len({run['height'] for run in runs}) >= 2
    assert len(runs) == len(report['native_runs']), 'Any native failure must remain a gate failure'
    current = report['input_area']
    assert any(run['generation'] == report['generation'] and run['width'] == current['width']
               and run['height'] == current['height'] and run['foreground_at_completion'] is True
               for run in runs), 'Current input view has no completed foreground proof'
    for run in runs:
        validate_native(run, contract, proofs)
    audio_runs = successful_audio_runs(report)
    assert len(audio_runs) >= (2 if full else 1)
    for run in audio_runs:
        validate_audio(run, contract)
    for run in report['audio_runs']:
        if run['passed'] is not True:
            validate_audio(run, contract, cancelled=True)
    validate_assets(report, contract, metadata)
    events = report['events']
    assert all(a['sequence'] < b['sequence'] and a['elapsed_ms'] <= b['elapsed_ms'] for a, b in zip(events, events[1:]))
    assert all(name in [event['type'] for event in events] for name in
               ('resize_requested', 'input_view_created', 'view_recreation_requested', 'auto_smoke_completed'))
    if full:
        validate_background(report, contract)
    else:
        assert report['background_return_gate_passed'] is False


def zero_input(snapshot):
    assert snapshot['result'] == 1
    assert snapshot['held'] == snapshot['pressed'] == snapshot['released'] == 0
    assert snapshot['delta_x'] == snapshot['delta_y'] == 0
    assert snapshot['axes'] == [0, 0, 0, 0]


def transport_complete(report):
    external = report.get('input_adapter', {}).get('external_android', {})
    return external.get('touch_begin', 0) >= 4 and external.get('touch_move', 0) >= 4 \
        and external.get('touch_end', 0) >= 4 and external.get('touch_motion_directions') == 15 \
        and external.get('key_down', 0) >= 6 and external.get('key_up', 0) >= 6


def validate_android_transport(report):
    adapter = report['input_adapter']
    assert adapter['schema'] == 'coh-android-input-adapter-v1'
    assert transport_complete(report)
    external = adapter['external_android']
    assert external['key_down'] == external['key_up']
    # ADB keyboard/touch callbacks qualify transport, not a physical joystick.
    assert external['controller_events'] == external['motion'] == 0
    assert external['left_axis_directions'] == external['right_axis_directions'] == 0
    expected_buttons = sum(1 << bit for bit in (8, 17, 20, 21, 22, 23))
    assert external['button_down_mask'] & expected_buttons == expected_buttons
    assert adapter['touch_active'] is False
    synthetic = adapter['in_app_synthetic']
    assert synthetic['key_down'] >= 1 and synthetic['motion'] >= 1
    assert synthetic['touch_begin'] >= 1 and synthetic['touch_move'] >= 1 and synthetic['focus_clear'] >= 2
    assert report['android_input_transport_passed'] is True
    frame = report['input_snapshot']
    assert frame['result'] == 1 and frame['frames'] > 0
    assert frame['rejected'] == 0
    assert len(frame['pyr']) == len(frame['target_pyr']) == 3
    assert all(math.isfinite(value) for value in frame['pyr'] + frame['target_pyr'])


def validate_background(report, contract):
    assert report['background_return_gate_passed'] is True
    receipt = report['background_return']
    events = {event['sequence']: event for event in report['events']}
    pause, stop, resume = (receipt[key] for key in ('pause_sequence', 'stop_sequence', 'resume_sequence'))
    assert 0 < pause < stop < resume
    assert events[pause]['type'] == 'activity_paused'
    assert events[stop]['type'] == 'activity_stopped'
    assert events[resume]['type'] == 'activity_resumed'
    assert receipt['input_cleared'] is True and receipt['audio_started_before_pause'] is True
    detail = events[pause]['detail']
    assert detail['input_cleared'] is True and detail['audio_active_or_pending'] is True
    assert detail['audio_started_before_pause'] is True
    assert detail['interrupted_audio_run_id'] == receipt['interrupted_audio_run_id']
    zero_input(detail['input_snapshot'])
    assert detail['input_snapshot']['clear_count'] > 0
    assert report['input_adapter']['external_android']['focus_clear'] > 0
    fresh_native = [run for run in successful_native_runs(report)
                    if run['started_after_event'] >= resume and run['foreground_at_completion'] is True]
    reopened = [run for run in successful_audio_runs(report)
                if run['started_after_event'] >= resume and run['foreground_at_completion'] is True]
    cancelled = [run for run in report['audio_runs']
                 if run['run_id'] == receipt['interrupted_audio_run_id']
                 and run['cancelled'] is True and run['started_after_event'] < pause]
    assert fresh_native and reopened and len(cancelled) == 1
    for run in cancelled:
        validate_audio(run, contract, cancelled=True)
        assert run['foreground_at_completion'] is False


def inject_android_input(initial):
    area = initial['input_area']
    left, top, width, height = (int(area[key]) for key in ('left', 'top', 'width', 'height'))
    assert left >= 0 and top >= 0 and width >= 64 and height >= 64
    x0, x1, y0, y1 = left + width//4, left + width*3//4, top + height//4, top + height*3//4
    xc, yc = left + width//2, top + height//2
    # Four genuine framework gestures exercise both signs of both directions.
    witnesses = []
    previous = initial
    for index, points in enumerate([(x0, yc, x1, yc), (x1, yc, x0, yc), (xc, y0, xc, y1), (xc, y1, xc, y0)]):
        adb('shell', 'input', 'touchscreen', 'swipe', *(str(value) for value in points), '800')
        axis = 1 if index < 2 else 0
        sign = 1 if index in (0, 2) else -1
        previous_angle = previous['input_snapshot']['pyr'][axis]
        previous_frames = previous['input_snapshot']['frames']
        ended = wait_report(lambda report: report.get('input_adapter', {}).get('external_android', {}).get('touch_end', 0) >= index + 1
                            and report.get('input_adapter', {}).get('touch_active') is False,
                            'Real Android touch release', seconds=15, interval=.1)
        end_frame = ended['input_snapshot']['frames']
        def native_motion_observed(report):
            snapshot = report.get('input_snapshot', {})
            pyr = snapshot.get('pyr', [])
            if len(pyr) != 3 or snapshot.get('frames', 0) < end_frame + 2:
                return False
            difference = pyr[axis] - previous_angle
            return sign * math.atan2(math.sin(difference), math.cos(difference)) >= .01 \
                and snapshot.get('delta_x') == snapshot.get('delta_y') == 0 \
                and report.get('input_adapter', {}).get('touch_active') is False
        observed = wait_report(native_motion_observed, 'Source native editor-look movement from Android touch', seconds=15, interval=.1)
        witnesses.append({'gesture': index + 1, 'axis': axis,
                          'native_frame_before': previous_frames,
                          'native_frame_at_observed_release': end_frame,
                          'native_frame_after': observed['input_snapshot']['frames'],
                          'expected_direction': sign,
                          'angle_before': previous_angle,
                          'angle_after': observed['input_snapshot']['pyr'][axis]})
        previous = observed
    adb('shell', 'input', 'keyboard', 'keyevent', 'KEYCODE_SPACE', 'KEYCODE_ENTER',
        'KEYCODE_W', 'KEYCODE_S', 'KEYCODE_A', 'KEYCODE_D')
    tap_control('run')
    (OUTPUT/'emulator-input-motion-proof.json').write_text(json.dumps({
        'schema': 1, 'passed': True, 'scope': 'Real injected Android touch callbacks reaching native source editor-look preview; no gameplay camera',
        'gestures': witnesses}, indent=2)+'\n')


def tap_control(action):
    """Tap the actual Android button without delivering a lifecycle Intent."""
    before = read_report()
    assert before is not None and action in before['controls']
    expected_event = {'run': 'checks_complete', 'play': 'audio_play_requested',
                      'stop': 'audio_cancel_requested', 'resize': 'resize_requested',
                      'recreate': 'view_recreation_requested'}[action]
    pauses = sum(event['type'] == 'activity_paused' for event in before['events'])
    row = before['control_row']
    assert row['visible'] is True and row['width'] >= 100 and row['height'] >= 20
    for direction in (-1, 1):
        for attempt in range(4):
            report = read_report()
            assert report is not None and report['session_id'] == before['session_id']
            target = report['controls'][action]
            if target['visible'] is True and target['width'] >= 20 and target['height'] >= 20:
                assert row['left'] <= target['left'] and row['top'] <= target['top']
                assert target['left'] + target['width'] <= row['left'] + row['width']
                assert target['top'] + target['height'] <= row['top'] + row['height']
                last_sequence = max(event['sequence'] for event in report['events'])
                native_before = max((run['run_id'] for run in report['native_runs']), default=0)
                x = int(target['left'] + target['width']//2)
                y = int(target['top'] + target['height']//2)
                adb('shell', 'input', 'touchscreen', 'tap', str(x), str(y))
                def matching_events(r):
                    candidates = [e for e in r.get('events', [])
                                  if e['sequence'] > last_sequence and e['type'] == expected_event]
                    if action in ('play', 'stop'):
                        return [e for e in candidates if e['detail'].get('reason') == 'manual']
                    if action == 'run':
                        manual_ids = {run['run_id'] for run in r.get('native_runs', [])
                                      if run['run_id'] > native_before and run.get('reason') == 'manual'}
                        return [e for e in candidates if e['detail']['run_id'] in manual_ids]
                    return candidates
                observed = wait_report(lambda r: r.get('session_id') == before['session_id']
                                       and bool(matching_events(r)),
                                       'Real Android button action ' + action, seconds=15, interval=.1)
                assert sum(event['type'] == 'activity_paused' for event in observed['events']) == pauses, 'Foreground UI action unexpectedly paused the Activity'
                matching = matching_events(observed)
                assert len(matching) == 1
                UI_TAP_WITNESSES.append({'action': action, 'tap_x': x, 'tap_y': y,
                    'visible_button_bounds': target, 'control_row_bounds': row,
                    'before_event_sequence': last_sequence,
                    'observed_event': matching[0], 'pause_events_before': pauses,
                    'pause_events_after': pauses})
                (OUTPUT/'emulator-ui-tap-proof.json').write_text(json.dumps({
                    'schema': 1, 'passed': True,
                    'scope': 'Measured real Android Button taps bound to exact listener events; no foreground lifecycle Intent',
                    'button_taps': UI_TAP_WITNESSES}, indent=2)+'\n')
                return observed
            xc, yc = int(row['left'] + row['width']//2), int(row['top'] + row['height']//2)
            distance = int(row['width']//3)
            adb('shell', 'input', 'touchscreen', 'swipe', str(xc - direction*distance), str(yc),
                str(xc + direction*distance), str(yc), '500')
            time.sleep(.6)
    raise RuntimeError('Android button remained outside the measured control row: ' + action)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    apk = OUTPUT / 'CoH-Native-Systems-Probe-0.1.1-emulator-x86_64.apk'
    contract, metadata = inspect_apk_inputs(apk)
    proofs = inspect_host_proofs()
    adb('install', '-r', str(apk))
    adb('shell', 'am', 'force-stop', PACKAGE)
    adb('shell', 'pm', 'clear', PACKAGE)
    adb('logcat', '-c')
    try:
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--ez', 'autoSmoke', 'true')
        ready = wait_report(lambda report: report.get('auto_smoke_stage') == 3
                            and report.get('audio_busy') is False
                            and len(successful_native_runs(report)) >= 3
                            and len(successful_audio_runs(report)) >= 1,
                              'Three native source proofs, full AAudio play/close, and resize/recreate')
        session = ready['session_id']
        inject_android_input(ready)
        initial = wait_report(lambda report: report.get('session_id') == session
                              and report.get('pre_background_checks_passed') is True
                              and transport_complete(report), 'Actual Android keyboard and touch transport')
        validate(initial, contract, metadata, proofs)
        save_report('emulator-initial-report.json', initial)
        # Cancellation is requested through the Android lifecycle while a real
        # AAudio worker owns an active stream, then its close result is checked.
        old_audio = max(run['run_id'] for run in initial['audio_runs'])
        tap_control('play')
        wait_report(lambda report: report.get('session_id') == session
                    and report.get('audio_busy') is True and report.get('backend_audio_active') is True,
                    'Native AAudio worker starting', seconds=15, interval=.05)
        time.sleep(.1)
        adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
        paused = wait_report(lambda report: report.get('session_id') == session
                             and report.get('qualification_passed') is False
                             and report.get('background_return', {}).get('stop_sequence', 0) > 0
                             and any(run['run_id'] > old_audio and run.get('cancelled') is True
                                     and run.get('closed') is True for run in report.get('audio_runs', [])),
                             'Home cancellation, input clear, and native Stop/Close', seconds=30, interval=.25)
        assert paused['audio_busy'] is paused['backend_audio_active'] is False
        zero_input(next(event for event in paused['events'] if event['sequence'] == paused['background_return']['pause_sequence'])['detail']['input_snapshot'])
        cancel = [run for run in paused['audio_runs'] if run['run_id'] > old_audio and run['cancelled'] is True]
        assert len(cancel) == 1
        validate_audio(cancel[0], contract, cancelled=True)
        save_report('emulator-background-report.json', paused)
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY)
        foreground = wait_report(lambda report: report.get('session_id') == session
                                 and report.get('qualification_passed') is True,
                                 'Fresh foreground source proofs and full AAudio reopen')
        validate(foreground, contract, metadata, proofs, full=True)
        save_report('emulator-foreground-report.json', foreground)
        before = max(run['run_id'] for run in successful_native_runs(foreground))
        tap_control('resize')
        resized = wait_report(lambda report: report.get('session_id') == session
                              and report.get('qualification_passed') is True
                              and any(run['run_id'] > before for run in successful_native_runs(report)),
                              'Second real input-view resize')
        validate(resized, contract, metadata, proofs, full=True)
        generation = max(run['generation'] for run in successful_native_runs(resized))
        tap_control('recreate')
        final = wait_report(lambda report: report.get('session_id') == session
                            and report.get('qualification_passed') is True
                            and any(run['generation'] > generation for run in successful_native_runs(report)),
                            'Second actual input-view recreation')
        validate(final, contract, metadata, proofs, full=True, minimum_generations=3)
        names = [event['type'] for event in final['events']]
        assert names.count('activity_paused') == names.count('activity_stopped') == 1
        assert names.count('activity_resumed') == 2
        snapshot = final['input_snapshot']
        zero_input(snapshot)
        save_report('emulator-final-report.json', final)
        summary = {'schema': 1, 'phases': [10, 11, 12], 'passed': True,
                   'scope': 'Android 13 x86_64 hosted emulator; source kernel proofs, injected real Android callbacks, AAudio sink, offline packet framing',
                   'native_runs': len(successful_native_runs(final)),
                   'successful_view_generations': len({run['generation'] for run in successful_native_runs(final)}),
                   'successful_actual_dimensions': len({(run['width'], run['height']) for run in successful_native_runs(final)}),
                   'input_source_cases': sum(run['input']['source_cases'] for run in successful_native_runs(final)),
                   'input_native_checks': sum(run['input']['checks'] for run in successful_native_runs(final)),
                   'external_android_input': final['input_adapter']['external_android'],
                   'in_app_synthetic_input': final['input_adapter']['in_app_synthetic'],
                   'source_gain_checks': sum(run['audio_source']['checks'] for run in successful_native_runs(final)),
                   'full_aaudio_play_stop_close_runs': len(successful_audio_runs(final)),
                   'aaudio_submitted_frames': sum(run['submitted_frames'] for run in successful_audio_runs(final)),
                   'aaudio_read_frames': sum(run['read_frames'] for run in successful_audio_runs(final)),
                   'lifecycle_audio_cancel_stop_close_runs': len(cancel),
                   'native_offline_wire_cases': sum(run['protocol']['wire_cases'] for run in successful_native_runs(final)),
                   'native_offline_bit_cases': sum(run['protocol']['bit_cases'] for run in successful_native_runs(final)),
                   'native_offline_malformed_cases': sum(run['protocol']['malformed_cases'] for run in successful_native_runs(final)),
                   'native_offline_unaligned_cases': sum(run['protocol']['unaligned_cases'] for run in successful_native_runs(final)),
                   'verified_audio_asset': contract['audio'],
                   'actual_resize_verified': True, 'view_recreation_verified': True,
                   'foreground_ui_buttons_preserve_home_receipt': True,
                   'actual_home_pause_stop_resume_cycles': 1,
                   'foreground_return_verified': True, 'foreground_input_clear_verified': True,
                   'physical_controller_verified': False, 'physical_audibility_verified': False,
                   'external_network_execution': False, 'server_interoperability_verified': False,
                   'original_game_execution': False, 'thor_device_execution_verified': False}
        (OUTPUT/'emulator-smoke-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print(json.dumps(summary))
    finally:
        (OUTPUT/'emulator-logcat.txt').write_bytes(adb('logcat', '-d', check=False).stdout)
        screenshot = adb('exec-out', 'screencap', '-p', check=False)
        if screenshot.returncode == 0 and screenshot.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
            (OUTPUT/'emulator-screenshot.png').write_bytes(screenshot.stdout)


if __name__ == '__main__':
    main()
