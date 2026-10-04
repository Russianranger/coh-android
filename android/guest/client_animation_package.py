#!/usr/bin/env python3
"""Expose the existing exact animation Pig to the unchanged graphical loader.

The original 5,878 loose tracks stay installed. The pack contains their original
bytes, so stock LOAD_ALL, validation, skeleton linking and last-frame calculation
remain in charge. A private link avoids duplicating the 88 MB runtime payload.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat
import tempfile
import time
import zipfile

import client_startup_diagnostic as client
import server_animation_package as animation

ROLE = 'exact_native_client_animation_storage'
MARKER = 'client-animation-link.json'
require = animation.require


def _regular_directory(path, owner=None):
    path = Path(path)
    require(os.path.lexists(path), 'Missing client animation directory: ' + str(path))
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and (owner is None or info.st_uid == owner),
            'Linked or foreign client animation directory: ' + str(path))
    return info.st_uid


def _directory_ancestors(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts,
            'Client animation path must be absolute and normalized')
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        _regular_directory(current)


def _regular(path, owner=None):
    path = Path(path)
    require(os.path.lexists(path), 'Missing client animation file: ' + str(path))
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and (owner is None or info.st_uid == owner),
            'Linked or foreign client animation file: ' + str(path))
    return info


def _check(context):
    if context is not None:
        context.check()


def client_contract(runtime, assets, document, *, context=None):
    """Bind real Game, its source receipts and loose imported animation paths."""
    runtime, assets = Path(runtime), Path(assets)
    require(runtime.is_absolute() and assets.is_absolute()
            and '..' not in runtime.parts and '..' not in assets.parts,
            'Client animation paths must be absolute and normalized')
    owner = _regular_directory(runtime)
    _regular_directory(assets)
    _directory_ancestors(runtime)
    _directory_ancestors(assets)
    _regular_directory(runtime / 'data', owner)
    _regular_directory(runtime / 'tools', owner)
    _regular(runtime / 'client-work.json', owner)
    saved = client.read_json(runtime / 'client-work.json')
    require(saved.get('format') == 1 and saved.get('worktree_key') == runtime.name
            and re.fullmatch(r'client-work-[0-9a-f]{24}', runtime.name)
            and saved.get('normalized_mtime_epoch') == client.CACHE_EPOCH,
            'Client animation worktree receipt differs')
    source = Path(saved.get('source_data', ''))
    require(source.is_absolute() and '..' not in source.parts,
            'Client animation source import path differs')
    _regular_directory(source, owner)
    _directory_ancestors(source)
    imported = client.import_identity(source)
    require(saved.get('import') == imported,
            'Client animation import generation differs')
    with zipfile.ZipFile(assets / 'client-runtime.zip') as archive:
        package = client.archive_manifest(archive, assets)
    require(document['identity']['source_commit'] == package['source_commit'] == client.SOURCE
            and document['identity']['data_commit'] == package['data_commit'] == client.DATA
            and document['identity']['asset_archive_sha256'] == client.ASSET_ARCHIVE_SHA,
            'Client animation source or original asset closure differs')
    require(saved.get('package_sha256') == client.base.file_hash(assets / 'client-runtime.zip')
            and saved.get('content_identity_sha256') == client.identity_sha256({
                'data': client.worktree_data_identity(saved),
                'native': client.native_closure_identity(package)}),
            'Client animation native/data content identity differs')
    executable = runtime / 'CityOfHeroes.exe'
    _regular(executable, owner)
    pin = package['files']['CityOfHeroes.exe']
    require(animation.file_pin(executable) == {'bytes': pin['size'], 'sha256': pin['sha256']},
            'Client animation actual Game identity differs')
    # The completed importer verified the original archive. Recheck every loose
    # animation's unchanged link, size, date and read-only source. The original
    # body hashes are independently checked by verify_package above.
    ancestors = set()
    for name, record in document['files'].items():
        _check(context)
        logical = Path(name)
        for base in (source, runtime / 'data'):
            parent = base
            for component in logical.parts[:-1]:
                parent /= component
                if parent not in ancestors:
                    _regular_directory(parent, owner)
                    ancestors.add(parent)
        original, loose = source / logical, runtime / 'data' / logical
        info = _regular(original, owner)
        require(not info.st_mode & 0o222 and info.st_size == record['bytes']
                and int(info.st_mtime) == record['timestamp']
                and loose.is_symlink() and loose.lstat().st_uid == owner
                and loose.resolve(strict=True) == original,
                'Client loose animation binding differs: ' + name)
    return {'format': 1, 'role': ROLE, 'runtime': str(runtime),
            'source_data': str(source), 'import': imported,
            'game_sha256': pin['sha256'],
            'source_commit': package['source_commit'], 'data_commit': package['data_commit'],
            'asset_archive_sha256': client.ASSET_ARCHIVE_SHA,
            'animation_inventory_sha256': document['identity']['animation_inventory_sha256'],
            'loose_animation_count': len(document['files'])}


def install(pigg, manifest, runtime, *, assets, context=None):
    """Install/rebind one owned link; never copy or change original animations."""
    started = time.monotonic()
    pigg, manifest, runtime, assets = map(Path, (pigg, manifest, runtime, assets))
    require(pigg == assets / animation.PIGG and manifest == assets / animation.MANIFEST,
            'Client animation resources must use the verified runtime asset paths')
    if not os.path.lexists(pigg) and not os.path.lexists(manifest):
        # Do not silently retain an old packed override when the optional input
        # has disappeared. Existing links require explicit compatible inputs.
        require(not os.path.lexists(runtime / 'piggs'),
                'Client animation input disappeared with a packed override present')
        return {'format': 1, 'installed': False,
                'fallback': 'ordinary_loose_animation_loader'}
    owner = _regular_directory(runtime)
    _directory_ancestors(assets)
    _regular(pigg, owner)
    _regular(manifest, owner)
    manifest_before = animation.file_pin(manifest)
    document = animation.verify_package(pigg, manifest, context=context)
    proof = client_contract(runtime, assets, document, context=context)
    # Setup extracts regular resources as 0644. Restrict only these two proved
    # animation inputs before exposing the link; preserve their original bytes.
    for path, expected_pin in ((pigg, {key: document['pigg'][key] for key in ('bytes', 'sha256')}),
                               (manifest, manifest_before)):
        _regular(path, owner)
        require(animation.file_pin(path) == expected_pin, 'Client animation resource changed during verification')
        path.chmod(0o400)
        info = _regular(path, owner)
        require(not info.st_mode & 0o222 and animation.file_pin(path) == expected_pin,
                'Client animation resource read-only protection differs')
    directory = runtime / 'piggs'
    if not os.path.lexists(directory):
        directory.mkdir(mode=0o700)
    _regular_directory(directory, owner)
    require(set(path.name for path in directory.iterdir()) <= {animation.PIGG, MARKER},
            'Foreign client animation Pig directory content')
    target, marker = directory / animation.PIGG, directory / MARKER
    expected = {'format': 1, 'role': ROLE, 'runtime': str(runtime),
                'source_data': proof['source_data'], 'import': proof['import'],
                'pigg': document['pigg'], 'target': str(pigg)}
    exists = os.path.lexists(target)
    prior = None
    if os.path.lexists(marker):
        _regular(marker, owner)
        prior = client.read_json(marker)
        require(isinstance(prior, dict) and set(prior) == set(expected)
                and all(prior[key] == expected[key] for key in expected if key != 'target')
                and isinstance(prior['target'], str)
                and Path(prior['target']).is_absolute()
                and '..' not in Path(prior['target']).parts
                and Path(prior['target']).name == animation.PIGG,
                'Client animation ownership receipt differs')
    if exists:
        require(prior is not None and target.is_symlink()
                and target.lstat().st_uid == owner
                and os.readlink(target) in (prior['target'], str(pigg)),
                'Foreign or unreceipted client animation Pig link')
        previous_resource = Path(prior['target'])
        if previous_resource != pigg and os.path.lexists(previous_resource):
            _directory_ancestors(previous_resource.parent)
            _regular(previous_resource, owner)
            require(animation.file_pin(previous_resource) == {
                key: document['pigg'][key] for key in ('bytes', 'sha256')},
                'Previous client animation resource differs')
        if os.readlink(target) == str(pigg) and prior == expected:
            return {'format': 1, 'installed': True, 'reused': True,
                    'pigg': document['pigg'], 'client_contract': proof,
                    'storage': 'owned_link_to_verified_runtime_payload',
                    'verified_payload_read_only': True,
                    'additional_animation_payload_bytes': 0,
                    'loose_inputs_preserved': True, 'native_animation_reader_changed': False,
                    'physical_startup_timing_validated': False,
                    'elapsed_seconds': round(time.monotonic() - started, 3)}
    _check(context)
    # Temporary outputs live outside piggs. An interrupted publication cannot
    # leave a foreign-looking temporary Pig that blocks ordinary resumption.
    descriptor, pending_marker = tempfile.mkstemp(prefix='client-animation-receipt-', dir=runtime)
    pending_link = runtime / ('client-animation-link-' + client.base.secrets.token_hex(8))
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(animation.canonical(expected)); output.flush(); os.fsync(output.fileno())
        os.chmod(pending_marker, 0o600)
        if exists:
            pending_link.symlink_to(pigg)
        _check(context)
        # Marker first on initial install: a missing link is safely repairable.
        # Link first on rebind: the old marker plus the verified new resource
        # proves an interrupted rebind without accepting any arbitrary target.
        if exists:
            os.replace(pending_link, target)
            os.replace(pending_marker, marker)
        else:
            os.replace(pending_marker, marker)
            # symlink creation is atomic and refuses an existing destination.
            target.symlink_to(pigg)
    finally:
        if os.path.lexists(pending_marker): os.unlink(pending_marker)
        if os.path.lexists(pending_link): os.unlink(pending_link)
    require(target.is_symlink() and target.resolve(strict=True) == pigg
            and client.read_json(marker) == expected,
            'Client animation link publication differs')
    return {'format': 1, 'installed': True, 'reused': False,
            'pigg': document['pigg'], 'client_contract': proof,
            'storage': 'owned_link_to_verified_runtime_payload',
            'verified_payload_read_only': True,
            'additional_animation_payload_bytes': 0,
            'loose_inputs_preserved': True, 'native_animation_reader_changed': False,
            'physical_startup_timing_validated': False,
            'elapsed_seconds': round(time.monotonic() - started, 3)}
