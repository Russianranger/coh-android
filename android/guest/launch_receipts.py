"""Skip a launch step whose pinned inputs and installed tree are unchanged since it last passed.

Thor 0.13.66 (2026-11-10): every launch re-checked installed files that had not changed
(Atlas world 21.7 s, client visual 25.2 s, zone resources 43.0 s, zone audio 3.0 s; each
reported 0 files installed). One path lookup costs about 1 ms through PRoot, so per-file
checks of 40,000 leaves dominate a launch. A receipt is written after a step passed in
full: the step's identity (its pinned inputs and code) and one row per directory between
the worktree and its installed leaves. A directory that holds leaves records its identity,
its times and its own listing (the name, inode number and type of every entry, as the
directory stores them); a directory above it records its identity only. A later launch
reads those directories and no leaf: adding, removing, renaming or replacing an entry
changes a row, and then the step runs in full again.

Not seen by a receipt: a rewrite of an installed leaf in place (same inode). Installed
leaves are read-only, and every receipt expires after MAX_AGE_SECONDS, so each step
still runs in full at least that often.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import time

FORMAT = 1
POLICY = 'pinned_inputs_and_directory_listings_v1'
MAX_AGE_SECONDS = 30 * 24 * 3600
MAX_DIRECTORIES = 20000
MAX_ENTRIES = 2000000
MAX_RECEIPT = 16 * 1024 * 1024
STEP = re.compile(r'[a-z][a-z0-9_]{0,40}')
# Per-run counters a step reports about work it did; a reused result did none of it.
WORK_COUNTERS = ('installed_files', 'decoded_files', 'decoded_payload_bytes', 'archive_read_bytes',
                 'verified_existing_bytes')
ELAPSED = ('preparation_elapsed_seconds', 'elapsed_seconds')


class ReceiptError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ReceiptError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def directories_of(root, targets):
    """{relative directory: holds a leaf} for every directory from root down to each target."""
    root = Path(root); found = {}
    for target in targets:
        relative = Path(target).relative_to(root)
        require(relative.parts and '..' not in relative.parts, 'Receipt leaf is not inside its worktree')
        parents = [('' if parent == Path('.') else parent.as_posix()) for parent in relative.parents]
        found[parents[0]] = True
        for name in parents[1:]:
            found.setdefault(name, False)
    require(0 < len(found) <= MAX_DIRECTORIES, 'Receipt directory count exceeds its bound')
    return found


def directory_row(path, *, listing):
    """One directory's identity; with `listing`, also its times and its entries.

    The times are read before the listing, so an entry that changes while the directory
    is read leaves a row that no later launch can match.
    """
    info = os.lstat(path)
    require(stat.S_ISDIR(info.st_mode), 'Receipt directory is linked or not a directory')
    row = [info.st_dev, info.st_ino, info.st_mode, info.st_uid]
    if not listing:
        return row
    entries = []
    with os.scandir(path) as found:
        for entry in found:
            kind = ('l' if entry.is_symlink() else 'd' if entry.is_dir(follow_symlinks=False)
                    else 'f' if entry.is_file(follow_symlinks=False) else 'o')
            entries.append((entry.name, entry.inode(), kind))
            require(len(entries) <= MAX_ENTRIES, 'Receipt directory listing exceeds its bound')
    digest = hashlib.sha256()
    for name, inode, kind in sorted(entries):
        digest.update(kind.encode() + str(inode).encode() + b':' + os.fsencode(name) + b'\0')
    return row + [info.st_mtime_ns, info.st_ctime_ns, len(entries), digest.hexdigest()]


def snapshot(root, directories, context=None):
    root = Path(root); rows = {}
    for name in sorted(directories):
        if context is not None:
            context.check()
        rows[name] = directory_row(root / name if name else root, listing=bool(directories[name]))
    return rows


def path_of(store, step):
    require(isinstance(step, str) and STEP.fullmatch(step), 'Invalid launch step name')
    return Path(store) / (step + '.json')


def load(store, step):
    path = path_of(store, step)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid()
                and 0 < info.st_size <= MAX_RECEIPT, 'Launch receipt is not an owned regular file')
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            raw = source.read(MAX_RECEIPT + 1)
    finally:
        os.close(descriptor)
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError) as failure:
        raise ReceiptError('Launch receipt is not JSON') from failure
    require(isinstance(value, dict), 'Launch receipt is not an object')
    return value


def reusable(store, step, identity, root, context=None, *, now=None):
    """(the step's last full result, None) while its receipt still holds, else (None, reason)."""
    try:
        receipt = load(store, step)
        if receipt is None:
            return None, 'no_receipt'
        now = time.time() if now is None else now
        require(receipt.get('format') == FORMAT and receipt.get('policy') == POLICY and receipt.get('step') == step
                and isinstance(receipt.get('result'), dict) and isinstance(receipt.get('directories'), dict)
                and 0 < len(receipt['directories']) <= MAX_DIRECTORIES
                and type(receipt.get('verified_utc')) in (int, float), 'receipt_format')
        if receipt.get('identity') != identity:
            return None, 'inputs_changed'
        if not 0 <= now - receipt['verified_utc'] <= MAX_AGE_SECONDS:
            return None, 'receipt_expired'
        root = Path(root)
        for name in sorted(receipt['directories']):
            if context is not None:
                context.check()
            row = receipt['directories'][name]
            require(isinstance(name, str) and isinstance(row, list) and len(row) in (4, 8)
                    and (name == '' or (not name.startswith('/') and '..' not in name.split('/'))), 'receipt_format')
            try:
                current = directory_row(root / name if name else root, listing=len(row) == 8)
            except (OSError, ReceiptError):
                return None, 'directory_missing: ' + (name or '.')[:200]
            if current != row:
                return None, 'directory_changed: ' + (name or '.')[:200]
        return receipt['result'], None
    except ReceiptError as failure:
        return None, 'receipt_refused: ' + str(failure)[:200]
    except OSError as failure:
        return None, 'receipt_unreadable: ' + type(failure).__name__


def record(store, step, identity, root, targets, result, context=None, *, now=None):
    """Write the receipt of a step that just passed in full; returns its directory count."""
    store = Path(store)
    store.mkdir(mode=0o700, exist_ok=True)
    info = os.lstat(store)
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid(), 'Launch receipt store is not an owned directory')
    rows = snapshot(root, directories_of(root, targets), context)
    raw = canonical({'format': FORMAT, 'policy': POLICY, 'step': step, 'identity': identity,
                     'verified_utc': time.time() if now is None else now, 'directories': rows, 'result': result})
    require(len(raw) <= MAX_RECEIPT, 'Launch receipt exceeds its bound')
    target = path_of(store, step)
    descriptor, name = tempfile.mkstemp(prefix='.receipt-', dir=store)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(raw); output.flush(); os.fsync(output.fileno())
        os.chmod(name, 0o600)
        os.replace(name, target)
    finally:
        if os.path.lexists(name):
            os.unlink(name)
    return len(rows)


def as_reused(result, elapsed_seconds):
    """A stored full result as this launch reports it: no work done, this launch's time."""
    value = dict(result)
    for key in WORK_COUNTERS:
        if key in value:
            value[key] = 0
    if 'reused_files' in value and type(value.get('file_count')) is int:
        value['reused_files'] = value['file_count']
    if 'fingerprint_reused' in value:
        value['fingerprint_reused'] = True
    if 'source_generation_rebound' in value:
        value['source_generation_rebound'] = False
    if value.get('reuse_validation') == 'pinned_content_verification':
        value['reuse_validation'] = 'unchanged_filesystem_receipt'
    for key in ELAPSED:
        if key in value:
            value[key] = round(elapsed_seconds, 6)
    return value
