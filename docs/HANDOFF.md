# City of Heroes Android handoff

Updated: 2026-09-23.

## Completed in this assessment

- Inspected the empty `Russianranger/coh-android` destination and prior September
  13 port plan.
- Attempted direct OuroDev access; GitLab/git requests returned HTTP 502 and wiki
  requests returned HTTP 403.
- Imported the complete public OuroDev-derived fork at
  `0b75ade0c801735e10c5798f641948a45cc50488` into `upstream/ouroboros`.
- Preserved all 5,995 files, bundled SDKs, config examples, build definitions and
  notices without edits. Recorded acquisition details and per-file hashes.
- Audited build restrictions, database providers, service dependencies, physics,
  rendering, input/audio, shared memory and content requirements.
- Wrote [the staged Android proposal](ANDROID_PORT_PROPOSAL.md) and verified
  snapshot identity. No port implementation or APK was created in this assessment.

## Next implementation sequence

1. **Reference build and data:** set up a Windows build runner matching the
   imported presets; freeze its toolchain and all dependencies. Obtain the
   companion data candidate at the lock's revision, inventory external binary
   assets, generate templates/bins, and create a hashed runtime package. Prove
   combat, normal mission entry/exit and character save/reload using MSSQL.
2. **Database prototype:** add an x86 Windows ODBC connection/transaction harness
   for PostgreSQL. Audit provider-specific SQL and attributes; fix the confirmed
   `sqlRemoveIndexAsync` PostgreSQL syntax error on a separate port branch. Test
   schema creation/evolution and game persistence with MSSQL stopped.
3. **Android diagnostic runtime:** app-owned ARM64 PostgreSQL plus Wine/FEX
   candidate, Win32 ODBC harness, process supervision and support-log export.
   Prove app-identity execution, child processes, shutdown and restart on Thor.
4. **Playable server:** integrate modified DBServer, Launcher/MapServer and any
   services actually required by the profile. Test with a desktop client first.
5. **Integrated client:** evaluate OpenGL/Cg via Wine/Mesa and the selected Vulkan
   driver; add editable controller mapping, audio, surface and focus handling.
6. **Product workflow:** imports/profiles, offline operation, backup/restore,
   update rollback, memory/thermal testing, then additional services.

These are work packages and acceptance gates, not already running jobs. The
current request authorized the source import and assessment/proposal. Subsequent
implementation should follow the user's next direction.

## Facts that must survive a handoff

- The acquired tree is an OuroDev-derived **downstream fork**, not verified
  identical to canonical OuroDev. It is Issue 24/Volume 2 lineage, not the older
  Issue 25 SCoRE snapshot used by the initial plan.
- Main targets are **MSVC Win32**. A MinGW preset exists but does not imply a
  portable MapServer/Game build. No Android toolchain has been added.
- PostgreSQL code exists but the shipped config says only MSSQL is supported.
  There is a confirmed malformed PostgreSQL DROP INDEX statement.
- Authentication, accounts, auctions and chat have separate persistence paths.
  Never call the whole server database-independent after testing only DBServer.
- Rendering is **desktop OpenGL/Cg**. Validate the correct graphics path before
  applying settings learned from Direct3D games.
- PhysX is actively linked into the selected MapServer and Game build; the
  bundled Windows binaries are not native ARM64 dependencies.
- Minimal fake-auth/local-map smoke tests do not prove ordinary mission transfer,
  account entitlements, full persistence or multi-map memory behavior.
- The companion data commit is pinned as a candidate, not a tested match. Full
  binary assets, generated bins and database templates are not in this repo.
- No CoH executable, Android APK, database migration or Thor benchmark was run.

## Verification and source updates

Run `python3 tools/verify_source.py` from the root before starting patches. Its
purpose is to verify the unchanged source snapshot, so deliberate source changes
will require a separate patch strategy or an explicitly updated validation
contract. Preserve the original import commit for comparison. Do not silently
regenerate the manifest over port changes and call them unchanged upstream.

Current source metrics and provenance are in `upstream-lock.json` and `docs/`.
Do not download a moving latest game release and assume protocol, bin or schema
compatibility with this source lock.
