#!/usr/bin/env python3
"""Bounded actual pinned CoH startup on the accepted private presentation path.

No database/server is started. Process/window evidence does not certify a usable
login menu; bounded screenshots are exported for visual review. Only Android can
certify that the observed pixels reached its native surface.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import struct
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import presentation_diagnostic as presentation
import game_hang_evidence
import native_responsiveness_contract as native_candidate
base, require = presentation.base, presentation.require
SCOPE = 'actual_client_startup_guest'
SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
EXE_SHA = '81885ffa8838ef8759c3526fa1cc0bd44f9108e92698b29054256dd0eb97a0ca'
DATA_COUNT, DATA_BYTES = 173011, 2977730517
ASSET_ARCHIVE_SHA = '28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07'
CACHE_EPOCH = 1767225600
CACHE_BYTES_LIMIT = 512*1024*1024
CLIENT_OUTPUT_LIMIT = 128*1024*1024
# 128 MiB raw console plus bounded screenshots/logs; 144 MiB evidence and the
# 2 MiB report fit Android's 160 MiB archive cap even with DEFLATE overhead.
CLIENT_EVIDENCE_LIMIT = 144*1024*1024
REQUIRED = (presentation.REQUIRED - {'presentation-probe.exe'}) | {
    'client_startup_diagnostic.py', 'client-launcher.exe', 'client-runtime.zip', 'client-caches.zip',
    'client-prerequisites.zip'}
PREREQUISITES = {
    'data/server/db/templates/badges.attribute': {'bytes': 51724,
        'sha256': '789ed244ac7c686cc275a8a2914de95bbb044b00483875df950a713f05b66fea'},
    'data/server/db/templates/pophelp.attribute': {'bytes': 2185,
        'sha256': '34195086d3223c717dca5e1cd00bc35a947a05d5fe31b2408a863e85aea617a1'},
    'data/server/db/templates/supergroup_badges.attribute': {'bytes': 1039,
        'sha256': 'd63b3c490fc23086aa6af4fd9add6c2af0892452011d32d6984cac2198d65a7e'},
}
PREREQUISITES_MANIFEST_SHA = '32c27465763cd08b9a210a75f0661634143f39fbe02d4bdaec43c819715a3c1f'
PRIVATE_CACHE_ROOTS = ('bin', 'server/bin', 'geobin')
LAUNCH_MARKER = 'COH_CLIENT_LAUNCH_V1 '
CONSOLE_MARKER = 'COH_CLIENT_CONSOLE_V1 '
MAX_IMAGE_BYTES = 1024*768*4


def read_json(path, limit=1024*1024):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= limit,
            'Missing, linked or oversized JSON input: ' + path.name)
    return json.loads(path.read_text(encoding='utf-8-sig'))


def publish_new_regular_file(temporary, target):
    """Move a completed payload without replacement or PRoot hard-link backing files."""
    # Refuse linked/existing destinations before entering PRoot's rename hook.
    # RENAME_NOREPLACE also closes the race with another publisher. Ordinary
    # rename/replace and hard-link fallbacks would weaken these guarantees.
    if os.path.lexists(target):
        raise FileExistsError(17, 'Asset publication destination already exists', os.fspath(target))
    require(temporary.is_file() and not temporary.is_symlink(),
            'Asset publication source must be an unlinked regular file')
    libc = C.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    require(rename is not None, 'Atomic no-replace asset publication is unavailable')
    rename.argtypes = (C.c_int, C.c_char_p, C.c_int, C.c_char_p, C.c_uint)
    rename.restype = C.c_int
    if rename(-100, os.fsencode(temporary), -100, os.fsencode(target), 1) != 0:
        error = C.get_errno()
        raise OSError(error, os.strerror(error), os.fspath(target))


def validate_args(args):
    require(re.fullmatch(r'[0-9a-f]{32}', args.session_id) is not None, 'Invalid session identity')
    require(type(args.startup_timeout_seconds) is int and 60 <= args.startup_timeout_seconds <= 900,
            'Startup bound must be 60 to 900 seconds')
    require(type(args.observation_seconds) is int and 5 <= args.observation_seconds <= 60,
            'Observation bound must be 5 to 60 seconds')
    require(type(args.timeout_seconds) is int and 180 <= args.timeout_seconds <= 1800,
            'Overall bound must be 180 to 1800 seconds')
    for path in (args.state, args.assets, args.socket_dir, args.game_data):
        require(path.is_absolute() and '..' not in path.parts and path != Path('/') and not path.is_symlink(),
                'Expected absolute unlinked private paths')


def verify_assets(assets):
    manifest = read_json(assets / 'client-manifest.json')
    require(type(manifest.get('format')) is int and manifest['format'] == 1 and manifest.get('scope') == SCOPE,
            'Client manifest scope differs')
    files = manifest.get('files')
    require(isinstance(files, dict) and REQUIRED <= set(files) and len(files) <= 64,
            'Client payload inventory differs')
    hashes = {}
    for name, expected in files.items():
        require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', name)
                and name not in ('.', '..') and isinstance(expected, dict), 'Unsafe client inventory entry')
        path = assets / name
        # This exact world supplement is independently pinned by its manifest
        # and runtime helper; unrelated payloads keep their existing cap.
        limit = (CACHE_BYTES_LIMIT if name in ('client-caches.zip', 'server-caches.zip') else
                 256*1024*1024 if name == 'atlas-world-supplement.zip' else 128*1024*1024)
        require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= limit,
                'Missing, linked or oversized client input: ' + name)
        digest = expected.get('sha256')
        size = expected.get('bytes', expected.get('size'))
        require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest)
                and type(size) is int and path.stat().st_size == size and base.file_hash(path) == digest,
                'Client input pin differs: ' + name)
        hashes[name] = digest
    for name in ('runtime-probe.exe', 'probe.dll', 'client-launcher.exe'):
        base.verify_pe32(assets / name)
    return hashes


def import_identity(data):
    require(data.is_dir() and not data.is_symlink(), 'Missing private imported data')
    receipt = data.parent / 'complete.properties'
    require(receipt.is_file() and not receipt.is_symlink() and receipt.stat().st_size <= 4096,
            'Missing completed import receipt')
    raw = receipt.read_bytes()
    values = {}
    for line in raw.decode('ascii').splitlines():
        key, separator, value = line.partition('=')
        require(separator and key not in values, 'Invalid import receipt')
        values[key] = value
    require(set(values) == {'generation', 'contract.sha256', 'count', 'bytes'}
            and re.fullmatch(r'generation-[0-9a-f]{32}', values['generation'])
            and re.fullmatch(r'[0-9a-f]{64}', values['contract.sha256'])
            and values['count'] == str(DATA_COUNT) and values['bytes'] == str(DATA_BYTES),
            'Imported generation receipt differs from the accepted data contract')
    return {'generation': values['generation'], 'receipt_sha256': hashlib.sha256(raw).hexdigest(),
            'contract_sha256': values['contract.sha256'], 'file_count': DATA_COUNT, 'total_bytes': DATA_BYTES}


def archive_manifest(archive, assets=None):
    entries = archive.infolist()
    require(len(entries) == 22 and len({e.filename.casefold() for e in entries}) == 22,
            'Unexpected client package entry count or duplicate')
    for entry in entries:
        mode = entry.external_attr >> 16
        require(re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', entry.filename) and entry.filename not in ('.', '..')
                and not entry.is_dir() and not entry.flag_bits & 1 and stat.S_IFMT(mode) in (0, stat.S_IFREG)
                and 0 < entry.file_size <= 16*1024*1024, 'Unsafe client archive entry')
    require(sum(e.file_size for e in entries) <= 64*1024*1024, 'Client package exceeded bound')
    require(archive.getinfo('client-package.json').file_size <= 1024*1024, 'Oversized client package receipt')
    manifest = json.loads(archive.read('client-package.json').decode('utf-8-sig'))
    require(manifest.get('format') == 1 and manifest.get('role') == 'actual_graphical_client'
            and manifest.get('source_commit') == SOURCE and manifest.get('data_commit') == DATA
            and manifest.get('reference_run_id') == 36088012664, 'Client package provenance differs')
    files = manifest.get('files')
    require(isinstance(files, dict) and len(files) == 21 and set(files) | {'client-package.json'} == {e.filename for e in entries}
            and set(name for name in files if name.lower().endswith('.exe')) == {'CityOfHeroes.exe'}
            and all(name == 'CityOfHeroes.exe' or name.lower().endswith('.dll') for name in files),
            'Client package must contain only the pinned client and its DLL closure')
    if 'native_responsiveness' in manifest:
        require(assets is not None, 'Native client candidate requires the installed source receipt')
        receipt = read_json(Path(assets) / 'native-responsiveness.json', 4 * 1024 * 1024)
        native_candidate.client_contract(manifest, receipt)
        require(receipt['retained_cache']['executable_sha256'] == EXE_SHA,
                'Native candidate changed prepared-cache donor history')
    else:
        require(files['CityOfHeroes.exe'].get('sha256') == EXE_SHA
                and files['CityOfHeroes.exe'].get('size') == 9432576, 'Unqualified graphical executable')
    for name, expected in files.items():
        require(isinstance(expected, dict) and re.fullmatch(r'[0-9a-f]{64}', expected.get('sha256', ''))
                and type(expected.get('size')) is int and archive.getinfo(name).file_size == expected['size']
                and expected.get('pe_machine') == 0x14c, 'Invalid client package inventory')
    return manifest


def private_cache(relative):
    value = relative.as_posix().casefold()
    return any(value == root or value.startswith(root + '/') for root in PRIVATE_CACHE_ROOTS)


def prerequisites_manifest(archive):
    entries = archive.infolist()
    manifest_name = 'client-prerequisites-manifest.json'
    require(len(entries) == 4 and {entry.filename for entry in entries} == set(PREREQUISITES) | {manifest_name},
            'Client prerequisite inventory differs from the exact three reviewed attributes')
    for entry in entries:
        mode = entry.external_attr >> 16
        require(not entry.is_dir() and not entry.flag_bits & 1 and stat.S_IFMT(mode) in (0, stat.S_IFREG)
                and 0 < entry.file_size <= 128*1024, 'Unsafe client prerequisite entry')
    raw = archive.read(manifest_name)
    require(hashlib.sha256(raw).hexdigest() == PREREQUISITES_MANIFEST_SHA,
            'Client prerequisite canonical provenance differs')
    manifest = json.loads(raw)
    require(type(manifest.get('format')) is int and manifest['format'] == 1
            and manifest.get('role') == 'actual_client_prerequisites'
            and manifest.get('source_commit') == SOURCE and manifest.get('data_commit') == DATA
            and manifest.get('reference_run_id') == 36088012664
            and manifest.get('schema_run_id') == 36088012666
            and manifest.get('ordinary_comparison_run_id') == 36176806895
            and manifest.get('files') == PREREQUISITES, 'Client prerequisite provenance or exact pins differ')
    for name, pin in PREREQUISITES.items():
        require(archive.getinfo(name).file_size == pin['bytes']
                and hashlib.sha256(archive.read(name)).hexdigest() == pin['sha256'],
                'Client prerequisite payload differs: ' + name)
    return manifest, hashlib.sha256(raw).hexdigest()


def cache_manifest(archive):
    entries = archive.infolist()
    require(1 < len(entries) <= 1025 and len({e.filename.casefold() for e in entries}) == len(entries),
            'Duplicate or oversized prepared cache inventory')
    require('client-cache-manifest.json' in archive.namelist()
            and archive.getinfo('client-cache-manifest.json').file_size <= 1024*1024,
            'Prepared cache manifest missing or oversized')
    manifest = json.loads(archive.read('client-cache-manifest.json'))
    require(manifest.get('format') == 1 and manifest.get('role') == 'actual_client_generated_caches'
            and manifest.get('source_commit') == SOURCE and manifest.get('data_commit') == DATA
            and manifest.get('executable_sha256') == EXE_SHA
            and manifest.get('asset_archive_sha256') == ASSET_ARCHIVE_SHA
            and manifest.get('reference_run_id') == 36088012664
            and re.fullmatch(r'[0-9a-f]{64}', str(manifest.get('prerequisites_manifest_sha256')))
            and manifest.get('generated_noncache_outputs') == []
            and type(manifest.get('normalized_mtime_epoch')) is int
            and manifest['normalized_mtime_epoch'] == CACHE_EPOCH,
            'Prepared cache source, data or timestamp identity differs')
    files = manifest.get('files')
    require(isinstance(files, dict) and files and set(files) | {'client-cache-manifest.json'} == set(archive.namelist())
            and 'data/bin/sequencers.bin' in {name.lower() for name in files},
            'Prepared cache contents differ or sequencer cache is missing')
    total = 0
    for entry in entries:
        mode = entry.external_attr >> 16
        require(not entry.is_dir() and not entry.flag_bits & 1 and stat.S_IFMT(mode) in (0, stat.S_IFREG),
                'Unsafe prepared cache entry')
        if entry.filename == 'client-cache-manifest.json': continue
        name = entry.filename
        require(name.isascii() and len(name) <= 260 and '\\' not in name and ':' not in name
                and all(part not in ('', '.', '..') for part in name.split('/'))
                and name.startswith(('data/bin/', 'data/server/bin/', 'data/geobin/'))
                and name.lower().endswith('.bin'), 'Unsafe prepared cache path')
        pin = files[name]
        require(isinstance(pin, dict) and type(pin.get('bytes')) is int and 0 < pin['bytes'] <= 256*1024*1024
                and pin['bytes'] == entry.file_size and re.fullmatch(r'[0-9a-f]{64}', str(pin.get('sha256')))
                and re.fullmatch(r'[0-9a-f]{8}', str(pin.get('schema_crc'))), 'Prepared cache file pin differs')
        total += entry.file_size
    require(total <= CACHE_BYTES_LIMIT, 'Prepared cache output exceeds bound')
    return manifest


def verify_cache_envelope(path, pin):
    """Verify Parse6 boundaries and source dates; the client validates its schema/body."""
    with path.open('rb') as source:
        def exact(count):
            data = source.read(count)
            require(len(data) == count, 'Truncated prepared cache envelope')
            return data
        def integer(): return struct.unpack('<I', exact(4))[0]
        def pascal():
            length = struct.unpack('<H', exact(2))[0]
            require(length <= 1024, 'Oversized prepared cache dependency path')
            data = exact(length)
            exact((-(length + 2)) % 4)
            return data
        require(exact(8) == b'CrypticS' and f'{integer():08x}' == pin['schema_crc']
                and pascal() == b'Parse6' and pascal() == b'Files1', 'Prepared cache envelope differs')
        size = integer()
        end = source.tell() + size
        require(4 <= size <= 32*1024*1024 and end + 4 <= pin['bytes'], 'Prepared cache dependency block exceeds bound')
        count = integer()
        require(count <= size // 8, 'Prepared cache dependency count exceeds block')
        for _ in range(count):
            name = pascal()
            require(name and not name.startswith((b'/', b'\\')) and b':' not in name
                    and b'..' not in name.replace(b'\\', b'/').split(b'/'), 'Unsafe prepared cache dependency')
            # Source permits zero for a deliberately checked missing optional file.
            require(integer() in (0, CACHE_EPOCH - 3600, CACHE_EPOCH, CACHE_EPOCH + 3600),
                    'Prepared cache source timestamp differs')
            require(source.tell() <= end, 'Prepared cache dependency exceeds block')
        require(source.tell() == end, 'Prepared cache dependency block length differs')
        body = integer()
        require(source.tell() + body == pin['bytes'], 'Prepared cache body length differs')


def native_closure_identity(package):
    """Bind actual verified native files, without ZIP/build-wrapper provenance."""
    return {'source_commit': package.get('source_commit'), 'data_commit': package.get('data_commit'),
            'files': package['files']}


def worktree_data_identity(receipt):
    """The immutable data/cache contract; refreshing a wrapper is not new data."""
    return {key: receipt[key] for key in ('format', 'source_data', 'import',
        'cache_archive_sha256', 'prerequisites_archive_sha256',
        'prerequisites_manifest_sha256', 'normalized_mtime_epoch')}


def identity_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def prepare_worktree(root, data, assets, identity, context):
    """Protect imported leaves, create one reusable thin tree, isolate all caches."""
    package_sha = base.file_hash(assets / 'client-runtime.zip')
    cache_sha = base.file_hash(assets / 'client-caches.zip')
    prerequisites_sha = base.file_hash(assets / 'client-prerequisites.zip')
    with zipfile.ZipFile(assets / 'client-prerequisites.zip') as archive:
        _, prerequisites_manifest_sha = prerequisites_manifest(archive)
    with zipfile.ZipFile(assets / 'client-caches.zip') as archive:
        caches = cache_manifest(archive)
    with zipfile.ZipFile(assets / 'client-runtime.zip') as archive:
        package = archive_manifest(archive, assets)
    candidate_receipt = (native_candidate.embedded_receipt(package)
                         if 'native_responsiveness' in package else None)
    previous_client_record = ({'size': 9432576, 'sha256': EXE_SHA}
                             if candidate_receipt is not None else None)
    if 'startup_bundle_client' in package:
        previous_client = package['startup_bundle_client']['base_client_executable']
        previous_client_record = {'size': previous_client['size'], 'sha256': previous_client['sha256']}
    if 'client_loading' in package:
        previous_client = package['client_loading']['base_client_executable']
        previous_client_record = {'size': previous_client['size'], 'sha256': previous_client['sha256']}
    if candidate_receipt is not None:
        require(candidate_receipt['retained_cache']['archive'] == {
                    'bytes': (assets / 'client-caches.zip').stat().st_size, 'sha256': cache_sha},
                'Native client candidate requires the exact retained prepared caches')
    require(caches['prerequisites_manifest_sha256'] == prerequisites_manifest_sha,
            'Prepared caches were generated with different client prerequisites')
    cache_bytes = sum(pin['bytes'] for pin in caches['files'].values())
    prerequisites_bytes = sum(pin['bytes'] for pin in PREREQUISITES.values())
    expected_identity = {'format': 1, 'source_data': str(data), 'import': identity,
                         'package_sha256': package_sha, 'cache_archive_sha256': cache_sha,
                         'prerequisites_archive_sha256': prerequisites_sha,
                         'prerequisites_manifest_sha256': prerequisites_manifest_sha,
                         'normalized_mtime_epoch': CACHE_EPOCH}
    content_sha = identity_sha256({'data': worktree_data_identity(expected_identity),
                                  'native': native_closure_identity(package)})
    def startup_index_migration_proof(report):
        # This producer is validated by archive_manifest, and cached files are
        # verified before every call below. Recompute the old native content
        # identity from its frozen exact executable/DLL closure, rather than
        # accepting a prior marker's claimed identity or a generic schema flag.
        layer = 'client_loading' if 'client_loading' in package else 'startup_bundle_client'
        if layer not in package or not report.get('reused'):
            return report
        wrapper = package[layer]
        old_files = dict(package['files'], **{'CityOfHeroes.exe': wrapper['base_client_executable']})
        old_native = dict(package, files=old_files)
        old_content = identity_sha256({'data': worktree_data_identity(expected_identity),
                                      'native': native_closure_identity(old_native)})
        report['source_root_preserved'] = True
        report['native_texture_index_migration'] = {
            'format': 1, 'policy': ('verified_client_loading_layer_v1' if layer == 'client_loading'
                                    else 'verified_startup_client_layer_v1'),
            'previous_client_identity': {'content_identity_sha256': old_content,
                'data_contract': worktree_data_identity(expected_identity)},
            'previous_executable_sha256': wrapper['base_client_executable']['sha256'],
            'client_executable_sha256': package['files']['CityOfHeroes.exe']['sha256'],
            'content_identity_sha256': content_sha,
            'layer_manifest_sha256': wrapper['manifest_sha256'],
            'texture_header_struct_bytes': 32, 'native_source_closure_verified': True}
        return report
    destination = root / ('client-work-' + content_sha[:24])
    def compatible_receipt(saved):
        # Only the ZIP wrapper provenance may differ. Imported generation,
        # prepared cache donor, prerequisites and timestamp policy stay exact.
        return (isinstance(saved, dict)
                and type(saved.get('format')) is int
                and isinstance(saved.get('package_sha256'), str)
                and re.fullmatch(r'[0-9a-f]{64}', saved['package_sha256']) is not None
                and all(saved.get(k) == v for k, v in expected_identity.items() if k != 'package_sha256'))

    def verify_cached_files(candidate, allow_native_upgrade=False):
        require((candidate / 'tools').is_dir() and not (candidate / 'tools').is_symlink(),
                'Missing private loose-data discovery marker')
        require((candidate / 'data').is_dir() and not (candidate / 'data').is_symlink(), 'Invalid private client data')
        for name in PRIVATE_CACHE_ROOTS:
            current = candidate / 'data'
            for part in Path(name).parts:
                current /= part
                require(not current.is_symlink(), 'Linked writable cache refused')
        upgrade = False
        for name, pin in package['files'].items():
            target = candidate / name
            require(target.is_file() and not target.is_symlink(), 'Linked or missing cached client binary: ' + name)
            actual = {'size': target.stat().st_size, 'sha256': base.file_hash(target)}
            if actual != {'size': pin['size'], 'sha256': pin['sha256']}:
                require(allow_native_upgrade and candidate_receipt is not None
                        and name == 'CityOfHeroes.exe'
                        and actual == previous_client_record,
                        'Cached client binary differs: ' + name)
                upgrade = True
        for name, pin in PREREQUISITES.items():
            target = candidate / name
            require(target.is_file() and not target.is_symlink() and target.stat().st_size == pin['bytes']
                    and base.file_hash(target) == pin['sha256'] and int(target.stat().st_mtime) == CACHE_EPOCH,
                    'Cached client prerequisite differs: ' + name)
        return upgrade

    candidate = destination
    migrated_from = None
    if not destination.exists() and not destination.is_symlink():
        # APK wrapper commits change client-runtime.zip's manifest bytes, but
        # leave the pinned executable/DLL closure unchanged. Reuse one proved
        # old tree instead of recreating 173,011 input links and losing caches.
        possible = [path for path in root.iterdir() if re.fullmatch(r'client-work-[0-9a-f]{24}', path.name)]
        require(len(possible) <= 16, 'Too many client worktrees for bounded reuse')
        matches = []
        for previous in possible:
            require(previous.is_dir() and not previous.is_symlink(), 'Linked client worktree')
            saved = read_json(previous / 'client-work.json')
            if not compatible_receipt(saved): continue
            if 'worktree_key' in saved or 'content_identity_sha256' in saved:
                require(saved.get('worktree_key') == previous.name
                        and re.fullmatch(r'[0-9a-f]{64}', str(saved.get('content_identity_sha256'))),
                        'Prior stable client worktree key differs')
            else:
                old_key = hashlib.sha256((identity['receipt_sha256'] + saved['package_sha256']
                    + cache_sha + prerequisites_sha + str(CACHE_EPOCH)).encode()).hexdigest()[:24]
                require(previous.name == 'client-work-' + old_key, 'Prior client worktree key differs')
            matches.append(previous)
        require(len(matches) <= 1, 'Ambiguous compatible client worktrees')
        if matches:
            candidate = matches[0]
            migrated_from = candidate.name
    if candidate.exists() or candidate.is_symlink():
        require(candidate.is_dir() and not candidate.is_symlink(), 'Linked client worktree')
        saved = read_json(candidate / 'client-work.json')
        require(compatible_receipt(saved), 'Client worktree identity differs')
        previous_receipt_sha = base.file_hash(candidate / 'client-work.json')
        changed_wrapper = saved['package_sha256'] != package_sha
        upgrade = verify_cached_files(candidate, allow_native_upgrade=changed_wrapper)
        if upgrade:
            # Replace only the exact previous donor executable. Imported data,
            # DLLs and generated cache bytes have already passed their checks.
            temporary = candidate / ('client-upgrade-' + base.secrets.token_hex(8) + '.tmp')
            try:
                with zipfile.ZipFile(assets / 'client-runtime.zip') as archive:
                    with archive.open('CityOfHeroes.exe') as source, temporary.open('xb') as output:
                        shutil.copyfileobj(source, output, 1024 * 1024)
                pin = package['files']['CityOfHeroes.exe']
                require(temporary.stat().st_size == pin['size'] and base.file_hash(temporary) == pin['sha256'],
                        'Native client upgrade bytes differ')
                base.verify_pe32(temporary)
                temporary.chmod(0o400)
                os.replace(temporary, candidate / 'CityOfHeroes.exe')
            finally:
                if temporary.exists(): temporary.unlink()
            verify_cached_files(candidate)
        # Existing server links and receipts name this exact root, including
        # regular world/avatar supplements. Keep that verified root in place;
        # renaming it would leave absolute immutable links pointing nowhere.
        destination = candidate
        lineage = saved.get('verified_legacy_receipts', [])
        require(isinstance(lineage, list) and len(lineage) <= 16
                and all(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value)
                        for value in lineage), 'Invalid client worktree receipt lineage')
        metadata_changed = (changed_wrapper or saved.get('content_identity_sha256') != content_sha
                            or saved.get('worktree_key') != destination.name)
        if metadata_changed:
            previous_verified = dict(saved)
            previous_sha = saved['package_sha256']
            saved.update(expected_identity)
            saved.update(content_identity_sha256=content_sha, worktree_key=destination.name,
                         verified_legacy_receipts=list(dict.fromkeys(lineage + [previous_receipt_sha]))[-16:])
            base.private_write(destination / 'client-work.json', json.dumps(saved, indent=2) + '\n')
            return destination, startup_index_migration_proof(dict(saved, reused=True, wrapper_only_migration=not upgrade,
                native_executable_upgraded=upgrade,
                previous_package_sha256=previous_sha, previous_worktree=migrated_from,
                previous_client_work_receipt_sha256=previous_receipt_sha,
                previous_verified_client_worktree=previous_verified,
                source_root_preserved=True, generated_cache_bytes_preserved=True))
        return destination, startup_index_migration_proof(dict(saved, reused=True))
    require(shutil.disk_usage(root).free >= DATA_COUNT*4096 + cache_bytes + prerequisites_bytes + 256*1024*1024,
            'Insufficient space for private client links, prepared caches and runtime reserve')
    staging = root / ('client-staging-' + base.secrets.token_hex(12))
    staging.mkdir(mode=0o700)
    count = total = linked = copied = 0
    try:
        (staging / 'data').mkdir(mode=0o700)
        (staging / 'tools').mkdir(mode=0o700)  # Pinned file.c addAppropriateDataDirs requires both.
        pending = [(data, staging / 'data')]
        progress = 0
        while pending:
            context.check()
            source_dir, target_dir = pending.pop()
            with os.scandir(source_dir) as entries:
                for entry in entries:
                    context.check()
                    require(not entry.is_symlink(), 'Linked immutable input refused')
                    source = Path(entry.path)
                    relative = source.relative_to(data)
                    target = target_dir / entry.name
                    info = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode):
                        target.mkdir(mode=0o700)
                        pending.append((source, target))
                    else:
                        require(stat.S_ISREG(info.st_mode), 'Nonregular immutable input refused')
                        count += 1; total += info.st_size
                        require(count <= DATA_COUNT and total <= DATA_BYTES, 'Imported content exceeds accepted bounds')
                        # Metadata is normalized once; accepted input bytes stay unchanged.
                        os.utime(source, (CACHE_EPOCH, CACHE_EPOCH), follow_symlinks=False)
                        os.chmod(source, 0o444, follow_symlinks=False)
                        if private_cache(relative) or source.suffix.casefold() == '.dbidmap':
                            shutil.copyfile(source, target, follow_symlinks=False)
                            os.chmod(target, 0o600)
                            os.utime(target, (CACHE_EPOCH, CACHE_EPOCH), follow_symlinks=False)
                            copied += 1
                        else:
                            target.symlink_to(source)
                            linked += 1
                    if time.monotonic() >= progress:
                        context.event('stage', status='running', message='Preparing reusable client data links', files=count)
                        progress = time.monotonic() + 5
        require((count, total) == (DATA_COUNT, DATA_BYTES), 'Imported data size/count differs from completed receipt')
        for name in PRIVATE_CACHE_ROOTS:
            (staging / 'data' / name).mkdir(parents=True, exist_ok=True, mode=0o700)
        with zipfile.ZipFile(assets / 'client-prerequisites.zip') as archive:
            for name, pin in PREREQUISITES.items():
                context.check()
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                require(not target.exists() and not target.is_symlink(), 'Client prerequisite would overwrite imported input')
                with target.open('xb') as output:
                    output.write(archive.read(name))
                require(base.file_hash(target) == pin['sha256'], 'Installed client prerequisite differs')
                os.utime(target, (CACHE_EPOCH, CACHE_EPOCH), follow_symlinks=False)
                os.chmod(target, 0o444)
        with zipfile.ZipFile(assets / 'client-caches.zip') as archive:
            for name, pin in caches['files'].items():
                context.check()
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                require(not target.is_symlink(), 'Linked prepared cache output refused')
                with archive.open(name) as source, target.open('wb') as output:
                    shutil.copyfileobj(source, output, 1024*1024)
                require(target.stat().st_size == pin['bytes'] and base.file_hash(target) == pin['sha256'],
                        'Prepared cache output hash differs: ' + name)
                verify_cache_envelope(target, pin)
                os.chmod(target, 0o600)
                os.utime(target, (CACHE_EPOCH, CACHE_EPOCH), follow_symlinks=False)
        with zipfile.ZipFile(assets / 'client-runtime.zip') as archive:
            package = archive_manifest(archive, assets)
            for name, pin in package['files'].items():
                context.check()
                target = staging / name
                with archive.open(name) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output, 1024*1024)
                require(base.file_hash(target) == pin['sha256'], 'Client archive hash differs: ' + name)
                base.verify_pe32(target)
                os.chmod(target, 0o400)
        saved = dict(expected_identity, linked_files=linked, copied_writable_files=copied,
                     input_files=count, input_bytes=total, imported_inputs_readonly=True,
                     imported_input_bytes_unchanged=True, imported_metadata_normalized=True,
                     prepared_cache_files=len(caches['files']), prepared_cache_bytes=cache_bytes,
                     prepared_prerequisite_files=len(PREREQUISITES), prepared_prerequisite_bytes=prerequisites_bytes,
                     writable_cache_roots=list(PRIVATE_CACHE_ROOTS),
                     content_identity_sha256=content_sha, worktree_key=destination.name,
                     verified_legacy_receipts=[])
        base.private_write(staging / 'client-work.json', json.dumps(saved, indent=2) + '\n')
        os.rename(staging, destination)
        return destination, dict(saved, reused=False)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


class XWindowAttributes(C.Structure):
    _fields_ = [('x', C.c_int), ('y', C.c_int), ('width', C.c_int), ('height', C.c_int),
        ('border_width', C.c_int), ('depth', C.c_int), ('visual', C.c_void_p), ('root', C.c_ulong),
        ('win_class', C.c_int), ('bit_gravity', C.c_int), ('win_gravity', C.c_int), ('backing_store', C.c_int),
        ('backing_planes', C.c_ulong), ('backing_pixel', C.c_ulong), ('save_under', C.c_int),
        ('colormap', C.c_ulong), ('map_installed', C.c_int), ('map_state', C.c_int),
        ('all_event_masks', C.c_long), ('your_event_mask', C.c_long), ('do_not_propagate_mask', C.c_long),
        ('override_redirect', C.c_int), ('screen', C.c_void_p)]


class XImage(C.Structure):
    _fields_ = [('width', C.c_int), ('height', C.c_int), ('xoffset', C.c_int), ('format', C.c_int),
        ('data', C.c_void_p), ('byte_order', C.c_int), ('bitmap_unit', C.c_int), ('bitmap_bit_order', C.c_int),
        ('bitmap_pad', C.c_int), ('depth', C.c_int), ('bytes_per_line', C.c_int), ('bits_per_pixel', C.c_int),
        ('red_mask', C.c_ulong), ('green_mask', C.c_ulong), ('blue_mask', C.c_ulong)]


def ppm_from_ximage(image):
    require(0 < image.width <= 1024 and 0 < image.height <= 768 and image.bits_per_pixel in (24, 32)
            and image.byte_order in (0, 1) and 0 < image.bytes_per_line <= 4096
            and image.width*(image.bits_per_pixel//8) <= image.bytes_per_line
            and image.bytes_per_line*image.height <= MAX_IMAGE_BYTES and image.data,
            'Unsupported or oversized X image')
    require((image.red_mask, image.green_mask, image.blue_mask) == (0xff0000, 0xff00, 0xff),
            'Unsupported X color masks')
    raw = C.string_at(image.data, image.bytes_per_line*image.height)
    output = bytearray()
    stride = image.bits_per_pixel//8
    order = 'little' if image.byte_order == 0 else 'big'
    colors = set()
    for row in range(image.height):
        for column in range(image.width):
            offset = row*image.bytes_per_line + column*stride
            pixel = int.from_bytes(raw[offset:offset+stride], order)
            rgb = ((pixel >> 16)&255, (pixel >> 8)&255, pixel&255)
            output.extend(rgb)
            if len(colors) < 256: colors.add(rgb)
    return f'P6\n{image.width} {image.height}\n255\n'.encode() + output, len(colors)


class XObserver:
    def __init__(self, display):
        self.lib = C.CDLL('libX11.so.6')
        lib = self.lib
        lib.XOpenDisplay.argtypes = [C.c_char_p]; lib.XOpenDisplay.restype = C.c_void_p
        lib.XDefaultRootWindow.argtypes = [C.c_void_p]; lib.XDefaultRootWindow.restype = C.c_ulong
        lib.XCloseDisplay.argtypes = [C.c_void_p]
        lib.XFree.argtypes = [C.c_void_p]
        lib.XSync.argtypes = [C.c_void_p, C.c_int]
        lib.XQueryTree.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_ulong), C.POINTER(C.c_ulong),
                                  C.POINTER(C.POINTER(C.c_ulong)), C.POINTER(C.c_uint)]
        lib.XFetchName.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_void_p)]
        lib.XGetWindowAttributes.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(XWindowAttributes)]
        lib.XGetImage.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_int, C.c_uint, C.c_uint, C.c_ulong, C.c_int]
        lib.XGetImage.restype = C.POINTER(XImage)
        lib.XDestroyImage.argtypes = [C.POINTER(XImage)]
        self.error_count = 0
        handler = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_void_p)
        def on_error(_display, _event):
            self.error_count += 1
            return 0
        self.error_callback = handler(on_error)
        lib.XSetErrorHandler.argtypes = [handler]
        lib.XSetErrorHandler.restype = C.c_void_p
        lib.XSetErrorHandler(self.error_callback)
        self.display = lib.XOpenDisplay(display.encode())
        require(self.display, 'Cannot observe owned X display')
        self.root = lib.XDefaultRootWindow(self.display)

    def windows(self):
        records, pending, seen = [], [self.root], set()
        while pending:
            window = pending.pop()
            if window in seen: continue
            seen.add(window)
            require(len(seen) <= 512, 'Owned X window count exceeded bound')
            attributes = XWindowAttributes()
            name_ptr = C.c_void_p()
            if self.lib.XGetWindowAttributes(self.display, window, C.byref(attributes)):
                name = ''
                if self.lib.XFetchName(self.display, window, C.byref(name_ptr)) and name_ptr:
                    try:
                        name = C.string_at(name_ptr).decode('utf-8', 'replace')[:256]
                    finally:
                        self.lib.XFree(name_ptr)
                if name:
                    records.append({'window_id': int(window), 'title': name, 'width': attributes.width,
                        'height': attributes.height, 'mapped': attributes.map_state == 2})
            root, parent, count, children = C.c_ulong(), C.c_ulong(), C.c_uint(), C.POINTER(C.c_ulong)()
            if self.lib.XQueryTree(self.display, window, C.byref(root), C.byref(parent), C.byref(children), C.byref(count)):
                try:
                    require(count.value <= 512, 'Owned X child count exceeded bound')
                    pending.extend(int(children[index]) for index in range(count.value))
                finally:
                    if children: self.lib.XFree(children)
        self.lib.XSync(self.display, False)
        return records

    def capture(self, path):
        image = self.lib.XGetImage(self.display, self.root, 0, 0, 800, 600, C.c_ulong(-1).value, 2)
        require(bool(image), 'Cannot capture owned X desktop')
        try:
            data, colors = ppm_from_ximage(image.contents)
        finally:
            self.lib.XDestroyImage(image)
        require(not path.exists() and not path.is_symlink(), 'Capture destination already exists')
        with path.open('xb') as output:
            output.write(data)
        return {'path': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                'width': 800, 'height': 600, 'distinct_colors_capped': colors,
                'kind': 'owned_x_desktop', 'menu_visual_validated': False}

    def close(self):
        if self.display:
            self.lib.XCloseDisplay(self.display)
            self.display = None


# str.splitlines recognizes these boundaries as well as CR/LF. Keep its exact
# identity semantics while avoiding a Python object for every unrelated native
# diagnostic line at each startup observation. Search all current output on
# every call, so a late duplicate, retry, or malformed identity is never cached.
_CONSOLE_LINE_BOUNDARIES = '\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029'
_CONSOLE_LINE_END = re.compile('[' + _CONSOLE_LINE_BOUNDARIES + ']')


def console_marker_values(output, marker):
    values, position = [], 0
    while True:
        position = output.find(marker, position)
        if position < 0:
            return values
        start = position + len(marker)
        if position == 0 or output[position - 1] in _CONSOLE_LINE_BOUNDARIES:
            end = _CONSOLE_LINE_END.search(output, start)
            values.append(json.loads(output[start:end.start() if end else len(output)]))
        position = start


def parse_launch(output, session):
    values = console_marker_values(output, LAUNCH_MARKER)
    require(len(values) <= 1, 'Duplicate client launch identity')
    if not values: return None
    value = values[0]
    require(isinstance(value, dict) and set(value) == {'session_id', 'pid'} and value['session_id'] == session
            and type(value['pid']) is int and 0 < value['pid'] < 2**32, 'Invalid client launch identity')
    return value


def startup_evidence(output, registry_output, windows, launch):
    main_loop = bool(re.search(r'(?mi)^\s*GameProgress\s+REG_SZ\s+game_mainLoop\s*$', registry_output))
    actual = [row for row in windows if current_client_title(row['title'], launch) and row['mapped']
              and row['width'] >= 320 and row['height'] >= 240]
    gl = {}
    for field, label in [('vendor', 'Vendor'), ('renderer', 'Renderer'), ('gl_version', 'Version')]:
        values = re.findall(r'OpenGL ' + label + r': ([^\r\n]{1,512})', output)
        if values: gl[field] = values[-1].strip()
    renderer = gl.get('renderer', '')
    gl['renderer_classification'] = ('software' if any(value in renderer.lower()
        for value in ('llvmpipe', 'softpipe', 'software rasterizer', 'swrast')) else 'unclassified')
    return {'graphics_observation': gl, 'renderer_initialized': 'Renderer initialization complete' in output,
        'all_data_loaded': 'Loaded all data!' in output, 'client_main_loop_reached': main_loop,
        'client_window_observed': bool(actual), 'client_windows': actual,
        'startup_observed': bool(main_loop and actual), 'menu_visual_validated': False}


def current_client_title(title, launch):
    """Match the owned client's menu or canonical map title without losing its PID."""
    if (not isinstance(title, str) or len(title) > 1000 or not isinstance(launch, dict)
            or type(launch.get('pid')) is not int or not 0 < launch['pid'] < 2**32):
        return False
    pid = str(launch['pid'])
    if title == 'City of Heroes : PID: ' + pid:
        return True
    # Entering a map changes the title while the same mapped X window and
    # launched Windows PID remain alive. Accept only a relative game map path,
    # then the observed two-space separator and exact current PID suffix.
    return re.fullmatch(r'City of Heroes : (?:[A-Za-z0-9_-]+/)+[A-Za-z0-9_-]+\.txt  PID: '
                        + pid, title) is not None


