#!/bin/sh
# M0 "what is behind the first errors" experiment. NOT port patches yet.
# Applies three one-line source fixes to a survey work copy (never upstream/)
# and writes shim headers that route x86 SSE headers to sse2neon on ARM64.
# Usage: apply.sh <survey-work-dir> <toolchain-dir> <overlay-dir>
set -eu
WORK=${1:?work dir}; TC=${2:?toolchain dir}; OV=${3:?overlay dir}
SRC="$WORK/src"
# 1. Typo MSVC accepts: "(oivd)" instead of "(void)".
sed -i 's/void rdrExamineDriversEarly(oivd);/void rdrExamineDriversEarly(void);/' \
	"$SRC/Game/src/render/renderUtil.h"
# 2. PowerMode declared as both an enum (powers.h) and an int (character_base.h).
sed -i 's/typedef int PowerMode;/typedef enum PowerMode PowerMode;/' \
	"$SRC/Common/entity/character_base.h"
# 3. Disable the x86-only PhysX (NovodeX) integration.
sed -i 's/#define NOVODEX 1/#define NOVODEX 0/' "$SRC/Common/NovodeX/NwWrapper.h"
mkdir -p "$OV"
for h in xmmintrin emmintrin pmmintrin tmmintrin smmintrin mmintrin; do
	printf '#if defined(__aarch64__)\n#include "%s/deps/sse2neon/sse2neon.h"\n#else\n#include_next <%s.h>\n#endif\n' "$TC" "$h" > "$OV/$h.h"
done
printf '#include <malloc.h>\n' > "$OV/alloca.h"
echo "experiment applied to $SRC; overlay in $OV"
