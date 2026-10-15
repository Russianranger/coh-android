cmake_minimum_required(VERSION 3.22.1)
project(coh_game_audio C)
add_library(coh_game_audio STATIC coh_mixer.c coh_audio_listener.c ../../audio/coh_audio.c)
target_include_directories(coh_game_audio PUBLIC "${CMAKE_CURRENT_LIST_DIR}")
target_compile_features(coh_game_audio PUBLIC c_std_11)
target_compile_options(coh_game_audio PRIVATE -Wall -Wextra -Werror -ffp-contract=off)
set_target_properties(coh_game_audio PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_link_libraries(coh_game_audio PUBLIC m)
if(ANDROID)
  target_sources(coh_game_audio PRIVATE coh_mixer_aaudio.c coh_audio_session.c)
  target_link_libraries(coh_game_audio PUBLIC aaudio)
endif()
# No decoder is invoked by the mixer. Optional decode/cache work links the
# accepted native-android/decode library on its own non-realtime worker.
