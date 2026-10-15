#!/usr/bin/env python3
"""Opt-in, pre-Game GPU prerequisite checks; ordinary Software stays the default.

The driver and both finite probes are current APK-pinned inputs. A successful
probe only selects an environment for an owned Game attempt. It cannot certify
Game rendering, Android presentation, or physical FPS. Probe failures fall back
before Game starts; cancellation or unverifiable cleanup stops the operation.
"""
import hashlib
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time
from types import SimpleNamespace
import zipfile

import native_responsiveness_contract as native_candidate
import native_startup_metadata_contract as metadata

ARCHIVE = 'hardware-renderer.zip'
MANIFEST = 'hardware-renderer-manifest.json'
MEMBERS = {MANIFEST, 'libvulkan_freedreno.so', 'coh-vulkan-gpu-probe',
           'coh-gpu-probe.exe', 'hardware-renderer-build-input.json', 'THIRD_PARTY_NOTICES.md'}
ARCHIVE_LIMIT = 64 * 1024 * 1024
UNCOMPRESSED_LIMIT = 128 * 1024 * 1024
PROBE_OUTPUT_LIMIT = 64 * 1024
NATIVE_PREFIX = 'COH_VULKAN_GPU_PROBE_V1 '
WGL_PREFIX = 'COH_GPU_PROBE_V2 '
MESA_SOURCE_SHA256 = '2a44e98e64d5c36cec64633de2d0ec7eff64703ee25b35364ba8fcaa84f33f72'
GAME_SOURCE_COMMIT = 'a4a658be25d2b5ca1393b7d3daedd83a7d9ca1f4'
GAME_SHA256 = 'adcabb11135fe44b2c1f997a088ec58e4ea0d90e9defaa9f88efea34538caa44'
PIPELINE_SOURCE_COMMIT = '5af0e27ccf6fbb53d5b3ff5c2c2f3bf5a1d58396'
PIPELINE_GAME_SHA256 = '1953fa3ed1bee3dcdecaed14ccd369730a13bc4addf06ddfc283f7f6f9211b72'
WGL_TRUE = ('zink_nonsoftware', 'multitexture', 'texture_compression', 'arb_vertex_program',
    'arb_fragment_program', 'framebuffer_extension', 'vertex_buffer_object', 's3tc', 'npot',
    'bgra_extension', 'api_loaded', 'arb_programs', 'multitexture_render', 'vbo_render',
    'npot_depth24_fbo', 'dxt1_render', 'dxt3_render', 'dxt5_render', 'dxt1_mipmaps',
    'dxt3_mipmaps', 'dxt5_mipmaps', 'dxt1_subimage', 'dxt3_subimage', 'dxt5_subimage',
    'bgra_render', 'bgra_subimage', 'backbuffer_render', 'swapped', 'presented_pattern_first',
    'presented_pattern_second', 'presented_readback', 'cleanup_ok')
AUTHORITY_FALSE = ('game_rendering_validated', 'cg_shaders_validated',
                   'android_surface_validated', 'hardware_acceleration_validated')


class GPUProfileError(Exception):
    pass


class GPUCleanupError(GPUProfileError):
    """An unsafe probe cannot launch a fallback Game."""


def require(condition, message):
    if not condition:
        raise GPUProfileError(message)


def unique_json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'GPU receipt contains duplicate JSON keys')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique)


def checked_regular(path, limit):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'GPU input requires an absolute private path')
    cursor = Path(path.anchor)
    for component in path.parts[1:]:
        cursor /= component
        require(not cursor.is_symlink(), 'Linked GPU input refused')
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit,
            'Missing, nonregular or oversized GPU input: ' + path.name)
    return info


