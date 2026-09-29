"""Boundary and provenance checks for the combined APK import/runtime gate."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

import host_device_smoke as host


class ApkExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def apk(self, *, extra=None, duplicate=None, symlink=None, manifest=None):
        manifest = manifest or {'format': 1, 'files': {'diagnostic.py': {'bytes': 1, 'sha256': 'a' * 64}}}
        members = {'assets/runtime/runtime-manifest.json': json.dumps(manifest),
                   'assets/runtime/diagnostic.py': b'x', 'classes.dex': b'dex'}
        members.update({'assets/atlas/' + name: b'import' for name in host.package.PACKAGE_FILES})
        members.update(extra or {})
        path = self.root / 'candidate.apk'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, content in members.items():
                if name == symlink:
                    entry = zipfile.ZipInfo(name)
                    entry.create_system = 3
                    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                    archive.writestr(entry, content)
                else:
                    archive.writestr(name, content)
            if duplicate:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    archive.writestr(duplicate, members[duplicate])
        return path

    def test_extracts_exact_both_asset_sets_without_extracting_code(self):
        paths = host.extract_apk_assets(self.apk(), self.root / 'assets')
        self.assertEqual(set(paths), {'runtime', 'atlas'})
        self.assertEqual({p.name for p in paths['atlas'].iterdir()}, set(host.package.PACKAGE_FILES))
        self.assertEqual((paths['runtime'] / 'diagnostic.py').read_bytes(), b'x')
        self.assertFalse((self.root / 'assets/classes.dex').exists())

    def test_extra_or_escape_asset_is_rejected_before_any_write(self):
        for name in ('assets/unreviewed.dat', 'assets/atlas/../escape', 'assets/runtime/extra.py'):
            with self.subTest(name=name):
                destination = self.root / 'assets'
                with self.assertRaisesRegex(RuntimeError, 'asset set'):
                    host.extract_apk_assets(self.apk(extra={name: b'bad'}), destination)
                self.assertFalse(destination.exists())

    def test_duplicate_apk_member_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'Duplicate APK'):
            host.extract_apk_assets(self.apk(duplicate='classes.dex'), self.root / 'assets')

    def test_linked_import_and_runtime_payloads_are_rejected(self):
        for name in ('assets/runtime/diagnostic.py', 'assets/atlas/' + host.package.TEXT_ARCHIVE):
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, 'Linked'):
                host.extract_apk_assets(self.apk(symlink=name), self.root / 'assets')
            self.assertFalse((self.root / 'assets').exists())

    def test_nonflat_runtime_and_aggregate_budget_are_rejected(self):
        manifest = {'format': 1, 'files': {'../escape': {'bytes': 1, 'sha256': 'a' * 64}}}
        with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
            host.extract_apk_assets(self.apk(manifest=manifest), self.root / 'assets')
        with mock.patch.object(host, 'MAX_APK_ASSETS', 32):
            with self.assertRaisesRegex(RuntimeError, 'extraction budget'):
                host.extract_apk_assets(self.apk(), self.root / 'assets')

    def test_existing_output_cannot_be_overwritten(self):
        output = self.root / 'assets'
        output.mkdir()
        (output / 'preserved').write_bytes(b'keep')
        with self.assertRaisesRegex(RuntimeError, 'must be new'):
            host.extract_apk_assets(self.apk(), output)
        self.assertEqual((output / 'preserved').read_bytes(), b'keep')


class AdapterTests(unittest.TestCase):
    def progress_game(self, producer, *, evicted=False):
        sys.path.insert(0, str(host.ROOT / 'android/guest'))
        import game_map_progress as progress
        observed = progress.evidence(producer)
        startup = {'profile': progress.PROFILE, 'requires_completed_tick_before_protocol': True, 'phases': {}}
        phases = []
        for index, phase in enumerate(('first', 'restart')):
            start = 100.0 + index * 1000
            history = {'path_name': 'coh-map-progress-' + phase + '-fixture.bin', 'process_label': phase + '-atlas',
                       'launch_monotonic': start, 'fresh_path_before_launch': True,
                       'sample_count': 0, 'dropped_samples': 0, 'samples': []}
            observed['phases'][phase] = history
            before_number, after_number = (18, 19) if evicted else (2, 3)
            witnesses = {}
            for number in range(1, 241 if evicted else 5):
                raw = progress.HEADER.pack(b'COHMAP1\0', 1, 128, 40 + index, 42 + index,
                    number * 2, 34, number - 1, number - 1, 0, 37) + bytes(80)
                sample = dict(progress.decode_record(raw), available=True, is_success_proof=False,
                    file_identity={'device': 1, 'inode': 200 + index}, observed_monotonic=start + number,
                    last_advance_monotonic=start + number, unchanged_seconds=0,
                    freshness='initial' if number == 1 else 'advanced', reason='synthetic-test')
                key = 'before' if number == before_number else 'after' if number == after_number else None
                if key is not None:
                    sample['reason'] = 'startup-tick-' + key + ':' + phase + '-ready'
                progress.append_sample(history, sample)
                if key is not None:
                    witnesses[key] = copy.deepcopy(sample)
            protocol = {'ready': True, 'map_id': 1, 'address': '127.0.0.1', 'port': 7001,
                        'network_age_seconds': 0, 'stats_age_seconds': 0, 'monotonic': start + before_number + .5}
            startup['phases'][phase] = {'status': 'passed', 'attempts': 1,
                **witnesses,
                'protocol': copy.deepcopy(protocol)}
            phases.append({'phase': phase + '_services_ready', 'map': protocol})
        return {'mapserver_progress': observed, 'mapserver_startup': startup, 'phases': phases}

    def sample(self, profile=None):
        imported = {'generation': 'generation-' + 'a' * 32, 'contract_sha256': 'b' * 64,
                    'receipt_sha256': 'c' * 64, 'file_count': 173011, 'total_bytes': 2977730517}
        bundle = host.assets_builder.bundle_contract(profile)
        runtime = {'atlas_device_bundle': bundle, 'files': {name: {'sha256': str(number) * 64}
                            for number, name in enumerate(host.assets_builder.GUEST_SCRIPTS)}}
        report = {'listener_policy': 'device', 'android_listener_binding_validated': False,
                  'imported_content': {**imported, 'private_copy_verified': True,
                                       'source_generation_unchanged': True},
                  'device_adapter': {'candidate_repository_commit': 'd' * 40,
                                     'accepted_runtime_manifest_sha256': host.dbhost.ACCEPTED_RUNTIME_MANIFEST,
                                     'accepted_game_repository_commit': host.assets_builder.PACKAGE_COMMIT,
                                     'selected_package_run_id': bundle['package_run_id'],
                                     'selected_package_repository_commit': bundle['package_repository_commit'],
                                     'selected_package_manifest_sha256': bundle['package_manifest_sha256'],
                                     'guest_source_sha256': {name: value['sha256']
                                                              for name, value in runtime['files'].items()}}}
        if profile is not None:
            report['device_adapter'].update(mapserver_progress_profile=profile,
                                            mapserver_progress_producer=bundle['mapserver_progress_producer'])
        return report, {'candidate_commit': 'd' * 40, 'runtime': runtime, 'import_report': imported,
                        'mapserver_progress_profile': profile}

    def test_complete_provenance_passes(self):
        report, expected = self.sample()
        host.validate_adapter_report(report, **expected)

    def test_host_cannot_claim_android_or_skip_device_listener_policy(self):
        for key, value in (('listener_policy', 'host-default'), ('android_listener_binding_validated', True)):
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'device-proof scope'):
                report, expected = self.sample()
                report[key] = value
                host.validate_adapter_report(report, **expected)

    def test_wrong_generation_changed_source_or_relaxed_boolean_is_rejected(self):
        mutations = [('generation', 'generation-' + 'e' * 32), ('contract_sha256', 'e' * 64),
                     ('receipt_sha256', 'e' * 64), ('file_count', 1), ('private_copy_verified', 1),
                     ('source_generation_unchanged', False)]
        for key, value in mutations:
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'generation'):
                report, expected = self.sample()
                report['imported_content'][key] = value
                host.validate_adapter_report(report, **expected)

    def test_new_candidate_cannot_relabel_the_accepted_donor_or_guest(self):
        report, expected = self.sample()
        for key in ('candidate_repository_commit', 'accepted_game_repository_commit',
                    'accepted_runtime_manifest_sha256', 'guest_source_sha256', 'selected_package_run_id',
                    'selected_package_repository_commit', 'selected_package_manifest_sha256'):
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'provenance'):
                changed = copy.deepcopy(report)
                changed['device_adapter'][key] = 'substituted'
                host.validate_adapter_report(changed, **expected)

    def test_progress_profile_keeps_wrapper_donor_and_support_identities_distinct(self):
        profile = host.game.MAPSERVER_PROGRESS_PROFILE
        report, expected = self.sample(profile)
        with mock.patch.object(host, 'validate_startup_progress') as startup:
            host.validate_adapter_report(report, **expected)
            startup.assert_called_once_with({}, expected['runtime']['atlas_device_bundle']['mapserver_progress_producer'])
        adapter = report['device_adapter']
        self.assertNotEqual(adapter['candidate_repository_commit'], adapter['selected_package_repository_commit'])
        self.assertNotEqual(adapter['accepted_game_repository_commit'], adapter['selected_package_repository_commit'])
        for key in ('mapserver_progress_profile', 'mapserver_progress_producer'):
            changed = copy.deepcopy(report)
            changed['device_adapter'][key] = 'substituted'
            with self.assertRaisesRegex(RuntimeError, 'provenance'):
                host.validate_adapter_report(changed, **expected)
        expected['mapserver_progress_profile'] = None
        with self.assertRaisesRegex(RuntimeError, 'bundle'):
            host.validate_adapter_report(report, **expected)

    def test_startup_guard_requires_raw_positive_ticks_same_identity_and_enclosed_current_protocol(self):
        profile = host.game.MAPSERVER_PROGRESS_PROFILE
        report, expected = self.sample(profile)
        producer = expected['runtime']['atlas_device_bundle']['mapserver_progress_producer']
        report['game'] = self.progress_game(producer)
        host.validate_adapter_report(report, **expected)
        mutations = {
            'missing-phase': lambda g: g['mapserver_startup']['phases'].pop('restart'),
            'missing-after': lambda g: g['mapserver_startup']['phases']['first'].update(after={}),
            'pending': lambda g: g['mapserver_startup']['phases']['first'].update(status='waiting'),
            'zero-tick': lambda g: g['mapserver_startup']['phases']['first'].update(
                before=copy.deepcopy(g['mapserver_progress']['phases']['first']['samples'][0])),
            'digest': lambda g: g['mapserver_startup']['phases']['first']['before'].update(raw_record_sha256='f' * 64),
            'different-phase': lambda g: g['mapserver_startup']['phases']['first'].update(
                after=copy.deepcopy(g['mapserver_startup']['phases']['restart']['after'])),
            'after-outside-history': lambda g: g['mapserver_startup']['phases']['first']['after'].update(observed_monotonic=1000),
            'query-too-early': lambda g: g['mapserver_startup']['phases']['first']['protocol'].update(monotonic=100),
            'query-after-read': lambda g: g['mapserver_startup']['phases']['first']['protocol'].update(monotonic=105),
            'stale-protocol': lambda g: (g['mapserver_startup']['phases']['first']['protocol'].update(stats_age_seconds=21),
                                        g['phases'][0]['map'].update(stats_age_seconds=21)),
            'different-protocol': lambda g: g['phases'][0]['map'].update(stats_age_seconds=1),
            'retained-time-disagrees': lambda g: g['mapserver_startup']['phases']['first']['before'].update(observed_monotonic=102.25),
            'retained-clock-rewritten': lambda g: g['mapserver_startup']['phases']['first']['before'].update(
                observed_monotonic=102.25, last_advance_monotonic=102.25),
            'zero-ordinal': lambda g: g['mapserver_startup']['phases']['first']['before'].update(sample_number=0),
            'out-of-range-ordinal': lambda g: g['mapserver_startup']['phases']['first']['after'].update(sample_number=5),
            'inverted-ordinal': lambda g: g['mapserver_startup']['phases']['first']['before'].update(sample_number=4),
            'wrong-reason': lambda g: g['mapserver_startup']['phases']['first']['before'].update(reason='unrelated'),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), self.assertRaises(RuntimeError):
                changed = copy.deepcopy(report['game'])
                mutate(changed)
                host.validate_startup_progress(changed, producer)

    def test_startup_proof_remains_valid_after_its_history_entries_are_evicted(self):
        producer = host.assets_builder.bundle_contract(host.game.MAPSERVER_PROGRESS_PROFILE)['mapserver_progress_producer']
        game_report = self.progress_game(producer, evicted=True)
        host.validate_startup_progress(game_report, producer)
        for phase in ('first', 'restart'):
            self.assertNotIn(18, [sample['sample_number'] for sample in
                                 game_report['mapserver_progress']['phases'][phase]['samples']])
        for field, value in (('unchanged_seconds', 8), ('last_advance_monotonic', float('nan')),
                             ('freshness', 'unknown'), ('sample_number', 0), ('sample_number', 241),
                             ('sample_number', 20), ('reason', 'unrelated')):
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                changed = copy.deepcopy(game_report)
                changed['mapserver_startup']['phases']['first']['before'][field] = value
                host.validate_startup_progress(changed, producer)

    def test_protected_history_entries_cannot_be_relabelled_as_evicted(self):
        producer = host.assets_builder.bundle_contract(host.game.MAPSERVER_PROGRESS_PROFILE)['mapserver_progress_producer']
        game_report = self.progress_game(producer)
        for phase in ('first', 'restart'):
            history = game_report['mapserver_progress']['phases'][phase]
            del history['samples'][1:3]
            history['dropped_samples'] = 2
        with self.assertRaisesRegex(RuntimeError, 'retention policy'):
            host.validate_startup_progress(game_report, producer)

    def test_helper_execution_uses_apk_bytes_and_missing_helper_cannot_fall_back_to_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets, work = root / 'assets', root / 'work'
            assets.mkdir()
            (work / 'm3-tools').mkdir(parents=True)
            runtime = {'files': {}}
            for name in host.assets_builder.GUEST_SCRIPTS:
                payload = ('APK source ' + name).encode()
                (assets / name).write_bytes(payload)
                runtime['files'][name] = {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
            helper = work / 'm3-tools/game_map_progress.py'
            helper.write_bytes(b'unrelated checkout helper')
            receipt = host.install_apk_guest_scripts(assets, work, runtime)
            self.assertEqual(helper.read_bytes(), (assets / helper.name).read_bytes())
            self.assertEqual(receipt[helper.name], runtime['files'][helper.name]['sha256'])
            (assets / helper.name).unlink()
            helper.write_bytes(b'unrelated checkout helper')
            with self.assertRaisesRegex(RuntimeError, 'Missing or linked input'):
                host.install_apk_guest_scripts(assets, work, runtime)
            (assets / helper.name).write_bytes(b'altered APK source')
            with self.assertRaisesRegex(RuntimeError, 'differs from declared payload'):
                host.install_apk_guest_scripts(assets, work, runtime)

    def test_command_uses_exact_adapter_receipt_manifest_and_device_policy(self):
        root = Path('/fixture')
        generation = root / 'installed' / ('generation-' + 'a' * 32)
        command = host.make_command(work=root / 'work', assets=root / 'runtime', package=root / 'package',
                                    generation=generation, schema=root / 'schema', data_manifest=root / 'manifest.json',
                                    import_contract=root / 'atlas-import.properties', proot=root / 'native',
                                    timeout_seconds=5400)
        self.assertIn('/opt/coh-m3/game_device_diagnostic.py', command)
        self.assertNotIn('/opt/coh-m3/game_diagnostic.py', command)
        self.assertEqual(command[command.index('--execution-platform') + 1], 'host')
        self.assertEqual(command[command.index('--listener-policy') + 1], 'device')
        self.assertEqual(command[command.index('--timeout-seconds') + 1], '5400')
        self.assertEqual(command[command.index('--game-data') + 1], '/opt/coh-game-data/' + generation.name)
        self.assertIn(str(generation) + ':/opt/coh-game-data/' + generation.name, command)
        self.assertIn(str(root / 'manifest.json') + ':/opt/coh-game-data-manifest.json', command)
        self.assertIn(str(root / 'atlas-import.properties') + ':/opt/coh-import-contract.properties', command)

    def test_host_namespace_wrapper_remains_mandatory_and_drops_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            with mock.patch.object(host.dbhost.os, 'getuid', return_value=1001), \
                    mock.patch.object(host.dbhost.os, 'geteuid', return_value=1001), \
                    mock.patch.object(host.dbhost.os, 'getgid', return_value=1001), \
                    mock.patch.object(host.dbhost.os, 'readlink', return_value='net:[123]'):
                command, environment, expected = host.dbhost.isolate_command(
                    ['proot', '--game-device'], evidence=path, proot=path, work=path)
            self.assertEqual(command[:5], ['sudo', '-n', 'unshare', '--net', '--'])
            self.assertNotIn('GH_TOKEN', environment)
            self.assertNotIn('GITHUB_TOKEN', environment)
            with self.assertRaisesRegex(RuntimeError, 'isolation receipt'):
                host.dbhost.validate_network_receipt({}, expected)


if __name__ == '__main__':
    unittest.main()
