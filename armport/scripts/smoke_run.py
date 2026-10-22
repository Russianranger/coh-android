#!/usr/bin/env python3
"""M2 smoke run: start the ARM64 CityOfHeroes.exe under the app's ARM64 Wine.

Stages a runtime directory (exe, the llvm-mingw runtime DLLs it imports, and
data/ as a link to the text data), runs the client on an Xvfb display for a
bounded time, and reports what happened as GitHub annotations: exit status or
timeout, Wine exceptions, top-level window titles, a screenshot summary and
the tail of the output and any log files written. Observational: the exit code
is 0 unless the script itself cannot run.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def note(kind, title, text):
    text = text.replace('%', '%25').replace('\r', '').replace('\n', '%0A')
    print(f'::{kind} title={title}::{text[:3800]}', flush=True)


def chunks(lines, n=25):
    for i in range(0, len(lines), n):
        yield '\n'.join(lines[i:i + n])


def imports(exe, llvm):
    out = subprocess.run([str(llvm / 'bin' / 'llvm-readobj'), '--coff-imports', str(exe)],
                         capture_output=True, text=True).stdout
    return sorted({l.split(':', 1)[1].strip() for l in out.splitlines()
                   if l.strip().startswith('Name:') and l.strip().lower().endswith('.dll')})


def ocr(path):
    """Screen text via ImageMagick + tesseract (3x scale for small dialog fonts)."""
    try:
        png = path.with_suffix('.png')
        subprocess.run(['convert', f'xwd:{path}', '-resize', '300%', str(png)],
                       capture_output=True, timeout=120)
        r = subprocess.run(['tesseract', str(png), '-', '--psm', '11'],
                           capture_output=True, text=True, timeout=120)
        words = ' '.join(r.stdout.split())
        return words or '(no text found)'
    except Exception as e:
        return f'ocr failed: {e!r}'


def merge_tree(src, dst):
    """Overlay src onto dst with symlinks, splitting a linked directory only
    where two roots both have it. Earlier roots win for files."""
    if not dst.exists() and not dst.is_symlink():
        dst.symlink_to(src, target_is_directory=src.is_dir())
        return
    if not (src.is_dir() and dst.is_dir()):
        return
    if dst.is_symlink():
        target = dst.resolve()
        dst.unlink()
        dst.mkdir()
        for child in target.iterdir():
            (dst / child.name).symlink_to(child, target_is_directory=child.is_dir())
    for child in src.iterdir():
        merge_tree(child, dst / child.name)


def screenshot_summary(display, path):
    try:
        return _screenshot_summary(display, path)
    except Exception as e:  # observational only
        return f'screenshot failed: {e!r}'


def _screenshot_summary(display, path):
    r = subprocess.run(['xwd', '-root', '-silent', '-display', display, '-out', str(path)],
                       capture_output=True)
    if r.returncode or not path.exists():
        return 'no screenshot'
    data = path.read_bytes()
    # xwd header: header_size at offset 0 (big endian); 32-bit pixels at 24 bpp depth.
    hsize = int.from_bytes(data[0:4], 'big')
    ncolors = int.from_bytes(data[76:80], 'big')
    pixels = data[hsize + ncolors * 12:]
    sample = pixels[::4 * 97]
    nonblack = sum(1 for b in sample if b) / max(1, len(sample))
    distinct = len(set(pixels[i:i + 3] for i in range(0, min(len(pixels), 4 * 200000), 4 * 13)))
    return f'nonzero bytes {nonblack:.1%}, distinct colors (sampled) {distinct}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', required=True, type=Path)
    ap.add_argument('--data', required=True, type=Path, action='append',
                    help='data root; repeat to overlay several (merged with symlinks)')
    ap.add_argument('--runtime', required=True, type=Path)
    ap.add_argument('--llvm-mingw', type=Path, help='for the import list and runtime DLLs')
    ap.add_argument('--wine', required=True, type=Path, help='directory with wine, wineserver')
    ap.add_argument('--seconds', type=int, default=180)
    ap.add_argument('--winedebug', default='err+all,fixme-all,+dialog,+class,+win')
    ap.add_argument('--cg-dir', type=Path, help='precompiled <key>.arb files for the Cg stand-in')
    ap.add_argument('--requests-out', type=Path, help='copy recorded Cg requests here')
    ap.add_argument('args', nargs='*')
    a = ap.parse_args()

    exes = list(a.build.rglob('CityOfHeroes.exe'))
    if not exes:
        note('error', 'ArmPort M2 smoke', 'CityOfHeroes.exe not found')
        return 1
    exe = exes[0]
    rt = a.runtime
    rt.mkdir(parents=True, exist_ok=False)
    shutil.copy2(exe, rt / exe.name)
    copied = []
    for dll in exe.parent.glob('*.dll'):  # runtime DLLs shipped next to the exe
        shutil.copy2(dll, rt / dll.name)
        copied.append(dll.name)
    if a.llvm_mingw:
        dlls = imports(exe, a.llvm_mingw)
        sysroot_bin = a.llvm_mingw / 'aarch64-w64-mingw32' / 'bin'
        for d in dlls:
            if d not in copied and (sysroot_bin / d).exists():
                shutil.copy2(sysroot_bin / d, rt / d)
                copied.append(d)
        note('notice', 'ArmPort M2 smoke imports', ', '.join(dlls))
    note('notice', 'ArmPort M2 smoke runtime DLLs', ', '.join(copied) or 'none')
    for root in a.data:
        merge_tree(root.resolve(), rt / 'data')
    cg = rt / 'armport_cg'
    cg.mkdir()
    arb = sorted(a.cg_dir.glob('*.arb')) if a.cg_dir and a.cg_dir.is_dir() else []
    for f in arb:
        shutil.copy2(f, cg / f.name)
    note('notice', 'ArmPort M2 smoke Cg programs', f'{len(arb)} precompiled ARB programs staged')

    display = ':99'
    xvfb = subprocess.Popen(['Xvfb', display, '-screen', '0', '1280x800x24', '-nolisten', 'tcp'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    env = dict(os.environ, DISPLAY=display, WINEDEBUG=a.winedebug,
               WINEDLLOVERRIDES='mscoree,mshtml=')
    wine = str(a.wine / 'wine')
    try:
        boot = subprocess.run([wine, 'wineboot', '-i'], env=env, capture_output=True, timeout=300)
        note('notice', 'ArmPort M2 smoke wineboot', f'exit {boot.returncode}')
    except subprocess.TimeoutExpired:
        note('warning', 'ArmPort M2 smoke wineboot', 'timed out after 300s')
    before = {p for p in rt.iterdir()}

    log = rt.parent / 'smoke-output.txt'
    start = time.time()
    with open(log, 'wb') as out:
        proc = subprocess.Popen([wine, str(rt / exe.name)] + a.args, cwd=rt, env=env,
                                stdout=out, stderr=subprocess.STDOUT)
        shot_mid = None
        titles = ''
        try:
            proc.wait(timeout=min(60, a.seconds))
        except subprocess.TimeoutExpired:
            pass
        if proc.poll() is None:
            shot_mid = screenshot_summary(display, rt.parent / 'shot60.xwd')
            titles = subprocess.run(['xwininfo', '-root', '-tree', '-display', display],
                                    capture_output=True, text=True).stdout
            try:
                proc.wait(timeout=max(0, a.seconds - 60))
            except subprocess.TimeoutExpired:
                pass
        elapsed = time.time() - start
        running = proc.poll() is None
        shot_end = screenshot_summary(display, rt.parent / 'shotend.xwd') if running else None
        if running:
            titles = subprocess.run(['xwininfo', '-root', '-tree', '-display', display],
                                    capture_output=True, text=True).stdout or titles
            proc.kill()
    subprocess.run([str(a.wine / 'wineserver'), '-k'], env=env, capture_output=True)
    xvfb.kill()

    status = f'still running after {elapsed:.0f}s (killed)' if running else f'exited with {proc.returncode} after {elapsed:.0f}s'
    named = [l.strip() for l in titles.splitlines() if '"' in l and 'has no name' not in l]
    note('notice', 'ArmPort M2 smoke status',
         f'{status}\nscreenshot @60s: {shot_mid}\nscreenshot @end: {shot_end}\nwindows:\n' + '\n'.join(named[:15]))
    for name in ('shot60.xwd', 'shotend.xwd'):
        if (rt.parent / name).exists():
            note('notice', f'ArmPort M2 smoke screen text {name}', ocr(rt.parent / name))

    lines = log.read_text(errors='replace').splitlines()
    dialog = [l[:300] for l in lines if 'trace:dialog' in l and ('L"' in l or '"' in l)]
    if dialog:
        note('notice', 'ArmPort M2 smoke dialog text', '\n'.join(dialog[:40]))
    # Window creation by the client's own class, with what follows on that thread.
    win = []
    for i, l in enumerate(lines):
        if 'CrypticWindow' in l and ('trace:win' in l or 'trace:class' in l):
            tid = l.split(':', 1)[0]
            win.append(l[:300])
            win += [m[:300] for m in lines[i + 1:i + 400] if m.startswith(tid + ':')
                    and ('trace:win' in m or 'trace:class' in m or 'err:' in m or 'warn:' in m)][:25]
            if len(win) > 60:
                break
    if win:
        note('notice', 'ArmPort M2 smoke window trace', '\n'.join(win[:60]))
    # Text the client put into windows and dialog controls (error messages).
    texts = []
    for l in lines:
        if 'set_window_text' in l and 'Default IME' not in l:
            t = l.split('set_window_text', 1)[1].strip()
            if t not in texts and t not in ('L""',):
                texts.append(t)
    if texts:
        note('warning', 'ArmPort M2 smoke window text', '\n'.join(t[:600] for t in texts[:30]))
    exc = [l for l in lines if 'exception' in l.lower() or 'unhandled' in l.lower() or 'err:' in l][:40]
    if exc:
        note('warning', 'ArmPort M2 smoke exceptions', '\n'.join(exc[:30]))
    tail = [l[:300] for l in lines if 'trace:' not in l][-75:]
    for i, c in enumerate(chunks(tail)):
        note('notice', f'ArmPort M2 smoke output {i}', c)

    new = [p for top in rt.iterdir() if top not in before and top.name != 'data'
           for p in ([top] if top.is_file() else top.rglob('*'))
           if p.is_file() and p.suffix.lower() in ('.log', '.txt')]
    for p in new[:6]:
        t = p.read_text(errors='replace').splitlines()[-30:]
        note('notice', f'ArmPort M2 smoke log {p.relative_to(rt)}', '\n'.join(l[:300] for l in t))
    reqs = sorted((cg / 'requests').glob('*.req')) if (cg / 'requests').is_dir() else []
    note('notice', 'ArmPort M2 smoke Cg requests', f'{len(reqs)} programs had no precompiled ARB assembly')
    if a.requests_out:
        a.requests_out.mkdir(parents=True, exist_ok=True)
        for f in reqs:
            shutil.copy2(f, a.requests_out / f.name)
    print('\n'.join(lines[-200:]))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        import traceback
        note('error', 'ArmPort M2 smoke script failed', traceback.format_exc())
        raise