def verify_archive(archive_path, expected_sha256, destination, *, on_created=None):
    """Hash and read one held regular file; publish only its exact safe closure."""
    before = checked_regular(archive_path, ARCHIVE_LIMIT)
    require(isinstance(expected_sha256, str) and re.fullmatch(r'[0-9a-f]{64}', expected_sha256),
            'GPU archive has no current verified APK asset pin')
    descriptor = os.open(archive_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        require(identity(os.fstat(stream.fileno())) == identity(before), 'GPU archive changed before verification')
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        require(digest.hexdigest() == expected_sha256, 'GPU archive differs from its current APK asset pin')
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            entries = archive.infolist()
            require(len(entries) == len(MEMBERS) and {entry.filename for entry in entries} == MEMBERS,
                    'GPU archive must have its exact six-member inventory')
            require(len({entry.filename.casefold() for entry in entries}) == len(entries), 'Duplicate GPU archive member')
            for entry in entries:
                mode = entry.external_attr >> 16
                require(not entry.is_dir() and not entry.flag_bits & 1 and stat.S_IFMT(mode) in (0, stat.S_IFREG)
                        and 0 < entry.file_size <= 64 * 1024 * 1024, 'Unsafe GPU archive member')
            require(sum(entry.file_size for entry in entries) <= UNCOMPRESSED_LIMIT,
                    'GPU archive exceeded its expanded bound')
            require(archive.getinfo(MANIFEST).file_size <= 1024 * 1024, 'GPU manifest exceeded bound')
            raw = archive.read(MANIFEST)
            manifest = unique_json(raw)
            validate_manifest(manifest)
            require(not os.path.lexists(destination), 'GPU extraction destination already exists')
            require(Path(destination).parent.is_dir() and not Path(destination).parent.is_symlink(),
                    'GPU extraction parent is not a private directory')
            Path(destination).mkdir(mode=0o700)
            if on_created is not None:
                on_created(Path(destination))
            for entry in entries:
                pin = manifest['files'].get(entry.filename)
                if pin is not None:
                    require(entry.file_size == pin['bytes'], 'GPU member size differs: ' + entry.filename)
                digest = hashlib.sha256()
                written = 0
                target = Path(destination) / entry.filename
                with archive.open(entry) as source, target.open('xb') as output:
                    while True:
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        written += len(block)
                        require(written <= entry.file_size, 'GPU member grew while extracting')
                        digest.update(block)
                        output.write(block)
                require(written == entry.file_size and (pin is None or digest.hexdigest() == pin['sha256']),
                        'GPU member pin differs: ' + entry.filename)
                target.chmod(0o600 if pin is None else pin['mode'])
            require(identity(os.fstat(stream.fileno())) == identity(before)
                    == identity(Path(archive_path).lstat()), 'GPU archive changed during extraction')
    return {'archive_sha256': expected_sha256, 'archive_bytes': before.st_size,
            'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'manifest': manifest}


def validate_manifest(value):
    fields = {'format', 'role', 'repository_commit', 'run_url', 'mesa_version', 'mesa_source_sha256',
              'platform', 'driver', 'gpu', 'files', 'software_default', 'physical_hardware_validated'}
    require(isinstance(value, dict) and set(value) == fields and type(value.get('format')) is int
            and value['format'] == 1 and value['role'] == 'client_hardware_renderer'
            and value['mesa_version'] == '26.0.0' and value['platform'] == 'linux-arm64-gnu-bookworm'
            and value['driver'] == 'turnip_kgsl' and value['gpu'] == 'Adreno740'
            and value['software_default'] is True and value['physical_hardware_validated'] is False,
            'GPU producer identity or evidence scope differs')
    require(re.fullmatch(r'[0-9a-f]{40}', str(value['repository_commit']))
            and value['mesa_source_sha256'] == MESA_SOURCE_SHA256
            and re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/[0-9]{1,20}', str(value['run_url'])),
            'GPU producer source or hosted provenance is missing')
    files = value['files']
    require(isinstance(files, dict) and set(files) == MEMBERS - {MANIFEST}, 'GPU producer closure differs')
    for name, pin in files.items():
        require(isinstance(pin, dict) and set(pin) == {'bytes', 'sha256', 'mode'}
                and type(pin['bytes']) is int and 0 < pin['bytes'] <= 64 * 1024 * 1024
                and re.fullmatch(r'[0-9a-f]{64}', str(pin['sha256']))
                and type(pin['mode']) is int and pin['mode'] == (0o755 if name == 'coh-vulkan-gpu-probe' else 0o644),
                'GPU producer member pin or mode differs: ' + name)


def candidate_environment(baseline, icd_path):
    """No inherited forcing/debug/version flags can make the GPU probes pass."""
    environment = dict(baseline)
    for name in tuple(environment):
        if (name.startswith(('MESA_', 'TU_', 'VK_', 'GALLIUM_', 'ZINK_', 'LIBGL_'))
                or name in ('LP_NUM_THREADS', 'DRI_PRIME', 'EGL_PLATFORM', 'GBM_BACKEND',
                            '__GLX_VENDOR_LIBRARY_NAME', '__EGL_VENDOR_LIBRARY_FILENAMES')):
            environment.pop(name, None)
    environment.update(MESA_LOADER_DRIVER_OVERRIDE='zink', VK_DRIVER_FILES=str(icd_path),
                       VK_ICD_FILENAMES=str(icd_path), MESA_VK_WSI_DEBUG='sw')
    return environment


def parse_probe(output, prefix):
    require(isinstance(output, str) and len(output.encode('utf-8')) <= PROBE_OUTPUT_LIMIT,
            'GPU probe output exceeded its bound')
    lines = [line for line in output.splitlines() if line.startswith(prefix.rstrip())]
    require(len(lines) == 1 and lines[0].startswith(prefix) and len(lines[0]) <= 16384,
            'GPU probe needs one complete bounded result')
    value = unique_json(lines[0][len(prefix):])
    require(isinstance(value, dict), 'GPU probe result must be an object')
    return value


def validate_vulkan_probe(output):
    value = parse_probe(output, NATIVE_PREFIX)
    fields = {'format', 'pointer_bits', 'status', 'failure_stage', 'vendor_id', 'device_id', 'device_type',
              'api_version', 'driver_version', 'driver_id', 'native_gpu_executed', 'fill_verified',
              'bytes_verified', 'expected_bytes', 'elapsed_ms', 'kgsl_chip_id', 'kgsl_verified'}
    require(set(value) == fields, 'Native GPU probe fields differ')
    for key in fields - {'status', 'failure_stage', 'native_gpu_executed', 'fill_verified', 'kgsl_verified'}:
        require(type(value[key]) is int and 0 <= value[key] <= 0xffffffff, 'Native GPU probe numeric field differs: ' + key)
    require(value['format'] == 1 and value['pointer_bits'] == 64 and value['status'] == 'passed'
            and value['failure_stage'] == '' and value['vendor_id'] == 0x5143
            and value['device_type'] == 1 and value['driver_id'] == 18
            and value['driver_version'] == (26 << 22) and value['kgsl_verified'] is True
            and value['device_id'] == value['kgsl_chip_id']
            and (value['device_id'] in (0x43050a01, 0x43050b00) or (value['device_id'] & 0xffffff00) == 0x07040000)
            and value['api_version'] >= ((1 << 22) | (2 << 12)) and value['elapsed_ms'] <= 60000
            and value['native_gpu_executed'] is True and value['fill_verified'] is True
            and value['bytes_verified'] == value['expected_bytes'] == 4096,
            'Native Vulkan did not prove the pinned Turnip Adreno 740 execution')
    return value


def validate_wgl_probe(output):
    value = parse_probe(output, WGL_PREFIX)
    fields = set(WGL_TRUE) | set(AUTHORITY_FALSE) | {'format', 'pointer_bits', 'scope', 'status', 'passed',
        'failure', 'win32_error', 'gl_error', 'gl_vendor', 'gl_renderer', 'gl_version',
        'fp_max_local_parameters', 'fp_max_temporaries', 'fp_max_native_temporaries', 'build_marker',
        'frontbuffer_readback', 'frontbuffer_gl_error', 'presentation_method', 'presentation_sample_count',
        'presentation_pattern_count', 'presentation_client_width', 'presentation_client_height',
        'presentation_attempts_first', 'presentation_attempts_second', 'presentation_elapsed_ms_first',
        'presentation_elapsed_ms_second', 'presented_pixels_first', 'presented_pixels_second'}
    require(set(value) == fields, 'Wine GPU prerequisite probe fields differ')
    require(type(value.get('format')) is int and value['format'] == 2
            and type(value.get('pointer_bits')) is int and value['pointer_bits'] == 32
            and value.get('scope') == 'bounded_wgl_gpu_prerequisites'
            and value.get('build_marker') == 'COH_GPU_PROBE_BUILD:production',
            'Wine GPU prerequisite probe changed scope')
    require(value.get('status') == 'passed' and value.get('passed') is True
            and value.get('failure') == '',
            'Wine GPU prerequisite probe failed: ' + (value['failure']
                if isinstance(value.get('failure'), str)
                and re.fullmatch(r'[a-z0-9_]{1,128}', value['failure']) else 'invalid_result'))
    require(type(value.get('gl_error')) is int and value['gl_error'] == 0
            and type(value.get('win32_error')) is int and value['win32_error'] == 0,
            'Wine GPU prerequisite probe failed or changed scope')
    require(all(value.get(key) is False for key in AUTHORITY_FALSE), 'Wine probe exceeds its actual prerequisite scope')
    require(all(value.get(key) is True for key in WGL_TRUE), 'Wine GPU pixel or native client capability proof is incomplete')
    require(type(value['frontbuffer_readback']) is bool and type(value['frontbuffer_gl_error']) is int
            and 0 <= value['frontbuffer_gl_error'] <= 0xffffffff,
            'Wine GPU front-buffer diagnostic fields differ')
    require(value['presentation_method'] == 'win32_screen_getpixel_two_patterns',
            'Wine GPU presented-pixel method differs')
    for key, expected in (('presentation_sample_count', 4), ('presentation_pattern_count', 2),
                          ('presentation_client_width', 64), ('presentation_client_height', 64)):
        require(type(value[key]) is int and value[key] == expected,
                'Wine GPU presented-pixel geometry differs: ' + key)
    for suffix in ('first', 'second'):
        attempts, elapsed = value['presentation_attempts_' + suffix], value['presentation_elapsed_ms_' + suffix]
        require(type(attempts) is int and 1 <= attempts <= 100
                and type(elapsed) is int and 0 <= elapsed <= 2000,
                'Wine GPU presented-pixel observation exceeded its bound: ' + suffix)
    patterns = (((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)),
                ((41, 93, 173), (211, 57, 99), (77, 201, 33), (163, 29, 227)))
    for suffix, expected in zip(('first', 'second'), patterns):
        pixels = value['presented_pixels_' + suffix]
        require(isinstance(pixels, list) and len(pixels) == 4,
                'Wine GPU presented-pixel samples differ: ' + suffix)
        for pixel, target in zip(pixels, expected):
            require(isinstance(pixel, list) and len(pixel) == 3
                    and all(type(channel) is int and 0 <= channel <= 255 and abs(channel - wanted) <= 3
                            for channel, wanted in zip(pixel, target)),
                    'Wine GPU presented pixels differ: ' + suffix)
    require(type(value.get('fp_max_local_parameters')) is int and value['fp_max_local_parameters'] >= 32
            and type(value.get('fp_max_temporaries')) is int and value['fp_max_temporaries'] >= 17
            and type(value.get('fp_max_native_temporaries')) is int and value['fp_max_native_temporaries'] >= 17,
            'Wine GPU ARB fragment program limits are below the stock client minimum')
    for key in ('gl_vendor', 'gl_renderer', 'gl_version'):
        require(isinstance(value.get(key), str) and 0 < len(value[key].encode('utf-8')) <= 512,
                'Wine GPU identity is missing or oversized: ' + key)
    renderer = value['gl_renderer'].lower()
    require('zink' in renderer and not any(word in renderer for word in ('llvmpipe', 'lavapipe', 'softpipe', 'swiftshader')),
            'Wine GPU probe observed a software or non-Zink renderer')
    return value


def run_probe(owner, label, command, environment, timeout, *, allow_background_output=False):
    """Keep a private-prefix leader's exit status until its owner proves EOF.

    The native path requires zero exit and output EOF immediately. The Wine
    path retains its owned child and original error; only private_wgl_probe can
    reject it after stopping the isolated prefix and proving leader exit/EOF.
    """
    import diagnostic as base
    environment = metadata.scrub_attempt_environment(environment)
    try:
        child = owner.ctx.start(label, command, env=environment)
    except base.DiagnosticError as error:
        owner.gpu_probe_owner_check_failure = error
        raise
    child.gpu_probe_error = None
    deadline = time.monotonic() + timeout
    try:
        while child.process.poll() is None or (child.reader.is_alive() and not allow_background_output):
            check_probe_owner(owner)
            require(len(child.output) <= PROBE_OUTPUT_LIMIT and not child.overflow, 'GPU probe exceeded output bound')
            require(time.monotonic() < deadline, 'GPU probe timed out: ' + label)
            time.sleep(.05)
        child.writer.join(timeout=1)
        if allow_background_output:
            child.reader.join(timeout=.2)
        check_probe_owner(owner)
        require(len(child.output) <= PROBE_OUTPUT_LIMIT and not child.overflow, 'GPU probe exceeded output bound')
        child.completion = {'policy': 'leader_exit_with_owned_background_output' if allow_background_output
                            else 'leader_exit_and_output_eof', 'leader_exit_code': child.process.poll(),
                            'output_capture_open': child.reader.is_alive(),
                            'elapsed_seconds': round(time.monotonic() - child.started, 3)}
        result = owner.ctx.record(child)
        if not allow_background_output:
            require(result['exit_code'] == 0, 'GPU probe exited without success: ' + label)
        return child if allow_background_output else child.text()
    except BaseException as error:
        if allow_background_output:
            # Services may retain the capture pipe in separate Wine sessions.
            # Keep the child witness for the private-token cleanup instead of
            # deciding safety from group-only stop while those services live.
            child.gpu_probe_error = error
            child.completion = {'policy': 'private_prefix_shutdown_after_probe_failure',
                'leader_exit_code': child.process.poll(), 'output_capture_open': child.reader.is_alive(),
                'elapsed_seconds': round(time.monotonic() - child.started, 3),
                'failure_type': type(error).__name__}
            return child
        stop_error = None
        try:
            child.stop()
        except BaseException as failed_stop:
            stop_error = failed_stop
        finally:
            try:
                owner.ctx.record(child, refresh=True)
            except BaseException as failed_record:
                stop_error = stop_error or failed_record
        if stop_error is not None or child.process.poll() is None or child.reader.is_alive() or child.writer.is_alive():
            raise GPUCleanupError('GPU probe process shutdown could not be proved: ' + label) from (stop_error or error)
        raise


def check_probe_owner(owner):
    """An operation-health failure is fatal even if a later check recovers."""
    try:
        owner.ctx.check()
    except BaseException as error:
        owner.gpu_probe_owner_check_failure = error
        raise


def record_wgl_probe(child, receipt):
    """Retain a bounded failed result even if later private cleanup is unsafe."""
    receipt['wine_probe_leader_exit_code'] = child.process.poll()
    receipt['wine_probe_output_bytes'] = len(child.output)
    try:
        if child.overflow or len(child.output) > PROBE_OUTPUT_LIMIT:
            return
        value = parse_probe(child.text(), WGL_PREFIX)
    except (GPUProfileError, ValueError):
        return
    receipt['wine_gl_probe'] = value
    failure = value.get('failure')
    if isinstance(failure, str) and re.fullmatch(r'[a-z0-9_]{1,128}', failure):
        receipt['wine_probe_failure_stage'] = failure


def verify_private_prefix(prefix, identity):
    require(isinstance(prefix, Path) and not prefix.is_symlink() and prefix.is_dir()
            and (prefix.stat().st_dev, prefix.stat().st_ino) == identity,
            'Private GPU probe prefix changed before cleanup')


class ProbePrefixCache:
    """Lease only an initialized, closed probe prefix; never cache GPU results.

    A durable busy marker precedes every native launch. Interrupted/changed
    generations are preserved and never reused. The flock is private to this
    operation and close-on-exec. All Wine/Vulkan checks still execute now.
    """
    POLICY = 'closed_owned_gpu_probe_prefix_v1'
    LIMIT = 16384

    def __init__(self, owner, environment, receipt):
        self.owner, self.fd, self.prefix, self.root_identity = owner, None, None, None
        self.prefix_identity = None
        self.report = receipt.setdefault('probe_prefix_cache', {
            'policy': self.POLICY, 'reused': False, 'published_closed': False,
            'fresh_wgl_probe_required': True, 'hardware_result_reused': False})
        self.marker = None
        self.identity = None
        self.prior_owner = None

    @staticmethod
    def state(info):
        return [info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode,
                info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink]

    @staticmethod
    def owned_directory(path):
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                and not info.st_mode & 0o022, 'Unowned GPU prefix cache directory')
        return [info.st_dev, info.st_ino, info.st_uid]

    def inventory(self, prefix):
        root = self.owned_directory(prefix)
        directories = {prefix: self.state(prefix.lstat())}
        pending, rows, regular_bytes = [prefix], [], 0
        while pending:
            self.owner.ctx.check()
            current = pending.pop()
            require(self.state(current.lstat()) == directories[current],
                    'GPU prefix directory changed during inventory')
            with os.scandir(current) as entries:
                for entry in entries:
                    info = entry.stat(follow_symlinks=False)
                    require(info.st_uid == os.geteuid(), 'Foreign GPU probe prefix entry')
                    path = Path(entry.path)
                    row = [path.relative_to(prefix).as_posix(), self.state(info)]
                    if stat.S_ISDIR(info.st_mode):
                        directories[path] = self.state(info)
                        pending.append(path)
                    elif stat.S_ISLNK(info.st_mode):
                        # Wine owns drive/DLL symlinks. Record their exact text;
                        # never traverse them into the game prefix or runtime.
                        row.append(os.readlink(path))
                    else:
                        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                                'Nonregular or shared GPU prefix entry')
                        regular_bytes += info.st_size
                    rows.append(row)
                    require(len(rows) <= self.LIMIT and regular_bytes <= 1024**3,
                            'GPU probe prefix inventory exceeds bound')
        require(self.owned_directory(prefix) == root and all(
            self.state(path.lstat()) == before for path, before in directories.items()),
            'GPU prefix root or parent changed during inventory')
        rows.sort(key=lambda row: row[0])
        raw = json.dumps(rows, separators=(',', ':'), ensure_ascii=True).encode()
        return {'directory': root, 'root_state': directories[prefix],
                'entries': len(rows), 'regular_bytes': regular_bytes,
                'inventory_sha256': hashlib.sha256(raw).hexdigest()}

    def verify_stopped(self, prefix):
        import diagnostic as base
        try:
            return base.verify_wine_stopped(prefix)
        except base.DiagnosticError as error:
            raise GPUProfileError('GPU prefix is not independently stopped: ' + str(error)) from error

    def verify_prior_stopped(self, prefix, prior_owner=None):
        """Reopen a closed generation after Android replaced the guest /tmp.

        Native shutdown at publication still needs the real Wine lock. That
        temporary lock is outside the persistent prefix and need not survive
        the next guest invocation. Absence alone is not a shutdown proof: the
        fallback also checks every inspectable same-UID process and live worker
        for this exact prefix, including processes older than this diagnostic.
        It never signals a process or recreates the missing native lock.
        """
        import diagnostic as base
        try:
            return self.verify_stopped(prefix)
        except GPUProfileError as error:
            if (not isinstance(error.__cause__, base.DiagnosticError)
                    or str(error.__cause__) != 'Wine server lock missing; cannot prove prefix shutdown'):
                raise
        before = absent_wine_endpoint(prefix)
        observation = observe_prior_prefix_owners(prefix, self.owner.ctx, prior_owner=prior_owner)
        require(absent_wine_endpoint(prefix) == before,
                'Prior GPU prefix Wine endpoint changed during ownership inspection')
        return {'policy': 'prior_closed_inventory_and_current_absent_endpoint_and_no_prefix_workers_v1',
                'native_lock_absent': True, 'server_socket_absent': True,
                'prefix_owner_observation': observation,
                'previous_actual_native_shutdown_required': True}

    def publish(self, value):
        require(self.owned_directory(self.owner.root) == self.root_identity,
                'GPU prefix cache parent changed')
        raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        require(len(raw) <= 4096, 'GPU prefix receipt exceeds bound')
        temporary = self.marker.with_name(self.marker.name + '.pending-' + os.urandom(8).hex())
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as output:
                output.write(raw); output.flush(); os.fsync(output.fileno())
            if os.path.lexists(self.marker):
                info = self.marker.lstat()
                require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
                        and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600,
                        'GPU prefix receipt changed before publication')
            os.replace(temporary, self.marker)
            directory_fd = os.open(self.owner.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)

    def checkout(self, environment, receipt):
        try:
            import diagnostic as base
            root = self.owner.root
            self.root_identity = self.owned_directory(root)
            report = self.owner.ctx.report
            runtime = report.get('asset_sha256', {}).get('runtime-lock.json')
            require(re.fullmatch('[0-9a-f]{64}', str(runtime)) is not None
                    and report.get('wine_initialization', {}).get('runtime_lock_sha256') == runtime,
                    'GPU prefix reuse lacks current authenticated Wine/FEX runtime')
            require(all(re.fullmatch('[0-9a-f]{64}', str(receipt.get(key)))
                        for key in ('archive_sha256', 'manifest_sha256')),
                    'GPU prefix reuse lacks exact GPU producer')
            self.identity = {'runtime_lock_sha256': runtime,
                'gpu_archive_sha256': receipt['archive_sha256'],
                'gpu_manifest_sha256': receipt['manifest_sha256'],
                'kernel': list(os.uname()), 'fex_rootfs': environment.get('FEX_ROOTFS'),
                'wine_commands': {str(path): base.file_hash(path) for path in
                    (self.owner.args.wine, self.owner.args.wineserver)}}
            key = hashlib.sha256(json.dumps(self.identity, sort_keys=True).encode()).hexdigest()[:24]
            lock = root / ('gpu-probe-prefix-' + key + '.lock')
            self.fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            info = os.fstat(self.fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
                    and info.st_nlink == 1 and info.st_size == 0 and stat.S_IMODE(info.st_mode) == 0o600,
                    'Unowned GPU prefix lock')
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.marker = root / ('gpu-probe-prefix-' + key + '.json')
            saved = None
            if os.path.lexists(self.marker):
                info = checked_regular(self.marker, 4096)
                require(info.st_uid == os.geteuid() and info.st_nlink == 1
                        and stat.S_IMODE(info.st_mode) == 0o600, 'Unowned GPU prefix receipt')
                saved = unique_json(self.marker.read_bytes())
                require(saved.get('format') == 1 and saved.get('policy') == self.POLICY
                        and saved.get('identity') == self.identity
                        and re.fullmatch('gpu-probe-prefix-' + key + '-[0-9a-f]{32}', str(saved.get('prefix'))),
                        'Unrecognized GPU prefix receipt')
                candidate = root / saved['prefix']
                if saved.get('state') == 'closed':
                    try:
                        require(saved.get('inventory') == self.inventory(candidate),
                                'Closed GPU prefix inventory changed')
                        self.report['prior_native_prefix_shutdown'] = self.verify_prior_stopped(
                            candidate, saved.get('prior_owner'))
                        require(saved.get('inventory') == self.inventory(candidate),
                                'Closed GPU prefix changed during shutdown verification')
                        self.prefix = candidate
                        self.prefix_identity = saved['inventory']['directory']
                        # A generation keeps its original possible-owner age.
                        # Advancing this to the latest checkout could hide an
                        # older process if its temporary Wine namespace later
                        # disappears. Legacy receipts without age provenance
                        # retain the conservative all-age census.
                        self.prior_owner = saved.get('prior_owner')
                        self.report['reused'] = True
                    except (OSError, GPUProfileError) as error:
                        self.report['reuse_refused'] = str(error)[:300]
                else:
                    self.report['reuse_refused'] = 'Prior GPU probe prefix did not prove closed ownership'
            if self.prefix is None:
                count = sum(1 for p in root.iterdir()
                    if re.fullmatch('gpu-probe-prefix-[0-9a-f]{24}-[0-9a-f]{32}', p.name))
                require(count < 8, 'GPU prefix retained generation bound reached')
                self.prefix = root / ('gpu-probe-prefix-' + key + '-' + os.urandom(16).hex())
                self.prefix.mkdir(mode=0o700)
                self.prefix_identity = self.owned_directory(self.prefix)
                self.prior_owner = prior_owner_scope(getattr(self, 'process_owner', None))
            self.publish({'format': 1, 'policy': self.POLICY, 'identity': self.identity,
                'prefix': self.prefix.name, 'state': 'busy'})
            self.report['generation'] = self.prefix.name
            self.verify_checkout()
            return self.prefix
        except (OSError, GPUProfileError, AttributeError, ValueError) as error:
            self.report['reuse_unavailable'] = str(error)[:300]
            self.release()
            if self.root_identity is not None:
                require(self.owned_directory(self.owner.root) == self.root_identity,
                        'GPU prefix cache parent changed during checkout')
            return None
        except BaseException:
            self.release()
            raise

    def close(self):
        self.verify_checkout()
        self.report['current_native_prefix_shutdown'] = self.verify_stopped(self.prefix)
        inventory = self.inventory(self.prefix)
        self.verify_checkout()
        self.publish({'format': 1, 'policy': self.POLICY, 'identity': self.identity,
            'prefix': self.prefix.name, 'state': 'closed', 'inventory': inventory,
            'prior_owner': self.prior_owner})
        self.report.update(published_closed=True, inventory=inventory)

    def verify_checkout(self):
        require(self.owned_directory(self.owner.root) == self.root_identity
                and self.owned_directory(self.prefix) == self.prefix_identity,
                'GPU prefix cache parent or prefix changed after checkout')

    def release(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def absent_wine_endpoint(prefix, *, server_base=None):
    """Read-only absent endpoint proof; never create a substitute Wine lock."""
    identity = ProbePrefixCache.owned_directory(prefix)
    # Match diagnostic.verify_wine_stopped and Wine's guest getuid(), which
    # PRoot virtualizes. The independent /proc census uses status.real_uid;
    # Android's real application UID must never substitute for this path UID.
    base = Path(server_base) if server_base is not None else Path('/tmp') / ('.wine-' + str(os.getuid()))
    server = base / ('server-%x-%x' % (identity[0], identity[1]))
    parents = []
    for directory in (base, server):
        try:
            info = directory.lstat()
        except FileNotFoundError:
            parents.append(None)
            continue
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                and not info.st_mode & 0o077,
                'Unowned or linked prior GPU Wine server directory')
        # Other prefixes can legitimately create sockets beneath the shared
        # .wine-UID directory. Its inode/owner must stay fixed, not its mtime.
        parents.append([info.st_dev, info.st_ino, info.st_uid, info.st_mode])
    require(not os.path.lexists(server / 'lock') and not os.path.lexists(server / 'socket'),
            'Prior GPU Wine lock or endpoint exists without shutdown proof')
    return {'prefix': identity, 'server_directories': parents}


