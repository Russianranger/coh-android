#!/usr/bin/env python3
"""Compile the Cg programs the ARM64 client asked for, with the original cgc.exe.

The ARM64 Cg stand-in (armport/standins/cg/cg_arb.cpp) records each program it
has no ARB assembly for as <key>.req: profile, entry, compiler args and the
exact source text the client passed to cgCreateProgram. This compiles each
request with the same profile, entry and args and writes <key>.arb, which the
stand-in loads on the next run. Runs on a Windows CI runner.

  compile_requests.py --cgc cgc.exe --shaders data/shaders --requests DIR --out DIR
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile


def request_key(profile, entry, args, source):
    """FNV-1a 64 over NUL-separated fields; must match cg_arb.cpp.
    Include-path args (-I...) are not part of the key."""
    h = 1469598103934665603
    prime = 1099511628211
    mask = (1 << 64) - 1

    def add(data):
        nonlocal h
        for b in data:
            h = ((h ^ b) * prime) & mask
        h = (h * prime) & mask

    add(profile.encode())
    add(entry.encode())
    for a in args:
        if not a.startswith('-I'):
            add(a.encode())
    add(b'')
    add(source)
    return '%016x' % h


def parse(path):
    data = open(path, 'rb').read()
    head, sep, source = data.partition(b'\nsource\n')
    if not sep:
        raise ValueError('no source section')
    fields = {'arg': []}
    for line in head.decode('latin-1').splitlines():
        name, _, value = line.partition(' ')
        if name == 'arg':
            fields['arg'].append(value)
        else:
            fields[name] = value
    return fields['profile'], fields['entry'], fields['arg'], source


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cgc', required=True)
    ap.add_argument('--shaders', required=True, help='data/shaders directory')
    ap.add_argument('--requests', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    root = os.path.join(a.shaders, 'cgfx')
    includes = [root] + [os.path.join(d, n) for d, dirs, _ in os.walk(root) for n in dirs]
    results = []
    for name in sorted(os.listdir(a.requests)):
        if not name.endswith('.req'):
            continue
        key = name[:-4]
        profile, entry, args, source = parse(os.path.join(a.requests, name))
        r = dict(key=key, profile=profile, args=args)
        if request_key(profile, entry, args, source) != key:
            r['error'] = 'key mismatch'
            results.append(r)
            continue
        # The source goes next to the shaders so relative #includes resolve.
        fd, src = tempfile.mkstemp(suffix='.cg', dir=root)
        with os.fdopen(fd, 'wb') as f:
            f.write(source)
        dst = os.path.join(a.out, key + '.arb')
        cmd = [a.cgc, '-quiet', '-profile', profile, '-entry', entry] + \
              ['-I' + d for d in includes] + [x for x in args if not x.startswith('-I')] + \
              ['-o', dst, src]
        p = subprocess.run(cmd, capture_output=True, text=True)
        os.remove(src)
        text = open(dst, encoding='latin-1').read() if os.path.exists(dst) else ''
        m = re.search(r'#\s*(\d+)\s+instructions', text)
        r.update(returncode=p.returncode, output_bytes=len(text),
                 instructions=int(m.group(1)) if m else None,
                 stderr=(p.stdout + p.stderr)[-600:])
        if p.returncode or not text.startswith('!!ARB'):
            if os.path.exists(dst):
                os.remove(dst)
            r['error'] = 'compile failed'
        results.append(r)
    ok = sum(1 for r in results if 'error' not in r)
    with open(os.path.join(a.out, 'report.json'), 'w') as f:
        json.dump(dict(requests=len(results), compiled=ok, results=results), f, indent=1)
    print(f'::notice title=ArmPort Cg precompile::{ok}/{len(results)} requests compiled to ARB')
    for r in [r for r in results if 'error' in r][:8]:
        msg = f"{r['key']} {r['profile']} {' '.join(r['args'])}: {r['error']} {r.get('stderr', '')}"
        print('::warning title=ArmPort Cg precompile failure::' + msg.replace('\n', '%0A')[:1500])
    return 0


if __name__ == '__main__':
    sys.exit(main())
