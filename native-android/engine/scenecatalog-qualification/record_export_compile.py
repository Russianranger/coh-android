#!/usr/bin/env python3
"""Retain an opt-in, nonshipping Win32 export compile experiment; never run it."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import struct

from common import child, digest, git_state, json_equal, read, write

HERE = Path(__file__).resolve().parent


def pe32_identity(path):
    """Require a bounded PE32 i386 executable, not a DLL or a renamed artifact."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 1024 <= path.stat().st_size <= 128 * 1024 * 1024:
        raise ValueError("Expected a regular bounded MapServer executable")
    with path.open("rb") as stream:
        dos = stream.read(64)
        if dos[:2] != b"MZ":
            raise ValueError("MapServer must have a DOS/PE header")
        offset = struct.unpack_from("<I", dos, 60)[0]
        if not 64 <= offset <= min(1024 * 1024, path.stat().st_size - 120):
            raise ValueError("Invalid PE header offset")
        stream.seek(offset)
        header = stream.read(120)
    machine, sections = struct.unpack_from("<HH", header, 4)
    optional_size, flags = struct.unpack_from("<HH", header, 20)
    if (header[:4] != b"PE\0\0" or machine != 0x14c or not 0 < sections <= 96
            or optional_size < 96 or flags & 0x2000 or not flags & 0x0002
            or offset + 24 + optional_size + sections * 40 > path.stat().st_size
            or struct.unpack_from("<H", header, 24)[0] != 0x10b
            or struct.unpack_from("<I", header, 40)[0] == 0):
        raise ValueError("MapServer must be an executable PE32 i386 image")


def validate_inputs(value, helper):
    expected = {"format": 1, "status": "exact_published_inputs_staged",
        "donor_commit": "74fe247be85173e618f1af2c8af71b1316de4cd8",
        "donor_apk": helper.DONOR, "asset_release": "coh-assets-v1.0.0", "base_volume": helper.BASE,
        "files": {**helper.INPUTS, "fxinfo-full.bin": helper.fx.BASE},
        "donor_rebuilt": False, "assets_republished": False,
        "native_runtime_execution_validated": False, "physical_execution_validated": False}
    if not json_equal(value, expected):
        raise ValueError("Expected the complete exact published startup-input admission receipt")
    return expected


def cmake_identity(path, staged):
    fields = {}
    for line in Path(path).read_text().splitlines():
        if not line or line.startswith(("#", "//")) or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name in fields:
            raise ValueError("Duplicate CMake cache key")
        fields[name] = value
    if (fields.get("CMAKE_GENERATOR:INTERNAL") != "Visual Studio 18 2026"
            or fields.get("CMAKE_GENERATOR_PLATFORM:INTERNAL") != "Win32"
            or "OptDebug" not in fields.get("CMAKE_CONFIGURATION_TYPES:STRING", "").split(";")
            or Path(fields.get("CMAKE_HOME_DIRECTORY:INTERNAL", "")).resolve() != staged.resolve()):
        raise ValueError("Expected the isolated VS2026 Win32 MapServer source/build cache")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=HERE.parents[2])
    parser.add_argument("--staged-source", type=Path, required=True)
    parser.add_argument("--inputs-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    repo, staged, out = args.source_root.resolve(), args.staged_source.resolve(), args.output.resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        parser.error("--output must be empty; retain prior compile experiment evidence")
    proof = {"schema": "coh-scenecatalog-export-compile-v1", "passed": False,
        "experimental": True, "compile_only": True, "nonshipping": True, "shipping_executable": False,
        "runtime_executed": False, "android_executed": False, "deployed": False,
        "accepted_apks_rebuilt": False, "errors": {}, "scope": "Win32 MapServer compilation only; no catalog emitted or runtime deployed"}
    try:
        state = git_state(repo)
        proof.update(state)
        if args.require_clean and state["source_git_status_porcelain"]:
            raise ValueError("Compile evidence requires a clean source checkout")
        helper_path = child(repo, "native-android/engine/scenecatalog-server/stage_export.py")
        spec = importlib.util.spec_from_file_location("coh_nonshipping_catalog_stage", helper_path)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        receipt = helper.verify_staged(repo, staged)
        if (receipt.get("build_role") != helper.ROLE or receipt.get("build_targets") != ["MapServer"]
                or receipt.get("contract", {}).get("nonshipping") is not True
                or receipt.get("contract", {}).get("runtime_executed") is not False
                or receipt.get("contract", {}).get("deployed") is not False):
            raise ValueError("Expected the verified explicit nonshipping export overlay")
        binary = child(staged, "out/build/vs2026/bin/OptDebug/MapServer.exe")
        cache = child(staged, "out/build/vs2026/CMakeCache.txt")
        pe32_identity(binary)
        cmake_identity(cache, staged)
        inputs_helper_path = child(repo, "tools/android/interactive/map_startup_inputs.py")
        inputs_spec = importlib.util.spec_from_file_location("coh_exact_map_startup_inputs", inputs_helper_path)
        inputs_helper = importlib.util.module_from_spec(inputs_spec)
        inputs_spec.loader.exec_module(inputs_helper)
        inputs = validate_inputs(read(args.inputs_receipt), inputs_helper)
        inputs_helper.checked(args.inputs_receipt.parent / "COH-Atlas-Gameplay-0.13.31.apk", inputs_helper.DONOR)
        for name, identity in inputs["files"].items():
            inputs_helper.checked(args.inputs_receipt.parent / name, identity)
        files = {"MapServer.exe": binary, "CMakeCache.txt": cache,
                 helper.RECEIPT: child(staged, helper.RECEIPT), helper.PRIOR: child(staged, helper.PRIOR),
                 "map-startup-inputs.json": args.inputs_receipt.resolve()}
        for name in (*receipt["patched_sha256"], *receipt["overlay_sha256"]):
            files["source/" + name] = child(staged, name)
        out.mkdir(parents=True, exist_ok=True)
        for name, source in files.items():
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation preserves prior evidence even after a partial failure.
            with source.open("rb") as original, target.open("xb") as destination:
                shutil.copyfileobj(original, destination)
        proof.update(build_role=helper.ROLE, build_target="MapServer", configuration="OptDebug",
            pe_machine="i386", generator="Visual Studio 18 2026", platform="Win32",
            source_stage_verified=True, stage_receipt_sha256=digest(staged / helper.RECEIPT),
            published_inputs_reverified=True, inputs_driver_sha256=digest(inputs_helper_path),
            producer_driver_sha256=digest(Path(__file__)), workflow_sha256=digest(repo / ".github/workflows/native-scene-catalog.yml"),
            artifacts={name: {"sha256": digest(out / name), "bytes": (out / name).stat().st_size} for name in files})
        state_end = git_state(repo)
        if (state_end["source_revision"] != state["source_revision"]
                or (args.require_clean and state_end["source_git_status_porcelain"])):
            raise ValueError("Source checkout changed while recording compile evidence")
        helper.verify_staged(repo, staged)
        proof["passed"] = True
    except Exception as error:
        proof["errors"]["compile_record"] = str(error)
    write(out / "compile-only-receipt.json", proof)
    print(json.dumps(proof, indent=2, sort_keys=True))
    return 0 if proof["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