def prior_owner_scope(owner, *, proc_root=Path('/proc')):
    """Persist only the prior cleanup owner's public process-age identity."""
    if owner is None or type(owner.real_uid) is not int or type(owner.diagnostic_starttime) is not int:
        return None
    try:
        boot = (proc_root / 'sys/kernel/random/boot_id').read_text().strip()
    except OSError:
        return None
    if not re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot):
        return None
    return {'format': 1, 'boot_id': boot, 'real_uid': owner.real_uid,
            'earliest_owner_starttime': owner.diagnostic_starttime}


def observe_prior_prefix_owners(prefix, context, *, prior_owner=None, proc_root=Path('/proc')):
    """Bounded read-only census using the existing real-UID/worker verifier.

    The current session's random token cannot identify an earlier generation.
    Matching its exact WINEPREFIX observes every potential prefix owner instead;
    callers must NEVER use this observer for cleanup or signaling.
    """
    import diagnostic as base
    from game_device_diagnostic import DeviceWineProcessOwner

    class ReadOnlyPrefixObserver(DeviceWineProcessOwner):
        def signal_owned(self, *args, **kwargs):
            raise GPUProfileError('A prior-prefix observer cannot signal processes')

        def cleanup(self, *args, **kwargs):
            raise GPUProfileError('A prior-prefix observer cannot clean up processes')

    observer = ReadOnlyPrefixObserver(SimpleNamespace(secrets=[], report={}), proc_root)
    try:
        observer.initialize()
        current_owner_starttime = observer.diagnostic_starttime
        observer.needle = b'WINEPREFIX=' + os.fsencode(prefix)
        # The base owner normally excludes older processes because its token
        # is newly random. That optimization is invalid for a saved prefix.
        observer.diagnostic_starttime = 0
        if prior_owner is not None:
            require(isinstance(prior_owner, dict) and set(prior_owner) == {
                'format', 'boot_id', 'real_uid', 'earliest_owner_starttime'}
                and type(prior_owner['format']) is int and prior_owner['format'] == 1
                and type(prior_owner['real_uid']) is int and prior_owner['real_uid'] == observer.real_uid
                and type(prior_owner['earliest_owner_starttime']) is int
                and 0 < prior_owner['earliest_owner_starttime'] <= current_owner_starttime,
                'Prior GPU prefix process-age authority differs')
            current = prior_owner_scope(observer, proc_root=proc_root)
            require(current is not None and current['boot_id'] == prior_owner['boot_id'],
                    'Prior GPU prefix boot generation differs; fresh private prefix required')
            # Its random path was private to the prior operation. Processes
            # older than that operation could not receive it in their startup
            # environment. Do not inspect unrelated non-dumpable app services.
            observer.diagnostic_starttime = prior_owner['earliest_owner_starttime']
        context.check()
        started = time.monotonic()
        matches = observer.scan(started + 3)
        context.check()
        require(not matches, 'Prior GPU probe prefix still has live processes or workers')
        require(observer.receipt['inspection_failures'] == 0,
                'Prior GPU probe prefix ownership inspection is incomplete')
        return {'policy': 'read_only_exact_prefix_prior_owner_age_and_live_workers_v1',
                'matching_processes': 0, 'complete': True,
                'scanned_processes': observer.receipt['scanned_processes'],
                'scanned_tasks': observer.receipt['scanned_tasks'],
                'elapsed_seconds': round(time.monotonic() - started, 3),
                'earliest_owner_starttime': observer.diagnostic_starttime,
                'signals_sent': 0}
    except (base.DiagnosticError, OSError, ValueError, KeyError, IndexError) as error:
        raise GPUProfileError('Prior GPU prefix ownership could not be proved: ' + str(error)) from error


