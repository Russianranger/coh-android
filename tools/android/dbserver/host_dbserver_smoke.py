#!/usr/bin/env python3
"""Qualify the real PE32 DbServer through the accepted M2 runtime on ARM64 Linux."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_assets import digest, fetch


ROOT = Path(__file__).resolve().parents[3]
ACCEPTED_RUNTIME_COMMIT = "9dc58f62c58dc4fc5c01288071429bf2aa06d2f4"
ACCEPTED_RUNTIME_MANIFEST = "fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203"
SOURCE_COMMIT = "0b75ade0c801735e10c5798f641948a45cc50488"
DATA_COMMIT = "d51533ec8e6a9cf726b9214968077a05fdcf19f3"
DIAGNOSTIC_MODE = "dbserver_persistence_and_generated_schema"
FIXTURE_MODES = ("initial", "fail", "exhaust", "delete-fail", "disconnect", "verify", "verify", "verify",
                 "rebuild", "verify-rebuilt", "rebuild-fail", "rebuild-fail-view", "verify-rebuilt", "verify-rebuilt")
FIXTURE_EXIT_CODES = (0, 3, 3, 3, 3, 0, 0, 0, 0, 0, 2, 2, 0, 0)
FIXTURE_CHECKS = (
    "real 64-worker SQL FIFO and container serialization",
    "foreign-key removal before table creation and when constraint is absent",
    "multi-batch create and update with 512 child rows", "ordered asynchronous read callback",
    "16 concurrent records and repeated same-record writes", "Unicode and unsigned byte 255",
    "case-insensitive game cache and SQL name lookup", "whole-save retry for 40001 and 40P01",
    "commit-time retry before acknowledgement", "atomic parent/child deletion",
    "permanent failure rolls back all save batches", "five-attempt retry limit without acknowledgement",
    "failed delete restores previously deleted child rows",
    "connection loss stops without replay or acknowledgement; in-flight write rolled back",
    "new-process container reload", "clean PostgreSQL restart", "WAL recovery of real saved containers",
    "real template reorder/add-column rebuild preserves high-water 9000",
    "inbound foreign keys and indexes survive table replacement",
    "failed data conversion and dependent-view rebuild preserve original table",
    "backup/restore reload through actual DbServer container reader")
STAGES = ("assets_and_architecture", "initialize_owned_cluster", "postgres_first_start",
          "restricted_fixture_database", "wine_prefix_and_driver", "win32_odbc_driver", "win32_runtime_dll",
          "dbserver_initial", "dbserver_fail", "dbserver_exhaust", "dbserver_delete_fail", "dbserver_disconnect",
          "dbserver_verify", "postgres_clean_restart_ready", "dbserver_verify", "postgres_immediate_restart",
          "postgres_wal_recovery_ready", "dbserver_verify", "dbserver_rebuild", "dbserver_verify_rebuilt",
          "dbserver_rebuild_fail", "dbserver_rebuild_fail_view", "dbserver_verify_rebuilt", "dbserver_backup_restore",
          "dbserver_verify_rebuilt", "restricted_fixture_database", "normal_dbserver_schema_1", "normal_dbserver_schema_2")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read_manifest(path):
    require(path.is_file() and not path.is_symlink(), "Missing or symlinked manifest: " + str(path))
    value = json.loads(path.read_text())
    require(isinstance(value, dict) and value.get("format") == 1,
            "Unsupported manifest: " + str(path))
    return value


def verify_inventory(directory, files, *, excluded=()):
    """Require the entire supplied tree to match its regular-file inventory."""
    require(isinstance(files, dict) and bool(files), "Empty or invalid input inventory")
    observed = set()
    for path in directory.rglob("*"):
        require(not path.is_symlink(), "Input inventory contains a symlink: " + str(path))
        if path.is_file():
            observed.add(path.relative_to(directory).as_posix())
        else:
            require(path.is_dir(), "Input inventory contains a special file: " + str(path))
    require(observed == set(files) | set(excluded), "Input tree differs from its inventory")
    for name, record in files.items():
        require(isinstance(name, str), "Invalid input inventory path type")
        relative = PurePosixPath(name)
        require(not relative.is_absolute()
                and relative.as_posix() == name and ".." not in relative.parts
                and "\\" not in name and bool(relative.parts), "Unsafe input inventory path")
        require(isinstance(record, dict) and type(record.get("bytes")) is int
                and record["bytes"] >= 0 and isinstance(record.get("sha256"), str),
                "Invalid input inventory record: " + name)
        path = directory / name
        require(path.stat().st_size == record["bytes"] and digest(path) == record["sha256"],
                "Input hash/size mismatch: " + name)


def verify_runtime_assets(assets):
    manifest_path = assets / "runtime-manifest.json"
    require(digest(manifest_path) == ACCEPTED_RUNTIME_MANIFEST,
            "M3 requires the exact accepted 0.1.5 runtime manifest")
    manifest = read_manifest(manifest_path)
    require(manifest.get("repository_commit") == ACCEPTED_RUNTIME_COMMIT,
            "Accepted M2 runtime source differs")
    require(len(manifest.get("files", {})) == 12, "Accepted M2 runtime inventory differs")
    verify_inventory(assets, manifest["files"], excluded=("runtime-manifest.json",))
    return manifest


def verify_package(package):
    manifest_path = package / "package-manifest.json"
    manifest = read_manifest(manifest_path)
    require(manifest.get("android_execution_validated") is False
            and manifest.get("gameplay_validated") is False,
            "Windows package cannot claim Android execution or gameplay")
    require(manifest.get("source_commit") == SOURCE_COMMIT,
            "DbServer package uses a different game source")
    variants = manifest.get("variants", {})
    require(set(variants) == {"fixture", "normal"}, "DbServer package needs both exact variants")
    require({path.name for path in package.iterdir()} == {"package-manifest.json", "fixture", "normal"},
            "Unexpected DbServer package entries")
    for name, enabled in (("fixture", True), ("normal", False)):
        record = variants[name]
        require(record.get("postgresql_persistence_fixture") is enabled,
                "DbServer fixture build flag differs: " + name)
        files = record.get("files", {})
        require("DbServer.exe" in files and all(len(PurePosixPath(item).parts) == 1 for item in files),
                "DbServer variant needs a flat executable/dependency inventory")
        require((package / name).is_dir() and not (package / name).is_symlink(),
                "Invalid DbServer variant directory")
        verify_inventory(package / name, files)
    return manifest


def verify_schema(schema):
    manifest_path = schema / "schema-manifest.json"
    manifest = read_manifest(manifest_path)
    require(manifest.get("scope") == "accepted_generated_schema_inputs"
            and manifest.get("acceptance_run_id") == 36088012666
            and manifest.get("source_commit") == SOURCE_COMMIT and manifest.get("data_commit") == DATA_COMMIT,
            "Schema inputs do not identify the accepted generation")
    require(manifest.get("android_execution_validated") is False and manifest.get("gameplay_validated") is False,
            "Generated schema inputs cannot claim Android execution or gameplay")
    verify_inventory(schema, manifest.get("files"), excluded=("schema-manifest.json",))
    require(isinstance(manifest.get("expected_tables"), dict) and manifest["expected_tables"]
            and isinstance(manifest.get("expected_attributes"), dict) and manifest["expected_attributes"],
            "Schema manifest lacks independent table/attribute expectations")
    require(manifest.get("generated_file_count") == 56 and manifest.get("supplemental_file_count") == 6
            and len(manifest["files"]) == 62 and len(manifest["expected_tables"]) == 99
            and sum(len(value) for value in manifest["expected_tables"].values()) == 5935
            and sum(len(value) for value in manifest["expected_attributes"].values()) == 58272,
            "Generated schema counts differ from the accepted gate")
    return manifest


def schema_expectations(manifest):
    tables, attributes = manifest["expected_tables"], manifest["expected_attributes"]
    ordered = "".join(table.encode().hex() + ":" + column.encode().hex() + "\n"
                      for table in sorted(tables) for column in tables[table])
    values = {table: hashlib.sha256("".join(str(row["id"]) + ":" + row["name"].encode().hex() + "\n"
                                             for row in sorted(rows, key=lambda row: row["id"])).encode()).hexdigest()
              for table, rows in attributes.items()}
    return {"table_count": len(tables), "column_count": sum(len(columns) for columns in tables.values()),
            "ordered_columns_sha256": hashlib.sha256(ordered.encode()).hexdigest(),
            "attribute_counts": {table: len(rows) for table, rows in attributes.items()}, "attribute_sha256": values}


def validate_report(report, *, expected):
    require(report.get("passed") is True and report.get("status") == "passed"
            and report.get("failures") == [] and report.get("cleanup_complete") is True,
            "DbServer runtime did not prove a complete successful result")
    require(report.get("diagnostic_mode") == DIAGNOSTIC_MODE
            and report.get("execution_platform_requested") == "host"
            and all(report.get(name) is False for name in ("android_execution_validated", "gameplay_validated",
                    "generated_character_persistence_validated", "android_listener_binding_validated")),
            "Hosted DbServer diagnostic mode or scope differs")
    require(all(report.get("cleanup", {}).get(name) is True for name in
                ("postgres_graceful", "wine_prefix_stopped", "owned_processes_reaped")),
            "DbServer runtime did not prove complete owned cleanup")
    ownership = report.get("wine_process_cleanup", {})
    require(ownership.get("complete") is True
            and type(ownership.get("remaining")) is int and ownership["remaining"] == 0
            and type(ownership.get("inspection_failures")) is int and ownership["inspection_failures"] == 0,
            "DbServer runtime has surviving or uninspected owned Wine processes")
    processes = report.get("processes", [])
    require(isinstance(processes, list) and bool(processes)
            and all(type(item.get("exit_code")) is int and item.get("input_closed") is True
                    and item.get("output_capture_closed") is True for item in processes),
            "DbServer runtime did not prove every input/output capture closed")
    inputs = report.get("inputs", {})
    require(all(inputs.get(name) == value for name, value in expected["inputs"].items()),
            "DbServer runtime input provenance differs from verified payloads")
    stages = report.get("stages", [])
    require(isinstance(stages, list) and tuple(stage.get("stage") for stage in stages) == STAGES
            and all(stage.get("status") == "passed" for stage in stages),
            "DbServer diagnostic stage coverage differs")
    require(stages[1].get("cluster_reused") is False, "DbServer host gate did not use a fresh cluster")
    wine = report.get("wine_initialization", {})
    require(wine.get("policy") == "initialize_once_then_reuse" and wine.get("state") == "ready"
            and wine.get("ready_prefix_reused") is False
            and wine.get("runtime_lock_sha256") == expected["runtime_lock_sha256"]
            and all(type(wine.get(name)) is int and wine[name] == count for name, count in
                    (("registration_processes", 3), ("wow64_registration_processes", 1), ("registration_passes", 1))),
            "DbServer runtime did not prove accepted cold Wine initialization")
    fixture = report.get("fixture", {})
    require(fixture.get("status") == "passed" and type(fixture.get("check_count")) is int
            and fixture["check_count"] == 21 and fixture.get("checks") == list(FIXTURE_CHECKS),
            "Real DbServer persistence fixture coverage differs")
    phases = fixture.get("phases", [])
    require(isinstance(phases, list) and len(phases) == len(FIXTURE_MODES),
            "Real DbServer persistence phase coverage differs")
    for phase, mode, code in zip(phases, FIXTURE_MODES, FIXTURE_EXIT_CODES):
        require(phase.get("mode") == mode and type(phase.get("exit_code")) is int
                and phase["exit_code"] == code and type(phase.get("expected_exit_code")) is int
                and phase["expected_exit_code"] == code,
                "Real DbServer phase did not prove its required exit status: " + mode)
        markers = phase.get("markers", [])
        require(isinstance(markers, list) and markers and all(isinstance(line, str) for line in markers)
                and not any("PG_TEST_FAILED" in line for line in markers)
                and bool(HEX64.fullmatch(phase.get("output_sha256", ""))),
                "Real DbServer phase lacks verified marker evidence: " + mode)
        complete = [line for line in markers if line.startswith("PG_TEST_COMPLETE ")]
        if code == 0:
            require(complete == ["PG_TEST_COMPLETE " + mode]
                    and not any("PG_TEST_FATAL" in line or "PG_FIFO_FAILED" in line for line in markers),
                    "Successful DbServer phase has contradictory markers: " + mode)
        else:
            marker = "PG_FIFO_FAILED" if code == 3 else "PG_TEST_FATAL"
            require(not complete and any(marker in line for line in markers),
                    "Expected DbServer failure lacks its refusal marker: " + mode)
    for index, evidence in ((6, "clean_postgres_restart"), (7, "postgres_wal_recovery"), (13, "backup_restore")):
        require(phases[index].get("evidence") == evidence, "DbServer durable-state phase evidence differs")
    generated = report.get("generated_schema", {})
    require(generated.get("status") == "passed" and generated.get("fixture_enabled") is False
            and generated.get("reload_stable") is True, "Normal DbServer generated-schema gate failed")
    normal_phases = generated.get("phases", [])
    require(isinstance(normal_phases, list) and len(normal_phases) == 2,
            "Normal DbServer did not prove both startup and reload")
    catalogs = []
    for number, phase in enumerate(normal_phases, 1):
        require(type(phase.get("number")) is int and phase["number"] == number
                and type(phase.get("exit_code")) is int and phase["exit_code"] == 0
                and phase.get("failure_diagnostic_lines") == []
                and type(phase.get("export_bytes")) is int and phase["export_bytes"] == 0
                and phase.get("export_sha256") == hashlib.sha256(b"").hexdigest()
                and phase.get("input_manifest_sha256") == expected["inputs"]["schema_manifest_sha256"],
                "Normal DbServer lacks a clean fresh export with the accepted schema")
        require(all(phase.get(name) == value for name, value in expected["schema"].items()),
                "Normal DbServer catalog/attributes differ from the accepted generated schema")
        catalog = phase.get("catalog_sha256", {})
        require(isinstance(catalog, dict) and set(catalog) == {"columns", "indexes", "constraints"}
                and all(isinstance(value, str) and HEX64.fullmatch(value) for value in catalog.values()),
                "Normal DbServer lacks full catalog fingerprints")
        catalogs.append(catalog)
    require(catalogs[0] == catalogs[1], "Normal DbServer reload changed its catalog")


def prepare_guest_hosts(work, evidence, hostname):
    """Resolve DbServer's localhost lookup without relying on external DNS."""
    require(isinstance(hostname, str) and 0 < len(hostname) <= 253
            and all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                    for label in hostname.split(".")),
            "Kernel hostname is not a safe hosts-file name")
    aliases = list(dict.fromkeys(("localhost", hostname, hostname.split(".")[0])))
    contents = ("127.0.0.1 " + " ".join(aliases) + "\n").encode("ascii")
    hosts = work / "hosts"
    hosts.write_bytes(contents)
    shutil.copyfile(hosts, evidence / "guest-etc-hosts")
    return {"kernel_hostname": hostname, "guest_hosts_sha256": digest(hosts),
            "guest_hosts_bytes": len(contents), "guest_hosts_loopback_aliases": aliases,
            "guest_hosts_evidence_file": "guest-etc-hosts"}


