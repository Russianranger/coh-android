"""Actual public .32 retention and narrowly scoped .33 report/loading packaging.

These are light package checks. Complete asset preparation and Android assembly
belong to the dedicated qualification lane; no physical timing is inferred here.
"""
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import sys
import unittest
from unittest.mock import patch
import zipfile

import build_client_report_loading_apk as package


class ReportLoadingPackageTests(unittest.TestCase):
    @classmethod
    def actual_inputs(cls):
        # CI supplies the authenticated donor paths. The same archived public
        # bytes are available in the recovered workspace for local qualification.
        recovered = package.ROOT.parent/'qualification/public032'
        default_apk = package.ROOT/'out/donor.apk'
        default_report = package.ROOT/'out/donor-evidence/client-map-startup-apk-build-report.json'
        if not default_apk.is_file(): default_apk = recovered/'COH-Atlas-Gameplay-0.13.32.apk'
        if not default_report.is_file(): default_report = recovered/'client-map-startup-apk-build-report.json'
        apk = Path(os.environ.get('COH_REPORT_LOADING_TEST_DONOR_APK', default_apk)).resolve()
        report = Path(os.environ.get('COH_REPORT_LOADING_TEST_DONOR_REPORT', default_report)).resolve()
        if not apk.is_file() or not report.is_file():
            raise AssertionError('Actual authenticated public .32 APK and build receipt are mandatory; no skips')
        return apk, report

    @classmethod
    def actual_fixture(cls):
        if not hasattr(cls, '_actual_fixture'):
            apk, report = cls.actual_inputs()
            donor = package.validate_donor(apk, report)
            commit = package.builder().source_commit(os.environ.get('COH_REPORT_LOADING_TEST_SOURCE_COMMIT'))
            with tempfile.TemporaryDirectory(prefix='coh-report-loading-light-') as temporary:
                destination = Path(temporary)/'candidate'
                runtime, payloads, preflight = package.extract_and_repair(
                    apk, donor, destination, commit, execute_preflight=False)
                with zipfile.ZipFile(apk) as archive:
                    original = {name: archive.read(name) for name in
                        set(donor['payloads']) | {'classes.dex'} | set(donor['retained_android_resources'])}
                candidate = {name: (destination/name).read_bytes() for name in original}
            cls._actual_fixture = (donor, commit, runtime, payloads, preflight, original, candidate)
        return cls._actual_fixture

    @staticmethod
    def tar_members(raw):
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
            return {entry.name: archive.extractfile(entry).read()
                for entry in archive.getmembers() if entry.isfile()}

    def test_monotonic_release_and_exact_public_donor_identity(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.33', 48))
        self.assertEqual(package.DONOR_COMMIT, '6c4d1d74f34ecdea8fabcf6238368bf72003878f')
        self.assertEqual(package.DONOR_RUN_ID, 38205495073)
        self.assertEqual(package.DONOR_APK, {'bytes': 42031636,
            'sha256': '8995ecef2622a7720b0ef296b0960a79cc2e914a5da2a9078379ff66732b2839'})
        self.assertEqual(package.DONOR_BUILD, {'bytes': 8175633,
            'sha256': '88428c1423185d1e8c2efd7821f4fbbd742bbf85b79d82dd6d85ad169ddc0d04'})
        self.assertEqual(package.DONOR_APK_NAME, 'COH-Atlas-Gameplay-0.13.32.apk')
        self.assertEqual(package.DONOR_REPORT_NAME, 'client-map-startup-apk-build-report.json')
        self.assertEqual(package.APK_NAME, 'COH-Atlas-Gameplay-0.13.33.apk')
        self.assertEqual(package.RELEASE_TAG, 'coh-atlas-gameplay-v0.13.33')

    def test_reviewed_source_scope_excludes_native_graphics_asset_and_acceptance_changes(self):
        java = 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
        self.assertEqual(package.REVIEWED_JAVA_CHANGES, {
            java+name+'.java' for name in ('ClientActivity', 'ClientRuntime', 'ClientService')
        } | {'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java'})
        self.assertEqual(package.GUEST_SOURCE_CHANGES, {'android/guest/'+name+'.py' for name in
            ('atlas_beacon_package', 'kings_row_beacon_package', 'local_character_server')})
        self.assertEqual(package.ADDED_PAYLOADS, frozenset())
        for flag in ('native_mapserver_recompiled', 'native_client_recompiled', 'native_dbserver_recompiled',
                'graphics_driver_changed', 'wine_or_fex_changed', 'world_assets_changed',
                'asset_reimport_required', 'save_acceptance_relaxed', 'native_runtime_booted',
                'physical_map_startup_speedup_validated', 'sub_30_second_map_startup_validated'):
            self.assertIn(flag, package.FALSE_FLAGS)

    def test_historical_032_builder_marker_and_native_qualification_remain_immutable(self):
        _, report = self.actual_inputs(); donor = json.loads(report.read_bytes())
        for name in ('tools/android/interactive/build_client_map_startup_apk.py',
                'tools/android/interactive/release-client-map-startup-0.13.32.json',
                'docs/android-evidence/client-map-startup-0.13.32-native.json'):
            self.assertEqual(package.builder().file_pin(package.ROOT/name),
                             donor['qualification']['source_files'][name], name)

    def test_derivative_owner_requires_direct_push_and_complete_successor_marker(self):
        import classify_client_report_loading_change as owner
        names = sorted(owner.CLIENT_REPORT_LOADING_ALLOWED)
        self.assertTrue(owner.client_report_loading_owned('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(owner.client_report_loading_owned('push', 'a'*40, 'b'*40, 'a'*40,
            sorted(owner.CLIENT_REPORT_LOADING_ALLOWED-{owner.CLIENT_REPORT_LOADING_MARKER})))
        self.assertTrue(owner.client_report_loading_owned('push', 'a'*40, 'b'*40, 'a'*40,
            sorted(owner.CLIENT_REPORT_LOADING_DOCS)))
        self.assertFalse(owner.client_report_loading_owned('push', 'a'*40, 'b'*40, 'a'*40,
            sorted(owner.CLIENT_REPORT_LOADING_DOCS-{owner.CLIENT_REPORT_LOADING_PUBLICATION})))

    def test_derivative_owner_never_bypasses_unknown_native_assets_or_ambiguous_history(self):
        import classify_client_report_loading_change as owner
        names = sorted(owner.CLIENT_REPORT_LOADING_ALLOWED)
        for extra in ('upstream/ouroboros/Game/src/graphics/gfx.c', 'android/native/client-launcher.c',
                'assets/asset-pack-manifest.json', 'android/guest/native_map_startup_contract.py',
                'tools/android/interactive/build_client_map_startup_apk.py',
                'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
                'docs/unreviewed-status.md'):
            with self.subTest(unreviewed=extra):
                self.assertFalse(owner.client_report_loading_owned('push', 'a'*40, 'b'*40, 'a'*40, names+[extra]))
        for event, before, head, parent in (('pull_request', 'a'*40, 'b'*40, 'a'*40),
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40), ('push', 'c'*40, 'b'*40, 'a'*40),
                ('push', 'a'*40, 'b'*40, 'a'*40+'\n'+'c'*40), ('push', '0'*40, 'b'*40, '0'*40),
                ('push', 'a'*40, 'a'*40, 'a'*40)):
            with self.subTest(event=event, before=before, parent=parent):
                self.assertFalse(owner.client_report_loading_owned(event, before, head, parent, names))

    @staticmethod
    def workflow():
        import yaml
        return yaml.safe_load((package.ROOT/package.WORKFLOW).read_text())

    def test_workflow_separates_qualification_publication_and_postpublication_audit(self):
        workflow = self.workflow(); marker = json.loads((package.ROOT/package.MARKER).read_bytes())
        self.assertIs(type(marker['publish_enabled']), bool)
        self.assertIs(type(marker['qualification_enabled']), bool)
        self.assertIs(marker['native_rebuild_required'], False)
        self.assertIs(marker['asset_rebuild_required'], False)
        self.assertEqual((marker['version'], marker['version_code'], marker['donor_commit']),
                         (package.VERSION_NAME, package.VERSION_CODE, package.DONOR_COMMIT))
        self.assertIs(workflow['concurrency']['cancel-in-progress'], False)
        jobs = workflow['jobs']
        self.assertEqual(set(jobs), {'changes', 'apk', 'public-audit'})
        self.assertEqual(jobs['apk']['needs'], 'changes')
        self.assertEqual(jobs['apk']['if'],
            "needs.changes.outputs.required == 'true' && github.repository == 'Russianranger/coh-android' && github.ref == 'refs/heads/codex/character-persistence-continuation'")
        publish = [step for step in jobs['apk']['steps']
            if 'build_client_report_loading_apk.py publish ' in step.get('run', '')]
        self.assertEqual(len(publish), 1)
        self.assertEqual(publish[0]['if'], "needs.changes.outputs.publish_enabled == 'true'")
        import shlex
        audit = [step for step in jobs['apk']['steps']
            if 'build_client_report_loading_apk.py audit ' in step.get('run', '')]
        self.assertEqual(len(audit), 1)
        self.assertLess(jobs['apk']['steps'].index(audit[0]), jobs['apk']['steps'].index(publish[0]))
        audit_arguments, publish_arguments = shlex.split(audit[0]['run']), shlex.split(publish[0]['run'])
        audited_path = audit_arguments[audit_arguments.index('--audit-receipt')+1]
        self.assertEqual(Path(audited_path).name, package.CLIENT_APK_AUDIT_NAME)
        self.assertEqual(publish_arguments[publish_arguments.index('--audit-receipt')+1], audited_path)
        self.assertTrue(any(step.get('with', {}).get('name') == 'coh-client-report-loading-apk'
            and step['with']['path'].rstrip('/') == str(Path(audited_path).parent)
            and jobs['apk']['steps'].index(step) > jobs['apk']['steps'].index(audit[0])
            for step in jobs['apk']['steps']))
        self.assertEqual(jobs['public-audit']['needs'], ['changes', 'apk'])
        self.assertEqual(jobs['public-audit']['if'],
            "always() && needs.changes.result == 'success' && needs.apk.result == 'success' && needs.changes.outputs.required == 'true' && needs.changes.outputs.publish_enabled == 'true'")
        public_audits = [step for step in jobs['public-audit']['steps']
            if 'build_client_report_loading_apk.py audit ' in step.get('run', '')]
        self.assertEqual(len(public_audits), 1)
        public_arguments = shlex.split(public_audits[0]['run'])
        self.assertNotEqual(public_arguments[public_arguments.index('--audit-receipt')+1], audited_path)
        for job in jobs.values():
            for step in job['steps']:
                run = step.get('run', '')
                self.assertNotIn('package_map_startup_native.py', run)
                self.assertNotIn('package_external_assets.py', run)
                self.assertNotIn('gh workflow run android-map-startup-native', run)

    def run_workflow_gate(self, marker, *, response=None, validator=None):
        import urllib.request
        gate = next(step for step in self.workflow()['jobs']['changes']['steps'] if step.get('id') == 'gate')
        lines = gate['run'].splitlines()
        self.assertEqual(lines[0], "python3 - <<'PY'"); self.assertEqual(lines[-1], 'PY')
        code = '\n'.join(lines[1:-1])
        prior_directory, prior_search = Path.cwd(), list(sys.path)
        with tempfile.TemporaryDirectory(prefix='coh-report-loading-workflow-gate-') as temporary:
            directory = Path(temporary); marker_path = directory/package.MARKER
            marker_path.parent.mkdir(parents=True); marker_path.write_text(json.dumps(marker))
            output = directory/'github-output'
            network = patch.object(urllib.request, 'urlopen',
                return_value=io.BytesIO(json.dumps(response).encode())) if response is not None else \
                patch.object(urllib.request, 'urlopen', side_effect=AssertionError('Disabled gate accessed network'))
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output), 'GH_TOKEN': 'unused-fixture-token'}), \
                    network, contextlib.redirect_stdout(io.StringIO()):
                validator_patch = patch.object(package, 'validate_existing_release', validator) if validator is not None else contextlib.nullcontext()
                try:
                    os.chdir(directory)
                    with validator_patch:
                        try: exec(compile(code, package.WORKFLOW+' gate', 'exec'), {'__name__': '__workflow_gate_fixture__'})
                        except SystemExit as exit_status:
                            self.assertEqual(exit_status.code, 0)
                finally:
                    os.chdir(prior_directory); sys.path[:] = prior_search
            return output.read_text()

    def test_false_qualification_gate_cannot_start_build_or_network_even_if_publication_flag_is_true(self):
        marker = json.loads((package.ROOT/package.MARKER).read_bytes())
        for enabled in (False, True):
            disabled = dict(marker, qualification_enabled=False, publish_enabled=enabled)
            with self.subTest(publish_enabled=enabled):
                self.assertEqual(self.run_workflow_gate(disabled),
                    'publish_enabled='+str(enabled).lower()+'\nrequired=false\n')
        for key in ('publish_enabled', 'qualification_enabled'):
            for value in (0, 1, 'false'):
                invalid = dict(marker, qualification_enabled=False, publish_enabled=False); invalid[key] = value
                with self.subTest(nonboolean=key, value=value), self.assertRaises(AssertionError):
                    self.run_workflow_gate(invalid)

    def test_existing_release_gate_validates_and_retains_publication_instead_of_rebuilding(self):
        from unittest.mock import Mock
        marker = dict(json.loads((package.ROOT/package.MARKER).read_bytes()),
                      qualification_enabled=True, publish_enabled=True)
        release = {'tag_name': package.RELEASE_TAG, 'id': 123}
        validate = Mock()
        self.assertEqual(self.run_workflow_gate(marker, response=release, validator=validate),
                         'publish_enabled=true\nrequired=false\n')
        validate.assert_called_once_with(release)
        reject = Mock(side_effect=ValueError('Existing release was not independently accepted'))
        with self.assertRaisesRegex(ValueError, 'not independently accepted'):
            self.run_workflow_gate(marker, response=release, validator=reject)

    def test_actual_donor_member_and_receipt_authentication(self):
        apk, report = self.actual_inputs()
        donor = package.validate_donor(apk, report)
        self.assertEqual(len(donor['payloads']), 74)
        self.assertEqual((donor['version_name'], donor['version_code']), ('0.13.32', 47))
        self.assertEqual(donor['repository_commit'], package.DONOR_COMMIT)
        self.assertEqual(donor['signer_certificate_sha256'], package.SIGNER)
        self.assertEqual((donor['external_asset_release_tag'], donor['asset_pack_version']),
                         ('coh-assets-v1.0.0', '1.0.0'))
        with zipfile.ZipFile(apk) as archive:
            for name, expected in donor['payloads'].items():
                self.assertEqual(package.pin(archive.read(name)), expected, name)
            self.assertEqual(package.pin(archive.read('classes.dex')), donor['recompiled_dex'])
            self.assertEqual(json.loads(archive.read('assets/runtime/runtime-manifest.json')),
                             donor['runtime_manifest'])

    def test_actual_donor_rejects_changed_apk_or_build_receipt_bytes(self):
        apk, report = self.actual_inputs()
        with tempfile.TemporaryDirectory(prefix='coh-report-loading-donor-negative-') as temporary:
            bad_apk = Path(temporary)/'donor.apk'; bad_apk.write_bytes(b'forged public APK')
            bad_report = Path(temporary)/'receipt.json'; bad_report.write_bytes(report.read_bytes()+b'\n')
            with self.assertRaises(ValueError): package.validate_donor(bad_apk, report)
            with self.assertRaises(ValueError): package.validate_donor(apk, bad_report)

    def test_actual_authenticated_report_still_requires_accepted_identity(self):
        apk, report = self.actual_inputs()
        original = json.loads(report.read_bytes())
        for key, value in (('version_name', '0.13.31'), ('version_code', 46),
                ('repository_commit', 'a'*40), ('runtime_repository_commit', 'a'*40),
                ('signer_certificate_sha256', '0'*64), ('signature_verified', False),
                ('external_asset_release_tag', 'coh-assets-v2.0.0'), ('asset_pack_version', '2.0.0')):
            bad = copy.deepcopy(original); bad[key] = value
            with self.subTest(changed=key), patch.object(package, 'read_json', return_value=bad):
                with self.assertRaises(ValueError): package.validate_donor(apk, report)

    def test_current_sources_retain_all_nonreviewed_java_guest_and_native_source_bytes(self):
        donor, _, _, _, _, _, _ = self.actual_fixture()
        current = package.current_sources(donor)
        self.assertEqual(set(current), set(donor['java_sources']))
        self.assertEqual(len(current), 24)
        changed = {name for name in current if current[name] != donor['java_sources'][name]}
        self.assertTrue(changed)
        self.assertLessEqual(changed, package.REVIEWED_JAVA_CHANGES)
        self.assertEqual(package.changed_java_sources(donor), sorted(changed))
        for name in set(current)-package.REVIEWED_JAVA_CHANGES:
            self.assertEqual(current[name], donor['java_sources'][name], name)
        for name, expected in donor['native_build_provenance']['source_files'].items():
            self.assertEqual(package.builder().file_pin(package.ROOT/name), expected, name)
        for name in donor['payloads']:
            if name.startswith('assets/runtime/') and name.endswith('.py'):
                source = 'android/guest/'+Path(name).name
                if source not in package.GUEST_SOURCE_CHANGES:
                    self.assertEqual(package.builder().file_pin(package.ROOT/source), donor['payloads'][name], source)

    def test_unreviewed_java_and_guest_source_pin_changes_cannot_enter_derivative(self):
        donor, _, _, _, _, _, _ = self.actual_fixture()
        for group, key in (('java_sources',
                'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSurface.java'),
                ('java_sources', 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java'),
                ('payloads', 'assets/runtime/client_gpu_profile.py'),
                ('payloads', 'assets/runtime/native_map_startup_contract.py'),
                ('payloads', 'assets/runtime/server_fx_catalog.py'),
                ('native_build_provenance', 'upstream/ouroboros/Game/src/graphics/gfx.c')):
            altered = copy.deepcopy(donor)
            if group == 'native_build_provenance':
                altered[group]['source_files'][key] = package.pin(b'unreviewed source change')
            else:
                altered[group][key] = package.pin(b'unreviewed source change')
            with self.subTest(changed=key), self.assertRaises(ValueError): package.current_sources(altered)

    def test_actual_changed_payloads_are_three_helpers_and_two_manifests_only(self):
        donor, _, _, payloads, _, _, _ = self.actual_fixture()
        expected = {'assets/runtime/'+Path(name).name for name in package.GUEST_SOURCE_CHANGES}
        expected |= {'assets/runtime/client-manifest.json', 'assets/runtime/runtime-manifest.json'}
        self.assertEqual(package.replacement_payloads(donor), expected)
        self.assertEqual(set(payloads), set(donor['payloads']))
        self.assertEqual({name for name in payloads if payloads[name] != donor['payloads'][name]}, expected)
        package.payload_boundaries(payloads, donor)

    def test_actual_derivative_retains_every_archive_native_component_graphics_and_asset_byte(self):
        donor, _, _, payloads, preflight, original, candidate = self.actual_fixture()
        changed = package.replacement_payloads(donor)
        for name in set(original)-changed:
            self.assertEqual(candidate[name], original[name], name)
        for name in donor['payloads']:
            self.assertEqual(package.pin(candidate[name]), payloads[name], name)
        self.assertEqual(preflight['server_archives'], donor['package_preflight']['server_archives'])
        for name in ('game-package.tar.gz', 'client-runtime.zip', 'hardware-renderer.zip',
                'dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'postgresql-runtime.tar.gz',
                'server-fx-catalog.bin', 'server-fx-catalog-manifest.json', 'map-startup-manifest.json',
                'asset-pack-manifest.json'):
            key = 'assets/runtime/'+name
            self.assertEqual(candidate[key], original[key], name)
        self.assertEqual(candidate['classes.dex'], original['classes.dex'])

    def test_actual_game_receipt_serialization_and_existing_native_reader_admissions_remain_exact(self):
        import game_diagnostic as guest
        donor, _, runtime, _, _, original, candidate = self.actual_fixture()
        old = self.tar_members(original['assets/runtime/game-package.tar.gz'])
        retained = self.tar_members(candidate['assets/runtime/game-package.tar.gz'])
        self.assertEqual(retained, old)
        raw = retained['game-package.json']; game = json.loads(raw)
        self.assertEqual(list(game), list(json.loads(old['game-package.json'])))
        self.assertEqual(guest.game_listener_contract(game), guest.evidence.GAME_LOOPBACK_METADATA)
        self.assertTrue(guest.game_loopback_contract(game)['endpoints'])
        progress = guest.mapserver_progress_contract(game)
        import native_map_startup_contract as contract
        receipt = contract.embedded_receipt(game)
        self.assertEqual(progress['producer']['mapserver_sha256'], receipt['mapserver']['sha256'])
        self.assertEqual(package.pin(retained['MapServer.exe']), contract.pin_record(receipt['mapserver']))
        mapping = runtime['client_bundle']['local_server']['mapserver']
        self.assertEqual(mapping, donor['runtime_manifest']['client_bundle']['local_server']['mapserver'])
        self.assertEqual(mapping['package_manifest_sha256'], package.pin(raw)['sha256'])
        with self.assertRaises(ValueError):
            guest.mapserver_progress_contract(json.loads(json.dumps(game, sort_keys=True)))

    def test_manifest_updates_preserve_existing_metadata_order_bindings_and_authority(self):
        donor, commit, runtime, _, _, _, candidate = self.actual_fixture()
        before = copy.deepcopy(donor)
        changed = package.replacement_payloads(donor)-{
            'assets/runtime/client-manifest.json', 'assets/runtime/runtime-manifest.json'}
        helpers = {Path(name).name: package.pin(candidate[name]) for name in changed}
        client, rebuilt = package.verification_manifests(donor, helpers, commit)
        self.assertEqual(donor, before)
        self.assertEqual(rebuilt, runtime)
        self.assertEqual(package.shared.encoded(client), candidate['assets/runtime/client-manifest.json'])
        self.assertEqual(package.shared.encoded(rebuilt), candidate['assets/runtime/runtime-manifest.json'])
        client_original = donor['_client_verification']
        for key in set(client)-{'files'}:
            self.assertEqual(client[key], client_original[key], key)
        self.assertEqual(set(client), set(client_original))
        self.assertEqual(list(client), list(client_original))
        self.assertEqual(set(client['files']), set(client_original['files']))
        self.assertEqual(list(client['files']), list(client_original['files']))
        for name in set(client['files'])-set(helpers):
            self.assertEqual(client['files'][name], client_original['files'][name], name)
        previous = donor['runtime_manifest']
        self.assertEqual(list(rebuilt), list(previous)+['client_report_loading'])
        self.assertEqual(set(rebuilt), set(previous)|{'client_report_loading'})
        for key in set(previous)-{'repository_commit', 'scope', 'files'}:
            self.assertEqual(rebuilt[key], previous[key], key)
            self.assertEqual(package.shared.encoded(rebuilt[key]), package.shared.encoded(previous[key]), key)
        self.assertEqual(set(rebuilt['files']), set(previous['files']))
        self.assertEqual(list(rebuilt['files']), list(previous['files']))
        for name in set(previous['files'])-set(helpers)-{'client-manifest.json'}:
            self.assertEqual(rebuilt['files'][name], previous['files'][name], name)
        self.assertEqual(rebuilt['files']['client-manifest.json'], package.pin(package.shared.encoded(client)))
        metadata = rebuilt['client_report_loading']
        self.assertEqual(metadata['repository_commit'], commit)
        self.assertEqual(metadata['donor_repository_commit'], package.DONOR_COMMIT)
        self.assertEqual(metadata['reviewed_guest_inputs'], helpers)
        for flag in package.FALSE_FLAGS: self.assertIs(metadata[flag], False, flag)
        for flag in package.TRUE_FLAGS: self.assertIs(metadata[flag], True, flag)

    def test_manifest_inputs_reject_extra_missing_or_retained_native_and_graphics_helpers(self):
        donor, commit, _, _, _, _, candidate = self.actual_fixture()
        helpers = {Path(name).name: package.pin(candidate[name]) for name in
            package.replacement_payloads(donor)-{
                'assets/runtime/client-manifest.json', 'assets/runtime/runtime-manifest.json'}}
        for name in ('game-package.tar.gz', 'client_gpu_profile.py', 'unreviewed.py', '../unsafe.py'):
            altered = dict(helpers, **{name: package.pin(b'unreviewed change')})
            with self.subTest(extra=name), self.assertRaises(ValueError):
                package.verification_manifests(donor, altered, commit)
        for name in helpers:
            missing = dict(helpers); del missing[name]
            with self.subTest(missing=name), self.assertRaises(ValueError):
                package.verification_manifests(donor, missing, commit)
            changed = dict(helpers); changed[name] = package.pin(b'wrong reviewed helper bytes')
            with self.subTest(wrong_bytes=name), self.assertRaises(ValueError):
                package.verification_manifests(donor, changed, commit)

    def test_actual_payload_boundary_rejects_any_unreviewed_change_addition_loss_or_unapplied_repair(self):
        donor, _, _, candidate, _, _, _ = self.actual_fixture()
        approved = package.replacement_payloads(donor)
        for name in set(candidate)-approved:
            altered = dict(candidate, **{name: package.pin(b'unreviewed payload bytes')})
            with self.subTest(changed=name), self.assertRaises(ValueError):
                package.payload_boundaries(altered, donor)
        for name in candidate:
            altered = dict(candidate); del altered[name]
            with self.subTest(missing=name), self.assertRaises(ValueError):
                package.payload_boundaries(altered, donor)
        for name in approved:
            altered = dict(candidate); altered[name] = donor['payloads'][name]
            with self.subTest(unapplied=name), self.assertRaises(ValueError):
                package.payload_boundaries(altered, donor)
        for name in ('assets/runtime/unreviewed.py', 'assets/runtime/observer-MapServer.exe', '../unsafe.bin'):
            altered = dict(candidate, **{name: package.pin(b'unreviewed added payload')})
            with self.subTest(added=name), self.assertRaises(ValueError):
                package.payload_boundaries(altered, donor)

    def test_signed_preparation_preserves_component_authority_and_distinguishes_boolean_claims(self):
        proof = {'server_archives': {'game-package.tar.gz': package.pin(b'accepted .32 archive')},
            'map_startup_component': {'repository_commit': 'a'*40,
                'physical_timing_validated': False, 'native_gameplay_validated': False},
            'runtime_assets': {'animation_count': 5878},
            'full_startup': {'format': 1, 'native_runtime_booted': False,
                'physical_execution_validated': False, 'full_prepare_runtime_executed': True}}
        qualification = {'package_preflight': copy.deepcopy(proof)}
        package.require_signed_preflight(proof, qualification)
        for section, key, value in (
                ('server_archives', 'game-package.tar.gz', package.pin(b'changed native archive')),
                ('map_startup_component', 'repository_commit', 'b'*40),
                ('map_startup_component', 'physical_timing_validated', True),
                ('map_startup_component', 'native_gameplay_validated', True),
                ('runtime_assets', 'animation_count', 5877),
                ('full_startup', 'format', True), ('full_startup', 'native_runtime_booted', True),
                ('full_startup', 'physical_execution_validated', True),
                ('full_startup', 'full_prepare_runtime_executed', 1)):
            altered = copy.deepcopy(proof); altered[section][key] = value
            with self.subTest(section=section, changed=key), self.assertRaises(ValueError):
                package.require_signed_preflight(altered, qualification)

    def retained_binary_fixture_inputs(self):
        apk, report = self.actual_inputs()
        donor = json.loads(report.read_bytes()); donor['_apk_path'] = apk
        with zipfile.ZipFile(apk) as archive:
            raw = archive.read('assets/runtime/local_character_server.py')
        return donor, raw

    def test_retained_binary_fixture_guest_methods_close_over_exact_actual_032_dependencies(self):
        import qualify_client_report_loading as qualification
        donor, raw = self.retained_binary_fixture_inputs()
        expected = {
            'test_kings_row_runtime_dependencies': {
                'LEVELUP_UI_REPAIR_BASE_BUNDLE_SHA256', 'LEVELUP_UI_REPAIR_BASE_EXECUTABLE',
                'LEVELUP_UI_REPAIR_ROLE', 'LocalCharacterServer.copy_kings_native_dependencies',
                'MANUAL_ATLAS_ACK', 'MANUAL_ATLAS_ENVIRONMENT', 'STARTUP_BUNDLE_BASE_BUILD_INPUT_SHA256',
                'STARTUP_BUNDLE_BASE_EXECUTABLE', 'STARTUP_BUNDLE_ROLE', 'base', 'dbserver', 'digest_json',
                'hashlib', 'install_manual_atlas_dbserver', 'json', 'levelup_ui_repair_build_input',
                'login', 'manual_atlas_wait_contract', 're', 'require', 'shutil',
                'startup_bundle_build_input', 'startup_bundle_save_contract'},
            'test_map_startup_cache_reuse': {'LocalCharacterServer.data_cache_native_package', 'login', 'require'},
        }
        for name, labels in expected.items():
            with self.subTest(suite=name):
                blocks = qualification.local_dependency_blocks(raw, qualification.RETAINED_GUEST_BLOCKS[name])
                self.assertEqual(set(blocks), labels)
                pins = qualification.retained_guest_block_pins(name, donor)
                self.assertEqual(pins, {label: package.pin(blocks[label]) for label in sorted(labels)})
                self.assertEqual(list(pins), sorted(labels))
                result = qualification.retained_contract_result(name, donor)
                self.assertEqual(result['unchanged_guest_source_blocks'], pins)
                self.assertEqual(result['tests_run'], 11 if name == 'test_kings_row_runtime_dependencies' else 5)
                self.assertIs(result['tests_executed_in_current_run'], False)
                self.assertEqual(result['source_scope'], 'accepted_032_retained_contract')
                self.assertEqual(result['source_repository_commit'], package.DONOR_COMMIT)
        self.assertEqual(qualification.retained_guest_block_pins('test_unrelated_suite', donor), {})

    def test_dependency_block_closure_detects_changed_roles_helpers_and_missing_import_bindings(self):
        import qualify_client_report_loading as qualification
        _, raw = self.retained_binary_fixture_inputs()
        roots = qualification.RETAINED_GUEST_BLOCKS['test_kings_row_runtime_dependencies']
        original = qualification.local_dependency_blocks(raw, roots)
        for label, replacement in (
                ('STARTUP_BUNDLE_ROLE', b"STARTUP_BUNDLE_ROLE = 'forged binary fixture role'"),
                ('require', b'def require(condition, message):\n    return None'),
                ('json', b'')):
            changed = raw.replace(original[label], replacement, 1)
            self.assertNotEqual(changed, raw)
            actual = qualification.local_dependency_blocks(changed, roots)
            with self.subTest(changed_dependency=label):
                self.assertNotEqual({name: package.pin(value) for name, value in actual.items()},
                                   {name: package.pin(value) for name, value in original.items()})
                if label == 'json': self.assertNotIn('json', actual)
        missing = raw.replace(original['require'], b'', 1)
        with self.assertRaisesRegex(ValueError, 'Missing retained module dependency'):
            qualification.local_dependency_blocks(missing, roots)

    def test_retained_binary_fixture_admission_rejects_current_method_and_transitive_dependency_changes(self):
        import qualify_client_report_loading as qualification
        donor, _ = self.retained_binary_fixture_inputs()
        helper = package.ROOT/'android/guest/local_character_server.py'
        current = helper.read_bytes(); original_read = Path.read_bytes
        cases = (
            ('test_kings_row_runtime_dependencies', 'LocalCharacterServer.copy_kings_native_dependencies',
             b'def copy_kings_native_dependencies(self, target):\n        return {}'),
            ('test_map_startup_cache_reuse', 'LocalCharacterServer.data_cache_native_package',
             b'def data_cache_native_package(self):\n        return self.map_package'),
            ('test_kings_row_runtime_dependencies', 'STARTUP_BUNDLE_ROLE',
             b"STARTUP_BUNDLE_ROLE = 'unqualified native role'"),
            ('test_kings_row_runtime_dependencies', 'require',
             b'def require(condition, message):\n    return None'),
        )
        for name, label, replacement in cases:
            old = qualification.source_block(current, label)
            changed = current.replace(old, replacement, 1)
            self.assertNotEqual(changed, current)
            def read(path):
                return changed if path == helper else original_read(path)
            with self.subTest(suite=name, changed=label), patch.object(Path, 'read_bytes', autospec=True, side_effect=read):
                with self.assertRaisesRegex(ValueError, 'Historical binary-fixture'):
                    qualification.retained_guest_block_pins(name, donor)

    def test_current_suite_admission_uses_actual_loader_count_without_executing_test_bodies(self):
        import qualify_client_report_loading as qualification
        import test_client_report_controls_java as controls
        name = 'test_client_report_controls_java'
        row = {'tests_run': 5, 'status': 'passed', 'skipped': 0,
            'source_scope': 'current_033_candidate_sources', 'tests_executed_in_current_run': True}
        with patch.object(unittest.TestSuite, 'run', side_effect=AssertionError('Suite body executed during counting')), \
                patch.object(unittest.TestCase, 'run', side_effect=AssertionError('Test body executed during counting')), \
                patch.object(controls.ReportControlsJava, 'setUpClass', side_effect=AssertionError('Java fixture compiled during counting')):
            self.assertEqual(qualification.current_suite_test_count(name), 5)
            self.assertEqual(qualification.validate_current_suite_result(name, row), row)
        for unknown in ('test_unqualified_suite', 'test_kings_row_runtime_dependencies'):
            with self.subTest(unqualified_or_historical=unknown), self.assertRaises(ValueError):
                qualification.current_suite_test_count(unknown)

    def test_current_suite_admission_rejects_reduced_counts_even_when_qualification_totals_are_adjusted(self):
        import qualify_client_report_loading as qualification
        name = 'test_client_report_controls_java'
        row = {'tests_run': 5, 'status': 'passed', 'skipped': 0,
            'source_scope': 'current_033_candidate_sources', 'tests_executed_in_current_run': True}
        for field, value in (('tests_run', 1), ('tests_run', 5.0), ('tests_run', True),
                ('tests_run', 0), ('skipped', False), ('skipped', 0.0), ('skipped', 1),
                ('status', 'failed'), ('source_scope', 'accepted_032_retained_contract'),
                ('tests_executed_in_current_run', False), ('tests_executed_in_current_run', 1)):
            altered = dict(row, **{field: value})
            with self.subTest(forged=field, value_type=type(value).__name__), self.assertRaises(ValueError):
                qualification.validate_current_suite_result(name, altered)
        with self.assertRaises(ValueError):
            qualification.validate_current_suite_result('test_kings_row_runtime_dependencies', row)
        donor, commit, _, _, _, _, _ = self.actual_fixture()
        reduced = dict(row, tests_run=1)
        candidate = {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE,
            'repository_commit': commit, 'runtime_repository_commit': commit, 'donor': package.donor_link(),
            'map_startup_component': donor['map_startup_component'],
            'java_sources': package.current_sources(donor), 'donor_dex': donor['recompiled_dex'],
            'changed_java_sources': package.changed_java_sources(donor),
            'external_asset_pack': donor['external_asset_pack'], 'native_build_provenance': donor['native_build_provenance'],
            'check_suites': qualification.CHECK_SUITES, 'checks': dict.fromkeys(package.CHECKS, True),
            'test_suites': {name: reduced}, 'tests_run': 1, 'current_tests_run': 1,
            'inherited_tests_retained': 0, 'current_suites_run': 1, 'inherited_suites_retained': 0,
            **dict.fromkeys(package.FALSE_FLAGS, False), **dict.fromkeys(package.TRUE_FLAGS, True)}
        # Narrow only the surrounding inventory fixture. Keep the real loader
        # and row validator, so consistent forged totals cannot reduce five
        # actual source scenarios to a fabricated one-test pass.
        with patch.object(package, 'module', return_value=qualification), \
                patch.object(qualification, 'validate_suite_inventory'), \
                patch.object(qualification, 'TEST_MODULES', (name,)), \
                patch.object(qualification, 'RETAINED_CONTRACT_MODULES', frozenset()), \
                patch.object(qualification, 'validate_current_suite_result', wraps=qualification.validate_current_suite_result) as admission:
            with self.assertRaisesRegex(ValueError, 'exact loader scenario count'):
                package.validate_qualification(candidate, commit, donor)
            admission.assert_called_once_with(name, reduced)

    def audit_fixture(self):
        """Metadata fixture after admission; this helper performs no APK audit."""
        donor, commit, runtime, payloads, preflight, _, _ = self.actual_fixture()
        source_names = ('android/guest/local_character_server.py', 'android/guest/atlas_beacon_package.py')
        sources = {name: package.builder().file_pin(package.ROOT/name) for name in source_names}
        qualification = {'format': 1, 'source_files': sources,
            'fixture_scope': 'audit receipt binding only; actual signed-byte admission is independently required'}
        report = {'apk': package.APK_NAME, **package.pin(b'synthetic signed-byte audit identity fixture'),
            'version_name': package.VERSION_NAME, 'version_code': package.VERSION_CODE,
            'repository_commit': commit, 'donor': package.donor_link(),
            'recompiled_dex': package.pin(b'synthetic independently compiled DEX fixture'),
            'runtime_manifest_sha256': payloads['assets/runtime/runtime-manifest.json']['sha256'],
            'payloads': copy.deepcopy(payloads), 'qualification': qualification,
            'package_preflight': copy.deepcopy(preflight),
            'map_startup_component': copy.deepcopy(donor['map_startup_component']),
            'external_asset_pack': copy.deepcopy(donor['external_asset_pack'])}
        return report, package.pin(package.shared.encoded(report)), package.pin(package.shared.encoded(qualification))

    def test_signed_audit_record_binds_every_authority_without_claiming_device_execution(self):
        report, build_pin, qualification_pin = self.audit_fixture()
        original = copy.deepcopy(report)
        receipt = package.audit_record(report, build_pin, qualification_pin)
        self.assertEqual(package.CLIENT_APK_AUDIT_NAME, 'client-report-loading-apk-audit.json')
        self.assertIs(type(receipt['format']), int); self.assertEqual(receipt['format'], 1)
        self.assertEqual(receipt['status'], 'passed')
        self.assertEqual(receipt['scope'], 'actual_signed_apk_independent_host_audit')
        self.assertEqual(receipt['repository_commit'], report['repository_commit'])
        self.assertEqual(receipt['repository_tree'], package.source_tree(report['repository_commit']))
        self.assertEqual(receipt['build_report'], build_pin)
        self.assertEqual(receipt['qualification_receipt'], qualification_pin)
        self.assertEqual(receipt['donor'], package.donor_link())
        self.assertEqual(receipt['independently_recompiled_dex'], report['recompiled_dex'])
        self.assertEqual(receipt['apk'], {key: report[key] for key in
            ('apk', 'bytes', 'sha256', 'version_name', 'version_code')})
        for field, authority in (
                ('qualified_source_closure', report['qualification']['source_files']),
                ('candidate_payload_inventory', report['payloads']),
                ('retained_native_server_archives', report['package_preflight']['server_archives']),
                ('retained_map_startup_component', report['map_startup_component']),
                ('retained_external_assets', report['external_asset_pack']),
                ('actual_package_preflight', report['package_preflight'])):
            self.assertEqual(receipt[field], package.pin(package.shared.encoded(authority)), field)
        self.assertEqual(receipt['runtime_manifest_sha256'], report['runtime_manifest_sha256'])
        self.assertEqual(receipt['reviewed_guest_inputs'], {
            Path(name).name: report['payloads']['assets/runtime/'+Path(name).name]
            for name in package.GUEST_SOURCE_CHANGES})
        for flag in ('actual_runtime_asset_installers_verified', 'full_startup_orchestration_verified',
                'signature_and_version_only_manifest_verified', 'exact_native_and_payload_boundaries_verified'):
            self.assertIs(receipt[flag], True, flag)
        for flag in ('native_runtime_booted', 'physical_execution_validated',
                'live_database_and_saved_character_executed', 'physical_map_startup_speedup_validated',
                'sub_30_second_map_startup_validated'):
            self.assertIs(receipt[flag], False, flag)
        self.assertEqual(receipt['process_and_sql_boundary'], 'not_executed')
        serialized = json.loads(package.shared.encoded(receipt))
        self.assertEqual(package.validate_audit_record(serialized, report, build_pin, qualification_pin), receipt)
        self.assertEqual(report, original)

    def test_signed_audit_record_rejects_forged_flags_pins_omissions_and_unreviewed_fields(self):
        report, build_pin, qualification_pin = self.audit_fixture()
        receipt = package.audit_record(report, build_pin, qualification_pin)
        for field, value in (('format', True), ('status', 'incomplete'), ('repository_commit', package.DONOR_COMMIT),
                ('repository_tree', '0'*40), ('runtime_manifest_sha256', '0'*64),
                ('actual_runtime_asset_installers_verified', False), ('full_startup_orchestration_verified', False),
                ('actual_runtime_asset_installers_verified', 1), ('full_startup_orchestration_verified', 1),
                ('native_runtime_booted', True), ('native_runtime_booted', 0),
                ('physical_execution_validated', True), ('physical_execution_validated', 0),
                ('live_database_and_saved_character_executed', True),
                ('physical_map_startup_speedup_validated', True), ('sub_30_second_map_startup_validated', True),
                ('process_and_sql_boundary', 'executed'),
                ('independently_recompiled_dex', package.pin(b'wrong DEX')),
                ('build_report', package.pin(b'wrong build report')),
                ('qualification_receipt', package.pin(b'wrong qualification')),
                ('qualified_source_closure', package.pin(b'wrong source closure')),
                ('candidate_payload_inventory', package.pin(b'wrong candidate payloads')),
                ('retained_native_server_archives', package.pin(b'wrong native archives')),
                ('retained_map_startup_component', package.pin(b'wrong native component')),
                ('retained_external_assets', package.pin(b'wrong asset pack')),
                ('actual_package_preflight', package.pin(b'unexecuted preflight'))):
            altered = copy.deepcopy(receipt); altered[field] = value
            with self.subTest(forged=field, value_type=type(value).__name__), self.assertRaises(ValueError):
                package.validate_audit_record(altered, report, build_pin, qualification_pin)
        for section, field, value in (('apk', 'bytes', report['bytes']+1), ('apk', 'sha256', '0'*64),
                ('apk', 'version_code', True), ('donor', 'repository_commit', '0'*40),
                ('reviewed_guest_inputs', 'local_character_server.py', package.pin(b'changed helper'))):
            altered = copy.deepcopy(receipt); altered[section][field] = value
            with self.subTest(section=section, forged=field), self.assertRaises(ValueError):
                package.validate_audit_record(altered, report, build_pin, qualification_pin)
        for field in receipt:
            altered = copy.deepcopy(receipt); del altered[field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                package.validate_audit_record(altered, report, build_pin, qualification_pin)
        extra = dict(receipt, unreviewed_device_success=True)
        with self.assertRaises(ValueError): package.validate_audit_record(extra, report, build_pin, qualification_pin)

    def test_signed_audit_record_cannot_be_replayed_for_changed_source_or_report_authority(self):
        report, build_pin, qualification_pin = self.audit_fixture()
        receipt = package.audit_record(report, build_pin, qualification_pin)
        for key, value in (('apk', package.DONOR_APK_NAME), ('version_name', '0.13.32'), ('version_code', 47),
                ('bytes', report['bytes']+1), ('sha256', '0'*64),
                ('recompiled_dex', package.pin(b'other DEX')), ('runtime_manifest_sha256', '0'*64),
                ('donor', dict(package.donor_link(), repository_commit='0'*40))):
            altered = copy.deepcopy(report); altered[key] = value
            with self.subTest(report_changed=key), self.assertRaises(ValueError):
                package.validate_audit_record(receipt, altered, build_pin, qualification_pin)
        changed = copy.deepcopy(report)
        changed['qualification']['source_files']['android/guest/atlas_beacon_package.py'] = package.pin(b'other source')
        with self.assertRaises(ValueError): package.validate_audit_record(receipt, changed, build_pin, qualification_pin)
        reordered = copy.deepcopy(report)
        reordered['qualification']['source_files'] = dict(sorted(reordered['qualification']['source_files'].items()))
        self.assertEqual(reordered['qualification']['source_files'], report['qualification']['source_files'])
        self.assertNotEqual(package.shared.encoded(reordered['qualification']['source_files']),
                            package.shared.encoded(report['qualification']['source_files']))
        with self.assertRaises(ValueError): package.validate_audit_record(receipt, reordered, build_pin, qualification_pin)
        with self.assertRaises(ValueError): package.validate_audit_record(receipt, report, package.pin(b'other report'), qualification_pin)
        with self.assertRaises(ValueError): package.validate_audit_record(receipt, report, build_pin, package.pin(b'other qualification'))
        for bad_pin in ({'bytes': True, 'sha256': 'a'*64}, {'bytes': 0, 'sha256': 'a'*64},
                {'bytes': 256*1024**2+1, 'sha256': 'a'*64}, {'bytes': 1, 'sha256': 'A'*64},
                {'bytes': 1, 'sha256': 'a'*63}, {'bytes': 1, 'sha256': 'a'*64, 'extra': True}):
            with self.subTest(unbounded_pin=bad_pin), self.assertRaises(ValueError):
                package.audit_record(report, bad_pin, qualification_pin)
            with self.subTest(unbounded_qualification_pin=bad_pin), self.assertRaises(ValueError):
                package.audit_record(report, build_pin, bad_pin)

    def test_light_signed_payload_verification_retains_native_bytes_without_repeating_heavy_preparation(self):
        donor, commit, runtime, payloads, preflight, _, candidate = self.actual_fixture()
        dex = b'synthetic reviewed DEX for payload-boundary fixture only'
        with tempfile.TemporaryDirectory(prefix='coh-report-loading-light-signed-') as temporary:
            apk = Path(temporary)/package.APK_NAME
            with zipfile.ZipFile(donor['_apk_path']) as source, zipfile.ZipFile(apk, 'w', zipfile.ZIP_DEFLATED) as target:
                for name, raw in candidate.items():
                    target.writestr(name, dex if name == 'classes.dex' else raw,
                                    compress_type=source.getinfo(name).compress_type)
                target.writestr('AndroidManifest.xml', source.read('AndroidManifest.xml'))
            with patch.object(package, 'actual_asset_preflight', side_effect=AssertionError('Duplicate asset preparation')), \
                    patch.object(package, 'actual_startup_preflight', side_effect=AssertionError('Duplicate startup preparation')):
                actual_runtime, actual_preflight = package.verify_derivative(
                    apk, donor, payloads, package.pin(dex), commit, execute_preflight=False)
        self.assertEqual(actual_runtime, runtime)
        self.assertEqual(actual_preflight, preflight)
        self.assertNotIn('runtime_assets', actual_preflight)
        self.assertNotIn('full_startup', actual_preflight)

    def test_independent_audit_writes_receipt_only_after_successful_full_signed_byte_admission(self):
        from types import SimpleNamespace
        report, build_pin, qualification_pin = self.audit_fixture()
        commit = report['repository_commit']
        with tempfile.TemporaryDirectory(prefix='coh-report-loading-audit-handoff-') as temporary:
            directory = Path(temporary)
            args = SimpleNamespace(build_report=directory/package.REPORT_NAME,
                qualification=directory/'qualification.json', audit_receipt=directory/package.CLIENT_APK_AUDIT_NAME)
            args.build_report.write_bytes(package.shared.encoded(report))
            args.qualification.write_bytes(package.shared.encoded(report['qualification']))
            with patch.object(package, 'verify_report', side_effect=ValueError('Signed-byte admission failed')) as verify:
                with self.assertRaisesRegex(ValueError, 'admission failed'): package.audit(args, commit)
                verify.assert_called_once_with(args, commit)
            self.assertFalse(args.audit_receipt.exists())
            with patch.object(package, 'verify_report', return_value=(report, None, None)) as verify, \
                    contextlib.redirect_stdout(io.StringIO()):
                receipt = package.audit(args, commit)
                verify.assert_called_once_with(args, commit)
            self.assertEqual(args.audit_receipt.read_bytes(), package.shared.encoded(receipt))
            self.assertEqual(package.validate_audit_record(json.loads(args.audit_receipt.read_bytes()),
                report, build_pin, qualification_pin), receipt)
            before = args.audit_receipt.read_bytes()
            with patch.object(package, 'verify_report', return_value=(report, None, None)), self.assertRaises(ValueError):
                package.audit(args, commit)
            self.assertEqual(args.audit_receipt.read_bytes(), before)

    def test_publication_requires_matching_independent_audit_receipt_before_any_api_call(self):
        from types import SimpleNamespace
        report, build_pin, qualification_pin = self.audit_fixture()
        receipt = package.audit_record(report, build_pin, qualification_pin)
        authorized_marker = {'publish_enabled': True, 'version': package.VERSION_NAME,
            'version_code': package.VERSION_CODE, 'donor_commit': package.DONOR_COMMIT}
        original_read = package.read_json
        def read(path):
            return authorized_marker if Path(path) == package.ROOT/package.MARKER else original_read(path)
        with tempfile.TemporaryDirectory(prefix='coh-report-loading-publish-handoff-') as temporary:
            directory = Path(temporary)
            args = SimpleNamespace(build_report=directory/package.REPORT_NAME,
                qualification=directory/'qualification.json', audit_receipt=directory/package.CLIENT_APK_AUDIT_NAME,
                donor_build_report=directory/package.DONOR_REPORT_NAME)
            args.build_report.write_bytes(package.shared.encoded(report))
            args.qualification.write_bytes(package.shared.encoded(report['qualification']))
            wrong_apk = copy.deepcopy(receipt); wrong_apk['apk']['sha256'] = '0'*64
            device_claim = dict(receipt, physical_execution_validated=True)
            different_report = dict(receipt, build_report=package.pin(b'other build report'))
            for forged in (None, wrong_apk, device_claim, different_report):
                if forged is None:
                    if args.audit_receipt.exists(): args.audit_receipt.unlink()
                else: args.audit_receipt.write_bytes(package.shared.encoded(forged))
                with self.subTest(receipt_missing=forged is None), \
                        patch.dict(os.environ, {'GITHUB_REPOSITORY': package.REPOSITORY,
                            'GITHUB_REF': 'refs/heads/'+package.BRANCH, 'GITHUB_EVENT_NAME': 'push',
                            'GITHUB_SHA': report['repository_commit'], 'GH_TOKEN': 'unused-fixture-token'}), \
                        patch.object(package, 'read_json', side_effect=read), \
                        patch.object(package, 'verify_report', return_value=(report, None, None)) as verify, \
                        patch.object(package, 'module', side_effect=AssertionError('Publication API reached before audit admission')) as api:
                    with self.assertRaises((ValueError, FileNotFoundError)): package.publish(args)
                    verify.assert_called_once_with(args, report['repository_commit'], execute_preflight=False)
                    api.assert_not_called()

    def test_light_extraction_never_runs_preparation_or_native_component_builds(self):
        apk, report = self.actual_inputs(); donor = package.validate_donor(apk, report)
        commit = package.builder().source_commit(os.environ.get('COH_REPORT_LOADING_TEST_SOURCE_COMMIT'))
        with tempfile.TemporaryDirectory(prefix='coh-report-loading-no-preflight-') as temporary:
            with patch.object(package, 'actual_asset_preflight', side_effect=AssertionError('heavy asset gate')), \
                    patch.object(package, 'actual_startup_preflight', side_effect=AssertionError('heavy startup gate')):
                _, payloads, preflight = package.extract_and_repair(
                    apk, donor, Path(temporary)/'candidate', commit, execute_preflight=False)
        package.payload_boundaries(payloads, donor)
        self.assertNotIn('runtime_assets', preflight)
        self.assertNotIn('full_startup', preflight)


if __name__ == '__main__': unittest.main()