def private_wgl_probe(owner, environment, executable, directory, receipt):
    environment = metadata.scrub_attempt_environment(environment)
    cache = ProbePrefixCache(owner, environment, receipt)
    try:
        return _private_wgl_probe(owner, environment, executable, directory, receipt, cache)
    finally:
        # Checkout owns a flock before any prefix/environment setup. Even a
        # changed path or cancelled setup must release it without native launch.
        cache.release()


def _private_wgl_probe(owner, environment, executable, directory, receipt, cache):
    """Separate prefix/token prevents probe cleanup from touching the running server."""
    import diagnostic as base
    from game_device_diagnostic import DeviceWineProcessOwner
    proxy = SimpleNamespace(secrets=owner.ctx.secrets, report={})
    process_owner = DeviceWineProcessOwner(proxy)
    process_owner.initialize()
    cache.process_owner = process_owner
    owners = getattr(owner, 'gpu_probe_owners', None)
    if owners is None:
        owners = owner.gpu_probe_owners = []
    checkout_started = time.monotonic()
    prefix = cache.checkout(environment, receipt)
    receipt['probe_prefix_checkout_seconds'] = round(time.monotonic() - checkout_started, 3)
    if prefix is None:
        prefix = directory / 'wineprefix'
        prefix.mkdir(mode=0o700)
    if cache.fd is not None:
        cache.verify_checkout()
    prefix_info = prefix.lstat()
    require(stat.S_ISDIR(prefix_info.st_mode) and prefix_info.st_uid == os.geteuid(),
            'Private GPU probe prefix changed before launch')
    prefix_identity = (prefix_info.st_dev, prefix_info.st_ino)
    process_owner.gpu_prefix_identity = prefix_identity
    probe_environment = dict(environment)
    probe_environment.update(process_owner.environment)
    probe_environment['WINEPREFIX'] = str(prefix)
    owners.append((process_owner, probe_environment, prefix, receipt))
    started = time.monotonic()
    try:
        if cache.fd is not None:
            cache.verify_checkout()
        verify_private_prefix(prefix, prefix_identity)
        child = run_probe(owner, 'gpu-wine-prerequisites', [owner.args.wine, base.windows_path(executable)],
                          probe_environment, 90, allow_background_output=True)
        probe_error = getattr(child, 'gpu_probe_error', None)
        if probe_error is not None:
            receipt['wine_probe_execution_failure'] = {'type': type(probe_error).__name__,
                'message': str(probe_error)[:500]}
        record_wgl_probe(child, receipt)
    finally:
        receipt['wine_probe_initialization_and_execution_seconds'] = round(time.monotonic() - started, 3)
        cleanup_started = time.monotonic()
        # Only this prefix is shut down. The accepted Game/server prefix and its
        # current lifecycle/readiness markers are never read or modified here.
        try:
            if cache.fd is not None:
                cache.verify_checkout()
            verify_private_prefix(prefix, prefix_identity)
            shutdown = owner.ctx.run('gpu-probe-prefix-stop', [owner.args.wineserver, '-k'], timeout=3,
                                     env=probe_environment, cleanup=True, check=False)
            process_owner.cleanup(time.monotonic() + 3)
            receipt['probe_process_cleanup'] = process_owner.receipt
            require(shutdown['exit_code'] == 0 and process_owner.receipt['complete'] is True,
                    'Private GPU probe prefix shutdown could not be proved')
            # A brand-new Wine prefix can leave service children holding its
            # stdout after the probe leader exits. Reap them before requiring
            # EOF; their retained handles must not consume the GL timeout.
            if 'child' in locals():
                child.reader.join(timeout=1)
                child.writer.join(timeout=1)
                require(child.process.poll() is not None
                        and not child.reader.is_alive() and not child.writer.is_alive(),
                        'Private GPU probe leader/output shutdown could not be proved')
                child.completion['output_capture_open'] = False
                child.completion['private_prefix_shutdown_and_output_eof'] = True
                owner.ctx.record(child, refresh=True)
                record_wgl_probe(child, receipt)
            verify_private_prefix(prefix, prefix_identity)
            # Reuse initialization only after successful current native pixels,
            # leader/output EOF and complete private-token cleanup. A failed
            # current probe never leaves a closed reusable generation.
            cacheable = (cache.fd is not None and 'child' in locals()
                and child.process.poll() == 0 and not child.overflow
                and len(child.output) <= PROBE_OUTPUT_LIMIT
                and getattr(child, 'gpu_probe_error', None) is None)
            if cacheable:
                try:
                    validate_wgl_probe(child.text())
                except GPUProfileError:
                    cacheable = False
            if cacheable:
                try:
                    cache.close()
                except GPUProfileError as error:
                    # An integrity refusal must never become authority to
                    # delete the path whose ownership just became uncertain.
                    receipt['probe_prefix_cache']['publication_refused'] = str(error)[:300]
                    raise
                except OSError as error:
                    # Optional cache publication can fail on a full filesystem.
                    # Preserve the prefix; only complete current ownership and
                    # native shutdown checks allow the GPU attempt to proceed.
                    receipt['probe_prefix_cache']['publication_refused'] = str(error)[:300]
                    cache.verify_checkout()
                    cache.verify_stopped(prefix)
                    receipt['probe_prefix_cache']['preserved_after_publication_error'] = True
            if not cacheable:
                if cache.fd is not None:
                    cache.verify_checkout()
                verify_private_prefix(prefix, prefix_identity)
                shutil.rmtree(prefix)
            receipt['probe_cleanup_safe'] = True
        except BaseException as error:
            receipt['probe_cleanup_safe'] = False
            receipt['probe_process_cleanup'] = process_owner.receipt
            raise GPUCleanupError('GPU probe cleanup needs attention: ' + str(error)[:300]) from error
        finally:
            cache.release()
            receipt['wine_probe_cleanup_and_cache_publication_seconds'] = round(
                time.monotonic() - cleanup_started, 3)
    check_probe_owner(owner)
    require(len(child.output) <= PROBE_OUTPUT_LIMIT and not child.overflow,
            'GPU probe output exceeded its bound')
    if probe_error is not None:
        raise probe_error
    result = validate_wgl_probe(child.text())
    require(child.process.poll() == 0,
            'Wine GPU prerequisite probe exited without success: ' + str(child.process.poll()))
    return result


