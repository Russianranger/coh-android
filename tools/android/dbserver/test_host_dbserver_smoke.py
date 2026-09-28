"""Negative acceptance and input-isolation checks for the hosted real-DbServer gate."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import host_dbserver_smoke as host
import run_isolated_network as network


class InputInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def file(self, name, data=b"input"):
        path = self.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"bytes": len(data), "sha256": host.digest(path)}

    def test_inventory_rejects_modified_or_unlisted_payload(self):
        files = {"data/schema.template": self.file("data/schema.template")}
        host.verify_inventory(self.directory, files)
        (self.directory / "data/schema.template").write_bytes(b"other")
        with self.assertRaisesRegex(RuntimeError, "hash/size"):
            host.verify_inventory(self.directory, files)
        self.file("extra.exe")
        with self.assertRaisesRegex(RuntimeError, "differs"):
            host.verify_inventory(self.directory, files)

    def test_inventory_rejects_symlink_payload(self):
        record = self.file("target")
        (self.directory / "alias").symlink_to(self.directory / "target")
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            host.verify_inventory(self.directory, {"target": record, "alias": record})

    def test_package_requires_both_build_modes_and_exact_dependencies(self):
        variants = {}
        for name, enabled in (("fixture", True), ("normal", False)):
            variants[name] = {"postgresql_persistence_fixture": enabled,
                              "files": {"DbServer.exe": self.file(name + "/DbServer.exe", name.encode())}}
        manifest = {"format": 1, "source_commit": host.SOURCE_COMMIT,
                    "android_execution_validated": False, "gameplay_validated": False,
                    "variants": variants}
        path = self.directory / "package-manifest.json"
        path.write_text(json.dumps(manifest))
        host.verify_package(self.directory)
        manifest["variants"]["normal"]["postgresql_persistence_fixture"] = True
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError, "build flag"):
            host.verify_package(self.directory)
        manifest["variants"]["normal"]["postgresql_persistence_fixture"] = False
        path.write_text(json.dumps(manifest))
        self.file("normal/unrecorded.dll")
        with self.assertRaisesRegex(RuntimeError, "differs"):
            host.verify_package(self.directory)

    def test_unpinned_runtime_manifest_is_rejected_before_running_anything(self):
        self.file("runtime-manifest.json", b'{"format":1}')
        with self.assertRaisesRegex(RuntimeError, "exact accepted"):
            host.verify_runtime_assets(self.directory)


class NetworkIsolationTests(unittest.TestCase):
    def expected(self):
        return {"host_network_namespace": "net:[100]", "original_uid": 1001, "original_gid": 1001}

    def receipt(self):
        return {"format": 1, "scope": "isolated_loopback_only_host_network", **self.expected(),
                "guest_network_namespace": "net:[200]", "effective_uid": 1001, "effective_gid": 1001,
                "distinct_network_namespace": True, "interfaces": ["lo"], "loopback_up": True,
                "external_network_disabled": True, "guest_runs_as_root": False}

    def test_receipt_requires_distinct_namespace_loopback_only_and_original_identity(self):
        host.validate_network_receipt(self.receipt(), self.expected())
        for field, value in (("guest_network_namespace", "net:[100]"), ("interfaces", ["lo", "eth0"]),
                             ("effective_uid", 0), ("effective_uid", True), ("original_uid", 1002),
                             ("effective_gid", 1002), ("loopback_up", False),
                             ("external_network_disabled", False), ("guest_runs_as_root", True)):
            with self.subTest(field=field, value=value):
                receipt = self.receipt()
                receipt[field] = value
                with self.assertRaises(RuntimeError):
                    host.validate_network_receipt(receipt, self.expected())

    def test_child_environment_does_not_forward_host_tokens(self):
        with mock.patch.dict(host.os.environ, {"GH_TOKEN": "private", "GITHUB_TOKEN": "private", "HOME": "/home/runner"}):
            environment = network.clean_environment(Path("/owned/proot-loader"), Path("/owned/tmp"))
        self.assertEqual(set(environment), {"PATH", "LANG", "TZ", "PYTHONDONTWRITEBYTECODE",
                                           "PROOT_LOADER", "PROOT_TMP_DIR", "PROOT_NO_SECCOMP"})
        self.assertNotIn("private", environment.values())

    def test_controlled_hosts_resolves_localhost_and_kernel_names_to_loopback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            work, evidence = root / "work", root / "evidence"
            work.mkdir()
            evidence.mkdir()
            receipt = host.prepare_guest_hosts(work, evidence, "runner-123.example.test")
            contents = (work / "hosts").read_bytes()
            records = [line.split() for line in contents.decode("ascii").splitlines()]
            self.assertEqual({record[0] for record in records}, {"127.0.0.1"})
            self.assertEqual({alias for record in records for alias in record[1:]},
                             {"localhost", "runner-123.example.test", "runner-123"})
            self.assertEqual((evidence / receipt["guest_hosts_evidence_file"]).read_bytes(), contents)
            self.assertEqual(receipt["guest_hosts_sha256"], host.hashlib.sha256(contents).hexdigest())
            self.assertEqual(receipt["guest_hosts_bytes"], len(contents))
            self.assertEqual(receipt["kernel_hostname"], "runner-123.example.test")

    def test_controlled_hosts_rejects_injected_or_invalid_hostname(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for hostname in ("", "runner\n203.0.113.1 attacker", "runner attacker", "runner#comment",
                             "runner..test", "-runner", "runner-", "a" * 64, "éxample"):
                with self.subTest(hostname=hostname), self.assertRaisesRegex(RuntimeError, "safe hosts-file"):
                    host.prepare_guest_hosts(root, root, hostname)
            self.assertFalse((root / "hosts").exists())

    def test_wrapper_always_unshares_and_requires_non_root_runner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(host.os, "getuid", return_value=1001), mock.patch.object(
                    host.os, "geteuid", return_value=1001), mock.patch.object(
                    host.os, "getgid", return_value=1001), mock.patch.object(
                    host.os, "readlink", return_value="net:[100]"):
                command, environment, expected = host.isolate_command(
                    ["/owned/proot", "-r", "/owned/rootfs"], evidence=root, proot=root, work=root)
            self.assertEqual(command[:6], ["sudo", "-n", "unshare", "--net", "--", sys.executable])
            self.assertEqual(command[-3:], ["/owned/proot", "-r", "/owned/rootfs"])
            self.assertNotIn("-E", command)
            self.assertNotIn("GH_TOKEN", environment)
            self.assertEqual(expected["original_uid"], 1001)
            with mock.patch.object(host.os, "getuid", return_value=0), mock.patch.object(
                    host.os, "geteuid", return_value=0), self.assertRaisesRegex(RuntimeError, "non-root"):
                host.isolate_command(["/owned/proot"], evidence=root, proot=root, work=root)


class RunnerCommandTests(unittest.TestCase):
    def test_new_guest_and_packages_have_separate_binds_from_accepted_m2(self):
        root = Path("/owned")
        command = host.make_command(work=root / "work", assets=root / "m2", package=root / "package",
                                    schema=root / "schema", proot=root / "proot", timeout_seconds=1800)
        self.assertIn("/owned/m2:/opt/coh", command)
        self.assertIn("/owned/work/m3-tools:/opt/coh-m3", command)
        self.assertIn("/owned/package:/opt/coh-dbserver", command)
        self.assertIn("/owned/schema:/opt/coh-schema", command)
        self.assertIn("/owned/work/hosts:/etc/hosts", command)
        self.assertNotIn("/etc/hosts:/etc/hosts", command)
        self.assertIn("/opt/coh-m3/dbserver_diagnostic.py", command)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", command)
        self.assertEqual(command[-2:], ["--timeout-seconds", "1800"])

    def test_zero_exit_without_new_report_cannot_reuse_previous_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / "state", root / "evidence"
            state.mkdir()
            evidence.mkdir()
            (state / "latest-report.json").write_text('{"passed":true}')
            (evidence / "dbserver-runtime-report.json").write_text('{"passed":true}')
            with self.assertRaisesRegex(RuntimeError, "fresh report"):
                host.run_guest([sys.executable, "-c", "pass"], {}, state, evidence,
                               timeout_seconds=1, expected={})
            self.assertFalse((state / "latest-report.json").exists())
            self.assertFalse((evidence / "dbserver-runtime-report.json").exists())


class ReportAcceptanceTests(unittest.TestCase):
    def expected(self):
        inputs = {name: "a" * 64 for name in ("runtime_manifest_sha256", "package_manifest_sha256",
                  "schema_manifest_sha256", "fixture_executable_sha256", "normal_executable_sha256")}
        inputs.update(repository_commit="b" * 40, source_commit=host.SOURCE_COMMIT, data_commit=host.DATA_COMMIT)
        schema = host.schema_expectations({"expected_tables": {"attributes": ["id", "name"]},
                                            "expected_attributes": {"attributes": [{"id": 1, "name": "hero"}]}})
        return {"inputs": inputs, "schema": schema, "runtime_lock_sha256": "c" * 64}

    def sample(self):
        expected = self.expected()
        phases = []
        for mode, code in zip(host.FIXTURE_MODES, host.FIXTURE_EXIT_CODES):
            marker = ("PG_TEST_COMPLETE " + mode) if code == 0 else (
                "PG_FIFO_FAILED expected refusal" if code == 3 else "PG_TEST_FATAL expected refusal")
            phases.append({"mode": mode, "exit_code": code, "expected_exit_code": code,
                           "markers": [marker], "output_sha256": "d" * 64})
        for index, label in ((6, "clean_postgres_restart"), (7, "postgres_wal_recovery"), (13, "backup_restore")):
            phases[index]["evidence"] = label
        stages = [{"stage": name, "status": "passed"} for name in host.STAGES]
        stages[1]["cluster_reused"] = False
        normal_phases = [{"number": number, "exit_code": 0, "failure_diagnostic_lines": [],
                          "export_bytes": 0, "export_sha256": host.hashlib.sha256(b"").hexdigest(),
                          "input_manifest_sha256": expected["inputs"]["schema_manifest_sha256"],
                          **copy.deepcopy(expected["schema"]),
                          "catalog_sha256": {name: "e" * 64 for name in ("columns", "indexes", "constraints")}}
                         for number in (1, 2)]
        return {"passed": True, "status": "passed", "failures": [], "cleanup_complete": True,
                "diagnostic_mode": host.DIAGNOSTIC_MODE, "execution_platform_requested": "host",
                "android_execution_validated": False, "gameplay_validated": False,
                "generated_character_persistence_validated": False, "android_listener_binding_validated": False,
                "cleanup": {name: True for name in ("postgres_graceful", "wine_prefix_stopped", "owned_processes_reaped")},
                "wine_process_cleanup": {"complete": True, "remaining": 0, "inspection_failures": 0},
                "processes": [{"exit_code": 0, "input_closed": True, "output_capture_closed": True}],
                "inputs": copy.deepcopy(expected["inputs"]), "stages": stages,
                "wine_initialization": {"policy": "initialize_once_then_reuse", "state": "ready",
                                        "ready_prefix_reused": False, "runtime_lock_sha256": "c" * 64,
                                        "registration_processes": 3, "wow64_registration_processes": 1,
                                        "registration_passes": 1},
                "fixture": {"status": "passed", "check_count": 21, "checks": list(host.FIXTURE_CHECKS), "phases": phases},
                "generated_schema": {"status": "passed", "fixture_enabled": False,
                                     "reload_stable": True, "phases": normal_phases}}

    def test_complete_report_is_accepted(self):
        host.validate_report(self.sample(), expected=self.expected())

    def test_partial_cleanup_false_scope_and_input_substitution_are_rejected(self):
        mutations = [lambda r: r.update(passed=False),
                     lambda r: r.update(android_execution_validated=True),
                     lambda r: r.update(generated_character_persistence_validated=True),
                     lambda r: r["cleanup"].update(owned_processes_reaped=False),
                     lambda r: r["wine_process_cleanup"].update(remaining=1),
                     lambda r: r["wine_process_cleanup"].update(inspection_failures=1),
                     lambda r: r["processes"][0].update(output_capture_closed=False),
                     lambda r: r["processes"][0].update(input_closed=False),
                     lambda r: r["inputs"].update(normal_executable_sha256="f" * 64),
                     lambda r: r["stages"].pop(),
                     lambda r: r["stages"][1].update(cluster_reused=True),
                     lambda r: r["wine_initialization"].update(registration_passes=2)]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                report = self.sample()
                mutate(report)
                with self.assertRaises(RuntimeError):
                    host.validate_report(report, expected=self.expected())

    def test_fixture_cannot_omit_refusal_phase_or_durable_reload(self):
        mutations = [lambda r: r["fixture"].update(check_count=20),
                     lambda r: r["fixture"]["checks"].pop(),
                     lambda r: r["fixture"]["phases"].pop(),
                     lambda r: r["fixture"]["phases"][1].update(exit_code=0, expected_exit_code=0),
                     lambda r: r["fixture"]["phases"][1].update(markers=["PG_TEST_COMPLETE fail"]),
                     lambda r: r["fixture"]["phases"][0].update(markers=["PG_TEST_COMPLETE initial", "PG_TEST_FAILED x"]),
                     lambda r: r["fixture"]["phases"][13].update(evidence="new_process_only")]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                report = self.sample()
                mutate(report)
                with self.assertRaises(RuntimeError):
                    host.validate_report(report, expected=self.expected())

    def test_normal_schema_requires_exact_input_and_stable_full_catalog(self):
        mutations = [lambda r: r["generated_schema"].update(fixture_enabled=True),
                     lambda r: r["generated_schema"]["phases"].pop(),
                     lambda r: r["generated_schema"]["phases"][1].update(export_bytes=1),
                     lambda r: r["generated_schema"]["phases"][0].update(failure_diagnostic_lines=["SQLERROR"]),
                     lambda r: r["generated_schema"]["phases"][0].update(input_manifest_sha256="f" * 64),
                     lambda r: r["generated_schema"]["phases"][1]["catalog_sha256"].update(indexes="f" * 64),
                     lambda r: r["generated_schema"]["phases"][1].update(ordered_columns_sha256="f" * 64),
                     lambda r: r["generated_schema"]["phases"][1]["attribute_sha256"].update(attributes="f" * 64)]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                report = self.sample()
                mutate(report)
                with self.assertRaises(RuntimeError):
                    host.validate_report(report, expected=self.expected())


if __name__ == "__main__":
    unittest.main()
