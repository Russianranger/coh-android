"""Exercise the real bundle ZIP conservation and reject forged replacement pins.

Native package production is qualified by the separate client/DbServer suites.
The fixture substitutes only those producer validators; the derivative archive,
SHA256, nested client manifest, extraction and shell checks all run unchanged.
"""
import argparse
import contextlib
import copy
import functools
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import zipfile

import build_startup_bundle_apk as package


COMMIT = 'a' * 40


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


@functools.lru_cache(maxsize=1)
def client_build_input():
    return package.client_builder().expected_receipt()


def client_fixture():
    contents = {'CityOfHeroes.exe': b'exact-frozen-Game',
                **{'fixture-%s.dll' % index: ('exact-DLL-%s' % index).encode()
                   for index in range(20)}}
    records = {name: {'size': len(raw), 'sha256': pin(raw)['sha256'],
                     'pe_machine': 0x14c, 'imports': [], 'delay_imports': []}
               for name, raw in contents.items()}
    contract = package.shared.native_contract
    shared = {'source_commit': contract.SOURCE, 'runtime_validation': 'unverified'}
    frozen = {'format': 1, 'role': contract.ROLE, 'repository_commit': 'b' * 40,
        'source_commit': contract.SOURCE, 'data_commit': contract.DATA,
        'configuration': 'OptDebug', 'architecture': 'Win32',
        'runtime_execution_validated': False, 'postgresql_persistence_fixture': False,
        'files': {name: copy.deepcopy(records['CityOfHeroes.exe']) for name in contract.EXECUTABLES},
        'build_inputs': {'character_events': dict(shared, build_role='character_events',
                progress_build_input={'build_role': 'mapserver_progress'}),
            'client_texture': copy.deepcopy(client_build_input()['base_texture_build_input']),
            'graphics_profile': dict(shared)},
        'retained_cache': {'schema_changed': False, 'executable_sha256': 'c' * 64,
            'archive': {'bytes': 10, 'sha256': 'd' * 64},
            'schema_sources_sha256': {'fixture': 'e' * 64}},
        'retained_native_files': {'client': {name: copy.deepcopy(record)
                for name, record in records.items() if name != 'CityOfHeroes.exe'},
            'game': {'DbServer.exe': copy.deepcopy(records['CityOfHeroes.exe'])}}}
    manifest = {'files': records, 'source_commit': contract.SOURCE, 'data_commit': contract.DATA,
        'repository_commit': frozen['repository_commit'], 'android_execution_validated': False,
        'gameplay_validated': False, 'native_responsiveness': {'receipt': frozen,
            'receipt_sha256': contract.canonical_sha(frozen)}}
    contract.client_contract(manifest, frozen)
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, 'w') as archive:
        for name, value in contents.items(): archive.writestr(name, value)
        archive.writestr('client-package.json', package.shared.encoded(manifest))
    new_game = b'new-verified-root-Game'
    new_record = dict(records['CityOfHeroes.exe'], size=len(new_game), sha256=pin(new_game)['sha256'])
    native = {'format': 1, 'role': 'verified_root_client_startup_supplement',
        'repository_commit': COMMIT, 'source_commit': contract.SOURCE, 'data_commit': contract.DATA,
        'configuration': 'OptDebug', 'architecture': 'Win32', 'build_targets': ['Game'],
        'postgresql_persistence_fixture': False, 'runtime_execution_validated': False,
        'replacement_scope': 'CityOfHeroes.exe_only', 'retained_native_dependencies_changed': False,
        'retained_source_inputs': copy.deepcopy(frozen['build_inputs']),
        'schema_sources_sha256': copy.deepcopy(frozen['retained_cache']['schema_sources_sha256']),
        'build_input': copy.deepcopy(client_build_input()), 'files': {'CityOfHeroes.exe': new_record}}
    return raw.getvalue(), manifest, frozen, native, new_game


