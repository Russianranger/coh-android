#!/usr/bin/env python3
"""Route the finite .32 MapServer derivative and final evidence to its owner.

The new native workflow builds only the certified shipping MapServer and the
separate host-only FX observer. The publication lane consumes accepted native
artifacts and authenticates the public .31 donor. Unknown paths, non-push
events and ambiguous ancestry always retain historical qualification gates.
"""
import os
from pathlib import Path
import re
import subprocess


CLIENT_MAP_STARTUP_MARKER = 'tools/android/interactive/release-client-map-startup-0.13.32.json'
CLIENT_MAP_STARTUP_PUBLICATION = 'docs/android-evidence/client-map-startup-0.13.32-publication.json'
CLIENT_MAP_STARTUP_DOCS = frozenset({
    'docs/HANDOFF.md', 'docs/COH-Atlas-Gameplay-0.13.32-testing.txt',
    'docs/MAP_STARTUP_NAMESPACE_CERTIFICATE.md',
    'docs/android-evidence/client-map-startup-0.13.31-device-result.json',
    'docs/android-evidence/client-map-startup-0.13.32-native.json',
    CLIENT_MAP_STARTUP_PUBLICATION,
})
CLIENT_MAP_STARTUP_ALLOWED = CLIENT_MAP_STARTUP_DOCS | frozenset({
    CLIENT_MAP_STARTUP_MARKER,
    '.github/workflows/android-client-map-startup.yml',
    '.github/workflows/android-map-startup-native.yml',
    '.github/workflows/android-game.yml',
    '.github/workflows/android-map-progress.yml',
    '.github/workflows/android-atlas-game.yml',
    'android/guest/atlas_beacon_package.py',
    'android/guest/character_zoning.py',
    'android/guest/game_device_diagnostic.py',
    'android/guest/local_character_server.py',
    'android/guest/native_map_startup_contract.py',
    'android/guest/native_monorail_contract.py',
    'android/guest/server_animation_package.py',
    'android/guest/server_cache_package.py',
    'android/guest/server_fx_catalog.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java',
    'database/map-startup/overlay/Common/seq/coh_animation_certificate.h',
    'database/map-startup/tests/animation_certificate.c',
    'database/map-startup/tests/monorail_budget_contract.c',
    'tools/android/atlasgame/prepare_server_fx_catalog.py',
    'tools/android/atlasgame/prepare_server_fx_control_fixture.py',
    'tools/android/atlasgame/test_device_cleanup_lineage.py',
    'tools/android/atlasgame/test_server_fx_catalog.py',
    'tools/android/atlasgame/test_server_fx_catalog_native_proof.py',
    'tools/android/game/test_map_startup_monorail_budget.py',
    'tools/android/run_retained_host_contracts.py',
    'tools/android/interactive/build_client_map_startup_apk.py',
    'tools/android/interactive/classify_client_map_startup_change.py',
    'tools/android/interactive/map_startup_inputs.py',
    'tools/android/interactive/map_startup_proof_transport.py',
    'tools/android/interactive/package_map_startup_native.py',
    'tools/android/interactive/qualify_client_map_startup.py',
    'tools/android/interactive/qualify_full_startup_preflight.py',
    'tools/android/interactive/qualify_runtime_asset_preflight.py',
    'tools/android/interactive/test_client_map_startup_package.py',
    'tools/android/interactive/test_complete_asset_stage_acceptance.py',
    'tools/android/interactive/test_completed_guest_report_java.py',
    'tools/android/interactive/test_full_startup_preflight.py',
    'tools/android/interactive/test_kings_preparation_budgets.py',
    'tools/android/interactive/test_map_startup_native_contract.py',
    'tools/android/interactive/test_map_startup_cache_reuse.py',
    'tools/android/interactive/fixtures/monorail-game-package-0.13.31.json',
    'tools/android/interactive/test_runtime_asset_preflight.py',
    'tools/map_startup_animation_certificate.py',
    'tools/map_startup_monorail_budget.py',
    'tools/map_startup_namespace_certificate.py',
    'tools/prepare_map_startup_source.py',
    'tools/prepare_server_fx_catalog_observer_source.py',
    'tools/test_map_startup_animation_certificate.py',
    'tools/test_map_startup_monorail_budget.py',
    'tools/test_map_startup_namespace_certificate.py',
    'tools/test_prepare_server_fx_catalog_observer_source.py',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_receipt_repair_change.py',
    'tools/android/interactive/classify_client_assets_change.py',
    'tools/android/interactive/classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
})


def client_map_startup_owned(event, before, head, parent, names):
    paths = set(names)
    direct = (event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and re.fullmatch('[0-9a-f]{40}', head or '')
        and re.fullmatch('[0-9a-f]{40}', parent or '')
        and before != '0'*40 and head != '0'*40
        and before == parent and head != before and bool(paths)
        and all(type(name) is str for name in paths))
    return bool(direct and ((paths <= CLIENT_MAP_STARTUP_ALLOWED
        and CLIENT_MAP_STARTUP_MARKER in paths)
        or (paths <= CLIENT_MAP_STARTUP_DOCS and CLIENT_MAP_STARTUP_PUBLICATION in paths)))


def main():
    required = True
    try:
        parent = subprocess.check_output(['git', 'rev-parse', 'HEAD^@'], text=True).strip()
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        names = subprocess.check_output(['git', 'diff', '--name-only', '-z', parent, head]).decode().rstrip('\0').split('\0')
        from classify_client_report_loading_change import client_report_loading_owned
        from classify_client_saved_map_reopen_change import client_saved_map_reopen_owned
        from classify_client_manual_session_change import client_manual_session_owned
        from classify_client_startup_latency_change import client_startup_latency_owned
        from classify_client_zone_startup_change import client_zone_startup_owned
        context = (os.environ.get('GITHUB_EVENT_NAME'), os.environ.get('COH_PUSH_BEFORE'), head, parent, names)
        required = not (client_map_startup_owned(*context) or client_report_loading_owned(*context) or client_saved_map_reopen_owned(*context) or client_manual_session_owned(*context) or client_startup_latency_owned(*context) or client_zone_startup_owned(*context))
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        pass
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write('legacy_native_required='+str(required).lower()+'\n')
    print('Historical qualification required' if required else
        'Dedicated finite derivative qualification owns this exact push')


if __name__ == '__main__': main()
