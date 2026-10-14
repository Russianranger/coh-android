"""Additive reviewed MapServer startup consumer; original cache history stays exact."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import re
import native_monorail_contract as monorail

require = monorail.require
SOURCE = monorail.retained.SOURCE
DATA = monorail.retained.DATA
ROLE = 'native_map_startup_certified_animation'
PREVIOUS_SHA256 = '53ff6ee013690670abbaed39e44d66267caf8753486fbc05c64766a56d9c0713'
PREVIOUS_RECEIPT_SHA256 = 'e0ab383a91b83c258bfacbc44acf328f1a0c1435c0e4a385eb5ad643566f3178'
PACK_SHA256 = '465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b'
TABLE_SHA256 = '179f8a15614dd42c9222be4d3716986bc9c0716a41d6045ef8f2ef7dc83427c4'
DEPENDENCY_SHA256 = '03236d08d8b33300cc27e614a25cbe37f6556ebe1c35132ab230a31170db33c9'
MANIFEST = 'map-startup-manifest.json'
# Separate committed source review. A source/SDK audit is not a native artifact
# and cannot authorize execution. Root freezes this independently of ZIP facts.
SOURCE_ONLY_COMPATIBILITY_REVIEW = {'descriptor': {'repository': 'Russianranger/coh-android',
                'commit': '1b8da4eb850c0e7c4f4ef0a49e43e15ac948ca2e',
                'path': 'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json',
                'git_blob': '6b6d373a275029476f28c77cc5fcfe010e58b9bb',
                'content': {'bytes': 15614,
                            'sha256': 'e5a268b0fbae23230e518f8dcbb49fdccdcdd998293de61b133cc7b5bbf1fd44'},
                'scope': {'source_compatibility_only': True,
                          'shipping_predecessor_execution_validated': False,
                          'new_native_runtime_qualification_proven': False,
                          'runtime_activation_allowed': False,
                          'shipping_allowed': False,
                          'native_ID_tables_observed': False,
                          'behavioral_collision_validated': False,
                          'physical_timing_validated': False}},
 'document': {'format': 1,
              'role': 'narrow_Map_metadata_consumer_source_and_historical_collision_boundary',
              'status': 'source_delta_verified_fresh_world_gate_pending',
              'shipping_allowed': False,
              'physical_candidate_behavior_measured': False,
              'shipping_036': {'APK_sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f',
                               'MapServer': {'bytes': 7475200,
                                             'delay_imports': [],
                                             'imports': ['ADVAPI32.dll',
                                                         'COMDLG32.dll',
                                                         'GDI32.dll',
                                                         'IPHLPAPI.DLL',
                                                         'KERNEL32.dll',
                                                         'PhysXCooking.dll',
                                                         'PhysXLoader.dll',
                                                         'SHELL32.dll',
                                                         'USER32.dll',
                                                         'WINMM.dll',
                                                         'WS2_32.dll'],
                                             'pe_machine': 332,
                                             'sha256': 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'},
                               'native_build_repository_commit': 'd456f06cd82a921964a895885a03c67137cb9257',
                               'native_build_manifest': {'bytes': 39595,
                                                         'sha256': '5ee56719f7abc4e12d19670c15398ba3d3b83ee14749ac7941b61e7ea4b291c1'},
                               'source_commit': '0b75ade0c801735e10c5798f641948a45cc50488'},
              'observed_control': {'native_source_commit': 'da5cf809925d9d91e029a117d8be184af03db2b6',
                                   'unobserved_control': {'delay_imports': [],
                                                          'imports': ['ADVAPI32.dll',
                                                                      'COMDLG32.dll',
                                                                      'GDI32.dll',
                                                                      'IPHLPAPI.DLL',
                                                                      'KERNEL32.dll',
                                                                      'PhysXCooking.dll',
                                                                      'PhysXLoader.dll',
                                                                      'SHELL32.dll',
                                                                      'USER32.dll',
                                                                      'WINMM.dll',
                                                                      'WS2_32.dll'],
                                                          'pe_machine': 332,
                                                          'sha256': '77c1f245132b76668e9f689bec26699ec980382c1079f000314d24b149e089ea',
                                                          'size': 7477248},
                                   'observed_Map': {'delay_imports': [],
                                                    'imports': ['ADVAPI32.dll',
                                                                'COMDLG32.dll',
                                                                'GDI32.dll',
                                                                'IPHLPAPI.DLL',
                                                                'KERNEL32.dll',
                                                                'PhysXCooking.dll',
                                                                'PhysXLoader.dll',
                                                                'SHELL32.dll',
                                                                'USER32.dll',
                                                                'WINMM.dll',
                                                                'WS2_32.dll'],
                                                    'pe_machine': 332,
                                                    'sha256': 'fbfcf1d80a41a80aaeecb1a0ec275daffed2a9e1ba25df3f16e23b16a51a493d',
                                                    'size': 7478784},
                                   'shipping_base_recipe_exactly_equal': True},
              'metadata_candidate': {'source_commit': '47e40d4d586d29e273e31ed4d0d51d160832b89d',
                                     'native': {'delay_imports': [],
                                                'imports': ['ADVAPI32.dll',
                                                            'COMDLG32.dll',
                                                            'GDI32.dll',
                                                            'IPHLPAPI.DLL',
                                                            'KERNEL32.dll',
                                                            'PhysXCooking.dll',
                                                            'PhysXLoader.dll',
                                                            'SHELL32.dll',
                                                            'USER32.dll',
                                                            'WINMM.dll',
                                                            'WS2_32.dll'],
                                                'pe_machine': 332,
                                                'sha256': '5927f87fdac50c5a839ac067ccbb34b5dfad6223e579287a66a2f866a7d4b2e6',
                                                'size': 7480832},
                                     'build_input': {'CRC_and_schema_checks_preserved': True,
                                                     'UtilitiesLib_SERVER_define_assumed': False,
                                                     'architecture': 'Win32',
                                                     'build_targets': ['MapServer'],
                                                     'configuration': 'OptDebug',
                                                     'environment': {'disabled_by_default': True,
                                                                     'enabled_value': '1',
                                                                     'name': 'COH_MAP_ANIMATION_METADATA_PREFETCH'},
                                                     'exact_request': {'directory': 'sequencers',
                                                                       'filemask': '.txt',
                                                                       'persistfile': 'bin/sequencers.bin',
                                                                       'tree': 'player_library/animations'},
                                                     'format': 1,
                                                     'freshness_body_exact_except_request': True,
                                                     'helper_sha256': 'b1ed267f299219469ab11d0e94f9cdfb47e375e8ab0b43d03f6c36160ba7cb88',
                                                     'native_decoder_preserved': True,
                                                     'native_execution_validated': False,
                                                     'new_asset_bytes_preloaded': False,
                                                     'patched_sha256': {'libs/UtilitiesLib/src/utils/textparser.c': '8008614d86bb33290f037b08536a0d81a747f4049612b8f76c4d2e8ad2dc9315'},
                                                     'persistent_cache_authority_added': False,
                                                     'physical_savings_validated': False,
                                                     'provider_precedence_preserved': True,
                                                     'publication_allowed': False,
                                                     'retained_Game_reference': {'patches/client-startup-followup/0001-preload-power-dependency-tree.patch': {'bytes': 1993,
                                                                                                                                                              'sha256': '96559ac8ef1470c1a9b3d78c8928bc68f960fdf4fcfaa8b59b37cf680b50b178'}},
                                                     'retained_callsites_sha256': {'Common/seq/seqload.c': '8c2761ceeabcc564f89d943780579a4f401ffb344f9ad6e7f5e73660c2b9b60f',
                                                                                   'libs/UtilitiesLib/src/utils/FolderCache.c': '93aac8a9e1a59ca47ab5a067580c36f7ed884db51038577b0453756f55af1d4c',
                                                                                   'libs/UtilitiesLib/src/utils/FolderCacheNode.c': '36faafa73afd83361fb8e4f25e340961fae5fb9d33c298b1200be9a4b2a48524',
                                                                                   'libs/UtilitiesLib/src/utils/file.c': '8ad08c34d2fed652578e26f0ec1fab79419b40414644c6b8e1ccbc58694733e1'},
                                                     'role': 'nonshipping_map_sequencer_metadata_prefetch',
                                                     'scope': 'ordinary_FolderCache_metadata_only_after_valid_BIN_dependency_header',
                                                     'shipping_allowed': False,
                                                     'source_date_and_membership_checks_preserved': True,
                                                     'source_local_Map_only_staging': True,
                                                     'source_sha256': {'libs/UtilitiesLib/src/utils/textparser.c': '860118093e7abd9a443d89ebeafb72e18f6ae78d42dbc67c2613cb80c1e7f56f'},
                                                     'staged_callsites_sha256': {'Common/seq/seqload.c': '524018cc27f24d043d4f384a54b644c4983ddb0777b89196bb3189af0d4eb392',
                                                                                 'libs/UtilitiesLib/src/utils/FolderCache.c': '93aac8a9e1a59ca47ab5a067580c36f7ed884db51038577b0453756f55af1d4c',
                                                                                 'libs/UtilitiesLib/src/utils/FolderCacheNode.c': '36faafa73afd83361fb8e4f25e340961fae5fb9d33c298b1200be9a4b2a48524',
                                                                                 'libs/UtilitiesLib/src/utils/file.c': '8ad08c34d2fed652578e26f0ec1fab79419b40414644c6b8e1ccbc58694733e1'},
                                                     'stock_text_and_failure_fallback_preserved': True},
                                     'baseline_import_tables_exactly_preserved': True,
                                     'parser_changes_after_observer_exactly_one_helper_and_one_call': True},
              'complete_upstream_and_PhysX_source_trees_identical': {'d456f06cd82a921964a895885a03c67137cb9257': {'upstream/ouroboros': 'f634e21e230009fa8edc91d15429cd4da69eee8c',
                                                                                                                  'upstream/ouroboros/3rdparty/PhysX': '8dcff92f61c34ec8a7ab35440253e4740cd014bf',
                                                                                                                  'upstream/ouroboros/Common/NovodeX': '34351117a24d51e7bb131f11913849922d3e4f81',
                                                                                                                  'upstream/ouroboros/Common/gridcoll': '915aad2f63c0a6411da955277bd9f7f053aaa428',
                                                                                                                  'upstream/ouroboros/Common/group': '83adfe8abd79ee783cb8f7728a4b4986b4d70dfe'},
                                                                     'da5cf809925d9d91e029a117d8be184af03db2b6': {'upstream/ouroboros': 'f634e21e230009fa8edc91d15429cd4da69eee8c',
                                                                                                                  'upstream/ouroboros/3rdparty/PhysX': '8dcff92f61c34ec8a7ab35440253e4740cd014bf',
                                                                                                                  'upstream/ouroboros/Common/NovodeX': '34351117a24d51e7bb131f11913849922d3e4f81',
                                                                                                                  'upstream/ouroboros/Common/gridcoll': '915aad2f63c0a6411da955277bd9f7f053aaa428',
                                                                                                                  'upstream/ouroboros/Common/group': '83adfe8abd79ee783cb8f7728a4b4986b4d70dfe'},
                                                                     '47e40d4d586d29e273e31ed4d0d51d160832b89d': {'upstream/ouroboros': 'f634e21e230009fa8edc91d15429cd4da69eee8c',
                                                                                                                  'upstream/ouroboros/3rdparty/PhysX': '8dcff92f61c34ec8a7ab35440253e4740cd014bf',
                                                                                                                  'upstream/ouroboros/Common/NovodeX': '34351117a24d51e7bb131f11913849922d3e4f81',
                                                                                                                  'upstream/ouroboros/Common/gridcoll': '915aad2f63c0a6411da955277bd9f7f053aaa428',
                                                                                                                  'upstream/ouroboros/Common/group': '83adfe8abd79ee783cb8f7728a4b4986b4d70dfe'}},
              'unchanged_collision_geometry_cooking_source_pins': {'MapServer/src/beacon/beaconConnection.c': {'bytes': 157353,
                                                                                                               'sha256': '93422a659fd2e3da9d8a522512a17a32f13b817b7c04e819e3efa38579638340'},
                                                                   'Common/gridcoll/gridcoll.c': {'bytes': 15111,
                                                                                                  'sha256': 'e25032c077b32896353e79929e74c81d4735564e8a8714c0d7c739db883655d4'},
                                                                   'Common/NovodeX/NwWrapper.cpp': {'bytes': 115965,
                                                                                                    'sha256': 'd666fcf6dba5a15f7b2cffd1d6b9227ad2b4dbbb7ab598d47bb0c61911661db6'},
                                                                   'MapServer/src/beacon/beaconGenerate.c': {'bytes': 150968,
                                                                                                             'sha256': 'eeaf26ddb3b2f65628aece1c77a9ba272318dc3581e3379616dc86c3ee355c38'},
                                                                   'Common/NovodeX/NwCoreDump.cpp': {'bytes': 148672,
                                                                                                     'sha256': '727fb50ed2a8639955dcea596577c556a92f8ed3b47c392e74934b6f9fc12b8d'},
                                                                   'MapServer/src/beacon/beaconPath.c': {'bytes': 88817,
                                                                                                         'sha256': '40092b27b9b6b73e19349422570ce1f0978aedacb6cf0d648af858fd46b69e14'},
                                                                   'Common/group/groupnovodex.c': {'bytes': 18132,
                                                                                                   'sha256': '445614b01f26bac995957dab705c9cc4129818a71bcc041559282955ce30e782'},
                                                                   'MapServer/src/beacon/beaconFile.c': {'bytes': 79037,
                                                                                                         'sha256': '2693b3cd9eb2432248605810a167a4aed8ab71f569c8f2fdc89fe4aa4271ad60'},
                                                                   'Common/NovodeX/NwWrapper.h': {'bytes': 12725,
                                                                                                  'sha256': '074a256d48e9b324efd39acb43d7737ec8f8545610eab5d6f892bf457eec77f3'},
                                                                   'Common/group/groupfileload.c': {'bytes': 63848,
                                                                                                    'sha256': '5fc2891ed78626b9fa38b181fd5fc975b69f000bf2f79bbb3c5527c86503e8d7'}},
              'unchanged_collision_function_pins': {'Common/gridcoll/gridcoll.c::int collGrid(': {'bytes': 3681,
                                                                                                  'sha256': '7aea75468f6adbd356acedbb0c49a9d1b1435abd5748e27f5fc8d4f7267b9d89',
                                                                                                  'source_function_unchanged': True},
                                                    'Common/group/groupnovodex.c::static void createGroupDefNxShape(': {'bytes': 2653,
                                                                                                                        'sha256': '3c9874bab2ab6f6a9d04bb73884444185d441df0c14e3e16f5239558c6ca4eac',
                                                                                                                        'source_function_unchanged': True},
                                                    'Common/group/groupnovodex.c::int createNxWorldShapes(': {'bytes': 902,
                                                                                                              'sha256': 'be094622c03058e96a328b19de166f9fa13b305a2e11e82b2877f50cf5bd5fcb',
                                                                                                              'source_function_unchanged': True},
                                                    'Common/NovodeX/NwWrapper.cpp::void nwCreatePhysicsSDK(': {'bytes': 993,
                                                                                                               'sha256': '2afbe13eb5f028e9825e3db46576287048c89deb5baa6e42ffc1e8e7014e30d8',
                                                                                                               'source_function_unchanged': True},
                                                    'Common/NovodeX/NwWrapper.cpp::U8 nwCookMeshShape(': {'bytes': 1582,
                                                                                                          'sha256': '3b8381ffc28d47b39cd4ea4787c930795a525d8749f6f613b69799c1ff8a2db4',
                                                                                                          'source_function_unchanged': True},
                                                    'MapServer/src/beacon/beaconPath.c::void beaconPathFind(': {'bytes': 6948,
                                                                                                                'sha256': '566f84141266493b415beed1a9b703e3c8711f7363cadc43b088cb2b9adbd5a1',
                                                                                                                'source_function_unchanged': True}},
              'historical_cooking_and_SDK_runtime_DLLs_to_require_in_fresh_world_inputs': {'NxCharacter.dll': {'bytes': 107872,
                                                                                                               'sha256': '816fefac0c6b3d7da68daf3098a73e7fa0eff326ef83b3dba7f0fe2dcf0bd095'},
                                                                                           'NxCooking.dll': {'bytes': 749568,
                                                                                                             'sha256': '5dc0333de6b18119b04f7a1beace3f5dfaff5754af62a0f4d8def9e73a09063c'},
                                                                                           'PhysXCooking.dll': {'bytes': 383840,
                                                                                                                'sha256': 'c6a1a1f4127bef756e8628775de18c57f93bb7cce22403efb3b519ea1f26a28d'},
                                                                                           'PhysXCore.dll': {'bytes': 3567456,
                                                                                                             'sha256': 'c1758f8deada5dad54eb384b4f94a43f69b54c6f671cdcabef4f64d9c6f1da3a'},
                                                                                           'PhysXDevice.dll': {'bytes': 65536,
                                                                                                               'sha256': '6b9f40f2da693b935163935c7ab56847bf11f7160f5b268c4e4881d2973d9cb7'},
                                                                                           'PhysXLoader.dll': {'bytes': 64352,
                                                                                                               'sha256': 'db9ea1334a6364c4d02c2e3fe826ab48fb6b07242fff00bd41feb17524fde4de'},
                                                                                           'physxcudart_20.dll': {'bytes': 197912,
                                                                                                                  'sha256': 'e7b1965ab2ba441c2f4040f6203c10e7d9f02bfbb794a25d2a022d95b6f01c70'}},
              'staged_delta': {'modified_existing_translation_units': ['libs/UtilitiesLib/src/utils/textparser.c',
                                                                       'Common/seq/seqload.c'],
                               'shipping_to_observed_control': 'Source-local bounded '
                                                               'QueryPerformanceCounter '
                                                               'freshness/BIN/sequencer observers; '
                                                               'all original decode/freshness '
                                                               'operations and decisions retained',
                               'observed_control_to_metadata_candidate': 'One ordinary '
                                                                         'FolderCacheRequestTree(player_library/animations) '
                                                                         'after valid sequencers '
                                                                         'BIN dependency header; '
                                                                         'opt-in flag only, '
                                                                         'CRC/source-date/membership/decoder/fallback '
                                                                         'retained',
                               'retained_FolderCache_FolderNode_file_PIG_implementations': {'Common/fxinfo.c': '61f36247ec92e56395cc6548689c34b1e341283a25c78490627327eafd5e9a13',
                                                                                            'Common/seq/animtrackanimate.c': 'ad976409823db61d1610e3cece2ba323ffc7623af8be1c2c1ac8b38abdcebf21',
                                                                                            'Common/seq/seqload.c': '8c2761ceeabcc564f89d943780579a4f401ffb344f9ad6e7f5e73660c2b9b60f',
                                                                                            'libs/UtilitiesLib/src/utils/FolderCache.c': '93aac8a9e1a59ca47ab5a067580c36f7ed884db51038577b0453756f55af1d4c',
                                                                                            'libs/UtilitiesLib/src/utils/FolderCacheNode.c': '36faafa73afd83361fb8e4f25e340961fae5fb9d33c298b1200be9a4b2a48524',
                                                                                            'libs/UtilitiesLib/src/utils/PigFileWrapper.c': 'e4347a4694045a559c8db4d97d4dfc60748378d272e4365508ace3e2ef90909e',
                                                                                            'libs/UtilitiesLib/src/utils/file.c': '8ad08c34d2fed652578e26f0ec1fab79419b40414644c6b8e1ccbc58694733e1',
                                                                                            'libs/UtilitiesLib/src/utils/piglib.c': '786ea2c5e9b8cf14fe4dfd4880b9cfe85a138afbccd56759e59b30b7663ed528',
                                                                                            'libs/UtilitiesLib/src/utils/textparser.c': '22be253a9e48e2565086e051d469ff92e68c2ae5a84802d8dc3d90713c766fef'},
                               'retained_staged_svr_init_door_svr_tick_build_recipe': {'MapServer/CMakeLists.txt': '88e9cc8e0eb9b4d50cd379062d7b1f993f0883c2977daf80df57507fe0f5af14',
                                                                                       'MapServer/src/door.c': '8bf53acf10f29b7f20ce96322d04f69201be9090a2fafe1ae95ac43b6a3aa2ce',
                                                                                       'MapServer/src/svr/svr_init.c': '398081161ebe9e9253b326e8a5f94f502a7bc0a9974a442f1ce83a46ee0f9ae3',
                                                                                       'MapServer/src/svr/svr_tick.c': 'a3810c112556b258ee2456a51eb28d6afeefd14b81c2fa97ed431659ae42a3d5'},
                               'no_global_SDK_ownership_cooking_geometry_source_or_recipe_change': True,
                               'new_owned_bounded_PhysX_stream_prototype_integrated': False},
              'qualification_boundary': {'fresh_actual_native_preload_source': '9454e7892ac81cf4503fd8ad961dc36c27cfc152',
                                         'fresh_actual_native_preload_run': 38352862725,
                                         'fresh_full_world_gate_source': '365c6f967c351b3f2ba0b2ea408e10d139bfc2a5',
                                         'fresh_full_world_gate_run': 38480106638,
                                         'fresh_full_world_status': 'in_progress_no_actual_output_artifact_yet',
                                         'required_fresh_facts': ['both Atlas1/7001 and '
                                                                  'Kings5/7003 actual native Db '
                                                                  'status and post-query held-PID '
                                                                  'Map tick advance',
                                                                  'exact full and SERVER-only FX '
                                                                  'consumption and generated '
                                                                  'BIN/ID/provider/graph/geometry '
                                                                  'bytes',
                                                                  'native PhysX object counts '
                                                                  'Atlas2311 Kings2166 and loaded '
                                                                  'spore grid',
                                                                  'actual SDK/cooking DLL hashes '
                                                                  'equal retained shipping '
                                                                  'identity',
                                                                  'native certified animation '
                                                                  'subset counts unchanged',
                                                                  'bounded Map memory '
                                                                  'working-set/privatecommit '
                                                                  'observations'],
                                         'fresh_world_behavioral_collision_proven': False,
                                         'historical_behavior_inherited_under_original_producer_identities': True,
                                         'inherited_graph_gate': 'Original Assets1.0.0 Atlas/Kings '
                                                                 'graph locks and source-bound '
                                                                 'complete geometry inventory; '
                                                                 'older dedicated native generator '
                                                                 'full-graph readback, fresh '
                                                                 'ordinary-world CRC, and32 native '
                                                                 'pathfinder successes in '
                                                                 'cold/reopened layouts',
                                         'inherited_physical_behavior': 'User observed working '
                                                                        'movement/graphics/combat/actual '
                                                                        'native monorail and '
                                                                        'committed saves under '
                                                                        'retained old native Map; '
                                                                        'latest .36 session '
                                                                        'observations remain bound '
                                                                        'to actualuploaded '
                                                                        'outerZIPs andoriginal Map '
                                                                        'identity',
                                         'physical_candidate_acceptance_required': 'Existing saved '
                                                                                   'character '
                                                                                   'movement/powers/graphics/combat/normal '
                                                                                   'save/export '
                                                                                   'and genuine '
                                                                                   'monorail under '
                                                                                   'candidate '
                                                                                   'remains a '
                                                                                   'subsequent '
                                                                                   'Thor test; '
                                                                                   'timing goals '
                                                                                   'unproven'},
              'unsafe_existing_colltest_not_executed': {'source': 'upstream/ouroboros/Common/gridcoll/gridcollperftest.c',
                                                        'hardcoded_file': 'C:/temp/gridcoll.bin',
                                                        'loop': 'unbounded',
                                                        'input_records': 'unchecked raw CollRecord '
                                                                         'array',
                                                        'executed': False}}}
RUNTIME_CACHE_PROOF_DERIVATION = None
RUNTIME_CACHE_DERIVATION_SCOPE = {
    "derived_by_source_reviewed_normalizer": True, "original_artifact_membership_claimed": False,
    "native_ID_tables_observed": False, "shipping_bytes_executed_claimed": False,
    "behavioral_collision_validated": False, "physical_timing_validated": False}
SOURCE_ONLY_REVIEW_SCOPE = {'source_compatibility_only': True,
    'shipping_predecessor_execution_validated': False, 'new_native_runtime_qualification_proven': False,
    'runtime_activation_allowed': False, 'shipping_allowed': False,
    'native_ID_tables_observed': False, 'behavioral_collision_validated': False,
    'physical_timing_validated': False}


def inspect_committed_source_review(descriptor, *, previous_shipping_consumer_sha256,
        actual_tested_control_consumers, actual_tested_candidate):
    """Bind source commit/path/blob/content and its exact nonexecution scope.

    The source-pinned document is embedded only after packaging independently
    checks the committed blob. It is never invented as a member of native ZIPs.
    Production authority remains absent until that separate review is frozen.
    """
    import native_startup_metadata_contract as metadata
    authority = SOURCE_ONLY_COMPATIBILITY_REVIEW
    require(type(authority) is dict and set(authority) == {'descriptor', 'document'},
        'Independent committed source-only compatibility review is not frozen')
    require(type(descriptor) is dict and set(descriptor) == {'repository', 'commit', 'path',
        'git_blob', 'content', 'scope'} and metadata.same(descriptor, authority['descriptor'])
        and descriptor['repository'] == 'Russianranger/coh-android'
        and re.fullmatch(r'[0-9a-f]{40}', str(descriptor['commit']))
        and re.fullmatch(r'[0-9a-f]{40}', str(descriptor['git_blob']))
        and type(descriptor['path']) is str
        and re.fullmatch(r'docs/android-evidence/[A-Za-z0-9_.-]{1,100}\.json', descriptor['path'])
        and metadata.same(descriptor['scope'], SOURCE_ONLY_REVIEW_SCOPE),
        'Committed source-only review identity/scope differs')
    document = authority['document']; raw = metadata.encoded(document)
    require(metadata.pin(raw) == metadata.pin_record(descriptor['content'], 8*1024**2)
        and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == descriptor['git_blob'],
        'Committed source review content or Git blob differs')
    require(type(document) is dict and type(document.get('format')) is int and document['format'] == 1
        and document.get('role') == 'narrow_Map_metadata_consumer_source_and_historical_collision_boundary'
        and document.get('status') == 'source_delta_verified_fresh_world_gate_pending'
        and document.get('shipping_allowed') is False
        and document.get('physical_candidate_behavior_measured') is False
        and document.get('qualification_boundary', {}).get('fresh_world_behavioral_collision_proven') is False,
        'Source-only pending qualification review was promoted into execution/behavior evidence')
    shipping = metadata.native_record_pin(document['shipping_036']['MapServer'])
    observed = document['observed_control']
    audited_controls = [metadata.native_record_pin(observed[name]) for name in ('unobserved_control', 'observed_Map')]
    candidate = metadata.native_record_pin(document['metadata_candidate']['native'])
    require(shipping['sha256'] == previous_shipping_consumer_sha256
        and metadata.same(candidate, actual_tested_candidate)
        and type(actual_tested_control_consumers) is list and actual_tested_control_consumers
        and len(actual_tested_control_consumers) <= 8
        and len({row['sha256'] for row in actual_tested_control_consumers}) == len(actual_tested_control_consumers)
        and all(any(metadata.same(row, audited) for audited in audited_controls) for row in actual_tested_control_consumers),
        'Source review shipping predecessor, actual tested controls or candidate differ')
    build = document['metadata_candidate']['build_input']
    require(observed.get('shipping_base_recipe_exactly_equal') is True
        and document['metadata_candidate'].get('baseline_import_tables_exactly_preserved') is True
        and build.get('native_decoder_preserved') is True and build.get('CRC_and_schema_checks_preserved') is True
        and build.get('freshness_body_exact_except_request') is True
        and build.get('source_date_and_membership_checks_preserved') is True
        and build.get('stock_text_and_failure_fallback_preserved') is True
        and build.get('provider_precedence_preserved') is True
        and build.get('native_execution_validated') is False and build.get('physical_savings_validated') is False
        and build.get('publication_allowed') is False,
        'Committed source decoder/schema/SDK compatibility boundary differs')
    trees = document.get('complete_upstream_and_PhysX_source_trees_identical')
    require(type(trees) is dict and len(trees) == 3
        and len({metadata.canonical_sha(row) for row in trees.values()}) == 1,
        'Committed upstream/SDK source equivalence closure differs')
    return {'committed_source_review': copy.deepcopy(descriptor), 'scope': copy.deepcopy(SOURCE_ONLY_REVIEW_SCOPE),
        'previous_shipping_consumer': shipping, 'audited_control_consumers': audited_controls,
        'actual_tested_control_consumers': copy.deepcopy(actual_tested_control_consumers),
        'actual_tested_candidate': candidate,
        'source_decoder_and_schema_checks_preserved': True, 'upstream_sdk_source_trees_identical': True,
        'native_execution_or_physical_results_added_by_source_review': False}



def inspect_runtime_cache_derivation(descriptor):
    """A derived flat proof has its own source/raw-input/output authority.

    Original producer/recovery/qualification ZIPs keep their exact members.
    No generated proof is invented as a native artifact member.
    """
    import native_startup_metadata_contract as metadata
    expected = RUNTIME_CACHE_PROOF_DERIVATION
    require(type(expected) is dict and metadata.same(descriptor, expected)
        and set(descriptor) == {'derivation_source', 'raw_inputs', 'output', 'scope'}
        and metadata.same(descriptor['scope'], RUNTIME_CACHE_DERIVATION_SCOPE),
        'Independent source-reviewed runtime cache derivation is not frozen or differs')
    source = descriptor['derivation_source']
    require(type(source) is dict and set(source) == {'repository_commit', 'path', 'git_blob', 'pin'}
        and re.fullmatch(r'[0-9a-f]{40}', str(source['repository_commit']))
        and re.fullmatch(r'[0-9a-f]{40}', str(source['git_blob']))
        and type(source['path']) is str and source['path'].startswith('tools/')
        and source['path'].endswith('.py') and ':' not in source['path'] and '\\' not in source['path']
        and all(part not in ('', '.', '..') for part in source['path'].split('/')),
        'Exact committed derivation source identity required')
    metadata.pin_record(source['pin'], 2*1024**2)
    inputs = descriptor['raw_inputs']
    base_inputs = {'preload', 'native_world', 'client_cache_manifest', 'server_cache_manifest'}
    require(type(inputs) is dict and set(inputs) in (base_inputs, base_inputs | {'inherited_native_world'}),
        'Exact raw preload/world/original manifest input closure required')
    for kind in ('preload', 'native_world', *(('inherited_native_world',) if 'inherited_native_world' in inputs else ())):
        row = inputs[kind]
        require(type(row) is dict and set(row) == {'repository_commit', 'run_id', 'artifact_id',
            'artifact_zip', 'member', 'member_pin'}
            and re.fullmatch(r'[0-9a-f]{40}', str(row['repository_commit']))
            and all(type(row[key]) is int and row[key] > 0 for key in ('run_id', 'artifact_id'))
            and type(row['member']) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', row['member'])
            and row['member'] not in ('.', '..'), 'Exact immutable raw native report provenance required')
        metadata.pin_record(row['artifact_zip'], 4*1024**3)
        metadata.pin_record(row['member_pin'], (64 if kind == 'native_world' else 8)*1024**2)
        if kind == 'inherited_native_world':
            require(metadata.same(row, {'repository_commit': '04b7a623ef21d7ad48774a58b3122c69ae07f46b',
                'run_id': 38494199595, 'artifact_id': 11864550716,
                'artifact_zip': {'bytes': 3039985, 'sha256': '962d7517ca5d91dd00b797f5b428bdf5fce1975c6c4afc392f7dc9e0a24b06fc'},
                'member': 'native-map-world-037-qualification.json',
                'member_pin': {'bytes': 1039965, 'sha256': 'c2c3d768a4269f665a0e3d8651054a63a188be9f815faea974fea98fe82207c7'}}),
                'Only the separately authenticated original failed04b raw stock report may be inherited')
    for kind in ('client_cache_manifest', 'server_cache_manifest'):
        row = inputs[kind]
        require(type(row) is dict and set(row) == {'component_zip', 'member', 'member_pin', 'origin'}
            and row['origin'] == 'exact_public_Assets_1_0_0_component'
            and row['member'] == ('client-cache-manifest.json' if kind == 'client_cache_manifest' else 'server-cache-manifest.json'),
            'Original donor must retain public component provenance, not invented native producer IDs')
        metadata.pin_record(row['component_zip'], 512*1024**2); metadata.pin_record(row['member_pin'], 4*1024**2)
    output = descriptor['output']
    require(type(output) is dict and set(output) == {'filename', 'pin'}
        and type(output['filename']) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', output['filename'])
        and output['filename'] not in ('.', '..'), 'Exact derived flat proof output identity required')
    metadata.pin_record(output['pin'], 8*1024**2)
    return copy.deepcopy(descriptor)


def runtime_cache_derivation_statement(descriptor):
    """Embed only source/input/scope facts; the output pin lives externally."""
    return {key: copy.deepcopy(descriptor[key]) for key in ('derivation_source', 'raw_inputs', 'scope')}


def metadata_admission(package, path=None):
    import native_startup_metadata_contract as metadata
    return (metadata.runtime_admission(package, 'mapserver', path)
            if isinstance(package, dict) and metadata.WRAPPER in package else None)


def legacy_package(package):
    """Restore old protocol/producer facts; this never aliases current bytes."""
    admitted = metadata_admission(package)
    return package if admitted is None else admitted['previous_package']


def current_consumer_evidence(admitted):
    return {key: admitted[key] for key in ('authority_sha256', 'execution_review_sha256',
        'current_consumer_sha256', 'previous_consumer_sha256', 'qualified_maps',
        'runtime_activation_allowed', 'physical_timing_validated', 'behavioral_collision_validated', 'native_producer')}


def verify_metadata_cache_context(path, package, context):
    """No old cache identity without independently prepared provider/BIN facts.

    Callers supply a context from their authenticated current provider and
    native cache qualification. The component's own compatibility receipt is
    never used as a substitute for those actual inputs. Missing context fails
    so preparation keeps a distinct generation and the ordinary native loader.
    """
    admitted = metadata_admission(package, path)
    require(admitted is not None and type(context) is dict and set(context) == {
        'provider_identity_sha256', 'bin_recipe_identity_sha256', 'original_proof_sha256',
        'qualified_per_bin'}, 'Actual metadata provider/recipe/BIN qualification context required')
    import native_startup_metadata_contract as metadata
    proof = metadata.cache_compatibility(package, 'mapserver',
        previous_consumer_sha256=admitted['previous_consumer_sha256'],
        provider_identity_sha256=context['provider_identity_sha256'],
        bin_recipe_identity_sha256=context['bin_recipe_identity_sha256'],
        original_proof_sha256=context['original_proof_sha256'])
    require(metadata.same(context['qualified_per_bin'], proof['qualified_per_bin']),
        'Actual per-BIN outputs/schema/identifier inputs/loader decisions differ')
    return {**proof, 'current_execution': current_consumer_evidence(admitted),
        'runtime_activation_allowed': True}


def verify_metadata_collision_graph(path, package, *, map_id, manifest_sha256, retained_collision_sources):
    admitted = metadata_admission(package, path)
    require(admitted is not None and type(map_id) is int and map_id in admitted['qualified_maps']
        and isinstance(manifest_sha256, str) and re.fullmatch(r'[0-9a-f]{64}', manifest_sha256),
        'Current consumer lacks this exact native world qualification')
    import native_startup_metadata_contract as metadata
    old = embedded_receipt(admitted['previous_package'])
    bridge = admitted['receipt']['compatibility'].get('collision')
    previous_files = admitted['previous_package']['files']
    retained = {name: record for name, record in previous_files.items() if name != 'MapServer.exe'}
    require(type(bridge) is dict and set(bridge) == {'policy', 'current_consumer_sha256',
        'retained_collision_sources', 'retained_native_files_sha256', 'graph_manifests'}
        and bridge['policy'] == 'exact_retained_collision_sdk_geometry_and_graph'
        and bridge['current_consumer_sha256'] == admitted['current_consumer_sha256']
        and metadata.same(bridge['retained_collision_sources'], retained_collision_sources)
        and metadata.same(old['build_input']['monorail_build_input'].get('retained_collision_sources'), retained_collision_sources)
        and bridge['retained_native_files_sha256'] == metadata.canonical_sha(retained)
        and type(bridge['graph_manifests']) is dict and set(bridge['graph_manifests']) == {'1', '5'}
        and all(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) for value in bridge['graph_manifests'].values())
        and bridge['graph_manifests'][str(map_id)] == manifest_sha256,
        'Current metadata consumer lacks exact collision/SDK/graph parity')
    return {'current_execution': current_consumer_evidence(admitted), 'map_id': map_id,
        'graph_manifest_sha256': manifest_sha256, 'historical_graph_producer_preserved': True,
        'retained_native_files_sha256': bridge['retained_native_files_sha256'],
        'behavioral_collision_validated': False, 'physical_timing_validated': False}


def same(first, second):
    return json.dumps(first, sort_keys=True, separators=(',', ':'), allow_nan=False) == json.dumps(second, sort_keys=True, separators=(',', ':'), allow_nan=False)

def compact_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def canonical_sha(value):
    return monorail.canonical_sha(value)

def file_pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Current MapServer must be a regular owned payload')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): digest.update(block)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}

def pin_record(row):
    require(isinstance(row, dict) and type(row.get('bytes', row.get('size'))) is int
        and 0 < row.get('bytes', row.get('size')) <= 64*1024*1024
        and monorail.retained.HEX64.fullmatch(str(row.get('sha256'))), 'Map startup byte pin differs')
    return {'bytes': row.get('bytes', row.get('size')), 'sha256': row['sha256']}

ANIMATION_SOURCE_SHA256 = {'Common/seq/animtrack.c': 'a8f07b2a46d9a45640770707d5730ddc2f9f53cfbde3dd546f66ec9e89dfd50e'}

ANIMATION_PATCHED_SHA256 = {'Common/seq/animtrack.c': '37061a3801e6e943b2d2f34414ae0191045c0e08415761889253cd8c5a93ccd2'}

ANIMATION_OVERLAY_SHA256 = {'Common/seq/coh_animation_certificate.h': 'e099c3136045dff355ed4a334b0962badeb9ca39d89c942d410cce713c1e8c4b', 'Common/seq/coh_animation_certificate_table.h': '179f8a15614dd42c9222be4d3716986bc9c0716a41d6045ef8f2ef7dc83427c4'}

RETAINED_SOURCES_SHA256 = {'Common/fxinfo.c': '61f36247ec92e56395cc6548689c34b1e341283a25c78490627327eafd5e9a13', 'Common/seq/seqload.c': '8c2761ceeabcc564f89d943780579a4f401ffb344f9ad6e7f5e73660c2b9b60f', 'Common/seq/animtrackanimate.c': 'ad976409823db61d1610e3cece2ba323ffc7623af8be1c2c1ac8b38abdcebf21', 'libs/UtilitiesLib/src/utils/textparser.c': '22be253a9e48e2565086e051d469ff92e68c2ae5a84802d8dc3d90713c766fef', 'libs/UtilitiesLib/src/utils/file.c': '8ad08c34d2fed652578e26f0ec1fab79419b40414644c6b8e1ccbc58694733e1', 'libs/UtilitiesLib/src/utils/FolderCache.c': '93aac8a9e1a59ca47ab5a067580c36f7ed884db51038577b0453756f55af1d4c', 'libs/UtilitiesLib/src/utils/FolderCacheNode.c': '36faafa73afd83361fb8e4f25e340961fae5fb9d33c298b1200be9a4b2a48524', 'libs/UtilitiesLib/src/utils/piglib.c': '786ea2c5e9b8cf14fe4dfd4880b9cfe85a138afbccd56759e59b30b7663ed528', 'libs/UtilitiesLib/src/utils/PigFileWrapper.c': 'e4347a4694045a559c8db4d97d4dfc60748378d272e4365508ace3e2ef90909e'}

ANIMATION_CONTRACT = {'format': 1, 'policy': 'actual_opened_pig_raw_bytes_full_sha256_before_pointer_fixup', 'server_only': True, 'build_targets': ['MapServer'], 'certified_tracks': 5878, 'certificate_schema': 1, 'validator_version': 'original-win32-animation-loader-numeric-and-bounded-structure-v1', 'bounded_structure_and_offsets_always_checked': True, 'full_position_and_rotation_payloads_retained': True, 'base_skeleton_linking_retained': True, 'stock_key_validation_fallback': ['loose_input', 'unknown_name', 'changed_bytes', 'crypto_failure', 'header_only'], 'client_or_renderer_changes': False, 'environment_trust_switch': False, 'physical_startup_timing_validated': False}

def validate_animation_certificate(value):
    import server_animation_package as animation
    require(isinstance(value, dict) and type(value.get('format')) is int and value['format'] == 1
        and value.get('role') == 'server_raw_animation_certificate'
        and value.get('validator_version') == ANIMATION_CONTRACT['validator_version']
        and type(value.get('validated_track_count')) is int and value['validated_track_count'] == 5878
        and type(value.get('validated_raw_bytes')) is int and value['validated_raw_bytes'] == 88380730
        and value.get('rotation_key_count') == 11894088 and value.get('position_key_count') == 2083384
        and value.get('original_animation_pack') == {'animation_count': 5878, 'bytes': 97084456,
            'metadata_bytes': 8703726, 'original_animation_bytes': 88380730, 'sha256': PACK_SHA256}
        and value.get('generated_table') == {'bytes': 1363915, 'sha256': TABLE_SHA256}
        and hashlib.sha256((json.dumps(value.get('dependency_closure'), sort_keys=True,
            separators=(',', ':'), allow_nan=False) + '\n').encode()).hexdigest() == DEPENDENCY_SHA256
        and value.get('native_execution_validated') is False
        and value.get('physical_startup_timing_validated') is False,
        'Map startup original animation certification differs')
    require(same(value.get('original_animation_identity'), animation.identity()),
        'Map startup animation donor history changed')
    require(isinstance(value.get('validator_sources'), dict) and value['validator_sources'],
        'Map startup animation validator sources missing')
    return value

def previous_package(package):
    package = legacy_package(package)
    require(isinstance(package, dict) and isinstance(package.get('native_map_startup'), dict),
        'Missing additive Map startup receipt')
    previous = copy.deepcopy(package)
    wrapper = previous.pop('native_map_startup')
    previous['files']['MapServer.exe'] = copy.deepcopy(wrapper.get('receipt', {}).get('previous_mapserver'))
    return previous

def embedded_receipt(package):
    package = legacy_package(package)
    wrapper = package.get('native_map_startup', {})
    receipt = wrapper.get('receipt', {})
    require(isinstance(wrapper, dict) and set(wrapper) == {'receipt', 'receipt_sha256'}
        and isinstance(receipt, dict) and type(receipt.get('format')) is int and receipt['format'] == 1 and receipt.get('role') == ROLE
        and re.fullmatch(r'[0-9a-f]{40}', str(receipt.get('repository_commit')))
        and receipt.get('source_commit') == package.get('source_commit') == SOURCE
        and receipt.get('data_commit') == package.get('data_commit') == DATA
        and wrapper['receipt_sha256'] == canonical_sha(receipt), 'Map startup receipt identity differs')
    previous = previous_package(package)
    old = monorail.embedded_receipt(previous)
    require(previous['native_monorail']['receipt_sha256'] == PREVIOUS_RECEIPT_SHA256
        and old['mapserver']['sha256'] == PREVIOUS_SHA256 and pin_record(old['mapserver'])['bytes'] == 6892032
        and same(receipt.get('previous_mapserver'), old['mapserver']), 'Map startup changed the accepted station donor')
    build = receipt.get('build_input', {})
    certificate = validate_animation_certificate(build.get('animation_certificate'))
    budget = build.get('monorail_budget', {})
    require(type(budget.get('schema_version')) is int and budget['schema_version'] == 1 and budget.get('build_role') == 'map_startup_monorail_budget'
        and budget.get('source_sha256') == {'MapServer/src/svr/wine_monorail.c': '002957b67a841cb650c67412b7fcd3a159e02000a358c29c591d8049f23acf56'}
        and budget.get('patched_sha256') == {'MapServer/src/svr/wine_monorail.c': '3bd765cddc3975d2ca9c4f69f36b6cdd21ae0454068c33bd437a1fb3e21c57ad'}
        and budget.get('retained_sources_sha256') == {'MapServer/src/svr/wine_monorail.h': 'e4fef174151cf1595275039e5155213ce3d2f1673b377a0cd606d31b35f6fba9'}
        and same(budget.get('base_monorail_contract'), monorail.CONTRACT)
        and budget.get('base_monorail_contract_canonical_sha256') == compact_sha(monorail.CONTRACT)
        and same(budget.get('contract'), dict(monorail.CONTRACT, station_preparation_timeout_seconds=720))
        and budget.get('patch_scope') == 'one_exact_native_station_pending_timeout_literal_only'
        and budget.get('guest_absolute_cap_basis') == 'validated_native_request_utc_ms_plus_720000'
        and budget.get('expiry_comparison') == 'strictly_greater_than_720000_milliseconds'
        and budget.get('native_fixture_required') is True and budget.get('runtime_validation') == 'unverified'
        and budget.get('physical_startup_timing_validated') is False
        and build.get('monorail_budget_canonical_sha256') == compact_sha(budget),
        'Map startup native station budget source/clock differs')
    require(type(build.get('schema_version')) is int and build['schema_version'] == 1 and build.get('build_role') == 'map_startup_certified_animation'
        and build.get('source_commit') == SOURCE and build.get('build_targets') == ['MapServer']
        and build.get('runtime_validation') == 'unverified'
        and build.get('animation_certificate_canonical_sha256') == compact_sha(certificate)
        and build.get('source_sha256') == dict(ANIMATION_SOURCE_SHA256, **budget['source_sha256'])
        and build.get('patched_sha256') == dict(ANIMATION_PATCHED_SHA256, **budget['patched_sha256'])
        and build.get('overlay_sha256') == ANIMATION_OVERLAY_SHA256
        and build.get('retained_sources_sha256') == RETAINED_SOURCES_SHA256
        and same(build.get('contract'), dict(ANIMATION_CONTRACT,
            native_station_prepare_seconds=720, historical_station_prepare_seconds=600)), 'Map startup source scope or ABI differs')
    base = build.get('monorail_build_input', {})
    require(build.get('monorail_build_input_canonical_sha256') == compact_sha(base),
        'Map startup station source ancestry digest differs')
    # Preserve both LF/CRLF PG histories through the existing narrow ancestry
    # comparator; every monorail source and protocol field remains exact.
    a, b = copy.deepcopy(base), copy.deepcopy(old['build_input'])
    for item in (a, b): item.pop('events_build_input', None); item.pop('events_build_input_canonical_sha256', None)
    require(same(a, b), 'Map startup changed the retained station bridge sources')
    original = copy.deepcopy(previous); original.pop('native_monorail')
    original['files']['MapServer.exe'] = old['previous_mapserver']
    accepted = monorail.retained.embedded_receipt(original)
    comparison = copy.deepcopy(accepted['build_inputs'])
    comparison['character_events'] = base.get('events_build_input')
    monorail.retained.scene_source_inputs_equivalent(comparison, accepted['build_inputs'])
    current = monorail.retained.pe_record(receipt.get('mapserver'))
    require(package.get('files', {}).get('MapServer.exe') == current
        and current['sha256'] != PREVIOUS_SHA256
        and current.get('imports') == old['mapserver'].get('imports')
        and current.get('delay_imports') == old['mapserver'].get('delay_imports')
        and receipt.get('retained_native_files') == {n:r for n,r in package['files'].items() if n != 'MapServer.exe'}
        and len(receipt['retained_native_files']) == 24
        and receipt.get('schema_sources_sha256') == old['schema_sources_sha256'],
        'Map startup changed native dependencies or Parse6 schemas')
    require(re.fullmatch(r'[0-9a-f]{40}', str(receipt.get('native_build_repository_commit')))
        and pin_record(receipt.get('native_build_manifest'))
        and pin_record(receipt.get('native_fixture'))
        and pin_record(receipt.get('native_monorail_fixture'))
        and pin_record(receipt.get('fx_qualification'))
        and receipt.get('physical_timing_validated') is False
        and receipt.get('native_gameplay_validated') is False,
        'Map startup component provenance/scope missing')
    return receipt

def verify_current_map(path, package):
    admitted = metadata_admission(package, path)
    if admitted is not None:
        # Historical parser/source claims stay nested in their original proof.
        # This current component changes textparser and sequencer observation.
        previous = admitted['previous_package']
        receipt = embedded_receipt(previous)
        historical = {'mapserver_sha256': receipt['mapserver']['sha256'],
            'native_build_repository_commit': receipt['native_build_repository_commit'],
            'native_build_manifest': receipt['native_build_manifest'],
            'native_map_startup_receipt_sha256': previous['native_map_startup']['receipt_sha256']}
        return {'format': 1, 'policy': 'explicit_reviewed_metadata_current_consumer',
            'actual_mapserver_sha256': admitted['current_consumer_sha256'],
            'previous_startup_mapserver_sha256': admitted['previous_consumer_sha256'],
            'original_cache_donor_mapserver_sha256': receipt['build_input']['animation_certificate']['original_animation_identity']['mapserver_sha256'],
            'historical_startup_producer': historical,
            'current_execution': current_consumer_evidence(admitted),
            'cache_donor_identity_preserved': False,
            'cache_provider_recipe_reuse_requires_separate_proof': True,
            'animation_identity_preserved': True, 'native_animation_reader_changed': True,
            'parser_or_definition_sources_changed': True,
            'behavioral_collision_validated': False, 'physical_loading_gain_validated': False}
    receipt = embedded_receipt(package)
    require(file_pin(path) == pin_record(receipt['mapserver']), 'Current MapServer bytes differ from startup source receipt')
    return {'format': 1, 'policy': 'qualified_startup_overlay_preserves_original_cache_and_graph_history',
        'actual_mapserver_sha256': receipt['mapserver']['sha256'],
        'previous_monorail_mapserver_sha256': PREVIOUS_SHA256,
        'original_cache_donor_mapserver_sha256': receipt['build_input']['animation_certificate']['original_animation_identity']['mapserver_sha256'],
        'cache_donor_identity_preserved': True, 'animation_identity_preserved': True,
        'native_animation_reader_changed': True, 'parser_or_definition_sources_changed': False,
        'native_build_repository_commit': receipt['native_build_repository_commit'],
        'native_build_manifest': receipt['native_build_manifest'],
        'native_map_startup_receipt_sha256': package['native_map_startup']['receipt_sha256'],
        'physical_loading_gain_validated': False}

def progress_contract(package):
    admitted = metadata_admission(package)
    receipt = embedded_receipt(package)
    result = {'contract': receipt['build_input']['monorail_build_input']['events_build_input']['progress_contract'],
        'producer': {'repository_commit': receipt['native_build_repository_commit'],
            'manifest_sha256': receipt['native_build_manifest']['sha256'],
            'mapserver_sha256': receipt['mapserver']['sha256']}}
    if admitted is not None:
        result['current_consumer'] = current_consumer_evidence(admitted)
    return result
