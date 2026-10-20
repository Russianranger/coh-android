cmake_minimum_required(VERSION 3.22.1)
project(coh_session_client LANGUAGES C)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(CORE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
set(MATERIAL_CPP "${CORE_ROOT}/material-probe/app/src/main/cpp")
set(WORLD_CPP "${CORE_ROOT}/world-probe/app/src/main/cpp")
set(CHARACTER_CPP "${CORE_ROOT}/character-probe/app/src/main/cpp")
set(WORLD_SHADER_ROOT "${CORE_ROOT}/world-probe/shaders")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${WORLD_SHADER_ROOT}/world.vert" "${WORLD_SHADER_ROOT}/world.frag")
execute_process(COMMAND "${Python3_EXECUTABLE}" "${WORLD_SHADER_ROOT}/embed_world_shaders.py"
    "${WORLD_SHADER_ROOT}" "${CMAKE_CURRENT_BINARY_DIR}/world_shader_sources.h"
    RESULT_VARIABLE EMBED_RESULT)
if(NOT EMBED_RESULT EQUAL 0)
    message(FATAL_ERROR "Could not embed accepted source world shaders")
endif()
add_library(coh_session_client SHARED session_renderer.c session_stream_world.c session_stream_qualify.c session_frame_capture.c session_frame_capture_gl.c
    "${CORE_ROOT}/engine/assets/coh_asset_zip.c" "${CORE_ROOT}/engine/world/coh_world_live.c"
    "${CORE_ROOT}/engine/assets/coh_asset_loader.c" "${CORE_ROOT}/engine/assets/coh_asset_geo.c"
    "${CORE_ROOT}/engine/bridge/coh_asset_render.c" "${CORE_ROOT}/engine/world/coh_world_stream.c"
    "${CORE_ROOT}/engine/renderer/coh_debug_entity.c"
    "${CORE_ROOT}/engine/renderer/coh_renderer.c" "${CORE_ROOT}/engine/renderer/coh_renderer_gles.c"
    "${CORE_ROOT}/src/coh_assets.c" "${CORE_ROOT}/src/coh_dds.c"
    "${WORLD_CPP}/coh_world_scene.c" "${CHARACTER_CPP}/coh_scene.c"
    "${MATERIAL_CPP}/coh_mesh.c" "${CORE_ROOT}/world/coh_world.c"
    "${CORE_ROOT}/character/coh_character.c"
    "${CORE_ROOT}/motion/coh_motion.c" "${CORE_ROOT}/locomotion/coh_locomotion.c"
    "${CORE_ROOT}/walkable/coh_walkable_scene.c" "${CORE_ROOT}/walk/coh_walk.c"
    "${CORE_ROOT}/walk/source_ctri.c" "${CORE_ROOT}/walk/source_world.c" "${CORE_ROOT}/walk/source_tritri.c")
target_include_directories(coh_session_client PRIVATE "${CMAKE_CURRENT_BINARY_DIR}"
    "${MATERIAL_CPP}" "${WORLD_CPP}" "${CHARACTER_CPP}" "${CORE_ROOT}/world"
    "${CORE_ROOT}/animation" "${CORE_ROOT}/character" "${CORE_ROOT}/motion"
    "${CORE_ROOT}/locomotion" "${CORE_ROOT}/walk" "${CORE_ROOT}/walkable"
    "${CORE_ROOT}/include" "${CORE_ROOT}/engine/assets" "${CORE_ROOT}/engine/bridge"
    "${CORE_ROOT}/engine/world" "${CORE_ROOT}/engine/renderer")
target_compile_features(coh_session_client PRIVATE c_std_11)
target_compile_options(coh_session_client PRIVATE -Wall -Wextra -Werror -ffp-contract=off -fno-strict-aliasing)
set_source_files_properties("${CORE_ROOT}/walk/source_world.c" "${CORE_ROOT}/walk/source_ctri.c"
    PROPERTIES COMPILE_OPTIONS "-Wno-unused-variable;-Wno-unused-parameter;-Wno-unused-but-set-variable;-Wno-unused-function;-Wno-misleading-indentation")
target_link_libraries(coh_session_client PRIVATE android EGL GLESv3 z m)

if(COH_FRAME_CAPTURE_DIAGNOSTIC)
    target_compile_definitions(coh_session_client PRIVATE COH_FRAME_CAPTURE_DIAGNOSTIC=1)
endif()