def console_identity(output, launch):
    values = console_marker_values(output, CONSOLE_MARKER)
    require(len(values) <= 1, 'Duplicate client console identity')
    if not values: return None
    value = values[0]
    require(launch is not None and isinstance(value, dict)
            and set(value) == {'session_id', 'pid', 'attached'}
            and value['session_id'] == launch['session_id']
            and type(value['pid']) is int and value['pid'] == launch['pid']
            and value['attached'] is True, 'Client console identity does not match owned launch')
    return value


def cache_inventory(work, deadline, entry_limit=4096):
    """Inspect only private cache metadata, never walk or copy the loose inputs."""
    result = {'format': 1, 'sampled_utc': base.utc(), 'entry_limit': entry_limit,
              'files': [], 'roots': list(PRIVATE_CACHE_ROOTS), 'truncated': False}
    pending = [work / 'data' / name for name in PRIVATE_CACHE_ROOTS]
    examined = 0
    while pending:
        directory = pending.pop()
        require(not directory.is_symlink(), 'Linked private cache directory refused')
        if not directory.exists(): continue
        with os.scandir(directory) as entries:
            for entry in entries:
                if examined >= entry_limit or time.monotonic() >= deadline:
                    result['truncated'] = True
                    return result
                examined += 1
                require(not entry.is_symlink(), 'Linked private cache entry refused')
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(Path(entry.path))
                elif stat.S_ISREG(info.st_mode):
                    result['files'].append({'path': Path(entry.path).relative_to(work).as_posix(),
                        'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns})
    return result


class ClientStartupDiagnostic(presentation.PresentationDiagnostic):
    def __init__(self, args, context):
        super().__init__(args, context)
        self.observer = None
        self.client = None
        self.work = None
        self.capture_dir = base.private_dir(args.state / ('client-evidence-' + args.session_id))
        self.captures = []
        self.startup_complete = False

    def initialize(self):
        self.ctx.stage('client_inputs')
        require(platform.machine().lower() in ('aarch64', 'arm64'), 'Guest must execute on ARM64')
        require(os.geteuid() == 1000, 'Guest requires PRoot -i 1000:1000')
        self.ctx.report['asset_sha256'] = verify_assets(self.args.assets)
        base.arm64_elf(self.args.wine); base.arm64_elf(self.args.wineserver)
        require(self.args.socket_dir.is_dir() and not self.args.socket_dir.is_symlink()
                and stat.S_IMODE(self.args.socket_dir.stat().st_mode) == 0o700, 'Invalid private presentation socket directory')
        require(not self.presentation_socket.exists() and not self.presentation_socket.is_symlink(), 'Socket already exists')
        identity = import_identity(self.args.game_data)
        self.ctx.report['import_identity'] = identity
        with zipfile.ZipFile(self.args.assets / 'client-runtime.zip') as archive:
            package = archive_manifest(archive, self.args.assets)
        self.client_executable_sha256 = package['files']['CityOfHeroes.exe']['sha256']
        if 'native_responsiveness' in package:
            candidate = native_candidate.embedded_receipt(package)
            self.ctx.report['native_responsiveness_candidate'] = {
                'repository_commit': candidate['repository_commit'],
                'receipt_sha256': native_candidate.canonical_sha(candidate),
                'runtime_execution_validated': False,
                'prepared_cache_donor_executable_sha256': EXE_SHA,
                'prepared_cache_schema_changed': False}
        if 'startup_bundle_client' in package:
            wrapper = package['startup_bundle_client']
            self.ctx.report['startup_bundle_client'] = {
                'repository_commit': wrapper['manifest']['repository_commit'],
                'manifest_sha256': wrapper['manifest_sha256'],
                'base_client_executable_sha256': wrapper['base_client_executable']['sha256'],
                'client_executable_sha256': self.client_executable_sha256,
                'replacement_scope': 'CityOfHeroes.exe_only',
                'prepared_cache_schema_changed': False, 'graphics_profile_changed': False,
                'runtime_execution_validated': False}
        if 'client_loading' in package:
            wrapper = package['client_loading']
            self.ctx.report['client_loading'] = {
                'repository_commit': wrapper['manifest']['repository_commit'],
                'manifest_sha256': wrapper['manifest_sha256'],
                'base_client_executable_sha256': wrapper['base_client_executable']['sha256'],
                'client_executable_sha256': self.client_executable_sha256,
                'replacement_scope': 'CityOfHeroes.exe_only',
                'prepared_cache_schema_changed': False, 'graphics_profile_changed': False,
                'runtime_execution_validated': False}
        self.ctx.passed(machine=platform.machine(), guest_uid=os.geteuid(), postgres_started=False,
                        source_commit=SOURCE, data_commit=DATA,
                        client_executable_sha256=self.client_executable_sha256)
        self.ctx.stage('client_private_data')
        self.work, receipt = prepare_worktree(self.root, self.args.game_data, self.args.assets, identity, self.ctx)
        self.ctx.report['client_worktree'] = receipt
        self.ctx.passed(**receipt)

    def capture(self, label):
        if self.observer is None or len(self.captures) >= 3: return None
        record = self.observer.capture(self.capture_dir / (label + '.ppm'))
        record.update(session_id=self.args.session_id, captured_utc=base.utc())
        self.captures.append(record)
        self.ctx.report['screenshots'] = self.captures
        return record

    def observe_console(self):
        started = time.monotonic()
        output = self.client.text()
        launch = parse_launch(output, self.args.session_id)
        if launch:
            self.ctx.report.update(client_process_started=True, client_launch=launch)
        console = console_identity(output, launch)
        self.ctx.report['client_console_observation'] = console
        require('COH_CLIENT_CONSOLE_TRUNCATED_V1' not in output, 'Actual client console exceeded observation budget')
        milliseconds = max(0.0, time.monotonic() - started) * 1000
        metrics = self.ctx.report.setdefault('client_console_identity_metrics', {
            'policy': 'complete_current_console_marker_search', 'calls': 0,
            'total_ms': 0.0, 'max_ms': 0.0,
            'whole_console_rescanned': True, 'identity_cache_added': False})
        metrics.update(calls=metrics['calls'] + 1,
                       total_ms=round(metrics['total_ms'] + milliseconds, 3),
                       max_ms=round(max(metrics['max_ms'], milliseconds), 3),
                       last_ms=round(milliseconds, 3), last_console_characters=len(output))
        return output, launch, console

    def execute(self):
        self.initialize()
        self.start_wine()
        self.ctx.stage('win32_runtime_dll')
        result = self.ctx.run('runtime-probe', [self.args.wine,
            base.windows_path(self.args.assets / 'runtime-probe.exe')], timeout=60, env=self.wine_env)
        self.ctx.passed(**base.validate_runtime_probe(result['output']))
        self.mark_wine_ready()
        # Consume any previous registry progress before the new client starts.
        self.ctx.run('client-progress-reset', [self.args.wine, 'reg', 'delete',
            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/f', '/reg:32'],
            timeout=8, env=self.wine_env, check=False)
        reset_query = self.ctx.run('client-progress-empty', [self.args.wine, 'reg', 'query',
            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/reg:32'],
            timeout=8, env=self.wine_env, check=False)
        require(not re.search(r'(?mi)^\s*GameProgress\s+REG_SZ\s+', reset_query['output']),
                'Prior client progress registry value could not be cleared')
        previous_logs = self.work / 'logs'
        require(not previous_logs.is_symlink(), 'Linked client logs refused')
        if previous_logs.exists():
            require(previous_logs.is_dir(), 'Client logs path must be a directory')
            shutil.rmtree(previous_logs)
        self.ctx.stage('actual_client_startup')
        self.observer = XObserver(self.wine_env['DISPLAY'])
        self.capture('before-client')
        self.ctx.event('client_display_ready', session_id=self.args.session_id, width=800, height=600,
                       socket_path=str(self.presentation_socket), startup_timeout_seconds=self.args.startup_timeout_seconds)
        # The launcher's -nogui diagnostic-UI profile preserves the actual game
        # window, renderer and data validation, while suppressing native dialogs
        # and splash UI. It keeps inherited log pipes and observes the owned
        # child's console as a fallback; game code and assets remain unchanged.
        command = [self.args.wine, base.windows_path(self.args.assets / 'client-launcher.exe'), self.args.session_id,
                   base.windows_path(self.work / 'CityOfHeroes.exe'), base.windows_path(self.work)]
        previous = Path.cwd()
        try:
            os.chdir(self.work)
            self.client = self.ctx.start('actual-coh-client', command, env=self.wine_env)
        finally:
            os.chdir(previous)
        started = time.monotonic()
        deadline = started + self.args.startup_timeout_seconds
        next_registry = next_progress = 0
        registry_output = ''
        ready_at = None
        console = None
        try:
            while True:
                self.ctx.check()
                require(self.client.process.poll() is None, 'Actual CoH client exited during startup or observation')
                require(self.xserver.process.poll() is None, 'Owned presentation display exited')
                now = time.monotonic()
                require(now < deadline, 'Actual CoH startup exceeded its bounded deadline')
                # Decoding and scanning a growing multi-MiB log at 10Hz steals
                # startup time. Use the existing five-second evidence poll;
                # stop/process/overall/overflow checks above remain at 100ms.
                # Refresh at the console deadline even between progress polls.
                if now >= next_progress or (console is None and now - started >= 120):
                    output, launch, console = self.observe_console()
                require(console is not None or now - started < 120,
                        'Could not attach to actual client console within 120 seconds')
                if now >= next_progress:
                    windows = self.observer.windows()
                    self.ctx.report['observed_windows'] = windows
                    if now >= next_registry:
                        registry = self.ctx.run('client-progress-registry', [self.args.wine, 'reg', 'query',
                            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/reg:32'],
                            timeout=8, env=self.wine_env, check=False)
                        registry_output = registry['output']
                        next_registry = time.monotonic() + 20
                    evidence = startup_evidence(output, registry_output, windows, launch)
                    self.ctx.report.update(evidence)
                    if evidence['startup_observed'] and evidence['renderer_initialized'] and evidence['all_data_loaded']:
                        if ready_at is None:
                            ready_at = time.monotonic()
                            deadline = max(deadline, ready_at + self.args.observation_seconds + 10)
                            shot = self.capture('client-startup')
                            require(shot and shot['distinct_colors_capped'] >= 8, 'Actual client desktop capture is blank')
                            self.ctx.event('client_startup_observed', session_id=self.args.session_id,
                                           client_pid=launch['pid'], menu_visual_validated=False)
                        elif time.monotonic() - ready_at >= self.args.observation_seconds:
                            self.ctx.report.update(observation_seconds=round(time.monotonic()-ready_at, 3),
                                                   startup_elapsed_seconds=round(ready_at-started, 3))
                            shot = self.capture('client-observed')
                            require(shot and shot['distinct_colors_capped'] >= 8, 'Observed client desktop became blank')
                            # Logs may grow during the registry query/capture.
                            # A fresh check forbids acceptance after truncation
                            # even though ordinary detection is on the 5s poll.
                            self.ctx.check()
                            self.observe_console()
                            self.ctx.passed(**evidence, bounded_live_observation=True)
                            self.startup_complete = True
                            return
                    else:
                        require(ready_at is None, 'Actual CoH window or startup evidence disappeared during observation')
                    self.ctx.event('stage', status='running', message='Starting City of Heroes' if ready_at is None
                                   else 'Observing actual City of Heroes window', elapsed_seconds=int(now-started),
                                   renderer_initialized=evidence['renderer_initialized'],
                                   client_main_loop_reached=evidence['client_main_loop_reached'])
                    next_progress = time.monotonic() + 5
                time.sleep(.1)
        finally:
            self.save_evidence()

    def save_evidence(self):
        if self.client:
            data = bytes(self.client.output)  # Preserve bounded raw bytes without replacement-decoding expansion.
            target = self.capture_dir / 'client-console.log'
            if not target.exists(): target.write_bytes(data)
            self.ctx.report['client_console'] = {'path': target.name, 'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest()}
        if self.observer and len(self.captures) < 3:
            try: self.capture('client-final')
            except Exception as exc: self.ctx.report.setdefault('observation_failures', []).append(str(exc))
        if self.work:
            try:
                inventory = cache_inventory(self.work, time.monotonic() + 3)
                target = self.capture_dir / 'private-cache-inventory.json'
                target.write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
                self.ctx.report['private_cache_inventory'] = {'path': target.name,
                    'files': len(inventory['files']), 'truncated': inventory['truncated']}
            except Exception as exc:
                self.ctx.report.setdefault('observation_failures', []).append('Cache inventory: ' + str(exc))
            if not self.startup_complete and self.wine_started:
                try:
                    snapshot = game_hang_evidence.capture_processes(self, time.monotonic() + 6)
                    target = self.capture_dir / 'owned-processes.json'
                    payload = json.dumps(snapshot, indent=2) + '\n'
                    require(len(payload.encode()) <= 1024*1024, 'Owned-process snapshot exceeded bound')
                    target.write_text(payload, encoding='utf-8')
                    self.ctx.report['owned_process_snapshot'] = {'path': target.name,
                        'owned_process_count': snapshot.get('owned_process_count')}
                except Exception as exc:
                    self.ctx.report.setdefault('observation_failures', []).append('Owned processes: ' + str(exc))
            logs = self.work / 'logs'
            if logs.is_dir() and not logs.is_symlink():
                output_dir = self.capture_dir / 'logs'
                count, total = 0, 0
                for path in logs.rglob('*'):
                    require(not path.is_symlink(), 'Linked client log refused')
                    if not path.is_file(): continue
                    count += 1
                    require(count <= 64, 'Client log count exceeded bound')
                    # Tail bounds preserve runtime failure clues without copying
                    # stale or unbounded diagnostics into the support archive.
                    with path.open('rb') as handle:
                        handle.seek(max(0, path.stat().st_size - 256*1024))
                        payload = handle.read(256*1024)
                    total += len(payload)
                    require(total <= 4*1024*1024, 'Client logs exceeded bound')
                    target = output_dir / path.relative_to(logs)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(payload)

    def cleanup(self):
        if self.observer:
            self.observer.close()
            self.observer = None
        return super().cleanup()


def persist_report(args, context, capture_dir, *, evidence_limit=None):
    if evidence_limit is None:
        evidence_limit = CLIENT_EVIDENCE_LIMIT
    document = json.dumps(base.redacted_value(context.report, context.secrets), indent=2) + '\n'
    require(len(document.encode()) <= 2*1024*1024, 'Client report exceeded bound')
    base.private_write(args.state / 'latest-report.json', document)
    target = args.state / 'report.zip'
    require(not target.is_symlink(), 'Linked support archive refused')
    temporary = target.with_name('report.zip.tmp-' + base.secrets.token_hex(8))
    try:
        with temporary.open('xb') as handle:
            os.chmod(temporary, 0o600)
            with zipfile.ZipFile(handle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('latest-report.json', document)
                total = count = 0
                if capture_dir is not None:
                    for path in sorted(capture_dir.rglob('*')):
                        require(not path.is_symlink(), 'Linked capture refused')
                        if not path.is_file(): continue
                        size = path.stat().st_size
                        count += 1; total += size
                        require(count <= 70 and total <= evidence_limit, 'Capture export exceeded bound')
                        archive.write(path, 'client-evidence/' + path.relative_to(capture_dir).as_posix())
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in [('state', '/state'), ('assets', '/opt/coh'), ('pg-bin', '/opt/coh/pgsql/bin'),
                          ('wine', '/opt/wine/bin/wine'), ('wineserver', '/opt/wine/bin/wineserver'),
                          ('xserver', '/usr/bin/Xtigervnc'), ('socket-dir', '/presentation-socket'),
                          ('game-data', '/game-import/data')]:
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--execution-platform', choices=('android', 'host'), default='host')
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--startup-timeout-seconds', type=int, default=900)
    parser.add_argument('--observation-seconds', type=int, default=30)
    parser.add_argument('--timeout-seconds', type=int, default=1800)
    args = parser.parse_args(argv)
    # This dedicated client invocation retains the full, verbose validation log
    # up to 128 MiB. Every owned child stays bounded and overflow remains fatal.
    # The accepted diagnostic.py payload itself stays byte-identical.
    base.OUTPUT_LIMIT = CLIENT_OUTPUT_LIMIT
    os.umask(0o077)
    context = base.Context(args.state, args.timeout_seconds)
    context.report.update(scope=SCOPE, diagnostic_mode='actual_client_startup', session_id=args.session_id,
        execution_platform_requested=args.execution_platform, postgres_started=False,
        server_started=False, game_validated=False, menu_visual_validated=False,
        android_surface_validated=False, hardware_acceleration_validated=False,
        client_process_started=False, startup_observed=False)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
    diagnostic = None
    validated = False
    try:
        validate_args(args); validated = True
        context.check()
        diagnostic = ClientStartupDiagnostic(args, context)
        diagnostic.execute()
        context.report['status'] = 'passed'
    except base.Cancelled as exc:
        context.report.update(status='cancelled', failures=[str(exc)])
    except Exception as exc:
        context.report.update(status='failed', failures=[str(exc)])
    finally:
        if diagnostic is not None:
            try: failures = diagnostic.cleanup()
            except Exception as exc: failures = ['Owned cleanup failed: ' + str(exc)]
            context.report['failures'].extend(failures)
        closed = all(c.process.poll() is not None and not c.reader.is_alive() and not c.writer.is_alive()
                     for c in context.children)
        context.report.update(finished_utc=base.utc(), cleanup_complete=closed,
            cleanup_execution={'diagnostic_initialized': diagnostic is not None,
                'wine_started': bool(diagnostic is not None and diagnostic.wine_started),
                'owned_child_count': len(context.children)},
            cleanup=diagnostic.cleanup_status if diagnostic else {'postgres_graceful': True,
                'wine_prefix_stopped': False, 'owned_processes_reaped': closed})
        context.report['passed'] = (context.report['status'] == 'passed' and not context.report['failures']
                                    and closed and all(context.report['cleanup'].values()))
        if context.report['status'] == 'passed' and not context.report['passed']:
            context.report['status'] = 'failed'
            if not context.report['failures']: context.report['failures'].append('Required cleanup was not proved')
        if validated:
            try:
                persist_report(args, context, diagnostic.capture_dir if diagnostic else None)
            except Exception as exc:
                context.report.update(status='failed', passed=False)
                context.report['failures'].append('Cannot persist client report: ' + str(exc))
                try: base.private_write(args.state / 'latest-report.json', json.dumps(context.report, indent=2) + '\n')
                except Exception: pass
        context.event('result', status=context.report['status'], passed=context.report['passed'],
                      report='/state/latest-report.json', failures=context.report['failures'])
    return 0 if context.report['passed'] else 2 if context.report['status'] == 'cancelled' else 1


if __name__ == '__main__':
    sys.exit(main())
