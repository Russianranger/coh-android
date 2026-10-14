cmake_minimum_required(VERSION 3.22.1)
project(coh_integration_probe LANGUAGES C)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(CORE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(MATERIAL_CPP "${CORE_ROOT}/material-probe/app/src/main/cpp")
set(WORLD_CPP "${CORE_ROOT}/world-probe/app/src/main/cpp")
set(SHADER_ROOT "${CORE_ROOT}/material-probe/shaders")
set(WORLD_SHADER_ROOT "${CORE_ROOT}/world-probe/shaders")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${SHADER_ROOT}/skinned_dual.vert" "${SHADER_ROOT}/material_quad.vert"
    "${SHADER_ROOT}/dual_tint.frag" "${WORLD_SHADER_ROOT}/world.vert"
    "${WORLD_SHADER_ROOT}/reference.vert" "${WORLD_SHADER_ROOT}/world.frag")
execute_process(COMMAND "${Python3_EXECUTABLE}" "${MATERIAL_CPP}/embed_shaders.py"
    "${SHADER_ROOT}" "${CMAKE_CURRENT_BINARY_DIR}/shader_sources.h"
    RESULT_VARIABLE EMBED_RESULT)
execute_process(COMMAND "${Python3_EXECUTABLE}" "${WORLD_SHADER_ROOT}/embed_world_shaders.py"
    "${WORLD_SHADER_ROOT}" "${CMAKE_CURRENT_BINARY_DIR}/world_shader_sources.h"
    RESULT_VARIABLE WORLD_EMBED_RESULT)
if(NOT EMBED_RESULT EQUAL 0 OR NOT WORLD_EMBED_RESULT EQUAL 0)
    message(FATAL_ERROR "Could not embed accepted source shaders")
endif()
add_subdirectory("${CORE_ROOT}/decode" "${CMAKE_CURRENT_BINARY_DIR}/decode")
add_library(coh_integration_probe SHARED integration_bridge.c
    "${CORE_ROOT}/input/coh_input.c"
    "${CORE_ROOT}/audio/coh_audio.c" "${CORE_ROOT}/audio/coh_aaudio.c"
    "${CORE_ROOT}/protocol/coh_protocol.c" "${CORE_ROOT}/protocol/coh_protocol_selftest.c"
    "${CORE_ROOT}/src/coh_blowfish.c" "${CORE_ROOT}/transport/coh_transport.c"
    "${CORE_ROOT}/interactive-world/coh_interactive_world.c"
    "${CORE_ROOT}/interactive-world/coh_interactive_camera.c"
    "${WORLD_CPP}/coh_world_scene.c" "${MATERIAL_CPP}/coh_mesh.c"
    "${CORE_ROOT}/world/coh_world.c")
target_include_directories(coh_integration_probe PRIVATE
    "${CMAKE_CURRENT_BINARY_DIR}" "${CORE_ROOT}/input" "${CORE_ROOT}/audio"
    "${CORE_ROOT}/protocol" "${CORE_ROOT}/include" "${CORE_ROOT}/transport"
    "${CORE_ROOT}/interactive-world" "${CORE_ROOT}/world" "${MATERIAL_CPP}" "${WORLD_CPP}")
target_compile_features(coh_integration_probe PRIVATE c_std_11)
target_compile_options(coh_integration_probe PRIVATE -Wall -Wextra -Werror -ffp-contract=off)
target_link_libraries(coh_integration_probe PRIVATE coh_native_decode android aaudio EGL GLESv3 m)
