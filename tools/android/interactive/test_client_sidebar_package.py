"""Actual ZIP conservation and qualification gates for the Android-only sidebar."""
import contextlib
import copy
import fnmatch
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error
import zipfile

import build_client_sidebar_apk as package
import test_client_gameplay_performance_package as previous

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


@contextlib.contextmanager
def candidate(folder):
    with previous.candidate(folder) as prior:
        apk = prior[0]; donor = copy.deepcopy(prior[2])
        donor.update(payloads=copy.deepcopy(prior[3]), runtime_manifest=copy.deepcopy(prior[4]))
    with zipfile.ZipFile(apk) as archive:
        donor['retained_dex'] = pin(archive.read('classes.dex'))
    runtime, payloads, preflight = package.extract_retained(apk, donor, folder/'sidebar-files')
    output = folder/'sidebar.apk'; dex = b'actual-Android-only-sidebar-DEX'; dex_pin = pin(dex)
    with zipfile.ZipFile(output, 'w') as archive, zipfile.ZipFile(apk) as original:
        for name in payloads: archive.write(folder/'sidebar-files'/name, name)
        for name in donor['retained_android_resources']: archive.writestr(name, original.read(name))
        archive.writestr('classes.dex', dex); archive.writestr('AndroidManifest.xml', b'version-only-shell')
    yield output, apk, donor, payloads, runtime, preflight, dex_pin


def qualification():
    q = package.module('sidebar_test_qualification', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE, 'repository_commit': COMMIT,
        'runtime_repository_commit': package.DONOR_COMMIT, 'donor': package.donor_link(),
        'checks': {name: True for name in package.CHECKS}, **{name: False for name in package.FALSE_FLAGS},
        'java_or_dex_recompiled': True, 'installed_runtime_identity_preserved': True,
        'native_client_package_reused': True, 'retained_native_source_and_Win32_proof_verified': True,
        'test_suites': {name: {'status': 'passed', 'skipped': 0, 'tests_run': 1} for name in q.TEST_MODULES},
        'tests_run': len(q.TEST_MODULES), 'check_suites': copy.deepcopy(q.CHECK_SUITES),
        'source_files': {name: pin(b'source') for name in package.SOURCE_FILES},
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback'],
        'postgresql_levelup_fixtures': sorted(package.retained.levelup_postgresql_fixtures())}


