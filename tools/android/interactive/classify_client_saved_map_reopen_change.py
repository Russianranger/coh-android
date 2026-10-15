#!/usr/bin/env python3
"""Own a direct finite .34 saved-map/report/cache repair without rebuilding retained native payloads.

An explicit successor marker and direct single-parent push are mandatory.
Unknown files and ambiguous ancestry continue through every historical gate.
"""
import os
from pathlib import Path
import re
import subprocess

CLIENT_SAVED_MAP_REOPEN_MARKER = 'tools/android/interactive/release-client-saved-map-reopen-0.13.34.json'
CLIENT_SAVED_MAP_REOPEN_PUBLICATION = 'docs/android-evidence/client-saved-map-reopen-0.13.34-publication.json'
CLIENT_SAVED_MAP_REOPEN_DOCS = frozenset({
    'docs/HANDOFF.md', 'docs/COH-Atlas-Gameplay-0.13.34-testing.txt',
    'docs/COH-MAP-CACHE-CONTINUATION-0.13.34.md',
    'docs/android-evidence/client-report-loading-0.13.33-publication.json',
    'docs/android-evidence/coh-continuation-recovery-0.13.34.json',
    'docs/android-evidence/client-saved-map-reopen-0.13.34-routing.json',
    CLIENT_SAVED_MAP_REOPEN_PUBLICATION,
})
CLIENT_SAVED_MAP_REOPEN_ALLOWED = CLIENT_SAVED_MAP_REOPEN_DOCS | frozenset({
    CLIENT_SAVED_MAP_REOPEN_MARKER,
    '.github/workflows/android-client-saved-map-reopen.yml',
    'tools/android/interactive/build_client_saved_map_reopen_apk.py',
    'tools/android/interactive/qualify_client_saved_map_reopen.py',
    'tools/android/interactive/test_client_saved_map_reopen_package.py',
    'tools/android/interactive/classify_client_saved_map_reopen_change.py',
    'tools/android/interactive/classify_client_animation_repair_change.py',
    'tools/android/interactive/classify_client_profile_recovery_change.py',
    'tools/android/interactive/classify_client_map_startup_change.py',
    'tools/android/interactive/test_classify_storage_cleanup_change.py',
    'android/guest/character_zoning.py',
    'android/guest/character_server_data_cache.py',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientActivity.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientService.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java',
    'tools/android/interactive/test_client_report_lifecycle_java.py',
    'tools/android/interactive/test_client_report_recovery_java.py',
    'tools/android/interactive/test_client_report_controls_java.py',
    'tools/android/interactive/test_completed_guest_report_java.py',
    'tools/android/interactive/test_character_zoning.py',
    'tools/android/interactive/test_server_worktree_reuse.py',
    'tools/android/interactive/test_saved_map_startup.py',
    'tools/android/interactive/test_saved_map_window_java.py',
    'tools/android/interactive/test_saved_map_postgresql.py',
})

def client_saved_map_reopen_owned(event, before, head, parent, names):
    paths = set(names)
    direct = (event == 'push' and re.fullmatch('[0-9a-f]{40}', before or '')
        and re.fullmatch('[0-9a-f]{40}', head or '')
        and re.fullmatch('[0-9a-f]{40}', parent or '')
        and before != '0'*40 and head != '0'*40
        and before == parent and head != before and bool(paths)
        and all(type(name) is str for name in paths))
    return bool(direct and ((paths <= CLIENT_SAVED_MAP_REOPEN_ALLOWED
        and CLIENT_SAVED_MAP_REOPEN_MARKER in paths)
        or (paths <= CLIENT_SAVED_MAP_REOPEN_DOCS and CLIENT_SAVED_MAP_REOPEN_PUBLICATION in paths)))
