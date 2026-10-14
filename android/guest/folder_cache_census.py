#!/usr/bin/env python3
"""Nonshipping fresh FolderCache metadata producer; no runtime registration.

Every invocation scans current membership and leaf metadata twice. No prior
fingerprint receipt, directory mtime, anchor or THI1 can donate a generation.
The FCEN1 bytes below are a source-derived projection for controlled parity
experiments, never a substitute for observed native WFD qualification.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import stat
import struct
import heapq
import tempfile
import time

FORMAT = 1
PRODUCTION_AUTHORITY = None
ACTIVATION_IMPLEMENTED = False
BRANCHES = ('texture_library', 'object_library', 'fx', 'scripts', 'scripts.loc')
WINE_SOURCE = 'b073859675060c9211fcbccfd90e4e87520dc2c2'
MAGIC = b'COHCNS1\0'
MAX_ROWS = 200000
MAX_DIRS = 16384
MAX_DIRECTORY_ENTRIES = 16384
MAX_BYTES = 64 * 1024**2
DOS_XATTR = 'user.DOSATTRIB'
ATTR_READONLY, ATTR_HIDDEN, ATTR_SYSTEM = 1, 2, 4
ATTR_DIRECTORY, ATTR_ARCHIVE, ATTR_REPARSE = 16, 32, 1024


class CensusRefused(ValueError):
    pass


def require(value, message):
    if not value:
        raise CensusRefused(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def name(value, *, path=False, empty=False):
    require(type(value) is str and (empty and value == '' or 0 < len(value) <= 259)
        and value.isascii() and '\\' not in value and ':' not in value
        and not value.startswith('/') and all(32 <= ord(c) <= 126 for c in value),
        'Unsupported native ASCII path')
    if value == '':
        return value
    parts = value.split('/') if path else [value]
    require((path or '/' not in value) and all(p and p not in ('.', '..')
        and not p.endswith(('.', ' ')) and not any(c in p for c in '*?"<>|') for p in parts),
        'Unsafe native path component')
    return value


def absolute_real(path, *, directory=True):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and path == path.absolute()
        and not str(path).startswith('//'),
        'Absolute canonical owned path required')
    for current in reversed((path, *path.parents)):
        require(not current.is_symlink(), 'Linked path ancestor refused')
    info = path.lstat()
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        and info.st_uid == os.getuid(), 'Current owned path required')
    if directory:
        require(info.st_mode & 0o500 == 0o500, 'Unreadable/unsearchable provider directory')
    return path, info


def fingerprint(info):
    # atime is intentionally excluded from the *consumed-field* authority:
    # reads may change it, and FolderCache does not consume it.
    return [info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
        info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def regular_pin(record):
    require(type(record) is dict and set(record) == {'path', 'bytes', 'sha256'}
        and type(record['path']) is str
        and type(record['bytes']) is int and 0 < record['bytes'] <= 128*1024**2
        and type(record['sha256']) is str and re.fullmatch('[0-9a-f]{64}', record['sha256']),
        'Exact current executable/runtime pin required')
    path, before = absolute_real(record['path'], directory=False)
    require(before.st_nlink == 1 and before.st_size == record['bytes'], 'Native/runtime size or links differ')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    hashed = hashlib.sha256()
    with os.fdopen(fd, 'rb') as stream:
        require(fingerprint(os.fstat(stream.fileno())) == fingerprint(before), 'Runtime changed before hashing')
        while True:
            chunk = stream.read(1024*1024)
            if not chunk:
                break
            hashed.update(chunk)
        require(fingerprint(os.fstat(stream.fileno())) == fingerprint(before), 'Runtime changed during hashing')
    require(fingerprint(path.lstat()) == fingerprint(before) and hashed.hexdigest() == record['sha256'],
        'Current native/runtime bytes differ')
    return dict(record, fingerprint=fingerprint(before))


def validate_recipe(root, recipe):
    required = {'format', 'branches', 'mode', 'exclusion',
        'ignore_prefixes', 'gdd_roots', 'source_roots', 'pig_providers', 'consumer', 'runtime_files',
        'wine_source_commit', 'supplements_finalized'}
    require(type(recipe) is dict and required <= set(recipe)
        and set(recipe) <= required | {'known_readonly_hardlinks'}, 'Exact current provider recipe required')
    require(type(recipe['format']) is int and recipe['format'] == FORMAT
        and recipe['branches'] == list(BRANCHES) and recipe['mode'] == 'development_dynamic'
        and recipe['exclusion'] == {'mode': 'all', 'name': None}
        and recipe['wine_source_commit'] == WINE_SOURCE and recipe['supplements_finalized'] is True,
        'Unsupported or unfinished native provider policy')
    require(recipe['gdd_roots'] == [str(root)], 'Exactly one current global GDD required')
    prefixes = recipe['ignore_prefixes']
    require(type(prefixes) is list and len(prefixes) <= 50 and all(type(p) is str
        and re.fullmatch('[A-Za-z0-9_-]{1,32}', p) for p in prefixes)
        and len({p.lower() for p in prefixes}) == len(prefixes), 'Aliased or unknown ignore-prefix policy')
    # These are current blob facts for first-census CAPTURE ONLY. No caller
    # member list/non-overlap flag is accepted; native index authority is absent.
    require(type(recipe['pig_providers']) is list and len(recipe['pig_providers']) <= 8,
        'Bounded current PIG blob inventory required')
    pig_identities = [regular_pin(p) for p in recipe['pig_providers']]
    require(all(Path(p['path']).suffix.lower() in ('.pigg', '.hogg') for p in pig_identities)
        and len({p['path'].lower() for p in pig_identities}) == len(pig_identities),
        'Unknown or aliased PIG blob inventory')
    # Discover ordinary local provider hooks rather than assuming the supplied
    # one-GDD/PIG recipe agrees with the native launch directory.
    for extra in ('localdata', 'serverdata', 'gamedatadir.txt'):
        candidate = root.parent/extra
        require(not candidate.exists() and not candidate.is_symlink(),
            'Unproved additional native source provider: '+extra)
    pig_root = root.parent/'piggs'
    discovered = []
    if pig_root.exists() or pig_root.is_symlink():
        absolute_real(pig_root)
        with os.scandir(pig_root) as entries:
            for entry in entries:
                require(len(discovered) < 8 and entry.is_file(follow_symlinks=False)
                    and Path(entry.name).suffix.lower() in ('.pigg','.hogg'),
                    'Unknown native PIG discovery entry')
                discovered.append(str(Path(entry.path)))
    require(sorted(discovered) == sorted(p['path'] for p in pig_identities),
        'Current native PIG discovery differs from capture recipe')
    require(type(recipe['source_roots']) is list and 1 <= len(recipe['source_roots']) <= 8
        and all(type(p) is str for p in recipe['source_roots']),
        'Finite owned immutable source roots required')
    sources = [absolute_real(p)[0] for p in recipe['source_roots']]
    require(len(set(sources)) == len(sources) and root in sources, 'Duplicate or missing source root')
    hardlinks = recipe.get('known_readonly_hardlinks', [])
    require(type(hardlinks) is list and len(hardlinks) <= MAX_ROWS,
        'Bounded complete readonly alias groups required')
    groups, used_paths = {}, set()
    for group in hardlinks:
        require(type(group) is list and 2 <= len(group) <= 32 and all(type(p) is str for p in group)
            and group == sorted(group) and len(set(group)) == len(group), 'Exact canonical readonly alias group required')
        require(not set(group) & used_paths, 'Readonly alias belongs to multiple groups')
        for text in group:
            path = Path(text)
            require(path.is_absolute() and '..' not in path.parts
                and any(path == p or p in path.parents for p in sources), 'Readonly alias escaped source/import closure')
            used_paths.add(text)
            require(len(used_paths) <= MAX_ROWS*2, 'Readonly alias inventory exceeds bound')
            groups[path] = tuple(Path(p) for p in group)
    require(type(recipe['runtime_files']) is list and 1 <= len(recipe['runtime_files']) <= 16,
        'Actual current Wine/FEX runtime closure required')
    identities = [regular_pin(recipe['consumer']), *[regular_pin(p) for p in recipe['runtime_files']], *pig_identities]
    require(len({p['path'] for p in identities}) == len(identities), 'Aliased runtime identities')
    return sources, identities, pig_identities, groups


def dos_attributes(path, info):
    try:
        raw = os.getxattr(path, DOS_XATTR, follow_symlinks=True)
    except OSError as exc:
        import errno
        require(exc.errno in {errno.ENODATA, errno.ENOTSUP, getattr(errno, 'ENOATTR', errno.ENODATA)},
            'DOS attributes unavailable; native projection unknown')
        raw = None
    require(raw is None or len(raw) <= 64, 'Oversized DOS attributes')
    extra = 0
    if raw is not None:
        require(re.fullmatch(b'0x[0-9a-fA-F]+', raw), 'Unqualified DOS attribute encoding')
        extra = int(raw[2:], 16) & (ATTR_HIDDEN | ATTR_SYSTEM)
    attributes = ATTR_DIRECTORY if stat.S_ISDIR(info.st_mode) else ATTR_ARCHIVE
    if not info.st_mode & 0o222:
        attributes |= ATTR_READONLY
    attributes |= extra
    if raw is None and path.name.startswith('.'):
        attributes |= ATTR_HIDDEN
    return attributes, None if raw is None else raw.hex()


def filetime(nanoseconds):
    value = nanoseconds // 100 + 116444736000000000
    require(0 <= value < 2**64, 'Unsupported native timestamp range')
    return value


def wfd(entry_name, info, attributes):
    """Canonical defined fields; unobserved short-name mapping stays explicit."""
    name(entry_name)
    require(0 <= info.st_size < 2**64, 'Unsupported native size')
    # Pinned Wine FILE_DIRECTORY_INFORMATION reports directory EndOfFile=0,
    # independent of the POSIX directory's allocation/entry-table size.
    native_size = 0 if stat.S_ISDIR(info.st_mode) else info.st_size
    result = bytearray(320)
    struct.pack_into('<IQQQII', result, 0, attributes,
        filetime(info.st_mtime_ns), filetime(info.st_atime_ns), filetime(info.st_mtime_ns),
        native_size >> 32, native_size & 0xffffffff)
    raw = entry_name.encode('ascii')
    result[44:44+len(raw)] = raw
    # Reserved fields, short-name buffer and all post-NUL padding remain zero.
    # This is a source projection, NOT a claim of observed native short names.
    return bytes(result)


class CheckedParents:
    """One-invocation ancestors, rechecked before the vector is accepted."""
    def __init__(self, sources, requests):
        self.sources, self.rows = tuple(sources), {}
        self.requests = requests

    def directory(self, path):
        path = Path(path)
        if path in self.rows:
            return
        if path.parent != path:
            self.directory(path.parent)
        info = path.lstat()
        self.requests['ancestor_initial_stats'] += 1
        require(stat.S_ISDIR(info.st_mode), 'Linked or non-directory provider ancestor')
        inside = any(path == p or p in path.parents for p in self.sources)
        if inside:
            require(info.st_uid == os.getuid() and info.st_mode & 0o500 == 0o500,
                'Provider ancestor owner/access differs')
        value = fingerprint(info) if inside else [info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid]
        self.rows[path] = (inside,value)
        require(len(self.rows) <= MAX_DIRS*4, 'Ancestor observation bound exceeded')

    def verify(self, hashed):
        for path,(inside,value) in sorted(self.rows.items(),key=lambda p:str(p[0])):
            info = path.lstat()
            self.requests['ancestor_recheck_stats'] += 1
            current = fingerprint(info) if inside else [info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid]
            require(stat.S_ISDIR(info.st_mode) and current == value, 'Provider ancestor changed during fresh snapshot')
            hashed.update(canonical({'ancestor':str(path),'identity':value,'within_source_root':inside})+b'\n')


def observe(path, info, sources, parents, groups, requests):
    parents.directory(path.parent)
    link = None
    if stat.S_ISLNK(info.st_mode):
        link = os.readlink(path)
        require(Path(link).is_absolute() and '..' not in Path(link).parts,
            'Unqualified relative/chained input alias')
        target = Path(link)
        parents.directory(target.parent)
        target_info = target.lstat()
        requests['symlink_target_stats'] += 1
        require(not stat.S_ISLNK(target_info.st_mode), 'Chained input alias refused')
    else:
        target, target_info = path, info
    require(any(target == p or p in target.parents for p in sources)
        and (stat.S_ISDIR(target_info.st_mode) or stat.S_ISREG(target_info.st_mode))
        and target_info.st_uid == os.getuid(), 'Input escaped owned provider or has unknown type')
    require(not (link and stat.S_ISDIR(target_info.st_mode)), 'Directory aliases need native mapping qualification')
    shared = None
    if stat.S_ISREG(target_info.st_mode):
        require(not target_info.st_mode & 0o222, 'Mutable input cannot donate census metadata')
        if target_info.st_nlink != 1:
            aliases = groups.get(target)
            require(aliases is not None and len(aliases) == target_info.st_nlink,
                'Unknown hardlinked input cannot donate census metadata')
            shared = []
            for alias in aliases:
                parents.directory(alias.parent)
                current = alias.lstat()
                requests['readonly_alias_stats'] += 1
                require(stat.S_ISREG(current.st_mode) and current.st_uid == os.getuid()
                    and not current.st_mode & 0o222 and fingerprint(current) == fingerprint(target_info),
                    'Readonly shared inode alias group changed')
                shared.append({'path':str(alias),'identity':fingerprint(current)})
        require(target_info.st_mode & 0o400, 'Unreadable input cannot donate override metadata')
        require(path.suffix.lower() not in ('.bin', '.dbidmap'), 'Mutable BIN/DB-ID input cannot be certified')
    attributes, xattr = dos_attributes(path, target_info)
    requests['dos_xattr_queries'] += 1
    value = {'alias': fingerprint(info), 'link': link, 'target': str(target),
        'resolved': fingerprint(target_info), 'dos_attributes': xattr, 'known_shared_inode':shared}
    return target_info, attributes, value


def _scan(root, sources, collect, records, groups):
    hashed = hashlib.sha256()
    directories = []
    # Keep the bounded row spool outside the Python object graph. Only one
    # final native blob is retained; no second list of WFD/row byte copies.
    row_count = 0
    requests = dict.fromkeys(('scandir_directories','entry_no_follow_stat_requests',
        'symlink_target_stats','readonly_alias_stats','ancestor_initial_stats',
        'ancestor_recheck_stats','dos_xattr_queries','directory_snapshots_and_rechecks'),0)
    parents = CheckedParents(sources,requests)
    for source in sources:
        parents.directory(source)
    files = links = outscope = 0
    root_info = root.lstat()
    hashed.update(canonical({'root': fingerprint(root_info)}) + b'\n')
    pending = [('', '', root)]
    while pending:
        _, relative, directory = heapq.heappop(pending)
        before = directory.lstat()
        requests['directory_snapshots_and_rechecks'] += 1
        require(stat.S_ISDIR(before.st_mode) and before.st_uid == os.getuid()
            and before.st_mode & 0o500 == 0o500, 'Current directory owner/type/access differs')
        name(relative, path=True, empty=True)
        with os.scandir(directory) as stream:
            requests['scandir_directories'] += 1
            entries = []
            for entry in stream:
                require(len(entries) < MAX_DIRECTORY_ENTRIES, 'Directory membership exceeds bounded capture')
                entries.append(entry)
            entries.sort(key=lambda p: (p.name.lower(), p.name))
        require(len({p.name.lower() for p in entries}) == len(entries), 'Case-aliased directory membership')
        require(len(entries) <= MAX_ROWS, 'Directory membership exceeds census bound')
        directory_row = {'path': relative, 'fingerprint': fingerprint(before),
            'children': [p.name for p in entries], 'root_partial_anchor': relative == ''}
        hashed.update(canonical(directory_row) + b'\n')
        if relative == '':
            selected = [p for p in entries if p.name.lower() in BRANCHES]
            require({p.name.lower() for p in selected} == set(BRANCHES)
                and all(p.is_dir(follow_symlinks=False) for p in selected),
                'Complete selected-branch provider is missing or aliased')
        rows = 0
        for entry in entries:
            name(entry.name)
            path = Path(entry.path)
            info = entry.stat(follow_symlinks=False)
            requests['entry_no_follow_stat_requests'] += 1
            logical = entry.name if not relative else relative+'/'+entry.name
            name(logical, path=True)
            if relative == '' and entry.name.lower() not in BRANCHES:
                # Reference root membership only; never certify mutable/outscope
                # children or recurse into them for this optional adapter.
                hashed.update(canonical({'path': logical, 'outscope_reference': fingerprint(info)}) + b'\n')
                outscope += 1
                continue
            current, attributes, observation = observe(path, info, sources, parents, groups, requests)
            hashed.update(canonical({'path': logical, **observation}) + b'\n')
            if collect:
                records.write(struct.pack('<II', len(directories), rows)+wfd(entry.name, current, attributes))
            rows += 1
            row_count += 1
            if stat.S_ISDIR(current.st_mode):
                heapq.heappush(pending, (logical.lower(), logical, path))
            else:
                files += 1
                links += int(stat.S_ISLNK(info.st_mode))
        require(fingerprint(directory.lstat()) == fingerprint(before), 'Directory changed during snapshot')
        requests['directory_snapshots_and_rechecks'] += 1
        directories.append((relative, rows))
        require(len(directories) <= MAX_DIRS and row_count <= MAX_ROWS,
            'Complete census row/directory bound exceeded')
    if collect:
        records.seek(0)
    parents.verify(hashed)
    return {'vector_sha256': hashed.hexdigest(), 'directories': directories if collect else None,
        'records': records if collect else None, 'files': files, 'links': links,
        'directory_count': len(directories), 'outscope_root_entries': outscope,
        'rows': row_count, 'ancestor_checks':len(parents.rows),'metadata_requests':requests}


def scan(root, sources, *, collect, groups=None):
    records = tempfile.SpooledTemporaryFile(max_size=1024**2) if collect else None
    try:
        return _scan(root, sources, collect, records, groups or {})
    except BaseException:
        if records is not None:
            records.close()
        raise


def encode(snapshot, token):
    require(type(token) is str and re.fullmatch('[0-9a-f]{64}', token), 'Exact generation token required')
    table = bytearray()
    first = 0
    for ordinal, (path, rows) in enumerate(snapshot['directories']):
        raw = path.encode('ascii')
        table += struct.pack('<HHIII', len(raw), 0, first, rows, ordinal)+raw
        table += bytes((-len(table)) % 4)
        first += rows
    total = 64+len(table)+328*snapshot['rows']
    require(total <= MAX_BYTES, 'Native census exceeds bounded RAM/file size')
    header = MAGIC+struct.pack('<IIIIII', FORMAT, total, len(snapshot['directories']),
        snapshot['rows'], 64+len(table), 0)+bytes.fromhex(token)
    from io import BytesIO
    packet = BytesIO()
    packet.write(header); packet.write(table)
    while True:
        chunk = snapshot['records'].read(1024*1024)
        if not chunk:
            break
        packet.write(chunk)
    require(packet.tell() == total, 'Census row spool differs')
    return packet.getvalue()


def capture(root, recipe, operation_id, *, _between_passes=None):
    require(type(operation_id) is str and re.fullmatch('[0-9a-f]{32}', operation_id), 'Exact current operation identity required')
    begin = time.monotonic()
    started_at = timestamp()
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    root, _ = absolute_real(root)
    sources, identities, pig_identities, groups = validate_recipe(root, recipe)
    prepared = time.monotonic()
    first = scan(root, sources, collect=True, groups=groups)
    captured = time.monotonic()
    try:
        if _between_passes is not None:
            _between_passes()
        second = scan(root, sources, collect=False, groups=groups)
        require(first['vector_sha256'] == second['vector_sha256']
            and all(first[k] == second[k] for k in ('files', 'links', 'directory_count', 'outscope_root_entries')),
            'Complete current metadata generation changed between fresh passes')
        for row in identities:
            require(fingerprint(Path(row['path']).lstat()) == row['fingerprint'], 'Native/runtime changed during provider validation')
        validated = time.monotonic()
        token = digest({'recipe_sha256': digest(recipe), 'vector_sha256': first['vector_sha256'],
            'operation_id': operation_id, 'native_runtime': identities})
        packet = encode(first, token)
    finally:
        first['records'].close()
    ended = time.monotonic()
    report = {'format': FORMAT, 'status': 'fresh_complete_metadata_captured_nonshipping',
        'started_at_utc': started_at, 'completed_at_utc': timestamp(),
        'operation_id': operation_id, 'generation_token': token, 'recipe_sha256': digest(recipe),
        'vector_sha256': first['vector_sha256'], 'root': str(root), 'native_runtime': identities,
        'files': first['files'], 'linked_files': first['links'], 'directories': first['directory_count'],
        'ancestor_checks_per_pass': first['ancestor_checks'],
        'metadata_requests':{'capture':first['metadata_requests'],'recheck':second['metadata_requests'],
            'interpretation':'explicit Python metadata API requests, not measured kernel syscall counts'},
        'record_count': first['rows'], 'outscope_root_reference_entries': first['outscope_root_entries'],
        'root_anchor_complete': False, 'complete_branches': list(BRANCHES),
        'fresh_full_metadata_passes': 2, 'prior_fingerprint_receipt_used': False,
        'same_operation_observations_reused': False,
        'observation_fusion_reason': 'existing mirror observations precede all final supplements; complete post-supplement coverage is unproved',
        'native_projection': 'source_derived_consumed_fields_unqualified',
        'native_short_names_observed': False, 'current_access_creation_field_parity_claimed': False,
        'actual_Wine_WFD_parity_qualified': False, 'native_registration_allowed': False,
        'current_pig_blob_facts': pig_identities, 'native_pig_index_complete': False,
        'known_readonly_shared_inode_alias_paths':len(groups),
        'native_pig_branch_nonoverlap_qualified': False,
        'effective_native_provider_selection_qualified': False,
        'actual_native_one_GDD_predicate_observed': False,
        'authenticated_import_content_identity_verified_by_producer': False,
        'native_activation_allowed': False, 'shipping_allowed': False,
        'persistent_native_provider_authority_created': False, 'mutable_BIN_schema_or_ID_certification': False,
        'production_authority_present': PRODUCTION_AUTHORITY is not None,
        'provider_inputs_changed_by_producer': False,
        'phase_seconds': {'current_recipe_and_native_hashes': round(prepared-begin,6),
            'fresh_complete_capture': round(captured-prepared,6),
            'fresh_complete_recheck': round(validated-captured,6), 'encode': round(ended-validated,6)},
        'whole_preflight_seconds': round(ended-begin,6),
        'process_maxrss_kib_before': rss_before,
        'process_maxrss_kib_after': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'packet': {'bytes': len(packet), 'sha256': hashlib.sha256(packet).hexdigest()}}
    require(PRODUCTION_AUTHORITY is None and ACTIVATION_IMPLEMENTED is False, 'Prototype cannot promote production authority')
    return packet, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--recipe', type=Path, required=True)
    parser.add_argument('--operation-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch('[0-9a-f]{32}', args.operation_id), 'Exact current operation identity required')
    root, _ = absolute_real(args.data_root)
    output, _ = absolute_real(args.output)
    require(not (output == root or root in output.parents or output in root.parents),
        'Census output must be separate from provider inputs')
    recipe_path, _ = absolute_real(args.recipe, directory=False)
    require(recipe_path.stat().st_size <= 65536, 'Recipe exceeds bound')
    report_path = output/('folder-census-'+args.operation_id+'.json')
    packet_path = output/('folder-census-'+args.operation_id+'.bin')
    require(not any(p.exists() or p.is_symlink() for p in (report_path, packet_path)),
        'Current operation output already exists; preserve prior evidence')
    start = time.monotonic()
    started_at = timestamp()
    try:
        def unique(rows):
            result = {}
            for key, value in rows:
                require(key not in result, 'Duplicate recipe JSON field')
                result[key] = value
            return result
        recipe = json.loads(recipe_path.read_bytes(), object_pairs_hook=unique,
            parse_constant=lambda x: (_ for _ in ()).throw(CensusRefused('Nonfinite recipe JSON')))
        # Refuse unsafe output before creating even a fallback report there.
        for text in recipe.get('source_roots', []):
            source = Path(text)
            if output == source or source in output.parents or output in source.parents:
                raise SystemExit('Census output overlaps an immutable source root')
        packet, report = capture(root, recipe, args.operation_id)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        packet = None
        report = {'format': FORMAT, 'status': 'ordinary_native_fallback_required',
            'started_at_utc': started_at, 'completed_at_utc': timestamp(),
            'operation_id': args.operation_id, 'reason': str(exc), 'error_type': type(exc).__name__,
            'native_registration_allowed': False, 'native_activation_allowed': False,
            'shipping_allowed': False, 'provider_inputs_changed_by_producer': False,
            'whole_preflight_seconds': round(time.monotonic()-start,6)}
    if packet is not None:
        with packet_path.open('xb') as stream:
            stream.write(packet)
    with report_path.open('x') as stream:
        json.dump(report, stream, indent=2); stream.write('\n')
    print(json.dumps({'status': report['status'], 'report': str(report_path),
        'native_registration_allowed': False, 'whole_preflight_seconds': report['whole_preflight_seconds']}))
    return 0 if packet is not None else 2


if __name__ == '__main__':
    raise SystemExit(main())
