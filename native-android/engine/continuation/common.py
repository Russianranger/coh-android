"""Strict receipt helpers for the additive primary protocol qualification."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess

ABIS = {"arm64-v8a": 183, "x86_64": 62}
MODULES = ("scenegraph", "entities", "auth-interop")
FIXTURES = {"scenegraph": "scenegraph_fixtures.h", "entities": "fixtures.h"}
CLAIMS = ("physical_thor_accepted", "actual_server_interoperability_verified",
          "real_account_login_verified", "full_live_world_verified", "gates25_27_complete",
          "accepted_apks_rebuilt")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def child(root, relative):
    root = Path(root).resolve()
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Artifact path must remain inside its artifact root")
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("Artifact is missing or outside its artifact root")
    return target


def elf_identity(path, abi):
    with Path(path).open("rb") as stream:
        header = stream.read(64)
    if (len(header) != 64 or header[:7] != b"\x7fELF\x02\x01\x01"
            or struct.unpack_from("<H", header, 16)[0] != 3
            or struct.unpack_from("<H", header, 18)[0] != ABIS[abi]):
        raise ValueError("Executable must be a 64-bit little-endian PIE of the claimed ABI")


def git_state(repo):
    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(repo), *arguments], text=True).strip()
    return {"source_revision": git("rev-parse", "HEAD"),
            "source_git_status_porcelain": git("status", "--porcelain=v1", "--untracked-files=normal").splitlines()}


def native_result(value):
    if (not isinstance(value, dict) or value.get("passed") is not True
            or type(value.get("checks")) is not int or value["checks"] <= 0):
        raise ValueError("Native contract must report passed=true and a positive integer check count")
    for key in CLAIMS + ("live_world", "real_authenticated_server", "actual_authentication"):
        if key in value and value[key] is not False:
            raise ValueError("A standalone contract cannot claim full-server or physical qualification")
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
    """Retain stdout/stderr even when a compiler/test fails or times out."""
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
