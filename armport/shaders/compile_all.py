#!/usr/bin/env python3
"""Compile every client Cg shader with the original cgc.exe to ARB assembly.

M0 check: can the shaders be compiled once, off-device, so the ARM64 client
never needs the x86-only Cg runtime? Runs on a Windows CI runner.

Profiles follow the client: *fp.cg -> arbfp1, *vp.cg -> arbvp1, entry "main".
This compiles each file with no variant defines; the client also compiles
variants (defines per blend mode / feature), which its own prebaked-shader
cache handles at run time. Output: a JSON report and the ARB text files.
"""
import argparse
import json
import os
import re
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cgc', required=True)
    ap.add_argument('--shaders', required=True, help='data/shaders directory')
    ap.add_argument('--out', required=True, help='output directory')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    root = os.path.join(a.shaders, 'cgfx')
    version = subprocess.run([a.cgc, '-v'], capture_output=True, text=True)
    results = []
    for dirpath, _, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith('.cg'):
                continue
            src = os.path.join(dirpath, name)
            rel = os.path.relpath(src, root).replace('\\', '/')
            if name.endswith('fp.cg'):
                profile = 'arbfp1'
            elif name.endswith('vp.cg'):
                profile = 'arbvp1'
            else:
                results.append(dict(file=rel, skipped='no fp/vp suffix'))
                continue
            dst = os.path.join(a.out, rel.replace('/', '__') + '.' + profile)
            cmd = [a.cgc, '-quiet', '-profile', profile, '-entry', 'main',
                   '-I' + root, '-I' + dirpath, '-o', dst, src]
            r = subprocess.run(cmd, capture_output=True, text=True)
            text = open(dst, encoding='latin-1').read() if os.path.exists(dst) else ''
            m = re.search(r'#\s*(\d+)\s+instructions', text)
            results.append(dict(file=rel, profile=profile, returncode=r.returncode,
                                output_bytes=len(text),
                                instructions=int(m.group(1)) if m else None,
                                messages=(r.stdout + r.stderr).strip().splitlines()[:6]))
    compiled = [x for x in results if x.get('returncode') == 0 and x.get('output_bytes')]
    report = dict(cgc_version=(version.stdout + version.stderr).strip().splitlines()[:2],
                  total=len(results), compiled=len(compiled),
                  failed=[x for x in results if 'skipped' not in x and x not in compiled],
                  skipped=[x for x in results if 'skipped' in x],
                  results=results)
    with open(os.path.join(a.out, 'report.json'), 'w') as f:
        json.dump(report, f, indent=1)
    print(f"compiled {len(compiled)} of {len(results)} shader files")
    for x in report['failed']:
        print('FAILED', x['file'], x['profile'], ' | '.join(x['messages'][:2]))
    # GitHub annotations: readable through the checks API without artifact access.
    if os.environ.get('GITHUB_ACTIONS'):
        def esc(t):
            return t.replace('%', '%25').replace('\r', '').replace('\n', '%0A')
        print(f"::notice title=ArmPort shaders::compiled {len(compiled)} of {len(results)}; "
              f"failed {len(report['failed'])}; skipped {len(report['skipped'])}; "
              f"cgc {esc(' '.join(report['cgc_version'])[:120])}")
        lines = [f"{x['file']} {x['profile']}: {' | '.join(x['messages'][:2])[:160]}"
                 for x in report['failed']]
        for i in range(0, len(lines), 6):
            print('::warning title=ArmPort shader failures ' + str(i // 6 + 1) + '::' +
                  esc('\n'.join(lines[i:i + 6])))
        ok = [f"{x['file']} {x['profile']} {x['instructions']} instr" for x in compiled]
        for i in range(0, len(ok), 12):
            print('::notice title=ArmPort shaders compiled ' + str(i // 12 + 1) + '::' +
                  esc('\n'.join(ok[i:i + 12])))


if __name__ == '__main__':
    main()
