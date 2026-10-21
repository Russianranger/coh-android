# Stand-ins for x86-only SDKs

The Win32 client links several closed, x86-only libraries. On ARM64 Windows
they are replaced here (wired in by patch 0021):

| SDK | ARM64 replacement | Why it is safe for now |
|---|---|---|
| PhysX (NovodeX) | headers only | `NOVODEX` is undefined on ARM64, so the physics integration (ragdolls, FX debris) is compiled out |
| AlienFX, NvCpl | headers only | vendor extras (lighting effects, NVIDIA control panel) |
| nvDXT | `nvdxt/nvdxt_standin.cpp` | 4 functions return failure; used for runtime DXT compression in texWords and the automap |
| Cg runtime | `cg/cg_standin.cpp` (generated) | 81 functions return failure; the client's behavior without Cg is examined next in M2 |

Regenerate the Cg stand-in after upstream changes:
`python3 armport/standins/cg/generate_standin.py`.
