"""Execute .21 conservation, frozen GPU provenance and publication guards.

Archive-policy fixtures explicitly replace native compilation/authentication;
they never qualify fixture ELF/PE bytes as production. APK extraction, finite
inventories, nested byte conservation and derivative verification remain real.
The hosted lane independently authenticates the pinned donor and Win32 proof.
"""
import argparse
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import urllib.error
import warnings
import zipfile
from unittest import mock

import build_client_gpu_repair_apk as package
import package_client_gpu_repair as repair
import test_client_gpu_profile_package as previous
from test_client_gpu_runtime_package import write_zip

COMMIT = 'a' * 40
RUN = 'https://github.com/Russianranger/coh-android/actions/runs/123456'
pin, replace_member = previous.pin, previous.replace_member


@contextlib.contextmanager
def candidate(folder):
    """Use the qualified .20 archive fixture, replacing exactly four payloads."""
    with previous.candidate(folder) as prior:
        apk, donor = prior[0], copy.deepcopy(prior[2])
        donor.update(payloads=copy.deepcopy(prior[3]), runtime_manifest=copy.deepcopy(prior[4]),
            recompiled_dex=copy.deepcopy(prior[8]), client_gpu_runtime=copy.deepcopy(prior[9]))
        with zipfile.ZipFile(apk) as archive:
            donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        donor['runtime_manifest']['repository_commit'] = package.DONOR_COMMIT
        for name in package.HELPERS:
            (folder / 'android/guest' / name).write_bytes(('reviewed-probe-repair-' + name).encode())
        directory = folder / 'repaired-gpu'; directory.mkdir()
        (directory / package.GPU_ARCHIVE).write_bytes(b'qualified-probe-only-repair-fixture')
        gpu = {'repository_commit': COMMIT, 'run_url': RUN,
            'files': {package.GPU_ARCHIVE: pin((directory / package.GPU_ARCHIVE).read_bytes())}}
        with mock.patch.object(package, 'ROOT', folder):
            runtime, payloads = package.extract_and_repair(apk, donor, folder / 'gpu-probe-repair-files', COMMIT, directory, gpu)
            output = folder / 'gpu-probe-repair.apk'; dex = b'recompiled-bounded-client-evidence-DEX'
            with zipfile.ZipFile(output, 'w') as archive, zipfile.ZipFile(apk) as original:
                for name in payloads: archive.write(folder / 'gpu-probe-repair-files' / name, name)
                for name in donor['retained_android_resources']: archive.writestr(name, original.read(name))
                archive.writestr('classes.dex', dex); archive.writestr('AndroidManifest.xml', b'version-only-update')
            yield {'apk': output, 'original': apk, 'donor': donor, 'payloads': payloads,
                'runtime': runtime, 'gpu': gpu, 'dex': pin(dex)}


def qualification():
    q = package.module('repair_package_qualification', package.ROOT / package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE,
        'repository_commit': COMMIT, 'runtime_repository_commit': COMMIT, 'donor': package.donor_link(),
        'checks': dict.fromkeys(package.CHECKS, True), **dict.fromkeys(package.FALSE_FLAGS, False),
        **dict.fromkeys(package.TRUE_FLAGS, True), 'installed_runtime_identity_preserved': False,
        'test_suites': {name: {'status': 'passed', 'skipped': 0, 'tests_run': 1} for name in q.TEST_MODULES},
        'tests_run': len(q.TEST_MODULES), 'check_suites': copy.deepcopy(q.CHECK_SUITES),
        'source_files': {name: pin(b'source-policy-fixture') for name in package.SOURCE_FILES},
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback'],
        'postgresql_levelup_fixtures': sorted(package.retained.levelup_postgresql_fixtures())}


