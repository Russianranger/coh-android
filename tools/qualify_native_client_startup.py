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
            require(not any(s in name for s in ('wine', 'cityofheroes', 'client-launcher')), 'Unreadable same-user Wine process')
    return matched

def stop_prefix(prefix, env, tool, directory):
    info = prefix.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o077,
            'Private owned host prefix required for stop')
    require(pin(Path(tool['resolved'])) == tool['resolved_pin'], 'Host wineserver executable changed')
    operations = []
    for option in ('-k', '-w'):
        result = subprocess.run([tool['invocation'], option], env=env, capture_output=True, timeout=30)
        require(len(result.stdout) <= 65536 and len(result.stderr) <= 65536, 'Wine stop diagnostic exceeded bound')
        (directory / ('wineserver' + option + '.stdout')).write_bytes(result.stdout)
        (directory / ('wineserver' + option + '.stderr')).write_bytes(result.stderr)
        operations.append({'argument': option, 'returncode': result.returncode,
                           'stdout': pin(directory / ('wineserver' + option + '.stdout')),
                           'stderr': pin(directory / ('wineserver' + option + '.stderr'))})
        require(result.returncode in ((0, 1) if option == '-k' else (0,)), 'Owned prefix Wine stop/wait failed')
    deadline = time.monotonic() + 10
    while True:
        processes = process_census(prefix)
        if not processes: break
        require(time.monotonic() < deadline, 'Owned prefix still has live processes after wait')
        time.sleep(.1)
    value = {'format': 1, 'prefix': str(prefix), 'prefix_identity': [info.st_dev, info.st_ino, info.st_uid],
        'operations': operations, 'exact_prefix_processes_remaining': processes,
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
    process = None; failure = None; cleanup = None
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
                    first = time.monotonic(); capture = observer.capture(directory / 'startup.ppm')
                    require(capture['distinct_colors_capped'] >= 16, 'Captured current renderer produced insufficient pixel variation')
                    ocr = subprocess.run([tools['tesseract']['invocation'], str(directory / 'startup.ppm'), 'stdout', '--psm', '11'],
                                         capture_output=True, timeout=30)
                    require(len(ocr.stdout) + len(ocr.stderr) <= 65536, 'Login frame OCR exceeded evidence budget')
                    (directory / 'startup-ocr.txt').write_bytes(ocr.stdout)
                    evidence = {'elapsed_seconds': round(first - started, 6), 'launch': launch, 'console': console,
                        'current_registry': raw, 'registry_returncode': registry.returncode, 'current_native_evidence': current,
                        'frame': capture, 'ocr_returncode': ocr.returncode,
                        'login_text_observed': ocr.returncode == 0 and bool(re.search(r'login|log in|password|account', ocr.stdout.decode('utf8', 'replace'), re.I)),
                        'menu_visual_parity_claimed': False, 'cg': parse_cg(text)}
                    require(current['graphics_observation']['renderer_classification'] == 'software',
                            'Actual host Game must identify its software renderer')
                    require(evidence['login_text_observed'], 'Captured current Game frame has no login/account/password text')
                    if args.native_role == 'cg-observed': require(evidence['cg']['rows'], 'Actual observed Game emitted no Cg measurements')
                    break
                time.sleep(2)
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': str(error)[:2048]}
    finally:
        if observer is not None: observer.close()
        try:
            cleanup = stop_prefix(Path(env['WINEPREFIX']), env, tools['wineserver'], directory)
            if process is not None: process.wait(timeout=20)
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
        stop_prefix(args.prefix, env, tools['wineserver'], initialization)
        write(initialization / 'initialization.json', {'elapsed_seconds': round(time.monotonic() - started, 6), 'tools': tools,
            'returncode': boot.returncode, 'fresh_prefix': True, 'initialization_outside_Game_timing': True})
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
