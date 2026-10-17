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
add_library(coh_combined_network SHARED combined_network.c
    "${ENGINE}/local/coh_local.c"
    "${ENGINE}/dbclient/coh_dbclient.c" "${ENGINE}/dbclient/coh_db_session.c"
    "${ENGINE}/mapclient/coh_mapclient.c" "${ENGINE}/mapclient/coh_mapclient_owned.c"
    "${ENGINE}/replication/coh_replication.c"
    "${ENGINE}/replication/coh_groups.c"
    "${ENGINE}/network/coh_net.c" "${ENGINE}/network/coh_net_frame.c"
    "${ENGINE}/network/coh_net_zip.c" "${ENGINE}/network/coh_net_udp.c"
    "${ENGINE}/auth/coh_auth.c" "${ENGINE}/auth/coh_auth_openssl.c"
    "${ENGINE}/session/coh_session_crypto.c"
    "${NATIVE_ROOT}/protocol/coh_protocol.c" "${NATIVE_ROOT}/src/coh_blowfish.c")
target_include_directories(coh_combined_network PRIVATE "${ENGINE}/local" "${ENGINE}/session"
    "${NATIVE_ROOT}/include" "${CRYPTO_ABI_ROOT}/include")
target_compile_features(coh_combined_network PRIVATE c_std_11)
target_compile_options(coh_combined_network PRIVATE -Wall -Wextra -Werror -ffp-contract=off)
target_link_options(coh_combined_network PRIVATE -Wl,--no-undefined -Wl,-z,defs)
target_link_libraries(coh_combined_network PRIVATE "${CRYPTO_ABI_ROOT}/lib/libcrypto.a" z dl)
