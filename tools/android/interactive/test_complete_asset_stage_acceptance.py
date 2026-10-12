#!/usr/bin/env python3
"""Replay both .31 physical report stage projections through production Java.

The archived guest reports have 16 stages; the old Android gate allowed 14.
Only stage names/statuses and cleanup fields are projected here. These fixtures
cannot provide Android captures, current-session events, or an overall pass.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java'
RELEASE_SOURCE = '74fe247be85173e618f1af2c8af71b1316de4cd8'
CLIENT_MANIFEST_SHA256 = '911e2b00877e9c40157d77bdf60569ca08f909f9856ab99f455136ad3f7c9665'
ZONE_PINS = ('zone_asset_package.py', 'zones-world-supplement.zip',
             'zones-world-supplement-manifest.json', 'zones-audio-supplement.zip',
             'zones-audio-supplement-manifest.json')
VISUAL_PINS = ('client_visual_assets.py', 'client_animation_package.py',
               'client-visual-assets.zip', 'client-visual-manifest.json')

# Exact pins from the authenticated .31 public APK; metadata authenticity is
# established by the release receipt. This gate checks complete typed pin sets.
PINS = json.loads(r'''{
  "001-coh-compat.sql": {
    "bytes": 7788,
    "sha256": "443ba977cdaf3e0a5c232986339f36ca8b19845943198177aaee5f191cd7f38a"
  },
  "atlas-world-supplement-manifest.json": {
    "bytes": 4258210,
    "sha256": "204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86"
  },
  "atlas-world-supplement.zip": {
    "bytes": 207803201,
    "sha256": "c7ed82aaaf987410fa471e19ee2b19115ef660892a06f79e2e2401d5672b095f"
  },
  "atlas_world_assets.py": {
    "bytes": 24825,
    "sha256": "ff372738ba5954912080a3b9b6725e225bc887e2c1274bbf4a002640ed572b69"
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
    "bytes": 15496,
    "sha256": "e4e17c8931786490728c721d6db063b55b2e7e17d27813a3da355e72773a8ae1"
  },
  "character_creation_diagnostic.py": {
    "bytes": 26016,
    "sha256": "eac84e21af4b593d9f2781ef5970c18ed4d7a4e10af9653f024f809c7cedf935"
  },
  "character_reopen_diagnostic.py": {
    "bytes": 15039,
    "sha256": "6c6b38a88c25f23ea48a6b4be2aa4245906591a6e1ec486bb084d64bed2bfe24"
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
    "bytes": 8702383,
    "sha256": "5636fe9b3d45c313b062ac83ba954bfb3b1b160af4aec1b34f046c8c2b421509"
  },
  "client_interactive_diagnostic.py": {
    "bytes": 31748,
    "sha256": "8ac5555163aa3fd67ff9080bbf956a5f73f161a15b60c2fd310f979160cdb594"
  },
  "client_login_diagnostic.py": {
    "bytes": 15316,
    "sha256": "7e226a43c0f7c6b6333e85481eee26942aa868d74d38f3e54ff521be56ba8fdf"
  },
  "client_startup_diagnostic.py": {
    "bytes": 91242,
    "sha256": "8ac9477951ff7a6252a1a72f8184242bb5c0863e604913ea452303e6d4696a53"
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
    "bytes": 10943638,
    "sha256": "36d815fd6e9b8eeebbf04de756ea05fa9ee4f29a5330a6cde15926522a4215aa"
  },
  "game_device_diagnostic.py": {
    "bytes": 51035,
    "sha256": "ffdb2ca9de0c408fd87a34ba8c97400cd8b85374833198c1ab1e24ad0ebde6ca"
  },
  "game_diagnostic.py": {
    "bytes": 80208,
    "sha256": "f7867ab725ad1b717f507d76b6c488c77e168732a9fe878eb3336d936606e737"
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
  "local_character_server.py": {
    "bytes": 150443,
    "sha256": "0472fd103d2a90deb2a60d603aac7a39515ee6cb18ac55810820137b1c9f8689"
  },
  "local_login_server.py": {
    "bytes": 21351,
    "sha256": "03afd9707d046ab65da5235efbcab70d1b55f9831d9b65b6b1b02d44f6a487de"
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
  "character_session_budget.py": {
    "bytes": 8816,
    "sha256": "0659ebf7caf31eb898e9d5770a91f64d496d0cfc77f515229bae3e55780ae8fe"
  },
  "character_server_data_cache.py": {
    "bytes": 32868,
    "sha256": "d742fe7348424db7406281c1346b845ec092d2a30725e4005b63de750e041bb7"
  },
  "texture_header_index.py": {
    "bytes": 17875,
    "sha256": "41adbf003f4ff481b158be09bba8393dd99f615ccb4a036470968596c93459ff"
  },
  "client_attempt_retry.py": {
    "bytes": 12707,
    "sha256": "afc9f16471eda4e7d18a2bdbafab46f27999141217b5c2db998317897f1b8380"
  },
  "native-responsiveness.json": {
    "bytes": 40754,
    "sha256": "e3005754339365b88a41af12dadc2afd540033ba9ee927a18f9e353387e41fc3"
  },
  "native_responsiveness_contract.py": {
    "bytes": 78410,
    "sha256": "7523e2a32f9db8cbe308c8d8bceaa59bd490168cf6886791598810ef86910f85"
  },
  "native_character_events.py": {
    "bytes": 6484,
    "sha256": "2f9813e29530497e6834b21cfbcfc5fd9dd33fc8c64f49502eafab99f25b65b6"
  },
  "stationary_contact_evidence.py": {
    "bytes": 11472,
    "sha256": "40ae7dde35df5d4d44c83bf2b85e52c1fc56171034dbcb483d55aeb0fa29f47d"
  },
  "server-cache-manifest.json": {
    "bytes": 39041,
    "sha256": "4e1a4c9c148509ef34245768f64ca2be4bb83659db845c6ef94ed594666b3fff"
  },
  "server-caches.zip": {
    "bytes": 29825263,
    "sha256": "7439d4557ae9fd74bb4bb4a324b6a676829387124be0817eb1da3c8adff10b17"
  },
  "server_message_cache_format.py": {
    "bytes": 4921,
    "sha256": "e70fa5aa8c591c866f0c72f3840495cd93024031936f92944c813a9901d3d6ec"
  },
  "server_cache_package.py": {
    "bytes": 22143,
    "sha256": "ba2c0b14f3622efe4f7a29246f096c2edb1065e69a38ea00625802f741c2f73d"
  },
  "task_gate_evidence.py": {
    "bytes": 30573,
    "sha256": "8907f38418645156596947ad4f01c091c2e0473b4bb3eb9b7b358df207fd5de1"
  },
  "server_animation_package.py": {
    "bytes": 12619,
    "sha256": "a8a32b3fce31bea5d4ff9a2e9089fa2cf26303392b87f6feecfa3eaf968cedab"
  },
  "server-animation-manifest.json": {
    "bytes": 1005794,
    "sha256": "8f752dceeffa632287602176f26722c3129fcdc9941709793d8b26d22151859f"
  },
  "task-gate.json": {
    "bytes": 300,
    "sha256": "df780496663132d0537ed748634fcb9bc262094536ef3b53a831e860bf2b7bdc"
  },
  "server-animations.pigg": {
    "bytes": 97084456,
    "sha256": "465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b"
  },
  "startup-dbserver-manifest.json": {
    "bytes": 32549,
    "sha256": "949a15e5a796c5c63cf94d3b16072762f9f310545ca28184f5a714d897c9f087"
  },
  "startup-dbserver.exe": {
    "bytes": 1664512,
    "sha256": "ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba"
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
    "bytes": 12813,
    "sha256": "622d6feecc5b0391abbc027c3ae3d67b5694746838c09aa2730ab2adf5baed38"
  },
  "client_visual_assets.py": {
    "bytes": 26592,
    "sha256": "a16936dc5be61ceb9e3152acaadfd6007212b5daaeb7d329171cd62da2c9690f"
  },
  "native_training_save.py": {
    "bytes": 17455,
    "sha256": "a1bc4641eb96fed662274d742cea8ad51f47ab44fc0a35dec155da8a0e486fdc"
  },
  "atlas-beacon-manifest.json": {
    "bytes": 934650,
    "sha256": "ee11bb703eed85229948b30b41277c515faf80da31ccd0436171862765ba41f4"
  },
  "atlas_beacon_package.py": {
    "bytes": 36026,
    "sha256": "d7523f78fa2d1c20442ec66a4ebe2611f3d5df8597db2d3e1bf039104ed82503"
  },
  "atlas-beacons.zip": {
    "bytes": 16150904,
    "sha256": "0c7f602d31a438c6e67409bbb89da5d45ee3aacf13c96a50de9401d7973b2949"
  },
  "client_gpu_profile.py": {
    "bytes": 43246,
    "sha256": "77d850cf3d86b7846fdc925437d0e0ef9f44ce226a48fb975e3c6b9282e5f324"
  },
  "hardware-renderer.zip": {
    "bytes": 2865215,
    "sha256": "55f50f8434375cb6587bbfc81b7e9829bdbc8f7ba9a8403eb705315e17ce6f38"
  },
  "character_zoning.py": {
    "bytes": 57652,
    "sha256": "c6bb13eb60dc7f0af82c424d8e3de6772ed0d15fc4ae73d0479d1058bd438b3b"
  },
  "character_zoning_scheduler.py": {
    "bytes": 20419,
    "sha256": "dc76a478d6fefe83a9c298079bd9a199208fbebd28f189478ebe4a13143ab254"
  },
  "asset-pack-manifest.json": {
    "bytes": 3946,
    "sha256": "9570447b93e7d6e42768e1b0e16b791256b82d509d9caf007aca5c88cd7fd05c"
  },
  "kings-row-beacon-lock.json": {
    "bytes": 233,
    "sha256": "e2be78c3c055967a17edf8046f43c8e74954c77d29900da264b7781a59334354"
  },
  "kings_row_beacon_package.py": {
    "bytes": 9387,
    "sha256": "9150ecf3f3887e3fa45a37f48f0f870a92dc4c0e3abc2d80679697d4bdcf7bca"
  },
  "native_monorail_contract.py": {
    "bytes": 4205,
    "sha256": "45dfcca1585d549b751d6f7bcaa60037ab34751b1f2afe3095e69900832072d2"
  },
  "native_monorail_events.py": {
    "bytes": 5877,
    "sha256": "c40c96c4701582220dfee722c5315b9e565ace165278baedcc140ae3000572fd"
  },
  "zone_asset_package.py": {
    "bytes": 14689,
    "sha256": "c9380472304c0a968a01fd83412ec6fd8ab050edbb9418a0dcc409e59f069105"
  },
  "kings-row-beacon-manifest.json": {
    "bytes": 1426843,
    "sha256": "0b2ade9719e30fe4267782a8affa556c6245a02ad9f421a57195c115afde4694"
  },
  "kings-row-beacons.zip": {
    "bytes": 23708626,
    "sha256": "6a7bcfba0d6f64a13d31fc6c31bd8cd366344c6ffa92b546a26ef3f132c2d64c"
  },
  "zones-audio-supplement-manifest.json": {
    "bytes": 316144,
    "sha256": "c819e1af90c1f29a64eac57a20b0bdfb61a50bd9791206ab1ce18c05d210ec6f"
  },
  "zones-audio-supplement.zip": {
    "bytes": 847802311,
    "sha256": "3bbc5773f50593e5b2e667c7e01e7f971c3a6a65137f149e0823423798d7b2a7"
  },
  "zones-world-supplement-manifest.json": {
    "bytes": 4237139,
    "sha256": "f466ad6c8ab6e84dabd16d404c3a05bcb9fbca3cfad5746852d53b04132d8f74"
  },
  "zones-world-supplement.zip": {
    "bytes": 1663681523,
    "sha256": "f12a0994cec20ab6d13c158495fe01402e89113ae756e412357e9c4a04833ad3"
  }
}''')
# Projections of the two original attachment reports, named and hash-bound.
REPORTS = json.loads(r'''[
  {
    "attachment": "coh-atlas-gameplay-20261012-010537.zip",
    "guest_report_sha256": "65d87cc35586502d4e4855b2302ca96237af7d3339d436041d1c2a26de4eb9c4",
    "status": "passed",
    "passed": true,
    "stages": [
      {
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
        "stage": "client_all_zone_assets",
        "status": "passed"
      },
      {
        "stage": "client_all_zone_audio",
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
        "stage": "actual_client_interaction",
        "status": "passed"
      }
    ],
    "cleanup": {
      "cleanup_complete": true,
      "cleanup_execution": {
        "diagnostic_initialized": true,
        "wine_started": true,
        "owned_child_count": 81
      },
      "cleanup": {
        "postgres_graceful": true,
        "wine_prefix_stopped": true,
        "owned_processes_reaped": true
      },
      "postgres_started": true,
      "wine_process_cleanup": {
        "policy": "same_real_uid_and_run_token",
        "scanned_processes": 305,
        "scanned_tasks": 102,
        "dead_leaders_with_live_tasks": 5,
        "owned_live_workers": 5,
        "leader_exit_retries": 0,
        "candidates": 5,
        "term_signals": 5,
        "kill_signals": 2,
        "pidfd_signals": 7,
        "identity_checked_signals": 0,
        "inspection_failures": 0,
        "remaining": 0,
        "complete": true,
        "permission_read_retries": 0,
        "worker_exit_rechecks": 0,
        "permission_observations": [],
        "permission_observations_omitted": 0,
        "proc_read_retries": 0,
        "proc_read_observations": [],
        "proc_read_observations_omitted": 0,
        "last_inspection_failure": null
      },
      "processes": [
        {
          "exit_code": 3,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 1,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 1,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": -15,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 1,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 1,
          "input_closed": true,
          "output_capture_closed": true
        }
      ]
    }
  },
  {
    "attachment": "coh-atlas-gameplay-20261012-013507.zip",
    "guest_report_sha256": "36d62e079abc76ae67f48bd5c73bdeee2bc8d2d982c589f9b08b2003ff42dfe3",
    "status": "failed",
    "passed": false,
    "stages": [
      {
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
        "stage": "client_all_zone_assets",
        "status": "passed"
      },
      {
        "stage": "client_all_zone_audio",
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
        "stage": "actual_client_interaction",
        "status": "passed"
      }
    ],
    "cleanup": {
      "cleanup_complete": false,
      "cleanup_execution": {
        "diagnostic_initialized": true,
        "wine_started": true,
        "owned_child_count": 83
      },
      "cleanup": {
        "postgres_graceful": true,
        "wine_prefix_stopped": true,
        "owned_processes_reaped": false
      },
      "postgres_started": true,
      "wine_process_cleanup": {
        "policy": "same_real_uid_and_run_token",
        "scanned_processes": 166,
        "scanned_tasks": 35,
        "dead_leaders_with_live_tasks": 6,
        "owned_live_workers": 6,
        "leader_exit_retries": 0,
        "candidates": 6,
        "term_signals": 6,
        "kill_signals": 0,
        "pidfd_signals": 6,
        "identity_checked_signals": 0,
        "inspection_failures": 1,
        "remaining": null,
        "complete": false,
        "permission_read_retries": 2,
        "worker_exit_rechecks": 0,
        "permission_observations": [
          {
            "group_pid": 26421,
            "group_starttime": 27442356,
            "worker_tid": 26443,
            "worker_starttime": 27442557,
            "operation": "worker_environment",
            "errno": 13,
            "error_type": "PermissionError",
            "attempt": 1,
            "worker_state_before": "R",
            "resolution": "retry_same_live_worker",
            "worker_state_after": "R"
          },
          {
            "group_pid": 26421,
            "group_starttime": 27442356,
            "worker_tid": 26443,
            "worker_starttime": 27442557,
            "operation": "worker_environment",
            "errno": 13,
            "error_type": "PermissionError",
            "attempt": 2,
            "worker_state_before": "R",
            "resolution": "retry_same_live_worker",
            "worker_state_after": "R"
          },
          {
            "group_pid": 26421,
            "group_starttime": 27442356,
            "worker_tid": 26443,
            "worker_starttime": 27442557,
            "operation": "worker_environment",
            "errno": 13,
            "error_type": "PermissionError",
            "attempt": 3,
            "worker_state_before": "R",
            "resolution": "persistent_live_permission_denied",
            "worker_state_after": "R"
          }
        ],
        "permission_observations_omitted": 0,
        "proc_read_retries": 0,
        "proc_read_observations": [],
        "proc_read_observations_omitted": 0,
        "last_inspection_failure": {
          "group_pid": 26421,
          "group_starttime": 27442356,
          "worker_tid": 26443,
          "worker_starttime": 27442557,
          "operation": "worker_environment",
          "errno": 13,
          "error_type": "PermissionError",
          "attempt": 3,
          "worker_state_before": "R",
          "resolution": "persistent_live_permission_denied",
          "worker_state_after": "R"
        }
      },
      "processes": [
        {
          "exit_code": 3,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": false
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 1,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 0,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": -15,
          "input_closed": true,
          "output_capture_closed": false
        },
        {
          "exit_code": 1,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": 1,
          "input_closed": true,
          "output_capture_closed": true
        },
        {
          "exit_code": -15,
          "input_closed": true,
          "output_capture_closed": true
        }
      ]
    }
  }
]''')


def java_value(value):
    if isinstance(value, dict):
        return 'map('+','.join(java_value(item) for pair in value.items() for item in pair)+')'
    if isinstance(value, list):
        return 'new ArrayList<Object>(Arrays.asList('+','.join(map(java_value, value))+'))'
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, bool):
        return 'Boolean.TRUE' if value else 'Boolean.FALSE'
    if value is None:
        return 'null'
    if isinstance(value, int):
        return str(value)+'L'
    raise AssertionError('Unexpected fixture type: '+repr(value))


HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
public final class CompleteAssetStageHost {
    static Map<String,Object> map(Object... values) {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i=0;i<values.length;i+=2) result.put((String)values[i],values[i+1]);
        return result;
    }
    @SuppressWarnings("unchecked") public static void main(String[] args) {
        List<Object> reports = REPORT_VALUES;
        Map<String,Object> report = (Map<String,Object>) reports.get(Integer.parseInt(args[0]));
        List<Object> stages = (List<Object>) report.get("stages");
        Map<String,Object> pins = PIN_VALUES;
        String mode = args[1];
        if (mode.equals("cleanup")) {
            System.out.print(ClientAcceptance.cleanupSafe(report.get("cleanup"))); return;
        }
        if (mode.startsWith("historical")) {
            stages.remove(12); stages.remove(11);
            for (String name : ZONE_PIN_VALUES) pins.remove(name);
            if (mode.equals("historical12")) {
                stages.remove(10); stages.remove(9);
                for (String name : VISUAL_PIN_VALUES) pins.remove(name);
            }
        }
        if (mode.equals("missing_stage")) stages.remove(Integer.parseInt(args[2]));
        if (mode.equals("failed_stage")) ((Map<String,Object>)stages.get(Integer.parseInt(args[2]))).put("status","failed");
        if (mode.equals("boolean_stage")) ((Map<String,Object>)stages.get(Integer.parseInt(args[2]))).put("status",Boolean.TRUE);
        if (mode.equals("unknown_stage")) ((Map<String,Object>)stages.get(Integer.parseInt(args[2]))).put("stage","unqualified_stage");
        if (mode.equals("reordered")) Collections.swap(stages,Integer.parseInt(args[2]),Integer.parseInt(args[2])+1);
        if (mode.equals("extra_stage")) stages.add(map("stage","unqualified_stage","status","passed"));
        if (mode.equals("missing_pin")) pins.remove(args[2]);
        if (mode.equals("unpin_all_zones")) for (String name : ZONE_PIN_VALUES) pins.remove(name);
        if (mode.equals("unpin_all_visual")) for (String name : VISUAL_PIN_VALUES) pins.remove(name);
        if (mode.equals("short_zone_stages")) { stages.remove(12); stages.remove(11); }
        if (mode.equals("invalid_pin")) {
            Map<String,Object> pin = (Map<String,Object>) pins.get(args[2]);
            switch(args[3]) {
                case "zero": pin.put("bytes",0L); break;
                case "negative": pin.put("bytes",-1L); break;
                case "boolean": pin.put("bytes",Boolean.TRUE); break;
                case "fraction": pin.put("bytes",1.5); break;
                case "string": pin.put("bytes","10"); break;
                case "no_bytes": pin.remove("bytes"); break;
                case "no_hash": pin.remove("sha256"); break;
                case "short_hash": pin.put("sha256","a"); break;
                case "uppercase": pin.put("sha256",((String)pin.get("sha256")).toUpperCase(Locale.ROOT)); break;
                default: throw new AssertionError(args[3]);
            }
        }
        System.out.print(ClientAcceptance.clientInteractionStageIndex(stages,pins));
    }
}
'''


class CompleteAssetStageAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='coh-complete-asset-stage-')
        harness = Path(cls.tmp.name)/'CompleteAssetStageHost.java'
        harness.write_text(HARNESS.replace('REPORT_VALUES',java_value(REPORTS))
                           .replace('ZONE_PIN_VALUES','new String[]{'+','.join(map(java_value,ZONE_PINS))+'}')
                           .replace('VISUAL_PIN_VALUES','new String[]{'+','.join(map(java_value,VISUAL_PINS))+'}')
                           .replace('PIN_VALUES',java_value(PINS)))
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8',
                        '-d',cls.tmp.name,str(JAVA),str(harness)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def execute(self,report,mode,*arguments,expected=-1):
        run = subprocess.run(['java','-cp',self.tmp.name,
            'io.github.russianranger.cohclientinteractive.CompleteAssetStageHost',
            str(report),mode,*map(str,arguments)],check=True,capture_output=True,text=True)
        self.assertEqual(run.stdout,str(expected))

    def test_actual_reports_have_complete_ordered_sixteen_stage_contract(self):
        self.assertEqual(len(PINS),76)
        for report in range(2):
            with self.subTest(report=report):
                self.assertEqual(len(REPORTS[report]['stages']),16)
                self.execute(report,'current',expected=15)

    def test_actual_failed_cleanup_is_still_rejected_independently(self):
        self.assertEqual((REPORTS[0]['status'],REPORTS[0]['passed']),('passed',True))
        self.assertEqual((REPORTS[1]['status'],REPORTS[1]['passed']),('failed',False))
        self.execute(0,'cleanup',expected='true')
        self.execute(1,'cleanup',expected='false')

    def test_historical_twelve_and_fourteen_stage_contracts_remain(self):
        self.execute(0,'historical12',expected=11)
        self.execute(0,'historical14',expected=13)

    def test_every_complete_stage_is_required(self):
        for index in range(16):
            with self.subTest(index=index): self.execute(0,'missing_stage',index)

    def test_every_complete_stage_must_pass(self):
        for index in range(16):
            with self.subTest(index=index): self.execute(0,'failed_stage',index)

    def test_boolean_pass_and_unqualified_names_are_rejected(self):
        for mode in ('boolean_stage','unknown_stage'):
            for index in range(16):
                with self.subTest(mode=mode,index=index): self.execute(0,mode,index)

    def test_complete_stage_order_and_inventory_are_exact(self):
        for index in range(15):
            with self.subTest(index=index): self.execute(0,'reordered',index)
        self.execute(0,'extra_stage')

    def test_every_zone_helper_manifest_and_archive_pin_is_required(self):
        for name in ZONE_PINS:
            with self.subTest(name=name): self.execute(0,'missing_pin',name)

    def test_every_zone_pin_requires_strict_bytes_and_lowercase_sha256(self):
        for name in ZONE_PINS:
            for invalid in ('zero','negative','boolean','fraction','string','no_bytes','no_hash','short_hash','uppercase'):
                with self.subTest(name=name,invalid=invalid): self.execute(0,'invalid_pin',name,invalid)

    def test_guest_cannot_add_unpinned_zone_stages(self):
        self.execute(0,'unpin_all_zones')

    def test_complete_zone_bundle_cannot_remove_retained_visual_contract(self):
        self.execute(0,'unpin_all_visual')

    def test_pinned_bundle_cannot_omit_zone_preparation_stages(self):
        self.execute(0,'short_zone_stages')


if __name__ == '__main__':
    unittest.main()
