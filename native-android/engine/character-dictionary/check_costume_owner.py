#!/usr/bin/env python3
"""Source-pinned immutable candidate/lifetime qualification; no runtime admission."""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def sha(data): return hashlib.sha256(data).hexdigest()
def run(command, work, stem, env=None):
    r = subprocess.run(list(map(str, command)), capture_output=True, text=True, env=env, timeout=240)
    for kind, text in [('command.json', json.dumps(list(map(str, command)))), ('stdout', r.stdout), ('stderr', r.stderr)]:
        (work / (stem + '.' + kind)).write_text(text)
    if r.returncode: raise RuntimeError(f'{stem}: exit {r.returncode}\n{r.stderr[-3000:]}{r.stdout[-1000:]}')
    return r.stdout
def main():
    p = argparse.ArgumentParser(); p.add_argument('--source-root', type=Path, default=ROOT)
    p.add_argument('--work', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); work = a.work.resolve(); work.mkdir(parents=True, exist_ok=False)
    pinfile = HERE / '../costume-import/source-pins.json'; expected = json.loads(pinfile.read_text())
    source = a.source_root.resolve() / 'upstream/ouroboros'
    texts = {name: (source / name).read_text().replace('\r\n', '\n') for name in expected['sha256_lf']}
    assert {n: sha(v.encode()) for n, v in texts.items()} == expected['sha256_lf']
    h, c = texts['Common/entity/costume.h'], texts['Common/entity/costume.c']
    definitions = [re.search(r'typedef enum BodyType\b.*?} BodyType;', h, re.S).group(),
                   re.search(r'typedef struct BodyTypeInfo\b.*?} BodyTypeInfo;', h, re.S).group(),
                   re.search(r'BodyTypeInfo g_BodyTypeInfos\[\]\s*=.*?\n};', c, re.S).group()]
    data = '\n\n'.join(definitions) + '\n'
    generated = '/* Exact LF-normalized original source declarations, retained as data only. */\nstatic const char bodytype_definitions[] =\n' + ''.join(json.dumps(line + '\n') + '\n' for line in data.splitlines()) + ';\n'
    assert (HERE / 'costume_owner_bodytypes.inc').read_text() == generated
    getter = re.search(r'^int getBodyTypeCount\(void\)\s*\{.*?^\}', c, re.S | re.M)
    if getter is None: getter = re.search(r'^[^\n]*\bgetBodyTypeCount\([^)]*\)\s*\{.*?^\}', c, re.S | re.M)
    assert getter is not None
    code = '#include <stddef.h>\n#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))\n' + '\n'.join(definitions) + '\n' + getter.group() + '\nint main(void){return getBodyTypeCount()!=9;}\n'
    (work / 'original-bodytypes.c').write_text(code)
    run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', work/'original-bodytypes.c', '-o', work/'original-bodytypes'], work, 'source-bodytype-compile')
    run([work/'original-bodytypes'], work, 'source-bodytype-run')
    sources = [HERE/'coh_costume_owner.c', HERE/'../costume-import/coh_costume_import.c', HERE/'../entities/coh_costume.c', HERE/'../replication/coh_replication.c']
    files = [*sources, HERE/'coh_costume_owner.h', HERE/'test_costume_owner.c', HERE/'costume_owner_bodytypes.inc', Path(__file__), pinfile,
             HERE/'../costume-import/coh_costume_import.h', HERE/'../costume-import/source_id.h', HERE/'../entities/coh_costume.h', HERE/'../entities/coh_entities.h',
             HERE/'../replication/coh_replication.h', HERE/'../coh_contracts.h', HERE/'../costume-export/source_body_witness.inc']
    before = {str(v.resolve().relative_to(ROOT)): sha(v.read_bytes()) for v in files}
    proof = {'schema': 'coh-costume-owner-candidate-v1', 'source_head': run(['git', '-C', ROOT, 'rev-parse', 'HEAD'], work, 'head').strip(),
             'source_provenance': expected, 'bodytype_definition_sha256': sha(data.encode()), 'original_bodytype_count': 9,
             'input_sha256': before, 'native': {}, 'compiler': run(['cc', '--version'], work, 'compiler').splitlines()[0]}
    for mode, flags in [('release', ['-O2', '-fstack-usage']), ('asan', ['-O1', '-g', '-fsanitize=address', '-fno-omit-frame-pointer']),
                        ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        target = work/mode; target.mkdir(); binary = target/'owner'
        run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic', *flags, *sources, HERE/'test_costume_owner.c', '-Wl,--wrap=calloc', '-Wl,--wrap=free', '-lcrypto', '-lm', '-o', binary], target, 'compile')
        env = os.environ.copy(); env.update(ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
        result = json.loads(run([binary], target, 'native', env)); result['binary_sha256'] = sha(binary.read_bytes())
        assert result['passed'] and not result['runtime_admitted']; proof['native'][mode] = result
    frames = []
    for path in (work/'release').glob('*.su'):
        for line in path.read_text().splitlines():
            name, size, kind = line.split('\t')
            if 'coh_costume_owner.c:' in name:
                assert kind in ('static', 'dynamic,bounded'); frames.append({'function': name.rsplit(':',1)[-1], 'bytes': int(size), 'kind': kind})
    assert frames and sum(v['bytes'] for v in frames) <= 16384
    proof['memory'] = {'owner_frame_conservative_sum': sum(v['bytes'] for v in frames), 'wrapper_stack_reserve': 16384, 'frames': frames,
                       'importer_stack_reserve_separate': 16384, 'ceiling_bytes': 8388608, 'whole_process_RSS_PSS': None,
                       'borrowed_source_or_runtime_owner': 'unavailable; not admitted', 'external_crypto_sanitizer_stack_closure': False,
                       'leak_sanitizer_executed': False, 'actual_owned_allocations_balanced_excluding_injected_failures': True}
    assert before == {str(v.resolve().relative_to(ROOT)): sha(v.read_bytes()) for v in files}
    proof.update(passed=True, source_stable_before_after=True, authentic_runtime_lease_available=False, current_server_catalog_admitted=False,
                 actual_rows_dictionary_generation_relation_verified=False, android_executed=False, application_ACK=False,
                 scope='Complete immutable candidate bytes/slot integrity and explicit data leases only; production query always refuses without authentic producer lease.')
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps({'passed':True, 'checks':{m:v['checks'] for m,v in proof['native'].items()}, 'output':str(a.output)}))
if __name__ == '__main__': main()
