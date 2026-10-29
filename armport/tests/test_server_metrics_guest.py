#!/usr/bin/env python3
"""Guest admission/consumer negatives with real donor metadata and synthetic PEs.

The trusted-binding fixture models a completed producer gate; it does not build
or execute Windows code, and cannot qualify a real shipping server artifact.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'android/guest'), str(ROOT/'armport/app'), str(ROOT/'armport/tests')]
import armport_server_metrics_contract as contract
import server_package as producer
from test_server_package import pe
import game_diagnostic
import native_map_startup_contract as startup
import native_monorail_contract as monorail
import server_cache_package as caches
import server_animation_package as animation
import server_fx_catalog as fx
import local_character_server as local


def history(relative):
    path = ROOT/relative
    raw = path.read_bytes() if path.exists() else subprocess.run(
        ['git', 'show', 'HEAD:'+relative], cwd=ROOT, capture_output=True, check=True).stdout
    return raw


class GuestMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        retained = history('docs/android-evidence/mapserver-progress-package-36630872719.json')
        modern = json.loads(history('docs/android-evidence/client-map-startup-0.13.32-publication.json'))
        modern = modern['complete_preparation']['native_admission']['game_package']
        cls.parents = {'retained_progress': retained,
                       'thor_certified_startup': (json.dumps(modern, indent=2)+'\n').encode()}

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name); self.assets = self.work/'assets'; self.assets.mkdir()
        self.runtime = self.work/('local-login-server-'+'a'*32); self.runtime.mkdir()
        patch = mock.patch.object(contract, 'ASSETS', self.assets); patch.start(); self.addCleanup(patch.stop)
        self.select('thor_certified_startup')

    def select(self, variant):
        self.variant = variant
        raw = self.parents[variant]; previous, baseline = producer.validate_predecessor(raw, variant)
        self.previous = previous
        self.executable = pe(b'new-observer', imports=tuple(previous['files']['MapServer.exe']['imports']))
        self.source = {'format': 1, 'role': contract.WRAPPER, 'variant': variant,
            'source_commit': contract.SOURCE, 'baseline_receipt': baseline,
            'patch': {'path': 'armport/patches/0119-armport-server-tick-file-metrics.patch', 'sha256': contract.PATCH},
            'patched_sha256': {'MapServer/src/svr/svr_init.c': 'a'*64},
            'contract': {'gameplay_decisions_changed': False, 'disabled_by_default': True},
            'build_targets': ['MapServer'], 'native_execution_validated': False}
        report = {'format': 1, 'role': 'armport_server_metrics_source_checks', 'status': 'passed',
            'variant': variant, 'build_input_sha256': contract.digest(contract.canonical(self.source)),
            'source_sha256': self.source['patched_sha256'], 'unpatched_control_failed': True,
            'shipping_binary_executed': False, 'scope': 'synthetic host admission reader fixture'}
        report_raw = contract.canonical(report)
        # Only the source-test execution gate is mocked: all actual donor,
        # package, report pin, runtime binding and current PE checks are real.
        with mock.patch.object(producer, 'validate_source', return_value=self.source), \
             mock.patch.object(producer, 'source_module') as module:
            module.return_value.validate_test_report.return_value = report
            build = producer.make_manifest(self.executable, b'pdb-fixture', self.source, raw,
                b'COH_PG_PERSISTENCE_TESTS:BOOL=OFF\n', report_raw,
                variant=variant, repository_commit='2'*40, run_id=123)
        self.build = build
        build_raw = producer.canonical(build)
        self.binding = {'format': 1, 'role': contract.ROLE,
            'server_package': contract.pin(b'package-fixture'), 'game_archive': contract.pin(b'game-fixture'),
            'build_manifest': contract.pin(build_raw), 'build_manifest_utf8': build_raw.decode(),
            'previous_manifest': contract.pin(raw), 'previous_manifest_utf8': raw.decode(),
            'source_report': contract.pin(report_raw), 'source_report_utf8': report_raw.decode()}
        self.game = copy.deepcopy(previous)
        self.game[contract.WRAPPER] = {'receipt': build, 'receipt_sha256': contract.digest(build_raw)}
        self.game['files']['MapServer.exe'] = build['files']['MapServer.exe']
        self.path = self.runtime/'MapServer.exe'; self.path.write_bytes(self.executable)
        (self.assets/'game-package.tar.gz').write_bytes(b'game-fixture')
        self.publish()

    def publish(self):
        raw = (json.dumps(self.binding, indent=2)+'\n').encode()
        (self.assets/contract.BINDING).write_bytes(raw)
        runtime = {'format': 1, 'repository_commit': self.build['repository_commit'],
            'files': {contract.BINDING: contract.pin(raw), 'game-package.tar.gz': self.binding['game_archive']},
            contract.WRAPPER: contract.summary(self.binding)}
        (self.assets/'runtime-manifest.json').write_text(json.dumps(runtime))

    def test_each_lineage_checks_actual_pe_then_returns_exact_ancestry(self):
        for variant in sorted(contract.VARIANTS):
            with self.subTest(variant=variant):
                self.select(variant)
                previous, proof = contract.verified_previous(self.path, self.game)
                self.assertEqual(previous, self.previous)
                self.assertEqual(proof['actual_mapserver_sha256'], producer.digest(self.executable))
                self.assertEqual(proof['previous_mapserver_sha256'], self.previous['files']['MapServer.exe']['sha256'])
                self.assertFalse(proof['runtime_execution_validated'])
                self.assertFalse(proof['physical_device_validated'])
                self.assertEqual(proof['variant'], variant)

    def test_bad_current_pe_is_rejected_before_historical_metadata_validation(self):
        self.path.write_bytes(b'changed')
        with mock.patch.object(startup, 'embedded_receipt', side_effect=AssertionError('projected too soon')):
            with self.assertRaisesRegex(ValueError, 'Current metrics MapServer bytes'):
                contract.verified_previous(self.path, self.game)

    def test_missing_or_linked_current_pe_rejected(self):
        self.path.unlink()
        with self.assertRaises(ValueError): contract.verify_current_map(self.path, self.game)
        other = self.runtime/'other.exe'; other.write_bytes(self.executable); self.path.symlink_to(other)
        with self.assertRaises(ValueError): contract.verify_current_map(self.path, self.game)

    def test_run_head_and_variant_changes_fail_even_when_wrapper_is_resealed(self):
        for key, value in (('run_id', 124), ('repository_commit', '3'*40), ('variant', 'retained_progress')):
            with self.subTest(key=key):
                game = copy.deepcopy(self.game); game[contract.WRAPPER]['receipt'][key] = value
                game[contract.WRAPPER]['receipt_sha256'] = contract.digest(contract.canonical(game[contract.WRAPPER]['receipt']))
                with self.assertRaisesRegex(ValueError, 'admitted build/run/head'):
                    contract.verify_current_map(self.path, game)

    def test_changed_dbserver_or_old_receipt_cannot_hide_behind_current_pe(self):
        for key in ('DbServer.exe', 'native_monorail'):
            with self.subTest(key=key):
                game = copy.deepcopy(self.game)
                if key.endswith('.exe'): game['files'][key]['sha256'] = '0'*64
                else: game[key]['receipt']['build_input']['contract']['station_preparation_timeout_seconds'] = 1
                with self.assertRaisesRegex(ValueError, 'retained native ancestry'):
                    contract.verify_current_map(self.path, game)

    def test_binding_source_report_and_runtime_summary_are_independently_bound(self):
        original = (self.assets/contract.BINDING).read_bytes()
        binding = json.loads(original); binding['source_report_utf8'] += ' '
        (self.assets/contract.BINDING).write_text(json.dumps(binding))
        with self.assertRaisesRegex(ValueError, 'raw document pin'): contract.verify_current_map(self.path, self.game)
        (self.assets/contract.BINDING).write_bytes(original)
        manifest = json.loads((self.assets/'runtime-manifest.json').read_text())
        manifest[contract.WRAPPER]['run_id'] = 124
        (self.assets/'runtime-manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'runtime inventory'): contract.verify_current_map(self.path, self.game)

    def test_archive_is_bound_before_cached_payload_reuse(self):
        contract.verify_archive(self.assets/'game-package.tar.gz')
        (self.assets/'game-package.tar.gz').write_bytes(b'other')
        with self.assertRaisesRegex(ValueError, 'game archive differs'):
            contract.verify_archive(self.assets/'game-package.tar.gz')

    def test_current_pe_architecture_is_checked_even_for_matching_hash(self):
        from struct import pack_into
        data = bytearray(self.executable); pack_into('<H', data, 68, 0xaa64)
        self.path.write_bytes(data)
        self.build['files']['MapServer.exe'].update(contract.pin(data))
        self.game['files']['MapServer.exe'] = self.build['files']['MapServer.exe']
        self.game[contract.WRAPPER]['receipt_sha256'] = contract.digest(contract.canonical(self.build))
        raw = contract.canonical(self.build)
        self.binding.update(build_manifest=contract.pin(raw), build_manifest_utf8=raw.decode())
        self.publish()
        with self.assertRaisesRegex(ValueError, 'not Win32 PE32'): contract.verify_current_map(self.path, self.game)

    def test_progress_abi_retained_but_actual_new_producer_reported(self):
        for variant in sorted(contract.VARIANTS):
            with self.subTest(variant=variant):
                self.select(variant)
                old = game_diagnostic.mapserver_progress_contract(self.previous)
                with self.assertRaisesRegex(Exception, 'actual current PE'):
                    game_diagnostic.mapserver_progress_contract(self.game)
                result = game_diagnostic.mapserver_progress_contract(self.game, self.path)
                self.assertEqual(result['contract'], old['contract'])
                self.assertEqual(result['producer']['mapserver_sha256'], contract.digest(self.executable))
                self.assertEqual(result['producer']['run_id'], 123)
                self.assertIn(contract.WRAPPER, result['producer'])

    def test_modern_cache_animation_monorail_fx_checks_preserve_old_provenance(self):
        result = caches.verify_mapserver_compatibility(self.path, self.game)
        self.assertEqual(result['actual_mapserver_sha256'], contract.digest(self.executable))
        self.assertEqual(result['original_cache_donor_mapserver_sha256'], caches.MAPSERVER_SHA256)
        self.assertEqual(monorail.current_receipt(self.path, self.game), monorail.embedded_receipt(self.previous))
        original = startup.embedded_receipt(self.previous)
        document = {'identity': animation.identity(), 'pigg': original['build_input']['animation_certificate']['original_animation_pack']}
        proof = animation.verify_runtime(self.runtime, document, mapserver_package=self.game)
        self.assertTrue(proof['animation_identity_preserved'])
        self.assertEqual(proof['actual_mapserver_sha256'], contract.digest(self.executable))
        proof = fx.verify_consumer(self.runtime, self.game)
        self.assertTrue(proof['native_fx_loader_source_unchanged'])
        self.assertEqual(proof['actual_mapserver_sha256'], contract.digest(self.executable))

    def test_retained_variant_cannot_inherit_modern_cache_or_monorail(self):
        self.select('retained_progress')
        with self.assertRaises(ValueError): startup.current_receipt(self.path, self.game)
        with self.assertRaises(ValueError): caches.verify_mapserver_compatibility(self.path, self.game)
        with self.assertRaises(ValueError): monorail.current_receipt(self.path, self.game)

    def test_projected_texture_inputs_report_actual_executable(self):
        projection = local.server_input_projection(self.game, self.path)
        self.assertEqual(projection['excluded_top_level_directories'], ['texture_library'])
        self.assertTrue(projection['native_bytes_changed'])
        self.assertEqual(projection['native_source_sha256'], self.source['patched_sha256']['MapServer/src/svr/svr_init.c'])
        self.assertEqual(projection['retained_native_source_sha256'], local.SERVER_TEXTURE_EXCLUSION_SOURCE)
        self.assertEqual(projection['native_consumer_sha256'], contract.digest(self.executable))
        self.select('retained_progress')
        self.assertIsNone(local.server_input_projection(self.game, self.path))

    def test_exported_compatibility_proof_requires_current_runtime_binding(self):
        record = game_diagnostic.mapserver_progress_contract(self.game, self.path)['producer']
        self.assertTrue(local.native_producer_matches(record))
        record['run_id'] += 1
        self.assertFalse(local.native_producer_matches(record))
        self.assertFalse(local.native_producer_matches({'mapserver_sha256': contract.digest(self.executable)}))
        self.assertTrue(local.native_producer_matches({'mapserver_sha256': contract.THOR_MAP}))

    def test_launch_env_only_enables_an_authenticated_current_binary(self):
        server = object.__new__(local.LocalCharacterServer); server.map_package = self.game
        env = server.map_metrics_environment({'ARMPORT_SERVER_METRICS': 'wrong', 'keep': '1'}, self.runtime)
        self.assertEqual(env, {'ARMPORT_SERVER_METRICS': '1', 'keep': '1'})
        self.assertTrue(server.server_metrics_enabled)
        self.path.write_bytes(b'changed')
        with self.assertRaises(ValueError): server.map_metrics_environment({}, self.runtime)
        server.map_package = self.previous
        self.assertEqual(server.map_metrics_environment({'ARMPORT_SERVER_METRICS': '1'}, self.runtime), {})
        self.assertFalse(server.server_metrics_enabled)

    def test_fx_installer_binds_original_qualified_consumer_separately_from_new_pe(self):
        (self.assets/fx.PAYLOAD).write_bytes(b'fixture marker')
        target = self.runtime/fx.TARGET; target.parent.mkdir(parents=True)
        target.write_bytes(b'private native cache must be retained')
        old = startup.pin_record(self.previous['files']['MapServer.exe'])
        value = {'native_qualification': {'startup_native_consumer': {'mapserver': old}}}
        with mock.patch.object(fx, 'verify_package', return_value=(value, b'not installed')):
            result = fx.install(self.assets, self.runtime, mapserver_package=self.game)
            self.assertEqual(result['status'], 'preserved_existing_fx_native_fallback')
        value['native_qualification']['startup_native_consumer']['mapserver'] = self.binding['build_manifest']
        with mock.patch.object(fx, 'verify_package', return_value=(value, b'not installed')):
            with self.assertRaisesRegex(ValueError, 'qualified for different startup native bytes'):
                fx.install(self.assets, self.runtime, mapserver_package=self.game)
        self.assertEqual(target.read_bytes(), b'private native cache must be retained')

    def test_data_cache_projection_keeps_exact_original_generation_for_both_variants(self):
        for variant in sorted(contract.VARIANTS):
            self.select(variant)
            server = object.__new__(local.LocalCharacterServer)
            server.map_package = self.game; server.map_package_dir = self.runtime; server.creation_report = {}
            result = server.data_cache_native_package()
            expected = startup.previous_package(self.previous) if variant == 'thor_certified_startup' else self.previous
            self.assertEqual(result, expected)
            self.assertEqual(server.map_package, self.game)
            self.path.write_bytes(b'wrong')
            with self.assertRaises(ValueError): server.data_cache_native_package()

    def test_map_payload_routes_original_contracts_after_current_pe_authentication(self):
        for variant in sorted(contract.VARIANTS):
            self.select(variant)
            (self.runtime/'game-package.json').write_text(json.dumps(self.game))
            receipt = self.previous.get('native_responsiveness', {}).get('receipt')
            # Historical DLL bytes are not part of this parser fixture. Their
            # inventory gate remains in place and must be called before it.
            with mock.patch.object(local.dbserver, 'verify_inventory') as inventory, \
                 mock.patch.object(local.base, 'verify_pe32'):
                result = local.LocalCharacterServer.verify_map_payload(self.runtime, receipt)
                self.assertEqual(result, self.game); inventory.assert_called_once()
                self.path.write_bytes(b'wrong current PE')
                with self.assertRaisesRegex(ValueError, 'Current metrics MapServer bytes'):
                    local.LocalCharacterServer.verify_map_payload(self.runtime, receipt)

    def stage_fixture(self, *, metrics=True, failure=False):
        import stage_app_assets as stage
        source = self.work/'donor'; source.mkdir()
        (source/'game-package.tar.gz').write_bytes(b'original donor archive')
        client = {'format': 1, 'scope': 'actual_client_startup_guest',
                  'files': {'game-package.tar.gz': stage.pin(source/'game-package.tar.gz')}}
        (source/'client-manifest.json').write_text(json.dumps(client))
        runtime = {'format': 1, 'repository_commit': '1'*40, 'files': {
            **client['files'], 'client-manifest.json': stage.pin(source/'client-manifest.json')}}
        (source/'runtime-manifest.json').write_text(json.dumps(runtime))
        armport = self.work/'client.zip'; armport.write_bytes(b'client overlay fixture')
        destination = self.work/'staged'
        document = {'files': {'CityOfHeroes.exe': {'sha256': 'c'*64}}, 'client_run_id': 123, 'data_run_id': 123}
        def patch_game(original, native, output, **kwargs):
            self.assertEqual(kwargs['variant'], self.variant)
            self.assertEqual(kwargs['repository_commit'], '2'*40)
            self.assertEqual(kwargs['run_id'], 123)
            self.assertEqual(original.read_bytes(), b'original donor archive')
            if failure: raise ValueError('unqualified native input')
            output.write_bytes(b'game-fixture')
        with mock.patch.object(stage.package, 'unpack', return_value=document), \
             mock.patch.object(producer, 'patch_game', side_effect=patch_game) as patch, \
             mock.patch.object(producer, 'runtime_binding', return_value=self.binding):
            options = {'server_archive': self.work/'native.zip', 'server_variant': self.variant,
                       'server_run_id': 123} if metrics else {}
            if failure:
                with self.assertRaisesRegex(ValueError, 'unqualified native input'):
                    stage.stage(source, armport, destination, '2'*40, **options)
                self.assertFalse(destination.exists())
                return
            stage.stage(source, armport, destination, '2'*40, **options)
            if metrics: patch.assert_called_once()
            else: patch.assert_not_called()
        return destination

    def test_staging_repins_binding_game_and_inner_outer_inventories(self):
        destination = self.stage_fixture()
        runtime = json.loads((destination/'runtime-manifest.json').read_text())
        client = json.loads((destination/'client-manifest.json').read_text())
        for name in ('game-package.tar.gz', contract.BINDING, 'armport_server_metrics_contract.py'):
            actual = contract.pin((destination/name).read_bytes())
            self.assertEqual(runtime['files'][name], actual)
            self.assertEqual(client['files'][name], actual)
        self.assertEqual(runtime[contract.WRAPPER], contract.summary(self.binding))
        with mock.patch.object(contract, 'ASSETS', destination):
            self.assertEqual(contract.verify_current_map(self.path, self.game)['run_id'], 123)

    def test_rejected_server_input_leaves_no_staged_output(self):
        self.stage_fixture(failure=True)

    def test_staging_without_server_overlay_keeps_original_game_and_no_binding(self):
        destination = self.stage_fixture(metrics=False)
        self.assertEqual((destination/'game-package.tar.gz').read_bytes(), b'original donor archive')
        self.assertFalse((destination/contract.BINDING).exists())
        self.assertFalse((destination/'armport_server_metrics_contract.py').exists())
        runtime = json.loads((destination/'runtime-manifest.json').read_text())
        self.assertNotIn(contract.WRAPPER, runtime)

    def test_no_wrapper_progress_and_projection_keep_original_behavior(self):
        self.assertEqual(local.server_input_projection(self.previous)['native_consumer_sha256'], contract.THOR_MAP)
        with mock.patch.object(contract, 'load_binding', side_effect=AssertionError('unexpected admission read')):
            self.assertEqual(game_diagnostic.mapserver_progress_contract(self.previous)['producer']['mapserver_sha256'], contract.THOR_MAP)
            self.assertTrue(local.native_producer_matches({'mapserver_sha256': contract.THOR_MAP}))


if __name__ == '__main__':
    unittest.main()
