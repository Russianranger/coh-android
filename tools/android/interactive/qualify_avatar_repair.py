#!/usr/bin/env python3
"""Qualify the old shipped avatar hard-link upgrade under real pinned PRoot.

This fixture owns its new directory only. It never opens an installed game
database or existing client worktree. Run with --link2symlink and guest UID 1000.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_avatar_assets as avatar

SCOPE = 'legacy_avatar_hardlink_repair_native_proot'
DONOR_SHA256 = 'e3a0760d23ef57747343ee8fd0c76e68a92194df040062266f3dc282cd15a924'
PREFIXES = ('.l2s.', '.proot.l2s.')
SOURCE_FILES = ('android/guest/character_avatar_assets.py',
                'tools/android/interactive/qualify_avatar_repair.py',
                'tools/android/interactive/build_avatar_repair_apk.py',
                '.github/workflows/android-avatar-repair.yml')


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


class Context:
    @staticmethod
    def check():
        pass


def immutable(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(raw)
    path.chmod(0o444)
    os.utime(path, (avatar.client.CACHE_EPOCH,) * 2)


def hidden_entries(worktree):
    return sorted(path for path in worktree.rglob('*') if path.name.startswith(PREFIXES))


def payload_identity(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            raw = source.read(avatar.PAYLOAD_BYTES + 1)
        real_uid = avatar.client.base.WineProcessOwner.status(Path('/proc/self'))['uid']
        check(info.st_uid in (os.geteuid(), real_uid), 'Fixture file owner differs from this process')
        return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                'mode': stat.S_IMODE(info.st_mode), 'mtime_ns': info.st_mtime_ns,
                'real_owner_uid': real_uid, 'nlink': info.st_nlink}
    finally:
        os.close(descriptor)


def snapshot(root):
    """Fingerprint entries without following a raw broken legacy link."""
    values = {}
    for path in sorted(root.rglob('*')):
        try:
            link = os.readlink(path)
        except OSError as error:
            check(error.errno == errno.EINVAL, 'Unexpected fixture readlink error')
            link = None
        if link is not None:
            # PRoot's virtual lstat attempts to consult an old absolute final
            # path. A broken fake hard-link need not yield usable virtual stat.
            values[path.relative_to(root).as_posix()] = [['link', link]]
            continue
        info = path.lstat()
        if path.is_dir():
            content = 'directory'
        else:
            content = ['sha256', hashlib.sha256(path.read_bytes()).hexdigest()]
        values[path.relative_to(root).as_posix()] = [content, info.st_mode,
                                                    info.st_mtime_ns, info.st_uid]
    return values


def legacy_fixture(root, payloads, names, *, relocate=True):
    old = root / ('client-work-' + '1' * 24)
    new = root / ('client-work-' + '2' * 24)
    (old / 'data').mkdir(parents=True, mode=0o700)
    for name in sorted(names):
        target = old / name
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix='.avatar-pending-', dir=target.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(payloads[name])
                output.flush()
                os.fsync(output.fileno())
            temporary.chmod(0o444)
            os.utime(temporary, (avatar.client.CACHE_EPOCH,) * 2)
            # Exactly the publication used by the accepted physical 0.9 APK.
            os.link(temporary, target, follow_symlinks=False)
        finally:
            temporary.unlink(missing_ok=True)
    before = {name: payload_identity(old / name) for name in names}
    check(len(hidden_entries(old)) == len(names) * 2,
          'Fixture is not running with the actual link2symlink layout')
    if not relocate:
        return old, old, before
    os.rename(old, new)  # Exactly the wrapper-only reusable-worktree migration.
    first = new / sorted(names)[0]
    try:
        payload_identity(first)
    except OSError as error:
        check(error.errno == errno.ELOOP, 'Legacy relocation did not reproduce Errno 40')
    else:
        raise RuntimeError('Legacy relocation unexpectedly passed O_NOFOLLOW')
    return old, new, before


def broken_chain(target):
    first = Path(os.readlink(target))
    check(first.is_absolute() and first.name.startswith(PREFIXES), 'Unexpected legacy leaf link')
    intermediate = target.parent / first.name
    second = Path(os.readlink(intermediate))
    check(second.is_absolute() and second.name == first.name + '.0001',
          'Unexpected legacy intermediate link')
    return intermediate, target.parent / second.name, second


def negative_cases(root, assets, payloads, first):
    cases = ('payload', 'permissions', 'timestamp', 'backing_symlink',
             'multiple_links', 'foreign_leaf')
    results = {}
    for kind in cases:
        case = root / ('negative-' + kind)
        _, work, _ = legacy_fixture(case, payloads, (first,))
        target = work / first
        intermediate, backing, stale_final = broken_chain(target)
        if kind == 'payload':
            backing.chmod(0o600)
            raw = bytearray(backing.read_bytes())
            raw[-1] ^= 1
            immutable(backing, raw)
        elif kind == 'permissions':
            backing.chmod(0o600)
        elif kind == 'timestamp':
            os.utime(backing, (avatar.client.CACHE_EPOCH + 1,) * 2)
        elif kind == 'backing_symlink':
            external = case / 'external.geo'
            immutable(external, payloads[first])
            backing.unlink()
            backing.symlink_to(external)
        elif kind == 'multiple_links':
            two_links = backing.with_name(backing.name[:-4] + '0002')
            os.rename(backing, two_links)
            intermediate.unlink()
            intermediate.symlink_to(stale_final.with_name(two_links.name))
        else:
            external = case / 'external.geo'
            immutable(external, payloads[first])
            target.unlink()
            target.symlink_to(external)
        before = snapshot(case)
        try:
            avatar.install(work, assets, Context())
        except (avatar.client.base.DiagnosticError, OSError):
            pass
        else:
            raise RuntimeError('Invalid legacy fixture was accepted: ' + kind)
        check(snapshot(case) == before, 'Refused fixture was modified: ' + kind)
        results[kind] = {'refused': True, 'all_entries_preserved': True}
    return results


def interruptions(root, assets, payloads):
    results = {}
    for kind in ('after_leaf_replacement', 'after_intermediate_removal'):
        _, work, before = legacy_fixture(root / kind, payloads, sorted(avatar.ALLOWED))
        first = work / sorted(avatar.ALLOWED)[0]
        first_intermediate, _, _ = broken_chain(first)
        if kind == 'after_leaf_replacement':
            native = os.replace

            def cancelled_replace(source, destination):
                native(source, destination)
                raise avatar.client.base.Cancelled('Qualification interrupted after replacing leaf')

            injection = patch.object(avatar.os, 'replace', side_effect=cancelled_replace)
        else:
            native = Path.unlink

            def cancelled_unlink(path, *args, **kwargs):
                native(path, *args, **kwargs)
                if path == first_intermediate:
                    raise avatar.client.base.Cancelled('Qualification interrupted after removing intermediate')

            injection = patch.object(Path, 'unlink', cancelled_unlink)
        with injection:
            try:
                avatar.install(work, assets, Context())
            except avatar.client.base.Cancelled:
                pass
            else:
                raise RuntimeError('Cancellation fixture did not interrupt the intended mutation')
        proof = avatar.install(work, assets, Context())
        expected = len(avatar.ALLOWED) - 1 if kind == 'after_leaf_replacement' else 0
        check(proof['legacy_repaired_files'] == expected and proof['installed_files'] == 0
              and proof['reused_files'] == len(avatar.ALLOWED), 'Interrupted repair did not resume')
        check({name: payload_identity(work / name) for name in avatar.ALLOWED} == before,
              'Interrupted repair changed bytes or metadata')
        check(not hidden_entries(work) and not list(work.rglob('.avatar-pending-*')),
              'Interrupted repair left private staging entries')
        results[kind] = {'retry_passed': True, 'all_payloads_preserved': True,
                         'hidden_backing_entries_removed': True}
    return results


def healthy_chain_refusal(root, assets, payloads):
    _, work, _ = legacy_fixture(root, payloads, sorted(avatar.ALLOWED), relocate=False)
    before = snapshot(root)
    try:
        avatar.install(work, assets, Context())
    except (avatar.client.base.DiagnosticError, OSError):
        pass
    else:
        raise RuntimeError('Healthy virtual hard-links entered the stale-link repair path')
    check(snapshot(root) == before, 'Healthy legacy links were changed')
    return {'refused': True, 'all_entries_preserved': True}


def qualify(args):
    check(platform.machine() == 'aarch64' and os.geteuid() == 1000,
          'Qualification requires native ARM64 PRoot with guest UID 1000')
    check(args.donor_apk_sha256 == DONOR_SHA256, 'Qualification donor APK pin differs')
    check(re.fullmatch('[0-9a-f]{40}', args.repository_commit or '') is not None,
          'Qualification repository commit is missing or invalid')
    check(args.state.is_absolute() and '..' not in args.state.parts
          and not os.path.lexists(args.state), 'Fixture state must be a new absolute directory')
    args.state.mkdir(parents=True, mode=0o700)
    manifest, payloads = avatar.package(args.assets)
    fixture = args.state / 'relocated-all-shipped-files'
    old, work, before = legacy_fixture(fixture, payloads, sorted(avatar.ALLOWED))
    # Mirrors the durable state the repair must preserve without opening a DB.
    sentinels = {
        fixture / 'database/character-rows': b'THORHERO|id=1|powers=7|costume=14|unchanged\n',
        work / 'client-work.json': b'{"fixture_identity":"preserved"}\n',
        work / 'data/bin/generated.bin': b'preserved private generated cache',
        fixture / 'import/original.geo': b'preserved imported content',
    }
    for path, content in sentinels.items():
        immutable(path, content)
    (work / 'data/original.geo').symlink_to(fixture / 'import/original.geo')
    sentinel_before = {str(path): payload_identity(path) for path in sentinels}
    proof = avatar.install(work, args.assets, Context())
    check(proof.get('legacy_repaired_files') == len(avatar.ALLOWED), 'Repair count differs')
    check(proof['installed_files'] == 0 and proof['reused_files'] == len(avatar.ALLOWED),
          'Legacy checked payloads were unnecessarily reinstalled')
    after = {name: payload_identity(work / name) for name in avatar.ALLOWED}
    check(after == before, 'Repair changed installed avatar bytes or metadata')
    check(not hidden_entries(work), 'Repair left private staging backing entries')
    check(not list(work.rglob('.avatar-pending-*')), 'Repair left a pending temporary entry')
    repeated = avatar.install(work, args.assets, Context())
    check(repeated.get('legacy_repaired_files') == 0 and repeated['installed_files'] == 0
          and repeated['reused_files'] == len(avatar.ALLOWED), 'Second install did not reuse every leaf')
    check({name: payload_identity(work / name) for name in avatar.ALLOWED} == after,
          'Repeat changed installed avatar bytes or metadata')
    check({str(path): payload_identity(path) for path in sentinels} == sentinel_before,
          'Repair changed an identity, imported leaf, generated cache or saved-row sentinel')
    check(os.readlink(work / 'data/original.geo') == str(fixture / 'import/original.geo'),
          'Repair changed unrelated imported link')
    negatives = negative_cases(args.state, args.assets, payloads, sorted(avatar.ALLOWED)[0])
    resumed = interruptions(args.state / 'interruption-fixtures', args.assets, payloads)
    healthy = healthy_chain_refusal(args.state / 'healthy-links-fixture', args.assets, payloads)
    return {'format': 1, 'scope': SCOPE, 'status': 'passed', 'machine': platform.machine(),
            'guest_uid': os.geteuid(), 'execution_platform': 'native_proot',
            'repository_commit': args.repository_commit,
            'source_files': {name: {'bytes': (ROOT / name).stat().st_size,
                                   'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
                             for name in SOURCE_FILES},
            'donor_apk_sha256': args.donor_apk_sha256,
            'helper_sha256': hashlib.sha256(Path(avatar.__file__).read_bytes()).hexdigest(),
            'qualifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'avatar_manifest_sha256': avatar.MANIFEST_SHA256,
            'avatar_archive_sha256': avatar.ARCHIVE_SHA256,
            'fixture': {'old_read_nofollow_errno': errno.ELOOP,
                        'repaired_files': len(avatar.ALLOWED),
                        'repeated_reused_files': repeated['reused_files'],
                        'exact_bytes_metadata_preserved': True,
                        'hidden_backing_entries_removed': True,
                        'sentinels_preserved': True, 'negative_cases_passed': True,
                        'negative_cases': negatives, 'interruption_cases': resumed,
                        'healthy_links_refused_unchanged': healthy},
            'saved_game_database_opened': False, 'gameplay_validated': False,
            'physical_android_execution_validated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', required=True, type=Path)
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--donor-apk-sha256', required=True)
    parser.add_argument('--repository-commit', default=os.environ.get('GITHUB_SHA'))
    args = parser.parse_args()
    try:
        receipt = qualify(args)
    except Exception as error:
        import traceback
        receipt = {'format': 1, 'scope': SCOPE, 'status': 'failed',
                   'error': str(error), 'traceback': traceback.format_exc(), 'machine': platform.machine(),
                   'guest_uid': os.geteuid(), 'gameplay_validated': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
