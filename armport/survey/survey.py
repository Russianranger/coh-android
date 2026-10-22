#!/usr/bin/env python3
"""M0 compile survey for the COH-ArmPort.

Copies the original client sources (UtilitiesLib + Game, which includes the
Common files the client uses) to a work directory, runs the original
StructParser code generator there, then compiles every source file
syntax-only for an ARM64 target and groups the diagnostics.

upstream/ is never modified. Nothing is linked or executed for the target.

Example:
  armport/toolchain/fetch.sh /tmp/tc
  python3 armport/survey/survey.py --toolchain /tmp/tc \
      --structparser /path/StructParser --target win-arm64 \
      --work /tmp/survey-work --out armport/survey/results/win-arm64.json
"""
import argparse
import collections
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPSTREAM = os.path.join(ROOT, 'upstream', 'ouroboros')
CLANG_RESOURCE = subprocess.run(['clang', '-print-resource-dir'], capture_output=True,
                                text=True).stdout.strip()


def cmake_list(path, var, append_too=True):
    """Return the entries of set(VAR ...) (plus list(APPEND VAR ...)) in a CMakeLists."""
    text = open(path, encoding='utf-8', errors='replace').read()
    text = re.sub(r'#[^\n]*', '', text)
    items = []
    pats = [r'set\(\s*' + var + r'\s+(.*?)\)']
    if append_too:
        pats.append(r'list\(\s*APPEND\s+' + var + r'\s+(.*?)\)')
    for pat in pats:
        for m in re.finditer(pat, text, re.S):
            for tok in re.findall(r'"[^"]*"|\S+', m.group(1)):
                items.append(tok.strip('"'))
    # The survey targets ARM64, so honor list(REMOVE_ITEM VAR ...) as well
    # (the ArmPort patches use it only inside if(COX_ARM64_WINDOWS)).
    removed = set()
    for m in re.finditer(r'list\(\s*REMOVE_ITEM\s+' + var + r'\s+(.*?)\)', text, re.S):
        removed.update(t.strip('"') for t in re.findall(r'"[^"]*"|\S+', m.group(1)))
    return [i for i in items if i not in removed]


def targets(src):
    util_dir = os.path.join(src, 'libs', 'UtilitiesLib')
    game_dir = os.path.join(src, 'Game')
    util_cm = os.path.join(util_dir, 'CMakeLists.txt')
    game_cm = os.path.join(game_dir, 'CMakeLists.txt')
    return [
        dict(name='UtilitiesLib', kind='library', project=util_dir,
             sources=cmake_list(util_cm, 'UtilitiesLib_SOURCE_FILES'),
             headers=cmake_list(util_cm, 'UtilitiesLib_HEADER_FILES'),
             generated=[],
             defines=['_LIB']),
        dict(name='Game', kind='executable', project=game_dir,
             sources=cmake_list(game_cm, 'Game_SOURCES'),
             headers=cmake_list(game_cm, 'Game_HEADERS'),
             generated=cmake_list(game_cm, 'Game_GENERATED'),
             defines=['CLIENT', 'USEZLIB', '_WINDOWS', '_MBCS',
                      'SUBSTANCE_PLATFORM_OGLCG', '_CRT_SECURE_NO_DEPRECATE']),
    ]


def run_structparser(sp, src, t, state_root):
    files = [os.path.normpath(os.path.join(t['project'], p))
             for p in t['sources'] + t['headers'] + t['generated']]
    lst = os.path.join(state_root, t['name'] + '.sources')
    with open(lst, 'w') as f:
        f.write('\n'.join(files) + '\n')
    cmd = [sp, '--target', t['name'], '--source-dir', os.path.join(t['project'], 'src'),
           '--common-dir', os.path.join(src, 'Common'), '--project-dir', t['project'],
           '--kind', t['kind'], '--sources-file', lst,
           '--state-dir', os.path.join(state_root, t['name'] + '.state')]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return dict(returncode=r.returncode, stdout_tail=r.stdout[-2000:],
                stderr_tail=r.stderr[-2000:])


def cxx_flags(kind, tc):
    """libc++ 18 headers; they must come before the C library headers."""
    cfg = os.path.join(tc, 'gen-cxx-win' if kind == 'win-arm64' else 'gen-cxx-linux')
    return ['-nostdinc++', '-isystem', cfg,
            '-isystem', os.path.join(tc, 'llvm', 'libcxx', 'include')]