def cleanup_probes(owner):
    """Retry unsafe isolated owners in final cleanup; never claim them reaped."""
    failures = []
    deadline = time.monotonic() + 3
    for process_owner, environment, prefix, receipt in getattr(owner, 'gpu_probe_owners', []):
        if receipt.get('probe_cleanup_safe') is True:
            continue
        try:
            require(time.monotonic() < deadline, 'GPU final cleanup bound expired')
            try:
                verify_private_prefix(prefix, process_owner.gpu_prefix_identity)
                owner.ctx.run('gpu-probe-final-prefix-stop', [owner.args.wineserver, '-k'],
                              timeout=max(.1, min(1, deadline - time.monotonic())),
                              env=environment, cleanup=True, check=False)
            finally:
                # A replaced prefix must never direct wineserver at a different
                # session. Its original token workers remain safe to inspect.
                process_owner.cleanup(deadline)
            receipt['probe_cleanup_safe'] = process_owner.receipt.get('complete') is True
            require(receipt['probe_cleanup_safe'], 'Isolated GPU probe descendants remain')
        except Exception as error:
            receipt['probe_cleanup_safe'] = False
            failures.append('GPU probe descendant cleanup: ' + str(error)[:300])
    return failures


def record_directory(owner, directory):
    owned = getattr(owner, 'gpu_profile_directories', None)
    if owned is None:
        owned = owner.gpu_profile_directories = []
    require(len(owned) < 4 and directory.parent == owner.root and not directory.is_symlink()
            and directory.is_dir(), 'GPU extraction ownership differs')
    info = directory.lstat()
    owned.append((directory, info.st_dev, info.st_ino))


