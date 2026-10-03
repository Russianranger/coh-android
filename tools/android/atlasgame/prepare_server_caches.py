#!/usr/bin/env python3
"""Generate exact server caches and prove native reuse without changing MapServer.

The isolated TSR2 preload exits normally through an owned console. The second
pass must consume every selected binary, perform no cache writes, and read no
source payload belonging to those cached definitions/message stores. Metadata
checks are allowed. Exported trace/log bytes are rechecked before APK packaging.
"""
from __future__ import annotations
import argparse
import fcntl
import functools
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import server_cache_package as package

require, pin = package.require, package.file_pin
REPORT = 'server-cache-generation-report.json'
DONOR_APK = {'bytes': 595203099, 'sha256': '4a507d7d59b3af07be74de4bf47e39b8fd09ac86266a34c4fefd756fb442ee7c'}
DONOR_REPORT = {'bytes': 103482, 'sha256': 'bb5cb7237fd1f489a53df5fe081398dcedde49f8d21ed7e9d27bb6417f21de07'}
DONE = b'Done loading, press Esc to exit'
MAX_LOG = 64 * 1024 * 1024
MAX_TRACE = 1024 * 1024 * 1024
GENERATOR_SOURCES = (
    'tools/android/atlasgame/prepare_server_caches.py',
    'tools/android/atlasgame/server_message_source_contract.py',
    'android/native/server-cache-launcher.c',
    'android/guest/server_cache_package.py', 'android/guest/server_message_cache_format.py',
    'tools/android/client/host_smoke.py', 'tools/android/client/build_apk.py',
    'tools/android/client/prepare_client_caches.py', 'tools/android/client/prepare_client_prerequisites.py',
    'tools/android/client/package_client_runtime.py', 'tools/android/client/prepare_assets.py',
    'tools/generate_runtime_data.py', 'tools/android/presentation/host_smoke.py',
    'android/guest/atlas_world_assets.py', 'android/guest/character_avatar_assets.py',
    'android/guest/client_startup_diagnostic.py', 'android/guest/presentation_diagnostic.py',
    'android/guest/local_login_server.py',
    'android/guest/game_hang_evidence.py', 'android/guest/native_responsiveness_contract.py',
    'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java',
    'tools/android/atlas/java/io/github/russianranger/cohatlas/HostImport.java',
    'upstream/ouroboros/MapServer/src/svr/svr_init.c',
    'upstream/ouroboros/MapServer/src/serverError.c',
    'upstream/ouroboros/MapServer/src/storyarc/storyarcutil.c',
    'upstream/ouroboros/MapServer/src/language/langServerUtil.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/error.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/utils.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/file.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/log.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/serialize.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/components/StringTable.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/language/MessageStore.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/language/MultiMessageStore.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/language/AppLocale.c',
)


def write_json(path, value):
    Path(path).write_bytes(package.canonical(value))


def generation_modules():
    # APK packaging imports this verifier beside another build_apk.py. Keep its
    # read-only evidence checker independent of generation's flat legacy imports.
    # The CLI's separate process can establish the exact client helper aliases.
    sys.path.insert(0, str(ROOT / 'tools/android/client'))
    import prepare_client_caches
    import prepare_client_prerequisites
    import host_smoke
    import atlas_world_assets
    import character_avatar_assets
    return prepare_client_caches, prepare_client_prerequisites, host_smoke, atlas_world_assets, character_avatar_assets


def read_json(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=package.unique_object)


def extract_donor(apk, receipt, output, client_host):
    require(pin(apk) == DONOR_APK and pin(receipt) == DONOR_REPORT, 'Exact published 0.12.0 donor differs')
    report = read_json(receipt)
    require(report.get('repository_commit') == '1791a3203ecf662191f2d6e3401cfa9ea4692004'
            and report.get('version_name') == '0.12.0' and report.get('signature_verified') is True
            and report.get('payload_bytes_verified') is True, 'Donor publication receipt differs')
    output.mkdir()
    imports, assets = output / 'atlas', output / 'runtime'
    imports.mkdir(); assets.mkdir()
    with zipfile.ZipFile(apk) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate donor APK member')
        for name, expected in report['payloads'].items():
            require(name.startswith(('assets/', 'lib/')) and '..' not in Path(name).parts, 'Unsafe donor payload')
            raw = archive.read(name)
            require(package.pin_bytes(raw) == expected, 'Donor payload differs: ' + name)
            if name.startswith(('assets/atlas/', 'assets/runtime/')):
                require(name.count('/') == 2, 'Unexpected donor asset nesting')
                target = (imports if name.startswith('assets/atlas/') else assets) / Path(name).name
                target.write_bytes(raw)
    client_host.apk_tool.verify_import_package(imports)
    return imports, assets


