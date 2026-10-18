#!/usr/bin/env python3
"""NEW public-session creation/retirement qualification; controlled UDP peers only."""
from pathlib import Path
import argparse, gzip, hashlib, importlib.abc, importlib.util, json, os, re, shlex, subprocess, sys
HERE = Path(__file__).resolve().parent
AUDIT_COMMIT = 'c7e4e30c2d9c8b258e7405683086c48a5bd0f069'
AUDIT_PATH = 'native-android/engine/auth-interop/evidence/fresh-character-source-scope-20261018/audit.json'
AUDIT_SHA = 'f8bcd25456f75ddcf1fc95e41ed05419871d13a15eadaa2a197e5be99b164a7f'
BASELINE = '396621362fb55ef5a424f86d8d0e4fad549e58a2'
def need(value, reason):
    if not value: raise ValueError(reason)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def run(argv, **kwargs):
    p = subprocess.run(list(map(str, argv)), capture_output=True, text=True, timeout=120, **kwargs)
    need(p.returncode == 0, 'NEW focused command failed\n' + p.stdout + p.stderr)
    return p.stdout
def git(root, *args): return subprocess.check_output(['git', '-C', str(root), *args])
def functions(raw):
    """Mask comments/literals, preserving offsets, then isolate complete C bodies."""
    text = raw.decode(); masked = list(text); i = 0
    while i < len(text):
        if text.startswith('//', i):
            end = text.find('\n', i); end = len(text) if end < 0 else end
        elif text.startswith('/*', i):
            end = text.find('*/', i + 2); need(end >= 0, 'unterminated C comment'); end += 2
        elif text[i] in '\"\'':
            quote = text[i]; end = i + 1
            while end < len(text):
                if text[end] == '\\': end += 2; continue
                if text[end] == quote: end += 1; break
                end += 1
        else: i += 1; continue
        for j in range(i, min(end, len(text))):
            if text[j] != '\n': masked[j] = ' '
        i = end
    masked = ''.join(masked); result = {}
    for match in re.finditer(r'(?m)^([\w *]+\b([A-Za-z_]\w*)\s*\([^;{}]*\))\s*\{', masked):
        start = match.start(); cursor = match.end(); depth = 1
        while depth:
            need(cursor < len(masked), 'unterminated C body')
            depth += (masked[cursor] == '{') - (masked[cursor] == '}'); cursor += 1
        result[match[2]] = raw[start:cursor]
    return result

