# M0 compile survey

Compiles the original client sources (UtilitiesLib and Game, including the
Common files the client uses) syntax-only for ARM64 and groups the errors.
Nothing is linked or run, and `upstream/` is never modified: the survey copies
the sources to a work directory and runs the original StructParser there.

## Reproduce

```sh
# 1. Pinned headers (GitHub only): mingw-w64 v12, libc++ 18, glibc, client deps
armport/toolchain/fetch.sh /tmp/tc

# 2. The original code generator, built for this machine
cmake -S upstream/ouroboros/Utilities/StructParser -B /tmp/sp -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/sp

# 3. Baseline: unmodified source
python3 armport/survey/survey.py --toolchain /tmp/tc --structparser /tmp/sp/StructParser \
    --target win-arm64 --work /tmp/work --out win-arm64-baseline.json

# 4. Compiler flags only (MSVC-accepted errors downgraded) plus 64-bit warnings
python3 armport/survey/survey.py ... --permissive --warn64 --out win-arm64-permissive.json

# 5. Experiment: three one-line fixes and SSE shims, applied to a copy of the work dir
cp -a /tmp/work /tmp/exp && armport/survey/experiment/apply.sh /tmp/exp /tmp/tc /tmp/exp/overlay
python3 armport/survey/survey.py ... --work /tmp/exp --permissive --warn64 \
    --overlay /tmp/exp/overlay --out win-arm64-experiment.json
```

Tested with Ubuntu clang 18.1.3 on x86_64. A full run takes about 2 minutes on 2 CPUs.

Targets: `win-arm64` is ARM64 Windows (aarch64-w64-mingw32, LLP64), which the
app's Wine 10 runs natively. `linux-arm64` (aarch64 glibc) is for comparison.

Results are in `results/`; the summary is in [M0-REPORT.md](../M0-REPORT.md).
