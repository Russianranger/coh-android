#!/usr/bin/env python3
"""Reproduce the original pointer/array macro conflict; qualify only its repair.

The original stdtypes.h definitions are extracted byte-for-byte. Host execution
does not substitute for the separate actual MSVC MapServer target build.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STDTYPES = ROOT / 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/stdtypes.h'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(ok):
    if not ok:
        raise ValueError('FORMATTER_COMPATIBILITY_REFUSED')


def original_define(raw, name):
    lines = raw.splitlines(keepends=True)
    found = []
    for i, line in enumerate(lines):
        rest = line.split(None, 2)
        if len(rest) < 2 or rest[0] != '#define':
            continue
        if rest[1].split('(', 1)[0] != name:
            continue
        value = line
        while value.rstrip().endswith('\\'):
            i += 1
            value += lines[i]
        found.append(value)
    need(len(found) == 1)
    return found[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    core_path = HERE / 'coh_server_initial_ledger.c'
    test_path = HERE / 'test_ledger.c'
    raw = STDTYPES.read_bytes()
    core = core_path.read_bytes()
    need(core.count(b'n=(snprintf)(out,cap,') == 1)
    old = core.replace(b'n=(snprintf)(out,cap,', b'n=snprintf(out,cap,', 1)
    (out / 'unparenthesized-ledger.c').write_bytes(old)
    definitions = {name: original_define(raw.decode(), name) for name in
                   ('FORMAT', 'ARRAY_SIZE_CHECKED', 'snprintf_s', 'snprintf')}
    declaration = next(line for line in raw.decode().splitlines()
                       if line.startswith('int quick_snprintf('))
    macro_header = '#include <stdio.h>\n' + definitions['FORMAT'] + declaration + '\n'
    macro_header += ''.join(definitions[name] for name in
                            ('ARRAY_SIZE_CHECKED', 'snprintf_s', 'snprintf'))
    macro_path = out / 'exact-original-format-macros.h'
    macro_path.write_text(macro_header)
    common = ['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic', '-I', str(HERE)]
    negative_command = common + ['-include', str(macro_path), '-c',
                                 str(out / 'unparenthesized-ledger.c'), '-o', str(out / 'negative.o')]
    negative = subprocess.run(negative_command, capture_output=True)
    (out / 'negative-compile.stderr').write_bytes(negative.stderr)
    need(negative.returncode != 0 and b'by zero' in negative.stderr)
    preprocessed = subprocess.run(['cc', '-std=c99', '-I', str(HERE), '-include',
                                  str(macro_path), '-E', '-P',
                                  str(out / 'unparenthesized-ledger.c')], capture_output=True, check=True)
    expansion = next(line for line in preprocessed.stdout.splitlines() if line.startswith(b' n=quick_snprintf('))
    need(b'sizeof(out)==sizeof(void*)' in expansion and b'?0:sizeof((out)[0])' in expansion)
    (out / 'actual-original-macro-expansion.txt').write_bytes(expansion + b'\n')
    runs = []
    for mode, flags in [('release', ['-O2']),
                        ('asan', ['-O1', '-g', '-fsanitize=address', '-fno-omit-frame-pointer', '-no-pie']),
                        ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        outputs = []
        for role, source, injection in [('old-standalone', out / 'unparenthesized-ledger.c', []),
                                        ('new-standalone', core_path, []),
                                        ('new-original-macros', core_path, ['-include', str(macro_path)])]:
            binary = out / (mode + '-' + role)
            command = common + flags + injection + [str(source), str(test_path), '-o', str(binary)]
            built = subprocess.run(command, capture_output=True)
            (out / (mode + '-' + role + '-compile.stderr')).write_bytes(built.stderr)
            need(built.returncode == 0 and not built.stderr)
            env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:abort_on_error=1')
            ran = subprocess.run([str(binary)], capture_output=True, env=env)
            (out / (mode + '-' + role + '.stdout')).write_bytes(ran.stdout)
            (out / (mode + '-' + role + '.stderr')).write_bytes(ran.stderr)
            need(ran.returncode == 0 and not ran.stderr and b'checks=105' in ran.stdout)
            need(ran.stdout.count(b'SNAPSHOT ') == 4)
            outputs.append(ran.stdout)
            runs.append({'mode': mode, 'role': role, 'checks': 105,
                         'elf_bytes': binary.stat().st_size, 'elf_sha256': sha(binary.read_bytes()),
                         'stdout_sha256': sha(ran.stdout), 'stderr_bytes': len(ran.stderr),
                         'compiler_argv': command})
        need(outputs[0] == outputs[1] == outputs[2])
    # The surrounding original policy must remain defined after the include.
    positive = '#include "' + str(core_path) + '"\n#ifndef snprintf\n#error ORIGINAL_MACRO_LOST\n#endif\n'
    positive += 'int array_macro_still_active(void){char array[32];return snprintf(array,sizeof(array),"%s","array");}\n'
    positive_path = out / 'containing-tu-macro-preserved.c'
    positive_path.write_text(positive)
    object_path = out / 'containing-tu-macro-preserved.o'
    compiled = subprocess.run(common + ['-include', str(macro_path), '-c', str(positive_path),
                                       '-o', str(object_path)], capture_output=True)
    need(compiled.returncode == 0 and not compiled.stderr)
    symbols = subprocess.run(['nm', '-u', str(object_path)], check=True, capture_output=True).stdout
    need(b'quick_snprintf' in symbols and b' snprintf' in symbols)
    (out / 'containing-tu-undefined-symbols.txt').write_bytes(symbols)
    proof = {'schema': 'coh-server-initial-formatter-compatibility-v1', 'passed': True,
             'cause': 'original array-only snprintf macro receives char pointer and divides sizeof(pointer) by zero',
             'repair': 'parenthesized C99 CRT snprintf identifier bypasses function-like macro at this call only',
             'source_sha256': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
                               (core_path, HERE / 'coh_server_initial_ledger.h', test_path,
                                STDTYPES, Path(__file__).resolve())},
             'exact_original_macros': definitions, 'exact_original_declaration': declaration,
             'unparenthesized_original_macro_compile_refused': True,
             'original_macro_preserved_for_containing_tu': True,
             'standalone_old_new_and_original_macro_outputs_equal': True,
             'runs': runs, 'json_schema_bounds_and_privacy_unchanged': True,
             'host_pointer_bits': __import__('struct').calcsize('P') * 8,
             'actual_msvc_executed': False, 'original_map_executed': False,
             'original_packet_serializers_executed': False, 'world_authority': False,
             'leak_sanitizer_enabled': False}
    (out / 'qualification.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'passed': True, 'compiled_and_executed_variants': len(runs),
                      'checks_per_variant': 105, 'original_macro_negative_control': True,
                      'whole_original_msvc_build_pending': True}))


if __name__ == '__main__':
    main()
