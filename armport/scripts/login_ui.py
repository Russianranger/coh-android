#!/usr/bin/env python3
"""Login screen automation shared by the M3 server run (armport_game_host.py)
and the M2 boot test's login probe (smoke_run.py --login-probe): screenshots,
OCR-located clicks and typing on the Xvfb display, with the control positions
measured from a real frame as fallback."""
import os
import json
import re
import subprocess
import time

DISPLAY = ':99'

QA_NOTICE = ('You are seeing pop-up errors because you have Access Level (9) or you are on a QA server. '
             'These will not be seen by customers.')


def dialogs_clear(path):
    """Fail closed on incomplete or malformed ordered traces, including torn writes."""
    pending = {}
    seen = False
    try:
        with path.open(encoding='utf-8') as source:
            for line in source:
                if not line.endswith('\n'):
                    return False
                row = json.loads(line)
                if (not isinstance(row, dict) or not isinstance(row.get('stage'), str)
                        or not isinstance(row.get('text'), str)
                        or type(row.get('tid')) is not int or row['tid'] <= 0):
                    return False
                seen = True
                stage = row['stage']
                if stage == 'client.fatal':
                    return False
                if stage.startswith('dialog.'):
                    if stage not in ('dialog.alert.begin', 'dialog.alert.done',
                                     'dialog.error.begin', 'dialog.error.done'):
                        return False
                    kind, action = stage.rsplit('.', 1)
                    key = (row['tid'], kind)
                    count = pending.get(key, 0)
                    if action == 'done' and not count:
                        return False
                    pending[key] = count + (1 if action == 'begin' else -1)
    except (OSError, ValueError, UnicodeError):
        return False
    return seen and not any(pending.values())


def character_select_from_log(path, zone_trace):
    """Use stdio only for the current UI stage; isolated trace owns dialog state."""
    try:
        with path.open('rb') as source:
            source.seek(0, 2)
            source.seek(max(0, source.tell() - 512 * 1024))
            text = source.read().decode('utf-8', errors='replace')
    except OSError:
        return False
    stages = re.findall(r'^ArmPort login: stage (\d+) select (\d+) player (-?\d+) of (\d+) ', text, re.M)
    if not stages:
        return False
    stage, selected, player, count = map(int, stages[-1])
    return stage == 6 and selected == 1 and 0 <= player < count and dialogs_clear(zone_trace)


def character_select_frame(path, zone_trace):
    """A complete latest stage sample for bounded Next retries; no stale-stage fallback."""
    try:
        with path.open('rb') as source:
            source.seek(0, 2)
            source.seek(max(0, source.tell() - 512 * 1024))
            text = source.read().decode('utf-8', errors='replace')
    except OSError:
        return None
    lines = [line for line in text.splitlines(keepends=True)
             if line.startswith('ArmPort login: stage ')]
    if not lines:
        return None
    sample = re.fullmatch(r'ArmPort login: stage 6 select 1 player (\d+) of (\d+) timeout 0 frames (\d+)\r?\n', lines[-1])
    if not sample or not dialogs_clear(zone_trace):
        return None
    player, count, frame = map(int, sample.groups())
    return frame if player < count else None


def pending_qa_notice(stdio):
    """Only the known informational notice, not arbitrary errors or asserts."""
    pending = None
    for event in re.finditer(r'^ArmPort zone: \d+ (dialog\.(?:alert|error)\.(?:begin|done)|client\.fatal)\s*([^\r\n]*)',
                             stdio, re.M):
        kind, detail = event.groups()
        if kind == 'client.fatal':
            return False
        pending = detail.split(' tid=')[0] if kind == 'dialog.alert.begin' else None
    return pending is not None and ' '.join(pending.split()) == QA_NOTICE


