"""Exercise actual extraction, immutable gameplay bytes and fresh manifest auditing."""
import contextlib
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_thor_performance_apk as package
import test_ui_beacon_package as previous

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


@contextlib.contextmanager
def candidate(folder):
    with previous.candidate(folder) as prior:
        apk = prior[0]; donor = copy.deepcopy(prior[2])
        donor.update(payloads=copy.deepcopy(prior[3]), runtime_manifest=copy.deepcopy(prior[4]))
        with zipfile.ZipFile(apk) as archive:
            donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        old_member = 'assets/runtime/retained-27.bin'
        new_member = 'assets/runtime/local_login_server.py'
        source = apk.with_suffix('.login-fixture.apk')
        with zipfile.ZipFile(apk) as original, zipfile.ZipFile(source, 'w') as output:
            for entry in original.infolist():
                if entry.filename != old_member: output.writestr(entry, original.read(entry))
            output.writestr(new_member, b'original-login-helper')
        source.replace(apk)
        donor['payloads'].pop(old_member); donor['payloads'][new_member] = pin(b'original-login-helper')
        # The historical tiny fixture predates local_login_server.py tracking;
        # the actual 0.13.14 donor includes it in both immutable inventories.
        for value in (donor['_client_verification'], donor['runtime_manifest']):
            value['files'].pop('retained-27.bin', None)
            value['files']['local_login_server.py'] = donor['payloads']['assets/runtime/local_login_server.py']
        client_raw = package.shared.encoded(donor['_client_verification'])
        donor['runtime_manifest']['files']['client-manifest.json'] = pin(client_raw)
        for name, raw in (('client-manifest.json', client_raw),
                ('runtime-manifest.json', package.shared.encoded(donor['runtime_manifest']))):
            member = 'assets/runtime/'+name; replace_member(apk, member, raw); donor['payloads'][member] = pin(raw)
        for name in package.HELPERS:
            (folder/'android/guest'/name).write_bytes(('reviewed-performance-'+name).encode())
        with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'current_sources', return_value={}):
            runtime, payloads, preflight = package.extract_and_repair(apk, donor, folder/'performance-files', COMMIT)
            output = folder/'performance.apk'
            with zipfile.ZipFile(output, 'w') as archive, zipfile.ZipFile(apk) as original:
                for name in payloads: archive.write(folder/'performance-files'/name, name)
                for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'):
                    archive.writestr(name, original.read(name))
                archive.writestr('AndroidManifest.xml', b'version-only-update')
            yield output, apk, donor, payloads, runtime, preflight


def qualification():
    contract = package.module('thor_performance_test_contract', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE, 'repository_commit': COMMIT,
        'donor': package.donor_link(), 'checks': {name: True for name in package.CHECKS},
        **{name: False for name in package.FALSE_FLAGS},
        'test_suites': {name: {'status': 'passed', 'skipped': 0, 'tests_run': 1} for name in contract.TEST_MODULES},
        'tests_run': len(contract.TEST_MODULES), 'check_suites': copy.deepcopy(contract.CHECK_SUITES),
        'source_files': {name: pin(b'source') for name in package.SOURCE_FILES},
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback'],
        'postgresql_levelup_fixtures': sorted(package.previous.previous.prior.levelup_postgresql_fixtures())}


