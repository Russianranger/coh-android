cmake_minimum_required(VERSION 3.22.1)
project(coh_systems_probe LANGUAGES C)
set(CORE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
add_library(coh_systems_probe SHARED systems_bridge.c
    "${CORE_ROOT}/input/coh_input.c"
    "${CORE_ROOT}/audio/coh_audio.c"
    "${CORE_ROOT}/audio/coh_aaudio.c"
    "${CORE_ROOT}/protocol/coh_protocol.c"
    "${CORE_ROOT}/protocol/coh_protocol_selftest.c"
    "${CORE_ROOT}/src/coh_blowfish.c")
target_include_directories(coh_systems_probe PRIVATE
    "${CORE_ROOT}/input" "${CORE_ROOT}/audio" "${CORE_ROOT}/protocol"
    "${CORE_ROOT}/include")
target_compile_features(coh_systems_probe PRIVATE c_std_11)
target_compile_options(coh_systems_probe PRIVATE -Wall -Wextra -Werror -ffp-contract=off)
target_link_libraries(coh_systems_probe PRIVATE aaudio android m)
