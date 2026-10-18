"""NEW owner composition fixtures from the admitted original writer; no old test entrypoint.

Importing this module is inert. produce() is for the new owner wire qualification
only. Its grants/lists/Map offers are synthetic, never an authenticated server.
"""
import ctypes as C
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

CHECK = 'native-android/engine/dbclient/check.py'
PINS = 'native-android/engine/dbclient/source-pins.json'
PREPARE = 'native-android/tools/protocol_fixture/prepare.py'
FIXED = {
 CHECK: (13934, '2cd5e8b80b593584e71f63cab21d774c00d39ec4056ae846d4698da68faac410'),
 PINS: (1167, 'a8c82a4c35eb73325ab4c7e0727645e40899330e7d7450b2c5976b26a89dbeb1'),
 PREPARE: (15215, '3739f5ac245e92e668507179f281d14afceff5f7d3f82b1859fcfc44fcdf724a'),
}
BEFORE = (' old_profile=profile;Packet *pak;int slot_number=3,createLocation=0;'
          'U32 local_map_ip=0x0100007f;strcpy(db_info.players[3].name,"Native Fixture");\n').encode()
AFTER = (' old_profile=profile;Packet *pak;int slot_number=0,createLocation=1;'
         'U32 local_map_ip=0;strcpy(db_info.players[0].name,"New Fixture");\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def committed(root, name, expected=None):
    path = root / name
    need(path.resolve() == path and path.is_file() and not path.is_symlink(), 'ORACLE_CANONICAL_SOURCE')
    raw = path.read_bytes()
    need(0 < len(raw) < 2 * 1024**2, 'ORACLE_SOURCE_BOUND')
    need(subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:' + name]) == raw,
         'ORACLE_COMMITTED_SOURCE')
    if expected is not None:
        need((len(raw), sha(raw)) == expected, 'ORACLE_FIXED_SOURCE')
    return raw


def produce(root: Path, work: Path):
    """Use one existing EMPTY private work directory and write the new header."""
    root = root.resolve(strict=True)
    work = work.absolute()
    need(work.resolve() == work and work.is_dir() and not work.is_symlink() and
         not any(work.iterdir()) and root not in work.parents and work != root,
         'ORACLE_FRESH_EXTERNAL_DIRECTORY')
    raw = {name: committed(root, name, pin) for name, pin in FIXED.items()}
    source_inputs = {name: sha(value) for name, value in raw.items()}
    source_pins = json.loads(raw[PINS])['sha256_lf']
    need(len(source_pins) == 10, 'ORACLE_TEN_ORIGINAL_INPUTS')
    originals = {}
    for name, digest in source_pins.items():
        value = committed(root, 'upstream/ouroboros/' + name)
        need(sha(value.replace(b'\r\n', b'\n')) == digest, 'ORACLE_ORIGINAL_LF_SOURCE')
        originals[name] = value.replace(b'\r\n', b'\n')
        source_inputs['upstream/ouroboros/' + name] = sha(value)
    client = originals['Game/src/clientcomm/dbclient.c']
    start = client.index(b'    pak = pktCreateEx(&db_comm_link,DBGAMECLIENT_CHOOSE_PLAYER);')
    end = client.index(b'    pktSend(&pak,&db_comm_link);', start)
    choose_block = client[start:end]

    # Admission above precedes BOTH normal project imports. The unchanged
    # check.py oracle writes its original generated C, then this one-call run
    # adapter changes ONLY trusted fixture inputs before its single compile.
    prior_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    accepted = None
    original_run = None
    observed = {}
    try:
        spec = importlib.util.spec_from_file_location('fresh_character_accepted_db_writer', root / CHECK)
        need(spec is not None and spec.loader is not None, 'ORACLE_IMPORT_SPEC')
        accepted = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(accepted)
        need(set(accepted.FILES) == set(source_pins), 'ORACLE_ORIGINAL_INVENTORY')
        original_run = accepted.run

        def compile_new_fixture(cmd, **kwargs):
            need(not observed and not kwargs and list(map(str, cmd)) == [
                'cc', '-std=c99', '-O0', '-fwrapv', '-fPIC', '-shared', '-w',
                '-I' + str(root / 'native-android/include'), str(work / 'oracle.c'),
                '-lz', '-o', str(work / 'oracle.so')], 'ORACLE_EXACT_SINGLE_COMPILE')
            path = work / 'oracle.c'
            before = path.read_bytes()
            need(before.count(BEFORE) == 1 and AFTER not in before and
                 before.count(choose_block) == 1, 'ORACLE_EXACT_FIXTURE_DECLARATION')
            after = before.replace(BEFORE, AFTER, 1)
            need(after.replace(AFTER, BEFORE, 1) == before and
                 after.count(choose_block) == 1, 'ORACLE_WRITER_AND_CHOOSE_BLOCK_UNCHANGED')
            observed.update(generated_source_before_sha256=sha(before),
                            generated_source_sha256=sha(after),
                            generated_source_bytes=len(after),
                            exact_fixture_declaration_only=True)
            path.write_bytes(after)
            return original_run(cmd)

        accepted.run = compile_new_fixture
        lib, writer_pins = accepted.oracle(root, work)
        need(writer_pins == source_pins and observed.get('exact_fixture_declaration_only') is True,
             'ORACLE_UNCHANGED_ORIGINAL_WRITER_ADMISSION')
    finally:
        if accepted is not None and original_run is not None:
            accepted.run = original_run
        sys.dont_write_bytecode = prior_bytecode

    def u(width, value):
        return [(width, value)]

    def p(value):
        return [(-1, value)]

    def s(value):
        return [(8, c) for c in value.encode('ascii') + b'\0']

    def floating(value):
        return u(32, struct.unpack('<I', struct.pack('<f', value))[0])

    def auto(value):
        widths = [2, 10, 24, 32]
        which = next(i for i, width in enumerate(widths) if value < 1 << width)
        return u(2, which) + u(widths[which], value)

    def array(value):
        return [(-99, c) for c in value]

    def fields(values, aligned):
        widths = (C.c_int * len(values))(*(v[0] for v in values))
        words = (C.c_uint32 * len(values))(*(v[1] for v in values))
        output = (C.c_uint8 * 65536)()
        bits = C.c_uint32()
        lib.original_fields(widths, words, len(values), aligned, output, C.byref(bits))
        need(0 < bits.value <= len(output) * 8, 'ORACLE_OUTPUT_BOUND')
        return bytes(output[:(bits.value + 7) // 8]), bits.value

    values = p(2) + auto(900001) + s('') + u(1, 0) + u(1, 0) + u(1, 0)
    values += p(2) + p(2) + p(0) + p(0) + p(0)
    for _ in range(2):
        values += p(0) + s('EMPTY') + s('') + s('')
        values += p(0) + p(0) + p(0) + auto(0) + p(0) + s('') + s('')
        values += p(0) + floating(0) + floating(0) + u(32, 0) + s('') + p(0)
        values += u(32, 0) + u(32, 0) + u(2, 0)
    values += array(bytes(128)) + array(bytes(128))
    player_wire = fields(values, 0)
    output = (C.c_uint8 * 65536)(); bits = C.c_uint32()
    lib.original_choose(0, output, C.byref(bits))
    need(0 < bits.value <= len(output) * 8, 'ORACLE_CHOOSE_OUTPUT_BOUND')
    choose_wire = bytes(output[:(bits.value + 7) // 8]), bits.value
    map_wire = fields(p(4) + p(17) + p(1) + p(0x0100007f) + p(0x0200007f) +
                      p(7001) + p(7002) + p(123456), 0)
    # These three replies are new source-layout synthetic fields. Native Auth
    # framing/parser/RSA are executed only by the separate new C peer harness.
    login_ok = bytes([3]) + bytes(range(1, 9)) + bytes(range(17, 25)) + bytes(28)
    shards = bytes([4, 1, 1, 1, 127, 0, 0, 1]) + struct.pack('<I', 7000)
    shards += bytes([0, 0]) + struct.pack('<HH', 0, 100) + bytes([1, 0])
    shards += bytes([0])  # Ordinary (not extended) shard record: empty name.
    play_ok = bytes([7]) + struct.pack('<II', 0x12345678, 900001) + bytes([1])
    need(len(login_ok) == 45 and len(shards) == 21 and len(play_ok) == 10,
         'ORACLE_AUTH_REPLY_EXACT_LAYOUT')
    header = ['/* NEW synthetic owner wire inputs; original DB bit/string/choose writers. */\n']
    for name, (data, bit_count) in zip(('fresh_players', 'fresh_choose', 'fresh_map'),
                                      (player_wire, choose_wire, map_wire)):
        header.append('static const uint8_t ' + name + '_bytes[]={' + ','.join(map(str, data)) + '};\n')
        header.append('static const Wire ' + name + '={' + name + '_bytes,' + str(bit_count) + 'u};\n')
    for name, data in [('fresh_auth_login_ok', login_ok), ('fresh_auth_shards', shards),
                       ('fresh_auth_play_ok', play_ok)]:
        header.append('static const uint8_t ' + name + '[]={' + ','.join(map(str, data)) + '};\n')
    header_bytes = ''.join(header).encode('ascii')
    with (work / 'fresh-character-wire-fixtures.h').open('xb') as stream:
        stream.write(header_bytes)
    for name, digest in source_inputs.items():
        need(sha(committed(root, name)) == digest, 'ORACLE_SOURCE_CHANGED')
    return {'schema': 'coh-fresh-character-original-writer-fixtures-v1',
        'source_inputs_sha256': source_inputs, 'whole_source_sha256_lf': source_pins,
        'original_choose_block_sha256_lf': sha(choose_block), **observed,
        'fixture_adapter': 'slot0/name New Fixture/local_map_ip0/source_create_location1 only',
        'accepted_oracle_function_unchanged': True,
        'normal_pinned_imports_after_git_admission': True,
        'single_new_fixture_compile': True, 'temporary_run_adapter_restored': accepted.run is original_run,
        'original_choose_profiles_executed': 1, 'original_scalar_string_bit_writers_executed': True,
        'original_login_executed': False,
        'old_choose_fixture_or_old_fixtures_or_old_main_executed': False,
        'DB_fixture_count': 3, 'Auth_source_layout_reply_count': 3,
        'synthetic_source_layout_lists_and_offers': True,
        'header_bytes': len(header_bytes), 'header_sha256': sha(header_bytes),
        'oracle_elf_sha256': sha((work / 'oracle.so').read_bytes()),
        'real_auth_db_map_servers_or_network_executed': False}
