cmake_minimum_required(VERSION 3.22.1)
project(coh_material_probe LANGUAGES C)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(SHADER_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../shaders")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${SHADER_ROOT}/skinned_dual.vert" "${SHADER_ROOT}/material_quad.vert"
    "${SHADER_ROOT}/dual_tint.frag")
execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/embed_shaders.py"
    "${SHADER_ROOT}" "${CMAKE_CURRENT_BINARY_DIR}/shader_sources.h"
    RESULT_VARIABLE EMBED_RESULT)
if(NOT EMBED_RESULT EQUAL 0)
    message(FATAL_ERROR "Could not embed reviewed shader sources")
endif()
add_library(coh_material_probe SHARED probe_renderer.c coh_mesh.c)
target_include_directories(coh_material_probe PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_compile_features(coh_material_probe PRIVATE c_std_11)
target_compile_options(coh_material_probe PRIVATE -Wall -Wextra -Werror)
target_link_libraries(coh_material_probe PRIVATE android EGL GLESv3 m)