class ClientSidebarPackageTests(unittest.TestCase):
    def verify(self, values):
        return package.verify_derivative(values[0], values[2], values[3], values[6])

    def test_version_and_exact_frozen_runtime_donor(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.18', 33))
        self.assertEqual(package.DONOR_RUN_ID, 37622107943)
        self.assertEqual(package.DONOR_BUILD, {'bytes': 5014125, 'sha256': '38ec339829afd5d326887fee3c5d5d537e86f38e317f22c8765ee7f650418eb4'})
        self.assertEqual(package.DONOR_GAME, {'bytes': 9477120, 'sha256': '5b6cfb6d20eb5f6642d6d1124e6b5ba188e89f9ad58c26268f0be35d996134aa'})
        self.assertEqual((len(package.JAVA_CHANGES), len(package.JAVA_ADDITIONS), len(package.REPLACED_PAYLOADS)), (5, 0, 0))

    def test_all75_runtime_payloads_and_native_archive_bytes_and_generation_retained(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            self.assertEqual(self.verify(values), values[4]); self.assertEqual(len(values[3]), 75)
            self.assertEqual(values[3], values[2]['payloads']); self.assertEqual(values[5], values[2]['server_payload_extraction_preflight'])
            with zipfile.ZipFile(values[0]) as current, zipfile.ZipFile(values[1]) as donor:
                for name in values[3]: self.assertEqual(current.read(name), donor.read(name), name)
                for name in values[2]['retained_android_resources']: self.assertEqual(current.read(name), donor.read(name), name)
                self.assertNotEqual(current.read('classes.dex'), donor.read('classes.dex'))
            self.assertEqual(values[4], values[2]['runtime_manifest'])

    def test_game_helpers_manifests_server_cache_visual_and_beacon_mutations_rejected(self):
        for name in ('client-runtime.zip', 'client_interactive_diagnostic.py', 'client_startup_diagnostic.py',
                'native_responsiveness_contract.py', 'texture_header_index.py', 'runtime-manifest.json',
                'client-manifest.json', 'game-package.tar.gz', 'dbserver-package.tar.gz',
                'dbserver-schema.tar.gz', 'server-caches.zip', 'client-caches.zip',
                'atlas-beacons.zip', 'client-visual-assets.zip'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'foreign')
                values[3][member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'retained runtime payloads'): self.verify(values)

    def test_unchanged_dex_resources_foreign_and_duplicate_members_rejected(self):
        for mutation in ('unchanged_dex', 'resource', 'extra', 'duplicate'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                if mutation == 'unchanged_dex':
                    with zipfile.ZipFile(values[1]) as donor: raw = donor.read('classes.dex')
                    replace_member(values[0], 'classes.dex', raw)
                    values = (*values[:6], pin(raw))
                elif mutation == 'resource': replace_member(values[0], 'resources.arsc', b'foreign')
                elif mutation == 'extra':
                    with zipfile.ZipFile(values[0], 'a') as archive: archive.writestr('assets/runtime/foreign', b'foreign')
                else:
                    with zipfile.ZipFile(values[0], 'a') as archive, self.assertWarns(UserWarning): archive.writestr('classes.dex', b'foreign')
                with self.assertRaises(ValueError): self.verify(values)

    def test_java_scope_retains14_sources_and_rejects_surface_or_inventory_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); names = sorted(package.JAVA_CHANGES)+[
                package.JAVA_ROOT+'ClientSurface.java', *('retained/File'+str(i)+'.java' for i in range(13))]
            for name in names:
                target = folder/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b'accepted-java')
            manifest = folder/'android/interactive/src/main/AndroidManifest.xml'; manifest.parent.mkdir(parents=True, exist_ok=True); manifest.write_bytes(b'accepted-manifest')
            donor = {'java_sources': {name: pin(b'accepted-java') for name in names}, 'preserved_sources': {},
                'payloads': {}, 'source_manifest': pin(b'accepted-manifest'), 'qualification': {'source_files': {}}}
            for name in package.JAVA_CHANGES: (folder/name).write_bytes(b'reviewed-sidebar-java')
            sources = [folder/name for name in names]
            with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package.retained.retained, 'java_sources', return_value=sources):
                _, pins, changed = package.current_java_sources(donor, folder/'generated')
                self.assertEqual(len(pins), 19); self.assertEqual(set(changed), package.JAVA_CHANGES)
                surface = folder/(package.JAVA_ROOT+'ClientSurface.java'); surface.write_bytes(b'foreign')
                with self.assertRaisesRegex(ValueError, 'Java changes'): package.current_java_sources(donor, folder/'generated')
                surface.write_bytes(b'accepted-java')
                with mock.patch.object(package.retained.retained, 'java_sources', return_value=sources[:-1]), self.assertRaisesRegex(ValueError, 'inventory'):
                    package.current_java_sources(donor, folder/'generated')

    def test_exact_retained_suites_source_pg_and_native_runtime_claims_required(self):
        receipt = qualification()
        with mock.patch.object(package, 'builder'):
            package.validate_qualification(receipt, COMMIT)
            for mutation in ('skip', 'suite', 'source', 'pg', 'native_recompiled', 'runtime_refresh', 'identity', 'native_proof'):
                changed = copy.deepcopy(receipt)
                if mutation == 'skip': next(iter(changed['test_suites'].values()))['skipped'] = 1
                elif mutation == 'suite': changed['test_suites'].pop(next(iter(changed['test_suites'])))
                elif mutation == 'source': changed['source_files'].pop(next(iter(package.SOURCE_FILES)))
                elif mutation == 'pg': changed['postgresql_levelup_fixtures'] = []
                elif mutation == 'native_recompiled': changed['native_client_recompiled'] = True
                elif mutation == 'runtime_refresh': changed['runtime_refresh_required'] = True
                elif mutation == 'identity': changed['installed_runtime_identity_preserved'] = False
                else: changed['retained_native_source_and_Win32_proof_verified'] = False
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): package.validate_qualification(changed, COMMIT)

    def test_workflow_never_rebuilds_native_and_has_fresh_and_public_sdk_audits(self):
        source = (package.ROOT/package.WORKFLOW).read_text()
        self.assertNotIn('windows-', source); self.assertNotIn('cmake ', source); self.assertNotIn('package_client_gameplay_performance_native.py', source)
        self.assertIn('coh-client-gameplay-performance-native', source); self.assertIn('run-id: 37622107943', source)
        self.assertIn("PYTHONHASHSEED: '73418'", source); self.assertIn("PYTHONHASHSEED: '1817'", source)
        self.assertLess(source.index('Fresh-process SDK source payload'), source.index('Publish only the newly qualified'))
        public = source.split('  public-audit:', 1)[1]
        self.assertIn('contents: read', public); self.assertNotIn('contents: write', public)
        self.assertIn('Download actual public APK checksum and testing notes', public)
        self.assertIn('Existing performance release differs', source); self.assertIn('sidebar_push', source)
        from classify_storage_cleanup_change import SIDEBAR_SOURCES
        block = source.split('    paths:\n', 1)[1].split('  workflow_dispatch:', 1)[0]
        patterns = [line.split('      - ', 1)[1] for line in block.splitlines() if line.startswith('      - ')]
        for name in SIDEBAR_SOURCES:
            with self.subTest(source=name): self.assertTrue(any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns))

    def test_superseded_head_blocks_release_creation_and_publication(self):
        for scenario in ('current', 'stale_before_creation', 'stale_during_upload'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); assets = tuple(folder/name for name in
                    (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME))
                for path in assets: path.write_bytes(b'fully-verified-release-fixture')
                report = dict(pin(assets[0].read_bytes()), repository_commit=COMMIT)
                api = mock.Mock(); heads = []

                def request(path, data=None, **kwargs):
                    if path == '/git/ref/heads/'+package.BRANCH:
                        heads.append(path)
                        stale = scenario == 'stale_before_creation' or (scenario == 'stale_during_upload' and len(heads) > 1)
                        return {'ref': 'refs/heads/'+package.BRANCH,
                            'object': {'type': 'commit', 'sha': 'b'*40 if stale else COMMIT}}
                    if path.startswith(('/releases/tags/', '/git/ref/tags/')):
                        raise urllib.error.HTTPError('https://api.github.com', 404, 'Not Found', {}, None)
                    if path == '/releases':
                        return {'id': 1, 'draft': True, 'prerelease': True, 'tag_name': package.RELEASE_TAG}
                    if path.startswith('/releases/1/assets?'):
                        record = pin(data.read_bytes())
                        return {'state': 'uploaded', 'name': data.name, 'size': record['bytes'], 'digest': 'sha256:'+record['sha256']}
                    self.assertEqual(path, '/releases/1')
                    return {'id': 1, 'draft': False, 'prerelease': True, 'tag_name': package.RELEASE_TAG,
                        'html_url': 'https://github.com/'+package.REPOSITORY+'/releases/tag/'+package.RELEASE_TAG}

                api.request.side_effect = request
                if scenario == 'current':
                    self.assertIn(package.RELEASE_TAG, package.publish_release(api, report, assets, 'qualified notes'))
                    self.assertEqual(len(heads), 2)
                else:
                    with self.assertRaisesRegex(ValueError, 'superseded'):
                        package.publish_release(api, report, assets, 'qualified notes')
                    self.assertFalse(any(call.kwargs.get('method') == 'PATCH' for call in api.request.call_args_list))
                    if scenario == 'stale_before_creation':
                        self.assertFalse(any(call.kwargs.get('method') == 'POST' for call in api.request.call_args_list))


if __name__ == '__main__': unittest.main()
