#!/usr/bin/env python3
"""Add the ARM64 option to extracted app assets; never builds/signs an APK."""
import argparse
import ast
import json
from pathlib import Path
import re
import shutil
import tempfile

import armport_client_package as package

ROOT = Path(__file__).resolve().parents[2]
# Current creation/reopen helpers need these dependencies even with the
# retained stock x86 client/server packages. Optional visual/zone payloads
# remain selected by the donor inventory; adding just their helper would
# falsely advertise an incomplete asset bundle.
GUEST_DEPENDENCIES = (
    'client_attempt_retry.py', 'character_session_budget.py',
    'character_server_data_cache.py', 'texture_header_index.py',
    'native_responsiveness_contract.py', 'client_gpu_profile.py',
    'server_cache_package.py', 'server_message_cache_format.py', 'server_fx_catalog.py',
    'native_character_events.py', 'native_training_save.py',
    'stationary_contact_evidence.py', 'task_gate_evidence.py',
    # LocalCharacterServer imports this to check archive/manifest presence.
    # The helper alone does not activate zones or audio; both payloads must exist.
    'zone_asset_package.py',
    # The server's immutable input-copy budgets import these constants even
    # when the retained donor has no optional client visual payload.
    'client_visual_assets.py',
    # Cache ancestry validation imports these before rejecting unsupported
    # producers and taking its existing original-loader fallback.
    'native_monorail_contract.py', 'native_map_startup_contract.py',
)

WORLD_PINS = frozenset(('MANIFEST_SHA256', 'ARCHIVE_SHA256', 'ARCHIVE_BYTES',
                        'PAYLOAD_BYTES', 'FILE_COUNT', 'FILES_SHA256'))


def world_pin_values(raw):
    """Read constants without executing a retained helper."""
    result = {}
    assignments = []
    for node in ast.parse(raw).body:
        if not isinstance(node, ast.Assign):
            continue
        names = [n.id for target in node.targets for n in ast.walk(target)
                 if isinstance(n, ast.Name)]
        if not WORLD_PINS.intersection(names):
            continue
        package.require(len(node.targets) == 1 and set(names) <= WORLD_PINS,
                        'Mixed world pin assignment')
        value = ast.literal_eval(node.value)
        values = value if isinstance(node.targets[0], (ast.Tuple, ast.List)) else [value]
        package.require(len(names) == len(values), 'Malformed world pins')
        for name, value in zip(names, values):
            valid = (type(value) is int and value > 0 if name.endswith('BYTES') or name == 'FILE_COUNT'
                     else isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value))
            package.require(name not in result and valid, 'Invalid world pin: ' + name)
            result[name] = value
        assignments.append((node, names))
    package.require(set(result) == WORLD_PINS, 'Incomplete world pins')
    return result, assignments


def bind_world_helper(current, donor):
    """Keep current validation code, bound to the authenticated donor payload.

    The retained 0.10 world predates the current 27-texture extension. Copying
    today's hardcoded constants alongside that old archive rejects valid donor
    bytes. Only the six immutable data constants are transplanted; no checks or
    bounds are removed and no code from the donor is executed.
    """
    pins, _ = world_pin_values(donor)
    _, assignments = world_pin_values(current)
    lines = current.splitlines(keepends=True)
    for node, names in reversed(assignments):
        lines[node.lineno - 1:node.end_lineno] = [
            ', '.join(names) + ' = ' + ', '.join(repr(pins[n]) for n in names) + '\n']
    bound = ''.join(lines)
    package.require(world_pin_values(bound)[0] == pins, 'World pin binding failed')
    return bound


def pin(path):
    return {'bytes': path.stat().st_size, 'sha256': package.digest(path)}


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def stage(source, armport, output, repository_commit):
    package.require(re.fullmatch('[0-9a-f]{40}', repository_commit), 'Exact repository commit required')
    package.require(not output.exists(), 'Fresh app asset output required')
    runtime = json.loads((source / 'runtime-manifest.json').read_text())
    client = json.loads((source / 'client-manifest.json').read_text())
    package.require(runtime.get('format') == client.get('format') == 1
                    and client.get('scope') == 'actual_client_startup_guest', 'Existing client manifest required')
    for name, expected in runtime['files'].items():
        package.require(re.fullmatch('[A-Za-z0-9_.-]+', name) and name not in ('.', '..'), 'Unsafe app payload')
        path = source / name
        package.require(path.is_file() and not path.is_symlink()
                        and pin(path) == expected, 'Donor app payload differs: ' + name)
    package.require(all(runtime['files'].get(name) == expected for name, expected in client['files'].items()),
                    'Inner/outer app inventories disagree')
    with tempfile.TemporaryDirectory(prefix='armport-package-check-') as temporary:
        document = package.unpack(armport, Path(temporary) / 'client')
    replacements = {'armport-client.zip': armport,
                    'armport_client_package.py': Path(__file__).with_name('armport_client_package.py'),
                    'armport_interactive.py': Path(__file__).with_name('armport_interactive.py'),
                    'client_stdio.py': Path(__file__).with_name('client_stdio.py'),
                    'character_creation_diagnostic.py': ROOT / 'android/guest/character_creation_diagnostic.py'}
    for name in set(client['files']) | set(GUEST_DEPENDENCIES):
        source_helper = ROOT / 'android/guest' / name
        if name.endswith('.py') and source_helper.is_file():
            replacements[name] = source_helper
    output.mkdir(parents=True)
    # Ordinary copies keep the retained donor independent of future edits.
    for name in runtime['files']:
        if name not in replacements and name != 'client-manifest.json':
            shutil.copyfile(source / name, output / name)
    for name, path in replacements.items():
        if name == 'atlas_world_assets.py':
            # source was authenticated against both inventories above.
            (output / name).write_text(bind_world_helper(path.read_text(), (source / name).read_text()))
        else:
            shutil.copyfile(path, output / name)
        record = pin(output / name)
        runtime['files'][name] = client['files'][name] = record
    package.require(len(client['files']) <= 96, 'Existing client inventory bound exceeded')
    (output / 'client-manifest.json').write_bytes(encoded(client))
    runtime['files']['client-manifest.json'] = pin(output / 'client-manifest.json')
    runtime['repository_commit'] = repository_commit
    runtime['armport_client'] = {'archive_sha256': package.digest(armport),
        'executable_sha256': document['files']['CityOfHeroes.exe']['sha256'],
        'client_run_id': document['client_run_id'], 'data_run_id': document['data_run_id'],
        'machine': 'ARM64', 'default_architecture': 'x86'}
    (output / 'runtime-manifest.json').write_bytes(encoded(runtime))
    return runtime['armport_client']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'armport', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    print(json.dumps(stage(**vars(parser.parse_args()))))


if __name__ == '__main__':
    main()
