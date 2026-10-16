# Exact Android socket boundary continuation

The initial 0.1.6 session workflow failed its Python qualification guard after
the Android C executable returned zero and reported all 1,194 checks. The guard
still expected the earlier 886-check suite; its strict expected counts now match
the added owned-message lifecycle scenarios. Key sets and field types remain
strict, with 55 independent validator controls.

| Evidence | Result |
|---|---|
| Original source | `7c9cfdb9d5f87c2297f8772fc3aeff528577728f` |
| Original workflow / failed guard job | `38830583695` / `116748693404` |
| Qualification-only commit | `a724487ecf774151ad73cd004023341e7d18381d` |
| Exact-binary continuation workflow / job | `38831867730` / `116752234079`, success |
| Android 13 x86_64 executable | 1,194 checks, 61 negative cases, 22 socket scenarios |
| Reused archive / continuation artifact | `12016554135` / `12018335330` |

Both original ELF binaries and the original compilation receipt are identical
byte for byte in the continuation. The old and newly executed Android stdout
also match exactly. The workflow checked the archive hash, bounded ZIP member
metadata before decompression, both ELF hashes, 14 C/header hashes and an
unchanged production source closure. No native executable or APK was rebuilt.
The original session workflow's two jobs were skipped on this qualification
commit, and no Combined APK workflow was started by it.

`exact-binary-reuse.json` records preparation before execution, so its
`android_executed` remains false. `android-udp-proof.json` records the subsequent
successful Android execution. This is a controlled OS socket test on x86_64;
it establishes no new ARM64 execution, physical Thor acceptance or authentic
game-server interoperability. All source, archive and binary identities are
recorded in `summary.json` and the linked receipts. Full artifacts remain in
GitHub Actions; only compact qualification receipts are stored here.