def target_flags(kind, tc):
    z = os.path.join(tc, 'zig', 'lib', 'libc', 'include')
    m = os.path.join(tc, 'mingw-w64', 'mingw-w64-headers')
    if kind == 'win-arm64':
        return ['--target=aarch64-w64-mingw32', '-nostdinc',
                '-isystem', os.path.join(CLANG_RESOURCE, 'include'),
                '-isystem', os.path.join(tc, 'gen'),
                '-isystem', os.path.join(m, 'crt'), '-isystem', os.path.join(m, 'include'),
                '-isystem', os.path.join(m, 'direct-x', 'include'),
                '-isystem', os.path.join(m, 'ddk', 'include'), '-D_UCRT',
                # clang 18 builtin __prefetch clashes with mingw-w64 intrin.h on
                # ARM64; rename the header's declaration (toolchain issue only).
                '-D__prefetch=__coh_mingw_prefetch']
    if kind == 'linux-arm64':
        return ['--target=aarch64-linux-gnu', '-nostdinc',
                '-isystem', os.path.join(CLANG_RESOURCE, 'include'),
                '-isystem', os.path.join(tc, 'gen'),
                '-isystem', os.path.join(z, 'aarch64-linux-gnu'),
                '-isystem', os.path.join(z, 'generic-glibc'),
                '-isystem', os.path.join(z, 'aarch64-linux-any'),
                '-isystem', os.path.join(z, 'any-linux-any')]
    raise SystemExit('unknown target ' + kind)


def dep_includes(src, tc):
    d = os.path.join(tc, 'deps')
    third = os.path.join(src, '3rdparty')
    inc = [os.path.join(tc, 'gen'),
           os.path.join(d, 'zlib'), os.path.join(d, 'freetype', 'include'),
           os.path.join(d, 'glew-cmake', 'include'),
           os.path.join(d, 'vorbis', 'include'), os.path.join(d, 'ogg', 'include'),
           os.path.join(d, 'libjpeg-turbo', 'src'), os.path.join(d, 'libjpeg-turbo'),
           os.path.join(d, 'jpgd'), os.path.join(d, 'jpgd', 'include'),
           os.path.join(d, 'sparsehash', 'src'),
           os.path.join(third, 'cg', 'include'), os.path.join(third, 'nvdxt'),
           os.path.join(third, 'nvparse', 'include', 'nvparse'),
           os.path.join(third, 'nvparse', 'include'),
           os.path.join(third, 'AlienFX SDK', 'Unmanaged', 'includes'),
           os.path.join(third, 'nvcpl'),
           os.path.join(src, 'libs', 'crashrpt', 'include'), os.path.join(d, 'cryptopp')]
    sdks = os.path.join(third, 'PhysX', 'SDKs')
    if os.path.isdir(sdks):
        for comp in sorted(os.listdir(sdks)):
            p = os.path.join(sdks, comp, 'include')
            if os.path.isdir(p):
                inc.append(p)
    return [x for x in inc if os.path.isdir(x)]


# clang errors that MSVC (and older GCC) accept; downgraded to warnings only.
PERMISSIVE = ['-Wno-error=incompatible-function-pointer-types', '-Wno-error=implicit-int',
              '-Wno-error=implicit-function-declaration', '-Wno-error=int-conversion',
              '-Wno-error=incompatible-pointer-types', '-Wno-error=return-type']

COMMON_DEFINES = ['WIN32', '_CRT_SECURE_NO_WARNINGS', '_CRT_NONSTDC_NO_DEPRECATE',
                  '_WINSOCK_DEPRECATED_NO_WARNINGS', 'FINAL', 'NDEBUG']
# Windows-only configuration macros; not defined for the linux-arm64 target so
# the sources take whatever non-Windows paths they have.
WINDOWS_ONLY_DEFINES = {'WIN32', '_WINDOWS', '_MBCS', '_CRT_SECURE_NO_WARNINGS',
                        '_CRT_NONSTDC_NO_DEPRECATE', '_WINSOCK_DEPRECATED_NO_WARNINGS',
                        '_CRT_SECURE_NO_DEPRECATE'}

