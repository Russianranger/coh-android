#!/usr/bin/env python3
"""Admit one unchanged retained receiver on the fresh hosted Linux destination.

No compilation, old controls, account input or service startup. The only native
invocations are the loader's verify/list and the exact no-argument exit2 smoke.
"""
import gzip
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import selectors
import signal
import stat
import subprocess
import sys
import time

PREFIX = 'native-android/combined-client/diagnostics/'
OLD = PREFIX + 'continuation-f-20261017/local-initial-tool-command-v2-dfc843bb2/'
REVIEW = PREFIX + 'continuation-f-20261017/local-initial-release-reuse-review-20261018/'
ELF = PREFIX + 'primary-authority-20261017/initial-receiver-release-20261018/coh-capture-local-initial'
FOLLOWUP = PREFIX + 'continuation-f-20261017/fresh-callback-profile-source-review-20261018/followup/review.json'
FOLLOWUP_SHA = 'a7f6c2dfaaf3e5b7b5e343f2ded01f153df83741551423213c0ff1e7ad8ee92e'
REVIEW_SHA = '03fd929739d8bb4b6134b9edde70190039a145612aec3421cbaedce62d180b1a'
GZIP_SHA = 'f65d849fbf89027b6cefb4a00f6f4230f04ef4d2595b98aab7a90d05ba2bb522'
BUILD_SHA = '59dbf8b59779efa513265bb78fce50f07019f6d730e8bdb7b3380c5be4d6c2cc'
ELF_SHA = 'eeb5e9a3c29bfb223c23a5b465378ce90b800f517396c2c04502a703d8874ea5'
MAP_SHA = '2ad1cbe6b04817a21e4db1e514d3199a87b8b1720f31ec2ba4a28272790ec9c5'
HISTORICAL = 'dfc843bb2f538956df843e7b117d60cd38bdfd90'
BASENAME = 'coh-capture-local-initial'
INTERPRETER = '/lib64/ld-linux-x86-64.so.2'
NEEDED = ['libz.so.1', 'libcrypto.so.3', 'libc.so.6']
VERSIONS = {'libz.so.1': ['ZLIB_1.2.0'], 'libcrypto.so.3': ['OPENSSL_3.0.0'],
            'libc.so.6': sorted(['GLIBC_2.33', 'GLIBC_2.17', 'GLIBC_2.14', 'GLIBC_2.34',
                                'GLIBC_2.4', 'GLIBC_2.2.5', 'GLIBC_2.3.4'])}
CLEAN_ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
GATE_KEYS = {'schema', 'passed', 'source_revision', 'historical_core_source_reference',
             'focused_helper_source_reference', 'historical_helper_pins_superseded',
             'source_sha256', 'host_controls_reexecuted', 'historical_worker_commit_replayed_in_CI',
             'source_preflight_only', 'runtime_executed', 'accepted_observer_equivalence',
             'source_generation_admitted', 'world_authority'}

class Refused(Exception):
    def __init__(self, code):
        self.code = code
        self.cleanup_verified = True

def need(ok, code):
    if not ok:
        raise Refused(code)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def raw(path, maximum=8 * 1024**2):
    need(path.resolve() == path, 'REGULAR_INPUT')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= maximum, 'REGULAR_INPUT')
        chunks, count = [], 0
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            count += len(block)
            need(count <= maximum, 'REGULAR_INPUT')
            chunks.append(block)
        after = os.fstat(fd)
        need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
             (after.st_dev, after.st_ino, count, after.st_mtime_ns), 'INPUT_CHANGED')
        return b''.join(chunks)
    finally:
        os.close(fd)

