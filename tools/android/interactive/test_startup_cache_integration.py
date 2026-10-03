"""Cross-feature checks on disposable owned server trees and synthetic donors.

Synthetic native receipts exercise verifier interfaces only. They do not prove
native consumption or qualify a release donor; the hosted generator does that.
"""
import json
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

import test_server_worktree_reuse as worktree
from test_server_cache_package import synthetic_archive
import server_cache_package as donor

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location('startup_cache_raw_observer_integration',
    ROOT/'tools/android/atlasgame/prepare_server_caches.py')
observer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(observer)


def synthetic_raw_proof(directory):
    """Produce observer fixtures, never real native execution evidence."""
    directory.mkdir()
    archive = directory/donor.ARCHIVE
    manifest = synthetic_archive(archive)
    runtime = directory/'synthetic-runtime'
    wine_prefix = directory/'synthetic-wine-prefix'
    wine_prefix.mkdir(mode=0o700)
    wine_base = directory/'synthetic-wineserver'
    wine_base.mkdir(mode=0o700)
    prefix_stat = wine_prefix.stat()
    wine_server = wine_base/f'server-{prefix_stat.st_dev:x}-{prefix_stat.st_ino:x}'
    wine_server.mkdir(mode=0o700)
    (wine_server/'lock').write_bytes(b'')
    cleanup = observer.prove_prefix_server_unlocked(wine_prefix, server_base=wine_base)
    phases = {}
    for stage in ('generation', 'consumption'):
        evidence = directory/'evidence'/stage
        evidence.mkdir(parents=True)
        events = []
        for kind, extra in (('LAUNCH', {}), ('CONSOLE', {'owned': True}),
                            ('ESCAPE', {'sent': True}), ('EXIT', {'exit_code': 0, 'escape_sent': True})):
            if kind == 'ESCAPE':
                events.append(b'470 arcs, 957 contacts, 3528 tasks; 46930 spawn definitions')
                events.append(observer.DONE)
            record = {'session_id': '1'*32, 'pid': 1234, **extra}
            events.append(('COH_SERVER_CACHE_'+kind+'_V1 ').encode()+json.dumps(record).encode())
        stdout = b'\n'.join(events)+b'\n'
        (evidence/'stdout.log').write_bytes(stdout)
        (evidence/'stderr.log').write_bytes(b'')
        phase = observer.phase_receipt(stdout, b'', stage, '1'*32, 0, True)
        phase['elapsed_seconds'] = 0.1
        phases[stage] = phase
        observer.write_json(evidence/'phase-receipt.json', phase)
        observer.write_json(evidence/'invocation.json', {'stage': stage, 'session_id': '1'*32,
            'identity': manifest['identity'], 'runtime_host_path': str(runtime),
            'timezone': 'UTC', 'wine_debug': '-all', 'wine_prefix': str(wine_prefix)})
        (evidence/'wine-helpers-stop.log').write_bytes(b'')
        observer.write_json(evidence/'wine-helpers-stop.json', {'format': 1,
            'kill_exit_code': 0, 'wait_exit_code': 0, 'normal_launcher_exit_observed_first': True,
            **cleanup})
    evidence = directory/'evidence/consumption'
    trace_file = evidence/'trace.1234'
    trace_file.write_text('openat(AT_FDCWD, "'+str(wine_server/'lock')+'", O_RDWR) = 9<'+
        str(wine_server/'lock')+'>\n'+''.join('read(3<'+str(runtime/name)+'>, "fixture", '+
        str(record['bytes'])+') = '+str(record['bytes'])+'\n'
        for name, record in manifest['files'].items()))
    sources = observer.archive_source_paths(archive, manifest['files'])
    trace = observer.trace_receipt([trace_file], runtime, manifest['files'], sources,
                                   manifest['identity']['identifier_files'])
    observer.write_json(evidence/'trace-receipt.json', trace)
    phases['consumption'] = {**phases['consumption'], 'cache_files_unchanged': True,
        **{key: trace[key] for key in ('cache_content_reads', 'cache_writes', 'source_content_reads')},
        'trace_receipt_sha256': hashlib.sha256(donor.canonical(trace)).hexdigest()}
    def proofs(value, payloads):
        value.update(native_generation=phases['generation'], native_consumption=phases['consumption'])
    manifest = synthetic_archive(archive, mutate=proofs)
    observer.write_json(directory/donor.MANIFEST, manifest)
    observer.write_json(directory/'evidence/generated-cache-inventory.json',
                        {'files': manifest['files'], 'source_paths': sources})
    launcher = directory/'evidence/server-cache-launcher.exe'
    launcher.write_bytes(b'SYNTHETIC OBSERVER FIXTURE; NOT AN EXECUTABLE')
    snapshot = {name: {**{key: record[key] for key in ('bytes', 'sha256')},
                       'mtime_ns': donor.EPOCH*1000000000} for name, record in manifest['files'].items()}
    report = {'format': 1, 'status': 'native_server_caches_generated_and_consumed',
        'repository_commit': manifest['repository_commit'], 'donor_apk': observer.DONOR_APK,
        'donor_build_report': observer.DONOR_REPORT, 'archive': observer.pin(archive),
        'identity': manifest['identity'],
        'launcher': observer.pin(launcher),
        'source_files': {name: observer.pin(ROOT/name) for name in observer.GENERATOR_SOURCES},
        'evidence_files': observer.evidence_pins(directory), 'source_paths': sources,
        'identifier_snapshots': {stage+'_'+moment: manifest['identity']['identifier_files']
            for stage in phases for moment in ('before', 'after')},
        'noncache_snapshots': {stage+'_'+moment: {'synthetic_inventory': 'same'}
            for stage in phases for moment in ('before', 'after')},
        'cache_snapshots': {'before': snapshot, 'after': snapshot},
        'physical_startup_timing_validated': False, 'dialog_semantics_validated': False}
    observer.write_json(directory/observer.REPORT, report)
    return manifest, report