def acknowledge_qa_notice(screen, stdio, pids, status):
    """Press the original dialog's OK button via Return; preserve all evidence.

    msgAlert uses ErrorDlg with the default title Program Error (winutil.c).
    Require its exact title AND the one mapped client process on our X display.
    xdotool defaults to --any: without --all it also returns the game window.
    Never dismiss a texture/error/crash dialog merely because it has that title.
    """
    attempts = status.setdefault('qa_notice_actions', [])
    pending = pending_qa_notice(stdio)
    status['qa_notice_last_check'] = {'pids': pids, 'pending_exact_notice': pending,
                                     'attempts': len(attempts)}
    if len(attempts) >= 3 or len(pids) != 1 or not pending:
        return False
    result = sh('xdotool', 'search', '--all', '--onlyvisible', '--pid', str(pids[0]),
                '--name', '^Program Error$')
    windows = result.stdout.split()
    status['qa_notice_last_check'].update(search_exit=result.returncode,
        windows=windows[:8], search_stderr=getattr(result, 'stderr', '')[:300])
    if result.returncode or len(windows) != 1 or not windows[0].isdigit():
        return False
    before = screen.shot('qa-notice-before')
    focused = sh('xdotool', 'windowfocus', '--sync', windows[0])
    action = {'window': windows[0], 'pid': pids[0], 'before': str(before),
              'focus_exit': focused.returncode, 'return_sent': False}
    attempts.append(action)
    if focused.returncode:
        return False
    screen.key('Return')
    action['return_sent'] = True
    action['after'] = str(screen.shot('qa-notice-after'))
    return True


def sh(*cmd, timeout=60, check=False):
    return subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout,
                          env=dict(os.environ, DISPLAY=DISPLAY), check=check)


def owned_client_window(pids):
    """Find a single visible game-sized window without relying on its map title."""
    if len(pids) != 1 or type(pids[0]) is not int or pids[0] <= 0:
        return None
    result = sh('xdotool', 'search', '--all', '--onlyvisible', '--pid', str(pids[0]),
                '--class', r'^cityofheroes\.exe$')
    windows = result.stdout.split()
    if result.returncode or not windows or len(windows) > 16 or any(not w.isdigit() for w in windows):
        return None
    candidates = []
    for window in set(windows):
        result = sh('xdotool', 'getwindowgeometry', '--shell', window)
        if result.returncode:
            return None
        values = dict(line.split('=', 1) for line in result.stdout.split() if '=' in line)
        try:
            if int(values['WINDOW']) != int(window):
                return None
            x, y, width, height = (int(values[key]) for key in ('X', 'Y', 'WIDTH', 'HEIGHT'))
        except (KeyError, ValueError):
            return None
        if x >= 0 and y >= 0 and width >= 640 and height >= 480:
            candidates.append((x, y, width, height))
    return candidates[0] if len(candidates) == 1 else None