def cleanup_directories(owner):
    """Drop only current-created payload copies, after Game/server process cleanup."""
    failures = []
    records = owner.ctx.report.setdefault('client_gpu_payload_cleanup', [])
    for directory, device, inode in getattr(owner, 'gpu_profile_directories', []):
        row = {'path': directory.name, 'removed': False}
        records.append(row)
        if owner.cleanup_status.get('owned_processes_reaped') is not True:
            row['reason'] = 'owned_process_cleanup_unproved'
            continue
        try:
            require(directory.parent == owner.root and not directory.is_symlink()
                    and re.fullmatch(r'gpu-profile-' + re.escape(owner.args.session_id) + r'-[1-4]', directory.name),
                    'GPU payload cleanup ownership differs')
            info = directory.lstat()
            require(stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == (device, inode),
                    'GPU payload directory changed before cleanup')
            shutil.rmtree(directory)
            row['removed'] = True
        except Exception as error:
            row['reason'] = str(error)[:300]
            failures.append('GPU payload cleanup: ' + row['reason'])
    return failures


def current_metadata_consumer(owner):
    package = getattr(owner, 'client_native_metadata_package', None)
    if package is None: return None
    return metadata.runtime_admission(package, 'game', owner.work / 'CityOfHeroes.exe')


def retained_client_sha256(owner):
    value = current_metadata_consumer(owner)
    return value['previous_consumer_sha256'] if value is not None else getattr(owner, 'client_executable_sha256', None)


def current_consumer_result(owner, historical):
    value = current_metadata_consumer(owner)
    if value is None: return historical
    require(historical['client_executable_sha256'] == value['previous_consumer_sha256'],
        'Current metadata Game does not retain this exact control producer')
    result = dict(historical, client_executable_sha256=value['current_consumer_sha256'],
        producer_scope='retained_controls_in_separately_qualified_metadata_consumer',
        retained_control_producer_executable_sha256=historical['client_executable_sha256'],
        native_metadata_authority_sha256=value['authority_sha256'],
        native_metadata_execution_review_sha256=value['execution_review_sha256'],
        native_metadata_consumer={'executable_sha256': value['current_consumer_sha256'],
            'component_receipt_sha256': metadata.canonical_sha(value['receipt']),
            'native_producer': value['native_producer']},
        physical_fps_improvement_validated=False)
    result['retained_producer'] = {key: result.pop(key) for key in
        ('repository_commit', 'manifest_sha256', 'native_source_sha256') if key in result}
    result['retained_producer']['executable_sha256'] = historical['client_executable_sha256']
    for key in ('current_Game_repository_commit', 'current_Game_manifest_sha256'):
        if key in result: result[key.replace('current_Game_', 'retained_control_Game_')] = result.pop(key)
    return result


