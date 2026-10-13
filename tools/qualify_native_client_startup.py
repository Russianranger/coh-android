#!/usr/bin/env python3
"""Run the actual retained Game in owned Wine/Xvfb, with bounded host evidence.

Two launches use the same closed prefix and data caches. No login is attempted;
Game main loop, renderer, current PID window and captured pixels are separate
observations. Software GL timings never predict AYN Thor or FEX performance.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time

from prepare_native_client_profile_fixture import APK, SOURCE, GAME_SHA, LAUNCHER_SHA, pin, require, write
ROOT = Path(__file__).resolve().parents[1]
MAX_LOG = 16 * 1024**2
OBSERVED_GAME = {'bytes': 9474048, 'sha256': '338172fe57ae9ce303797f784d85c5c9e3a2f768b3373fc5340dfd78f8b75020'}
CLIENT_PROBE = {'bytes': 470392, 'sha256': '24bd3e6927afaddd63fe9a4b0fac240a28383ab5e2c7d8d41d5b4d0781214cd0'}

class UnreadableWineProcess(ValueError):
    def __init__(self, pid, name):
        super().__init__('Unreadable same-user Wine process')
        self.pid, self.name = pid, name[:128]

def login_crop(source, target):
    """Read-only OCR derivative; no native UI action or graphics change."""
    raw = source.read_bytes()
    require(len(raw) <= 4 * 1024**2, 'Login capture exceeded bounded RGB frame')
    match = re.match(rb'P6\n([0-9]+) ([0-9]+)\n255\n', raw)
    require(match is not None, 'Exact native RGB PPM capture required')
    width, height = map(int, match.groups()); pixels = raw[match.end():]
    require(320 <= width <= 1280 and 240 <= height <= 720 and len(pixels) == width * height * 3,
            'Login capture dimensions/payload invalid')
    # The actual manual profile is 800x600. Keep a bounded normalized right
    # label region, away from the stock first-prefix graphics-choice popup.
    left, top, right, bottom = width * 11 // 16, height * 17 // 60, width * 79 // 80, height * 89 // 120
    scale = 4; rows = []
    for y in range(top, bottom):
        row = pixels[(y * width + left) * 3:(y * width + right) * 3]
        expanded = b''.join(row[x:x + 3] * scale for x in range(0, len(row), 3))
        rows.extend([expanded] * scale)
    out_width, out_height = (right - left) * scale, (bottom - top) * scale
    require(out_width * out_height * 3 <= 8 * 1024**2, 'OCR derivative exceeded bound')
    target.write_bytes(('P6\n%d %d\n255\n' % (out_width, out_height)).encode() + b''.join(rows))
    return {'source': pin(source), 'derivative': pin(target), 'crop_xyxy': [left, top, right, bottom],
            'scale': scale, 'method': 'RGB_right_login_labels_nearest_upscale', 'native_pixels_or_UI_changed': False}

def observe_login_text(frame_path, tool, directory, label):
    require(pin(Path(tool['resolved'])) == tool['resolved_pin'], 'Host OCR binary changed')
    derivative = directory / (label + '-login-crop.ppm')
    transform = login_crop(frame_path, derivative)
    results = []
    for kind, path, psm in (('full', frame_path, '11'), ('right_labels', derivative, '6'), ('right_labels', derivative, '11')):
        result = subprocess.run([tool['invocation'], str(path), 'stdout', '--psm', psm], capture_output=True, timeout=30)
        require(len(result.stdout) + len(result.stderr) <= 65536, 'Login frame OCR exceeded bound')
        output = directory / (label + '-ocr-' + kind + '-' + psm + '.txt'); output.write_bytes(result.stdout)
        diagnostic = directory / (label + '-ocr-' + kind + '-' + psm + '.stderr'); diagnostic.write_bytes(result.stderr)
        seen = result.returncode == 0 and bool(re.search(r'login|log in|password|account', result.stdout.decode('utf8', 'replace'), re.I))
        results.append({'kind': kind, 'psm': int(psm), 'returncode': result.returncode,
                        'output': pin(output), 'stderr': pin(diagnostic), 'login_text_observed': seen})
        if seen: break
    value = {'format': 1, 'raw_frame': pin(frame_path), 'transform': transform, 'attempts': results,
             'login_text_observed': any(row['login_text_observed'] for row in results),
             'UI_input_sent': False, 'graphics_quality_changed': False}
    write(directory / (label + '-login-observation.json'), value)
    return value

def native_probe(assets, env, wine, directory):
    probe = Path(assets) / 'client-probe.exe'
    require(pin(probe) == CLIENT_PROBE, 'Exact retained native PE32 client probe required')
    started = time.monotonic()
    result = subprocess.run([wine, 'Z:' + str(probe).replace('/', '\\')], env=env,
                            capture_output=True, timeout=60)
    require(len(result.stdout) + len(result.stderr) <= 1024**2, 'Native WGL prerequisite output exceeded bound')
    (directory / 'client-probe.stdout').write_bytes(result.stdout)
    (directory / 'client-probe.stderr').write_bytes(result.stderr)
    rows = re.findall(r'^COH_CLIENT_PROBE_V1 (\{[^\n]*\})\r?$', result.stdout.decode('utf8', 'replace'), re.M)
    require(len(rows) == 1, 'Exactly one actual retained WGL probe record required')
    row = json.loads(rows[0]); write(directory / 'client-probe.json', row)
    require(result.returncode == 0 and row.get('status') == 'passed' and row.get('pointer_bits') == 32
            and row.get('failure_stage') == '' and row.get('gl', {}).get('renderer_class') == 'software'
            and row.get('render', {}).get('textured_quad_verified') is True
            and row.get('render', {}).get('samples_verified') == 4 and row.get('render', {}).get('swap_buffers') is True,
            'Actual retained PE32 software-WGL/context/texture/readback prerequisites failed')
    return {'native_probe': CLIENT_PROBE, 'elapsed_seconds': round(time.monotonic() - started, 6),
            'actual_record': row, 'outside_Game_timing': True, 'may_warm_driver_and_prefix': True,
            'Game_shaders_or_assets_exercised': False}

def all_x_windows(observer, client):
    """Retain empty-titled native dialogs as well as ordinary named windows."""
    C = client.C; pending = [observer.root]; seen = set(); rows = []
    while pending:
        window = pending.pop()
        if window in seen: continue
        seen.add(window); require(len(seen) <= 512, 'Failure X window inventory exceeded bound')
        attributes = client.XWindowAttributes(); pointer = C.c_void_p(); title = ''
        if observer.lib.XGetWindowAttributes(observer.display, window, C.byref(attributes)):
            if observer.lib.XFetchName(observer.display, window, C.byref(pointer)) and pointer:
                try: title = C.string_at(pointer).decode('utf8', 'replace')[:256]
                finally: observer.lib.XFree(pointer)
            rows.append({'window_id': int(window), 'title': title, 'width': attributes.width, 'height': attributes.height,
                         'mapped': attributes.map_state == 2, 'x': attributes.x, 'y': attributes.y})
        root, parent, count, children = C.c_ulong(), C.c_ulong(), C.c_uint(), C.POINTER(C.c_ulong)()
        if observer.lib.XQueryTree(observer.display, window, C.byref(root), C.byref(parent), C.byref(children), C.byref(count)):
            try:
                require(count.value <= 512, 'Failure X child inventory exceeded bound')
                pending.extend(int(children[i]) for i in range(count.value))
            finally:
                if children: observer.lib.XFree(children)
    return rows

def failure_evidence(observer, client, work, env, tools, directory):
    records = {}; omissions = []
    try:
        query = subprocess.run([tools['wine']['invocation'], 'reg', 'query', r'HKCU\Software\Cryptic\CoH',
            '/v', 'GameProgress', '/reg:32'], env=env, capture_output=True, timeout=15)
        require(len(query.stdout) + len(query.stderr) <= 65536, 'Failure registry observation exceeded bound')
        (directory / 'failure-registry.stdout').write_bytes(query.stdout)
        (directory / 'failure-registry.stderr').write_bytes(query.stderr)
        records['registry_returncode'] = query.returncode
    except BaseException as error: omissions.append({'kind': 'registry', 'reason': str(error)[:500]})
    if observer is not None:
        try:
            records['all_X_windows_including_untitled'] = all_x_windows(observer, client)
            records['frame'] = observer.capture(directory / 'failure-desktop.ppm')
            ocr = subprocess.run([tools['tesseract']['invocation'], str(directory / 'failure-desktop.ppm'), 'stdout', '--psm', '11'],
                                 capture_output=True, timeout=30)
            require(len(ocr.stdout) + len(ocr.stderr) <= 65536, 'Failure desktop OCR exceeded bound')
            (directory / 'failure-desktop-ocr.txt').write_bytes(ocr.stdout)
            records['ocr_returncode'] = ocr.returncode
        except BaseException as error: omissions.append({'kind': 'window/frame', 'reason': str(error)[:500]})
    logs = work / 'logs'; selected = []; total = 0
    try:
        if logs.exists():
            require(logs.is_dir() and not logs.is_symlink(), 'Linked native Game error logs refused')
            for path in sorted(logs.rglob('*')):
                if path.is_dir(): continue
                info = path.lstat()
                require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid(), 'Unowned native error log refused')
                if len(selected) == 64 or total + info.st_size > 8 * 1024**2:
                    omissions.append({'kind': 'native_log', 'path': path.relative_to(work).as_posix(), 'reason': 'bounded_report_limit'}); continue
                target = directory / 'native-error-logs' / path.relative_to(logs)
                target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
                total += info.st_size; selected.append({'path': path.relative_to(work).as_posix(), 'bytes': info.st_size})
        records['native_error_logs'] = selected
    except BaseException as error: omissions.append({'kind': 'native_logs', 'reason': str(error)[:500]})
    records['omissions'] = omissions; write(directory / 'failure-observations.json', records)
    return records

def binary_tool(name):
    invocation = shutil.which(name)
    require(invocation is not None, 'Required host tool unavailable: ' + name)
    # Preserve the Wine wrapper invocation. Debian alternatives are links;
    # authenticate their resolved regular executable without calling it instead.
    resolved = Path(invocation).resolve(strict=True)
    return {'invocation': invocation, 'resolved': str(resolved), 'resolved_pin': pin(resolved)}

def process_census(prefix):
    matched = []; entries = list(Path('/proc').iterdir())
    require(len(entries) <= 16384, 'Host process census exceeded bound')
    for path in entries:
        if not path.name.isdigit(): continue
        try:
            status = (path / 'status').read_text(); match = re.search(r'^Uid:\s+(\d+)', status, re.M)
            if not match or int(match.group(1)) != os.geteuid(): continue
            raw = (path / 'environ').read_bytes()
            require(len(raw) <= 1024**2, 'Oversized process environment')
            if b'WINEPREFIX=' + str(prefix).encode() not in raw.split(b'\0'): continue
            matched.append({'pid': int(path.name), 'name': (path / 'comm').read_text().strip()[:128]})
        except (FileNotFoundError, ProcessLookupError): continue
        except PermissionError:
            # Same-user unreadable Wine process prevents claiming cleanup.
            try: name = (path / 'comm').read_text().lower()
            except (FileNotFoundError, ProcessLookupError): continue
            if any(s in name for s in ('wine', 'cityofheroes', 'client-launcher')):
                raise UnreadableWineProcess(int(path.name), name)
    return matched

def check_held_prefix(prefix, descriptor, info):
    held, current = os.fstat(descriptor), prefix.lstat()
    require((held.st_dev, held.st_ino, held.st_uid) == (info.st_dev, info.st_ino, info.st_uid)
            == (current.st_dev, current.st_ino, current.st_uid) and stat.S_ISDIR(current.st_mode)
            and not current.st_mode & 0o077, 'Held owned prefix identity changed during stop/census wait')

def stop_prefix(prefix, env, tool, directory, owned_process=None):
    info = prefix.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o077,
            'Private owned host prefix required for stop')
    require(pin(Path(tool['resolved'])) == tool['resolved_pin'], 'Host wineserver executable changed')
    require(env.get('WINEPREFIX') == str(prefix.absolute()), 'Exact owned prefix environment required for stop')
    descriptor = os.open(prefix, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    operations = []
    observations = []; reaped = None
    try:
        for option in ('-k', '-w'):
            check_held_prefix(prefix, descriptor, info)
            result = subprocess.run([tool['invocation'], option], env=env, capture_output=True, timeout=30)
            require(len(result.stdout) <= 65536 and len(result.stderr) <= 65536, 'Wine stop diagnostic exceeded bound')
            (directory / ('wineserver' + option + '.stdout')).write_bytes(result.stdout)
            (directory / ('wineserver' + option + '.stderr')).write_bytes(result.stderr)
            operations.append({'argument': option, 'returncode': result.returncode,
                               'stdout': pin(directory / ('wineserver' + option + '.stdout')),
                               'stderr': pin(directory / ('wineserver' + option + '.stderr'))})
            require(result.returncode in ((0, 1) if option == '-k' else (0,)), 'Owned prefix Wine stop/wait failed')
        if owned_process is not None:
            require(isinstance(owned_process, subprocess.Popen), 'Exact held native-launch Popen required for reap')
            held_pid = owned_process.pid
            returncode = owned_process.wait(timeout=10)
            require(type(held_pid) is int and held_pid > 0 and type(returncode) is int,
                    'Held native-launch process could not be reaped')
            reaped = {'pid': held_pid, 'returncode': returncode, 'reaped_after_exact_prefix_stop': True,
                      'additional_signal_sent': False, 'normal_game_exit_claimed': False}
            write(directory / 'held-launcher-reaped.json', reaped)
        deadline = time.monotonic() + 10
        while True:
            check_held_prefix(prefix, descriptor, info)
            try:
                processes = process_census(prefix)
                observation = {'status': 'readable', 'exact_prefix_processes': processes}
            except UnreadableWineProcess as error:
                processes = None
                observation = {'status': 'unreadable_same_user_Wine', 'pid': error.pid, 'name': error.name,
                               'absence_claimed': False, 'additional_signal_sent': False}
            observations.append(observation)
            write(directory / 'owned-prefix-census.json', {'format': 1, 'observations': observations,
                  'held_owned_prefix_identity': [info.st_dev, info.st_ino, info.st_uid], 'bounded_wait_seconds': 10})
            if processes == []: break
            require(time.monotonic() < deadline and len(observations) <= 101,
                    'Owned prefix census remained unreadable or live after bounded wait')
            time.sleep(.1)
    finally: os.close(descriptor)
    value = {'format': 1, 'prefix': str(prefix), 'prefix_identity': [info.st_dev, info.st_ino, info.st_uid],
        'operations': operations, 'exact_prefix_processes_remaining': processes,
        'census_observations': observations, 'held_owned_prefix_handle_checked': True,
        'held_launch_Popen_reaped_before_census': reaped,
        'passed': True, 'unrelated_processes_signalled': False, 'normal_game_exit_claimed': False}
    write(directory / 'owned-prefix-stop.json', value)
    return value

def registry_empty(wine, env, directory):
    root = r'HKCU\Software\Cryptic\CoH'
    records = []
    for action in ('delete', 'query'):
        command = [wine, 'reg', action, root, '/v', 'GameProgress']
        if action == 'delete': command.append('/f')
        command.append('/reg:32')
        result = subprocess.run(command, env=env, capture_output=True, timeout=30)
        require(len(result.stdout) + len(result.stderr) <= 65536, 'Registry reset output exceeded bound')
        for label, raw in (('stdout', result.stdout), ('stderr', result.stderr)):
            (directory / ('registry-' + action + '.' + label)).write_bytes(raw)
        text = (result.stdout + result.stderr).decode('utf8', 'replace')
        records.append({'action': action, 'returncode': result.returncode, 'output': text})
        if action == 'delete':
            require(result.returncode == 0 or result.returncode == 1 and
                    re.search(r'unable to find|not found|does not exist', text, re.I), 'GameProgress reset failed')
        else:
            require(result.returncode == 1 and not re.search(r'^\s*GameProgress\s+REG_SZ', text, re.M)
                    and re.search(r'unable to find|not found|does not exist', text, re.I),
                    'GameProgress must be absent before current Game launch')
    write(directory / 'registry-reset.json', records)
    return records

def cache_snapshot(work):
    result = {}
    for relative in ('data/bin', 'data/geobin', 'data/server/bin'):
        root = work / relative
        require(root.is_dir() and not root.is_symlink(), 'Private cache root required')
        for path in sorted(root.rglob('*.bin')):
            require(len(result) < 8192, 'Native BIN snapshot exceeded bound')
            result[path.relative_to(work).as_posix()] = pin(path)
    return result

def cache_delta(before, after):
    keys = sorted(set(before) | set(after))
    return [{'path': n, 'before': before.get(n), 'after': after.get(n)} for n in keys if before.get(n) != after.get(n)]

def parse_cg(text):
    rows = []
    for line in text.replace('\r', '').splitlines():
        if not line.startswith('COH_NATIVE_CG_PROFILE_V1 '): continue
        pairs = [field.split('=', 1) for field in line.split()[1:]]
        require(all(len(p) == 2 for p in pairs), 'Malformed native Cg field')
        fields = dict(pairs)
        require(len(fields) == len(pairs), 'Duplicate native Cg field')
        require(set(fields) == {'kind', 'input_token', 'success', 'clock_valid', 'create_us', 'driver_load_called', 'driver_load_us'},
                'Native Cg profile fields differ')
        require(fields['kind'] in ('0', '1', '2') and fields['clock_valid'] == '1'
                and fields['success'] in ('0', '1') and fields['driver_load_called'] in ('0', '1')
                and re.fullmatch('[0-9a-f]{8}', fields['input_token']), 'Native Cg row invalid')
        for n in ('create_us', 'driver_load_us'):
            require(re.fullmatch('0|[1-9][0-9]*', fields[n]) and int(fields[n]) < 2**64, 'Native Cg integer invalid')
            fields[n] = int(fields[n])
        rows.append(fields)
    require(len(rows) <= 1024, 'Native Cg rows unbounded')
    return {'rows': rows, 'source_count': sum(r['kind'] == '1' for r in rows),
        'object_count': sum(r['kind'] == '2' for r in rows),
        'create_us': sum(r['create_us'] for r in rows), 'driver_load_us': sum(r['driver_load_us'] for r in rows),
        'object_does_not_prove_gpu_driver_cache_hit': True}

def launch_case(args, fixture, client, work, env, tools, output, label):
    directory = output / label; directory.mkdir(mode=0o700)
    before = {}
    session = os.urandom(16).hex()
    command = [tools['wine']['invocation'], 'Z:' + str(Path(fixture['assets']) / 'client-launcher.exe').replace('/', '\\'),
               session, 'Z:' + str(work / 'CityOfHeroes.exe').replace('/', '\\'), 'Z:' + str(work).replace('/', '\\'), '--character-manual']
    write(directory / 'invocation.json', {'session': session, 'command': command,
        'game': pin(work / 'CityOfHeroes.exe'), 'native_role': args.native_role,
        'effective_graphics_profile': env['COH_CLIENT_GRAPHICS_PROFILE'], 'bounded_host_seconds': args.timeout_seconds,
        'shader_cache_acceptance_changed': False, 'source_freshness_changed': False,
        'native_software_renderer_only': True, 'owned_prefix': env['WINEPREFIX'],
        'controls': {k: v for k, v in env.items() if k.startswith('COH_')}})
    started = time.monotonic(); observer = None; samples = []; evidence = None
    process = None; failure = None; cleanup = None; login_observations = []; first_native_seconds = None
    try:
        registry_empty(tools['wine']['invocation'], env, directory)
        before = cache_snapshot(work); write(directory / 'bins-before.json', before)
        observer = client.XObserver(env['DISPLAY'])
        with (directory / 'stdout.log').open('wb') as stdout, (directory / 'stderr.log').open('wb') as stderr:
            started = time.monotonic()
            process = subprocess.Popen(command, cwd=work, env=env, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, start_new_session=True)
            deadline = started + args.timeout_seconds
            while True:
                require(time.monotonic() < deadline, 'Actual Game startup exceeded bounded host deadline')
                require(process.poll() is None, 'Actual Game/launcher exited during startup')
                require((directory / 'stdout.log').stat().st_size <= MAX_LOG and (directory / 'stderr.log').stat().st_size <= MAX_LOG,
                        'Native current console exceeded evidence budget')
                text = (directory / 'stdout.log').read_text(errors='replace')
                require('COH_CLIENT_CONSOLE_TRUNCATED_V1' not in text, 'Native console truncated')
                launch = client.parse_launch(text, session); console = client.console_identity(text, launch)
                registry = subprocess.run([tools['wine']['invocation'], 'reg', 'query', r'HKCU\Software\Cryptic\CoH',
                    '/v', 'GameProgress', '/reg:32'], env=env, capture_output=True, timeout=15)
                require(len(registry.stdout) + len(registry.stderr) <= 65536, 'Current registry evidence exceeded bound')
                raw = registry.stdout.decode('utf8', 'replace')
                current = client.startup_evidence(text, raw, observer.windows(), launch)
                samples.append({'elapsed_seconds': round(time.monotonic() - started, 6), 'registry_returncode': registry.returncode,
                    'main_loop': current['client_main_loop_reached'], 'current_pid': launch.get('pid') if launch else None,
                    'current_owned_window': current['client_window_observed']})
                require(len(samples) <= 721, 'Current startup observer exceeded sample bound')
                if registry.returncode == 0 and console and current['startup_observed'] and current['renderer_initialized'] and current['all_data_loaded']:
                    first = time.monotonic()
                    if first_native_seconds is None: first_native_seconds = round(first - started, 6)
                    require(len(login_observations) < 3, 'Captured current Game frames have no login/account/password text')
                    capture_label = 'startup' if not login_observations else 'startup-retry-' + str(len(login_observations) + 1)
                    capture = observer.capture(directory / (capture_label + '.ppm'))
                    require(capture['distinct_colors_capped'] >= 16, 'Captured current renderer produced insufficient pixel variation')
                    ocr = observe_login_text(directory / (capture_label + '.ppm'), tools['tesseract'], directory, capture_label)
                    login_observations.append(dict(ocr, capture=capture, elapsed_seconds=round(time.monotonic() - started, 6)))
                    evidence = {'elapsed_seconds': first_native_seconds, 'launch': launch, 'console': console,
                        'current_registry': raw, 'registry_returncode': registry.returncode, 'current_native_evidence': current,
                        'frame': capture, 'ocr_returncode': ocr['attempts'][-1]['returncode'],
                        'login_text_observed': ocr['login_text_observed'], 'login_observations': login_observations,
                        'native_startup_witness_seconds': first_native_seconds,
                        'login_frame_observed_seconds': round(time.monotonic() - started, 6),
                        'OCR_processing_separate_from_native_startup_clock': True,
                        'menu_visual_parity_claimed': False, 'cg': parse_cg(text)}
                    require(current['graphics_observation']['renderer_classification'] == 'software',
                            'Actual host Game must identify its software renderer')
                    if evidence['login_text_observed']:
                        if args.native_role == 'cg-observed': require(evidence['cg']['rows'], 'Actual observed Game emitted no Cg measurements')
                        break
                time.sleep(2)
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': str(error)[:2048]}
    finally:
        if failure is not None:
            failure_evidence(observer, client, work, env, tools, directory)
        if observer is not None: observer.close()
        try:
            cleanup = stop_prefix(Path(env['WINEPREFIX']), env, tools['wineserver'], directory, owned_process=process)
        except BaseException as error:
            cleanup = {'passed': False, 'message': str(error)[:2048]}
        try:
            after = cache_snapshot(work)
            write(directory / 'bins-after.json', after)
        except BaseException as error:
            after = {}
            if failure is None: failure = {'type': type(error).__name__, 'message': str(error)[:2048]}
        result = {'format': 1, 'status': 'passed' if evidence and not failure and cleanup['passed'] else 'failed',
            'label': label, 'evidence': evidence, 'failure': failure, 'cleanup': cleanup,
            'cache_delta': cache_delta(before, after), 'cache_before_count': len(before), 'cache_after_count': len(after),
            'samples': samples, 'generated_cache_mutations_reported': True,
            'bounded_login_frame_observations': login_observations,
            'native_game_executed': process is not None, 'physical_device_executed': False,
            'native_map_or_character_connection_claimed': False, 'software_GL_timing_scope': True}
        write(directory / 'native-client-phase.json', result)
    require(result['status'] == 'passed', 'Actual Game phase failed; current evidence retained: ' + label)
    return result

def qualify(args):
    require(sys.platform == 'linux' and 60 <= args.timeout_seconds <= 900, 'Bounded Linux host execution required')
    fixture = json.loads(args.fixture.read_text()); work = Path(fixture['work']); assets = Path(fixture['assets'])
    require(fixture.get('role') == 'complete_public_036_native_client_host_fixture' and fixture.get('donor_apk') == APK
            and fixture.get('donor_source_commit') == SOURCE and fixture.get('status') == 'prepared', 'Authenticated .36 full client fixture required')
    require(pin(work / 'CityOfHeroes.exe') == fixture['game'] and fixture['game']['sha256'] == GAME_SHA,
            'Retained .36 Game fixture changed')
    require(pin(assets / 'client-launcher.exe')['sha256'] == LAUNCHER_SHA, 'Retained manual launcher changed')
    require(not args.output.exists() and not args.prefix.exists() and not any(p.is_symlink() for p in (*args.output.parents, *args.prefix.parents)),
            'Fresh unlinked client evidence and owned prefix required')
    args.output.mkdir(parents=True, mode=0o700); args.prefix.mkdir(parents=True, mode=0o700)
    tools = {n: binary_tool(n) for n in ('wine', 'wineserver', 'tesseract')}
    sys.path.insert(0, str(assets)); client = importlib.import_module('client_startup_diagnostic')
    require(Path(client.__file__).parent == assets, 'Only actual donor guest observer required')
    context = type('FixtureContext', (), {'report': {'client_worktree': fixture['actual_client_worktree']}, 'check': lambda self: None,
                                            'event': lambda self, *args, **kwargs: None})()
    texture_env = fixture['texture_header_environment']
    if args.native_role == 'cg-observed':
        require(args.native is not None and pin(args.native) == OBSERVED_GAME, 'Exact completed historical Cg diagnostic Game required')
        work.joinpath('CityOfHeroes.exe').chmod(0o600); shutil.copyfile(args.native, work / 'CityOfHeroes.exe')
        thi = importlib.import_module('texture_header_index')
        index, texture_env = thi.prepare(work, fixture['actual_client_worktree']['import'], OBSERVED_GAME['sha256'], context)
        require(index.get('native_file_opens_avoidable', 0) > 0 and index.get('original_texture_files_unchanged') is True,
                'New observed executable texture index binding required')
        write(args.output / 'observed-texture-index.json', index)
    else: require(args.native_role == 'retained' and args.native is None, 'Unexpected native role')
    env = dict(os.environ, WINEARCH='win32', WINEPREFIX=str(args.prefix.absolute()), WINEDEBUG='-all',
        WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree=d;mshtml=d', TZ='UTC', LANG='C.UTF-8',
        LIBGL_ALWAYS_SOFTWARE='1', XDG_CACHE_HOME=str(args.prefix.absolute() / 'xdg-cache'),
        MESA_SHADER_CACHE_DIR=str(args.prefix.absolute() / 'mesa-shader-cache'),
        COH_CLIENT_GRAPHICS_PROFILE='performance', COH_CLIENT_DEPENDENCY_PRELOAD='1',
        COH_CLIENT_SCENE_PROFILE='1', COH_CLIENT_DEFER_DISCARDED_FX_PRELOAD='1', COH_CLIENT_FRAME_TIMING='1',
        COH_CLIENT_BIN_PROFILE='1', COH_CLIENT_KNOWN_STRING_COPY='1',
        COH_CLIENT_GAMEPLAY_FPS='30', COH_CLIENT_BOUNDED_TEXTURE_ERRORS='1',
        COH_CLIENT_RENDERER_ATTRIBUTION='1', COH_CLIENT_RENDER_PIPELINE='0', COH_CLIENT_RENDER_QUEUE='1')
    env.update(texture_env)
    require(env.get('DISPLAY'), 'Explicit owned Xvfb display required')
    initialization = args.output / 'initialization'; initialization.mkdir()
    results = []; failure = None; final_cleanup = None
    try:
        started = time.monotonic()
        boot = subprocess.run([tools['wine']['invocation'], 'wineboot', '--init'], env=env, capture_output=True, timeout=180)
        for label, raw in (('stdout', boot.stdout), ('stderr', boot.stderr)): (initialization / ('wineboot.' + label)).write_bytes(raw)
        require(boot.returncode == 0 and len(boot.stdout) + len(boot.stderr) <= 1024**2, 'Owned Wine initialization failed')
        probe = native_probe(assets, env, tools['wine']['invocation'], initialization)
        stop_prefix(args.prefix, env, tools['wineserver'], initialization)
        write(initialization / 'initialization.json', {'elapsed_seconds': round(time.monotonic() - started, 6), 'tools': tools,
            'returncode': boot.returncode, 'fresh_prefix': True, 'initialization_outside_Game_timing': True,
            'actual_PE32_WGL_preflight': probe})
        for label in ('first-launch', 'closed-prefix-second-launch'):
            results.append(launch_case(args, fixture, client, work, env, tools, args.output, label))
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': str(error)[:2048]}
    finally:
        cleanup_directory = args.output / 'final-cleanup'; cleanup_directory.mkdir()
        try:
            final_cleanup = stop_prefix(args.prefix, env, tools['wineserver'], cleanup_directory)
        except BaseException as error:
            final_cleanup = {'passed': False, 'type': type(error).__name__, 'message': str(error)[:2048]}
        value = {'format': 1, 'role': 'nonshipping_native_client_Wine_software_GL_startup',
            'status': 'passed' if len(results) == 2 and failure is None and final_cleanup['passed'] else 'failed',
            'failure': failure, 'final_cleanup': final_cleanup, 'fixture': pin(args.fixture), 'native_role': args.native_role,
            'actual_native': pin(work / 'CityOfHeroes.exe'), 'donor_source': SOURCE, 'host_tools': tools, 'cases': results,
            'qualification_source': pin(Path(__file__)), 'fixture_source': fixture['source_script'],
            'repository_commit': os.environ.get('GITHUB_SHA'), 'workflow_run_id': os.environ.get('GITHUB_RUN_ID'),
            'current_window_and_console_PID_required': True, 'captured_desktop_not_exclusive_Game_frame': True,
            'login_text_required': True, 'software_renderer_identity_required': True,
            'database_opened': False, 'character_login_attempted': False, 'player_profile_used': False,
            'physical_device_executed': False, 'performance_target_met_on_Thor': False,
            'closed_prefix_is_not_cold_filesystem_cache': True, 'publication_allowed': False}
        write(args.output / 'native-client-startup-qualification.json', value)
    require(value['status'] == 'passed', 'Actual client native qualification failed; current failure/cleanup evidence retained')
    return value

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('fixture', 'output', 'prefix'): p.add_argument('--' + n, type=Path, required=True)
    p.add_argument('--native-role', choices=('retained', 'cg-observed'), default='retained')
    p.add_argument('--native', type=Path); p.add_argument('--timeout-seconds', type=int, default=900)
    value = qualify(p.parse_args()); print(json.dumps({'status': value['status'], 'role': value['role']}))
