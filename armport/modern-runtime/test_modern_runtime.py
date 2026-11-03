"""Admission/projection controls. Fixtures are metadata, never runtime evidence."""
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import modern_runtime_donor as donor
import modern_runtime_host as host
import modern_validation as v

ROOT = Path(os.environ.get('COH_CANDIDATE_ROOT', str(Path.cwd() / 'candidate')))
interactive, stage, pipeline, progress = host.load_candidate(ROOT.resolve())
COMMIT, RUN, SESSION = 'a' * 40, 123, '1' * 32


def fixture(reopening=False):
    files = {name: {'bytes': 100, 'sha256': str(i) * 64} for i, name in enumerate((
        'client-visual-manifest.json', 'client-visual-assets.zip', 'server-animation-manifest.json',
        'zones-world-supplement-manifest.json', 'zones-audio-supplement-manifest.json'), 1)}
    for name in interactive.character.host.assets_tool.PROBE_FILES:
        files.setdefault(name, {'bytes': 100, 'sha256': '0' * 64})
    pe, predecessor = {'bytes': 2, 'sha256': 'a' * 64}, {'bytes': 1, 'sha256': 'b' * 64}
    build = {'predecessor': {'mapserver': predecessor}, 'fixture_only': True}
    expected = {'format': 1, 'variant': v.VARIANT, 'repository_commit': COMMIT, 'run_id': RUN,
        'server_package': {'bytes': 10, 'sha256': 'c' * 64}, 'mapserver': pe,
        'build_manifest': {'bytes': 20, 'sha256': 'd' * 64}, 'source_receipt_sha256': 'e' * 64,
        'runtime_execution_validated': False, 'physical_device_validated': False}
    proof = {**expected, 'policy': 'authenticated_metrics_only_overlay', 'actual_mapserver_sha256': pe['sha256'],
        'previous_mapserver_sha256': predecessor['sha256'],
        'package_receipt_sha256': __import__('hashlib').sha256(v.canonical(build)).hexdigest(),
        'parser_or_definition_sources_changed': False, 'gameplay_decisions_changed': False}
    native = {'source_commit': 's' * 40, 'data_commit': 't' * 40,
              'files': {'CityOfHeroes.exe': {'sha256': 'f' * 64}}}
    arm = dict(archive_sha256='9' * 64, executable_sha256='8' * 64, client_run_id=RUN, data_run_id=RUN)
    runtime = {'armport_server_metrics': expected, 'armport_server_metrics_build': build,
               'files': files, 'armport_server_native_closure': native, 'armport_client': arm}
    documents = {'client-visual-manifest.json': dict(scope='visual', file_count=2, payload_bytes=20, files_sha256='7' * 64),
        'server-animation-manifest.json': dict(pigg={'bytes': 50, 'sha256': '6' * 64}, files={'first': {}, 'second': {}},
            identity={'animation_inventory_sha256': '5' * 64}),
        'zones-world-supplement-manifest.json': dict(version='1.0.0', file_count=3, payload_bytes=30, files_sha256='4' * 64),
        'zones-audio-supplement-manifest.json': dict(version='1.0.0', file_count=4, payload_bytes=40, files_sha256='3' * 64)}
    work = {'source_data': '/game-import/data', 'worktree_key': 'client-work-' + '2' * 24, 'import': {'receipt_sha256': '1' * 64}}
    visual = {**documents['client-visual-manifest.json'],
        'manifest_sha256': files['client-visual-manifest.json']['sha256'],
        'archive_sha256': files['client-visual-assets.zip']['sha256'],
        'worktree': work['worktree_key'], 'installed_files': 2, 'reused_files': 0, 'decoded_files': 2,
        'fingerprint_reused': False, 'retained_baseline_payloads_preserved': True,
        'preparation_elapsed_seconds': 1, 'archive_read_bytes': 100,
        **dict.fromkeys(('imported_files_modified', 'generated_caches_modified', 'existing_supplements_modified',
                         'runtime_visual_validated', 'full_global_asset_closure'), False)}
    animation = dict(installed=True, reused=False, pigg=documents['server-animation-manifest.json']['pigg'],
        storage='owned_link_to_verified_runtime_payload', verified_payload_read_only=True, loose_inputs_preserved=True,
        additional_animation_payload_bytes=0, native_animation_reader_changed=False, physical_startup_timing_validated=False,
        client_contract=dict(**{key: work[key] for key in ('import', 'source_data')}, game_sha256='f' * 64,
            source_commit=native['source_commit'], data_commit=native['data_commit'],
            animation_inventory_sha256='5' * 64, loose_animation_count=2), elapsed_seconds=1)
    zones = {}
    for key, name, selection in (('client_zone_supplement', 'zones-world-supplement-manifest.json', 'all_zone_client_resources'),
            ('client_zone_audio_supplement', 'zones-audio-supplement-manifest.json', 'all_zone_client_audio')):
        doc = documents[name]
        zones[key] = dict(version=doc['version'], scope=selection, file_count=doc['file_count'], files_sha256=doc['files_sha256'],
            manifest_sha256=files[name]['sha256'], installed_files=doc['file_count'], decoded_payload_bytes=doc['payload_bytes'],
            fingerprint_reused=False, source_generation_rebound=False, elapsed_seconds=1,
            **dict.fromkeys(('imported_files_modified', 'prepared_caches_modified', 'runtime_visual_validated', 'physical_zoning_verified'), False))
    def record(sequence, tick):
        raw = progress.HEADER.pack(b'COHMAP1\0', 1, 128, 42, 43, sequence, 37, tick, tick, 0, len(progress.STAGES))
        raw += b'\0' * (128 - len(raw))
        return {**progress.decode_record(raw), 'available': True, 'unchanged_seconds': 0, 'file_identity': [1, 2, 128]}
    character = dict(session_id=SESSION, map_ready=True, map_id=1,
        mapserver_producer={'mapserver_sha256': pe['sha256'], 'repository_commit': COMMIT,
            'run_id': RUN, 'manifest_sha256': expected['build_manifest']['sha256'], 'armport_server_metrics': proof},
        map_startup_guard=dict(passed=True, requires_completed_tick_before_protocol=True, before=record(2, 1), after=record(4, 2),
            protocol=dict(ready=True, map_id=1, address='127.0.0.1', port=7001, network_age_seconds=0, stats_age_seconds=0)),
        committed_sql_verified=True, requested_logout_observed=True, forced_stop_before_save=False)
    stage_names = list(v.BASE_STAGES[:9]) + list(v.OPTIONAL_STAGES) + ['armport_client_data'] + list(v.BASE_STAGES[9:])
    rows = [{'stage': name, 'status': 'passed'} for name in stage_names]
    rows[13].update(machine='ARM64', x86_bins_reused=False, executable_sha256=arm['executable_sha256'])
    key = 'character_reopen' if reopening else 'character_creation'
    report = {'scope': 'actual_' + key + '_guest', 'session_id': SESSION, key: character,
        'stages': rows, 'client_worktree': work, 'client_visual_supplement': visual,
        'client_animation_pack': animation, **zones, 'armport_client': dict(machine='ARM64', x86_bins_reused=False, **arm),
        'asset_sha256': {key: value['sha256'] for key, value in files.items()},
        'processes': [{'label': 'local-character-zoning-1' if reopening else 'local-character-atlas'}],
        'failures': []}
    if reopening:
        report.update(zoning_enabled=True, character_zoning={'transfers': [], 'saved_startup': dict(map_id=1,
            native_ready_verified=True, character_world_entry_verified=True, native_maps_started=[1], sql_game_mutations_performed=False)})
        character.update(zoning_enabled=True, connected_on_supported_map=True)
    return report, runtime, {'files': copy.deepcopy(files)}, documents


