"""Install only the qualified native Atlas graph into the private server tree.

The native generator is a host-only tool and never ships. World inputs are
proved once against the exact geometry/group/trick inventory; subsequent starts
reuse the proof only while all readonly input and graph fingerprints match.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import tempfile
import time
import zipfile

import atlas_world_assets as world

ARCHIVE = 'atlas-beacons.zip'
MANIFEST = 'atlas-beacon-manifest.json'
ROLE = 'authentic_native_atlas_beacon_graph'
MAP = 'maps/city_zones/city_01_01/city_01_01.txt'
GRAPH = 'data/server/' + MAP + '.v8.bcn'
DATE = GRAPH + '.date'
MARKER = 'data/server/atlas-beacon-installed.json'
POLICY = 'exact_native_atlas_graph_required_geometry_two_fresh_layouts_v3'
GEOMETRY_POLICY = 'exact_required_original_atlas_object_geometry_v1'
GEOMETRY_MARKER = 'atlas-required-geometry-installed.json'
SERVER_GEOMETRY_PROFILE = 'required_original_object_geometry'
GEOMETRY_CACHE_POLICY = 'once_required_original_atlas_private_geobin_refresh_v1'
# Frozen only after the hosted producer completes real generation/readback/CRC/routes.
MANIFEST_SHA256 = 'ee11bb703eed85229948b30b41277c515faf80da31ccd0436171862765ba41f4'
ARCHIVE_SHA256 = '0c7f602d31a438c6e67409bbb89da5d45ee3aacf13c96a50de9401d7973b2949'
ARCHIVE_BYTES = 16150904
STOCK_MAPSERVER_SHA256 = '6a5bf60b2130c31df74f1767510de65c581652caa90f639a5a6e4a9453b47d36'
SOURCE_COMMIT = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA_COMMIT = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
BASE_ARCHIVE = {'bytes': 615541018, 'sha256': '28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07'}
WORLD_MANIFEST_SHA256 = '204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86'
VISUAL_GEOMETRY_SHA256 = '208393ade4edbb9608e200fc7103279217ce95a0cc316eac8018bfe558f54f1f'
VISUAL_SOURCE_MANIFEST = {'bytes': 42553059, 'sha256': 'e1f1702c9d5b38f38bb324b1171ac7aeaa5cba7e12072dd8face4efbc09a5fa3'}
VISUAL_OBJECT_GEOMETRY_SHA256 = 'c5eddbe19511356d1c9eb26890728b169db6989917da9e1375b6f1692f41bb43'
REQUIRED_GEOMETRY_SHA256 = 'c5eddbe19511356d1c9eb26890728b169db6989917da9e1375b6f1692f41bb43'
REQUIRED_GEOS = 406
PROFILES = ('required_geometry_cold', 'client_visual_reopen')
MAX_MANIFEST = 8 * 1024 * 1024
MAX_GRAPH = 128 * 1024 * 1024
MAX_INPUTS = 12288
EPOCH = 1767225600


def require(condition, message):
    if not condition: raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def regular(path, limit, *, readonly=False):
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= limit,
            'Linked, special, empty or oversized beacon package file')
    require(not readonly or not info.st_mode & 0o222, 'Beacon proof requires readonly input')
    return info


def pin(path, context=None):
    digest = hashlib.sha256(); total = 0
    with Path(path).open('rb') as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b''):
            if context is not None: context.check()
            total += len(raw); digest.update(raw)
    return {'bytes': total, 'sha256': digest.hexdigest()}


def safe(name):
    return (isinstance(name, str) and name and name.isascii() and '\\' not in name and ':' not in name
            and PurePosixPath(name).as_posix() == name and not name.startswith('/')
            and all(part not in ('', '.', '..') for part in name.split('/')))


def input_name(name):
    if not safe(name): return False
    # Logical directories are canonical; original leaf spelling remains exact.
    parts = name.split('/')
    if any(part != part.casefold() for part in parts[:-1]): return False
    folded = name.casefold()
    return (
        folded.startswith('data/object_library/') and folded.endswith(('.geo', '.txt'))
        or folded.startswith('data/maps/city_zones/city_01_01/') and folded.endswith('.txt')
        or folded.startswith('data/tricks/') and folded.endswith('.txt'))


def read_manifest(path):
    regular(path, MAX_MANIFEST)
    raw = Path(path).read_bytes()
    require(re.fullmatch('[0-9a-f]{64}', MANIFEST_SHA256) and hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256,
            'Atlas beacon manifest has not been qualified or differs')
    value = json.loads(raw)
    files, inputs, native = value.get('files'), value.get('input_files'), value.get('native')
    required, profiles = value.get('required_geometry_files'), value.get('input_profiles')
    require(value.get('format') == 3 and value.get('role') == ROLE and value.get('map') == MAP
            and value.get('source_commit') == SOURCE_COMMIT and value.get('data_commit') == DATA_COMMIT
            and value.get('stock_mapserver_sha256') == STOCK_MAPSERVER_SHA256
            and value.get('runtime_graph_readback') is True
            and value.get('physical_npc_pathing_validated') is False,
            'Atlas native graph provenance differs')
    require(isinstance(files, dict) and set(files) == {GRAPH, DATE}
            and files[DATE].get('bytes') == 12 and 18 < files[GRAPH].get('bytes', 0) <= MAX_GRAPH,
            'Only the native Atlas v8 graph and v9 sidecar may be installed')
    require(isinstance(inputs, dict) and 100 < len(inputs) <= MAX_INPUTS and all(input_name(name) for name in inputs)
            and ('data/' + MAP).casefold() in {name.casefold() for name in inputs}
            and len({name.casefold() for name in inputs}) == len(inputs)
            and hashlib.sha256(canonical(inputs)).hexdigest() == value.get('input_files_sha256'),
            'Atlas collision/group source identity differs')
    require(isinstance(required, dict) and len(required) == REQUIRED_GEOS
            and all(input_name(name) and name.startswith('data/object_library/') and name.casefold().endswith('.geo')
                    for name in required)
            and len({name.casefold() for name in required}) == len(required)
            and not {name.casefold() for name in inputs}.intersection(name.casefold() for name in required)
            and len(inputs) + len(required) <= MAX_INPUTS
            and hashlib.sha256(canonical(required)).hexdigest() == REQUIRED_GEOMETRY_SHA256,
            'Exact required original object geometry identity differs')
    require(all(isinstance(record, dict) and set(record) == {'bytes', 'sha256'}
                and type(record['bytes']) is int and 0 < record['bytes'] <= MAX_GRAPH
                and re.fullmatch('[0-9a-f]{64}', str(record['sha256']))
                for record in list(files.values()) + list(inputs.values()) + list(required.values())), 'Invalid native input/payload pin')
    identity = value.get('input_identity', {})
    require(identity.get('asset_archive') == BASE_ARCHIVE
            and identity.get('world_manifest', {}).get('sha256') == WORLD_MANIFEST_SHA256
            and identity.get('visual_geometry_sha256') == VISUAL_GEOMETRY_SHA256
            and identity.get('visual_source_manifest') == VISUAL_SOURCE_MANIFEST
            and identity.get('visual_object_geometry_sha256') == VISUAL_OBJECT_GEOMETRY_SHA256
            and identity.get('required_geometry_sha256') == REQUIRED_GEOMETRY_SHA256,
            'Native graph was generated from a different world/geometry supplement')
    require(isinstance(native, dict) and native.get('native_full_graph_readback_verified') is True
            and native.get('fresh_ordinary_world_crc_verified') is True
            and native.get('native_pathfinder_successes') == 32 and native.get('date_version') == 9
            and 1000 < native.get('connected_beacons', 0) <= native.get('combat_beacons', 0) <= 1000000
            and native.get('ground_connections', 0) > 1000 and native.get('grid_blocks', 0) > 0
            and re.fullmatch('0x[0-9a-f]{8}', str(native.get('full_world_crc'))),
            'Native generation, full reader, CRC or path proofs are incomplete')
    require(isinstance(profiles, dict) and set(profiles) == set(PROFILES), 'Both fresh required-geometry native layouts are required')
    for profile in PROFILES:
        selected = {**inputs, **required}
        require(profiles[profile] == {'native': native,
                    'input_files_sha256': hashlib.sha256(canonical(selected)).hexdigest()},
                'Fresh cold/warm native CRC, graph readback or path proofs differ')
    return value


def actual_targets(runtime, names, context):
    """Resolve canonical logical directories using the existing world policy."""
    return world.resolve_targets(Path(runtime), names, context)


def select_profile(runtime, manifest, context):
    """Require the one complete geometry inventory proved in both fresh layouts."""
    runtime = Path(runtime); required = manifest['required_geometry_files']
    selected = {**manifest['input_files'], **required}
    targets = actual_targets(runtime, selected, context)
    for name in required:
        context.check()
        require(os.path.lexists(targets[name]),
                'Every required original Atlas geometry leaf must exist before graph installation')
    profile = SERVER_GEOMETRY_PROFILE
    declared = {name.casefold(): name for name in selected}
    require(len(declared) == len(selected), 'Case-conflicting Atlas source declaration refused')
    # The enclosing server cache verifies immutable links; this finite inventory
    # also refuses extra source leaves whose collision contribution was not proved.
    actual, seen = {}, set()
    for relative in ('data/object_library', 'data/maps/city_zones/city_01_01', 'data/tricks'):
        # A non-created sentinel makes the directory a parent, so the world
        # resolver reuses its spelling rather than treating it as a leaf.
        sentinel = relative + '/.atlas-beacon-inventory'
        root = actual_targets(runtime, (sentinel,), context)[sentinel].parent
        require(root.is_dir() and not root.is_symlink(), 'Private Atlas source directory required')
        for path in root.rglob('*'):
            context.check()
            relative_name = path.relative_to(runtime).as_posix()
            folded = relative_name.casefold()
            require(folded not in seen, 'Case-conflicting Atlas source inventory refused')
            seen.add(folded)
            require(not (path.is_symlink() and path.is_dir()), 'Linked Atlas source directory refused')
            suffixes = ('.geo', '.txt') if relative == 'data/object_library' else ('.txt',)
            if path.suffix.casefold() in suffixes and not path.is_dir():
                actual[folded] = relative_name
                require(len(actual) <= MAX_INPUTS, 'Atlas source inventory exceeds proof bound')
    require(set(actual) == set(declared)
            and all(actual[folded] == targets[name].relative_to(runtime).as_posix()
                    for folded, name in declared.items()),
            'Actual Atlas source inventory has no qualified native profile')
    return profile, selected



def required_geometry_identity(files):
    require(isinstance(files, dict) and len(files) == REQUIRED_GEOS
            and all(input_name(name) and name.startswith('data/object_library/')
                    and name.casefold().endswith('.geo') for name in files)
            and len({name.casefold() for name in files}) == len(files)
            and all(isinstance(row, dict) and set(row) == {'bytes', 'sha256'}
                    and type(row['bytes']) is int and 0 < row['bytes'] <= MAX_GRAPH
                    and re.fullmatch('[0-9a-f]{64}', str(row['sha256']))
                    for row in files.values())
            and hashlib.sha256(canonical(files)).hexdigest() == REQUIRED_GEOMETRY_SHA256,
            'Exact required original object geometry identity differs')
    return {'format': 1, 'policy': GEOMETRY_POLICY,
            'required_geometry_sha256': REQUIRED_GEOMETRY_SHA256,
            'file_count': REQUIRED_GEOS, 'cache_policy': GEOMETRY_CACHE_POLICY}


def geometry_client_identity(worktree, context):
    sentinel = actual_targets(worktree, ('data/.atlas-required-geometry',), context)['data/.atlas-required-geometry']
    data = sentinel.parent
    world.real_directory(worktree); world.real_directory(data)
    return {'worktree': str(worktree),
            'directory_identity': [[path.stat().st_dev, path.stat().st_ino] for path in (worktree, data)],
            'client_work_sha256': hashlib.sha256(
                world.read_regular(worktree / 'client-work.json', 1024**2)).hexdigest()}


def required_geometry_cache_inventory(worktree, files, context):
    """Use the existing world allowlist for finite owned caches, resolving case."""
    worktree = Path(worktree)
    sentinel = 'data/geobin/.atlas-required-geometry-cache'
    root = actual_targets(worktree, (sentinel,), context)[sentinel].parent
    if not os.path.lexists(root): return []
    world.real_directory(root)
    geometry = {name.removeprefix('data/').casefold() for name in files}
    pending, scanned, total, result, seen = [root], 0, 0, [], set()
    while pending:
        context.check()
        current = pending.pop()
        world.real_directory(current)
        for entry in current.iterdir():
            context.check()
            info = entry.lstat()
            relative = entry.relative_to(root)
            folded = relative.as_posix().casefold()
            require(folded not in seen, 'Case-conflicting required geometry cache refused')
            seen.add(folded)
            require(len(seen) <= 2 * world.MAX_CACHE_FILES,
                    'Required geometry private cache inventory exceeds bound')
            require(not stat.S_ISLNK(info.st_mode), 'Linked required geometry private cache refused')
            if stat.S_ISDIR(info.st_mode):
                pending.append(entry)
                continue
            scanned += 1
            require(scanned <= world.MAX_CACHE_FILES and stat.S_ISREG(info.st_mode),
                    'Required geometry private cache scan exceeds bound')
            if not world.cache_path_allowed(relative, geometry): continue
            size, digest, _ = world.hash_regular(entry, world.MAX_CACHE_BYTES, context)
            total += size
            require(total <= world.MAX_CACHE_BYTES, 'Required geometry cache refresh exceeds byte bound')
            result.append({'path': entry.relative_to(worktree).as_posix(),
                           'bytes': size, 'sha256': digest})
    return sorted(result, key=lambda row: row['path'])


def required_geometry_cache_receipt(saved, files):
    """Check once-only refresh history without reading regenerated cache payloads."""
    refresh, removed = saved.get('cache_refresh'), saved.get('removed_cache_files')
    require(isinstance(refresh, dict) and set(refresh) == {
                'policy', 'performed', 'removed_files', 'removed_bytes',
                'removed_inventory_sha256', 'accepted_cache_archive_modified'}
            and isinstance(removed, list) and len(removed) <= world.MAX_CACHE_FILES,
            'Required geometry cache refresh receipt is missing or malformed')
    geometry = {name.removeprefix('data/').casefold() for name in files}
    paths = []
    for row in removed:
        require(isinstance(row, dict) and set(row) == {'path', 'bytes', 'sha256'}
                and safe(row['path']) and row['path'].casefold().startswith('data/geobin/')
                and type(row['bytes']) is int and 0 < row['bytes'] <= world.MAX_CACHE_BYTES
                and re.fullmatch('[0-9a-f]{64}', str(row['sha256'])),
                'Invalid required geometry removed-cache pin')
        relative = PurePosixPath('/'.join(row['path'].split('/')[2:]))
        require(world.cache_path_allowed(relative, geometry),
                'Required geometry cache history exceeds the finite allowlist')
        paths.append(row['path'])
    require(paths == sorted(paths) and len({name.casefold() for name in paths}) == len(paths)
            and refresh['policy'] == GEOMETRY_CACHE_POLICY and refresh['performed'] is True
            and refresh['accepted_cache_archive_modified'] is False
            and type(refresh['removed_files']) is int and refresh['removed_files'] == len(removed)
            and type(refresh['removed_bytes']) is int
            and refresh['removed_bytes'] == sum(row['bytes'] for row in removed)
            and 0 <= refresh['removed_bytes'] <= world.MAX_CACHE_BYTES
            and refresh['removed_inventory_sha256'] == hashlib.sha256(canonical(removed)).hexdigest(),
            'Required geometry cache refresh receipt differs')
    return refresh, removed


def geometry_marker_state(worktree):
    marker = Path(worktree) / GEOMETRY_MARKER
    if not os.path.lexists(marker): return None
    raw = world.read_regular(marker, MAX_MANIFEST, installed=True)
    try: saved = json.loads(raw)
    except (ValueError, UnicodeError): return None
    return saved if isinstance(saved, dict) else None


def validate_required_geometry(worktree, context):
    """Validate the durable selected-geometry proof without graph qualification."""
    worktree = Path(worktree)
    saved = geometry_marker_state(worktree)
    require(isinstance(saved, dict), 'Required Atlas geometry receipt is missing')
    files = saved.get('required_geometry_files')
    identity = required_geometry_identity(files)
    required_geometry_cache_receipt(saved, files)
    require(saved.get('format') == 1 and saved.get('identity') == identity
            and saved.get('client_identity') == geometry_client_identity(worktree, context),
            'Required Atlas geometry receipt identity differs')
    targets = actual_targets(worktree, files, context)
    outputs = world.output_state(worktree, targets, files, context)
    require(all(row['stat'] is not None for row in outputs.values())
            and saved.get('outputs') == outputs,
            'Required Atlas geometry immutable fingerprints changed')
    return identity


def ensure_required_geometry(worktree, assets, context):
    """Prepare only the exact original server collision GEOs in the client source.

    This runs before server cache checkout/staging. Selected payload SHA-256s,
    not unrelated ZIP members, prove the finite geometry. Full UI archive
    verification remains the existing client visual/package boundary.
    """
    import client_visual_assets as visual
    started = time.monotonic()
    worktree, assets = Path(worktree), Path(assets)
    context.check()
    world.real_directory(worktree); world.real_directory(assets)
    client_identity = geometry_client_identity(worktree, context)
    source_state = visual.source_state(assets)
    saved = geometry_marker_state(worktree)
    marker = worktree / GEOMETRY_MARKER
    marker_before = world.file_state(marker, MAX_MANIFEST, installed=True) if os.path.lexists(marker) else None
    if isinstance(saved, dict):
        files = saved.get('required_geometry_files')
        try:
            identity = required_geometry_identity(files)
            refresh, prior_removed = required_geometry_cache_receipt(saved, files)
        except ValueError:
            identity = None
        if (identity is not None and saved.get('format') == 1
                and saved.get('identity') == identity and saved.get('client_identity') == client_identity
                and saved.get('source_state') == source_state):
            targets = actual_targets(worktree, files, context)
            outputs = world.output_state(worktree, targets, files, context)
            if all(row['stat'] is not None for row in outputs.values()) and saved.get('outputs') == outputs:
                return {'format': 1, 'status': 'reused_verified_required_geometry',
                        'identity': identity, 'installed_files': 0, 'input_files_checked': len(files),
                        'selected_payload_bytes_hashed': 0, 'archive_decoded': False,
                        'cache_refresh': refresh, 'cache_files_removed_this_prepare': 0,
                        'cache_refresh_reused': True, 'full_visual_preload': False, 'native_graph_qualified': False,
                        'preparation_elapsed_seconds': round(time.monotonic() - started, 6)}
    document = visual.package(assets)
    files = {name: {key: row[key] for key in ('bytes', 'sha256')}
             for name, row in document['files'].items()
             if name.startswith('data/object_library/') and name.casefold().endswith('.geo')}
    identity = required_geometry_identity(files)
    targets = actual_targets(worktree, files, context)
    before = world.output_state(worktree, targets, files, context)
    cache_reused = False
    if (isinstance(saved, dict) and saved.get('format') == 1 and saved.get('identity') == identity
            and saved.get('client_identity') == client_identity
            and saved.get('required_geometry_files') == files
            and saved.get('outputs') == before):
        try:
            refresh, removed_history = required_geometry_cache_receipt(saved, files)
            cache_reused = True
        except ValueError:
            pass
    removed = [] if cache_reused else required_geometry_cache_inventory(worktree, files, context)
    verified = installed = decoded = 0
    for name, target in targets.items():
        context.check()
        if before[name]['stat'] is not None:
            world.verify_target(target, files[name], context)
            verified += files[name]['bytes']
    missing = [name for name in files if before[name]['stat'] is None]
    if missing:
        descriptor = os.open(assets / visual.ARCHIVE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            require(world.checked_info(assets / visual.ARCHIVE, os.fstat(descriptor),
                        visual.MAX_ARCHIVE_BYTES) == source_state[visual.ARCHIVE],
                    'Required geometry source archive changed before reading')
            with os.fdopen(descriptor, 'rb', closefd=False) as stream, zipfile.ZipFile(stream) as archive:
                visual.validate_archive(archive, document['files'], context)
                for name in missing:
                    context.check(); target = targets[name]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    world.real_directory(target.parent)
                    fd, temporary_name = tempfile.mkstemp(prefix='.atlas-required-geometry-', dir=target.parent)
                    temporary = Path(temporary_name)
                    try:
                        with os.fdopen(fd, 'wb') as output:
                            world.extract_payload(archive, name, files[name], output, context)
                            output.flush(); os.fsync(output.fileno())
                        temporary.chmod(0o444)
                        os.utime(temporary, (visual.client.CACHE_EPOCH, visual.client.CACHE_EPOCH))
                        context.check()
                        world.real_directory(target.parent)
                        visual.client.publish_new_regular_file(temporary, target)
                        installed += 1; decoded += files[name]['bytes']
                    finally:
                        temporary.unlink(missing_ok=True)
            world.unchanged(assets / visual.ARCHIVE, descriptor, source_state[visual.ARCHIVE])
        finally:
            os.close(descriptor)
    context.check()
    require(visual.source_state(assets) == source_state
            and geometry_client_identity(worktree, context) == client_identity
            and actual_targets(worktree, files, context) == targets,
            'Required geometry source or destination changed during preparation')
    after = world.output_state(worktree, targets, files, context)
    require(all(row['stat'] is not None for row in after.values())
            and all(before[name]['stat'] is None or after[name] == before[name] for name in files),
            'Required geometry output disappeared or an existing leaf changed')
    require((world.file_state(marker, MAX_MANIFEST, installed=True) if os.path.lexists(marker) else None)
            == marker_before, 'Required geometry receipt changed before private cache refresh')
    if not cache_reused:
        # Flattened Atlas bins can encode missing models, and adding GEOs at
        # CACHE_EPOCH does not prove their freshness. Refresh only the exact
        # finite world-policy cache leaves before publishing this receipt.
        for row in removed:
            context.check()
            world.remove_cache(worktree / row['path'], row, context)
        removed_history = removed
        refresh = {'policy': GEOMETRY_CACHE_POLICY, 'performed': True,
                   'removed_files': len(removed), 'removed_bytes': sum(row['bytes'] for row in removed),
                   'removed_inventory_sha256': hashlib.sha256(canonical(removed)).hexdigest(),
                   'accepted_cache_archive_modified': False}
    context.check()
    require(visual.source_state(assets) == source_state
            and geometry_client_identity(worktree, context) == client_identity
            and actual_targets(worktree, files, context) == targets
            and world.output_state(worktree, targets, files, context) == after,
            'Required geometry proof changed during private cache refresh')
    previous = marker_before
    require((world.file_state(marker, MAX_MANIFEST, installed=True) if os.path.lexists(marker) else None)
            == previous, 'Required geometry receipt changed after private cache refresh')
    record = {'format': 1, 'identity': identity, 'client_identity': client_identity,
              'source_state': source_state, 'required_geometry_files': files, 'outputs': after,
              'cache_refresh': refresh, 'removed_cache_files': removed_history}
    fd, temporary_name = tempfile.mkstemp(prefix='.atlas-required-geometry-marker-', dir=worktree)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(canonical(record)); output.flush(); os.fsync(output.fileno())
        temporary.chmod(0o444)
        os.utime(temporary, (visual.client.CACHE_EPOCH, visual.client.CACHE_EPOCH))
        context.check()
        world.real_directory(worktree)
        if previous is None:
            visual.client.publish_new_regular_file(temporary, marker)
        else:
            require(world.file_state(marker, MAX_MANIFEST, installed=True) == previous,
                    'Required geometry receipt changed before publication')
            os.replace(temporary, marker)
    finally:
        temporary.unlink(missing_ok=True)
    require(validate_required_geometry(worktree, context) == identity,
            'Required geometry durable proof differs after publication')
    return {'format': 1, 'status': 'installed_verified_required_geometry',
            'identity': identity, 'installed_files': installed, 'input_files_checked': len(files),
            'selected_payload_bytes_hashed': verified + decoded, 'archive_decoded': bool(missing),
            'cache_refresh': refresh, 'cache_files_removed_this_prepare': len(removed),
            'cache_refresh_reused': cache_reused, 'full_visual_preload': False, 'native_graph_qualified': False,
            'preparation_elapsed_seconds': round(time.monotonic() - started, 6)}


def fingerprint(path, *, immutable_input=False):
    path = Path(path)
    # Imported leaves may be the existing verified per-file links. Their targets
    # are already constrained by the enclosing private client/server worktree.
    info = path.stat() if immutable_input else regular(path, MAX_GRAPH, readonly=True)
    require(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o222,
            'Atlas graph inputs must retain immutable leaf permissions')
    return {'device': info.st_dev, 'inode': info.st_ino, 'bytes': info.st_size,
            'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns,
            'mode': stat.S_IMODE(info.st_mode)}


def fingerprints(runtime, names, context, *, immutable_input=False):
    runtime = Path(runtime); result = {}
    for name, target in actual_targets(runtime, names, context).items():
        context.check()
        result[name] = {**fingerprint(target, immutable_input=immutable_input),
                        'path': target.relative_to(runtime).as_posix()}
    return result


def private_target(runtime, name, context):
    require(name in (GRAPH, DATE, MARKER), 'Unexpected beacon target')
    current = Path(runtime)
    require(current.is_dir() and not current.is_symlink(), 'Beacon runtime root must be private')
    target = actual_targets(current, (name,), context)[name]
    for part in target.relative_to(current).parts[:-1]:
        current /= part
        if not current.exists(): current.mkdir(mode=0o700)
        require(current.is_dir() and not current.is_symlink(), 'Linked beacon parent refused')
    require(not target.is_symlink(), 'Linked beacon target refused')
    return target


def atomic_bytes(path, raw):
    fd, name = tempfile.mkstemp(prefix='.atlas-beacon-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        temporary.chmod(0o400); os.utime(temporary, (EPOCH, EPOCH))
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()


def install(archive, manifest_path, runtime, *, context, imported_inputs_readonly):
    started = time.monotonic(); runtime = Path(runtime)
    require(imported_inputs_readonly is True, 'Beacon installation requires the qualified readonly private world')
    value = read_manifest(manifest_path)
    profile, selected = select_profile(runtime, value, context)
    require(pin(runtime / 'MapServer.exe', context)['sha256'] == STOCK_MAPSERVER_SHA256,
            'A different MapServer cannot consume this qualified native graph')
    inputs = fingerprints(runtime, selected, context, immutable_input=True)
    targets = {name: private_target(runtime, name, context) for name in value['files']}
    marker = private_target(runtime, MARKER, context)
    prior = None
    if marker.exists():
        try:
            regular(marker, MAX_MANIFEST)
            prior = json.loads(marker.read_bytes())
        except (ValueError, OSError, json.JSONDecodeError): pass
    if (isinstance(prior, dict) and prior.get('format') == 3 and prior.get('policy') == POLICY
            and prior.get('manifest_sha256') == MANIFEST_SHA256 and prior.get('input_fingerprints') == inputs
            and prior.get('server_geometry_profile') == profile
            and all(path.exists() for path in targets.values())
            and prior.get('graph_fingerprints') == fingerprints(runtime, targets, context)):
        return {'format': 3, 'status': 'reused_verified_graph', 'map': MAP, 'server_geometry_profile': profile,
                'full_world_crc': value['native']['full_world_crc'], 'installed_files': 0,
                'input_files_checked': len(inputs), 'input_payload_bytes_hashed': 0,
                'archive_decoded': False, 'fingerprint_walk': True, 'input_inventory_walk': True,
                'preparation_elapsed_seconds': round(time.monotonic() - started, 6)}
    total = 0
    input_targets = actual_targets(runtime, selected, context)
    for name, expected in selected.items():
        context.check()
        require(pin(input_targets[name], context) == expected, 'Actual Atlas collision/group input differs: ' + name)
        total += expected['bytes']
    require(inputs == fingerprints(runtime, selected, context, immutable_input=True)
            and select_profile(runtime, value, context)[0] == profile,
            'Atlas inputs changed while establishing native graph compatibility')
    regular(archive, 2 * MAX_GRAPH)
    require(ARCHIVE_BYTES > 0 and pin(archive, context) == {'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA256},
            'Atlas beacon archive differs from the qualified native producer')
    installed = 0
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist(); names = [entry.filename for entry in entries]
        require(len(names) == 3 and set(names) == set(value['files']) | {MANIFEST}
                and len({name.casefold() for name in names}) == 3
                and all(not entry.is_dir() and not entry.flag_bits & 1
                        and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG)
                        for entry in entries), 'Unsafe or unrelated beacon archive member')
        require(source.read(MANIFEST) == Path(manifest_path).read_bytes(), 'Embedded beacon manifest differs')
        for name, expected in value['files'].items():
            context.check(); require(source.getinfo(name).file_size == expected['bytes'], 'Beacon member size differs')
            raw = source.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Beacon member hash differs')
            if name == DATE:
                version, newest, crc = struct.unpack('<iII', raw)
                require(version == 9 and f'0x{crc:08x}' == value['native']['full_world_crc'],
                        'Beacon sidecar differs from the verified native loaded-world CRC')
            target = targets[name]
            if target.exists():
                regular(target, MAX_GRAPH)
                require(pin(target, context) == expected, 'An existing different beacon graph is preserved')
                target.chmod(0o400)
            else:
                atomic_bytes(target, raw); installed += 1
    record = {'format': 3, 'policy': POLICY, 'manifest_sha256': MANIFEST_SHA256,
              'server_geometry_profile': profile,
              'input_fingerprints': inputs,
              'graph_fingerprints': fingerprints(runtime, targets, context)}
    atomic_bytes(marker, canonical(record))
    return {'format': 3, 'status': 'installed_verified_graph', 'map': MAP, 'server_geometry_profile': profile,
            'full_world_crc': value['native']['full_world_crc'], 'installed_files': installed,
            'input_files_checked': len(inputs), 'input_payload_bytes_hashed': total,
            'archive_decoded': True, 'fingerprint_walk': True, 'input_inventory_walk': True,
            'native_graph_readback_qualified': True,
            'preparation_elapsed_seconds': round(time.monotonic() - started, 6)}
