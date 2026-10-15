cmake_minimum_required(VERSION 3.16)
project(coh_engine_perf C)
add_library(coh_engine_perf STATIC coh_perf.c coh_perf_bridge.c coh_skin_cache.c)
target_compile_features(coh_engine_perf PUBLIC c_std_11)
target_include_directories(coh_engine_perf PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
# Consumers also link the accepted coh_mesh_skin_vertex kernel. No JNI, GL,
# network, process-global instrumentation or accepted build target is changed.
