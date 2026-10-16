"""Strict, byte-bound evidence for standalone catalog/scene/entity contracts."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import math
import re
import struct
import subprocess

ABIS = {"arm64-v8a": 183, "x86_64": 62}
MODULES = ("scenecatalog", "scenegraph", "entities")
FIXTURES = {"scenecatalog": "catalog_fixtures.h", "scenegraph": "scenegraph_fixtures.h", "entities": "fixtures.h"}
REQUIRED_SOURCES = {name: {"native-android/engine/" + name + "/" + suffix for suffix in
    ("check.py", "coh_" + name + ".c", "coh_" + name + ".h",
     ("" if name == "entities" else "tests/") + "test_" + name + ".c")} for name in MODULES}
REQUIRED_SOURCES["scenecatalog"].update({"native-android/engine/scenecatalog/source_export.inc",
                                       "native-android/engine/scenecatalog/tests/source_catalog_harness.c",
                                       "native-android/engine/scenecatalog/tests/test_walk.c.inc",
                                       "native-android/engine/scenecatalog/coh_catalog_owner.c",
                                       "native-android/engine/scenecatalog/coh_catalog_owner.h",
                                       "native-android/engine/scenecatalog/tests/test_owner.c.inc"})
REQUIRED_SOURCES["entities"].update({"native-android/engine/entities/" + name for name in
    ("coh_costume.c", "coh_costume.h", "test_costume.c", "costume_oracle.py", "costume_oracle_shim.h",
     "costume_envelope_oracle_shim.h", "costume_envelope_oracle.c.inc", "costume_envelope_fixture.c.inc",
     "power_custom_oracle_shim.h", "power_custom_observer.c.inc", "power_custom_fixture.c.inc",
     "titles_oracle_shim.h", "titles_fixture.c.inc", "test_titles.c.inc",
     "taskforce_oracle_shim.h", "taskforce_fixture.c.inc", "test_taskforce.c.inc",
     "coh_taskforce.c", "coh_taskforce.h",
     "rare_oracle_shim.h", "rare_fixture.c.inc", "test_rare.c.inc")})
REQUIRED_SOURCES["scenegraph"].update({"native-android/engine/scenegraph/" + name for name in
    ("coh_scene_metadata.c", "coh_scene_metadata.h", "tests/metadata_source_harness.inc",
     "check_lookup.py", "lookup-source-pins.json", "coh_scene_lookup.c", "coh_scene_lookup.h",
     "tests/lookup_oracle_shim.h", "tests/test_scene_lookup.c",
     "coh_scene_compact.c", "coh_scene_compact.h", "tests/test_scene_compact.c")})
CLAIMS = ("physical_thor_accepted", "actual_server_interoperability_verified",
          "real_account_login_verified", "full_live_world_verified", "gates25_27_complete",
          "accepted_apks_rebuilt")
FALSE_ALIASES = ("live_world", "real_authenticated_server", "actual_authentication",
                 "real_server_capture", "thor_accepted", "real_server_interoperability")
SCHEMA = "coh-scenecatalog-android-v1"
HEX = re.compile(r"[a-f0-9]{64}\Z")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def loads(text):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("Duplicate JSON object key: " + key)
            value[key] = item
        return value
    def constant(value):
        raise ValueError("Non-finite JSON number: " + value)
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number: " + value)
        return number
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite)


def read(path):
    return loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(label + " must be a JSON object")
    return value


def relative_name(value):
    if (not isinstance(value, str) or not value or "\\" in value or "\x00" in value
            or PurePosixPath(value).is_absolute()
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ValueError("Artifact/source path must be a canonical relative POSIX path")
    return value


def child(root, relative):
    root = Path(root).resolve()
    target = (root / relative_name(relative)).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("Artifact/source file is missing or outside its root")
    return target


def hash_value(value):
    if not isinstance(value, str) or HEX.fullmatch(value) is None:
        raise ValueError("Expected a lowercase SHA-256 digest")
    return value


def source_hashes(value):
    mapping(value, "Source inventory")
    if not value:
        raise ValueError("Source inventory must be nonempty")
    for name, sha in value.items():
        relative_name(name)
        hash_value(sha)
    return value


def suite_sources(module, value):
    source_hashes(value)
    if not REQUIRED_SOURCES[module].issubset(value):
        raise ValueError("Source inventory omits a required module build/oracle input: " + module)
    return value


def verify_sources(repo, sources):
    for relative, sha in source_hashes(sources).items():
        if digest(child(repo, relative)) != sha:
            raise ValueError("Qualified source bytes differ: " + relative)


def elf_identity(path, abi):
    with Path(path).open("rb") as stream:
        header = stream.read(64)
    if (len(header) != 64 or header[:7] != b"\x7fELF\x02\x01\x01"
            or struct.unpack_from("<H", header, 16)[0] != 3
            or struct.unpack_from("<H", header, 18)[0] != ABIS[abi]
            or struct.unpack_from("<I", header, 20)[0] != 1):
        raise ValueError("Executable must be a 64-bit little-endian PIE of the claimed ABI")


def git_state(repo):
    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(repo), *arguments], text=True).strip()
    return {"source_revision": git("rev-parse", "HEAD"),
            "source_git_status_porcelain": git("status", "--porcelain=v1", "--untracked-files=normal").splitlines()}


def reject_claims(value, required=False):
    mapping(value, "Receipt")
    for key in CLAIMS + FALSE_ALIASES:
        if (required and key in CLAIMS) or key in value:
            if value.get(key) is not False:
                raise ValueError("Standalone contract has an unsupported acceptance claim: " + key)


def reject_compile_claims(value):
    reject_claims(value)
    for key in ("android_executed", "emulator_qualified", "physical_android_executed", "executed", "execution_qualified"):
        if key in value and value[key] is not False:
            raise ValueError("Host/build receipt cannot claim Android execution: " + key)


def native_result(value):
    mapping(value, "Native contract result")
    if (value.get("passed") is not True or type(value.get("checks")) is not int
            or not 0 < value["checks"] < 1_000_000_000):
        raise ValueError("Native contract must report passed=true and a positive integer check count")
    reject_claims(value)
    return value


def json_equal(left, right):
    """JSON booleans and integers are different evidence types."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    return left == right


def execute(command, log, timeout=1200, env=None):
    """Retain stdout/stderr for successful, failed and timed-out commands."""
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("wb") as stream:
        try:
            process = subprocess.run([str(arg) for arg in command], stdout=stream,
                                     stderr=subprocess.STDOUT, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Timed out after {timeout}s; diagnostic log: {log.name}") from None
    if process.returncode:
        raise RuntimeError(f"Command exited {process.returncode}; diagnostic log: {log.name}")
    return log.read_text()