class RepairApkTests(unittest.TestCase):
    def verify(self, v):
        return package.verify_derivative(v['apk'], v['donor'], v['payloads'], v['dex'], COMMIT, v['gpu'])

    def test_exact_public_donor_version_and_four_payload_boundary(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.21', 36))
        self.assertEqual((package.DONOR_COMMIT, package.DONOR_RUN_ID), ('5a592380a5272a187248a1f971d9798a298ca5c0', 37788954170))
        self.assertEqual(package.DONOR_APK, {'bytes': 1560271624, 'sha256': 'ac99a528e088bccce6e3164de62b55408624e3027ebaef24bce0f8c9f9e8b94e'})
        self.assertEqual(package.DONOR_BUILD, {'bytes': 5244666, 'sha256': '2a86d163f90a4f1bd30a7d799c5030647a717d890d7395f8931aac67397fa848'})
        self.assertEqual(package.REPLACED_PAYLOADS, frozenset('assets/runtime/' + name for name in
            ('client_gpu_profile.py', package.GPU_ARCHIVE, 'client-manifest.json', 'runtime-manifest.json')))
        self.assertEqual(len(package.JAVA_CHANGES), 2)
        self.assertNotIn('assets/runtime/client-runtime.zip', package.REPLACED_PAYLOADS)
        self.assertNotIn('android/runtime-lock.json', package.REVIEWED_DONOR_SOURCE_CHANGES)

    def test_real77_payloads73_retained_all22_native_members_resources_and_default(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as v:
            self.assertEqual(self.verify(v), v['runtime']); self.assertEqual(len(v['payloads']), 77)
            changed = {name for name in v['payloads'] if v['payloads'][name] != v['donor']['payloads'][name]}
            self.assertEqual(changed, package.REPLACED_PAYLOADS)
            with zipfile.ZipFile(v['apk']) as current, zipfile.ZipFile(v['original']) as donor:
                for name in set(v['payloads']) - changed: self.assertEqual(current.read(name), donor.read(name), name)
                for name in v['donor']['retained_android_resources']: self.assertEqual(current.read(name), donor.read(name), name)
                self.assertNotEqual(current.read('classes.dex'), donor.read('classes.dex'))
                with zipfile.ZipFile(io.BytesIO(current.read('assets/runtime/client-runtime.zip'))) as native:
                    self.assertEqual(len(native.namelist()), 22)
                    for name, expected in v['donor']['_client_members'].items(): self.assertEqual(pin(native.read(name)), expected, name)
            self.assertEqual(v['runtime']['client_gpu_profile']['default_profile'], 'software')
            self.assertIs(v['runtime']['client_gpu_profile']['hardware_opt_in'], True)
            self.assertIs(v['runtime']['client_gpu_profile']['physical_hardware_renderer_validated'], False)
            for key, value in v['donor']['runtime_manifest'].items():
                if key not in ('files', 'repository_commit', 'scope', 'client_gpu_profile'):
                    self.assertEqual(v['runtime'][key], value, key)

    def test_resealed_native_server_cache_Wine_FEX_and_unreviewed_helpers_fail_closed(self):
        names = ('client-runtime.zip', 'game-package.tar.gz', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz',
            'client-caches.zip', 'server-caches.zip', 'atlas-beacons.zip', 'client-visual-assets.zip',
            'native_responsiveness_contract.py', 'native_training_save.py', 'local_login_server.py')
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as v:
                member = 'assets/runtime/' + name
                replace_member(v['apk'], member, b'foreign-with-valid-ZIP-CRC'); v['payloads'][member] = pin(b'foreign-with-valid-ZIP-CRC')
                with self.assertRaisesRegex(ValueError, 'four repaired payloads'): self.verify(v)

    def test_current_helper_gpu_dex_resources_and_exact_zip_inventory_are_bound(self):
        names = ('assets/runtime/client_gpu_profile.py', 'assets/runtime/' + package.GPU_ARCHIVE,
            'classes.dex', 'resources.arsc', 'unchanged_dex', 'duplicate', 'missing', 'extra')
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as v:
                if name == 'unchanged_dex':
                    with zipfile.ZipFile(v['original']) as donor: raw = donor.read('classes.dex')
                    replace_member(v['apk'], 'classes.dex', raw); v['dex'] = pin(raw)
                elif name == 'duplicate':
                    with warnings.catch_warnings(), zipfile.ZipFile(v['apk'], 'a') as archive:
                        warnings.simplefilter('ignore', UserWarning); archive.writestr('classes.dex', b'foreign')
                elif name == 'missing': v['payloads'].pop('assets/runtime/client_gpu_profile.py')
                elif name == 'extra': v['payloads']['assets/runtime/unreviewed.so'] = pin(b'foreign')
                else:
                    replace_member(v['apk'], name, b'foreign')
                    if name in v['payloads']: v['payloads'][name] = pin(b'foreign')
                with self.assertRaises(ValueError): self.verify(v)

    def test_only_two_reviewed_Java_sources_change_and_all_remaining_sources_stay_pinned(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            names = sorted(package.JAVA_CHANGES) + ['retained/File' + str(i) + '.java' for i in range(17)]
            for name in names:
                target = folder / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b'accepted-java')
            manifest = folder / 'android/interactive/src/main/AndroidManifest.xml'
            manifest.parent.mkdir(parents=True, exist_ok=True); manifest.write_bytes(b'accepted-manifest')
            helper = folder / 'android/guest/client_gpu_profile.py'; helper.parent.mkdir(parents=True); helper.write_bytes(b'new-owned-cleanup')
            donor = {'java_sources': {name: pin(b'accepted-java') for name in names}, 'preserved_sources': {},
                'payloads': {'assets/runtime/client_gpu_profile.py': pin(b'old-helper')},
                'source_manifest': pin(b'accepted-manifest'), 'qualification': {'source_files': {}}}
            for name in package.JAVA_CHANGES: (folder / name).write_bytes(b'reviewed-current-session-budget')
            sources = [folder / name for name in names]
            with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package.retained.retained, 'java_sources', return_value=sources):
                _, pins, changed = package.current_java_sources(donor, folder / 'generated')
                self.assertEqual(len(pins), 19); self.assertEqual(set(changed), package.JAVA_CHANGES)
                (folder / names[-1]).write_bytes(b'foreign')
                with self.assertRaises(ValueError): package.current_java_sources(donor, folder / 'generated')
                (folder / names[-1]).write_bytes(b'accepted-java')
                with mock.patch.object(package.retained.retained, 'java_sources', return_value=sources[:-1]), self.assertRaises(ValueError):
                    package.current_java_sources(donor, folder / 'generated')
                helper.write_bytes(b'old-helper')
                with self.assertRaisesRegex(ValueError, 'helper'): package.current_java_sources(donor, folder / 'generated')
            for name in ('android/runtime-lock.json', 'tools/android/gpu-runtime/base-abi.json',
                    'android/native/coh-vulkan-gpu-probe.c', 'upstream/ouroboros/Game/src/graphics/gfx.c'):
                self.assertNotIn(name, package.REVIEWED_DONOR_SOURCE_CHANGES)
                target = folder / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b'accepted-frozen-source')
                frozen = {'qualification': {'source_files': {name: pin(target.read_bytes())}}}
                with mock.patch.object(package, 'ROOT', folder):
                    package.validate_retained_sources(frozen); target.write_bytes(b'foreign')
                    with self.assertRaises(ValueError): package.validate_retained_sources(frozen)

    def test_all99_suites_seven_pg_fixtures_source_closure_and_truthful_claims_required(self):
        receipt = qualification()
        with mock.patch.object(package, 'builder'):
            package.validate_qualification(receipt, COMMIT)
            for mutation in ('skip', 'suite', 'source', 'total', 'pg', 'native', 'mesa', 'physical', 'identity', 'save', 'refresh', 'java', 'unsafe_source'):
                changed = copy.deepcopy(receipt)
                if mutation == 'skip': next(iter(changed['test_suites'].values()))['skipped'] = 1
                elif mutation == 'suite': changed['test_suites'].pop(next(iter(changed['test_suites'])))
                elif mutation == 'source': changed['source_files'].pop(next(iter(package.SOURCE_FILES)))
                elif mutation == 'total': changed['tests_run'] += 1
                elif mutation == 'pg': changed['postgresql_levelup_fixtures'] = []
                elif mutation == 'native': changed['native_client_recompiled'] = True
                elif mutation == 'mesa': changed['mesa_driver_compiled_in_current_run'] = True
                elif mutation == 'physical': changed['physical_hardware_renderer_validated'] = True
                elif mutation == 'identity': changed['installed_runtime_identity_preserved'] = True
                elif mutation == 'save': changed['save_acceptance_relaxed'] = True
                elif mutation == 'refresh': changed['runtime_refresh_required'] = False
                elif mutation == 'java': changed['java_or_dex_recompiled'] = False
                else: changed['source_files']['../escaped-source'] = pin(b'foreign')
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): package.validate_qualification(changed, COMMIT)
        q = package.module('repair_inventory_regression', package.ROOT / package.QUALIFICATION_SCRIPT)
        self.assertEqual((len(q.RETAINED_TEST_MODULES), len(q.TEST_MODULES)), (96, 99)); q.validate_suite_inventory()
        with mock.patch.object(q, 'TEST_MODULES', q.TEST_MODULES[:-1]), self.assertRaisesRegex(ValueError, 'inventory'):
            q.validate_suite_inventory()

    def test_stale_head_and_mismatched_upload_digest_never_publish(self):
        for scenario in ('current', 'stale_before_creation', 'stale_during_upload', 'wrong_upload_digest'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); assets = tuple(folder / name for name in (package.APK_NAME, package.APK_NAME + '.sha256', package.NOTES_NAME))
                for path in assets: path.write_bytes(b'qualified-release-fixture')
                report = {'repository_commit': COMMIT, **pin(assets[0].read_bytes())}
                api = mock.Mock(); state = {'heads': 0, 'created': 0, 'published': 0}
                def request(path, data=None, **kwargs):
                    if path.startswith('/releases/tags/') or path.startswith('/git/ref/tags/'):
                        raise urllib.error.HTTPError('https://api.github.com' + path, 404, 'absent', {}, None)
                    if path.startswith('/git/ref/heads/'):
                        state['heads'] += 1
                        stale = scenario == 'stale_before_creation' or scenario == 'stale_during_upload' and state['heads'] > 1
                        return {'ref': 'refs/heads/' + package.BRANCH, 'object': {'type': 'commit', 'sha': 'b' * 40 if stale else COMMIT}}
                    if path == '/releases': state['created'] += 1; return {'id': 123, 'draft': True, 'tag_name': package.RELEASE_TAG}
                    if '/assets?' in path:
                        digest = 'f' * 64 if scenario == 'wrong_upload_digest' else pin(data.read_bytes())['sha256']
                        return {'state': 'uploaded', 'name': data.name, 'size': data.stat().st_size, 'digest': 'sha256:' + digest}
                    if path == '/releases/123':
                        state['published'] += 1
                        return {'id': 123, 'draft': False, 'prerelease': True, 'tag_name': package.RELEASE_TAG, 'html_url': 'release'}
                    raise AssertionError(path)
                api.request.side_effect = request
                if scenario == 'current': self.assertEqual(package.publish_release(api, report, assets, 'notes'), 'release')
                else:
                    with self.assertRaisesRegex(ValueError, 'differs' if scenario == 'wrong_upload_digest' else 'superseded'):
                        package.publish_release(api, report, assets, 'notes')
                self.assertEqual(state['created'], 0 if scenario == 'stale_before_creation' else 1)
                self.assertEqual(state['published'], 1 if scenario == 'current' else 0)

    def test_existing_release_is_never_replaced(self):
        api = mock.Mock(); api.request.return_value = {'id': 1, 'tag_name': package.RELEASE_TAG}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); assets = tuple(folder / name for name in (package.APK_NAME, package.APK_NAME + '.sha256', package.NOTES_NAME))
            for path in assets: path.write_bytes(b'fixture')
            with self.assertRaisesRegex(ValueError, 'never replaced'):
                package.publish_release(api, {'repository_commit': COMMIT, **pin(b'fixture')}, assets, 'notes')
            self.assertEqual(api.request.call_count, 1)