def make_command(*, work, assets, package, schema, proot, timeout_seconds):
    command = [str(proot / "proot"), "--link2symlink", "--kill-on-exit", "--sysvipc",
               "-i", "1000:1000", "-r", str(work / "rootfs")]
    binds = [("/dev", "/dev"), ("/proc", "/proc"), ("/sys", "/sys"),
             (work / "state", "/state"), (work / "tmp", "/tmp"),
             (assets, "/opt/coh"), (work / "pg/opt/coh/pgsql", "/opt/coh/pgsql"),
             (work / "wine", "/opt/wine"), (package, "/opt/coh-dbserver"),
             (schema, "/opt/coh-schema"), (work / "m3-tools", "/opt/coh-m3"),
             (work / "passwd", "/etc/passwd"), (work / "group", "/etc/group"),
             (work / "hosts", "/etc/hosts")]
    for source, destination in binds:
        command += ["-b", str(Path(source).resolve()) + ":" + destination]
    command += ["-w", "/state", "/usr/bin/env", "-i", "HOME=/state", "USER=coh", "LOGNAME=coh",
                "PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin", "LANG=C.UTF-8", "TZ=UTC",
                "TMPDIR=/tmp", "PYTHONUNBUFFERED=1", "PYTHONDONTWRITEBYTECODE=1",
                "/usr/bin/python3", "/opt/coh-m3/dbserver_diagnostic.py", "--state", "/state",
                "--assets", "/opt/coh", "--package", "/opt/coh-dbserver", "--schema", "/opt/coh-schema",
                "--pg-bin", "/opt/coh/pgsql/bin", "--wine", "/opt/wine/bin/wine",
                "--wineserver", "/opt/wine/bin/wineserver",
                "--timeout-seconds", str(timeout_seconds)]
    return command


