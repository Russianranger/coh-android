#!/usr/bin/env python3
"""Build COH Atlas Gameplay 0.13.70 with the ARM64 client option.

User approval (2026-10-26, Claude lead session): build and sign this APK for the
M5 Thor play test. It is an in-place update of the installed 0.13.36 app: same
application ID and the same retained development signer, so the app's saved
character, private database, imported assets and Wine prefix are kept.

Inputs are pinned:
- the public 0.13.36 donor APK;
- the ARM64 client package from the explicitly selected runtime qualification;
- optionally, both MapServer metrics packages from that same native build,
  bound to retained creation/reopen execution in that runtime qualification;
- the retained signing identity (run 36731428735).

Changes against the donor:
- classes.dex is recompiled from this repository's app sources (0.13.36
  sources plus the reviewed M4 ARM64-option diff);
- version metadata becomes 0.13.70 / 85, and the binary manifest is checked
  to differ only in its version fields;
- stage_app_assets adds the ARM64 client, its guest helpers and the manifest
  entries and the explicitly listed guest helpers;
- with metrics enabled, the authenticated modern MapServer replaces only the
  donor's MapServer; its host build checks do not claim Thor execution.

Every other APK member must stay byte-identical to the donor. x86 remains the
default client.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import importlib.util

import stage_app_assets
import server_pipeline

ROOT = Path(__file__).resolve().parents[2]
APP_ID = 'io.github.russianranger.cohclientinteractive'
ANDROID = '{http://schemas.android.com/apk/res/android}'
VERSION_NAME, VERSION_CODE = '0.13.70', 85
APK_NAME = 'COH-Atlas-Gameplay-0.13.70.apk'
DONOR_NAME = 'COH-Atlas-Gameplay-0.13.36.apk'
DONOR_RELEASE = 'coh-atlas-gameplay-v0.13.36'
DONOR_ASSET_ID = 635975286
DONOR_APK = {'bytes': 42076692, 'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
DONOR_COMMIT = '3570430cefdb'  # release target prefix, informational
SIGNER = '92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282'
ALIAS = 'coh-client-interactive'
# The donor DEX's exact 24-source set (class list of the 0.13.36 classes.dex).
HELPERS = ('TarExtractor', 'DeviceHosts', 'DiagnosticOutcome', 'DiagnosticReports', 'CleanupGuard',
           'DiagnosticRuntime', 'DbServerAcceptance', 'AssetPackArchive', 'AssetPackStore', 'SetupMemoryGuard')
EXTRA_SOURCES = ('android/zoning/src/main/java/io/github/russianranger/cohclientinteractive/ClientZoning.java',
                 'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java',
                 'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientSocketRecovery.java')
# Runtime payloads the ARM64 option may add or change. Everything else is retained.
ADDED_RUNTIME = frozenset({'armport-client.zip', 'armport_client_package.py', 'armport_interactive.py',
                           'client_stdio.py', 'server_metrics.py',
                           # 0.13.54: on-demand zone supervisor, inert unless COH_EXTERNAL_MAPS=1
                           # and the external-maps DbServer layer is installed.
                           'external_map_supervisor.py',
                           # 0.13.55: the game's own zone travel policy (COH_STOCK_TRAVEL=1).
                           'zone_travel.py', 'zone_index.py',
                           # 0.13.65: zone beacon graphs for the shared zone tree (inert without them).
                           'zone_beacon_package.py',
                           # 0.13.67: launch receipts (an unchanged install step is not re-checked leaf by leaf).
                           'launch_receipts.py'})
CHANGED_RUNTIME = frozenset({'diagnostic.py', 'character_server_data_cache.py', 'client_login_diagnostic.py', 'character_creation_diagnostic.py', 'local_login_server.py', 'local_character_server.py', 'character_zoning.py',
                             'character_zoning_scheduler.py', 'client_visual_assets.py', 'zone_asset_package.py',
                             'native_training_save.py',
                             # 0.13.55: the reopen budget accepts any static zone in stock travel.
                             'character_reopen_diagnostic.py', 'character_session_budget.py',
                             # 0.13.59: the reopen's early client retry keeps no zone server
                             # when the zone starts at Enter Game.
                             'client_attempt_retry.py',
                             # 0.13.62: the contact and task log patterns follow the character's own name.
                             'stationary_contact_evidence.py', 'task_gate_evidence.py',
                             'runtime-manifest.json', 'client-manifest.json',
                             'game_diagnostic.py', 'game_device_diagnostic.py', 'atlas_beacon_package.py',
                             'native_map_startup_contract.py', 'native_monorail_contract.py',
                             'server_cache_package.py', 'server_fx_catalog.py', 'server_animation_package.py'})
SERVER_ADDED_RUNTIME = frozenset({'armport_server_metrics_contract.py', 'armport-server-metrics-binding.json'})
SERVER_CHANGED_RUNTIME = frozenset({'game-package.tar.gz'})
# --server-option (0.13.52): the donor game archive stays byte-identical and the
# admitted Thor server is added beside it, used only when the launch option asks.
SERVER_OPTION_ADDED_RUNTIME = SERVER_ADDED_RUNTIME | {'game-package-trusted.tar.gz'}
REVIEWED_JAVA_CHANGES = frozenset({
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientActivity.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAudio.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientInput.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientService.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSurface.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/InteractiveRfbClient.java'})
# Overlay menu and controller mapping (ported from the owner's TRASC launcher); Java only, no resources.
ADDED_JAVA_SOURCES = frozenset({
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientOverlayPosition.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ControllerBridge.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ControllerDialog.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ControllerInput.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ControllerManager.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ControllerProfile.java'})


# 0.13.69: a second PRoot build (android/native/proot patch 0004) beside the donor's. The
# donor's libproot.so stays byte-identical and stays the default; the launch option "Graphics
# calls skip the system-call monitor" starts this build with PROOT_IOCTL_COMMANDS_ONLY=1.
# Its build receipt, licence files and complete corresponding source travel in the APK.
PROOT_IOCTL_LIBRARIES = {'lib/arm64-v8a/libproot-ioctl.so': 'libproot.so',
                         'lib/arm64-v8a/libproot-ioctl-loader.so': 'libproot-loader.so'}
PROOT_IOCTL_ASSETS = 'assets/proot-ioctl/'
PROOT_RECEIPT, PROOT_SOURCES = 'proot-build-receipt.json', 'proot-corresponding-sources.tar.gz'


def proot_recipe():
    """tools/android/build_proot.py of this checkout (its pins and patch list)."""
    path = ROOT / 'tools/android/build_proot.py'
    spec = importlib.util.spec_from_file_location('coh_build_proot', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def proot_ioctl_members(directory, donor_members):
    """({APK member: file}, report record) for an android-arm64 output of build_proot.py.

    The receipt must describe this checkout's recipe exactly: the pinned PRoot commit and tree,
    the NDK, every patch byte for byte (0004 among them) and the build script itself; the two
    programs, the source bundle and the licence files must be the files it records.
    """
    recipe, recipe_path = proot_recipe()
    directory = Path(directory)
    receipt_path = directory / PROOT_RECEIPT
    require(receipt_path.is_file() and receipt_path.stat().st_size <= 1024 * 1024, 'PRoot build receipt missing')
    receipt = json.loads(receipt_path.read_text())
    require(receipt.get('schema_version') == 1 and receipt.get('target') == 'android-arm64'
            and receipt.get('status') == 'native_built_runtime_unverified', 'Not a built Android PRoot receipt')
    require(receipt.get('source_commit') == recipe.PROOT_COMMIT and receipt.get('source_tree') == recipe.PROOT_TREE
            and receipt.get('ndk_version') == recipe.NDK_VERSION and receipt.get('android_api') == 26
            and receipt.get('max_page_size') == 16384 and receipt.get('talloc_linkage') == 'static',
            'PRoot build differs from the pinned source or toolchain')
    require('0004-ioctl-command-filter.patch' in recipe.PATCH_NAMES and receipt.get('ioctl_command_filter_patch') is True
            and '0005-stop-counts-getsockopt-filter.patch' in recipe.PATCH_NAMES and receipt.get('stop_counts_patch') is True
            and receipt.get('patches') == {name: pin(recipe.PATCHES / name) for name in recipe.PATCH_NAMES}
            and receipt.get('recipe_sha256') == pin(recipe_path)['sha256'],
            'PRoot build did not use this checkout\'s patches and recipe')
    members = {}
    files = receipt.get('files')
    require(isinstance(files, dict) and set(files) == set(PROOT_IOCTL_LIBRARIES.values()), 'Unexpected PRoot outputs')
    for member, name in PROOT_IOCTL_LIBRARIES.items():
        path = directory / name
        require(path.is_file() and not path.is_symlink()
                and {key: files[name].get(key) for key in ('bytes', 'sha256')} == pin(path)
                and files[name].get('elf_machine') == 'aarch64', 'PRoot output differs from its receipt: ' + name)
        require(member not in donor_members, 'Donor already holds ' + member)
        members[member] = path
    sources = receipt.get('corresponding_sources')
    require(isinstance(sources, dict) and sources.get('file') == PROOT_SOURCES
            and {key: sources.get(key) for key in ('bytes', 'sha256')} == pin(directory / PROOT_SOURCES),
            'PRoot corresponding source bundle differs from its receipt')
    licenses = receipt.get('license_files')
    require(isinstance(licenses, dict) and 'PRoot-COPYING' in licenses and len(licenses) <= 16
            and all(re.fullmatch(r'[A-Za-z0-9._-]{1,64}', name) for name in licenses), 'PRoot licence files missing')
    members[PROOT_IOCTL_ASSETS + PROOT_RECEIPT] = receipt_path
    members[PROOT_IOCTL_ASSETS + PROOT_SOURCES] = directory / PROOT_SOURCES
    for name, record in licenses.items():
        path = directory / 'licenses' / name
        require(path.is_file() and not path.is_symlink() and pin(path) == record, 'PRoot licence file differs: ' + name)
        members[PROOT_IOCTL_ASSETS + 'licenses/' + name] = path
    donor = donor_members.get('lib/arm64-v8a/libproot.so')
    record = {'format': 2, 'switch': 'PROOT_IOCTL_COMMANDS_ONLY=1', 'default': True,
              'switches': ['PROOT_IOCTL_COMMANDS_ONLY=1', 'PROOT_GETSOCKOPT_PEERCRED_ONLY=1', 'PROOT_STOP_COUNTS=<file>'],
              'launch_option': 'proot-call-filter', 'members': {member: pin(path) for member, path in sorted(members.items())},
              'source_commit': receipt['source_commit'], 'patches': receipt['patches'],
              'compiler': receipt.get('compiler'), 'ndk_version': receipt['ndk_version'],
              'donor_libproot_retained': donor,
              # Thor 0.13.69 (20261113-013835, 20261113-015905): the 0004 build ran two launches, probe
              # listed_commands_only. This build adds 0005 and has not run on a device.
              'device_validated': False, 'previous_build_device_validated': '0.13.69'}
    return members, record


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest_bytes(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def pin(path):
    require(path.is_file() and not path.is_symlink(), 'Regular file required: ' + str(path))
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def run(*command, env=None):
    result = subprocess.run([str(part) for part in command], capture_output=True, text=True, env=env)
    require(result.returncode == 0, 'Command failed: ' + ' '.join(map(str, command[:3])) + '\n'
            + result.stdout[-2000:] + result.stderr[-2000:])
    return result.stdout


def java_sources(main_dir, generated):
    sources = sorted((main_dir / 'java').rglob('*.java'))
    for path in sources:
        packages = re.findall(r'^package\s+([A-Za-z0-9_.]+)\s*;', path.read_text(), re.M)
        require(len(packages) == 1 and (packages[0] == APP_ID or packages[0].startswith(APP_ID + '.')),
                'Unexpected Java package: ' + path.name)
    sources += sorted(generated.rglob('*.java'))
    sources.append(ROOT / 'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java')
    diagnostic = ROOT / 'android/app/src/main/java/io/github/russianranger/cohdiagnostic'
    sources += [diagnostic / (name + '.java') for name in HELPERS]
    sources += [ROOT / name for name in EXTRA_SOURCES]
    # The donor's 24 sources plus ClientAudio.java (game audio bridge, 0.13.53) and the
    # overlay/controller sources.
    added = {p.relative_to(ROOT).as_posix() for p in sources if p.is_relative_to(ROOT)} & ADDED_JAVA_SOURCES
    require(added == ADDED_JAVA_SOURCES, 'Overlay/controller sources missing')
    require(len([p for p in sources if not p.is_relative_to(generated)]) == 25 + len(ADDED_JAVA_SOURCES),
            'Donor 24-source set plus ClientAudio and overlay/controller sources differs')
    require(any(p.name == 'ClientAudio.java' for p in sources), 'Game audio bridge source missing')
    require(len(sources) == len(set(sources)) and all(p.is_file() and not p.is_symlink() for p in sources),
            'Missing, linked or duplicated Java source')
    return sources


def versioned_manifest(source, destination):
    tree = ET.parse(source)
    root = tree.getroot()
    require(root.tag == 'manifest' and root.get('package') == APP_ID, 'Source manifest identity differs')
    root.set(ANDROID + 'versionName', VERSION_NAME)
    root.set(ANDROID + 'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', ANDROID[1:-1])
    tree.write(destination, encoding='utf-8', xml_declaration=True)


def normalized_manifest(apk, build_tools):
    output = run(build_tools / 'aapt2', 'dump', 'xmltree', apk, '--file', 'AndroidManifest.xml')
    lines = output.splitlines()
    require(sum(':versionCode(' in l for l in lines) == 1 and sum(':versionName(' in l for l in lines) == 1,
            'Binary manifest version metadata missing or duplicated')
    result = []
    for line in lines:
        line = re.sub(r' \(line=\d+\)', '', line)
        if ':versionCode(' in line or ':versionName(' in line:
            line = line.split('=')[0] + '=VERSION'
        result.append(line)
    return result


def verify_signature(apk, build_tools):
    output = run('java', '-jar', build_tools / 'lib/apksigner.jar', 'verify', '--verbose', '--print-certs', apk)
    require('Verified using v2 scheme (APK Signature Scheme v2): true' in output
            and 'Verified using v3 scheme (APK Signature Scheme v3): true' in output, 'v2/v3 signature required')
    certs = re.findall(r'Signer #1 certificate SHA-256 digest: ([0-9a-f]{64})', output)
    require(certs == [SIGNER], 'Signer certificate differs from the installed app lineage')
    return certs[0]


def members(apk):
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate APK member')
        return {name: digest_bytes(archive.read(name)) for name in names if not name.endswith('/')}


def build(args):
    require(re.fullmatch('[0-9a-f]{40}', args.repository_commit), 'Exact repository commit required')
    server_directory = getattr(args, 'server_metrics', None)
    runtime_run_id = getattr(args, 'runtime_run_id', None)
    baseline_directory = getattr(args, 'baseline_root', None)
    require((server_directory is None) == (runtime_run_id is None) == (baseline_directory is None),
            'Metrics APK requires its exact runtime qualification artifact, run and pinned baseline')
    baseline = server_pipeline.native.baseline_root(baseline_directory) if server_directory else ROOT
    server_qualification = (server_pipeline.read_qualification(server_directory,
        args.repository_commit, runtime_run_id, baseline) if server_directory is not None else None)
    server_option = bool(getattr(args, 'server_option', False))
    require(not server_option or server_qualification, 'The server option requires a qualified metrics server')
    if server_option:
        added_runtime = ADDED_RUNTIME | SERVER_OPTION_ADDED_RUNTIME
        changed_runtime = CHANGED_RUNTIME
    else:
        added_runtime = ADDED_RUNTIME | (SERVER_ADDED_RUNTIME if server_qualification else frozenset())
        changed_runtime = CHANGED_RUNTIME | (SERVER_CHANGED_RUNTIME if server_qualification else frozenset())
    dbserver = getattr(args, 'external_maps_dbserver', None)
    if dbserver is not None:
        # On-demand zones (inert until the supervisor enables it): only the two DbServer payloads change.
        changed_runtime = changed_runtime | frozenset(stage_app_assets.DBSERVER_PAYLOADS)
    zone_graphs = getattr(args, 'zone_beacons', None)
    if zone_graphs is not None:
        # 0.13.65: each carried zone graph adds exactly its archive, manifest and lock.
        zone_graphs = (zone_graphs, args.zone_beacons_run_json)
        added_runtime = added_runtime | frozenset(stage_app_assets.zone_beacons(*zone_graphs)[0])
    navigation = getattr(args, 'navigation_maps', None)
    if navigation is not None:
        # Every zone's navigation map (owner, 2026-11-09): the APK adds only the pack's descriptor.
        navigation = (navigation, args.navigation_maps_run_json)
        added_runtime = added_runtime | frozenset(stage_app_assets.navigation_maps(*navigation)[0])
    require(pin(args.donor_apk) == DONOR_APK, 'Donor 0.13.36 APK bytes differ from the public release')
    proot_directory = getattr(args, 'proot_ioctl', None)
    require(args.output.name == APK_NAME and not args.output.exists(), 'Fresh output required')
    for tool in (args.android_jar, args.build_tools / 'aapt2', args.build_tools / 'zipalign',
                 args.build_tools / 'lib/d8.jar', args.build_tools / 'lib/apksigner.jar'):
        require(tool.is_file(), 'Missing Android SDK tool: ' + str(tool))
    donor_signer = verify_signature(args.donor_apk, args.build_tools)
    password = 'env:' + args.password_env
    require(os.environ.get(args.password_env), 'Signing password environment variable is empty')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    donor_members = members(args.donor_apk)
    proot_members, proot_record = (proot_ioctl_members(proot_directory, donor_members)
                                   if proot_directory is not None else ({}, None))
    with tempfile.TemporaryDirectory(prefix='coh-thor-apk-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        # 1. Donor runtime assets, then the reviewed ARM64 staging.
        donor_runtime = work / 'donor-runtime'
        donor_runtime.mkdir()
        with zipfile.ZipFile(args.donor_apk) as archive:
            for name in donor_members:
                path = PurePosixPath(name)
                if name.startswith('assets/runtime/'):
                    require(len(path.parts) == 3 and '\\' not in name, 'Unsafe donor runtime member')
                    (donor_runtime / path.name).write_bytes(archive.read(name))
        pack = json.loads((donor_runtime / 'asset-pack-manifest.json').read_text())
        external = {name.split('/', 1)[1]: record for name, record in pack['files'].items()
                    if name.startswith('runtime/')}
        runtime_files = json.loads((donor_runtime / 'runtime-manifest.json').read_text())['files']
        require({n for n in runtime_files if not (donor_runtime / n).exists()} == set(external),
                'Unpackaged runtime payloads must be exactly the external asset-pack runtime files')
        staged = work / 'staged-runtime'
        armport = stage_app_assets.stage(donor_runtime, args.armport, staged, args.repository_commit, external,
            server_archive=(server_directory / server_pipeline.PACKAGES['thor_certified_startup']
                            if server_qualification else None),
            server_variant='thor_certified_startup' if server_qualification else None,
            server_run_id=server_qualification['native_build_run_id'] if server_qualification else None,
            upstream_root=baseline, server_option=server_option, dbserver=dbserver, zone_graphs=zone_graphs,
            navigation=navigation)
        staged_manifest = json.loads((staged / 'runtime-manifest.json').read_text())
        dbserver_record = staged_manifest.get(stage_app_assets.EXTERNAL_MAPS_KEY)
        zone_record = staged_manifest.get(stage_app_assets.ZONE_BEACONS_KEY)
        require((zone_record is not None) == (zone_graphs is not None), 'Zone graph record mismatch')
        navigation_record = staged_manifest.get(stage_app_assets.NAVIGATION_MAPS_KEY)
        require((navigation_record is not None) == (navigation is not None), 'Navigation map record mismatch')
        require((dbserver_record is not None) == (dbserver is not None), 'External map DbServer record mismatch')
        if server_qualification:
            require(armport['client_run_id'] == armport['data_run_id'] == server_qualification['native_build_run_id'],
                    'APK client/data and metrics servers came from different builds')
        staged_names = {p.name for p in staged.iterdir()}
        donor_names = {p.name for p in donor_runtime.iterdir()}
        require(staged_names - donor_names == added_runtime and donor_names <= staged_names,
                'Unexpected runtime additions or removals: ' + repr(sorted(staged_names ^ donor_names)))
        changed = sorted(name for name in donor_names if pin(staged / name) != pin(donor_runtime / name))
        require(set(changed) <= changed_runtime, 'Unreviewed runtime payload changed: ' + repr(changed))
        # 2. Shell: versioned manifest, retained resources, recompiled DEX.
        manifest = work / 'AndroidManifest.xml'
        main_dir = ROOT / 'android/interactive/src/main'
        versioned_manifest(main_dir / 'AndroidManifest.xml', manifest)
        resources, unsigned = work / 'resources.zip', work / 'unsigned.apk'
        classes, generated, dex = work / 'classes', work / 'generated', work / 'dex'
        for folder in (classes, generated, dex):
            folder.mkdir()
        run(args.build_tools / 'aapt2', 'compile', '--dir', main_dir / 'res', '-o', resources)
        run(args.build_tools / 'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest,
            '--min-sdk-version', '26', '--target-sdk-version', '35', '--java', generated, resources, '-o', unsigned)
        shell = members(unsigned)
        for name, record in shell.items():
            if name != 'AndroidManifest.xml':
                require(donor_members.get(name) == record, 'Android resource differs from donor: ' + name)
        sources = java_sources(main_dir, generated)
        source_pins = {p.relative_to(ROOT).as_posix(): pin(p) for p in sources if p.is_relative_to(ROOT)}
        run('java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-cp', args.android_jar,
            '-d', classes, *sources)
        jar = work / 'classes.jar'
        with zipfile.ZipFile(jar, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob('*.class')):
                archive.write(path, path.relative_to(classes).as_posix())
        run('java', '-cp', args.build_tools / 'lib/d8.jar', 'com.android.tools.r8.D8', '--min-api', '26',
            '--lib', args.android_jar, '--output', dex, jar)
        require({p.name for p in dex.iterdir()} == {'classes.dex'}, 'Unexpected DEX output')
        # 3. Assemble: donor non-shell members (runtime from staging), new DEX.
        with zipfile.ZipFile(args.donor_apk) as donor, zipfile.ZipFile(unsigned, 'a') as archive:
            for info in donor.infolist():
                name = info.filename
                if (name in shell or name == 'classes.dex' or name.startswith('META-INF/')
                        or name.startswith('assets/runtime/') or name.endswith('/')):
                    continue
                archive.writestr(info, donor.read(name), compress_type=info.compress_type)
            runtime_compression = {i.filename: i.compress_type for i in donor.infolist()}
            for path in sorted(staged.iterdir()):
                name = 'assets/runtime/' + path.name
                compress = runtime_compression.get(name, zipfile.ZIP_STORED if path.suffix == '.zip'
                                                   else zipfile.ZIP_DEFLATED)
                archive.write(path, name, compress_type=compress)
            for name, path in sorted(proot_members.items()):
                archive.write(path, name, compress_type=zipfile.ZIP_DEFLATED)
            archive.write(dex / 'classes.dex', 'classes.dex', compress_type=zipfile.ZIP_DEFLATED)
        aligned, signed = work / 'aligned.apk', work / 'signed.apk'
        run(args.build_tools / 'zipalign', '-f', '-p', '4', unsigned, aligned)
        run('java', '-jar', args.build_tools / 'lib/apksigner.jar', 'sign', '--ks', args.keystore,
            '--ks-key-alias', ALIAS, '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = verify_signature(signed, args.build_tools)
        run(args.build_tools / 'zipalign', '-c', '-p', '4', signed)
        badging = run(args.build_tools / 'aapt2', 'dump', 'badging', signed)
        require(re.search(r"^package: name='%s' versionCode='%d' versionName='%s'" % (
            re.escape(APP_ID), VERSION_CODE, re.escape(VERSION_NAME)), badging, re.M), 'Badging identity differs')
        require(normalized_manifest(signed, args.build_tools) == normalized_manifest(args.donor_apk, args.build_tools),
                'Binary manifest changed beyond version metadata')
        # 4. Exact member accounting against the donor.
        final = members(signed)
        retained, replaced, added = [], [], []
        for name, record in final.items():
            if name.startswith('META-INF/'):
                continue
            if name not in donor_members:
                added.append(name)
            elif donor_members[name] == record:
                retained.append(name)
            else:
                replaced.append(name)
        removed = sorted(n for n in donor_members if n not in final and not n.startswith('META-INF/'))
        require(not removed, 'Donor members removed: ' + repr(removed))
        require(set(added) == {'assets/runtime/' + n for n in added_runtime} | set(proot_members),
                'Unexpected added members: ' + repr(added))
        for name, path in proot_members.items():
            require(final[name] == pin(path), 'Second PRoot build member differs: ' + name)
        require(final['lib/arm64-v8a/libproot.so'] == donor_members['lib/arm64-v8a/libproot.so']
                and final['lib/arm64-v8a/libproot-loader.so'] == donor_members['lib/arm64-v8a/libproot-loader.so'],
                'The default PRoot must stay the donor\'s')
        require(set(replaced) <= {'classes.dex', 'AndroidManifest.xml'} | {'assets/runtime/' + n for n in changed_runtime},
                'Unreviewed replaced members: ' + repr(replaced))
        for name in added_runtime | changed_runtime:
            if (staged / name).exists():
                require(final['assets/runtime/' + name] == pin(staged / name), 'Staged payload differs: ' + name)
        shutil.copyfile(signed, args.output)
    report = {
        'format': 1, 'apk': APK_NAME, **pin(args.output), 'application_id': APP_ID,
        'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'repository_commit': args.repository_commit,
        'donor': {'apk': DONOR_NAME, 'release': DONOR_RELEASE, 'release_asset_id': DONOR_ASSET_ID, **DONOR_APK,
                  'signer_certificate_sha256': donor_signer},
        'armport_client': armport, 'armport_package': pin(args.armport),
        'signer_certificate_sha256': certificate, 'signing_key_created': False,
        'signature_verified': True, 'binary_manifest_version_only_verified': True,
        'retained_members': len(retained), 'replaced_members': sorted(replaced), 'added_members': sorted(added),
        'changed_runtime_payloads': changed, 'java_sources': source_pins,
        'default_client_architecture': 'x86', 'arm64_client_selectable': True,
        'installation': 'In-place update of COH Atlas Gameplay 0.13.36 (same application ID and signer). '
                        'Keeps the saved character, private database, imported assets and Wine prefix.',
        'device_validated': False, 'gameplay_validated': False, 'm5_complete': False,
    }
    if dbserver_record is not None:
        report['external_maps_dbserver'] = dict(dbserver_record,
                                                build_run=getattr(args, 'external_maps_build_run', None))
    if zone_record is not None:
        report['zone_beacons'] = zone_record
    if navigation_record is not None:
        report['navigation_map_pack'] = navigation_record
    if proot_record is not None:
        report['proot_ioctl_filter'] = proot_record
    if server_qualification:
        report['server_metrics_qualification'] = server_qualification
        report['server_metrics_variant'] = 'thor_certified_startup'
        report['server_metrics_runtime_validated'] = False
        report['server_metrics_placement'] = ('launch_option_second_archive' if server_option
                                              else 'replaces_game_archive')
    report_path = args.output.with_name('thor-apk-build-report.json')
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    args.output.with_suffix('.apk.sha256').write_text(report['sha256'] + '  ' + APK_NAME + '\n')
    print(json.dumps({k: report[k] for k in ('apk', 'bytes', 'sha256', 'version_name', 'version_code',
                                              'signer_certificate_sha256', 'replaced_members', 'added_members')}))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('donor-apk', 'armport', 'android-jar', 'build-tools', 'keystore', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
    parser.add_argument('--server-metrics', type=Path)
    parser.add_argument('--runtime-run-id', type=int)
    parser.add_argument('--baseline-root', type=Path)
    parser.add_argument('--server-option', action='store_true',
                        help='Carry the metrics server as an opt-in second archive (default server unchanged)')
    parser.add_argument('--external-maps-dbserver', type=Path,
                        help='On-demand zone DbServer package (armport-external-maps-dbserver artifact); inert by default')
    parser.add_argument('--external-maps-run-json', type=Path,
                        help='The armport-external-maps-dbserver run that built --external-maps-dbserver')
    parser.add_argument('--zone-beacons', type=Path,
                        help='Zone graph package directory (armport-zone-beacons artifact): pets and NPCs path there')
    parser.add_argument('--zone-beacons-run-json', type=Path,
                        help='The armport-zone-beacons run that generated --zone-beacons')
    parser.add_argument('--proot-ioctl', type=Path,
                        help='android-arm64 output of tools/android/build_proot.py (patch 0004): added as a second '
                             'PRoot build for the launch option; the donor build stays the default')
    parser.add_argument('--navigation-maps', type=Path,
                        help='Navigation map pack descriptor and report (armport-zone-beacons pack artifact)')
    parser.add_argument('--navigation-maps-run-json', type=Path,
                        help='The armport-zone-beacons pack run that built --navigation-maps')
    args = parser.parse_args()
    for key in ('donor_apk', 'armport', 'android_jar', 'build_tools', 'keystore', 'output'):
        setattr(args, key, getattr(args, key).absolute())
    if args.server_metrics is not None:
        args.server_metrics = args.server_metrics.absolute()
    if (args.external_maps_dbserver is None) != (args.external_maps_run_json is None):
        parser.error('--external-maps-dbserver and --external-maps-run-json go together')
    if (args.zone_beacons is None) != (args.zone_beacons_run_json is None):
        parser.error('--zone-beacons and --zone-beacons-run-json go together')
    if (args.navigation_maps is None) != (args.navigation_maps_run_json is None):
        parser.error('--navigation-maps and --navigation-maps-run-json go together')
    if args.proot_ioctl is not None:
        args.proot_ioctl = args.proot_ioctl.absolute()
    if args.navigation_maps is not None:
        args.navigation_maps, args.navigation_maps_run_json = (args.navigation_maps.absolute(),
                                                               args.navigation_maps_run_json.absolute())
    if args.zone_beacons is not None:
        args.zone_beacons, args.zone_beacons_run_json = args.zone_beacons.absolute(), args.zone_beacons_run_json.absolute()
    if args.external_maps_dbserver is not None:
        args.external_maps_dbserver = args.external_maps_dbserver.absolute()
        args.external_maps_build_run = stage_app_assets.external_maps_build_run(
            args.external_maps_run_json, args.external_maps_dbserver)
    build(args)


if __name__ == '__main__':
    main()