class ModernAdmissionTests(unittest.TestCase):
    def test_exact_candidate_checkout_and_modified_or_untracked_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'source.py').write_text('candidate\n')
            subprocess.run(['git', '-C', str(root), 'add', 'source.py'], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=test', '-c', 'user.email=test@localhost', 'commit', '-qm', 'candidate'], check=True)
            commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
            self.assertEqual(v.verify_candidate_checkout(root, commit), root)
            with self.assertRaisesRegex(ValueError, 'another source'): v.verify_candidate_checkout(root, 'a' * 40)
            (root / 'source.py').write_text('changed\n')
            with self.assertRaisesRegex(ValueError, 'modified'): v.verify_candidate_checkout(root, commit)
            (root / 'source.py').write_text('candidate\n'); (root / 'shadow.py').write_text('foreign\n')
            with self.assertRaisesRegex(ValueError, 'modified'): v.verify_candidate_checkout(root, commit)

    def test_runtime_run_exact_candidate_identity(self):
        run = dict(id=456, head_sha=COMMIT, event='workflow_dispatch', status='completed', conclusion='success',
            path='.github/workflows/armport-app-runtime.yml', repository={'full_name': pipeline.REPOSITORY}, head_repository={'full_name': pipeline.REPOSITORY})
        self.assertEqual(v.verify_runtime_run(run, COMMIT, 456), run)
        for key, value in [('id', True), ('head_sha', 'b' * 40), ('event', 'push'), ('conclusion', 'failure'), ('path', '.github/workflows/other.yml')]:
            changed = dict(run, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError): v.verify_runtime_run(changed, COMMIT, 456)

    def test_native_admission_rejects_alternate_architecture_lineage_run_and_session(self):
        report, runtime, _, _ = fixture()
        self.assertEqual(v.native_admission(report, runtime)['session_id'], SESSION)
        for target, key, value in [('producer', 'run_id', 124), ('proof', 'variant', 'retained_progress'),
                                  ('proof', 'actual_mapserver_sha256', '0' * 64), ('proof', 'gameplay_decisions_changed', True),
                                  ('proof', 'runtime_execution_validated', True), ('proof', 'package_receipt_sha256', '0' * 64)]:
            changed = copy.deepcopy(report); producer = changed['character_creation']['mapserver_producer']
            (producer if target == 'producer' else producer['armport_server_metrics'])[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): v.native_admission(changed, runtime)
        changed = copy.deepcopy(report); changed['session_id'] = '2' * 32
        with self.assertRaises(ValueError): v.native_admission(changed, runtime)

    def test_readiness_rejects_published_only_stale_unregistered_and_wrong_raw_pid(self):
        report, _, _, _ = fixture()
        v.validate_readiness(report, progress)
        for target, key, value in [('guard', 'passed', False), ('protocol', 'port', 7003),
                                  ('protocol', 'network_age_seconds', 21), ('before', 'tick_completed', 0),
                                  ('before', 'unchanged_seconds', 21), ('after', 'windows_pid', 99),
                                  ('after', 'file_identity', [3, 4, 128])]:
            changed = copy.deepcopy(report); guard = changed['character_creation']['map_startup_guard']
            obj = guard if target == 'guard' else guard[target]
            obj[key] = value
            with self.subTest(target=target, key=key), self.assertRaises((ValueError, progress.base.DiagnosticError)):
                v.validate_readiness(changed, progress)

    def test_optional_stages_and_asset_preservation_are_required(self):
        report, runtime, _, docs = fixture()
        v.validate_components(report, runtime, docs)
        for mutate in [lambda r: r['stages'].pop(9), lambda r: r['stages'][9].update(status='failed'),
                       lambda r: r['stages'].insert(9, {'stage': 'unqualified', 'status': 'passed'}),
                       lambda r: r['client_visual_supplement'].update(imported_files_modified=True),
                       lambda r: r['client_visual_supplement'].update(reused_files=3),
                       lambda r: r['client_visual_supplement'].update(fingerprint_reused=True, archive_read_bytes=0),
                       lambda r: r['client_zone_supplement'].update(source_generation_rebound=True),
                       lambda r: r['client_animation_pack'].update(loose_inputs_preserved=False),
                       lambda r: r['client_zone_supplement'].update(file_count=2),
                       lambda r: r['client_zone_audio_supplement'].update(fingerprint_reused=True),
                       lambda r: r['client_zone_audio_supplement'].update(prepared_caches_modified=True)]:
            changed = copy.deepcopy(report); mutate(changed)
            with self.assertRaises(ValueError): v.validate_components(changed, runtime, docs)

    def test_projection_preserves_raw_save_failure_identity_and_cleanup_evidence(self):
        for reopening in (False, True):
            report, runtime, client, docs = fixture(reopening)
            report.update(cleanup={'postgres_graceful': False}, failures=['original SQL failure'])
            key = 'character_reopen' if reopening else 'character_creation'
            report[key]['committed_sql_verified'] = False
            before = copy.deepcopy(report)
            projector = v.ModernProjector(interactive, runtime, client, docs, progress)
            projected = projector.project(report, runtime, client)
            self.assertEqual(report, before)
            self.assertEqual(projected[key], before[key])
            self.assertEqual(projected['cleanup'], before['cleanup'])
            self.assertEqual(projected['failures'], before['failures'])
            self.assertEqual([r['stage'] for r in projected['stages']], list(v.BASE_STAGES))
            self.assertEqual(projected['processes'][0]['label'], 'local-character-atlas')
            self.assertEqual(projector.records[SESSION]['session_id'], SESSION)

    def test_zoning_route_requires_current_real_world_entry_no_task_removal(self):
        for mutation in [lambda r: r.update(zoning_enabled=False),
                         lambda r: r['character_zoning']['saved_startup'].update(character_world_entry_verified=False),
                         lambda r: r['character_zoning']['saved_startup'].update(native_maps_started=[1, 5]),
                         lambda r: r['processes'].append({'label': 'local-character-atlas'}),
                         lambda r: r['processes'][0].update(label='unowned-map')]:
            report, runtime, client, docs = fixture(True); mutation(report)
            projector = v.ModernProjector(interactive, runtime, client, docs, progress)
            with self.assertRaises(ValueError): projector.project(report, runtime, client)

    def test_two_slow_sessions_each_retain_their_own_existing_bound(self):
        clock, calls, continuity = [100.0], [], []
        first, second = '1' * 32, '2' * 32
        def run_session(*args, **kwargs):
            self.assertEqual(args[7] - clock[0], 5400)
            calls.append((list(args[0]), args[4], args[7], kwargs))
            clock[0] += 5399
            return {'session_id': args[4]}
        reopen = SimpleNamespace(
            persistent_profile_identity=lambda _work: {'same_profile': True},
            archive_completed_reports=lambda *_args: None,
            reset_session_requests=lambda *_args: None,
            reopen_command=lambda command, previous, session: [value.replace(previous, session) for value in command],
            validate_continuity=lambda *args: continuity.append(args))
        driver = SimpleNamespace(character=SimpleNamespace(OVERALL_SECONDS=5400), reopen=reopen, run_session=run_session)
        with mock.patch.object(host.time, 'monotonic', side_effect=lambda: clock[0]):
            created, reopened, timing = host.run_character_pair(driver, ['python', first], Path('/work'),
                Path('/evidence'), Path('/proot'), {}, {}, first, second)
        self.assertEqual([item[1] for item in calls], [first, second])
        self.assertNotIn('--zoning', calls[0][0])
        self.assertEqual(calls[1][0][-1], '--zoning')
        self.assertEqual(calls[1][3], {'reopening': True})
        self.assertEqual(calls[1][2] - calls[0][2], 5399)
        self.assertEqual(timing['per_session_seconds'], 5400)
        self.assertEqual(continuity, [(created, reopened, {'same_profile': True}, {'same_profile': True})])

    def test_candidate_manifest_component_bytes_are_reauthenticated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); manifest = {'files': {}}
            names = ('client-visual-manifest.json', 'server-animation-manifest.json', 'zones-world-supplement-manifest.json', 'zones-audio-supplement-manifest.json')
            for name in names:
                (root / name).write_text('{"fixture":true}')
                manifest['files'][name] = donor.pin(root / name)
            self.assertEqual(set(v.contracts(root, manifest)), set(names))
            (root / names[0]).write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, 'metadata changed'): v.contracts(root, manifest)


if __name__ == '__main__': unittest.main()
