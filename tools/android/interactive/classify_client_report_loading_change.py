#!/usr/bin/env python3
"""Own a direct finite .33 report/helper repair without rebuilding retained native payloads.

An explicit successor marker and direct single-parent push are mandatory.
Unknown files and ambiguous ancestry continue through every historical gate.
"""
import os
from pathlib import Path
import re
import subprocess

CLIENT_REPORT_LOADING_MARKER = 'tools/android/interactive/release-client-report-loading-0.13.33.json'
CLIENT_REPORT_LOADING_PUBLICATION = 'docs/android-evidence/client-report-loading-0.13.33-publication.json'
CLIENT_REPORT_LOADING_DOCS = frozenset({
    'docs/HANDOFF.md', 'docs/COH-Atlas-Gameplay-0.13.33-testing.txt',
    'docs/android-evidence/client-report-loading-0.13.32-device-result.json',
    'docs/android-evidence/client-report-loading-0.13.33-routing.json',
    CLIENT_REPORT_LOADING_PUBLICATION,
})
CLIENT_REPORT_LOADING_ALLOWED = CLIENT_REPORT_LOADING_DOCS | frozenset({
    CLIENT_REPORT_LOADING_MARKER,
    '.github/workflows/android-client-report-loading.yml',
    'tools/android/interactive/build_client_report_loading_apk.py',
    'tools/android/interactive/qualify_client_report_loading.py',
    'tools/android/interactive/test_client_report_loading_package.py',
    'tools/android/interactive/classify_client_report_loading_change.py',
    'android/guest/atlas_beacon_package.py',
    'android/guest/kings_row_beacon_package.py',
    'android/guest/local_character_server.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientActivity.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientService.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java',
    'tools/android/interactive/test_client_report_lifecycle_java.py',
    'tools/android/interactive/test_client_report_recovery_java.py',
    'tools/android/interactive/test_client_report_controls_java.py',
    'tools/android/interactive/test_collision_input_snapshot.py',
    'tools/android/interactive/test_shared_collision_input_proof.py',
    'tools/android/interactive/test_map_startup_observation.py',
    'tools/android/interactive/test_profile_failure_presentation.py',
    'tools/android/interactive/test_storage_ui.py',
    'tools/android/interactive/test_storage_recovery_ui.py',
    'tools/android/interactive/test_fresh_profile_recovery.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/classify_client_map_startup_change.py',
    'tools/qualify_map_startup_prerequisites.py',
    'tools/test_qualify_map_startup_prerequisites.py',
    '.github/workflows/map-startup-prerequisites.yml',
})

def client_report_loading_owned(event, before, head, parent, names):
    paths = set(names)
    direct = (event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and re.fullmatch('[0-9a-f]{40}', head or '')
        and re.fullmatch('[0-9a-f]{40}', parent or '')
        and before != '0'*40 and head != '0'*40
        and before == parent and head != before and bool(paths)
        and all(type(name) is str for name in paths))
    return bool(direct and ((paths <= CLIENT_REPORT_LOADING_ALLOWED
        and CLIENT_REPORT_LOADING_MARKER in paths)
        or (paths <= CLIENT_REPORT_LOADING_DOCS and CLIENT_REPORT_LOADING_PUBLICATION in paths)))


