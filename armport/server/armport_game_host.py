#!/usr/bin/env python3
"""ArmPort M3 host driver: original server stack plus the ARM64 client, login
scripted on a shared X display.

Reuses the repository's qualified ARM64 game stack (tools/android/game/
host_game_smoke.py): the same PRoot guest, private loopback-only network
namespace, PostgreSQL, Wine 10 with FEX, fake-auth DbServer, Atlas MapServer
and the original TestClient that creates and saves a character
(armport_game_guest.py). This driver then runs the ARM64 client exactly as
M2's boot test does (the app's Wine 10 on the host, Xvfb, Mesa; folder staged
by smoke_run.py --stage-only), but inside the guest's private network
namespace (nsenter), so it reaches the servers on 127.0.0.1 and nothing else.
It types the login with xdotool, finds buttons by OCR, and keeps a screenshot
of every step.

Exit status 0 only if the guest report passed, which requires the ARM64
client's character to be connected on Atlas (map 1) in the database and still
connected after the in-game screenshots.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools/android/game'))
sys.path.insert(0, str(ROOT / 'armport/scripts'))
import host_game_smoke as game  # noqa: E402
import smoke_run  # noqa: E402
import client_errors  # noqa: E402
import atlas_wine  # noqa: E402
sys.path.insert(0, str(ROOT / 'armport/replay'))
import stall_snapshot  # noqa: E402
import zone_frame  # noqa: E402
from login_ui import DISPLAY, sh, Screen, at, wait_for, login, after_login, acknowledge_qa_notice, character_select_from_log  # noqa: E402

dbhost = game.dbhost
note, flush_report = smoke_run.note, smoke_run.flush_report
def guest_netns(own):
    """A process of ours inside the guest's network namespace (PRoot runs
    there as the original user)."""
    for entry in os.listdir('/proc'):
        if not entry.isdigit():
            continue
        try:
            if os.stat(f'/proc/{entry}').st_uid != os.getuid():
                continue
            ns = os.readlink(f'/proc/{entry}/ns/net')
        except OSError:
            continue
        if ns != own:
            return int(entry), ns
    return None, None


def start_client(a, state, status, evidence):
    """Waits for the guest's ready marker, then starts the ARM64 client in the
    guest's network namespace. Returns the process or None."""
    ready = state / 'armport-ready.json'
    while not ready.exists():
        if status.get('guest_exited'):
            return None, None
        time.sleep(2)
    info = json.loads(ready.read_text())
    pid, ns = guest_netns(os.readlink('/proc/self/ns/net'))
    status['guest_netns'] = ns
    status['guest_pid'] = pid
    capture_traffic(status, evidence)
    if not pid:
        status['client_error'] = 'guest network namespace not found'
        (state / 'armport-client-exited.json').write_text(json.dumps({'error': status['client_error']}) + '\n')
        return None, info
    client = a.client.resolve()
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(a.client_home), 'LANG': 'C.UTF-8', 'DISPLAY': DISPLAY,
           'WINEPREFIX': str(a.client_prefix), 'WINEDEBUG': 'err+all,fixme-all,+seh',
           'WINEDLLOVERRIDES': 'mscoree,mshtml=', 'ARMPORT_LOOSE_DATA': '1', 'ARMPORT_STDIO_LOG': 'armport_stdio.txt',
           'ARMPORT_ZONE_LOG': 'zone-trace.jsonl',
           'ARMPORT_WINE_BOUNDARY_LOG': 'Z:' + str((evidence / 'client-output.txt').resolve()).replace('/', '\\'),
           # The servers are 32-bit builds with their own version string (patch 0045).
           'ARMPORT_NO_VERSION_CHECK': '1'}
    args = ['-fullscreen', '0', '-screen', '1024', '768', '-verbose', '1', '-db', '127.0.0.1']
    command = ['sudo', '-n', 'nsenter', f'--net=/proc/{pid}/ns/net', '--', 'sudo', '-n', '-u', os.environ.get('USER', 'runner'),
               '--', 'env', '-C', str(client)] + [f'{k}={v}' for k, v in env.items()] + \
              [str(a.wine / 'wine'), str(client / 'CityOfHeroes.exe')] + args
    # Wine and the client's map-start witness append to this same stream.
    # Remove stale evidence before opening with O_APPEND; never overwrite a
    # client boundary with a later Wine write at a stale descriptor offset.
    (evidence / 'client-output.txt').unlink(missing_ok=True)
    out = open(evidence / 'client-output.txt', 'ab')
    proc = subprocess.Popen(command, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    status['client_started'] = True
    status['client_args'] = args
    (state / 'armport-client-started.json').write_text(json.dumps({'args': args, 'netns': ns}) + '\n')

    def watch():
        code = proc.wait()
        status['client_exit'] = code
        if not (state / 'armport-guest-finished.json').exists():
            (state / 'armport-client-exited.json').write_text(json.dumps({'exit': code}) + '\n')

    def stop_when_guest_finishes():
        # The guest's own cleanup audits same-user Wine processes, so the
        # client and its wineserver must be gone before it continues.
        while not (state / 'armport-guest-finished.json').exists():
            if status.get('guest_exited'):
                return
            time.sleep(2)
        stop_client(a, proc)
        (state / 'armport-client-stopped.json').write_text(json.dumps({'stopped': True}) + '\n')
    threading.Thread(target=watch, daemon=True).start()
    threading.Thread(target=stop_when_guest_finishes, daemon=True).start()
    return proc, info


def stop_client(a, proc):
    if proc and proc.poll() is None:
        subprocess.run(['sudo', '-n', 'kill', '-TERM', '--', f'-{proc.pid}'], capture_output=True)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            subprocess.run(['sudo', '-n', 'kill', '-KILL', '--', f'-{proc.pid}'], capture_output=True)
    wenv = dict(os.environ, WINEPREFIX=str(a.client_prefix), HOME=str(a.client_home))
    subprocess.run([str(a.wine / 'wineserver'), '-k'], capture_output=True, timeout=120, env=wenv)
    # Wait until the client's wineserver (and so its Wine processes) is gone:
    # the guest's cleanup audits same-user Wine processes.
    try:
        subprocess.run([str(a.wine / 'wineserver'), '-w'], capture_output=True, timeout=90, env=wenv)
    except subprocess.TimeoutExpired:
        pass


def capture_traffic(status, evidence):
    """Loopback traffic on the game-client ports inside the guest's namespace,
    from as soon as it exists (so the TestClient's login is the reference)."""
    own = os.readlink('/proc/self/ns/net')
    while not status.get('guest_exited'):
        pid, ns = guest_netns(own)
        if pid:
            cap = evidence / 'udp-7000-7001.pcap'
            # Detached through a shell that exits at once: a sudo process left
            # running keeps this user's real UID with a root-only environment,
            # which the guest's Wine-ownership audit (rightly) refuses.
            subprocess.run(['sudo', '-n', 'sh', '-c',
                            f'nsenter --net=/proc/{pid}/ns/net tcpdump -i lo -n -U -s 256 -w {cap} '
                            "'udp and (port 7000 or port 7001)' </dev/null >/dev/null 2>&1 &"],
                           capture_output=True, timeout=30)
            status['tcpdump'] = True
            return
        time.sleep(3)


def drive_login(a, screen, state, status, evidence):
    """Runs in a thread: starts the client when the servers are ready, then logs in."""
    proc, info = start_client(a, state, status, evidence)
    status['proc'] = proc
    if not proc:
        return
    # Sockets in the guest's network namespace: does the client reach DbServer (7000/UDP)?
    def sockets(label):
        pid = status.get('guest_pid')
        r = subprocess.run(['sudo', '-n', 'nsenter', f'--net=/proc/{pid}/ns/net', 'ss', '-tanup'],
                           capture_output=True, text=True, timeout=30) if pid else None
        # The client's own sockets (servers' listeners and wineserver-held
        # sockets are known from the DbServer and MapServer logs).
        lines = [l for l in (r.stdout.splitlines() if r else [])
                 if 'CityOfHeroes' in l or ('ESTAB' in l and ':70' in l)]
        windows = sh('xwininfo', '-root', '-tree').stdout.splitlines()
        named = [' '.join(w.split())[:140] for w in windows if '"' in w and 'has no name' not in w]
        status.setdefault('sockets', []).append({'when': label, 'client_sockets': [' '.join(l.split())[:200] for l in lines[:30]],
                                                 'windows': named[:12]})
    status['account'] = info['account']
    if not login(screen, info['account'], 'armportm3', status, after=sockets):
        return
    # Character select: the created character's name, then Play (or Enter).
    checks = {'n': 0}

    def character_select(p):
        status['character_select_by_trace'] = character_select_from_log(a.client / 'armport_stdio.txt')
        if status['character_select_by_trace']:
            return True
        checks['n'] += 1
        if checks['n'] % 3 == 0:
            sockets(f'character-select wait {checks["n"]}')
        # After a successful dbConnect the client may show the NDA/agreement
        # dialog (uiLogin.c LOGIN_STAGE_NDA) before the character list.
        agree = screen.find(p, 'Agree', 'AGREE', 'Accept', 'ACCEPT')
        if agree:
            status['nda_agreed'] = status.get('nda_agreed', 0) + 1
            screen.click(*agree)
            return None
        t = screen.text(p)
        return t if info['character'].lower() in t.lower() or 'play' in t.lower() else None
    # EULA/NDA agreements and the server list come first (login_ui.after_login).
    png = after_login(screen, status, rounds=8, interval=10, done=character_select, after=sockets)
    png = png if png and character_select(png) else None
    trace_ready = status.get('character_select_by_trace', False)
    if trace_ready or (not png and status.get('server_clicked')):
        # Character select draws a 3D scene that OCR may not read; the login
        # traffic shows the character list arrives, so enter by the Next arrow.
        pos = at(screen, 'enter_world')
        if pos:
            screen.click(*pos)
            status['enter_by_layout'] = True
            (state / 'armport-play-sent.json').write_text(json.dumps({'play_sent': 'layout'}) + '\n')
            time.sleep(15)
            screen.shot('after-enter')
            sockets('15s after Next')
        else:
            status['enter_layout_error'] = 'Client window unavailable for Next'
    status['character_select'] = bool(png) or trace_ready
    if png and not trace_ready:
        pos = screen.find(png, info['character'])
        if pos:
            screen.click(*pos)
            time.sleep(2)
            png = screen.shot('character-chosen')
        pos = screen.find(png, 'Play', 'PLAY')
        if pos:
            screen.click(*pos)
        else:
            screen.key('Return')
        status['play_sent'] = True
        (state / 'armport-play-sent.json').write_text(json.dumps({'play_sent': True}) + '\n')
    # In game: wait for the guest's database confirmation, then screenshots.
    atlas = state / 'armport-atlas.json'
    deadline = time.time() + 1200
    while not atlas.exists() and time.time() < deadline and not status.get('guest_exited'):
        time.sleep(15)
        screen.shot('loading')
    if atlas.exists():
        status['atlas'] = json.loads(atlas.read_text())
        # The database has the character on Atlas; the client then loads the
        # zone (a mostly white loading screen). Wait for the world to render.
        started = time.monotonic()
        diagnostic_seconds = 0
        rendered = 0
        status['loading_brightness'] = []
        status['load_samples'] = []
        status['frame_checks'] = []
        next_snapshot = iter((120, 600))
        snapshot_at = next(next_snapshot, None)
        while time.monotonic() - started - diagnostic_seconds < 1500 and rendered < 2 and not status.get('guest_exited'):
            time.sleep(30)
            png = screen.shot('zone-loading')
            stdio = a.client / 'armport_stdio.txt'
            stdio_text = stdio.read_text(errors='replace') if stdio.exists() else ''
            if acknowledge_qa_notice(screen, stdio_text, stall_snapshot.client_pids(a.client), status):
                # This pre-input frame cannot establish rendering. The next
                # iteration must observe the original load/READY and image checks.
                rendered = 0
                continue
            check = zone_frame.evaluate(png, screen.window(), stdio_text, screen.text)
            status['frame_checks'].append(check)
            mean = check['frame']['mean'] if check['frame'] else None
            status['loading_brightness'].append(round(mean, 3) if mean is not None else None)
            rendered = rendered + 1 if check['rendered'] else 0
            status['load_samples'].append({'seconds': round(time.monotonic() - started - diagnostic_seconds),
                                          'stdio_bytes': stdio.stat().st_size if stdio.exists() else None})
            if rendered == 0 and snapshot_at is not None and time.monotonic() - started - diagnostic_seconds >= snapshot_at:
                sample_started = time.monotonic()
                try:
                    stall_snapshot.capture(a.client, evidence, str(snapshot_at), a.llvm_mingw)
                except Exception as exc:
                    # A diagnostic failure must not alter the existing verdict.
                    (evidence / f'stall-{snapshot_at}.txt').write_text(repr(exc))
                finally:
                    diagnostic_seconds += time.monotonic() - sample_started
                snapshot_at = next(next_snapshot, None)
        status['world_rendered'] = rendered >= 2
        status['zone_load_seconds'] = round(time.monotonic() - started - diagnostic_seconds)
        status['diagnostic_seconds_excluded'] = round(diagnostic_seconds, 3)
        status['atlas_shot'] = str(png) if png else None
        time.sleep(30)
        status['atlas_shot_later'] = str(screen.shot('atlas-later'))
        (state / 'armport-host-done.json').write_text(json.dumps({'done': True}) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--assets', type=Path, required=True, help='coh-diagnostic-runtime-inputs')
    ap.add_argument('--package', type=Path, required=True, help='assembled wine-game package')
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--schema', type=Path, required=True)
    ap.add_argument('--stack-probe', type=Path, required=True)
    ap.add_argument('--proot', type=Path, required=True)
    ap.add_argument('--client', type=Path, required=True, help='ARM64 client runtime folder (smoke_run --stage-only)')
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--evidence', type=Path, required=True)
    ap.add_argument('--wine', type=Path, required=True, help='host install of the app\'s Wine (wine, wineserver)')
    ap.add_argument('--llvm-mingw', type=Path, help='for llvm-symbolizer on client crashes')
    ap.add_argument('--client-prefix', type=Path, required=True, help='fresh Wine prefix for the client')
    ap.add_argument('--client-home', type=Path, required=True)
    ap.add_argument('--timeout-seconds', type=int, default=5400)
    a = ap.parse_args()
    assets, package, data, schema, work, evidence, proot, client = (
        getattr(a, n).resolve() for n in ('assets', 'package', 'data', 'schema', 'work', 'evidence', 'proot', 'client'))

    dbhost.verify_runtime_assets(assets)
    game.verify_package(package, dbserver_profile='loopback', game_listener_profile='loopback')
    data_manifest = game.verify_data(data)
    dbhost.verify_schema(schema)
    disk = game.check_paths_and_space(work, evidence, (assets, package, data, schema, proot),
                                      data_bytes=sum(r['bytes'] for r in data_manifest['files'].values()))
    note('notice', 'ArmPort M3 disk preflight', json.dumps(disk)[:600])
    for name in ('proot', 'proot-loader'):
        (proot / name).chmod(0o755)
    game.prepare_runtime(work, evidence, assets)
    shutil.copyfile(a.stack_probe / 'GameStackProbe.exe', work / 'm3-tools/GameStackProbe.exe')
    shutil.copyfile(HERE / 'armport_game_guest.py', work / 'm3-tools/armport_game_guest.py')

    command = game.make_command(work=work, assets=assets, package=package, data=data, schema=schema,
                                proot=proot, timeout_seconds=a.timeout_seconds)
    command = ['/opt/coh-m3/armport_game_guest.py' if c == '/opt/coh-m3/game_diagnostic.py' else c for c in command]
    py = command.index('/usr/bin/python3')
    command[py:py] = ['ARMPORT_CLIENT_SECONDS=1500']
    command, env, network_expected = dbhost.isolate_command(command, evidence=evidence, proot=proot, work=work)

    # Large enough for the whole 1024x768 window at Wine's default position
    # (+104+130); at 1280x800 its bottom rows were off screen in M2.
    xvfb = subprocess.Popen(['Xvfb', DISPLAY, '-screen', '0', '1600x1200x24', '-nolisten', 'tcp', '+extension', 'GLX'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    # The client's own Wine prefix, prepared on the host as in M2 while the
    # servers start (wineserver stopped again so the client starts its own).
    a.client_home.mkdir(parents=True, exist_ok=True)
    wenv = dict(os.environ, DISPLAY=DISPLAY, WINEPREFIX=str(a.client_prefix), HOME=str(a.client_home),
                WINEDLLOVERRIDES='mscoree,mshtml=')
    boot = subprocess.run([str(a.wine / 'wine'), 'wineboot', '-i'], env=wenv, capture_output=True, timeout=600)
    subprocess.run([str(a.wine / 'wine'), 'reg', 'add', 'HKCU\\Software\\Wine\\WineDbg', '/v', 'ShowCrashDialog',
                    '/t', 'REG_DWORD', '/d', '0', '/f'], env=wenv, capture_output=True, timeout=120)
    subprocess.run([str(a.wine / 'wineserver'), '-k'], env=wenv, capture_output=True, timeout=120)
    note('notice', 'ArmPort M3 client prefix', f'wineboot exit {boot.returncode}')
    screen = Screen(evidence / 'screens')
    state = work / 'state'
    status = {}

    log_path = evidence / 'host-game.log'
    report_path = state / 'latest-report.json'
    code = None
    with log_path.open('w') as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        driver = threading.Thread(target=drive_login, args=(a, screen, state, status, evidence), daemon=True)
        driver.start()
        # (The capture starts with the ARM64 client: started with the guest, the two
        # runs with it lost Atlas readiness in the original flow; the TestClient
        # reference conversation is in runs 39910179066 and 39917757607.)
        try:
            code = process.wait(timeout=a.timeout_seconds + 120)
        except subprocess.TimeoutExpired:
            note('error', 'ArmPort M3 guest', 'timed out: ' + dbhost.stop_guest(process, state))
    status['guest_exited'] = True
    driver.join(timeout=60)
    stop_client(a, status.pop('proc', None))
    if status.pop('tcpdump', None):
        subprocess.run(['sudo', '-n', 'pkill', '-INT', '-f', 'tcpdump -i lo -n -U -s 256'], capture_output=True)
        time.sleep(2)
        cap = evidence / 'udp-7000-7001.pcap'
        if cap.exists():
            subprocess.run(['sudo', '-n', 'chown', str(os.getuid()), str(cap)], capture_output=True)
            r = subprocess.run(['tcpdump', '-r', str(cap), '-n', '-tt'], capture_output=True, text=True)
            pk = r.stdout.splitlines()
            flows = {}
            for l in pk:
                m = l.split()
                if len(m) > 4:
                    flows[(m[2], m[4].rstrip(':'))] = flows.get((m[2], m[4].rstrip(':')), 0) + 1
            note('notice', 'ArmPort M3 UDP 7000/7001', f'{len(pk)} packets; flows: ' +
                 '; '.join(f'{s}>{d}: {n}' for (s, d), n in sorted(flows.items(), key=lambda kv: -kv[1])[:12]))
            # Packet sizes in order per client port (TestClient first, then the ARM64 client).
            seq = {}
            for l in pk:
                m = l.split()
                if len(m) > 4:
                    src, dst = m[2], m[4].rstrip(':')
                    port = src if src.endswith(('.7000', '.7001')) is False else dst
                    arrow = '>' if dst.endswith(('.7000', '.7001')) else '<'
                    size = l.rsplit('(', 1)[-1].rstrip(')') if '(' in l else '?'
                    seq.setdefault(port.rsplit('.', 1)[-1] + ('/7001' if '7001' in src + dst else '/7000'), []).append(arrow + size)
            note('notice', 'ArmPort M3 UDP sequences', '\n'.join(f'{k}: ' + ' '.join(v[:45]) for k, v in seq.items())[:3800])
            x = subprocess.run(['tcpdump', '-r', str(cap), '-n', '-X', '-c', '14'], capture_output=True, text=True).stdout
            note('notice', 'ArmPort M3 UDP first packets (hex)', x[:3800])
    xvfb.kill()

    report = json.loads(report_path.read_text()) if report_path.is_file() else {}
    if report_path.is_file():
        shutil.copyfile(report_path, evidence / 'armport-game-report.json')
    stages = [(s.get('name') or s.get('stage'), s.get('status')) for s in report.get('stages', [])]
    note('notice' if report.get('passed') else 'error', 'ArmPort M3 guest result',
         f"exit {code}; status {report.get('status')}; passed {report.get('passed')}\n"
         + '\n'.join(f'{n}: {s}' for n, s in stages[-25:])
         + ('\nfailures: ' + json.dumps(report.get('failures'))[:1500] if report.get('failures') else ''))
    client_record = report.get('game', {}).get('armport_client', {})
    note('notice', 'ArmPort M3 ARM64 client (guest view)', json.dumps(client_record, indent=1)[:3500])
    lines = (evidence / 'client-output.txt').read_text(errors='replace').splitlines() \
        if (evidence / 'client-output.txt').exists() else []
    smoke_run.report_exceptions(lines, client / 'CityOfHeroes.exe', a.llvm_mingw, 'ArmPort M3 client')
    smoke_run.report_crash(lines, 'ArmPort M3 client crash', client / 'CityOfHeroes.exe', a.llvm_mingw)
    tail = [l[:300] for l in lines if not l.startswith('ALSA lib')][-60:]
    if tail:
        note('notice', 'ArmPort M3 client output tail', '\n'.join(tail))
    errs = [l[:300] for l in lines if ':err:' in l or 'trace:seh' in l or 'Unhandled' in l]
    if errs:
        note('notice', 'ArmPort M3 client Wine errors', f'{len(errs)} lines; last 50:\n' + '\n'.join(errs[-50:]))
    (evidence / 'login-driver.json').write_text(json.dumps(status, indent=2) + '\n')
    note('notice', 'ArmPort M3 login driver', json.dumps(status, indent=1)[:1500] + '\n' + '\n'.join(screen.log[-60:]))
    smoke_run.report_stdio(client / 'armport_stdio.txt', 'ArmPort M3 client stdio')
    stdio = client / 'armport_stdio.txt'
    if stdio.exists():
        marks = [l[:200] for l in stdio.read_text(errors='replace').splitlines() if l.startswith('ArmPort ')]
        changes = [l for i, l in enumerate(marks) if i == 0 or l.split(' frames')[0] != marks[i - 1].split(' frames')[0]]
        note('notice', 'ArmPort M3 client login stages and dialogs (patch 0046)',
             f'{len(marks)} lines; stage numbers from uiLogin.h LoginStage (0 start, 1 EULA, 3 server select, '
             f'4 NDA, 6 character select, 7 leaving). Changes:\n' + '\n'.join(changes[:30]) +
             '\nLast:\n' + '\n'.join(marks[-5:]))
    try:
        dbhost.validate_network_receipt(game.read_json(evidence / 'network-isolation.json'), network_expected)
        note('notice', 'ArmPort M3 network', 'guest ran in a private loopback-only network namespace')
    except Exception as e:  # reported, and fails the run below
        note('error', 'ArmPort M3 network', repr(e))
        code = code or 1
    # The servers' side of the login: DbServer's and MapServer's own output.
    captures = state / 'game-service-captures'
    for name in ('first-dbserver-stdout.txt', 'first-atlas-stdout.txt'):
        path = captures / name
        if path.exists():
            shutil.copyfile(path, evidence / name)
            tail = [l[:300] for l in path.read_text(errors='replace').splitlines() if l.strip()][-40:]
            note('notice', f'ArmPort M3 {name} tail', '\n'.join(tail))
    # DbServer/MapServer log files the guest captured (connection records).
    manifest = captures / 'manifest.json'
    if manifest.exists():
        files = json.loads(manifest.read_text()).get('files', {})
        logs = {n: f.get('source_relative_path') for n, f in files.items() if f.get('kind') == 'runtime_log'}
        note('notice', 'ArmPort M3 server log files', '\n'.join(f'{n}: {p}' for n, p in sorted(logs.items()))[:3500])
        versions = []
        for n, rel in sorted(logs.items()):
            if rel and 'dbserver/error' in rel:
                versions += [l[:300] for l in (captures / n).read_text(errors='replace').splitlines()
                             if 'connected with' in l or 'WrongVersion' in l or 'protocol' in l]
        note('notice', 'ArmPort M3 DbServer version checks', '\n'.join(versions[-12:]) or 'none logged')
        accounts = []
        for n, rel in sorted(logs.items()):
            if rel and ('SystemSpecs' in rel or 'dbserver/debug' in rel):
                accounts += [l[:200] for l in (captures / n).read_text(errors='replace').splitlines()
                             if 'AuthName' in l or 'successful login' in l]
        note('notice', 'ArmPort M3 DbServer logins', f"typed account {status.get('account')!r}\n" + '\n'.join(accounts[-10:]))
        for n, rel in sorted(logs.items()):
            if rel and any(k in rel.lower() for k in ('dbserver', 'connect', 'login', 'client', 'error')):
                text = (captures / n).read_text(errors='replace').splitlines()
                note('notice', f'ArmPort M3 log {rel}', '\n'.join(l[:250] for l in text[-30:]))
    for name in ('login-panel-typed', 'login-panel-after'):
        crop = evidence / 'screens' / f'crop-{name}.jpg'
        if crop.exists():
            shutil.copyfile(crop, evidence / f'{name}.jpg')
    # Contact sheet of the login steps (exported as 'ArmPort M3 steps').
    wanted = ('login-assumed', 'login-wait', 'ultra-dismissed', 'password-typed', 'character-select', 'loading', 'atlas')
    steps = []
    for key in wanted:
        hits = [p for p in shots if key in p.name] if (shots := sorted((evidence / 'screens').glob('*.png'))) else []
        if hits:
            steps.append(hits[0] if key != 'loading' else hits[-1])
    if steps:
        for size, q in (('256x192', 50), ('200x150', 40), ('160x120', 35)):
            subprocess.run(['montage', *map(str, steps), '-tile', '4x', '-geometry', size + '+2+2',
                            '-label', '%t', '-pointsize', '9', '-quality', str(q), str(evidence / 'steps.jpg')],
                           capture_output=True)
            if (evidence / 'steps.jpg').exists() and (evidence / 'steps.jpg').stat().st_size < 24000:
                break
    # A small JPEG of the in-game frame (or the last step) for screen_export.py.
    shots = sorted((evidence / 'screens').glob('*.png'))
    pick = next((Path(p) for p in (status.get('atlas_shot'), ) if p and Path(p).exists()), shots[-1] if shots else None)
    if pick:
        for q in (60, 45, 35, 25):
            subprocess.run(['convert', str(pick), '-resize', '512x400', '-quality', str(q), str(evidence / 'screen.jpg')])
            if (evidence / 'screen.jpg').stat().st_size < 24000:
                break
    error_evidence_ok = False
    try:
        errors = client_errors.inventory(client / 'armport_stdio.txt', evidence / 'client-errors.json',
                                         client / 'zone-trace.jsonl')
        assets = client_errors.asset_lookup(errors, client / 'data')
        (evidence / 'error-assets.json').write_text(json.dumps(assets, indent=2) + '\n')
        wine = atlas_wine.inventory(evidence / 'client-output.txt', client / 'zone-trace.jsonl')
        (evidence / 'wine-errors.json').write_text(json.dumps(wine, indent=2) + '\n')
        error_evidence_ok = (wine['passed'] and not errors['integrity_failures'] and errors['map_load_finished']
                             and not errors['phase_counts'].get('after_map_load', 0))
        note('notice', 'ArmPort M3 phased errors', json.dumps(dict(
            passed=error_evidence_ok, phase_counts=errors['phase_counts'],
            trace_record_count=errors['trace_records'], classes=assets['classes'],
            allowed_startup_rpc_exceptions=wine['allowed_startup_rpc_exceptions'],
            wine_failures=wine['failures'],
            integrity_failures=errors['integrity_failures'])))
    except (OSError, ValueError) as error:
        note('error', 'ArmPort M3 error evidence', str(error)[:1000])
    ok = error_evidence_ok and code == 0 and report.get('passed') is True and client_record.get('connected_on_atlas') is True \
        and client_record.get('still_connected') is True and status.get('world_rendered') is True
    note('notice' if ok else 'error', 'ArmPort M3 verdict',
         f"ARM64 client logged in through the UI, is connected on Atlas Park (DB status), rendered the zone after "
         f"{status.get('zone_load_seconds')} s and was still connected after the screenshots"
         if ok else 'M3 login to Atlas not proved (see guest result, login driver and screens)')
    return 0 if ok else 1


if __name__ == '__main__':
    try:
        rc = main()
    except Exception:
        import traceback
        note('error', 'ArmPort M3 host driver failed', traceback.format_exc())
        flush_report()
        raise
    flush_report()
    sys.exit(rc)
