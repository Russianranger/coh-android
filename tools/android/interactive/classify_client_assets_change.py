#!/usr/bin/env python3
"""Route the explicit .28 asset/monorail lane away from historical native builds.

This is only a workflow owner selector. Unknown paths, dispatches, ambiguous
history and unrelated native edits still require the legacy gates. The .28
pipeline runs all retained host suites, the new MapServer native fixtures,
beacon generation, payload/signature qualification and public byte audits.
"""
import os
from pathlib import Path
import re
import subprocess

CLIENT_ASSETS_ALLOWED = frozenset({
    'docs/android-evidence/zone-assets-1.0.0-all-maps.json',
    'docs/android-evidence/zone-assets-1.0.0-publication-inputs.json',
    'docs/android-evidence/zone-assets-1.0.0-thor-errors.json',
    '.github/workflows/android-client-assets.yml',
    '.github/workflows/android-game.yml',
    '.github/workflows/android-kings-row-native.yml',
    '.github/workflows/android-map-progress.yml',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/AssetPackArchive.java',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/AssetPackStore.java',
    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/DiagnosticRuntime.java',
    'android/guest/atlas_beacon_package.py',
    'android/guest/atlas_world_assets.py',
    'android/guest/character_avatar_assets.py',
    'android/guest/character_creation_diagnostic.py',
    'android/guest/character_reopen_diagnostic.py',
    'android/guest/character_session_budget.py',
    'android/guest/character_zoning.py',
    'android/guest/client_animation_package.py',
    'android/guest/client_startup_diagnostic.py',
    'android/guest/client_visual_assets.py',
    'android/guest/game_diagnostic.py',
    'android/guest/kings_row_beacon_package.py',
    'android/guest/local_character_server.py',
    'android/guest/native_monorail_contract.py',
    'android/guest/native_monorail_events.py',
    'android/guest/server_cache_package.py',
    'android/guest/zone_asset_package.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientActivity.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSessionBudget.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/StorageAudit.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/StorageFiles.java',
    'android/zoning/src/main/java/io/github/russianranger/cohclientinteractive/ClientZoning.java',
    'assets/zones-audio-supplement-manifest.json',
    'assets/zones-audio-metadata.json',
    'assets/zones-world-supplement-manifest.json',
    'database/monorail/overlay/MapServer/src/svr/wine_monorail.c',
    'database/monorail/overlay/MapServer/src/svr/wine_monorail.h',
    'database/monorail/tests/monorail_contract.c',
    'docs/COH-0.13.27-THOR-REPORT.md',
    'docs/COH-Atlas-Gameplay-0.13.28-testing.txt',
    'docs/COH-ASSETS-0.13.28.md',
    'docs/HANDOFF.md',
    'docs/android-evidence/client-assets-0.13.28-publication.json',
    'docs/android-evidence/recovery-0.13.27-thor-20261011.json',
    'patches/kings-row-beacons/0001-host-only-kings-row-generator.patch',
    'patches/monorail/0001-monorail.patch',
    'tools/android/game/test_monorail.py',
    'tools/android/interactive/audit_kings_row_foundation.py',
    'tools/android/interactive/audit_zone_asset_coverage.py',
    'tools/android/interactive/build_client_assets_apk.py',
    'tools/android/interactive/classify_client_assets_change.py',
    'tools/android/interactive/client_assets_reuse.py',
    'tools/android/interactive/test_client_assets_reuse.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/generate_kings_row_beacons.py',
    'tools/android/interactive/package_external_assets.py',
    'tools/android/interactive/package_monorail_native.py',
    'tools/android/interactive/prepare_zones_audio_assets.py',
    'tools/android/interactive/prepare_zones_world_assets.py',
    'tools/android/interactive/qualify_client_assets.py',
    'tools/android/interactive/release-client-assets-0.13.28.json',
    'tools/android/interactive/test_asset_pack_import.py',
    'tools/android/interactive/test_character_monorail.py',
    'tools/android/interactive/test_classify_client_assets_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/test_client_assets_package.py',
    'tools/android/interactive/test_client_monorail_java.py',
    'tools/android/interactive/test_external_assets.py',
    'tools/android/interactive/test_kings_row_beacons.py',
    'tools/android/interactive/test_monorail_native_package.py',
    'tools/android/interactive/test_monorail_observer.py',
    'tools/android/interactive/test_runtime_setup_reuse.py',
    'tools/android/interactive/test_shared_asset_inputs.py',
    'tools/android/interactive/test_storage_audit.py',
    'tools/android/interactive/test_storage_files.py',
    'tools/android/interactive/test_zone_asset_package.py',
    'tools/android/interactive/test_zones_audio_assets.py',
    'tools/android/interactive/test_zones_world_assets.py',
    'tools/prepare_kings_row_beacon_generator_source.py',
    'tools/prepare_monorail_source.py',
    'tools/test_prepare_kings_row_beacon_generator_source.py',
})
CLIENT_ASSETS_MARKERS = frozenset({
    '.github/workflows/android-client-assets.yml',
    '.github/workflows/android-kings-row-native.yml',
    'tools/android/interactive/build_client_assets_apk.py',
    'tools/android/interactive/qualify_client_assets.py',
    'tools/android/interactive/classify_client_assets_change.py',
    'tools/android/interactive/release-client-assets-0.13.28.json',
    'docs/android-evidence/client-assets-0.13.28-publication.json',
})


def client_assets_owned(event,before,head,parent,names):
    paths=set(names)
    return bool(event=='push' and re.fullmatch('[0-9a-f]{40}',before or '')
        and re.fullmatch('[0-9a-f]{40}',head or '') and before!='0'*40
        and before==parent and head!=before and names and paths<=CLIENT_ASSETS_ALLOWED
        and paths & CLIENT_ASSETS_MARKERS)


def main():
    required=True
    try:
        parent=subprocess.check_output(['git','rev-parse','HEAD^'],text=True).strip()
        head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        names=subprocess.check_output(['git','diff','--name-only','-z',parent,head]).decode().rstrip('\0').split('\0')
        required=not client_assets_owned(os.environ.get('GITHUB_EVENT_NAME'),os.environ.get('COH_PUSH_BEFORE'),head,parent,names)
    except (OSError,subprocess.CalledProcessError,UnicodeError):pass
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write('legacy_native_required='+str(required).lower()+'\n')
    print('Historical native pipeline required' if required else 'Dedicated .28 source-bound native and asset pipeline owns this push')


if __name__=='__main__':main()
