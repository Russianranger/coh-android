#!/usr/bin/env python3
"""Prepare graphical character creation with accepted client and server donors."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import sys
import zipfile
# The accepted helpers use their own sibling imports. Keep those imports local
# to initialization; their path changes must not redirect interactive discovery.
_import_path = sys.path[:]
try:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'client'))
    import package_client_runtime as client_package
    import prepare_client_caches as cache_package
    import prepare_client_prerequisites as prerequisite_package
finally:
    sys.path[:] = _import_path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME_RUN_ID = 36364550345
RUNTIME_COMMIT = '9dc58f62c58dc4fc5c01288071429bf2aa06d2f4'
RUNTIME_MANIFEST_SHA256 = 'fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203'
BASE_MANIFEST = 'accepted-runtime-manifest.json'
PROBE_MANIFEST = 'client-manifest.json'
GUEST_SCRIPTS = ('character_avatar_assets.py', 'character_creation_diagnostic.py', 'local_character_server.py', 'client_login_diagnostic.py', 'local_login_server.py', 'diagnostic.py', 'presentation_diagnostic.py', 'client_startup_diagnostic.py', 'client_interactive_diagnostic.py', 'dbserver_diagnostic.py',
                 'game_diagnostic.py', 'game_device_diagnostic.py', 'game_evidence.py',
                 'game_hang_evidence.py', 'game_map_progress.py')
SERVER_ARCHIVES = frozenset(('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'))
MAPSERVER_PROFILE = 'dispatch_progress_v1'
ATLAS_RECEIPT = ROOT/'docs/android-evidence/atlas-test-apk-build-36638344040.json'
ATLAS_RECEIPT_SHA256 = '39f4e75aa947d5519e42d176d756c317adae21ed18ea03fcdeb155b6bb7535ea'
AVATAR_FILES = frozenset(('character-avatar-defaults.zip', 'character-avatar-defaults-manifest.json'))
PROBE_FILES = frozenset((*AVATAR_FILES, *SERVER_ARCHIVES, *GUEST_SCRIPTS, 'runtime-lock.json', 'runtime-probe.exe', 'probe.dll',
                         '001-coh-compat.sql', 'psqlodbc_x86.msi',
                         'client-launcher.exe', 'client-runtime.zip', 'client-caches.zip', 'client-prerequisites.zip'))
EXTRA_FILES = frozenset({*AVATAR_FILES, *SERVER_ARCHIVES, BASE_MANIFEST, PROBE_MANIFEST, 'client-launcher.exe', 'client-runtime.zip', 'client-caches.zip', 'client-prerequisites.zip', *GUEST_SCRIPTS} - {'diagnostic.py'})
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\Z')
MAX_FILE_BYTES = 256 * 1024 * 1024


def avatar_tools():
    name = 'coh_character_avatar_package'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name('prepare_character_avatar_assets.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
    return sys.modules[name]


def server_tools():
    """Load accepted helpers without borrowing another prepare_assets module.

    Existing command-line tools share that name. Preserve the caller's aliases
    and search path so importing the login packager cannot redirect them.
    """
    name = 'coh_login_accepted_dbserver_assets'
    if name in sys.modules:
        return sys.modules[name]
    aliases = ('prepare_assets', 'host_dbserver_smoke')
    previous = {key: sys.modules.get(key) for key in aliases}
    search_path = sys.path[:]
    def load(module_name, path):
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    try:
        load('prepare_assets', ROOT/'tools/android/prepare_assets.py')
        load('host_dbserver_smoke', ROOT/'tools/android/dbserver/host_dbserver_smoke.py')
        return load(name, ROOT/'tools/android/dbserver/prepare_device_assets.py')
    except BaseException:
        sys.modules.pop(name, None)
        raise
    finally:
        sys.path[:] = search_path
        for key, value in previous.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value



def mapserver_tools():
    """Load the accepted composite verifier with its original sibling imports."""
    name = 'coh_character_accepted_atlas_assets'
    if name in sys.modules:
        return sys.modules[name]
    aliases = ('prepare_assets', 'host_dbserver_smoke', 'host_game_smoke')
    previous = {key: sys.modules.get(key) for key in aliases}
    search_path = sys.path[:]
    def load(module_name, path):
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    try:
        sys.path.insert(0, str(ROOT/'tools/android/game'))
        load('prepare_assets', ROOT/'tools/android/prepare_assets.py')
        load('host_dbserver_smoke', ROOT/'tools/android/dbserver/host_dbserver_smoke.py')
        load('host_game_smoke', ROOT/'tools/android/game/host_game_smoke.py')
        # The verifier imports these lazily. Resolve their exact siblings while
        # its private search path is active, then restore the caller's path.
        import package_loopback_game
        import package_mapserver_progress
        return load(name, ROOT/'tools/android/atlasgame/prepare_device_assets.py')
    except BaseException:
        sys.modules.pop(name, None)
        raise
    finally:
        sys.path[:] = search_path
        for key, value in previous.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


def accepted_mapserver_receipt():
    require(digest(ATLAS_RECEIPT) == ATLAS_RECEIPT_SHA256, 'Accepted Atlas build receipt differs')
    receipt = read_json(ATLAS_RECEIPT)
    require(receipt.get('repository_commit') == 'e30c0b58b0e53534f92e77cdb7b8b93fe3ddc5ce',
            'Accepted Atlas source identity differs')
    return receipt


def mapserver_contract():
    accepted = mapserver_tools().bundle_contract(MAPSERVER_PROFILE)
    keys = ('package_run_id', 'package_repository_commit', 'package_manifest_sha256',
            'package_archive', 'mapserver_progress_profile', 'mapserver_progress_producer',
            'dbserver_profile', 'game_listener_profile')
    return {key: accepted[key] for key in keys} | {
        'archive_pin': accepted_mapserver_receipt()['payloads']['assets/runtime/game-package.tar.gz'],
        'apk_donor_run_id': 36638344040,
        'apk_donor_sha256': accepted_mapserver_receipt()['sha256']}


def verify_mapserver_package(package):
    """Verify the selected MapServer and every unchanged supporting dependency."""
    accepted = mapserver_tools()
    accepted.accepted_evidence(MAPSERVER_PROFILE)
    contract = mapserver_contract()
    package = Path(package)
    require(digest(package/'game-package.json') == contract['package_manifest_sha256'],
            'Requires the exact accepted MapServer composite manifest')
    manifest = accepted.game.verify_package(package, dbserver_profile='loopback',
        game_listener_profile='loopback', mapserver_progress_profile=MAPSERVER_PROFILE)
    require(manifest.get('repository_commit') == contract['package_repository_commit'],
            'Accepted MapServer composite commit differs')
    accepted.verify_progress_identity(manifest, contract)
    return manifest


def extract_mapserver_archive(archive, output):
    archive, output = Path(archive), Path(output)
    require(archive.is_file() and not archive.is_symlink()
            and file_pin(archive) == mapserver_contract()['archive_pin'],
            'Accepted MapServer archive bytes differ')
    server_tools().extract_archive(archive, output)
    return verify_mapserver_package(output)


def recover_mapserver_archive(apk, output):
    """Copy the accepted compressed bytes; do not rebuild its composite package."""
    apk, output = Path(apk), Path(output)
    receipt = accepted_mapserver_receipt()
    require(apk.is_file() and not apk.is_symlink()
            and file_pin(apk) == {'bytes': receipt['bytes'], 'sha256': receipt['sha256']},
            'Accepted Atlas APK bytes differ')
    require(not output.exists() and not output.is_symlink(), 'Use a fresh MapServer archive output')
    with zipfile.ZipFile(apk) as donor:
        names = donor.namelist()
        require(len(names) == len(set(names)), 'Duplicate accepted Atlas APK member')
        member = 'assets/runtime/game-package.tar.gz'
        require(donor.getinfo(member).file_size == mapserver_contract()['archive_pin']['bytes'],
                'Accepted MapServer archive size differs')
        with donor.open(member) as source, output.open('xb') as target:
            shutil.copyfileobj(source, target, 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix='coh-mapserver-donor-') as temporary:
        extract_mapserver_archive(output, Path(temporary)/'package')
    return mapserver_contract()


def local_server_contract():
    accepted = server_tools().bundle_contract()
    return {key: value for key, value in accepted.items()
            if key not in ('format', 'guest_script', 'android_execution_validated', 'gameplay_validated')} | {
                'variant': 'normal', 'persistent_profile': 'android-local-login',
                'mapserver_included': True, 'mapserver': mapserver_contract()}


def verify_local_server_inputs(package, schema):
    accepted = server_tools()
    accepted.accepted_evidence()
    return accepted.verify_input_payloads(Path(package), Path(schema))


def extract_local_server_inputs(assets, output):
    """Inspect only the exact accepted archives packaged alongside the client."""
    assets, output = Path(assets), Path(output)
    require(not output.exists() and not output.is_symlink(), 'Use a fresh server inputs output directory')
    accepted = server_tools()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.login-server-inputs-', dir=output.parent) as temporary:
        staging = Path(temporary)/'inputs'; staging.mkdir()
        accepted.extract_archive(assets/'dbserver-package.tar.gz', staging/'package')
        accepted.extract_archive(assets/'dbserver-schema.tar.gz', staging/'schema')
        verify_local_server_inputs(staging/'package', staging/'schema')
        extract_mapserver_archive(assets/'game-package.tar.gz', staging/'game-package')
        staging.rename(output)
    return {'package': output/'package', 'schema': output/'schema', 'game_package': output/'game-package'}


def require(value, message):
    if not value: raise ValueError(message)


def exact(left, right):
    return type(left) is type(right) and json.dumps(left, sort_keys=True, separators=(',', ':')) == json.dumps(right, sort_keys=True, separators=(',', ':'))


def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def file_pin(path):
    return {'bytes': Path(path).stat().st_size, 'sha256': digest(path)}


def read_json(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 8*1024*1024,
            'Missing, linked or oversized metadata: ' + path.name)
    return json.loads(path.read_text())


def verify_inventory(directory, files, *, excluded=()):
    require(isinstance(files, dict) and 0 < len(files) <= 40, 'Invalid runtime inventory')
    require(directory.is_dir() and not directory.is_symlink(), 'Runtime directory must be regular')
    require({path.name for path in directory.iterdir()} == set(files) | set(excluded), 'Runtime file set differs')
    for name, pin in files.items():
        require(isinstance(name, str) and NAME.fullmatch(name) and name != 'runtime-manifest.json', 'Unsafe runtime filename')
        require(isinstance(pin, dict) and set(pin) == {'bytes', 'sha256'} and type(pin['bytes']) is int
                and 0 < pin['bytes'] <= MAX_FILE_BYTES and isinstance(pin['sha256'], str)
                and HEX64.fullmatch(pin['sha256']), 'Invalid runtime pin: ' + name)
        path = directory / name
        require(path.is_file() and not path.is_symlink() and file_pin(path) == pin, 'Runtime payload differs: ' + name)


def verify_base(assets):
    manifest = read_json(assets / 'runtime-manifest.json')
    require(digest(assets / 'runtime-manifest.json') == RUNTIME_MANIFEST_SHA256,
            'Requires the exact accepted M2 runtime manifest')
    require(manifest.get('repository_commit') == RUNTIME_COMMIT and manifest.get('format') == 1
            and len(manifest.get('files', {})) == 12, 'Accepted M2 identity differs')
    verify_inventory(assets, manifest['files'], excluded=('runtime-manifest.json',))
    return manifest


def pe32(path):
    with path.open('rb') as stream:
        header = stream.read(64)
        require(len(header) == 64 and header[:2] == b'MZ', 'Probe is not PE32')
        offset = struct.unpack_from('<I', header, 60)[0]
        require(64 <= offset <= path.stat().st_size - 26, 'Invalid PE header offset')
        stream.seek(offset); pe = stream.read(26)
    require(pe[:4] == b'PE\0\0' and struct.unpack_from('<H', pe, 4)[0] == 0x14c
            and struct.unpack_from('<H', pe, 24)[0] == 0x10b, 'Probe must be i686 PE32')


def bundle_contract():
    return {'format':1,'scope':'actual_character_creation_guest','guest_script':'character_creation_diagnostic.py',
            'executable':'CityOfHeroes.exe','reference_run_id':36088012664,
            'width':800,'height':600,'transport':'private_unix_rfb',
            'server_packages_included':True,'local_server':local_server_contract(),'game_assets_external':True,
            'avatar_supplement':avatar_tools().bundle_contract(),
            'android_execution_validated':False,'gameplay_validated':False}


def base_contract(base):
    return {'run_id': RUNTIME_RUN_ID, 'repository_commit': RUNTIME_COMMIT,
            'manifest_file': BASE_MANIFEST, 'manifest_sha256': RUNTIME_MANIFEST_SHA256,
            'manifest': base}


def verify_device_assets(assets, *, repository_commit=None):
    assets = Path(assets)
    manifest, base = read_json(assets/'runtime-manifest.json'), read_json(assets/BASE_MANIFEST)
    require(digest(assets/BASE_MANIFEST) == RUNTIME_MANIFEST_SHA256
            and base.get('repository_commit') == RUNTIME_COMMIT and len(base.get('files', {})) == 12,
            'Accepted runtime identity differs')
    require(isinstance(manifest.get('repository_commit'), str) and HEX40.fullmatch(manifest['repository_commit'])
            and (repository_commit is None or manifest['repository_commit'] == repository_commit),
            'Candidate source commit differs')
    require(set(manifest) == set(base) | {'accepted_base_runtime', 'client_bundle'}, 'Runtime manifest fields differ')
    require(exact(manifest['accepted_base_runtime'], base_contract(base))
            and exact(manifest['client_bundle'], bundle_contract()), 'Client bundle contract differs')
    require(all(exact(manifest[key], base[key]) for key in set(base)-{'files','repository_commit','scope'}),
            'Accepted runtime fields modified')
    require(set(manifest.get('files', {})) == set(base['files']) | EXTRA_FILES
            and all(manifest['files'].get(name) == pin for name, pin in base['files'].items()),
            'Accepted base payload pins modified')
    verify_inventory(assets, manifest['files'], excluded=('runtime-manifest.json',))
    probe = read_json(assets/PROBE_MANIFEST)
    require(set(probe) == {'format','scope','files'} and type(probe['format']) is int and probe['format'] == 1
            and probe['scope'] == 'actual_client_startup_guest' and set(probe.get('files', {})) == PROBE_FILES
            and all(probe['files'][name] == manifest['files'][name] for name in PROBE_FILES),
            'Client verification inventory differs')
    for name in GUEST_SCRIPTS:
        require(file_pin(assets/name) == file_pin(ROOT/'android/guest'/name), 'Guest script differs from checkout: '+name)
    pe32(assets/'client-launcher.exe')
    client_package.verify_archive(assets/'client-runtime.zip', repository_commit)
    cache_package.verify_cache_archive(assets/'client-caches.zip')
    prerequisite_package.verify_archive(assets/'client-prerequisites.zip')
    avatar_tools().verify(assets/'character-avatar-defaults.zip', assets/'character-avatar-defaults-manifest.json')
    with tempfile.TemporaryDirectory(prefix='coh-login-server-verify-') as temporary:
        extract_local_server_inputs(assets, Path(temporary)/'inputs')
    return manifest


def prepare(*, assets, output, client, client_caches, dbserver_package, dbserver_schema, mapserver_apk, repository_commit, cc='i686-w64-mingw32-gcc', objdump='i686-w64-mingw32-objdump'):
    assets, output = Path(assets), Path(output)
    require(isinstance(repository_commit, str) and HEX40.fullmatch(repository_commit), 'Expected exact source commit')
    require(not output.exists() and not output.is_symlink(), 'Use a fresh assets output directory')
    base = verify_base(assets)
    verify_local_server_inputs(dbserver_package, dbserver_schema)
    require(file_pin(assets/'diagnostic.py') == file_pin(ROOT/'android/guest/diagnostic.py'),
            'Accepted diagnostic.py must remain byte-identical to the current helper')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.interactive-assets-', dir=output.parent) as temporary:
        staging = Path(temporary)/'runtime'; staging.mkdir()
        for name in base['files']: shutil.copyfile(assets/name, staging/name)
        shutil.copyfile(assets/'runtime-manifest.json', staging/BASE_MANIFEST)
        for name in GUEST_SCRIPTS:
            if name != 'diagnostic.py': shutil.copyfile(ROOT/'android/guest'/name, staging/name)
        client_package.verify_archive(Path(client), repository_commit)
        shutil.copyfile(client, staging/'client-runtime.zip')
        cache_package.verify_cache_archive(Path(client_caches))
        shutil.copyfile(client_caches, staging/'client-caches.zip')
        prerequisite_package.prepare(staging/'client-prerequisites.zip')
        avatar_tools().prepare(staging)
        server_tools().write_archive(Path(dbserver_package), staging/'dbserver-package.tar.gz')
        server_tools().write_archive(Path(dbserver_schema), staging/'dbserver-schema.tar.gz')
        recover_mapserver_archive(mapserver_apk, staging/'game-package.tar.gz')
        subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-static-libgcc','-mconsole',
                        str(ROOT/'android/native/client-launcher.c'),'-luser32','-lkernel32',
                        '-o',str(staging/'client-launcher.exe')],check=True)
        pe32(staging/'client-launcher.exe')
        dump = subprocess.check_output([objdump,'-p',str(staging/'client-launcher.exe')],text=True)
        libraries = {value.lower() for value in re.findall(r'DLL Name:\s*(\S+)',dump)}
        (staging/PROBE_MANIFEST).write_text(json.dumps({'format': 1, 'scope': 'actual_client_startup_guest',
            'files': {name: file_pin(staging/name) for name in sorted(PROBE_FILES)}}, indent=2)+'\n')
        manifest = copy.deepcopy(base)
        manifest.update(repository_commit=repository_commit, accepted_base_runtime=base_contract(base),
                        client_bundle=bundle_contract(),
                        scope='Graphical character creation candidate inputs; device character creation and gameplay unvalidated')
        manifest['files'].update({name: file_pin(staging/name) for name in sorted(EXTRA_FILES)})
        (staging/'runtime-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        verify_device_assets(staging, repository_commit=repository_commit)
        staging.rename(output)
    return {'format': 1, 'repository_commit': repository_commit, 'accepted_runtime_run_id': RUNTIME_RUN_ID,
            'runtime_manifest_sha256': digest(output/'runtime-manifest.json'), 'base_file_bytes_preserved': True,
            'native_launcher_windows_libraries': sorted(libraries),
            'native_launcher_source': file_pin(ROOT/'android/native/client-launcher.c'),
            'client_package_sha256': digest(output/'client-runtime.zip'),
            'local_server': local_server_contract(), 'server_input_bytes_preserved': True,
            'avatar_supplement': avatar_tools().bundle_contract(),
            'android_execution_validated': False,
            'gameplay_validated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('assets', 'output', 'client', 'client-caches', 'dbserver-package', 'dbserver-schema', 'mapserver-apk'): parser.add_argument('--'+key, required=True, type=Path)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--cc', default='i686-w64-mingw32-gcc')
    parser.add_argument('--objdump', default='i686-w64-mingw32-objdump')
    print(json.dumps(prepare(**vars(parser.parse_args())), indent=2))

if __name__ == '__main__': main()
