cmake_minimum_required(VERSION 3.22.1)
project(coh_world_probe LANGUAGES C)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(CORE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(MATERIAL_CPP "${CORE_ROOT}/material-probe/app/src/main/cpp")
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
    message(FATAL_ERROR "Could not embed source-reviewed shader sources")
endif()
add_library(coh_world_probe SHARED probe_renderer.c coh_world_scene.c
    "${MATERIAL_CPP}/coh_mesh.c" "${CORE_ROOT}/world/coh_world.c")
target_include_directories(coh_world_probe PRIVATE "${CMAKE_CURRENT_BINARY_DIR}"
    "${MATERIAL_CPP}" "${CORE_ROOT}/world")
target_compile_features(coh_world_probe PRIVATE c_std_11)
target_compile_options(coh_world_probe PRIVATE -Wall -Wextra -Werror -ffp-contract=off)
target_link_libraries(coh_world_probe PRIVATE android EGL GLESv3 m)