@contextlib.contextmanager
def gpu_candidate(folder):
    """Frozen donor policy fixture, mocking only actual ELF/Win32 build proof."""
    old = repair.old; root = folder / 'sources'; donor = folder / 'donor'; donor.mkdir()
    for name in set(old.SOURCE_FILES) | set(repair.SOURCE_FILES):
        target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(('frozen-source:' + name).encode())
    source_files = {name: old.file_pin(root / name) for name in old.SOURCE_FILES}
    contents = {name: ('policy-fixture-not-production:' + name).encode() for name in (*repair.RETAINED, old.PE32_PROBE)}
    def binary_checks(directory):
        return {name: {'policy_fixture_not_production': True, 'raw_bytes': pin((Path(directory) / name).read_bytes()),
            'retained_exact_base_ABI': {'library_source': old.base_pin()}} for name in (old.DRIVER, old.VULKAN_PROBE, old.PE32_PROBE)}
    staged = folder / 'staged'; staged.mkdir()
    for name, raw in contents.items(): (staged / name).write_bytes(raw)
    checks = binary_checks(staged)
    build = {'repository_commit': repair.DONOR_COMMIT, 'run_url': repair.DONOR_RUN,
        'source_files': source_files, 'base_archive': old.base_pin(),
        'base_abi': old.file_pin(old.ROOT / 'tools/android/gpu-runtime/base-abi.json'),
        'binary_checks': checks, 'container_build': {'policy_fixture_not_production': True}}
    contents[old.INNER_RECEIPT] = old.encoded(build)
    inner = {'format': 1, 'role': old.ROLE, 'repository_commit': repair.DONOR_COMMIT, 'run_url': repair.DONOR_RUN,
        'mesa_version': old.lock()['mesa']['version'], 'mesa_source_sha256': old.lock()['mesa']['sha256'],
        'platform': old.lock()['platform'], 'driver': old.lock()['driver'], 'gpu': 'Adreno740',
        'files': {name: dict(pin(contents[name]), mode=mode) for name, mode in old.MODES.items()},
        'software_default': True, 'physical_hardware_validated': False}
    contents[old.INNER_MANIFEST] = old.encoded(inner); write_zip(donor / old.ARCHIVE, contents)
    producer = {'format': 1, 'role': old.ROLE, 'repository_commit': repair.DONOR_COMMIT, 'run_url': repair.DONOR_RUN,
        'files': {old.ARCHIVE: old.file_pin(donor / old.ARCHIVE)}, 'hardware_manifest': inner,
        'source_build': build, 'binary_checks': checks, 'physical_hardware_validated': False, 'physical_performance_validated': False}
    (donor / old.MANIFEST).write_bytes(old.encoded(producer)); (donor / old.RECEIPT).write_bytes(old.encoded(build))
    probe = folder / 'probe'; probe.mkdir(); new_probe = b'current-production-WGL-policy-fixture-not-production'
    (probe / old.PE32_PROBE).write_bytes(new_probe)
    helper_files = {name: pin(('Win32-policy-fixture:' + name).encode()) for name in (old.PE32_HELPER_SOURCE, old.PE32_HELPER_EXE)}
    for name in helper_files: (probe / name).write_bytes(('Win32-policy-fixture:' + name).encode())
    current_checks = {'policy_fixture_not_production': True, 'commit': COMMIT, 'github_run_url': RUN,
        'production_probe': pin(new_probe), 'helper_files': helper_files}
    (probe / 'coh-gpu-probe-native-checks.json').write_bytes(old.encoded(current_checks))
    def current_proof(value, commit, run, production, directory):
        old.require(value == current_checks and value['commit'] == commit and value['github_run_url'] == run
            and value['production_probe'] == pin(production), 'Current policy Win32 source/run/probe differs')
        for name, expected in helper_files.items(): repair.checked(Path(directory) / name, expected)
        return helper_files
    with mock.patch.object(repair, 'ROOT', root), mock.patch.object(repair, 'DONOR_ARCHIVE', old.file_pin(donor / old.ARCHIVE)), \
            mock.patch.object(repair, 'DONOR_MANIFEST', old.file_pin(donor / old.MANIFEST)), \
            mock.patch.object(old, 'binary_checks', side_effect=binary_checks), \
            mock.patch.object(repair, 'validate_current_proof', side_effect=current_proof), \
            mock.patch.dict(os.environ, {'GITHUB_RUN_ID': '123456'}):
        args = argparse.Namespace(repository_commit=COMMIT, run_url=RUN, donor_directory=donor,
            probe_directory=probe, output=folder / 'repaired')
        outer = repair.package(args)
        yield {'args': args, 'outer': outer, 'original': contents, 'producer': producer, 'root': root,
            'binary_checks': binary_checks}


