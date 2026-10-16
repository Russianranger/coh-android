add_library(coh_world_render_adapter STATIC coh_world_render.c)
target_include_directories(coh_world_render_adapter PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_features(coh_world_render_adapter PUBLIC c_std_11)
target_compile_options(coh_world_render_adapter PRIVATE -Wall -Wextra -Werror -ffp-contract=off)
find_package(Threads REQUIRED)
target_link_libraries(coh_world_render_adapter PUBLIC Threads::Threads)
# Deliberately not added to parent CMake or any shipping APK. Coordinator owns
# activation only after full catalog/asset/character transaction qualification.
