"""Synthetic supplemental records exercise rejection; never native evidence.

Fixture byte pins are explicitly substituted for the immutable public pins.
The real ZIP, cache format, raw-trace and receipt verifiers remain in use.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools/android/atlasgame'),
               str(ROOT/'tools/android/interactive'), str(ROOT/'android/guest')]
_spec = importlib.util.spec_from_file_location('published_server_cache_qualification_tests',
    Path(__file__).with_name('qualify_published_server_caches.py'))
qualification = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qualification)
observer, package = qualification.observer, qualification.package
from test_server_cache_package import synthetic_archive, parse6
from test_prepare_server_caches import phase_stdout


def synthetic_public_archive(path, count=93):
    def extend(manifest, payloads):
        manifest['repository_commit'] = '3'*40
        for number in range(count-len(payloads)):
            name = f'data/server/bin/fixture_{number:02}.bin'
            raw = parse6()
            payloads[name] = raw
            manifest['files'][name] = {**package.pin_bytes(raw), 'kind': 'Parse6',
                                      'structure': package.inspect_payload(raw, 'Parse6')}
        manifest['native_consumption']['cache_content_reads'] = {
            name: len(raw) for name, raw in payloads.items()}
    return synthetic_archive(path, mutate=extend)


def synthetic_public_proof(directory):
    """An explicitly nonexecuting fixture with a real disposable lock leaf."""
    directory.mkdir()
    archive = directory/qualification.ARCHIVE
    manifest = synthetic_public_archive(archive)
    apk = directory/'synthetic-public.apk'
    with zipfile.ZipFile(apk, 'w') as outer:
        outer.writestr('assets/runtime/server-caches.zip', archive.read_bytes())
        outer.writestr('assets/runtime/server-cache-manifest.json', package.canonical(manifest))
    evidence = directory/'evidence/consumption'
    evidence.mkdir(parents=True)
    prefix = directory/'synthetic-prefix'; prefix.mkdir(mode=0o700)
    base = directory/'synthetic-server-base'; base.mkdir(mode=0o700)
    info = prefix.stat()
    server = base/f'server-{info.st_dev:x}-{info.st_ino:x}'
    server.mkdir(mode=0o700)
    (server/'lock').write_bytes(b'')
    cleanup = observer.prove_prefix_server_unlocked(prefix, server_base=base)
    observer.write_json(evidence/'wine-helpers-stop.json', {'format': 1,
        'kill_exit_code': 0, 'wait_exit_code': 0,
        'normal_launcher_exit_observed_first': True, **cleanup})
    (evidence/'wine-helpers-stop.log').write_bytes(b'')
    initialized = directory/'evidence/prefix-initialization'; initialized.mkdir()
    observer.write_json(initialized/'phase-receipt.json', {
        'context': 'owned_prefix_initialization_before_native_launch',
        'wineboot_exit_code': 0, 'mapserver_launched': False})
    observer.write_json(initialized/'wine-helpers-stop.json', {'format': 1,
        'kill_exit_code': 0, 'wait_exit_code': 0,
        'normal_launcher_exit_observed_first': False, **cleanup})
    (initialized/'wine-helpers-stop.log').write_bytes(b'')
    stdout = phase_stdout()
    (evidence/'stdout.log').write_bytes(stdout)
    (evidence/'stderr.log').write_bytes(b'')
    phase = observer.phase_receipt(stdout, b'', 'consumption', '1'*32, 0, True)
    phase['elapsed_seconds'] = 0.1
    observer.write_json(evidence/'phase-receipt.json', phase)
    runtime = directory/'synthetic-runtime'
    observer.write_json(evidence/'invocation.json', {'stage': 'consumption',
        'session_id': '1'*32, 'identity': manifest['identity'],
        'runtime_host_path': str(runtime), 'timezone': 'UTC', 'wine_debug': '-all',
        'wine_prefix': str(prefix)})
    trace_path = evidence/'trace.12'
    trace_path.write_text('openat(AT_FDCWD, "'+str(server/'lock')+'", O_RDWR) = 9<'+
        str(server/'lock')+'>\n'+''.join('read(3<'+str(runtime/name)+'>, "fixture", '+
        str(record['bytes'])+') = '+str(record['bytes'])+'\n'
        for name, record in manifest['files'].items()))
    sources = observer.archive_source_paths(archive, manifest['files'])
    trace = observer.trace_receipt([trace_path], runtime, manifest['files'], sources,
                                   manifest['identity']['identifier_files'])
    observer.write_json(evidence/'trace-receipt.json', trace)
    launcher = directory/'evidence/server-cache-launcher.exe'
    launcher.write_bytes(b'SYNTHETIC RECEIPT FIXTURE; NOT AN EXECUTABLE')
    snapshot = {name: {**{key: value[key] for key in ('bytes', 'sha256')},
                         'mtime_ns': package.EPOCH*10**9}
                for name, value in manifest['files'].items()}
    report = {'format': 1, 'role': 'published_server_cache_consumption',
        'status': 'exact_public_server_caches_consumed', 'repository_commit': '4'*40,
        'published_apk': package.file_pin(apk),
        'published_cache_archive': package.file_pin(archive),
        'published_cache_commit': manifest['repository_commit'],
        'donor_apk': observer.DONOR_APK, 'donor_build_report': observer.DONOR_REPORT,
        'identity': manifest['identity'],
        'source_files': {name: package.file_pin(ROOT/name) for name in qualification.QUALIFICATION_SOURCES},
        'evidence_files': observer.evidence_pins(directory), 'launcher': package.file_pin(launcher),
        'native_consumption': {**phase, 'cache_files_unchanged': True,
            **{key: trace[key] for key in ('cache_content_reads', 'cache_writes', 'source_content_reads')},
            'trace_receipt_sha256': hashlib.sha256(package.canonical(trace)).hexdigest()},
        'identifier_snapshots': {'before': manifest['identity']['identifier_files'],
                                 'after': manifest['identity']['identifier_files']},
        'noncache_snapshots': {'before': {'synthetic': True}, 'after': {'synthetic': True}},
        'cache_snapshots': {'before': snapshot, 'after': snapshot}, 'source_paths': sources,
        'observed_prefix_server_directories': [str(server)],
        'no_native_cache_generation': True, 'published_artifacts_changed': False,
        'native_client_or_server_recompiled': False, 'android_execution_validated': False,
        'physical_startup_timing_validated': False, 'dialog_semantics_validated': False}
    observer.write_json(directory/qualification.REPORT, report)
    return manifest, report, apk


def workflow_commands(path):
    """Read command scalars from the deliberately simple pinned workflow."""
    lines = path.read_text().splitlines(); result = []
    for number, line in enumerate(lines):
        if line.lstrip().startswith('run:'):
            indent = len(line)-len(line.lstrip()); scalar = line.strip()[4:].strip()
            if scalar in ('|', '>-'):
                values = []
                for following in lines[number+1:]:
                    if following.strip() and len(following)-len(following.lstrip()) <= indent:
                        break
                    values.append(following.strip())
                scalar = '\n'.join(values)
            result.append(scalar)
    return result


class PublishedServerCacheQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root/'proof'
        self.manifest, self.report, self.apk = synthetic_public_proof(self.directory)
        for name, value in (('PUBLISHED_APK', self.report['published_apk']),
                            ('PUBLISHED_CACHE_ARCHIVE', self.report['published_cache_archive']),
                            ('PUBLISHED_CACHE_COMMIT', self.report['published_cache_commit'])):
            patcher = mock.patch.object(qualification, name, value)
            patcher.start(); self.addCleanup(patcher.stop)

    def save(self, report=None, refresh_evidence=False):
        report = self.report if report is None else report
        if refresh_evidence: report['evidence_files'] = observer.evidence_pins(self.directory)
        observer.write_json(self.directory/qualification.REPORT, report)

    def json_mutation(self, name, mutate):
        path = self.directory/'evidence/consumption'/name
        value = observer.read_json(path); mutate(value); observer.write_json(path, value)
        self.save(refresh_evidence=True)

    def assert_rejected(self):
        with self.assertRaises((ValueError, KeyError)):
            qualification.verify_published_qualification(self.directory)

    def refresh_trace_claims(self):
        """Keep tampered raw evidence internally consistent to test policy."""
        evidence = self.directory/'evidence/consumption'
        invocation = observer.read_json(evidence/'invocation.json')
        trace = observer.trace_receipt(evidence.glob('trace.*'), invocation['runtime_host_path'],
            self.manifest['files'], self.report['source_paths'], self.manifest['identity']['identifier_files'])
        observer.write_json(evidence/'trace-receipt.json', trace)
        self.report['native_consumption'].update({key: trace[key]
            for key in ('cache_content_reads', 'cache_writes', 'source_content_reads')})
        self.report['native_consumption']['trace_receipt_sha256'] = hashlib.sha256(package.canonical(trace)).hexdigest()
        self.report['observed_prefix_server_directories'] = qualification.observed_prefix_server_directories(evidence.glob('trace.*'))
        self.save(refresh_evidence=True)

    def test_complete_consumption_only_raw_proof_recomputes_with_same_archive_bytes(self):
        before = package.file_pin(self.directory/qualification.ARCHIVE)
        self.assertEqual(qualification.verify_published_qualification(self.directory), self.report)
        self.assertEqual(before, package.file_pin(self.directory/qualification.ARCHIVE))
        self.assertFalse((self.directory/'evidence/generation').exists())

    def test_public_extract_copies_verbatim_and_refuses_reuse(self):
        destination = self.root/'copy'; destination.mkdir()
        self.assertEqual(qualification.extract_published_caches(self.apk, destination), self.manifest)
        self.assertEqual((destination/qualification.ARCHIVE).read_bytes(),
                         (self.directory/qualification.ARCHIVE).read_bytes())
        with self.assertRaises(ValueError): qualification.extract_published_caches(self.apk, destination)

    def test_public_apk_pin_failure_precedes_any_cache_copy(self):
        destination = self.root/'copy'; destination.mkdir()
        with self.apk.open('ab') as target: target.write(b'changed')
        with self.assertRaises(ValueError): qualification.extract_published_caches(self.apk, destination)
        self.assertEqual(list(destination.iterdir()), [])

    def test_external_manifest_and_duplicate_public_apk_members_rejected(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                apk = self.root/f'bad-{duplicate}.apk'
                with warnings.catch_warnings(), zipfile.ZipFile(apk, 'w') as outer:
                    warnings.simplefilter('ignore', UserWarning)
                    outer.writestr('assets/runtime/server-caches.zip',
                                   (self.directory/qualification.ARCHIVE).read_bytes())
                    external = {**self.manifest, 'repository_commit': '5'*40}
                    outer.writestr('assets/runtime/server-cache-manifest.json',
                                   package.canonical(self.manifest if duplicate else external))
                    if duplicate: outer.writestr('assets/runtime/server-cache-manifest.json', package.canonical(self.manifest))
                destination = self.root/f'copy-{duplicate}'; destination.mkdir()
                with mock.patch.object(qualification, 'PUBLISHED_APK', package.file_pin(apk)), self.assertRaises(ValueError):
                    qualification.extract_published_caches(apk, destination)

    def test_original_commit_and_complete_93_file_inventory_required(self):
        for value in ('5'*40, '3'*40):
            with self.subTest(commit=value):
                with mock.patch.object(qualification, 'PUBLISHED_CACHE_COMMIT', value):
                    if value != self.manifest['repository_commit']: self.assert_rejected()
        archive = self.root/'incomplete.zip'; manifest = synthetic_public_archive(archive, count=92)
        apk = self.root/'incomplete.apk'
        with zipfile.ZipFile(apk, 'w') as outer:
            outer.writestr('assets/runtime/server-caches.zip', archive.read_bytes())
            outer.writestr('assets/runtime/server-cache-manifest.json', package.canonical(manifest))
        destination = self.root/'incomplete-copy'; destination.mkdir()
        with mock.patch.object(qualification, 'PUBLISHED_APK', package.file_pin(apk)), \
             mock.patch.object(qualification, 'PUBLISHED_CACHE_ARCHIVE', package.file_pin(archive)), self.assertRaises(ValueError):
            qualification.extract_published_caches(apk, destination)

    def test_wrong_old_tmp_cleanup_path_rejected_after_evidence_rehash(self):
        self.json_mutation('wine-helpers-stop.json', lambda value: value.update(
            server_directory='/tmp/.wine-999/server-1-2'))
        self.assert_rejected()

    def test_absent_held_premature_and_noninteger_cleanup_claims_rejected(self):
        path = self.directory/'evidence/consumption/wine-helpers-stop.json'
        original = observer.read_json(path)
        for mutation in ({'status': 'no_prefix_server_directory'}, {'status': 'prefix_server_lock_held'},
                         {'normal_launcher_exit_observed_first': False}, {'wait_exit_code': True},
                         {'kill_exit_code': False}):
            with self.subTest(mutation=mutation):
                observer.write_json(path, {**original, **mutation})
                self.save(refresh_evidence=True); self.assert_rejected()

    def test_prefix_initialization_must_finish_without_mapserver_before_trace(self):
        directory = self.directory/'evidence/prefix-initialization'
        path = directory/'phase-receipt.json'; original = observer.read_json(path)
        for mutation in ({'mapserver_launched': True}, {'wineboot_exit_code': 1},
                         {'context': 'after_native_launch'}):
            with self.subTest(mutation=mutation):
                observer.write_json(path, {**original, **mutation})
                self.save(refresh_evidence=True); self.assert_rejected()

    def test_prefix_initialization_cleanup_matches_same_actual_prefix_lock(self):
        path = self.directory/'evidence/prefix-initialization/wine-helpers-stop.json'
        original = observer.read_json(path)
        for mutation in ({'prefix': '/tmp/other-prefix'}, {'server_directory': '/tmp/wrong/server-1-2'},
                         {'status': 'no_prefix_server_directory'}, {'normal_launcher_exit_observed_first': True},
                         {'wait_exit_code': True}, {'kill_exit_code': False}):
            with self.subTest(mutation=mutation):
                observer.write_json(path, {**original, **mutation})
                self.save(refresh_evidence=True); self.assert_rejected()

    def test_missing_or_second_actual_lock_directory_rejected(self):
        path = self.directory/'evidence/consumption/trace.12'; original = path.read_text()
        for text in ('\n'.join(original.splitlines()[1:])+'\n',
                     original+'read(9</tmp/other/server-1-2/lock>, "a", 1) = 1\n'):
            with self.subTest(text=text):
                path.write_text(text); self.refresh_trace_claims(); self.assert_rejected()

    def test_definition_and_persisted_message_source_reads_rejected(self):
        path = self.directory/'evidence/consumption/trace.12'; original = path.read_text()
        runtime = observer.read_json(path.parent/'invocation.json')['runtime_host_path']
        for name in (self.report['source_paths'][0], 'data/texts/English/Contacts/custom.def'):
            with self.subTest(name=name):
                path.write_text(original+f'read(8<{runtime}/{name}>, "bad", 3) = 3\n')
                self.refresh_trace_claims(); self.assert_rejected()

    def test_metadata_only_cache_access_or_write_is_insufficient(self):
        path = self.directory/'evidence/consumption/trace.12'; original = path.read_text()
        for text in (original.replace('read(3<', 'openat(3<', 1), original.replace('read(3<', 'write(3<', 1)):
            with self.subTest(text=text):
                path.write_text(text); self.refresh_trace_claims(); self.assert_rejected()

    def test_persistent_identifier_and_noncache_state_changes_rejected(self):
        original = json.loads(package.canonical(self.report))
        for field in ('identifier_snapshots', 'noncache_snapshots'):
            with self.subTest(field=field):
                report = json.loads(package.canonical(original))
                report[field]['after'] = {'changed': True}
                self.save(report); self.assert_rejected()

    def test_cache_hash_or_seed_epoch_change_rejected(self):
        original = json.loads(package.canonical(self.report)); name = next(iter(self.manifest['files']))
        for field, value in (('sha256', '0'*64), ('mtime_ns', (package.EPOCH+1)*10**9)):
            with self.subTest(field=field):
                report = json.loads(package.canonical(original))
                for moment in ('before', 'after'): report['cache_snapshots'][moment][name][field] = value
                self.save(report); self.assert_rejected()

    def test_native_error_is_not_hidden_by_rehashed_evidence(self):
        (self.directory/'evidence/consumption/stderr.log').write_bytes(b'Could not find appropriate game data dir\n')
        self.save(refresh_evidence=True); self.assert_rejected()

    def test_source_pins_scope_and_invocation_identity_cannot_be_substituted(self):
        original = json.loads(package.canonical(self.report))
        for mutate in (lambda r: r['source_files'].pop(next(iter(r['source_files']))),
                       lambda r: r.update(source_paths=[])):
            report = json.loads(package.canonical(original)); mutate(report)
            self.save(report); self.assert_rejected()
        self.save(original)
        self.json_mutation('invocation.json', lambda value: value['identity'].update(mapserver_sha256='0'*64))
        self.assert_rejected()

    def test_regeneration_publication_android_or_timing_claims_rejected(self):
        original = json.loads(package.canonical(self.report))
        for field, value in (('no_native_cache_generation', False), ('published_artifacts_changed', True),
                             ('native_client_or_server_recompiled', True), ('android_execution_validated', True),
                             ('physical_startup_timing_validated', True), ('dialog_semantics_validated', True)):
            with self.subTest(field=field):
                report = json.loads(package.canonical(original)); report[field] = value
                self.save(report); self.assert_rejected()

    def test_original_publication_workflow_requires_explicit_manual_dispatch(self):
        text = (ROOT/'.github/workflows/android-startup-caches.yml').read_text()
        trigger = text.split('on:\n', 1)[1].split('\npermissions:', 1)[0]
        self.assertIn('workflow_dispatch:', trigger)
        self.assertNotIn('push:', trigger)
        self.assertNotIn('pull_request:', trigger)

    def test_supplemental_workflow_only_reads_and_consumes_existing_artifacts(self):
        commands = workflow_commands(ROOT/'.github/workflows/android-startup-cache-evidence.yml')
        self.assertTrue(any('qualify_startup_caches.py' in command for command in commands))
        self.assertTrue(any('qualify_published_server_caches.py' in command for command in commands))
        for command in commands:
            tokens = shlex.split(command)
            self.assertNotIn('prepare_server_caches.py', command)
            self.assertNotIn('apksigner', command)
            self.assertNotIn('--publish', tokens)
            self.assertNotIn('gh release', command)
            if 'build_startup_caches_apk.py' in command:
                self.assertIn('download-donor', command)
                self.assertNotIn(' build ', command)


if __name__ == '__main__':
    unittest.main()