class Screen:
    """Screenshots and OCR-located clicks on the shared display."""

    def __init__(self, out):
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        self.count = 0
        self.log = []
        self._words_key = None
        self._words_value = []

    def shot(self, name, tries=4):
        """Screenshot; the client redraws at about 60 fps and a capture can
        catch a frame half presented, so the most detailed of a few quick
        captures is kept (largest PNG)."""
        self.count += 1
        png = self.out / f'{self.count:02d}-{name}.png'
        best = None
        for i in range(tries):
            xwd = self.out / f'grab{i}.xwd'
            cand = self.out / f'grab{i}.png'
            sh('xwd', '-root', '-silent', '-out', str(xwd))
            if xwd.exists():
                sh('convert', f'xwd:{xwd}', str(cand))
                xwd.unlink()
            if cand.exists() and (best is None or cand.stat().st_size > best.stat().st_size):
                best = cand
            time.sleep(0.05)
        if best:
            best.rename(png)
        for left in self.out.glob('grab*.png'):
            left.unlink()
        self.log.append(f'{self.count:02d} {name}')
        return png if png.exists() else None

    def words(self, png):
        """OCR words with their centres in screen pixels. As M2's smoke
        OCR: 3x scale and sparse-text mode for the UI's small fonts."""
        if not png:
            return []
        stat = png.stat()
        key = (str(png), stat.st_mtime_ns, stat.st_size)
        if self._words_key == key:
            return self._words_value
        big = png.with_name(png.stem + '-x3.png')
        sh('convert', str(png), '-resize', '300%', str(big), timeout=120)
        r = sh('tesseract', str(big), '-', '--psm', '11', 'tsv', timeout=180)
        big.unlink(missing_ok=True)
        found = []
        for line in r.stdout.splitlines()[1:]:
            f = line.split('\t')
            if len(f) == 12 and f[11].strip():
                left, top, w, h = map(int, f[6:10])
                found.append((f[11].strip(), (left + w // 2) // 3, (top + h // 2) // 3))
        self._words_key, self._words_value = key, found
        return found

    def text(self, png):
        return ' '.join(w for w, _, _ in self.words(png))

    def find(self, png, *candidates):
        for word, x, y in self.words(png):
            if any(word.lower().strip('.:,') == c.lower() for c in candidates):
                return x, y
        return None

    def click(self, x, y, hold=0.15):
        # The game reads the mouse once per frame (DirectInput); at software-
        # rendering frame rates an instant press and release can fall between
        # two frames, so the button is held down.
        sh('xdotool', 'mousemove', str(x), str(y))
        time.sleep(0.5)
        sh('xdotool', 'mousedown', '1')
        time.sleep(hold)
        sh('xdotool', 'mouseup', '1')
        self.log.append(f'   click {x},{y} (held {hold}s)')

    # The game reads the keyboard once per frame (DirectInput); xdotool's
    # instant press and release can fall between two frames and be lost, so
    # every key is held down for a few frames.
    KEYSYMS = {'-': 'minus', '_': 'underscore', '.': 'period', ' ': 'space'}

    def press(self, keysym, hold=0.06):
        sh('xdotool', 'keydown', keysym)
        time.sleep(hold)
        sh('xdotool', 'keyup', keysym)
        time.sleep(0.08)

    def type(self, text):
        for ch in text:
            self.press(self.KEYSYMS.get(ch, ch))
        self.log.append(f'   type {len(text)} characters (held keys)')

    def key(self, name):
        if '+' in name:            # chords such as ctrl+a
            mod, k = name.split('+', 1)
            sh('xdotool', 'keydown', mod)
            self.press(k)
            sh('xdotool', 'keyup', mod)
        else:
            self.press(name)
        self.log.append(f'   key {name}')

    def crop(self, png, name, box):
        """Full-resolution crop (x, y, w, h relative to the client window)."""
        win = self.window()
        if not png or not win:
            return None
        x, y, w, h = box
        out = self.out / f'crop-{name}.jpg'
        sh('convert', str(png), '-crop', f'{w}x{h}+{win[0] + x}+{win[1] + y}', '+repage', '-quality', '45', str(out))
        return out if out.exists() else None

    def window(self):
        """Client window origin and size, or None."""
        r = sh('xdotool', 'search', '--name', 'City of Heroes', 'getwindowgeometry', '--shell')
        geo = dict(l.split('=', 1) for l in r.stdout.split() if '=' in l)
        try:
            return int(geo['X']), int(geo['Y']), int(geo['WIDTH']), int(geo['HEIGHT'])
        except (KeyError, ValueError):
            return None


# Login screen layout in the 1024x768 client window, measured from the M3
# frame of run 39803404449 (used when OCR does not find a control).
LAYOUT = {'ultra_cancel': (512, 495), 'account_field': (849, 307),
          'password_field': (849, 420), 'login_button': (899, 486),
          # First server row: uiLogin.c SERVER_X 660, SERVER_LIST_Y 266, row
          # 328 x 30 in the 1024x768 design space (scale 1 at this size).
          'server_row': (824, 281),
          # Character select's Next arrow (uiHybridMenu.c drawHybridNext:
          # x = 1024 - HYBRID_NEXT_X_OFFSET 55, y = 768 - HYBRID_NEXT_Y_OFFSET 27).
          'enter_world': (969, 741)}


def at(screen, name):
    win = screen.window()
    if not win:
        return None
    x, y = LAYOUT[name]
    return win[0] + x * win[2] // 1024, win[1] + y * win[3] // 768


def wait_for(screen, label, predicate, seconds, interval=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        png = screen.shot(label)
        value = predicate(png)
        if value:
            return png, value
        time.sleep(interval)
    return None, None

def login(screen, account, password, status, after=lambda label: None, wait_seconds=600):
    """Dismiss the Ultra Mode prompt, type account and password, press Log In.
    OCR finds the controls when it can; otherwise the measured LAYOUT is used.
    after(label) is called 2 s and 10 s after Log In. Returns True once
    Log In was pressed."""
    # Login screen: the account field label is drawn by the game's own UI.
    png, words = wait_for(screen, 'login-wait', lambda p: (lambda t: t if 'account' in t.lower() else None)(screen.text(p)),
                          wait_seconds, interval=20)
    if not png:
        # No OCR match: go by the measured layout once the window exists.
        png = screen.shot('login-assumed')
        if not screen.window():
            status['login_screen'] = False
            return False
        words = 'ultra'
        status['login_by_layout'] = True
    status['login_screen'] = True
    if 'ultra' in words.lower():
        pos = screen.find(png, 'Cancel') or at(screen, 'ultra_cancel')
        if pos:
            screen.click(*pos)
        else:
            screen.key('Escape')
        time.sleep(3)
        png = screen.shot('ultra-dismissed')
        status['ultra_prompt_left'] = 'ultra' in screen.text(png).lower()
    # Account and password by keyboard: the account field takes focus (one
    # click on it), Tab moves to the password field, Return logs in.
    positions = sorted(((w, x, y) for w, x, y in screen.words(png) if w.strip(':') in ('ACCOUNT', 'Account')),
                       key=lambda p: p[2])
    pos = (positions[0][1] + 40, positions[0][2] + 34) if positions else at(screen, 'account_field')
    if pos:
        screen.click(*pos)
    screen.key('ctrl+a')
    screen.type(account)
    time.sleep(1)
    png = screen.shot('account-typed')
    screen.key('Tab')
    time.sleep(0.5)
    screen.type(password)
    time.sleep(1)
    png = screen.shot('password-typed')
    # The login panel (fields and buttons) at full resolution, before and after Log In.
    panel = (560, 260, 460, 280)
    status['crop_before'] = str(screen.crop(png, 'login-panel-typed', panel))
    screen.key('Return')
    status['login_sent'] = "Return"
    time.sleep(2)
    after('2s after Log In')
    time.sleep(8)
    status['crop_after'] = str(screen.crop(screen.shot('after-login'), 'login-panel-after', panel))
    after('10s after Log In')
    return True


def after_login(screen, status, rounds=20, interval=15, done=lambda png: False, after=lambda label: None):
    """Screens between Log In and the character list (uiLogin.c): the EULA
    and NDA agreements (Agree) and the server list, where the single -db
    entry is named 127.0.0.1 and clicking it calls loginToDbServer. Stops
    when done(png) is true. Returns the last screenshot."""
    png = None
    for n in range(rounds):
        time.sleep(interval)
        png = screen.shot(f'post-login-{n:02d}')
        if done(png):
            return png
        words = screen.words(png)
        status.setdefault('post_login_text', []).append(' '.join(w for w, _, _ in words)[:300])
        agree = next(((x, y) for w, x, y in words if w.lower().strip('.:,') in ('agree', 'accept')), None)
        server = next(((x, y) for w, x, y in words if '127.0.0' in w), None)
        if not server and not agree and n < 3 and status.get('server_clicked', 0) < 3:
            # Return leads to Select a Server (probe frames); OCR does not
            # read its heading reliably, so the first row is clicked by layout.
            server = at(screen, 'server_row')
        if agree:
            status['agreed'] = status.get('agreed', 0) + 1
            screen.click(*agree)
        elif server:
            status['server_clicked'] = status.get('server_clicked', 0) + 1
            screen.click(*server)
            after(f'server clicked ({n})')
    return png
