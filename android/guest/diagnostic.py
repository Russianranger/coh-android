#!/usr/bin/env python3
"""Owned ARM64 Linux/Wine diagnostic, invoked inside ONE PRoot --sysvipc session.

This does not launch CoH, alter a game database, or prove Android gameplay.
Stdout is bounded JSON lines; the atomic, redacted receipt is latest-report.json.
"""
import argparse
import datetime
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import secrets
import signal
import socket
import stat
import struct
import subprocess
import sys
import threading
import time

OWNER = {"format": 1, "purpose": "coh-android-diagnostic"}
RUNTIME_MARKER = "COH_RUNTIME_PROBE_V1 PASS bits=32 dll=verified"
PROBE_MARKERS = (
    "PASS all 65 stock DbServer ODBC connections coexist",
    "PASS ID ordering, deleted highest ID, rollback and bulk-import startup state",
    "PASS indexes: duplicate field names, idempotence, schema isolation, legacy cleanup",
    "PASS foreign keys: absent table/constraint removal, add/remove, child rows, orphan rejection",
    "PASS bound values: integer limits, byte 255, float, UTF-16, timestamp, 32 KiB bytea chunks, long text and NULL",
    "PASS SQLColumns: canonical PostgreSQL types, Unicode varchar, text and bytea",
    "PASS atomic schema rebuild: row data, deleted-highest ID, foreign keys, indexes, conversion/dependency rollback, ASCII name keys",
    "PASS column migration and connection reopen",
)
VERIFY_MARKER = "PASS persisted fixture after reconnect/restart/restore"
OUTPUT_LIMIT = 2 * 1024 * 1024
REQUIRED_ASSETS = ("001-coh-compat.sql", "odbc_probe.exe", "psqlodbc_x86.msi",
                   "runtime-probe.exe", "probe.dll")


class DiagnosticError(RuntimeError):
    pass


class Cancelled(DiagnosticError):
    pass


def require(condition, message):
    if not condition:
        raise DiagnosticError(message)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def redact(text, secrets):
    for secret in sorted((s for s in secrets if s), key=len, reverse=True):
        text = text.replace(secret, "[redacted]")
    text = re.sub(r"(?i)\b(password|pwd|pgpassword)\s*[=:]\s*(?:\{[^}]*\}|[^;\s]+)",
                  r"\1=[redacted]", text)
    return text


