#!/usr/bin/env python3
"""Execute hash-pinned original GROUPS producers on bounded trusted input.

This is a host-only oracle, never a server capture. Original worldSendUpdate,
sendGroupFile, sendDef, property serializers, matrix packing and BitStream
functions are extracted without body edits. A small trusted shim supplies
bounded engine objects and trap-only unsupported services. Legacy bit code is
run at O0 without sanitizers; the native parser is separately sanitized.
"""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import re
import subprocess
import tempfile
import zlib

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE_FUNCTIONS = {
    'libs/UtilitiesLib/src/components/BitStream.c': [
        'initBitStream', 'bsSetByteAlignment', 'bsWriteBits', 'bsWriteBitsPack', 'bsWriteString',
        'bsWriteF32', 'bsAlignByte', 'bsGetCursorBitPosition'],
    'libs/UtilitiesLib/src/network/net_packet.c': [
        'pktSetByteAlignment', 'pktSetCompression',
        'pktSendBits', 'pktSendBitsPack', 'pktSendString', 'pktSendF32'],
    'libs/UtilitiesLib/src/network/net_packetutil.c': [
        'pktSendIfSetF32', 'pktSendBitsAuto'],
    'libs/UtilitiesLib/include/utilitieslib/network/net_packet_common.h': [
        'pktSendVec3', 'pktSendMat4'],
    'libs/UtilitiesLib/src/network/netcomp.c': [
        'unitZeroMat', 'unpackMat', 'packMat', 'pktSendF32Comp',
        'pktSendF32Deg', 'sendMat4'],
    'libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h': [
        'nearSameVec3', 'nearSameVec3Tol', 'normalVec3'],
    'libs/UtilitiesLib/src/utils/mathutil.c': [
        'extractScale', 'scaleMat3Vec3', 'createMat3YPR', 'getMat3YPR'],
    'Common/group/groupProperties.c': [
        'PropertyTablePaketWriter', 'WriteGroupPropertiesToPacket'],
    'Common/group/group.c': [
        'groupInfoCrcDefs', 'cryptAdler32UpdateString', 'groupInfoCrcRefs',
        'groupInfoRefCount'],
    'MapServer/src/group/groupnetsend.c': [
        'sendDef', 'sendGroupFile', 'sendLoadScreenPages', 'worldSendUpdate'],
}
AUDIT_PATHS = [
    'Common/comm_game.h', 'Common/group/groupProperties.h',
    'Common/entity/gametypes.h',
    'libs/UtilitiesLib/src/network/net_version.c',
    'Game/src/group/groupnetrecv.c',
    'libs/UtilitiesLib/include/utilitieslib/network/net_packet_common.h',
    'libs/UtilitiesLib/src/network/crypt.cpp',
    'libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h',
]