def control_producer_field(producer, key):
    # Legacy results retain their exact shape. Additive results state explicitly
    # that these source/manifest hashes belong to the retained control producer.
    return producer[key] if key in producer else producer['retained_producer'][key]


def verified_render_pipeline_producer(owner):
    """Bind the current Game to the full typed extension of the retained .19 Game.

    The payload/probe producer remains separately APK-pinned. Neither a claimed
    current hash nor the old renderer report can authorize replacement bytes.
    Revalidate the whole executable/DLL/source history on each owned attempt.
    """
    package = getattr(owner, 'client_render_pipeline_package', None)
    producer = owner.ctx.report.get('client_render_pipeline')
    require(getattr(owner, 'client_render_pipeline', False) is True
            and isinstance(package, dict) and isinstance(producer, dict),
            'Render pipeline lacks its current typed Game producer')
    record = native_candidate.client_contract(package)
    queue = (verified_render_queue_producer(owner)
             if getattr(owner, 'client_render_queue', False) is True else None)
    if queue is not None:
        require(native_candidate.canonical_sha(package) == native_candidate.canonical_sha(owner.client_render_queue_package),
                'Render pipeline and render queue differ in their current typed package')
    pipeline_record = (native_candidate.client_render_pipeline_contract(package)
                       if queue is not None else record)
    wrapper = package.get('client_render_pipeline')
    require(isinstance(wrapper, dict), 'Render pipeline typed extension is missing')
    parent = package['client_renderer_attribution']
    parent_manifest = parent['manifest']
    manifest = wrapper['manifest']
    require(parent_manifest['repository_commit'] == GAME_SOURCE_COMMIT
            and parent_manifest['files']['CityOfHeroes.exe']['sha256'] == GAME_SHA256
            and wrapper['base_client_executable']['sha256'] == GAME_SHA256,
            'Render pipeline does not extend the exact retained .19 Game producer')
    require(type(producer.get('format')) is int and producer['format'] == 1
            and producer.get('verified') is True
            and producer.get('repository_commit') == manifest['repository_commit']
            and producer.get('manifest_sha256') == wrapper['manifest_sha256']
            and producer.get('base_client_renderer_attribution_manifest_sha256') == parent['manifest_sha256']
            and producer.get('base_client_executable_sha256') == GAME_SHA256
            and producer.get('client_executable_sha256') == pipeline_record['sha256']
            and retained_client_sha256(owner) == record['sha256']
            and producer.get('source_commit') == package['source_commit']
            and producer.get('data_commit') == package['data_commit']
            and producer.get('native_source_sha256') == native_candidate.canonical_sha(manifest['retained_source_inputs'])
            and re.fullmatch(r'[0-9a-f]{64}', str(producer.get('data_source_sha256', '')))
            and producer['data_source_sha256'] == owner.ctx.report.get('import_identity', {}).get('contract_sha256')
            and producer.get('replacement_scope') == 'CityOfHeroes.exe_only'
            and producer.get('source_freshness_preserved') is True
            and producer.get('prepared_cache_schema_changed') is False
            and producer.get('renderer_changed') is False
            and producer.get('graphics_fidelity_preserved') is True
            and producer.get('gameplay_frame_cap_changed') is False
            and producer.get('bounded_render_pipeline_diagnostics') is True
            and producer.get('worker_wakeup_repaired') is True
            and producer.get('physical_fps_improvement_validated') is False,
            'Render pipeline lacks its current verified Game producer')
    result = {'policy': 'exact_retained_renderer_Game_then_full_typed_render_pipeline_v1',
            'repository_commit': manifest['repository_commit'],
            'manifest_sha256': wrapper['manifest_sha256'], 'client_executable_sha256': record['sha256'],
            'retained_renderer_repository_commit': GAME_SOURCE_COMMIT,
            'retained_renderer_manifest_sha256': parent['manifest_sha256'],
            'retained_renderer_executable_sha256': GAME_SHA256,
            'native_source_sha256': native_candidate.canonical_sha(manifest['retained_source_inputs'])}
    if queue is not None:
        result.update(policy='retained_pipeline_in_verified_render_queue_Game_attempt_v1',
            pipeline_producer_executable_sha256=pipeline_record['sha256'],
            current_Game_repository_commit=control_producer_field(queue, 'repository_commit'),
            current_Game_manifest_sha256=control_producer_field(queue, 'manifest_sha256'),
            typed_render_queue_extension=True)
    return current_consumer_result(owner, result)


def verified_render_queue_producer(owner):
    """Extend the exact frozen .22 Game, retaining its raw source and Win32 proof."""
    package = getattr(owner, 'client_render_queue_package', None)
    producer = owner.ctx.report.get('client_render_queue')
    require(getattr(owner, 'client_render_queue', False) is True
            and getattr(owner, 'client_render_pipeline', False) is True
            and isinstance(package, dict) and isinstance(producer, dict),
            'Render queue lacks its current typed Game producer')
    record = native_candidate.client_contract(package)
    wrapper = package.get('client_render_queue')
    require(isinstance(wrapper, dict), 'Render queue typed extension is missing')
    parent = package['client_render_pipeline']
    parent_manifest = parent['manifest']
    renderer = package['client_renderer_attribution']['manifest']
    manifest = wrapper['manifest']
    historical = owner.ctx.report.get('client_render_pipeline')
    require(parent_manifest['repository_commit'] == PIPELINE_SOURCE_COMMIT
            and parent_manifest['files']['CityOfHeroes.exe']['sha256'] == PIPELINE_GAME_SHA256
            and parent_manifest['files']['CityOfHeroes.exe']['size'] == 9494016
            and wrapper['base_client_executable']['sha256'] == PIPELINE_GAME_SHA256
            and renderer['repository_commit'] == GAME_SOURCE_COMMIT
            and renderer['files']['CityOfHeroes.exe']['sha256'] == GAME_SHA256,
            'Render queue does not extend the exact retained .22/.19 Game producers')
    require(isinstance(historical, dict) and type(historical.get('format')) is int
            and historical['format'] == 1 and historical.get('verified') is True
            and historical.get('repository_commit') == PIPELINE_SOURCE_COMMIT
            and historical.get('client_executable_sha256') == PIPELINE_GAME_SHA256
            and historical.get('manifest_sha256') == parent['manifest_sha256'],
            'Render queue changed its retained historical pipeline producer')
    require(type(producer.get('format')) is int and producer['format'] == 1
            and producer.get('verified') is True
            and producer.get('repository_commit') == manifest['repository_commit']
            and producer.get('manifest_sha256') == wrapper['manifest_sha256']
            and producer.get('base_client_render_pipeline_manifest_sha256') == parent['manifest_sha256']
            and producer.get('base_client_executable_sha256') == PIPELINE_GAME_SHA256
            and producer.get('client_executable_sha256') == retained_client_sha256(owner) == record['sha256']
            and producer.get('source_commit') == package['source_commit']
            and producer.get('data_commit') == package['data_commit']
            and producer.get('native_source_sha256') == native_candidate.canonical_sha(manifest['retained_source_inputs'])
            and re.fullmatch(r'[0-9a-f]{64}', str(producer.get('data_source_sha256', '')))
            and producer['data_source_sha256'] == owner.ctx.report.get('import_identity', {}).get('contract_sha256')
            and producer.get('replacement_scope') == 'CityOfHeroes.exe_only'
            and producer.get('source_freshness_preserved') is True
            and producer.get('prepared_cache_schema_changed') is False
            and producer.get('renderer_changed') is False
            and producer.get('graphics_fidelity_preserved') is True
            and producer.get('gameplay_frame_cap_changed') is False
            and producer.get('bounded_render_queue_diagnostics') is True
            and producer.get('render_worker_wake_coalesced') is True
            and producer.get('physical_fps_improvement_validated') is False,
            'Render queue lacks its current verified Game producer')
    return current_consumer_result(owner, {'policy': 'exact_retained_pipeline_Game_then_full_typed_render_queue_v1',
            'repository_commit': manifest['repository_commit'], 'manifest_sha256': wrapper['manifest_sha256'],
            'client_executable_sha256': record['sha256'],
            'retained_pipeline_repository_commit': PIPELINE_SOURCE_COMMIT,
            'retained_pipeline_manifest_sha256': parent['manifest_sha256'],
            'retained_pipeline_executable_sha256': PIPELINE_GAME_SHA256,
            'retained_renderer_repository_commit': GAME_SOURCE_COMMIT,
            'retained_renderer_executable_sha256': GAME_SHA256,
            'native_source_sha256': native_candidate.canonical_sha(manifest['retained_source_inputs'])})


