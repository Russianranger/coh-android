#!/usr/bin/env python3
"""Focused borrowed-renderer identity/lifecycle check; no EGL or world admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GUARD = '    if (p->renderer && p->renderer!=r) return COH_STATE;\n'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [HERE / 'coh_world_render.c', HERE / 'tests/test_presentation_renderer_identity.c',
               ROOT / 'native-android/engine/renderer/coh_renderer.c']
    pins = [*sources, HERE / 'coh_world_render.h', HERE / 'coh_wr_presentation.h',
            HERE / 'coh_wr_presentation.inc', Path(__file__).resolve(),
            ROOT / 'native-android/engine/renderer/coh_renderer.h',
            ROOT / 'native-android/engine/renderer/coh_renderer_shaders.h',
            ROOT / 'native-android/engine/coh_contracts.h']
    before = {str(p.relative_to(ROOT)): sha(p) for p in pins}
    proof = {'scope': 'borrowed renderer identity and CPU publication/resource lifecycle',
             'source_revision': subprocess.check_output(['git', '-C', ROOT, 'rev-parse', 'HEAD'], text=True).strip(),
             'source_sha256': before, 'fixture_only': True, 'gles_executed': False,
             'android_executed': False, 'world_authority': False, 'modes': {}, 'mutations': {}}
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-ffp-contract=off', '-pthread', '-I'+str(HERE)]

    def execute(label, command, env=None, expect_failure=False):
        result = subprocess.run([str(x) for x in command], capture_output=True, text=True, timeout=60, env=env)
        (args.output / (label+'.stdout')).write_text(result.stdout)
        (args.output / (label+'.stderr')).write_text(result.stderr)
        if (result.returncode != 0) != expect_failure:
            raise RuntimeError(label+' unexpected return '+str(result.returncode))
        return result

    with tempfile.TemporaryDirectory(prefix='coh-renderer-identity-') as d:
        temp = Path(d)
        for mode in ('release', 'address', 'undefined'):
            binary = temp / mode
            options = ['-O2'] if mode == 'release' else ['-O1', '-g', '-fno-omit-frame-pointer', '-no-pie', '-fsanitize='+mode]
            execute(mode+'-build', [os.environ.get('CC', 'cc'), *flags, *options, *sources, '-lm', '-o', binary])
            env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:abort_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            result = json.loads(execute(mode, [binary], env).stdout)
            if mode != 'release' and result != proof['modes']['release']['result']:
                raise ValueError('mode results differ')
            proof['modes'][mode] = {'result': result, 'binary_sha256': sha(binary)}
        original = (HERE / 'coh_wr_presentation.inc').read_text()
        core = (HERE / 'coh_world_render.c').read_text()
        for name in ('resume', 'pause', 'surface_lost', 'render', 'stop'):
            function = 'coh_wr_presentation_'+name
            start = original.index('CohStatus '+function+'(')
            end = original.index('\n}', start)+2
            body = original[start:end]
            if body.count(GUARD) != 1:
                raise ValueError('missing unique guard in '+function)
            mutant = original[:start]+body.replace(GUARD, '')+original[end:]
            include = temp / 'presentation-mutant.inc'; include.write_text(mutant)
            candidate = temp / 'core-mutant.c'
            candidate.write_text(core.replace('#include "coh_wr_presentation.inc"', '#include "'+str(include)+'"'))
            binary = temp / ('mutation-'+name)
            execute('mutation-'+name+'-build', [os.environ.get('CC', 'cc'), *flags, '-O2', candidate, *sources[1:], '-lm', '-o', binary])
            run = execute('mutation-'+name, [binary], expect_failure=True)
            proof['mutations'][function] = {'removed': GUARD.strip(), 'rejected': True,
                'returncode': run.returncode, 'modified_include_sha256': hashlib.sha256(mutant.encode()).hexdigest()}
    proof['source_inputs_unchanged'] = before == {str(p.relative_to(ROOT)): sha(p) for p in pins}
    if not proof['source_inputs_unchanged']:
        raise ValueError('consumed source changed during focused qualification')
    proof['leak_sanitizer_executed'] = False
    proof['passed'] = True
    (args.output / 'qualification.json').write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps({'passed': True, 'checks_each_mode': proof['modes']['release']['result']['checks'],
                      'modes': list(proof['modes']), 'mutations_rejected': len(proof['mutations'])}))


if __name__ == '__main__':
    main()
