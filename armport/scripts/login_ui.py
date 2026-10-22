#!/usr/bin/env python3
"""Login screen automation shared by the M3 server run (armport_game_host.py)
and the M2 boot test's login probe (smoke_run.py --login-probe): screenshots,
OCR-located clicks and typing on the Xvfb display, with the control positions
measured from a real frame as fallback."""
import os
import subprocess
import time

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
        """OCR words with their centres in screen pixels. As M2's smoke
        OCR: 3x scale and sparse-text mode for the UI's small fonts."""
        if not png:
            return []
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

    def type(self, text):
        sh('xdotool', 'type', '--delay', '120', text)
        self.log.append(f'   type {len(text)} characters')

    def key(self, name):
        sh('xdotool', 'key', name)
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
          'password_field': (849, 420), 'login_button': (899, 486)}


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
    # Account and password: click just below each label (the fields sit under them).
    for label_words, value, name in ((('ACCOUNT', 'Account'), account, 'account'),
                                     (('PASSWORD', 'Password'), password, 'password')):
        positions = [(w, x, y) for w, x, y in screen.words(png) if w.strip(':') in label_words]
        if name == 'account':
            # "ACCOUNT NAME" and "ACCOUNT PASSWORD" both start with ACCOUNT; take the upper one.
            positions.sort(key=lambda p: p[2])
        if positions:
            _, x, y = positions[0]
            screen.click(x + 40, y + 34)
        else:
            pos = at(screen, name + '_field')
            if pos:
                screen.click(*pos)
        screen.key('ctrl+a')
        screen.type(value)
        time.sleep(1)
        png = screen.shot(name + '-typed')
    # The login panel (fields and buttons) at full resolution, before and after Log In.
    panel = (560, 260, 460, 280)
    status['crop_before'] = str(screen.crop(png, 'login-panel-typed', panel))
    pos = screen.find(png, 'Log', 'Login') or at(screen, 'login_button')
    if pos:
        screen.click(*pos)
    else:
        screen.key('Return')
    status['login_sent'] = True
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
        if agree:
            status['agreed'] = status.get('agreed', 0) + 1
            screen.click(*agree)
        elif server:
            status['server_clicked'] = status.get('server_clicked', 0) + 1
            screen.click(*server)
            after(f'server clicked ({n})')
    return png
