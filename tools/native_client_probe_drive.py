#!/usr/bin/env python3
"""Owned, fixed X: alias for a read-only CI probe; no provider authority.

The caller owns native process attribution and cleanup. Admission alone requires
an actually closed private Wine prefix. Checks while Game/probe run retain every
directory handle and validate the exact alias and physical work/data identities.
No native source, input payload or existing drive mapping is changed.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat

import native_client_census_observed_bridge as bridge
import qualify_native_client_startup as startup


FALSE_AUTHORITY = {
    'provider_authority': False, 'asset_authority': False,
    'Android_mapping_authority': False, 'native_registration_allowed': False,
    'native_replay_allowed': False, 'publication_allowed': False,
    'Game_GDD_root_changed': False, 'absolute_root_equivalence_qualified': False,
    'volume_identity_equivalence_qualified': False,
    'native_short_name_equivalence_qualified': False,
}
NATIVE_ROOT = 'X:/data'
LINK_NAME = 'x:'
MAX_PATH = 260


def require(value, message):
    if not value:
        raise ValueError(message)


def _identity(info):
    return [info.st_dev, info.st_ino, info.st_uid]


def _directory_pin(info):
    return (_identity(info), info.st_gid, stat.S_IMODE(info.st_mode))


def _link_pin(info):
    return (_identity(info), info.st_gid, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _absolute(path):
    text = os.fspath(path)
    require(type(text) is str and text.startswith('/') and not text.startswith('//')
            and text.isascii() and all(32 <= ord(c) <= 126 for c in text)
            and '\\' not in text and ':' not in text,
            'Unambiguous absolute host directory required')
    value = Path(text)
    require('..' not in value.parts and str(value) == text and value != Path('/'),
            'Canonical non-root host directory required')
    return value


def _component(name, *, alias=False):
    return (bridge._component(name) and (alias and name in ('.', '..') or
            name not in ('.', '..') and not name.endswith(('.', ' '))))


def _decode_view(census):
    if type(census) is bridge.CensusView:
        view = bridge.decode(census.packet, census.generation)
        require(view == census, 'Census view differs from its complete immutable packet')
    else:
        view = bridge.decode(census)
    return view


def _path_observation(census):
    """Check every probe-constructed path, without storing a second row list."""
    return _path_observation_view(_decode_view(census))


def _path_observation_view(view):
    require(view.directories[0].path == '', 'Partial source root anchor required')
    roots = list(view.rows(0))
    require(len(roots) == 5 and {row['name'] for row in roots} == set(bridge.BRANCHES)
            and all(row['attributes'] & 16 for row in roots),
            'Complete exact five-branch source census required')
    observed_roots = {entry.path for entry in view.directories if '/' not in entry.path and entry.path}
    require(observed_roots == set(bridge.BRANCHES), 'Exact source branch directory closure required')
    hashed = hashlib.sha256()
    counts = dict.fromkeys(('root', 'directory', 'wildcard', 'row', 'dot_alias',
                           'projected_short_alias'), 0)
    maximum, longest = 0, None

    def path(kind, value):
        nonlocal maximum, longest
        require(value.isascii() and '\x00' not in value and len(value) < MAX_PATH,
                'Constructed native ANSI probe path reaches MAX_PATH')
        hashed.update(kind.encode('ascii') + b'\0' + value.encode('ascii') + b'\n')
        counts[kind] += 1
        if len(value) > maximum:
            maximum, longest = len(value), {'kind': kind, 'path': value}

    path('root', NATIVE_ROOT)
    for row in roots:
        path('row', NATIVE_ROOT + '/' + row['name'])
    for directory in view.directories:
        if not directory.path:
            continue  # Native root is a readable partial anchor, never enumerated.
        require(directory.path.split('/')[0] in bridge.BRANCHES
                and all(_component(part) for part in directory.path.split('/')),
                'Source directory escaped exact selected branches')
        native = NATIVE_ROOT + '/' + directory.path
        path('directory', native)
        path('wildcard', native + '/*')
        for alias in ('.', '..'):
            path('dot_alias', native + '/' + alias)
        seen, previous = set(), None
        for row in view.rows(directory.ordinal):
            name = row['name']
            require(_component(name, alias=True) and name.lower() not in seen,
                    'Unsupported or case-aliased source row name')
            seen.add(name.lower())
            if name not in ('.', '..'):
                require(previous is None or previous < name.lower(),
                        'Source rows are not in canonical source order')
                previous = name.lower()
            path('row', native + '/' + name)
            if row['alternate']:
                require(_component(row['alternate']), 'Unsupported projected short alias')
                path('projected_short_alias', native + '/' + row['alternate'])
    return {'format': 1, 'role': 'complete_source_census_ANSI_probe_path_bound',
            'packet_bytes': len(view.packet), 'packet_sha256': hashlib.sha256(view.packet).hexdigest(),
            'generation': view.generation, 'source_directories': len(view.directories),
            'source_rows': view.row_count, 'native_root': NATIVE_ROOT,
            'complete_selected_branches': list(bridge.BRANCHES), 'root_anchor_partial': True,
            'root_enumeration_claimed': False, 'all_constructed_paths_below_MAX_PATH': True,
            'MAX_PATH': MAX_PATH, 'path_counts': counts, 'path_stream_sha256': hashed.hexdigest(),
            'maximum_path_characters': maximum, 'longest_checked_path': longest,
            'native_alternate_name_field_characters': 13,
            'alternate_name_paths_constructed_by_native_probe': False,
            'unknown_native_entries_admitted_by_this_check': False, **FALSE_AUTHORITY}


class MappedProbeDrive:
    """A terminal custody context; close never deletes its owned prefix alias."""

    def __init__(self, prefix, work, prefix_identity, census=None):
        self.prefix, self.work = _absolute(prefix), _absolute(work)
        require(not (self.prefix == self.work or self.prefix in self.work.parents
                     or self.work in self.prefix.parents), 'Prefix and provider work must be disjoint')
        require(type(prefix_identity) in (list, tuple) and len(prefix_identity) == 3
                and all(type(value) is int and value >= 0 for value in prefix_identity)
                and prefix_identity[2] == os.geteuid(), 'Exact owned prefix identity required')
        self.prefix_identity = list(prefix_identity)
        self._paths, self._view = None, None
        self._held, self._target_fd, self._link_info = {}, None, None
        self._directory_history = {}
        self._state, self._created, self._checks = 'new', False, 0
        self._admission_census = False
        if census is not None:
            self.bind_census(census)

    @property
    def native_root(self):
        self.require_census()
        return NATIVE_ROOT

    def require_census(self):
        require(self._state == 'admitted' and self._view is not None,
                'Held admitted mapping and complete path census required for native use')
        return self._paths

    def bind_census(self, census):
        try:
            require(self._state in ('new', 'admitted') and self._view is None,
                    'Census binding is single-use and cannot revive a context')
            if self._state == 'admitted':
                self._check()
            view = _decode_view(census)
            paths = _path_observation_view(view)
            if self._state == 'admitted':
                self._check()
            self._view, self._paths = view, paths
            return self.report()
        except BaseException:
            self.close()
            raise

    def _hold_chain(self, path):
        chain = [Path('/')] + [Path('/').joinpath(*path.parts[1:index + 1])
                                for index in range(1, len(path.parts))]
        for current in chain:
            if current in self._held:
                continue
            parent = self._held.get(current.parent)
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            descriptor = os.open(current.name if parent else str(current), flags,
                                 dir_fd=parent[0] if parent else None)
            try:
                info = os.fstat(descriptor)
                observed = os.stat(current.name if parent else str(current),
                                   dir_fd=parent[0] if parent else None, follow_symlinks=False)
                require(stat.S_ISDIR(info.st_mode) and stat.S_ISDIR(observed.st_mode)
                        and _directory_pin(info) == _directory_pin(observed),
                        'No-follow held ancestor identity differs')
                self._held[current] = (descriptor, info)
                self._directory_history[current] = info
            except BaseException:
                os.close(descriptor)
                raise

    def _check_directories(self):
        for path, (descriptor, original) in self._held.items():
            parent = self._held.get(path.parent) if path != Path('/') else None
            observed = os.stat(path.name if parent else str(path),
                               dir_fd=parent[0] if parent else None, follow_symlinks=False)
            held = os.fstat(descriptor)
            require(stat.S_ISDIR(observed.st_mode) and stat.S_ISDIR(held.st_mode)
                    and _directory_pin(original) == _directory_pin(held) == _directory_pin(observed),
                    'Held directory/ancestor identity or mode changed')
        for path in (self.prefix, self.prefix/'dosdevices', self.work, self.work/'data'):
            info = self._held[path][1]
            require(info.st_uid == os.geteuid() and info.st_mode & 0o500 == 0o500,
                    'Current-owned readable directory required')
        info = self._held[self.prefix][1]
        require(_identity(info) == self.prefix_identity and not info.st_mode & 0o077,
                'Exact private prefix identity required')

    def _aliases(self, *, created):
        descriptor = self._held[self.prefix/'dosdevices'][0]
        entries = os.listdir(descriptor)
        require(len(entries) <= 256, 'Bounded existing Wine drive inventory required')
        aliases = [name for name in entries if name.lower() in ('x:', 'x::')]
        require(aliases == ([LINK_NAME] if created else []),
                'Existing or case-aliased X: Wine drive refused')

    def _check(self):
        self._check_directories()
        self._aliases(created=True)
        descriptor = self._held[self.prefix/'dosdevices'][0]
        current = os.stat(LINK_NAME, dir_fd=descriptor, follow_symlinks=False)
        require(stat.S_ISLNK(current.st_mode) and current.st_uid == os.geteuid()
                and _link_pin(current) == _link_pin(self._link_info)
                and os.readlink(LINK_NAME, dir_fd=descriptor) == str(self.work),
                'Exact owned X: link identity/target changed')
        linked = os.stat(LINK_NAME, dir_fd=descriptor, follow_symlinks=True)
        require(_directory_pin(linked) == _directory_pin(self._held[self.work][1])
                == _directory_pin(os.fstat(self._target_fd)),
                'Mapped work physical directory identity changed')

    def admit(self):
        try:
            require(self._state == 'new', 'Mapping context is single-admission and terminal')
            for path in (self.prefix/'dosdevices', self.work/'data'):
                self._hold_chain(path)
            self._check_directories()
            require(startup.process_census(self.prefix) == [],
                    'Actual owned prefix must be closed before drive creation')
            self._admission_census = True
            self._aliases(created=False)
            descriptor = self._held[self.prefix/'dosdevices'][0]
            os.symlink(str(self.work), LINK_NAME, dir_fd=descriptor)
            self._created = True
            self._link_info = os.stat(LINK_NAME, dir_fd=descriptor, follow_symlinks=False)
            self._target_fd = os.open(LINK_NAME, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
                                      dir_fd=descriptor)
            self._check()
            require(startup.process_census(self.prefix) == [],
                    'Owned prefix became active during drive admission')
            self._state = 'admitted'
            self._checks += 1
            return self.report()
        except BaseException:
            self.close()
            raise

    def check(self):
        try:
            require(self._state == 'admitted', 'Held admitted mapping required')
            self._check()
            self._checks += 1
            return self.report()
        except BaseException:
            self.close()
            raise

    def report(self):
        return {'format': 1, 'role': 'owned_fixed_X_drive_readonly_CI_probe_mapping',
                'prefix': str(self.prefix), 'work': str(self.work),
                'data': str(self.work/'data'), 'native_root': NATIVE_ROOT,
                'path_census_admitted': self._view is not None,
                'path_census_previously_bound': self._paths is not None,
                'native_use_admitted': self._state == 'admitted' and self._view is not None,
                'prefix_identity': self.prefix_identity[:],
                'state': self._state, 'created_exclusively': self._created,
                'closed_prefix_process_census_at_admission': self._admission_census,
                'successful_identity_checks': self._checks,
                'held_directory_count': len(self._held),
                'work_identity': _identity(self._directory_history[self.work]) if self.work in self._directory_history else None,
                'data_identity': _identity(self._directory_history[self.work/'data']) if self.work/'data' in self._directory_history else None,
                'held_directory_identities': [{'path': str(path), 'identity': _identity(info),
                    'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode)}
                    for path, info in self._directory_history.items()],
                'link': {'path': str(self.prefix/'dosdevices'/LINK_NAME), 'target': str(self.work),
                    'identity': _identity(self._link_info) if self._link_info else None,
                    'exact_readlink_checked': self._checks > 0,
                    'preserved_with_owned_private_prefix': self._created},
                'source_path_observation': self._paths,
                'new_provider_copy_created': False, 'existing_mapping_overwritten': False,
                'source_payloads_modified': False, 'native_process_attribution_owned_by_caller': True,
                'native_execution_performed_by_this_module': False, **FALSE_AUTHORITY}

    def close(self):
        descriptors = ([self._target_fd] if self._target_fd is not None else [])
        descriptors += [descriptor for descriptor, _ in self._held.values()]
        self._target_fd, self._held, self._state, self._view = None, {}, 'closed', None
        failure = None
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except BaseException as error:
                if failure is None:
                    failure = error
        if failure is not None:
            raise failure

    def __enter__(self):
        self.admit()
        return self

    def __exit__(self, *unused):
        self.close()
