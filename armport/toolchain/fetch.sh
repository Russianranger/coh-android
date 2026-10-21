#!/bin/sh
# Fetch the pinned headers and tools the M0 compile survey uses.
# Usage: armport/toolchain/fetch.sh <dir>
# Needs git and clang (tested with clang 18). Only GitHub is contacted.
set -eu
DIR=${1:?usage: fetch.sh <dir>}
mkdir -p "$DIR/deps" "$DIR/gen"
cd "$DIR"

pin() { # pin <dir> <url> <rev> [sparse paths...]
	d=$1 url=$2 rev=$3; shift 3
	if [ ! -d "$d/.git" ]; then
		git init -q "$d"
		git -C "$d" remote add origin "$url"
	fi
	if [ $# -gt 0 ]; then
		git -C "$d" sparse-checkout set --no-cone "$@"
	fi
	git -C "$d" fetch -q --depth 1 --filter=blob:none origin "$rev"
	git -C "$d" checkout -q FETCH_HEAD
}

# aarch64 glibc and Linux headers (from Zig's bundled libc headers).
pin zig https://github.com/ziglang/zig 738d2be9d6b6ef3ff3559130c05159ef53336224 \
	/lib/libc/include/generic-glibc/ /lib/libc/include/aarch64-linux-gnu/ \
	/lib/libc/include/any-linux-any/ /lib/libc/include/aarch64-linux-any/
# mingw-w64 v12.0.0 Windows headers (ARM64 Windows target; matches clang 18).
pin mingw-w64 https://github.com/mingw-w64/mingw-w64 819a6ec2ea87c19814b287e21d65e0dc7f05abba \
	/mingw-w64-headers/include/ /mingw-w64-headers/crt/ \
	/mingw-w64-headers/direct-x/ /mingw-w64-headers/ddk/
mkdir -p gen/sdks
sed -e 's/@DEFAULT_MSVCRT_VERSION@/0xE00/' -e 's/@DEFAULT_WIN32_WINNT@/0xa00/' \
	mingw-w64/mingw-w64-headers/crt/_mingw.h.in > gen/_mingw.h
sed -e 's/@MINGW_HAS_DDK@/1/' \
	mingw-w64/mingw-w64-headers/crt/sdks/_mingw_ddk.h.in > gen/sdks/_mingw_ddk.h

# libc++ 18 headers for the C++ sources, with a minimal config per target.
pin llvm https://github.com/llvm/llvm-project llvmorg-18.1.3 /libcxx/include/ /libcxx/vendor/
for t in win linux; do
	mkdir -p gen-cxx-$t
	if [ $t = win ]; then thr=_LIBCPP_HAS_THREAD_API_WIN32; else thr=_LIBCPP_HAS_THREAD_API_PTHREAD; fi
	printf '#ifndef _LIBCPP___CONFIG_SITE\n#define _LIBCPP___CONFIG_SITE\n#define _LIBCPP_ABI_VERSION 1\n#define _LIBCPP_ABI_NAMESPACE __1\n#define %s\n#define _LIBCPP_HAS_NO_VENDOR_AVAILABILITY_ANNOTATIONS\n#define _LIBCPP_PSTL_CPU_BACKEND_SERIAL\n#define _LIBCPP_HARDENING_MODE_DEFAULT _LIBCPP_HARDENING_MODE_NONE\n#endif\n' "$thr" > gen-cxx-$t/__config_site
	cp llvm/libcxx/vendor/llvm/default_assertion_handler.in gen-cxx-$t/__assertion_handler
done

# Client dependencies at the commits upstream CMake pins
# (zlib: madler mirror of the same API instead of the Chromium copy;
#  GLEW: Perlmint/glew-cmake, which commits the generated 2.1.0 headers).
pin deps/sparsehash https://github.com/sparsehash/sparsehash f93c0c69e959c1c77611d0ba8d107aa971338811
pin deps/cryptopp https://github.com/weidai11/cryptopp b5242667a24e3db8e4600e77b2e502ef204e5280
pin deps/ogg https://github.com/xiph/ogg be05b13e98b048f0b5a0f5fa8ce514d56db5f822
pin deps/vorbis https://github.com/xiph/vorbis 0657aee69dec8508a0011f47f3b69d7538e9d262
pin deps/jpgd https://github.com/richgel999/jpeg-compressor a385a2045aa01584987a6bafc0f7e0c420d28c82
pin deps/libjpeg-turbo https://github.com/libjpeg-turbo/libjpeg-turbo ec32420f6b5dfa4e86883d42b209e8371e55aeb5
pin deps/freetype https://github.com/freetype/freetype 21ddf945c3439f4d3feed27a991a6bcdd5316fb4
pin deps/zlib https://github.com/madler/zlib 05527a1b1ef39014b44281fbbbec5deabb4be106
pin deps/glew-cmake https://github.com/Perlmint/glew-cmake b38c74c243c130ff16153d2fe445179c08675a26
# SSE-to-NEON translation header (experiment shims for x86 intrinsics).
pin deps/sse2neon https://github.com/DLTcollab/sse2neon 3cf69760cc6fdc45a5d70f0d42a8f079489f9867

# Small generated config headers the real build writes at configure time.
mkdir -p gen/sparsehash/internal gen/ogg
cat > gen/sparsehash/internal/sparseconfig.h <<'EOF'
#ifndef COX_SPARSEHASH_CONFIG_H
#define COX_SPARSEHASH_CONFIG_H
#define GOOGLE_NAMESPACE ::google
#define HASH_FUN_H <functional>
#define HASH_NAMESPACE std
#define SPARSEHASH_HASH HASH_NAMESPACE::hash
#define SPARSEHASH_HASH_NO_NAMESPACE hash
#define HAVE_INTTYPES_H 1
#define HAVE_LONG_LONG 1
#define HAVE_MEMCPY 1
#define HAVE_STDINT_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_UINT16_T 1
#define _END_GOOGLE_NAMESPACE_ }
#define _START_GOOGLE_NAMESPACE_ namespace google {
#endif
EOF
cat > gen/ogg/config_types.h <<'EOF'
#ifndef __CONFIG_TYPES_H__
#define __CONFIG_TYPES_H__
#include <stdint.h>
typedef int16_t ogg_int16_t;
typedef uint16_t ogg_uint16_t;
typedef int32_t ogg_int32_t;
typedef uint32_t ogg_uint32_t;
typedef int64_t ogg_int64_t;
typedef uint64_t ogg_uint64_t;
#endif
EOF
echo "fetched into $DIR"