def redacted_value(value, secrets):
    # Redact before encoding; editing JSON text can consume closing delimiters.
    if isinstance(value, str):
        return redact(value, secrets)
    if isinstance(value, dict):
        return {key: redacted_value(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [redacted_value(item, secrets) for item in value]
    return value


def private_write(path, text):
    require(not path.is_symlink(), "Refusing a symlink output")
    temporary = path.with_name(path.name + ".tmp-" + secrets.token_hex(6))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def private_dir(path):
    require(not path.is_symlink(), "Refusing a symlink directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(path.is_dir(), "Expected an owned directory")
    os.chmod(path, 0o700)
    return path


def owned_workspace(state):
    state = Path(state)
    require(state.is_absolute() and state != Path("/") and not state.is_symlink(),
            "State must be an absolute app-owned directory")
    private_dir(state)
    root = state / "diagnostic"
    require(not root.is_symlink(), "Refusing a symlink diagnostic workspace")
    marker = root / ".coh-diagnostic-owner.json"
    if root.exists():
        require(root.is_dir(), "Diagnostic workspace is not a directory")
        if marker.exists():
            require(not marker.is_symlink(), "Refusing a symlink ownership marker")
            try:
                require(json.loads(marker.read_text()) == OWNER, "Diagnostic ownership marker differs")
            except (ValueError, OSError) as exc:
                raise DiagnosticError("Invalid diagnostic ownership marker") from exc
        else:
            require(not any(root.iterdir()), "Refusing populated unmarked diagnostic workspace")
    private_dir(root)
    if not marker.exists():
        private_write(marker, json.dumps(OWNER) + "\n")
    return root


def validate_probe(output, *, verify=False):
    headers = re.findall(r"^psqlODBC ([0-9.]+); pointer bits (\d+); SQLWCHAR bytes (\d+)\s*$",
                         output, re.MULTILINE)
    require(len(headers) == 1 and headers[0][1:] == ("32", "2"),
            "ODBC probe did not prove PE32 and 2-byte SQLWCHAR")
    lines = output.splitlines()
    markers = (VERIFY_MARKER,) if verify else PROBE_MARKERS
    require(all(lines.count(marker) == 1 for marker in markers), "ODBC probe acceptance markers missing or duplicated")
    require(not re.search(r"(?im)^(FAIL\b|ODBC failure\b)", output), "ODBC probe reported failure")
    return {"driver_version": headers[0][0], "pointer_bits": 32,
            "sqlwchar_bytes": 2, "checks": list(markers)}


def validate_runtime_probe(output):
    require(output.splitlines().count(RUNTIME_MARKER) == 1,
            "Runtime probe did not prove Win32 DLL loading")
    require(not re.search(r"(?im)^(FAIL\b|COH_RUNTIME_PROBE_V1 FAIL\b)", output),
            "Runtime probe reported failure")
    return {"pointer_bits": 32, "dll_export_verified": True, "odbc_manager_loaded": True}


def validate_client_probe(output, *, require_pass=True):
    """Accept observed pixels/input only; extension presence is inventory, not proof."""
    prefix = "COH_CLIENT_PROBE_V1 "
    lines = [line for line in output.splitlines() if line.startswith("COH_CLIENT_PROBE_V1")]
    require(len(lines) == 1 and lines[0].startswith(prefix) and len(lines[0]) <= 16384,
            "Client probe needs one bounded result")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Client probe contains duplicate JSON keys")
            result[key] = value
        return result
    try:
        result = json.loads(lines[0][len(prefix):], object_pairs_hook=unique_object)
    except ValueError as exc:
        raise DiagnosticError("Client probe result is not JSON") from exc
    require(isinstance(result, dict) and type(result.get("format")) is int
            and result["format"] == 1 and result.get("pointer_bits") == 32
            and result.get("scope") == "headless_wgl_client_capabilities"
            and result.get("status") in ("passed", "failed"), "Client probe contract differs")
    for key in ("cg_shaders_validated", "game_rendering_validated", "android_surface_validated",
                "hardware_acceleration_validated"):
        require(result.get(key) is False, "Client fixture cannot validate " + key)
    gl, render, inputs, audio = (result.get(key) for key in ("gl", "render", "input", "audio"))
    require(all(isinstance(item, dict) for item in (gl, render, inputs, audio)),
            "Client capability evidence missing")
    require(inputs.get("scope") == "synthetic_own_window_and_device_creation_only"
            and inputs.get("physical_input_validated") is False
            and audio.get("scope") == "device_enumeration_only"
            and audio.get("playback_validated") is False
            and gl.get("pbuffer_exercised") is False, "Client probe exceeds its exercised scope")
    require(isinstance(result.get("failure_stage"), str) and len(result["failure_stage"]) <= 128,
            "Client failure stage missing")
    if result["status"] == "passed":
        require(result["failure_stage"] == "", "Successful client probe reports a failure")
        for key in ("vendor", "renderer", "version"):
            require(isinstance(gl.get(key), str) and 0 < len(gl[key]) <= 512,
                    "Missing observed OpenGL " + key)
        require(gl.get("renderer_class") in ("software", "unclassified"),
                "Client fixture cannot classify hardware acceleration")
        require(render.get("textured_quad_verified") is True and render.get("swap_buffers") is True
                and type(render.get("samples_verified")) is int and render["samples_verified"] == 4,
                "Client probe did not verify textured rendering and buffer swap")
        pixels = render.get("rgb_samples")
        require(isinstance(pixels, list) and len(pixels) == 4, "Client pixel readback missing")
        expected = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255))
        for pixel, target in zip(pixels, expected):
            require(isinstance(pixel, list) and len(pixel) == 3
                    and all(type(value) is int and 0 <= value <= 255 and abs(value - wanted) <= 3
                            for value, wanted in zip(pixel, target)), "Client pixel readback differs")
        require(inputs.get("window_messages_verified") is True
                and inputs.get("keyboard_message_mask") == 3 and inputs.get("mouse_message_mask") == 7
                and inputs.get("directinput_devices_created") is True
                and type(inputs.get("directinput_hresult")) is int and inputs["directinput_hresult"] == 0,
                "Client probe did not exercise required Windows input plumbing")
    else:
        require(bool(result["failure_stage"]), "Failed client probe needs a failure stage")
    if require_pass:
        require(result["status"] == "passed", "Client capability fixture failed: " + result["failure_stage"])
    return result


def validate_odbc_driver(output):
    """Require observed PE32 registration plus a loaded native driver DLL."""
    lines = output.splitlines()
    names = [line.removeprefix("COH_ODBC_DRIVER_V1 NAME ") for line in lines
             if line.startswith("COH_ODBC_DRIVER_V1 NAME ")]
    paths = [line.removeprefix("COH_ODBC_DRIVER_V1 DLL ") for line in lines
             if line.startswith("COH_ODBC_DRIVER_V1 DLL ")]
    require(len(names) == 1 and names[0] in ("PostgreSQL Unicode", "PostgreSQL Unicode(x86)"),
            "ODBC driver preflight did not identify one supported registration")
    require(len(paths) == 1 and len(paths[0]) <= 1024
            and re.fullmatch(r"[A-Za-z]:\\[^\x00-\x1f\x7f]+\.dll", paths[0], re.IGNORECASE),
            "ODBC driver preflight did not identify an absolute DLL path")
    require([line for line in lines if line.startswith("COH_ODBC_DRIVER_V1 PASS")]
            == ["COH_ODBC_DRIVER_V1 PASS bits=32"]
            and not any(line.startswith("COH_ODBC_DRIVER_V1 FAIL") for line in lines)
            and not re.search(r"(?m)^FAIL\b", output),
            "ODBC driver preflight did not prove PE32 DLL loading")
    return {"driver_name": names[0], "driver_path": paths[0], "pointer_bits": 32,
            "registry_view": 32, "driver_dll_loaded": True}


class OwnedProcess:
    """One new session/process group; never signal a process found by name."""
    def __init__(self, label, argv, env, input_text=None):
        self.label, self.started = label, time.monotonic()
        self.output = bytearray()
        self.overflow = False
        self.forced_stop = False
        self.recorded = None
        self.process = subprocess.Popen([str(x) for x in argv], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        env=env, start_new_session=True)
        def read():
            try:
                while True:
                    # Buffered read(n) can wait for n bytes from a long-lived server.
                    data = os.read(self.process.stdout.fileno(), 8192)
                    if not data:
                        break
                    if len(self.output) + len(data) > OUTPUT_LIMIT:
                        self.overflow = True
                    else:
                        self.output.extend(data)
            finally:
                self.process.stdout.close()
        def write():
            try:
                if input_text is not None:
                    self.process.stdin.write(input_text.encode("utf-8"))
                    self.process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
            finally:
                self.process.stdin.close()
        self.reader = threading.Thread(target=read, daemon=True)
        self.writer = threading.Thread(target=write, daemon=True)
        self.reader.start()
        self.writer.start()

    def text(self):
        return self.output.decode("utf-8", "replace")

    def stop(self):
        # The original session leader may exit while descendants still hold pipes.
        self.forced_stop = self.process.poll() is None or self.reader.is_alive()
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        self.reader.join(timeout=0.2)
        # Descendants can ignore TERM and close inherited stdout after the leader
        # exits. The original owned group still needs the final bounded signal.
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait(timeout=3)
        self.reader.join(timeout=1)
        self.writer.join(timeout=1)


class Context:
    def __init__(self, state, total_timeout=900):
        self.state = Path(state)
        self.deadline = time.monotonic() + total_timeout
        self.cancel_requested = False
        self.secrets = []
        self.children = []
        self.cleanup_deadline = None
        self.stage_name = "preflight"
        self.report = {"format": 1, "status": "running", "started_utc": utc(),
                       "stages": [], "processes": [], "failures": [],
                       "scope": "Native ARM64 PostgreSQL, Wine/FEX PE32 DLL and ODBC fixtures with clean restart",
                       "passed": False, "gameplay_validated": False,
                       "android_execution_validated": False}

    def event(self, kind, **fields):
        safe = redacted_value(fields, self.secrets)
        print(json.dumps({"type": kind, "stage": self.stage_name, "time_utc": utc(), **safe}), flush=True)

    def stage(self, name):
        self.stage_name = name
        self.check()
        self.report["stages"].append({"stage": name, "started_utc": utc()})
        self.event("stage", status="running")

    def passed(self, **evidence):
        self.report["stages"][-1].update(status="passed", finished_utc=utc(), **evidence)
        self.event("stage", status="passed")

    def cancelled(self):
        return self.cancel_requested or (self.state / "stop-request").exists()

    def check(self):
        if self.cancelled():
            raise Cancelled("Cancellation requested")
        require(time.monotonic() < self.deadline, "Overall diagnostic deadline exceeded")
        for child in self.children:
            require(not child.overflow, "Owned process exceeded output bound: " + child.label)

    def start(self, label, argv, *, env=None, input_text=None, cleanup=False):
        if not cleanup:
            self.check()
        require(len(self.children) < 120, "Process count exceeded bound")
        child = OwnedProcess(label, argv, env or os.environ.copy(), input_text)
        self.children.append(child)
        return child

    def record(self, child):
        if child.recorded is not None:
            return child.recorded
        record = {"label": child.label, "exit_code": child.process.poll(),
                  "forced_stop": child.forced_stop,
                  "elapsed_seconds": round(time.monotonic() - child.started, 3),
                  "output": redact(child.text(), self.secrets)[-16384:]}
        self.report["processes"].append(record)
        child.recorded = record
        if record["output"]:
            self.event("log", label=child.label, message=record["output"][-4096:])
        return record

    def run(self, label, argv, *, timeout=60, env=None, input_text=None, check=True, cleanup=False,
            before_stop=None):
        child = self.start(label, argv, env=env, input_text=input_text, cleanup=cleanup)
        try:
            deadline = time.monotonic() + timeout
            if cleanup and self.cleanup_deadline is not None:
                deadline = min(deadline, self.cleanup_deadline)
            while child.process.poll() is None or child.reader.is_alive():
                if not cleanup:
                    self.check()
                require(not child.overflow, label + " exceeded output bound")
                require(time.monotonic() < deadline, label + " timed out")
                time.sleep(0.05)
            child.writer.join(timeout=1)
            result = self.record(child)
            if check:
                require(result["exit_code"] == 0, label + " failed: " + result["output"][-4096:])
            return result
        except BaseException:
            try:
                if before_stop is not None:
                    try:
                        before_stop(child)
                    except Exception as exc:
                        message = redact(str(exc), self.secrets)[-2048:]
                        self.report.setdefault("observation_failures", []).append(message)
                        self.event("log", label=label + "-observation", message=message)
            finally:
                child.stop()
                self.record(child)
            raise


def windows_path(path):
    return "Z:" + str(Path(path).absolute()).replace("/", "\\")


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_pe32(path):
    with path.open("rb") as handle:
        data = handle.read(65536)
    require(data[:2] == b"MZ" and len(data) >= 64, "Missing PE header: " + path.name)
    offset = struct.unpack_from("<I", data, 60)[0]
    require(offset + 26 <= len(data) and data[offset:offset+4] == b"PE\0\0"
            and struct.unpack_from("<H", data, offset+4)[0] == 0x14c
            and struct.unpack_from("<H", data, offset+24)[0] == 0x10b,
            "Expected PE32 i386: " + path.name)


def verify_assets(assets, *, client_probe=False):
    manifest = json.loads((assets / "runtime-manifest.json").read_text())
    require(manifest.get("format") == 1, "Unsupported runtime asset manifest")
    hashes = {}
    for name in REQUIRED_ASSETS + (("client-probe.exe",) if client_probe else ()):
        path = assets / name
        require(path.is_file() and not path.is_symlink(), "Missing or linked asset: " + name)
        expected = manifest.get("files", {}).get(name)
        if isinstance(expected, dict):
            expected = expected.get("sha256")
        require(isinstance(expected, str) and re.fullmatch(r"[a-f0-9]{64}", expected),
                "Missing asset hash: " + name)
        hashes[name] = file_hash(path)
        require(hashes[name] == expected, "Asset hash mismatch: " + name)
    expected_probe = {"executable": "runtime-probe.exe", "marker": RUNTIME_MARKER, "dll": "probe.dll"}
    require(manifest.get("runtime_probe") == expected_probe, "Runtime probe manifest contract differs")
    for name in ("runtime-probe.exe", "probe.dll", "odbc_probe.exe"):
        verify_pe32(assets / name)
    if client_probe:
        require(manifest.get("client_probe") == {
            "executable": "client-probe.exe", "marker": "COH_CLIENT_PROBE_V1 ",
            "scope": "headless_wgl_client_capabilities", "optional": True},
            "Client probe manifest contract differs")
        verify_pe32(assets / "client-probe.exe")
    return hashes


def arm64_elf(path):
    with path.open("rb") as handle:
        data = handle.read(20)
    require(len(data) == 20 and data[:6] == b"\x7fELF\x02\x01"
            and struct.unpack_from("<H", data, 18)[0] == 183,
            "Expected native ARM64 ELF: " + path.name)


def verify_wine_stopped(prefix, *, server_base=None):
    """Verify the pinned Linux Wine 10 server's exact prefix lock and endpoint.

    server/request.c derives this directory from prefix device/inode and uses a
    POSIX byte-range lock, not flock. A silent `wineserver -k` exit 1 means no
    owner (or a lock error); `-w` itself ignores the fcntl result. Independently
    taking that same lock and refusing a live socket keeps cleanup fail-closed.
    """
    require(not prefix.is_symlink(), "Linked Wine prefix refused")
    prefix_stat = prefix.stat()
    base = Path(server_base) if server_base is not None else Path(f"/tmp/.wine-{os.getuid()}")
    server = base / f"server-{prefix_stat.st_dev:x}-{prefix_stat.st_ino:x}"
    lock = server / "lock"
    require(not base.is_symlink() and not server.is_symlink() and not lock.is_symlink(),
            "Linked Wine server lock refused")
    require(lock.is_file(), "Wine server lock missing; cannot prove prefix shutdown")
    fd = os.open(lock, os.O_RDWR | os.O_NOFOLLOW)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "Wine server lock is not a regular file")
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, 0, os.SEEK_SET)
        except OSError as exc:
            raise DiagnosticError("Wine prefix lock is still owned or cannot be verified") from exc
        endpoint = server / "socket"
        try:
            endpoint_stat = endpoint.lstat()
        except FileNotFoundError:
            return {"prefix_lock_free": True, "server_socket_inactive": True}
        require(stat.S_ISSOCK(endpoint_stat.st_mode), "Wine server endpoint is not a Unix socket")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.25)
            try:
                probe.connect(str(endpoint))
            except OSError as exc:
                require(exc.errno in (errno.ENOENT, errno.ECONNREFUSED),
                        "Wine server endpoint state could not be verified")
            else:
                raise DiagnosticError("Wine prefix server socket still accepts connections")
        return {"prefix_lock_free": True, "server_socket_inactive": True}
    finally:
        os.close(fd)


