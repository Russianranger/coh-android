# CMake toolchain for building the original client as ARM64 Windows
# (aarch64-w64-mingw32, LLP64) for the app's ARM64 Wine 10.
#
# Two modes:
#   COH_LLVM_MINGW=<llvm-mingw root>   real toolchain (CI): compile, link, run.
#   COH_ARMPORT_HEADERS=<fetch.sh dir> compile-only with system clang and the
#                                      pinned headers (local iteration; static
#                                      libraries only, nothing is linked).
# COH_WINE=<path to wine> sets the emulator used to run built test programs.

set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

if(DEFINED ENV{COH_LLVM_MINGW})
	set(_coh_prefix "$ENV{COH_LLVM_MINGW}/bin/aarch64-w64-mingw32-")
	set(CMAKE_C_COMPILER "${_coh_prefix}clang")
	set(CMAKE_CXX_COMPILER "${_coh_prefix}clang++")
	set(CMAKE_RC_COMPILER "${_coh_prefix}windres")
	set(CMAKE_AR "$ENV{COH_LLVM_MINGW}/bin/llvm-ar" CACHE FILEPATH "")
	set(CMAKE_RANLIB "$ENV{COH_LLVM_MINGW}/bin/llvm-ranlib" CACHE FILEPATH "")
	set(CMAKE_FIND_ROOT_PATH "$ENV{COH_LLVM_MINGW}/aarch64-w64-mingw32")
elseif(DEFINED ENV{COH_ARMPORT_HEADERS})
	set(_h "$ENV{COH_ARMPORT_HEADERS}")
	set(_m "${_h}/mingw-w64/mingw-w64-headers")
	execute_process(COMMAND clang -print-resource-dir
		OUTPUT_VARIABLE _res OUTPUT_STRIP_TRAILING_WHITESPACE)
	set(CMAKE_C_COMPILER clang)
	set(CMAKE_CXX_COMPILER clang++)
	set(CMAKE_C_COMPILER_TARGET aarch64-w64-mingw32)
	set(CMAKE_CXX_COMPILER_TARGET aarch64-w64-mingw32)
	set(CMAKE_RC_COMPILER llvm-rc)
	set(CMAKE_AR llvm-ar CACHE FILEPATH "")
	set(CMAKE_RANLIB llvm-ranlib CACHE FILEPATH "")
	set(_sys "-nostdinc -isystem ${_res}/include -isystem ${_h}/gen -isystem ${_m}/crt -isystem ${_m}/include -isystem ${_m}/direct-x/include -isystem ${_m}/ddk/include -D_UCRT -D__prefetch=__coh_mingw_prefetch")
	set(CMAKE_C_FLAGS_INIT "${_sys}")
	set(CMAKE_CXX_FLAGS_INIT "-nostdinc++ -isystem ${_h}/gen-cxx-win -isystem ${_h}/llvm/libcxx/include ${_sys}")
	# No CRT libraries locally: configure checks build static libraries only.
	set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
	set(COX_ARMPORT_COMPILE_ONLY ON CACHE BOOL "Local compile-only mode" FORCE)
else()
	message(FATAL_ERROR "Set COH_LLVM_MINGW (real toolchain) or COH_ARMPORT_HEADERS (compile-only)")
endif()

if(DEFINED ENV{COH_WINE})
	set(CMAKE_CROSSCOMPILING_EMULATOR "$ENV{COH_WINE}" CACHE STRING "" FORCE)
endif()

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