class StartupCacheIntegrationTests(unittest.TestCase):
    setUp = worktree.ServerWorktreeReuseTests.setUp
    source = worktree.ServerWorktreeReuseTests.source
    base_prepare = worktree.ServerWorktreeReuseTests.base_prepare
    prepare = worktree.ServerWorktreeReuseTests.prepare
    close = worktree.ServerWorktreeReuseTests.close

    def make(self, sequence):
        value = worktree.ServerWorktreeReuseTests.make(self, sequence)
        value.owner.args.assets = self.root/'assets'
        value.owner.args.assets.mkdir(exist_ok=True)
        return value

    def schema_identifier(self):
        name = 'data/server/db/templates/vars.attribute'
        self.schema_files = (*self.schema_files, name)
        path = self.schema_dir/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'0 fixed_character_attribute\n')

    def package(self, runtime_data, name='qualified-fixture.zip'):
        identity = {**donor.compatibility_identity(),
                    'identifier_files': donor.identifier_snapshot(runtime_data)}
        archive = self.root/name
        synthetic_archive(archive, identity=identity)
        return archive, identity

    def test_missing_definition_and_message_seeds_preserve_native_bins_and_identifiers(self):
        self.schema_identifier()
        value = self.make(1); self.prepare(value); data = value.runtime/'data'
        (data/'server/bin').mkdir(exist_ok=True)
        powers = data/'server/bin/powers.bin'; powers.write_bytes(b'device-generated-powers')
        messages = data/'server/bin/storyarcmsg-en.bin'; messages.write_bytes(b'device-generated-dialog-text')
        identifiers = donor.identifier_snapshot(data)
        archive, identity = self.package(data)
        result = donor.install(archive, data, identity, value.ctx)
        self.assertGreater(result['installed_files'], 0)
        self.assertEqual(powers.read_bytes(), b'device-generated-powers')
        self.assertEqual(messages.read_bytes(), b'device-generated-dialog-text')
        self.assertEqual(identifiers, donor.identifier_snapshot(data))
        self.assertEqual((data/'server/db/templates/vars.attribute').read_bytes(),
                         (self.schema_dir/'data/server/db/templates/vars.attribute').read_bytes())
        self.assertTrue(result['native_loader_fallback_retained'])
        self.close(value)

    def test_seeded_custom_messages_survive_clean_cache_return_and_next_owned_checkout(self):
        self.schema_identifier()
        first = self.make(1); self.prepare(first); data = first.runtime/'data'
        archive, identity = self.package(data)
        donor.install(archive, data, identity, first.ctx)
        before = {name: (data/name.removeprefix('data/')).read_bytes()
                  for name in donor.REQUIRED_MESSAGES}
        inode = data.stat().st_ino
        self.close(first)
        second = self.make(2)
        with patch.object(second, 'stage_map_data', side_effect=AssertionError('recreated immutable inputs')):
            result = self.prepare(second)
        self.assertTrue(result['server_data_cache']['reused'])
        data = second.runtime/'data'
        self.assertEqual(data.stat().st_ino, inode)
        self.assertEqual(donor.identifier_snapshot(data), identity['identifier_files'])
        for name, raw in before.items():
            self.assertEqual((data/name.removeprefix('data/')).read_bytes(), raw)
        reseed = donor.install(archive, data, identity, second.ctx)
        self.assertEqual(reseed['installed_files'], 0)
        self.assertEqual(reseed['status'], 'preserved_existing_native_caches')
        self.assertEqual((data/'server/db/servers.cfg').read_bytes(),
                         (self.schema_dir/'data/server/db/servers.cfg').read_bytes())
        self.close(second)
        self.assertFalse((second.data_cache.path/'data/server/db/servers.cfg').exists())

    def test_incompatible_donor_is_optional_and_does_not_touch_owned_data(self):
        self.schema_identifier()
        value = self.make(1); self.prepare(value); data = value.runtime/'data'
        archive, identity = self.package(data)
        changed = dict(identity, parser_contract='incompatible-native-schema')
        before = donor.identifier_snapshot(data)
        inode = data.stat().st_ino
        result = donor.install(archive, data, changed, value.ctx)
        self.assertEqual(result['status'], 'skipped_native_fallback')
        self.assertEqual(result['installed_files'], 0)
        self.assertEqual(data.stat().st_ino, inode)
        self.assertEqual(donor.identifier_snapshot(data), before)
        self.assertFalse((data/'server/bin/powers.bin').exists())
        self.close(value)

    def test_current_schema_restoration_precedes_donor_identity_comparison(self):
        self.schema_identifier()
        first = self.make(1); self.prepare(first); data = first.runtime/'data'
        archive, identity = self.package(data)
        (data/'server/db/templates/vars.attribute').write_bytes(b'private old-generation scratch')
        self.close(first)
        second = self.make(2); result = self.prepare(second)
        self.assertTrue(result['server_data_cache']['reused'])
        data = second.runtime/'data'
        self.assertEqual(donor.identifier_snapshot(data), identity['identifier_files'])
        seeded = donor.install(archive, data, identity, second.ctx)
        self.assertGreater(seeded['installed_files'], 0)
        self.assertEqual((data/'server/db/templates/vars.attribute').read_bytes(),
                         (self.schema_dir/'data/server/db/templates/vars.attribute').read_bytes())
        self.close(second)

    def test_wrapper_receipt_change_retains_owned_seeded_dictionary_data(self):
        self.schema_identifier()
        first = self.make(1); self.prepare(first); data = first.runtime/'data'
        archive, identity = self.package(data)
        donor.install(archive, data, identity, first.ctx)
        key, inode = first.data_cache.key, data.stat().st_ino
        selected = (data/'server/bin/spawndefs.bin').read_bytes()
        self.close(first)
        (self.work/'client-work.json').write_text('{"verified":"new-wrapper-same-content"}\n')
        second = self.make(2)
        with patch.object(second, 'stage_map_data', side_effect=AssertionError('wrapper restaged data')):
            result = self.prepare(second)
        self.assertEqual(second.data_cache.key, key)
        self.assertTrue(result['server_data_cache']['reused'])
        self.assertEqual((second.runtime/'data').stat().st_ino, inode)
        self.assertEqual((second.runtime/'data/server/bin/spawndefs.bin').read_bytes(), selected)
        self.close(second)

    def test_cancelled_seeding_does_not_publish_partial_file_or_authorize_old_lease(self):
        self.schema_identifier()
        first = self.make(1); self.prepare(first); data = first.runtime/'data'
        archive, identity = self.package(data)
        calls = 0
        def cancel():
            nonlocal calls
            calls += 1
            if calls >= 2:
                raise worktree.server.base.Cancelled('fixture cancellation')
        first.ctx.check.side_effect = cancel
        with self.assertRaises(worktree.server.base.Cancelled):
            donor.install(archive, data, identity, first.ctx)
        self.assertFalse(list(data.rglob('.server-cache-pending-*')))
        old_tree = data
        old_marker = first.data_cache.marker.read_bytes()
        second = self.make(2); result = self.prepare(second)
        self.assertFalse(result['server_data_cache']['reused'])
        self.assertIn('prior owner', result['server_data_cache']['reuse_refused'])
        self.assertEqual(first.data_cache.marker.read_bytes(), old_marker)
        self.assertTrue(old_tree.is_dir())
        self.assertNotEqual((second.runtime/'data').stat().st_ino, old_tree.stat().st_ino)
        self.assertEqual(json.loads(old_marker)['status'], 'checked_out')
        self.close(second)

    def test_raw_native_observer_recomputes_scope_identity_errors_and_acceptance_claims(self):
        for case in ('source_scope', 'invocation_identity', 'hidden_error', 'physical_claim',
                     'non_epoch_cache', 'premature_cleanup'):
            directory = self.root/('raw-proof-'+case)
            manifest, report = synthetic_raw_proof(directory)
            self.assertEqual(manifest, observer.verify_generated_package(directory))
            if case == 'source_scope':
                report['source_paths'] = []
            elif case == 'invocation_identity':
                path = directory/'evidence/consumption/invocation.json'
                invocation = observer.read_json(path)
                invocation['identity'] = dict(invocation['identity'], mapserver_sha256='0'*64)
                observer.write_json(path, invocation)
                report['evidence_files'] = observer.evidence_pins(directory)
            elif case == 'hidden_error':
                (directory/'evidence/generation/stderr.log').write_bytes(b'Invalid power definition\n')
                report['evidence_files'] = observer.evidence_pins(directory)
            elif case == 'physical_claim':
                report['physical_startup_timing_validated'] = True
            elif case == 'premature_cleanup':
                path = directory/'evidence/consumption/wine-helpers-stop.json'
                receipt = observer.read_json(path)
                receipt['normal_launcher_exit_observed_first'] = False
                observer.write_json(path, receipt)
                report['evidence_files'] = observer.evidence_pins(directory)
            else:
                for snapshot in report['cache_snapshots'].values():
                    for record in snapshot.values():
                        record['mtime_ns'] += 1000000000
            observer.write_json(directory/observer.REPORT, report)
            with self.subTest(case=case), self.assertRaises(ValueError):
                observer.verify_generated_package(directory)


if __name__ == '__main__':
    unittest.main()
