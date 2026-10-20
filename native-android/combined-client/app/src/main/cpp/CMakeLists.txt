cmake_minimum_required(VERSION 3.22.1)
project(coh_combined_client LANGUAGES C)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
get_filename_component(NATIVE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../.." ABSOLUTE)
# Build the exact accepted renderer sources as a dependency. The new network
# owner never publishes inspected server messages into this local preview.
add_subdirectory("${NATIVE_ROOT}/session-client/app/src/main/cpp" "${CMAKE_CURRENT_BINARY_DIR}/accepted-scene")

if(NOT DEFINED COH_CRYPTO_ROOT OR COH_CRYPTO_ROOT STREQUAL "")
    message(FATAL_ERROR "COH_CRYPTO_ROOT must name a pinned public Android crypto build")
endif()
if(EXISTS "${COH_CRYPTO_ROOT}/${ANDROID_ABI}/receipt.json")
    set(CRYPTO_ABI_ROOT "${COH_CRYPTO_ROOT}/${ANDROID_ABI}")
else()
    set(CRYPTO_ABI_ROOT "${COH_CRYPTO_ROOT}")
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/verify_crypto.py"
    "${CRYPTO_ABI_ROOT}" "${ANDROID_ABI}" "${NATIVE_ROOT}/engine/auth/android/openssl-source.json"
    RESULT_VARIABLE VERIFY_CRYPTO)
if(NOT VERIFY_CRYPTO EQUAL 0)
    message(FATAL_ERROR "Public Android crypto provenance/hash verification failed")
endif()
set(ENGINE "${NATIVE_ROOT}/engine")
add_library(coh_combined_network SHARED combined_network.c process_memory_jni.c
    "${ENGINE}/perf/coh_process_memory.c" "${ENGINE}/perf/coh_perf_bridge.c" "${ENGINE}/perf/coh_perf.c"
    "${ENGINE}/local/coh_local.c"
    "${ENGINE}/dbclient/coh_dbclient.c" "${ENGINE}/dbclient/coh_db_session.c"
    "${ENGINE}/dbclient/coh_db_account_controls.c"
    "${ENGINE}/mapclient/coh_mapclient.c" "${ENGINE}/mapclient/coh_mapclient_owned.c"
    "${ENGINE}/replication/coh_replication.c"
    "${ENGINE}/replication/coh_groups.c"
    "${ENGINE}/network/coh_net.c" "${ENGINE}/network/coh_net_frame.c"
    "${ENGINE}/network/coh_net_zip.c" "${ENGINE}/network/coh_net_udp.c"
    "${ENGINE}/auth/coh_auth.c" "${ENGINE}/auth/coh_auth_openssl.c"
    "${ENGINE}/session/coh_session_crypto.c"
    "${NATIVE_ROOT}/protocol/coh_protocol.c" "${NATIVE_ROOT}/src/coh_blowfish.c")
target_include_directories(coh_combined_network PRIVATE "${ENGINE}/local" "${ENGINE}/session"
    "${NATIVE_ROOT}/include" "${CRYPTO_ABI_ROOT}/include" "${ENGINE}/perf")
target_compile_features(coh_combined_network PRIVATE c_std_11)
target_compile_options(coh_combined_network PRIVATE -Wall -Wextra -Werror -ffp-contract=off)
target_link_options(coh_combined_network PRIVATE -Wl,--no-undefined -Wl,-z,defs)
target_link_libraries(coh_combined_network PRIVATE "${CRYPTO_ABI_ROOT}/lib/libcrypto.a" z dl)

