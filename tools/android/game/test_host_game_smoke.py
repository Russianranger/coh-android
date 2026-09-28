"""Fail-closed input, execution and report tests for the hosted game gate."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import host_game_smoke as host


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
    def sample(self):
        paths = {"reference": "docs/reference-runtime-evidence/build-36088012664.json",
                 "dbserver": "docs/android-evidence/dbserver-package-36369485666.json",
                 "resume": "docs/postgresql-evidence/resume-testclient-build-36297542986.json"}
        proofs = {role: {**{key: pin[key] for key in ("run_id", "repository_commit", "manifest_sha256")},
                         "manifest": json.loads((host.ROOT / paths[role]).read_text())}
                  for role, pin in host.DONORS.items()}
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
        return {"format": 1, "role": "wine_game_runtime", "source_commit": host.dbhost.SOURCE_COMMIT,
                "data_commit": host.dbhost.DATA_COMMIT, "repository_commit": "f" * 40,
                "client_version": "coh-persistence-diagnostic", "postgresql_persistence_fixture": False,
                "runtime_execution_validated": False, "inputs": proofs, "files": files,
                "file_donors": {name: role for name, (_, role) in selected.items()},
                "dependency_report": host.dependency_report(files)}

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


class ReportTests(unittest.TestCase):
    def sample(self):
        expected = {"inputs": {"game_package_sha256": "a" * 64}, "schema": {
            "table_count": 99, "column_count": 5935, "attribute_counts": {"attributes": 56411},
            "attribute_sha256": {"attributes": "a" * 64}, "ordered_columns_sha256": "b" * 64},
            "runtime_lock_sha256": "c" * 64}
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
                  "pipe_disconnected": True, "child_exited": True,
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
                "process_budget": 240, "query_budget": 80, "query_processes": 20, "readiness_queries": 4,
                "phases": [{"phase": name + "_services_ready", "status": "passed", "baseline_not_started": True,
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
                     lambda r: r["game"]["sessions"]["second"]["result"].update(child_exited=False),
                     lambda r: r["game"]["sessions"]["second"].update(proof_completed_before_stop=False)]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                report, expected = self.sample()
                expected = copy.deepcopy(expected)
                mutate(report)
                with self.assertRaises(RuntimeError):
                    host.validate_report(report, expected=expected)


class CaptureTests(unittest.TestCase):
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
