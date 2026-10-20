#!/usr/bin/env python3
"""Stage/verify/record a disposable compile-only original MapServer witness.

Never starts a game process or accepts a runtime generation. CMake runs only in
an independently prepared external source tree. Compilation belongs to CI.
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
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROLE = 'nonshipping_bodypart_original_loader_target'
STAGE = 'body-witness-target-stage.json'
COMPILE = 'body-witness-target-compile.json'
MAX_FILE = 32 * 1024**2
MAX_MANIFEST = 20000
MAX_TOTAL = 768 * 1024**2
PROTOTYPE = b'/* NONSHIPPING body witness observer only. */\nextern int coh_source_body_witness_snapshot_startup(void);\n'
HOOK = b'    if(coh_source_body_witness_snapshot_startup()!=0) FatalErrorf("Nonshipping body witness failed");\n'


def require(ok, code):
    if not ok:
        raise ValueError(code)


def safe(value):
    path = Path(os.path.abspath(value))
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'TARGET_PATH_LINK')
    return path


def read(value, limit=MAX_FILE):
    path = safe(value)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 <= before.st_size <= limit,
            'TARGET_FILE_BOUND')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    after = path.stat()
    require(len(raw) == before.st_size and len(raw) <= limit and
            (before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns), 'TARGET_FILE_CHANGED')
    return raw


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = read(path)
    return {'bytes': len(raw), 'sha256': sha(raw)}


def decode(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'TARGET_JSON_DUPLICATE')
            out[key] = value
        return out
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: require(False, 'TARGET_JSON_NONFINITE'))
    require(type(value) is dict, 'TARGET_JSON_OBJECT')
    return value


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def modules(root):
    require(HERE == root / 'native-android/engine/costume-export', 'TARGET_OWN_CHECKOUT')
    witness = load('body_target_original_witness', HERE / 'stage_body_witness.py')
    prior = load('body_target_prior', root / 'native-android/engine/scenecatalog-server/stage_export.py')
    return witness, prior


def checkout(root):
    root = safe(root)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    require(re.fullmatch('[0-9a-f]{40}', head), 'TARGET_HEAD')
    require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=root), 'TARGET_DIRTY_CHECKOUT')
    # This check binds imported suppliers to their actual tracked bytes. Detailed
    # upstream/import provenance remains in the inherited original staging graph.
    rows = subprocess.check_output(['git', 'ls-tree', '-r', '-z', 'HEAD', '--',
        'tools', 'database', 'patches', 'upstream/ouroboros', 'android/guest',
        'native-android/engine/costume-export', 'native-android/engine/body-catalog',
        'native-android/engine/scenecatalog-server/stage_export.py',
        'native-android/engine/scenecatalog-qualification'], cwd=root)
    require(len(rows) <= 8 * 1024**2, 'TARGET_TREE_BOUND')
    result = {}; total = 0
    for row in rows.split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1); mode, kind, blob = meta.split()
        require(kind == b'blob' and mode in (b'100644', b'100755'), 'TARGET_TRACKED_MODE')
        path = root / name.decode()
        raw = read(path); total += len(raw)
        require(len(result) < MAX_MANIFEST and total <= MAX_TOTAL, 'TARGET_CHECKOUT_BUDGET')
        require(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blob.decode(),
                'TARGET_TRACKED_BYTES')
        result[name.decode()] = {'bytes': len(raw), 'sha256': sha(raw)}
    return {'head': head, 'files': result, 'total_bytes': total}


def startup_patch(original):
    require(b'\r' not in original and original.count(b'    loadCostumes();\n') == 1 and
            b'coh_source_body_witness_snapshot_startup' not in original, 'TARGET_STARTUP_ANCHOR')
    return PROTOTYPE + original.replace(b'    loadCostumes();\n', b'    loadCostumes();\n' + HOOK, 1)


def startup_unpatch(patched):
    require(patched.startswith(PROTOTYPE) and patched.count(HOOK) == 1, 'TARGET_STARTUP_REVERSAL')
    return patched[len(PROTOTYPE):].replace(HOOK, b'', 1)


def inputs(root, directory):
    helper = load('body_target_startup_inputs', root / 'tools/android/interactive/map_startup_inputs.py')
    sys.path.insert(0, str(root / 'native-android/engine/scenecatalog-qualification'))
    try:
        validator = load('body_target_compile_validator', root / 'native-android/engine/scenecatalog-qualification/record_export_compile.py')
    finally:
        sys.path.pop(0)
    proof = validator.validate_inputs(decode(read(directory / 'map-startup-inputs.json')), helper)
    helper.checked(directory / 'COH-Atlas-Gameplay-0.13.31.apk', helper.DONOR)
    for name, expected in proof['files'].items():
        helper.checked(directory / name, expected)
    return proof, validator


def paths(root, staged):
    root, staged = safe(root), safe(staged)
    require(root != staged and root not in staged.parents and staged not in root.parents,
            'TARGET_EXTERNAL_STAGE_REQUIRED')
    require(staged.is_dir(), 'TARGET_STAGE_MISSING')
    return root, staged


def stage(root, staged, metadata):
    root, staged = paths(root, staged)
    witness, prior = modules(root)
    admission = checkout(root)
    inherited = prior.validate_prior(root, staged)
    require(not (staged / STAGE).exists(), 'TARGET_STAGE_EXISTS')
    names = (witness.BODY, witness.PARSER, witness.SERVER, witness.BODY_H, witness.BONES_H)
    originals = {n: read(root / 'upstream/ouroboros' / n) for n in names}
    rendered, body = witness.render(originals, metadata)
    # Body/parser remain byte-exact originals in the inherited startup role.
    # svr_init has qualified inherited progress hooks: compose rather than replace.
    for n in (witness.BODY, witness.PARSER):
        require(read(staged / n) == originals[n], 'TARGET_LOADER_BASE_CHANGED')
    previous = read(staged / witness.SERVER)
    rendered[witness.SERVER] = startup_patch(previous)
    require(startup_unpatch(rendered[witness.SERVER]) == previous, 'TARGET_STARTUP_PRESERVATION')
    new = set(rendered) - {witness.BODY, witness.PARSER, witness.SERVER}
    for n in new:
        require(not (staged / n).exists(), 'TARGET_OVERLAY_COLLISION')
    receipt = {'schema': 'coh-body-witness-target-stage-v1', 'build_role': ROLE,
        'source_revision': admission['head'], 'checkout_manifest_sha256': sha(encoded(admission)),
        'prior_build_input': inherited, 'metadata_labels': metadata, 'body_overlay': body,
        'original_startup_sha256': sha(previous), 'outputs': {n: {'bytes': len(raw), 'sha256': sha(raw)} for n, raw in rendered.items()},
        'runtime_executed': False, 'runtime_generation_admitted': False, 'world_authority': False,
        'witness_enabled_by_default': False, 'original_loader_decisions_preserved': True}
    # Preflight all names/bytes before mutations. Failure restores previous TUs
    # and removes only this operation's newly created files.
    saved = {n: read(staged / n) for n in rendered if n not in new}
    created = []
    try:
        for n, raw in rendered.items():
            target = staged / n
            require(target.parent.is_dir(), 'TARGET_OVERLAY_PARENT')
            with target.open('xb' if n in new else 'wb') as stream:
                if n in new: created.append(target)
                stream.write(raw)
        with (staged / STAGE).open('xb') as stream:
            created.append(staged / STAGE); stream.write(encoded(receipt))
        require(checkout(root) == admission, 'TARGET_CHECKOUT_CHANGED')
        return receipt
    except BaseException:
        for n, raw in saved.items(): (staged / n).write_bytes(raw)
        for target in reversed(created): target.unlink(missing_ok=True)
        raise


def verify(root, staged):
    root, staged = paths(root, staged)
    witness, prior = modules(root)
    admission = checkout(root); receipt = decode(read(staged / STAGE))
    require(receipt.get('schema') == 'coh-body-witness-target-stage-v1' and
            receipt.get('build_role') == ROLE and receipt.get('source_revision') == admission['head'] and
            receipt.get('checkout_manifest_sha256') == sha(encoded(admission)), 'TARGET_STAGE_IDENTITY')
    inherited = receipt['prior_build_input']
    require(prior.json_equal(inherited, prior.expected_prior(root, inherited)) and
            decode(read(staged / 'map-startup-build-input.json')) == inherited, 'TARGET_INHERITED_IDENTITY')
    names = (witness.BODY, witness.PARSER, witness.SERVER, witness.BODY_H, witness.BONES_H)
    rendered, body = witness.render({n: read(root / 'upstream/ouroboros' / n) for n in names}, receipt['metadata_labels'])
    previous = startup_unpatch(read(staged / witness.SERVER))
    require(sha(previous) == receipt['original_startup_sha256'], 'TARGET_INHERITED_STARTUP')
    rendered[witness.SERVER] = startup_patch(previous)
    require(body == receipt['body_overlay'] and receipt['outputs'] ==
            {n: {'bytes': len(raw), 'sha256': sha(raw)} for n, raw in rendered.items()}, 'TARGET_RENDER_CHANGED')
    inherited_hashes = prior.inherited_hashes(inherited)
    for n, digest in inherited_hashes.items():
        raw = previous if n == witness.SERVER else read(staged / n)
        if n not in (witness.BODY, witness.PARSER):
            require(sha(raw) == digest, 'TARGET_INHERITED_CHANGED')
        else:
            require(sha(read(root / 'upstream/ouroboros' / n)) == digest, 'TARGET_LOADER_INHERITED_CHANGED')
    for n, raw in rendered.items(): require(read(staged / n) == raw, 'TARGET_STAGED_BYTES')
    return receipt, admission


def dependency_manifest(staged):
    """Actual populated CPM source bytes; recipes retain their pinned URL hashes.

    Stream one bounded file at a time, without copying third-party source trees.
    Generated binaries and .git internals are excluded from this source manifest.
    """
    base = staged / 'out/build/CPM'
    require(base.is_dir() and not base.is_symlink(), 'TARGET_DEPENDENCIES_MISSING')
    result = {}; total = 0
    for current, directories, files in os.walk(base, followlinks=False):
        directories[:] = sorted(n for n in directories if n not in ('.git', 'CMakeFiles'))
        require(not any((Path(current) / n).is_symlink() for n in directories + files),
                'TARGET_DEPENDENCY_LINK')
        for name in sorted(files):
            path = Path(current) / name
            value = pin(path); total += value['bytes']
            require(len(result) < MAX_MANIFEST and total <= MAX_TOTAL, 'TARGET_DEPENDENCY_BUDGET')
            result[path.relative_to(base).as_posix()] = value
    require(result, 'TARGET_DEPENDENCIES_EMPTY')
    return {'files': result, 'total_bytes': total,
            'scope': 'Actual CPM source cache; external SDK/compiler identities recorded separately'}


def msbuild_identity(cache_fields, compiler_files):
    """VS generators may omit CMAKE_MAKE_PROGRAM: use their selected instance.

    Never search PATH or an unrelated installed Visual Studio. The selected
    compiler driver must belong to the same instance's MSVC tool directory.
    """
    def field(name):
        values = [v for k, v in cache_fields.items() if k.split(':', 1)[0] == name]
        require(len(values) <= 1, 'TARGET_CMAKE_TOOL_ALIAS')
        return values[0] if values else None
    instance = field('CMAKE_GENERATOR_INSTANCE')
    require(instance and ',version=' not in instance, 'TARGET_VS_INSTANCE_MISSING')
    instance = safe(instance)
    require(instance.is_dir(), 'TARGET_VS_INSTANCE_MISSING')
    for item in compiler_files.values():
        compiler = safe(item['path'])
        require(instance / 'VC/Tools/MSVC' in compiler.parents, 'TARGET_COMPILER_INSTANCE_MISMATCH')
    configured = field('CMAKE_MAKE_PROGRAM') or field('CMAKE_VS_MSBUILD_COMMAND')
    if configured:
        selected = safe(configured)
        require(instance / 'MSBuild' in selected.parents, 'TARGET_MSBUILD_INSTANCE_MISMATCH')
    else:
        candidates = [instance / 'MSBuild/Current/Bin/amd64/MSBuild.exe',
                      instance / 'MSBuild/Current/Bin/MSBuild.exe']
        selected = next((p for p in candidates if p.is_file()), None)
        require(selected is not None, 'TARGET_MSBUILD_IDENTITY')
    return {'path': str(selected), **pin(selected), 'selected_vs_instance': str(instance),
            'resolution': 'explicit_cmake_tool' if configured else 'selected_cmake_vs_instance'}


def toolchain_manifest(project, cache_fields, selected_sdk, compiler_files):
    """Evaluate this actual generated target, then hash selected SDK/tool inputs."""
    require(os.name == 'nt', 'TARGET_WINDOWS_TOOLCHAIN_REQUIRED')
    build_tool = msbuild_identity(cache_fields, compiler_files)
    name = build_tool['path']
    command = [name, str(project), '-nologo', '-verbosity:quiet',
        '-p:Configuration=OptDebug', '-p:Platform=Win32',
        '-getProperty:WindowsSdkDir,WindowsTargetPlatformVersion,VCToolsInstallDir,UniversalCRTSdkDir,UCRTVersion,PlatformToolset']
    run = subprocess.run(command, check=True, capture_output=True, timeout=60)
    require(len(run.stdout) <= 16384 and len(run.stderr) <= 16384, 'TARGET_TOOLCHAIN_QUERY_BOUND')
    value = decode(run.stdout)['Properties']
    require(set(value) == {'WindowsSdkDir', 'WindowsTargetPlatformVersion', 'VCToolsInstallDir',
        'UniversalCRTSdkDir', 'UCRTVersion', 'PlatformToolset'}, 'TARGET_TOOLCHAIN_PROPERTIES')
    require(value['WindowsTargetPlatformVersion'] == selected_sdk and value['UCRTVersion'] == selected_sdk,
            'TARGET_EVALUATED_SDK_MISMATCH')
    roots = {'sdk/include': safe(value['WindowsSdkDir']) / 'Include' / selected_sdk,
        'sdk/um-x86': safe(value['WindowsSdkDir']) / 'Lib' / selected_sdk / 'um/x86',
        'sdk/ucrt-x86': safe(value['UniversalCRTSdkDir']) / 'Lib' / selected_sdk / 'ucrt/x86',
        'msvc/include': safe(value['VCToolsInstallDir']) / 'include',
        'msvc/lib-x86': safe(value['VCToolsInstallDir']) / 'lib/x86'}
    files = {}; total = 0
    for label, base in roots.items():
        require(base.is_dir() and not base.is_symlink(), 'TARGET_TOOLCHAIN_INPUT_MISSING')
        for current, directories, names in os.walk(base, followlinks=False):
            directories.sort()
            require(not any((Path(current) / n).is_symlink() for n in directories + names), 'TARGET_TOOLCHAIN_INPUT_LINK')
            for leaf in sorted(names):
                path = Path(current) / leaf; item = pin(path); total += item['bytes']
                require(len(files) < MAX_MANIFEST and total <= MAX_TOTAL, 'TARGET_TOOLCHAIN_BUDGET')
                files[label + '/' + path.relative_to(base).as_posix()] = item
    return {'evaluated_properties': value, 'msbuild': build_tool,
        'query_command': command, 'files': files, 'total_bytes': total,
        'scope': 'Actual generated MapServer target evaluated SDK include/Win32 libraries and MSVC include/Win32 libraries; no runtime launch'}


def record(root, staged, input_dir, output):
    root, staged = paths(root, staged); output = safe(output)
    require(not output.exists() and root not in output.parents and staged not in output.parents,
            'TARGET_FRESH_OUTPUT')
    before, admission = verify(root, staged)
    startup, validator = inputs(root, safe(input_dir))
    binary = staged / 'out/build/vs2026/bin/OptDebug/MapServer.exe'
    cache = staged / 'out/build/vs2026/CMakeCache.txt'
    validator.pe32_identity(binary); validator.cmake_identity(cache, staged)
    cache_fields = dict(line.split('=', 1) for line in read(cache).decode().splitlines()
                        if '=' in line and not line.startswith(('#', '//')))
    compiler = {k: v for k, v in cache_fields.items() if k.startswith(('CMAKE_C_COMPILER:', 'CMAKE_CXX_COMPILER:',
        'CMAKE_VS_PLATFORM_TOOLSET:', 'CMAKE_VS_WINDOWS_TARGET_PLATFORM_VERSION:'))}
    compiler_files = {}; compiler_info = {}
    for language in ('C', 'CXX'):
        candidates = sorted((staged / 'out/build/vs2026/CMakeFiles').glob('*/CMake' + language + 'Compiler.cmake'))
        require(len(candidates) == 1, 'TARGET_COMPILER_INFO_MISSING')
        raw = read(candidates[0]); compiler_info[language] = pin(candidates[0])
        matches = re.findall(rb'^set\(CMAKE_' + language.encode() + rb'_COMPILER "([^"\r\n]+)"\)', raw, re.M)
        require(len(matches) == 1, 'TARGET_COMPILER_PATH_MISSING')
        name = matches[0].decode()
        compiler_files[language] = {'path': name, **pin(safe(name))}
    projects = sorted((staged / 'out/build/vs2026').rglob('MapServer.vcxproj'))
    require(len(projects) == 1, 'TARGET_GENERATED_PROJECT_MISSING')
    project = read(projects[0])
    sdk_versions = sorted(set(v.decode() for v in re.findall(rb'<WindowsTargetPlatformVersion>([^<]+)</WindowsTargetPlatformVersion>', project)))
    require(len(sdk_versions) == 1 and re.fullmatch(r'10\.[0-9.]+', sdk_versions[0]), 'TARGET_WINDOWS_SDK_SELECTION')
    dependencies = dependency_manifest(staged)
    toolchain = toolchain_manifest(projects[0], cache_fields, sdk_versions[0], compiler_files)
    files = {'MapServer.exe': binary, 'CMakeCache.txt': cache, STAGE: staged / STAGE,
        'map-startup-inputs.json': safe(input_dir) / 'map-startup-inputs.json',
        'map-startup-build-input.json': staged / 'map-startup-build-input.json'}
    files.update({'source/' + n: staged / n for n in before['outputs']})
    files['generated/MapServer.vcxproj'] = projects[0]
    for language in ('C', 'CXX'):
        files['generated/CMake' + language + 'Compiler.cmake'] = next((staged / 'out/build/vs2026/CMakeFiles').glob('*/CMake' + language + 'Compiler.cmake'))
    artifacts = {n: pin(path) for n, path in files.items()}
    result = {'schema': 'coh-body-witness-target-compile-v1', 'build_role': ROLE,
        'source_revision': admission['head'], 'target_compiled': True, 'platform': 'Win32',
        'configuration': 'OptDebug', 'generator': 'Visual Studio 18 2026', 'compiler_cache_fields': compiler,
        'actual_compiler_files': compiler_files, 'generated_compiler_info': compiler_info,
        'windows_sdk_project_version': sdk_versions[0], 'generated_project': pin(projects[0]),
        'populated_dependency_manifest_sha256': sha(encoded(dependencies)),
        'evaluated_toolchain_manifest_sha256': sha(encoded(toolchain)),
        'compiler_parallelism_override': os.environ.get('_CL_', ''),
        'actual_runtime_executed': False, 'loaded_rows_observed': False, 'runtime_catalog_admitted': False,
        'metadata_self_attestation': False, 'actor_or_ack_authority': False,
        'original_startup_inputs': startup, 'artifacts': artifacts,
        'next_missing_prerequisite': 'Isolated execution capability with disposable database/runtime and independently established coherent selected Map/session/load-generation ownership; exact selected cache/shared-segment provenance.'}
    output.mkdir(mode=0o700)
    try:
        for n, source in files.items():
            target = output / n; target.parent.mkdir(parents=True, exist_ok=True)
            with source.open('rb') as inp, target.open('xb') as out: shutil.copyfileobj(inp, out, 1024**2)
            require(pin(target) == artifacts[n], 'TARGET_COPY_CHANGED')
        require(verify(root, staged) == (before, admission), 'TARGET_CHANGED_AFTER_BUILD')
        require(dependency_manifest(staged) == dependencies, 'TARGET_DEPENDENCIES_CHANGED')
        (output / 'build-dependency-manifest.json').write_bytes(encoded(dependencies))
        (output / 'evaluated-toolchain-manifest.json').write_bytes(encoded(toolchain))
        (output / 'checkout-source-manifest.json').write_bytes(encoded(admission))
        (output / COMPILE).write_bytes(encoded(result))
    except BaseException:
        # Keep the isolated failed output for diagnosis, never publish a receipt.
        (output / COMPILE).unlink(missing_ok=True)
        raise
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('stage', 'verify', 'record'))
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--already-staged', type=Path, required=True)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.operation == 'stage':
        require(args.metadata and not args.inputs and not args.output, 'TARGET_STAGE_ARGS')
        value = stage(args.source_root, args.already_staged, decode(read(args.metadata)))
    elif args.operation == 'verify':
        require(not any((args.metadata, args.inputs, args.output)), 'TARGET_VERIFY_ARGS')
        value, _ = verify(args.source_root, args.already_staged)
    else:
        require(args.inputs and args.output and not args.metadata, 'TARGET_RECORD_ARGS')
        value = record(args.source_root, args.already_staged, args.inputs, args.output)
    print(json.dumps({'passed': True, 'build_role': value['build_role'],
        'target_compiled': value.get('target_compiled', False), 'runtime_executed': False}))


if __name__ == '__main__':
    main()
