cmake_minimum_required(VERSION 3.16)
project(coh_native_mapclient C)
add_library(coh_native_mapclient STATIC coh_mapclient.c coh_mapclient_owned.c)
target_include_directories(coh_native_mapclient PUBLIC .)
target_compile_features(coh_native_mapclient PUBLIC c_std_99)
target_compile_options(coh_native_mapclient PRIVATE -Wall -Wextra -Werror)
# Parent links network, protocol, Blowfish, replication and zlib.
# Calling optional begin_owned extracts the bridge and requires DBSession.
