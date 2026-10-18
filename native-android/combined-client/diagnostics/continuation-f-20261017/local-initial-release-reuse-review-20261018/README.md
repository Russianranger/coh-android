Retained release receiver reuse

The exact 180424-byte release executable and original 240894-byte build receipt remain intact. Independent dependency preprocessing found 43 current project inputs; each equals both the historical dfc843bb2 Git blob and the current recorded Git blob. Existing 151-check profiles and 12 safe stdout files are preserved as historical evidence, without replay.

The ELF is x86_64 PIE, uses the standard x86_64 Linux interpreter, and directly needs libz.so.1, libcrypto.so.3 and libc.so.6. It has no RPATH/RUNPATH; required symbol versions are retained in the static report. This permits a destination compatibility gate, not an assumption that a future runner has the required libraries.

Before Map startup, the destination must re-admit exact bytes and project source closure, resolve the dynamic dependencies in its intended clean environment, and run only a bounded no-argument smoke requiring exit 2 and empty stdout/stderr. The source exits before account/output/controller/socket work for that invocation. The original receipt must not be relabeled as a current CI build. A separate transfer/preflight receipt should identify the current checkout and actual destination result.

No native executable, old test suite, compiler object build, service or network session was run for this review. Dependency preprocessing and readelf only were executed. The original receipt does not identify the compiler binary/system headers/shared libraries and supplies no reproducible-toolchain claim. A no-argument smoke does not qualify entropy, crypto or DB interoperability.
