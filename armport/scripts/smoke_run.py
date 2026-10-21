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


def screenshot_summary(display, path):
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
    ap.add_argument('--data', required=True, type=Path)
    ap.add_argument('--runtime', required=True, type=Path)
    ap.add_argument('--llvm-mingw', required=True, type=Path)
    ap.add_argument('--wine', required=True, type=Path, help='directory with wine, wineserver')
    ap.add_argument('--seconds', type=int, default=180)
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
    dlls = imports(exe, a.llvm_mingw)
    sysroot_bin = a.llvm_mingw / 'aarch64-w64-mingw32' / 'bin'
    copied = []
    for d in dlls:
        src = sysroot_bin / d
        if src.exists():
            shutil.copy2(src, rt / d)
            copied.append(d)
    (rt / 'data').symlink_to(a.data.resolve(), target_is_directory=True)
    note('notice', 'ArmPort M2 smoke imports', f'{", ".join(dlls)}\ncopied from llvm-mingw: {", ".join(copied) or "none"}')

    display = ':99'
    xvfb = subprocess.Popen(['Xvfb', display, '-screen', '0', '1280x800x24', '-nolisten', 'tcp'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    env = dict(os.environ, DISPLAY=display, WINEDEBUG='err+all,fixme-all,+seh',
               WINEDLLOVERRIDES='mscoree,mshtml=')
    wine = str(a.wine / 'wine')
    subprocess.run([wine, 'wineboot', '-i'], env=env, capture_output=True, timeout=300)
    before = {p for p in rt.rglob('*') if not str(p).startswith(str(rt / 'data'))}

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

    lines = log.read_text(errors='replace').splitlines()
    exc = [l for l in lines if 'exception' in l.lower() or 'unhandled' in l.lower() or 'err:' in l][:40]
    if exc:
        note('warning', 'ArmPort M2 smoke exceptions', '\n'.join(exc[:30]))
    tail = [l[:300] for l in lines if '+seh' not in l][-75:]
    for i, c in enumerate(chunks(tail)):
        note('notice', f'ArmPort M2 smoke output {i}', c)

    new = [p for p in rt.rglob('*') if p.is_file() and p not in before
           and not str(p).startswith(str(rt / 'data')) and p.suffix.lower() in ('.log', '.txt')]
    for p in new[:6]:
        t = p.read_text(errors='replace').splitlines()[-30:]
        note('notice', f'ArmPort M2 smoke log {p.relative_to(rt)}', '\n'.join(l[:300] for l in t))
    print('\n'.join(lines[-200:]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
