#!/usr/bin/env python3
"""Opt-in, pre-Game GPU prerequisite checks; ordinary Software stays the default.

The driver and both finite probes are current APK-pinned inputs. A successful
probe only selects an environment for an owned Game attempt. It cannot certify
Game rendering, Android presentation, or physical FPS. Probe failures fall back
before Game starts; cancellation or unverifiable cleanup stops the operation.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time
from types import SimpleNamespace
import zipfile

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


def private_wgl_probe(owner, environment, executable, directory, receipt):
    """Separate prefix/token prevents probe cleanup from touching the running server."""
    import diagnostic as base
    from game_device_diagnostic import DeviceWineProcessOwner
    proxy = SimpleNamespace(secrets=owner.ctx.secrets, report={})
    process_owner = DeviceWineProcessOwner(proxy)
    process_owner.initialize()
    owners = getattr(owner, 'gpu_probe_owners', None)
    if owners is None:
        owners = owner.gpu_probe_owners = []
    prefix = directory / 'wineprefix'
    prefix.mkdir(mode=0o700)
    prefix_identity = (prefix.stat().st_dev, prefix.stat().st_ino)
    process_owner.gpu_prefix_identity = prefix_identity
    probe_environment = dict(environment)
    probe_environment.update(process_owner.environment)
    probe_environment['WINEPREFIX'] = str(prefix)
    owners.append((process_owner, probe_environment, prefix, receipt))
    started = time.monotonic()
    try:
        child = run_probe(owner, 'gpu-wine-prerequisites', [owner.args.wine, base.windows_path(executable)],
                          probe_environment, 90, allow_background_output=True)
        probe_error = getattr(child, 'gpu_probe_error', None)
        if probe_error is not None:
            receipt['wine_probe_execution_failure'] = {'type': type(probe_error).__name__,
                'message': str(probe_error)[:500]}
        record_wgl_probe(child, receipt)
    finally:
        receipt['wine_probe_initialization_and_execution_seconds'] = round(time.monotonic() - started, 3)
        # Only this prefix is shut down. The accepted Game/server prefix and its
        # current lifecycle/readiness markers are never read or modified here.
        try:
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
            shutil.rmtree(prefix)
            receipt['probe_cleanup_safe'] = True
        except BaseException as error:
            receipt['probe_cleanup_safe'] = False
            receipt['probe_process_cleanup'] = process_owner.receipt
            raise GPUCleanupError('GPU probe cleanup needs attention: ' + str(error)[:300]) from error
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
    try:
        require(requested == 'turnip', 'Unknown requested GPU profile')
        require(count <= 4, 'GPU profile attempt count exceeded bound')
        producer = owner.ctx.report.get('client_renderer_attribution')
        require(getattr(owner, 'client_renderer_attribution', False) is True
                and isinstance(producer, dict) and producer.get('verified') is True
                and producer.get('repository_commit') == GAME_SOURCE_COMMIT
                and producer.get('client_executable_sha256') == owner.client_executable_sha256 == GAME_SHA256,
                'GPU profile lacks the current verified .19 Game producer')
        require(platform_is_arm64(), 'GPU test requires the retained native ARM64 guest')
        owner.ctx.event('stage', status='running', message='Checking GPU test prerequisites before Game launch')
        directory = owner.root / ('gpu-profile-' + owner.args.session_id + '-' + str(count))
        archive_receipt = verify_archive(owner.args.assets / ARCHIVE,
            owner.ctx.report.get('asset_sha256', {}).get(ARCHIVE), directory,
            on_created=lambda created: record_directory(owner, created))
        receipt.update(archive_receipt)
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
        receipt['vulkan_probe'] = validate_vulkan_probe(run_probe(owner, 'gpu-native-vulkan-prerequisites',
            [directory / 'coh-vulkan-gpu-probe'], environment, 30))
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


def platform_is_arm64():
    import platform
    return platform.machine().lower() in ('aarch64', 'arm64')
