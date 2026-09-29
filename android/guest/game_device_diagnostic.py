#!/usr/bin/env python3
"""Run the accepted Atlas proof against a completed private Android import.

The accepted orchestration remains in game_diagnostic.py. This adapter validates
the separate immutable inventory and copies the imported generation into a new
writable session before the original eighteen stages run. Android execution is
attested by the native application, never by a guest command-line flag.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import game_diagnostic as game

base, dbserver, require = game.base, game.dbserver, game.require
SOURCE_COMMIT = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA_COMMIT = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
GAME_COMMIT = 'ac4c1f7978be444a893f65f5177641191861d42f'
BASE_COMMIT = '9dc58f62c58dc4fc5c01288071429bf2aa06d2f4'
BASE_MANIFEST_SHA256 = 'fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203'
PACKAGE_SHA256 = 'ebfdbbab3984627f7c39220f42a9c3e67b78ffe555aa742621a7a1450731fb2a'
SCHEMA_SHA256 = 'b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92'
DATA_MANIFEST_SHA256 = 'b367cc35d3f3826d9988ffa5dadb0a240ffc0967f0d248586e54d8ac545615f4'
DATA_MANIFEST_BYTES = 32184737
DATA_COUNT = 173011
DATA_BYTES = 2977730517
GUEST_FILES = ('game_diagnostic.py', 'dbserver_diagnostic.py', 'game_evidence.py',
               'game_hang_evidence.py', 'game_device_diagnostic.py')
COPY_BLOCK = 1024 * 1024
RUNTIME_RESERVE_BYTES = 2 * 1024**3


def checked_file(path, limit):
    path = Path(path)
    require(path.is_absolute(), 'Input path must be absolute')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        require(part not in ('.', '..'), 'Unsafe input path')
        current /= part
        require(not current.is_symlink(), 'Linked input refused')
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit,
            'Missing, nonregular or oversized input: ' + path.name)
    return path


def pinned_json(path, expected, limit):
    path = checked_file(path, limit)
    require(base.file_hash(path) == expected, 'Accepted input digest differs: ' + path.name)
    return dbserver.load_json(path, limit)


def read_properties(path, limit):
    raw = checked_file(path, limit).read_bytes()
    try:
        lines = raw.decode('ascii').splitlines()
    except UnicodeDecodeError as exc:
        raise base.DiagnosticError('Content properties must be ASCII') from exc
    require(raw.endswith(b'\n'), 'Incomplete content properties')
    properties = {}
    for line in lines:
        key, separator, value = line.partition('=')
        require(separator and key not in properties and re.fullmatch(r'[a-z0-9.]+', key)
                and value and all(32 <= ord(char) < 127 for char in value)
                and '\\' not in value, 'Duplicate or malformed content properties')
        properties[key] = value
    return properties, hashlib.sha256(raw).hexdigest()


def import_contract(path, repository_commit):
    properties, digest = read_properties(path, 16384)
    require(all(properties.get(name) == value for name, value in {
        'format': '1', 'source.commit': SOURCE_COMMIT, 'data.commit': DATA_COMMIT,
        'repository.commit': repository_commit, 'total.count': str(DATA_COUNT),
        'total.bytes': str(DATA_BYTES),
        'asset.archive.sha256': '28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07',
        'asset.archive.bytes': '615541018',
        'asset.manifest.sha256': 'cf96742b1b65306356df69d065fcfb5bda0986ec8700d47ae1422452a1c0db7f',
    }.items()), 'APK import content or candidate repository contract differs')
    return digest


def import_receipt(generation, contract_sha256):
    """Accept only the exact four-field receipt written by AtlasAssetImporter."""
    require(not generation.is_symlink() and generation.is_dir(), 'Invalid imported generation')
    path = checked_file(generation / 'complete.properties', 4096)
    properties, digest = read_properties(path, 4096)
    require(set(properties) == {'generation', 'contract.sha256', 'count', 'bytes'}
            and re.fullmatch(r'generation-[0-9a-f]{32}', properties['generation'])
            and properties['generation'] == generation.name
            and properties['contract.sha256'] == contract_sha256
            and properties['count'] == str(DATA_COUNT) and properties['bytes'] == str(DATA_BYTES),
            'Imported generation identity or content contract differs')
    require(not (generation / 'data').is_symlink() and (generation / 'data').is_dir(),
            'Imported generation data is missing or linked')
    return {'generation': properties['generation'], 'contract_sha256': properties['contract.sha256'],
            'receipt_sha256': digest, 'file_count': DATA_COUNT,
            'total_bytes': DATA_BYTES, 'private_copy_verified': False,
            'source_generation_unchanged': False}


def candidate_metadata(assets):
    accepted = pinned_json(assets / 'accepted-runtime-manifest.json', BASE_MANIFEST_SHA256, 256 * 1024)
    current = dbserver.load_json(checked_file(assets / 'runtime-manifest.json', 1024 * 1024), 1024 * 1024)
    require(accepted.get('format') == current.get('format') == 1
            and accepted.get('repository_commit') == BASE_COMMIT
            and dbserver.COMMIT.fullmatch(current.get('repository_commit', '')),
            'Accepted base or candidate runtime identity differs')
    original_files, files = accepted.get('files', {}), current.get('files', {})
    require(isinstance(original_files, dict) and len(original_files) == 12 and isinstance(files, dict)
            and all(dbserver.exact_contract(files.get(name), record) for name, record in original_files.items()),
            'Candidate substituted accepted base runtime inputs')
    for name in set(accepted) - {'files', 'repository_commit', 'scope'}:
        require(dbserver.exact_contract(current.get(name), accepted[name]),
                'Candidate changed accepted base runtime contract: ' + name)
    guests = {}
    for name in GUEST_FILES:
        path = checked_file(assets / name, 256 * 1024)
        actual = base.file_hash(path)
        record = files.get(name, {})
        expected = record.get('sha256') if isinstance(record, dict) else record
        require(actual == expected, 'Candidate guest source differs: ' + name)
        guests[name] = actual
    return {'candidate_repository_commit': current['repository_commit'],
            'accepted_runtime_manifest_sha256': BASE_MANIFEST_SHA256,
            'accepted_game_repository_commit': GAME_COMMIT, 'guest_source_sha256': guests}


class ManifestDirectory:
    """Read-only adapter for the original constructor's one manifest lookup.

    The original constructor reads and fingerprints game-data-manifest.json;
    prepare_runtime below uses the actual imported generation separately.
    Keeping this narrow rejects any future unreviewed data-directory use.
    """
    def __init__(self, manifest):
        self.manifest = manifest

    def __truediv__(self, name):
        require(name == 'game-data-manifest.json', 'Unexpected imported-data adapter lookup')
        return self.manifest


class WineMemorySampler:
    """Bounded read-only samples; a missing measurement cannot fail gameplay proof.

    This deliberately excludes PostgreSQL, Python, Java and app memory. RSS is
    summed across token-owned Wine/FEX processes and can double-count shared
    pages. Its largest sample is not a measured instantaneous peak or PSS.
    Sampling runs on the guest loop, with no worker to delay Stop or cleanup.
    """
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        self.next_sample = 0
        self.scanner = object.__new__(base.WineProcessOwner)
        self.scanner.__dict__.update(diagnostic.wine_owner.__dict__)
        self.scanner.initialized = False
        self.scanner.receipt = dict(diagnostic.wine_owner.receipt)
        self.scanner.dead_leaders, self.scanner.owned_workers = set(), set()
        self.report = {'scope': 'run_token_owned_Wine_FEX_processes_only',
            'measurement': 'sampled_sum_of_process_VmRSS_kibibytes', 'minimum_interval_seconds': 5,
            'inspection_budget_seconds': 1, 'excludes': ['PostgreSQL', 'Python', 'Java', 'Android app'],
            'shared_pages_may_be_counted_more_than_once': True, 'instantaneous_peak_measured': False,
            'pss_measured': False, 'successful_samples': 0, 'unavailable_samples': 0,
            'maximum_sampled_rss_kib': None, 'samples': []}
        diagnostic.ctx.report['memory_observation'] = self.report

    def sample(self):
        now = time.monotonic()
        if not self.diagnostic.wine_started or now < self.next_sample:
            return
        self.next_sample = now + 5
        try:
            deadline = now + 1
            owned = self.scanner.scan(deadline)
            total, observed = 0, 0
            for identity in owned:
                require(time.monotonic() < deadline, 'Resource sample exceeded inspection budget')
                path = self.scanner.proc_root / str(identity['proc_pid'])
                try:
                    before = self.scanner.process_stat(path)
                    status = (path / 'status').read_text()
                    after = self.scanner.process_stat(path)
                except FileNotFoundError:
                    continue
                require(before['pid'] == after['pid'] == identity['proc_pid']
                        and before['starttime'] == after['starttime'] == identity['starttime'],
                        'Resource sample process identity changed')
                if before['state'] == 'Z' or after['state'] == 'Z':
                    continue
                values = re.findall(r'^VmRSS:\s+(\d+)\s+kB$', status, re.MULTILINE)
                require(len(values) == 1, 'Owned process RSS is unavailable')
                total += int(values[0])
                observed += 1
            require(observed > 0, 'No owned Wine RSS was observable')
            require(len(self.report['samples']) < 2048, 'Resource sample count exceeded bound')
            self.report['samples'].append({'stage': self.diagnostic.ctx.stage_name,
                                          'owned_processes': observed, 'rss_kib': total})
            self.report['successful_samples'] += 1
            self.report['maximum_sampled_rss_kib'] = max(total, self.report['maximum_sampled_rss_kib'] or 0)
        except Exception as exc:
            self.report['unavailable_samples'] += 1
            self.report['last_unavailable_type'] = type(exc).__name__


class DeviceGameContext(game.GameContext):
    memory_sampler = None

    def check(self):
        super().check()
        if self.memory_sampler is not None:
            self.memory_sampler.sample()


def copy_verified(source, target, record, check):
    """Copy without links, with cancellation between bounded reads and hashes."""
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as incoming:
        before = os.fstat(incoming.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_size == record['bytes'], 'Game input is linked, nonregular or has wrong size')
        total = 0
        with target.open('xb') as output:
            while True:
                check()
                chunk = incoming.read(COPY_BLOCK)
                if not chunk:
                    break
                total += len(chunk)
                require(total <= record['bytes'], 'Game input grew during copy')
                output.write(chunk)
        after = os.fstat(incoming.fileno())
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                and total == record['bytes'], 'Game input changed during copy')
    digest = hashlib.sha256()
    with target.open('rb') as copied:
        while True:
            check()
            chunk = copied.read(COPY_BLOCK)
            if not chunk:
                break
            digest.update(chunk)
    require(digest.hexdigest() == record['sha256'], 'Copied game data hash differs: ' + target.name)


class DeviceGameDiagnostic(game.GameDiagnostic):
    def __init__(self, args, context):
        args.listener_policy = dbserver.listener_policy(args.execution_platform, args.listener_policy)
        context.report['listener_policy'] = args.listener_policy
        adapter = candidate_metadata(args.assets)
        contract_sha256 = import_contract(args.import_contract, adapter['candidate_repository_commit'])
        imported = import_receipt(args.game_data, contract_sha256)
        package = pinned_json(args.game_package / 'game-package.json', PACKAGE_SHA256, 8 * 1024 * 1024)
        pinned_json(args.schema / 'schema-manifest.json', SCHEMA_SHA256, 8 * 1024 * 1024)
        checked_file(args.game_data_manifest, DATA_MANIFEST_BYTES)
        require(args.game_data_manifest.stat().st_size == DATA_MANIFEST_BYTES
                and base.file_hash(args.game_data_manifest) == DATA_MANIFEST_SHA256,
                'Accepted game data manifest differs')
        require(package.get('repository_commit') == GAME_COMMIT
                and package.get('source_commit') == SOURCE_COMMIT and package.get('data_commit') == DATA_COMMIT
                and package.get('dbserver_profile') == package.get('game_listener_profile') == 'loopback'
                and package.get('postgresql_persistence_fixture') is False,
                'Android Atlas requires the accepted loopback game package')
        if args.android_metadata is not None:
            context.report['android_context_unverified'] = dbserver.load_json(
                checked_file(args.android_metadata, 16384), 16384)
        self.import_generation = args.game_data
        adapted = argparse.Namespace(**vars(args))
        adapted.game_data = ManifestDirectory(args.game_data_manifest)
        super().__init__(adapted, context)
        self.imported = imported
        self.ctx.report['imported_content'] = imported
        self.ctx.report['device_adapter'] = adapter
        self.ctx.memory_sampler = WineMemorySampler(self)

    def prepare_runtime(self):
        self.ctx.stage('game_private_runtime')
        files = self.data.get('files')
        require(isinstance(files, dict) and len(files) == self.data.get('file_count') == DATA_COUNT
                and self.data.get('total_bytes') == DATA_BYTES, 'Invalid accepted game data inventory')
        minimum_free = DATA_BYTES + DATA_COUNT * 4096 + RUNTIME_RESERVE_BYTES
        require(shutil.disk_usage(self.root).free >= minimum_free,
                'Insufficient private storage for a fresh game copy and runtime reserve')
        self.runtime.mkdir(mode=0o700)
        (self.runtime / 'tools').mkdir(mode=0o700)
        created = {self.runtime, self.runtime / 'tools'}
        names, total = {}, 0
        next_progress = time.monotonic()
        for number, (name, record) in enumerate(files.items(), 1):
            self.ctx.check()
            require(game.safe_path(name).parts[0] == 'data' and name.casefold() not in names,
                    'Unexpected or case-colliding game data path')
            require(isinstance(record, dict) and type(record.get('bytes')) is int and record['bytes'] >= 0
                    and isinstance(record.get('sha256'), str) and dbserver.HEX64.fullmatch(record['sha256']),
                    'Invalid game data digest record')
            total += record['bytes']
            require(total <= DATA_BYTES, 'Game data exceeds accepted byte bound')
            source = game.regular_path(self.import_generation, name)
            target = self.runtime / name
            game.create_private_parents(target.parent, self.runtime, created)
            copy_verified(source, target, record, self.ctx.check)
            names[name.casefold()] = name
            if time.monotonic() >= next_progress:
                self.ctx.event('stage', status='running', message='Staging verified imported game inputs', files=number)
                next_progress = time.monotonic() + 5
        actual = game.inventory_files(self.import_generation, self.ctx.check)
        require(actual == set(files) | {'complete.properties'} and total == DATA_BYTES,
                'Imported game data inventory has extra/missing files or bytes')
        require(import_receipt(self.import_generation, self.imported['contract_sha256']) == self.imported,
                'Imported generation receipt changed')
        for name in self.schema['files']:
            target = self.runtime / names.get(name.casefold(), name)
            game.create_private_parents(target.parent, self.runtime, created)
            shutil.copyfile(self.args.schema / name, target)
        require(len(self.schema['files']) == 62, 'Fixed-input game schema must contain 62 accepted files')
        self.fixed_schema_paths = {names.get(name.casefold(), name) for name in self.schema['files']}
        for name in self.package['files']:
            shutil.copyfile(self.args.game_package / name, self.runtime / name)
        require(not (self.runtime / 'gamedatadir.txt').exists(), 'External game data roots are forbidden')
        self.imported.update(private_copy_verified=True, source_generation_unchanged=True)
        self.ctx.log_root = self.runtime
        self.ctx.passed(input_files=len(files), input_bytes=total, accepted_schema_overlay_files=62)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in (('state', '/state'), ('assets', '/opt/coh'), ('game-package', '/opt/coh-game-package'),
                          ('game-data', '/opt/coh-game-data'), ('schema', '/opt/coh-schema'),
                          ('game-data-manifest', '/opt/coh-game-data-manifest.json'),
                          ('import-contract', '/opt/coh-import-contract.properties'),
                          ('pg-bin', '/opt/coh/pgsql/bin'), ('wine', '/opt/wine/bin/wine'),
                          ('wineserver', '/opt/wine/bin/wineserver'), ('xserver', '/usr/bin/Xtigervnc')):
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--timeout-seconds', type=int, default=5400)
    parser.add_argument('--execution-platform', choices=('host', 'android'), required=True)
    parser.add_argument('--listener-policy', choices=('host-default', 'device'))
    parser.add_argument('--android-metadata', type=Path)
    args = parser.parse_args(argv)
    args.client_probe = False
    os.umask(0o077)
    context = DeviceGameContext(args.state, args.timeout_seconds)
    context.report.update(diagnostic_mode='atlas_character_persistence',
        execution_platform_requested=args.execution_platform,
        scope='Private imported Atlas data, managed local servers and diagnostic create/save/restart/exact-name resume on ARM64 Wine/FEX',
        android_execution_validated=False, gameplay_validated=False, android_surface_validated=False,
        hardware_acceleration_validated=False, interactive_rendering_validated=False,
        android_listener_binding_validated=False)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
    diagnostic = None
    try:
        require(60 <= args.timeout_seconds <= 7200, 'Timeout must be 60 to 7200 seconds')
        context.check()
        diagnostic = DeviceGameDiagnostic(args, context)
        diagnostic.execute()
        context.report['status'] = 'passed'
    except base.Cancelled as exc:
        context.report.update(status='cancelled', failures=[str(exc)])
    except Exception as exc:
        context.report.update(status='failed', failures=[str(exc)])
    finally:
        # Preserve whether runtimes were ever started before cleanup changes
        # their state. A Stop while copying inputs has nothing to shut down;
        # native acceptance must distinguish that from an unproved shutdown.
        context.report['cleanup_execution'] = {
            'diagnostic_initialized': diagnostic is not None,
            'wine_started': bool(diagnostic is not None and diagnostic.wine_started),
            'postgres_started': any(child.label in ('postgres_first_start', 'postgres_game_restart')
                                    for child in context.children),
            'owned_child_count': len(context.children)}
        if diagnostic is not None:
            if context.report['status'] == 'failed':
                try:
                    game.hang_evidence.capture(diagnostic)
                except Exception as exc:
                    context.report.setdefault('observation_failures', []).append(
                        'Cannot capture pre-cleanup game evidence: ' + str(exc))
            try:
                context.report['failures'].extend(diagnostic.cleanup())
            except Exception as exc:
                context.report['failures'].append('Owned cleanup failed: ' + str(exc))
            for label, export in (('game', diagnostic.export_captures), ('service', diagnostic.export_service_captures)):
                try:
                    export()
                except Exception as exc:
                    context.report['failures'].append('Cannot export bounded ' + label + ' evidence: ' + str(exc))
        # Cleanup can launch its own bounded stop/wait helpers. Bind the final
        # count to every owned child, including helpers whose capture failed.
        context.report['cleanup_execution']['owned_child_count'] = len(context.children)
        context.report['finished_utc'] = base.utc()
        context.report['cleanup_complete'] = all(child.process.poll() is not None and not child.reader.is_alive()
                                                and not child.writer.is_alive() for child in context.children)
        context.report['cleanup'] = diagnostic.cleanup_status if diagnostic else {
            'postgres_graceful': False, 'wine_prefix_stopped': False, 'owned_processes_reaped': False}
        context.report['passed'] = context.report['status'] == 'passed' and not context.report['failures'] \
            and context.report['cleanup_complete'] and all(context.report['cleanup'].values())
        if context.report['status'] == 'passed' and not context.report['passed']:
            context.report['status'] = 'failed'
            context.report['failures'].append('Required owned cleanup was not proved')
        try:
            text = json.dumps(base.redacted_value(context.report, context.secrets), indent=2) + '\n'
            require(len(text.encode()) <= 2 * 1024 * 1024, 'Report exceeded bound')
            base.private_write(args.state / 'latest-report.json', text)
        except Exception as exc:
            context.report.update(status='failed', passed=False)
            context.report['failures'].append('Cannot persist game report: ' + str(exc))
        context.event('result', status=context.report['status'], passed=context.report['passed'],
                      report='/state/latest-report.json', failures=context.report['failures'])
    return 0 if context.report['passed'] else 2 if context.report['status'] == 'cancelled' else 1


if __name__ == '__main__':
    sys.exit(main())
