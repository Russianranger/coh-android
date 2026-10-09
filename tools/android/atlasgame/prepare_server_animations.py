#!/usr/bin/env python3
"""Pack unchanged animations and prove stock native preload consumption.

All 5,878 accepted .anim payloads and native cached header prefixes are stored
uncompressed in one Pig v2. An isolated stock MapServer baseline and two packed
preloads prove normal exit, original cache/input conservation and actual packed
content reads. This is host qualification; Thor startup savings remain unmeasured.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
sys.path.insert(0, str(ROOT / 'tools'))
import server_animation_package as package
from animation_format import animation_header, animation_dependency_report

spec = importlib.util.spec_from_file_location('animation_public_cache_observer', Path(__file__).with_name('qualify_published_server_caches.py'))
public = importlib.util.module_from_spec(spec); spec.loader.exec_module(public)
observer = public.observer
require, pin, canonical = package.require, package.file_pin, package.canonical
REPORT = 'server-animation-generation-report.json'
SOURCES = ('android/guest/server_animation_package.py', 'tools/android/atlasgame/prepare_server_animations.py',
           'tools/animation_format.py', 'assets/reference-inputs-manifest.json',
           'upstream/ouroboros/Common/seq/animtrack.c', 'upstream/ouroboros/Common/seq/animtrack.h',
           'upstream/ouroboros/Common/seq/seqload.c',
           'upstream/ouroboros/libs/UtilitiesLib/src/utils/piglib.c',
           'upstream/ouroboros/libs/UtilitiesLib/src/utils/file.c',
           'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCache.c',
           'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCacheNode.c',
           'upstream/ouroboros/libs/UtilitiesLib/src/utils/PigFileWrapper.c',
           'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/piglib_internal.h',
           *public.QUALIFICATION_SOURCES)
GENERATOR_SOURCES = tuple(dict.fromkeys(SOURCES))


def accepted_inventory():
    source = ROOT / 'assets/reference-inputs-manifest.json'
    require(pin(source)['sha256'] == package.ASSET_MANIFEST_SHA256, 'Accepted asset manifest differs')
    document = json.loads(source.read_bytes(), object_pairs_hook=observer.package.unique_object)
    files = {entry['path']: {'bytes': entry['size'], 'sha256': entry['sha256'], 'timestamp': observer.package.EPOCH}
             for entry in document['files'] if entry['path'].endswith('.anim')}
    return package.validate_inventory(files)


def data_pool(flag, items):
    body = b''.join(struct.pack('<I', len(item)) + item for item in items)
    require(len(body) <= package.MAX_METADATA, 'Pig pool exceeds bound')
    return struct.pack('<III', flag, len(items), len(body)) + body


def write_pigg(path, files, payloads):
    """Yield/read one immutable payload at a time; preserve native 32-bit bytes."""
    files = package.validate_inventory(files, exact=len(files) == package.ANIMATION_COUNT)
    names = sorted(files, key=str.upper)
    headers, facts = [], {}
    for name in names:
        body = payloads(name)
        require(observer.package.pin_bytes(body) == {key: files[name][key] for key in ('bytes', 'sha256')},
                'Accepted animation payload differs: ' + name)
        header = animation_header(body)
        require(header['validation_status'] == 'structural_checks_passed', 'Animation structure differs: ' + name)
        require(header['name'].replace('\\', '/').casefold() == name[len('player_library/animations/'):-5],
                'Animation logical name differs: ' + name)
        headers.append(body[:header['header_size']]); facts[name] = header
    dependency = animation_dependency_report(facts.values())
    require(dependency['validated_track_count'] == len(files)
            and all(not dependency[key] for key in ('invalid_header_names', 'duplicate_casefolded_names',
                        'missing_base_names', 'nonterminal_cycles', 'terminal_bases_without_hierarchy'))
            and dependency['terminal_base_count'] > 0, 'Animation base skeleton closure differs')
    name_pool = data_pool(0x6789, [name.encode('ascii') + b'\0' for name in names])
    header_pool = data_pool(0x9ABC, headers)
    offset = 16 + 48 * len(names) + len(name_pool) + len(header_pool)
    require(offset <= package.MAX_METADATA, 'Pig metadata exceeds bound')
    with Path(path).open('xb') as output:
        output.write(package.HEADER.pack(0x123, 2, 2, 16, 48, len(names)))
        for index, name in enumerate(names):
            body = payloads(name)
            require(observer.package.pin_bytes(body) == {key: files[name][key] for key in ('bytes', 'sha256')},
                    'Animation changed during packing: ' + name)
            output.write(package.ENTRY.pack(0x3456, index, len(body), files[name]['timestamp'], offset, 0,
                                            index, hashlib.md5(body).digest(), 0))
            offset += len(body)
        output.write(name_pool); output.write(header_pool)
        for name in names:
            body = payloads(name)
            require(observer.package.pin_bytes(body) == {key: files[name][key] for key in ('bytes', 'sha256')},
                    'Animation changed during payload copy: ' + name)
            output.write(body)
    return package.verify_pigg(path, files, exact=len(files) == package.ANIMATION_COUNT), dependency


def prepare_pack(asset_archive, output, repository_commit):
    require(pin(asset_archive)['sha256'] == package.ASSET_ARCHIVE_SHA256, 'Accepted asset archive differs')
    files = accepted_inventory()
    with zipfile.ZipFile(asset_archive) as source:
        names = source.namelist()
        require(len(names) == len(set(names)), 'Duplicate accepted asset archive entry')
        def body(name):
            # The accepted ZIP prefixes original logical asset paths with assets/.
            info = source.getinfo('assets/' + name)
            require(not info.is_dir() and not info.flag_bits & 1 and info.file_size == files[name]['bytes'],
                    'Accepted animation ZIP member differs')
            return source.read(info)
        pigment, dependencies = write_pigg(output / package.PIGG, files, body)
    manifest = {'format': 1, 'role': package.ROLE, 'repository_commit': repository_commit,
                'identity': package.identity(), 'files': files, 'pigg': pigment,
                'loose_inputs_preserved': True, 'native_client_or_server_recompiled': False,
                'android_execution_validated': False, 'physical_startup_timing_validated': False}
    observer.write_json(output / package.MANIFEST, manifest)
    package.verify_package(output / package.PIGG, output / package.MANIFEST)
    return manifest, dependencies


def animation_trace_path(raw, runtime):
    raw = raw.removesuffix(' (deleted)')
    if not raw.startswith('/'): return None
    prefix = observer.trace_runtime_prefix(str(runtime))
    value = raw.replace('\\', '/').casefold()
    if not value.startswith(prefix): return None
    relative = value[len(prefix):]
    if (relative.startswith('data/player_library/animations/') or relative == 'piggs/' + package.PIGG) and all(
            part not in ('', '.', '..') for part in relative.split('/')):
        return relative
    return None


def completed_animation_trace_lines(path):
    pending = {}
    with Path(path).open(errors='replace') as source:
        for line in source:
            unfinished = re.search(r'\b(read|pread64|write|pwrite64|mmap|mmap2)\(.*<unfinished \.\.\.>\s*$', line)
            if unfinished:
                operation = unfinished.group(1)
                require(operation not in pending, 'Overlapping unfinished animation syscall')
                pending[operation] = line[:line.index('<unfinished ...>')]
                continue
            resumed = re.match(r'^\s*<\.\.\. (read|pread64|write|pwrite64|mmap|mmap2) resumed>(.*)$', line)
            if resumed:
                operation, rest = resumed.groups(); start = pending.pop(operation, None)
                if start is None:
                    require(not re.search(r'\)\s*=\s*(?:[1-9]\d*|0x[0-9a-f]+)(?:\s|$)', rest),
                            'Unmatched successful animation syscall')
                    continue
                yield start + rest + '\n'
            else: yield line
    require(not any('/piggs/' in line.replace('\\', '/').casefold()
                    or '/data/player_library/animations/' in line.replace('\\', '/').casefold()
                    for line in pending.values()), 'Unfinished animation content syscall has no completion')


def animation_trace(paths, runtime, metadata_bytes):
    """Actual successful descriptor reads, not open/stat or manifest assertions."""
    packed_reads, loose_reads, writes, pins = 0, {}, {}, {}
    total = 0
    for path in sorted(map(Path, paths)):
        require(path.is_file() and not path.is_symlink(), 'Missing animation trace leaf')
        total += path.stat().st_size; require(total <= observer.MAX_TRACE, 'Animation traces exceed bound')
        pins[path.name] = pin(path)
        for line in completed_animation_trace_lines(path):
            match = re.search(r'\b(read|pread64|write|pwrite64)\(\d+<([^>]*)>.*\)\s*=\s*(\d+)(?:\s|$)', line)
            if match:
                operation, raw, amount = match.groups(); amount = int(amount)
                name = animation_trace_path(raw, runtime)
                if not name or not amount: continue
                animation = name.startswith('data/player_library/animations/') and name.endswith('.anim')
                packed = name == 'piggs/' + package.PIGG
                if not (animation or packed): continue
                if operation in ('write', 'pwrite64'): writes[name] = writes.get(name, 0) + amount
                elif packed: packed_reads += amount
                elif animation: loose_reads[name] = loose_reads.get(name, 0) + amount
            if re.search(r'\bmmap(?:2)?\(', line) and 'PROT_READ' in line and re.search(r'\)\s*=\s*0x', line):
                for raw in re.findall(r'\d+<([^>]*)>', line):
                    name = animation_trace_path(raw, runtime)
                    require(not (name and name.startswith('data/player_library/animations/') and name.endswith('.anim')),
                            'Mapped loose animation cannot prove packed-only loading')
            if re.search(r'\b(?:rename|renameat|renameat2|unlink|unlinkat)\(', line) and re.search(r'\)\s*=\s*0(?:\s|$)', line):
                for raw in re.findall(r'"([^"\n]+)"', line):
                    name = animation_trace_path(raw, runtime)
                    if name == 'piggs/' + package.PIGG or (name and name.startswith('data/player_library/animations/') and name.endswith('.anim')):
                        writes[name] = writes.get(name, 0) + 1
    require(pins, 'Missing animation consumption traces')
    return {'format': 1, 'observer': 'strace-successful-native-content-reads', 'trace_files': pins,
            'packed_content_read_bytes': packed_reads, 'pack_metadata_bytes': metadata_bytes,
            'loose_animation_content_reads': dict(sorted(loose_reads.items())),
            'animation_writes': dict(sorted(writes.items())),
            'packed_only_loading_proven': packed_reads > metadata_bytes * 2 and not loose_reads and not writes}


def verify_generated_package(directory):
    directory = Path(directory)
    manifest = package.verify_package(directory / package.PIGG, directory / package.MANIFEST)
    report = observer.read_json(directory / REPORT)
    require(report.get('format') == 1 and report.get('status') == 'original_animations_native_packed_consumption_qualified'
            and report.get('repository_commit') == manifest['repository_commit']
            and report.get('identity') == package.identity()
            and report.get('pigg') == manifest['pigg']
            and report.get('source_files') == {name: pin(ROOT / name) for name in dict.fromkeys(SOURCES)}
            and report.get('evidence_files') == observer.evidence_pins(directory),
            'Animation producer/evidence bytes differ')
    require(report.get('donor_apk') == observer.DONOR_APK
            and report.get('donor_build_report') == observer.DONOR_REPORT
            and report.get('published_apk') == public.PUBLISHED_APK
            and report.get('published_cache_archive') == public.PUBLISHED_CACHE_ARCHIVE
            and report.get('launcher') == pin(directory / 'evidence/server-cache-launcher.exe')
            and report.get('android_execution_validated') is False
            and report.get('physical_startup_timing_validated') is False,
            'Animation qualification provenance differs')
    require(report['identifier_snapshots']['before'] == report['identifier_snapshots']['after']
            and report['noncache_snapshots']['before'] == report['noncache_snapshots']['after']
            and report['cache_snapshots']['before'] == report['cache_snapshots']['after'],
            'Animation qualification changed original native inputs/caches')
    cache_manifest = observer.package.verify_archive(directory / public.ARCHIVE)
    require(pin(directory / public.ARCHIVE) == public.PUBLISHED_CACHE_ARCHIVE
            and cache_manifest['repository_commit'] == public.PUBLISHED_CACHE_COMMIT, 'Public server cache bytes differ')
    source_paths = observer.archive_source_paths(directory / public.ARCHIVE, cache_manifest['files'])
    for stage in ('baseline', 'cold', 'warm'):
        evidence = directory / 'evidence' / stage
        invocation = observer.read_json(evidence / 'invocation.json')
        recorded = observer.read_json(evidence / 'phase-receipt.json')
        require(invocation.get('stage') == stage and invocation.get('identity') == cache_manifest['identity']
                and invocation.get('timezone') == 'UTC' and invocation.get('wine_debug') == '-all'
                and type(recorded.get('elapsed_seconds')) in (int, float) and recorded['elapsed_seconds'] > 0,
                'Animation native invocation identity/timezone differs')
        phase = observer.phase_receipt((evidence / 'stdout.log').read_bytes(), (evidence / 'stderr.log').read_bytes(),
                                       stage, invocation['session_id'], recorded['launcher_exit_code'], True)
        require(all(recorded.get(key) == value for key, value in phase.items()), 'Native phase receipt differs')
        cleanup = observer.read_json(evidence / 'wine-helpers-stop.json')
        require(cleanup.get('kill_exit_code') in (0, 1) and cleanup.get('wait_exit_code') == 0
                and cleanup.get('normal_launcher_exit_observed_first') is True
                and cleanup.get('status') == 'prefix_server_lock_unheld'
                and cleanup.get('prefix') == invocation.get('wine_prefix')
                and isinstance(cleanup.get('server_directory'), str)
                and Path(cleanup['server_directory']).is_absolute()
                and (evidence / 'wine-helpers-stop.log').read_bytes() == b'',
                'Animation native prefix quiescence missing')
        trace = observer.trace_receipt(evidence.glob('trace.*'), invocation['runtime_host_path'],
                                       cache_manifest['files'], source_paths, invocation['identity']['identifier_files'])
        require(not trace['source_content_reads'] and not trace['cache_writes']
                and all(trace['cache_content_reads'].values()), 'Packed preload changed cache consumption')
        animation = animation_trace(evidence.glob('trace.*'), invocation['runtime_host_path'], manifest['pigg']['metadata_bytes'])
        require(animation == observer.read_json(evidence / 'animation-trace-receipt.json'), 'Animation trace facts differ')
        require(report['native_phases'][stage] == {'elapsed_seconds': recorded['elapsed_seconds'], 'animation': animation},
                'Recorded native animation phase differs')
        if stage == 'baseline':
            require(animation['loose_animation_content_reads'] and not animation['packed_content_read_bytes']
                    and not animation['animation_writes'], 'Ordinary loose fallback evidence missing')
        else:
            require(animation['packed_only_loading_proven'], 'Native packed-only animation consumption missing')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('donor-apk', 'donor-build-report', 'published-apk', 'asset-archive', 'work', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--wine', default='wine')
    parser.add_argument('--timeout-seconds', type=int, default=1800)
    args = parser.parse_args()
    args.work, args.output = args.work.resolve(), args.output.resolve()
    require(observer.package.HEX40.fullmatch(args.repository_commit)
            and 30 <= args.timeout_seconds <= 3600, 'Invalid animation commit/timeout')
    require(not args.work.exists() and not args.output.exists(), 'Fresh animation work/output required')
    args.work.mkdir(parents=True); args.output.mkdir(parents=True); (args.output / 'evidence').mkdir()
    manifest, dependencies = prepare_pack(args.asset_archive.resolve(), args.output, args.repository_commit)
    cache_manifest = public.extract_published_caches(args.published_apk.resolve(), args.output)
    caches, prerequisites, host, world, avatar = observer.generation_modules()
    imports, assets = observer.extract_donor(args.donor_apk.resolve(), args.donor_build_report.resolve(), args.work / 'donor', host)
    data = host.import_game_data(imports, args.asset_archive.resolve(), args.work, args.output / 'evidence')
    runtime = data.parent
    observer.extract_tar(assets / 'game-package.tar.gz', runtime, 'game-package.json')
    observer.extract_tar(assets / 'dbserver-schema.tar.gz', runtime, 'schema-manifest.json', observer.package.compatibility_identity()['schema_manifest_sha256'])
    observer.seed_zip(assets / 'client-caches.zip', runtime, caches.verify_cache_archive(assets / 'client-caches.zip'))
    observer.seed_zip(assets / 'client-prerequisites.zip', runtime, prerequisites.verify_archive(assets / 'client-prerequisites.zip'))
    context = type('HostContext', (), {'check': lambda self: None})()
    world.install(runtime, assets, context); avatar.install(runtime, assets, context)
    observer.normalize_data(data)
    identity = observer.package.build_expected_identity(data, runtime / 'MapServer.exe')
    public.seed_published_caches(args.output / public.ARCHIVE, runtime, cache_manifest, fresh_host_only=True)
    observer.write_json(args.output / 'evidence/native-runtime-layout.json', observer.prepare_runtime_layout(runtime))
    launcher = args.work / 'server-cache-launcher.exe'
    with (args.output / 'evidence/launcher-build.log').open('wb') as log:
        subprocess.run(['i686-w64-mingw32-gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-static-libgcc',
                        str(ROOT / 'android/native/server-cache-launcher.c'), '-o', str(launcher)],
                       check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    shutil.copyfile(launcher, args.output / 'evidence/server-cache-launcher.exe')
    environment = dict(os.environ, WINEARCH='win32', WINEPREFIX=str(args.work / 'wine-prefix'), WINEDEBUG='-all',
                       WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree=d;mshtml=d', TZ='UTC', LANG='C.UTF-8')
    identifiers = {'before': observer.package.identifier_snapshot(data)}
    noncache = {'before': observer.data_snapshot(data)}
    snapshots = {'before': observer.cache_state(runtime, cache_manifest['files'])}
    sources = observer.archive_source_paths(args.output / public.ARCHIVE, cache_manifest['files'])
    phases = {}
    for stage in ('baseline', 'cold', 'warm'):
        if stage == 'cold': package.install(args.output / package.PIGG, args.output / package.MANIFEST, runtime, context=context)
        with (args.output / 'evidence' / ('wine-initialization-' + stage + '.log')).open('wb') as log:
            subprocess.run([args.wine, 'wineboot', '--init'], env=environment, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=180)
        initialization = args.output / 'evidence' / ('prefix-initialization-' + stage); initialization.mkdir()
        observer.stop_owned_prefix(environment, initialization, normal_launcher_exit_observed_first=False)
        phase = observer.run_phase(args, runtime, launcher, environment, args.output, stage, identity, trace=True)
        evidence = args.output / 'evidence' / stage
        trace = observer.trace_receipt(evidence.glob('trace.*'), runtime, cache_manifest['files'], sources, identity['identifier_files'])
        require(not trace['source_content_reads'] and not trace['cache_writes'] and all(trace['cache_content_reads'].values()),
                'Animation preload did not retain exact public cache consumption')
        animation = animation_trace(evidence.glob('trace.*'), runtime, manifest['pigg']['metadata_bytes'])
        observer.write_json(evidence / 'animation-trace-receipt.json', animation)
        phases[stage] = {'elapsed_seconds': phase['elapsed_seconds'], 'animation': animation}
    identifiers['after'] = observer.package.identifier_snapshot(data)
    noncache['after'] = observer.data_snapshot(data)
    snapshots['after'] = observer.cache_state(runtime, cache_manifest['files'])
    report = {'format': 1, 'status': 'original_animations_native_packed_consumption_qualified',
              'repository_commit': args.repository_commit, 'identity': package.identity(), 'pigg': manifest['pigg'],
              'donor_apk': observer.DONOR_APK, 'donor_build_report': observer.DONOR_REPORT,
              'published_apk': public.PUBLISHED_APK, 'published_cache_archive': public.PUBLISHED_CACHE_ARCHIVE,
              'launcher': pin(launcher),
              'source_files': {name: pin(ROOT / name) for name in dict.fromkeys(SOURCES)},
              'dependencies': dependencies, 'native_phases': phases,
              'identifier_snapshots': identifiers, 'noncache_snapshots': noncache, 'cache_snapshots': snapshots,
              'evidence_files': observer.evidence_pins(args.output),
              'android_execution_validated': False, 'physical_startup_timing_validated': False}
    observer.write_json(args.output / REPORT, report)
    verify_generated_package(args.output)
    print(json.dumps({'status': report['status'], 'pigg': report['pigg'],
                      'native_preload_seconds': {stage: phases[stage]['elapsed_seconds'] for stage in phases}}))


if __name__ == '__main__': main()
