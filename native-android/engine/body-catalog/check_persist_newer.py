#!/usr/bin/env python3
"""One bounded original ParserIsPersistNewer production/header qualification."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
_spec = importlib.util.spec_from_file_location('persist_schema_crc_helpers', HERE / 'check_schema_crc.py')
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
sha, canonical, run, module, compiler, array = (_schema.sha, _schema.canonical, _schema.run,
                                               _schema.module, _schema.compiler, _schema.array)


def fixtures(root, work):
    status = {name: int(value) for name, value in re.findall(r'(COH_[A-Z_]+)\s*=\s*([0-9]+)',
              (root / 'native-android/engine/coh_contracts.h').read_text())}
    if not all(name in status for name in ('COH_OK', 'COH_INVALID', 'COH_LIMIT', 'COH_UNSUPPORTED')):
        raise ValueError('Native status ABI absent')
    archive = root / _schema.ARCHIVE
    packed = archive.read_bytes()
    if (len(packed) != 2253704 or sha(packed) != _schema.ARCHIVE_SHA or
            run(['git', '-C', root, 'rev-parse', 'HEAD:' + _schema.ARCHIVE]).stdout.strip() != _schema.ARCHIVE_BLOB):
        raise ValueError('Exact retained CLIENT archive changed')
    with zipfile.ZipFile(archive) as z:
        inventory = {'data/bin/BodyParts.bin': 2584, 'data/bin/costume.bin': 17691352,
                     'data/bin/supergroupColors.bin': 2664}
        members = z.infolist()
        if (len(members) != 3 or {i.filename: i.file_size for i in members} != inventory or
                any(i.flag_bits & 1 or i.is_dir() for i in members)):
            raise ValueError('Exact retained subset inventory changed')
        retained = z.read('data/bin/BodyParts.bin')
    if len(retained) != 2584 or sha(retained) != _schema.BODY_SHA:
        raise ValueError('Retained CLIENT bytes changed')
    # Reuse only the independently source-parsed baseline projection. Neither
    # the prior checker main, its fixture generator, nor native suite executes.
    tables, flags = _schema.original_reference(root)
    independent = _schema.reference(tables, flags, [])
    crc = independent['crc']
    retained_crc = struct.unpack_from('<I', retained, 8)[0]
    if retained[:8] != b'CrypticS' or retained[12:20] != struct.pack('<H', 6) + b'Parse6':
        raise ValueError('Retained CLIENT original header changed')
    (work / 'retained-CLIENT-BodyParts.bin').write_bytes(retained)
    stream_reference = {'source_enum_and_flags': flags, 'source_crc': crc,
                        'standard_adler32': independent['standard_adler32'],
                        'stream_hex': independent['stream'].hex(), 'events': independent['events'],
                        'update_lengths': independent['lengths'],
                        'visited_fields': independent['visited'], 'interpret_calls': independent['interprets']}
    (work / 'schema-stream-reference.json').write_bytes(canonical(stream_reference))
    cases = []

    def header(value=b'Parse6', value_crc=retained_crc, padding=None):
        size = (4 - (len(value) + 2) % 4) % 4
        return b'CrypticS' + struct.pack('<IH', value_crc, len(value)) + value + (bytes(size) if padding is None else padding)

    def add(label, data, route=0, production=1, fault=0, authentic=False):
        # Independent bounded framing and source strcmp predicate projection.
        # route0 is the actual production caller. route1 is a separately labelled
        # strict-CRC dependency control, never a development caller execution.
        source = mode = opened = source_close = wrapper_close = end = failure = 0
        if len(data) > 65536:
            code, stage = status['COH_LIMIT'], 1
        elif route > 1 or production != (1 if route == 0 else 0) or fault > 1:
            code, stage = status['COH_UNSUPPORTED'], 3
        elif len(data) < 14:
            code, stage, failure = status['COH_INVALID'], 4, len(data)
        else:
            length = struct.unpack_from('<H', data, 12)[0]
            end = 14 + length + (4 - (length + 2) % 4) % 4
            if length >= 4096:
                code, stage, failure = status['COH_LIMIT'], 5, 12
            elif len(data) < end:
                code, stage, failure = status['COH_INVALID'], 4, len(data)
            else:
                source, mode, opened = int(route == 0), int(route == 0), 1
                if fault:
                    code, stage = status['COH_UNSUPPORTED'], 6
                else:
                    actual = struct.unpack_from('<I', data, 8)[0]
                    kind = data[14:14 + length].split(b'\0', 1)[0]
                    accepted = data[:8] == b'CrypticS' and kind == b'Parse6' and (route == 0 or actual == crc)
                    if accepted:
                        code, stage, wrapper_close = status['COH_OK'], 8, 1
                        mode += int(route == 0)
                    else:
                        code, stage, source_close = status['COH_UNSUPPORTED'], 7, 1
        cases.append({'label': label, 'data': data, 'route': route, 'production': production,
                      'fault': fault, 'status': code, 'stage': stage, 'failure': failure,
                      'source_calls': source, 'mode_calls': mode, 'open_calls': opened,
                      'source_close_calls': source_close, 'wrapper_close_calls': wrapper_close,
                      'accepted_header_end': end if code == status['COH_OK'] else 0,
                      'authentic_retained_CLIENT_input': authentic})

    add('authentic_CLIENT_whole_input_production_header_only', retained, authentic=True)
    add('synthetic_exact_header_extent_production', retained[:20])
    add('production_ignoreCRC1_zero_word', header(value_crc=0))
    add('production_ignoreCRC1_max_word', header(value_crc=0xffffffff))
    for bit in range(32):
        add('production_ignoreCRC1_crc_bit_' + str(bit), header(value_crc=retained_crc ^ (1 << bit)))
    add('production_unused_nonzero_body_suffix', header() + bytes(range(256)))
    add('production_unused_zero_body_suffix', header() + bytes(64))
    for index in range(8):
        changed = bytearray(header()); changed[index] ^= 0x80
        add('source_rejected_magic_byte_' + str(index), bytes(changed))
    for size in range(20):
        add('preflight_truncated_header_' + str(size), retained[:size])
    for value in (b'', b'Parse', b'parse6', b'Parse6X', b'\xffParse6', b'Parse6\0',
                  b'Parse6\0suffix', b'Parse6\0\xff', b'\0Parse6'):
        add('source_type_' + value.hex(), header(value))
    add('source_arbitrary_nonzero_padding', header(b'Parse6\0', padding=b'\xa5\xff\x7f'))
    add('source_max_safe_type4095_embedded_NUL', header(b'Parse6\0' + b'X' * 4088, padding=b'\xff' * 3))
    for length in (4096, 65535):
        add('preflight_type_length_' + str(length), b'CrypticS' + struct.pack('<IH', retained_crc, length))
    add('source_open_adapter_refusal', retained, fault=1)
    add('profile_development_mode_unqualified', retained, production=0)
    add('profile_unknown_production_mode', retained, production=2)
    add('profile_unknown_fault', retained, fault=2)
    add('profile_unknown_route', retained, route=2)
    add('profile_strict_dependency_requires_mode0', retained, route=1, production=1)
    add('input65536_unused_tail_boundary', header() + bytes(65536 - 20))
    add('input65537_preflight_limit', header() + bytes(65537 - 20))
    padded = header(b'Parse6\0')
    for size in (21, 22, 23):
        add('preflight_padding_truncated_' + str(size), padded[:size])
    for word in (crc, 0, 0xffffffff, crc ^ 1):
        add('strict_dependency_crc_' + format(word, '08x'), header(value_crc=word), route=1, production=0)
    add('strict_dependency_embedded_NUL_equal_crc', header(b'Parse6\0suffix', value_crc=crc), route=1, production=0)
    add('strict_dependency_open_refusal', header(value_crc=crc), route=1, production=0, fault=1)
    add('fresh_authentic_production_after_all_refusals', retained, authentic=True)
    path = work / 'persist-newer-fixtures.bin'
    manifest = []
    with path.open('xb') as f:
        f.write(struct.pack('<III', 0x31464e50, len(cases), crc))
        for index, case in enumerate(cases):
            data = case['data']
            f.write(struct.pack('<13I', index, case['status'], case['stage'], case['failure'], len(data),
                                case['route'], case['production'], case['fault'], case['source_calls'],
                                case['mode_calls'], case['open_calls'], case['source_close_calls'], case['wrapper_close_calls']))
            f.write(bytes.fromhex(sha(data))); f.write(data)
            manifest.append({k: v for k, v in case.items() if k != 'data'} |
                            {'case': index, 'bytes': len(data), 'sha256': sha(data),
                             'synthetic_control': not case['authentic_retained_CLIENT_input'],
                             'strict_dependency_only': case['route'] == 1})
    if path.stat().st_size > 262144:
        raise ValueError('Fixture file bound')
    proof = {'primary_input': 'full retained CLIENT BodyParts.bin; production caller consumes header only',
             'primary_input_bytes': len(retained), 'primary_input_sha256': sha(retained),
             'archive_path': _schema.ARCHIVE, 'archive_bytes': len(packed), 'archive_sha256': _schema.ARCHIVE_SHA,
             'archive_git_blob_sha1': _schema.ARCHIVE_BLOB, 'retained_CLIENT_member': 'data/bin/BodyParts.bin',
             'retained_CLIENT_bytes': len(retained), 'retained_CLIENT_sha256': sha(retained),
             'retained_CLIENT_crc_word': retained_crc, 'independent_source_crc': crc,
             'retained_CLIENT_word_matches_independent_source_crc': retained_crc == crc,
             'retained_origin_run_id': 36707839624, 'retained_origin_artifact_id': 11092897979,
             'independent_stream_bytes': len(independent['stream']),
             'independent_stream_sha256': sha(independent['stream']),
             'independent_update_lengths': independent['lengths'],
             'independent_update_calls': len(independent['lengths']),
             'independent_visited_fields': independent['visited'],
             'independent_interpret_calls': independent['interprets'],
             'retained_CLIENT_word_never_supplied_as_source_crc': True,
             'fixture_bytes': path.stat().st_size, 'fixture_sha256': sha(path.read_bytes()), 'cases': manifest,
             'independent_expectations': 'Source-parsed exact BodyPart schemas and standard zlib.Adler32(seed1) using original digest-byte convention; independent bounded LE framing plus C-string header predicate. Actual source computes CRC without retained CRC argument. Production ignoreCRC1 and separately labelled strictCRC0 dependency controls. Prior checker mains/fixture suites never execute.',
             'development_caller_executed': False, 'current_Map_selection_provenance_verified': False}
    (work / 'fixture-reference.json').write_bytes(canonical(proof))
    return path, proof


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence-directory', type=Path)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args(); root = args.source_root.resolve()
    if not __debug__:
        raise ValueError('Python assertions required')
    if args.output.exists() or (args.evidence_directory and args.evidence_directory.exists()):
        raise ValueError('Fresh output/evidence required')
    manifest_path = HERE / 'qualification/schema-crc-20261019/cryptopp-adler-source.json'
    manifest = json.loads(manifest_path.read_text())
    initial_paths = [Path(__file__).resolve(), HERE / 'check_schema_crc.py', HERE / 'test_persist_newer.c',
                     HERE / 'persist_newer_provider.py', HERE / 'persist-newer-source-pins.json',
                     HERE / 'schema_crc_provider.py', HERE / 'schema-crc-source-pins.json',
                     HERE / 'binary_read_open_provider.py', HERE / 'binary-read-open-source-pins.json',
                     HERE / 'cryptopp_adler_source.py', manifest_path, root / manifest['archive']['path'],
                     root / manifest['repository_dependency']['path'], root / _schema.ARCHIVE,
                     root / 'native-android/engine/coh_contracts.h',
                     root / 'upstream/ouroboros/Common/gameData/BodyPart.c',
                     root / 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/textparser.h']
    initial = {path.resolve(): path.read_bytes() for path in initial_paths}
    provider = module(HERE / 'persist_newer_provider.py')
    temporary = tempfile.TemporaryDirectory(prefix='coh-persist-newer-') if not args.evidence_directory else None
    work = Path(temporary.name) if temporary else args.evidence_directory.resolve()
    if not temporary:
        work.mkdir(parents=True)
    try:
        tools = {name: compiler(work, name) for name in ('cc', 'c++')}
        cc, cxx = tools['cc']['resolved_path'], tools['c++']['resolved_path']
        python_path = Path(sys.executable).resolve()
        zlib_path = Path(zlib.__file__).resolve() if hasattr(zlib, '__file__') else python_path
        environment = {'system': platform.system(), 'machine': platform.machine(), 'byteorder': sys.byteorder,
                       'python_pointer_bytes': struct.calcsize('P'), 'python_version': sys.version,
                       'python_executable': str(python_path), 'python_executable_sha256': sha(python_path.read_bytes()),
                       'reference_zlib_version': zlib.ZLIB_VERSION, 'reference_zlib_runtime_version': zlib.ZLIB_RUNTIME_VERSION,
                       'reference_zlib_builtin_to_measured_python': not hasattr(zlib, '__file__'),
                       'reference_zlib_module_or_python_binary': str(zlib_path),
                       'reference_zlib_module_sha256': sha(zlib_path.read_bytes()),
                       'original_engine_Win32_or_Android_ABI_qualified': False}
        wire, inputs = fixtures(root, work)
        generated, origin = provider.build(root, work)
        generated = Path(generated); adler_cpp = Path(origin['adler_cpp_path'])
        dependency = origin['crypto_dependency']; source_paths = set(initial)
        for name, digest in origin['source_sha256'].items():
            path = (root / name).resolve()
            if sha(path.read_bytes()) != digest:
                raise ValueError('Persist source pin changed')
            source_paths.add(path)
        test = HERE / 'test_persist_newer.c'
        engine_include = root / 'native-android/engine/costume-import'
        crypto_include = Path(dependency['include_dir'])
        cpp_sources = [adler_cpp, *map(Path, dependency['source_paths'])]
        (work / 'persist-newer-qualification-identity.h').write_text('/* dependency discovery only */\n')

        def dependencies(command):
            output = run(command).stdout.replace('\\\n', ' ').split(':', 1)[1]
            return [Path(name).resolve() for name in shlex.split(output)]

        for source in (generated, test):
            source_paths.update(path for path in dependencies([cc, '-std=c99', '-I' + str(work),
                                '-I' + str(engine_include), '-MM', source]) if path.is_relative_to(root))
        dep_flags, link_flags = dependency['proof']['compile_flags'], dependency['proof']['link_flags']
        for source in cpp_sources:
            source_paths.update(path for path in dependencies([cxx, *dep_flags, '-I' + str(crypto_include),
                                '-MM', source]) if path.is_relative_to(root))
        if any(path.read_bytes() != raw for path, raw in initial.items()):
            raise ValueError('Source changed during provider generation')
        frozen = {path: path.read_bytes() for path in source_paths}
        # Include every generated native header/source, not only the final
        # composite, so dependency discovery cannot silently leave a gap.
        owned = {path.resolve(): path.read_bytes() for path in work.iterdir()
                 if path.is_file() and path.suffix in ('.c', '.cpp', '.h')
                 and path.name != 'persist-newer-qualification-identity.h'}
        dep_snapshots = {Path(path).resolve(): digest for path, digest in dependency['snapshot_sha256'].items()}
        source_hashes = {str(path.relative_to(root)): sha(raw) for path, raw in sorted(frozen.items())}
        crypto_snapshots = {str(path.relative_to(work)): digest for path, digest in sorted(dep_snapshots.items())}
        generated_hashes = {str(path.relative_to(work)): sha(raw) for path, raw in sorted(owned.items())}
        source_identity = {'schema': 'coh-persist-newer-fixture-source-v1', 'source_sha256': source_hashes,
                           'generated_native_source_sha256': generated_hashes,
                           'dependency_snapshot_sha256': crypto_snapshots,
                           'excluded_circular_derived_files': ['persist-newer-qualification-identity.h',
                             'per-mode compile/build receipts', 'object files/native executables', 'run ledgers']}
        source_bytes = canonical(source_identity); (work / 'source-identity.json').write_bytes(source_bytes)
        source_id = sha(source_bytes)
        profile = {'schema': 'coh-persist-newer-fixture-profile-v1',
                   'scope': 'exact original ParserIsPersistNewer production branch with exact BodyPart source schemas, definesNULL',
                   'original_functions': 'ParserIsPersistNewer + ParseTableCRC/UpdateCRCFromParseInfo/interpretfield + SerializeReadOpen/ReadPascalString/U16/U32/SimpleBufRead/Seek/Tell + cryptAdler32 wrappers and pinned CryptoPP Adler32',
                   'source_crc_never_caller_supplied': True, 'production_mode': 1,
                   'production_ignoreCRC1_preserved': True,
                   'strictCRC0_controls': 'separate dependency route; no development ParserIsPersistNewer invocation',
                   'input_max': 65536, 'declared_type_max': 4095, 'complete_header_preflight': True,
                   'source_embedded_NUL_and_arbitrary_padding_semantics_preserved': True,
                   'fixed_owned_buffer_no_filesystem': True, 'trace_max': 512, 'update_max': 64,
                   'child_fixture_max': 262144, 'child_input_ledger_max': 65536,
                   'child_build_receipt_max': 65536, 'child_stdout_max': 4096,
                   'int32_intptr64_size64_little_endian_host_only': True, 'fixture_only': True,
                   'development_mode_executed': False, 'filesystem_freshness_executed': False,
                   'date_comparison_executed': False, 'current_Map_selection_provenance_verified': False,
                   'runtime_body_catalog_admitted': False, 'runtime_default_admitted': False,
                   'dictionary_imported': False, 'source_generation_admitted': False,
                   'complete_initial_character': False, 'server_identity_bound': False,
                   'selected_owner_bound': False, 'actor_publication': False, 'ack_permitted': False,
                   'world_authority': False}
        profile_bytes = canonical(profile); (work / 'fixture-profile.json').write_bytes(profile_bytes)
        profile_id = sha(profile_bytes); ledger_bytes = canonical(inputs)
        if len(ledger_bytes) > 65536:
            raise ValueError('Input ledger bound')
        (work / 'input-ledger.json').write_bytes(ledger_bytes); ledger_id = sha(ledger_bytes)

        def verify():
            if any(path.read_bytes() != raw for path, raw in frozen.items()) or any(path.read_bytes() != raw for path, raw in owned.items()):
                raise ValueError('Source changed during persist qualification')
            if any(sha(path.read_bytes()) != digest for path, digest in dep_snapshots.items()):
                raise ValueError('CryptoPP dependency changed during qualification')
            for command, tool in tools.items():
                if (Path(shutil.which(command)).resolve() != Path(tool['resolved_path']) or
                        sha(Path(tool['resolved_path']).read_bytes()) != tool['executable_sha256']):
                    raise ValueError('Compiler changed during persist qualification')
            if (sha(python_path.read_bytes()) != environment['python_executable_sha256'] or
                    sha(zlib_path.read_bytes()) != environment['reference_zlib_module_sha256']):
                raise ValueError('Python/reference zlib binary changed')

        def command(command_args, stem, env=None):
            result = subprocess.run(list(map(str, command_args)), capture_output=True, text=True, timeout=240, env=env)
            Path(str(stem) + '.stdout').write_text(result.stdout)
            Path(str(stem) + '.stderr').write_text(result.stderr)
            if result.returncode:
                raise RuntimeError('PERSIST_NEWER_QUALIFICATION_REFUSED ' + str(stem) + '\n' +
                                   result.stdout[:1024] + result.stderr[:3072])
            return result

        def actual_dependencies(path, identity):
            for dep in [Path(name).resolve() for name in shlex.split(path.read_text().replace('\\\n', ' ').split(':', 1)[1])]:
                if dep == identity or dep in frozen or dep in owned or dep in dep_snapshots:
                    continue
                raise ValueError('Unfrozen non-system compile dependency: ' + str(dep))

        checks, bindings, builds = {}, {}, {}
        modes = [('release', ['-O2', '-fstack-usage'])]
        if args.sanitize:
            modes += [('asan', ['-O1', '-g', '-fsanitize=address', '-fno-omit-frame-pointer', '-no-pie']),
                      ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1', LC_ALL='C')
        c_flags = ['-std=c99', '-Wall', '-Wextra', '-Werror', '-Wno-missing-field-initializers',
                   '-Wno-unused-parameter', '-Wno-unused-value', '-Wno-pointer-sign', '-pedantic', '-fno-strict-aliasing']
        cpp_flags = [*dep_flags, '-Wall', '-Wextra']
        for mode, flags in modes:
            directory = work / mode; directory.mkdir(); nonce = os.urandom(32).hex()
            compile_profile = {'schema': 'coh-persist-newer-fixture-compile-profile-v1', 'mode': mode,
                               'compilers': tools, 'c_flags': c_flags + flags, 'cpp_flags': cpp_flags + flags,
                               'link_flags': link_flags + flags, 'generated_native_source_sha256': generated_hashes,
                               'test_source_sha256': sha(test.read_bytes()),
                               'dependency_snapshot_manifest_sha256': sha(canonical(crypto_snapshots))}
            compile_id = sha(canonical(compile_profile))
            identity = '/* Controlled fixture association only; no runtime attestation. */\n' + ''.join(
                array(name, value) for name, value in [('fixture_source_id', source_id),
                ('fixture_profile_id', profile_id), ('fixture_run_id', nonce),
                ('fixture_input_sha256', inputs['primary_input_sha256']),
                ('fixture_wire_sha256', inputs['fixture_sha256']), ('fixture_input_ledger_id', ledger_id),
                ('fixture_compile_profile_id', compile_id)])
            identity_header = directory / 'persist-newer-qualification-identity.h'
            identity_header.write_text(identity); objects, commands = [], []
            for name, source in [('provider', generated), ('test', test)]:
                obj, dep_file = directory / (name + '.o'), directory / (name + '.d')
                cmd = [cc, *c_flags, *flags, '-I' + str(directory), '-I' + str(work),
                       '-I' + str(engine_include), '-MMD', '-MF', str(dep_file), '-c', str(source), '-o', str(obj)]
                command(cmd, directory / ('compile-' + name)); commands.append(cmd); objects.append(obj)
                actual_dependencies(dep_file, identity_header)
            for number, source in enumerate(cpp_sources):
                label = 'cpp-wrapper' if not number else 'crypto-' + str(number) + '-' + source.stem
                obj, dep_file = directory / (label + '.o'), directory / (label + '.d')
                cmd = [cxx, *cpp_flags, *flags, '-I' + str(crypto_include), '-MMD', '-MF', str(dep_file),
                       '-c', str(source), '-o', str(obj)]
                command(cmd, directory / ('compile-' + label)); commands.append(cmd); objects.append(obj)
                actual_dependencies(dep_file, identity_header)
            exe = directory / 'persist-newer'
            cmd = [cxx, *flags, *map(str, objects), *link_flags, '-lcrypto', '-o', str(exe)]
            command(cmd, directory / 'link'); commands.append(cmd)
            commands_bytes = canonical(commands); (directory / 'commands.json').write_bytes(commands_bytes)
            build = {'schema': 'coh-persist-newer-fixture-build-v1', 'compile_profile': compile_profile,
                     'compile_profile_sha256': compile_id, 'commands_sha256': sha(commands_bytes),
                     'commands': commands, 'source_identity_sha256': source_id, 'profile_sha256': profile_id,
                     'fixture_run_nonce': nonce, 'generated_identity_header_sha256': sha(identity.encode()),
                     'executable_bytes': exe.stat().st_size, 'executable_sha256': sha(exe.read_bytes())}
            build_bytes = canonical(build)
            if len(build_bytes) > 65536:
                raise ValueError('Build receipt bound')
            (directory / 'build.json').write_bytes(build_bytes); build_id = sha(build_bytes)
            ledger = b'COHPN1\0\0' + b''.join(bytes.fromhex(value) for value in
                      (source_id, build_id, profile_id, nonce, inputs['primary_input_sha256'],
                       build['executable_sha256'], ledger_id, compile_id))
            (directory / 'run-ledger.bin').write_bytes(ledger)
            ran = command([exe, wire, directory / 'run-ledger.bin', directory / 'build.json',
                           work / 'input-ledger.json'], directory / 'native', env)
            if ran.stderr or len(ran.stdout.encode()) > 4096:
                raise ValueError('Native output bound/refusal')
            result = json.loads(ran.stdout); checks[mode], bindings[mode] = result['checks'], result['fixture_binding']
            expected = {'source_id': source_id, 'build_id': build_id, 'profile_id': profile_id, 'run_id': nonce,
                        'input_sha256': inputs['primary_input_sha256'], 'fixture_sha256': inputs['fixture_sha256'],
                        'executable_sha256': build['executable_sha256'], 'input_ledger_sha256': ledger_id,
                        'compile_profile_sha256': compile_id, 'run_ledger_sha256': sha(ledger)}
            if bindings[mode] != expected:
                raise ValueError('Child-measured fixture association differs')
            builds[mode] = {k: v for k, v in build.items() if k not in ('commands', 'compile_profile')}
            builds[mode].update(build_receipt_path=mode + '/build.json', build_receipt_sha256=build_id,
                                compile_profile=compile_profile)
            verify()
        if any(value != checks['release'] for value in checks.values()):
            raise ValueError('Native check counts differ')
        core_names = ('Adler32::Update', 'Adler32::TruncatedFinal', 'Adler32::Reset', 'Adler32::Restart',
                      'Adler32::Adler32', 'Adler32::~Adler32', 'cryptAdler32Init', 'cryptAdler32Update',
                      'cryptAdler32Final', 'schema_adler_')
        stack, stack_reports = [], []
        for path in sorted((work / 'release').glob('*.su')):
            for line in path.read_text().splitlines():
                location, size, bound = line.split('\t')
                match = re.match(r'.*:[0-9]+:[0-9]+:(.*)', location)
                function = match[1] if match else location
                if path.name in ('provider.su', 'test.su') or any(name in function for name in core_names):
                    stack.append({'function': function, 'bytes': int(size), 'bound': bound,
                                  'report': str(path.relative_to(work))})
            stack_reports.append({'path': str(path.relative_to(work)), 'bytes': path.stat().st_size,
                                  'sha256': sha(path.read_bytes())})
        if not stack or any(row['bound'] not in ('static', 'dynamic,bounded') for row in stack):
            raise ValueError('Unbounded selected native stack')
        verify()
        resources = {'profile_input_max': 65536, 'profile_type_max': 4095,
                     'fixture_file_bytes': wire.stat().st_size, 'fixture_file_max': 262144,
                     'input_ledger_bytes': len(ledger_bytes), 'input_ledger_max': 65536,
                     'native_stdout_max': 4096, 'per_build_receipt_max': 65536,
                     'provider_owned_static_bytes': checks['release']['provider_owner_bytes'],
                     'actual_Adler_object_bytes': checks['release']['crypto_object_bytes'],
                     'wrapper_stack_charge_reserve': 16384, 'wrapper_total_budget_max': 1048576,
                     'digest_scratch_reserve_fixture': 65536, 'retained_reserve_fixture': 65536,
                     'selected_release_max_frame': max(row['bytes'] for row in stack),
                     'selected_release_frame_count': len(stack),
                     'stack_scope': 'new C provider/test and actual wrapper/Adler core only; every dependency .su retained',
                     'whole_process_or_aggregate_stack_bound_claimed': False}
        (work / 'resource-bounds.json').write_bytes(canonical(resources))
        files = {str(path.relative_to(work)): {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
                 for path in sorted(work.rglob('*')) if path.is_file()}
        compact_inputs = {k: v for k, v in inputs.items() if k != 'cases'}
        compact_inputs.update(case_count=len(inputs['cases']), full_fixture_reference={'path': 'fixture-reference.json', **files['fixture-reference.json']},
                              full_input_ledger={'path': 'input-ledger.json', **files['input-ledger.json']},
                              full_schema_stream_reference={'path': 'schema-stream-reference.json', **files['schema-stream-reference.json']})
        compact_origin = {k: v for k, v in origin.items() if k not in ('crypto_dependency', 'adler_cpp_path', 'evidence_paths')}
        compact_origin['crypto_dependency'] = {'revision': dependency['proof']['revision'], 'tree': dependency['proof']['tree'],
             'Git_commit_tree_selected_blob_membership_verified': True, 'retained_source_file_count': dependency['proof']['source_files_count'],
             'compiled_dependency_translation_units': len(dependency['source_paths']),
             'source_snapshot_count': len(dep_snapshots), 'source_snapshot_manifest_sha256': sha(canonical(crypto_snapshots)),
             'source_stable_before_after': True, 'full_provenance': {'path': 'cryptopp-provenance.json', **files['cryptopp-provenance.json']},
             'original_backend_not_alternate_Adler': True, 'system_cpp_runtime_allocator_or_platform_closure': False}
        proof = {'schema': 'coh-original-persist-newer-qualification-v1', 'passed': True,
                 'source_revision': run(['git', '-C', root, 'rev-parse', 'HEAD']).stdout.strip(),
                 'source_sha256': source_hashes, 'source_stable_before_after': True, 'host_environment': environment,
                 'host_python_and_reference_zlib_module_stable_before_after': True, 'host_compiler_identities': tools,
                 'host_compilers_stable_before_after': True, 'original_persist_newer_provider': compact_origin,
                 'source_schema_and_header_fixtures': compact_inputs, 'fixture_source_identity': source_identity,
                 'fixture_source_identity_sha256': source_id, 'fixture_profile': profile,
                 'fixture_profile_sha256': profile_id, 'child_measured_fixture_bindings': bindings,
                 'checks': checks, 'builds': builds, 'resource_bounds': resources, 'native_stack_frames': stack,
                 'full_dependency_stack_reports': stack_reports, 'evidence_files': files,
                 'scope': 'Exact pinned original ParserIsPersistNewer production early-return branch, actual existing ParseTableCRC/interpretfield and original cryptAdler32 wrappers with pinned CryptoPP Adler32, plus original SerializeReadOpen dependencies. Actual computed CRC independently agrees with the source-derived baseline; new receipts check callback and byte totals. Prior accepted schema qualifier owns byte-for-byte stream evidence. Real source CRC feeds header open. Production ignoreCRC1 accepted/rejected branches and labelled strictCRC0 dependency controls only. Fixed owned-memory open/close adapter; no filesystem. Source/input/ELF/build/profile/random labels are measured fixture associations, never current Map attestation.',
                 'actual_original_ParserIsPersistNewer_production_executed': True,
                 'actual_original_ParseTableCRC_executed': True, 'actual_original_SerializeReadOpen_executed': True,
                 'actual_original_CryptoPP_Adler32_executed': True, 'production_ignoreCRC1_preserved': True,
                 'development_mode_executed': False, 'date_or_filesystem_freshness_executed': False,
                 'Files1_or_FileListRead_executed': False, 'full_body_reader_executed': False,
                 'old_checker_mains_executed': False, 'old_native_suites_executed': False,
                 'external_Cpp_OpenSSL_libc_allocator_sanitizer_or_total_stack_closure': False,
                 'current_Map_runtime_executed': False, 'current_Map_selection_provenance_verified': False,
                 'runtime_body_catalog_admitted': False, 'runtime_default_admitted': False,
                 'dictionary_imported': False, 'source_generation_admitted': False,
                 'complete_initial_character': False, 'server_identity_bound': False, 'selected_owner_bound': False,
                 'actor_publication': False, 'ack_permitted': False, 'world_authority': False}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(proof, indent=2) + '\n')
        print(json.dumps({'passed': True, 'checks': checks, 'case_count': len(inputs['cases'])}))
    finally:
        if temporary:
            temporary.cleanup()


if __name__ == '__main__':
    main()
