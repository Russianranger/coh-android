#!/usr/bin/env python3
"""Focused occupied-owner refusal with actual private host EGL/GLES.

This does not replay accepted renderer suites or qualify Android/world entry.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FLAGS = ["-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic", "-ffp-contract=off"]


def require(value, code):
    if not value:
        raise ValueError("COH_RENDERER_OWNER_" + code)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command, output, label, env=None, must_pass=True):
    child = subprocess.run(list(map(str, command)), cwd=ROOT, capture_output=True,
                           timeout=90, env=env)
    require(len(child.stdout) + len(child.stderr) < 1024 * 1024, "OUTPUT_BOUND")
    (output / (label + ".stdout")).write_bytes(child.stdout)
    (output / (label + ".stderr")).write_bytes(child.stderr)
    if must_pass:
        require(child.returncode == 0, "CHILD_" + label)
    return child


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-root", "host-headers", "host-egl", "host-gles", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    require(__debug__ and args.source_root.resolve() == ROOT, "SOURCE_ROOT")
    output = args.output.absolute()
    require(not output.exists() and output.parent.is_dir(), "FRESH_OUTPUT")
    headers = args.host_headers.resolve()
    manifest = HERE.parent / "world-render-adapter/egl-host-header-pins.json"
    header_pins = json.loads(manifest.read_bytes())
    for name, pin in header_pins.items():
        path = headers / name
        require(path.is_file() and not path.is_symlink() and
                path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"], "HEADERS")
    compiler = Path(shutil.which("cc")).resolve()
    libraries = {str(p.resolve()): sha(p.resolve()) for p in (args.host_egl, args.host_gles)}
    sources = [HERE / n for n in ("coh_renderer.c", "coh_renderer_gles.c", "tests/create_ownership.c")]
    dep = subprocess.run([compiler, *FLAGS, "-I" + str(headers), "-MM", *sources],
                         cwd=ROOT, capture_output=True, text=True, timeout=30)
    require(dep.returncode == 0 and len(dep.stdout) < 1024 * 1024, "DEPENDENCIES")
    files = {Path(__file__).resolve(), manifest, HERE / "README.md"}
    for line in dep.stdout.replace("\\\n", " ").splitlines():
        require(":" in line, "DEPENDENCY_SYNTAX")
        for name in shlex.split(line.split(":", 1)[1]):
            path = Path(name).resolve()
            if path.is_relative_to(ROOT):
                files.add(path)
            else:
                require(path.is_relative_to(headers), "HEADER_ROOT")
    pins = {str(path.relative_to(ROOT)): sha(path) for path in sorted(files)}
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                       text=True, timeout=30).strip()
    output.mkdir(mode=0o700)
    environment = dict(os.environ, EGL_PLATFORM="surfaceless",
                       ASAN_OPTIONS="detect_leaks=0:halt_on_error=1",
                       UBSAN_OPTIONS="halt_on_error=1")
    modes = {"release": ["-O2"],
             "asan": ["-O1", "-g", "-fsanitize=address", "-fno-omit-frame-pointer", "-no-pie"],
             "ubsan": ["-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all"]}
    link = ["-Wl,--wrap=calloc", "-Wl,--wrap=free", args.host_egl.resolve(),
            args.host_gles.resolve(), "-lm"]
    results = {}
    for mode, flags in modes.items():
        executable = output / mode
        run([compiler, *FLAGS, *flags, "-I" + str(headers), *sources, *link, "-o", executable],
            output, "compile-" + mode)
        value = json.loads(run([executable], output, "execute-" + mode, environment).stdout)
        expected = {"passed": True, "checks": 44, "project_allocations": 4, "project_frees": 4,
                    "actual_gles": True, "frames": 2, "occupied_owner_refusals": 2,
                    "dirty_error_preserved": True, "cleanup_verified": True,
                    "android_executed": False, "world_authority": False, "actor_authority": False}
        require(set(value) == set(expected) | {"gl_version", "gl_renderer"}, "NATIVE_FIELDS")
        for key, wanted in expected.items():
            require(type(value[key]) is type(wanted) and value[key] == wanted, "NATIVE_" + key)
        for key in ("gl_version", "gl_renderer"):
            require(type(value[key]) is str and 0 < len(value[key]) < 192 and
                    all(32 <= ord(c) < 127 for c in value[key]), "GL_IDENTITY")
        require(value["gl_version"].startswith("OpenGL ES 3."), "GLES3")
        results[mode] = {"native": value, "binary_sha256": sha(executable)}
    require(all(result["native"] == results["release"]["native"]
                for result in results.values()), "MODE_RESULTS")
    mutations = []
    for index in (0, 1):
        source = sources[index]
        text = source.read_text()
        guard = "  if (*out)\n    return COH_STATE;\n"
        require(text.count(guard) == 1, "MUTATION_TARGET")
        mutant = output / (source.stem + "-unguarded.c")
        mutant.write_text(text.replace(guard, ""))
        mutated = list(sources)
        mutated[index] = mutant
        executable = output / (source.stem + "-unguarded")
        run([compiler, *FLAGS, "-O2", "-I" + str(headers), "-I" + str(HERE),
             *mutated, *link, "-o", executable], output, "compile-mutation-" + source.stem)
        child = run([executable], output, "execute-mutation-" + source.stem,
                    environment, must_pass=False)
        require(child.returncode != 0 and b"ownership check failed" in child.stderr,
                "MUTATION_SURVIVED")
        mutations.append({"source": str(source.relative_to(ROOT)),
                          "removed_occupied_owner_refusal": True,
                          "returncode": child.returncode, "binary_sha256": sha(executable)})
    require(pins == {name: sha(ROOT / name) for name in pins}, "SOURCE_CHANGED")
    require(libraries == {str(p.resolve()): sha(p.resolve())
                          for p in (args.host_egl, args.host_gles)}, "LIBRARIES_CHANGED")
    for name, pin in header_pins.items():
        require(sha(headers / name) == pin["sha256"], "HEADERS_CHANGED")
    require(all(sha(output / mode) == result["binary_sha256"]
                for mode, result in results.items()), "BINARIES_CHANGED")
    proof = {"schema": "coh-renderer-create-owner-egl-v1", "passed": True,
             "base_revision": revision, "source_sha256": pins,
             "working_tree_sources_verified_before_after": True,
             "header_pins": header_pins, "compiler_path": str(compiler),
             "compiler_sha256": sha(compiler),
             "compiler_version": subprocess.check_output([compiler, "--version"], text=True).splitlines()[0],
             "declared_host_library_files": libraries, "results": results,
             "mode_flags": modes, "semantic_mutations_refused": mutations,
             "actual_host_gles_executed": True, "system_driver_sanitized": False,
             "loaded_driver_mapping_verified": False, "asan_leak_detection": False,
             "android_built": False, "android_executed": False, "physical_thor": False,
             "controlled_texture_geometry_only": True,
             "original_client_material_qualified": False,
             "source_generation_admitted": False, "world_authority": False, "actor_authority": False}
    (output / "qualification.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"passed": True, "modes": list(results), "actual_host_gles_executed": True,
                      "checks_per_mode": 44, "semantic_mutations_refused": len(mutations),
                      "android_executed": False, "world_authority": False}))


if __name__ == "__main__":
    main()