def fixture(folder):
    guest = folder / 'android/guest'; guest.mkdir(parents=True)
    assets = {name: ('old-' + name).encode() for name in package.HELPERS}
    for name in package.HELPERS: (guest / name).write_bytes(('new-' + name).encode())
    client_raw, client_manifest, frozen, client_native, new_game = client_fixture()
    normal = {'files': {'DbServer.exe': {'bytes': 7, 'sha256': pin(b'base-Db')['sha256']},
                        'fixture.dll': {'bytes': 8, 'sha256': pin(b'exact-Db')['sha256']}},
              'cmake_cache_sha256': 'f' * 64}
    original_db = {'variants': {'normal': normal}, 'wine_build_input': {'frozen': True}}
    original_db_raw = package.shared.encoded(original_db)
    db_build = {'base_wine_build_input': original_db['wine_build_input']}
    db_native = {'format': 1, 'repository_commit': COMMIT, 'build_input': db_build,
        'base_startup_executable': pin(b'old-manual-Atlas-DbServer'),
        'base_package_manifest_sha256': pin(original_db_raw)['sha256'],
        'base_normal_executable': normal['files']['DbServer.exe'],
        'retained_normal_files': {'fixture.dll': normal['files']['fixture.dll']},
        'base_normal_cmake_cache_sha256': normal['cmake_cache_sha256']}
    assets.update({'client-runtime.zip': client_raw, 'client-caches.zip': b'exact-client-cache',
        'server-caches.zip': b'exact-server-cache', 'server-animations.pigg': b'exact-animations',
        'server-animation-manifest.json': package.shared.encoded({'history': 'retained'}),
        'native-responsiveness.json': package.shared.encoded(frozen),
        'startup-dbserver.exe': b'old-manual-Atlas-DbServer',
        'startup-dbserver-manifest.json': package.shared.encoded({'history': 'retained'}),
        'atlas-world-supplement.zip': b'exact-world', 'character-avatar-defaults.zip': b'exact-avatar',
        'task_gate_evidence.py': b'exact-task-helper', 'task-gate.json': b'{"required":true}',
        'character_reopen_diagnostic.py': b'exact-startup-only-reopen'})
    for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'):
        path = folder / name
        members = {'retained.bin': b'exact-native-baseline'}
        if name == 'dbserver-package.tar.gz': members['package-manifest.json'] = original_db_raw
        package.shared.write_game_archive(path, members)
        assets[name] = path.read_bytes()
    native_members = package.builder().NATIVE_MEMBERS
    while len(assets) + 2 + len(native_members) < 67:
        assets['retained-%s.bin' % len(assets)] = b'exact-retained-runtime'
    assets['client-manifest.json'] = package.shared.encoded({'files': {
        name: pin(raw) for name, raw in assets.items()}})
    runtime = {'repository_commit': package.DONOR_RUNTIME_COMMIT, 'startup_only_reopen': True,
        'task_gate_required': True, 'files': {name: pin(raw) for name, raw in assets.items()}}
    assets['runtime-manifest.json'] = package.shared.encoded(runtime)
    payloads = {'assets/runtime/' + name: raw for name, raw in assets.items()}
    payloads.update({name: b'exact-Android-native' for name in native_members})
    donor = {'payloads': {name: pin(raw) for name, raw in payloads.items()}, 'runtime_manifest': runtime,
        'native_responsiveness': frozen, 'server_animation_manifest': {'history': 'retained'},
        'native_dbserver': {'build_input': db_build}, 'recompiled_dex': pin(b'exact-memory-DEX'),
        'retained_android_resources': {'resources.arsc': pin(b'resources'),
            'res/drawable/ic_coh_client.xml': pin(b'icon')}, '_client_manifest': client_manifest}
    with zipfile.ZipFile(io.BytesIO(client_raw)) as archive:
        donor['_client_members'] = package.client_member_pins(archive)
    apk = folder / 'donor.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        for name, raw in payloads.items(): archive.writestr(name, raw)
        for name, raw in {'AndroidManifest.xml': b'old-manifest', 'classes.dex': b'exact-memory-DEX',
                'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items():
            archive.writestr(name, raw)
    donor['server_payload_extraction_preflight'] = package.verify_apk_server_archives(apk)
    db_directory, client_directory = folder / 'native-db', folder / 'native-client'
    db_directory.mkdir(); client_directory.mkdir()
    (db_directory / 'DbServer.exe').write_bytes(b'new-source-bound-DbServer')
    (db_directory / 'startup-dbserver-manifest.json').write_bytes(package.shared.encoded(db_native))
    (client_directory / 'CityOfHeroes.exe').write_bytes(new_game)
    return apk, donor, db_directory, client_directory, db_native, client_native


@contextlib.contextmanager
def candidate(folder):
    apk, donor, db_directory, client_directory, db_native, client_native = fixture(folder)
    with mock.patch.object(package, 'ROOT', folder), \
            mock.patch.object(package, 'current_sources', return_value={}), \
            mock.patch.object(package, 'validate_native', return_value=(db_native, client_native)):
        runtime, payloads, _, _, preflight = package.extract_and_repair(apk, donor,
            folder / 'unpacked', COMMIT, db_directory, client_directory)
        output = folder / 'candidate.apk'
        with zipfile.ZipFile(output, 'w') as archive:
            for name in payloads: archive.write(folder / 'unpacked' / name, name)
            for name, raw in {'AndroidManifest.xml': b'new-manifest', 'classes.dex': b'exact-memory-DEX',
                    'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items():
                archive.writestr(name, raw)
        yield output, apk, donor, db_directory, client_directory, payloads, runtime, preflight


def replace_member(path, name, raw):
    with zipfile.ZipFile(path) as archive:
        entries = [(entry.filename, archive.read(entry)) for entry in archive.infolist()]
    with zipfile.ZipFile(path, 'w') as archive:
        for member, old in entries: archive.writestr(member, raw if member == name else old)


def qualification():
    contract = package.module('startup_bundle_package_test_contract', package.ROOT / package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE,
        'repository_commit': COMMIT, 'retained_runtime_repository_commit': package.DONOR_RUNTIME_COMMIT,
        'retained_setup_memory_repository_commit': package.DONOR_COMMIT,
        'retained_native_repository_commit': package.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': package.DONOR_APK['sha256'],
        **{name: False for name in ('physical_gameplay_validated', 'physical_startup_timing_validated',
            'physical_storage_cleanup_validated', 'physical_fresh_profile_recovery_validated',
            'native_runtime_booted', 'long_prior_gameplay_milestones_repeated', 'asset_reimport_required',
            'java_or_dex_recompiled', 'native_mapserver_recompiled')},
        **{name: True for name in ('native_dbserver_recompiled', 'native_client_recompiled',
            'runtime_refresh_required', 'previous_runtime_generation_retained', 'setup_memory_guards_preserved')},
        'postgresql_emission_fixture_verified': True,
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits',
            'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback'],
        'tests_run': len(contract.TEST_MODULES), 'checks': {name: True for name in package.CHECKS},
        'source_files': {}, 'check_suites': copy.deepcopy(contract.CHECK_SUITES),
        'test_suites': {name: {'tests_run': 1, 'status': 'passed', 'skipped': 0}
            for name in contract.TEST_MODULES}}


class StartupBundlePackagingTests(unittest.TestCase):
    def verify(self, values):
        output, _, donor, db_directory, client_directory, payloads, _, _ = values
        return package.verify_derivative(output, donor, payloads, COMMIT, db_directory, client_directory)

    def test_real_derivative_retains_all_baselines_and_exact_memory_shell(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, apk, donor, _, _, payloads, runtime, preflight = values
            self.verify(values)
            self.assertEqual(len(payloads), 67)
            self.assertEqual(set(payloads), set(donor['payloads']))
            self.assertEqual({name for name in payloads if payloads[name] != donor['payloads'][name]},
                package.REPLACED_PAYLOADS)
            self.assertEqual(preflight, donor['server_payload_extraction_preflight'])
            self.assertEqual(runtime['repository_commit'], COMMIT)
            self.assertTrue(runtime['startup_only_reopen']); self.assertTrue(runtime['task_gate_required'])
            self.assertFalse(runtime['startup_bundle']['native_mapserver_recompiled'])
            with zipfile.ZipFile(output) as updated, zipfile.ZipFile(apk) as old:
                for name in donor['payloads']:
                    if name not in package.REPLACED_PAYLOADS:
                        self.assertEqual(updated.read(name), old.read(name), name)
                self.assertEqual(updated.read('classes.dex'), old.read('classes.dex'))

    def test_nested_client_replaces_only_game_and_separate_source_receipt(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, apk, _, _, _, _, _, _ = values
            with zipfile.ZipFile(output) as updated, zipfile.ZipFile(apk) as old:
                with zipfile.ZipFile(io.BytesIO(updated.read('assets/runtime/client-runtime.zip'))) as new_client, \
                        zipfile.ZipFile(io.BytesIO(old.read('assets/runtime/client-runtime.zip'))) as old_client:
                    self.assertEqual(set(new_client.namelist()), set(old_client.namelist()))
                    self.assertEqual(len(new_client.namelist()), 22)
                    for name in old_client.namelist():
                        if name not in ('CityOfHeroes.exe', 'client-package.json'):
                            self.assertEqual(new_client.read(name), old_client.read(name), name)
                    manifest = json.loads(new_client.read('client-package.json'))
                    old_manifest = json.loads(old_client.read('client-package.json'))
                    self.assertEqual(manifest['native_responsiveness'], old_manifest['native_responsiveness'])
                    self.assertEqual(manifest['startup_bundle_client']['base_client_executable'],
                        old_manifest['files']['CityOfHeroes.exe'])

    def test_unauthorized_payload_replacement_cannot_be_hidden_by_new_pin(self):
        names = ('game-package.tar.gz', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz',
            'server-caches.zip', 'client-caches.zip', 'server-animations.pigg',
            'atlas-world-supplement.zip', 'character-avatar-defaults.zip',
            'native-responsiveness.json', 'server-animation-manifest.json',
            'task_gate_evidence.py', 'character_reopen_diagnostic.py')
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                member = 'assets/runtime/' + name
                replace_member(output, member, b'foreign'); payloads[member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_native_android_library_and_memory_dex_must_remain_exact(self):
        for member in (next(iter(package.builder().NATIVE_MEMBERS)), 'classes.dex', 'resources.arsc'):
            with self.subTest(member=member), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                replace_member(output, member, b'foreign')
                if member in payloads: payloads[member] = pin(b'foreign')
                with self.assertRaises(ValueError): self.verify(values)

    def test_allowed_helper_still_requires_exact_authored_source(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, _, _, _, payloads, _, _ = values
            name = 'character_server_data_cache.py'; member = 'assets/runtime/' + name
            replace_member(output, member, b'foreign helper'); payloads[member] = pin(b'foreign helper')
            with self.assertRaisesRegex(ValueError, 'Authored startup helper'): self.verify(values)

    def test_source_bound_dbserver_artifacts_cannot_change_after_packaging(self):
        for name in ('DbServer.exe', 'startup-dbserver-manifest.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                (values[3] / name).write_bytes(b'foreign native producer')
                with self.assertRaisesRegex(ValueError, 'DbServer supplement'): self.verify(values)

    def test_nested_dll_or_game_tampering_rejected_even_with_outer_updated_pin(self):
        for name in ('fixture-0.dll', 'CityOfHeroes.exe'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                nested = Path(temporary) / 'client.zip'
                with zipfile.ZipFile(output) as archive: nested.write_bytes(archive.read('assets/runtime/client-runtime.zip'))
                replace_member(nested, name, b'foreign binary')
                replace_member(output, 'assets/runtime/client-runtime.zip', nested.read_bytes())
                payloads['assets/runtime/client-runtime.zip'] = pin(nested.read_bytes())
                with self.assertRaises(ValueError): self.verify(values)

    def test_nested_client_manifest_cannot_relabel_frozen_history_or_add_fields(self):
        for kind in ('history', 'extra'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                nested = Path(temporary) / 'client.zip'
                with zipfile.ZipFile(output) as archive: nested.write_bytes(archive.read('assets/runtime/client-runtime.zip'))
                with zipfile.ZipFile(nested) as archive: manifest = json.loads(archive.read('client-package.json'))
                if kind == 'history': manifest['native_responsiveness']['receipt']['runtime_execution_validated'] = True
                else: manifest['unreviewed'] = True
                replace_member(nested, 'client-package.json', package.shared.encoded(manifest))
                replace_member(output, 'assets/runtime/client-runtime.zip', nested.read_bytes())
                payloads['assets/runtime/client-runtime.zip'] = pin(nested.read_bytes())
                with self.assertRaisesRegex(ValueError, 'Client package drifted'): self.verify(values)

    def test_top_manifests_cannot_add_flags_even_with_forged_payload_pins(self):
        for name in ('client-manifest.json', 'runtime-manifest.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                member = 'assets/runtime/' + name
                with zipfile.ZipFile(output) as archive: value = json.loads(archive.read(member))
                value['unreviewed'] = True; raw = package.shared.encoded(value)
                replace_member(output, member, raw); payloads[member] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'manifest drifted'): self.verify(values)

    def test_foreign_duplicate_and_linked_outer_members_rejected(self):
        for kind in ('foreign', 'duplicate', 'linked'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                with zipfile.ZipFile(values[0], 'a') as archive:
                    if kind == 'duplicate':
                        with self.assertWarns(UserWarning): archive.writestr('classes.dex', b'exact-memory-DEX')
                    elif kind == 'linked':
                        entry = zipfile.ZipInfo('foreign-link'); entry.create_system = 3
                        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                        archive.writestr(entry, b'target')
                    else: archive.writestr('assets/runtime/foreign.bin', b'foreign')
                with self.assertRaises(ValueError): self.verify(values)

    def test_nested_client_member_parser_rejects_unsafe_duplicate_and_linked_paths(self):
        for kind in ('parent', 'directory', 'duplicate', 'linked', 'empty'):
            with self.subTest(kind=kind):
                raw = io.BytesIO()
                with zipfile.ZipFile(raw, 'w') as archive:
                    archive.writestr('safe.dll', b'content')
                    if kind == 'duplicate':
                        with self.assertWarns(UserWarning): archive.writestr('safe.dll', b'content')
                    elif kind == 'linked':
                        entry = zipfile.ZipInfo('link.dll'); entry.create_system = 3
                        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                        archive.writestr(entry, b'safe.dll')
                    else: archive.writestr({'parent': '../foreign.dll', 'directory': 'dir/foreign.dll',
                        'empty': 'empty.dll'}[kind], b'' if kind == 'empty' else b'content')
                with zipfile.ZipFile(raw) as archive, self.assertRaises(ValueError): package.client_member_pins(archive)

    def test_native_packages_mandatory_and_bound_to_actual_baseline_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            apk, donor, db_dir, client_dir, native, client = fixture(Path(temporary))
            with self.assertRaisesRegex(ValueError, 'Both source-bound'): package.validate_native(None, client_dir, COMMIT, apk, donor)
            db_validator = mock.Mock(); db_validator.validate_package.return_value = native
            client_validator = mock.Mock(); client_validator.validate_package.return_value = client
            with mock.patch.object(package, 'native_builder', return_value=db_validator), \
                    mock.patch.object(package, 'client_builder', return_value=client_validator):
                package.validate_native(db_dir, client_dir, COMMIT, apk, donor)
                for field in ('base_package_manifest_sha256', 'base_normal_cmake_cache_sha256',
                        'base_startup_executable', 'retained_normal_files', 'build_input'):
                    changed = copy.deepcopy(native); changed[field] = {} if field in ('retained_normal_files', 'build_input') else '0' * 64
                    db_validator.validate_package.return_value = changed
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        package.validate_native(db_dir, client_dir, COMMIT, apk, donor)
                db_validator.validate_package.return_value = native
                client_validator.validate_package.return_value = dict(client, retained_source_inputs={})
                with self.assertRaises(ValueError): package.validate_native(db_dir, client_dir, COMMIT, apk, donor)

    def test_all_nineteen_java_sources_and_other_guest_helpers_are_pinned(self):
        base = package.builder()
        sources = package.retained.java_sources(base, package.ROOT / 'out/nonexistent-generated-java')
        pins = {path.relative_to(package.ROOT).as_posix(): base.file_pin(path) for path in sources}
        donor = {'java_sources': pins, 'preserved_sources': {},
            'source_manifest': base.file_pin(package.ROOT / 'android/interactive/src/main/AndroidManifest.xml'),
            'payloads': {'assets/runtime/' + name: pin(('old-' + name).encode()) for name in package.HELPERS}}
        self.assertEqual(package.current_sources(donor), pins)
        self.assertEqual(len(pins), 19)
        name = next(iter(pins)); donor['java_sources'] = dict(pins, **{name: pin(b'foreign Java')})
        with self.assertRaisesRegex(ValueError, '19 setup-memory Java'): package.current_sources(donor)
        donor['java_sources'] = pins
        donor['payloads']['assets/runtime/task_gate_evidence.py'] = pin(b'foreign task observer')
        with self.assertRaises(ValueError): package.current_sources(donor)

    def test_qualification_requires_exact_suites_no_skips_and_accounted_totals(self):
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            package.validate_qualification(qualification(), COMMIT)
            for change in ({'test_suites': {}}, {'check_suites': {}}, {'tests_run': 0}, {'tests_run': 999},
                    {'repository_commit': 'b' * 40}, {'checks': {name: False for name in package.CHECKS}}):
                receipt = qualification(); receipt.update(change)
                with self.subTest(change=change), self.assertRaises(ValueError): package.validate_qualification(receipt, COMMIT)
            for change in ({'skipped': 1}, {'status': 'failed'}, {'tests_run': 0}):
                receipt = qualification(); receipt['test_suites']['test_startup_bundle_client'].update(change)
                with self.subTest(change=change), self.assertRaises(ValueError): package.validate_qualification(receipt, COMMIT)

    def test_qualification_cannot_claim_physical_success_or_rebuild_retained_shell_map(self):
        changes = {name: True for name in ('physical_gameplay_validated', 'physical_startup_timing_validated',
            'physical_storage_cleanup_validated', 'physical_fresh_profile_recovery_validated',
            'native_runtime_booted', 'long_prior_gameplay_milestones_repeated', 'asset_reimport_required',
            'java_or_dex_recompiled', 'native_mapserver_recompiled')}
        changes.update({name: False for name in ('native_dbserver_recompiled', 'native_client_recompiled',
            'runtime_refresh_required', 'previous_runtime_generation_retained', 'setup_memory_guards_preserved',
            'postgresql_emission_fixture_verified')})
        changes['postgresql_emission_fixtures'] = []
        for name, value in changes.items():
            receipt = qualification(); receipt[name] = value
            with self.subTest(name=name), mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
                package.validate_qualification(receipt, COMMIT)

    def test_qualification_rejects_unsafe_stale_and_incomplete_source_pins(self):
        for name in ('../foreign.py', '/foreign.py', 'dir\\foreign.py'):
            receipt = qualification(); receipt['source_files'] = {name: pin(b'foreign')}
            with self.subTest(name=name), mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaisesRegex(ValueError, 'Unsafe'):
                package.validate_qualification(receipt, COMMIT)
        receipt = qualification(); receipt['source_files'] = {'tools/android/interactive/test_startup_bundle_package.py': pin(b'stale')}
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError): package.validate_qualification(receipt, COMMIT)
        with self.assertRaisesRegex(ValueError, 'source closure'): package.validate_qualification(qualification(), COMMIT)

    def test_bad_qualification_fails_before_signing_access(self):
        args = argparse.Namespace(repository_commit=COMMIT, donor_apk=Path('donor.apk'),
            donor_build_report=Path('donor.json'), qualification=Path('qualification.json'))
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), \
                mock.patch.object(package, 'validate_donor', return_value={}), \
                mock.patch.object(package, 'read_json', return_value={}), \
                mock.patch.object(package, 'validate_qualification', side_effect=ValueError('qualification failed')), \
                mock.patch.object(base, 'signing_password_spec') as signer:
            with self.assertRaisesRegex(ValueError, 'qualification failed'): package.build(args)
            signer.assert_not_called()

    def test_changed_native_packages_fail_before_signing_even_with_passed_host_receipt(self):
        args = argparse.Namespace(repository_commit=COMMIT, donor_apk=Path('donor.apk'),
            donor_build_report=Path('donor.json'), qualification=Path('qualification.json'),
            native_directory=Path('native-db'), client_directory=Path('native-client'))
        base = package.builder()
        receipt = {'native_dbserver': {'qualified': True}, 'native_client_startup': {'qualified': True}}
        with mock.patch.object(package, 'builder', return_value=base), \
                mock.patch.object(package, 'validate_donor', return_value={}), \
                mock.patch.object(package, 'read_json', return_value=receipt), \
                mock.patch.object(package, 'validate_qualification', return_value=receipt), \
                mock.patch.object(package, 'validate_native', return_value=({'foreign': True}, {'qualified': True})), \
                mock.patch.object(base, 'signing_password_spec') as signer:
            with self.assertRaisesRegex(ValueError, 'changed after host qualification'): package.build(args)
            signer.assert_not_called()

    def test_source_manifest_changes_only_version_values_without_mutation(self):
        source = package.ROOT / 'android/interactive/src/main/AndroidManifest.xml'; before = source.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'manifest.xml'; package.repair_android_manifest(source, destination)
            package.builder(repaired=True).verify_source_manifest(destination)
            self.assertIn(b'android:versionName="0.13.6"', destination.read_bytes())
            self.assertIn(b'android:versionCode="21"', destination.read_bytes())
        self.assertEqual(source.read_bytes(), before)

    def test_binary_manifest_guard_rejects_extra_component(self):
        original = 'E: manifest (line=1)\n A: android:versionCode(0x1)=20\n A: android:versionName(0x2)="0.13.5"\n E: application'
        updated = original.replace('line=1', 'line=2').replace('=20', '=21').replace('0.13.5', '0.13.6')
        base = mock.Mock(); base.run.side_effect = (original, updated)
        with mock.patch.object(package.retained, 'builder', return_value=base):
            package.verify_binary_manifest(Path('candidate.apk'), Path('donor.apk'), Path('sdk'))
        base.run.side_effect = (original, updated + '\n E: foreign-service')
        with mock.patch.object(package.retained, 'builder', return_value=base), self.assertRaisesRegex(ValueError, 'beyond version'):
            package.verify_binary_manifest(Path('candidate.apk'), Path('donor.apk'), Path('sdk'))

    def test_signer_and_v2_v3_are_required_and_existing_release_never_replaced(self):
        text = ('Verified using v2 scheme (APK Signature Scheme v2): true\n'
            'Verified using v3 scheme (APK Signature Scheme v3): true\n'
            'Signer #1 certificate SHA-256 digest: ' + package.SIGNER)
        base = package.retained.builder()
        with mock.patch.object(package.retained, 'builder', return_value=base), mock.patch.object(base, 'run', return_value=text):
            self.assertEqual(package.verify_signature(Path('candidate.apk'), Path('sdk')), package.SIGNER)
        for invalid in (text.replace(package.SIGNER, '0' * 64), text.replace('v2): true', 'v2): false'), text.replace('v3): true', 'v3): false')):
            with self.subTest(invalid=invalid), mock.patch.object(package.retained, 'builder', return_value=base), \
                    mock.patch.object(base, 'run', return_value=invalid), self.assertRaises(ValueError):
                package.verify_signature(Path('candidate.apk'), Path('sdk'))
        api = mock.Mock(); api.request.return_value = {'id': 42}
        paths = tuple(Path(name) for name in (package.APK_NAME, package.APK_NAME + '.sha256', package.NOTES_NAME))
        with mock.patch.object(package, 'builder', return_value=mock.Mock()), self.assertRaisesRegex(ValueError, 'never replaced'):
            package.publish_release(api, {'repository_commit': COMMIT}, paths, 'notes')
        self.assertEqual(api.request.call_count, 1)


if __name__ == '__main__': unittest.main()
