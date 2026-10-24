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
import hashlib
import re
import json
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


def merge_tree(src, dst, strict=False):
    """Overlay src onto dst as hard links (real directories, no symlinks, so the
    client's directory scans see ordinary files). Earlier roots win for files.
    Strict supplements must agree byte-for-byte with every earlier collision,
    including case aliases, before any of their files are installed."""
    collisions = 0
    if strict:
        prior = {}
        incoming = {}
        for base, _, names in os.walk(dst, followlinks=True):
            for name in names:
                path = Path(base) / name
                prior.setdefault(path.relative_to(dst).as_posix().casefold(), []).append(path)
        for base, _, names in os.walk(src, followlinks=True):
            for name in names:
                path = Path(base) / name
                key = path.relative_to(src).as_posix().casefold()
                if key in incoming:
                    raise ValueError('Case-aliased supplement members: ' + key)
                incoming[key] = path
                for old in prior.get(key, []):
                    collisions += 1
                    with path.open('rb') as new_file, old.open('rb') as old_file:
                        same = hashlib.file_digest(new_file, 'sha256').digest() == hashlib.file_digest(old_file, 'sha256').digest()
                    if not same:
                        print('::error title=ArmPort reviewed Atlas supplement::' +
                              json.dumps(dict(collisions=collisions, conflicting_path=key)))
                        raise ValueError('Supplement conflicts with earlier data: ' + key)
    for dirpath, dirnames, filenames in os.walk(src, followlinks=True):
        rel = os.path.relpath(dirpath, src)
        target = dst / rel if rel != '.' else dst
        target.mkdir(parents=True, exist_ok=True)
        for f in filenames:
            out = target / f
            if strict and (Path(rel) / f).as_posix().casefold() in prior:
                continue
            if out.exists():
                continue
            try:
                os.link(os.path.join(dirpath, f), out)
            except OSError:
                shutil.copy2(os.path.join(dirpath, f), out)
    if strict:
        print('::notice title=ArmPort reviewed Atlas supplement::' +
              json.dumps(dict(layer=str(src), collisions=collisions, conflicting_collisions=0)))
    return collisions

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
    report_crash(lines, 'ArmPort M2 createbins crash', binner, a.llvm_mingw)
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
    # Missing-art warnings (assets not in the bundle) bury everything else.
    noise = re.compile(r'references missing texture|^ERRORLOG FILEERROR|^File: |^Last Author|'
                       r"It won't create anything|contains EntCreate|^Player texture .* not found")
    text = [l for l in text if not noise.search(l)]
    note('notice', title + ' after filtering', f'{len(text)} lines')
    focus = [l[:300] for l in text if re.search(r'(?i)tokenizer|scene|couldn.t open|geoLoadStubs', l)]
    if focus:
        note('warning', title + ' tokenizer and scene', '\n'.join(focus[-40:]))
    errors = [l[:300] for l in text if re.search(r'error|assert|fatal|fail|unable|cannot|missing|couldn.t open|is empty', l, re.I)
              and 'references missing texture' not in l and "It won't create" not in l]
    for i, c in enumerate(chunks(errors[:50])):
        note('warning', f'{title} errors {i}', c)
    for i, c in enumerate(chunks([l[:300] for l in text[-75:]])):
        note('notice', f'{title} tail {i}', c)


