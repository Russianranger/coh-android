#!/usr/bin/env python3
"""Focused new policy/CLI controls. Explicit component doubles; no servers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess


OWNED = Path("native-android/engine/auth-interop/fresh-character-owner/probe")
ONE = "begin_attempted shard_attempted bridge_attempted creation_attempted retirement_attempted actual_grant_verified matching_empty_list_verified creation_request_queued allocated_offer_observed private_offer_retired container_uninitialized persistent_allocation_possible private_name_wiped bridge_temporaries_wiped controllers_destroyed cleanup_cancel_close_used session_generation receipt_generation selection_generation provisional_development_policy development_skip_requested".split()
ZERO = "actual_server_development_skip_observed normal_version_admitted checksum_reference_admitted initialized_character persistent_rollback_claimed map_socket_opened map_character_body_sent sends_ready sends_received_character sends_full_update_ack current_world_verified actor_publication world_authority".split()
ENUM = "phase status failure observed_auth_phase observed_db_phase final_auth_phase final_db_phase".split()
PLATFORM = "initialization_verified supplied_map_policy_admitted map_process_file_generation_before map_process_file_generation_after checksum_measured_from_actual_probe fresh_connect_entropy no_live_tcp_handles no_live_udp_handles transport_cleanup_complete private_policy_handle_closed map_process_handle_closed cleanup_complete".split()
PUBLIC_KEYS = set("schema passed stage status phase failure session_generation receipt_generation selection_generation offer_retired container_uninitialized persistent_allocation_possible local_sensitive_buffers_wiped owner_cleanup_complete platform_cleanup_complete supplied_map_process_file_policy_admitted Map_READY_observed_by_probe actual_server_development_skip_observed normal_version_admitted checksum_reference_admitted persistent_rollback_claimed Map_socket_or_body_or_READY_or_ACK world_authority".split())
FALSE_PUBLIC = "Map_READY_observed_by_probe actual_server_development_skip_observed normal_version_admitted checksum_reference_admitted persistent_rollback_claimed Map_socket_or_body_or_READY_or_ACK world_authority".split()
PRIVATE = b"FixtureUser\nPrivatePassword\nFresh Fixture\n"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, *, cwd, env=None, data=None):
    return subprocess.run(command, cwd=cwd, env=env, input=data, capture_output=True, timeout=20, check=False)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    root, output = args.source_root.resolve(), args.output.resolve()
    require(not output.exists(), "output must be a fresh external directory")
    require(root not in output.parents, "output must be outside source tree")
    output.mkdir(parents=True)
    cc = os.environ.get("CC", "cc")
    common = [cc, "-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic", "-fno-pie", "-no-pie", "-I", "native-android/include"]
    policy = [OWNED / "fresh_probe_policy.c", OWNED / "test_fresh_probe_policy.c"]
    cli = [OWNED / "fresh_character_probe.c", OWNED / "test_fresh_probe_platform.c"]
    commands = []
    records = []
    source_paths = {OWNED / "check_fresh_probe_controls.py"}
    for sources in (policy, cli):
        command = common + ["-MM"] + [str(p) for p in sources]
        dependency = run(command, cwd=root)
        commands.append(command)
        (output / (sources[0].stem + "-dependencies.txt")).write_bytes(dependency.stdout)
        (output / (sources[0].stem + "-dependencies.stderr")).write_bytes(dependency.stderr)
        require(dependency.returncode == 0, "dependency query refused")
        # Each source has one Make target. Escaped lines are joined before
        # parsing; paths are admitted relative source files, never external.
        for line in dependency.stdout.decode().replace("\\\n", "").splitlines():
            for value in shlex.split(line.split(":", 1)[1]):
                raw_path = Path(value)
                require(not raw_path.is_absolute(), "unexpected absolute compiler dependency path")
                require(not (root / raw_path).is_symlink(), "symlink compiler dependency")
                path = (root / raw_path).resolve().relative_to(root)
                require((root / path).is_file(), "nonregular source dependency")
                source_paths.add(path)
    before = {str(p): digest(root / p) for p in sorted(source_paths)}
    head = run(["git", "rev-parse", "HEAD"], cwd=root)
    require(head.returncode == 0, "Git HEAD unavailable")
    head = head.stdout.decode().strip()
    modes = [("release", ["-O2"])]
    if args.sanitize:
        modes += [("asan", ["-O1", "-g", "-fsanitize=address", "-fno-omit-frame-pointer"]),
                  ("ubsan", ["-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all"])]
    environment = os.environ.copy()
    environment["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
    environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    binaries = {}
    for mode, flags in modes:
        for label, sources in (("policy", policy), ("cli", cli)):
            binary = output / f"{label}-{mode}"
            command = common + flags + [str(p) for p in sources] + ["-o", str(binary)]
            commands.append(command)
            compiled = run(command, cwd=root)
            (output / f"{label}-{mode}-compile.stdout").write_bytes(compiled.stdout)
            (output / f"{label}-{mode}-compile.stderr").write_bytes(compiled.stderr)
            require(compiled.returncode == 0, f"{label} {mode} compile refused; exact stderr retained")
            binaries[f"{label}-{mode}"] = digest(binary)
        process = run([str(output / f"policy-{mode}")], cwd=root, env=environment)
        (output / f"policy-{mode}.stdout").write_bytes(process.stdout)
        (output / f"policy-{mode}.stderr").write_bytes(process.stderr)
        require(process.returncode == 0 and not process.stderr, f"{mode} policy child refused")
        policy_result = json.loads(process.stdout)
        records.append({"mode": mode, "kind": "policy", "result": policy_result})

        cases = [("success", ["--allocate-offer", "PRIVATE_POLICY_SENTINEL"], PRIVATE, True, 0),
                 ("preflight", ["--platform-preflight"], b"", True, 0)]
        expected_status = {"open-null": 1, "config-fail": 6, "before-fail": 3, "create-null": 4,
                           "begin-fail": 1, "service-fail": 6, "first-failure": 6,
                           "timeout": 7, "clock-backwards": 7, "finish-fail": 3,
                           "owner-close-fail": 6, "owner-diag-fail": 6, "owner-destroy-fail": 6,
                           "platform-diag-fail": 6, "platform-destroy-fail": 6}
        failures = list(expected_status)
        failures += [f"owner-bad-{name}" for name in ONE + ZERO + ENUM]
        failures += [f"platform-bad-{name}" for name in PLATFORM]
        cases += [(name, ["--allocate-offer", "PRIVATE_POLICY_SENTINEL"], PRIVATE, False,
                   expected_status.get(name, 7)) for name in failures]
        # Preflight must refuse Map observations too; it never touches an owner.
        cases += [(f"platform-bad-{name}", ["--platform-preflight"], b"", False, 7) for name in PLATFORM]
        inputs = [b"", b"\nPrivatePassword\nFresh Fixture\n", b"FixtureUser\n\nFresh Fixture\n",
                  b"FixtureUser\nPrivatePassword\n\n", PRIVATE[:-1], PRIVATE + b"\n", PRIVATE + b"x",
                  b"A" * 15 + b"\nPrivatePassword\nFresh Fixture\n",
                  b"FixtureUser\n" + b"P" * 17 + b"\nFresh Fixture\n",
                  b"FixtureUser\nPrivatePassword\n" + b"N" * 64 + b"\n",
                  PRIVATE.replace(b"Fresh Fixture", b"Fresh\x00Fixture"), PRIVATE.replace(b"FixtureUser", b"Fixture\rUser"),
                  PRIVATE.replace(b"Fresh Fixture", b"Fresh\x7fFixture"), PRIVATE.replace(b"Fresh Fixture", b"Fresh\xffFixture")]
        cases += [("input-refusal", ["--allocate-offer", "PRIVATE_POLICY_SENTINEL"], data, False, 1) for data in inputs]
        cases.append(("input-refusal-io", ["--allocate-offer", "PRIVATE_POLICY_SENTINEL"], b"", False, 1))
        cases += [("input-refusal", argv, b"", False, 1) for argv in
                  ([], ["--allocate-offer"], ["--allocate-offer", ""], ["--bad"], ["--platform-preflight", "extra"])]
        # Both upper and lower accepted private-input lengths are exercised.
        cases += [("success", ["--allocate-offer", "PRIVATE_POLICY_SENTINEL"],
                   b"A" * 14 + b"\n" + b"P" * 16 + b"\n" + b"N" * 63 + b"\n", True, 0),
                  ("success", ["--allocate-offer", "PRIVATE_POLICY_SENTINEL"], b"A\nP\nN\n", True, 0)]
        for index, (case, argv, data, accepted, status) in enumerate(cases):
            env = environment | {"FRESH_PROBE_TEST_CASE": case}
            child = run([str(output / f"cli-{mode}")] + argv, cwd=root, env=env, data=data)
            stem = f"cli-{mode}-{index:03d}"
            (output / f"{stem}.stdout").write_bytes(child.stdout)
            (output / f"{stem}.stderr").write_bytes(child.stderr)
            require(child.returncode == (0 if accepted else 1) and not child.stderr, f"{stem} refused control case {case}")
            result = json.loads(child.stdout)
            require(set(result) == PUBLIC_KEYS, f"{stem} changed fixed public schema")
            require(result["schema"] == ("coh-fresh-character-platform-preflight-v1" if argv == ["--platform-preflight"] else "coh-fresh-character-offer-probe-v1"), f"{stem} changed schema identity")
            require(result["passed"] is accepted and result["status"] == status, f"{stem} status mismatch")
            require(result["local_sensitive_buffers_wiped"] is True, f"{stem} local wipe refusal")
            require(all(result[key] is False for key in FALSE_PUBLIC), f"{stem} authority barrier changed")
            require(all(value not in child.stdout + child.stderr for value in (b"FixtureUser", b"PrivatePassword", b"Fresh Fixture", b"PRIVATE_POLICY_SENTINEL")), f"{stem} private sentinel escaped")
            if case == "first-failure":
                require(result["failure"] == 6 and result["persistent_allocation_possible"] == 1,
                        "first owner failure or persistent-allocation possibility lost during cleanup")
            records.append({"mode": mode, "kind": "cli", "case": case, "index": index, "result": result})
    after = {str(p): digest(root / p) for p in sorted(source_paths)}
    require(before == after, "source changed during focused controls")
    require(all(digest(output / key) == value for key, value in binaries.items()), "child executable changed")
    release = [{k: v for k, v in row.items() if k != "mode"} for row in records if row["mode"] == "release"]
    for mode, _ in modes[1:]:
        require(release == [{k: v for k, v in row.items() if k != "mode"} for row in records if row["mode"] == mode], "cross-mode controls differ")
    receipt = {"schema": "coh-fresh-probe-policy-cli-controls-v1", "head": head,
               "source_before": before, "source_after": after, "commands": commands,
               "executable_sha256": binaries, "results": records,
               "scope": "new fixed-record parser and actual CLI, explicit owner/platform doubles only",
               "original_owner_or_controller_executed": False, "windows_execution": False,
               "original_server_transaction": False, "world_authority": False,
               "leak_sanitizer_enabled": False,
               "limitation": "No Windows backend, original Map readiness, authentication, persistent SQL or process/RSS admission"}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"passed": True, "modes": [name for name, _ in modes], "controls_per_mode": len(release), "source_inputs": len(before)}))


if __name__ == "__main__":
    main()
