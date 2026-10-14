#!/usr/bin/env python3
"""Prepare a complete disposable client using authenticated published guest code.

This is a host input producer. It opens no database and makes no character.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '3570430cefdb15d9b239563e85cccf4d8fe6f32e'
APK = {'bytes': 42076692, 'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
GAME_SHA = '5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b'
LAUNCHER_SHA = 'b453c42876408a842a4f3b717ef3857d4f10624f02462b6e1c6ce5bcdca92159'
MAX_MEMBERS, MAX_RUNTIME_LEAF = 512, 64 * 1024**2

def require(value, message):
    if not value: raise ValueError(message)

def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Regular profile input required: ' + str(path))
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''): h.update(block)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}

def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')

def prepare(args):
    output, payloads = args.output.absolute(), args.payloads.absolute()
    require(pin(args.donor_apk) == APK and not output.exists(), 'Exact audited .36 APK and fresh client fixture required')
    require(not any(p.is_symlink() for p in (output, *output.parents)), 'Linked host fixture output refused')
    output.mkdir(parents=True, mode=0o700)
    assets = output / 'assets'; assets.mkdir(mode=0o700)
    with zipfile.ZipFile(args.donor_apk) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate donor APK members')
        selected = [n for n in names if n.startswith('assets/runtime/')]
        require(0 < len(selected) <= MAX_MEMBERS and all(n.count('/') == 2 for n in selected), 'Flat bounded runtime closure required')
        for name in selected:
            entry = archive.getinfo(name)
            require(not entry.is_dir() and not entry.flag_bits & 1 and 0 < entry.file_size <= MAX_RUNTIME_LEAF,
                    'Invalid donor runtime member')
            (assets / Path(name).name).write_bytes(archive.read(entry))
    # This separate process imports the actual public APK's helpers first.
    sys.path.insert(0, str(assets))
    names = ('client_startup_diagnostic', 'character_avatar_assets', 'atlas_world_assets',
             'client_visual_assets', 'client_animation_package', 'zone_asset_package', 'texture_header_index')
    modules = {n: importlib.import_module(n) for n in names}
    require(all(Path(m.__file__).resolve().parent == assets for m in modules.values()), 'Client fixture imported non-APK guest code')
    sys.path.insert(1, str(ROOT / 'tools/android/interactive'))
    complete = importlib.import_module('qualify_full_startup_preflight')
    payload_pins = complete.leaf.validate_assets(payloads); complete.extra_inputs(payloads)
    for name in set(payload_pins) | {Path(n).name for n in complete.IMPORT_INPUTS}:
        target = assets / name
        if target.exists(): require(pin(target) == pin(payloads / name), 'External/APK asset collision differs')
        else: shutil.copyfile(payloads / name, target)
        target.chmod(0o444)
    client = modules['client_startup_diagnostic']
    hashes, data, imported = complete.verify_inputs_before_import(client, assets, payloads)
    context = complete.Context(); owned = output / 'owned'; owned.mkdir(mode=0o700)
    identity = client.import_identity(data)
    work, work_receipt = client.prepare_worktree(owned, data, assets, identity, context)
    require(work_receipt['reused'] is False and work_receipt['input_files'] == complete.COUNT, 'Complete actual cold client preparation required')
    context.report['client_worktree'] = work_receipt
    supplements = {}
    for name in ('character_avatar_assets', 'atlas_world_assets', 'client_visual_assets'):
        supplements[name] = modules[name].install(work, assets, context)
    supplements['client_animation_package'] = modules['client_animation_package'].install(
        assets / 'server-animations.pigg', assets / 'server-animation-manifest.json', work,
        assets=assets, context=context)
    supplements['zone_asset_package'] = modules['zone_asset_package'].install(work, assets, context)
    supplements['zone_audio_asset_package'] = modules['zone_asset_package'].install(work, assets, context, audio=True)
    require(pin(work / 'CityOfHeroes.exe')['sha256'] == GAME_SHA and pin(assets / 'client-launcher.exe')['sha256'] == LAUNCHER_SHA,
            'Retained real Game/launcher bytes differ')
    index, index_environment = modules['texture_header_index'].prepare(work, identity, GAME_SHA, context)
    require(index.get('native_file_opens_avoidable', 0) > 0 and index.get('original_texture_files_unchanged') is True,
            'Authenticated current texture header pack required')
    value = {'format': 1, 'role': 'complete_public_036_native_client_host_fixture', 'status': 'prepared',
        'donor_apk': APK, 'donor_source_commit': SOURCE, 'work': str(work), 'assets': str(assets),
        'game': pin(work / 'CityOfHeroes.exe'), 'launcher': pin(assets / 'client-launcher.exe'),
        'original_import': imported, 'actual_client_worktree': work_receipt, 'supplements': supplements,
        'texture_header_index': index, 'texture_header_environment': index_environment,
        'packaged_guest_sources': {p.name: pin(p) for p in sorted(assets.glob('*.py'))},
        'verified_assets': hashes, 'native_process_started': False, 'database_opened': False,
        'player_profile_used': False, 'physical_device_executed': False, 'source_script': pin(Path(__file__))}
    write(output / 'native-client-fixture.json', value)
    return value

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('donor-apk', 'payloads', 'output'): p.add_argument('--' + n, type=Path, required=True)
    value = prepare(p.parse_args())
    print(json.dumps({'status': value['status'], 'work': value['work'], 'scope': value['role']}))
