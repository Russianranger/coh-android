# Qualification-only injection admitted by exact source/package receipts.
# Pass via CMAKE_PROJECT_INCLUDE in the one Game-only producer. The retained
# project and all CFLAGS remain unchanged; no production workflow passes this.
if(NOT PROJECT_IS_TOP_LEVEL)
    return()
endif()
function(coh_client_metadata_capture_define)
    if(NOT WIN32 OR NOT MSVC OR NOT CMAKE_SIZEOF_VOID_P EQUAL 4)
        message(FATAL_ERROR "Metadata capture requires MSVC Win32")
    endif()
    if(NOT TARGET UtilitiesLib OR NOT TARGET Game)
        message(FATAL_ERROR "Metadata capture requires retained Game/UtilitiesLib")
    endif()
    if(COX_BUILD_MAPSERVER OR COX_BUILD_BEACONSERVER)
        message(FATAL_ERROR "Metadata capture producer must be Game-only")
    endif()
    target_compile_definitions(UtilitiesLib PRIVATE COH_CLIENT_METADATA_CENSUS_CAPTURE=1)
endfunction()
cmake_language(DEFER DIRECTORY "${CMAKE_SOURCE_DIR}" CALL coh_client_metadata_capture_define)
