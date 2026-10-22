#!/usr/bin/env python3
"""ArmPort M3 host driver: original server stack plus the ARM64 client, login
scripted on a shared X display.

Reuses the repository's qualified ARM64 game stack (tools/android/game/
host_game_smoke.py): the same PRoot guest, private loopback-only network
namespace, PostgreSQL, Wine 10 with FEX, fake-auth DbServer, Atlas MapServer
and the original TestClient that creates and saves a character. The guest
script is armport_game_guest.py, which then starts the ARM64 client (staged
by smoke_run.py --stage-only) in the same Wine. This driver runs Xvfb on the
host (the guest reaches it through the bound /tmp/.X11-unix socket file),
types the login with xdotool, finds buttons by OCR, and keeps a screenshot of
every step.

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

dbhost = game.dbhost
note, flush_report = smoke_run.note, smoke_run.flush_report
DISPLAY = ':99'


def sh(*cmd, timeout=60, check=False):
    return subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout,
                          env=dict(os.environ, DISPLAY=DISPLAY), check=check)


class Screen:
    """Screenshots and OCR-located clicks on the shared display."""

    def __init__(self, out):
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        self.count = 0
        self.log = []

    def shot(self, name):
        self.count += 1
        xwd = self.out / f'{self.count:02d}-{name}.xwd'
        png = xwd.with_suffix('.png')
        sh('xwd', '-root', '-silent', '-out', str(xwd))
        if xwd.exists():
            sh('convert', f'xwd:{xwd}', str(png))
            xwd.unlink()
        self.log.append(f'{self.count:02d} {name}')
        return png if png.exists() else None

    def words(self, png):
        """OCR words with their centres in screen pixels."""
        if not png:
            return []
        r = sh('tesseract', str(png), '-', 'tsv', timeout=120)
        found = []
        for line in r.stdout.splitlines()[1:]:
            f = line.split('\t')
            if len(f) == 12 and f[11].strip():
                left, top, w, h = map(int, f[6:10])
                found.append((f[11].strip(), left + w // 2, top + h // 2))
        return found

    def text(self, png):
        return ' '.join(w for w, _, _ in self.words(png))

    def find(self, png, *candidates):
        for word, x, y in self.words(png):
            if any(word.lower().strip('.:,') == c.lower() for c in candidates):
                return x, y
        return None

    def click(self, x, y):
        sh('xdotool', 'mousemove', str(x), str(y))
        time.sleep(0.3)
        sh('xdotool', 'click', '1')
        self.log.append(f'   click {x},{y}')

    def type(self, text):
        sh('xdotool', 'type', '--delay', '120', text)
        self.log.append(f'   type {len(text)} characters')

    def key(self, name):
        sh('xdotool', 'key', name)
        self.log.append(f'   key {name}')


def wait_for(screen, label, predicate, seconds, interval=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        png = screen.shot(label)
        value = predicate(png)
        if value:
            return png, value
        time.sleep(interval)
    return None, None


def drive_login(screen, state, status):
    """Runs in a thread: waits for the guest's client marker, then logs in."""
    started = state / 'armport-client-started.json'
    while not started.exists():
        if status.get('guest_exited'):
            return
        time.sleep(2)
    info = json.loads(started.read_text())
    status['client_started'] = True
    # Login screen: the account field label is drawn by the game's own UI.
    png, words = wait_for(screen, 'login-wait', lambda p: (lambda t: t if 'account' in t.lower() else None)(screen.text(p)),
                          900, interval=20)
    if not png:
        status['login_screen'] = False
        return
    status['login_screen'] = True
    if 'ultra' in words.lower():
        pos = screen.find(png, 'Cancel')
        if pos:
            screen.click(*pos)
        else:
            screen.key('Escape')
        time.sleep(3)
        png = screen.shot('ultra-dismissed')
    # Account and password: click just below each label (the fields sit under them).
    for label_words, value, name in ((('ACCOUNT', 'Account'), info['account'], 'account'),
                                     (('PASSWORD', 'Password'), 'armport-m3', 'password')):
        positions = [(w, x, y) for w, x, y in screen.words(png) if w.strip(':') in label_words]
        if name == 'account':
            # "ACCOUNT NAME" and "ACCOUNT PASSWORD" both start with ACCOUNT; take the upper one.
            positions.sort(key=lambda p: p[2])
        if positions:
            _, x, y = positions[0]
            screen.click(x + 40, y + 34)
        screen.key('ctrl+a')
        screen.type(value)
        time.sleep(1)
        png = screen.shot(name + '-typed')
    pos = screen.find(png, 'Log', 'Login')
    if pos:
        screen.click(*pos)
    else:
        screen.key('Return')
    status['login_sent'] = True
    # Character select: the created character's name, then Play (or Enter).
    png, _ = wait_for(screen, 'character-select',
                      lambda p: (lambda t: t if info['character'].lower() in t.lower() or 'play' in t.lower() else None)(screen.text(p)),
                      300, interval=10)
    status['character_select'] = bool(png)
    if png:
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
    # In game: wait for the guest's database confirmation, then screenshots.
    atlas = state / 'armport-atlas.json'
    deadline = time.time() + 1200
    while not atlas.exists() and time.time() < deadline and not status.get('guest_exited'):
        time.sleep(15)
        screen.shot('loading')
    if atlas.exists():
        status['atlas'] = json.loads(atlas.read_text())
        time.sleep(20)
        status['atlas_shot'] = str(screen.shot('atlas'))
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
    ap.add_argument('--timeout-seconds', type=int, default=3600)
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
    w = command.index('-w')
    command[w:w] = ['-b', f'{client}:/opt/armport-client', '-b', '/tmp/.X11-unix:/tmp/.X11-unix']
    py = command.index('/usr/bin/python3')
    command[py:py] = ['ARMPORT_CLIENT_DIR=/opt/armport-client', f'ARMPORT_DISPLAY={DISPLAY}',
                      'ARMPORT_CLIENT_SECONDS=1500']
    command, env, network_expected = dbhost.isolate_command(command, evidence=evidence, proot=proot, work=work)

    xvfb = subprocess.Popen(['Xvfb', DISPLAY, '-screen', '0', '1280x800x24', '-nolisten', 'tcp', '+extension', 'GLX'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    screen = Screen(evidence / 'screens')
    state = work / 'state'
    status = {}
    driver = threading.Thread(target=drive_login, args=(screen, state, status), daemon=True)
    driver.start()

    log_path = evidence / 'host-game.log'
    report_path = state / 'latest-report.json'
    code = None
    with log_path.open('w') as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=a.timeout_seconds + 120)
        except subprocess.TimeoutExpired:
            note('error', 'ArmPort M3 guest', 'timed out: ' + dbhost.stop_guest(process, state))
    status['guest_exited'] = True
    driver.join(timeout=60)
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
    note('notice', 'ArmPort M3 ARM64 client', json.dumps({k: v for k, v in client_record.items()
                                                          if k != 'client_output_tail'}, indent=1)[:3500])
    if client_record.get('client_output_tail'):
        note('notice', 'ArmPort M3 client output tail', client_record['client_output_tail'][-3500:])
    note('notice', 'ArmPort M3 login driver', json.dumps(status, indent=1)[:1500] + '\n' + '\n'.join(screen.log[-60:]))
    smoke_run.report_stdio(client / 'armport_stdio.txt', 'ArmPort M3 client stdio')
    try:
        dbhost.validate_network_receipt(game.read_json(evidence / 'network-isolation.json'), network_expected)
        note('notice', 'ArmPort M3 network', 'guest ran in a private loopback-only network namespace')
    except Exception as e:  # reported, and fails the run below
        note('error', 'ArmPort M3 network', repr(e))
        code = code or 1
    # A small JPEG of the in-game frame (or the last step) for screen_export.py.
    shots = sorted((evidence / 'screens').glob('*.png'))
    pick = next((Path(p) for p in (status.get('atlas_shot'), ) if p and Path(p).exists()), shots[-1] if shots else None)
    if pick:
        for q in (60, 45, 35, 25):
            subprocess.run(['convert', str(pick), '-resize', '512x400', '-quality', str(q), str(evidence / 'screen.jpg')])
            if (evidence / 'screen.jpg').stat().st_size < 24000:
                break
    ok = code == 0 and report.get('passed') is True and client_record.get('connected_on_atlas') is True \
        and client_record.get('still_connected') is True
    note('notice' if ok else 'error', 'ArmPort M3 verdict',
         'ARM64 client logged in through the UI and is connected on Atlas Park (DB status), still connected after the screenshots'
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
