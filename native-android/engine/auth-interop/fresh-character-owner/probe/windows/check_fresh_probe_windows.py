#!/usr/bin/env python3
"""New backend host API controls, not Windows/original-service qualification."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

OWNED = Path("native-android/engine/auth-interop/fresh-character-owner/probe/windows")
SOURCES = [OWNED / "fresh_probe_windows.c", OWNED.parent / "fresh_probe_policy.c",
           OWNED / "test_fresh_probe_windows.c"]


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, root, environment=None):
    return subprocess.run(command, cwd=root, env=environment, capture_output=True, timeout=40, check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    root, output = args.source_root.resolve(), args.output.resolve()
    require(not output.exists() and root not in output.parents, "fresh external output required")
    output.mkdir(parents=True)
    compiler = shutil.which(os.environ.get("CC", "cc"))
    require(compiler is not None, "compiler unavailable")
    compiler = str(Path(compiler).resolve())
    commands, source_paths, system_paths = [], {OWNED / "check_fresh_probe_windows.py"}, {Path(compiler)}
    common = [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic", "-DCOH_FRESH_WINDOWS_TEST",
              "-fno-pie", "-no-pie", "-I", "native-android/include"]
    dependency_command = common + ["-M"] + [str(p) for p in SOURCES]
    commands.append(dependency_command)
    dependency = run(dependency_command, root)
    (output / "dependencies.stdout").write_bytes(dependency.stdout)
    (output / "dependencies.stderr").write_bytes(dependency.stderr)
    require(dependency.returncode == 0 and not dependency.stderr, "dependency admission refused; stderr retained")
    for line in dependency.stdout.decode().replace("\\\n", "").splitlines():
        for token in shlex.split(line.split(":", 1)[1]):
            path = Path(token)
            absolute = path if path.is_absolute() else root / path
            require(absolute.is_file(), "nonregular compiler dependency")
            canonical = absolute.resolve()
            if canonical.is_relative_to(root):
                require(not absolute.is_symlink(), "source symlink refused")
                source_paths.add(canonical.relative_to(root))
            else:
                system_paths.add(canonical)
    before = {str(path): digest(root / path) for path in sorted(source_paths)}
    system_before = {str(path): digest(path) for path in sorted(system_paths)}
    head = run(["git", "rev-parse", "HEAD"], root)
    require(head.returncode == 0, "HEAD unavailable")
    source_head = head.stdout.decode().strip()
    compiler_version = run([compiler, "--version"], root)
    require(compiler_version.returncode == 0, "compiler version unavailable")
    (output / "compiler-version.txt").write_bytes(compiler_version.stdout + compiler_version.stderr)
    modes = [("release", ["-O2"])]
    if args.sanitize:
        modes += [("asan", ["-O1", "-g", "-fsanitize=address", "-fno-omit-frame-pointer"]),
                  ("ubsan", ["-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all"])]
    environment = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
                       UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    results, binaries, libraries, stack_files = {}, {}, {}, {}
    for mode, flags in modes:
        binary = output / f"backend-{mode}"
        command = common + flags + [str(path) for path in SOURCES] + ["-Wl,--wrap=calloc", "-Wl,--wrap=free", "-lcrypto", "-o", str(binary)]
        commands.append(command)
        child = run(command, root)
        (output / f"{mode}-compile.stdout").write_bytes(child.stdout)
        (output / f"{mode}-compile.stderr").write_bytes(child.stderr)
        require(child.returncode == 0 and not child.stderr, f"{mode} compile refused; exact stderr retained")
        binaries[str(binary)] = digest(binary)
        linked = run(["ldd", str(binary)], root)
        (output / f"{mode}-ldd.txt").write_bytes(linked.stdout + linked.stderr)
        require(linked.returncode == 0 and not linked.stderr, "linked library admission refused")
        for token in re.findall(rb"/[^\s()]+", linked.stdout):
            library = Path(os.fsdecode(token)).resolve()
            require(library.is_file(), "nonregular linked library")
            libraries[str(library)] = digest(library)
        process = run([str(binary)], root, environment)
        (output / f"{mode}-child.stdout").write_bytes(process.stdout)
        (output / f"{mode}-child.stderr").write_bytes(process.stderr)
        require(process.returncode == 0 and not process.stderr, f"{mode} control refused; exact child output retained")
        result = json.loads(process.stdout)
        require(result["synthetic_file_process_transport_entropy_APIs"] is True and
                result["real_host_EVP_file_digests"] is True and
                all(result[key] is False for key in ("Windows_execution", "original_owner_or_server", "Map_READY_or_world_authority")),
                "scope barrier changed")
        require(all(value not in process.stdout + process.stderr for value in
                    (b"PRIVATE_POLICY_SENTINEL", b"PRIVATE_MAP_SENTINEL", b"PRIVATE_SELF_SENTINEL", b"4242", b"123456")),
                "private synthetic sentinel escaped")
        results[mode] = result
    require(all(result == results["release"] for result in results.values()), "cross-mode results differ")
    after = {str(path): digest(root / path) for path in sorted(source_paths)}
    require(before == after, "source changed during new qualification")
    require(system_before == {str(path): digest(path) for path in sorted(system_paths)}, "compiler/header changed")
    require(all(digest(Path(path)) == value for path, value in binaries.items()), "executable changed")
    require(all(digest(Path(path)) == value for path, value in libraries.items()), "linked library changed")
    require(run(["git", "rev-parse", "HEAD"], root).stdout.decode().strip() == source_head, "HEAD changed")
    receipt = {"schema": "coh-fresh-windows-backend-host-controls-v1", "head": source_head,
               "source_before": before, "source_after": after, "compiler_and_header_sha256": system_before,
               "linked_library_sha256": libraries, "executable_sha256": binaries, "commands": commands,
               "results": results, "scope": "new backend using explicit Win32/process/file/transport/entropy doubles, real host EVP synthetic-byte digests",
               "Windows_compiler_or_header_ABI_or_execution": False, "original_owner_or_controllers_executed": False,
               "same_realm_Map_READY_observed": False, "actual_allocation_or_SQL": False,
               "world_authority": False, "leak_sanitizer_enabled": False}
    (output / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"passed": True, "source_inputs": len(before), "compiler_header_inputs": len(system_before),
                      "modes": list(results), "scenarios_per_mode": results["release"]["scenarios"],
                      "checks_per_mode": results["release"]["checks"]}))


if __name__ == "__main__":
    main()
