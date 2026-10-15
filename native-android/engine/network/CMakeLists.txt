cmake_minimum_required(VERSION 3.16)
project(coh_native_net C)
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
add_library(coh_native_net STATIC
    coh_net.c coh_net_frame.c coh_net_zip.c coh_net_udp.c
    ../../protocol/coh_protocol.c ../../src/coh_blowfish.c)
target_include_directories(coh_native_net PUBLIC . ../../include ../../protocol)
target_link_libraries(coh_native_net PUBLIC z)
target_compile_options(coh_native_net PRIVATE -Wall -Wextra -Werror)
