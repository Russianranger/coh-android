"""NEW dormant POSIX owner replacement; NOT recovered revision 3 or admission.

Only creates an exclusive, disposable fixture below a caller-supplied private
parent. No Wine, Game, Android, namespace, process-start or runtime caller exists.
The typed context is a custody binding, never self-authenticating authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from contextlib import nullcontext
import json
import os
from pathlib import Path
import re
import secrets
import stat
import threading

MAX_CHILDREN = 8
MAX_DOCUMENT_BYTES = 4096
_HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_RAW_SECRET = re.compile(rb'"auth_nonce"\s*:\s*"([0-9a-fA-F]{64})"')
_FIELDS = frozenset(("format", "session_id", "operation_id", "process_instance",
                     "child_index", "auth_nonce"))


class Refusal(Exception):
    """Only fixed, nonsecret reason codes leave this module."""


@dataclass(frozen=True)
class CurrentOperation:
    session_id: str
    operation_id: str
    process_instance: str
    real_uid: int
    device: int

    def validate(self):
        for value, pattern in ((self.session_id, r"[0-9a-f]{32}"),
            (self.operation_id, r"[0-9]{13}-[0-9a-f]{12}"),
            (self.process_instance, r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")):
            if not isinstance(value, str) or re.fullmatch(pattern, value, re.ASCII) is None:
                raise Refusal("operation_refused")
        if (type(self.real_uid) is not int or self.real_uid != os.getuid()
            or self.real_uid != os.geteuid() or type(self.device) is not int
            or not 0 <= self.device < 1 << 64):
            raise Refusal("operation_refused")


class PrivateSecrets:
    """Finite, operation-private redaction set. Never exported or serialized."""
    def __init__(self):
        self._values = set()

    def remember(self, value):
        if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value, re.ASCII):
            if value not in self._values and len(self._values) >= 128:
                raise Refusal("redaction_bound")
            self._values.add(value)

    def redact(self, text):
        for value in sorted(self._values):
            text = text.replace(value, "[private]")
        return text

    def __repr__(self):
        return "PrivateSecrets(<private>)"

    def __reduce__(self):
        raise TypeError("private state is not serializable")


@dataclass(frozen=True, eq=False)
class ChildTicket:
    """Process-local opaque one-use ticket; no public path/credential fields."""
    index: int
    _nonce: str = field(repr=False)

    def __reduce__(self):
        raise TypeError("private state is not serializable")


@dataclass
class _Child:
    ticket: ChildTicket
    name: str
    fd: int
    identity: tuple
    consumed: bool = False
    deleted: bool = False


def _directory_identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode)


def _file_identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _regular(info, operation):
    return (stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600
            and info.st_uid == operation.real_uid and info.st_dev == operation.device
            and info.st_nlink == 1 and 0 < info.st_size <= MAX_DOCUMENT_BYTES)


def _fresh_descriptor_info(fd):
    """A just-opened descriptor is not published until its first fstat works."""
    try:
        return os.fstat(fd)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _canonical_path(value):
    if not isinstance(value, (str, Path)):
        raise Refusal("parent_path_refused")
    text = str(value)
    path = Path(text)
    if (not path.is_absolute() or str(path) != text or ".." in path.parts
        or "." in path.parts or "\x00" in text or text == "/"):
        raise Refusal("parent_path_refused")
    return path


class FixtureOwner:
    """Exclusive new host fixture, with held ancestry and per-file custody.

    Reopening/restoring an earlier owner and supplying existing fixture roots
    are deliberately unsupported. A one-use child is document custody only;
    consuming it does not start or qualify any native child.
    """
    def __init__(self):
        raise Refusal("use_create_only")

    @classmethod
    def create(cls, parent, operation, registry):
        if type(operation) is not CurrentOperation or type(registry) is not PrivateSecrets:
            raise Refusal("typed_context_required")
        operation.validate()
        path = _canonical_path(parent)
        if any(not hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_CLOEXEC", "O_DIRECTORY")):
            raise Refusal("platform_refused")
        self = object.__new__(cls)
        self._operation, self._registry = operation, registry
        self._pid, self._lock = os.getpid(), threading.Lock()
        self._fds, self._fd_identities, self._anchors, self._children = [], {}, [], {}
        self._closed = self._poisoned = False
        self._cleanup_report = None
        self._root_fd = self._parent_fd = None
        self._root_name = self._root_identity = None
        self._root_created = False
        try:
            current = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            info = _fresh_descriptor_info(current)
            self._fds.append(current)
            self._fd_identities[current] = _directory_identity(info)[:2]
            for name in path.parts[1:]:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
                                dir_fd=current)
                info = _fresh_descriptor_info(child)
                self._fds.append(child)
                self._fd_identities[child] = _directory_identity(info)[:2]
                self._anchors.append((current, name, child, _directory_identity(info)))
                current = child
            info = os.fstat(current)
            if (stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != operation.real_uid
                or info.st_dev != operation.device):
                raise Refusal("private_parent_required")
            self._parent_fd = current
            self._root_name = "live-fixture-" + secrets.token_hex(12)
            os.mkdir(self._root_name, mode=0o700, dir_fd=current)
            self._root_created = True
            root_fd = os.open(self._root_name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=current)
            info = _fresh_descriptor_info(root_fd)
            self._root_fd = root_fd
            self._fds.append(self._root_fd)
            self._root_identity = _directory_identity(info)
            self._fd_identities[self._root_fd] = self._root_identity[:2]
            self._check_live()
            return self
        except BaseException as error:
            cleanup = self.close()
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            if not cleanup["cleanup_complete"]:
                raise Refusal("fixture_creation_cleanup_incomplete") from None
            if isinstance(error, Refusal):
                raise
            raise Refusal("fixture_creation_refused") from None

    def _check_process(self):
        if self._closed:
            raise Refusal("owner_closed")
        if self._poisoned:
            raise Refusal("owner_poisoned")
        if os.getpid() != self._pid:
            raise Refusal("process_changed")
        self._operation.validate()

    def _check_ancestry(self):
        for parent, name, child, identity in self._anchors:
            held = os.fstat(child)
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (not stat.S_ISDIR(named.st_mode) or _directory_identity(held) != identity
                or _directory_identity(named) != identity):
                raise Refusal("ancestor_changed")

    def _check_live(self):
        self._check_process()
        self._check_ancestry()
        held = os.fstat(self._root_fd)
        named = os.stat(self._root_name, dir_fd=self._parent_fd, follow_symlinks=False)
        if (not stat.S_ISDIR(held.st_mode) or _directory_identity(held) != self._root_identity
            or _directory_identity(named) != self._root_identity
            or held.st_uid != self._operation.real_uid or held.st_dev != self._operation.device
            or stat.S_IMODE(held.st_mode) != 0o700 or held.st_nlink != 2):
            raise Refusal("fixture_root_changed")
        expected = {child.name for child in self._children.values() if not child.deleted}
        actual = set()
        with os.scandir(self._root_fd) as entries:
            for entry in entries:
                actual.add(entry.name)
                if len(actual) > MAX_CHILDREN:
                    raise Refusal("fixture_membership_bound")
        if actual != expected:
            raise Refusal("fixture_membership_changed")
        for child in self._children.values():
            if not child.deleted:
                self._check_child(child)

    def _check_child(self, child):
        held = os.fstat(child.fd)
        named = os.stat(child.name, dir_fd=self._root_fd, follow_symlinks=False)
        if (not _regular(held, self._operation) or not _regular(named, self._operation)
            or _file_identity(held) != child.identity or _file_identity(named) != child.identity):
            raise Refusal("child_custody_changed")

    def issue_child(self):
        # Do not acquire a possibly inherited locked mutex in a forked copy.
        if os.getpid() != self._pid:
            raise Refusal("process_changed")
        with self._lock:
            # The issuance cap counts every issued ticket, INCLUDING consumed
            # tickets. This check precedes RNG, redaction, IO and state effects.
            if len(self._children) >= MAX_CHILDREN:
                raise Refusal("child_limit")
            try:
                self._check_live()
                index = len(self._children) + 1
                nonce = secrets.token_hex(32)
                if not _HEX64.fullmatch(nonce) or any(c.ticket._nonce == nonce for c in self._children.values()):
                    raise Refusal("fresh_nonce_required")
                self._registry.remember(nonce)
                ticket = ChildTicket(index, nonce)
                raw = json.dumps({"format": 1, "session_id": self._operation.session_id,
                    "operation_id": self._operation.operation_id,
                    "process_instance": self._operation.process_instance,
                    "child_index": index, "auth_nonce": nonce},
                    sort_keys=True, separators=(",", ":")).encode("ascii")
                if not 0 < len(raw) <= MAX_DOCUMENT_BYTES:
                    raise Refusal("document_bound")
                name = "child-%d.json" % index
                fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=self._root_fd)
                info = _fresh_descriptor_info(fd)
                # Register the fd immediately so any interrupted write remains
                # owned and is closed by cleanup. No existing file is replaced.
                child = _Child(ticket, name, fd, _file_identity(info))
                self._children[index] = child
                offset = 0
                while offset < len(raw):
                    count = os.write(fd, raw[offset:])
                    if count <= 0:
                        raise Refusal("short_private_write")
                    offset += count
                os.fsync(fd)
                child.identity = _file_identity(os.fstat(fd))
                self._check_live()
                return ticket
            except BaseException as error:
                self._poisoned = True
                if isinstance(error, (Refusal, KeyboardInterrupt, SystemExit)):
                    raise
                raise Refusal("private_issue_refused") from None

    def _read_document(self, child):
        self._check_child(child)
        raw = os.pread(child.fd, MAX_DOCUMENT_BYTES + 1, 0)
        self._check_child(child)
        if len(raw) != child.identity[5] or len(raw) > MAX_DOCUMENT_BYTES:
            raise Refusal("document_bound")
        # Register malformed/duplicate-key AUTH values before parsing; never
        # put raw bytes, exception text, paths or credentials in a diagnostic.
        for match in _RAW_SECRET.finditer(raw):
            self._registry.remember(match.group(1).decode("ascii"))
        if any(byte >= 128 for byte in raw):
            raise Refusal("non_ascii_document")
        def pairs(values):
            result = {}
            for key, value in values:
                if key == "auth_nonce":
                    self._registry.remember(value)
                if key in result:
                    raise Refusal("duplicate_json_key")
                result[key] = value
            return result
        try:
            value = json.loads(raw.decode("ascii"), object_pairs_hook=pairs,
                parse_constant=lambda _: (_ for _ in ()).throw(Refusal("invalid_constant")))
        except Refusal:
            raise
        except (ValueError, RecursionError):
            raise Refusal("invalid_document") from None
        if type(value) is not dict or set(value) != _FIELDS:
            raise Refusal("document_fields_refused")
        expected = {"format": 1, "session_id": self._operation.session_id,
            "operation_id": self._operation.operation_id,
            "process_instance": self._operation.process_instance,
            "child_index": child.ticket.index, "auth_nonce": child.ticket._nonce}
        if any(type(value[key]) is not type(expected[key]) or value[key] != expected[key] for key in _FIELDS):
            raise Refusal("current_document_mismatch")

    def consume_child(self, ticket):
        if os.getpid() != self._pid:
            raise Refusal("process_changed")
        with self._lock:
            try:
                self._check_live()
                child = self._children.get(ticket.index) if type(ticket) is ChildTicket else None
                if child is None or child.ticket is not ticket:
                    raise Refusal("foreign_ticket")
                if child.consumed:
                    raise Refusal("child_already_used")
                # Burn before IO so a failed attempt cannot replay authority.
                child.consumed = True
                self._read_document(child)
                self._check_live()
                os.unlink(child.name, dir_fd=self._root_fd)
                child.deleted = True
                os.close(child.fd)
                child.fd = -1
                self._check_live()
                return {"role": "new_host_only_child_document_custody", "child_index": ticket.index,
                        "decision": "consumed_once", "runtime_admission": False}
            except BaseException as error:
                self._poisoned = True
                if isinstance(error, (Refusal, KeyboardInterrupt, SystemExit)):
                    raise
                raise Refusal("private_consume_refused") from None

    def close(self):
        # Foreign copies close only inherited fds; no wait on a lock inherited
        # from a vanished thread, and no mutation of the parent's fixture.
        with (self._lock if os.getpid() == self._pid else nullcontext()):
            if self._closed:
                return self._copy_cleanup_report()
            failed = []
            same_process = os.getpid() == self._pid
            # A forked copy closes only its inherited descriptors. It must not
            # unlink the live parent's documents or directory.
            if not same_process:
                failed.append("foreign_process_cleanup_refused")
            if self._root_created and self._root_fd is None:
                # mkdir succeeded but no root fd was admitted. Do not claim
                # full cleanup or delete an unheld named directory by guess.
                failed.append("unanchored_created_root_cleanup_refused")
            if same_process and self._root_fd is not None:
                for child in self._children.values():
                    if child.deleted:
                        continue
                    try:
                        held = os.fstat(child.fd)
                        named = os.stat(child.name, dir_fd=self._root_fd, follow_symlinks=False)
                        if (not stat.S_ISREG(held.st_mode) or held.st_uid != self._operation.real_uid
                            or held.st_dev != self._operation.device or held.st_nlink != 1
                            or (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino)
                            or (child.identity and (held.st_dev, held.st_ino) != child.identity[:2])):
                            raise Refusal("child_cleanup_custody_refused")
                        os.unlink(child.name, dir_fd=self._root_fd)
                        child.deleted = True
                    except (OSError, Refusal):
                        failed.append("child_cleanup_custody_refused")
                try:
                    self._check_ancestry()
                    held = os.fstat(self._root_fd)
                    named = os.stat(self._root_name, dir_fd=self._parent_fd, follow_symlinks=False)
                    with os.scandir(self._root_fd) as entries:
                        nonempty = next(entries, None) is not None
                    if (self._root_identity is None or _directory_identity(held) != self._root_identity
                        or _directory_identity(named) != self._root_identity
                        or held.st_nlink != 2 or nonempty):
                        raise Refusal("root_cleanup_custody_refused")
                    os.rmdir(self._root_name, dir_fd=self._parent_fd)
                except (OSError, Refusal):
                    failed.append("root_cleanup_custody_refused")
            for child in self._children.values():
                if child.fd >= 0:
                    try:
                        current = os.fstat(child.fd)
                        if (current.st_dev, current.st_ino) != child.identity[:2]:
                            raise Refusal("descriptor_reused")
                        os.close(child.fd)
                    except (OSError, Refusal):
                        failed.append("descriptor_close_custody_refused")
                    child.fd = -1
            for fd in reversed(self._fds):
                try:
                    current = os.fstat(fd)
                    if (current.st_dev, current.st_ino) != self._fd_identities.get(fd):
                        raise Refusal("descriptor_reused")
                    os.close(fd)
                except (OSError, Refusal):
                    failed.append("descriptor_close_custody_refused")
            self._fds.clear()
            self._closed = True
            self._cleanup_report = {"role": "new_host_only_fixture_cleanup", "cleanup_complete": not failed,
                "reasons": sorted(set(failed)), "runtime_admission": False}
            return self._copy_cleanup_report()

    def _copy_cleanup_report(self):
        copied = dict(self._cleanup_report)
        copied["reasons"] = list(copied["reasons"])
        return copied

    def __reduce__(self):
        raise TypeError("private state is not serializable")