# Explicit nonshipping Gates 25-27 observation role. Its Map/Local and transport
# replacements keep the original production sources separate from the default
# client; an observed initial packet grants no actor, ACK or world authority.
add_library(coh_combined_interop SHARED interop_network.c
    "${ENGINE}/initial-capture/coh_initial_create_probe.c"
    "${ENGINE}/initial-capture/coh_initial_pose_probe.c"
    "${ENGINE}/initial-capture/coh_initial_sequence_probe.c"
    "${ENGINE}/initial-capture/coh_initial_triggered_probe.c"
    "${ENGINE}/initial-capture/coh_initial_aianim_probe.c"
    "${ENGINE}/initial-capture/coh_initial_netfx_probe.c"
    "${ENGINE}/initial-capture/coh_initial_costume_probe.c"
    "${ENGINE}/initial-capture/coh_initial_reward_probe.c"
    "${ENGINE}/initial-capture/coh_initial_reward_list_probe.c"
    "${ENGINE}/initial-capture/coh_initial_costume_slots_probe.c"
    "${ENGINE}/initial-capture/coh_initial_costume_body_probe.c"
    "${ENGINE}/initial-capture/coh_initial_appearance_probe.c"
    "${ENGINE}/initial-capture/coh_initial_sgcolors_probe.c"
    "${ENGINE}/initial-capture/coh_initial_scales_probe.c"
    "${ENGINE}/initial-capture/coh_initial_partcount_probe.c"
    "${ENGINE}/initial-capture/coh_local_bodypart_default.c"
    "${ENGINE}/entities/coh_original_costume_receive.c"
    "${ENGINE}/entities/coh_entities.c"
    "${ENGINE}/initial-capture/coh_initial_local.c"
    "${ENGINE}/initial-capture/coh_request_tx_map.c"
    "${ENGINE}/initial-capture/coh_request_tx_net.c"
    "${ENGINE}/initial-capture/coh_request_tx_udp.c"
    "${ENGINE}/initial-capture/coh_request_tx.c"
    "${ENGINE}/dbclient/coh_dbclient.c" "${ENGINE}/dbclient/coh_db_session.c"
    "${ENGINE}/dbclient/coh_db_account_controls.c"
    "${ENGINE}/mapclient/coh_mapclient_owned.c"
    "${ENGINE}/replication/coh_replication.c" "${ENGINE}/replication/coh_groups.c"
    "${ENGINE}/network/coh_net_frame.c" "${ENGINE}/network/coh_net_zip.c"
    "${ENGINE}/auth/coh_auth.c" "${ENGINE}/auth/coh_auth_openssl.c"
    "${ENGINE}/session/coh_session_crypto.c"
    "${NATIVE_ROOT}/protocol/coh_protocol.c" "${NATIVE_ROOT}/src/coh_blowfish.c")
set_target_properties(coh_combined_interop PROPERTIES C_VISIBILITY_PRESET hidden)
target_include_directories(coh_combined_interop PRIVATE "${ENGINE}/initial-capture" "${ENGINE}/entities"
    "${ENGINE}/session" "${NATIVE_ROOT}/include" "${CRYPTO_ABI_ROOT}/include")
target_compile_features(coh_combined_interop PRIVATE c_std_11)
target_compile_definitions(coh_combined_interop PRIVATE COH_INTEROP_REQUEST_TX=1)
if(COH_CLIENT_SLOT_DICTIONARY)
    target_compile_definitions(coh_combined_interop PRIVATE COH_INTEROP_CLIENT_SLOTS=1)
    target_link_libraries(coh_combined_interop PRIVATE android)
endif()
target_compile_options(coh_combined_interop PRIVATE -Wall -Wextra -Werror -ffp-contract=off)
target_link_options(coh_combined_interop PRIVATE -Wl,--no-undefined -Wl,-z,defs
    -Wl,--exclude-libs,ALL)
target_link_libraries(coh_combined_interop PRIVATE "${CRYPTO_ABI_ROOT}/lib/libcrypto.a" z dl m)

if(COH_FRAME_CAPTURE_DIAGNOSTIC)
    target_sources(coh_combined_interop PRIVATE "${ENGINE}/entities/coh_original_ent_costume.c"
        "${ENGINE}/entities/coh_original_taskforce_receive.c"
        "${ENGINE}/entities/coh_original_rare_receive.c"
        "${ENGINE}/entities/coh_very_rare_tail.c"
        "${ENGINE}/entities/coh_teammate_buffs.c"
        "${ENGINE}/entities/coh_original_initial_tail.c"
        "${ENGINE}/entities/coh_original_command_tail.c"
        "${ENGINE}/initial-capture/coh_initial_send.c"
        "${ENGINE}/entities/coh_character_outer.c" "${ENGINE}/entities/coh_character_tail.c"
        "${ENGINE}/entities/coh_character_creation.c" "${ENGINE}/entities/coh_character_initial.c"
        "${ENGINE}/entities/coh_character_prefix.c" "${ENGINE}/entities/coh_character_ui.c"
        "${ENGINE}/character-data/coh_character_data.c" "${ENGINE}/entity-control/coh_entity_control.c"
        "${ENGINE}/entity-globals/coh_power_info.c" "${ENGINE}/entity-globals/coh_entity_globals.c"
        "${ENGINE}/entity-globals/coh_badges.c" "${ENGINE}/entity-inventory/coh_inventory.c"
        "${ENGINE}/entity-inventory/coh_invention.c" "${ENGINE}/entity-inventory/coh_inventory_phase.c"
        "${ENGINE}/entity-team/coh_team.c" "${ENGINE}/entity-superstats/coh_superstats.c"
        "${ENGINE}/entity-social/coh_social.c" "${ENGINE}/entity-attributes/coh_attrib_monitor.c"
        "${ENGINE}/entity-dynamic/coh_dynamic.c" "${ENGINE}/entity-view/coh_view.c")
    target_compile_definitions(coh_combined_interop PRIVATE COH_FRAME_CAPTURE_DIAGNOSTIC=1)
endif()

if(COH_FULLSCREEN_DIAGNOSTIC)
    target_compile_definitions(coh_combined_interop PRIVATE COH_FULLSCREEN_DIAGNOSTIC=1)
endif()