def isolate_command(command, *, evidence, proot, work):
    uid, gid = os.getuid(), os.getgid()
    require(uid > 0 and os.geteuid() == uid, "Run the host gate as the original non-root runner")
    host_netns = os.readlink("/proc/self/ns/net")
    receipt = evidence / "network-isolation.json"
    receipt.unlink(missing_ok=True)
    isolated = ["sudo", "-n", "unshare", "--net", "--", sys.executable,
                str(Path(__file__).with_name("run_isolated_network.py").resolve()),
                "--uid", str(uid), "--gid", str(gid), "--host-netns", host_netns,
                "--receipt", str(receipt), "--proot-loader", str(proot / "proot-loader"),
                "--proot-tmp", str(work / "tmp"), "--", *command]
    # No GitHub credentials or broad sudo environment preservation enter the guest.
    environment = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                   "LANG": "C.UTF-8", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1"}
    return isolated, environment, {"host_network_namespace": host_netns,
                                   "original_uid": uid, "original_gid": gid}


def validate_network_receipt(report, expected):
    require(report.get("format") == 1 and report.get("scope") == "isolated_loopback_only_host_network",
            "Missing network isolation receipt")
    require(all(report.get(name) is True for name in
                ("distinct_network_namespace", "loopback_up", "external_network_disabled"))
            and report.get("guest_runs_as_root") is False and report.get("interfaces") == ["lo"],
            "DbServer runtime was not isolated to a private loopback interface")
    require(all(report.get(name) == value for name, value in expected.items())
            and type(report.get("effective_uid")) is int
            and report["effective_uid"] == expected["original_uid"] > 0
            and type(report.get("effective_gid")) is int
            and report["effective_gid"] == expected["original_gid"],
            "DbServer runtime did not retain the original non-root identity")
    require(isinstance(report.get("guest_network_namespace"), str)
            and report["guest_network_namespace"] != expected["host_network_namespace"],
            "DbServer runtime shared the host network namespace")