def current_game_producer(owner):
    """Preserve the exact .21 route and admit only its reviewed typed extension."""
    producer = owner.ctx.report.get('client_renderer_attribution')
    require(getattr(owner, 'client_renderer_attribution', False) is True
            and isinstance(producer, dict) and producer.get('verified') is True
            and producer.get('repository_commit') == GAME_SOURCE_COMMIT,
            'GPU profile lacks its verified retained Game attribution producer')
    if getattr(owner, 'client_render_pipeline', False) is True:
        require(producer.get('client_executable_sha256') == GAME_SHA256,
                'GPU profile changed its retained historical Game producer')
        # The pipeline attempt gate validates its raw historical report as well
        # as a possible newer exact extension; GPU selection names the actual
        # current Game producer independently of those retained layer receipts.
        verified = verified_render_pipeline_producer(owner)
        return (verified_render_queue_producer(owner)
                if getattr(owner, 'client_render_queue', False) is True else verified)
    require(producer.get('client_executable_sha256') == getattr(owner, 'client_executable_sha256', None) == GAME_SHA256,
            'GPU profile lacks the current verified .19 Game producer')
    return {'policy': 'exact_retained_renderer_Game_v1', 'repository_commit': GAME_SOURCE_COMMIT,
            'client_executable_sha256': GAME_SHA256}


def apply_profile(owner, baseline, label):
    """Called immediately before each owned initial/retry Game launch."""
    requested = baseline.get('COH_CLIENT_GPU_PROFILE', 'software')
    attempts = owner.ctx.report.setdefault('client_gpu_profile_attempts', [])
    count = owner.ctx.report.get('client_gpu_profile_attempt_count', 0) + 1
    owner.ctx.report['client_gpu_profile_attempt_count'] = count
    receipt = {'format': 1, 'policy': 'owned_Game_attempt_after_bounded_prerequisites',
               'session_id': owner.args.session_id, 'launch_label': label, 'requested': requested,
               'selected': 'software', 'state': 'software_default', 'fallback_reason': None,
               'probe_cleanup_safe': True, 'shared_wine_environment_modified': False,
               'game_prefix_modified_by_probe': False, 'game_rendering_validated': False,
               'hardware_acceleration_validated': False, 'physical_fps_improvement_validated': False,
               'automatic_mid_game_fallback': False}
    attempts.append(receipt)
    del attempts[:-4]
    owner.ctx.report['client_gpu_profile'] = receipt
    if requested == 'software':
        return dict(baseline)
    owner.gpu_probe_owner_check_failure = None
    prerequisites_started = time.monotonic()
    try:
        require(requested == 'turnip', 'Unknown requested GPU profile')
        require(count <= 4, 'GPU profile attempt count exceeded bound')
        receipt['game_producer'] = current_game_producer(owner)
        require(platform_is_arm64(), 'GPU test requires the retained native ARM64 guest')
        owner.ctx.event('stage', status='running', message='Checking GPU test prerequisites before Game launch')
        directory = owner.root / ('gpu-profile-' + owner.args.session_id + '-' + str(count))
        archive_started = time.monotonic()
        archive_receipt = verify_archive(owner.args.assets / ARCHIVE,
            owner.ctx.report.get('asset_sha256', {}).get(ARCHIVE), directory,
            on_created=lambda created: record_directory(owner, created))
        receipt.update(archive_receipt)
        receipt['gpu_archive_verification_and_extraction_seconds'] = round(time.monotonic() - archive_started, 3)
        receipt['gpu_payload_producer'] = {
            'policy': 'retained_APK_pinned_GPU_driver_and_finite_probes_v1',
            'repository_commit': archive_receipt['manifest']['repository_commit'],
            'run_url': archive_receipt['manifest']['run_url'],
            'archive_sha256': archive_receipt['archive_sha256'],
            'manifest_sha256': archive_receipt['manifest_sha256'],
            'game_producer_distinct': True, 'actual_Game_renderer_observed': False}
        driver = directory / 'libvulkan_freedreno.so'
        icd = directory / 'turnip-private-icd.json'
        with icd.open('x', encoding='ascii') as stream:
            json.dump({'file_format_version': '1.0.0', 'ICD': {'library_path': str(driver), 'api_version': '1.3.0'}}, stream)
        icd.chmod(0o600)
        environment = candidate_environment(baseline, icd)
        receipt['candidate_environment'] = {key: environment[key] for key in
            ('MESA_LOADER_DRIVER_OVERRIDE', 'VK_DRIVER_FILES', 'VK_ICD_FILENAMES', 'MESA_VK_WSI_DEBUG')}
        import diagnostic as base
        base.arm64_elf(directory / 'coh-vulkan-gpu-probe')
        base.arm64_elf(driver)
        base.verify_pe32(directory / 'coh-gpu-probe.exe')
        vulkan_started = time.monotonic()
        receipt['vulkan_probe'] = validate_vulkan_probe(run_probe(owner, 'gpu-native-vulkan-prerequisites',
            [directory / 'coh-vulkan-gpu-probe'], environment, 30))
        receipt['vulkan_process_and_verification_seconds'] = round(time.monotonic() - vulkan_started, 3)
        receipt['wine_gl_probe'] = private_wgl_probe(owner, environment, directory / 'coh-gpu-probe.exe', directory, receipt)
        receipt.update(selected='turnip', state='selected_after_probes')
        owner.ctx.event('stage', status='running', message='GPU test prerequisites passed; starting Game with the GPU candidate')
        return environment
    except GPUCleanupError:
        receipt.update(state='unsafe_probe_cleanup', selected=None, probe_cleanup_safe=False)
        raise
    except Exception as error:
        # Cancellation, server-health failure, or the overall deadline remains
        # fatal. Only an ordinary rejected optional prerequisite may fall back.
        if getattr(owner, 'gpu_probe_owner_check_failure', None) is not None:
            raise owner.gpu_probe_owner_check_failure
        check_probe_owner(owner)
        require(receipt['probe_cleanup_safe'] is True, 'Unsafe GPU probe cannot start a fallback Game')
        receipt.update(state='software_fallback', fallback_reason=(type(error).__name__ + ': ' + str(error))[:500])
        owner.ctx.event('stage', status='running', message='No GPU available; using Software. ' + receipt['fallback_reason'])
        return dict(baseline)
    finally:
        receipt['total_prerequisites_seconds'] = round(time.monotonic() - prerequisites_started, 3)


def platform_is_arm64():
    import platform
    return platform.machine().lower() in ('aarch64', 'arm64')
