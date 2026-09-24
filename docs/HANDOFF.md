# City of Heroes i25 Android handoff

Updated: 2026-09-24.

## User direction

- Use **OuroDev i25/SCoRE source**, not Volume 2 or a VM.
- The user has no Windows PC. Use hosted Windows builds/reference tests and Thor
  gameplay testing; do not require user-installed MSVC or SQL Server.
- The user added an Actions repository secret named `odtoken`. Reference it only
  through Actions; do not print, export or request its value in chat.

## Latest result

Canonical source target: `https://git.ourodev.com/score/SCoRE.git`. The indexed
OuroDev guide names `Lexicon-Project(Co)X`; remote refs and commit are not verified.
Two Actions probes established that the secret is present but the server TLS
certificate is expired. Credential validity has not been tested. Expiration:
**2026-09-23 10:39:54 UTC**. See [acquisition evidence](I25_SOURCE_ACQUISITION.md).

No canonical i25 source was imported. Do not interpret TLS failure as an invalid
token or ask the user to recreate the secret based on this result.

## Preserved work

The prior Volume 2-derived source remains under `upstream/ouroboros`, with its
integrity manifest and verifier. Backup branch
`archive/volume2-assessment-2026-09-23` preserves commit
`19082428d6dd5484c34c6a7a2913374d79b167be` and its assessment. The old proposal is
also retained as `docs/VOLUME2_PORT_PROPOSAL.md`.

The root README and active proposal now select i25. `upstream-lock.json` identifies
only the historical import; `source-target.json` records the active target and
blocked acquisition state.

## Next steps

1. After certificate renewal, manually run `Discover canonical OuroDev i25 source`
   in Actions. Its public TLS check stops the job before authentication on failure.
   Alternatively inspect a user-provided canonical i25 ZIP/export.
2. Verify the documented branch; pin its commit/tree, inspect inventory/notices,
   submodules and large files, then import under `upstream/i25-score` with any
   exclusions recorded. Preserve the historical source separately.
3. Audit exact i25 build graph, bitness, third-party dependencies, rendering,
   authentication and every database path. Do not assume the previous fork's
   modern CMake/Win32 setup applies.
4. Establish a hosted reference build and matched content, then database and Thor
   runtime probes according to the [active proposal](ANDROID_PORT_PROPOSAL.md).

There is no scheduled retry, running background import, Android build or APK.
