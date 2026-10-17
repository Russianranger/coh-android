#!/usr/bin/env python3
"""Stage a pinned, nonshipping AuthServer receive-offset candidate outside the repo.

Only DecPacket's pointer changes from inBuf+2 to inBuf+pi. The exact original
CIOSocket::Read, length policy, encryption function and dispatch remain intact.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

from hosted_auth_stage import ORIGINAL_TREE
from source_audit import decoded, extract

HERE = Path(__file__).resolve().parent
SOCKET = 'upstream/ouroboros/AuthServer/src/SocketServerEx.cpp'
IO = 'upstream/ouroboros/AuthServer/src/IOSocket.cpp'
SOURCE_SHA256 = {
    SOCKET: '7ba1ae3f483a4b32b57d609c007f7049e16684d8aa875165b40a462ef7d1a1cb',
    IO: 'bdf40132e33e1280b9a7f3cce32eb33a8ebcede2838673959fc317c78097d319',
}
BEFORE = b'result = DecPacket(inBuf+2, DecOneTimeKey , packetLen);'
AFTER = b'result = DecPacket(inBuf+pi, DecOneTimeKey , packetLen);'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sources(root):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], timeout=30)
    if git('rev-parse', 'HEAD:upstream/ouroboros').decode().strip() != ORIGINAL_TREE:
        raise ValueError('receive_candidate_original_tree_mismatch')
    values = {path: git('show', 'HEAD:' + path) for path in (SOCKET, IO)}
    if any(digest(value) != SOURCE_SHA256[path] for path, value in values.items()):
        raise ValueError('receive_candidate_original_source_mismatch')
    return values


def replace_offset(original):
    if digest(original) != SOURCE_SHA256[SOCKET] or original.count(BEFORE) != 1:
        raise ValueError('receive_candidate_replacement_boundary_changed')
    candidate = original.replace(BEFORE, AFTER)
    old_function = extract(decoded(original), 'CSocketServerEx::OnRead')
    new_function = extract(decoded(candidate), 'CSocketServerEx::OnRead')
    if new_function.replace(AFTER.decode(), BEFORE.decode()) != old_function:
        raise ValueError('receive_candidate_function_change_not_exact')
    return candidate


def prepare(root, directory):
    root, directory = root.resolve(), directory.resolve()
    if directory == root or directory.is_relative_to(root) or directory.exists():
        raise ValueError('receive_candidate_new_external_directory_required')
    values = sources(root)
    candidate = replace_offset(values[SOCKET])
    directory.mkdir(parents=True)
    # These complete source files are independently pinned. They are not a new
    # upstream tree or a claim that the full original Windows server was built.
    for path in (SOCKET, IO):
        destination = directory / Path(path).name
        destination.write_bytes(candidate if path == SOCKET else values[path])
    patch = ''.join(difflib.unified_diff(decoded(values[SOCKET]).splitlines(True),
        decoded(candidate).splitlines(True), fromfile='a/' + SOCKET, tofile='b/' + SOCKET))
    (directory / 'receive-offset.patch').write_text(patch)
    proof = {'schema': 'coh-authserver-receive-offset-candidate-v1',
        'original_source_tree': ORIGINAL_TREE,
        'original_source_sha256': {path: digest(value) for path, value in values.items()},
        'candidate_source_sha256': digest(candidate),
        'original_onread_sha256_utf8_lf': digest(extract(decoded(values[SOCKET]), 'CSocketServerEx::OnRead').encode()),
        'candidate_onread_sha256_utf8_lf': digest(extract(decoded(candidate), 'CSocketServerEx::OnRead').encode()),
        'unchanged_read_sha256_utf8_lf': digest(extract(decoded(values[IO]), 'CIOSocket::Read').encode()),
        'patch_sha256_utf8_lf': digest(patch.encode()),
        'declared_changes': ['Pass the current body cursor pi to the original DecPacket function.'],
        'buffer_compaction_unchanged': True, 'length_validation_unchanged': True,
        'encryption_unchanged': True, 'dispatch_unchanged': True, 'account_policy_unchanged': True,
        'upstream_worktree_modified': False, 'nonshipping_only': True,
        'patched_authserver_windows_built': False, 'patched_authserver_executed': False,
        'encrypted_account_login_verified': False, 'general_tcp_segmentation_accepted': False,
        'authenticated_db_map_handoff_verified': False}
    (directory / 'candidate-manifest.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof = prepare(args.source_root, args.output)
    print(json.dumps({'staged': True, 'candidate_source_sha256': proof['candidate_source_sha256'],
                      'patched_authserver_executed': False, 'encrypted_account_login_verified': False}))
