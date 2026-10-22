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
import re
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


# GitHub keeps only about 10 annotations of each kind per step, so reports are
# buffered and emitted at the end as a few large annotations per kind.
_REPORT = {'notice': [], 'warning': [], 'error': []}


def note(kind, title, text):
    _REPORT[kind].append(f'### {title}\n{text.strip()}')
    print(f'--- {title}\n{text}', flush=True)


def flush_report(limit=3800, per_kind=9):
    for kind in ('error', 'warning', 'notice'):
        pieces, cur = [], ''
        for entry in _REPORT[kind]:
            entry = entry[:limit]
            if len(cur) + len(entry) + 1 > limit:
                pieces.append(cur)
                cur = ''
            cur += entry + '\n'
        if cur:
            pieces.append(cur)
        for i, piece in enumerate(pieces[:per_kind]):
            text = piece.replace('%', '%25').replace('\r', '').replace('\n', '%0A')
            print(f'::{kind} title=ArmPort M2 smoke {kind} {i + 1}/{min(len(pieces), per_kind)}::{text}', flush=True)
        _REPORT[kind].clear()


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
    """Overlay src onto dst as hard links (real directories, no symlinks, so the
    client's directory scans see ordinary files). Earlier roots win for files."""
    for dirpath, dirnames, filenames in os.walk(src, followlinks=True):
        rel = os.path.relpath(dirpath, src)
        target = dst / rel if rel != '.' else dst
        target.mkdir(parents=True, exist_ok=True)
        for f in filenames:
            out = target / f
            if out.exists():
                continue
            try:
                os.link(os.path.join(dirpath, f), out)
            except OSError:
                shutil.copy2(os.path.join(dirpath, f), out)

def window_texts(lines):
    texts = []
    for l in lines:
        if 'set_window_text' in l and 'Default IME' not in l:
            t = l.split('set_window_text', 1)[1].strip()
            if t not in texts and t not in ('L""', '(null)', 'L"WineAppBar"'):
                texts.append(t)
    return texts


def createbins(a, rt, exe, env, wine):
    """Build the client's .bin files from the text data (as the x86 tools do)."""
    log = rt.parent / 'createbins-output.txt'
    stdio = rt / 'armport_stdio_createbins.txt'
    binner = rt / exe.name
    if a.createbins_build:
        dev = next(a.createbins_build.rglob('CityOfHeroes.exe'))
        binner = rt / 'CityOfHeroes-createbins.exe'
        shutil.copy2(dev, binner)
    start = time.time()
    with open(log, 'wb') as out:
        p = subprocess.Popen([wine, str(binner), '-createbins', '-nogui', '1', '-verbose', '1'],
                             cwd=rt, env=dict(env, ARMPORT_STDIO_LOG=stdio.name,
                                              WINEDEBUG=a.winedebug + ',+seh'),
                             stdout=out, stderr=subprocess.STDOUT)
        status = 'timed out (killed)'
        while time.time() - start < a.createbins_seconds:
            try:
                p.wait(timeout=20)
                status = f'exited with {p.returncode}'
                break
            except subprocess.TimeoutExpired:
                pass
            # A modal error dialog waits forever; stop once one appears.
            if b'L"Fatal Error"' in log.read_bytes()[-2_000_000:]:
                time.sleep(5)
                status = 'stopped at a Fatal Error dialog'
                break
        if p.poll() is None:
            p.kill()
    subprocess.run([str(a.wine / 'wineserver'), '-k'], env=env, capture_output=True)
    bins = sorted((rt / 'data' / 'bin').glob('*.bin')) if (rt / 'data' / 'bin').is_dir() else []
    if a.bins_out and bins:
        shutil.copytree(rt / 'data' / 'bin', a.bins_out, dirs_exist_ok=True)
    lines = log.read_text(errors='replace').splitlines()
    texts = window_texts(lines)
    note('notice', 'ArmPort M2 createbins',
         f'{status} after {time.time() - start:.0f}s; {len(bins)} files in data/bin\n'
         + ', '.join(b.name for b in bins[:80]))
    if texts:
        note('warning', 'ArmPort M2 createbins window text', '\n'.join(t[:600] for t in texts[:20]))
    report_stdio(stdio, 'ArmPort M2 createbins client output')
    # The calls leading to each process exit (relay trace, same thread).
    # The client is the process that loaded the game's own DLL imports.
    exits = [i for i, l in enumerate(lines) if 'Call KERNEL32.ExitProcess' in l
             or 'Call ucrtbase.exit(' in l or 'Call ucrtbase._exit(' in l
             or 'Call ntdll.RtlExitUserProcess' in l]
    shown = set()
    for end_i in exits:
        tid = lines[end_i].split(':', 1)[0]
        if tid in shown:
            continue
        shown.add(tid)
        ctx = [l[:220] for l in lines[max(0, end_i - 20000):end_i + 2] if l.startswith(tid + ':')
               and ('Call ' in l or 'Ret ' in l or 'err:' in l)
               and 'RtlNtStatusToDosError' not in l and 'HeapFree' not in l]
        dlls = 'opengl32' in ' '.join(lines[max(0, end_i - 200000):end_i]).lower()
        note('warning', f'ArmPort M2 createbins exit on thread {tid}' + (' (client)' if dlls else ''),
             '\n'.join(ctx[-45:]))
    # How the client chose production vs development data (./piggs/texts.pigg).
    pig = []
    for i, l in enumerate(lines):
        if ('pigg' in l.lower() or re.search(r'ucrtbase\._w?stat|ucrtbase\._findfirst|GetFileAttributes', l)) \
                and ('Call ' in l or 'Ret ' in l):
            tid = l.split(':', 1)[0]
            pig.append(l[:260])
            pig += [m[:260] for m in lines[i + 1:i + 60] if m.startswith(tid + ':') and 'Ret ' in m][:3]
            if len(pig) > 40:
                break
    note('warning', 'ArmPort M2 createbins piggs check', '\n'.join(pig) or 'no texts.pigg lookups')
    note('notice', 'ArmPort M2 createbins trace size', f'{len(lines)} lines')
    report_exceptions(lines, binner, a.llvm_mingw, 'ArmPort M2 createbins')
    exc = [l[:300] for l in lines if 'err:' in l]
    if exc:
        note('warning', 'ArmPort M2 createbins exceptions and exits', '\n'.join(exc[:40]))
    wine_tail = [l[:300] for l in lines if 'trace:' not in l][-40:]
    note('notice', 'ArmPort M2 createbins Wine output', '\n'.join(wine_tail) or '(empty)')