def run(command, **kwargs):
    result = subprocess.run(command, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(repr(command) + '\n' + result.stdout + result.stderr)
    return result


def read_source(repo, relative):
    """Sparse checkouts may omit a source blob; read exact tracked HEAD then."""
    path = repo / 'upstream/ouroboros' / relative
    if path.is_file():
        data = path.read_bytes()
    else:
        data = subprocess.check_output([
            'git', '-C', str(repo), 'show', 'HEAD:upstream/ouroboros/' + relative])
    return data.replace(b'\r\n', b'\n').decode()


def extract(source, name):
    pattern = r'^[\w \t*]+\b' + re.escape(name) + r'\s*\([^;{}]*\)\s*\{'
    match = re.search(pattern, source, re.M)
    if not match:
        raise ValueError('Original function not found: ' + name)
    begin = source.index('{', match.start())
    depth, at = 1, begin + 1
    while depth:
        depth += (source[at] == '{') - (source[at] == '}')
        at += 1
    return source[match.start():at] + '\n'


def sources_and_pins(repo):
    sources = {p: read_source(repo, p) for p in dict.fromkeys(
        [*SOURCE_FUNCTIONS, *AUDIT_PATHS])}
    pins = {
        'schema': 1,
        'repository': 'Russianranger/coh-android',
        'reference_commit': 'bf653dd4ef5372c921b049a76f902a4a921e8c4d',
        'sha256_lf': {p: hashlib.sha256(s.encode()).hexdigest()
                      for p, s in sources.items()},
        'functions': {name: {
            'source': p,
            'sha256_lf': hashlib.sha256(extract(sources[p], name).encode()).hexdigest()
        } for p, names in SOURCE_FUNCTIONS.items() for name in names},
        'checksum_adapter': 'zlib Adler32 with source Crypto++ digest-byte order; '
                            'original groupInfoCrcDefs/Refs/RefCount executed',
    }
    return sources, pins


def compile_oracle(repo, directory, sources):
    spec = importlib.util.spec_from_file_location(
        'coh_original_bit_reference', repo / 'native-android/tools/protocol_fixture/prepare.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    preamble = helper.PREAMBLE
    preamble = preamble.replace(
        'typedef struct {int ack_count;U32 ids_toack[32];int compressionAllowed,orderedAllowed;} NetLink;',
        'typedef struct {U32 last_update_time;int last_world_id;} NetLink;')
    preamble = preamble.replace(
        'static void pktSendBitsAuto(Packet *p,unsigned int v){(void)p;(void)v;assert(0);}', '')
    preamble = preamble.replace('ordered,ordered_id;} Packet;', 'ordered,ordered_id,reliable;} Packet;')
    code = preamble + '\n' + (HERE / 'tests/groups_oracle_shim.h').read_text()
    # Dependency order deliberately differs from the source-file inventory.
    order = [
        ('libs/UtilitiesLib/src/components/BitStream.c', SOURCE_FUNCTIONS['libs/UtilitiesLib/src/components/BitStream.c']),
        ('libs/UtilitiesLib/src/network/net_packet.c', SOURCE_FUNCTIONS['libs/UtilitiesLib/src/network/net_packet.c']),
        ('libs/UtilitiesLib/src/network/net_packetutil.c', SOURCE_FUNCTIONS['libs/UtilitiesLib/src/network/net_packetutil.c']),
        ('libs/UtilitiesLib/include/utilitieslib/network/net_packet_common.h', SOURCE_FUNCTIONS['libs/UtilitiesLib/include/utilitieslib/network/net_packet_common.h']),
        ('libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h', SOURCE_FUNCTIONS['libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h']),
        ('libs/UtilitiesLib/src/utils/mathutil.c', SOURCE_FUNCTIONS['libs/UtilitiesLib/src/utils/mathutil.c']),
        ('libs/UtilitiesLib/src/network/netcomp.c', SOURCE_FUNCTIONS['libs/UtilitiesLib/src/network/netcomp.c']),
        ('Common/group/groupProperties.c', SOURCE_FUNCTIONS['Common/group/groupProperties.c']),
        ('Common/group/group.c', SOURCE_FUNCTIONS['Common/group/group.c']),
        ('MapServer/src/group/groupnetsend.c', SOURCE_FUNCTIONS['MapServer/src/group/groupnetsend.c']),
    ]
    for path, names in order:
        if path.endswith('netcomp.c'):
            code += '\n#undef NEARZERO\n#define NEARZERO 1e-16\n#define INT_SCALE 2\n'
        code += '\n'.join(extract(sources[path], name) for name in names)
    code += '\n' + (HERE / 'tests/groups_oracle_harness.c').read_text()
    original = directory / 'groups-original.c'
    original.write_text(code)
    output = directory / 'groups-original.so'
    run(['cc', '-std=c99', '-O0', '-fno-strict-aliasing', '-fPIC', '-shared', '-w',
         '-I' + str(repo / 'native-android/include'), str(original), '-lm', '-lz',
         '-o', str(output)])
    lib = C.CDLL(str(output))
    lib.groups_original.argtypes = [C.c_uint32, C.c_uint32, C.c_uint32,
        C.c_void_p, C.POINTER(C.c_uint32), C.POINTER(C.c_uint32)]
    lib.groups_original.restype = C.c_int
    return lib


def source_crc(parts):
    """Crypto++ Final writes big-endian digest bytes, read as little-endian U32."""
    value = zlib.adler32(b''.join(parts)) & 0xffffffff
    return int.from_bytes(value.to_bytes(4, 'big'), 'little')


def expectations(case):
    common = dict(new_world=1, files=0, present_files=0, defs=0,
                  removed_defs=0, children=0, roots=0, removed_roots=0,
                  properties=0, swaps=0, raw_matrices=0, packed_matrices=0,
                  max_def_id=0, max_root_id=0, footer_file_count=0,
                  footer_active_roots=0, footer_defs_crc=source_crc([]),
                  footer_refs_crc=source_crc([]))
    if case == 1:
        common.update(files=1, present_files=1, defs=1, roots=1,
            packed_matrices=1, footer_file_count=1, footer_active_roots=1,
            footer_defs_crc=source_crc([b'oracle_root']),
            footer_refs_crc=source_crc([b'oracle_root']))
    elif case in (2, 3, 8):
        common.update(new_world=int(case != 3), files=3, present_files=3,
            defs=5 if case == 8 else 4, removed_defs=1, children=2, roots=4, removed_roots=1,
            properties=2, swaps=2, raw_matrices=2, packed_matrices=3,
            max_def_id=2, max_root_id=3, footer_file_count=3,
            footer_active_roots=3,
            footer_defs_crc=source_crc([b'oracle_rich', b'NAMELESS', b'oracle_future',
                                       b'oracle_saved_library', b'oracle_other_file']),
            footer_refs_crc=source_crc([b'oracle_rich', b'oracle_future',
                                       b'oracle_future', b'oracle_other_file']))
    elif case == 4:
        common.update(new_world=0, files=2, present_files=1,
            defs=1, removed_defs=1, roots=2, removed_roots=1,
            packed_matrices=1, max_def_id=1, max_root_id=3,
            footer_file_count=2, footer_active_roots=2,
            footer_defs_crc=source_crc([b'oracle_root', b'NAMELESS', b'oracle_saved_library']),
            footer_refs_crc=source_crc([b'oracle_root', b'oracle_saved_library']))
    elif case == 5:
        names = [f'oracle_large_{i:04d}'.encode() for i in range(192)]
        common.update(files=1, present_files=1, defs=192, children=384,
            roots=4, properties=384, swaps=384, raw_matrices=194,
            packed_matrices=194, max_def_id=191, max_root_id=3,
            footer_file_count=1, footer_active_roots=4,
            footer_defs_crc=source_crc(names),
            footer_refs_crc=source_crc(sum(([names[i], names[(i+1) % 192]]
                                           for i in range(4)), [])))
    elif case == 6:
        common.update(files=1, present_files=1)
    elif case == 7:
        common.update(files=1, present_files=1, defs=1, roots=3,
            packed_matrices=3, max_root_id=2, footer_file_count=1,
            footer_active_roots=3, footer_defs_crc=source_crc([b'oracle_matrix']),
            footer_refs_crc=source_crc([b'oracle_matrix'] * 3))
    elif case == 9:
        common.update(files=1, present_files=1, defs=3, max_def_id=2,
            footer_file_count=1,
            footer_defs_crc=source_crc([b'oracle_trick_empty', b'oracle_ambient', b'oracle_light']))
    elif case == 10:
        pass
    return common


def produce_fixtures(source_root=REPO, directory=None):
    """Return (fixtures, receipt), emitting only trusted original-source inputs.

    Payloads include a modern normalized command (6), or old wire command (11).
    This command-number adapter is explicit; the oracle does not execute the
    later pktSend wire-command remapping. Packed and byte_aligned are scalar
    representations after transport decompression, not zlib wire streams.
    Exact source compression setters select byte alignment before writing.
    Packed bodies use incremental full_update=0 with all mod-times above the
    link checkpoint. Aligned bodies use full_update=1 except the intentional
    incremental case, whose controlled packet-factory compression default is1.
    """
    repo = Path(source_root).resolve()
    if directory is None:
        with tempfile.TemporaryDirectory(prefix='coh-groups-oracle-') as temp:
            return produce_fixtures(repo, Path(temp))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    sources, pins = sources_and_pins(repo)
    expected_pins = json.loads((HERE / 'groups-source-pins.json').read_text())
    if pins != expected_pins:
        raise ValueError('GROUPS original source/function pins differ')
    lib = compile_oracle(repo, directory, sources)
    fixtures = []
    cases = ['empty_world', 'minimal_world', 'rich_world', 'rich_same_world',
             'incremental_world', 'large_world', 'unsupported_base_header',
             'matrix_variants_world', 'force_reload_world',
             'alternate_tricks_world', 'no_pages_world']
    for case, name in enumerate(cases):
        for aligned, representation in enumerate(['packed', 'byte_aligned']):
            for legacy in (0, 1):
                output = (C.c_uint8 * (1024 * 1024))()
                bits = C.c_uint32()
                footer = (C.c_uint32 * 4)()
                result = lib.groups_original(case, aligned, legacy, output,
                                             C.byref(bits), footer)
                if result != 1 or not bits.value:
                    raise ValueError('Original producer failed: ' + name)
                payload = bytes(output[:(bits.value + 7) // 8])
                wanted = expectations(case)
                actual_footer = dict(zip(['footer_file_count', 'footer_active_roots',
                    'footer_defs_crc', 'footer_refs_crc'], footer))
                if case != 6 and any(wanted[k] != v for k, v in actual_footer.items()):
                    raise ValueError('Independent checksum/footer oracle differs: ' + name)
                fixture_name = name + '_' + representation + ('_legacy' if legacy else '')
                fixtures.append(dict(name=fixture_name, representation=representation,
                    legacy_commands=legacy, payload_hex=payload.hex(),
                    payload_bits=bits.value, payload_bytes=len(payload),
                    sha256=hashlib.sha256(payload).hexdigest(), expected_status=2 if case == 6 else 0,
                    expected=wanted if case != 6 else {},
                    source_case=case, source_producer=True,
                    full_update=bool(aligned and case != 4),
                    packet_default_compression=aligned,
                    command_number_adapter='normalized6_to_legacy_wire11' if legacy else 'normalized6',
                    source_scope='original base header; nested base body omitted' if case == 6
                        else 'complete normal-world grammar',
                    scene_tail_complete=case != 6, captured_server_data=False))
    large = next(f for f in fixtures if f['name'] == 'large_world_byte_aligned')
    if large['payload_bytes'] <= 42889:
        raise ValueError('Large fixture no longer exercises physical decoded-body scale')
    receipt = dict(schema=1, passed=True,
        scope='deterministic trusted original-source producer execution; no server capture/login/world acceptance',
        source_files=len(pins['sha256_lf']), source_functions=len(pins['functions']),
        fixtures=len(fixtures), success_fixtures=sum(f['expected_status'] == 0 for f in fixtures),
        unsupported_base_fixtures=sum(f['expected_status'] == 2 for f in fixtures),
        source_pin_sha256=hashlib.sha256((HERE / 'groups-source-pins.json').read_bytes()).hexdigest(),
        original_harness_sha256=hashlib.sha256((directory / 'groups-original.c').read_bytes()).hexdigest(),
        original_producer_sanitized=False,
        compression_helpers='unchanged pktSetCompression, pktSetByteAlignment and bsSetByteAlignment; '
            'trusted packet factory supplies controlled compressionDefault0/1 before any writes',
        packed_full_updates=0,
        checksum_adapter=pins['checksum_adapter'],
        fixtures_sha256=hashlib.sha256((json.dumps(fixtures, sort_keys=True,
            separators=(',', ':')) + '\n').encode()).hexdigest(),
        large_fixture={k: large[k] for k in ['name', 'payload_bits', 'payload_bytes', 'sha256', 'expected']},
        authentic_server_interoperability=False, authenticated_session=False,
        resolved_asset_graph=False, authoritative_spawn=False)
    return fixtures, receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, default=REPO)
    parser.add_argument('--initialize-pins', action='store_true')
    parser.add_argument('--fixtures-output', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.initialize_pins:
        _, pins = sources_and_pins(args.source_root.resolve())
        (HERE / 'groups-source-pins.json').write_text(json.dumps(pins, indent=2) + '\n')
    fixtures, receipt = produce_fixtures(args.source_root)
    if args.fixtures_output:
        args.fixtures_output.parent.mkdir(parents=True, exist_ok=True)
        args.fixtures_output.write_text(json.dumps(fixtures, indent=2) + '\n')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
