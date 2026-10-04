#!/usr/bin/env python3
"""Stage separately receipted, opt-in MapServer and creation/resume UDP bindings.

The immutable source, earlier donors and default socket behavior are preserved.
This prepares source only; it makes no native Windows/Android acceptance claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from prepare_runtime import expected_pg_receipt, pg_receipt_matches, require, sha256
from prepare_resume_client_source import (apply_patch, canonical_hash,
                                         expected_resume_receipt, apply_resume_overlay)
import prepare_resume_client_source as resume

ROOT = Path(__file__).resolve().parents[1]
PATCH = 'patches/game-loopback/0001-game-loopback-bindings.patch'
RECEIPT = 'game-loopback-build-input.json'
GAME_FILES = ('libs/UtilitiesLib/src/network/sock.c',
              'libs/UtilitiesLib/include/utilitieslib/network/sock.h',
              'libs/UtilitiesLib/src/network/net_link.c',
              'Utilities/TestClient/src/packetFlood.c',
              'MapServer/src/svr/svr_init.c', 'Utilities/TestClient/src/main.c')
VARIANTS = ('creation', 'resume')


def patch_bytes(root=ROOT):
    patch = (root / PATCH).read_bytes().replace(b'\r\n', b'\n')
    names = [line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/')]
    require(len(names) == len(GAME_FILES) and set(names) == set(GAME_FILES),
            'Unexpected game loopback patch file list')
    return patch


def loopback_metadata(source):
    constants = dict(re.findall(r'^#define (COH_GAME_LOOPBACK_\w+) "([^"\n]+)"$', source, re.MULTILINE))
    require(set(constants) == {'COH_GAME_LOOPBACK_ENVIRONMENT', 'COH_GAME_LOOPBACK_ACK'},
            'Unexpected game loopback source contract')
    return {
        'environment_variable': constants['COH_GAME_LOOPBACK_ENVIRONMENT'],
        'enabled_value': '1', 'disabled_by_default': True,
        'activation': 'before_common_startup',
        'late_activation': 'refused_after_first_explicit_or_client_UDP_bind_attempt',
        'wildcard_address': '127.0.0.1', 'explicit_addresses': 'IPv4_127/8_only',
        'client_UDP': 'explicit_loopback_ephemeral_bind_before_first_send',
        'endpoint_verification': 'getsockname_and_SO_TYPE_after_each_successful_bind',
        'socket_types': ['tcp', 'udp'], 'endpoint_record': 'protocol_address_port',
        'scope': 'explicit_IPv4_listeners_and_client_UDP_bindings',
        'network_namespace_isolation': False, 'outbound_connections_restricted': False,
        'outbound_TCP': 'unchanged', 'failure': 'close_socket_and_exit_2',
        'startup_acknowledgement': constants['COH_GAME_LOOPBACK_ACK'],
        'android_execution_validated': False,
    }


def socket_contract(root=ROOT):
    """Pin the actual listener constant and all direct game-client UDP paths."""
    names = ('Common/comm_backend.h', 'MapServer/src/svr/svr_init.c',
             'libs/UtilitiesLib/src/network/net_linklist.c',
             'libs/UtilitiesLib/src/network/net_link.c', 'Utilities/TestClient/src/packetFlood.c',
             'Utilities/TestClient/src/win_init.c')
    contents = {name: (root / 'upstream/ouroboros' / name).read_bytes() for name in names}
    texts = {name: value.decode() for name, value in contents.items()}
    matches = re.findall(r'^#define\s+DEFAULT_DBGAMECLIENT_PORT\s+(\d+)\b',
                         texts[names[0]], re.MULTILINE)
    require(len(matches) == 1 and int(matches[0]) + 1 == 7001
            and re.search(r'^#define\s+BASE_MAPSERVER_PORT\s+\(DEFAULT_DBGAMECLIENT_PORT\+1\)',
                          texts[names[0]], re.MULTILINE), 'MapServer listener port changed')
    require('server_state.udp_port = BASE_MAPSERVER_PORT;' in texts[names[1]]
            and 'netInit(&net_links,server_state.udp_port,server_state.tcp_port)' in texts[names[1]],
            'MapServer listener call site changed')
    require(texts[names[3]].count('socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP)') == 1
            and texts[names[4]].count('socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)') == 2,
            'Direct client UDP socket paths changed')
    require('    newConsoleWindow();\n    return main(argc,argv);' in texts[names[5]],
            'TestClient console must exist before policy acknowledgement')
    return {
        'scope': 'fakeauth_Atlas_create_save_restart_resume',
        'source_sha256': {name: hashlib.sha256(value).hexdigest() for name, value in contents.items()},
        'mapserver': {'required_endpoints': [{'protocol': 'udp', 'address': '127.0.0.1',
                                            'port': int(matches[0]) + 1, 'constant': 'BASE_MAPSERVER_PORT'}]},
        'testclient': {'protocol': 'udp', 'address': '127.0.0.1', 'port': 'assigned_nonzero',
                       'minimum_binds_per_session': 2,
                       'paths': ['netOpenSocketUdp', 'sendToUDP', 'sendToUDPStream']},
    }


def expected_game_receipt(root=ROOT, postgresql_build_input=None, variant='creation'):
    root = Path(root)
    require(variant in VARIANTS, 'Invalid game source variant')
    lock = json.loads((root / 'upstream-lock.json').read_text())
    pg = expected_pg_receipt(root, lock)
    if postgresql_build_input is not None:
        require(pg_receipt_matches(postgresql_build_input, pg, root), 'PostgreSQL build receipt mismatch')
        pg = postgresql_build_input
    resume_input = expected_resume_receipt(root, pg) if variant == 'resume' else None
    require(not set(GAME_FILES).intersection(pg['patched_sha256']),
            'Game and PostgreSQL patches overlap; explicit rebase required')
    patch = patch_bytes(root)
    with tempfile.TemporaryDirectory(prefix='coh-game-receipt-') as temporary:
        stage = Path(temporary)
        for name in GAME_FILES:
            source = root / lock['destination'] / name
            require(source.is_file() and not source.is_symlink(), 'Missing game source: ' + name)
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        if resume_input:
            apply_patch(stage, resume.patch_bytes(root))
        inputs = {name: sha256(stage / name) for name in GAME_FILES}
        apply_patch(stage, patch)
        outputs = {name: sha256(stage / name) for name in GAME_FILES}
        metadata = loopback_metadata((stage / GAME_FILES[0]).read_text())
    require(all(inputs[name] != outputs[name] for name in GAME_FILES), 'Game patch left a file unchanged')
    return {
        'schema_version': 1, 'build_role': 'game_loopback', 'variant': variant,
        'source_commit': lock['commit'], 'postgresql_build_input': pg,
        'postgresql_build_input_canonical_sha256': canonical_hash(pg),
        'resume_build_input': resume_input,
        'game_patch_sha256': hashlib.sha256(patch).hexdigest(),
        'source_sha256': inputs, 'patched_sha256': outputs,
        'loopback_only': metadata, 'socket_contract': socket_contract(root),
        'runtime_validation': 'unverified',
    }


def apply_game_overlay(source, root=ROOT, variant='creation'):
    source, root = Path(source).resolve(), Path(root).resolve()
    require(source not in (root, root / 'upstream') and root / 'upstream' not in source.parents,
            'Game overlay may not modify immutable snapshots')
    receipt_path = source / RECEIPT
    require(not receipt_path.exists() and not receipt_path.is_symlink(),
            'Game receipt already exists; use a fresh staging tree')
    pg_path = source / 'postgresql-build-input.json'
    require(pg_path.is_file() and not pg_path.is_symlink(), 'Missing PostgreSQL build receipt')
    pg = json.loads(pg_path.read_text())
    expected = expected_game_receipt(root, pg, variant)
    resume_path = source / resume.RECEIPT
    if variant == 'resume':
        require(resume_path.is_file() and not resume_path.is_symlink(), 'Missing resume build receipt')
        require(json.loads(resume_path.read_text()) == expected['resume_build_input'],
                'Resume build receipt mismatch')
    else:
        require(not resume_path.exists() and not resume_path.is_symlink(),
                'Creation source must not contain a resume overlay')
    inputs = dict(pg['patched_sha256'])
    inputs.update(pg['overlay_sha256'])
    inputs.update(expected['source_sha256'])
    for name, digest in inputs.items():
        path = source / name
        require(path.is_file() and not path.is_symlink() and sha256(path) == digest,
                'Staged source SHA-256 mismatch: ' + name)
        require(not any(parent.is_symlink() for parent in path.parents if source in parent.parents),
                'Staged source parent is linked: ' + name)
    apply_patch(source, patch_bytes(root))
    require({name: sha256(source / name) for name in GAME_FILES} == expected['patched_sha256'],
            'Applied game patch hashes differ from receipt')
    receipt_path.write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    return expected


def prepare(output, root=ROOT, variant='creation'):
    output, root = Path(output), Path(root).resolve()
    require(variant in VARIANTS, 'Invalid game source variant')
    require(not output.exists() and not output.is_symlink(), 'Output must be a new directory')
    output = output.resolve()
    require(output not in (root, root / 'upstream') and root / 'upstream' not in output.parents,
            'Output must be outside immutable snapshots')
    subprocess.run([sys.executable, str(root / 'tools/prepare_pg_source.py'), '--output', str(output)], check=True)
    if variant == 'resume':
        apply_resume_overlay(output, root)
    return apply_game_overlay(output, root, variant)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--variant', choices=VARIANTS, default='creation')
    args = parser.parse_args()
    prepare(args.output, variant=args.variant)
    print('Prepared separately identified game loopback source:', args.variant, args.output)


if __name__ == '__main__':
    main()
