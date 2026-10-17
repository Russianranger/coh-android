# Actual standalone Android qualification, run38998532705

Artifact12088426347 is retained byte-for-byte as `artifact.zip`; SHA256
`84916be2a7827aac487aae7677557afb79874240aca29f5ccad7300be231b4bb`.
The source pin is `c21f2c059c0045aedfd9693ff076391598b33163` on native-android.

Worker F independently verified archive CRC/SHA,203 bound source inputs against
committed Git blobs, both ABI binary receipts/ELF machines, host sanitizer result
and binary/readback hashes, actual Android SDK33/x86_64 emulator logs, transferred
binary/fixture identities,27 actual GPU mip readbacks, stable platform library
file observations, and native/device cleanup. Unmodified strict EGL and suffix
admission drivers were independently replayed from a new sparse detached source
worktree at the exact pin, in validate-only mode; their receipts explicitly do
not claim a second Android execution. No server or accepted APK was rebuilt.

Actual Android EGL:183 controls, ES3.0 SwiftShader, all9 mip levels through each
of3 uploads/readbacks,2 contexts and3 surfaces destroyed. Actual standalone
initial GLOBAL suffix:9991 checks,2390 matched scratch acquire/release pairs,
peak scratch5993424bytes. ARM64 binaries built; only x86_64 binaries executed.
`verify.py` rechecks retained bytes and source identities without executing them.

This is standalone texture/fixture and raw suffix qualification. Source generation
and sampler are fixture-only. System/vendor drivers and platform zlib were not
rebuilt sanitized; library file hashes are not verified loaded mappings or full
transitive dependency/stack closure. No material, actor, complete initial update,
ACK, server world, encrypted DB/Map handoff or physical Thor acceptance follows.