def extract_tar(path, runtime, manifest_name, manifest_sha=None):
    """Closed, regular-only native/schema TAR; hashes come from the pinned APK."""
    with tarfile.open(path, 'r:gz') as archive:
        entries = archive.getmembers()
        names = [entry.name for entry in entries]
        require(len(names) == len(set(name.casefold() for name in names)) and manifest_name in names,
                'Native/schema TAR inventory differs')
        require(all(entry.isfile() and not entry.islnk() and not entry.issym()
                    and 0 < entry.size <= 128 * 1024 * 1024
                    and not entry.name.startswith('/') and '\\' not in entry.name
                    and all(part not in ('', '.', '..') for part in entry.name.split('/'))
                    for entry in entries), 'Unsafe native/schema TAR member')
        raw = archive.extractfile(manifest_name).read()
        if manifest_sha:
            require(hashlib.sha256(raw).hexdigest() == manifest_sha, 'Schema manifest compatibility differs')
        manifest = json.loads(raw)
        require(set(names) == set(manifest['files']) | {manifest_name}, 'Native/schema closure differs')
        for entry in entries:
            data = archive.extractfile(entry).read()
            if entry.name != manifest_name:
                expected = manifest['files'][entry.name]
                require(package.pin_bytes(data) == {key: expected[key] for key in ('bytes', 'sha256')},
                        'Native/schema file differs: ' + entry.name)
            target = runtime / entry.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            os.chmod(target, 0o600)
            os.utime(target, (package.EPOCH, package.EPOCH))
    return manifest


def seed_zip(path, runtime, manifest):
    with zipfile.ZipFile(path) as archive:
        for name, expected in manifest['files'].items():
            raw = archive.read(name)
            require(package.pin_bytes(raw) == {key: expected[key] for key in ('bytes', 'sha256')}, 'Seed file differs')
            target = runtime / name
            if target.exists():
                # Schema/prerequisite collisions are permitted only byte-for-byte.
                require(target.read_bytes() == raw, 'Seed collides with accepted schema: ' + name)
            else:
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
            os.chmod(target, 0o600); os.utime(target, (package.EPOCH, package.EPOCH))


def normalize_data(data):
    count = 0
    for current, dirs, files in os.walk(data):
        for name in files:
            path = Path(current) / name
            require(path.is_file() and not path.is_symlink(), 'Unexpected linked host import')
            relative = path.relative_to(data).as_posix()
            mutable = relative.startswith(('bin/', 'geobin/', 'server/bin/', 'server/db/')) or path.suffix in ('.dbidmap', '.attribute')
            os.chmod(path, 0o600 if mutable else 0o444)
            os.utime(path, (package.EPOCH, package.EPOCH)); count += 1
            require(count <= 200000, 'Host data inventory exceeds bound')
    return count


def prepare_runtime_layout(runtime):
    """Match LocalLoginServer's isolated data+tools native auto-discovery shape."""
    runtime = Path(runtime)
    require(runtime.is_dir() and not runtime.is_symlink()
            and (runtime / 'data').is_dir() and not (runtime / 'data').is_symlink(),
            'Expected isolated native runtime/data layout')
    require(not (runtime / 'gamedatadir.txt').exists() and not (runtime / 'tools').exists(),
            'Fresh bounded native discovery layout required')
    (runtime / 'tools').mkdir(mode=0o700)
    return {'format': 1, 'cwd': str(runtime.resolve()), 'data_directory': 'data',
            'tools_directory': 'tools', 'tools_entries': 0, 'external_data_roots': False}


