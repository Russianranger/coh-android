"""On-demand zone DbServer layer: source receipt, package contract and guest acceptance (no build)."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/server'), str(ROOT / 'armport/app'), str(ROOT / 'tools/android/interactive'),
                str(ROOT / 'android/guest')]
import package_external_maps_dbserver as external  # noqa: E402
import local_character_server as character  # noqa: E402
from test_package_reference_runtime import pe_file  # noqa: E402


def layered_inputs():
    base = external.accepted_base()
    bundle = external.bundle_layer.expected_receipt(ROOT, base)
    levelup = external.levelup.expected_receipt(ROOT, base, bundle)
    return base, bundle, levelup


def guest_fixture(root, receipt):
    assets, runtime = root / 'assets', root / 'runtime'
    assets.mkdir(); runtime.mkdir()
    package = json.loads((ROOT / external.manual.ACCEPTED_BASE_MANIFEST).read_text())
    original, library = b'accepted donor executable', b'accepted donor library'
    normal = package['variants']['normal']
    normal['files'] = {'DbServer.exe': {'bytes': len(original), 'sha256': hashlib.sha256(original).hexdigest()},
                       'retained.dll': {'bytes': len(library), 'sha256': hashlib.sha256(library).hexdigest()}}
    (runtime / 'DbServer.exe').write_bytes(original); (runtime / 'retained.dll').write_bytes(library)
    image = pe_file(('KERNEL32.dll',)); (assets / 'startup-dbserver.exe').write_bytes(image)
    base, bundle, levelup = layered_inputs()
    manifest = {'format': 1, 'role': external.ROLE, 'repository_commit': 'a' * 40,
        'source_commit': package['source_commit'], 'base_package_manifest_sha256': external.manual.BASE_PACKAGE_SHA256,
        'replacement_scope': 'fresh_owned_manual_atlas_runtime_DbServer.exe_only',
        'base_package_archive_changed': False, 'architecture': 'Win32', 'configuration': 'OptDebug',
        'postgresql_persistence_fixture': False, 'android_execution_validated': False, 'gameplay_validated': False,
        'retained_normal_files': {'retained.dll': normal['files']['retained.dll']},
        'base_normal_executable': normal['files']['DbServer.exe'],
        'base_normal_cmake_cache_sha256': normal['cmake_cache_sha256'],
        'base_startup_executable': external.bundle_layer.BASE_STARTUP_EXECUTABLE,
        'base_startup_bundle_executable': external.levelup.BASE_STARTUP_BUNDLE_EXECUTABLE,
        'base_levelup_ui_repair_executable': external.BASE_LEVELUP_EXECUTABLE,
        'build_input': base, 'startup_bundle_build_input': bundle, 'levelup_ui_repair_build_input': levelup,
        'external_maps_build_input': receipt,
        'files': {'DbServer.exe': {'bytes': len(image), 'sha256': hashlib.sha256(image).hexdigest()}},
        'dependency_report': {'unresolved': []}, 'odbc_imports': list(external.wine.REQUIRED_IMPORTS)}
    (assets / 'startup-dbserver-manifest.json').write_text(json.dumps(manifest))
    return assets, runtime, package, manifest, original, image


class ExternalMapsDbServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = external.expected_receipt(ROOT)

    def test_receipt_sits_on_the_shipped_level_up_layer_and_matches_the_guest_pins(self):
        base, bundle, levelup = layered_inputs()
        self.assertEqual(character.digest_json(levelup), character.EXTERNAL_MAPS_BASE_LEVELUP_SHA256)
        self.assertEqual(levelup, character.levelup_ui_repair_build_input(base, bundle))
        self.assertEqual(character.digest_json(self.receipt), character.EXTERNAL_MAPS_BUILD_INPUT_SHA256)
        self.assertEqual(character.EXTERNAL_MAPS_BASE_EXECUTABLE, external.BASE_LEVELUP_EXECUTABLE)
        self.assertEqual(character.EXTERNAL_MAPS_ROLE, external.ROLE)
        self.assertEqual(set(self.receipt['patched_sha256']), set(external.PATCHED_FILES))
        self.assertEqual(set(self.receipt['overlay_sha256']), set(external.OVERLAY_FILES))
        self.assertTrue(self.receipt['request_contract']['disabled_by_default'])
        # The acknowledgement is the overlay's own string.
        header = (ROOT / external.OVERLAY / 'DBServer/src/wine_external_maps.h').read_text()
        self.assertIn('"' + self.receipt['request_contract']['acknowledgement'] + '"', header)

    def test_guest_installs_the_layer_inert_with_the_level_up_contracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            assets, runtime, package, _, _, image = guest_fixture(Path(temporary), self.receipt)
            installed = character.install_manual_atlas_dbserver(assets, runtime, package)
            self.assertEqual((runtime / 'DbServer.exe').read_bytes(), image)
            self.assertFalse(installed['external_maps']['enabled'])
            self.assertEqual(installed['external_maps']['request_contract'], self.receipt['request_contract'])
            # The level-up read and save contracts stay active (training save, logging).
            self.assertIsNotNone(installed['levelup_ui_repair_save'])
            self.assertIsNotNone(installed['startup_bundle_save'])

    def test_changed_layer_or_relabeled_role_is_refused_before_replacement(self):
        changes = [lambda m: m['external_maps_build_input']['request_contract'].update(disabled_by_default=False),
                   lambda m: m['external_maps_build_input']['patched_sha256'].update({'DBServer/src/mapxfer.c': 'f' * 64}),
                   lambda m: m.update(base_levelup_ui_repair_executable={'bytes': 1, 'sha256': 'f' * 64}),
                   lambda m: m['levelup_ui_repair_build_input'].update(patch_sha256='f' * 64),
                   lambda m: m.pop('external_maps_build_input'),
                   # A level-up manifest may not carry an unqualified external layer.
                   lambda m: m.update(role=character.LEVELUP_UI_REPAIR_ROLE)]
        for index, change in enumerate(changes):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temporary:
                assets, runtime, package, manifest, original, _ = guest_fixture(Path(temporary), copy.deepcopy(self.receipt))
                change(manifest)
                (assets / 'startup-dbserver-manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(character.base.DiagnosticError):
                    character.install_manual_atlas_dbserver(assets, runtime, package)
                self.assertEqual((runtime / 'DbServer.exe').read_bytes(), original)


class ExternalMapsApkAdmissionTests(unittest.TestCase):
    """build_thor_apk --external-maps-dbserver: only the two DbServer payloads, on the donor's level-up DbServer."""
    def fixture(self, root):
        import stage_app_assets
        source, package = root / 'donor', root / 'package'
        source.mkdir(); package.mkdir()
        old_exe, new_exe = b'donor level-up DbServer', b'external map DbServer'
        (source / 'startup-dbserver.exe').write_bytes(old_exe)
        base, bundle, levelup = layered_inputs()
        base_pin = stage_app_assets.pin(source / 'startup-dbserver.exe')
        donor = {'role': 'manual_atlas_dbserver_levelup_ui_repair', 'build_input': base,
                 'startup_bundle_build_input': bundle, 'levelup_ui_repair_build_input': levelup,
                 'files': {'DbServer.exe': dict(base_pin, pe_machine=332)}}
        (source / 'startup-dbserver-manifest.json').write_text(json.dumps(donor))
        (package / 'DbServer.exe').write_bytes(new_exe)
        value = dict(donor, role=external.ROLE, repository_commit='b' * 40,
                     external_maps_build_input=external.expected_receipt(ROOT),
                     files={'DbServer.exe': {'bytes': len(new_exe), 'sha256': hashlib.sha256(new_exe).hexdigest()}})
        (package / external.MANIFEST).write_text(json.dumps(value))
        return stage_app_assets, source, package, base_pin, value

    def test_admission_replaces_two_payloads_and_records_the_layer_inert(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage_app_assets, source, package, base_pin, value = self.fixture(Path(temporary))
            with patch.object(external, 'BASE_LEVELUP_EXECUTABLE', base_pin), \
                    patch.object(external, 'validate_package', return_value=value) as validate:
                generated, record = stage_app_assets.external_maps_dbserver(source, package)
            validate.assert_called_once_with(package, 'b' * 40)
            self.assertEqual(set(generated), set(stage_app_assets.DBSERVER_PAYLOADS))
            self.assertEqual(generated['startup-dbserver.exe'], b'external map DbServer')
            self.assertEqual(record['role'], external.ROLE)
            self.assertFalse(record['enabled_by_default'])
            self.assertEqual(record['build_input_sha256'], character.EXTERNAL_MAPS_BUILD_INPUT_SHA256)

    def test_admission_refuses_another_donor_dbserver_or_ancestry(self):
        for change in ('executable', 'role', 'ancestry'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                stage_app_assets, source, package, base_pin, value = self.fixture(Path(temporary))
                donor = json.loads((source / 'startup-dbserver-manifest.json').read_text())
                if change == 'executable':
                    (source / 'startup-dbserver.exe').write_bytes(b'another DbServer')
                elif change == 'role':
                    donor['role'] = 'manual_atlas_dbserver_startup_bundle'
                else:
                    donor['levelup_ui_repair_build_input'] = dict(donor['levelup_ui_repair_build_input'], patch_sha256='f' * 64)
                (source / 'startup-dbserver-manifest.json').write_text(json.dumps(donor))
                with patch.object(external, 'BASE_LEVELUP_EXECUTABLE', base_pin), \
                        patch.object(external, 'validate_package', return_value=value), \
                        self.assertRaisesRegex(ValueError, 'does not sit on the donor'):
                    stage_app_assets.external_maps_dbserver(source, package)

    def test_ci_runtime_adds_the_two_payloads_to_a_donor_without_a_startup_dbserver(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage_app_assets, source, package, base_pin, value = self.fixture(Path(temporary))
            for name in stage_app_assets.DBSERVER_PAYLOADS:
                (source / name).unlink()
            with patch.object(external, 'validate_package', return_value=value) as validate:
                generated, record = stage_app_assets.external_maps_dbserver(source, package, ci_runtime=True)
            validate.assert_called_once_with(package, 'b' * 40)
            self.assertEqual(set(generated), set(stage_app_assets.DBSERVER_PAYLOADS))
            self.assertEqual(record['admission'], 'ci_runtime_addition')
            self.assertFalse(record['enabled_by_default'])
            # A donor that does carry a startup DbServer takes the APK path only.
            (source / 'startup-dbserver.exe').write_bytes(b'donor level-up DbServer')
            with patch.object(external, 'validate_package', return_value=value), \
                    self.assertRaisesRegex(ValueError, 'unexpectedly carries'):
                stage_app_assets.external_maps_dbserver(source, package, ci_runtime=True)

    def test_ci_runtime_package_comes_from_its_own_successful_build_run(self):
        import interactive_host
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'startup-dbserver-manifest.json').write_text(json.dumps({'repository_commit': 'c' * 40}))
            run = {'id': 41883310382, 'path': interactive_host.EXTERNAL_MAPS_WORKFLOW, 'status': 'completed',
                   'conclusion': 'success', 'head_sha': 'c' * 40}
            path = directory / 'run.json'
            path.write_text(json.dumps(run))
            self.assertEqual(interactive_host.external_maps_build_run(path, directory)['run_id'], 41883310382)
            for change in ({'conclusion': 'failure'}, {'head_sha': 'd' * 40},
                           {'path': '.github/workflows/armport-app-runtime.yml'}, {'status': 'in_progress'}):
                with self.subTest(change=change):
                    path.write_text(json.dumps(dict(run, **change)))
                    with self.assertRaisesRegex(ValueError, 'not from one successful build run'):
                        interactive_host.external_maps_build_run(path, directory)
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn('external_maps_run_id:', workflow)
        self.assertIn('name: armport-external-maps-dbserver', workflow)
        self.assertIn('--external-maps-dbserver "$RUNNER_TEMP/external-maps-dbserver" '
                      '--external-maps-run-json "$RUNNER_TEMP/external-maps-run.json"', workflow)
        # An experiment runtime never produces the qualified servers an APK build consumes.
        self.assertEqual(workflow.count("if: env.SERVER_RUN_ID != '' && env.EXTERNAL_MAPS_RUN_ID == ''"), 2)

    def test_ci_notice_summarises_the_supervisor_report(self):
        import interactive_host
        section = {'manual_atlas_startup': {'native_ack_observed': True},
                   'external_maps': {'format': 1, 'requested': True, 'enabled': True, 'reason': None,
                                     'dbserver_layer': character.EXTERNAL_MAPS_BUILD_INPUT_SHA256,
                                     'supervisor': {'acknowledgement_observed': True, 'stopped': None,
                                                    'counts': {'delink_finished': 1}, 'session_maps': [1],
                                                    'map_starts_executed': False, 'anomalies': [],
                                                    'requests': [{'map_id': 5, 'cookie': 7, 'is_static': 1,
                                                                  'decision': 'delink', 'reason': 'not_served',
                                                                  'map_name': 'x' * 120,
                                                                  'delink': {'passed': True}}]}}}
        summary = interactive_host.external_maps_summary(section)
        self.assertTrue(summary['enabled'])
        self.assertTrue(summary['manual_atlas_ack'])
        self.assertEqual(summary['requests'], [{'map_id': 5, 'is_static': 1, 'decision': 'delink',
                                                'reason': 'not_served', 'refused_option': None,
                                            'delink_passed': True}])
        self.assertLess(len(json.dumps(summary)), 1500)
        self.assertIsNone(interactive_host.external_maps_summary({}))

    def test_apk_builder_admits_exactly_the_two_payloads(self):
        import build_thor_apk
        source = (ROOT / 'armport/app/build_thor_apk.py').read_text()
        self.assertIn('changed_runtime | frozenset(stage_app_assets.DBSERVER_PAYLOADS)', source)
        self.assertIn("'--external-maps-dbserver'", source)
        self.assertFalse(set(build_thor_apk.CHANGED_RUNTIME) & {'startup-dbserver.exe', 'startup-dbserver-manifest.json'})


if __name__ == '__main__':
    unittest.main()
