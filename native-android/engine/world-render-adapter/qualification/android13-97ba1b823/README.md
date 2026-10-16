# Consolidated source and Android 13 receipt review

Both workflows succeeded at source
`97ba1b82306858d0f6c4b2e226dfa435c8170c8a`, tree
`cfe06bab7c4cf7677b3477338acaff1fedaaea36`.

| Workflow | Host artifact | Android execution artifact |
| --- | --- | --- |
| [Primary 38951436617](https://github.com/Russianranger/coh-android/actions/runs/38951436617) | 12067748750 | 12068923240 |
| [Catalog 38951436564](https://github.com/Russianranger/coh-android/actions/runs/38951436564) | 12067963278 | 12068543749 |

Each downloaded archive was checked against GitHub's advertised SHA256:

| Archive | SHA256 |
| --- | --- |
| Primary host | `ce485167c03686900fe7b02fee925f2c668c7d74aef0774f897f7b0790bb4412` |
| Primary Android | `9be999895ba0e9920611c9f16734490d033f173a52fe523e5dd4864a3b52a168` |
| Catalog host | `47e80114f6c3d5c75923b392feeb3b8fac73e0d33ae5c48fd0ad44d568905cf7` |
| Catalog Android | `a8889e3c677854e9c09f35b7b918b401a977e933fd812f524afcebdd199a674f` |

Independent replay matched every declared source byte to `git show` at this
commit; checked clean qualified source, all preserved fixture identities,
both ABI executable/receipt SHA256 values and ELF machine identities; and matched
host release/ASan/UBSan results with actual Android execution. Graph
`lookup_fixtures.h` is independently bound to its host receipt and both build
receipts alongside the existing scene fixture. Costume fixtures are likewise
bound separately. The exact-source catalog admission driver passed read-only
replay against the full artifacts. Primary batch receipts show both drivers were
attempted successfully, and adapter execution returned zero with validated native
output and successful temporary-file cleanup.

| Standalone suite | Identical host sanitizer / Android assertions |
| --- | ---: |
| Entity records, rare bodies and costume/title/taskforce helpers | 2,570,029 |
| Character data | 232,005 |
| Entity controls | 667,138 |
| Global power modes | 5,930,110 |
| Scene graph and library/model lookup metadata | 265,494 |
| Saved catalog | 21,111 |
| Auth interoperability contracts | 2,147 |
| Immutable world adapter | 16,745 |

This is the first Android build/execution qualification of the new standalone
character-data and power-mode components in this continuation. Executed ABI:
x86_64, Android 13 / SDK 33 emulator. ARM64 binaries were built and their exact
identities verified, but ARM64 execution and physical Thor acceptance were not
performed. The adapter binary identities remain unchanged from the preceding
qualified checkpoint; no adapter implementation or accepted APK was rebuilt for
a device test. No installed application or saved profile was touched.

The suites qualify bounded, independently staged contracts. They do not validate
an authentic full-world transaction, resolve all materials/assets, identify an
authoritative rendered player, perform encrypted account login or admit a
renderer-ready scene. Gate 27 and the complete global/full-character transaction
remain open. Catalog stress data remain source-produced fixtures. No genuine
capture is attributed to these workflows; the separate authentic-capture work
has its own provenance. Optional Win32 exporter compilation was skipped and the
auth deployment workflow was not rerun by this source checkpoint.

Copied JSON/log receipts and the independent replay script are retained below.
Full binary/fixture archives were retained locally under
`/tmp/coh-qualification-97ba/{primary,catalog}` during this session and remain in
the linked workflow artifacts. The verifier requires those full extracted
archives; this evidence directory intentionally contains compact receipts,
without duplicating the generated executable payloads.