def data_snapshot(data):
    result = {}
    for current, dirs, files in os.walk(data):
        for name in files:
            path = Path(current) / name
            info = path.lstat(); require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Nonregular generated leaf')
            relative = 'data/' + path.relative_to(data).as_posix()
            if relative.startswith(('data/bin/', 'data/geobin/', 'data/server/bin/')) and path.suffix.lower() == '.bin':
                continue
            result[relative] = {'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns, 'mode': stat.S_IMODE(info.st_mode)}
    require(len(result) <= 200000, 'Data snapshot exceeds bound')
    return {'files': len(result), 'bytes': sum(record['bytes'] for record in result.values()),
            'inventory_sha256': hashlib.sha256(package.canonical(result)).hexdigest()}


def phase_receipt(stdout, stderr, stage, session, returncode, identifiers_unchanged):
    """Reject failures even when the native preload prints its ordinary done line."""
    require(len(stdout) <= MAX_LOG and len(stderr) <= MAX_LOG, 'Native observer log exceeds bound')
    text = stdout.decode('utf-8', 'replace').replace('\r', '')
    require(text.count(DONE.decode()) == 1, 'Native completed-preload marker missing/repeated')
    events = {}
    for kind in ('LAUNCH', 'CONSOLE', 'ESCAPE', 'EXIT'):
        matches = re.findall(r'^COH_SERVER_CACHE_' + kind + r'_V1 (\{[^\n]*\})$', text, re.M)
        require(len(matches) == 1, 'Missing/repeated native console event: ' + kind)
        events[kind] = json.loads(matches[0])
    pid = events['LAUNCH'].get('pid')
    require(type(pid) is int and pid > 0 and all(event.get('session_id') == session and event.get('pid') == pid
            for event in events.values()), 'Native console session/PID differs')
    require(returncode == 0 and events['EXIT'].get('exit_code') == 0
            and events['CONSOLE'].get('owned') is True and events['ESCAPE'].get('sent') is True
            and events['EXIT'].get('escape_sent') is True and identifiers_unchanged,
            'Native normal exit, owned console or identifier stability missing')
    require('COH_SERVER_CACHE_TIMEOUT' not in text and 'COH_SERVER_CACHE_STOP_REFUSED' not in text
            and 'COH_SERVER_CACHE_LAUNCH_ERROR' not in text, 'Native console launcher failed')
    require(text.index(DONE.decode()) < text.index('COH_SERVER_CACHE_ESCAPE_V1') < text.index('COH_SERVER_CACHE_EXIT_V1'),
            'Native normal exit preceded completed preload')
    # ErrorvInternal immediately invokes serverErrorfCallback in this exact
    # source; development-mode callback emits printf_stderr before any later
    # server dialog queue. Do not mislabel its unused queue flag as an error drain.
    # svr_init.c's registered exit callback and log.c's normal shutdown emit
    # these two lines even on exit(0). Only the fixed TSR2 argument sequence is
    # accepted; auto-discovery/data errors remain unconditionally forbidden.
    benign = re.compile(r'^(?:started .+|detected QuickEdit mode.*|'
                        r'Quitting: [^\r\n]*[\\/]MapServer\.exe\s+-tsr2 -assertmode 8256\s*|'
                        r'Flushing log files to disk)$')
    unknown_stderr = [line for line in stderr.decode('utf-8', 'replace').replace('\r', '').splitlines()
                      if line.strip() and not benign.fullmatch(line)]
    require(not unknown_stderr, 'Unclassified native/Wine stderr: ' + repr(unknown_stderr[:8]))
    errors = re.findall(r'(?im)^.*(?:ERRORLOG FILEERROR:|LastAuthor:|Fatal error|Assertion failed|Error loading|EncounterPreloadError).*$' , text)
    require(not errors, 'Native data/assert errors observed: ' + repr(errors[:8]))
    story_counts = re.findall(r'\b(\d+) arcs,\s*(\d+) contacts,\s*(\d+) tasks\b', text)
    spawn_counts = re.findall(r'\b(\d+) spawn definitions\b', text)
    require(story_counts == [('470', '957', '3528')] and spawn_counts == ['46930'],
            'Native definition cardinality differs from the accepted complete input set')
    return {'format': 1, 'stage': stage, 'session_id': session, 'mapserver_pid': pid,
            'mapserver_sha256': package.MAPSERVER_SHA256, 'native_exit_code': 0, 'launcher_exit_code': returncode,
            'completed_preload': True, 'console_owned': True, 'escape_sent': True,
            'identifier_files_unchanged': True, 'timed_out': False,
            'definition_counts': {'story_arcs': 470, 'contacts': 957, 'tasks': 3528, 'spawn_definitions': 46930},
            'native_errors': {'status': 'no_native_data_errors', 'observer': 'immediate_development_callback_stderr_and_fileerror_stdout',
                              'stderr_unclassified_lines': 0, 'queued_error_drain_claimed': False}}


@functools.lru_cache(maxsize=32)
def trace_runtime_prefix(runtime):
    return str(Path(runtime).resolve()).replace('\\', '/').casefold() + '/'


@functools.lru_cache(maxsize=1)
def message_source_contract():
    source = Path(__file__).with_name('server_message_source_contract.py')
    spec = importlib.util.spec_from_file_location('qualified_native_message_source_contract', source)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def relative_trace_path(raw, runtime):
    """Only direct regular host data leaves; Wine paths use the existing Z: drive."""
    raw = raw.removesuffix(' (deleted)')
    if not raw.startswith('/'):
        return None
    prefix = trace_runtime_prefix(str(runtime))
    value = raw.replace('\\', '/').casefold()
    if value.startswith(prefix):
        relative = value[len(prefix):]
        if relative.startswith('data/') and all(part not in ('', '.', '..') for part in relative.split('/')):
            return relative
    return None


def completed_trace_lines(path):
    """Join -ff unfinished/resumed records before interpreting content effects."""
    pending = {}
    with Path(path).open(errors='replace') as stream:
        for line in stream:
            unfinished = re.search(r'\b(read|pread64|write|pwrite64|mmap|mmap2)\(.*<unfinished \.\.\.>\s*$', line)
            if unfinished:
                operation = unfinished.group(1)
                require(operation not in pending, 'Overlapping unfinished native content syscall')
                pending[operation] = line[:line.index('<unfinished ...>')]
                continue
            resumed = re.match(r'^\s*<\.\.\. (read|pread64|write|pwrite64|mmap|mmap2) resumed>(.*)$', line)
            if resumed:
                operation, rest = resumed.groups()
                prefix = pending.pop(operation, None)
                if prefix is None:
                    require(not re.search(r'\)\s*=\s*(?:[1-9]\d*|0x[0-9a-f]+)(?:\s|$)', rest),
                            'Unmatched successful resumed native content syscall')
                    continue
                yield prefix + rest + '\n'
            else:
                yield line
    # A successful normal phase can leave Wine service threads blocked on pipes.
    # A native data-leaf read/write whose outcome is lost cannot prove a hit.
    require(not any('/data/' in line.replace('\\', '/').casefold() for line in pending.values()),
            'Unfinished native data content syscall has no completion')


def trace_receipt(paths, runtime, files, source_paths, identifier_files=()):
    """Count completed successful content reads, not CreateFile/fstat attempts."""
    cache_names = {name.casefold(): name for name in files}
    sources = {name.casefold() for name in source_paths}
    identifiers = {name.casefold() for name in identifier_files}
    sources -= identifiers
    reads = {name: 0 for name in files}; source_reads = {}; identifier_reads = {}; writes = {}; trace_pins = {}
    total = 0
    for path in sorted(map(Path, paths)):
        require(path.is_file() and not path.is_symlink(), 'Missing native trace leaf')
        total += path.stat().st_size; require(total <= MAX_TRACE, 'Native trace exceeds bound')
        trace_pins[path.name] = pin(path)
        for line in completed_trace_lines(path):
                # -yy annotates the descriptor on read/pread/write. The final
                # syscall return distinguishes attempted reads from content.
                match = re.search(r'\b(read|pread64|write|pwrite64)\(\d+<([^>]*)>.*\)\s*=\s*(\d+)(?:\s|$)', line)
                if match:
                    operation, raw, amount = match.groups(); amount = int(amount)
                    name = relative_trace_path(raw, runtime)
                    if not name or not amount: continue
                    if operation in ('write', 'pwrite64'):
                        if name in cache_names: writes[cache_names[name]] = writes.get(cache_names[name], 0) + amount
                    elif name in cache_names:
                        reads[cache_names[name]] += amount
                    elif name in identifiers:
                        identifier_reads[name] = identifier_reads.get(name, 0) + amount
                    elif name in sources or message_source_contract().is_persisted_source(name):
                        source_reads[name] = source_reads.get(name, 0) + amount
                # fileAlloc currently fread()s cache payloads. A future mapped
                # source reader must not escape the no-source-content proof.
                if re.search(r'\bmmap(?:2)?\(', line) and 'PROT_READ' in line and re.search(r'\)\s*=\s*0x', line):
                    for raw in re.findall(r'\d+<([^>]*)>', line):
                        name = relative_trace_path(raw, runtime)
                        if name in identifiers:
                            identifier_reads[name] = identifier_reads.get(name, 0) + 1
                        elif name in sources or (name and message_source_contract().is_persisted_source(name)):
                            source_reads[name] = source_reads.get(name, 0) + 1
                if re.search(r'\b(?:rename|renameat|renameat2|unlink|unlinkat)\(', line) and re.search(r'\)\s*=\s*0(?:\s|$)', line):
                    for raw in re.findall(r'"([^"\n]+)"', line):
                        name = relative_trace_path(raw, runtime)
                        if name in cache_names: writes[cache_names[name]] = writes.get(cache_names[name], 0) + 1
    require(trace_pins, 'Missing strace content evidence')
    return {'format': 1, 'observer': 'strace-successful-fd-content-reads-and-writes',
            'runtime_host_path': str(Path(runtime).resolve()), 'trace_files': trace_pins,
            'message_source_contract': json.loads(package.canonical(message_source_contract().persisted_source_contract())),
            'cache_content_reads': reads,
            'identifier_content_reads': [{'path': name, 'bytes': value} for name, value in sorted(identifier_reads.items())],
            'source_content_reads': [{'path': name, 'bytes': value} for name, value in sorted(source_reads.items())],
            'cache_writes': [{'path': name, 'bytes': value} for name, value in sorted(writes.items())]}


def wine_path(path):
    return 'Z:' + str(Path(path).resolve()).replace('/', '\\')


def prove_prefix_server_unlocked(prefix, server_base=None):
    """Check Wine's per-prefix device/inode lock, not a process-name guess.

    Wine9 server/request.c uses /tmp/.wine-UID/server-DEV-INODE/lock and a
    POSIX write lock on its first byte. -k may return1 when this lock is already
    absent. A successful nonblocking lock independently proves quiescence.
    """
    prefix = Path(prefix)
    info = prefix.lstat()
    require(prefix.is_absolute() and stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid(),
            'Unowned or linked Wine prefix cleanup refused')
    base = Path(server_base) if server_base is not None else Path('/tmp') / ('.wine-' + str(os.geteuid()))
    server = base / f'server-{info.st_dev:x}-{info.st_ino:x}'
    for path in (base, server):
        if not os.path.lexists(path):
            return {'status': 'no_prefix_server_directory', 'prefix': str(prefix), 'server_directory': str(server)}
        entry = path.lstat()
        require(stat.S_ISDIR(entry.st_mode) and entry.st_uid == os.geteuid() and not entry.st_mode & 0o077,
                'Unowned or linked Wine server directory refused')
    lock = server / 'lock'
    if not os.path.lexists(lock):
        return {'status': 'no_prefix_server_lock', 'prefix': str(prefix), 'server_directory': str(server)}
    descriptor = os.open(lock, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        entry = os.fstat(descriptor)
        require(stat.S_ISREG(entry.st_mode) and entry.st_nlink == 1 and entry.st_uid == os.geteuid(),
                'Invalid Wine prefix lock leaf')
        fcntl.lockf(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, 0, os.SEEK_SET)
        fcntl.lockf(descriptor, fcntl.LOCK_UN, 1, 0, os.SEEK_SET)
    finally:
        os.close(descriptor)
    return {'status': 'prefix_server_lock_unheld', 'prefix': str(prefix), 'server_directory': str(server)}


def stop_owned_prefix(environment, directory):
    with (directory / 'wine-helpers-stop.log').open('wb') as log:
        killed = subprocess.run(['wineserver', '-k'], env=environment, check=False,
                                stdout=log, stderr=subprocess.STDOUT, timeout=30)
        require(killed.returncode in (0, 1), 'Owned Wine prefix stop failed')
        waited = subprocess.run(['wineserver', '-w'], env=environment, check=True,
                                stdout=log, stderr=subprocess.STDOUT, timeout=30)
        require(waited.returncode == 0, 'Owned Wine prefix wait failed')
    # Empty-output status1 is the documented no-lock-owner case; diagnostics or
    # a still-held lock remain failures. The native launcher has already ended.
    require((directory / 'wine-helpers-stop.log').stat().st_size == 0, 'Wine prefix cleanup emitted diagnostics')
    proof = prove_prefix_server_unlocked(environment['WINEPREFIX'])
    write_json(directory / 'wine-helpers-stop.json', {'format': 1, 'kill_exit_code': killed.returncode,
               'wait_exit_code': waited.returncode, 'normal_launcher_exit_observed_first': True, **proof})


def run_phase(args, runtime, launcher, environment, output, stage, identity, trace=False):
    directory = output / 'evidence' / stage; directory.mkdir(parents=True)
    session = secrets.token_hex(16); stop = runtime / ('cache-stop-' + session)
    command = [args.wine, str(launcher), session, wine_path(runtime / 'MapServer.exe'),
               wine_path(runtime), wine_path(stop), str(args.timeout_seconds)]
    if trace:
        command = ['strace', '-ff', '-yy', '-s', '128', '-o', str(directory / 'trace'), '-e',
                   'trace=read,pread64,mmap,mmap2,write,pwrite64,openat,close,rename,renameat,renameat2,unlink,unlinkat', *command]
    write_json(directory / 'invocation.json', {'session_id': session, 'stage': stage, 'command': command,
               'runtime_host_path': str(runtime), 'identity': identity, 'timeout_seconds': args.timeout_seconds,
               'timezone': environment['TZ'], 'wine_debug': environment['WINEDEBUG'],
               'wine_prefix': environment['WINEPREFIX']})
    before = package.identifier_snapshot(runtime / 'data')
    started = time.monotonic()
    with (directory / 'stdout.log').open('wb') as stdout, (directory / 'stderr.log').open('wb') as stderr:
        process = subprocess.Popen(command, cwd=runtime, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            offset = 0; pending = b''; completed = False
            while process.poll() is None:
                require(time.monotonic() - started <= args.timeout_seconds + 30, 'Native phase timeout')
                require((directory / 'stdout.log').stat().st_size <= MAX_LOG
                        and (directory / 'stderr.log').stat().st_size <= MAX_LOG, 'Native phase logs exceed bound')
                with (directory / 'stdout.log').open('rb') as source:
                    source.seek(offset); chunk = source.read(1024 * 1024); offset += len(chunk)
                pending = (pending + chunk)[-1024 * 1024:]
                if not completed and DONE in pending:
                    with stop.open('xb') as request: request.write((session + '\n').encode()); request.flush(); os.fsync(request.fileno())
                    completed = True
                time.sleep(0.1)
            returncode = process.wait(timeout=10)
            # Only after the real launcher/tracer has exited: never infer its
            # successful termination from the earlier child EXIT event and
            # risk killing the launcher during normal process teardown.
            require(returncode == 0, 'Native launcher/tracer failed before Wine cleanup')
            stop_owned_prefix(environment, directory)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=5)
    stop.unlink(missing_ok=True)
    receipt = phase_receipt((directory / 'stdout.log').read_bytes(), (directory / 'stderr.log').read_bytes(),
                            stage, session, returncode, before == package.identifier_snapshot(runtime / 'data'))
    receipt['elapsed_seconds'] = round(time.monotonic() - started, 3)
    write_json(directory / 'phase-receipt.json', receipt)
    return receipt


def selected_caches(runtime):
    result, sources = {}, set()
    for path in sorted((runtime / 'data/server/bin').iterdir()):
        if path.suffix.lower() != '.bin': continue
        name = 'data/server/bin/' + path.name
        require(package.safe_cache(name) and path.is_file() and not path.is_symlink(), 'Unsafe generated server cache')
        raw = path.read_bytes()
        if raw.startswith(b'CrypticS'):
            kind = 'Parse6'; decoded = package.inspect_parse6(raw)
            for dependency in decoded['dependencies']:
                relative = dependency['path'].casefold().removeprefix('data/')
                sources.add('data/' + relative)
        elif name.casefold() in package.REQUIRED_MESSAGES:
            kind = 'MessageStore20090521'
        else: continue
        result[name] = {**package.pin_bytes(raw), 'kind': kind, 'structure': package.inspect_payload(raw, kind)}
    require(package.REQUIRED_PARSE6 | package.REQUIRED_MESSAGES <= {name.casefold() for name in result},
            'Native TSR generation did not produce required definition/message coverage')
    return result, sorted(sources)


def archive_source_paths(path, files):
    sources = set()
    with zipfile.ZipFile(path) as archive:
        for name, record in files.items():
            if record['kind'] == 'Parse6':
                for dependency in package.inspect_parse6(archive.read(name))['dependencies']:
                    sources.add('data/' + dependency['path'].casefold().removeprefix('data/'))
    return sorted(sources)


def cache_state(runtime, files):
    return {name: {**pin(runtime / name), 'mtime_ns': (runtime / name).stat().st_mtime_ns} for name in files}


def normalize_shipped_cache_dates(runtime, files):
    """Qualify the exact EPOCH date shape used by the Android missing-only seed."""
    for name in files:
        require(package.safe_cache(name), 'Unsafe selected cache normalization path')
        path = Path(runtime) / name
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid(),
                'Nonprivate selected cache normalization leaf')
        os.chmod(path, 0o600)
        os.utime(path, ns=(package.EPOCH * 10**9, package.EPOCH * 10**9))


def evidence_pins(output):
    return {path.relative_to(output).as_posix(): pin(path) for path in sorted((output / 'evidence').rglob('*')) if path.is_file()}


def verify_generated_package(directory):
    """Recompute qualified facts from pinned native evidence, not manifest flags."""
    directory = Path(directory)
    manifest = package.verify_archive(directory / package.ARCHIVE)
    require(manifest == read_json(directory / package.MANIFEST), 'Embedded/external server donor manifest differs')
    report = read_json(directory / REPORT)
    require(report.get('format') == 1 and report.get('status') == 'native_server_caches_generated_and_consumed'
            and report.get('repository_commit') == manifest['repository_commit']
            and report.get('donor_apk') == DONOR_APK and report.get('donor_build_report') == DONOR_REPORT
            and report.get('archive') == pin(directory / package.ARCHIVE)
            and report.get('identity') == manifest['identity']
            and report.get('physical_startup_timing_validated') is False
            and report.get('dialog_semantics_validated') is False, 'Server generation provenance differs')
    require(report.get('source_files') == {name: pin(ROOT / name) for name in GENERATOR_SOURCES}, 'Generator/source pins differ')
    require(report.get('evidence_files') == evidence_pins(directory), 'Exported native evidence bytes differ')
    require(report.get('launcher') == pin(directory / 'evidence/server-cache-launcher.exe'),
            'Owned-console launcher evidence bytes differ')
    for stage in ('generation', 'consumption'):
        evidence = directory / 'evidence' / stage
        invocation = read_json(evidence / 'invocation.json'); recorded = read_json(evidence / 'phase-receipt.json')
        require(invocation.get('stage') == stage and invocation.get('identity') == manifest['identity']
                and invocation.get('timezone') == 'UTC' and invocation.get('wine_debug') == '-all',
                'Native invocation cache identity/timezone differs')
        recomputed = phase_receipt((evidence / 'stdout.log').read_bytes(), (evidence / 'stderr.log').read_bytes(),
                                   stage, invocation['session_id'], recorded['launcher_exit_code'],
                                   report['identifier_snapshots'][stage + '_before'] == report['identifier_snapshots'][stage + '_after'])
        require(all(recorded.get(key) == value for key, value in recomputed.items()), 'Native completion/error proof differs')
        cleanup = read_json(evidence / 'wine-helpers-stop.json')
        prefix = invocation.get('wine_prefix')
        require(isinstance(prefix, str) and Path(prefix).is_absolute()
                and cleanup.get('format') == 1 and cleanup.get('kill_exit_code') in (0, 1)
                and cleanup.get('wait_exit_code') == 0
                and cleanup.get('normal_launcher_exit_observed_first') is True
                and cleanup.get('status') in ('no_prefix_server_directory', 'no_prefix_server_lock', 'prefix_server_lock_unheld')
                and cleanup.get('prefix') == prefix and isinstance(cleanup.get('server_directory'), str)
                and Path(cleanup['server_directory']).is_absolute()
                and (evidence / 'wine-helpers-stop.log').read_bytes() == b'',
                'Owned Wine prefix cleanup proof differs')
        require(report['identifier_snapshots'][stage + '_before'] == manifest['identity']['identifier_files'],
                'Native identifier snapshot differs from accepted donor identity')
        require(report['noncache_snapshots'][stage + '_before'] == report['noncache_snapshots'][stage + '_after'],
                'Native generation changed noncache data')
        if stage == 'generation':
            require(recorded == manifest['native_generation'], 'Native generation manifest proof differs')
    evidence = directory / 'evidence/consumption'
    invocation = read_json(evidence / 'invocation.json')
    require(invocation.get('timezone') == 'UTC' and invocation.get('wine_debug') == '-all', 'Native timezone/debug contract differs')
    sources = archive_source_paths(directory / package.ARCHIVE, manifest['files'])
    require(report.get('source_paths') == sources, 'Native forbidden source scope differs from actual Parse6 dependencies')
    require(read_json(directory / 'evidence/generated-cache-inventory.json') == {'files': manifest['files'], 'source_paths': sources},
            'Native generated candidate inventory differs from final archive')
    trace = trace_receipt(evidence.glob('trace.*'), invocation['runtime_host_path'], manifest['files'], sources,
                          manifest['identity']['identifier_files'])
    require(trace == read_json(evidence / 'trace-receipt.json'), 'Native consumption trace proof differs')
    require(not trace['source_content_reads'] and not trace['cache_writes'] and all(trace['cache_content_reads'].values()),
            'Native consumption missed/rebuilt caches or read source payload')
    require(report['cache_snapshots']['before'] == report['cache_snapshots']['after']
            and {name: {key: record[key] for key in ('bytes', 'sha256')} for name, record in report['cache_snapshots']['before'].items()}
                == {name: {key: record[key] for key in ('bytes', 'sha256')} for name, record in manifest['files'].items()},
            'Native consumed cache bytes/timestamps changed')
    require(all(record.get('mtime_ns') == package.EPOCH * 10**9
                for record in report['cache_snapshots']['before'].values()),
            'Native consumption did not exercise the shipped normalized cache dates')
    consumption = {**read_json(evidence / 'phase-receipt.json'), 'cache_files_unchanged': True,
                   **{key: trace[key] for key in ('cache_content_reads', 'cache_writes', 'source_content_reads')},
                   'trace_receipt_sha256': hashlib.sha256(package.canonical(trace)).hexdigest()}
    require(consumption == manifest['native_consumption'], 'Manifest consumption proof differs from exported native evidence')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('donor-apk', 'donor-build-report', 'asset-archive', 'work', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--wine', default='wine')
    parser.add_argument('--timeout-seconds', type=int, default=1800)
    args = parser.parse_args()
    args.work, args.output = args.work.resolve(), args.output.resolve()
    require(package.HEX40.fullmatch(args.repository_commit) and 30 <= args.timeout_seconds <= 3600, 'Invalid commit/timeout')
    require(not args.work.exists() and not args.output.exists(), 'Fresh server cache work/output required')
    args.work.mkdir(parents=True); args.output.mkdir(parents=True)
    (args.output / 'evidence').mkdir()
    client_caches, prerequisites, client_host, world, avatar = generation_modules()
    source_files = {name: pin(ROOT / name) for name in GENERATOR_SOURCES}
    imports, assets = extract_donor(args.donor_apk.resolve(), args.donor_build_report.resolve(), args.work / 'donor', client_host)
    data = client_host.import_game_data(imports, args.asset_archive.resolve(), args.work, args.output / 'evidence')
    runtime = data.parent
    extract_tar(assets / 'game-package.tar.gz', runtime, 'game-package.json')
    extract_tar(assets / 'dbserver-schema.tar.gz', runtime, 'schema-manifest.json', package.compatibility_identity()['schema_manifest_sha256'])
    seed_zip(assets / 'client-caches.zip', runtime, client_caches.verify_cache_archive(assets / 'client-caches.zip'))
    seed_zip(assets / 'client-prerequisites.zip', runtime, prerequisites.verify_archive(assets / 'client-prerequisites.zip'))
    context = type('HostContext', (), {'check': lambda self: None})()
    world.install(runtime, assets, context); avatar.install(runtime, assets, context)
    normalize_data(data)
    identity = package.build_expected_identity(data, runtime / 'MapServer.exe')
    layout = prepare_runtime_layout(runtime)
    write_json(args.output / 'evidence/native-runtime-layout.json', layout)
    launcher = args.work / 'server-cache-launcher.exe'
    with (args.output / 'evidence/launcher-build.log').open('wb') as log:
        subprocess.run(['i686-w64-mingw32-gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-static-libgcc',
                        str(ROOT / 'android/native/server-cache-launcher.c'), '-o', str(launcher)],
                       check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    shutil.copyfile(launcher, args.output / 'evidence/server-cache-launcher.exe')
    require(not (runtime / 'piggs/texts.pigg').exists(), 'Native generation requires the exact development-mode callback path')
    environment = dict(os.environ, WINEARCH='win32', WINEPREFIX=str(args.work / 'wine-prefix'), WINEDEBUG='-all',
                       WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree=d;mshtml=d', TZ='UTC', LANG='C.UTF-8')
    with (args.output / 'evidence/wine-initialization.log').open('wb') as log:
        subprocess.run([args.wine, 'wineboot', '--init'], env=environment, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=180)
    identifiers, noncache = {}, {}
    identifiers['generation_before'] = package.identifier_snapshot(data); noncache['generation_before'] = data_snapshot(data)
    generation = run_phase(args, runtime, launcher, environment, args.output, 'generation', identity)
    identifiers['generation_after'] = package.identifier_snapshot(data); noncache['generation_after'] = data_snapshot(data)
    require(noncache['generation_before'] == noncache['generation_after'], 'Native generation changed noncache inputs')
    files, sources = selected_caches(runtime)
    # This diagnostic inventory is not a qualified donor or consumption claim.
    # Retain the exact selected dependency scope before the second native phase.
    write_json(args.output / 'evidence/generated-cache-inventory.json', {'files': files, 'source_paths': sources})
    normalize_shipped_cache_dates(runtime, files)
    before = cache_state(runtime, files)
    # Establish services outside strace's descendant tree again after the
    # generation prefix cleanup. The same prefix and cache bytes are retained.
    with (args.output / 'evidence/wine-reinitialization.log').open('wb') as log:
        subprocess.run([args.wine, 'wineboot', '--init'], env=environment, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=180)
    identifiers['consumption_before'] = package.identifier_snapshot(data); noncache['consumption_before'] = data_snapshot(data)
    consumption = run_phase(args, runtime, launcher, environment, args.output, 'consumption', identity, trace=True)
    identifiers['consumption_after'] = package.identifier_snapshot(data); noncache['consumption_after'] = data_snapshot(data)
    after = cache_state(runtime, files)
    require(before == after and noncache['consumption_before'] == noncache['consumption_after'], 'Native reuse changed cache/source files')
    trace = trace_receipt((args.output / 'evidence/consumption').glob('trace.*'), runtime, files, sources, identity['identifier_files'])
    require(not trace['source_content_reads'] and not trace['cache_writes'] and all(trace['cache_content_reads'].values()),
            'Native cache hit proof failed; inspect retained trace evidence')
    write_json(args.output / 'evidence/consumption/trace-receipt.json', trace)
    consumption.update({key: trace[key] for key in ('cache_content_reads', 'cache_writes', 'source_content_reads')})
    consumption.update(cache_files_unchanged=True, trace_receipt_sha256=hashlib.sha256(package.canonical(trace)).hexdigest())
    manifest = {'format': 1, 'role': package.ROLE, 'repository_commit': args.repository_commit, 'identity': identity,
                'files': files, 'native_generation': generation, 'native_consumption': consumption,
                'native_client_or_server_recompiled': False, 'generated_noncache_outputs': [],
                'android_execution_validated': False, 'physical_gameplay_validated': False}
    with zipfile.ZipFile(args.output / package.ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)); info.external_attr = 0o100600 << 16
            info.compress_type = zipfile.ZIP_DEFLATED; archive.writestr(info, (runtime / name).read_bytes())
        info = zipfile.ZipInfo(package.MANIFEST, (2026, 1, 1, 0, 0, 0)); info.external_attr = 0o100600 << 16
        info.compress_type = zipfile.ZIP_DEFLATED; archive.writestr(info, package.canonical(manifest))
    write_json(args.output / package.MANIFEST, manifest)
    report = {'format': 1, 'status': 'native_server_caches_generated_and_consumed', 'repository_commit': args.repository_commit,
              'donor_apk': DONOR_APK, 'donor_build_report': DONOR_REPORT, 'identity': identity, 'source_files': source_files,
              'launcher': pin(launcher), 'source_paths': sources, 'identifier_snapshots': identifiers,
              'noncache_snapshots': noncache, 'cache_snapshots': {'before': before, 'after': after},
              'archive': pin(args.output / package.ARCHIVE), 'evidence_files': evidence_pins(args.output),
              'physical_startup_timing_validated': False, 'dialog_semantics_validated': False}
    write_json(args.output / REPORT, report)
    verify_generated_package(args.output)
    (args.output / (package.ARCHIVE + '.sha256')).write_text(report['archive']['sha256'] + '  ' + package.ARCHIVE + '\n')
    print(json.dumps({'status': report['status'], 'files': len(files), 'archive': report['archive']}))


if __name__ == '__main__':
    main()