CATEGORIES = [
    ('missing-header', re.compile(r"fatal error: '([^']+)' file not found")),
    ('pointer-truncation', re.compile(r'cast from pointer to smaller type|loses information|'
                                      r'cast to smaller integer type')),
    ('int-pointer-conversion', re.compile(r'incompatible (integer to pointer|pointer to integer) conversion')),
    ('inline-asm', re.compile(r'MS-style inline assembly|__asm|_asm\b')),
    ('x86-intrinsics', re.compile(r"_mm_|__m128|xmmintrin|emmintrin|__cpuid|_BitScan|__rdtsc|_InterlockedCompareExchange64|'(x|e|p|t|s)mmintrin")),
    ('implicit-function', re.compile(r'call to undeclared function|implicit declaration of function')),
    ('static-assert', re.compile(r'static assertion failed|static_assert')),
    ('undeclared-identifier', re.compile(r'use of undeclared identifier|unknown type name')),
    ('redefinition', re.compile(r'redefinition of|conflicting types for|typedef redefinition')),
    ('cxx-language', re.compile(r'cannot initialize|no matching (function|constructor)|'
                                r'non-const lvalue|ISO C\+\+|invalid conversion')),
]


# Pointer-sized integer types; narrowing one of these to 32 bits can cut a
# pointer or handle (e.g. an intptr_t _findfirst handle stored in an int).
POINTER_SIZED = re.compile(r"'(u?intptr_t|INT_PTR|UINT_PTR|LONG_PTR|ULONG_PTR|DWORD_PTR|LPARAM|WPARAM|"
                           r"LRESULT|HANDLE|ptrdiff_t|SSIZE_T)'")


def classify(msg):
    for name, pat in CATEGORIES:
        if pat.search(msg):
            return name
    return 'other'


