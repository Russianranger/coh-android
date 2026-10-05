# Native training and following-load validation

This is a read-only diagnostic correction for the UI/beacon continuation after
the 0.13.13 Thor reports dated 2026-10-05. It changes no native executable,
character input, SQL transaction, schema or saved profile.

The first report recorded a native Aimed Shot purchase and a normal logout,
then rejected the committed `ents` comparison. The second recorded another
normal logout and rejected `powers`. Those reports remain failed diagnostic
reports. The user observed no crash; their SQL outputs establish that the
first session saved level 2, Aimed Shot, 140 XP and 103 influence, and the
following session retained them. See [the device review](ANDROID_UI_BEACON_DEVICE_RESULT.md)
for the raw report identities and startup phases.

Two source-bounded differences explain the validator failures:

- The shipped `schema-manifest.json` maps `vars.attribute` names in lowercase,
  including `class_blaster` and `blaster_ranged.archery.aimed_shot`. Native
  `BuyPower` logs preserve authored capitalization. The original host training
  fixture used authored capitalization for both and missed that difference.
  `native_training_save.verify` now compares ASCII attribute names with the
  native dictionary's case-insensitive lookup semantics. Positive UniqueID
  conservation, exact eligible purchase, first internal-level transition
  0 to 1, seven finite automatic grants, point credits and ordinary save gates
  remain required.
- On the following native load, `unpackEntPowers` in `character_db.c` assigns
  each autoissued power's `piAvailable` to its parent's `iLevelBought`. The
  final owned power in each set determines that shared field.
  `packageEntPowers` later writes the shared parent field to every row.
  `powers_load.c` marks the Inherent category automatic. For this exact
  level-2 character, the last owned Inherent power is Fitness Fix at internal
  level 1, and all four Fitness powers become available at 1. Consequently,
  all eleven existing Inherent/Fitness rows change only
  `PowerSetLevelBought` from NULL/0 to 1. This is native load/save normalization;
  it is neither a second purchase nor a change to the powers owned.

The new normalization proof applies only to the typed repaired DbServer
producer, the ordinary reopen path without an authored task gate, internal
level 1 before and after, the preserved Blaster/Archery/Gadgets profile, all
eleven finite known automatic powers, and the owned ready connection and
requested ordinary logout. Every other selected power field, UniqueID,
SubId, PowerID, row count and order stays exact. Unknown powers, changed
purchase levels, boost-slot fields, other set levels, identity drift and
missing/stale/foreign sender or native-ready evidence still fail. Every other
selected character table retains its existing checks. An already normalized
following reopen uses the original exact comparison and needs no exception.

The report names the normalization explicitly and stores before/after row
digests. It does not claim a new purchase. `selected_non_reward_rows_preserved`
is false when training or this normalization changes selected fields; the
specific preservation policy and native evidence describe the accepted
semantic difference.

## Host regression evidence

`tools/android/interactive/fixtures/thor-training-normalization-0.13.13-20261005.json`
retains the two exported SQL transitions, used IDs from the actual shipped
attribute mapping, owned connection evidence and relevant original native
log lines. Private logout sender receipts were not exported in those ZIPs;
the replay supplies a synthetic current-session receipt immediately before
the real native timer. This exercises the complete validator/save pipeline
without retroactively turning a historical report into a passed device test.

`test_training_save.py` has 19 scenarios, including both real row transitions,
full disconnected-SQL ordinary-save replays, all selected-field mutations,
row/UID changes, sender/producer/task exclusions and native source/data checks.
The retained combat reward, reopen, task integration, reader contract and
ground suites also pass (59 scenarios). New on-device reports must independently
prove their own current sender, native position, logout and committed rows.
