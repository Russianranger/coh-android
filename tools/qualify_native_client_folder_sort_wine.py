#!/usr/bin/env python3
"""Compare retained and constructor Game on one provider and closed owned prefix.

The initial retained run may generate caches. Subsequent candidate runs must
preserve every warmed BIN, identifier and non-cache data leaf. All shader cache
acceptance remains native; this is software-GL host startup, not world entry.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import package_native_client_folder_sort as native
import qualify_native_client_startup as baseline
from prepare_native_client_profile_fixture import require, pin, write

MAX_FILES, MAX_BYTES = 250000, 10 * 1024**3
CACHE_ROOTS = (('bin',), ('geobin',), ('server', 'bin'))
ANIMATION_PIG = 'server-animations.pigg'
ANIMATION_MARKER = 'client-animation-link.json'
TEXTURE_AUXILIARY = ('coh-texture-header-index.bin', 'coh-texture-header-index.json')
WORK_RECEIPTS = ('client-work.json', 'atlas-world-installed.json', 'atlas-world-reuse.json',
                 'client-visual-installed.json', 'zones-world-installed.json', 'zones-audio-installed.json')

def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)

def cached(relative):
    return any(relative.parts[:len(parts)] == parts for parts in CACHE_ROOTS)

def native_closure(work, expected):
    result = {}
    for name, record in expected.items():
        path = work / name
        result[name] = pin(path)
        require(result[name] == {'bytes': record['size'], 'sha256': record['sha256']},
                'Current native DLL/Game member changed: ' + name)
    return result

def metadata(info):
    return {'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns,
            'device': info.st_dev, 'inode': info.st_ino, 'owner_uid': info.st_uid,
            'mode': stat.S_IMODE(info.st_mode),
            'readonly': not bool(info.st_mode & 0o222)}

def leaf_snapshot(path, *, readonly=False, expected=None):
    """Bind one regular auxiliary input, including native-visible attributes."""
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid()
            and (not readonly or not before.st_mode & 0o222), 'Unowned, linked or writable auxiliary input')
    require(before.st_size <= 128 * 1024**2, 'Auxiliary input exceeded per-leaf bound')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        opened = os.fstat(descriptor)
        require(fingerprint(opened) == fingerprint(before), 'Auxiliary input changed before read')
        digest = hashlib.sha256(); count = 0
        while raw := os.read(descriptor, 1024**2):
            count += len(raw)
            require(count <= 128 * 1024**2, 'Auxiliary input grew past bound')
            digest.update(raw)
        require(fingerprint(os.fstat(descriptor)) == fingerprint(opened)
                and fingerprint(path.lstat()) == fingerprint(before), 'Auxiliary input changed during read')
    finally: os.close(descriptor)
    content = {'bytes': count, 'sha256': digest.hexdigest()}
    if expected is not None:
        require(content == {key: expected[key] for key in ('bytes', 'sha256')}, 'Authenticated auxiliary input changed: ' + path.name)
    return dict(content, **metadata(opened))

def auxiliary_snapshot(work, assets, fixture):
    """Census immutable native inputs outside data, with per-stage texture pins.

    Shader source and extracted prerequisites are inside the complete data
    census. Generated driver shader caches live in the owned prefix and remain
    native cache outputs; these are never accepted as immutable providers.
    """
    stable = {}; texture = {}
    piggs = work / 'piggs'; info = piggs.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid(), 'Owned animation Pig directory required')
    require({entry.name for entry in piggs.iterdir()} == {ANIMATION_PIG, ANIMATION_MARKER}, 'Unexpected animation Pig membership')
    target = piggs / ANIMATION_PIG; link = target.lstat()
    resource = assets / ANIMATION_PIG
    require(stat.S_ISLNK(link.st_mode) and link.st_uid == os.geteuid()
            and os.readlink(target) == str(resource) and target.resolve(strict=True) == resource,
            'Animation Pig must retain exact authenticated resource link')
    stable['piggs'] = metadata(info)
    stable['piggs/' + ANIMATION_PIG] = dict(leaf_snapshot(resource, readonly=True,
        expected=fixture['supplements']['client_animation_package']['pigg']), link_target=str(resource),
        link_mtime_ns=link.st_mtime_ns, link_mode=stat.S_IMODE(link.st_mode))
    stable['piggs/' + ANIMATION_MARKER] = leaf_snapshot(piggs / ANIMATION_MARKER)
    tools = work / 'tools'; tool_info = tools.lstat()
    require(stat.S_ISDIR(tool_info.st_mode) and tool_info.st_uid == os.geteuid()
            and list(tools.iterdir()) == [], 'Native tools prerequisite directory must remain empty')
    stable['tools'] = metadata(tool_info)
    for name in WORK_RECEIPTS:
        path = work / name
        if os.path.lexists(path): stable[name] = leaf_snapshot(path)
        else: stable[name] = None
    for name, expected in fixture['packaged_guest_sources'].items():
        stable['assets/' + name] = leaf_snapshot(assets / name, expected=expected)
    for name, expected in (('client-launcher.exe', fixture['launcher']), ('client-probe.exe', baseline.CLIENT_PROBE)):
        stable['assets/' + name] = leaf_snapshot(assets / name, expected=expected)
    stable['assets/server-animation-manifest.json'] = leaf_snapshot(assets / 'server-animation-manifest.json', readonly=True)
    for name in TEXTURE_AUXILIARY: texture[name] = leaf_snapshot(work / name, readonly=True)
    require(len(stable) <= 128 and sum(row.get('bytes', 0) for row in stable.values() if row) <= 160 * 1024**2,
            'Immutable auxiliary census exceeded bound')
    return {'format': 1, 'stable_inputs': stable, 'native_texture_binding': texture,
            'all_auxiliary_bytes_rehashed': True, 'shader_and_extracted_prerequisite_inputs_covered_by_data_census': True,
            'generated_prefix_shader_cache_is_native_output': True}

def provider_snapshot(work, import_root):
    """Hash complete data membership outside private BIN/geobin roots.

    Only existing readonly links into the verified import are admitted. Exact
    bytes are checked before and after, never promoted to persistent authority.
    """
    data = work / 'data'; imported = import_root.resolve(strict=True)
    require(data.is_dir() and not data.is_symlink() and imported.is_dir() and not import_root.is_symlink(),
            'Owned provider data and verified import roots required')
    entries = {}; directories = {}; pending = [data]; total = 0
    while pending:
        current = pending.pop()
        relative = current.relative_to(data)
        if relative.parts and cached(relative): continue
        info = current.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid(), 'Foreign or linked provider directory')
        directories[relative.as_posix()] = metadata(info)
        require(len(directories) < 25000, 'Provider directory bound exceeded')
        with os.scandir(current) as children:
            observed = sorted(children, key=lambda item: item.name)
        require(len({item.name.casefold() for item in observed}) == len(observed), 'Aliased provider siblings refused')
        for entry in observed:
            path = Path(entry.path); relative = path.relative_to(data)
            if cached(relative): continue
            before = path.lstat()
            if stat.S_ISDIR(before.st_mode): pending.append(path); continue
            if stat.S_ISLNK(before.st_mode):
                resolved = path.resolve(strict=True)
                require(resolved.is_relative_to(imported) and not resolved.is_symlink(), 'Provider link escaped original readonly import')
                before_target = resolved.stat()
                require(stat.S_ISREG(before_target.st_mode) and before_target.st_uid == os.geteuid()
                        and not before_target.st_mode & 0o222, 'Linked imported leaf is writable or foreign')
            else:
                require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid(), 'Nonregular or foreign provider leaf')
                resolved = path; before_target = before
            descriptor = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                opened = os.fstat(descriptor)
                require((opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) ==
                        (before_target.st_dev, before_target.st_ino, before_target.st_size, before_target.st_mtime_ns, before_target.st_ctime_ns),
                        'Provider leaf changed before read')
                h = hashlib.sha256(); count = 0
                while raw := os.read(descriptor, 1024**2):
                    count += len(raw); total += len(raw)
                    require(total <= MAX_BYTES and count <= 512 * 1024**2, 'Provider payload bound exceeded')
                    h.update(raw)
                after = os.fstat(descriptor)
                require((opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns, opened.st_mode) ==
                        (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_mode),
                        'Provider changed during read')
                require(fingerprint(path.lstat()) == fingerprint(before), 'Provider link or leaf changed during snapshot')
                entries[relative.as_posix()] = dict(bytes=count, sha256=h.hexdigest(), **metadata(opened),
                    link_target=os.readlink(path) if stat.S_ISLNK(before.st_mode) else None)
            finally: os.close(descriptor)
            require(len(entries) <= MAX_FILES, 'Provider leaf count exceeded bound')
    canonical = json.dumps({'files': entries, 'directories': directories}, sort_keys=True, separators=(',', ':')).encode()
    return {'format': 1, 'files': len(entries), 'bytes': total, 'directories': len(directories),
            'membership_and_content_sha256': hashlib.sha256(canonical).hexdigest(),
            'complete_bytes_rehashed': True, 'native_visible_mtime_permissions_and_readonly_bound': True,
            'persistent_authority_created': False}

def parse_constructor(text):
    rows = []
    pattern = re.compile(r'^COH_CLIENT_FOLDER_METADATA_SORT_V1 entries=([0-9]+) capacity_bytes=([0-9]+) '
                         r'reason=(sorted|allocation_failure|entry_limit|case_alias) arrival_inversions=([0-9]+) '
                         r'callback_absent=1 limit=16384 bounded_rows=256$', re.M)
    marked = [line for line in text.replace('\r', '').splitlines() if line.startswith('COH_CLIENT_FOLDER_METADATA_SORT_V1 ')]
    for line in marked:
        match = pattern.fullmatch(line)
        require(match is not None, 'Malformed actual native constructor observation')
        entries, capacity, reason, inversions = match.groups()
        values = tuple(map(int, (entries, capacity, inversions)))
        require(values[0] <= 16384 and values[1] <= 5308416 and values[2] <= values[0], 'Constructor observation exceeds native bound')
        rows.append({'entries': values[0], 'capacity_bytes': values[1], 'reason': reason, 'arrival_inversions': values[2]})
    require(0 < len(rows) <= 256 and any(row['reason'] == 'sorted' for row in rows), 'Actual Game constructor candidate did not execute')
    return rows

def logical_counts(text):
    text = text.replace('\r', '')
    texture = re.findall(r'COH_TEXTURE_INDEX_V1 hits=([0-9]+) ordinary_reads=([0-9]+)', text)
    groups = re.findall(r'(?:Loaded|Loading) group\s*libs[^\n]*?([0-9]+) files[^\n]*?([0-9]+) names', text, re.I)
    require(texture and all(tuple(map(int, row)) == tuple(map(int, texture[0])) for row in texture), 'Texture hit/count evidence missing or inconsistent')
    require(groups and all(row == groups[0] for row in groups), 'Native complete group catalog cardinality missing or inconsistent')
    return {'texture_header_hits': int(texture[0][0]), 'ordinary_header_reads': int(texture[0][1]),
            'group_catalog_observations': [list(map(int, row)) for row in groups]}

def renderer_identity(phase):
    value = phase['evidence']['current_native_evidence']['graphics_observation']
    require(set(value) == {'vendor', 'renderer', 'gl_version', 'renderer_classification'}
            and all(isinstance(value[name], str) and value[name] for name in value)
            and value['renderer_classification'] == 'software', 'Complete actual software renderer identity required')
    return value

def environment(prefix, texture):
    env = dict(os.environ, WINEARCH='win32', WINEPREFIX=str(prefix), WINEDEBUG='-all',
        WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree=d;mshtml=d', TZ='UTC', LANG='C.UTF-8',
        LIBGL_ALWAYS_SOFTWARE='1', XDG_CACHE_HOME=str(prefix / 'xdg-cache'), MESA_SHADER_CACHE_DIR=str(prefix / 'mesa-shader-cache'),
        COH_CLIENT_GRAPHICS_PROFILE='performance', COH_CLIENT_DEPENDENCY_PRELOAD='1', COH_CLIENT_SCENE_PROFILE='1',
        COH_CLIENT_DEFER_DISCARDED_FX_PRELOAD='1', COH_CLIENT_FRAME_TIMING='1', COH_CLIENT_BIN_PROFILE='1',
        COH_CLIENT_KNOWN_STRING_COPY='1', COH_CLIENT_GAMEPLAY_FPS='30', COH_CLIENT_BOUNDED_TEXTURE_ERRORS='1',
        COH_CLIENT_RENDERER_ATTRIBUTION='1', COH_CLIENT_RENDER_PIPELINE='0', COH_CLIENT_RENDER_QUEUE='1',
        COH_CLIENT_FOLDER_METADATA_SORT='1')
    env.update(texture)
    return env

def qualify(args):
    require(not args.output.exists(), 'Fresh paired Game evidence required')
    build = native.validate_package(args.package, args.package_commit, args.donor_apk)
    fixture = json.loads(args.fixture.read_text()); work = Path(fixture['work']); assets = Path(fixture['assets'])
    imported = Path(fixture['actual_client_worktree']['source_data'])
    args.output.mkdir(parents=True, mode=0o700)
    inherited = build['retained_public_client']['native_member_closure']
    before = provider_snapshot(work, imported); write(args.output / 'provider-before.json', before)
    auxiliary_before = auxiliary_snapshot(work, assets, fixture)
    write(args.output / 'auxiliary-before.json', auxiliary_before)
    native_closure(work, inherited)
    base_args = SimpleNamespace(fixture=args.fixture, prefix=args.prefix, output=args.output / 'retained',
                                native_role='retained', native=None, timeout_seconds=args.timeout_seconds)
    retained = baseline.qualify(base_args)
    require(retained['status'] == 'passed' and retained['final_cleanup']['passed'], 'Two actual retained Game launches required')
    warm = provider_snapshot(work, imported)
    require(warm == before, 'Retained initialization mutated original non-cache provider or identifiers')
    auxiliary_warm = auxiliary_snapshot(work, assets, fixture)
    require(auxiliary_warm == auxiliary_before, 'Retained initialization mutated auxiliary input bytes, dates or attributes')
    old_renderer = renderer_identity(retained['cases'][1])
    native_closure(work, inherited)
    prefix = args.prefix.absolute(); identity = retained['final_cleanup']['prefix_identity']
    info = prefix.lstat()
    require([info.st_dev, info.st_ino, info.st_uid] == identity and not info.st_mode & 0o077
            and baseline.process_census(prefix) == [], 'Current owned closed prefix identity changed')
    bins = baseline.cache_snapshot(work); write(args.output / 'warmed-bins.json', bins)
    target = work / 'CityOfHeroes.exe'; require(pin(target)['sha256'] == baseline.GAME_SHA, 'Only exact retained Game may be replaced')
    target.chmod(0o600); shutil.copyfile(args.package / 'CityOfHeroes.exe', target)
    target.chmod(0o400)
    require(pin(target) == {'bytes': build['files']['CityOfHeroes.exe']['size'], 'sha256': build['files']['CityOfHeroes.exe']['sha256']},
            'Actual candidate executable changed during publication to owned host fixture')
    sys.path.insert(0, str(assets))
    client = importlib.import_module('client_startup_diagnostic'); index = importlib.import_module('texture_header_index')
    require(all(Path(module.__file__).resolve().parent == assets for module in (client, index)), 'Only actual published guest observer/index code admitted')
    context = SimpleNamespace(report={'client_worktree': fixture['actual_client_worktree']}, check=lambda: None, event=lambda *a, **k: None)
    header, texture = index.prepare(work, fixture['actual_client_worktree']['import'], build['files']['CityOfHeroes.exe']['sha256'], context)
    require(header['native_file_opens_avoidable'] > 0 and header['original_texture_files_unchanged'], 'Candidate texture identity binding required')
    write(args.output / 'candidate-texture-index.json', header)
    candidate_auxiliary = auxiliary_snapshot(work, assets, fixture)
    require(candidate_auxiliary['stable_inputs'] == auxiliary_warm['stable_inputs'],
            'Candidate texture rebinding mutated original auxiliary inputs')
    write(args.output / 'candidate-auxiliary-before.json', candidate_auxiliary)
    env = environment(prefix, texture); tools = retained['host_tools']; results = []; cg_results = []; failure = None; cleanup = None
    candidate_dir = args.output / 'candidate'; candidate_dir.mkdir()
    try:
        case_args = SimpleNamespace(native_role='folder-sort', timeout_seconds=args.timeout_seconds)
        for label in ('first-candidate-closed-prefix', 'second-candidate-closed-prefix'):
            phase = baseline.launch_case(case_args, fixture, client, work, env, tools, candidate_dir, label)
            raw = (candidate_dir / label / 'stdout.log').read_text(errors='replace')
            phase['actual_constructor_rows'] = parse_constructor(raw); phase['logical_counts'] = logical_counts(raw)
            require(not phase['cache_delta'] and baseline.cache_snapshot(work) == bins, 'Candidate altered warmed native BIN bytes/schema')
            require(provider_snapshot(work, imported) == warm, 'Candidate mutated non-cache provider or identifiers')
            require(auxiliary_snapshot(work, assets, fixture) == candidate_auxiliary,
                    'Candidate changed animation, texture binding, helper or prerequisite input metadata/bytes')
            require(renderer_identity(phase) == old_renderer, 'Candidate software renderer vendor/version/identity changed')
            expected = dict(inherited, **{'CityOfHeroes.exe': build['files']['CityOfHeroes.exe']})
            native_closure(work, expected)
            results.append(phase)
        old_text = (args.output / 'retained' / 'closed-prefix-second-launch' / 'stdout.log').read_text(errors='replace')
        old_counts = logical_counts(old_text)
        require(all(row['logical_counts'] == old_counts for row in results), 'Native texture/catalog output cardinality changed')
        if args.cg_package is not None:
            import reuse_native_startup_profile as cg_reuse
            cg_reuse.validate_package(args.cg_package)
            target.chmod(0o600); shutil.copyfile(args.cg_package / 'CityOfHeroes-profile.exe', target); target.chmod(0o400)
            require(pin(target) == baseline.OBSERVED_GAME, 'Exact historical Cg observation executable required')
            cg_header, cg_texture = index.prepare(work, fixture['actual_client_worktree']['import'], baseline.OBSERVED_GAME['sha256'], context)
            write(args.output / 'cg-texture-index.json', cg_header)
            cg_auxiliary = auxiliary_snapshot(work, assets, fixture)
            require(cg_auxiliary['stable_inputs'] == auxiliary_warm['stable_inputs'], 'Cg binding mutated immutable auxiliary inputs')
            write(args.output / 'cg-auxiliary-before.json', cg_auxiliary)
            cg_env = environment(prefix, cg_texture); cg_env.pop('COH_CLIENT_FOLDER_METADATA_SORT', None)
            cg_dir = args.output / 'cg-observed'; cg_dir.mkdir()
            for label in ('first-cg-closed-prefix', 'second-cg-closed-prefix'):
                phase = baseline.launch_case(SimpleNamespace(native_role='cg-observed', timeout_seconds=args.timeout_seconds),
                    fixture, client, work, cg_env, tools, cg_dir, label)
                require(not phase['cache_delta'] and baseline.cache_snapshot(work) == bins and provider_snapshot(work, imported) == warm,
                        'Cg diagnostic changed warmed BIN or source/identifier bytes')
                require(auxiliary_snapshot(work, assets, fixture) == cg_auxiliary,
                        'Cg diagnostic changed immutable auxiliary input metadata/bytes')
                native_closure(work, dict(inherited, **{'CityOfHeroes.exe':
                    {'size': baseline.OBSERVED_GAME['bytes'], 'sha256': baseline.OBSERVED_GAME['sha256']}}))
                require(renderer_identity(phase) == old_renderer, 'Cg observer software renderer identity changed')
                cg_results.append(phase)
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': str(error)[:2048]}
    finally:
        stop = args.output / 'paired-final-cleanup'; stop.mkdir()
        try: cleanup = baseline.stop_prefix(prefix, env, tools['wineserver'], stop)
        except BaseException as error: cleanup = {'passed': False, 'message': str(error)[:2048]}
        value = {'format': 1, 'role': 'nonshipping_paired_Game_folder_constructor_Wine_startup',
            'status': 'passed' if len(results) == 2 and failure is None and cleanup['passed'] else 'failed',
            'failure': failure, 'final_cleanup': cleanup, 'retained': retained, 'candidate': results, 'cg_observed': cg_results,
            'actual_candidate_package': pin(args.package / native.MANIFEST), 'native_package_commit': args.package_commit,
            'provider_before': before, 'warmed_provider': warm, 'warmed_BIN_inventory': bins,
            'auxiliary_before': auxiliary_before, 'warmed_auxiliary': auxiliary_warm,
            'candidate_auxiliary_binding': candidate_auxiliary, 'retained_software_renderer': old_renderer,
            'single_provider_preparation': True, 'same_closed_owned_prefix': True,
            'timing_comparison_scope': 'retained_second_launch_vs_candidate_first_and_second_on_same_warm_provider_prefix_and_host',
            'native_startup_renderer_and_cardinality_parity': len(results) == 2 and failure is None,
            'shader_cache_acceptance_changed': False, 'original_immutable_inputs_changed': False,
            'native_world_entry_qualified': False, 'gameplay_or_visual_parity_claimed': False,
            'cold_filesystem_cache_qualified': False, 'physical_Thor_executed': False, 'publication_allowed': False,
            'source_script': pin(Path(__file__)), 'repository_commit': os.environ.get('GITHUB_SHA'),
            'workflow_run_id': os.environ.get('GITHUB_RUN_ID')}
        write(args.output / 'native-client-folder-sort-Wine-qualification.json', value)
    require(value['status'] == 'passed', 'Paired actual Game failed; native evidence and cleanup retained')
    return value

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'fixture', 'donor-apk', 'output', 'prefix'): p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--package-commit', required=True); p.add_argument('--timeout-seconds', type=int, default=900)
    p.add_argument('--cg-package', type=Path)
    value = qualify(p.parse_args()); print(json.dumps({'status': value['status'], 'scope': value['role']}))
