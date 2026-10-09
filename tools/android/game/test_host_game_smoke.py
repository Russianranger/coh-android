"""Fail-closed input, execution and report tests for the hosted game gate."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import host_game_smoke as host


def loopback_sample(game, expected):
    donor = json.loads((host.ROOT / 'docs/android-evidence/dbserver-package-36460867428.json').read_text())
    build_input = donor['wine_build_input']
    endpoints = host.dbhost.validate_loopback_build_input(build_input)
    expected.update(dbserver_profile='loopback', loopback_metadata=build_input['loopback_only'],
                    loopback_endpoints=endpoints)
    game.update(dbserver_profile='loopback',
                loopback_only={'requested': True, 'metadata': copy.deepcopy(build_input['loopback_only'])})
    for phase in game['phases']:
        phase['loopback_only'] = {'requested': True, 'startup_acknowledgement': host.dbhost.LOOPBACK_ACK,
                                 'endpoints': copy.deepcopy(endpoints['required'])}
    return endpoints


def loopback_stdout(endpoints):
    return host.dbhost.LOOPBACK_ACK + '\n' + ''.join(
        'COH_WINE_DB_LOOPBACK_ONLY bind verified: protocol={protocol} address={address} port={port}\n'.format(**value)
        for value in endpoints)


def fixed_input_sample():
    record = {'bytes': 1, 'sha256': 'a' * 64}
    schema = {'files': {'data/defs/entities.def': {'bytes': 2, 'sha256': 'b' * 64},
                        **{'data/attributes/name' + str(number) + '.def': dict(record) for number in range(61)}}}
    data = {'files': {'data/server/db/servers.cfg': dict(record),
                      'data/server/db/sub/WeeklyTF.cfg': dict(record),
                      'data/defs/Entities.def': dict(record), 'data/bin/generated.bin': dict(record)}}
    expected = host.fixed_input_expectations(data, schema)
    files = {name: (record if record is not None else {'bytes': 100, 'sha256': 'c' * 64})
             for name, record in expected['files'].items()}
    payload = {'files': copy.deepcopy(files), 'directories': expected['directories'].copy()}
    baseline = {**payload, 'inventory_sha256': host.canonical_digest(payload),
                'file_count': len(files), 'total_bytes': sum(record['bytes'] for record in files.values())}
    value = {'requested': True, 'metadata': copy.deepcopy(host.dbhost.FIXED_INPUTS_METADATA),
             'scope': 'accepted_schema_and_db_configuration', 'schema_file_count': 62, 'baseline': baseline,
             'checks': [{'phase': phase, 'unchanged': True,
                         **{key: baseline[key] for key in ('inventory_sha256', 'file_count', 'total_bytes')}}
                        for phase in ('before-first', 'after-first-save', 'before-restart', 'after-second-save')]}
    return value, expected


class FixedInputTests(unittest.TestCase):
    def sample(self):
        value, expected = fixed_input_sample()
        phases = [{'fixed_inputs': {'requested': True, 'startup_acknowledgement': host.dbhost.FIXED_INPUTS_ACK}}
                  for _ in range(2)]
        return {'fixed_inputs': value, 'phases': phases}, expected

    def reseal(self, game):
        value = game['fixed_inputs']
        baseline = value['baseline']
        baseline['file_count'] = len(baseline['files'])
        baseline['total_bytes'] = sum(record['bytes'] for record in baseline['files'].values())
        baseline['inventory_sha256'] = host.canonical_digest({key: baseline[key] for key in ('files', 'directories')})
        for check in value['checks']:
            check.update({key: baseline[key] for key in ('inventory_sha256', 'file_count', 'total_bytes')})

    def test_host_derives_exact_casefold_schema_overlay_and_configuration_union(self):
        game, expected = self.sample()
        host.validate_fixed_inputs(game, expected)
        self.assertEqual(expected['files']['data/defs/Entities.def'], {'bytes': 2, 'sha256': 'b' * 64})
        self.assertIsNone(expected['files']['data/server/db/servers.cfg'])
        self.assertNotIn('data/defs/entities.def', expected['files'])
        self.assertNotIn('data/bin/generated.bin', expected['files'])
        self.assertEqual(expected['directories'], ['data/server/db', 'data/server/db/sub'])

    def test_resealed_file_scope_metadata_and_phase_tampering_is_rejected(self):
        mutations = [lambda g: g['fixed_inputs'].update(requested=1),
                     lambda g: g['fixed_inputs'].update(unexpected='unbound metadata'),
                     lambda g: g['fixed_inputs'].update(scope='all_data'),
                     lambda g: g['fixed_inputs'].update(schema_file_count=61),
                     lambda g: g['fixed_inputs']['metadata'].update(disabled_by_default=False),
                     lambda g: g['fixed_inputs']['baseline']['files']['data/defs/Entities.def'].update(sha256='d'*64),
                     lambda g: g['fixed_inputs']['baseline']['files']['data/server/db/servers.cfg'].update(bytes=0),
                     lambda g: g['fixed_inputs']['baseline']['files'].pop('data/server/db/sub/WeeklyTF.cfg'),
                     lambda g: g['fixed_inputs']['baseline']['files'].update({'data/extra.cfg': {'bytes': 1, 'sha256': 'e'*64}}),
                     lambda g: g['fixed_inputs']['baseline']['directories'].append('data/server/db/extra'),
                     lambda g: g['fixed_inputs']['checks'].pop(),
                     lambda g: g['fixed_inputs']['checks'][1].update(phase='before-first'),
                     lambda g: g['fixed_inputs']['checks'][2].update(unchanged=1),
                     lambda g: g['phases'][0]['fixed_inputs'].update(requested=1),
                     lambda g: g['phases'][1]['fixed_inputs'].update(startup_acknowledgement='missing')]
        for number, mutate in enumerate(mutations):
            with self.subTest(mutation=number):
                game, expected = self.sample()
                mutate(game)
                self.reseal(game)
                with self.assertRaises(RuntimeError):
                    host.validate_fixed_inputs(game, expected)


class InputTests(unittest.TestCase):
    def record(self, payload=b"x"):
        return {"bytes": len(payload), "sha256": host.dbhost.hashlib.sha256(payload).hexdigest()}

    def test_inventory_bounds_reject_escape_case_collision_and_excess(self):
        record = self.record()
        self.assertEqual(host.inventory_bounds({"data/one": record}, maximum_files=1, maximum_bytes=1), 1)
        for files, count, size in (({"../outside": record}, 1, 1),
                                   ({"data/Name": record, "data/name": record}, 2, 2),
                                   ({"data/one": record}, 0, 1),
                                   ({"data/one": record}, 1, 0),
                                   ({"data/one": {**record, "bytes": True}}, 1, 1),
                                   ({"data/one": {**record, "sha256": "not-a-hash"}}, 1, 1)):
            with self.subTest(files=files, count=count, size=size), self.assertRaises(RuntimeError):
                host.inventory_bounds(files, maximum_files=count, maximum_bytes=size)

    def test_game_data_requires_reviewed_full_assembly_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = {"format": 1, "scope": "reviewed_game_data",
                        "source_commit": host.dbhost.SOURCE_COMMIT, "data_commit": host.dbhost.DATA_COMMIT,
                        "files": {"data/one": self.record()}, "file_count": 1, "total_bytes": 1,
                        "asset_manifest_sha256": host.ASSET_MANIFEST_SHA256,
                        "asset_archive_sha256": host.ASSET_ARCHIVE_SHA256,
                        "android_execution_validated": False, "gameplay_validated": False}
            (root / "game-data-manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(RuntimeError, "reviewed full asset/text"):
                host.verify_data(root)

    def test_bounded_json_rejects_links_and_oversized_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / "report.json"
            report.write_text('{"format":1}')
            self.assertEqual(host.read_json(report), {"format": 1})
            with self.assertRaisesRegex(RuntimeError, "oversized"):
                host.read_json(report, limit=2)
            linked = root / "linked.json"
            linked.symlink_to(report)
            with self.assertRaisesRegex(RuntimeError, "linked"):
                host.read_json(linked)

    def test_output_overlap_and_low_disk_fail_before_staging(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data, work, evidence = root / "data", root / "work", root / "evidence"
            data.mkdir()
            with mock.patch.object(host.shutil, "disk_usage", return_value=mock.Mock(free=host.MIN_FREE_BYTES)):
                record = host.check_paths_and_space(work, evidence, (data,), data_bytes=100)
                self.assertEqual(record["required_free_bytes"], host.MIN_FREE_BYTES)
                for new_work, new_evidence in ((data / "work", evidence), (work, work / "evidence"),
                                                (root, evidence)):
                    with self.subTest(work=new_work, evidence=new_evidence), self.assertRaises(RuntimeError):
                        host.check_paths_and_space(new_work, new_evidence, (data,), data_bytes=100)
            with mock.patch.object(host.shutil, "disk_usage", return_value=mock.Mock(free=host.MIN_FREE_BYTES-1)):
                with self.assertRaisesRegex(RuntimeError, "Insufficient disk"):
                    host.check_paths_and_space(work, evidence, (data,), data_bytes=100)
            self.assertFalse(work.exists())
            self.assertFalse(evidence.exists())


class PackageTests(unittest.TestCase):
    def sample(self, dbserver_profile='accepted'):
        paths = {"reference": "docs/reference-runtime-evidence/build-36088012664.json",
                 "dbserver": "docs/android-evidence/dbserver-package-36451873322.json",
                 "resume": "docs/postgresql-evidence/resume-testclient-build-36297542986.json"}
        donors = host.DONORS
        if dbserver_profile == 'loopback':
            paths['dbserver'] = 'docs/android-evidence/dbserver-package-36460867428.json'
            donors = {**donors, 'dbserver': host.LOOPBACK_DONOR}
        proofs = {role: {**{key: pin[key] for key in ("run_id", "repository_commit", "manifest_sha256")},
                         "manifest": json.loads((host.ROOT / paths[role]).read_text())}
                  for role, pin in donors.items()}
        reference = proofs["reference"]["manifest"]["files"]
        normal = proofs["dbserver"]["manifest"]["variants"]["normal"]["files"]
        selected = {name: (record, "reference") for name, record in reference.items() if name.lower().endswith(".dll")}
        selected.update({"MapServer.exe": (reference["MapServer.exe"], "reference"),
                         "TestClientCreate.exe": (reference["TestClient.exe"], "reference")})
        selected.update({name: (record, "dbserver") for name, record in normal.items()})
        selected["TestClientResume.exe"] = (proofs["resume"]["manifest"]["files"]["TestClient.exe"], "resume")
        bridge_record = {"bytes": 512, "sha256": "a" * 64, "pe_machine": "0x014c", "pe_format": "PE32",
                         "imports": ["KERNEL32.dll"], "delay_imports": []}
        bridge = {"format": 1, "role": "stock_testclient_launcher_bridge", "repository_commit": "f" * 40,
                  "architecture": "Win32", "compiler": "MSVC", "flags": "/nologo /W4 /O2 /MT /D_WIN32_WINNT=0x0601",
                  "sources_sha256_lf": {name: host.hashlib.sha256((host.ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                        for name in ("database/wine-game/TestClientBridge.c", "database/wine-game/bridge_protocol.h")},
                  "files": {"TestClientBridge.exe": bridge_record}}
        proofs["bridge"] = {"repository_commit": "f" * 40, "manifest": bridge,
                            "manifest_sha256": host.hashlib.sha256((json.dumps(bridge, indent=2) + "\n").encode()).hexdigest()}
        selected["TestClientBridge.exe"] = (bridge_record, "bridge")
        files = {name: {**{key: value for key, value in record.items() if key != "size"},
                        "bytes": record.get("bytes", record.get("size"))} for name, (record, _) in selected.items()}
        return {**({'dbserver_profile': 'loopback'} if dbserver_profile == 'loopback' else {}),
                "format": 1, "role": "wine_game_runtime", "source_commit": host.dbhost.SOURCE_COMMIT,
                "data_commit": host.dbhost.DATA_COMMIT, "repository_commit": "f" * 40,
                "client_version": "coh-persistence-diagnostic", "postgresql_persistence_fixture": False,
                "runtime_execution_validated": False, "inputs": proofs, "files": files,
                "file_donors": {name: role for name, (_, role) in selected.items()},
                "dependency_report": host.dependency_report(files)}

    def test_profile_requires_exact_loopback_donor_and_explicit_host_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = self.sample('loopback')
            for name in candidate['files']:
                (root / name).write_bytes(name.encode())
            def pe_record(data):
                return {key: value for key, value in candidate['files'][data.decode()].items()
                        if key not in ('bytes', 'sha256')}
            with mock.patch.object(host.dbhost, 'verify_inventory'), mock.patch.object(host, 'pe_info', side_effect=pe_record):
                path = root / 'game-package.json'
                path.write_text(json.dumps(candidate))
                host.verify_package(root, dbserver_profile='loopback')
                with self.assertRaisesRegex(RuntimeError, 'profile differs'):
                    host.verify_package(root)
                mutations = [lambda m: m.pop('dbserver_profile'),
                             lambda m: m.update(dbserver_profile='unqualified'),
                             lambda m: m['inputs'].update(dbserver=self.sample()['inputs']['dbserver']),
                             lambda m: m['inputs']['dbserver'].update(run_id=36451873322),
                             lambda m: m['inputs']['dbserver']['manifest']['wine_build_input']['loopback_only'].update(
                                 disabled_by_default=False)]
                for number, mutate in enumerate(mutations):
                    with self.subTest(mutation=number):
                        changed = copy.deepcopy(candidate)
                        mutate(changed)
                        path.write_text(json.dumps(changed))
                        with self.assertRaises(RuntimeError):
                            host.verify_package(root, dbserver_profile='loopback')

    def test_package_requires_exact_donors_and_current_bridge_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sample = self.sample()
            for name in sample["files"]:
                (root / name).write_bytes(name.encode())
            def pe_record(data):
                return {key: value for key, value in sample["files"][data.decode()].items()
                        if key not in ("bytes", "sha256")}
            with mock.patch.object(host.dbhost, "verify_inventory"), mock.patch.object(host, "pe_info", side_effect=pe_record):
                path = root / "game-package.json"
                path.write_text(json.dumps(sample))
                host.verify_package(root)
                mutations = [lambda m: m["inputs"]["reference"].update(run_id=1),
                             lambda m: m["inputs"]["reference"]["manifest"]["files"]["MapServer.exe"].update(sha256="b"*64),
                             lambda m: m["inputs"]["bridge"]["manifest"].update(sources_sha256_lf={}),
                             lambda m: m["inputs"]["bridge"].update(manifest_sha256="b"*64),
                             lambda m: m["files"]["DbServer.exe"].update(sha256="b"*64),
                             lambda m: m["file_donors"].update(**{"DbServer.exe": "reference"}),
                             lambda m: m.update(postgresql_persistence_fixture=True),
                             lambda m: m["files"].update(**{"Unexpected.exe": m["files"]["MapServer.exe"]})]
                for index, mutate in enumerate(mutations):
                    with self.subTest(case=index):
                        value = copy.deepcopy(sample)
                        mutate(value)
                        path.write_text(json.dumps(value))
                        with self.assertRaises(RuntimeError):
                            host.verify_package(root)


class MapServerProgressHostTests(unittest.TestCase):
    def progress_sample(self):
        sys.path.insert(0, str(host.ROOT / 'android/guest'))
        import game_map_progress as progress
        producer = {'repository_commit': 'f' * 40, 'manifest_sha256': 'a' * 64,
                    'mapserver_sha256': 'b' * 64}
        value = progress.evidence(producer)
        for inode, label in enumerate(('first', 'restart'), 1):
            phase = {'fresh_path_before_launch': True, 'process_label': label + '-atlas',
                     'path_name': 'coh-map-progress-' + label + '-fixture.bin',
                     'launch_monotonic': 0, 'sample_count': 0, 'dropped_samples': 0, 'samples': []}
            value['phases'][label] = phase
            for ticks in (0, 1):
                raw = progress.HEADER.pack(b'COHMAP1\0', 1, 128, inode * 100, 42, (ticks + 1) * 2,
                                           34 if ticks else 1, ticks, ticks, 0, 37) + bytes(80)
                sample = {**progress.decode_record(raw), 'available': True, 'is_success_proof': False,
                          'reason': 'owned_read', 'observed_monotonic': ticks + 1,
                          'file_identity': {'device': 1, 'inode': inode},
                          'freshness': 'advanced' if ticks else 'initial',
                          'last_advance_monotonic': ticks + 1, 'unchanged_seconds': 0}
                progress.append_sample(phase, sample)
        return value, {'mapserver_progress_profile': host.MAPSERVER_PROGRESS_PROFILE,
                       'mapserver_progress_producer': producer}

    def candidate(self):
        manifest = host.accepted_game_package()
        manifest['repository_commit'] = 'f' * 40
        manifest['mapserver_progress_profile'] = host.MAPSERVER_PROGRESS_PROFILE
        manifest['files']['MapServer.exe']['sha256'] = 'a' * 64
        record = dict(manifest['files']['MapServer.exe'])
        record['size'] = record.pop('bytes')
        donor = {'repository_commit': 'f' * 40, 'files': {'MapServer.exe': record}}
        manifest['inputs']['mapserver_progress'] = {
            'repository_commit': 'f' * 40, 'manifest': donor,
            'manifest_sha256': host.hashlib.sha256((json.dumps(donor, indent=2) + '\n').encode()).hexdigest()}
        manifest['file_donors']['MapServer.exe'] = 'mapserver_progress'
        return manifest

    def test_explicit_profile_keeps_exact_accepted_supporting_donors(self):
        import package_mapserver_progress
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = self.candidate()
            for name in original['files']:
                (root / name).write_bytes(name.encode())
            def pe_record(data):
                return {key: value for key, value in original['files'][data.decode()].items()
                        if key not in ('bytes', 'sha256')}
            options = {'dbserver_profile': 'loopback', 'game_listener_profile': 'loopback',
                       'mapserver_progress_profile': host.MAPSERVER_PROGRESS_PROFILE}
            with mock.patch.object(host.dbhost, 'verify_inventory'), \
                    mock.patch.object(host, 'pe_info', side_effect=pe_record), \
                    mock.patch.object(package_mapserver_progress, 'verify_mapserver_progress_manifest') as verify:
                path = root / 'game-package.json'
                path.write_text(json.dumps(original))
                host.verify_package(root, **options)
                verify.assert_called_once_with(original['inputs']['mapserver_progress']['manifest'], 'f' * 40,
                                               original['inputs']['reference']['manifest'])
                with self.assertRaisesRegex(RuntimeError, 'progress profile'):
                    host.verify_package(root, dbserver_profile='loopback', game_listener_profile='loopback')
                mutations = [lambda m: m.pop('mapserver_progress_profile'),
                             lambda m: m['inputs']['bridge'].update(repository_commit='f' * 40),
                             lambda m: m['inputs']['loopback_game']['manifest'].update(repository_commit='f' * 40),
                             lambda m: m['inputs']['mapserver_progress'].update(repository_commit=host.ACCEPTED_GAME_COMMIT),
                             lambda m: m['inputs']['mapserver_progress'].update(manifest_sha256='0' * 64),
                             lambda m: m['files']['TestClientCreate.exe'].update(sha256='0' * 64),
                             lambda m: m['file_donors'].update({'MapServer.exe': 'loopback_game'})]
                for index, mutation in enumerate(mutations):
                    with self.subTest(mutation=index):
                        value = copy.deepcopy(original)
                        mutation(value)
                        path.write_text(json.dumps(value))
                        with self.assertRaises(RuntimeError):
                            host.verify_package(root, **options)

    def test_progress_requires_exact_accepted_stack_receipt_without_relabeling(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'stack-probe-build.json').write_text('{}')
            with mock.patch.object(host.stack_probe_receipt, 'verify', return_value={}) as verify:
                with self.assertRaisesRegex(RuntimeError, 'exact accepted stack'):
                    host.verify_stack_probe(root, 'f' * 40, host.MAPSERVER_PROGRESS_PROFILE)
                verify.assert_not_called()
                with mock.patch.object(host, 'digest', return_value=host.ACCEPTED_STACK_PROBE_SHA256):
                    host.verify_stack_probe(root, 'f' * 40, host.MAPSERVER_PROGRESS_PROFILE)
                    verify.assert_called_once_with(root, host.ACCEPTED_GAME_COMMIT)
                verify.reset_mock()
                host.verify_stack_probe(root, 'f' * 40)
                verify.assert_called_once_with(root, 'f' * 40)

    def test_unselected_profile_rejects_diagnostic_claims(self):
        with self.assertRaisesRegex(RuntimeError, 'Unselected'):
            host.validate_mapserver_progress({'mapserver_progress': {}}, {})

    def test_success_requires_raw_completed_tick_advance_on_both_owned_starts(self):
        value, expected = self.progress_sample()
        report, full_expected = ReportTests().sample()
        report['game']['mapserver_progress'] = value
        full_expected.update(expected)
        host.validate_report(report, expected=full_expected)
        mutations = [lambda v: v['phases'].pop('restart'),
                     lambda v: v['producer'].update(mapserver_sha256='0' * 64),
                     lambda v: v['phases']['restart']['samples'][1].update(raw_record_sha256='0' * 64),
                     lambda v: v['phases']['first']['samples'][1].update(tick_completed=0),
                     lambda v: v['phases']['first']['samples'][1].update(freshness='unchanged'),
                     lambda v: v['phases']['restart']['samples'][1].update(file_identity={'device': 1, 'inode': 99})]
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                changed = copy.deepcopy(value)
                mutation(changed)
                with self.assertRaises(RuntimeError):
                    host.validate_mapserver_progress({'mapserver_progress': changed}, expected)
        # A valid producer record is additional evidence, never a replacement
        # for the existing fresh Atlas endpoint and complete game lifecycle.
        report['game']['phases'][0]['map']['network_age_seconds'] = 21
        with self.assertRaises(RuntimeError):
            host.validate_report(report, expected=full_expected)

    def test_failure_exports_bounded_raw_progress_without_claiming_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / 'state', root / 'evidence'
            captures = state / 'game-captures'
            captures.mkdir(parents=True)
            evidence.mkdir()
            source = captures / 'mapserver-progress.json'
            source.write_text('{"enabled":true,"is_success_proof":false}')
            records = host.copy_game_captures(state, evidence)
            self.assertEqual(records[source.name]['sha256'], host.digest(source))
            self.assertEqual((evidence / 'game-captures' / source.name).read_bytes(), source.read_bytes())
            with self.assertRaisesRegex(RuntimeError, 'exact exported capture inventory'):
                host.validate_capture_files({'game': {'capture_files': records}}, evidence, records)


class RunnerTests(unittest.TestCase):
    def test_game_binds_keep_accepted_runtime_and_separate_script_inputs(self):
        root = Path("/owned")
        command = host.make_command(work=root / "work", assets=root / "m2", package=root / "package",
                                    data=root / "data", schema=root / "schema", proot=root / "proot",
                                    timeout_seconds=3600)
        for value in ("/owned/m2:/opt/coh", "/owned/work/m3-tools:/opt/coh-m3",
                      "/owned/package:/opt/coh-game-package", "/owned/data:/opt/coh-game-data",
                      "/owned/schema:/opt/coh-schema", "/owned/work/hosts:/etc/hosts"):
            self.assertIn(value, command)
        self.assertIn("/opt/coh-m3/game_diagnostic.py", command)
        self.assertNotIn("/opt/coh-m3/dbserver_diagnostic.py", command)
        self.assertNotIn("/opt/coh-dbserver", command)
        self.assertNotIn("--package", command)
        self.assertIn("--game-package", command)
        self.assertEqual(command[-4:], ["--game-data", "/opt/coh-game-data", "--execution-platform", "host"])
        self.assertEqual(command[command.index("/usr/bin/env") + 1], "-i")

    def test_zero_exit_cannot_accept_stale_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / "state", root / "evidence"
            state.mkdir()
            evidence.mkdir()
            for path in (state / "latest-report.json", evidence / "game-runtime-report.json"):
                path.write_text('{"format":1,"passed":true}')
            with self.assertRaisesRegex(RuntimeError, "fresh bounded report"):
                host.run_guest([sys.executable, "-c", "pass"], {}, state, evidence,
                               timeout_seconds=1, expected={})
            self.assertFalse((state / "latest-report.json").exists())
            self.assertFalse((evidence / "game-runtime-report.json").exists())

    def test_oversized_report_is_not_published_or_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / "state", root / "evidence"
            state.mkdir()
            evidence.mkdir()
            command = [sys.executable, "-c", "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('x'*100)",
                       str(state / "latest-report.json")]
            with mock.patch.object(host, "MAX_REPORT_BYTES", 10), self.assertRaisesRegex(RuntimeError, "fresh bounded report"):
                host.run_guest(command, {}, state, evidence, timeout_seconds=1, expected={})
            self.assertFalse((evidence / "game-runtime-report.json").exists())


class ProgressTests(unittest.TestCase):
    def event(self, **updates):
        return {"type": "stage", "stage": "game_services_first", "status": "running",
                "time_utc": "2026-09-28T04:30:00+00:00", "message": "Waiting for Atlas", **updates}

    def test_only_complete_bounded_stage_fields_are_forwarded(self):
        observed = []
        progress = host.StageProgress(observed.append)
        event = self.event(files=123, password="must stay in capture", output="private console")
        raw = json.dumps(event).encode() + b'\n'
        progress.feed(raw[:20])
        self.assertEqual(observed, [])
        progress.feed(raw[20:])
        self.assertEqual(observed, [self.event(files=123)])
        for value in (self.event(type="log"), self.event(stage="unreviewed_stage"),
                      self.event(status="arbitrary"), {"secret": "not-a-stage"}, []):
            progress.feed(json.dumps(value).encode() + b'\n')
        progress.feed(b'raw subprocess warning\n\xff\n')
        progress.feed(b'x' * (host.PROGRESS_LINE_LIMIT + 1))
        self.assertEqual(len(progress.pending), 0)
        progress.feed(json.dumps(self.event()).encode() + b'\n')  # Still part of the discarded line.
        progress.feed(json.dumps(self.event(status="passed", message="x" * 257, files=True)).encode() + b'\n')
        self.assertEqual(len(observed), 2)
        self.assertEqual(observed[-1], {"type": "stage", "stage": "game_services_first", "status": "passed",
                                      "time_utc": "2026-09-28T04:30:00+00:00"})

    def test_progress_is_visible_before_child_exits_and_raw_log_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log_path, acknowledgement = root / "capture.log", root / "observed"
            event = self.event()
            program = ("import json,pathlib,sys,time\n"
                       "print(json.dumps(json.loads(sys.argv[1])),flush=True)\n"
                       "marker=pathlib.Path(sys.argv[2]); deadline=time.monotonic()+5\n"
                       "while not marker.exists() and time.monotonic()<deadline: time.sleep(.01)\n"
                       "sys.exit(0 if marker.exists() else 2)\n")
            observed = []
            with log_path.open('wb') as log:
                process = subprocess.Popen([sys.executable, '-c', program, json.dumps(event), str(acknowledgement)],
                                           stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    def emit(value):
                        self.assertIsNone(process.poll(), 'Progress arrived only after process completion')
                        observed.append(value)
                        acknowledgement.write_text('seen')
                    self.assertEqual(host.wait_with_progress(process, log_path, 6, emit=emit), 0)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
            self.assertEqual(observed, [event])
            self.assertEqual(log_path.read_bytes(), json.dumps(event).encode() + b'\n')

    def test_final_drain_and_event_count_are_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'capture.log'
            path.write_bytes(json.dumps(self.event(status='passed')).encode() + b'\n')
            observed = []
            with path.open('rb') as stream:
                progress = host.StageProgress(observed.append)
                progress.count = host.PROGRESS_EVENT_LIMIT - 1
                progress.drain(stream)
                progress.feed(json.dumps(self.event()).encode() + b'\n')
            self.assertEqual(len(observed), 1)
            process = mock.Mock(args=['completed-guest'])
            process.wait.return_value = 0
            observed = []
            self.assertEqual(host.wait_with_progress(process, path, 1, emit=observed.append), 0)
            self.assertEqual(observed, [self.event(status='passed')])

    def test_host_timeout_keeps_original_stop_policy_and_regular_file_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / 'state', root / 'evidence'
            state.mkdir(); evidence.mkdir()
            process = mock.Mock(args=['guest'])
            with mock.patch.object(host.subprocess, 'Popen', return_value=process) as start, \
                    mock.patch.object(host, 'wait_with_progress', side_effect=subprocess.TimeoutExpired(['guest'], 91)) as wait, \
                    mock.patch.object(host.dbhost, 'stop_guest', return_value='wrapper exited after stop') as stop:
                with self.assertRaisesRegex(RuntimeError, 'tracee cleanup is unverified'):
                    host.run_guest(['guest'], {}, state, evidence, timeout_seconds=1, expected={})
            self.assertEqual(wait.call_args.args[2], 91)
            stop.assert_called_once_with(process, state)
            self.assertEqual(Path(start.call_args.kwargs['stdout'].name), evidence / 'host-game.log')
            self.assertTrue(start.call_args.kwargs['start_new_session'])
            self.assertEqual(start.call_args.kwargs['stderr'], subprocess.STDOUT)
            self.assertTrue((evidence / 'game-captures.json').is_file())


class ReportTests(unittest.TestCase):
    def sample(self):
        expected = {"inputs": {"game_package_sha256": "a" * 64}, "schema": {
            "table_count": 99, "column_count": 5935, "attribute_counts": {"attributes": 56411},
            "attribute_sha256": {"attributes": "a" * 64}, "ordered_columns_sha256": "b" * 64},
            "runtime_lock_sha256": "c" * 64}
        fixed_inputs, expected['fixed_inputs'] = fixed_input_sample()
        stages = [{"stage": name, "status": "passed"} for name in host.STAGES]
        stages[0].update(input_files=host.DATA_FILE_COUNT, input_bytes=host.DATA_TOTAL_BYTES, accepted_schema_overlay_files=62)
        stages[2].update(cluster_reused=False)
        owned = {"complete": True, "remaining": 0, "inspection_failures": 0}
        ready_map = {"ready": True, "map_id": 1, "address": "127.0.0.1", "port": 7001,
                     "network_age_seconds": 0, "stats_age_seconds": 1}
        rows = {"ents": 1, "ents2": 1, "powers": 4, "costumeparts": 7}
        ready = {"format": 1, "child_pid": 120, "transport_pid": 120, "console_attached": True,
                 "pipe_pid_verified": True, "protocol_pid_verified": True, "initial_snapshot": True,
                 "buffer_rows_limit": 16384, "version_requests": 1, "capture_byte_limit": 16*1024*1024,
                 "event_byte_limit": 8*1024*1024}
        result = {"format": 1, "child_pid": 120, "child_exit_code": 0, "child_forced_stop": True,
                  "error": None, "final_snapshot": True, "pipe_framing_complete": True, "version_requests": 1,
                  "pipe_disconnected": True,
                  "command_count": 3, "event_count": 15, "console_snapshots": 20,
                  "capture_byte_limit": 16*1024*1024, "event_byte_limit": 8*1024*1024}
        session = {"proof_completed_before_stop": True, "ready": ready, "result": result,
                   "commands": 3, "console_sha256": "d"*64, "events_sha256": "e"*64}
        comparison = {"identity_unchanged": True, "selected_rows_unchanged": True,
                      "login_count_before": 1, "row_counts": rows}
        save = {"protocol_quit": True, "quitnow_is_save_ack": False, "disconnected_before_sql": True,
                "independent_committed_sql": True, "forced_stop_before_save": False, "influence": 12345,
                "snapshot_sha256": "f"*64, "row_counts": rows}
        game = {"status": "passed", "created_connected": True, "attributes_unchanged": True,
                "fixed_inputs": fixed_inputs,
                "process_budget": 240, "query_budget": 80, "query_processes": 20, "readiness_queries": 4,
                "phases": [{"phase": name + "_services_ready", "status": "passed", "baseline_not_started": True,
                            "fixed_inputs": {"requested": True, "startup_acknowledgement": host.dbhost.FIXED_INPUTS_ACK},
                            "map": copy.deepcopy(ready_map), "schema": {**expected["schema"],
                            "catalog_sha256": {key: "1"*64 for key in ("columns", "indexes", "constraints")}}}
                           for name in ("first", "restart")],
                "atlas_observation": {"seconds": 30.1, "minimum_seconds": 30, "db_confirmed_ready": True,
                    "current_heartbeats": True, "samples": [{**ready_map, "monotonic": time} for time in (100, 115, 130)]},
                "account": "CohA0123456789", "character": {"container_id": 42, "name": "Hero", "account": "CohA0123456789"},
                "live_currency": {"player": "Hero", "account": "CohA0123456789", "influence": 12345, "sequence": 10},
                "first_save": {**save, "login_count": 1},
                "second_save": {**save, "login_count": 2, "comparison": {**comparison, "phase": "second_logout", "login_count_after": 2}},
                "restart": {**comparison, "phase": "restart", "login_count_after": 1, "same_cluster": True,
                    "same_database": True, "no_reseed_or_restore": True, "owned_cleanup": owned,
                    "wine_shutdown": {"prefix_lock_free": True, "server_socket_inactive": True}},
                "resume": {"database_id": 42, "exact_name": "Hero", "slot": 0, "creation_disabled": True,
                    "connected_on_atlas": True, "processed_server_update": True, "scene_exchange_observed": True,
                    "processed_server_update_for_original_player": True, "active_gameplay_confirmed": False},
                "sessions": {"first": copy.deepcopy(session), "second": copy.deepcopy(session)}}
        report = {"format": 1, "passed": True, "status": "passed", "failures": [], "cleanup_complete": True,
                  "diagnostic_mode": "atlas_character_persistence", "execution_platform_requested": "host",
                  "android_execution_validated": False, "gameplay_validated": False, "android_surface_validated": False,
                  "hardware_acceleration_validated": False, "interactive_rendering_validated": False,
                  "inputs": expected["inputs"], "stages": stages, "wine_process_cleanup": owned,
                  "cleanup": {key: True for key in ("postgres_graceful", "wine_prefix_stopped", "owned_processes_reaped")},
                  "processes": [{"label": name, "exit_code": 0, "input_closed": True, "output_capture_closed": True}
                                for name in ("first-dbserver", "first-atlas", "restart-dbserver", "restart-atlas",
                                             "bridge-create", "bridge-resume", "postgres_first_start", "postgres_game_restart")],
                  "wine_initialization": {"policy": "initialize_once_then_reuse", "state": "ready", "ready_prefix_reused": False,
                    "runtime_lock_sha256": expected["runtime_lock_sha256"], "registration_processes": 3,
                    "wow64_registration_processes": 1, "registration_passes": 1}, "game": game}
        return report, expected

    def test_full_two_session_contract_is_accepted(self):
        report, expected = self.sample()
        host.validate_report(report, expected=expected)

    def test_incomplete_readiness_save_resume_cleanup_or_bridge_is_rejected(self):
        mutations = [lambda r: r["stages"].pop(),
                     lambda r: r["inputs"].update(game_package_sha256="f"*64),
                     lambda r: r["processes"][0].update(output_capture_closed=False),
                     lambda r: r["wine_process_cleanup"].update(remaining=1),
                     lambda r: r["game"]["atlas_observation"].update(seconds=29.9),
                     lambda r: r["game"]["atlas_observation"].update(seconds=float('nan')),
                     lambda r: r["game"]["atlas_observation"]["samples"][1].update(monotonic=100),
                     lambda r: r["game"]["phases"][1]["map"].update(stats_age_seconds=21),
                     lambda r: r["game"]["phases"][1]["schema"].update(ordered_columns_sha256="f"*64),
                     lambda r: r["game"]["live_currency"].update(player="Other"),
                     lambda r: r["game"]["first_save"].update(independent_committed_sql=False),
                     lambda r: r["game"]["second_save"].update(forced_stop_before_save=True),
                     lambda r: r["game"]["restart"].update(no_reseed_or_restore=False),
                     lambda r: r["game"]["resume"].update(database_id=43),
                     lambda r: r["game"]["resume"].update(processed_server_update=False),
                     lambda r: r["game"]["sessions"]["first"]["ready"].update(transport_pid=121),
                     lambda r: r["game"]["sessions"]["second"]["result"].update(final_snapshot=False),
                     lambda r: r["game"]["sessions"]["second"]["result"].update(pipe_disconnected=False),
                     lambda r: r["game"]["sessions"]["second"]["result"].update(child_exit_code=259),
                     lambda r: r["game"]["sessions"]["second"]["result"].update(child_exit_code=None),
                     lambda r: r["game"]["sessions"]["second"]["result"].update(child_exit_code=True),
                     lambda r: r["game"]["sessions"]["second"]["result"].update(child_exit_code=-1),
                     lambda r: r["game"]["sessions"]["second"]["result"].update(child_exit_code=0x100000000),
                     lambda r: r["game"]["sessions"]["second"].update(proof_completed_before_stop=False)]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                report, expected = self.sample()
                expected = copy.deepcopy(expected)
                mutate(report)
                with self.assertRaises(RuntimeError):
                    host.validate_report(report, expected=expected)


class GameListenerHostTests(unittest.TestCase):
    def output(self, ports):
        return host.GAME_LOOPBACK_ACK + '\n' + ''.join(
            f'{host.GAME_LOOPBACK_ENV} bind verified: protocol=udp address=127.0.0.1 port={port}\n'
            for port in ports)

    def sample(self):
        report, expected = ReportTests().sample()
        loopback_sample(report['game'], expected)
        metadata = {'environment_variable': host.GAME_LOOPBACK_ENV, 'disabled_by_default': True}
        expected.update(game_listener_profile='loopback', game_listener_metadata=metadata)
        game = report['game']
        game.update(game_listener_profile='loopback',
                    game_listener_policy={'requested': True, 'metadata': copy.deepcopy(metadata)},
                    client_listener_observations={})
        for phase in game['phases']:
            phase['game_listeners'] = host.parse_game_listener_output(self.output([7001]), 'atlas')
        for label, session in game['sessions'].items():
            session['game_listeners'] = host.parse_game_listener_output(self.output([41001, 41002]), 'client')
            game['client_listener_observations'][label] = copy.deepcopy(session['game_listeners'])
        return report, expected

    def test_binding_policy_requires_live_and_final_proof_across_both_starts_and_saves(self):
        report, expected = self.sample()
        host.validate_report(report, expected=expected)
        mutations = [lambda g: g.pop('game_listener_profile'),
                     lambda g: g['game_listener_policy']['metadata'].update(disabled_by_default=False),
                     lambda g: g['phases'][1].pop('game_listeners'),
                     lambda g: g['phases'][0]['game_listeners']['endpoints'][0].update(address='0.0.0.0'),
                     lambda g: g['phases'][0]['game_listeners']['endpoints'][0].update(port=True),
                     lambda g: g['client_listener_observations'].pop('second'),
                     lambda g: g['sessions']['first']['game_listeners']['endpoints'].pop(),
                     lambda g: g['sessions']['second']['game_listeners']['endpoints'].reverse()]
        for number, mutate in enumerate(mutations):
            with self.subTest(mutation=number), self.assertRaises(RuntimeError):
                changed = copy.deepcopy(report)
                mutate(changed['game'])
                host.validate_report(changed, expected=expected)
        earlier_profile = dict(expected)
        earlier_profile.pop('game_listener_profile')
        with self.assertRaisesRegex(RuntimeError, 'unexpectedly claims'):
            host.validate_report(report, expected=earlier_profile)

    def test_host_parser_rejects_spoofed_incomplete_and_nonlocal_owned_output(self):
        good = self.output([41001, 41002])
        for text in ('', self.output([41001]), good.replace(host.GAME_LOOPBACK_ACK, 'missing'),
                     good + host.GAME_LOOPBACK_ACK + '\n', good.replace('udp', 'tcp'),
                     good.replace('127.0.0.1', '0.0.0.0'), good.replace('port=41001', 'port=0'),
                     good.replace('port=41001', 'port=65536'), 'prefix ' + good):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                host.parse_game_listener_output(text, 'client')
        value = host.parse_game_listener_output(self.output([41001, 41001]), 'client')
        self.assertEqual(value['endpoints'][0], value['endpoints'][1])

    def test_resealed_raw_atlas_capture_must_match_both_readiness_bindings(self):
        for tampered in (None, 'first-atlas', 'restart-atlas', 'first-dbserver'):
            with self.subTest(tampered=tampered), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                state, evidence = root / 'state', root / 'evidence'
                source = state / 'game-service-captures'
                source.mkdir(parents=True)
                evidence.mkdir()
                report, expected = self.sample()
                files = {}
                for label in host.SERVICE_LABELS:
                    if label.endswith('dbserver'):
                        output = host.dbhost.FIXED_INPUTS_ACK + '\n' + loopback_stdout(expected['loopback_endpoints']['required'])
                    else:
                        output = self.output([7001])
                    if label == tampered:
                        output = output + self.output([7001]) if label.endswith('dbserver') else output.replace('port=7001', 'port=7002')
                    path = source / (label + '-stdout.txt')
                    path.write_text(output)
                    files[path.name] = {'bytes': path.stat().st_size, 'sha256': host.digest(path),
                        'kind': 'owned_service_stdout', 'process_label': label,
                        'original_bytes': path.stat().st_size, 'truncated': False,
                        'capture_closed': True, 'overflow': False}
                (source / 'manifest.json').write_text(json.dumps({'format': 1, 'files': files,
                    'selected_log_limit': 32, 'log_segment_bytes': 512 * 1024, 'unselected_logs': 0}))
                records = host.copy_service_captures(state, evidence)
                report['game']['service_capture_files'] = records
                if tampered:
                    with self.assertRaises(RuntimeError):
                        host.validate_service_captures(report, evidence, records, expected=expected)
                else:
                    host.validate_service_captures(report, evidence, records, expected=expected)

    def test_resealed_raw_client_console_must_match_final_identity_bound_session(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / 'state', root / 'evidence'
            source = state / 'game-captures'
            source.mkdir(parents=True)
            evidence.mkdir()
            report, expected = self.sample()
            game = report['game']
            identity = {'containerid': 42, 'authid': 12, 'authname': game['account'], 'name': 'Hero'}
            rows = {table: [{'containerid': 42, 'subid': n} for n in range(count)]
                    for table, count in game['first_save']['row_counts'].items()}
            rows['ents'] = [{**identity, 'influencepoints': 12345}]
            for prefix, proof in (('first', game['first_save']), ('restart', game['restart']), ('second', game['second_save'])):
                snapshot = {'identity': identity, 'login_count': 2 if prefix == 'second' else 1, 'rows': rows}
                (source / (prefix + '-snapshot.json')).write_text(json.dumps(snapshot))
                proof['snapshot_sha256'] = host.canonical_digest(snapshot)
            for prefix, session in game['sessions'].items():
                for name in ('ready', 'result'):
                    (source / (prefix + '-' + name + '.json')).write_text(json.dumps(session[name]))
                for name, text, key in (('console.txt', self.output([41001, 41002]), 'console_sha256'),
                                        ('events.jsonl', '{}\n', 'events_sha256')):
                    path = source / (prefix + '-' + name)
                    path.write_text(text)
                    session[key] = host.digest(path)
            records = host.copy_game_captures(state, evidence)
            game['capture_files'] = records
            host.validate_capture_files(report, evidence, records, expected=expected)
            for prefix in ('first', 'second'):
                path = evidence / 'game-captures' / (prefix + '-console.txt')
                path.write_text(self.output([41001, 41999]))
                records[path.name] = {'bytes': path.stat().st_size, 'sha256': host.digest(path)}
                game['sessions'][prefix]['console_sha256'] = host.digest(path)
                with self.subTest(prefix=prefix), self.assertRaisesRegex(RuntimeError, 'actual bindings differ'):
                    host.validate_capture_files(report, evidence, records, expected=expected)
                path.write_text(self.output([41001, 41002]))
                records[path.name] = {'bytes': path.stat().st_size, 'sha256': host.digest(path)}
                game['sessions'][prefix]['console_sha256'] = host.digest(path)


class LoopbackTests(unittest.TestCase):
    def test_combined_report_requires_both_starts_and_cannot_downgrade_the_profile(self):
        report, expected = ReportTests().sample()
        loopback_sample(report['game'], expected)
        host.validate_report(report, expected=expected)
        mutations = [lambda g: g.pop('dbserver_profile'),
                     lambda g: g.update(dbserver_profile='accepted'),
                     lambda g: g['loopback_only'].update(requested=1),
                     lambda g: g['loopback_only']['metadata'].update(android_execution_validated=True),
                     lambda g: g['phases'][0].pop('loopback_only'),
                     lambda g: g['phases'][1]['loopback_only'].update(requested=1),
                     lambda g: g['phases'][1]['loopback_only'].update(startup_acknowledgement='missing'),
                     lambda g: g['phases'][1]['loopback_only']['endpoints'].pop(),
                     lambda g: g['phases'][1]['loopback_only']['endpoints'][0].update(address='0.0.0.0'),
                     lambda g: g['phases'][1]['loopback_only']['endpoints'][0].update(port=True)]
        for number, mutate in enumerate(mutations):
            with self.subTest(mutation=number):
                changed = copy.deepcopy(report)
                mutate(changed['game'])
                with self.assertRaises(RuntimeError):
                    host.validate_report(changed, expected=expected)
        accepted_expected = ReportTests().sample()[1]
        with self.assertRaisesRegex(RuntimeError, 'unexpectedly claims'):
            host.validate_report(report, expected=accepted_expected)

    def test_final_stdout_requires_exact_ack_and_complete_source_derived_bind_set(self):
        report, expected = ReportTests().sample()
        endpoints = loopback_sample(report['game'], expected)
        good = loopback_stdout(endpoints['required'])
        host.parse_loopback_output(good, endpoints)
        with_optional = loopback_stdout(endpoints['required'] + endpoints['optional'])
        self.assertEqual(len(host.parse_loopback_output(with_optional, endpoints)['endpoints']), 14)
        failures = [good.replace(host.dbhost.LOOPBACK_ACK + '\n', ''),
                    good + host.dbhost.LOOPBACK_ACK + '\n',
                    good + good.splitlines()[1] + '\n',
                    loopback_stdout(endpoints['required'][:-1]),
                    good.replace('127.0.0.1', '0.0.0.0'),
                    good.replace('port=6971', 'port=7002'),
                    good.replace('port=6971', 'port=69710'),
                    good.replace('protocol=tcp', 'protocol=unknown', 1)]
        for number, output in enumerate(failures):
            with self.subTest(mutation=number), self.assertRaises(RuntimeError):
                host.parse_loopback_output(output, endpoints)

    def test_resealed_raw_service_captures_cannot_hide_missing_or_mis_scoped_bind_proof(self):
        report, expected = ReportTests().sample()
        endpoints = loopback_sample(report['game'], expected)
        required = loopback_stdout(endpoints['required'])
        later = loopback_stdout(endpoints['required'] + endpoints['optional'])
        cases = [(None, None, False),
                 ('first-dbserver', later, False),
                 ('restart-dbserver', later, False),
                 ('first-dbserver', '', True),
                 ('restart-dbserver', loopback_stdout(endpoints['required'][:-1]), True),
                 ('restart-dbserver', required.replace('127.0.0.1', '0.0.0.0'), True),
                 ('restart-dbserver', required + required.splitlines()[1] + '\n', True),
                 ('first-atlas', required, True)]
        for label, changed, fails in cases:
            with self.subTest(label=label, changed=changed), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                state, evidence = root / 'state', root / 'evidence'
                source = state / 'game-service-captures'
                source.mkdir(parents=True)
                evidence.mkdir()
                files = {}
                for service in host.SERVICE_LABELS:
                    output = required if service.endswith('-dbserver') else ''
                    if service == label:
                        output = changed
                    if service.endswith('-dbserver'):
                        output = host.dbhost.FIXED_INPUTS_ACK + '\n' + output
                    path = source / (service + '-stdout.txt')
                    path.write_text('owned process output\n' + output)
                    files[path.name] = {'bytes': path.stat().st_size, 'sha256': host.digest(path),
                        'kind': 'owned_service_stdout', 'process_label': service,
                        'original_bytes': path.stat().st_size, 'truncated': False,
                        'capture_closed': True, 'overflow': False}
                (source / 'manifest.json').write_text(json.dumps({'format': 1, 'files': files,
                    'selected_log_limit': 32, 'log_segment_bytes': 512 * 1024, 'unselected_logs': 0}))
                records = host.copy_service_captures(state, evidence)
                report['game']['service_capture_files'] = records
                if fails:
                    with self.assertRaises(RuntimeError):
                        host.validate_service_captures(report, evidence, records, expected=expected)
                else:
                    host.validate_service_captures(report, evidence, records, expected=expected)
                    with self.assertRaises(RuntimeError):
                        host.validate_service_captures(report, evidence, records)


class CaptureTests(unittest.TestCase):
    def test_service_exports_require_all_owned_stdout_and_matching_safe_log_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / 'state', root / 'evidence'
            source = state / 'game-service-captures'
            source.mkdir(parents=True)
            evidence.mkdir()
            files = {}
            for label in host.SERVICE_LABELS:
                path = source / (label + '-stdout.txt')
                path.write_text('service diagnostic\n' + (host.dbhost.FIXED_INPUTS_ACK + '\n' if label.endswith('-dbserver') else ''))
                files[path.name] = {'bytes': path.stat().st_size, 'sha256': host.digest(path),
                    'kind': 'owned_service_stdout', 'process_label': label, 'original_bytes': path.stat().st_size,
                    'truncated': False, 'capture_closed': True, 'overflow': False}
            path = source / 'log-001.txt'
            path.write_text('bounded beginning\n[middle omitted]\nbounded end\n')
            files[path.name] = {'bytes': path.stat().st_size, 'sha256': host.digest(path),
                'kind': 'runtime_log', 'source_relative_path': 'logs/mapserver/error.log',
                'original_bytes': 2 * 1024 * 1024, 'truncated': True}
            manifest = {'format': 1, 'files': files, 'selected_log_limit': 32,
                        'log_segment_bytes': 512 * 1024, 'unselected_logs': 3}
            (source / 'manifest.json').write_text(json.dumps(manifest))
            records = host.copy_service_captures(state, evidence)
            report = {'game': {'service_capture_files': records}}
            host.validate_service_captures(report, evidence, records)
            mutations = [lambda m: m['files']['first-atlas-stdout.txt'].update(capture_closed=False),
                         lambda m: m['files']['first-atlas-stdout.txt'].update(overflow=True),
                         lambda m: m['files']['first-atlas-stdout.txt'].update(process_label='other-atlas'),
                         lambda m: m['files']['log-001.txt'].update(source_relative_path='../private.log'),
                         lambda m: m['files']['log-001.txt'].update(source_relative_path='data/private.log'),
                         lambda m: m['files']['log-001.txt'].update(truncated=False),
                         lambda m: m['files']['log-001.txt'].update(sha256='0'*64),
                         lambda m: m.update(inspection_failure='unreadable log')]
            for index, mutate in enumerate(mutations):
                with self.subTest(case=index):
                    changed = copy.deepcopy(manifest)
                    mutate(changed)
                    path = evidence / 'game-service-captures/manifest.json'
                    path.write_text(json.dumps(changed))
                    records['manifest.json'] = {'bytes': path.stat().st_size, 'sha256': host.digest(path)}
                    with self.assertRaises(RuntimeError):
                        host.validate_service_captures(report, evidence, records)

            # Rehashing both capture and manifest cannot make missing, altered,
            # duplicated or wrongly scoped activation output into valid proof.
            for label, text in (('first-dbserver', 'missing\n'),
                                ('restart-dbserver', host.dbhost.FIXED_INPUTS_ACK + '.\n'),
                                ('first-dbserver', (host.dbhost.FIXED_INPUTS_ACK + '\n') * 2),
                                ('restart-atlas', host.dbhost.FIXED_INPUTS_ACK + '\n')):
                with self.subTest(label=label, text=text):
                    changed = copy.deepcopy(manifest)
                    path = evidence / 'game-service-captures' / (label + '-stdout.txt')
                    original = path.read_text()
                    path.write_text(text)
                    record = {'bytes': path.stat().st_size, 'sha256': host.digest(path)}
                    changed['files'][path.name].update(record, original_bytes=record['bytes'])
                    original_record = records[path.name]
                    records[path.name] = record
                    manifest_path = path.parent / 'manifest.json'
                    manifest_path.write_text(json.dumps(changed))
                    records['manifest.json'] = {'bytes': manifest_path.stat().st_size, 'sha256': host.digest(manifest_path)}
                    with self.assertRaisesRegex(RuntimeError, 'acknowledgement differs'):
                        host.validate_service_captures(report, evidence, records)
                    path.write_text(original)
                    records[path.name] = original_record

    def test_partial_service_startup_failure_is_exported_without_claiming_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / 'state', root / 'evidence'
            source = state / 'game-service-captures'
            source.mkdir(parents=True)
            evidence.mkdir()
            (source / 'first-atlas-stdout.txt').write_text('stopped while loading definitions\n')
            records = host.copy_service_captures(state, evidence)
            self.assertEqual(set(records), {'first-atlas-stdout.txt'})
            self.assertEqual((evidence / 'game-service-captures/first-atlas-stdout.txt').read_text(),
                             'stopped while loading definitions\n')
            with self.assertRaisesRegex(RuntimeError, 'service capture inventory'):
                host.validate_service_captures({'game': {'service_capture_files': records}}, evidence, records)

    def test_service_export_refuses_unlisted_private_file_and_oversized_capture(self):
        for filename, size in (('credentials.json', 1), ('log-033.txt', 1), ('manifest.json', 128*1024+1)):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / 'state/game-service-captures').mkdir(parents=True)
                (root / 'evidence').mkdir()
                (root / 'state/game-service-captures' / filename).write_bytes(b'x'*size)
                with self.assertRaises(RuntimeError):
                    host.copy_service_captures(root / 'state', root / 'evidence')
                self.assertFalse((root / 'evidence/game-service-captures').exists())

    def test_capture_hashes_and_sql_rows_bind_both_saves_and_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / "state", root / "evidence"
            source = state / "game-captures"
            source.mkdir(parents=True)
            evidence.mkdir()
            report, _ = ReportTests().sample()
            game = report["game"]
            identity = {"containerid": 42, "authid": 12, "authname": game["account"], "name": "Hero"}
            rows = {table: [{"containerid": 42, "subid": n} for n in range(count)]
                    for table, count in game["first_save"]["row_counts"].items()}
            rows["ents"] = [{**identity, "influencepoints": 12345}]
            first = {"identity": identity, "login_count": 1, "rows": rows}
            for prefix, proof in (("first", game["first_save"]), ("restart", game["restart"]), ("second", game["second_save"])):
                snapshot = {**first, "login_count": 2 if prefix == "second" else 1}
                (source / (prefix + "-snapshot.json")).write_text(json.dumps(snapshot, sort_keys=True, separators=(',', ':')) + '\n')
                proof["snapshot_sha256"] = host.canonical_digest(snapshot)
            for prefix in ("first", "second"):
                session = game["sessions"][prefix]
                for name in ("ready", "result"):
                    (source / (prefix + "-" + name + ".json")).write_text(json.dumps(session[name]))
                for name, value in (("console.txt", b"diagnostic console\n"), ("events.jsonl", b'{}\n')):
                    (source / (prefix + "-" + name)).write_bytes(value)
                    key = "console_sha256" if name == "console.txt" else "events_sha256"
                    session[key] = host.hashlib.sha256(value).hexdigest()
            records = host.copy_game_captures(state, evidence)
            game["capture_files"] = records
            host.validate_capture_files(report, evidence, records)
            path = evidence / "game-captures/second-snapshot.json"
            changed = json.loads(path.read_text())
            changed["rows"]["powers"][0]["subid"] = 900
            path.write_text(json.dumps(changed))
            game["second_save"]["snapshot_sha256"] = host.canonical_digest(changed)
            records[path.name] = {"bytes": path.stat().st_size, "sha256": host.digest(path)}
            with self.assertRaisesRegex(RuntimeError, "Second logout changed"):
                host.validate_capture_files(report, evidence, records)

    def test_partial_failure_captures_are_copied_with_exact_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / "state", root / "evidence"
            (state / "game-captures").mkdir(parents=True)
            evidence.mkdir()
            payload = b'Partial diagnostic console\n'
            (state / "game-captures/first-console.txt").write_bytes(payload)
            records = host.copy_game_captures(state, evidence)
            self.assertEqual((evidence / "game-captures/first-console.txt").read_bytes(), payload)
            self.assertEqual(records, {"first-console.txt": {"bytes": len(payload), "sha256": host.hashlib.sha256(payload).hexdigest()}})
            self.assertEqual(json.loads((evidence / "game-captures.json").read_text())["files"], records)

    def test_capture_export_refuses_private_names_links_and_excess(self):
        for mode in ("private", "link", "oversized"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                state, evidence = root / "state", root / "evidence"
                (state / "game-captures").mkdir(parents=True)
                evidence.mkdir()
                path = state / "game-captures" / ("credentials.json" if mode == "private" else "first-ready.json")
                if mode == "link":
                    (root / "private").write_text('private')
                    path.symlink_to(root / "private")
                else:
                    path.write_bytes(b'x' * (16385 if mode == "oversized" else 1))
                with self.assertRaises(RuntimeError):
                    host.copy_game_captures(state, evidence)
                self.assertFalse((evidence / "game-captures").exists())


if __name__ == "__main__":
    unittest.main()
