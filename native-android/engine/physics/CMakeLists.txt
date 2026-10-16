cmake_minimum_required(VERSION 3.18)
project(coh_physics C)
# Opt-in standalone target. Accepted root/session build files remain unchanged.
add_library(coh_physics STATIC coh_physics.c coh_physics_snapshot.c coh_physics_neighborhood.c)
target_include_directories(coh_physics PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_features(coh_physics PUBLIC c_std_11)
# Link the existing accepted WALK/motion/CTri objects once in the application.
target_link_libraries(coh_physics PUBLIC m)
