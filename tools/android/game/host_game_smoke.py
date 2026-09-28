#!/usr/bin/env python3
"""Qualify managed Atlas and diagnostic TestClient on isolated ARM64 Wine/FEX."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dbserver"))
import host_dbserver_smoke as dbhost

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from package_reference_runtime import pe_info, dependency_report

require, digest = dbhost.require, dbhost.digest
MAX_MANIFEST_BYTES = 64 * 1024 * 1024
MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_DATA_FILES = 250000
MAX_DATA_BYTES = 4 * 1024**3
MIN_FREE_BYTES = 10 * 1024**3
DATA_FILE_COUNT = 173011
DATA_TOTAL_BYTES = 2977730517
ASSET_MANIFEST_SHA256 = "cf96742b1b65306356df69d065fcfb5bda0986ec8700d47ae1422452a1c0db7f"
ASSET_ARCHIVE_SHA256 = "28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07"
DONORS = {
    "reference": {"run_id": 36088012664, "repository_commit": "775a0dd770adac045484805dbbb5f68054c7a354",
                  "manifest_sha256": "a498eeb9c92299d44a748d08e720cd2e8aeacca0631129182a766ed00ff98952",
                  "canonical_sha256": "31f5553e093947e6ce8c67caa1ed375ce86bf870dc25a5ee2609149b4ae7b03a"},
    "dbserver": {"run_id": 36369485666, "repository_commit": "1a5eea159172a4698441eb8cfed5ea5ca99fcf12",
                 "manifest_sha256": "2dee0ef37aaaab5666c868393dfdba7bcfd1520b4aa1bffe9d565632cfd9327b",
                 "canonical_sha256": "4b9c2693988d1800b2eea7cfe98f4e9b376e1574601b64f27487a877df9494c6"},
    "resume": {"run_id": 36297542986, "repository_commit": "5f2c561058a186de59d3f27301eea210bd4bb66d",
               "manifest_sha256": "299b908e42abd3164d85e75b96122c3a61bfb1d33055e0967ccfe3f891ab7048",
               "canonical_sha256": "00cfdbd15aa272c4d964b66ad3d646fceed6d85b09a7ccb23ee841e75ce3b28a"},
}
EXECUTABLES = ("DbServer.exe", "MapServer.exe", "TestClientCreate.exe", "TestClientResume.exe", "TestClientBridge.exe")
CAPTURE_LIMITS = {prefix + "-" + name: limit for prefix in ("first", "second") for name, limit in
                  (("ready.json", 16384), ("result.json", 16384),
                   ("events.jsonl", 8 * 1024 * 1024), ("console.txt", 16 * 1024 * 1024))}
CAPTURE_LIMITS.update({prefix + "-snapshot.json": 1024 * 1024 for prefix in ("first", "restart", "second")})
SERVICE_LABELS = ("first-dbserver", "first-atlas", "restart-dbserver", "restart-atlas")
SERVICE_CAPTURE_LIMITS = {label + "-stdout.txt": 6 * 1024 * 1024 for label in SERVICE_LABELS}
SERVICE_CAPTURE_LIMITS.update({"log-" + str(number).zfill(3) + ".txt": 4 * 1024 * 1024 for number in range(1, 33)})
SERVICE_CAPTURE_LIMITS["manifest.json"] = 128 * 1024
STAGES = ("game_private_runtime", "assets_and_architecture", "initialize_owned_cluster", "postgres_first_start",
          "restricted_fixture_database", "wine_prefix_and_driver", "win32_odbc_driver", "win32_runtime_dll",
          "game_services_first", "atlas_ready_observation", "game_create_and_connect", "game_live_currency",
          "game_protocol_logout_first", "game_restart", "postgres_game_restart", "game_services_restart",
          "game_resume_exact_name", "game_protocol_logout_second")
PROGRESS_LINE_LIMIT = 64 * 1024
PROGRESS_EVENT_LIMIT = 4096


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read_json(path, limit=MAX_MANIFEST_BYTES):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= limit,
            "Missing, linked or oversized JSON input: " + str(path))
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict) and value.get("format") == 1,
            "Unsupported JSON input: " + str(path))
    return value


def inventory_bounds(files, *, maximum_files, maximum_bytes):
    require(isinstance(files, dict) and 0 < len(files) <= maximum_files,
            "Input file count exceeds its bound")
    total, folded = 0, set()
    for name, record in files.items():
        require(isinstance(name, str) and isinstance(record, dict), "Invalid inventory record")
        path = PurePosixPath(name)
        require(name and path.as_posix() == name and not path.is_absolute()
                and ".." not in path.parts and "\\" not in name and ":" not in name
                and name.casefold() not in folded, "Unsafe or case-conflicting input path")
        require(type(record.get("bytes")) is int and record["bytes"] >= 0
                and isinstance(record.get("sha256"), str)
                and dbhost.HEX64.fullmatch(record["sha256"]), "Invalid input size/hash")
        folded.add(name.casefold())
        total += record["bytes"]
        require(total <= maximum_bytes, "Input payload bytes exceed their bound")
    return total


def verify_package(package):
    manifest = read_json(package / "game-package.json", 8 * 1024 * 1024)
    require(manifest.get("role") == "wine_game_runtime"
            and manifest.get("source_commit") == dbhost.SOURCE_COMMIT
            and manifest.get("data_commit") == dbhost.DATA_COMMIT
            and re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("repository_commit", "")))
            and manifest.get("client_version") == "coh-persistence-diagnostic"
            and manifest.get("postgresql_persistence_fixture") is False
            and manifest.get("runtime_execution_validated") is False,
            "Game package identity, diagnostic version or fixture mode differs")
    files = manifest.get("files")
    inventory_bounds(files, maximum_files=64, maximum_bytes=512 * 1024 * 1024)
    require(all(len(PurePosixPath(name).parts) == 1 for name in files), "Game package must be flat")
    proofs = manifest.get("inputs", {})
    require(isinstance(proofs, dict) and set(proofs) == {*DONORS, "bridge"}, "Game package donor set differs")
    for role, pin in DONORS.items():
        proof = proofs[role]
        require(isinstance(proof, dict)
                and all(proof.get(key) == pin[key] for key in ("run_id", "repository_commit", "manifest_sha256"))
                and canonical_digest(proof.get("manifest")) == pin["canonical_sha256"],
                "Game package donor is not the exact accepted build: " + role)
    bridge = proofs["bridge"]
    require(isinstance(bridge, dict) and isinstance(bridge.get("manifest"), dict), "Missing bridge build receipt")
    receipt = bridge["manifest"]
    bridge_sources = {name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                      for name in ("database/wine-game/TestClientBridge.c", "database/wine-game/bridge_protocol.h")}
    require(bridge.get("repository_commit") == receipt.get("repository_commit") == manifest["repository_commit"]
            and receipt.get("format") == 1 and receipt.get("role") == "stock_testclient_launcher_bridge"
            and receipt.get("architecture") == "Win32" and receipt.get("compiler") == "MSVC"
            and receipt.get("flags") == "/nologo /W4 /O2 /MT /D_WIN32_WINNT=0x0601"
            and receipt.get("sources_sha256_lf") == bridge_sources
            and set(receipt.get("files", {})) == {"TestClientBridge.exe"},
            "Bridge source, architecture, build flags or repository identity differs")
    encoded = json.dumps(receipt, indent=2) + "\n"
    require(bridge.get("manifest_sha256") in {hashlib.sha256(encoded.encode()).hexdigest(),
            hashlib.sha256(encoded.replace("\n", "\r\n").encode()).hexdigest()},
            "Bridge embedded receipt does not match its recorded bytes")
    reference = proofs["reference"]["manifest"]["files"]
    normal = proofs["dbserver"]["manifest"]["variants"]["normal"]["files"]
    selected = {name: (record, "reference") for name, record in reference.items() if name.lower().endswith(".dll")}
    selected.update({"MapServer.exe": (reference["MapServer.exe"], "reference"),
                     "TestClientCreate.exe": (reference["TestClient.exe"], "reference")})
    selected.update({name: (record, "dbserver") for name, record in normal.items()})
    selected["TestClientResume.exe"] = (proofs["resume"]["manifest"]["files"]["TestClient.exe"], "resume")
    selected["TestClientBridge.exe"] = (receipt["files"]["TestClientBridge.exe"], "bridge")
    require(set(files) == set(selected) and set(name for name in files if name.lower().endswith(".exe")) == set(EXECUTABLES),
            "Game package executable/dependency selection differs")
    require(manifest.get("file_donors") == {name: role for name, (_, role) in selected.items()},
            "Game package file donor mapping differs")
    for name, (record, _) in selected.items():
        expected = {key: value for key, value in record.items() if key != "size"}
        expected["bytes"] = record.get("bytes", record.get("size"))
        require(files[name] == expected, "Game package substituted a donor payload: " + name)
    dbhost.verify_inventory(package, files, excluded=("game-package.json",))
    for name, record in files.items():
        require(all(record.get(key) == value for key, value in pe_info((package / name).read_bytes()).items()),
                "Game package PE metadata differs: " + name)
    dependencies = dependency_report(files)
    require(not dependencies["unresolved"] and manifest.get("dependency_report") == dependencies,
            "Game package imports do not match its complete dependency inventory")
    return manifest


def verify_data(data):
    manifest = read_json(data / "game-data-manifest.json")
    require(manifest.get("scope") == "reviewed_game_data"
            and manifest.get("source_commit") == dbhost.SOURCE_COMMIT
            and manifest.get("data_commit") == dbhost.DATA_COMMIT
            and manifest.get("android_execution_validated") is False
            and manifest.get("gameplay_validated") is False,
            "Game data source/data identity differs")
    files = manifest.get("files")
    total = inventory_bounds(files, maximum_files=MAX_DATA_FILES, maximum_bytes=MAX_DATA_BYTES)
    require(manifest.get("file_count") == len(files) == DATA_FILE_COUNT
            and manifest.get("total_bytes") == total == DATA_TOTAL_BYTES
            and manifest.get("asset_manifest_sha256") == ASSET_MANIFEST_SHA256
            and manifest.get("asset_archive_sha256") == ASSET_ARCHIVE_SHA256,
            "Game data differs from the reviewed full asset/text assembly")
    require(all(name.startswith("data/") for name in files), "Game data contains a non-data payload")
    dbhost.verify_inventory(data, files, excluded=("game-data-manifest.json",))
    return manifest


def make_expectations(assets, package, data, schema, package_manifest, schema_manifest):
    inputs = {"runtime_manifest_sha256": digest(assets / "runtime-manifest.json"),
              "game_package_sha256": digest(package / "game-package.json"),
              "game_data_manifest_sha256": digest(data / "game-data-manifest.json"),
              "schema_manifest_sha256": digest(schema / "schema-manifest.json"),
              "repository_commit": package_manifest["repository_commit"],
              "source_commit": dbhost.SOURCE_COMMIT, "data_commit": dbhost.DATA_COMMIT,
              "binary_sha256": {name: package_manifest["files"][name]["sha256"] for name in EXECUTABLES}}
    return {"inputs": inputs, "schema": dbhost.schema_expectations(schema_manifest),
            "runtime_lock_sha256": digest(assets / "runtime-lock.json")}


def owned_cleanup_complete(value):
    return (isinstance(value, dict) and value.get("complete") is True
            and type(value.get("remaining")) is int and value["remaining"] == 0
            and type(value.get("inspection_failures")) is int and value["inspection_failures"] == 0)


def map_ready(value):
    return (isinstance(value, dict) and value.get("ready") is True and value.get("map_id") == 1
            and value.get("address") == "127.0.0.1" and type(value.get("port")) is int and value["port"] == 7001
            and all(type(value.get(key)) is int and 0 <= value[key] <= 20
                    for key in ("network_age_seconds", "stats_age_seconds")))


def validate_session(session):
    ready, result = session.get("ready", {}), session.get("result", {})
    require(session.get("proof_completed_before_stop") is True and ready.get("format") == result.get("format") == 1
            and type(ready.get("child_pid")) is int and 0 < ready["child_pid"] <= 0xffffffff
            and type(ready.get("transport_pid")) is int and ready["transport_pid"] == ready["child_pid"]
            and result.get("child_pid") == ready["child_pid"]
            and all(ready.get(key) is True for key in ("console_attached", "pipe_pid_verified",
                    "protocol_pid_verified", "initial_snapshot"))
            and result.get("error") is None and result.get("final_snapshot") is True
            and result.get("pipe_framing_complete") is True
            and result.get("pipe_disconnected") is True and result.get("child_exited") is True
            and type(result.get("child_exit_code")) is int and type(result.get("child_forced_stop")) is bool,
            "TestClient bridge lacks completed identity-bound observation and final capture")
    require(ready.get("buffer_rows_limit") == 16384
            and all(type(item.get("version_requests")) is int and item["version_requests"] == 1
                    and item.get("capture_byte_limit") == 16 * 1024 * 1024
                    and item.get("event_byte_limit") == 8 * 1024 * 1024 for item in (ready, result))
            and type(session.get("commands")) is int and 1 <= session["commands"] <= 64
            and result.get("command_count") == session["commands"]
            and type(result.get("event_count")) is int and 1 <= result["event_count"] <= 20000
            and type(result.get("console_snapshots")) is int and result["console_snapshots"] >= 2
            and all(isinstance(session.get(key), str) and dbhost.HEX64.fullmatch(session[key])
                    for key in ("console_sha256", "events_sha256")),
            "TestClient bridge capture bounds, hashes or protocol counts differ")


def validate_report(report, *, expected):
    require(report.get("passed") is True and report.get("status") == "passed" and report.get("failures") == []
            and report.get("cleanup_complete") is True, "Game runtime did not prove complete success")
    require(report.get("diagnostic_mode") == "atlas_character_persistence"
            and report.get("execution_platform_requested") == "host"
            and all(report.get(key) is False for key in ("android_execution_validated", "gameplay_validated",
                    "android_surface_validated", "hardware_acceleration_validated", "interactive_rendering_validated")),
            "Hosted game report scope differs")
    require(report.get("inputs") == expected["inputs"], "Game runtime input provenance differs")
    stages = report.get("stages", [])
    require(isinstance(stages, list) and tuple(item.get("stage") for item in stages) == STAGES
            and all(item.get("status") == "passed" for item in stages), "Game stage coverage differs")
    require(stages[0].get("input_files") == DATA_FILE_COUNT and stages[0].get("input_bytes") == DATA_TOTAL_BYTES
            and stages[0].get("accepted_schema_overlay_files") == 62
            and stages[2].get("cluster_reused") is False, "Game private staging or fresh-cluster evidence differs")
    require(all(report.get("cleanup", {}).get(key) is True
                for key in ("postgres_graceful", "wine_prefix_stopped", "owned_processes_reaped"))
            and owned_cleanup_complete(report.get("wine_process_cleanup")), "Game owned cleanup is incomplete")
    processes = report.get("processes", [])
    require(isinstance(processes, list) and 0 < len(processes) <= 240
            and all(type(item.get("exit_code")) is int and item.get("input_closed") is True
                    and item.get("output_capture_closed") is True for item in processes),
            "Game process exit/input/output capture is incomplete")
    labels = [item.get("label") for item in processes]
    require(all(labels.count(label) == 1 for label in ("first-dbserver", "first-atlas", "restart-dbserver",
                "restart-atlas", "bridge-create", "bridge-resume", "postgres_first_start", "postgres_game_restart")),
            "Game report lacks each managed server/client process")
    require(all(item["exit_code"] == 0 for item in processes if item.get("label") in ("bridge-create", "bridge-resume")),
            "TestClient bridge failed")
    wine = report.get("wine_initialization", {})
    require(wine.get("policy") == "initialize_once_then_reuse" and wine.get("state") == "ready"
            and wine.get("ready_prefix_reused") is False and wine.get("runtime_lock_sha256") == expected["runtime_lock_sha256"]
            and all(type(wine.get(key)) is int and wine[key] == count for key, count in
                    (("registration_processes", 3), ("wow64_registration_processes", 1), ("registration_passes", 1))),
            "Game runtime did not prove accepted cold Wine initialization")
    game = report.get("game", {})
    require(game.get("status") == "passed" and game.get("created_connected") is True
            and game.get("attributes_unchanged") is True and game.get("process_budget") == 240
            and game.get("query_budget") == 80 and type(game.get("query_processes")) is int
            and 1 <= game["query_processes"] <= 80 and type(game.get("readiness_queries")) is int
            and 1 <= game["readiness_queries"] <= 20, "Game proof or bounded-query coverage is incomplete")
    phases = game.get("phases", [])
    require(isinstance(phases, list) and [item.get("phase") for item in phases] == ["first_services_ready", "restart_services_ready"],
            "Both game service starts were not proved")
    catalogs = []
    for phase in phases:
        require(phase.get("status") == "passed" and phase.get("baseline_not_started") is True and map_ready(phase.get("map")),
                "Game services lack an unstarted baseline and current owned Atlas endpoint")
        schema = phase.get("schema", {})
        require(all(schema.get(key) == value for key, value in expected["schema"].items()),
                "Game schema or exact attribute IDs differ from accepted generation")
        catalog = schema.get("catalog_sha256", {})
        require(isinstance(catalog, dict) and set(catalog) == {"columns", "indexes", "constraints"}
                and all(isinstance(value, str) and dbhost.HEX64.fullmatch(value) for value in catalog.values()),
                "Game catalog fingerprints are incomplete")
        catalogs.append(catalog)
    require(catalogs[0] == catalogs[1], "Game service restart changed the SQL catalog")
    observation = game.get("atlas_observation", {})
    seconds, samples = observation.get("seconds"), observation.get("samples", [])
    require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 30
            and observation.get("minimum_seconds") == 30 and observation.get("db_confirmed_ready") is True
            and observation.get("current_heartbeats") is True and isinstance(samples, list) and len(samples) >= 2
            and all(map_ready(sample) for sample in samples), "Atlas did not prove 30 seconds of current readiness")
    timestamps = [sample.get("monotonic") for sample in samples]
    require(all(type(value) in (int, float) and math.isfinite(value) and value > 0 for value in timestamps)
            and all(before < after for before, after in zip(timestamps, timestamps[1:])),
            "Atlas readiness observations are not distinct chronological samples")
    character = game.get("character", {})
    require(type(character.get("container_id")) is int and character["container_id"] > 0
            and isinstance(character.get("name"), str) and 0 < len(character["name"]) <= 128
            and not any(ord(value) < 32 for value in character["name"])
            and re.fullmatch(r"CohA[0-9a-f]{10}", str(game.get("account", "")))
            and character.get("account") == game["account"], "Game character/account identity differs")
    currency = game.get("live_currency", {})
    require(currency.get("player") == character["name"] and currency.get("account") == game["account"]
            and type(currency.get("influence")) is int and currency["influence"] == 12345
            and type(currency.get("sequence")) is int and currency["sequence"] > 0,
            "Game lacks an identity-bound live influence response")
    rows = None
    for label, count in (("first", 1), ("second", 2)):
        proof = game.get(label + "_save", {})
        require(all(proof.get(key) is True for key in ("protocol_quit", "disconnected_before_sql", "independent_committed_sql"))
                and proof.get("quitnow_is_save_ack") is False and proof.get("forced_stop_before_save") is False
                and type(proof.get("login_count")) is int and proof["login_count"] == count
                and type(proof.get("influence")) is int and proof["influence"] == 12345
                and isinstance(proof.get("snapshot_sha256"), str) and dbhost.HEX64.fullmatch(proof["snapshot_sha256"]),
                "Game protocol logout lacks independent committed SQL proof: " + label)
        counts = proof.get("row_counts", {})
        require(isinstance(counts, dict) and set(counts) == {"ents", "ents2", "powers", "costumeparts"}
                and all(type(value) is int and value > 0 for value in counts.values())
                and counts["ents"] == counts["ents2"] == 1, "Saved character parent/child rows are incomplete")
        require(rows is None or counts == rows, "Second save changed selected child-row counts")
        rows = counts
    restart = game.get("restart", {})
    require(all(restart.get(key) is True for key in ("same_cluster", "same_database", "no_reseed_or_restore"))
            and all(restart.get("wine_shutdown", {}).get(key) is True for key in ("prefix_lock_free", "server_socket_inactive"))
            and owned_cleanup_complete(restart.get("owned_cleanup")), "Game restart ownership or no-restore proof is incomplete")
    for item, phase, after in ((restart, "restart", 1), (game["second_save"].get("comparison", {}), "second_logout", 2)):
        require(item.get("phase") == phase and item.get("identity_unchanged") is True
                and item.get("selected_rows_unchanged") is True and item.get("login_count_before") == 1
                and item.get("login_count_after") == after and item.get("row_counts") == rows,
                "Saved character comparison failed after " + phase)
    resume = game.get("resume", {})
    require(resume.get("database_id") == character["container_id"] and resume.get("exact_name") == character["name"]
            and type(resume.get("slot")) is int and resume["slot"] >= 0
            and all(resume.get(key) is True for key in ("creation_disabled", "connected_on_atlas", "processed_server_update",
                    "scene_exchange_observed", "processed_server_update_for_original_player"))
            and resume.get("active_gameplay_confirmed") is False, "Resume did not prove the original processed player entity")
    sessions = game.get("sessions", {})
    require(isinstance(sessions, dict) and set(sessions) == {"first", "second"}, "Both client sessions must complete")
    for session in sessions.values():
        validate_session(session)


def copy_capture_area(state, evidence, directory, limits, total_limit):
    """Copy only the guest's bounded, redacted diagnostic export area."""
    source, destination = state / directory, evidence / directory
    records = {}
    if source.exists() or source.is_symlink():
        require(source.is_dir() and not source.is_symlink(), "Invalid game capture export directory")
        files = sorted(source.iterdir())
        require(len(files) <= len(limits) and all(path.name in limits for path in files),
                "Game capture export contains an unexpected name")
        total = 0
        for path in files:
            require(path.is_file() and not path.is_symlink(), "Linked or nonregular game capture refused")
            total += path.stat().st_size
            require(path.stat().st_size <= limits[path.name] and total <= total_limit,
                    "Game capture export exceeds its bounds")
        destination.mkdir(exist_ok=False)
        for path in files:
            target = destination / path.name
            shutil.copyfile(path, target)
            records[path.name] = {"bytes": target.stat().st_size, "sha256": digest(target)}
    return records


