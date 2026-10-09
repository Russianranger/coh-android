"""Replay 0.13.20's preserved Game and verified connection budget against Android gates.

Only acceptance inputs are retained from the physical Software export. Screenshots,
SQL/profile contents and process output are excluded. Identical APK/client/guest
pins are stored once; closed child processes are reduced to their exit codes. The import receipt is rebuilt
for the host harness and only its digest is rebound; its original contract stays
pinned. The launcher timestamp maps the native display event into the recorded
Android monotonic timeline, conservatively within transport tolerance.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
FIXTURE = json.loads(r'''{
  "android": {
    "character_connected_event": {
      "account": "COHLOCAL",
      "baseline_character_id": 1,
      "character_id": 1,
      "client_pid": 644,
      "existing_character_verified": true,
      "map_id": 1,
      "name": "THORHERO",
      "native_client_ready_observed": true,
      "preserved_existing_identity": true,
      "reopen_verified": true,
      "session_id": "c197815449fa49e190141c1cc6b6354b",
      "stage": "actual_client_interaction",
      "time_utc": "2026-10-08T19:03:14.929283+00:00",
      "type": "character_connected"
    },
    "character_saved_event": {
      "character_id": 1,
      "client_pid": 644,
      "committed_native_position_verified": true,
      "committed_sql_verified": true,
      "costume_preserved": true,
      "name": "THORHERO",
      "powers_preserved": true,
      "preserved_existing_identity": true,
      "recovery_requested": false,
      "recovery_verified": false,
      "reopen_verified": true,
      "session_id": "c197815449fa49e190141c1cc6b6354b",
      "stage": "actual_client_interaction",
      "time_utc": "2026-10-08T19:17:37.425873+00:00",
      "type": "character_saved"
    },
    "client_window_ended_uptime_ms": 510003208,
    "client_window_observed_uptime_ms": 508698930,
    "interaction_deadline_uptime_ms": 510001794,
    "session_budget_events": [
      {
        "account": "COHLOCAL",
        "character_id": 1,
        "client_pid": 644,
        "deadline_utc_ms": 1791487394929,
        "format": 1,
        "generated_utc_ms": 1791486194929,
        "map_id": 1,
        "movement_deadline_utc_ms": 1791487154929,
        "name": "THORHERO",
        "native_client_ready_observed": true,
        "phase": "connected",
        "reopen_verified": true,
        "revision": 1,
        "save_request_deadline_utc_ms": 1791487214929,
        "session_id": "c197815449fa49e190141c1cc6b6354b",
        "stage": "actual_client_interaction",
        "time_utc": "2026-10-08T19:03:14.929611+00:00",
        "type": "character_session_budget"
      }
    ],
    "session_id": "c197815449fa49e190141c1cc6b6354b",
    "started_uptime_ms": 508157591
  },
  "android_error": "The guest completed, but its current-session client evidence did not match this APK.",
  "app_version": "0.13.20",
  "current_apk_files": {
    "001-coh-compat.sql": {
      "bytes": 7788,
      "sha256": "443ba977cdaf3e0a5c232986339f36ca8b19845943198177aaee5f191cd7f38a"
    },
    "atlas-beacon-manifest.json": {
      "bytes": 934650,
      "sha256": "ee11bb703eed85229948b30b41277c515faf80da31ccd0436171862765ba41f4"
    },
    "atlas-beacons.zip": {
      "bytes": 16150904,
      "sha256": "0c7f602d31a438c6e67409bbb89da5d45ee3aacf13c96a50de9401d7973b2949"
    },
    "atlas-world-supplement-manifest.json": {
      "bytes": 4258210,
      "sha256": "204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86"
    },
    "atlas-world-supplement.zip": {
      "bytes": 207803201,
      "sha256": "c7ed82aaaf987410fa471e19ee2b19115ef660892a06f79e2e2401d5672b095f"
    },
    "atlas_beacon_package.py": {
      "bytes": 34541,
      "sha256": "7445774cb8df831dc9aef21e57dda03677cdf11f6e7194ed726464364e160130"
    },
    "atlas_world_assets.py": {
      "bytes": 24268,
      "sha256": "4189cff59dce2f9da6d045d754ecc1fda56a09241124f842566b1da69b5865b6"
    },
    "character-avatar-defaults-manifest.json": {
      "bytes": 28554,
      "sha256": "2a96ff8fb24b686502d62e1e1ed25453681d4c15389c59b1f35ce3fbf1a5feb7"
    },
    "character-avatar-defaults.zip": {
      "bytes": 1842488,
      "sha256": "03f980c983702c2c9d21b0f674903e151129d0554b25d800b8724036f2cb4a29"
    },
    "character_avatar_assets.py": {
      "bytes": 15165,
      "sha256": "a19e1bf49f6d89b80e5be212cd8bbee5a9c4c7601305af50c9653e5cab927f73"
    },
    "character_creation_diagnostic.py": {
      "bytes": 24584,
      "sha256": "409b5f50b9e2f4c69de9c073e9f4a80f917b6e5229a03c48f330fa6233cd53a3"
    },
    "character_reopen_diagnostic.py": {
      "bytes": 12328,
      "sha256": "57f6a3ff09ca0f154f6bf0a540d345fc87867d2cfe5c7d8fe57d7983c8d278b9"
    },
    "character_server_data_cache.py": {
      "bytes": 32868,
      "sha256": "d742fe7348424db7406281c1346b845ec092d2a30725e4005b63de750e041bb7"
    },
    "character_session_budget.py": {
      "bytes": 7608,
      "sha256": "37abe0e486604a6d73071d557117ea64d067bb33a561606e45bb0b0711132582"
    },
    "client-caches.zip": {
      "bytes": 27071659,
      "sha256": "5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051"
    },
    "client-launcher.exe": {
      "bytes": 246319,
      "sha256": "fd8a3724bd009d122fe98e03229e62516b5ee31245db9c093dfaceef73bd11db"
    },
    "client-prerequisites.zip": {
      "bytes": 18757,
      "sha256": "cc8bd66c482233a8d5ee7f33e51015bb5981f993cad014378b3861550b520e0e"
    },
    "client-runtime.zip": {
      "bytes": 8658250,
      "sha256": "094162db847a77b91ef8ff04e99a2b072b3eeeda3f6530267b0b896dfdf148cb"
    },
    "client-visual-assets.zip": {
      "bytes": 859075775,
      "sha256": "5f91b7d4ebe91e6a547923d702e2fcd56d7fc1d36fb7bffbb66463562d977d60"
    },
    "client-visual-manifest.json": {
      "bytes": 48591999,
      "sha256": "8587015400e1af639e2118649f0d9c77a089d564bfe2c97cbf9d80baaee5f9a2"
    },
    "client_animation_package.py": {
      "bytes": 12408,
      "sha256": "c6a291400e2614cab6007d6cb7c1dfd898a1a1b31b9a6f6985856ef6ec8150e4"
    },
    "client_attempt_retry.py": {
      "bytes": 12707,
      "sha256": "afc9f16471eda4e7d18a2bdbafab46f27999141217b5c2db998317897f1b8380"
    },
    "client_gpu_profile.py": {
      "bytes": 26233,
      "sha256": "71e72faab7c0e19407d586668f71e9ad2c46c10d0dbe214d76ead3240afd9e5c"
    },
    "client_interactive_diagnostic.py": {
      "bytes": 29745,
      "sha256": "b48c30437b98564f0d57d65699c0f7c224c97d02a49e25227c36f08ce7a70bf6"
    },
    "client_login_diagnostic.py": {
      "bytes": 15316,
      "sha256": "7e226a43c0f7c6b6333e85481eee26942aa868d74d38f3e54ff521be56ba8fdf"
    },
    "client_startup_diagnostic.py": {
      "bytes": 81516,
      "sha256": "0bc84d757a30c6ebb93402c4a3736ccbf5d69d4c8c914b34c3ba2d43349369a8"
    },
    "client_visual_assets.py": {
      "bytes": 26514,
      "sha256": "b560fa3004c05fcbeb30668c1f98aa1002d472513022ce5d6c202109fe399f89"
    },
    "dbserver-package.tar.gz": {
      "bytes": 2133821,
      "sha256": "83df206a4d41cf0b4b141b6486287ee6bf9ffe7f8125d9e970979cd87b33ca80"
    },
    "dbserver-schema.tar.gz": {
      "bytes": 1139794,
      "sha256": "637b3aeb7ec1bbf9f57f9f46cadd9eafd84254e920fe7e09a29280bdea9ea792"
    },
    "dbserver_diagnostic.py": {
      "bytes": 50159,
      "sha256": "6dd13390d2f299ad369251433f5a7ec5b13ad2454f5d873a136b7955120100a2"
    },
    "diagnostic.py": {
      "bytes": 69529,
      "sha256": "748975acf9b0c01b094166150112306edfc12c18656bc4b1926e00ea9460dbaf"
    },
    "game-package.tar.gz": {
      "bytes": 10976915,
      "sha256": "d781779ea33b99591ed9972ee09aa614cf4eb6c5afc355bb88197f20881fe67d"
    },
    "game_device_diagnostic.py": {
      "bytes": 51035,
      "sha256": "ffdb2ca9de0c408fd87a34ba8c97400cd8b85374833198c1ab1e24ad0ebde6ca"
    },
    "game_diagnostic.py": {
      "bytes": 79950,
      "sha256": "0d7d13c0c6ad134cb099e4a838b951f6873e331f5c6f7d21464882084f842541"
    },
    "game_evidence.py": {
      "bytes": 25884,
      "sha256": "12aad81ef11d82507de4ab002bf7615da4adf689b150dde9143a9b149af4718d"
    },
    "game_hang_evidence.py": {
      "bytes": 22400,
      "sha256": "ab5fe714b97e3d432d48a3acc9cef59674c22bcc9cec2e8b2c9d427662d39aef"
    },
    "game_map_progress.py": {
      "bytes": 14789,
      "sha256": "b98bc8d2d117c71f8d06f2cd2057646861f75c04d52d5cf8bd515a5919c199ec"
    },
    "hardware-renderer.zip": {
      "bytes": 2854913,
      "sha256": "5dff0392ddf724b43a6f3da900dfe8edc2926c116d8e190b1c75125c202df17d"
    },
    "local_character_server.py": {
      "bytes": 133022,
      "sha256": "68ff5b9580d7eec441c4053505269c9617ab2768e0171c6bd2efe8e8dd06da8f"
    },
    "local_login_server.py": {
      "bytes": 21351,
      "sha256": "03afd9707d046ab65da5235efbcab70d1b55f9831d9b65b6b1b02d44f6a487de"
    },
    "native-responsiveness.json": {
      "bytes": 40754,
      "sha256": "e3005754339365b88a41af12dadc2afd540033ba9ee927a18f9e353387e41fc3"
    },
    "native_character_events.py": {
      "bytes": 6484,
      "sha256": "2f9813e29530497e6834b21cfbcfc5fd9dd33fc8c64f49502eafab99f25b65b6"
    },
    "native_responsiveness_contract.py": {
      "bytes": 56170,
      "sha256": "fc674be005b430689d9594c3699d840e70edf7bd4d9e42b78d6df05d959148f8"
    },
    "native_training_save.py": {
      "bytes": 17455,
      "sha256": "a1bc4641eb96fed662274d742cea8ad51f47ab44fc0a35dec155da8a0e486fdc"
    },
    "presentation_diagnostic.py": {
      "bytes": 17396,
      "sha256": "751f163d6fb1c2573437f80bcb1484acc6ddb7219a625221f2f619e7683329df"
    },
    "probe.dll": {
      "bytes": 82761,
      "sha256": "746135e7a22624cee2c46fc6fef5762277f44e57e6f50184eb41d585491cfd1b"
    },
    "psqlodbc_x86.msi": {
      "bytes": 4079616,
      "sha256": "1b1c85f694ecad95fd3a0125a8b071669772bef098366738de48812124896773"
    },
    "runtime-lock.json": {
      "bytes": 1688,
      "sha256": "025e9bf55b214be4ff4709ec917ba326648a78feae8e97cd0131b72adca4f760"
    },
    "runtime-probe.exe": {
      "bytes": 245968,
      "sha256": "1205adc31f5324d42c30cf83aa1de4d847e2da4b3ee23f28deebac23f49d1842"
    },
    "server-animation-manifest.json": {
      "bytes": 1005794,
      "sha256": "8f752dceeffa632287602176f26722c3129fcdc9941709793d8b26d22151859f"
    },
    "server-animations.pigg": {
      "bytes": 97084456,
      "sha256": "465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b"
    },
    "server-cache-manifest.json": {
      "bytes": 39041,
      "sha256": "4e1a4c9c148509ef34245768f64ca2be4bb83659db845c6ef94ed594666b3fff"
    },
    "server-caches.zip": {
      "bytes": 29825263,
      "sha256": "7439d4557ae9fd74bb4bb4a324b6a676829387124be0817eb1da3c8adff10b17"
    },
    "server_animation_package.py": {
      "bytes": 10482,
      "sha256": "9fcbc32e2aa7f43151f4ec1c4ddc51e6c12202d81076fb5521936721f5174f81"
    },
    "server_cache_package.py": {
      "bytes": 20625,
      "sha256": "2d38757408f978fc5b79245e6bc590b0f368ee695f3854acea6fb38cf3173d33"
    },
    "server_message_cache_format.py": {
      "bytes": 4921,
      "sha256": "e70fa5aa8c591c866f0c72f3840495cd93024031936f92944c813a9901d3d6ec"
    },
    "startup-dbserver-manifest.json": {
      "bytes": 32549,
      "sha256": "949a15e5a796c5c63cf94d3b16072762f9f310545ca28184f5a714d897c9f087"
    },
    "startup-dbserver.exe": {
      "bytes": 1664512,
      "sha256": "ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba"
    },
    "stationary_contact_evidence.py": {
      "bytes": 11472,
      "sha256": "40ae7dde35df5d4d44c83bf2b85e52c1fc56171034dbcb483d55aeb0fa29f47d"
    },
    "task-gate.json": {
      "bytes": 300,
      "sha256": "df780496663132d0537ed748634fcb9bc262094536ef3b53a831e860bf2b7bdc"
    },
    "task_gate_evidence.py": {
      "bytes": 30573,
      "sha256": "8907f38418645156596947ad4f01c091c2e0473b4bb3eb9b7b358df207fd5de1"
    },
    "texture_header_index.py": {
      "bytes": 17694,
      "sha256": "ccc16dd3091d4d5622c0791a9c25f4d719523778b2755269c8e1abf9683fcb6a"
    }
  },
  "guest": {
    "all_data_loaded": true,
    "android_surface_validated": false,
    "character_reopen": {
      "account": "COHLOCAL",
      "auth_id": 1353310574,
      "baseline_character_count": 1,
      "baseline_character_id": 1,
      "baseline_identity_sha256": "e1ea5a6b325dba6b37e7171cc5f7bd1ab3f6a0cdc8773f7f62fbdcdf2a6fca06",
      "before_character_id": 1,
      "before_login_count": 16,
      "character_id": 1,
      "client_pid": 644,
      "client_ready_observed_utc": "2026-10-08T19:03:14.929204+00:00",
      "client_ready_observed_utc_ms": 1791486194929,
      "committed_native_position_verified": true,
      "committed_safe_position_verified": false,
      "committed_sql_verified": true,
      "connected_on_atlas": true,
      "costume_preserved": true,
      "db_map_assignment_observed": true,
      "disconnected_before_sql": true,
      "evidence_scope": "existing_committed_character_native_ready_then_requested_logout_and_preserved_committed_rows",
      "existing_character_verified": true,
      "forced_stop_before_save": false,
      "gameplay_verified": false,
      "login_count": 17,
      "logout_timer_observed": true,
      "map_id": 1,
      "map_ready": true,
      "name": "THORHERO",
      "native_client_ready_observed": true,
      "on_atlas_safe_position": false,
      "operation": "reopen_existing_character",
      "ordinary_stuck_observed": false,
      "powers_preserved": true,
      "preserved_existing_identity": true,
      "recovery_requested": false,
      "recovery_verified": false,
      "reopen_verified": true,
      "requested_logout_observed": true,
      "saved_utc": "2026-10-08T19:17:37.100081+00:00",
      "selected_rows_preserved": true,
      "session_id": "c197815449fa49e190141c1cc6b6354b",
      "snapshot_sha256": "c5bb997f87211afb39d9bbc795e185e85ce985259f89814ad2b75e27196564f7",
      "sql_game_mutations_performed": false,
      "stable_ground_verified": false,
      "verified": true,
      "verified_utc": "2026-10-08T19:17:37.425807+00:00"
    },
    "character_session_budgets": [
      {
        "account": "COHLOCAL",
        "character_id": 1,
        "client_pid": 644,
        "deadline_utc_ms": 1791487394929,
        "format": 1,
        "generated_utc_ms": 1791486194929,
        "map_id": 1,
        "movement_deadline_utc_ms": 1791487154929,
        "name": "THORHERO",
        "native_client_ready_observed": true,
        "phase": "connected",
        "reopen_verified": true,
        "revision": 1,
        "save_request_deadline_utc_ms": 1791487214929,
        "session_id": "c197815449fa49e190141c1cc6b6354b"
      }
    ],
    "cleanup": {
      "owned_processes_reaped": true,
      "postgres_graceful": true,
      "wine_prefix_stopped": true
    },
    "cleanup_complete": true,
    "cleanup_execution": {
      "diagnostic_initialized": true,
      "owned_child_count": 76,
      "wine_started": true
    },
    "client_gpu_profile": {
      "automatic_mid_game_fallback": false,
      "fallback_reason": null,
      "format": 1,
      "game_prefix_modified_by_probe": false,
      "game_rendering_validated": false,
      "hardware_acceleration_validated": false,
      "launch_label": "actual-coh-client",
      "physical_fps_improvement_validated": false,
      "policy": "owned_Game_attempt_after_bounded_prerequisites",
      "probe_cleanup_safe": true,
      "requested": "software",
      "selected": "software",
      "session_id": "c197815449fa49e190141c1cc6b6354b",
      "shared_wine_environment_modified": false,
      "state": "software_default"
    },
    "client_launch": {
      "pid": 644,
      "session_id": "c197815449fa49e190141c1cc6b6354b"
    },
    "client_main_loop_reached": true,
    "client_process_started": true,
    "client_window_observed": true,
    "client_windows": [
      {
        "height": 600,
        "mapped": true,
        "title": "City of Heroes : City_Zones/City_01_01/City_01_01.txt  PID: 644",
        "width": 800,
        "window_id": 20971523
      }
    ],
    "client_worktree": {
      "cache_archive_sha256": "5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051",
      "content_identity_sha256": "1fec98aa547502a1e65f1c48d6ca1441be9f692dbbd68565e70ba1883402a053",
      "copied_writable_files": 6,
      "format": 1,
      "imported_input_bytes_unchanged": true,
      "imported_inputs_readonly": true,
      "imported_metadata_normalized": true,
      "input_bytes": 2977730517,
      "input_files": 173011,
      "linked_files": 173005,
      "normalized_mtime_epoch": 1767225600,
      "package_sha256": "094162db847a77b91ef8ff04e99a2b072b3eeeda3f6530267b0b896dfdf148cb",
      "prepared_cache_bytes": 364703716,
      "prepared_cache_files": 100,
      "prepared_prerequisite_bytes": 54948,
      "prepared_prerequisite_files": 3,
      "prerequisites_archive_sha256": "cc8bd66c482233a8d5ee7f33e51015bb5981f993cad014378b3861550b520e0e",
      "prerequisites_manifest_sha256": "32c27465763cd08b9a210a75f0661634143f39fbe02d4bdaec43c819715a3c1f",
      "reused": true,
      "source_data": "/game-import/data",
      "source_root_preserved": true,
      "worktree_key": "client-work-285adbfb0389ed61b577b734"
    },
    "diagnostic_mode": "actual_character_startup_timing",
    "execution_platform_requested": "android",
    "failures": [],
    "game_validated": false,
    "gameplay_validated": false,
    "hardware_acceleration_validated": false,
    "import_identity": {
      "contract_sha256": "adf389319248eea549e4096ff12e5dca38ccfe9241eaa9fad4d136441b4cf293",
      "file_count": 173011,
      "generation": "generation-465fcafc89e648ecab66a94b14ad502b",
      "receipt_sha256": "c67e2df0575173e4c2bac3f6900d316d117a0126657db78b84c067a0b1b2b7fe",
      "total_bytes": 2977730517
    },
    "input_effect_verified": false,
    "interaction_completion_reason": "interaction_timeout",
    "interaction_session_completed": true,
    "interaction_timeout_seconds": 1200,
    "local_login": {
      "auth_id": 1353310574,
      "character_list_response_sent": true,
      "character_list_sent": true,
      "client_pid": 644,
      "database_preserved": true,
      "local_account_verified": true,
      "local_login_verified": true,
      "profile": "android-local-login",
      "session_id": "c197815449fa49e190141c1cc6b6354b"
    },
    "mapserver_started": true,
    "menu_visual_validated": false,
    "observation_seconds": 1304.498,
    "passed": true,
    "postgres_started": true,
    "presentation_socket_removed": true,
    "process_exit_codes": [
      3,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      1,
      1,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      -15,
      1,
      1
    ],
    "renderer_initialized": true,
    "scope": "actual_character_startup_timing_guest",
    "screenshots": [
      {
        "distinct_colors_capped": 1,
        "height": 600,
        "path": "before-client.ppm",
        "session_id": "c197815449fa49e190141c1cc6b6354b",
        "sha256": "c3b3d73f6bbb08ab3fa3dfa65d01f89916ba25d37a4f5fbd8cd2202edaa58077",
        "width": 800
      },
      {
        "distinct_colors_capped": 256,
        "height": 600,
        "path": "client-startup.ppm",
        "session_id": "c197815449fa49e190141c1cc6b6354b",
        "sha256": "97683bf55cf2415d55503b87c88928a03a787d39aa04817bf276cec97cc752b8",
        "width": 800
      },
      {
        "distinct_colors_capped": 256,
        "height": 600,
        "path": "client-observed.ppm",
        "session_id": "c197815449fa49e190141c1cc6b6354b",
        "sha256": "c16c003e1b39b1e8411bd5a95202caef17e9b711802594c5610f5f9d4709ee21",
        "width": 800
      }
    ],
    "server_started": true,
    "session_id": "c197815449fa49e190141c1cc6b6354b",
    "stages": [
      {
        "data_commit": "d51533ec8e6a9cf726b9214968077a05fdcf19f3",
        "source_commit": "0b75ade0c801735e10c5798f641948a45cc50488",
        "stage": "client_inputs",
        "status": "passed"
      },
      {
        "stage": "client_private_data",
        "status": "passed"
      },
      {
        "stage": "persistent_server_profile",
        "status": "passed"
      },
      {
        "stage": "postgres_local_login",
        "status": "passed"
      },
      {
        "stage": "presentation_display",
        "status": "passed"
      },
      {
        "stage": "wine_initialization",
        "status": "passed"
      },
      {
        "stage": "local_login_odbc",
        "status": "passed"
      },
      {
        "stage": "local_dbserver_startup",
        "status": "passed"
      },
      {
        "stage": "local_atlas_startup",
        "status": "passed"
      },
      {
        "stage": "client_visual_assets",
        "status": "passed"
      },
      {
        "stage": "client_animation_pack",
        "status": "passed"
      },
      {
        "stage": "win32_runtime_dll",
        "status": "passed"
      },
      {
        "stage": "actual_client_startup",
        "status": "passed"
      },
      {
        "bounded_live_observation": true,
        "stage": "actual_client_interaction",
        "status": "passed"
      }
    ],
    "startup_elapsed_seconds": 167.725,
    "startup_observed": true,
    "startup_only_reopen": true,
    "status": "passed",
    "task_gate_required": false,
    "wine_process_cleanup": {
      "complete": true,
      "inspection_failures": 0,
      "remaining": 0
    }
  },
  "launcher_started_uptime_ms": 508530977,
  "retained_native_producer": {
    "client_executable_sha256": "adcabb11135fe44b2c1f997a088ec58e4ea0d90e9defaa9f88efea34538caa44",
    "manifest_sha256": "406b49ff12d74446baf8cf1977658c1b264e17a92ef2376f74b239a14b98a960",
    "repository_commit": "a4a658be25d2b5ca1393b7d3daedd83a7d9ca1f4"
  },
  "retained_native_runtime_sha256": "094162db847a77b91ef8ff04e99a2b072b3eeeda3f6530267b0b896dfdf148cb",
  "source_report_sha256": "70bd8860a6bf9d455e53b1ed2fd9774483edc120f3b638f902384039dd6aea67"
}''')


def method(source, signature):
    start = source.index(signature)
    cursor = source.index('{', start)
    depth, end = 1, cursor + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def java_value(value):
    if isinstance(value, dict):
        return 'obj(' + ','.join(java_value(item) for pair in value.items() for item in pair) + ')'
    if isinstance(value, list):
        return 'arr(' + ','.join(map(java_value, value)) + ')'
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, bool):
        return 'Boolean.TRUE' if value else 'Boolean.FALSE'
    if value is None:
        return 'null'
    if isinstance(value, int):
        return str(value) + ('L' if abs(value) > 2147483647 else '')
    if isinstance(value, float):
        return repr(value)
    raise AssertionError(value)


HARNESS = r'''package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
final class JSONObject extends LinkedHashMap<String,Object> {
 Object opt(String k){return get(k);} boolean has(String k){return containsKey(k);}
 boolean isNull(String k){return !has(k)||get(k)==null;} int length(){return size();}
 Iterator<String> keys(){return keySet().iterator();}
 String getString(String k){return (String)get(k);}
 String optString(String k){Object v=get(k);return v instanceof String?(String)v:"";}
 boolean optBoolean(String k){return Boolean.TRUE.equals(get(k));}
 long optLong(String k,long fallback){Object v=get(k);return v instanceof Number?((Number)v).longValue():fallback;}
 int optInt(String k,int fallback){return (int)optLong(k,fallback);} int optInt(String k){return optInt(k,0);}
 double optDouble(String k,double fallback){Object v=get(k);return v instanceof Number?((Number)v).doubleValue():fallback;}
 JSONObject optJSONObject(String k){Object v=get(k);return v instanceof JSONObject?(JSONObject)v:null;}
 JSONObject getJSONObject(String k){return (JSONObject)get(k);}
 JSONArray optJSONArray(String k){Object v=get(k);return v instanceof JSONArray?(JSONArray)v:null;}
 JSONArray getJSONArray(String k){return (JSONArray)get(k);}
}
final class JSONArray extends ArrayList<Object> {
 int length(){return size();} JSONObject getJSONObject(int i){return (JSONObject)get(i);}
}
public final class GPURepairEvidenceHost {
 static JSONObject obj(Object... vals){JSONObject r=new JSONObject();for(int i=0;i<vals.length;i+=2)r.put((String)vals[i],vals[i+1]);return r;}
 static JSONArray arr(Object... vals){JSONArray r=new JSONArray();Collections.addAll(r,vals);return r;}
 static void require(boolean ok,String why){if(!ok)throw new AssertionError(why);}
 static final class Imported {
  String generation,sourceCommit,dataCommit;long count,bytes;File dataDirectory=new File("/host/import/data");
 }
 static final class Runtime {
  boolean reopen=true;String session,gpuProfileRequested="software";JSONObject manifest,clientManifest;
  JSONObject characterConnectedEvent,characterSavedEvent;
  long observedClientPid,clientWindowObservedUptime,clientWindowEndedUptime,launcherBudgetStartedUptime,startedUptime;
  List<Map<String,Object>> sessionBudgetEvents=new ArrayList<>();
  ClientSessionBudget sessionBudget=new ClientSessionBudget();Imported imported=new Imported();byte[] receipt;
  static final int MAX_JSON=4000000;
  Object jsonValue(Object value){return value;}
  byte[] read(File path,int max){return receipt;}
  String hex(byte[] value){StringBuilder r=new StringBuilder();for(byte v:value)r.append(String.format("%02x",v&255));return r.toString();}
  METHODS
 }
 @SuppressWarnings("unchecked") public static void main(String[] args)throws Exception {
  JSONObject fixture=FIXTURE_VALUE,report=fixture.getJSONObject("guest"),a=fixture.getJSONObject("android");
  Runtime owner=new Runtime();owner.session=a.getString("session_id");
  owner.observedClientPid=report.getJSONObject("client_launch").optLong("pid",-1);
  JSONObject pinned=fixture.getJSONObject("current_apk_files"),runtimePins=new JSONObject(),clientPins=new JSONObject(),guestHashes=new JSONObject();
  for(String name:pinned.keySet()) {
   runtimePins.put(name,obj("sha256",pinned.getJSONObject(name).getString("sha256"),"bytes",pinned.getJSONObject(name).opt("bytes")));
   clientPins.put(name,obj("sha256",pinned.getJSONObject(name).getString("sha256"),"bytes",pinned.getJSONObject(name).opt("bytes")));
   guestHashes.put(name,pinned.getJSONObject(name).getString("sha256"));
  }
  report.put("asset_sha256",guestHashes);
  JSONArray processes=new JSONArray();for(Object code:report.getJSONArray("process_exit_codes"))processes.add(obj("exit_code",code,"input_closed",true,"output_capture_closed",true));
  report.put("processes",processes);report.remove("process_exit_codes");
  owner.manifest=obj("startup_only_reopen",true,"client_gpu_profile",obj("format",1),"files",runtimePins);
  owner.clientManifest=obj("files",clientPins);
  owner.characterConnectedEvent=a.getJSONObject("character_connected_event");owner.characterSavedEvent=a.getJSONObject("character_saved_event");
  owner.startedUptime=a.optLong("started_uptime_ms",-1);
  owner.clientWindowObservedUptime=a.optLong("client_window_observed_uptime_ms",-1);
  owner.clientWindowEndedUptime=a.optLong("client_window_ended_uptime_ms",-1);
  owner.launcherBudgetStartedUptime=fixture.optLong("launcher_started_uptime_ms",-1);
  for(Object event:a.getJSONArray("session_budget_events")) {
   Map<String,Object> row=(Map<String,Object>)event;long generated=((Number)row.get("generated_utc_ms")).longValue();
   long observed=a.optLong("interaction_deadline_uptime_ms",-1)-((Number)row.get("deadline_utc_ms")).longValue()+generated;
   require(owner.sessionBudget.apply(row,owner.session,owner.observedClientPid,true,false,0,generated,observed,
    Math.min(owner.startedUptime+5400000,owner.launcherBudgetStartedUptime+2100000)),"physical accepted budget");
   owner.sessionBudgetEvents.add(row);
  }
  JSONObject identity=report.getJSONObject("import_identity");owner.imported.generation=identity.getString("generation");
  owner.imported.count=identity.optLong("file_count",-1);owner.imported.bytes=identity.optLong("total_bytes",-1);
  JSONObject inputs=report.getJSONArray("stages").getJSONObject(0);
  owner.imported.sourceCommit=inputs.getString("source_commit");owner.imported.dataCommit=inputs.getString("data_commit");
  owner.receipt=("contract.sha256="+identity.getString("contract_sha256")+"\n").getBytes(StandardCharsets.UTF_8);
  identity.put("receipt_sha256",owner.hex(MessageDigest.getInstance("SHA-256").digest(owner.receipt)));
  String mode=args[0];JSONObject row=report.getJSONArray("character_session_budgets").getJSONObject(0);
  if(mode.equals("physical")){
   require(report.optDouble("observation_seconds",0)>1210,"legacy cap was the exact mismatch");
   require(fixture.getJSONObject("retained_native_producer").getString("repository_commit").equals("a4a658be25d2b5ca1393b7d3daedd83a7d9ca1f4"),".19 producer retained by .20");
   require(owner.clientManifest.getJSONObject("files").getJSONObject("client-runtime.zip").getString("sha256").equals(
    fixture.getString("retained_native_runtime_sha256")),"typed Game predecessor remains pinned");
  }
  if(mode.equals("legacy")){owner.sessionBudgetEvents.clear();report.remove("character_session_budgets");report.put("observation_seconds",1200);}
  if(mode.equals("unapproved_extension"))owner.sessionBudgetEvents.clear();
  if(mode.equals("foreign_session"))report.put("session_id","00000000000000000000000000000000");
  if(mode.equals("foreign_pid"))report.getJSONObject("client_launch").put("pid",645);
  if(mode.equals("foreign_budget_session"))row.put("session_id","00000000000000000000000000000000");
  if(mode.equals("foreign_budget_pid"))row.put("client_pid",645);
  if(mode.equals("budget_deadline"))row.put("deadline_utc_ms",row.optLong("deadline_utc_ms",-1)+1000);
  if(mode.equals("budget_revision"))row.put("revision",2);
  if(mode.equals("budget_format_boolean"))row.put("format",true);
  if(mode.equals("budget_revision_float"))row.put("revision",1.0);
  if(mode.equals("budget_unverified"))row.put("native_client_ready_observed",false);
  if(mode.equals("budget_missing"))report.remove("character_session_budgets");
  if(mode.equals("budget_duplicate"))report.getJSONArray("character_session_budgets").add(row);
  if(mode.equals("overlong"))report.put("observation_seconds",3000);
  if(mode.equals("window_overrun"))owner.clientWindowEndedUptime=owner.sessionBudget.deadline()+10001;
  if(mode.equals("launcher_overrun"))owner.launcherBudgetStartedUptime=owner.sessionBudget.deadline()-2100001;
  if(mode.equals("operation_overrun"))owner.startedUptime=owner.sessionBudget.deadline()-5400001;
  if(mode.equals("foreign_payload"))report.getJSONObject("asset_sha256").put("client_gpu_profile.py",String.join("",Collections.nCopies(64,"e")));
  if(mode.equals("foreign_Game_producer"))report.getJSONObject("asset_sha256").put("client-runtime.zip",String.join("",Collections.nCopies(64,"e")));
  if(mode.equals("forged_APK_Game_pin"))owner.manifest.getJSONObject("files").getJSONObject("client-runtime.zip").put("sha256",String.join("",Collections.nCopies(64,"e")));
  if(mode.equals("foreign_GPU_session"))report.getJSONObject("client_gpu_profile").put("session_id","foreign");
  if(mode.equals("no_preserved_powers"))report.getJSONObject("character_reopen").put("powers_preserved",false);
  if(mode.equals("no_cleanup"))report.put("cleanup_complete",false);
  if(mode.equals("missing_stage"))report.getJSONArray("stages").remove(10);
  System.out.print(owner.guestAccepted(report));
 }
}
'''


class GPURepairEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (JAVA/'ClientRuntime.java').read_text()
        methods = '\n'.join(method(source, signature) for signature in (
            'private boolean gpuProfileReportMatches(', 'private boolean guestAccepted('))
        cls.temp = tempfile.TemporaryDirectory(prefix='coh-gpu-repair-evidence-')
        harness = Path(cls.temp.name)/'GPURepairEvidenceHost.java'
        harness.write_text(HARNESS.replace('METHODS', methods).replace('FIXTURE_VALUE', java_value(FIXTURE)))
        result = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
            '-d', cls.temp.name, str(JAVA/'ClientAcceptance.java'), str(JAVA/'ClientSessionBudget.java'), str(harness)],
            capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def execute(self, mode, accepted=False):
        result = subprocess.run(['java', '-cp', self.temp.name,
            'io.github.russianranger.cohclientinteractive.GPURepairEvidenceHost', mode],
            check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout, str(accepted).lower(), mode)

    def test_physical_0_13_20_software_report_uses_verified_connection_budget(self):
        self.assertEqual(FIXTURE['app_version'], '0.13.20')
        self.assertEqual(FIXTURE['guest']['observation_seconds'], 1304.498)
        self.assertEqual(FIXTURE['retained_native_producer']['client_executable_sha256'],
                         'adcabb11135fe44b2c1f997a088ec58e4ea0d90e9defaa9f88efea34538caa44')
        self.execute('physical', True)

    def test_legacy_short_observation_stays_accepted(self):
        self.execute('legacy', True)

    def test_guest_cannot_grant_itself_an_extended_window(self):
        for mode in ('unapproved_extension','budget_missing','budget_duplicate','budget_deadline',
                     'budget_revision','budget_format_boolean','budget_revision_float','budget_unverified'):
            with self.subTest(mode=mode): self.execute(mode)

    def test_session_and_native_pid_must_match_owned_android_evidence(self):
        for mode in ('foreign_session','foreign_pid','foreign_budget_session','foreign_budget_pid','foreign_GPU_session'):
            with self.subTest(mode=mode): self.execute(mode)

    def test_duration_stays_bounded_by_accepted_local_deadlines(self):
        for mode in ('overlong','window_overrun','launcher_overrun','operation_overrun'):
            with self.subTest(mode=mode): self.execute(mode)

    def test_retained_Game_producer_and_current_APK_payload_pins_remain_required(self):
        for mode in ('foreign_payload','foreign_Game_producer','forged_APK_Game_pin'):
            with self.subTest(mode=mode): self.execute(mode)

    def test_character_preservation_cleanup_and_complete_stage_contract_still_required(self):
        for mode in ('no_preserved_powers','no_cleanup','missing_stage'):
            with self.subTest(mode=mode): self.execute(mode)


if __name__ == '__main__':
    unittest.main()
