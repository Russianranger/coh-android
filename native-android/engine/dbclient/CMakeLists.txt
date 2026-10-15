cmake_minimum_required(VERSION 3.16)
project(coh_native_dbclient C)
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
add_library(coh_native_dbclient STATIC coh_dbclient.c coh_db_session.c
    ../auth/coh_auth.c ../network/coh_net.c ../network/coh_net_frame.c
    ../network/coh_net_udp.c ../network/coh_net_zip.c
    ../../protocol/coh_protocol.c ../../src/coh_blowfish.c)
target_include_directories(coh_native_dbclient PUBLIC . ../../include)
target_link_libraries(coh_native_dbclient PUBLIC z m)
target_compile_options(coh_native_dbclient PRIVATE -Wall -Wextra -Werror)
