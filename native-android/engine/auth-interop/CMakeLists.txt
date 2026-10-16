cmake_minimum_required(VERSION 3.22)
project(coh_auth_interop C)
add_library(coh_auth_interop STATIC coh_auth_interop.c)
target_compile_features(coh_auth_interop PUBLIC c_std_11)
target_include_directories(coh_auth_interop PUBLIC . ../../include)
# This optional policy/probe module is deliberately absent from accepted APKs.
# The probe owner links the already-qualified real auth/DB/map/socket modules.
