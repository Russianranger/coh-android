# Actual full manual PG/Wine compile attempt

Run39006696548, source8cf325f4dc78eab451f23382ac8a13f8fa9ffe5c, artifact12090714854:660418bytes/SHA2564703de08a2ef50d3af14112668b2ce48f482a21f7a6f02b3b865ceb9fe329baa. Exact ZIP and raw receipt/log retained.

The reviewed tool/SDK identities and source checks passed. All three dependencies fetched and patched successfully. CMake identified MSVC19.51.36260.0, then failed because the canonical Windows rc.exe path was emitted with backslashes into generated CMakeRCCompiler.cmake (invalid character escape). No full DbServer build or game/server execution occurred. Source/toolchain remained unchanged and final source/dependency maps were captured. This is failed compile evidence, not binary admission.

A new isolated correction renders only CMake-consumed path arguments with portable forward slashes, preserving observed tool strings/hashes. It requires independent review and a genuinely new source attempt. No accepted profile, binary, auth policy or persistence data changed.
