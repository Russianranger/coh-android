cmake_minimum_required(VERSION 3.22)
project(coh_auth_android_crypto C)
if(NOT ANDROID)
    message(FATAL_ERROR "This provider target requires the public Android NDK")
endif()
set(COH_OPENSSL_ROOT "" CACHE PATH "ABI directory produced by auth/android/build.py")
if(NOT EXISTS "${COH_OPENSSL_ROOT}/receipt.json")
    message(FATAL_ERROR "Build pinned Android libcrypto using auth/android/build.py first")
endif()
file(READ "${COH_OPENSSL_ROOT}/receipt.json" _coh_receipt)
string(JSON _coh_status GET "${_coh_receipt}" status)
string(JSON _coh_abi GET "${_coh_receipt}" abi)
string(JSON _coh_api GET "${_coh_receipt}" api)
string(JSON _coh_version GET "${_coh_receipt}" openssl_version)
string(JSON _coh_archive_sha GET "${_coh_receipt}" openssl_archive_sha256)
string(JSON _coh_pin_sha GET "${_coh_receipt}" source_pin_sha256)
string(JSON _coh_crypto_sha GET "${_coh_receipt}" artifacts_sha256 "lib/libcrypto.a")
file(SHA256 "${COH_OPENSSL_ROOT}/lib/libcrypto.a" _coh_actual_sha)
file(SHA256 "${CMAKE_CURRENT_LIST_DIR}/openssl-source.json" _coh_expected_pin_sha)
file(SHA256 "${COH_OPENSSL_ROOT}/OPENSSL-LICENSE.txt" _coh_license_sha)
# The NDK toolchain's default legacy CMake mode reports system version 1;
# ANDROID_PLATFORM_LEVEL is its actual selected public Android API.
if(DEFINED ANDROID_ABI)
    set(_coh_target_abi "${ANDROID_ABI}")
else()
    set(_coh_target_abi "${CMAKE_ANDROID_ARCH_ABI}")
endif()
if(DEFINED ANDROID_PLATFORM_LEVEL)
    set(_coh_target_api "${ANDROID_PLATFORM_LEVEL}")
else()
    set(_coh_target_api "${CMAKE_SYSTEM_VERSION}")
endif()
if(NOT _coh_status STREQUAL "PASS"
   OR NOT _coh_abi STREQUAL _coh_target_abi
   OR _coh_api GREATER _coh_target_api
   OR NOT _coh_version STREQUAL "3.5.9"
   OR NOT _coh_archive_sha STREQUAL "603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a"
   OR NOT _coh_pin_sha STREQUAL _coh_expected_pin_sha
   OR NOT _coh_license_sha STREQUAL "7d5450cb2d142651b8afa315b5f238efc805dad827d91ba367d8516bc9d49e7a"
   OR NOT _coh_crypto_sha STREQUAL _coh_actual_sha)
    message(FATAL_ERROR "OpenSSL artifact receipt or ABI mismatch")
endif()
if(NOT TARGET coh_auth)
    message(FATAL_ERROR "Add the accepted engine/auth target before auth/android")
endif()
add_library(coh_auth_android_openssl STATIC IMPORTED GLOBAL)
set_target_properties(coh_auth_android_openssl PROPERTIES
    IMPORTED_LOCATION "${COH_OPENSSL_ROOT}/lib/libcrypto.a"
    INTERFACE_INCLUDE_DIRECTORIES "${COH_OPENSSL_ROOT}/include")
add_library(coh_auth_android_crypto STATIC ../coh_auth_openssl.c)
target_include_directories(coh_auth_android_crypto PUBLIC ..)
target_compile_features(coh_auth_android_crypto PUBLIC c_std_99)
target_compile_options(coh_auth_android_crypto PRIVATE -fvisibility=hidden)
target_link_libraries(coh_auth_android_crypto PUBLIC coh_auth coh_auth_android_openssl dl)