def copy_game_captures(state, evidence):
    records = copy_capture_area(state, evidence, "game-captures", CAPTURE_LIMITS, 53 * 1024 * 1024)
    receipt = {"format": 1, "scope": "redacted_game_diagnostic_captures", "files": records}
    (evidence / "game-captures.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return records


def copy_service_captures(state, evidence):
    records = copy_capture_area(state, evidence, "game-service-captures", SERVICE_CAPTURE_LIMITS, 153 * 1024 * 1024)
    receipt = {"format": 1, "scope": "redacted_game_service_captures", "files": records}
    (evidence / "game-service-captures.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return records


def validate_service_captures(report, evidence, records):
    required = {label + "-stdout.txt" for label in SERVICE_LABELS} | {"manifest.json"}
    require(required <= set(records) <= set(SERVICE_CAPTURE_LIMITS)
            and report["game"].get("service_capture_files") == records,
            "Successful game proof lacks its exact service capture inventory")
    manifest = read_json(evidence / "game-service-captures/manifest.json", 128 * 1024)
    files = manifest.get("files", {})
    require(isinstance(files, dict) and set(files) == set(records) - {"manifest.json"}
            and manifest.get("selected_log_limit") == 32 and manifest.get("log_segment_bytes") == 512 * 1024
            and type(manifest.get("unselected_logs")) is int and manifest["unselected_logs"] >= 0
            and manifest.get("inspection_failure") is None,
            "Service capture manifest is incomplete or failed inspection")
    for name, record in files.items():
        require(isinstance(record, dict) and all(record.get(key) == records[name][key] for key in ("bytes", "sha256"))
                and type(record.get("original_bytes")) is int and record["original_bytes"] >= 0
                and type(record.get("truncated")) is bool, "Service capture identity or truncation metadata differs")
        if name.endswith("-stdout.txt"):
            require(record.get("kind") == "owned_service_stdout" and record.get("process_label") == name[:-11]
                    and record["original_bytes"] <= 2 * 1024 * 1024 and record["truncated"] is False
                    and record.get("overflow") is False and record.get("capture_closed") is True,
                    "Owned service stdout is incomplete or overflowed")
        else:
            source = record.get("source_relative_path")
            require(isinstance(source, str) and source and "\\" not in source and ":" not in source,
                    "Invalid service log source path")
            relative = PurePosixPath(source)
            require(not relative.is_absolute() and relative.as_posix() == source and ".." not in relative.parts
                    and relative.suffix == ".log" and (len(relative.parts) == 1 or relative.parts[0] == "logs")
                    and record.get("kind") == "runtime_log"
                    and record["truncated"] == (record["original_bytes"] > 1024 * 1024),
                    "Service log source or bounded-segment metadata differs")


def validate_capture_files(report, evidence, records):
    game = report["game"]
    require(set(records) == set(CAPTURE_LIMITS) and game.get("capture_files") == records,
            "Successful game proof lacks its exact exported capture inventory")
    folder = evidence / "game-captures"
    snapshots = {}
    for prefix in ("first", "second"):
        session = game["sessions"][prefix]
        require(records[prefix + "-console.txt"]["sha256"] == session["console_sha256"]
                and records[prefix + "-events.jsonl"]["sha256"] == session["events_sha256"],
                "Exported TestClient console/events differ from session proof")
        for kind in ("ready", "result"):
            require(read_json(folder / (prefix + "-" + kind + ".json"), 16384) == session[kind],
                    "Exported bridge identity/result differs from session proof")
    for prefix, proof in (("first", game["first_save"]), ("restart", game["restart"]), ("second", game["second_save"])):
        path = folder / (prefix + "-snapshot.json")
        value = json.loads(path.read_text(encoding="utf-8"))
        require(isinstance(value, dict) and set(value) == {"identity", "login_count", "rows"}
                and canonical_digest(value) == proof.get("snapshot_sha256"),
                "Exported committed SQL snapshot differs from proof: " + prefix)
        identity, rows = value["identity"], value["rows"]
        require(isinstance(identity, dict) and set(identity) == {"containerid", "authid", "authname", "name"}
                and type(identity["containerid"]) is int and identity["containerid"] == game["character"]["container_id"]
                and type(identity["authid"]) is int and identity["authid"] > 0
                and isinstance(identity["authname"], str) and identity["authname"].lower() == game["account"].lower()
                and identity["name"] == game["character"]["name"], "Committed SQL snapshot identity differs")
        counts = game["first_save"]["row_counts"]
        require(isinstance(rows, dict) and set(rows) == set(counts)
                and all(isinstance(rows[table], list) and len(rows[table]) == count for table, count in counts.items())
                and all(isinstance(row, dict) and type(row.get("containerid")) is int
                        and row["containerid"] == identity["containerid"] for values in rows.values() for row in values)
                and all(rows["ents"][0].get(key) == identity[key] for key in identity)
                and type(rows["ents"][0].get("influencepoints")) is int and rows["ents"][0]["influencepoints"] == 12345,
                "Committed SQL snapshot rows differ from character proof")
        require(type(value["login_count"]) is int and value["login_count"] == (2 if prefix == "second" else 1),
                "Exported SQL LoginCount progression differs")
        snapshots[prefix] = value
    require(canonical_digest(snapshots["first"]) == canonical_digest(snapshots["restart"]),
            "SQL snapshot changed across game/PostgreSQL restart")
    second = dict(snapshots["second"], login_count=1)
    require(canonical_digest(snapshots["first"]) == canonical_digest(second),
            "Second logout changed selected saved fields")


def check_paths_and_space(work, evidence, inputs, *, data_bytes):
    require(not work.exists() and not evidence.exists(), "Use fresh game work and evidence directories")
    require(work != evidence and work not in evidence.parents and evidence not in work.parents,
            "Keep game work and evidence separate")
    for destination in (work, evidence):
        require(destination != ROOT and (ROOT / "upstream") not in destination.parents,
                "Game output overlaps protected source")
        require(all(destination != source and destination not in source.parents and source not in destination.parents
                    for source in inputs), "Game output overlaps an input directory")
    parent = work.parent
    while not parent.exists():
        parent = parent.parent
    free = shutil.disk_usage(parent).free
    required = max(MIN_FREE_BYTES, data_bytes * 2 + 4 * 1024**3)
    require(free >= required, "Insufficient disk for private game copies and generated caches")
    return {"free_bytes_before_setup": free, "required_free_bytes": required}


def make_command(*, work, assets, package, data, schema, proot, timeout_seconds):
    command = dbhost.make_command(work=work, assets=assets, package=package, schema=schema,
                                  proot=proot, timeout_seconds=timeout_seconds)
    replacements = {
        str(package.resolve()) + ":/opt/coh-dbserver": str(package.resolve()) + ":/opt/coh-game-package",
        "/opt/coh-dbserver": "/opt/coh-game-package",
        "/opt/coh-m3/dbserver_diagnostic.py": "/opt/coh-m3/game_diagnostic.py",
        "--package": "--game-package",
    }
    command = [replacements.get(value, value) for value in command]
    index = command.index("-w")
    command[index:index] = ["-b", str(data.resolve()) + ":/opt/coh-game-data"]
    return command + ["--game-data", "/opt/coh-game-data", "--execution-platform", "host"]


def prepare_runtime(work, evidence, assets):
    """Use the accepted downloads/extractor without modifying the M2 payload."""
    work.mkdir(parents=True, mode=0o700)
    evidence.mkdir(parents=True)
    lock = read_json(assets / "runtime-lock.json")
    base = dbhost.fetch(lock["base"], ROOT / "out/android/cache/base.tar.gz")
    wine = dbhost.fetch(lock["wine"], ROOT / "out/android/cache/wine.tar.gz")
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
    hosts = dbhost.prepare_guest_hosts(work, evidence, os.uname().nodename)
    for name in ("opt/coh", "opt/coh/pgsql", "opt/coh-game-package", "opt/coh-game-data",
                 "opt/coh-schema", "opt/coh-m3", "opt/wine", "state", "tmp"):
        (work / "rootfs" / name).mkdir(parents=True, exist_ok=True)
    scripts = {}
    for name in ("game_diagnostic.py", "game_evidence.py", "game_failure.py", "dbserver_diagnostic.py"):
        target = work / "m3-tools" / name
        shutil.copyfile(ROOT / "android/guest" / name, target)
        scripts[name] = digest(target)
    return {**hosts, "guest_script_sha256": scripts}


class StageProgress:
    """Observe the existing regular capture file; never own a child output pipe."""
    def __init__(self, emit=None):
        self.pending = bytearray()
        self.discarding = False
        self.count = 0
        self.emit = emit if emit is not None else lambda value: print(json.dumps(value), flush=True)

    def line(self, raw):
        if self.count >= PROGRESS_EVENT_LIMIT:
            return
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError, RecursionError):
            return
        if (not isinstance(value, dict) or value.get("type") != "stage"
                or value.get("stage") not in STAGES or value.get("status") not in ("running", "passed")):
            return
        event = {key: value[key] for key in ("type", "stage", "status")}
        # Stage messages are already redacted by Context.event. Project only
        # bounded progress fields: process output and arbitrary JSON stay in
        # the owned evidence file and are not streamed into the job console.
        for key, limit in (("time_utc", 64), ("message", 256)):
            item = value.get(key)
            if isinstance(item, str) and len(item) <= limit and all(ord(c) >= 32 for c in item):
                event[key] = item
        if type(value.get("files")) is int and 0 <= value["files"] <= MAX_DATA_FILES:
            event["files"] = value["files"]
        self.count += 1
        self.emit(event)

    def feed(self, chunk):
        parts = chunk.split(b"\n")
        for index, part in enumerate(parts):
            complete = index < len(parts) - 1
            if self.discarding:
                if complete:
                    self.discarding = False
                continue
            if len(self.pending) + len(part) > PROGRESS_LINE_LIMIT:
                self.pending.clear()
                self.discarding = not complete
                continue
            self.pending.extend(part)
            if complete:
                self.line(self.pending)
                self.pending.clear()

    def drain(self, stream, *, limit=256 * 1024):
        # A fixed byte budget also bounds the final drain if a descendant still
        # appends after the namespace wrapper exits. EOF is not a wait target.
        remaining = min(limit, max(0, os.fstat(stream.fileno()).st_size - stream.tell()))
        while remaining:
            chunk = stream.read(min(65536, remaining))
            if not chunk:
                break
            self.feed(chunk)
            remaining -= len(chunk)


def wait_with_progress(process, log_path, timeout_seconds, *, emit=None):
    deadline = time.monotonic() + timeout_seconds
    progress = StageProgress(emit)
    with log_path.open("rb") as stream:
        try:
            while True:
                progress.drain(stream)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(process.args, timeout_seconds)
                try:
                    return process.wait(timeout=min(1, remaining))
                except subprocess.TimeoutExpired:
                    pass
        finally:
            progress.drain(stream, limit=max(0, os.fstat(stream.fileno()).st_size - stream.tell()))


def run_guest(command, env, state, evidence, *, timeout_seconds, expected):
    source = state / "latest-report.json"
    target = evidence / "game-runtime-report.json"
    log_path = evidence / "host-game.log"
    source.unlink(missing_ok=True)
    target.unlink(missing_ok=True)
    with log_path.open("w") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            code = wait_with_progress(process, log_path, timeout_seconds + 90)
        except subprocess.TimeoutExpired:
            termination = dbhost.stop_guest(process, state)
            raise RuntimeError("Game host runtime exceeded its bounded time; tracee cleanup is unverified: " + termination)
        finally:
            if source.is_file() and not source.is_symlink() and source.stat().st_size <= MAX_REPORT_BYTES:
                shutil.copyfile(source, target)
            captures = copy_game_captures(state, evidence)
            service_captures = copy_service_captures(state, evidence)
    try:
        require(code == 0, "Game PRoot runtime returned a failure exit status")
        require(target.is_file(), "Game runtime did not write a fresh bounded report")
        report = read_json(target, MAX_REPORT_BYTES)
        validate_report(report, expected=expected)
        validate_capture_files(report, evidence, captures)
        validate_service_captures(report, evidence, service_captures)
    except (RuntimeError, ValueError):
        with log_path.open("rb") as log:
            log.seek(max(0, log_path.stat().st_size - 24000))
            print(log.read().decode("utf-8", errors="replace"))
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ROOT / "out/android/assets/runtime")
    for name in ("package", "data", "schema"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--work", type=Path, default=ROOT / "out/android/game-host")
    parser.add_argument("--evidence", type=Path, default=ROOT / "out/android/game-evidence")
    parser.add_argument("--proot", type=Path, default=ROOT / "out/android/native/linux-arm64")
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    args = parser.parse_args()
    require(sys.platform == "linux" and platform.machine().lower() in ("aarch64", "arm64"),
            "Native ARM64 Linux is required")
    require(os.getuid() > 0 and os.geteuid() == os.getuid(), "Run as the original non-root runner")
    require(60 <= args.timeout_seconds <= 3600, "Guest timeout must be between 60 and 3600 seconds")
    assets, package, data, schema, work, evidence, proot = (
        getattr(args, name).resolve() for name in ("assets", "package", "data", "schema", "work", "evidence", "proot"))
    runtime = dbhost.verify_runtime_assets(assets)
    package_manifest = verify_package(package)
    data_manifest = verify_data(data)
    schema_manifest = dbhost.verify_schema(schema)
    repository_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(package_manifest.get("repository_commit") == repository_commit,
            "Game bridge package differs from the checked-out harness source")
    disk = check_paths_and_space(work, evidence, (assets, package, data, schema, proot),
                                 data_bytes=sum(record["bytes"] for record in data_manifest["files"].values()))
    for name in ("proot", "proot-loader"):
        path = proot / name
        require(path.is_file() and not path.is_symlink(), "Missing native PRoot input")
        path.chmod(0o755)
    setup = prepare_runtime(work, evidence, assets)
    expected = make_expectations(assets, package, data, schema, package_manifest, schema_manifest)
    inputs = {"format": 1, "scope": "host_game_runtime_inputs", **expected["inputs"], **setup,
              "disk_preflight": disk, "runtime_commit": runtime["repository_commit"],
              "proot_sha256": digest(proot / "proot"), "proot_loader_sha256": digest(proot / "proot-loader"),
              "android_execution_validated": False, "gameplay_validated": False}
    (evidence / "host-game-inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    command = make_command(work=work, assets=assets, package=package, data=data, schema=schema,
                           proot=proot, timeout_seconds=args.timeout_seconds)
    command, env, network_expected = dbhost.isolate_command(command, evidence=evidence, proot=proot, work=work)
    report = run_guest(command, env, work / "state", evidence,
                       timeout_seconds=args.timeout_seconds, expected=expected)
    dbhost.validate_network_receipt(read_json(evidence / "network-isolation.json"), network_expected)
    print(json.dumps({"status": "native_arm64_proot_game_passed_android_unvalidated",
                      "report": str(evidence / "game-runtime-report.json"), "stages": len(report["stages"])}))


if __name__ == "__main__":
    main()
