#!/usr/bin/env python3
"""Bounded actual pinned CoH startup on the accepted private presentation path.

No database/server is started. Process/window evidence does not certify a usable
login menu; bounded screenshots are exported for visual review. Only Android can
certify that the observed pixels reached its native surface.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import presentation_diagnostic as presentation
import game_hang_evidence
base, require = presentation.base, presentation.require
SCOPE = 'actual_client_startup_guest'
SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
EXE_SHA = '81885ffa8838ef8759c3526fa1cc0bd44f9108e92698b29054256dd0eb97a0ca'
DATA_COUNT, DATA_BYTES = 173011, 2977730517
REQUIRED = (presentation.REQUIRED - {'presentation-probe.exe'}) | {
    'client_startup_diagnostic.py', 'client-launcher.exe', 'client-runtime.zip'}
PRIVATE_CACHE_ROOTS = ('bin', 'server/bin', 'geobin')
LAUNCH_MARKER = 'COH_CLIENT_LAUNCH_V1 '
CONSOLE_MARKER = 'COH_CLIENT_CONSOLE_V1 '
MAX_IMAGE_BYTES = 1024*768*4


def read_json(path, limit=1024*1024):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= limit,
            'Missing, linked or oversized JSON input: ' + path.name)
    return json.loads(path.read_text(encoding='utf-8-sig'))


def validate_args(args):
    require(re.fullmatch(r'[0-9a-f]{32}', args.session_id) is not None, 'Invalid session identity')
    require(type(args.startup_timeout_seconds) is int and 60 <= args.startup_timeout_seconds <= 900,
            'Startup bound must be 60 to 900 seconds')
    require(type(args.observation_seconds) is int and 5 <= args.observation_seconds <= 60,
            'Observation bound must be 5 to 60 seconds')
    require(type(args.timeout_seconds) is int and 180 <= args.timeout_seconds <= 1800,
            'Overall bound must be 180 to 1800 seconds')
    for path in (args.state, args.assets, args.socket_dir, args.game_data):
        require(path.is_absolute() and '..' not in path.parts and path != Path('/') and not path.is_symlink(),
                'Expected absolute unlinked private paths')


def verify_assets(assets):
    manifest = read_json(assets / 'client-manifest.json')
    require(type(manifest.get('format')) is int and manifest['format'] == 1 and manifest.get('scope') == SCOPE,
            'Client manifest scope differs')
    files = manifest.get('files')
    require(isinstance(files, dict) and REQUIRED <= set(files) and len(files) <= 64,
            'Client payload inventory differs')
    hashes = {}
    for name, expected in files.items():
        require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', name)
                and name not in ('.', '..') and isinstance(expected, dict), 'Unsafe client inventory entry')
        path = assets / name
        require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 128*1024*1024,
                'Missing, linked or oversized client input: ' + name)
        digest = expected.get('sha256')
        size = expected.get('bytes', expected.get('size'))
        require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest)
                and type(size) is int and path.stat().st_size == size and base.file_hash(path) == digest,
                'Client input pin differs: ' + name)
        hashes[name] = digest
    for name in ('runtime-probe.exe', 'probe.dll', 'client-launcher.exe'):
        base.verify_pe32(assets / name)
    return hashes


def import_identity(data):
    require(data.is_dir() and not data.is_symlink(), 'Missing private imported data')
    receipt = data.parent / 'complete.properties'
    require(receipt.is_file() and not receipt.is_symlink() and receipt.stat().st_size <= 4096,
            'Missing completed import receipt')
    raw = receipt.read_bytes()
    values = {}
    for line in raw.decode('ascii').splitlines():
        key, separator, value = line.partition('=')
        require(separator and key not in values, 'Invalid import receipt')
        values[key] = value
    require(set(values) == {'generation', 'contract.sha256', 'count', 'bytes'}
            and re.fullmatch(r'generation-[0-9a-f]{32}', values['generation'])
            and re.fullmatch(r'[0-9a-f]{64}', values['contract.sha256'])
            and values['count'] == str(DATA_COUNT) and values['bytes'] == str(DATA_BYTES),
            'Imported generation receipt differs from the accepted data contract')
    return {'generation': values['generation'], 'receipt_sha256': hashlib.sha256(raw).hexdigest(),
            'contract_sha256': values['contract.sha256'], 'file_count': DATA_COUNT, 'total_bytes': DATA_BYTES}


def archive_manifest(archive):
    entries = archive.infolist()
    require(len(entries) == 22 and len({e.filename.casefold() for e in entries}) == 22,
            'Unexpected client package entry count or duplicate')
    for entry in entries:
        mode = entry.external_attr >> 16
        require(re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', entry.filename) and entry.filename not in ('.', '..')
                and not entry.is_dir() and not entry.flag_bits & 1 and stat.S_IFMT(mode) in (0, stat.S_IFREG)
                and 0 < entry.file_size <= 16*1024*1024, 'Unsafe client archive entry')
    require(sum(e.file_size for e in entries) <= 64*1024*1024, 'Client package exceeded bound')
    require(archive.getinfo('client-package.json').file_size <= 1024*1024, 'Oversized client package receipt')
    manifest = json.loads(archive.read('client-package.json').decode('utf-8-sig'))
    require(manifest.get('format') == 1 and manifest.get('role') == 'actual_graphical_client'
            and manifest.get('source_commit') == SOURCE and manifest.get('data_commit') == DATA
            and manifest.get('reference_run_id') == 36088012664, 'Client package provenance differs')
    files = manifest.get('files')
    require(isinstance(files, dict) and len(files) == 21 and set(files) | {'client-package.json'} == {e.filename for e in entries}
            and set(name for name in files if name.lower().endswith('.exe')) == {'CityOfHeroes.exe'}
            and all(name == 'CityOfHeroes.exe' or name.lower().endswith('.dll') for name in files),
            'Client package must contain only the pinned client and its DLL closure')
    require(files['CityOfHeroes.exe'].get('sha256') == EXE_SHA
            and files['CityOfHeroes.exe'].get('size') == 9432576, 'Unqualified graphical executable')
    for name, expected in files.items():
        require(isinstance(expected, dict) and re.fullmatch(r'[0-9a-f]{64}', expected.get('sha256', ''))
                and type(expected.get('size')) is int and archive.getinfo(name).file_size == expected['size']
                and expected.get('pe_machine') == 0x14c, 'Invalid client package inventory')
    return manifest


def private_cache(relative):
    value = relative.as_posix().casefold()
    return any(value == root or value.startswith(root + '/') for root in PRIVATE_CACHE_ROOTS)


def prepare_worktree(root, data, assets, identity, context):
    """Protect imported leaves, create one reusable thin tree, isolate all caches."""
    package_sha = base.file_hash(assets / 'client-runtime.zip')
    key = hashlib.sha256((identity['receipt_sha256'] + package_sha).encode()).hexdigest()[:24]
    destination = root / ('client-work-' + key)
    marker = destination / 'client-work.json'
    expected_identity = {'format': 1, 'source_data': str(data), 'import': identity,
                         'package_sha256': package_sha}
    if destination.exists() or destination.is_symlink():
        require(destination.is_dir() and not destination.is_symlink(), 'Linked client worktree')
        saved = read_json(marker)
        require(all(saved.get(k) == v for k, v in expected_identity.items()), 'Client worktree identity differs')
        require((destination / 'tools').is_dir() and not (destination / 'tools').is_symlink(),
                'Missing private loose-data discovery marker')
        require((destination / 'data').is_dir() and not (destination / 'data').is_symlink(), 'Invalid private client data')
        for name in PRIVATE_CACHE_ROOTS:
            current = destination / 'data'
            for part in Path(name).parts:
                current /= part
                require(not current.is_symlink(), 'Linked writable cache refused')
        with zipfile.ZipFile(assets / 'client-runtime.zip') as archive:
            package = archive_manifest(archive)
        for name, pin in package['files'].items():
            target = destination / name
            require(target.is_file() and not target.is_symlink() and target.stat().st_size == pin['size']
                    and base.file_hash(target) == pin['sha256'], 'Cached client binary differs: ' + name)
        return destination, dict(saved, reused=True)
    staging = root / ('client-staging-' + base.secrets.token_hex(12))
    staging.mkdir(mode=0o700)
    count = total = linked = copied = 0
    try:
        (staging / 'data').mkdir(mode=0o700)
        (staging / 'tools').mkdir(mode=0o700)  # Pinned file.c addAppropriateDataDirs requires both.
        pending = [(data, staging / 'data')]
        progress = 0
        while pending:
            context.check()
            source_dir, target_dir = pending.pop()
            with os.scandir(source_dir) as entries:
                for entry in entries:
                    context.check()
                    require(not entry.is_symlink(), 'Linked immutable input refused')
                    source = Path(entry.path)
                    relative = source.relative_to(data)
                    target = target_dir / entry.name
                    info = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode):
                        target.mkdir(mode=0o700)
                        pending.append((source, target))
                    else:
                        require(stat.S_ISREG(info.st_mode), 'Nonregular immutable input refused')
                        count += 1; total += info.st_size
                        require(count <= DATA_COUNT and total <= DATA_BYTES, 'Imported content exceeds accepted bounds')
                        os.chmod(source, 0o444, follow_symlinks=False)
                        if private_cache(relative) or source.suffix.casefold() == '.dbidmap':
                            shutil.copyfile(source, target, follow_symlinks=False)
                            os.chmod(target, 0o600)
                            copied += 1
                        else:
                            target.symlink_to(source)
                            linked += 1
                    if time.monotonic() >= progress:
                        context.event('stage', status='running', message='Preparing reusable client data links', files=count)
                        progress = time.monotonic() + 5
        require((count, total) == (DATA_COUNT, DATA_BYTES), 'Imported data size/count differs from completed receipt')
        for name in PRIVATE_CACHE_ROOTS:
            (staging / 'data' / name).mkdir(parents=True, exist_ok=True, mode=0o700)
        with zipfile.ZipFile(assets / 'client-runtime.zip') as archive:
            package = archive_manifest(archive)
            for name, pin in package['files'].items():
                context.check()
                target = staging / name
                with archive.open(name) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output, 1024*1024)
                require(base.file_hash(target) == pin['sha256'], 'Client archive hash differs: ' + name)
                base.verify_pe32(target)
                os.chmod(target, 0o400)
        saved = dict(expected_identity, linked_files=linked, copied_writable_files=copied,
                     input_files=count, input_bytes=total, imported_inputs_readonly=True,
                     writable_cache_roots=list(PRIVATE_CACHE_ROOTS))
        base.private_write(staging / 'client-work.json', json.dumps(saved, indent=2) + '\n')
        os.rename(staging, destination)
        return destination, dict(saved, reused=False)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


class XWindowAttributes(C.Structure):
    _fields_ = [('x', C.c_int), ('y', C.c_int), ('width', C.c_int), ('height', C.c_int),
        ('border_width', C.c_int), ('depth', C.c_int), ('visual', C.c_void_p), ('root', C.c_ulong),
        ('win_class', C.c_int), ('bit_gravity', C.c_int), ('win_gravity', C.c_int), ('backing_store', C.c_int),
        ('backing_planes', C.c_ulong), ('backing_pixel', C.c_ulong), ('save_under', C.c_int),
        ('colormap', C.c_ulong), ('map_installed', C.c_int), ('map_state', C.c_int),
        ('all_event_masks', C.c_long), ('your_event_mask', C.c_long), ('do_not_propagate_mask', C.c_long),
        ('override_redirect', C.c_int), ('screen', C.c_void_p)]


class XImage(C.Structure):
    _fields_ = [('width', C.c_int), ('height', C.c_int), ('xoffset', C.c_int), ('format', C.c_int),
        ('data', C.c_void_p), ('byte_order', C.c_int), ('bitmap_unit', C.c_int), ('bitmap_bit_order', C.c_int),
        ('bitmap_pad', C.c_int), ('depth', C.c_int), ('bytes_per_line', C.c_int), ('bits_per_pixel', C.c_int),
        ('red_mask', C.c_ulong), ('green_mask', C.c_ulong), ('blue_mask', C.c_ulong)]


def ppm_from_ximage(image):
    require(0 < image.width <= 1024 and 0 < image.height <= 768 and image.bits_per_pixel in (24, 32)
            and image.byte_order in (0, 1) and 0 < image.bytes_per_line <= 4096
            and image.width*(image.bits_per_pixel//8) <= image.bytes_per_line
            and image.bytes_per_line*image.height <= MAX_IMAGE_BYTES and image.data,
            'Unsupported or oversized X image')
    require((image.red_mask, image.green_mask, image.blue_mask) == (0xff0000, 0xff00, 0xff),
            'Unsupported X color masks')
    raw = C.string_at(image.data, image.bytes_per_line*image.height)
    output = bytearray()
    stride = image.bits_per_pixel//8
    order = 'little' if image.byte_order == 0 else 'big'
    colors = set()
    for row in range(image.height):
        for column in range(image.width):
            offset = row*image.bytes_per_line + column*stride
            pixel = int.from_bytes(raw[offset:offset+stride], order)
            rgb = ((pixel >> 16)&255, (pixel >> 8)&255, pixel&255)
            output.extend(rgb)
            if len(colors) < 256: colors.add(rgb)
    return f'P6\n{image.width} {image.height}\n255\n'.encode() + output, len(colors)


class XObserver:
    def __init__(self, display):
        self.lib = C.CDLL('libX11.so.6')
        lib = self.lib
        lib.XOpenDisplay.argtypes = [C.c_char_p]; lib.XOpenDisplay.restype = C.c_void_p
        lib.XDefaultRootWindow.argtypes = [C.c_void_p]; lib.XDefaultRootWindow.restype = C.c_ulong
        lib.XCloseDisplay.argtypes = [C.c_void_p]
        lib.XFree.argtypes = [C.c_void_p]
        lib.XSync.argtypes = [C.c_void_p, C.c_int]
        lib.XQueryTree.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_ulong), C.POINTER(C.c_ulong),
                                  C.POINTER(C.POINTER(C.c_ulong)), C.POINTER(C.c_uint)]
        lib.XFetchName.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(C.c_void_p)]
        lib.XGetWindowAttributes.argtypes = [C.c_void_p, C.c_ulong, C.POINTER(XWindowAttributes)]
        lib.XGetImage.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_int, C.c_uint, C.c_uint, C.c_ulong, C.c_int]
        lib.XGetImage.restype = C.POINTER(XImage)
        lib.XDestroyImage.argtypes = [C.POINTER(XImage)]
        self.error_count = 0
        handler = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_void_p)
        def on_error(_display, _event):
            self.error_count += 1
            return 0
        self.error_callback = handler(on_error)
        lib.XSetErrorHandler.argtypes = [handler]
        lib.XSetErrorHandler.restype = C.c_void_p
        lib.XSetErrorHandler(self.error_callback)
        self.display = lib.XOpenDisplay(display.encode())
        require(self.display, 'Cannot observe owned X display')
        self.root = lib.XDefaultRootWindow(self.display)

    def windows(self):
        records, pending, seen = [], [self.root], set()
        while pending:
            window = pending.pop()
            if window in seen: continue
            seen.add(window)
            require(len(seen) <= 512, 'Owned X window count exceeded bound')
            attributes = XWindowAttributes()
            name_ptr = C.c_void_p()
            if self.lib.XGetWindowAttributes(self.display, window, C.byref(attributes)):
                name = ''
                if self.lib.XFetchName(self.display, window, C.byref(name_ptr)) and name_ptr:
                    try:
                        name = C.string_at(name_ptr).decode('utf-8', 'replace')[:256]
                    finally:
                        self.lib.XFree(name_ptr)
                if name:
                    records.append({'window_id': int(window), 'title': name, 'width': attributes.width,
                        'height': attributes.height, 'mapped': attributes.map_state == 2})
            root, parent, count, children = C.c_ulong(), C.c_ulong(), C.c_uint(), C.POINTER(C.c_ulong)()
            if self.lib.XQueryTree(self.display, window, C.byref(root), C.byref(parent), C.byref(children), C.byref(count)):
                try:
                    require(count.value <= 512, 'Owned X child count exceeded bound')
                    pending.extend(int(children[index]) for index in range(count.value))
                finally:
                    if children: self.lib.XFree(children)
        self.lib.XSync(self.display, False)
        return records

    def capture(self, path):
        image = self.lib.XGetImage(self.display, self.root, 0, 0, 800, 600, C.c_ulong(-1).value, 2)
        require(bool(image), 'Cannot capture owned X desktop')
        try:
            data, colors = ppm_from_ximage(image.contents)
        finally:
            self.lib.XDestroyImage(image)
        require(not path.exists() and not path.is_symlink(), 'Capture destination already exists')
        with path.open('xb') as output:
            output.write(data)
        return {'path': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                'width': 800, 'height': 600, 'distinct_colors_capped': colors,
                'kind': 'owned_x_desktop', 'menu_visual_validated': False}

    def close(self):
        if self.display:
            self.lib.XCloseDisplay(self.display)
            self.display = None


def parse_launch(output, session):
    values = [json.loads(line[len(LAUNCH_MARKER):]) for line in output.splitlines() if line.startswith(LAUNCH_MARKER)]
    require(len(values) <= 1, 'Duplicate client launch identity')
    if not values: return None
    value = values[0]
    require(isinstance(value, dict) and set(value) == {'session_id', 'pid'} and value['session_id'] == session
            and type(value['pid']) is int and 0 < value['pid'] < 2**32, 'Invalid client launch identity')
    return value


def startup_evidence(output, registry_output, windows, launch):
    main_loop = bool(re.search(r'(?mi)^\s*GameProgress\s+REG_SZ\s+game_mainLoop\s*$', registry_output))
    title = 'City of Heroes : PID: ' + str(launch['pid']) if launch else None
    actual = [row for row in windows if row['title'] == title and row['mapped']
              and row['width'] >= 320 and row['height'] >= 240]
    gl = {}
    for field, label in [('vendor', 'Vendor'), ('renderer', 'Renderer'), ('gl_version', 'Version')]:
        values = re.findall(r'OpenGL ' + label + r': ([^\r\n]{1,512})', output)
        if values: gl[field] = values[-1].strip()
    renderer = gl.get('renderer', '')
    gl['renderer_classification'] = ('software' if any(value in renderer.lower()
        for value in ('llvmpipe', 'softpipe', 'software rasterizer', 'swrast')) else 'unclassified')
    return {'graphics_observation': gl, 'renderer_initialized': 'Renderer initialization complete' in output,
        'all_data_loaded': 'Loaded all data!' in output, 'client_main_loop_reached': main_loop,
        'client_window_observed': bool(actual), 'client_windows': actual,
        'startup_observed': bool(main_loop and actual), 'menu_visual_validated': False}


def console_identity(output, launch):
    values = [json.loads(line[len(CONSOLE_MARKER):]) for line in output.splitlines()
              if line.startswith(CONSOLE_MARKER)]
    require(len(values) <= 1, 'Duplicate client console identity')
    if not values: return None
    value = values[0]
    require(launch is not None and isinstance(value, dict)
            and set(value) == {'session_id', 'pid', 'attached'}
            and value['session_id'] == launch['session_id']
            and type(value['pid']) is int and value['pid'] == launch['pid']
            and value['attached'] is True, 'Client console identity does not match owned launch')
    return value


def cache_inventory(work, deadline, entry_limit=4096):
    """Inspect only private cache metadata, never walk or copy the loose inputs."""
    result = {'format': 1, 'sampled_utc': base.utc(), 'entry_limit': entry_limit,
              'files': [], 'roots': list(PRIVATE_CACHE_ROOTS), 'truncated': False}
    pending = [work / 'data' / name for name in PRIVATE_CACHE_ROOTS]
    examined = 0
    while pending:
        directory = pending.pop()
        require(not directory.is_symlink(), 'Linked private cache directory refused')
        if not directory.exists(): continue
        with os.scandir(directory) as entries:
            for entry in entries:
                if examined >= entry_limit or time.monotonic() >= deadline:
                    result['truncated'] = True
                    return result
                examined += 1
                require(not entry.is_symlink(), 'Linked private cache entry refused')
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(Path(entry.path))
                elif stat.S_ISREG(info.st_mode):
                    result['files'].append({'path': Path(entry.path).relative_to(work).as_posix(),
                        'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns})
    return result


class ClientStartupDiagnostic(presentation.PresentationDiagnostic):
    def __init__(self, args, context):
        super().__init__(args, context)
        self.observer = None
        self.client = None
        self.work = None
        self.capture_dir = base.private_dir(args.state / ('client-evidence-' + args.session_id))
        self.captures = []
        self.startup_complete = False

    def initialize(self):
        self.ctx.stage('client_inputs')
        require(platform.machine().lower() in ('aarch64', 'arm64'), 'Guest must execute on ARM64')
        require(os.geteuid() == 1000, 'Guest requires PRoot -i 1000:1000')
        self.ctx.report['asset_sha256'] = verify_assets(self.args.assets)
        base.arm64_elf(self.args.wine); base.arm64_elf(self.args.wineserver)
        require(self.args.socket_dir.is_dir() and not self.args.socket_dir.is_symlink()
                and stat.S_IMODE(self.args.socket_dir.stat().st_mode) == 0o700, 'Invalid private presentation socket directory')
        require(not self.presentation_socket.exists() and not self.presentation_socket.is_symlink(), 'Socket already exists')
        identity = import_identity(self.args.game_data)
        self.ctx.report['import_identity'] = identity
        self.ctx.passed(machine=platform.machine(), guest_uid=os.geteuid(), postgres_started=False,
                        source_commit=SOURCE, data_commit=DATA, client_executable_sha256=EXE_SHA)
        self.ctx.stage('client_private_data')
        self.work, receipt = prepare_worktree(self.root, self.args.game_data, self.args.assets, identity, self.ctx)
        self.ctx.report['client_worktree'] = receipt
        self.ctx.passed(**receipt)

    def capture(self, label):
        if self.observer is None or len(self.captures) >= 3: return None
        record = self.observer.capture(self.capture_dir / (label + '.ppm'))
        record.update(session_id=self.args.session_id, captured_utc=base.utc())
        self.captures.append(record)
        self.ctx.report['screenshots'] = self.captures
        return record

    def execute(self):
        self.initialize()
        self.start_wine()
        self.ctx.stage('win32_runtime_dll')
        result = self.ctx.run('runtime-probe', [self.args.wine,
            base.windows_path(self.args.assets / 'runtime-probe.exe')], timeout=60, env=self.wine_env)
        self.ctx.passed(**base.validate_runtime_probe(result['output']))
        self.mark_wine_ready()
        # Consume any previous registry progress before the new client starts.
        self.ctx.run('client-progress-reset', [self.args.wine, 'reg', 'delete',
            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/f', '/reg:32'],
            timeout=8, env=self.wine_env, check=False)
        reset_query = self.ctx.run('client-progress-empty', [self.args.wine, 'reg', 'query',
            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/reg:32'],
            timeout=8, env=self.wine_env, check=False)
        require(not re.search(r'(?mi)^\s*GameProgress\s+REG_SZ\s+', reset_query['output']),
                'Prior client progress registry value could not be cleared')
        previous_logs = self.work / 'logs'
        require(not previous_logs.is_symlink(), 'Linked client logs refused')
        if previous_logs.exists():
            require(previous_logs.is_dir(), 'Client logs path must be a directory')
            shutil.rmtree(previous_logs)
        self.ctx.stage('actual_client_startup')
        self.observer = XObserver(self.wine_env['DISPLAY'])
        self.capture('before-client')
        self.ctx.event('client_display_ready', session_id=self.args.session_id, width=800, height=600,
                       socket_path=str(self.presentation_socket), startup_timeout_seconds=self.args.startup_timeout_seconds)
        # The GUI client allocates and redirects to its own console. The helper
        # attaches to that exact child and copies its screen buffer to our pipe.
        command = [self.args.wine, base.windows_path(self.args.assets / 'client-launcher.exe'), self.args.session_id,
                   base.windows_path(self.work / 'CityOfHeroes.exe'), base.windows_path(self.work)]
        previous = Path.cwd()
        try:
            os.chdir(self.work)
            self.client = self.ctx.start('actual-coh-client', command, env=self.wine_env)
        finally:
            os.chdir(previous)
        started = time.monotonic()
        deadline = started + self.args.startup_timeout_seconds
        next_registry = next_progress = 0
        registry_output = ''
        ready_at = None
        try:
            while True:
                self.ctx.check()
                require(self.client.process.poll() is None, 'Actual CoH client exited during startup or observation')
                require(self.xserver.process.poll() is None, 'Owned presentation display exited')
                now = time.monotonic()
                require(now < deadline, 'Actual CoH startup exceeded its bounded deadline')
                output = self.client.text()
                launch = parse_launch(output, self.args.session_id)
                if launch:
                    self.ctx.report.update(client_process_started=True, client_launch=launch)
                console = console_identity(output, launch)
                self.ctx.report['client_console_observation'] = console
                require('COH_CLIENT_CONSOLE_TRUNCATED_V1' not in output, 'Actual client console exceeded observation budget')
                require(console is not None or now - started < 120,
                        'Could not attach to actual client console within 120 seconds')
                if now >= next_progress:
                    windows = self.observer.windows()
                    self.ctx.report['observed_windows'] = windows
                    if now >= next_registry:
                        registry = self.ctx.run('client-progress-registry', [self.args.wine, 'reg', 'query',
                            r'HKCU\Software\Cryptic\CoH', '/v', 'GameProgress', '/reg:32'],
                            timeout=8, env=self.wine_env, check=False)
                        registry_output = registry['output']
                        next_registry = time.monotonic() + 20
                    evidence = startup_evidence(output, registry_output, windows, launch)
                    self.ctx.report.update(evidence)
                    if evidence['startup_observed'] and evidence['renderer_initialized'] and evidence['all_data_loaded']:
                        if ready_at is None:
                            ready_at = time.monotonic()
                            deadline = max(deadline, ready_at + self.args.observation_seconds + 10)
                            shot = self.capture('client-startup')
                            require(shot and shot['distinct_colors_capped'] >= 8, 'Actual client desktop capture is blank')
                            self.ctx.event('client_startup_observed', session_id=self.args.session_id,
                                           client_pid=launch['pid'], menu_visual_validated=False)
                        elif time.monotonic() - ready_at >= self.args.observation_seconds:
                            self.ctx.report.update(observation_seconds=round(time.monotonic()-ready_at, 3),
                                                   startup_elapsed_seconds=round(ready_at-started, 3))
                            shot = self.capture('client-observed')
                            require(shot and shot['distinct_colors_capped'] >= 8, 'Observed client desktop became blank')
                            self.ctx.passed(**evidence, bounded_live_observation=True)
                            self.startup_complete = True
                            return
                    else:
                        require(ready_at is None, 'Actual CoH window or startup evidence disappeared during observation')
                    self.ctx.event('stage', status='running', message='Starting City of Heroes' if ready_at is None
                                   else 'Observing actual City of Heroes window', elapsed_seconds=int(now-started),
                                   renderer_initialized=evidence['renderer_initialized'],
                                   client_main_loop_reached=evidence['client_main_loop_reached'])
                    next_progress = time.monotonic() + 5
                time.sleep(.1)
        finally:
            self.save_evidence()

    def save_evidence(self):
        if self.client:
            data = self.client.text().encode('utf-8')
            target = self.capture_dir / 'client-console.log'
            if not target.exists(): target.write_bytes(data)
            self.ctx.report['client_console'] = {'path': target.name, 'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest()}
        if self.observer and len(self.captures) < 3:
            try: self.capture('client-final')
            except Exception as exc: self.ctx.report.setdefault('observation_failures', []).append(str(exc))
        if self.work:
            try:
                inventory = cache_inventory(self.work, time.monotonic() + 3)
                target = self.capture_dir / 'private-cache-inventory.json'
                target.write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
                self.ctx.report['private_cache_inventory'] = {'path': target.name,
                    'files': len(inventory['files']), 'truncated': inventory['truncated']}
            except Exception as exc:
                self.ctx.report.setdefault('observation_failures', []).append('Cache inventory: ' + str(exc))
            if not self.startup_complete and self.wine_started:
                try:
                    snapshot = game_hang_evidence.capture_processes(self, time.monotonic() + 6)
                    target = self.capture_dir / 'owned-processes.json'
                    payload = json.dumps(snapshot, indent=2) + '\n'
                    require(len(payload.encode()) <= 1024*1024, 'Owned-process snapshot exceeded bound')
                    target.write_text(payload, encoding='utf-8')
                    self.ctx.report['owned_process_snapshot'] = {'path': target.name,
                        'owned_process_count': snapshot.get('owned_process_count')}
                except Exception as exc:
                    self.ctx.report.setdefault('observation_failures', []).append('Owned processes: ' + str(exc))
            logs = self.work / 'logs'
            if logs.is_dir() and not logs.is_symlink():
                output_dir = self.capture_dir / 'logs'
                count, total = 0, 0
                for path in logs.rglob('*'):
                    require(not path.is_symlink(), 'Linked client log refused')
                    if not path.is_file(): continue
                    count += 1
                    require(count <= 64, 'Client log count exceeded bound')
                    # Tail bounds preserve runtime failure clues without copying
                    # stale or unbounded diagnostics into the support archive.
                    with path.open('rb') as handle:
                        handle.seek(max(0, path.stat().st_size - 256*1024))
                        payload = handle.read(256*1024)
                    total += len(payload)
                    require(total <= 4*1024*1024, 'Client logs exceeded bound')
                    target = output_dir / path.relative_to(logs)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(payload)

    def cleanup(self):
        if self.observer:
            self.observer.close()
            self.observer = None
        return super().cleanup()


def persist_report(args, context, capture_dir):
    document = json.dumps(base.redacted_value(context.report, context.secrets), indent=2) + '\n'
    require(len(document.encode()) <= 2*1024*1024, 'Client report exceeded bound')
    base.private_write(args.state / 'latest-report.json', document)
    target = args.state / 'report.zip'
    require(not target.is_symlink(), 'Linked support archive refused')
    temporary = target.with_name('report.zip.tmp-' + base.secrets.token_hex(8))
    try:
        with temporary.open('xb') as handle:
            os.chmod(temporary, 0o600)
            with zipfile.ZipFile(handle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('latest-report.json', document)
                total = count = 0
                if capture_dir is not None:
                    for path in sorted(capture_dir.rglob('*')):
                        require(not path.is_symlink(), 'Linked capture refused')
                        if not path.is_file(): continue
                        size = path.stat().st_size
                        count += 1; total += size
                        require(count <= 70 and total <= 12*1024*1024, 'Capture export exceeded bound')
                        archive.write(path, 'client-evidence/' + path.relative_to(capture_dir).as_posix())
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in [('state', '/state'), ('assets', '/opt/coh'), ('pg-bin', '/opt/coh/pgsql/bin'),
                          ('wine', '/opt/wine/bin/wine'), ('wineserver', '/opt/wine/bin/wineserver'),
                          ('xserver', '/usr/bin/Xtigervnc'), ('socket-dir', '/presentation-socket'),
                          ('game-data', '/game-import/data')]:
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--execution-platform', choices=('android', 'host'), default='host')
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--startup-timeout-seconds', type=int, default=900)
    parser.add_argument('--observation-seconds', type=int, default=30)
    parser.add_argument('--timeout-seconds', type=int, default=1800)
    args = parser.parse_args(argv)
    os.umask(0o077)
    context = base.Context(args.state, args.timeout_seconds)
    context.report.update(scope=SCOPE, diagnostic_mode='actual_client_startup', session_id=args.session_id,
        execution_platform_requested=args.execution_platform, postgres_started=False,
        server_started=False, game_validated=False, menu_visual_validated=False,
        android_surface_validated=False, hardware_acceleration_validated=False,
        client_process_started=False, startup_observed=False)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
    diagnostic = None
    validated = False
    try:
        validate_args(args); validated = True
        context.check()
        diagnostic = ClientStartupDiagnostic(args, context)
        diagnostic.execute()
        context.report['status'] = 'passed'
    except base.Cancelled as exc:
        context.report.update(status='cancelled', failures=[str(exc)])
    except Exception as exc:
        context.report.update(status='failed', failures=[str(exc)])
    finally:
        if diagnostic is not None:
            try: failures = diagnostic.cleanup()
            except Exception as exc: failures = ['Owned cleanup failed: ' + str(exc)]
            context.report['failures'].extend(failures)
        closed = all(c.process.poll() is not None and not c.reader.is_alive() and not c.writer.is_alive()
                     for c in context.children)
        context.report.update(finished_utc=base.utc(), cleanup_complete=closed,
            cleanup_execution={'diagnostic_initialized': diagnostic is not None,
                'wine_started': bool(diagnostic is not None and diagnostic.wine_started),
                'owned_child_count': len(context.children)},
            cleanup=diagnostic.cleanup_status if diagnostic else {'postgres_graceful': True,
                'wine_prefix_stopped': False, 'owned_processes_reaped': closed})
        context.report['passed'] = (context.report['status'] == 'passed' and not context.report['failures']
                                    and closed and all(context.report['cleanup'].values()))
        if context.report['status'] == 'passed' and not context.report['passed']:
            context.report['status'] = 'failed'
            if not context.report['failures']: context.report['failures'].append('Required cleanup was not proved')
        if validated:
            try:
                persist_report(args, context, diagnostic.capture_dir if diagnostic else None)
            except Exception as exc:
                context.report.update(status='failed', passed=False)
                context.report['failures'].append('Cannot persist client report: ' + str(exc))
                try: base.private_write(args.state / 'latest-report.json', json.dumps(context.report, indent=2) + '\n')
                except Exception: pass
        context.event('result', status=context.report['status'], passed=context.report['passed'],
                      report='/state/latest-report.json', failures=context.report['failures'])
    return 0 if context.report['passed'] else 2 if context.report['status'] == 'cancelled' else 1


if __name__ == '__main__':
    sys.exit(main())