def compile_one(args):
    path, lang, flags, cxx, rel = args
    if lang == 'c':
        cmd = ['clang', flags[0], '-x', 'c', '-std=gnu11'] + flags[1:]
    else:
        cmd = ['clang', flags[0], '-x', 'c++', '-std=gnu++17'] + cxx + flags[1:]
    cmd += ['-fsyntax-only', path]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    errs = [l for l in r.stderr.splitlines() if ': error: ' in l or ': fatal error: ' in l]
    w64 = [l for l in r.stderr.splitlines() if ': warning: ' in l and
           (re.search(r'-W(void-)?pointer-to-(int|enum)-cast|-Wint-to-pointer-cast', l) or
            ('-Wshorten-64-to-32' in l and POINTER_SIZED.search(l)))]
    return dict(file=rel, ok=(r.returncode == 0), errors=errs, warn64=w64,
                seconds=round(time.time() - t0, 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--toolchain', required=True)
    ap.add_argument('--structparser', required=True)
    ap.add_argument('--target', choices=['win-arm64', 'linux-arm64'], required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--out', required=True)
    # Two compiler processes by default, matching the bounded build-host rule.
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--limit', type=int, default=0, help='compile only N files per target (debug)')
    ap.add_argument('--all-errors', action='store_true',
                    help='keep every error line per failing file (default: first only)')
    ap.add_argument('--permissive', action='store_true',
                    help='downgrade clang strictness errors that MSVC accepts (flags only, no patches)')
    ap.add_argument('--patched', action='store_true',
                    help='work dir was made by armport/scripts/prepare.py: use the same ARM64 settings '
                         'as the patched CMake build (shim headers, sse2neon, permissive flags)')
    ap.add_argument('--overlay', default='',
                    help='extra include dir searched first (shim headers for experiments)')
    ap.add_argument('--warn64', action='store_true',
                    help='report pointer/integer size warnings instead of suppressing all warnings')
    ap.add_argument('--warn-width', action='store_true',
                    help='with --warn64, also report pointer-sized integers narrowed to 32 bits')
    a = ap.parse_args()

    src = os.path.join(a.work, 'src')
    if not os.path.isdir(src):
        shutil.copytree(UPSTREAM, src, symlinks=True,
                        ignore=shutil.ignore_patterns('data', 'Assets', '.git'))
    state = os.path.join(a.work, 'state')
    os.makedirs(state, exist_ok=True)

    if a.patched:
        a.permissive = True
        a.overlay = a.overlay or os.path.join(src, 'cmake', 'armport-include')
    tflags = target_flags(a.target, a.toolchain)
    cxx = cxx_flags(a.target, a.toolchain)
    deps = dep_includes(src, a.toolchain)
    report = dict(target=a.target, permissive=a.permissive, warn64=a.warn64, clang=subprocess.run(['clang', '--version'], capture_output=True,
                                                         text=True).stdout.splitlines()[0],
                  started=time.strftime('%Y-%m-%dT%H:%M:%S%z'), targets={})
    for t in targets(src):
        sp = run_structparser(a.structparser, src, t, state)
        inc = ([a.overlay] if a.overlay else []) + [t['project'] + '/src', t['project'] + '/include', os.path.join(src, 'Common'),
               os.path.join(src, 'libs', 'UtilitiesLib', 'include')] + deps
        warn = ['-w']
        if a.warn64:
            warn = ['-Wno-everything', '-Wpointer-to-int-cast', '-Wint-to-pointer-cast',
                    '-Wvoid-pointer-to-int-cast', '-Wvoid-pointer-to-enum-cast'] + \
                (['-Wshorten-64-to-32'] if a.warn_width else [])
        flags = tflags + ['-fms-extensions', '-fno-strict-aliasing', '-ferror-limit=0',
                          '-fno-color-diagnostics'] + warn + (PERMISSIVE if a.permissive else []) + \
            ['-D' + d for d in COMMON_DEFINES + t['defines'] +
             (['DISABLE_SHARED_MEMORY_SEGMENT'] if a.patched else [])
             if a.target == 'win-arm64' or d not in WINDOWS_ONLY_DEFINES] + \
            (['-isystem', os.path.join(a.toolchain, 'deps', 'sse2neon')] if a.patched else []) + \
            [x for p in inc if os.path.isdir(p) for x in ('-I', p)]
        jobs = []
        for p in t['sources']:
            full = os.path.normpath(os.path.join(t['project'], p))
            ext = os.path.splitext(p)[1]
            if ext not in ('.c', '.C', '.cpp', '.cxx', '.cc'):
                continue
            if not os.path.exists(full):
                continue
            lang = 'c' if ext in ('.c', '.C') else 'c++'
            jobs.append((full, lang, flags, cxx, os.path.relpath(full, src)))
        if a.limit:
            jobs = jobs[:a.limit]
        with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
            results = list(ex.map(compile_one, jobs))
        cats = collections.Counter()
        headers = collections.Counter()
        first = collections.Counter()
        examples = collections.defaultdict(list)
        for r in results:
            for i, e in enumerate(r['errors']):
                c = classify(e)
                cats[c] += 1
                if i == 0:
                    first[c] += 1
                m = CATEGORIES[0][1].search(e)
                if m:
                    headers[m.group(1)] += 1
                if len(examples[c]) < 8:
                    examples[c].append(e.split(src + '/', 1)[-1][:300])
        w64 = collections.Counter()
        w64_examples = []
        for r in results:
            for w in r['warn64']:
                w64[r['file']] += 1
                if len(w64_examples) < (100000 if a.warn_width else 12):
                    w64_examples.append(w.split(src + '/', 1)[-1][:240])
        report['targets'][t['name']] = dict(
            warn64_total=sum(w64.values()), warn64_files=len(w64),
            warn64_top_files=dict(w64.most_common(25)), warn64_examples=w64_examples,
            structparser=sp, files=len(results),
            files_clean=sum(1 for r in results if r['ok']),
            errors_total=sum(len(r['errors']) for r in results),
            errors_by_category=dict(cats.most_common()),
            first_error_by_category=dict(first.most_common()),
            missing_headers=dict(headers.most_common(40)),
            examples=examples,
            worst_files=[dict(file=r['file'], errors=len(r['errors']))
                         for r in sorted(results, key=lambda r: -len(r['errors']))[:25]],
            per_file=[dict(file=r['file'], ok=r['ok'], errors=len(r['errors']),
                           first=(r['errors'][0].split(src + '/', 1)[-1][:240]
                                  if r['errors'] else ''),
                           **({'all': [e.split(src + '/', 1)[-1][:300] for e in r['errors']]}
                              if a.all_errors and r['errors'] else {}))
                      for r in results])
    report['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w') as f:
        json.dump(report, f, indent=1)
    for name, t in report['targets'].items():
        print(f"{name}: {t['files_clean']}/{t['files']} clean, {t['errors_total']} errors; "
              f"by category {t['errors_by_category']}")


if __name__ == '__main__':
    main()
