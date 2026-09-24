# City of Heroes i25 Android: active proposal

Updated 2026-09-24. The user selected **OuroDev i25/SCoRE source** and has no
Windows PC. This supersedes the previous source selection. The earlier
[Volume 2 assessment](VOLUME2_PORT_PROPOSAL.md) is historical reference.

## Evidence boundary

The canonical target is `https://git.ourodev.com/score/SCoRE.git`. OuroDev's
indexed [i25 modding guide](https://wiki.ourodev.com/Modding_your_i25_Server) names
`Lexicon-Project(Co)X`. Its availability, commit and build dependencies must be
verified through authenticated Git access.

The Actions secret `odtoken` is present. Authentication is blocked before
credential validation because the server's TLS certificate expired at
2026-09-23 10:39:54 UTC. See [acquisition evidence](I25_SOURCE_ACQUISITION.md).
No canonical i25 files or executable changes were produced in this pass.

The previous import's modern CMake presets, compiler version, Win32-only gates,
source paths and TestClient behavior are not verified properties of this i25
branch. The September 13 historical SCoRE research remains a lead for the database
audit, not evidence of the exact canonical revision now requested.

## Implementation sequence

| Stage | Deliverable | Acceptance gate |
| --- | --- | --- |
| 0: canonical source | Verified branch/commit, feasible complete source, integrity manifest and provenance | Canonical checkout or user-supplied export; code, SDKs, data, submodules and large-file exclusions inventoried |
| 1: hosted reference build | Windows CI with the exact i25 compiler/SDK/dependencies, matching content and generated templates/bins | Repeatable binaries and version manifest; headless login/map/persistence checks where supported; no user Windows PC required |
| 2: persistence audit | Inspect DBServer, auth, accounts, chat, auctions and all enabled storage | Test required SQL operations and whether i25's PostgreSQL path can replace MSSQL without losing character/account state |
| 3: Thor diagnostic runtime | App-owned ARM64 database candidate, Wine/translator candidate, ODBC/runtime probes and logs | Process lifecycle, transactions, restart, shared memory and children work without Termux/root |
| 4: playable i25 | Matching Thor client and required server/map services | Combat, ordinary mission transfers, save/reload and renderer correctness pass on Thor; desktop client is optional |
| 5: offline app | Imports/profiles, controller/audio, backup/restore, updates and recovery | Fresh installation to play, offline operation, consistent restore, long-session and thermal checks |

Provisional architecture: preserve Windows game processes under a tested Wine
translation environment and evaluate native ARM64 PostgreSQL for storage. Inspect
the actual i25 executable architectures, physics SDK, graphics/shaders and database
provider before selecting runtime versions. FEX is a candidate, not demonstrated
CoH compatibility. Native ARM64 conversion is a later workstream.

Hosted Windows build/SQL automation replaces a user-owned PC. CI is not assumed
to provide a persistent public game server or graphical gameplay verification.
Bring forward a Thor client probe for visual tests. Audit and extend headless
TestClient coverage only after reading i25's implementation. No paid compute or
user-installed Windows tooling is assumed.

## Source and content boundaries

Acquire source code, not a VM image. Game data, client binaries, generated bins,
schemas and SDK/runtime packages may be separate. Match and hash those versions
before starting a server. Do not combine the earlier Volume 2 content candidate
or binaries with i25. Preserve notices and record unavailable or oversized
components rather than representing a partial source import as runnable.

## Next action

After the site's certificate is renewed, retry authenticated SCoRE ref discovery;
alternatively inspect a canonical i25 archive supplied by the user. Pin the verified
revision and import separately into `upstream/i25-score/`. Then perform the exact
source's build/dependency/database audit and expand this proposal into implementation
work. No Android implementation has begun.