def child(command, cwd, limit=262144, seconds=20):
    """Bound output while reading, bound time, and reap on every failure."""
    process = subprocess.Popen(command, cwd=cwd, env=CLEAN_ENV, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    out = [bytearray(), bytearray()]
    failure, result, clean = None, None, True
    try:
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate((process.stdout, process.stderr)):
                selector.register(stream, selectors.EVENT_READ, index)
            deadline = time.monotonic() + seconds
            while selector.get_map():
                remaining = deadline - time.monotonic()
                need(remaining > 0, 'CHILD_TIMEOUT')
                for key, _ in selector.select(min(remaining, 0.1)):
                    block = os.read(key.fd, 4096)
                    if not block:
                        selector.unregister(key.fileobj)
                    else:
                        out[key.data].extend(block)
                        need(len(out[key.data]) <= limit, 'CHILD_OUTPUT')
            remaining = deadline - time.monotonic()
            need(remaining > 0, 'CHILD_TIMEOUT')
            result = process.wait(timeout=remaining)
    except BaseException as error:
        failure = error if isinstance(error, Refused) else Refused('CHILD_PROCESS')
    finally:
        # A dead leader can leave a descendant holding a pipe or group alive.
        # Never predicate group teardown on Popen.poll()/leader liveness.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            clean = False
        try:
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            clean = False
        for stream in (process.stdout, process.stderr):
            try:
                stream.close()
            except BaseException:
                clean = False
        until = time.monotonic() + 1
        while True:
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                break
            except OSError:
                clean = False
                break
            if time.monotonic() >= until:
                clean = False
                break
            time.sleep(0.01)
    if failure is not None:
        failure.cleanup_verified = clean
        raise failure
    if not clean:
        failure = Refused('CHILD_CLEANUP')
        failure.cleanup_verified = False
        raise failure
    return result, bytes(out[0]), bytes(out[1])

def git(root, *args):
    status, value, error = child(['/usr/bin/git', *args], root)
    need(status == 0 and not error, 'GIT_SOURCE')
    return value

def committed(root, pins, revision):
    need(git(root, 'rev-parse', 'HEAD').decode().strip() == revision, 'SOURCE_HEAD')
    need(type(pins) is dict and 173 <= len(pins) <= 512, 'SOURCE_GATE')
    tree = git(root, 'ls-tree', '-r', '-z', revision, '--', *sorted(pins))
    blobs = {}
    for row in tree.split(b'\0'):
        if row:
            meta, name = row.split(b'\t', 1)
            mode, kind, blob = meta.split()
            need(kind == b'blob' and mode in (b'100644', b'100755'), 'GIT_SOURCE')
            blobs[name.decode()] = blob.decode()
    need(set(blobs) == set(pins), 'GIT_SOURCE')
    for name, pin in pins.items():
        rel = PurePosixPath(name)
        need(type(name) is str and rel.as_posix() == name and not rel.is_absolute() and
             all(p not in ('', '.', '..') for p in rel.parts) and '\\' not in name and ':' not in name and
             type(pin) is str and re.fullmatch('[0-9a-f]{64}', pin), 'SOURCE_GATE')
        value = raw(root / name)
        need(digest(value) == pin and hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest()
             == blobs[name], 'SOURCE_BYTES')
    need(git(root, 'rev-parse', 'HEAD').decode().strip() == revision, 'SOURCE_HEAD')

def fixed(root, name, size, pin):
    value = raw(root / name)
    need(len(value) == size and digest(value) == pin, 'FIXED_INPUT')
    return value

def evidence(root):
    review = json.loads(fixed(root, REVIEW + 'review.json', 12131, REVIEW_SHA))
    gz = fixed(root, OLD + 'build.json.gz', 85006, GZIP_SHA)
    original = gzip.decompress(gz)
    need(len(original) == 240894 and digest(original) == BUILD_SHA, 'FIXED_INPUT')
    build = json.loads(original)
    binary = fixed(root, ELF, 180424, ELF_SHA)
    need(review['schema'] == 'coh-f-retained-local-initial-release-reuse-review-v1' and review['passed'] is True
         and review['historical_build_source_revision'] == build['source_revision'] == HISTORICAL, 'HISTORICAL_SCOPE')
    mapping = review['current_project_consumer_dependencies']['sha256']
    need(len(mapping) == 43 and digest(json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode()) == MAP_SHA,
         'CURRENT_43_MAP')
    need(all(build['source_sha256'].get(k) == v for k, v in mapping.items()), 'CURRENT_43_MAP')
    static = review['static_ELF']
    need(static['interpreter'] == INTERPRETER and static['needed'] == NEEDED and
         static['required_versions'] == VERSIONS and static['RPATH'] is False and static['RUNPATH'] is False,
         'ELF_METADATA')
    pins = {ELF: ELF_SHA, OLD + 'build.json.gz': GZIP_SHA, REVIEW + 'review.json': REVIEW_SHA}
    statuses = review['historical_controls']['safe_status_files_verified']
    expected = {f'status-{mode}/{case}.json' for mode in ('release', 'address', 'undefined')
                for case in ('captured', 'unknown', 'badheader', 'none')}
    need(set(statuses) == expected, 'HISTORICAL_SCOPE')
    for mode in ('release', 'address', 'undefined'):
        tests = build['modes'][mode]['tests']
        need(tests['passed'] is True and tests['checks'] == 151 and tests['scripted_peers_only'] is True,
             'HISTORICAL_SCOPE')
        for case in ('captured', 'unknown', 'badheader', 'none'):
            name = f'status-{mode}/{case}.json'
            item = statuses[name]
            need(item == tests['fixed_status_stdout'][case] and item['file'] == name, 'HISTORICAL_SCOPE')
            fixed(root, OLD + name, item['bytes'], item['sha256'])
            pins[OLD + name] = item['sha256']
    for item in static['readelf_outputs'].values():
        fixed(root, REVIEW + item['file'], item['bytes'], item['sha256'])
    return binary, original, mapping, pins

def admit_gate(root, runner, revision, own_name, artifact_pins):
    path = runner / 'fresh-groups-source-admission.json'
    gate_raw = raw(path, 256 * 1024)
    gate = json.loads(gate_raw)
    need(type(gate) is dict and set(gate) == GATE_KEYS and gate['schema'] ==
         'coh-fresh-groups-live-source-admission-v1' and gate['passed'] is True and
         gate['source_preflight_only'] is True and gate['source_revision'] == revision, 'SOURCE_GATE')
    for key in ('host_controls_reexecuted', 'historical_worker_commit_replayed_in_CI', 'runtime_executed',
                'accepted_observer_equivalence', 'source_generation_admitted', 'world_authority'):
        need(gate[key] is False, 'SOURCE_GATE')
    need(gate['historical_core_source_reference'] == '55f4dd46061bc378f72921ab83b51c79883a1b6e' and
         gate['focused_helper_source_reference'] == '419b61c1188acef7b208066d13b8eca42c0887d1', 'SOURCE_GATE')
    scene = 'native-android/engine/scenecatalog-server/'
    need(gate['historical_helper_pins_superseded'] == sorted(scene + p for p in (
        'fresh_callback_observer/stage.py', 'fresh_callback_observer/test_stage.py', 'admit_groups_capture.py',
        'admit_source_snapshot.py', 'capture_groups_transaction.py', 'retain_fresh_initial_observation.py',
        'retain_fresh_source_snapshot.py', 'summarize_groups_capture.py')), 'SOURCE_GATE')
    focused = raw(root / FOLLOWUP)
    need(digest(focused) == FOLLOWUP_SHA, 'SOURCE_GATE')
    base = json.loads(focused)['merged_effective_current_gate']['source_sha256']
    pins = gate['source_sha256']
    need(len(base) == 173 and all(pins.get(k) == v for k, v in base.items()) and
         all(pins.get(k) == v for k, v in artifact_pins.items()) and own_name in pins, 'SOURCE_GATE')
    committed(root, pins, revision)
    return path, digest(gate_raw), pins

def static_elf(binary, directory):
    outputs = []
    for flag in ('-h', '-l', '-d', '-V'):
        status, out, error = child(['/usr/bin/readelf', flag, str(binary)], directory, 16384)
        need(status == 0 and not error, 'ELF_METADATA')
        outputs.append(out.decode('ascii'))
    header, segments, dynamic, versions = outputs
    need(re.search(r'Class:\s+ELF64\b', header) and re.search(r'Data:\s+2.s complement, little endian', header)
         and re.search(r'Type:\s+DYN\b', header) and 'Advanced Micro Devices X86-64' in header, 'ELF_METADATA')
    need(re.findall(r'Requesting program interpreter: ([^\]]+)', segments) == [INTERPRETER] and
         re.findall(r'\(NEEDED\).*Shared library: \[([^\]]+)\]', dynamic) == NEEDED and
         not re.search(r'\((?:RPATH|RUNPATH)\)', dynamic) and '(FLAGS)' in dynamic and
         'BIND_NOW' in dynamic and re.search(r'\(FLAGS_1\).*NOW PIE', dynamic), 'ELF_METADATA')
    required, current = {}, None
    need("Version needs section '.gnu.version_r' contains 3 entries:" in versions, 'ELF_METADATA')
    for line in versions.split("Version needs section", 1)[1].splitlines():
        match = re.search(r'File: (\S+)\s+Cnt:', line)
        if match:
            current = match[1]
            need(current not in required, 'ELF_METADATA')
            required[current] = []
        match = re.search(r'Name: (\S+)\s+Flags:', line)
        if match:
            need(current is not None, 'ELF_METADATA')
            required[current].append(match[1])
    need({k: sorted(v) for k, v in required.items()} == VERSIONS, 'ELF_METADATA')

def system_files():
    declared = {name: Path('/lib/x86_64-linux-gnu') / name for name in NEEDED}
    declared['loader'] = Path(INTERPRETER)
    result = {}
    for name, path in declared.items():
        resolved = path.resolve(strict=True)
        info = resolved.stat()
        need(info.st_uid == 0 and not info.st_mode & 0o022 and stat.S_ISREG(info.st_mode), 'SYSTEM_FILES')
        value = raw(resolved, 32 * 1024**2)
        result[name] = {'declared': str(path), 'resolved': str(resolved), 'bytes': len(value),
                        'sha256': digest(value), 'device': info.st_dev, 'inode': info.st_ino}
    return result

def loader_checks(binary, directory, systems):
    need(not os.path.lexists('/etc/ld.so.preload'), 'LOADER_PRELOAD')
    status, out, error = child([INTERPRETER, '--verify', str(binary)], directory, 16384, 10)
    need(status == 0 and not out and not error, 'LOADER_VERIFY')
    status, out, error = child([INTERPRETER, '--list', str(binary)], directory, 16384, 10)
    need(status == 0 and not error, 'LOADER_LIST')
    seen = set()
    for line in out.decode('ascii').splitlines():
        line = line.strip()
        if re.fullmatch(r'linux-vdso\.so\.1 \(0x[0-9a-f]+\)', line):
            name = 'vDSO'
        elif re.fullmatch(re.escape(INTERPRETER) + r' \(0x[0-9a-f]+\)', line):
            name = 'loader'
        else:
            match = re.fullmatch(r'(libz\.so\.1|libcrypto\.so\.3|libc\.so\.6) => (/[^\s]+) \(0x[0-9a-f]+\)', line)
            need(match is not None, 'LOADER_LIST')
            name = match[1]
            need(str(Path(match[2]).resolve(strict=True)) == systems[name]['resolved'], 'LOADER_LIST')
        need(name not in seen, 'LOADER_LIST')
        seen.add(name)
    need(seen == {*NEEDED, 'loader', 'vDSO'}, 'LOADER_LIST')
    status, out, error = child([str(binary)], directory, 16384, 10)
    need(status == 2 and not out and not error, 'NOARGS_SMOKE')

def imported_sources(root, pins):
    for module in tuple(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            path = Path(name).resolve()
            if root in path.parents:
                relative = path.relative_to(root).as_posix()
                need(relative in pins and digest(raw(path)) == pins[relative], 'IMPORTED_SOURCE')

def write_new(path, value, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    owned, failure = None, None
    try:
        identity = os.fstat(fd)
        owned = (identity.st_dev, identity.st_ino)
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(value)
            stream.flush()
            os.fsync(fd)
    except BaseException as error:
        failure = error if isinstance(error, Refused) else Refused('OUTPUT_WRITE')
    try:
        os.close(fd)
    except OSError:
        if failure is None:
            failure = Refused('OUTPUT_CLOSE')
    if failure is not None:
        failure.cleanup_verified = owned is not None and unlink_owned(path, owned)
        raise failure
    return owned

def unlink_owned(path, identity):
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != identity:
            return False
        path.unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False

def export_env(path, runner):
    need(path.resolve(strict=True) == path and runner in path.parents, 'ENV_EXPORT')
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    info, written, failure = None, 0, None
    try:
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o022, 'ENV_EXPORT')
        line = ('INITIAL_BUILD_SHA256=' + BUILD_SHA + '\n').encode()
        written = os.write(fd, line)
        need(written == len(line), 'ENV_EXPORT')
        os.fsync(fd)
    except BaseException:
        failure = Refused('ENV_EXPORT')
    try:
        os.close(fd)
    except BaseException:
        failure = failure or Refused('ENV_EXPORT')
    if failure is not None:
        # Roll back only our exact append; never truncate another writer's data.
        failure.cleanup_verified = False
        if info is not None:
            rollback = None
            try:
                rollback = os.open(path, os.O_WRONLY | os.O_NOFOLLOW)
                current = os.fstat(rollback)
                need((current.st_dev, current.st_ino, current.st_size) ==
                     (info.st_dev, info.st_ino, info.st_size + written), 'ENV_EXPORT')
                os.ftruncate(rollback, info.st_size)
                os.fsync(rollback)
                failure.cleanup_verified = True
            except BaseException:
                pass
            finally:
                if rollback is not None:
                    try:
                        os.close(rollback)
                    except BaseException:
                        failure.cleanup_verified = False
        raise failure

def admit(root, output):
    need(__debug__ and not os.environ.get('PYTHONOPTIMIZE') and sys.platform == 'linux' and
         platform.machine() == 'x86_64' and os.geteuid() != 0 and os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted' and os.environ.get('RUNNER_OS') == 'Linux' and
         os.environ.get('RUNNER_ARCH') == 'X64' and os.environ.get('GITHUB_REPOSITORY') == 'Russianranger/coh-android'
         and os.environ.get('GITHUB_REF') == 'refs/heads/native-android', 'HOSTED_DESTINATION')
    revision = os.environ.get('GITHUB_SHA', '')
    need(re.fullmatch('[0-9a-f]{40}', revision), 'SOURCE_HEAD')
    need('INITIAL_BUILD_SHA256' not in os.environ, 'ENV_EXPORT')
    root = root.resolve(strict=True)
    own_name = Path(__file__).resolve().relative_to(root).as_posix()
    runner = Path(os.environ['RUNNER_TEMP']).resolve(strict=True)
    need(output.is_absolute() and output.parent.resolve(strict=True) == output.parent and
         runner in output.parents and root not in output.parents and output not in root.parents and
         not os.path.lexists(output), 'PRIVATE_OUTPUT')
    parent = output.parent.stat()
    need(parent.st_uid == os.geteuid() and not parent.st_mode & 0o077, 'PRIVATE_OUTPUT')
    binary_raw, build_raw, mapping, artifact_pins = evidence(root)
    gate_path, gate_sha, pins = admit_gate(root, runner, revision, own_name, artifact_pins)
    need(all(k not in pins or pins[k] == v for k, v in mapping.items()), 'CURRENT_43_MAP')
    pins = {**pins, **mapping}
    committed(root, pins, revision)
    need(not any(getattr(m, '__file__', None) and root in Path(m.__file__).resolve().parents
                 for key, m in sys.modules.items() if key != '__main__'), 'IMPORTED_SOURCE')
    output.mkdir(mode=0o700)
    created = []
    try:
        os.chmod(output, 0o700)
        binary, build = output / BASENAME, output / 'build.json'
        for path, value, mode in ((binary, binary_raw, 0o700), (build, build_raw, 0o600)):
            created.append((path, write_new(path, value, mode)))
        sys.dont_write_bytecode = True
        sys.pycache_prefix = str(output / 'unused-bytecode')
        sys.path.insert(0, str(root / 'native-android/engine/scenecatalog-server'))
        capture = importlib.import_module('capture_groups_transaction')
        need(Path(capture.__file__).resolve() == root / 'native-android/engine/scenecatalog-server/capture_groups_transaction.py',
             'IMPORTED_SOURCE')
        imported_sources(root, pins)
        saved_environment = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update(CLEAN_ENV)
            native = capture.native_input(binary, build, BUILD_SHA, root)
        except Exception:
            raise Refused('NATIVE_INPUT') from None
        finally:
            os.environ.clear()
            os.environ.update(saved_environment)
        need(native['dependencies_sha256'] == mapping and native['project_dependencies'] == 43 and
             native['source_revision'] == HISTORICAL, 'CURRENT_43_MAP')
        imported_sources(root, pins)
        committed(root, pins, revision)
        static_elf(binary, output)
        systems = system_files()
        loader_checks(binary, output, systems)
        def recheck():
            need(system_files() == systems, 'SYSTEM_FILES_CHANGED')
            need(raw(binary) == binary_raw and raw(build) == build_raw, 'COPY_CHANGED')
            need(evidence(root)[:2] == (binary_raw, build_raw) and digest(raw(gate_path)) == gate_sha, 'LATE_INPUT')
            committed(root, pins, revision)
            imported_sources(root, pins)
        recheck()
        result = {'schema': 'coh-retained-initial-receiver-reuse-v1', 'passed': True,
                  'source_revision': revision, 'historical_build_source_revision': HISTORICAL,
                  'original_build_receipt_sha256': BUILD_SHA, 'binary_sha256': ELF_SHA,
                  'project_dependencies': 43, 'dependencies_sha256': mapping,
                  'source_gate_sha256': gate_sha, 'helper_sha256': pins[own_name],
                  'historical_checks_each_mode': 151, 'historical_status_files': 12,
                  'historical_controls_reexecuted': False, 'binary_recompiled': False,
                  'static_elf_interpreter': INTERPRETER, 'static_elf_needed': NEEDED,
                  'static_elf_required_versions': VERSIONS, 'destination_system_files': systems,
                  'loader_verify_passed': True, 'loader_list_passed': True,
                  'noargs_exit_status': 2, 'noargs_stdout_bytes': 0, 'noargs_stderr_bytes': 0,
                  'cleanup_verified': True, 'services_started_by_helper': False,
                  'actual_loaded_mappings_verified': False, 'full_system_or_toolchain_closure_verified': False,
                  'crypto_RNG_or_protocol_functionality_verified': False,
                  'source_generation_admitted': False, 'actor_publication': False,
                  'world_authority': False, 'application_ACK_permitted': False}
        receipt = output / 'receiver-reuse.json'
        receipt_bytes = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
        created.append((receipt, write_new(receipt, receipt_bytes, 0o600)))
        recheck()
        need(raw(receipt) == receipt_bytes and {p.name for p in output.iterdir()} ==
             {BASENAME, 'build.json', 'receiver-reuse.json'}, 'REUSE_RECEIPT_CHANGED')
        for path, identity in created:
            info = path.lstat()
            need(stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) == identity and
                 stat.S_IMODE(info.st_mode) == (0o700 if path.name == BASENAME else 0o600), 'COPY_CHANGED')
        export_env(Path(os.environ['GITHUB_ENV']), runner)
        return result
    except BaseException as failure:
        cleanup = getattr(failure, 'cleanup_verified', True)
        for path, identity in reversed(created):
            cleanup = unlink_owned(path, identity) and cleanup
        code = failure.code if isinstance(failure, Refused) else 'RECEIVER_REUSE_REFUSED'
        try:
            write_new(output / 'receiver-reuse.json', (json.dumps({'schema': 'coh-retained-initial-receiver-reuse-v1',
                      'passed': False, 'code': code, 'cleanup_verified': cleanup,
                      'services_started_by_helper': False, 'source_generation_admitted': False,
                      'world_authority': False}, sort_keys=True) + '\n').encode(), 0o600)
        except BaseException:
            pass
        raise

def main():
    try:
        values = sys.argv[1:]
        need(len(values) == 4 and set(values[::2]) == {'--source-root', '--output'}, 'ARGUMENTS')
        args = dict(zip(values[::2], values[1::2]))
        admit(Path(args['--source-root']), Path(args['--output']))
        print(json.dumps({'passed': True, 'receiver_reused': True, 'historical_controls_reexecuted': False,
                          'source_generation_admitted': False, 'world_authority': False}, sort_keys=True))
        return 0
    except BaseException as failure:
        code = failure.code if isinstance(failure, Refused) else 'RECEIVER_REUSE_REFUSED'
        print(json.dumps({'passed': False, 'code': code}, sort_keys=True))
        return 1

if __name__ == '__main__':
    sys.exit(main())
