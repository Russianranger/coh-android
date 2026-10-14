"""Dormant, Game-only current-operation LIVE handoff validation.

Nothing in a control document grants fixture/producer permission. The caller
must construct ExpectedContext from independently reviewed, compiled current
fixture/producer authority and actual current Game/runtime/work identities.
The default is absent authority and stock behavior. Controlled host tests of
this module do not execute Android, Wine, PRoot, FEX, JNI or Game.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
import threading

PREFIX = 'COH_CLIENT_LIVE_DIRECTORY'
_ASCII_UPPER = str.maketrans('abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
FILENAME = 'client-live-directory-control.json'
MAX_BYTES = 16 * 1024
RECIPE = 'wine-b073-constructor-v1'
PROOF_SCOPE = 'reviewed-current-packaged-Android-Wine-FEX-PRoot-live-directory-v1'
FIELDS = frozenset(('format', 'session_id', 'operation_id', 'process_instance',
    'game_sha256', 'game_bytes', 'runtime_sha256', 'helper_sha256',
    'descriptor_sha256', 'guest_root', 'recipe', 'device', 'endpoint', 'auth_nonce'))
_HEX64 = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)
_HEX32 = re.compile(r'[0-9a-f]{32}\Z', re.ASCII)
_OPERATION = re.compile(r'[0-9]{13}-[0-9a-f]{12}\Z', re.ASCII)
_INSTANCE = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z', re.ASCII)
_ROOT = re.compile(r'/state/diagnostic/client-work-[0-9a-f]{24}/data\Z', re.ASCII)
_RAW_NONCE = re.compile(rb'"auth_nonce"\s*:\s*"([0-9a-fA-F]{64})"')
_claimed = set()
_claim_lock = threading.Lock()
_MAX_CLAIMS = 64


@dataclass(frozen=True)
class VerifiedFixtureProducer:
    """Trusted caller's reviewed proof identity; never parsed from config JSON.

    This type is a handoff boundary, not a self-verifying proof constructor.
    Production must keep it absent until the exact current packaged fixture
    and producer have passed their independent admission. Tests may supply a
    controlled stand-in, which grants no runtime or shipping qualification.
    """
    proof_sha256: str
    producer_commit: str
    scope: str
    game_sha256: str
    game_bytes: int
    runtime_sha256: str
    helper_sha256: str
    descriptor_sha256: str


@dataclass(frozen=True)
class ExpectedContext:
    session_id: str
    operation_id: str
    process_instance: str
    game_sha256: str
    game_bytes: int
    runtime_sha256: str
    helper_sha256: str
    descriptor_sha256: str
    guest_root: str
    device: str
    endpoint: str
    auth_nonce: str
    owner_uid: int
    fixture_producer: VerifiedFixtureProducer | None = None


class _Refusal(Exception):
    pass


def _environment_key(key):
    # Windows native environment lookup is ASCII case-insensitive. Only fold
    # ASCII so Unicode lookalikes cannot become a genuine control key.
    if isinstance(key, str):
        return key.translate(_ASCII_UPPER)
    if isinstance(key, bytes):
        return key.upper()
    return None


def strip_live_environment(environment):
    """Copy shared settings with every ASCII-case alias of LIVE removed."""
    result = {}
    for key, value in environment.items():
        canonical = _environment_key(key)
        if ((isinstance(canonical, str) and canonical.startswith(PREFIX))
            or (isinstance(canonical, bytes) and canonical.startswith(PREFIX.encode('ascii')))):
            continue
        result[key] = value
    return result


def _secret(ctx, value):
    if isinstance(value, bytes):
        try:
            value = value.decode('ascii')
        except UnicodeError:
            return
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', value, re.ASCII):
        return
    secrets = getattr(ctx, 'secrets', None)
    if not isinstance(secrets, list):
        raise _Refusal('redaction_unavailable')
    if value not in secrets:
        secrets.append(value)


def _matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _u64(value):
    return (isinstance(value, str) and re.fullmatch(r'0|[1-9][0-9]{0,19}', value, re.ASCII)
        is not None and int(value) <= (1 << 64) - 1)


def _endpoint(value):
    if not isinstance(value, str):
        return False
    match = re.fullmatch(r'127\.0\.0\.1:([1-9][0-9]{0,4})', value, re.ASCII)
    return match is not None and int(match.group(1)) <= 65535


def _expected_valid(expected):
    if type(expected) is not ExpectedContext:
        return False
    if (not _matches(_HEX32, expected.session_id)
        or not _matches(_OPERATION, expected.operation_id)
        or not _matches(_INSTANCE, expected.process_instance)
        or not _matches(_ROOT, expected.guest_root)
        or not _u64(expected.device) or not _endpoint(expected.endpoint)
        or type(expected.owner_uid) is not int or not 0 <= expected.owner_uid < (1 << 32)
        or type(expected.game_bytes) is not int or not 0 < expected.game_bytes <= 64 * 1024 * 1024):
        return False
    if not all(_matches(_HEX64, getattr(expected, key)) for key in
        ('game_sha256', 'runtime_sha256', 'helper_sha256', 'descriptor_sha256', 'auth_nonce')):
        return False
    proof = expected.fixture_producer
    if (type(proof) is not VerifiedFixtureProducer or proof.scope != PROOF_SCOPE
        or type(proof.game_bytes) is not int
        or not _matches(_HEX64, proof.proof_sha256)
        or not isinstance(proof.producer_commit, str)
        or re.fullmatch(r'[0-9a-f]{40}', proof.producer_commit, re.ASCII) is None):
        return False
    return all(getattr(proof, key) == getattr(expected, key) for key in
        ('game_sha256', 'game_bytes', 'runtime_sha256', 'helper_sha256', 'descriptor_sha256'))


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_nlink,
        info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _file_valid(info, expected):
    return (stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600
        and info.st_nlink == 1 and info.st_uid == expected.owner_uid
        and info.st_dev == int(expected.device) and 0 < info.st_size <= MAX_BYTES)


def _read_private_bytes(expected_path, expected):
    """Hold every path component; check fd/path identities around the read."""
    path = Path(expected_path)
    if (not path.is_absolute() or path.parts[0] != '/' or path.name != FILENAME or '..' in path.parts
        or '.' in path.parts or str(path) != str(expected_path) or '.l2s' in str(path)):
        raise _Refusal('path_refused')
    if not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_CLOEXEC'):
        raise _Refusal('platform_refused')
    with ExitStack() as stack:
        root = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        stack.callback(os.close, root)
        current = root
        anchors = []
        for name in path.parent.parts[1:]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=current)
            stack.callback(os.close, child)
            info = os.fstat(child)
            if not stat.S_ISDIR(info.st_mode):
                raise _Refusal('path_refused')
            anchors.append((current, name, child, info.st_dev, info.st_ino))
            current = child
        parent = os.fstat(current)
        if (parent.st_uid != expected.owner_uid or parent.st_dev != int(expected.device)
            or stat.S_IMODE(parent.st_mode) & 0o022):
            raise _Refusal('directory_refused')
        before = os.stat(path.name, dir_fd=current, follow_symlinks=False)
        if not _file_valid(before, expected):
            raise _Refusal('file_refused')
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
            dir_fd=current)
        stack.callback(os.close, fd)
        held = os.fstat(fd)
        if not _file_valid(held, expected) or _identity(held) != _identity(before):
            raise _Refusal('file_changed')
        chunks = []
        remaining = MAX_BYTES + 1
        while remaining:
            piece = os.read(fd, remaining)
            if not piece:
                break
            chunks.append(piece)
            remaining -= len(piece)
        raw = b''.join(chunks)
        after = os.fstat(fd)
        final = os.stat(path.name, dir_fd=current, follow_symlinks=False)
        if (_identity(held) != _identity(after) or _identity(held) != _identity(final)
            or len(raw) != held.st_size or len(raw) > MAX_BYTES):
            raise _Refusal('file_changed')
        for parent_fd, name, child_fd, device, inode in anchors:
            held_dir = os.fstat(child_fd)
            named_dir = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (not stat.S_ISDIR(named_dir.st_mode) or held_dir.st_dev != device
                or held_dir.st_ino != inode or named_dir.st_dev != device or named_dir.st_ino != inode):
                raise _Refusal('directory_changed')
        return raw


def _document(raw, ctx):
    # Even malformed/duplicate JSON cannot cause a nonce to enter diagnostics.
    for match in _RAW_NONCE.finditer(raw):
        _secret(ctx, match.group(1).decode('ascii'))
    if any(byte >= 128 for byte in raw):
        raise _Refusal('non_ascii_document')
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key == 'auth_nonce':
                _secret(ctx, value)
            if key in result:
                raise _Refusal('duplicate_json_key')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('ascii'), object_pairs_hook=object_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(_Refusal('invalid_json_constant')))
    except _Refusal:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise _Refusal('invalid_json') from None
    if type(value) is not dict or set(value) != FIELDS:
        raise _Refusal('document_fields_refused')
    if (type(value['format']) is not int or value['format'] != 1
        or type(value['game_bytes']) is not int
        or any(not isinstance(value[key], str) or not value[key].isascii()
            for key in FIELDS - {'format', 'game_bytes'})):
        raise _Refusal('document_types_refused')
    return value


def game_environment(environment, ctx, *, expected=None, expected_path=None,
    native_role=None, game_attempt=None):
    """Return a fresh Game-only env and a bounded nonsecret decision record.

    Call strip_live_environment for every shared Wine/Db/Map environment too.
    expected_path is deliberately absent by default. Production uses exactly
    /tmp/client-live-directory-control.json under the current operation bind;
    explicit host fixture paths are controlled tests, not Android qualification.
    """
    env = strip_live_environment(environment)
    report = {'role': 'dormant_current_Game_live_control_validation', 'decision': 'stock',
        'reason': 'authority_absent', 'native_provider_executed': False,
        'runtime_fixture_qualified_by_this_module': False}
    try:
        if type(expected) is ExpectedContext:
            _secret(ctx, expected.auth_nonce)
        for key, value in environment.items():
            if _environment_key(key) in (PREFIX + '_AUTH', (PREFIX + '_AUTH').encode('ascii')):
                _secret(ctx, value)
        if native_role != 'Game':
            raise _Refusal('not_Game')
        if type(game_attempt) is not int or game_attempt != 1:
            raise _Refusal('not_first_Game_attempt')
        if not _expected_valid(expected):
            raise _Refusal('authority_absent')
        key = (os.getpid(), expected.session_id, expected.operation_id, expected.process_instance)
        with _claim_lock:
            if key in _claimed:
                raise _Refusal('already_attempted')
            if len(_claimed) >= _MAX_CLAIMS:
                raise _Refusal('attempt_bound')
            _claimed.add(key)
        if expected_path is None:
            raise _Refusal('control_path_absent')
        raw = _read_private_bytes(expected_path, expected)
        value = _document(raw, ctx)
        if value['recipe'] != RECIPE or any(value[key] != getattr(expected, key)
            for key in FIELDS - {'format', 'recipe'}):
            raise _Refusal('current_identity_mismatch')
        env.update({PREFIX: '1', PREFIX+'_ENDPOINT': expected.endpoint,
            PREFIX+'_SESSION': expected.session_id, PREFIX+'_AUTH': expected.auth_nonce,
            PREFIX+'_DEVICE': expected.device, PREFIX+'_GUEST_ROOT': expected.guest_root,
            PREFIX+'_RECIPE': RECIPE, PREFIX+'_DESCRIPTOR': expected.descriptor_sha256})
        report.update(decision='current_Game_handoff', reason='current_private_control_matched',
            operation_id=expected.operation_id, session_id=expected.session_id,
            fixture_producer_proof_sha256=expected.fixture_producer.proof_sha256)
    except _Refusal as refusal:
        report['reason'] = refusal.args[0]
    except (OSError, ValueError, TypeError, OverflowError):
        # Do not include exception text, paths or config values in reports.
        report['reason'] = 'private_control_unavailable'
    return env, report
