# Phase 6: bounded REA-assisted shader upload discovery

The saved Phase 1 native project was recovered and queried **read-only, with no new executable import or autoanalysis**. The original Game was not executed. This pass preserves generic shader-upload instruction references and candidate bone/render strings; an exact bone-specific source-to-binary function match remains unresolved.

## Inputs and tools

Reference: the `CityOfHeroes.exe` from `coh-atlas-gameplay-v0.13.35`, SHA-256 `5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b`. The retained database reports that identity. It has partial prior analysis and no matching PDB.

REA workflow/evidence originated from `Russianranger/rea` at commit `0365454a573eb52c7089320fd74bfd4a673b78ae`, version 6.4.0. The prior genuine PE-resource evidence is `ev_d88ee0566099d5a65f69581142f00e9790e56fcd03a6a916de8b997a78f1113c`. This pass reuses those saved instructions and analysis state. Its new native output comes from a directly supervised Ghidra continuation, **not an REA-owned native provider call**. The REA bridge's previously observed PID namespace/process-ownership restriction was not retried or bypassed.

Portable Ghidra 12.1.4 and full Temurin JDK 21.0.12.1+1 were restored from the same hash-verified official archives. SHA-256 values, checkpoint/input/script/source hashes, limits, and receipts are recorded in [evidence/phase6/rea-shader-upload.json](evidence/phase6/rea-shader-upload.json). All ten retained project files match the recovered ZIP CRCs after the read-only query; no project database bytes changed.

## Executable-level observations

| Boundary | Observed address or result |
|---|---|
| `cgGLSetParameter4fv` import pointer | `0x00a3b890` |
| Import thunk | `0x00994d51` |
| Calls inside analyzed function `0x00642fc0` | `0x00643159`, `0x006431c6`, `0x0064349d`, `0x006434bc` |
| Call inside analyzed function `0x00643b70` | `0x00643c2d` |
| `g_BoneMatrixArrVP` raw string | `0x00a9efdc`; no references recovered in partial database |
| `drawLoopBoned` raw string | `0x00a976a0`; no references recovered |
| Boned draw marker format | `0x00a976b0`; no references recovered |
| `rt_bonedmodel.c` path substring | `0x00a97633`; no references recovered |
| `loadBoneMatrices` raw string | No match in searched initialized image memory |

The two upload callers have complete retained instruction listings for their analyzed bodies: 480 instructions/2,086 body bytes and 89 instructions/325 body bytes. Both bounded decompile requests returned `decompile_completed=false`, no pseudocode, and no failure explanation. Neither function is assigned a source name. Imported `cgGLSetMatrixParameterfc` and `cgGLSetParameterArray3f` metadata is also preserved, with available references; that metadata does not establish bone usage.

Detailed reference edges and instruction listings are in [evidence/phase6/ghidra-shader-upload-instructions.json](evidence/phase6/ghidra-shader-upload-instructions.json). An empty reference search in this partial database does not prove a string or API is unused.

## Independent source contract for the renderer gate

The inspected source files are hash-pinned in the receipt. `rt_bonedmodel.c::loadBoneMatrices` packs three vec4 rows per draw-local bone from Game's column-stored `Mat4`: row `k` is `{mp[0][k], mp[1][k], mp[2][k], mp[3][k]}`. It submits `bone_count * 3` rows through `WCW_SetCgShaderParamArray4fv` for `kShaderParam_BoneMatrixArrVP`. The source limit is 15 draw-local bones (45 rows); the selected three-bone fixture supplies nine rows. `wcw_statemgmt.c` declares the named parameter `g_BoneMatrixArrVP`, 48 vec4 slots, with ARB environment-register base 16.

`WCW_SetCgShaderParamArray4fv` selects the legacy ARB path, hard-constant environment-register path, or named-parameter cache according to renderer mode. `setArbEnvReg` uses one `glProgramEnvParameters4fvEXT` call when supported, otherwise one `glProgramEnvParameter4fvARB` call per row. Named values are cached and subsequently pushed by Cg code. These are source observations; this pass does not establish which branch executes on the original client or correlate the discovered generic vec4 callers with this bone path.

The GLES fixture should qualify row packing, the two-influence vertex contract, draw-local palette indices, material state, and the selected shader variant using the separate source/shader audit. This native binary slice supplies bounded corroborating seams. It supplies no runtime capture, Thor performance measurement, full asset-corpus qualification, or playable-client claim.

## Reproduce the read-only query

Recover the Phase 1 `.gpr` and `.rep` together and verify the reference identity and hashes first. With the portable paths used in this workspace:

```bash
timeout -s TERM -k 10s 90s env \
  JAVA_HOME=/workspace/scratch/119099198117/native-phase6/tools/jdk-21.0.12.1+1 \
  GHIDRA_HEADLESS_MAXMEM=2G \
  /workspace/scratch/119099198117/native-phase6/tools/ghidra_12.1.4_PUBLIC/support/analyzeHeadless \
  /workspace/scratch/119099198117/native-phase6/rea-recovered/ghidra-project CityOfHeroesNative \
  -process CityOfHeroes.exe -noanalysis -readOnly \
  -scriptPath /workspace/scratch/119099198117/native-coh/native-android/evidence/phase6 \
  -postScript CoHPhase6ShaderUpload.java /tmp/coh-phase6-shader-upload.json
```

The retained script admits at most three non-thunk functions, ten seconds per decompile, and 800 instructions per selected function. It never creates functions, changes database labels, or executes the client. The supervised job completed with exit code 0, and no analysis job remains running.