def stop_guest(process, state):
    (state / "stop-request").write_text("stop\n")
    try:
        process.wait(timeout=35)
        return "wrapper exited after the stop request"
    except subprocess.TimeoutExpired:
        pass
    # The pinned PRoot SIGQUIT handler terminates and drains its tracees,
    # including Wine helpers that detached from the original process group.
    process.send_signal(signal.SIGQUIT)
    try:
        process.wait(timeout=10)
        return "wrapper exited after SIGQUIT"
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        return "namespace wrapper was forcibly killed; descendant cleanup requires runner teardown"


def run_guest(command, env, state, evidence, *, timeout_seconds, expected):
    source_report = state / "latest-report.json"
    report_path = evidence / "dbserver-runtime-report.json"
    log_path = evidence / "host-dbserver.log"
    source_report.unlink(missing_ok=True)
    report_path.unlink(missing_ok=True)
    with log_path.open("w") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            code = process.wait(timeout=timeout_seconds + 90)
        except subprocess.TimeoutExpired:
            termination = stop_guest(process, state)
            raise RuntimeError("DbServer host runtime exceeded its bounded time; forced wrapper termination does not prove tracee cleanup; cleanup is unverified: " + termination)
        finally:
            if source_report.is_file():
                shutil.copyfile(source_report, report_path)
    try:
        require(code == 0, "DbServer PRoot runtime returned a failure exit status")
        require(report_path.is_file(), "DbServer runtime did not write a fresh report")
        report = json.loads(report_path.read_text())
        validate_report(report, expected=expected)
    except (RuntimeError, ValueError):
        print(log_path.read_text()[-24000:])
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ROOT / "out/android/assets/runtime")
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--work", type=Path, default=ROOT / "out/android/dbserver-host")
    parser.add_argument("--evidence", type=Path, default=ROOT / "out/android/dbserver-evidence")
    parser.add_argument("--proot", type=Path, default=ROOT / "out/android/native/linux-arm64")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--isolate-network", action="store_true", default=True,
                        help="Mandatory: use a private loopback-only namespace (always enabled)")
    args = parser.parse_args()
    require(sys.platform == "linux" and platform.machine().lower() in ("aarch64", "arm64"),
            "Native ARM64 Linux is required")
    require(os.getuid() > 0 and os.geteuid() == os.getuid(),
            "Run the host gate as the original non-root runner")
    require(60 <= args.timeout_seconds <= 3600, "Guest timeout must be between 60 and 3600 seconds")
    assets, package, schema, work, evidence, proot = (
        getattr(args, name).resolve() for name in ("assets", "package", "schema", "work", "evidence", "proot"))
    require(not work.exists(), "Use a fresh owned DbServer smoke directory")
    require(not evidence.exists(), "Use a fresh DbServer evidence directory")
    require(work != evidence, "Keep state and evidence in separate directories")
    runtime_manifest = verify_runtime_assets(assets)
    package_manifest = verify_package(package)
    schema_manifest = verify_schema(schema)
    repository_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(package_manifest.get("repository_commit") == repository_commit,
            "DbServer package was not built from the checked-out runner source")
    work.mkdir(parents=True, mode=0o700)
    evidence.mkdir(parents=True)
    lock = json.loads((assets / "runtime-lock.json").read_text())
    base = fetch(lock["base"], ROOT / "out/android/cache/base.tar.gz")
    wine = fetch(lock["wine"], ROOT / "out/android/cache/wine.tar.gz")
    subprocess.run([sys.executable, str(ROOT / "tools/android/test_archive.py"),
                    "--extract", str(base), str(work / "rootfs"),
                    "--extract", str(wine), str(work / "wine"),
                    "--extract", str(assets / "postgresql-runtime.tar.gz"), str(work / "pg")], check=True)
    require(digest(work / "wine/lsb-fex.json") == lock["wine"]["manifest_sha256"],
            "Wine source receipt mismatch")
    for name in ("state", "tmp", "m3-tools"):
        (work / name).mkdir(mode=0o700)
    (work / "passwd").write_text("root:x:0:0:root:/root:/bin/sh\ncoh:x:1000:1000:COH:/state:/bin/sh\nnobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n")
    (work / "group").write_text("root:x:0:\ncoh:x:1000:\nnogroup:x:65534:\n")
    hosts_input = prepare_guest_hosts(work, evidence, os.uname().nodename)
    for name in ("opt/coh", "opt/coh/pgsql", "opt/coh-dbserver", "opt/coh-schema", "opt/coh-m3", "opt/wine", "state", "tmp"):
        (work / "rootfs" / name).mkdir(parents=True, exist_ok=True)
    guest_script = work / "m3-tools/dbserver_diagnostic.py"
    shutil.copyfile(ROOT / "android/guest/dbserver_diagnostic.py", guest_script)
    for name in ("proot", "proot-loader"):
        require((proot / name).is_file() and not (proot / name).is_symlink(), "Missing native PRoot input")
        (proot / name).chmod(0o755)
    expected_inputs = {
        "runtime_manifest_sha256": digest(assets / "runtime-manifest.json"),
        "package_manifest_sha256": digest(package / "package-manifest.json"),
        "fixture_executable_sha256": package_manifest["variants"]["fixture"]["files"]["DbServer.exe"]["sha256"],
        "normal_executable_sha256": package_manifest["variants"]["normal"]["files"]["DbServer.exe"]["sha256"],
        "schema_manifest_sha256": digest(schema / "schema-manifest.json"),
        "repository_commit": repository_commit, "source_commit": SOURCE_COMMIT, "data_commit": DATA_COMMIT,
    }
    expected = {"inputs": expected_inputs, "schema": schema_expectations(schema_manifest),
                "runtime_lock_sha256": digest(assets / "runtime-lock.json")}
    inputs = {"format": 1, "scope": "host_dbserver_runtime_inputs", **expected_inputs, **hosts_input,
              "runtime_commit": runtime_manifest["repository_commit"],
              "package_commit": package_manifest["repository_commit"],
              "guest_script_sha256": digest(guest_script),
              "proot_sha256": digest(proot / "proot"),
              "proot_loader_sha256": digest(proot / "proot-loader"),
              "schema_acceptance_run_id": schema_manifest["acceptance_run_id"],
              "android_execution_validated": False, "gameplay_validated": False}
    (evidence / "host-dbserver-inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    command = make_command(work=work, assets=assets, package=package, schema=schema,
                           proot=proot, timeout_seconds=args.timeout_seconds)
    command, env, network_expected = isolate_command(command, evidence=evidence, proot=proot, work=work)
    report = run_guest(command, env, work / "state", evidence,
                       timeout_seconds=args.timeout_seconds, expected=expected)
    validate_network_receipt(read_manifest(evidence / "network-isolation.json"), network_expected)
    print(json.dumps({"status": "native_arm64_proot_dbserver_passed_android_unvalidated",
                      "report": str(evidence / "dbserver-runtime-report.json"),
                      "stages": len(report["stages"])}))


if __name__ == "__main__":
    main()