class Diagnostic:
    def __init__(self, args, context):
        self.args, self.ctx = args, context
        self.root = owned_workspace(args.state)
        self.pgdata = self.root / "pgdata"
        self.socket_dir = private_dir(self.root / "socket")
        self.wineprefix = self.root / "wine"
        require(not self.pgdata.is_symlink() and not self.wineprefix.is_symlink(), "Linked runtime state refused")
        lockpath = self.root / "run.lock"
        require(not lockpath.is_symlink(), "Linked runtime lock refused")
        self.lock = open(lockpath, "a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DiagnosticError("A diagnostic already owns this workspace") from exc
        self.pg = None
        self.xserver = None
        self.wine_started = False
        self.database = "coh_test_" + secrets.token_hex(8)
        self.base_env = os.environ.copy()
        self.base_env.update(HOME=str(args.state), LANG="C", LC_ALL="C", TZ="UTC")
        self.wine_env = self.base_env.copy()
        self.wine_env.update(WINEPREFIX=str(self.wineprefix), WINEARCH="win64", WINEDEBUG="-all,err+module",
                             WINEDLLOVERRIDES="winemenubuilder,mshtml,mscoree=;winedbg.exe=",
                             XDG_RUNTIME_DIR=str(private_dir(self.root / "runtime")))
        self.port = None
        self.credentials = None
        self.database_created = False
        self.cleanup_status = {"postgres_graceful": False, "wine_prefix_stopped": False,
                               "owned_processes_reaped": False}

    def pgtool(self, name):
        return str(self.args.pg_bin / name)

    def sql(self, sql, *, game=False, cleanup=False):
        user = "cohtest" if game else "cohdiag_admin"
        env = self.base_env.copy()
        env["PGPASSWORD"] = self.credentials[user]
        env["PGCONNECT_TIMEOUT"] = "5"
        result = self.ctx.run("sql-" + ("fixture" if game else "admin"),
                              [self.pgtool("psql"), "-X", "-w", "-A", "-t", "-v", "ON_ERROR_STOP=1",
                               "-h", str(self.socket_dir), "-p", str(self.port), "-U", user,
                               "-d", self.database if game else "postgres"],
                              timeout=5 if cleanup else 30, env=env, input_text=sql, cleanup=cleanup)
        return result["output"].strip()

    def initialize(self):
        self.ctx.stage("assets_and_architecture")
        require(platform.machine().lower() in ("aarch64", "arm64"), "Guest must execute on ARM64")
        require(os.geteuid() == 1000, "Guest requires PRoot -i 1000:1000")
        self.ctx.report["asset_sha256"] = verify_assets(self.args.assets, client_probe=self.args.client_probe)
        for name in ("initdb", "postgres", "pg_ctl", "psql"):
            arm64_elf(self.args.pg_bin / name)
        arm64_elf(self.args.wine)
        arm64_elf(self.args.wineserver)
        self.ctx.passed(machine=platform.machine(), guest_uid=os.geteuid(), postgres_native_arm64=True)
        self.ctx.stage("initialize_owned_cluster")
        credentials_path = self.root / "credentials.json"
        require(not credentials_path.is_symlink(), "Linked credentials refused")
        if credentials_path.exists():
            self.credentials = json.loads(credentials_path.read_text())
            require(set(self.credentials) == {"cohdiag_admin", "cohtest"}, "Invalid private credentials")
            require(all(re.fullmatch(r"[0-9a-f]{64}", value) for value in self.credentials.values()),
                    "Invalid private credentials")
        else:
            require(not self.pgdata.exists(), "Refusing cluster without owned credentials")
            self.credentials = {role: secrets.token_hex(32) for role in ("cohdiag_admin", "cohtest")}
            private_write(credentials_path, json.dumps(self.credentials))
        self.ctx.secrets.extend(self.credentials.values())
        os.chmod(credentials_path, 0o600)
        reused = self.pgdata.exists()
        if not reused:
            # A cancelled init never replaces pgdata. Keep partial attempts private;
            # retry in a fresh directory and bound retained interrupted attempts.
            require(len(list(self.root.glob("init-pending-*"))) < 8,
                    "Too many interrupted initializations; reset diagnostic state")
            pending = self.root / ("init-pending-" + secrets.token_hex(8))
            password_file = self.root / "init-password"
            private_write(password_file, self.credentials["cohdiag_admin"] + "\n")
            try:
                self.ctx.run("initdb", [self.pgtool("initdb"), "-D", pending, "-U", "cohdiag_admin",
                                        "--pwfile", password_file, "--auth-local=scram-sha-256",
                                        "--auth-host=scram-sha-256", "--encoding=UTF8", "--locale=C",
                                        "-c", "shared_memory_type=mmap", "-c", "dynamic_shared_memory_type=mmap"],
                             timeout=90, env=self.base_env)
                pending.rename(self.pgdata)
            finally:
                password_file.unlink(missing_ok=True)
        require((self.pgdata / "PG_VERSION").is_file(), "Owned cluster is incomplete")
        status = self.ctx.run("existing-cluster-status", [self.pgtool("pg_ctl"), "-D", self.pgdata, "status"],
                              check=False, env=self.base_env)
        require(status["exit_code"] == 3, "Refusing an already running or unreadable cluster")
        # Kernel chooses the actual loopback port. It is authenticated again after startup.
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.ctx.report["postgres_port"] = self.port
        self.ctx.passed(cluster_reused=reused)

    def start_postgres(self, label):
        self.ctx.stage(label)
        self.cleanup_status["postgres_graceful"] = False
        self.pg = self.ctx.start(label, [self.pgtool("postgres"), "-D", self.pgdata,
            "-c", "listen_addresses=127.0.0.1", "-c", "port=" + str(self.port),
            "-c", "unix_socket_directories=" + str(self.socket_dir),
            "-c", "unix_socket_permissions=0700", "-c", "max_connections=80",
            "-c", "shared_buffers=32MB", "-c", "shared_memory_type=mmap",
            "-c", "dynamic_shared_memory_type=mmap",
            "-c", "fsync=on", "-c", "synchronous_commit=on", "-c", "full_page_writes=on"], env=self.base_env)
        deadline = time.monotonic() + 60
        while True:
            self.ctx.check()
            require(self.pg.process.poll() is None, "PostgreSQL exited before readiness: " + self.pg.text()[-2048:])
            if "database system is ready to accept connections" in self.pg.text():
                break
            require(time.monotonic() < deadline, "PostgreSQL startup timed out")
            time.sleep(0.1)
        actual = self.sql("SELECT current_setting('listen_addresses') || '|' || current_setting('port') || '|' || current_setting('data_directory') || '|' || current_setting('fsync') || '|' || current_setting('synchronous_commit') || '|' || current_setting('full_page_writes');")
        require(actual == f"127.0.0.1|{self.port}|{self.pgdata}|on|on|on", "PostgreSQL connection identity or durability differs")
        version = self.sql("SELECT version();")
        self.ctx.passed(loopback="127.0.0.1", port=self.port, durability_verified=True, server_version=version)

    def stop_postgres(self, *, cleanup=False):
        if self.pg is None:
            return
        pg = self.pg
        try:
            self.ctx.run("postgres-graceful-stop", [self.pgtool("pg_ctl"), "-D", self.pgdata,
                         "-m", "fast", "-w", "-t", "10" if cleanup else "20", "stop"],
                         timeout=12 if cleanup else 25, env=self.base_env, cleanup=cleanup)
            pg.process.wait(timeout=5)
            pg.reader.join(timeout=2)
            require(pg.process.returncode == 0, "PostgreSQL did not exit cleanly")
            require("database system is shut down" in pg.text(), "PostgreSQL clean shutdown marker missing")
            self.cleanup_status["postgres_graceful"] = True
            self.ctx.record(pg)
            self.pg = None
        except BaseException:
            pg.stop()
            self.ctx.record(pg)
            self.pg = None
            raise

    def prepare_database(self):
        self.ctx.stage("restricted_fixture_database")
        # Only the diagnostic-created database is used by the destructive stock probe.
        existing = self.sql("SELECT count(*) FROM pg_database WHERE datname NOT IN ('postgres','template0','template1') AND datname !~ '^coh_test_[0-9a-f]{16}$';")
        require(existing == "0", "Refusing cluster containing non-diagnostic databases")
        role = self.sql("SELECT count(*) FROM pg_roles WHERE rolname='cohtest';")
        if role == "0":
            self.sql("CREATE ROLE cohtest LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '" + self.credentials["cohtest"] + "';")
        require(self.sql("SELECT (NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication)::int FROM pg_roles WHERE rolname='cohtest';") == "1", "Fixture role gained privileged rights")
        self.sql('CREATE DATABASE "' + self.database + '" OWNER cohtest;')
        self.database_created = True
        self.sql("REVOKE ALL ON DATABASE " + self.database + " FROM PUBLIC;")
        self.sql("ALTER DATABASE " + self.database + " SET search_path=dbo,pg_catalog;")
        self.sql("REVOKE CREATE ON SCHEMA public FROM PUBLIC;", game=True)
        self.sql((self.args.assets / "001-coh-compat.sql").read_text(), game=True)
        self.sql((self.args.assets / "001-coh-compat.sql").read_text(), game=True)
        require(self.sql("SELECT current_user || '|' || max(version) FROM coh_meta.schema_version;", game=True) == "cohtest|2", "Compatibility migration identity/version differs")
        self.ctx.passed(database=self.database, role="cohtest", migration_version=2, reapplied=True)

    def start_wine(self):
        self.ctx.stage("wine_prefix_and_driver")
        private_dir(self.wineprefix)
        number = None
        for candidate in range(100, 300):
            if not Path(f"/tmp/.X11-unix/X{candidate}").exists() and not Path(f"/tmp/.X{candidate}-lock").exists():
                number = candidate
                break
        require(number is not None, "No free owned X display")
        self.wine_env["DISPLAY"] = f":{number}"
        self.xserver = self.ctx.start("private-headless-x", [self.args.xserver, f":{number}",
            "-geometry", "800x600", "-depth", "24", "-ac", "-nolisten", "tcp", "-rfbport", "-1",
            "-rfbunixpath", self.root / "runtime" / "vnc.sock", "-rfbunixmode", "0600",
            "-SecurityTypes", "None", "-localhost"], env=self.base_env)
        deadline = time.monotonic() + 20
        while not Path(f"/tmp/.X11-unix/X{number}").exists():
            self.ctx.check()
            require(self.xserver.process.poll() is None, "Headless X server failed: " + self.xserver.text()[-2048:])
            require(time.monotonic() < deadline, "Headless X server startup timed out")
            time.sleep(0.1)
        self.wine_started = True
        self.ctx.run("wineboot", [self.args.wine, "wineboot", "-u"], timeout=150, env=self.wine_env)
        # Wine's MSI ODBC action writes the caller's registry view. Execute the
        # actual PE32 installer so its registration matches the PE32 ODBC client.
        installer = self.wineprefix / "drive_c" / "windows" / "syswow64" / "msiexec.exe"
        verify_pe32(installer)
        self.ctx.report["odbc_installer"] = {"path": r"C:\windows\syswow64\msiexec.exe",
                                              "pointer_bits": 32, "sha256": file_hash(installer)}
        self.ctx.run("install-x86-psqlodbc", [self.args.wine, r"C:\windows\syswow64\msiexec.exe", "/i",
                     windows_path(self.args.assets / "psqlodbc_x86.msi"), "/qn", "/norestart"],
                     timeout=150, env=self.wine_env)
        self.ctx.passed(prefix_owned=True, architecture="win64 with PE32 WoW64/FEX", x_tcp=False, rfb_tcp=False,
                        installer=self.ctx.report["odbc_installer"])
        self.ctx.stage("win32_odbc_driver")
        result = self.ctx.run("odbc-driver-preflight", [self.args.wine,
                              windows_path(self.args.assets / "runtime-probe.exe"), "--odbc-driver"],
                              timeout=60, env=self.wine_env)
        evidence = validate_odbc_driver(result["output"])
        self.ctx.report["odbc_driver"] = evidence
        connection = ("Driver={" + evidence["driver_name"] + "};Servername=127.0.0.1;Port=" + str(self.port)
                      + ";Database=" + self.database + ";Username=cohtest;Password=" + self.credentials["cohtest"]
                      + ";SSLmode=disable;ByteaAsLongVarBinary=0;UseServerSidePrepare=0;\n")
        self.connection = self.root / "odbc-connection.txt"
        private_write(self.connection, connection)
        self.ctx.passed(**evidence)

    def probe(self, *, verify=False):
        self.ctx.stage("odbc_after_restart" if verify else "odbc_fixture")
        argv = [self.args.wine, windows_path(self.args.assets / "odbc_probe.exe"), windows_path(self.connection)]
        if verify:
            argv.append("verify")
        result = self.ctx.run("odbc-verify" if verify else "odbc-fixture", argv, timeout=180,
                              env=self.wine_env, before_stop=self.observe_odbc_failure)
        self.ctx.passed(**validate_probe(result["output"], verify=verify))

    def observe_odbc_failure(self, child):
        """Inspect only the private fixture's sessions before cancelling its client.

        Statements are classified, never copied: connection strings, data values
        and credentials cannot enter this evidence through pg_stat_activity.
        """
        if self.pg is None or self.pg.process.poll() is not None:
            return
        env = self.base_env.copy()
        env.update(PGPASSWORD=self.credentials["cohdiag_admin"], PGCONNECT_TIMEOUT="2",
                   PGOPTIONS="-c statement_timeout=2000")
        query = """WITH activity AS (
SELECT backend_type, state, wait_event_type, wait_event,
       extract(epoch FROM clock_timestamp()-query_start)::integer AS query_age_seconds,
       extract(epoch FROM clock_timestamp()-xact_start)::integer AS transaction_age_seconds,
       CASE
         WHEN query LIKE '%%pg_stat_activity%%' THEN 'connection_pool_count'
         WHEN query LIKE '%%coh_reserve_id%%' THEN 'reserve_container_id'
         WHEN query LIKE '%%coh_container_high_water%%' THEN 'container_high_water'
         WHEN query LIKE '%%coh_rebuild_table%%' THEN 'schema_rebuild'
         WHEN query ~* '^(begin|commit|rollback)' THEN 'transaction_control'
         WHEN query ~* '^(create|alter|drop)' THEN 'schema_operation'
         WHEN query ~* '^(insert|update|delete)' THEN 'fixture_write'
         WHEN query ~* '^select' THEN 'fixture_read'
         WHEN query = '' THEN 'none'
         ELSE 'other'
       END AS operation
FROM pg_stat_activity WHERE datname='%s' AND usename='cohtest'
LIMIT 80)
SELECT json_build_object('session_count', (SELECT count(*) FROM activity),
 'groups', (SELECT coalesce(json_agg(row_to_json(summary)), '[]'::json) FROM (
 SELECT backend_type, state, wait_event_type, wait_event, operation, count(*) AS sessions,
        max(query_age_seconds) AS max_query_age_seconds,
        max(transaction_age_seconds) AS max_transaction_age_seconds
 FROM activity GROUP BY backend_type, state, wait_event_type, wait_event, operation
 ORDER BY count(*) DESC LIMIT 16) summary));""" % self.database
        result = self.ctx.run("odbc-failure-activity", [self.pgtool("psql"), "-X", "-w", "-A", "-t",
                              "-v", "ON_ERROR_STOP=1", "-h", str(self.socket_dir), "-p", str(self.port),
                              "-U", "cohdiag_admin", "-d", "postgres"],
                              timeout=3, env=env, input_text=query, cleanup=True)
        activity = json.loads(result["output"])
        require(isinstance(activity, dict) and isinstance(activity.get("groups"), list)
                and len(activity["groups"]) <= 16 and isinstance(activity.get("session_count"), int)
                and 0 <= activity["session_count"] <= 80, "Invalid bounded ODBC activity result")
        self.ctx.report.setdefault("odbc_failure_activity", []).append({
            "time_utc": utc(), "probe": child.label, "client_alive": child.process.poll() is None,
            **activity, "raw_sql_included": False})

    def execute(self):
        self.initialize()
        self.start_postgres("postgres_first_start")
        self.prepare_database()
        self.start_wine()
        self.ctx.stage("win32_runtime_dll")
        result = self.ctx.run("runtime-probe", [self.args.wine, windows_path(self.args.assets / "runtime-probe.exe")],
                              timeout=60, env=self.wine_env)
        self.ctx.passed(**validate_runtime_probe(result["output"]))
        if self.args.client_probe:
            self.ctx.stage("win32_client_capabilities")
            result = self.ctx.run("client-probe", [self.args.wine,
                windows_path(self.args.assets / "client-probe.exe")], timeout=90,
                env=self.wine_env, check=False)
            evidence = validate_client_probe(result["output"], require_pass=False)
            self.ctx.report["client_probe"] = evidence
            require(result["exit_code"] == 0 and evidence["status"] == "passed",
                    "Client capability fixture failed: " + evidence.get("failure_stage", "unknown"))
            self.ctx.passed(client_probe=evidence)
        self.probe()
        self.ctx.stage("postgres_clean_restart")
        self.stop_postgres()
        self.ctx.passed(same_cluster=True, graceful=True)
        self.start_postgres("postgres_restart_ready")
        self.probe(verify=True)

    def cleanup(self):
        failures = []
        # Android grants 30 seconds after stop-request before terminating PRoot.
        # Reserve time for final process-group reaping and the atomic receipt.
        self.ctx.cleanup_deadline = time.monotonic() + 22
        if self.wine_started:
            try:
                stopped = self.ctx.run("owned-wine-stop", [self.args.wineserver, "-k"], timeout=3,
                                       env=self.wine_env, cleanup=True, check=False)
                waited = self.ctx.run("owned-wine-wait", [self.args.wineserver, "-w"], timeout=5,
                                      env=self.wine_env, cleanup=True)
                require(stopped["exit_code"] in (0, 1), "Wine stop returned an unexpected exit code")
                evidence = verify_wine_stopped(self.wineprefix)
                self.ctx.report["wine_shutdown"] = {"stop_exit_code": stopped["exit_code"],
                                                     "wait_exit_code": waited["exit_code"], **evidence}
                self.cleanup_status["wine_prefix_stopped"] = True
            except Exception as exc:
                failures.append("Wine cleanup: " + str(exc))
        if self.pg is not None:
            if self.database_created and self.pg.process.poll() is None:
                try:
                    self.sql('DROP DATABASE "' + self.database + '";', cleanup=True)
                except Exception as exc:
                    failures.append("Fixture cleanup: " + str(exc))
            try:
                self.stop_postgres(cleanup=True)
            except Exception as exc:
                failures.append("PostgreSQL cleanup: " + str(exc))
        if self.xserver is not None:
            self.xserver.stop()
            self.ctx.record(self.xserver)
        for child in self.ctx.children:
            if child.process.poll() is None or child.reader.is_alive():
                child.stop()
        self.cleanup_status["owned_processes_reaped"] = all(c.process.poll() is not None for c in self.ctx.children)
        (self.root / "odbc-connection.txt").unlink(missing_ok=True)
        self.lock.close()
        return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path("/state"))
    parser.add_argument("--assets", type=Path, default=Path("/opt/coh"))
    parser.add_argument("--pg-bin", type=Path, default=Path("/opt/coh/pgsql/bin"))
    parser.add_argument("--wine", type=Path, default=Path("/opt/wine/bin/wine"))
    parser.add_argument("--wineserver", type=Path, default=Path("/opt/wine/bin/wineserver"))
    parser.add_argument("--xserver", type=Path, default=Path("/usr/bin/Xtigervnc"))
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--execution-platform", choices=("android", "host"), default="host")
    parser.add_argument("--android-metadata", type=Path)
    parser.add_argument("--client-probe", action="store_true",
                        help="Also exercise headless Win32 WGL and synthetic input; no gameplay claim")
    args = parser.parse_args(argv)
    os.umask(0o077)
    context = Context(args.state, args.timeout_seconds)
    context.report["execution_platform_requested"] = args.execution_platform
    context.report["diagnostic_mode"] = "database_and_client" if args.client_probe else "database"
    if args.client_probe:
        context.report["scope"] += "; headless WGL rendering and synthetic input fixture"
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, "cancel_requested", True))
    diagnostic = None
    try:
        require(60 <= args.timeout_seconds <= 1800, "Timeout must be 60 to 1800 seconds")
        context.check()
        diagnostic = Diagnostic(args, context)
        if args.android_metadata is not None:
            require(args.android_metadata.is_file() and args.android_metadata.stat().st_size <= 16384,
                    "Invalid Android metadata file")
            context.report["android_context_unverified"] = json.loads(args.android_metadata.read_text())
        diagnostic.execute()
        context.report["status"] = "passed"
    except Cancelled as exc:
        context.report.update(status="cancelled", failures=[str(exc)])
    except Exception as exc:
        context.report.update(status="failed", failures=[str(exc)])
    finally:
        if diagnostic is not None:
            try:
                failures = diagnostic.cleanup()
            except Exception as exc:
                failures = ["Owned cleanup failed: " + str(exc)]
            if failures:
                context.report["failures"].extend(failures)
                if context.report["status"] == "passed":
                    context.report["status"] = "failed"
        context.report["finished_utc"] = utc()
        context.report["cleanup_complete"] = not any(c.process.poll() is None for c in context.children)
        context.report["cleanup"] = diagnostic.cleanup_status if diagnostic else {
            "postgres_graceful": False, "wine_prefix_stopped": False,
            "owned_processes_reaped": context.report["cleanup_complete"]}
        context.report["passed"] = context.report["status"] == "passed" and all(context.report["cleanup"].values())
        if context.report["status"] == "passed" and not context.report["passed"]:
            context.report["status"] = "failed"
            context.report["failures"].append("Required owned cleanup was not proved")
        text = json.dumps(redacted_value(context.report, context.secrets), indent=2) + "\n"
        try:
            require(len(text.encode()) <= 2 * 1024 * 1024, "Report exceeded bound")
            private_write(args.state / "latest-report.json", text)
        except Exception as exc:
            context.report["status"] = "failed"
            context.report["passed"] = False
            context.report["failures"].append("Cannot persist diagnostic report: " + str(exc))
        context.event("result", status=context.report["status"], passed=context.report["passed"], report="/state/latest-report.json",
                      failures=context.report["failures"])
    return 0 if context.report["status"] == "passed" else 2 if context.report["status"] == "cancelled" else 1


if __name__ == "__main__":
    sys.exit(main())