def report_stdio(path, title):
    """The client's own stdout/stderr (patch 0028, ARMPORT_STDIO_LOG)."""
    if not path.exists():
        note('notice', title, 'no client output file')
        return
    text = path.read_text(errors='replace').splitlines()
    note('notice', title + ' size', f'{len(text)} lines')
    errors = [l[:300] for l in text if re.search(r'error|assert|fatal|fail|unable|cannot|missing', l, re.I)]
    for i, c in enumerate(chunks(errors[:50])):
        note('warning', f'{title} errors {i}', c)
    for i, c in enumerate(chunks([l[:300] for l in text[-75:]])):
        note('notice', f'{title} tail {i}', c)


def symbolize(exe, addrs, llvm):
    """Map client addresses (image base 0x140000000) to functions via DWARF."""
    if not llvm or not addrs:
        return {}
    r = subprocess.run([str(llvm / 'bin' / 'llvm-symbolizer'), '--obj=' + str(exe), '--functions=linkage',
                        '--inlining=false', '--relative-address'] + ['0x%x' % (x - 0x140000000) for x in addrs],
                       capture_output=True, text=True)
    out = [b.strip().replace('\n', ' at ') for b in r.stdout.strip().split('\n\n')]
    return dict(zip(addrs, out))


def report_exceptions(lines, exe, llvm, title):
    """Wine SEH traces: exception code and the client functions at pc/lr."""
    blocks = []
    for i, l in enumerate(lines):
        if 'dispatch_exception code=' in l and 'RPC_S_SERVER_UNAVAILABLE' not in l:
            tid = l.split(':', 1)[0]
            regs = ' '.join(m for m in lines[i + 1:i + 40] if m.startswith(tid + ':trace:seh:dispatch_exception'))[:2000]
            pc = re.search(r'pc=([0-9a-f]+)', regs)
            lr = re.search(r'lr=([0-9a-f]+)', regs)
            blocks.append((l.split('trace:seh:dispatch_exception', 1)[-1].strip(),
                           int(pc.group(1), 16) if pc else 0, int(lr.group(1), 16) if lr else 0))
    if not blocks:
        return
    uniq = []
    for b in blocks:
        if b not in uniq:
            uniq.append(b)
    # The client function that catches each exception: the unwind target.
    targets = []
    for l in lines:
        m = re.search(r'RtlUnwindEx code=\S+ flags=\S+ end_frame=\S+ target_ip=([0-9A-Fa-f]+)', l)
        if m:
            targets.append(int(m.group(1), 16))
    client = sorted({x for _, pc, lr in uniq for x in (pc, lr) if 0x140000000 <= x < 0x150000000}
                    | {x for x in targets if 0x140000000 <= x < 0x150000000})
    names = symbolize(exe, client, llvm)
    text = [f'{len(blocks)} exceptions, {len(uniq)} distinct']
    for code, pc, lr in uniq[:12]:
        text.append(f'{code}\n  pc={pc:x} {names.get(pc, "")}\n  lr={lr:x} {names.get(lr, "")}')
    for t in sorted(set(targets))[:8]:
        text.append(f'caught at {t:x} {names.get(t, "")}')
    note('warning', f'{title} exceptions', '\n'.join(text))