class ThorPerformancePackagingTests(unittest.TestCase):
    def verify(self, values):
        return package.verify_derivative(values[0], values[2], values[3], COMMIT)

    def test_new_version_exact_public_accepted_donor_and_no_asset_changes(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.15', 30))
        self.assertEqual(package.donor_link()['run_id'], 37392793426)
        self.assertEqual(package.DONOR_COMMIT, '25f821da9e782281953412543057054abd8dd320')
        self.assertEqual(package.DONOR_APK['sha256'], '1dab30d097978e6d8b7e299e868a932d73c924410dcc20d4e6e51f36353b11ee')
        self.assertEqual((len(package.REPLACED_PAYLOADS), len(package.ADDED_PAYLOADS)), (6, 0))

    def test_actual_extraction_conserves_all69_immutable_payloads_and_android_shell(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            self.assertEqual(self.verify(values), values[4])
            self.assertEqual(len(values[3]), 75)
            self.assertEqual(len(set(values[2]['payloads'])-package.REPLACED_PAYLOADS), 69)
            self.assertEqual(values[5], values[2]['server_payload_extraction_preflight'])
            with zipfile.ZipFile(values[0]) as current, zipfile.ZipFile(values[1]) as donor:
                for name in set(values[2]['payloads'])-package.REPLACED_PAYLOADS:
                    self.assertEqual(current.read(name), donor.read(name), name)
                for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'):
                    self.assertEqual(current.read(name), donor.read(name), name)
            for key in ('ui_beacon', 'levelup_ui_repair', 'reopen_startup_repair', 'task_gate_required', 'startup_only_reopen'):
                self.assertEqual(values[4][key], values[2]['runtime_manifest'][key])

    def test_native_visual_beacon_cache_and_nonreviewed_helpers_cannot_change(self):
        names = ('client-runtime.zip', 'game-package.tar.gz', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz',
            'server-caches.zip', 'client-caches.zip', 'atlas-world-supplement.zip', 'server-animations.pigg',
            'startup-dbserver.exe', 'startup-dbserver-manifest.json', 'client-launcher.exe',
            'client-visual-assets.zip', 'client-visual-manifest.json', 'atlas-beacons.zip', 'atlas-beacon-manifest.json',
            'client_visual_assets.py', 'atlas_beacon_package.py', 'native_training_save.py', 'texture_header_index.py')
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'foreign'); values[3][member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_each_changed_guest_helper_must_match_actual_qualified_source(self):
        for name in package.HELPERS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'foreign'); values[3][member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'Authored performance helper'): self.verify(values)

    def test_extra_missing_or_unchanged_required_replacements_are_rejected(self):
        for mutation in ('add', 'delete', 'unchanged'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                if mutation == 'add': values[3]['assets/runtime/foreign.py'] = pin(b'foreign')
                elif mutation == 'delete': values[3].pop('assets/runtime/atlas-beacons.zip')
                else:
                    name = 'assets/runtime/local_character_server.py'; values[3][name] = values[2]['payloads'][name]
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_android_shell_or_unknown_archive_members_cannot_change(self):
        for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml', 'assets/runtime/foreign.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                if name.endswith('foreign.py'):
                    with zipfile.ZipFile(values[0], 'a') as archive: archive.writestr(name, b'foreign')
                else: replace_member(values[0], name, b'foreign')
                with self.assertRaises(ValueError): self.verify(values)

    def test_embedded_client_manifest_order_tolerance_preserves_exact_byte_pin(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            original = package.verification_manifests
            def reordered(donor, updates, commit):
                client, runtime = original(donor, updates, commit)
                client['files'] = dict(reversed(list(client['files'].items())))
                raw = package.shared.encoded(client)
                runtime['files']['client-manifest.json'] = pin(raw)
                with zipfile.ZipFile(values[0]) as archive:
                    self.assertNotEqual(pin(archive.read('assets/runtime/client-manifest.json')), pin(raw))
                return client, runtime
            with mock.patch.object(package, 'verification_manifests', side_effect=reordered):
                self.assertEqual(self.verify(values), values[4])

    def test_manifest_logic_or_prior_gameplay_provenance_cannot_be_relabelled(self):
        for mutation in ('client', 'client_reference', 'ui_beacon', 'levelup_ui_repair', 'thor_performance'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/client-manifest.json' if mutation == 'client' else 'assets/runtime/runtime-manifest.json'
                with zipfile.ZipFile(values[0]) as archive: value = json.loads(archive.read(member))
                if mutation == 'client': value['files']['local_character_server.py'] = pin(b'foreign')
                elif mutation == 'client_reference': value['files']['client-manifest.json'] = pin(b'foreign')
                else: value[mutation] = 'foreign'
                raw = package.shared.encoded(value); replace_member(values[0], member, raw); values[3][member] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'provenance'): self.verify(values)

    def test_qualification_requires_all_suites_real_pg_and_exact_source_closure(self):
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file'):
            self.assertEqual(package.validate_qualification(qualification(), COMMIT)['status'], 'passed')
            for mutation in ('suite', 'skip', 'failure', 'count', 'native', 'physical', 'pg', 'source', 'scope'):
                value = qualification(); first = next(iter(value['test_suites']))
                if mutation == 'suite': value['test_suites'].pop(first)
                elif mutation == 'skip': value['test_suites'][first]['skipped'] = 1
                elif mutation == 'failure': value['test_suites'][first]['status'] = 'failed'
                elif mutation == 'count': value['tests_run'] += 1
                elif mutation == 'native': value['native_mapserver_recompiled'] = True
                elif mutation == 'physical': value['physical_client_timing_validated'] = True
                elif mutation == 'pg': value['postgresql_levelup_fixtures'] = []
                elif mutation == 'source': value['source_files'].pop(next(iter(value['source_files'])))
                else: value['scope'] = 'foreign'
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): package.validate_qualification(value, COMMIT)

    def test_existing_release_never_replaced(self):
        api = mock.Mock(); api.request.return_value = {'id': 1}
        assets = tuple(Path(name) for name in (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME)); base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file'):
            with self.assertRaisesRegex(ValueError, 'Existing release'): package.publish_release(api, {'repository_commit': COMMIT}, assets, 'notes')
        self.assertFalse(any(call.kwargs.get('method') in ('POST', 'PATCH') for call in api.request.call_args_list))

    def test_workflow_retains_donor_signer_and_has_fresh_audit_before_publish_and_after(self):
        source = (package.ROOT/package.WORKFLOW).read_text()
        for expected in ('run-id: 37392793426', 'run-id: 36731428735', 'coh-client-interactive.jks',
                'COH_REQUIRE_STARTUP_BUNDLE_PG', 'COH_REQUIRE_LEVELUP_UI_REPAIR_PG',
                'image: postgres:16', '35.0.0', 'android-35/android.jar', package.APK_NAME,
                'fetch-depth: 2', 'Independent fresh-job public SDK signer exact payload and source audit'):
            self.assertIn(expected, source)
        self.assertLess(source.index('Fresh-process SDK source payload and signer audit before publication'),
            source.index('Publish only the newly qualified performance prerelease'))
        self.assertNotIn('--target Game', source); self.assertNotIn('generate_atlas_beacons.py', source)
        self.assertNotIn('prepare_client_ui_sweep_assets.py', source)
        public = source.split('  public-audit:\n', 1)[1]
        self.assertIn('contents: read', public); self.assertNotIn('coh-client-interactive.jks', public)
        self.assertIn("required: ${{ steps.gate.outputs.required }}", source)


if __name__ == '__main__': unittest.main()
