cmake_minimum_required(VERSION 3.16)
project(coh_native_local C)
add_library(coh_native_local STATIC coh_local.c)
target_include_directories(coh_native_local PUBLIC .)
target_compile_features(coh_native_local PUBLIC c_std_11)
target_compile_options(coh_native_local PRIVATE -Wall -Wextra -Werror)
# Parent links the existing DB, Map, network, protocol, replication and zlib
# modules and supplies the public key-exchange callback for encrypted peers.
