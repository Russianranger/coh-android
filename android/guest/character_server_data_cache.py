"""Reuse an owned Atlas data tree only after proved server-process cleanup."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time

import diagnostic as base

require = base.require
POLICY = 'closed_owned_atlas_data_directory_v1'
MARKER_LIMIT = 8 * 1024**2
DIRECTORY_LIMIT = 20000
PRIVATE_ENTRY_LIMIT = 16384
PRIVATE_BYTES_LIMIT = 2 * 1024**3
CHANGED_DIRECTORY_LIMIT = 64
CHANGED_ENTRY_LIMIT = 20000
PRIVATE_ROOTS = ('bin', 'geobin', 'server')
CONFIG = 'server/db/servers.cfg'
STATS = {'files', 'bytes', 'directories', 'linked_immutable_files',
         'copied_private_files', 'preserved_schema_files'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def relative_name(value):
    path = Path(value) if isinstance(value, str) else None
    return (path is not None and not path.is_absolute() and '\\' not in value
            and path.as_posix() == value and '..' not in path.parts
            and all(part not in ('', '.') for part in path.parts))


def fingerprint(path, *, directory=False):
    info = Path(path).lstat()
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            and (directory or info.st_nlink == 1), 'Linked or invalid Atlas cache path')
    value = {'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid}
    if not directory:
        value.update(bytes=info.st_size, mtime_ns=info.st_mtime_ns, mode=stat.S_IMODE(info.st_mode))
    return value


def real_path(root, name, *, directory=False):
    require(name == '' or relative_name(name), 'Unsafe Atlas cache relative path')
    current = Path(root)
    fingerprint(current, directory=True)
    for part in Path(name).parts:
        current /= part
        if current == Path(root) / name and not directory:
            break
        fingerprint(current, directory=True)
    if directory:
        fingerprint(current, directory=True)
    return current


class CheckedInputResolver:
    """Resolve shared real parents once during a bounded, owned input mirror.

    Each leaf still gets a fresh type/containment check. Directory aliases and
    chained file links retain strict pathlib resolution. A final metadata pass
    refuses any parent replaced or edited while the mirror was in progress.
    This cache lasts for this invocation only; it is never an integrity donor.
    """
    def __init__(self, roots, context):
        self.roots, self.ctx = tuple(roots), context
        self.parents, self.observed = {}, {}
        self.leaves = self.strict_links = 0

    @staticmethod
    def directory_identity(info):
        return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_mtime_ns)

    def directory(self, path):
        path = Path(path)
        if path in self.parents:
            return self.parents[path]
        self.ctx.check()
        current = path if path.parent == path else self.directory(path.parent) / path.name
        info = current.lstat()
        if any(root == current or root in current.parents for root in self.roots):
            identity = self.directory_identity(info)
            require(current not in self.observed or self.observed[current] == identity,
                    'Atlas input parent changed during staging: ' + str(current))
            self.observed.setdefault(current, identity)
        if stat.S_ISLNK(info.st_mode):
            resolved = current.resolve(strict=True)
            require(resolved != current, 'Recursive Atlas input directory')
            result = self.directory(resolved)
        else:
            require(stat.S_ISDIR(info.st_mode), 'Non-directory Atlas input parent')
            result = current
        self.parents[path] = result
        return result

    def leaf(self, path):
        path = Path(path)
        current = self.directory(path.parent) / path.name
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            target = Path(os.readlink(current))
            if not target.is_absolute():
                target = current.parent / target
            # Keep pathlib's handling of dot components and arbitrary chains.
            if '..' in target.parts:
                resolved = current.resolve(strict=True)
                self.strict_links += 1
            else:
                resolved = self.directory(target.parent) / target.name
                if resolved.is_symlink():
                    resolved = current.resolve(strict=True)
                    self.strict_links += 1
            self.directory(resolved.parent)
            info = resolved.lstat()
        else:
            resolved = current
        require(any(root == resolved or root in resolved.parents for root in self.roots)
                and stat.S_ISREG(info.st_mode), 'Private map copy escaped verified data roots')
        self.leaves += 1
        return resolved, info

    def verify(self):
        for path, identity in self.observed.items():
            self.ctx.check()
            require(self.directory_identity(path.lstat()) == identity,
                    'Atlas input parent changed during staging: ' + str(path))
        return {'policy': 'per_invocation_checked_real_input_parents_v1',
                'resolved_leaves': self.leaves, 'strict_link_fallbacks': self.strict_links,
                'parent_directory_checks': len(self.observed),
                'parent_metadata_rechecks': len(self.observed)}


class ServerDataCache:
    """Directory rename preserves private cache bytes; session logs remain fresh."""
    def __init__(self, root, identity, session, context, *, legacy_identity_validator=None):
        require(isinstance(identity, dict) and identity and isinstance(session, str)
                and re.fullmatch(r'[0-9a-f]{32}', session), 'Invalid Atlas cache identity')
        self.root, self.identity, self.session, self.ctx = Path(root), identity, session, context
        self.legacy_identity_validator = legacy_identity_validator
        fingerprint(self.root, directory=True)
        require(isinstance(identity.get('source_roots'), list) and len(identity['source_roots']) == 2,
                'Atlas cache lacks both verified source roots')
        for row in identity['source_roots']:
            require(isinstance(row, dict) and set(row) == {'path', 'identity'}
                    and isinstance(row['path'], str) and Path(row['path']).is_absolute()
                    and fingerprint(Path(row['path']), directory=True) == row['identity'],
                    'Atlas cache verified source root changed')
        self.generation_limit_reached = False
        count = 0
        for path in self.root.iterdir():
            if re.fullmatch('character-server-data-[0-9a-f]{24}(?:-[0-9a-f]{32})?', path.name):
                count += 1
                if count >= 16:
                    self.generation_limit_reached = True
                    break
        self.disabled = False
        self.key = hashlib.sha256(canonical(identity)).hexdigest()[:24]
        self.path = self.root / ('character-server-data-' + self.key)
        self.pointer = self.root / ('character-server-data-' + self.key + '.json')
        self.pointer_invalid = False
        if self.pointer.exists() or self.pointer.is_symlink():
            try:
                info = self.pointer.lstat()
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 1024,
                        'Invalid Atlas cache pointer')
                selected = json.loads(self.pointer.read_text())
                require(isinstance(selected, dict) and set(selected) == {'format', 'key', 'generation'}
                        and type(selected['format']) is int and selected['format'] == 1
                        and selected['key'] == self.key and isinstance(selected['generation'], str)
                        and re.fullmatch('character-server-data-[0-9a-f]{24}(?:-[0-9a-f]{32})?',
                                         selected['generation']), 'Atlas cache pointer identity differs')
                self.path = self.root / selected['generation']
            except (base.DiagnosticError, OSError, ValueError, TypeError, KeyError):
                self.pointer_invalid = True
                self.path = self.root / ('character-server-data-' + self.key + '-' + session)
        self.marker = self.path / 'cache.json'
        self.directory_names, self.private_names, self.anchor_names = [], [], {}
        self.record = None
        self.summary = {'format': 1, 'policy': POLICY, 'key': self.key, 'reused': False,
            'legacy_session_tree_adopted': False, 'first_use_requires_full_staging': True}
        if self.pointer_invalid:
            self.summary['reuse_refused'] = 'invalid_cache_pointer'

    def observe(self, relative, destination, resolved, private):
        """Collect paths during the original bounded mirror; no second input walk."""
        name = relative.as_posix() if relative.parts else ''
        if resolved is None:
            if not private:
                self.directory_names.append(name)
        elif private:
            if name != CONFIG:
                self.private_names.append(name)
        elif len(self.anchor_names) < 64 and resolved.stat().st_size <= 1024**2:
            # One bounded read-only leaf per top-level input directory.
            self.anchor_names.setdefault(relative.parts[0], name)

    def write(self, record):
        payload = json.dumps(record, sort_keys=True) + '\n'
        require(len(payload.encode()) <= MARKER_LIMIT, 'Atlas cache marker exceeded bound')
        if not self.path.exists():
            self.path.mkdir(mode=0o700)
        require(fingerprint(self.path, directory=True)['uid'] == self.root.stat().st_uid,
                'Atlas cache directory owner changed')
        if self.marker.exists() or self.marker.is_symlink():
            fingerprint(self.marker)
        base.private_write(self.marker, payload)

    def read(self):
        require(fingerprint(self.path, directory=True)['uid'] == self.root.stat().st_uid,
                'Atlas cache directory owner changed')
        info = self.marker.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and 0 < info.st_size <= MARKER_LIMIT, 'Invalid Atlas cache marker')
        value = json.loads(self.marker.read_text())
        require(isinstance(value, dict) and set(value) == {'format', 'policy', 'identity', 'key',
            'status', 'owner', 'data_identity', 'directories', 'private_files', 'anchors', 'stats'}
            and type(value['format']) is int and value['format'] == 1
            and value['policy'] == POLICY and value['identity'] == self.identity
            and value['key'] == self.key and value['status'] == 'closed' and value['owner'] is None,
            'Atlas cache identity differs or prior owner did not prove cleanup')
        require(isinstance(value['stats'], dict) and set(value['stats']) == STATS
            and all(type(n) is int and n >= 0 for n in value['stats'].values())
            and isinstance(value['directories'], list) and 0 < len(value['directories']) <= DIRECTORY_LIMIT
            and isinstance(value['private_files'], list) and len(value['private_files']) <= PRIVATE_ENTRY_LIMIT
            and isinstance(value['anchors'], list) and 0 < len(value['anchors']) <= 64,
            'Atlas cache inventory differs')
        return value

    def verify_changed_directories(self, data, record, changed, directory_names):
        """Prove changed parent metadata without accepting changed input links.

        Private DB-ID map replacement or a native directory timestamp update
        can change the parent of otherwise unchanged immutable inputs. The
        already qualified source tree supplies its exact direct-child layout;
        every child must remain a recorded real directory, a receipt-listed
        private regular file, or the original read-only source link. This is
        bounded to changed parents, never a second whole-data-tree mirror.
        """
        require(len(changed) <= CHANGED_DIRECTORY_LIMIT,
                'Changed Atlas directory validation bound exceeded')
        source = Path(self.identity['source_data'])
        source_identity = fingerprint(source, directory=True)
        require(source_identity['device'] == self.identity['source_device']
                and source_identity['inode'] == self.identity['source_inode'],
                'Atlas cache source data changed')
        roots = [Path(value['path']) for value in self.identity['source_roots']]
        require(any(root == source or root in source.parents for root in roots),
                'Atlas cache source data escaped verified roots')
        private_names = set(record['private_files'])
        owner_uid = self.root.stat().st_uid
        examined = 0
        for row, observed_mtime in changed:
            self.ctx.check()
            name = row['path']
            self.summary['changed_directory_under_validation'] = name or '.'
            original = real_path(source, name, directory=True)
            target = Path(data) / name
            expected = set()
            with os.scandir(original) as entries:
                for entry in entries:
                    self.ctx.check()
                    examined += 1
                    require(examined <= CHANGED_ENTRY_LIMIT,
                            'Changed Atlas directory entry bound exceeded')
                    expected.add(entry.name)
            actual = set()
            with os.scandir(target) as entries:
                for entry in entries:
                    self.ctx.check()
                    examined += 1
                    require(examined <= CHANGED_ENTRY_LIMIT,
                            'Changed Atlas directory entry bound exceeded')
                    actual.add(entry.name)
                    relative = (Path(name) / entry.name).as_posix()
                    require(entry.name in expected,
                            'Unexpected immutable Atlas entry: ' + relative)
                    original_path = original / entry.name
                    original_info = original_path.lstat()
                    info = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(original_info.st_mode):
                        require(stat.S_ISDIR(info.st_mode)
                                and info.st_uid == owner_uid
                                and (relative in directory_names or relative in PRIVATE_ROOTS),
                                'Immutable Atlas child directory changed: ' + relative)
                    elif relative in private_names:
                        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                                and info.st_uid == owner_uid,
                                'Private Atlas child file changed: ' + relative)
                    else:
                        resolved = original_path.resolve(strict=True)
                        resolved_info = resolved.stat()
                        require(stat.S_ISLNK(info.st_mode)
                                and os.readlink(entry.path) == str(resolved)
                                and any(root == resolved or root in resolved.parents for root in roots)
                                and stat.S_ISREG(resolved_info.st_mode)
                                and not resolved_info.st_mode & 0o222,
                                'Immutable Atlas child link changed: ' + relative)
            require(actual == expected, 'Immutable Atlas child layout changed: ' + (name or '.'))
            require(target.lstat().st_mtime_ns == observed_mtime,
                    'Immutable Atlas directory changed during validation: ' + (name or '.'))
        self.summary.pop('changed_directory_under_validation', None)
        return examined

    def verify(self, data, record):
        require(fingerprint(data, directory=True) == record['data_identity'], 'Atlas cache data root changed')
        owner_uid = self.root.stat().st_uid
        require(record['data_identity']['uid'] == owner_uid, 'Atlas cache data owner differs')
        names, changed = [], []
        for row in record['directories']:
            self.ctx.check()
            require(isinstance(row, dict) and set(row) == {'path', 'device', 'inode', 'uid', 'mtime_ns'}
                    and (row['path'] == '' or relative_name(row['path']))
                    and all(type(row[key]) is int and row[key] >= 0 for key in ('device', 'inode', 'uid', 'mtime_ns'))
                    and row['uid'] == owner_uid,
                    'Invalid immutable Atlas directory receipt')
            # Every immutable parent is itself recorded and checked before launch.
            # Avoid rechecking the same ancestors for all 9,000 directories.
            path = Path(data) / row['path']
            fingerprint(path, directory=True)
            info = path.lstat()
            require((info.st_dev, info.st_ino, info.st_uid) ==
                    (row['device'], row['inode'], row['uid']),
                    'Immutable Atlas directory changed: ' + (row['path'] or '.'))
            if info.st_mtime_ns != row['mtime_ns']:
                changed.append((row, info.st_mtime_ns))
            names.append(row['path'])
        require(len(names) == len(set(names)), 'Duplicate Atlas cache directory receipt')
        directory_names = set(names)
        require('' in directory_names, 'Incomplete immutable Atlas directory receipt')
        for name in names:
            if name:
                parent = Path(name).parent.as_posix()
                require(('' if parent == '.' else parent) in directory_names,
                        'Incomplete immutable Atlas directory receipt')
        changed_entries = (self.verify_changed_directories(data, record, changed, directory_names)
                           if changed else 0)
        for row in record['anchors']:
            require(isinstance(row, dict) and set(row) == {'path', 'source', 'source_identity', 'sha256'}
                    and relative_name(row['path']) and isinstance(row['source'], str)
                    and Path(row['source']).is_absolute() and re.fullmatch('[0-9a-f]{64}', str(row['sha256'])),
                    'Invalid Atlas immutable anchor')
            path = real_path(data, row['path'])
            resolved = Path(row['source']).resolve(strict=True)
            roots = [Path(value['path']) for value in self.identity['source_roots']]
            require(path.is_symlink() and str(path.resolve(strict=True)) == row['source']
                    and resolved == Path(row['source'])
                    and any(root == resolved or root in resolved.parents for root in roots)
                    and fingerprint(Path(row['source'])) == row['source_identity']
                    and not Path(row['source']).stat().st_mode & 0o222
                    and base.file_hash(Path(row['source'])) == row['sha256'], 'Atlas immutable anchor changed')
        for name in record['private_files']:
            require(fingerprint(real_path(data, name))['uid'] == owner_uid,
                    'Private Atlas cache file owner changed: ' + name)
        examined = total = 0
        for name in PRIVATE_ROOTS:
            root = real_path(data, name, directory=True)
            require(root.lstat().st_uid == owner_uid, 'Private Atlas cache root owner changed: ' + name)
            pending = [root]
            while pending:
                self.ctx.check()
                with os.scandir(pending.pop()) as entries:
                    for entry in entries:
                        examined += 1
                        require(examined <= PRIVATE_ENTRY_LIMIT, 'Private Atlas cache entry bound exceeded')
                        info = entry.stat(follow_symlinks=False)
                        if stat.S_ISDIR(info.st_mode):
                            require(info.st_uid == self.root.stat().st_uid,
                                    'Private Atlas cache directory owner changed')
                            pending.append(Path(entry.path))
                        else:
                            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                                    'Linked private Atlas cache entry refused')
                            require(info.st_uid == self.root.stat().st_uid,
                                    'Private Atlas cache file owner changed')
                            total += info.st_size
                            require(total <= PRIVATE_BYTES_LIMIT, 'Private Atlas cache byte bound exceeded')
        # Update only parent timestamps whose entire exact child layout passed,
        # after all anchors and private entries passed as well. Checkout
        # atomically writes the qualified receipt before taking ownership.
        # Release keeps this pre-launch baseline and does no new input walk.
        for row, observed_mtime in changed:
            row['mtime_ns'] = observed_mtime
        self.summary.update(immutable_directory_checks=len(names), immutable_anchor_checks=len(record['anchors']),
                            private_entries_checked=examined, private_bytes=total,
                            immutable_anchors=record['anchors'],
                            changed_parent_directory_checks=len(changed),
                            changed_parent_entry_checks=changed_entries,
                            changed_parent_paths=[row['path'] or '.' for row, _ in changed])

    def select_compatible_generation(self):
        """Rekey one proved closed generation in place; never rebase source links.

        The callback qualifies old wrapper receipts and the actual native
        closure. Normal read/verify still checks ownership, immutable roots,
        directory receipts, anchors and every private entry. An interrupted
        atomic marker refresh can be recovered before its new pointer exists.
        """
        if self.pointer_invalid or self.legacy_identity_validator is None:
            return False
        possible = []
        for path in self.root.iterdir():
            if re.fullmatch('character-server-data-[0-9a-f]{24}(?:-[0-9a-f]{32})?', path.name):
                possible.append(path)
                if len(possible) > 16:
                    self.summary['migration_refused'] = 'cache_generation_limit_reached'
                    return False
        matches = []
        for path in possible:
            self.ctx.check()
            try:
                require(fingerprint(path, directory=True)['uid'] == self.root.stat().st_uid,
                        'Atlas migration directory owner changed')
                marker = path / 'cache.json'
                info = marker.lstat()
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                        and 0 < info.st_size <= MARKER_LIMIT, 'Invalid Atlas migration marker')
                raw = json.loads(marker.read_text())
                old_identity = raw.get('identity') if isinstance(raw, dict) else None
                if not isinstance(old_identity, dict):
                    continue
                recovered = old_identity == self.identity and raw.get('key') == self.key
                if not recovered and not self.legacy_identity_validator(old_identity):
                    continue
                probe = ServerDataCache(self.root, old_identity, self.session, self.ctx)
                probe.path, probe.marker = path, marker
                record = probe.read()
                probe.verify(path / 'data', record)
                config = real_path(path / 'data', CONFIG)
                require(not config.exists() and not config.is_symlink(),
                        'Closed Atlas migration retained credential configuration')
                matches.append((path, record, recovered))
            except base.Cancelled:
                raise
            except (base.DiagnosticError, OSError, ValueError, TypeError, KeyError):
                # An optimization donor is optional. Preserve malformed or
                # incompatible generations and use the existing full mirror.
                continue
        if len(matches) != 1:
            if matches:
                self.summary['migration_refused'] = 'ambiguous_compatible_generations'
            elif possible:
                self.summary['migration_refused'] = 'no_qualified_closed_generation'
            self.summary['migration_candidates_examined'] = len(possible)
            return False
        path, record, recovered = matches[0]
        record.update(identity=self.identity, key=self.key)
        original_path = self.path
        self.path, self.marker = path, path / 'cache.json'
        try:
            self.write(record)  # One fsync + atomic metadata replacement; no tree move.
        except base.Cancelled:
            raise
        except (base.DiagnosticError, OSError) as failure:
            self.path, self.marker = original_path, original_path / 'cache.json'
            self.summary['migration_refused'] = str(failure)
            return False
        self.summary.update(legacy_generation_migrated=not recovered,
                            interrupted_migration_recovered=recovered,
                            source_link_targets_preserved=True, migrated_generation=path.name)
        return True

    def checkout(self, target):
        """Only a clean receipt can donate data; never inspect prior session trees."""
        started = time.monotonic()
        target = Path(target)
        if not self.path.exists() and not self.path.is_symlink():
            self.select_compatible_generation()
        if not self.path.exists() and not self.path.is_symlink():
            if self.generation_limit_reached:
                self.disabled = True
                self.summary['reuse_refused'] = 'cache_generation_limit_reached'
            return False
        try:
            record = self.read()
            cached = self.path / 'data'
            self.verify(cached, record)
        except base.Cancelled:
            raise
        except (base.DiagnosticError, OSError, ValueError, TypeError, KeyError) as failure:
            # An unusable performance cache must not block a healthy session.
            # Preserve its marker/tree and rebuild through the original mirror.
            self.summary.update(reuse_refused=str(failure), refused_generation=self.path.name)
            self.path = self.root / ('character-server-data-' + self.key + '-' + self.session)
            self.marker = self.path / 'cache.json'
            require(not self.path.exists() and not self.path.is_symlink(), 'Fresh Atlas cache generation exists')
            if self.generation_limit_reached:
                self.disabled = True
                self.summary['cache_creation_disabled'] = 'cache_generation_limit_reached'
            return False
        # The base launcher just populated this small fresh pinned schema tree.
        pending = [target]; count = 0
        while pending:
            directory = pending.pop(); fingerprint(directory, directory=True)
            with os.scandir(directory) as entries:
                for entry in entries:
                    count += 1
                    require(count <= 256 and not entry.is_symlink(), 'Fresh Atlas schema tree differs')
                    if entry.is_dir(follow_symlinks=False): pending.append(Path(entry.path))
                    else: fingerprint(Path(entry.path))
        record.update(status='checked_out', owner={'session_id': self.session, 'target': str(target)})
        self.write(record)  # Refuse interrupted ownership even before directory rename.
        shutil.rmtree(target)
        cached.rename(target)
        self.record = record
        self.summary.update(reused=True, first_use_requires_full_staging=False,
                            checkout_elapsed_seconds=round(time.monotonic() - started, 6))
        return True

    def seal(self, data, stats):
        if self.disabled:
            self.summary['cache_created'] = False
            return
        data = Path(data)
        require(0 < len(self.directory_names) <= DIRECTORY_LIMIT and self.anchor_names,
                'Missing Atlas immutable cache anchors')
        directories = []
        names = set(self.directory_names)
        require(len(names) == len(self.directory_names) and '' in names,
                'Duplicate or incomplete Atlas cache directories')
        owner_uid = self.root.stat().st_uid
        for name in self.directory_names:
            require(name == '' or relative_name(name), 'Unsafe Atlas cache directory receipt')
            parent = Path(name).parent.as_posix()
            require(name == '' or ('' if parent == '.' else parent) in names,
                    'Incomplete Atlas cache directory parents')
            # All parents were created by the bounded mirror and are checked
            # exactly once here, rather than once again for every descendant.
            info = (data / name).lstat()
            require(stat.S_ISDIR(info.st_mode) and info.st_uid == owner_uid,
                    'Linked or foreign Atlas cache directory')
            directories.append({'path': name, 'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid,
                                'mtime_ns': info.st_mtime_ns})
        anchors = []
        for name in self.anchor_names.values():
            source = real_path(data, name).resolve(strict=True)
            roots = [Path(value['path']) for value in self.identity['source_roots']]
            require(any(root == source or root in source.parents for root in roots),
                    'Atlas immutable anchor escaped verified roots')
            anchors.append({'path': name, 'source': str(source), 'source_identity': fingerprint(source),
                            'sha256': base.file_hash(source)})
        self.record = {'format': 1, 'policy': POLICY, 'identity': self.identity, 'key': self.key,
            'status': 'checked_out', 'owner': {'session_id': self.session, 'target': str(data)},
            'data_identity': fingerprint(data, directory=True), 'directories': directories,
            'private_files': sorted(set(self.private_names)), 'anchors': anchors, 'stats': dict(stats)}
        self.write(self.record)
        self.summary.update(cache_created=True, immutable_directory_checks=len(directories),
                            immutable_anchor_checks=len(anchors), immutable_anchors=anchors)

    @staticmethod
    def restore_schema(source, target, runtime):
        target, runtime = Path(target), Path(runtime)
        relative = target.relative_to(runtime).as_posix()
        parent = real_path(runtime, str(Path(relative).parent), directory=True)
        if target.exists() or target.is_symlink():
            fingerprint(target)
            if base.file_hash(target) == base.file_hash(source):
                return
        shutil.copyfile(source, parent / target.name)
        target.chmod(0o600)

    def release(self, data, cleanup):
        """Credential removal and proved stopped owners precede the cache return."""
        if self.record is None:
            return False
        require(all(cleanup.get(key) is True for key in ('wine_prefix_stopped', 'owned_processes_reaped')),
                'Atlas data cache return lacks proved owned Wine cleanup')
        data = Path(data)
        fingerprint(self.marker)
        require(self.record['owner'] == {'session_id': self.session, 'target': str(data)}
                and json.loads(self.marker.read_text()) == self.record
                and fingerprint(data, directory=True) == self.record['data_identity']
                and not (self.path / 'data').exists() and not (self.path / 'data').is_symlink(),
                'Atlas data cache checkout ownership changed')
        config = real_path(data, CONFIG)
        if config.exists() or config.is_symlink():
            fingerprint(config)
            config.unlink()
        data.rename(self.path / 'data')
        self.record.update(status='closed', owner=None)
        self.write(self.record)
        if self.pointer.exists() or self.pointer.is_symlink():
            # Replacement is local cache metadata only; preserve malformed links
            # or receipts without following them or asking for manual cleanup.
            if self.pointer_invalid or self.pointer.is_symlink():
                self.pointer.rename(self.pointer.with_name(self.pointer.name + '-invalid-' + self.session))
            else:
                fingerprint(self.pointer)
        base.private_write(self.pointer, json.dumps({'format': 1, 'key': self.key,
                                                     'generation': self.path.name}) + '\n')
        self.summary.update(returned_after_owned_cleanup=True, credential_config_removed=True)
        return True