def report_runtime_files(rt):
    """The client's own log files and what it wrote into the runtime folder."""
    listing = []
    for p in sorted(rt.rglob('*')):
        if 'data' in p.relative_to(rt).parts[:1] or 'armport_cg' in p.relative_to(rt).parts[:1]:
            continue
        if p.is_file():
            listing.append(f'{p.stat().st_size:>10} {p.relative_to(rt)}')
    note('notice', 'ArmPort M2 runtime files', '\n'.join(listing[:60]))
    for p in sorted(rt.rglob('*.log'))[:8]:
        if 'data' in p.relative_to(rt).parts[:1]:
            continue
        t = p.read_text(errors='replace').splitlines()
        note('warning' if 'error' in p.name.lower() else 'notice', f'ArmPort M2 log {p.relative_to(rt)}',
             '\n'.join(l[:300] for l in t[-40:]) or '(empty)')


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
    ap.add_argument('--createbins', action='store_true',
                    help='first run the client with -createbins to build data/bin from text data')
    ap.add_argument('--createbins-seconds', type=int, default=1800)
    ap.add_argument('--createbins-build', type=Path,
                    help='directory with the non-FINAL (OptDebug) client used for -createbins')
    ap.add_argument('--bins-out', type=Path, help='copy the created data/bin here')
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
    # Development (non-FINAL) builds take a folder with data/ and tools/ as the
    # game root (UtilitiesLib file.c addAppropriateDataDirs).
    (rt / 'tools').mkdir()
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

    if a.createbins:
        createbins(a, rt, exe, env, wine)

    log = rt.parent / 'smoke-output.txt'
    start = time.time()
    with open(log, 'wb') as out:
        args = a.args or ['-fullscreen', '0', '-screen', '1024', '768']
        proc = subprocess.Popen([wine, str(rt / exe.name)] + args, cwd=rt,
                                env=dict(env, ARMPORT_STDIO_LOG='armport_stdio.txt'),
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
    # A small JPEG of the last screen, for export as annotations (screen_export.py).
    last = rt.parent / ('shotend.xwd' if (rt.parent / 'shotend.xwd').exists() else 'shot60.xwd')
    if last.exists():
        for q in (60, 45, 35, 25):
            subprocess.run(['convert', f'xwd:{last}', '-resize', '512x400', '-quality', str(q),
                            str(rt.parent / 'screen.jpg')], capture_output=True)
            if (rt.parent / 'screen.jpg').exists() and (rt.parent / 'screen.jpg').stat().st_size < 24000:
                break

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
    report_stdio(rt / 'armport_stdio.txt', 'ArmPort M2 client output')
    # Text the client put into windows and dialog controls (error messages).
    texts = window_texts(lines)
    if texts:
        note('warning', 'ArmPort M2 smoke window text', '\n'.join(t[:600] for t in texts[:30]))
    report_exceptions(lines, rt / exe.name, a.llvm_mingw, 'ArmPort M2 client')
    tail = [l[:300] for l in lines if 'trace:' not in l][-75:]
    for i, c in enumerate(chunks(tail)):
        note('notice', f'ArmPort M2 smoke output {i}', c)

    report_runtime_files(rt)
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
        rc = main()
    except Exception:
        import traceback
        note('error', 'ArmPort M2 smoke script failed', traceback.format_exc())
        flush_report()
        raise
    flush_report()
    sys.exit(rc)