def symbolize(exe, addrs, llvm):
    """Map client addresses (image base 0x140000000) to functions via DWARF."""
    if not llvm or not addrs:
        return {}
    r = subprocess.run([str(llvm / 'bin' / 'llvm-symbolizer'), '--obj=' + str(exe), '--functions=linkage',
                        '--inlining=false', '--relative-address', '--basenames'] + ['0x%x' % (x - 0x140000000) for x in addrs],
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


def report_crash(lines, title, exe=None, llvm=None):
    """Wine's unhandled-exception report and winedbg backtrace, if any, with
    client addresses (image base 0x140000000) mapped to functions and lines."""
    out = []
    for i, l in enumerate(lines):
        if 'Unhandled exception' in l or 'Unhandled page fault' in l:
            out.append(l[:220])
            block = [m for m in lines[i + 1:i + 600] if 'trace:' not in m and 'fixme:' not in m
                     and 'err:' not in m]
            keep = []
            for m in block:
                if (m.startswith('Backtrace:') or re.match(r'\s*=?>?\s*\d+\s+0x', m) or
                        re.search(r'(?i)cityofheroes|ucrtbase|libc\+\+|opengl32|ntdll|kernelbase', m) and
                        ('PE' in m or 'ELF' in m or '-' in m) or m.startswith('Modules:') or
                        'Register dump' in m or re.match(r'\s*(pc|lr|sp|fp|x\d+):', m)):
                    keep.append(m[:220])
            out += keep[:70]
            break
    if out:
        addrs = sorted({int(x, 16) for l in out for x in re.findall(r'(?:0x|\b)0*(14[0-9a-fA-F]{7})\b', l)})
        names = symbolize(exe, addrs[:40], llvm) if exe else {}
        if names:
            out.append('client frames:')
            out += [f'  {x:x} {names[x]}' for x in addrs if x in names]
        note('error', title, '\n'.join(out[:110]))


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
    # Sample the whole frame (the window is not at the top of a tall display).
    step = max(4, (len(pixels) // 4 // 60000) * 4)
    distinct = len(set(pixels[i:i + 3] for i in range(0, len(pixels) - 3, step)))
    return f'nonzero bytes {nonblack:.1%}, distinct colors (sampled) {distinct}'


def login_probe(out, proc):
    """M3 debugging aid: drive the login screen as the M3 server run does."""
    from login_ui import Screen, login
    screen = Screen(out)
    status = {}

    def after(label):
        r = subprocess.run(['ss', '-tuanp'], capture_output=True, text=True, timeout=30)
        sockets = [' '.join(l.split())[:200] for l in r.stdout.splitlines() if 'CityOfHeroes' in l.lower() or 'cityofheroes' in l.lower()]
        w = subprocess.run(['xwininfo', '-root', '-tree', '-display', ':99'], capture_output=True, text=True).stdout
        named = [' '.join(x.split())[:140] for x in w.splitlines() if '"' in x and 'has no name' not in x]
        top = subprocess.run(['top', '-b', '-n', '1', '-w', '200'], capture_output=True, text=True).stdout
        cpu = [' '.join(l.split())[:120] for l in top.splitlines() if 'cityofheroes' in l.lower() or 'CityOfHeroes' in l][:3]
        status.setdefault('after', []).append({'when': label, 'client_sockets': sockets, 'windows': named[:8],
                                               'client_alive': proc.poll() is None, 'cpu': cpu})
    # Stand-in for DbServer's game-client port: record what the client sends.
    import socket as _socket
    import threading as _threading
    received = []
    listener = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
    try:
        listener.bind(('127.0.0.1', 7000))
        listener.settimeout(1)
    except OSError as e:
        status['listener_error'] = repr(e)
        listener = None

    def listen():
        while listener and not status.get('probe_done'):
            try:
                data, addr = listener.recvfrom(65536)
            except OSError:
                continue
            received.append((time.time(), addr[1], data))
    if listener:
        _threading.Thread(target=listen, daemon=True).start()
    after('before the probe')
    try:
        from login_ui import after_login
        if login(screen, 'armportprobe', 'probepass', status, after=after, wait_seconds=120):
            after_login(screen, status, rounds=8, interval=12, after=after)
        screen.shot('probe-end')
        after('end of probe')
    except Exception as e:  # diagnostics only
        status['error'] = repr(e)
    status['probe_done'] = True
    status['udp_7000'] = {'datagrams': len(received), 'sizes': [len(d) for _, _, d in received[:20]],
                          'first': [d[:48].hex() for _, _, d in received[:3]],
                          'source_ports': sorted({p for _, p, _ in received})[:5]}
    if listener:
        listener.close()
    note('notice', 'ArmPort M2 login probe', json.dumps(status, indent=1)[:3000] + '\n' + '\n'.join(screen.log[-40:]))
    # One sheet of the steps, each cropped to the client window (GitHub keeps
    # about ten notices per step, so one image for screen_export.py).
    frames = []
    for key in ('ultra-dismissed', 'account-typed', 'password-typed', 'after-login', 'post-login-03', 'probe-end'):
        hits = [p for p in sorted(out.glob('*.png')) if key in p.name]
        if hits:
            crop = out / f'sheet-{key}.png'
            subprocess.run(['convert', str(hits[-1]), '-crop', '1024x768+104+130', '+repage', str(crop)], capture_output=True)
            if crop.exists():
                frames.append(crop)
    if frames:
        dst = out.parent / 'probe-steps.jpg'
        for size, q in (('320x240', 40), ('256x192', 35), ('224x168', 30), ('192x144', 30)):
            subprocess.run(['montage', *map(str, frames), '-tile', '3x', '-geometry', size + '+2+2',
                            '-quality', str(q), str(dst)], capture_output=True)
            if dst.exists() and dst.stat().st_size < 24000:
                break
        if dst.exists() and dst.stat().st_size >= 24000:
            subprocess.run(['convert', str(dst), '-quality', '20', str(dst)], capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', required=True, type=Path)
    ap.add_argument('--strict-data', type=Path, action='append', default=[],
                    help='--data root whose collisions must have identical bytes')
    ap.add_argument('--data', required=True, type=Path, action='append',
                    help='data root; repeat to overlay several (merged with symlinks)')
    ap.add_argument('--runtime', required=True, type=Path)
    ap.add_argument('--llvm-mingw', type=Path, help='for the import list and runtime DLLs')
    ap.add_argument('--wine', type=Path, help='directory with wine, wineserver (not needed with --stage-only)')
    ap.add_argument('--login-probe', action='store_true',
                    help='after the 60 s screenshot, type a throwaway login on the login screen and press '
                         'Log In (login_ui.py); reports the client\'s sockets and windows and a step contact '
                         'sheet. There is no server, so this only shows whether Log In starts a connection.')
    ap.add_argument('--stage-only', action='store_true',
                    help='only build the runtime folder (exe, DLLs, data overlay, Cg programs) and exit; '
                         'used by the M3 server run, which starts the client itself')
    ap.add_argument('--seconds', type=int, default=180)
    ap.add_argument('--require-alive', action='store_true',
                    help='exit 1 unless the client is still running at --seconds with no unhandled '
                         'exception, no message box and a drawn screen (diagnostics are reported either way)')
    ap.add_argument('--winedebug', default='err+all,fixme-all,+dialog,+class,+win,+seh,+fps')
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
    strict_roots = {root.resolve() for root in a.strict_data}
    if not strict_roots.issubset({root.resolve() for root in a.data}):
        raise ValueError('--strict-data must also appear in --data')
    for root in a.data:
        merge_tree(root.resolve(), rt / 'data', strict=root.resolve() in strict_roots)
    # Development (non-FINAL) builds take a folder with data/ and tools/ as the
    # game root (UtilitiesLib file.c addAppropriateDataDirs).
    (rt / 'tools').mkdir()
    cg = rt / 'armport_cg'
    cg.mkdir()
    arb = sorted(a.cg_dir.glob('*.arb')) if a.cg_dir and a.cg_dir.is_dir() else []
    for f in arb:
        shutil.copy2(f, cg / f.name)
    note('notice', 'ArmPort M2 smoke Cg programs', f'{len(arb)} precompiled ARB programs staged')
    if a.stage_only:
        return 0
    if not a.wine:
        note('error', 'ArmPort M2 smoke', '--wine is required unless --stage-only')
        return 1

    display = ':99'
    # 1600x1200 so the whole 1024x768 window is on screen at Wine's default
    # position (+104+130), as in the M3 server run.
    xvfb = subprocess.Popen(['Xvfb', display, '-screen', '0', '1600x1200x24', '-nolisten', 'tcp'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    env = dict(os.environ, DISPLAY=display, WINEDEBUG=a.winedebug,
               WINEDLLOVERRIDES='mscoree,mshtml=',
               # CI has loose data only, no piggs (patch 0042).
               ARMPORT_LOOSE_DATA='1')
    wine = str(a.wine / 'wine')
    try:
        boot = subprocess.run([wine, 'wineboot', '-i'], env=env, capture_output=True, timeout=300)
        note('notice', 'ArmPort M2 smoke wineboot', f'exit {boot.returncode}')
    except subprocess.TimeoutExpired:
        note('warning', 'ArmPort M2 smoke wineboot', 'timed out after 300s')
    # Crashes: no Wine crash dialog; winedbg prints the backtrace to the log.
    subprocess.run([wine, 'reg', 'add', 'HKCU\\Software\\Wine\\WineDbg', '/v', 'ShowCrashDialog',
                    '/t', 'REG_DWORD', '/d', '0', '/f'], env=env, capture_output=True, timeout=120)
    before = {p for p in rt.iterdir()}

    if a.createbins:
        createbins(a, rt, exe, env, wine)

    log = rt.parent / 'smoke-output.txt'
    start = time.time()
    with open(log, 'wb') as out:
        args = a.args or ['-fullscreen', '0', '-screen', '1024', '768', '-verbose', '1']
        if a.login_probe and not a.args:
            # As in the M3 run: one server entry, 127.0.0.1 (nothing listens here).
            args = args + ['-db', '127.0.0.1']
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
            if a.login_probe:
                login_probe(rt.parent / 'probe', proc)
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
    fps = [l.split('fps:', 1)[-1].strip()[:80] for l in lines if ':fps:' in l]
    if fps:
        note('notice', 'ArmPort M2 frame rate', f'{len(fps)} samples (Wine +fps, about one per second while frames are presented); '
             f'first 10: {fps[:10]}; last 20: {fps[-20:]}')
    else:
        note('notice', 'ArmPort M2 frame rate', 'no +fps samples (no frame presented through wglSwapBuffers?)')
    report_stdio(rt / 'armport_stdio.txt', 'ArmPort M2 client output')
    if a.login_probe and (rt / 'armport_stdio.txt').exists():
        marks = [l[:240] for l in (rt / 'armport_stdio.txt').read_text(errors='replace').splitlines() if l.startswith('ArmPort ')]
        note('notice', 'ArmPort M2 login probe stages and dialogs', f'{len(marks)} lines\n' + '\n'.join(marks[-40:]))
    # Text the client put into windows and dialog controls (error messages).
    texts = window_texts(lines)
    if texts:
        note('warning', 'ArmPort M2 smoke window text', '\n'.join(t[:600] for t in texts[:30]))
    report_exceptions(lines, rt / exe.name, a.llvm_mingw, 'ArmPort M2 client')
    report_crash(lines, 'ArmPort M2 client crash', rt / exe.name, a.llvm_mingw)
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
    if a.require_alive:
        failures = []
        if not running:
            failures.append(status)
        crashes = [l for l in lines if l.startswith('wine: Unhandled')]
        if crashes:
            failures.append(f'{len(crashes)} unhandled exception(s): {crashes[0][:200]}')
        if dialog:
            failures.append(f'message box shown: {dialog[0][:200]}')
        # A live client must also be drawing: the last screen needs real content
        # (the login screen samples about 1,200 distinct colours; a blank one 1).
        # With --login-probe the screen check uses the frame from before the probe.
        m = re.search(r'distinct colors \(sampled\) (\d+)', (shot_mid if a.login_probe else shot_end) or '')
        if running and (not m or int(m.group(1)) < 64):
            failures.append(f'last screen blank or missing: {shot_end}')
        if failures:
            note('error', 'ArmPort M2 smoke verdict', 'boot test failed:\n' + '\n'.join(failures))
            return 1
        note('notice', 'ArmPort M2 smoke verdict', f'boot test passed: {status}, no unhandled exception, no message box, screen drawn ({shot_end})')
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
