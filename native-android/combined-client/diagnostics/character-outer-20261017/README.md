# Original outer-character wire oracles

Pin: `767d55e48fa35261f1428bd542aa6cd3b2b9fa32`. Production character/entity,
renderer, gameplay and launcher files are unchanged. These diagnostic helpers
supply reproducible raw source vectors for the native composition worker.

`group4_oracle.generate(texts)` returns original C source, whole-function hashes
and exact inline-block hashes. `qualify(texts)` compiles that source and returns
60 fixtures. Each fixture records scenario, scalar alignment, begin/end bits,
complete raw bytes and nine original-consumer observations. The generated C
exports `group4_fixture(scenario,aligned,prefix,out,bits,end,observed)` and
`group4_counts(out)`; all scalar arguments/outputs are unsigned 32-bit, byte output
capacity must be at least 1 MiB, observation capacity at least 9 words.

Group4 starts immediately at `sendTray` and ends after all 128 `sendWindow`
records, before reward tokens. It executes the exact original sender and consumer
inline blocks; full original tray sender/reader/object functions; full iterator
control flow; original windows, strings and help consumers. Original writer and
reader cursor ends agree for all 60 cases. An independent bounded Python decoder
also agrees on every cursor and all observations. Cases cover both scalar modes,
bit offsets 0–7 or byte offsets 0/8,720 tray slots across 8 builds, normal/hidden macros,
powers/inspirations/empty/other types, default power and mixed window variants.

Earray capacity, object storage, known power/inspiration dictionaries and UI
callbacks are explicitly synthetic shells. All modeled dictionary indices are
zero. `TEST_CLIENT` excludes window UI application. No full gameplay consumer,
dictionary admission or semantic state application follows. Other tray item
kinds are retained raw by future native staging; the original fixture consumer
creates an empty object for them. The fixture observation projection preserves
that distinction. `receiveEntStrings` changes description angle brackets to square;
raw staging must retain the wire text separately.

`qualify_outer.py` separately executes full original window/string helpers and
the exact complete saved/default options sender branch. Saved options execute
the complete original `receiveOptions` against the unchanged enum, option table,
stash initialization and lookup functions; the stash storage itself is a fixture
shell. All1560 cases agree with the independent byte model. Selected rich helper
bodies also reject every bit truncation in that bounded model. Malformed data is
never passed to the original unbounded routines.

Original code retains its x86 assumptions and runs unsanitized at O0 with strict
aliasing disabled. Native parser ASan/UBSan qualification belongs to the consuming
module. There is no native parser, Android binary, server capture, physical test,
authoritative actor, complete character or protocol acknowledgement in this work.

`outer-grammar.json` records exact full groups 4–6 order and option names/widths,
with whole-function and source-file hashes. It distinguishes executed helpers
from remaining token/chat/keybind/friend/monitor helpers. Chat is 5 windows, 20 tabs,
15 channels and 2 system-channel words; tabs' bit arrays align independently.
Window count is 128, help status/latest counts 128/5, keybind count 256, monitor
count 10, options count 114. No optional branch is assumed absent.

Run from the repository root:

```sh
python3 native-android/combined-client/diagnostics/character-outer-20261017/qualify_outer.py --output /tmp/outer-helper-proof.json
python3 native-android/combined-client/diagnostics/character-outer-20261017/group4_oracle.py --output /tmp/outer-group4-proof.json
python3 native-android/combined-client/diagnostics/character-outer-20261017/schema.py
python3 -m unittest discover -s native-android/combined-client/diagnostics/character-outer-20261017 -p 'test_*.py' -v
```

Retained fixture archives are deterministic gzip files. Their exact SHA256,
expanded size and count are checked before replay. The 7 diagnostic tests cover
source-pin refusal, exact original fixtures, false observation refusal, truncated
group4 bodies, source constants and authority boundaries. Existing source worktrees
and accepted binaries remain unchanged.
