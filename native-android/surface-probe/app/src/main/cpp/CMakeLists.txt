cmake_minimum_required(VERSION 3.22.1)
project(coh_surface_probe LANGUAGES C)

set(COH_CORE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../..")
add_library(coh_surface_probe SHARED
    probe_renderer.c
    "${COH_CORE_ROOT}/src/coh_dds.c")
target_include_directories(coh_surface_probe PRIVATE "${COH_CORE_ROOT}/include")
target_compile_features(coh_surface_probe PRIVATE c_std_11)
target_compile_options(coh_surface_probe PRIVATE -Wall -Wextra -Werror)
target_link_libraries(coh_surface_probe PRIVATE android EGL GLESv3)
