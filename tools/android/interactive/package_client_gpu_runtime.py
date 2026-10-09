#!/usr/bin/env python3
"""Source-bound KGSL Turnip payload; retain the exact accepted GL/Wine rootfs.

The base ABI snapshot comes from the fully authenticated existing root archive.
Every new strong dynamic symbol/version must resolve against that exact base;
private replacements for previously loaded core SONAMEs are not permitted.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools')]
from package_reference_runtime import pe_info

ROLE = 'client_hardware_renderer'
ARCHIVE = 'hardware-renderer.zip'
MANIFEST = 'client-gpu-runtime-manifest.json'
RECEIPT = 'client-gpu-runtime-build-input.json'
INNER_MANIFEST = 'hardware-renderer-manifest.json'
INNER_RECEIPT = 'hardware-renderer-build-input.json'
DRIVER = 'libvulkan_freedreno.so'
VULKAN_PROBE = 'coh-vulkan-gpu-probe'
PE32_PROBE = 'coh-gpu-probe.exe'
PE32_HELPER_SOURCE = 'coh-gpu-probe-helper-checks.c'
PE32_HELPER_EXE = 'coh-gpu-probe-helper-checks.exe'
NOTICES = 'THIRD_PARTY_NOTICES.md'
MODES = {DRIVER: 0o644, VULKAN_PROBE: 0o755, PE32_PROBE: 0o644,
    INNER_RECEIPT: 0o644, NOTICES: 0o644}
SOURCE_FILES = (
    'tools/android/interactive/package_client_gpu_runtime.py',
    'tools/android/gpu-runtime/Dockerfile', 'tools/android/gpu-runtime/lock.json',
    'tools/android/gpu-runtime/build.py', 'tools/android/gpu-runtime/base-abi.json',
    'android/runtime-lock.json', 'android/native/coh-vulkan-gpu-probe.c',
    'android/native/coh-gpu-probe.c',
    'tools/android/interactive/test_coh_vulkan_gpu_probe.py',
    'tools/android/interactive/test_coh_gpu_probe_native.py',
    'tools/android/interactive/test_client_gpu_runtime_package.py')
BASE_LIBRARIES = (
    'libc.so.6', 'libm.so.6', 'libgcc_s.so.1', 'libstdc++.so.6',
    'ld-linux-aarch64.so.1', 'libpthread.so.0', 'libdl.so.2', 'librt.so.1',
    'libexpat.so.1', 'libzstd.so.1', 'libz.so.1', 'libvulkan.so.1', 'libdrm.so.2',
    'libxcb.so.1', 'libxcb-dri3.so.0', 'libxcb-present.so.0', 'libxcb-randr.so.0',
    'libxcb-sync.so.1', 'libxcb-xfixes.so.0', 'libxcb-shm.so.0', 'libxshmfence.so.1',
    'libX11.so.6', 'libX11-xcb.so.1', 'libXau.so.6', 'libXdmcp.so.6',
    'libbsd.so.0', 'libmd.so.0')
PREREQUISITES = ('usr/lib/aarch64-linux-gnu/dri/zink_dri.so',
    'usr/lib/aarch64-linux-gnu/libGLX_mesa.so.0', 'usr/lib/aarch64-linux-gnu/libvulkan.so.1')
MAX_MEMBER = 64 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_ARCHIVE = 64 * 1024 * 1024
RUN = r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]+'


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def file_pin(path):
    return {'bytes': Path(path).stat().st_size, 'sha256': digest(path)}


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def json_value(data):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, 'Duplicate GPU JSON key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite GPU JSON')))


def read_json(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= MAX_MEMBER,
        'Missing or oversized GPU JSON')
    return json_value(path.read_bytes())


def typed_equal(left, right):
    return encoded(left) == encoded(right)


def lock():
    value = read_json(ROOT / 'tools/android/gpu-runtime/lock.json')
    require(value.get('format') == 1 and value.get('platform') == 'linux-arm64-gnu-bookworm'
        and value.get('mesa', {}).get('version') == '26.0.0'
        and value['mesa'].get('sha256') == '2a44e98e64d5c36cec64633de2d0ec7eff64703ee25b35364ba8fcaa84f33f72'
        and value.get('driver') == 'turnip_kgsl', 'Pinned GPU source lock differs')
    return value


def base_pin():
    base = read_json(ROOT / 'android/runtime-lock.json')['base']
    require(base['bytes'] == 353710639 and base['sha256'] ==
        '08c639c26506dc6fbd15464bec475337087bb23cb7c0c5ace2db5240ee36424f',
        'Accepted base runtime pin differs')
    return {key: base[key] for key in ('url', 'bytes', 'sha256')}


def source_pins():
    return {name: file_pin(ROOT / name) for name in SOURCE_FILES}


def inspect_elf(path):
    data = Path(path).read_bytes()
    require(data[:6] == b'\x7fELF\x02\x01' and len(data) >= 64, 'Expected little-endian ELF64')
    machine = struct.unpack_from('<H', data, 18)[0]
    dynamic = subprocess.check_output(['readelf', '-d', '--wide', str(path)], text=True)
    symbols = subprocess.check_output(['readelf', '--dyn-syms', '--wide', str(path)], text=True)
    needed = re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', dynamic)
    soname = re.findall(r'\(SONAME\).*?\[([^\]]+)\]', dynamic)
    require(len(needed) == len(set(needed)) and len(soname) <= 1,
        'Ambiguous ELF dependencies')
    version_text = subprocess.check_output(['readelf', '--version-info', '--wide', str(path)], text=True)
    version_needs, version_definitions = {}, []
    section, provider = None, None
    for line in version_text.splitlines():
        if line.startswith('Version definition section'):
            section = 'definitions'
        elif line.startswith('Version needs section'):
            section = 'needs'
        elif line.startswith('Version symbols section'):
            section = None
        if section == 'needs':
            match = re.search(r'File: (\S+)\s+Cnt:', line)
            if match:
                provider = match[1]
                require(provider not in version_needs, 'Duplicate ELF version provider')
                version_needs[provider] = []
            match = re.search(r'Name: (\S+)\s+Flags:', line)
            if match:
                require(provider is not None, 'ELF version lacks a provider')
                version_needs[provider].append(match[1])
        elif section == 'definitions':
            match = re.search(r'Name: (\S+)', line)
            if match:
                version_definitions.append(match[1])
    required, exported, default = [], [], []
    for line in symbols.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].endswith(':') or fields[4] not in ('GLOBAL', 'WEAK', 'GNU_UNIQUE'):
            continue
        name = fields[7]
        if not name or name == '0':
            continue
        if fields[6] == 'UND':
            if fields[4] != 'WEAK':
                required.append(name)
        elif fields[5] in ('DEFAULT', 'PROTECTED'):
            exported.append(name.replace('@@', '@'))
            if '@' not in name or '@@' in name:
                default.append(name.split('@', 1)[0])
    require(not re.search(r'\((?:RPATH|RUNPATH)\)', dynamic), 'Unreviewed ELF library search path')
    return {'machine': machine, 'class': 64, 'little_endian': True,
        'needed': sorted(needed), 'soname': soname[0] if soname else None,
        'required_symbols': sorted(set(required)),
        'exported_symbols': sorted(set(exported)), 'default_symbols': sorted(set(default)),
        'version_needs': {name: sorted(set(versions)) for name, versions in sorted(version_needs.items())},
        'version_definitions': sorted(set(version_definitions))}


def _member(archive, members, name, read_data=True):
    for _ in range(16):
        require(name in members, 'Required base library is missing: ' + name)
        member = members[name]
        if member.isreg():
            require(0 < member.size <= 64 * 1024 * 1024, 'Oversized base library')
            return member, archive.extractfile(member).read() if read_data else b''
        require(member.issym() or member.islnk(), 'Base prerequisite is not a file/link')
        target = member.linkname
        name = posixpath.normpath(target if member.islnk() or target.startswith('/')
            else posixpath.join(posixpath.dirname(name), target)).lstrip('/')
        require(not name.startswith('../') and name != '..' and '\\' not in name,
            'Escaping base library link')
        # The pinned Bookworm archive uses merged /usr paths.
        if name not in members and name.startswith('lib/'):
            name = 'usr/' + name
    raise ValueError('Cyclic base prerequisite link')


def base_snapshot(path):
    require(file_pin(path) == {k: base_pin()[k] for k in ('bytes', 'sha256')},
        'Actual accepted base archive differs')
    result = {'format': 1, 'base_archive': base_pin(), 'libraries': {}, 'prerequisites': {}}
    with tempfile.TemporaryDirectory(prefix='coh-base-abi-') as temporary, tarfile.open(path, 'r:gz') as archive:
        entries = archive.getmembers()
        require(len(entries) < 100000 and len({m.name for m in entries}) == len(entries),
            'Duplicate or excessive base archive inventory')
        members = {m.name.lstrip('./'): m for m in entries}
        targets = {name: _member(archive, members, name, read_data=False)[0]
            for name in (*('usr/lib/aarch64-linux-gnu/' + x for x in BASE_LIBRARIES), *PREREQUISITES)}
        # Reading canonical targets in archive order avoids repeated gzip rewind
        # for the shared zink/swrast hardlink and the 27 SONAME aliases.
        data_cache = {member.name: archive.extractfile(member).read()
            for member in sorted({member.name: member for member in targets.values()}.values(),
                key=lambda member: member.offset_data)}
        for name, member in targets.items():
            data = data_cache[member.name]
            local = Path(temporary) / ('lib-' + str(len(result['libraries']) + len(result['prerequisites'])))
            local.write_bytes(data)
            elf = inspect_elf(local)
            require(elf['machine'] == 183, 'Base GPU ABI is not AArch64')
            record = {'path': name, 'resolved_path': member.name, **pin(data), 'elf': elf}
            if name in PREREQUISITES:
                if name.endswith('zink_dri.so'):
                    require('__driDriverGetExtensions_zink' in elf['default_symbols'],
                        'Actual retained base lacks the Zink entrypoint')
                result['prerequisites'][name] = {k: record[k] for k in ('path', 'resolved_path', 'bytes', 'sha256')}
            if PurePosixPath(name).name in BASE_LIBRARIES:
                require(elf['soname'] == PurePosixPath(name).name, 'Base library SONAME differs')
                result['libraries'][elf['soname']] = record
    return result


def abi_snapshot():
    value = read_json(ROOT / 'tools/android/gpu-runtime/base-abi.json')
    require(value.get('format') == 1 and value.get('base_archive') == base_pin()
        and set(value.get('libraries', {})) == set(BASE_LIBRARIES)
        and set(value.get('prerequisites', {})) == set(PREREQUISITES),
        'Exact accepted GPU base ABI snapshot differs')
    for name, record in value['libraries'].items():
        require(record.get('elf', {}).get('machine') == 183 and record['elf'].get('soname') == name,
            'Invalid accepted base ABI identity')
    return value


def dependency_closure(binary, snapshot):
    available = snapshot['libraries']
    selected, pending = {}, list(binary['needed'])
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        require(name in available, 'GPU dependency is absent from the exact base: ' + name)
        record = available[name]
        selected[name] = record
        pending.extend(record['elf']['needed'])
    # Loaded GLX may already have a core SONAME. We require the existing exact
    # library rather than relying on an $ORIGIN replacement with the same name.
    versions = {symbol for record in selected.values() for symbol in record['elf']['exported_symbols']}
    defaults = {symbol for record in selected.values() for symbol in record['elf']['default_symbols']}
    missing = [symbol for symbol in binary['required_symbols']
        if symbol not in (versions if '@' in symbol else defaults)]
    require(not missing, 'GPU dynamic symbol/version is absent from the exact base: ' + repr(missing[:12]))
    for current in (binary, *(record['elf'] for record in selected.values())):
        for provider, versions_needed in current['version_needs'].items():
            require(provider in selected, 'GPU version provider is absent from the exact base: ' + provider)
            absent = set(versions_needed) - set(selected[provider]['elf']['version_definitions'])
            require(not absent, 'GPU dependency version is absent from its declared SONAME: '
                + provider + ': ' + repr(sorted(absent)))
    return {name: {key: record[key] for key in ('path', 'resolved_path', 'bytes', 'sha256')}
        for name, record in sorted(selected.items())}


def binary_checks(directory):
    snapshot = abi_snapshot()
    checks = {}
    for name in (DRIVER, VULKAN_PROBE):
        raw = (Path(directory) / name).read_bytes()
        elf = inspect_elf(Path(directory) / name)
        require(elf['machine'] == 183, 'GPU runtime binary is not ARM64')
        if name == DRIVER:
            require(elf['soname'] == DRIVER, 'KGSL driver SONAME differs')
            require('vk_icdGetInstanceProcAddr' in elf['default_symbols'], 'Vulkan ICD entrypoint missing')
        else:
            require(b'COH_VULKAN_GPU_PROBE_BUILD:production' in raw
                and b'COH_VULKAN_GPU_PROBE_BUILD:host_fixture' not in raw,
                'A host fixture cannot be distributed as the native GPU probe')
        checks[name] = {'elf': elf, 'base_dependency_closure': dependency_closure(elf, snapshot)}
    pe_raw = (Path(directory) / PE32_PROBE).read_bytes()
    require(b'COH_GPU_PROBE_BUILD:production' in pe_raw
        and b'COH_GPU_PROBE_BUILD:host_fixture' not in pe_raw,
        'A host fixture cannot be distributed as the PE32 GPU probe')
    pe = pe_info(pe_raw)
    allowed = {'kernel32.dll', 'gdi32.dll', 'user32.dll', 'opengl32.dll', 'msvcrt.dll', 'ucrtbase.dll',
        'advapi32.dll', 'shell32.dll', 'ole32.dll'}
    require(set(x.lower() for x in pe['imports']) <= allowed and not pe['delay_imports'],
        'GPU PE32 probe imports differ')
    require({'gdi32.dll', 'user32.dll', 'opengl32.dll'} <= {x.lower() for x in pe['imports']},
        'GPU PE32 probe does not import the real WGL APIs')
    checks[PE32_PROBE] = {'pe_machine': 332, **pe}
    return checks


def validate_inner(inner, contents, commit):
    expected_keys = {'format', 'role', 'repository_commit', 'run_url', 'mesa_version',
        'mesa_source_sha256', 'platform', 'driver', 'gpu', 'files',
        'software_default', 'physical_hardware_validated'}
    require(set(inner) == expected_keys and type(inner['format']) is int and inner['format'] == 1
        and inner['role'] == ROLE and inner['repository_commit'] == commit
        and re.fullmatch(RUN, inner['run_url']) and inner['mesa_version'] == lock()['mesa']['version']
        and inner['mesa_source_sha256'] == lock()['mesa']['sha256']
        and inner['platform'] == lock()['platform'] and inner['driver'] == lock()['driver']
        and inner['gpu'] == 'Adreno740' and inner['software_default'] is True
        and inner['physical_hardware_validated'] is False, 'GPU inner manifest differs')
    require(set(inner['files']) == set(MODES), 'GPU inner member pins differ')
    for name, mode in MODES.items():
        require(typed_equal(inner['files'][name], dict(pin(contents[name]), mode=mode)),
            'GPU inner member bytes/mode differ: ' + name)


def archive_contents(path):
    require(0 < Path(path).stat().st_size <= MAX_ARCHIVE, 'GPU archive size differs')
    contents = {}
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(len(entries) == 6 and {entry.filename for entry in entries} == {*MODES, INNER_MANIFEST},
            'GPU archive must have the exact six members')
        require(sum(entry.file_size for entry in entries) <= MAX_TOTAL, 'Excessive GPU archive expansion')
        for entry in entries:
            mode = entry.external_attr >> 16
            expected_mode = MODES.get(entry.filename, 0o644)
            require(entry.create_system == 3 and stat.S_IFMT(mode) == stat.S_IFREG
                and stat.S_IMODE(mode) == expected_mode and not entry.flag_bits & 1
                and 0 < entry.file_size <= MAX_MEMBER, 'Unsafe GPU archive member')
            contents[entry.filename] = archive.read(entry)
    return contents


def validate_container_receipt(receipt):
    sources = receipt.get('source_archives', {})
    wanted = lock()
    require(receipt.get('format') == 1 and receipt.get('architecture') == 'aarch64'
        and receipt.get('platform') == 'linux' and receipt.get('debian_image') == wanted['debian_image']
        and receipt.get('mesa_options') == wanted['mesa_options']
        and receipt.get('probe_compile_args') == wanted['probe_compile_args']
        and receipt.get('native_probe_source_sha256') == digest(ROOT / 'android/native/coh-vulkan-gpu-probe.c')
        and receipt.get('hardware_execution_validated') is False
        and receipt.get('performance_validated') is False
        and type(receipt.get('compiler')) is str and receipt['compiler'].startswith('cc (Debian 12.')
        and type(receipt.get('dpkg_packages')) is list and receipt['dpkg_packages']
        and receipt.get('build_tools', {}).get('meson') == wanted['meson']
        and receipt['build_tools'].get('cmake') == 'cmake version ' + wanted['cmake'],
        'Actual ARM64 GPU build recipe differs')
    require(set(sources) == {'mesa', 'glslang'}, 'GPU upstream source inventory differs')
    for name in sources:
        require(sources[name].get('url') == wanted[name]['url']
            and sources[name].get('sha256') == wanted[name]['sha256']
            and type(sources[name].get('bytes')) is int and sources[name]['bytes'] > 0
            and ('bytes' not in wanted[name] or sources[name]['bytes'] == wanted[name]['bytes']),
            'GPU upstream source bytes differ')


def validate_pe32_checks(checks, commit=None, run_url=None, production=None):
    # The companion module owns and independently validates its fixed Win32
    # guard proof. That proof explicitly does not assert a working host GPU.
    sys.path.insert(0, str(ROOT / 'tools/android/interactive'))
    import test_coh_gpu_probe_native as probe
    validator = getattr(probe, 'validate_windows_checks', None)
    require(callable(validator), 'Actual Win32 probe guard validator is required')
    validator(checks)
    if commit is not None or run_url is not None or production is not None:
        require(checks.get('commit') == commit and checks.get('github_run_url') == run_url
            and typed_equal(checks.get('production_probe'), dict(pin(production),
                pe_machine=332, build_marker='COH_GPU_PROBE_BUILD:production')),
            'GPU production PE32 bytes/current source/run differ from Win32 qualification')


def pe32_helper_pins(checks):
    return {PE32_HELPER_SOURCE: {'bytes': checks.get('fixture_bytes'), 'sha256': checks.get('fixture_sha256')},
        PE32_HELPER_EXE: {'bytes': checks.get('executable_bytes'), 'sha256': checks.get('executable_sha256')}}


def validate_pe32_helpers(checks, directory):
    """At generation, close the downloaded current-job guard source and PE.

    Helpers stay in the Windows evidence artifact. The fixed GPU payload carries
    their source/run-bound receipt, without shipping these host-only fixtures.
    """
    import test_coh_gpu_probe_native as probe
    directory = Path(directory)
    pins = pe32_helper_pins(checks)
    for name, expected in pins.items():
        path = directory / name
        require(path.is_file() and not path.is_symlink()
            and type(expected['bytes']) is int and 0 < expected['bytes'] <= 16 * 1024 * 1024
            and typed_equal(file_pin(path), expected), 'Actual Win32 helper file pin differs: ' + name)
    source = (directory / PE32_HELPER_SOURCE).read_text().replace('\r\n', '\n')
    includes = re.findall(r'^#include ("[^\n]+")$', source, re.MULTILINE)
    require(len(includes) == 1, 'Actual Win32 helper source include differs')
    target = json_value(includes[0])
    require(type(target) is str and re.fullmatch(r'[A-Za-z]:/[^\r\n\x00]+/android/native/coh-gpu-probe\.c', target),
        'Actual Win32 helper must include the current checkout probe source')
    positive = '\n'.join(f'r->{field} = 1;' for field in probe.BOOL_FIELDS)
    rejected = '\n'.join(f'positive(&r); r.{field} = 0; printf("%d",result_passes(&r));'
        for field in probe.BOOL_FIELDS)
    expected_source = probe.FIXTURE.replace('SOURCE_PATH', includes[0]).replace(
        'POSITIVE_FIELDS', positive).replace('REJECT_FIELDS', rejected)
    require(source == expected_source, 'Actual Win32 helper code differs from the current source test seam')
    raw = (directory / PE32_HELPER_EXE).read_bytes()
    helper = pe_info(raw)
    require(helper['pe_machine'] == 332 and b'COH_GPU_PROBE_BUILD:host_fixture' in raw
        and b'COH_GPU_PROBE_BUILD:production' not in raw and not helper['delay_imports'],
        'Actual Win32 guard executable must be a distinct PE32 host fixture')
    return pins


def validate_package(directory, commit):
    directory = Path(directory)
    require(re.fullmatch(r'[0-9a-f]{40}', commit or ''), 'Exact GPU repository commit required')
    require(directory.is_dir() and not directory.is_symlink()
        and {path.name for path in directory.iterdir()} == {ARCHIVE, MANIFEST, RECEIPT}
        and all(path.is_file() and not path.is_symlink() for path in directory.iterdir()),
        'GPU producer artifact inventory differs')
    outer, receipt = read_json(directory / MANIFEST), read_json(directory / RECEIPT)
    contents = archive_contents(directory / ARCHIVE)
    inner = json_value(contents[INNER_MANIFEST])
    validate_inner(inner, contents, commit)
    require(typed_equal(json_value(contents[INNER_RECEIPT]), receipt), 'GPU build receipt closure differs')
    require(receipt.get('format') == 1 and receipt.get('role') == 'client_hardware_renderer_build_input'
        and receipt.get('repository_commit') == commit and receipt.get('run_url') == inner['run_url']
        and typed_equal(receipt.get('source_files'), source_pins())
        and typed_equal(receipt.get('lock'), lock())
        and receipt.get('base_archive') == base_pin()
        and receipt.get('base_abi') == file_pin(ROOT / 'tools/android/gpu-runtime/base-abi.json'),
        'GPU current source/build inputs differ')
    validate_container_receipt(receipt.get('container_build', {}))
    validate_pe32_checks(receipt.get('pe32_checks'), commit, inner['run_url'], contents[PE32_PROBE])
    require(typed_equal(receipt.get('pe32_helper_files'), pe32_helper_pins(receipt['pe32_checks'])),
        'GPU source/run-bound Win32 helper receipt differs')
    with tempfile.TemporaryDirectory(prefix='coh-verify-gpu-') as temporary:
        for name in (DRIVER, VULKAN_PROBE, PE32_PROBE):
            (Path(temporary) / name).write_bytes(contents[name])
        actual_checks = binary_checks(temporary)
    require(typed_equal(receipt.get('binary_checks'), actual_checks), 'GPU actual binary/ABI checks differ')
    expected = {'format': 1, 'role': ROLE, 'repository_commit': commit,
        'run_url': inner['run_url'], 'files': {ARCHIVE: file_pin(directory / ARCHIVE)},
        'hardware_manifest': inner, 'source_build': receipt, 'binary_checks': actual_checks,
        'physical_hardware_validated': False, 'physical_performance_validated': False}
    require(typed_equal(outer, expected), 'GPU outer producer manifest differs')
    return outer


def package(args):
    require(re.fullmatch(r'[0-9a-f]{40}', args.repository_commit or '')
        and re.fullmatch(RUN, args.run_url or ''), 'Exact current GPU source/run required')
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh GPU producer output required')
    receipt = {'format': 1, 'role': 'client_hardware_renderer_build_input',
        'repository_commit': args.repository_commit, 'run_url': args.run_url,
        'source_files': source_pins(), 'lock': lock(), 'base_archive': base_pin(),
        'base_abi': file_pin(ROOT / 'tools/android/gpu-runtime/base-abi.json'),
        'container_build': read_json(args.directory / 'container-build.json'),
        'pe32_checks': read_json(args.pe32_checks)}
    validate_container_receipt(receipt['container_build'])
    require(args.pe32_probe.is_file() and not args.pe32_probe.is_symlink(),
        'Missing actual production PE32 probe')
    validate_pe32_checks(receipt['pe32_checks'], args.repository_commit, args.run_url,
        args.pe32_probe.read_bytes())
    receipt['pe32_helper_files'] = validate_pe32_helpers(receipt['pe32_checks'], args.pe32_checks.parent)
    with tempfile.TemporaryDirectory(prefix='coh-package-gpu-') as temporary:
        staged = Path(temporary)
        for name in (DRIVER, VULKAN_PROBE, NOTICES):
            source = args.directory / name
            require(source.is_file() and not source.is_symlink(), 'Missing GPU container product')
            shutil.copyfile(source, staged / name)
        shutil.copyfile(args.pe32_probe, staged / PE32_PROBE)
        receipt['binary_checks'] = binary_checks(staged)
        contents = {name: (staged / name).read_bytes() for name in (DRIVER, VULKAN_PROBE, PE32_PROBE, NOTICES)}
        contents[INNER_RECEIPT] = encoded(receipt)
    inner = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'run_url': args.run_url, 'mesa_version': lock()['mesa']['version'],
        'mesa_source_sha256': lock()['mesa']['sha256'], 'platform': lock()['platform'],
        'driver': lock()['driver'], 'gpu': 'Adreno740',
        'files': {name: dict(pin(contents[name]), mode=mode) for name, mode in MODES.items()},
        'software_default': True, 'physical_hardware_validated': False}
    contents[INNER_MANIFEST] = encoded(inner)
    args.output.mkdir(parents=True)
    with zipfile.ZipFile(args.output / ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(contents):
            entry = zipfile.ZipInfo(name, (2026, 10, 8, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | MODES.get(name, 0o644)) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, contents[name])
    (args.output / RECEIPT).write_bytes(encoded(receipt))
    outer = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'run_url': args.run_url, 'files': {ARCHIVE: file_pin(args.output / ARCHIVE)},
        'hardware_manifest': inner, 'source_build': receipt, 'binary_checks': receipt['binary_checks'],
        'physical_hardware_validated': False, 'physical_performance_validated': False}
    (args.output / MANIFEST).write_bytes(encoded(outer))
    return validate_package(args.output, args.repository_commit)


def download_base(path):
    path = Path(path); wanted = base_pin()
    if path.exists():
        require(path.is_file() and not path.is_symlink()
            and file_pin(path) == {k: wanted[k] for k in ('bytes', 'sha256')},
            'Existing GPU base archive differs')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(wanted['url'],
        headers={'User-Agent': 'coh-source-bound-gpu-builder'}), timeout=90) as response, path.open('xb') as output:
        total = 0
        while data := response.read(1024 * 1024):
            total += len(data)
            require(total <= wanted['bytes'], 'Oversized GPU base download')
            output.write(data)
    require(file_pin(path) == {k: wanted[k] for k in ('bytes', 'sha256')}, 'Actual GPU base download differs')


def build(args):
    require(typed_equal(base_snapshot(args.base_runtime), abi_snapshot()),
        'Actual base ABI differs from the independently pinned snapshot')
    tag = 'coh-gpu-runtime:' + args.repository_commit
    subprocess.run(['docker', 'build', '--platform', 'linux/arm64', '-f',
        str(ROOT / 'tools/android/gpu-runtime/Dockerfile'), '-t', tag, str(ROOT)], check=True)
    container = subprocess.check_output(['docker', 'create', tag], text=True).strip()
    try:
        with tempfile.TemporaryDirectory(prefix='coh-gpu-container-') as temporary:
            subprocess.run(['docker', 'cp', container + ':/out/.', temporary], check=True)
            args.directory = Path(temporary)
            return package(args)
    finally:
        subprocess.run(['docker', 'rm', '-f', container], check=True)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    download = sub.add_parser('download-base'); download.add_argument('--output', type=Path, required=True)
    snapshot = sub.add_parser('snapshot-base'); snapshot.add_argument('--base-runtime', type=Path, required=True)
    snapshot.add_argument('--output', type=Path, required=True)
    verify = sub.add_parser('verify'); verify.add_argument('--directory', type=Path, required=True)
    verify.add_argument('--repository-commit', required=True)
    for name in ('build', 'package'):
        command = sub.add_parser(name)
        command.add_argument('--output', type=Path, required=True)
        command.add_argument('--repository-commit', required=True); command.add_argument('--run-url', required=True)
        command.add_argument('--pe32-probe', type=Path, required=True); command.add_argument('--pe32-checks', type=Path, required=True)
        if name == 'build': command.add_argument('--base-runtime', type=Path, required=True)
        else: command.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'download-base': download_base(args.output)
    elif args.command == 'snapshot-base': args.output.write_bytes(encoded(base_snapshot(args.base_runtime)))
    elif args.command == 'verify': validate_package(args.directory, args.repository_commit)
    elif args.command == 'build': build(args)
    else: package(args)


if __name__ == '__main__':
    main()