def reseal_gpu(v, *, receipt=None, contents=None):
    """Recompute hashes, without granting authorization for changed claims."""
    old = repair.old; path = v['args'].output
    outer = old.read_json(path / repair.MANIFEST)
    receipt = receipt if receipt is not None else old.read_json(path / repair.RECEIPT)
    contents = contents if contents is not None else old.archive_contents(path / old.ARCHIVE)
    contents[old.INNER_RECEIPT] = old.encoded(receipt)
    inner = old.json_value(contents[old.INNER_MANIFEST])
    inner['files'] = {name: dict(pin(contents[name]), mode=mode) for name, mode in old.MODES.items()}
    contents[old.INNER_MANIFEST] = old.encoded(inner); write_zip(path / old.ARCHIVE, contents)
    (path / repair.RECEIPT).write_bytes(old.encoded(receipt))
    outer.update(files={old.ARCHIVE: old.file_pin(path / old.ARCHIVE)}, hardware_manifest=inner, probe_repair=receipt)
    (path / repair.MANIFEST).write_bytes(old.encoded(outer))


class RepairGpuArchiveTests(unittest.TestCase):
    def verify(self, v):
        a = v['args']; return repair.validate_package(a.output, COMMIT, a.donor_directory, a.probe_directory)

    def test_original_driver_Vulkan_notices_source_build_and_ABI_proof_retained(self):
        with tempfile.TemporaryDirectory() as temporary, gpu_candidate(Path(temporary)) as v:
            self.assertEqual(self.verify(v), v['outer'])
            current = repair.old.archive_contents(v['args'].output / repair.ARCHIVE)
            self.assertEqual(set(current), set(v['original']))
            for name in repair.RETAINED: self.assertEqual(current[name], v['original'][name], name)
            self.assertNotEqual(current[repair.old.PE32_PROBE], v['original'][repair.old.PE32_PROBE])
            receipt = v['outer']['probe_repair']
            self.assertEqual(receipt['retained_gpu_producer'], v['producer'])
            self.assertEqual(receipt['retained_gpu_producer']['source_build']['base_abi'], v['producer']['source_build']['base_abi'])
            self.assertIs(receipt['mesa_driver_compiled_in_current_run'], False)
            self.assertIs(receipt['native_vulkan_probe_compiled_in_current_run'], False)
            self.assertIs(receipt['wgl_probe_compiled_in_current_run'], True)

    def test_resealed_retained_member_and_producer_claim_mutations_rejected(self):
        mutations = tuple(sorted(repair.RETAINED)) + ('mesa', 'Vulkan', 'wgl', 'physical', 'nested_ABI')
        for name in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, gpu_candidate(Path(temporary)) as v:
                contents = repair.old.archive_contents(v['args'].output / repair.ARCHIVE)
                receipt = repair.old.read_json(v['args'].output / repair.RECEIPT)
                if name in repair.RETAINED: contents[name] += b'foreign'
                elif name == 'mesa': receipt['mesa_driver_compiled_in_current_run'] = True
                elif name == 'Vulkan': receipt['native_vulkan_probe_compiled_in_current_run'] = True
                elif name == 'wgl': receipt['wgl_probe_compiled_in_current_run'] = False
                elif name == 'physical': receipt['physical_performance_validated'] = True
                else: receipt['retained_gpu_producer']['source_build']['base_abi']['sha256'] = 'f' * 64
                reseal_gpu(v, receipt=receipt, contents=contents)
                with self.assertRaises(ValueError): self.verify(v)

    def test_current_probe_guard_source_run_and_helper_pins_cannot_be_swapped(self):
        for mutation in ('production', 'checks', 'helper', 'run'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, gpu_candidate(Path(temporary)) as v:
                directory = v['args'].probe_directory
                if mutation == 'production': (directory / repair.old.PE32_PROBE).write_bytes(b'swapped-WGL-probe')
                elif mutation == 'helper': (directory / repair.old.PE32_HELPER_EXE).write_bytes(b'swapped-host-checks')
                elif mutation == 'checks':
                    checks = repair.old.read_json(directory / 'coh-gpu-probe-native-checks.json'); checks['commit'] = 'b' * 40
                    (directory / 'coh-gpu-probe-native-checks.json').write_bytes(repair.old.encoded(checks))
                else: os.environ['GITHUB_RUN_ID'] = '999999'
                with self.assertRaises(ValueError): self.verify(v)

    def test_frozen_donor_pins_source_ABI_paths_and_finite_inventory_required(self):
        for mutation in ('archive', 'producer', 'receipt', 'extra', 'source', 'duplicate', 'traversal'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, gpu_candidate(Path(temporary)) as v:
                donor = v['args'].donor_directory
                if mutation == 'archive': (donor / repair.ARCHIVE).write_bytes(b'foreign')
                elif mutation == 'producer': (donor / repair.old.MANIFEST).write_bytes(b'{}')
                elif mutation == 'receipt': (donor / repair.old.RECEIPT).write_bytes(b'{}')
                elif mutation == 'extra': (donor / 'extra-proof.json').write_bytes(b'{}')
                elif mutation == 'source': (v['root'] / 'tools/android/gpu-runtime/base-abi.json').write_bytes(b'foreign-ABI')
                else:
                    with warnings.catch_warnings(), zipfile.ZipFile(v['args'].output / repair.ARCHIVE, 'a') as archive:
                        warnings.simplefilter('ignore', UserWarning)
                        archive.writestr(repair.old.DRIVER if mutation == 'duplicate' else '../escape', b'foreign')
                with self.assertRaises(ValueError): self.verify(v)


class ExistingReleaseMetadataTests(unittest.TestCase):
    def test_only_complete_public_asset_metadata_may_skip_publication(self):
        import copy
        import build_client_gpu_repair_apk as package
        base = 'https://github.com/'+package.REPOSITORY+'/releases/download/'+package.RELEASE_TAG+'/'
        assets = [{'name': name, 'state': 'uploaded', 'size': 97 if name.endswith('.sha256') else 1024,
            'digest': 'sha256:'+'a'*64, 'browser_download_url': base+name}
            for name in (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME)]
        release = {'id': 1, 'tag_name': package.RELEASE_TAG, 'draft': False, 'prerelease': True,
            'published_at': '2026-10-08T21:00:00Z', 'assets': assets}
        self.assertTrue(package.validate_existing_release(release))
        for mutation in ('draft', 'missing', 'duplicate', 'empty', 'uploading', 'digest', 'url', 'published', 'checksum'):
            changed = copy.deepcopy(release)
            if mutation == 'draft': changed['draft'] = True
            elif mutation == 'missing': changed['assets'].pop()
            elif mutation == 'duplicate': changed['assets'][-1] = copy.deepcopy(changed['assets'][0])
            elif mutation == 'empty': changed['assets'][0]['size'] = 0
            elif mutation == 'uploading': changed['assets'][0]['state'] = 'uploading'
            elif mutation == 'digest': changed['assets'][0]['digest'] = None
            elif mutation == 'url': changed['assets'][0]['browser_download_url'] = 'https://example.com/unqualified.apk'
            elif mutation == 'published': changed['published_at'] = None
            else: changed['assets'][1]['size'] = 96
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                package.validate_existing_release(changed)


if __name__ == '__main__': unittest.main()
