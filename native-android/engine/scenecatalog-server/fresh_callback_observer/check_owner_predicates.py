#!/usr/bin/env python3
"""New host-only differential oracle for the fresh owner's fixed failure atoms."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types
import unittest
import io

HERE = Path(__file__).resolve().parent
MODES = {'release': ['-O2'], 'address': ['-O1', '-fsanitize=address', '-no-pie'],
         'undefined': ['-O1', '-fsanitize=undefined', '-fno-sanitize-recover=all']}
ORIGINALS = (
    'libs/UtilitiesLib/include/utilitieslib/components/ArrayOld.h',
    'MapServer/src/svr/svr_base.h',
    'libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h',
    'Common/entity/gametypes.h', 'Common/entity/entity.h',
    'Common/entity/entity.c', 'Common/entity/character_base.h')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, code):
    if not value:
        raise ValueError('COH_FRESH_OWNER_QUAL_' + code)


def unchanged(admitted):
    require(all(path.read_bytes() == raw for path, raw in admitted.items()), 'SOURCE_CHANGED')


def py_function(raw, name):
    text = raw.decode('utf-8')
    nodes = [n for n in ast.parse(text).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    require(len(nodes) == 1, 'PY_FUNCTION_' + name)
    n = nodes[0]
    return ''.join(text.splitlines(keepends=True)[n.lineno - 1:n.end_lineno])


def c_function(text, name):
    match = re.search(r'^[\w \t*]+\b' + re.escape(name) + r'\s*\([^;{}]*\)\s*\{', text, re.M)
    require(match is not None, 'C_FUNCTION_' + name)
    at = text.index('{', match.start()) + 1
    depth = 1
    while depth:
        depth += (text[at] == '{') - (text[at] == '}')
        at += 1
    return text[match.start():at] + '\n'


def declaration(text, begin, end):
    at = text.index(begin)
    return text[at:text.index(end, at) + len(end)] + '\n'


def original_sources(root):
    result = {}
    for name in ORIGINALS:
        raw = subprocess.run(['git', 'show', 'HEAD:upstream/ouroboros/' + name], cwd=root,
                             check=True, capture_output=True).stdout
        require(b'\r' not in raw.replace(b'\r\n', b'\n'), 'ORIGINAL_NEWLINES')
        result[name] = raw.replace(b'\r\n', b'\n')
        local = root / 'upstream/ouroboros' / name
        if local.exists():
            require(local.read_bytes().replace(b'\r\n', b'\n') == result[name], 'ORIGINAL_CHECKOUT')
    return result


def functions_from_admitted(admitted):
    # Execute ONLY the complete named production functions. No project module's
    # imports, staging, CLI or old qualification is executed by this checker.
    base_path = HERE.parent / 'stage_export.py'
    base = types.SimpleNamespace()
    ns = {'hashlib': hashlib}
    for name in ('require', 'sha', 'lf'):
        exec(compile(py_function(admitted[base_path], name), str(base_path), 'exec'), ns)
        setattr(base, name, ns[name])
    stage_path = HERE / 'stage.py'
    stage_raw = admitted[stage_path]
    pin = re.findall(rb"^OWNER_SHA='([0-9a-f]{64})'$", stage_raw, re.M)
    require(len(pin) == 1, 'OWNER_PIN')
    scope = {'base': base, 'HERE': HERE, 're': re, 'OWNER_SHA': pin[0].decode()}
    unchanged(admitted)
    for node in ast.parse(stage_raw.decode()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                scope[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    # These two actual source assignments select the unchanged old loader guard
    # overlay name. Their modules are inspected, never imported/executed.
    capture = ast.parse(admitted[HERE.parent / 'stage_groups_capture.py'].decode())
    resource = ast.parse(admitted[HERE.parent / 'stage_resources.py'].decode())
    guard_assignment = [n.value for n in capture.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == 'GUARD_IMPL' for t in n.targets)]
    require(len(guard_assignment) == 1 and ast.dump(guard_assignment[0]) ==
            "Attribute(value=Name(id='resources', ctx=Load()), attr='GUARD_IMPL', ctx=Load())", 'GUARD_ASSIGNMENT')
    guard_names = [ast.literal_eval(n.value) for n in resource.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'GUARD_IMPL' for t in n.targets)]
    require(len(guard_names) == 1, 'GUARD_OVERLAY_NAME')
    scope['old'] = types.SimpleNamespace(GUARD_IMPL=guard_names[0])
    for name in ('owner_predicates', 'instrument_owner', 'overlays'):
        exec(compile(py_function(stage_raw, name), str(stage_path), 'exec'), scope)
    unchanged(admitted)
    return scope


def fixture_header(admitted, sources, transformed):
    texts = {k: v.decode() for k, v in sources.items()}
    types_used = []
    for path, begin, end in (
        (ORIGINALS[0], 'typedef struct Array{', '} Array;'),
        (ORIGINALS[2], 'typedef enum NetLinkType', '} NetLinkType;'),
        (ORIGINALS[2], 'typedef enum NetLinkOperationType', '} NetLinkOperationType;'),
        (ORIGINALS[3], 'typedef enum DbFlag', '} DbFlag;')):
        types_used.append(declaration(texts[path], begin, end))
    maxdef = re.search(r'^#define MAX_ENTITIES_PRIVATE\s+\d+[^\n]*', texts[ORIGINALS[3]], re.M).group(0)
    inuse = re.search(r'^#define ENTITY_IN_USE\s+\([^\n]+', texts[ORIGINALS[4]], re.M).group(0)
    freeing = re.search(r'^#define ENTITY_BEING_FREED\s+\([^\n]+', texts[ORIGINALS[4]], re.M).group(0)
    client = declaration(texts[ORIGINALS[1]], 'typedef enum ClientReadyState', '} ClientReadyState;')
    client += declaration(texts[ORIGINALS[1]], 'typedef struct ClientLink', '} ClientLink;')
    shim = admitted[HERE.parent / 'groups_owner_oracle_shim.h'].decode()
    # Retain exactly the existing explicitly source-verified host member subset.
    # Its unrelated source-constructor observers and old tests are not included.
    shim = shim[:shim.index('static unsigned checks,position_calls')]
    globals_at = shim.index('static NetLinkList net_links;')
    shim = shim[:globals_at] + '''
static struct OwnerGlobals {
 union {NetLinkList value;unsigned char separate[512];} links;
 union {int value;unsigned char separate[512];} world;
 union {int value;unsigned char separate[512];} maximum;
 union {Entity *value[MAX_ENTITIES_PRIVATE];unsigned char extra[sizeof(Entity*)*MAX_ENTITIES_PRIVATE+512];} table;
 union {U8 value[MAX_ENTITIES_PRIVATE];unsigned char extra[MAX_ENTITIES_PRIVATE+512];} state;
} owner_globals;
#define net_links owner_globals.links.value
#define world_id owner_globals.world.value
#define entities_max owner_globals.maximum.value
#define entities owner_globals.table.value
#define entity_state owner_globals.state.value
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"fresh owner check line %d: %s\\n",__LINE__,#x);abort();}}while(0)
#define INLINEDBG inline
'''
    shim = shim.replace('/* ORIGINAL_TYPES */', '\n'.join(types_used + [maxdef, inuse, freeing]))
    shim = shim.replace('/* ORIGINAL_CLIENT_LINK */', client)
    header = shim + c_function(texts[ORIGINALS[6]], 'character_IsInitialized')
    header += c_function(texts[ORIGINALS[5]], 'entInUse')
    header += '\n#include "coh_fresh_source_profile_api.h"\n'
    group = admitted[HERE / 'source_group_profile.inc'].decode()
    header += '''
/* Only the owner/thread primitive is a single-thread host stub; latch body is
 * unchanged original fresh-profile C and does not perform any native call. */
typedef int32_t LONG;typedef uint32_t DWORD;
static LONG coh_fp_thread;static DWORD current_thread;
static unsigned coh_fp_entered,coh_fp_complete;
static CohFreshOwnerFailure coh_fp_owner_failure;
static LONG InterlockedCompareExchange(volatile LONG *p,LONG exchange,LONG compare){LONG old=*p;if(old==compare)*p=exchange;return old;}
static DWORD GetCurrentThreadId(void){return current_thread;}
'''
    header += c_function(group, 'coh_fp_owner')
    header += '#define coh_fresh_source_owner_failed original_latch\n'
    header += c_function(group, 'coh_fresh_source_owner_failed')
    header += '#undef coh_fresh_source_owner_failed\n'
    header += '''
static unsigned trace_count,trace_ids[131120];static int trace_values[131120];
int coh_fresh_source_owner_failed(int value,CohFreshOwnerFailure reason){
 CHECK(trace_count<131120);trace_ids[trace_count]=(unsigned)reason;trace_values[trace_count++]=value;
 return original_latch(value,reason);
}
'''
    header += '#define coh_source_groups_prepare_owner original_prepare\n'
    header += admitted[HERE.parent / 'source_groups_owner.inc'].decode()
    header += '\n#undef coh_source_groups_prepare_owner\n#define coh_source_groups_prepare_owner fresh_prepare\n'
    header += c_function(transformed.decode(), 'coh_source_groups_prepare_owner')
    header += '\n#undef coh_source_groups_prepare_owner\n'
    return header.encode(), {
        'character_IsInitialized': sha(c_function(texts[ORIGINALS[6]], 'character_IsInitialized').encode()),
        'entInUse': sha(c_function(texts[ORIGINALS[5]], 'entInUse').encode()),
        'fresh_owner_thread': sha(c_function(group, 'coh_fp_owner').encode()),
        'fresh_owner_latch': sha(c_function(group, 'coh_fresh_source_owner_failed').encode())}


def process(command, admitted, *, timeout=120):
    unchanged(admitted)
    value = subprocess.run(list(map(str, command)), capture_output=True, timeout=timeout,
                           env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
                                    UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
    unchanged(admitted)
    return value


def mutation_controls(args, output, admitted, header, rows):
    prefix, tail = header.split(b'#define coh_source_groups_prepare_owner fresh_prepare\n', 1)
    name, atom = rows[0]
    first = b'coh_fresh_source_owner_failed((' + atom + b'),COH_FRESH_OWNER_' + name.encode() + b')'
    require(tail.count(first) == 1, 'MUTATION_ANCHOR')
    variants = {
        'duplicate_atom_evaluation': prefix + b'#define coh_source_groups_prepare_owner fresh_prepare\n' +
            tail.replace(first, b'(' + first + b'||' + first + b')', 1),
        'wrong_first_reason': prefix + b'#define coh_source_groups_prepare_owner fresh_prepare\n' +
            tail.replace(first, first.replace(b'COH_FRESH_OWNER_INPUT_LINK', b'COH_FRESH_OWNER_INPUT_OUTPUT'), 1),
        'refusal_return_changed': prefix + b'#define coh_source_groups_prepare_owner fresh_prepare\n' +
            tail.replace(b')return 0;', b')return 1;', 1),
        'first_latch_overwritten': header.replace(b'coh_fp_owner_failure==COH_FRESH_OWNER_NONE', b'1', 1),
        'output_written_before_validation': prefix + b'#define coh_source_groups_prepare_owner fresh_prepare\n' +
            tail.replace(b' const ClientLink*client;', b' memset(out,0,sizeof(*out));\n const ClientLink*client;', 1)}
    receipts = {}
    for name, mutated in variants.items():
        require(mutated != header, 'MUTATION_UNCHANGED_' + name)
        work = output / ('mutation-' + name);work.mkdir(mode=0o700)
        (work / 'owner_fixture.h').write_bytes(mutated)
        for target, source in [('test.c', 'test_owner_predicates.c'),
                               ('coh_fresh_source_profile_api.h', 'source_group_profile_api.h'),
                               ('coh_fresh_folder_profile_api.h', 'source_folder_profile_api.h')]:
            (work / target).write_bytes(admitted[HERE / source])
        binary = work / 'test-owner-predicates'
        built = process([args.cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-pedantic',
                         '-I', work, work / 'test.c', '-o', binary], admitted)
        require(built.returncode == 0, 'MUTATION_BUILD_' + name)
        tested = process([binary], admitted, timeout=30)
        require(tested.returncode != 0, 'MUTATION_SURVIVED_' + name)
        receipts[name] = {'compiled': True, 'refused_by_new_controls': True,
                          'mutated_header_sha256': sha(mutated)}
    return receipts


def admitted_module(name, path, admitted):
    unchanged(admitted)
    require(name not in sys.modules, 'MODULE_ALREADY_LOADED')
    module = types.ModuleType(name);module.__file__ = str(path)
    sys.modules[name] = module
    try:
        exec(compile(admitted[path], str(path), 'exec'), module.__dict__)
    finally:
        unchanged(admitted)
    return module


def emitter_controls(args, output, admitted, stage):
    probe = admitted_module('probe', HERE / 'probe.py', admitted)
    modes = {}
    overlays = stage['overlays'](args.source_root)
    unchanged(admitted)
    for mode, flags in MODES.items():
        work = output / ('emitter-' + mode);work.mkdir(mode=0o700)
        for name, raw in overlays.items():
            path = work / name;path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(raw)
        (work / 'test.c').write_bytes(admitted[HERE / 'test_profile.c'])
        includes = sum((['-I', work / n] for n in ('libs/UtilitiesLib/src/utils', 'Common/seq', 'MapServer/src/group')), [])
        binary = work / 'test-owner-emitter'
        built = process([args.cc, '-std=c11', '-g', '-Wall', '-Wextra', '-Werror', '-pedantic',
                         '-pthread', *flags, *includes, work / 'test.c', '-o', binary], admitted)
        (work / 'build.stdout').write_bytes(built.stdout);(work / 'build.stderr').write_bytes(built.stderr)
        require(built.returncode == 0, 'EMITTER_BUILD_' + mode)
        before = binary.read_bytes()
        tested = process([binary, '--owner-reason'], admitted, timeout=30)
        require(binary.read_bytes() == before, 'EMITTER_BINARY_CHANGED')
        (work / 'stdout.json').write_bytes(tested.stdout);(work / 'stderr.txt').write_bytes(tested.stderr)
        require(tested.returncode == 0 and not tested.stderr, 'EMITTER_RUN_' + mode)
        result = json.loads(tested.stdout)
        require(result['passed'] is True and type(result['probe']) is dict and
                result['owner_reason_cases'] == 47 and result['old_profile_scenarios_replayed'] is False and
                result['real_server'] is False and result['world_authority'] is False, 'EMITTER_CONTROLS_' + mode)
        parsed = probe.parse((json.dumps(result['probe'], separators=(',', ':')) + '\n').encode('ascii'))
        require(parsed == result['probe'] and parsed['owner_failure'] == 'CLIENT_INCIDENCE' and
                parsed['source_generation_admitted'] is False and parsed['world_authority'] is False, 'EMITTER_PARSE_' + mode)
        modes[mode] = {'controls': {k: v for k, v in result.items() if k != 'probe'},
                       'parsed_owner_failure': parsed['owner_failure'], 'exact_emitter_object_parsed': True,
                       'binary_sha256': sha(before), 'binary_bytes': len(before)}
    require(all(v['controls'] == modes['release']['controls'] for v in modes.values()), 'EMITTER_MODES')
    # Import the finite stage-helper chain from admitted byte buffers in
    # dependency order. No staging CLI or old qualification is invoked.
    for name in ('stage_export', 'stage_groups_boundary', 'stage_snapshot',
                 'stage_resources', 'stage_groups_capture'):
        admitted_module(name, HERE.parent / (name + '.py'), admitted)
    admitted_module('stage', HERE / 'stage.py', admitted)
    tests = admitted_module('coh_fresh_owner_probe_tests', HERE / 'test_probe.py', admitted)
    transform_tests = admitted_module('coh_fresh_owner_stage_tests', HERE / 'test_stage.py', admitted)
    probe_names = ('test_exact_source_emitter_schema_and_fixed_names',
                   'test_strict_parser_types_keys_enums_and_source_bounds',
                   'test_owner_reason_v2_fixed_vocabulary_and_no_legacy_normalization',
                   'test_actual_owned_child_owner_reason_projection_excludes_private_binding')
    stage_names = ('test_exact_hook_positions_and_preserved_old_group',
                   'test_crlf_staged_sources_preserve_raw_line_endings',
                   'test_synthetic_source_reconstruction_and_every_final_byte',
                   'test_owner_atom_order_reversibility_and_changed_table_refusal')
    suite = unittest.TestSuite([*(tests.ProbeTests(name) for name in probe_names),
                               *(transform_tests.Controls(name) for name in stage_names)])
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (output / 'targeted-parser-tests.txt').write_text(log.getvalue())
    require(result.wasSuccessful() and result.testsRun == 8, 'TARGETED_PARSER_TESTS')
    unchanged(admitted)
    return {'modes': modes, 'targeted_probe_methods': list(probe_names),
            'targeted_stage_methods': list(stage_names), 'targeted_python_method_count': 8,
            'actual_map_executed': False, 'source_win32_io_stubs': True,
            'original_foldercache_executed': False, 'old_profile_scenarios_replayed': False}


def run(args):
    root = args.source_root.resolve(strict=True)
    require(HERE == root / 'native-android/engine/scenecatalog-server/fresh_callback_observer', 'OWN_ROOT')
    output = args.output.absolute()
    require(not output.exists() and not output.is_symlink(), 'OUTPUT_EXISTS')
    paths = [Path(__file__).resolve(), HERE / 'test_owner_predicates.c', HERE / 'stage.py',
             HERE / 'source_group_profile_api.h', HERE / 'source_group_profile.inc',
             HERE / 'source_folder_profile_api.h', HERE.parent / 'source_groups_owner.inc',
             HERE.parent / 'groups_owner_oracle_shim.h', HERE.parent / 'groups-owner-source-pins.json',
             HERE.parent / 'stage_export.py', HERE / 'test_profile.c', HERE / 'probe.py',
             HERE / 'test_probe.py', HERE / 'source_folder_profile.inc',
             HERE / 'source_sealed_quiescence.inc', HERE.parent / 'source_resource_quiescence.inc',
             HERE.parent / 'stage_groups_capture.py', HERE.parent / 'stage_resources.py',
             HERE / 'test_stage.py', HERE.parent / 'stage_snapshot.py',
             HERE.parent / 'stage_groups_boundary.py', HERE.parent / 'resource-source-pins.json',
             HERE / 'README.md', HERE / 'OWNER_FAILURE_DIAGNOSTIC.md',
             HERE.parent / 'SOURCE_PROFILE_RUNTIME.md']
    # Full read-only inline supplier closure used by the new deterministic
    # transform controls; none of their old qualifiers is executed.
    paths += list(HERE.parent.glob('*.inc'))
    paths += [HERE.parent.parent / 'scenecatalog/source_export.inc']
    staged_originals = (
        'MapServer/src/group/groupnetsend.c', 'MapServer/src/svr/svr_init.c',
        'Common/seq/anim.c', 'libs/UtilitiesLib/src/utils/FolderCache.c')
    paths += [root / 'upstream/ouroboros' / n for n in staged_originals]
    admitted = {p: p.read_bytes() for p in paths}
    for name in staged_originals:
        tracked = subprocess.run(['git', 'show', 'HEAD:upstream/ouroboros/' + name], cwd=root,
                                 check=True, capture_output=True).stdout
        require(tracked.replace(b'\r\n', b'\n') ==
                admitted[root / 'upstream/ouroboros' / name].replace(b'\r\n', b'\n'), 'STAGED_ORIGINAL_GIT')
    sources = original_sources(root)
    oldpins = json.loads(admitted[HERE.parent / 'groups-owner-source-pins.json'])['original_sha256_lf']
    require(all(oldpins[n] == sha(b) for n, b in sources.items()), 'ORIGINAL_PINS')
    stage = functions_from_admitted(admitted)
    rows = stage['owner_predicates']()
    raw = admitted[HERE.parent / 'source_groups_owner.inc']
    transformed = stage['instrument_owner'](raw)
    require(len(rows) == 47 and transformed != raw, 'TRANSFORM')
    # An independent textual reversal proves no other original owner byte was
    # replaced, including the candidate commit, return0 and short-circuit order.
    reversed_raw = transformed
    for name, atom in rows:
        wrapper = b'coh_fresh_source_owner_failed((' + atom + b'),COH_FRESH_OWNER_' + name.encode() + b')'
        require(reversed_raw.count(wrapper) == 1, 'WRAP_ONCE_' + name)
        reversed_raw = reversed_raw.replace(wrapper, atom, 1)
    require(reversed_raw == raw, 'EXACT_REVERSAL')
    header, functions = fixture_header(admitted, sources, transformed)
    output.mkdir(mode=0o700, parents=True)
    compiler = process([args.cc, '--version'], admitted)
    require(compiler.returncode == 0, 'COMPILER')
    modes = {}
    for mode, flags in MODES.items():
        work = output / mode;work.mkdir(mode=0o700)
        (work / 'owner_fixture.h').write_bytes(header)
        (work / 'test.c').write_bytes(admitted[HERE / 'test_owner_predicates.c'])
        (work / 'coh_fresh_source_profile_api.h').write_bytes(admitted[HERE / 'source_group_profile_api.h'])
        (work / 'coh_fresh_folder_profile_api.h').write_bytes(admitted[HERE / 'source_folder_profile_api.h'])
        binary = work / 'test-owner-predicates'
        command = [args.cc, '-std=c11', '-g', '-Wall', '-Wextra', '-Werror', '-pedantic',
                   '-fstack-usage', *flags, '-I', work, work / 'test.c', '-o', binary]
        built = process(command, admitted)
        (work / 'build.stdout').write_bytes(built.stdout);(work / 'build.stderr').write_bytes(built.stderr)
        require(built.returncode == 0, 'BUILD_' + mode)
        executable = binary.read_bytes()
        tested = process([binary], admitted, timeout=30)
        require(binary.read_bytes() == executable, 'BINARY_CHANGED')
        (work / 'stdout.json').write_bytes(tested.stdout);(work / 'stderr.txt').write_bytes(tested.stderr)
        require(tested.returncode == 0 and not tested.stderr, 'RUN_' + mode)
        result = json.loads(tested.stdout)
        require(result['passed'] is True and result['first_failure_atoms'] == 47 and
                result['latch_controls'] == 7 and result['short_circuit_controls'] == 3, 'CONTROLS_' + mode)
        stack = {}
        for row in (work / 'test-owner-predicates-test.su').read_text().splitlines():
            location, size, kind = row.split('\t')
            require('unbounded' not in kind, 'STACK')
            name = location.rsplit(':', 1)[-1]
            if name in ('original_prepare', 'fresh_prepare', 'original_latch', 'coh_fresh_source_owner_failed', 'coh_fp_owner'):
                stack[name] = int(size)
        modes[mode] = {'controls': result, 'flags': flags, 'binary_bytes': len(executable),
                       'binary_sha256': sha(executable), 'stack_frames': stack}
    require(all(m['controls'] == modes['release']['controls'] for m in modes.values()), 'MODE_RESULT')
    mutations = mutation_controls(args, output, admitted, header, rows)
    emitter = emitter_controls(args, output, admitted, stage)
    unchanged(admitted)
    require(original_sources(root) == sources, 'ORIGINAL_CHANGED')
    receipt = {'schema': 'coh-fresh-owner-predicates-host-v1', 'passed': True,
               'source_sha256': {str(p.relative_to(root)): sha(b) for p, b in admitted.items()},
               'original_sha256_lf': {n: sha(b) for n, b in sources.items()},
               'whole_function_sha256_lf': functions,
               'predicate_names_in_source_order': [n for n, _ in rows],
               'original_owner_sha256': sha(raw), 'instrumented_owner_sha256': sha(transformed),
               'generated_host_header_sha256': sha(header), 'modes': modes,
               'mutations': mutations,
               'new_owner_emitter_and_parser': emitter,
               'compiler': compiler.stdout.decode().splitlines()[0],
               'exact_reverse_to_original_bytes': True, 'production_transform_functions_executed_unchanged': True,
               'old_qualification_replayed': False, 'original_win32_layout_qualified': False,
               'host_member_subset_storage_only': True, 'owner_thread_primitive_host_stub': True,
               'leak_sanitizer_qualified': False, 'actual_windows_executed': False,
               'runtime_executed': False, 'source_generation_admitted': False, 'world_authority': False}
    with (output / 'owner-predicates.json').open('xb') as stream:
        stream.write((json.dumps(receipt, indent=2, sort_keys=True) + '\n').encode('utf-8'))
        stream.flush();os.fsync(stream.fileno())
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cc', default='cc')
    value = run(parser.parse_args())
    print(json.dumps({'passed': True, 'schema': value['schema'],
                      'controls': value['modes']['release']['controls']}))