def main():
    need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'), 'Python optimization unsupported')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args(); root = args.source_root.resolve(strict=True); native = root / 'native-android'
    need(HERE == native / 'engine/dbclient', 'checker must belong to selected source checkout')
    need(not args.output.exists() and not args.output.is_symlink(), 'fresh qualification directory required')
    revision = git(root, 'rev-parse', 'HEAD').decode().strip()
    project = [HERE / 'coh_db_session.c', HERE / 'coh_db_account_controls.c', HERE / 'coh_dbclient.c',
               native / 'engine/auth/coh_auth.c', native / 'protocol/coh_protocol.c', native / 'src/coh_blowfish.c',
               *[native / 'engine/network' / n for n in ('coh_net.c','coh_net_frame.c','coh_net_udp.c','coh_net_zip.c')]]
    test = HERE / 'tests/test_empty_creation.c'; oracle = HERE / 'empty_creation_oracle.py'
    files = set(project + [test, oracle, Path(__file__).resolve(), HERE / 'EMPTY_CREATION.md',
                           HERE / 'check.py', HERE / 'source-pins.json',
                           native / 'tools/protocol_fixture/prepare.py', native / 'engine/coh_contracts.h',
                           native / 'src/byte_reader.h', native / 'protocol/coh_protocol.h',
                           HERE / 'qualification/account-inventory-396621362.json.gz'])
    for directory in (HERE, native / 'engine/auth', native / 'engine/network', native / 'include'):
        files.update(directory.glob('*.h'))
    for name in json.loads((HERE / 'source-pins.json').read_bytes())['sha256_lf']:
        files.add(root / 'upstream/ouroboros' / name)
    audit_raw = git(root, 'show', AUDIT_COMMIT + ':' + AUDIT_PATH)
    need(len(audit_raw) == 15606 and sha(audit_raw) == AUDIT_SHA, 'fixed original creation audit')
    audit = json.loads(audit_raw)
    for name, pin in audit['source_files'].items():
        old = git(root, 'show', AUDIT_COMMIT + ':' + name)
        need(len(old) == pin['bytes'] and sha(old) == pin['sha256'], 'historical audit Git input')
        if name.startswith('upstream/'):
            need((root / name).read_bytes() == old, 'original creation source changed')
            files.add(root / name)
    original_spans = 0
    for name, entries in audit['whole_function_spans'].items():
        old = git(root, 'show', AUDIT_COMMIT + ':' + name).replace(b'\r\n', b'\n')
        for function, pin in entries.items():
            span = old[pin['offset']:pin['offset'] + pin['bytes']]
            need(sha(span) == pin['sha256'] and old[:pin['offset']].count(b'\n') + 1 == pin['line'], 'original audit function span')
            original_spans += 1
    need(original_spans == 43, 'complete original creation function audit')
    previous_raw = gzip.decompress((HERE / 'qualification/account-inventory-396621362.json.gz').read_bytes())
    previous = json.loads(previous_raw); transitions = {}
    core = {'native-android/engine/dbclient/coh_db_session.c', 'native-android/engine/dbclient/coh_db_session.h'}
    for name, digest in previous['source_sha256'].items():
        files.add(root / name)
        old = git(root, 'show', BASELINE + ':' + name)
        need(sha(old) == digest, 'historical C50 source pin')
        if name in core: transitions[name] = {'historical_sha256': digest, 'current_sha256': sha((root / name).read_bytes())}
        else: need(sha((root / name).read_bytes()) == digest, 'unapproved C50 source transition')
    need(len(transitions) == 2, 'exact two C50 transitions')
    before_functions = functions(git(root, 'show', BASELINE + ':native-android/engine/dbclient/coh_db_session.c'))
    after_functions = functions((HERE / 'coh_db_session.c').read_bytes())
    changed = {name for name, body in before_functions.items() if after_functions.get(name) != body}
    need(changed == {'forget','coh_db_session_take_handoff','coh_db_session_take_handoff_owner_alloc'}, 'exact prior function changes')
    unchanged = {name: sha(body) for name, body in before_functions.items() if name not in changed}
    need(set(after_functions) - set(before_functions) == {'coh_db_session_create_empty','coh_db_session_retire_created_offer'}, 'exact two new functions')
    frozen = {p.resolve(): p.read_bytes() for p in files}
    def committed():
        need(git(root, 'rev-parse', 'HEAD').decode().strip() == revision, 'HEAD changed')
        for path, raw in frozen.items():
            need(path.read_bytes() == raw and git(root, 'show', revision + ':' + str(path.relative_to(root))) == raw, 'source differs from frozen committed input')
    committed()
    args.output.mkdir(mode=0o700); work = args.output.resolve(); fixture_dir = work / 'fixture'; fixture_dir.mkdir(mode=0o700)
    loaded = []; original_spec = importlib.util.spec_from_file_location
    class Loader(importlib.abc.Loader):
        def __init__(self, path): self.path = path
        def create_module(self, spec): return None
        def exec_module(self, module):
            committed(); need(self.path in frozen and self.path.suffix == '.py', 'unadmitted project helper')
            module.__file__ = str(self.path); module.__cached__ = None
            exec(compile(frozen[self.path], str(self.path), 'exec', dont_inherit=True), module.__dict__)
            loaded.append(str(self.path.relative_to(root))); committed()
    def spec(name, path, *a, **kw):
        path = Path(path).resolve()
        return original_spec(name, path, loader=Loader(path)) if path.is_relative_to(root) else original_spec(name, path, *a, **kw)
    importlib.util.spec_from_file_location = spec
    try:
        module_spec = spec('new_empty_creation_fixture', oracle); helper = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(helper)
        oracle_proof = helper.produce(root, fixture_dir)
    finally: importlib.util.spec_from_file_location = original_spec
    fixture = fixture_dir / 'empty-creation-fixtures.h'; fixture_raw = fixture.read_bytes()
    flags = ['-std=c99','-pedantic','-Wall','-Wextra','-Werror','-fstack-usage','-I'+str(native/'include'),'-I'+str(fixture_dir)]
    dependencies = set()
    for source in [*project, test]:
        words = run(['cc',*flags,'-MM',source]).replace('\\\n',' ').split(':', 1)[1]
        for name in shlex.split(words):
            path = Path(name).resolve(); need(path in frozen or path == fixture, 'compiled project dependency outside admitted closure'); dependencies.add(path)
    modes = [('release',['-O2'])]
    if args.sanitize: modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    results = {}; elfs = {}; stack = {}
    for mode, options in modes:
        committed(); need(fixture.read_bytes() == fixture_raw, 'fixture changed'); objects = []
        for i, source in enumerate(project):
            target = work / (mode + '-' + str(i) + '.o')
            run(['cc',*flags,*options,*(['-O0'] if source.name in ('coh_protocol.c','coh_blowfish.c','coh_auth.c') else []),'-c',source,'-o',target]); objects.append(target)
        exe = work / ('empty-creation-' + mode)
        run(['cc',*flags,*options,test,*objects,*['-Wl,--wrap='+n for n in ('malloc','calloc','free','close','coh_net_udp_queue')],'-lz','-lm','-o',exe])
        binary = exe.read_bytes(); raw_result = run([exe], env=env)
        need(exe.read_bytes() == binary and fixture.read_bytes() == fixture_raw, 'executable/fixture mutated during focused run'); committed()
        (work / (mode + '-result.json')).write_text(raw_result)
        result = json.loads(raw_result); need(result.get('passed') is True and result['project_live_allocations'] == 0, 'focused public transaction failed')
        results[mode] = result; elfs[mode] = {'bytes':len(binary),'sha256':sha(binary),'file':exe.name}
        stack[mode] = [line for path in sorted(work.glob(mode+'*.su')) for line in path.read_text().splitlines() if 'coh_db_session.c:' in line]
    need(all(value == results['release'] for value in results.values()), 'cross-mode transaction disagreement'); committed()
    proof = {'schema':'coh-db-empty-creation-focused-tests-v1','passed':True,'source_revision':revision,
      'source_sha256':{str(p.relative_to(root)):sha(raw) for p,raw in sorted(frozen.items())},'all_inputs_equal_committed_HEAD':True,
      'project_compilation_inputs':len(project)+1,'compiler_dependency_sha256':{str(p.relative_to(root)):sha(frozen[p]) for p in sorted(dependencies) if p in frozen},
      'loaded_frozen_helpers':loaded,'original_fixture':oracle_proof,'original_creation_audit':{'commit':AUDIT_COMMIT,'path':AUDIT_PATH,'bytes':len(audit_raw),'sha256':AUDIT_SHA,'files':27,'whole_function_spans':original_spans,'executed_as_code':False},
      'C50_historical_core_transitions':transitions,'C50_other_48_source_pins_unchanged':True,'unchanged_prior_session_function_sha256':unchanged,
      'modes':results,'binaries':elfs,'session_stack_usage_rows':stack,'fixture_header':{'bytes':len(fixture_raw),'sha256':sha(fixture_raw)},
      'scope':{'only_new_focused_entrypoint_executed':True,'old_suites_executed':False,'real_controlled_loopback_UDP_queue_and_parser':True,'synthetic_Auth_receipts':True,'encryption_enabled':False,'actual_Auth_DB_Map_SQL':False,'private_handoff_setter_or_session_struct_access':False,'server_allocation_and_SQL_rollback_observed':False,'persistent_row_model_is_only_a_synthetic_nonrollback_control':True,'selection_counter_overflow_canonically_unreachable_with_zero_lifetime_choices':True,'request_uintmax_controls_are_mismatches_not_private_overflow_injection':True,'single_owner_nonreentrant_contract':True,'cancel_and_close_reentry_probes_are_only_handoff_guards':True,'global_aggregate_budget_or_RSS_admitted':False,'source_generation_admitted':False,'world_authority':False,'ACK_authority':False,'leak_sanitizer_enabled':False},
      'compiler':run(['cc','--version']).splitlines()[0],'python_optimization_refused':True}
    raw = (json.dumps(proof,indent=2)+'\n').encode()
    with (work/'proof.json').open('xb') as output: output.write(raw)
    committed(); print(json.dumps({'passed':True,'source_inputs':len(frozen),'proof_sha256':sha(raw),'modes':results}))
if __name__ == '__main__': main()
