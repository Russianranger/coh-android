"""Missing-only all-zone client resources and the separate finite Map 5 overlay.

APK client-manifest pins own the imported archive identity. Atlas retains its
original collision inventory; only the client receives the complete supplement.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import stat
import tempfile
import time
import zipfile

import atlas_world_assets as world
import client_startup_diagnostic as client

require = client.require
ARCHIVE = 'zones-world-supplement.zip'
MANIFEST = 'zones-world-supplement-manifest.json'
SCOPE = 'coh_all_zones_original_asset_supplement_v1'
VERSION = '1.0.0'
MAX_ARCHIVE = 1900 * 1024**2
MAX_MANIFEST = 128 * 1024**2
MAX_FILES = 30000
MAX_ENTRY = 32 * 1024**2
MAX_PAYLOAD = 4 * 1024**3
MAX_RECEIPT = 16 * 1024**2
_PACKAGES = {}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def safe_payload(name):
    if not isinstance(name, str) or not name.isascii() or name != name.casefold():
        return False
    path = PurePosixPath(name)
    return (path.as_posix() == name and not path.is_absolute() and '\\' not in name and ':' not in name
        and all(part not in ('', '.', '..') for part in name.split('/'))
        and (name.startswith(('data/object_library/', 'data/player_library/')) and path.suffix == '.geo'
             or name.startswith('data/texture_library/') and path.suffix == '.texture'
             or name.startswith('data/sound/ogg/') and path.suffix == '.ogg'))


def source_state(path, limit):
    info = Path(path).lstat()
    # Android's immutable content store intentionally shares archive hard links.
    # Symlinks remain forbidden; trusted APK hashes, ownership and unchanged inode
    # fingerprints authorize input reads. Installed output files remain single-link.
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
            and 0 < info.st_size <= limit and info.st_nlink >= 1,
            'Linked, foreign or oversized zone package input')
    return list(client.asset_fingerprint(path))


def present(assets):
    found = {name for name in (ARCHIVE, MANIFEST) if os.path.lexists(Path(assets) / name)}
    require(not found or found == {ARCHIVE, MANIFEST}, 'Incomplete all-zone asset package')
    return bool(found)


def package(assets):
    assets = Path(assets)
    owner = json.loads(world.read_regular(assets / 'client-manifest.json', 2 * 1024**2))
    require(owner.get('format') == 1 and owner.get('scope') == client.SCOPE,
            'Zone package lacks the APK client inventory')
    pins = {name: owner.get('files', {}).get(name) for name in (ARCHIVE, MANIFEST)}
    require(all(isinstance(pin, dict) and type(pin.get('bytes')) is int and pin['bytes'] > 0
                and re.fullmatch('[0-9a-f]{64}', str(pin.get('sha256'))) for pin in pins.values()),
            'Zone package lacks exact APK payload pins')
    state = {name: source_state(assets / name, MAX_ARCHIVE if name == ARCHIVE else MAX_MANIFEST)
             for name in pins}
    key = (str(assets), hashlib.sha256(canonical([pins, state])).hexdigest())
    if key in _PACKAGES:
        return _PACKAGES[key]
    raw = (assets / MANIFEST).read_bytes()
    require(len(raw) == pins[MANIFEST]['bytes'] and hashlib.sha256(raw).hexdigest() == pins[MANIFEST]['sha256'],
            'Zone manifest differs from the APK pin')
    value = json.loads(raw)
    files = value.get('files', {})
    collision = value.get('kings_row_collision_files', {})
    require(value.get('format') == 1 and value.get('scope') == SCOPE and value.get('version') == VERSION
            and value.get('source_commit') == client.SOURCE and value.get('data_commit') == client.DATA
            and value.get('missing_only') is True and value.get('retained_resources_preserved') is True
            and value.get('original_payloads_verified') is True
            and value.get('donor_generated_caches_installed') is False
            and value.get('archive') == {'filename': ARCHIVE, **pins[ARCHIVE]}
            and isinstance(files, dict) and 0 < len(files) == value.get('file_count') <= MAX_FILES
            and all(safe_payload(name) and isinstance(pin, dict) and set(pin) == {'bytes', 'sha256'}
                    and type(pin['bytes']) is int and 0 < pin['bytes'] <= MAX_ENTRY
                    and re.fullmatch('[0-9a-f]{64}', str(pin['sha256'])) for name, pin in files.items())
            and sum(pin['bytes'] for pin in files.values()) == value.get('payload_bytes') <= MAX_PAYLOAD
            and hashlib.sha256(canonical(files)).hexdigest() == value.get('files_sha256'),
            'Zone manifest provenance, inventory or limits differ')
    require(isinstance(collision, dict) and len(collision) == 52 and set(collision) <= set(files)
            and all(name.startswith('data/object_library/') and name.endswith('.geo')
                    and files[name] == pin for name, pin in collision.items())
            and hashlib.sha256(canonical(collision)).hexdigest() == value.get('kings_row_collision_files_sha256')
            and value.get('kings_row_source_world_graph_complete') is True,
            'Kings Row required original geometry is incomplete')
    require(state == {name: source_state(assets / name, MAX_ARCHIVE if name == ARCHIVE else MAX_MANIFEST)
                      for name in pins}, 'Zone package changed while reading metadata')
    # Large original range provenance is for the publication audit, not retained
    # in the game process after this pinned metadata has been validated.
    result = {key: value[key] for key in ('version', 'files', 'files_sha256', 'file_count', 'payload_bytes',
        'kings_row_collision_files', 'kings_row_collision_files_sha256')}
    result.update(pins=pins, inputs=state)
    _PACKAGES.clear()
    _PACKAGES[key] = result
    return result


def install(worktree, assets, context, *, collision_only=False):
    started = time.monotonic()
    worktree, assets = Path(worktree), Path(assets)
    world.real_directory(worktree); world.real_directory(worktree / 'data')
    document = package(assets)
    files = document['kings_row_collision_files'] if collision_only else document['files']
    marker = worktree / ('kings-row-geometry-installed.json' if collision_only else 'zones-world-installed.json')
    identity = {'format': 1, 'version': VERSION, 'manifest': document['pins'][MANIFEST],
        'selection': 'kings_row_required_collision' if collision_only else 'all_zone_client_resources',
        'files_sha256': hashlib.sha256(canonical(files)).hexdigest(),
        'root': [[path.stat().st_dev, path.stat().st_ino] for path in (worktree, worktree / 'data')]}
    targets = world.resolve_targets(worktree, files, context)
    before = world.output_state(worktree, targets, files, context)
    saved = None
    if os.path.lexists(marker):
        try:
            saved = json.loads(world.read_regular(marker, MAX_RECEIPT, installed=True))
        except (ValueError, UnicodeError):
            pass
    reused = all(row['stat'] is not None for row in before.values()) and saved == {
        'identity': identity, 'inputs': document['inputs'], 'outputs': before}
    installed = decoded = 0
    if not reused:
        for name, target in targets.items():
            context.check()
            world.verify_target(target, files[name], context)
        descriptor = os.open(assets / ARCHIVE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            require(list((os.fstat(descriptor).st_dev, os.fstat(descriptor).st_ino)) == document['inputs'][ARCHIVE][:2],
                    'Zone archive opened inode differs')
            with os.fdopen(descriptor, 'rb', closefd=False) as source:
                if not client.verified_asset_matches(assets / ARCHIVE, document['pins'][ARCHIVE]):
                    size, digest = world.hash_stream(source, context, MAX_ARCHIVE)
                    require({'bytes': size, 'sha256': digest} == document['pins'][ARCHIVE], 'Zone archive pin differs')
                    source.seek(0)
                with zipfile.ZipFile(source) as archive:
                    entries = archive.infolist()
                    require(len(entries) == len({e.filename for e in entries}) == len(document['files'])
                            and {e.filename for e in entries} == set(document['files']), 'Zone ZIP inventory differs')
                    for entry in entries:
                        require(stat.S_ISREG(entry.external_attr >> 16) and not entry.is_dir()
                                and not entry.flag_bits & 1 and entry.file_size == document['files'][entry.filename]['bytes']
                                and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'Invalid zone ZIP entry')
                    for name, target in targets.items():
                        context.check()
                        if before[name]['stat'] is not None:
                            continue
                        target.parent.mkdir(parents=True, exist_ok=True); world.real_directory(target.parent)
                        fd, temporary_name = tempfile.mkstemp(prefix='.zone-asset-', dir=target.parent)
                        temporary = Path(temporary_name)
                        try:
                            with os.fdopen(fd, 'wb') as output:
                                world.extract_payload(archive, name, files[name], output, context)
                                output.flush(); os.fsync(output.fileno())
                            temporary.chmod(0o444); os.utime(temporary, (client.CACHE_EPOCH, client.CACHE_EPOCH))
                            world.real_directory(target.parent)
                            client.publish_new_regular_file(temporary, target)
                            installed += 1; decoded += files[name]['bytes']
                        finally:
                            temporary.unlink(missing_ok=True)
        finally:
            os.close(descriptor)
    require(document['inputs'] == {name: source_state(assets / name, MAX_ARCHIVE if name == ARCHIVE else MAX_MANIFEST)
                                  for name in (ARCHIVE, MANIFEST)}, 'Zone package changed during installation')
    after = world.output_state(worktree, targets, files, context)
    require(all(row['stat'] is not None for row in after.values()) and all(before[name]['stat'] is None
            or after[name] == before[name] for name in files), 'Zone output changed or disappeared')
    if not reused:
        previous = world.file_state(marker, MAX_RECEIPT, installed=True) if os.path.lexists(marker) else None
        fd, name = tempfile.mkstemp(prefix='.zone-receipt-', dir=worktree)
        temporary = Path(name)
        try:
            raw = canonical({'identity': identity, 'inputs': document['inputs'], 'outputs': after})
            require(len(raw) <= MAX_RECEIPT, 'Zone receipt exceeds bound')
            with os.fdopen(fd, 'wb') as output:
                output.write(raw); output.flush(); os.fsync(output.fileno())
            temporary.chmod(0o444); os.utime(temporary, (client.CACHE_EPOCH, client.CACHE_EPOCH))
            if previous is None:
                client.publish_new_regular_file(temporary, marker)
            else:
                require(world.file_state(marker, MAX_RECEIPT, installed=True) == previous, 'Zone receipt changed')
                os.replace(temporary, marker)
        finally:
            temporary.unlink(missing_ok=True)
    return {'format': 1, 'version': VERSION, 'scope': identity['selection'], 'file_count': len(files),
        'files_sha256': identity['files_sha256'], 'manifest_sha256': document['pins'][MANIFEST]['sha256'],
        'installed_files': installed, 'decoded_payload_bytes': decoded, 'fingerprint_reused': reused,
        'imported_files_modified': False, 'prepared_caches_modified': False,
        'runtime_visual_validated': False, 'physical_zoning_verified': False,
        'elapsed_seconds': round(time.monotonic() - started, 6)}
