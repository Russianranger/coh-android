#!/usr/bin/env python3
"""Whole original production cache-hit loader qualification; no prior main executes."""
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
_spec = importlib.util.spec_from_file_location('unopened_schema_crc_helpers', HERE / 'check_schema_crc.py')
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
sha, canonical, run, module, compiler, array = (_schema.sha, _schema.canonical, _schema.run,
                                               _schema.module, _schema.compiler, _schema.array)



ARCHIVE=_schema.ARCHIVE;ARCHIVE_SHA=_schema.ARCHIVE_SHA;ARCHIVE_BLOB=_schema.ARCHIVE_BLOB;BODY_SHA=_schema.BODY_SHA
def fixtures(root,work):
 # Parse only the retained CLIENT BodyPart fixture independently; no accepted
 # checker main or native suite is invoked. Typed destruction cases contain no
 # pointers and derive expected release order directly from descriptor indexes.
 archive=(root/ARCHIVE).read_bytes()
 if sha(archive)!=ARCHIVE_SHA:raise ValueError('Retained archive pin changed')
 with zipfile.ZipFile(root/ARCHIVE)as z:raw=z.read('data/bin/BodyParts.bin')
 if len(raw)!=2584 or sha(raw)!=BODY_SHA:raise ValueError('Retained BodyPart bytes changed')
 (work/'BodyParts.bin').write_bytes(raw)
 at=76;parts=[];release_strings=0
 for i in range(28):
  strings=[];words=[]
  for field in range(12):
   if field in(0,1,4,5,6):
    n=struct.unpack_from('<H',raw,at)[0];at+=2;value=raw[at:at+n].split(b'\0',1)[0];at+=n+(4-(n+2)%4)%4;strings.append(value);release_strings+=bool(value)
   else:words.append(struct.unpack_from('<I',raw,at)[0]);at+=4
  # End token has no bytes. Next record begins with its own declared length.
  strings_out=b''.join(v.ljust(260,b'\0')for v in strings)
  final=[words[2],words[1],words[3]&255,words[4],words[5],words[6],sum((not v)<<k for k,v in enumerate(strings))]
  parts.append(strings_out+struct.pack('<14I',*words,*final))
  if i<27:at+=4
 if at!=2584:raise ValueError('Independent retained row extents')
 expected=struct.pack('<7I',0xcf27aba3,20,64,2584,28,28,2516)+b''.join(parts)+bytes(2*1356)
 if len(expected)!=40708:raise ValueError('Independent result layout')
 loaders=[]
 def load(label,data,status=0,stage=18,fault=0,rows=28,strings=release_strings,arrays=1):
  loaders.append({'label':label,'data':data,'status':status,'stage':stage,'fault':fault,'rows':rows,'strings':strings,'arrays':arrays})
 load('authentic_CLIENT_clear_after_copy',raw)
 changed=bytearray(raw);struct.pack_into('<I',changed,8,0);load('production_CRC_ignore_preserved_with_original_clear',bytes(changed))
 load('header_rejection_original_empty_clear',b'X'+raw[1:],2,15,rows=0,strings=0,arrays=0)
 changed=bytearray(raw);struct.pack_into('<I',changed,72,0);load('partial_read_failure_original_clear',bytes(changed),2,16,rows=1,strings=sum(bool(v)for v in [raw[78:78+struct.unpack_from('<H',raw,76)[0]]]),arrays=1)
 # Independent first parsed row has all five string setters, but only its name
 # and source filename are nonempty in the retained fixture.
 loaders[-1]['strings']=sum(bool(parts[0][i*260:(i+1)*260].split(b'\0',1)[0])for i in range(5))
 changed=bytearray(raw);struct.pack_into('<I',changed,64,2517);load('full_read_failure_original_clear',bytes(changed),2,16)
 load('missing_cache_original_empty_clear',raw,2,15,4,0,0,0)
 load('open_failure_original_empty_clear',raw,2,15,1,0,0,0)
 load('truncated_preflight_no_destructor',raw[:-1],1,13,rows=0,strings=0,arrays=0)
 direct=[]
 def case(label,rows=(),array=1,fault=0,borrowed=0,count=None,status=0,stage=18):
  count=len(rows)if count is None else count;data=struct.pack('<4I',count,array,fault,borrowed)
  for present,mask,lengths in rows:data+=struct.pack('<7I',present,mask,*lengths)
  data+=bytes((30-len(rows))*28)
  order=[i for i,row in enumerate(rows)if row[0]][::-1]if not status else[]
  strings=sum(row[1].bit_count()for row in rows if row[0])if not status else 0
  want=struct.pack('<4I',len(order),strings,array,len(order))+struct.pack('<30I',*(order+[0]*(30-len(order))))+struct.pack('<3I',len(order),1,1)
  direct.append({'label':label,'data':data,'expected':want,'status':status,'stage':stage,'rows':len(order),'strings':strings,'arrays':array if not status else 0})
 case('null_array_empty',array=0);case('allocated_empty_array');case('all_null_nested_slots',[(0,31,[259]*5)]*30)
 for mask in range(32):case('every_string_mask_'+str(mask),[(1,mask,[0,1,2,258,259])])
 case('three_rows_reverse_null_middle',[(1,31,[1]*5),(0,31,[259]*5),(1,31,[259]*5)])
 case('max30_nested_owned_strings',[(1,31,[259]*5)]*30)
 case('alternating_partial_rows',[(i%2,(i*7)%32,[i]*5)for i in range(30)])
 case('unselected_null_fields_ignore_lengths',[(1,0,[259]*5)])
 case('capacity31_preflight',count=31,status=4,stage=3)
 case('count_without_array_preflight',[(1,31,[1]*5)],array=0,status=2,stage=3)
 case('borrowed_storage_preflight',[(1,31,[1]*5)],borrowed=1,status=2,stage=3)
 case('unsupported_string_mask_preflight',[(1,63,[1]*5)],status=2,stage=3)
 case('invalid_present_preflight',[(2,0,[1]*5)],status=2,stage=3)
 case('string260_preflight',[(1,31,[260]*5)],status=4,stage=3)
 case('fixed_reservation_preflight',[(1,31,[1]*5)],fault=1,status=4,stage=17)
 case('invalid_reservation_preflight',fault=2,status=2,stage=3)
 path=work/'struct-clear-fixtures.bin';manifest=[]
 with path.open('xb')as f:
  f.write(struct.pack('<3I',0x31435343,len(loaders),len(direct)))
  for i,c in enumerate(loaders):
   data=c['data'];f.write(struct.pack('<8I',i,c['status'],c['stage'],c['fault'],c['rows'],c['strings'],c['arrays'],len(data))+bytes.fromhex(sha(data))+data)
   if not c['status']:f.write(expected)
   manifest.append({k:v for k,v in c.items()if k!='data'}|{'kind':'loader','sha256':sha(data),'bytes':len(data)})
  for i,c in enumerate(direct):
   f.write(struct.pack('<3I',i,c['status'],c['stage'])+bytes.fromhex(sha(c['data']))+c['data'])
   if not c['status']:f.write(c['expected'])
   manifest.append({k:v for k,v in c.items()if k not in('data','expected')}|{'kind':'direct','sha256':sha(c['data']),'bytes':len(c['data']),'expected_sha256':sha(c['expected'])})
 proof={'archive_path':ARCHIVE,'archive_sha256':ARCHIVE_SHA,'member_sha256':BODY_SHA,'primary_input_sha256':BODY_SHA,'fixture_sha256':sha(path.read_bytes()),'fixture_bytes':path.stat().st_size,'cases':manifest,'loader_cases':len(loaders),'direct_cases':len(direct),'independent_reference':'Raw retained schema-order scalar/string projection for exact loader outputs; direct descriptor masks and reversed present indexes determine release counts/order. Empty allocated strings count as releases. No accepted native checker main or full suite executes.'}
 (work/'fixture-reference.json').write_bytes(canonical(proof));(work/'schema-stream-reference.json').write_bytes(canonical({'actual_crc':0xcf27aba3,'source':'immutable accepted exact-source CRC dependency; this milestone does not replay its suite'}));return path,proof

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
    initial_paths = [Path(__file__).resolve(), HERE / 'check_schema_crc.py', HERE / 'unopened_binary_provider.py', HERE / 'unopened-binary-source-pins.json', HERE / 'body_part_loader_provider.py', HERE / 'body-part-loader-source-pins.json', HERE / 'test_struct_clear.c',
                     HERE / 'struct_clear_provider.py', HERE / 'struct-clear-source-pins.json', HERE / 'cache_hit_loader_provider.py', HERE / 'cache-hit-loader-source-pins.json',
                     HERE / 'schema_crc_provider.py', HERE / 'schema-crc-source-pins.json',
                     HERE / 'body_read_provider.py', HERE / 'body-read-source-pins.json',
                     HERE / 'cryptopp_adler_source.py', manifest_path, root / manifest['archive']['path'],
                     root / manifest['repository_dependency']['path'], root / _schema.ARCHIVE,
                     root / 'native-android/engine/coh_contracts.h',
                     root / 'upstream/ouroboros/Common/gameData/BodyPart.c',
                     root / 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/textparser.h']
    initial = {path.resolve(): path.read_bytes() for path in initial_paths}
    provider = module(HERE / 'struct_clear_provider.py')
    temporary = tempfile.TemporaryDirectory(prefix='coh-struct-clear-') if not args.evidence_directory else None
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
                raise ValueError('Struct-clear source pin changed')
            source_paths.add(path)
        test = HERE / 'test_struct_clear.c'
        engine_include = root / 'native-android/engine/costume-import'
        crypto_include = Path(dependency['include_dir'])
        cpp_sources = [adler_cpp, *map(Path, dependency['source_paths'])]
        (work / 'struct-clear-qualification-identity.h').write_text('/* dependency discovery only */\n')

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
                 and path.name != 'struct-clear-qualification-identity.h'}
        dep_snapshots = {Path(path).resolve(): digest for path, digest in dependency['snapshot_sha256'].items()}
        source_hashes = {str(path.relative_to(root)): sha(raw) for path, raw in sorted(frozen.items())}
        crypto_snapshots = {str(path.relative_to(work)): digest for path, digest in sorted(dep_snapshots.items())}
        generated_hashes = {str(path.relative_to(work)): sha(raw) for path, raw in sorted(owned.items())}
        source_identity = {'schema': 'coh-struct-clear-fixture-source-v1', 'source_sha256': source_hashes,
                           'generated_native_source_sha256': generated_hashes,
                           'dependency_snapshot_sha256': crypto_snapshots,
                           'excluded_circular_derived_files': ['struct-clear-qualification-identity.h',
                             'per-mode compile/build receipts', 'object files/native executables', 'run ledgers']}
        source_bytes = canonical(source_identity); (work / 'source-identity.json').write_bytes(source_bytes)
        source_id = sha(source_bytes)
        profile = {'schema': 'coh-struct-clear-fixture-profile-v1',
                   'scope': 'original StructClear BodyPart destruction including exact original TokenStore leaves; new loader production-failure integration and private owned partial-row fixtures',
                   'original_functions': 'StructClear/string_destroystruct/struct_destroystruct/nonarray_destroystruct/earray_destroystruct/TokenStoreFreeString/TokenStoreFree/TokenStoreGetPointer(Const)/TokenStoreGetNumElems/TokenStoreDestroyEArray + bpReadBodyPartFiles/ParserLoadFilesShared SMAR_Error/ParserLoadFiles/ParserIsPersistNewer -> ParserReadBinaryFile(SUPPLIED live handle) + ParseTableCRC/UpdateCRCFromParseInfo/interpretfield/CryptoPP + SerializeReadOpen/FileListRead(NULL)/ParserReadBinaryTable/readbin/SerializeClose',
                   'source_crc_never_caller_supplied': True, 'production_mode': 1,
                   'production_ignoreCRC1_preserved': True, 'shared_acquisition_shell': 'SMAR_Error only', 'source_ParseBoneNames_calls':0, 'filesystem_selection_or_mode_helpers_qualified':False,
                   'complete_entered_header_dependency_body_preflight':True,'all_authentic_prefix_truncations_tested':0,
                   'failure_profiles': 'direct owned fixed-arena reservation refusal before originals; owned open refusal after actual CRC; missing fixture cache; partial/full read accounting rejection reaches exact StructClear supported destructor chain. Accepted row/crypto reservation implementation reused, its broad suite not replayed; no original allocator/engine heap recovery claim',
                   'input_max': 65536, 'positive_count_policy_max':30,'declared_string_policy_max':259, 'declared_type_max': 4095, 'complete_header_preflight': True,
                   'source_embedded_NUL_and_arbitrary_padding_semantics_preserved': True,
                   'fixed_owned_buffer_no_filesystem': True, 'trace_max': 512, 'update_max': 64,
                   'child_fixture_max': 1048576, 'child_input_ledger_max': 131072,
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
        if len(ledger_bytes) > 131072:
            raise ValueError('Input ledger bound')
        (work / 'input-ledger.json').write_bytes(ledger_bytes); ledger_id = sha(ledger_bytes)

        def verify():
            if any(path.read_bytes() != raw for path, raw in frozen.items()) or any(path.read_bytes() != raw for path, raw in owned.items()):
                raise ValueError('Source changed during struct-clear qualification')
            if any(sha(path.read_bytes()) != digest for path, digest in dep_snapshots.items()):
                raise ValueError('CryptoPP dependency changed during qualification')
            for command, tool in tools.items():
                if (Path(shutil.which(command)).resolve() != Path(tool['resolved_path']) or
                        sha(Path(tool['resolved_path']).read_bytes()) != tool['executable_sha256']):
                    raise ValueError('Compiler changed during struct-clear qualification')
            if (sha(python_path.read_bytes()) != environment['python_executable_sha256'] or
                    sha(zlib_path.read_bytes()) != environment['reference_zlib_module_sha256']):
                raise ValueError('Python/reference zlib binary changed')

        def command(command_args, stem, env=None):
            result = subprocess.run(list(map(str, command_args)), capture_output=True, text=True, timeout=240, env=env)
            Path(str(stem) + '.stdout').write_text(result.stdout)
            Path(str(stem) + '.stderr').write_text(result.stderr)
            if result.returncode:
                raise RuntimeError('STRUCT_CLEAR_QUALIFICATION_REFUSED ' + str(stem) + '\n' +
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
                   '-Wno-parentheses', '-Wno-unused-parameter', '-Wno-unused-value', '-Wno-unused-but-set-variable', '-Wno-pointer-sign', '-pedantic', '-fno-strict-aliasing']
        cpp_flags = [*dep_flags, '-Wall', '-Wextra']
        for mode, flags in modes:
            directory = work / mode; directory.mkdir(); nonce = os.urandom(32).hex()
            compile_profile = {'schema': 'coh-struct-clear-fixture-compile-profile-v1', 'mode': mode,
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
            identity_header = directory / 'struct-clear-qualification-identity.h'
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
            exe = directory / 'struct-clear'
            cmd = [cxx, *flags, *map(str, objects), *link_flags, '-lcrypto', '-o', str(exe)]
            command(cmd, directory / 'link'); commands.append(cmd)
            commands_bytes = canonical(commands); (directory / 'commands.json').write_bytes(commands_bytes)
            build = {'schema': 'coh-struct-clear-fixture-build-v1', 'compile_profile': compile_profile,
                     'compile_profile_sha256': compile_id, 'commands_sha256': sha(commands_bytes),
                     'commands': commands, 'source_identity_sha256': source_id, 'profile_sha256': profile_id,
                     'fixture_run_nonce': nonce, 'generated_identity_header_sha256': sha(identity.encode()),
                     'executable_bytes': exe.stat().st_size, 'executable_sha256': sha(exe.read_bytes())}
            build_bytes = canonical(build)
            if len(build_bytes) > 65536:
                raise ValueError('Build receipt bound')
            (directory / 'build.json').write_bytes(build_bytes); build_id = sha(build_bytes)
            ledger = b'COHUB1\0\0' + b''.join(bytes.fromhex(value) for value in
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
        if not stack or any(row['bound'] not in ('static', 'dynamic,bounded') or row['bytes']>98304 for row in stack):
            raise ValueError('Unbounded selected native stack')
        # A deliberately overinclusive own-C bound: sum every emitted provider
        # frame, then add measured duplicates for the only schema-depth2 call
        # paths. External C++/libc/sanitizer frames remain outside this claim.
        provider_frames=[row for row in stack if row['report']=='release/provider.su']
        recursive_names=('StructClear','nonarray_destroystruct','ParserReadBinaryTable','observed_table','nonarray_readbin')
        provider_sum=sum(row['bytes']for row in provider_frames)
        reentrant_extra=sum(row['bytes']for row in provider_frames if row['function'].split('.')[0]in recursive_names)
        if not provider_frames or provider_sum+reentrant_extra>98304:
            raise ValueError('Bounded schema own-C frame reserve exceeded')
        verify()
        resources = {'profile_input_max': 65536, 'profile_type_max': 4095,
                     'fixture_file_bytes': wire.stat().st_size, 'fixture_file_max': 1048576,
                     'input_ledger_bytes': len(ledger_bytes), 'input_ledger_max': 131072,
                     'native_stdout_max': 4096, 'per_build_receipt_max': 65536,
                     'provider_owned_static_bytes': checks['release']['provider_owner_bytes'],
                     'actual_Adler_object_bytes': checks['release']['crypto_object_bytes'],
                     'wrapper_stack_charge_reserve': 98304, 'wrapper_total_budget_max': 1048576,
                     'digest_scratch_reserve_fixture': 65536, 'retained_reserve_fixture': 65536,
                     'selected_release_max_frame': max(row['bytes'] for row in stack),
                     'selected_release_frame_count': len(stack), 'all_provider_frame_sum':provider_sum,
                     'supported_schema_reentrant_extra':reentrant_extra, 'conservative_own_C_stack_bound':provider_sum+reentrant_extra,
                     'stack_scope': 'new C provider/test and actual wrapper/Adler core only; every selected frame must fit98,304B own reserve; every dependency .su retained. No aggregate/external stack closure',
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
        proof = {'schema': 'coh-original-struct-clear-qualification-v1', 'passed': True,
                 'source_revision': run(['git', '-C', root, 'rev-parse', 'HEAD']).stdout.strip(),
                 'source_sha256': source_hashes, 'source_stable_before_after': True, 'host_environment': environment,
                 'host_python_and_reference_zlib_module_stable_before_after': True, 'host_compiler_identities': tools,
                 'host_compilers_stable_before_after': True, 'original_struct_clear_provider': compact_origin,
                 'source_schema_and_body_fixtures': compact_inputs, 'fixture_source_identity': source_identity,
                 'fixture_source_identity_sha256': source_id, 'fixture_profile': profile,
                 'fixture_profile_sha256': profile_id, 'child_measured_fixture_bindings': bindings,
                 'checks': checks, 'builds': builds, 'resource_bounds': resources, 'native_stack_frames': stack,
                 'full_dependency_stack_reports': stack_reports, 'evidence_files': files,
                 'scope': 'Original StructClear/destructor extension. Whole unchanged original bpReadBodyPartFiles/ParserLoadFilesShared SMAR_Error/ParserLoadFiles invokes actual ParserIsPersistNewer actual CRC/CryptoPP/SerializeReadOpen ignoreCRC1, hands SAME live handle to original ParserReadBinaryFile, executes FileListRead(NULL)/body and source close. Source cache-hit early return preserves cached words and never preprocesses; production rejection reaches unchanged original StructClear and all required supported BodyPart destructor/TokenStore leaves. Environment shells do not prove filesystem selection. Every authentic field compared independently; production CRC mismatch acceptance preserved. One terminal truncation proves inherited preflight prevents destructor entry; accepted broad prefix suite is not replayed. Direct fixed-arena reservation and open refusals are separately qualified; unsafe original NULL/new failures are not simulated. Source/input/ELF/build/profile/random labels are measured fixture associations, never current Map attestation.',
                 'actual_original_ParserLoadFiles_executed': True, 'actual_original_ParserLoadFilesShared_SMAR_Error_executed': True, 'actual_original_ParserIsPersistNewer_executed': True, 'actual_original_ParserReadBinaryFile_SUPPLIED_handle_executed': True,
                 'actual_original_ParseTableCRC_executed': True, 'actual_original_SerializeReadOpen_executed': True,
                 'actual_original_CryptoPP_Adler32_executed': True, 'production_ignoreCRC1_preserved': True, 'shared_acquisition_shell': 'SMAR_Error only', 'source_ParseBoneNames_calls':0, 'filesystem_selection_or_mode_helpers_qualified':False,
                 'development_mode_executed': False, 'date_or_filesystem_freshness_executed': False,
                 'original_FileListRead_NULL_executed': True, 'full_original_body_reader_executed': True,
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
