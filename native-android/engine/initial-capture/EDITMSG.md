# Bounded original editor-message handling

The genuine run39088537547 public diagnostic at orchestration77af974e93324fadc61b4d3fb3f5b4ca15636ba7
reported a decoded SERVER_EDITMSG refusal after valid GROUPS and one REQALLENTS.
The sole retained ZIP is1,568 bytes, SHA256
`e9c61d5ce7aee72626facfb2808664ccca3f20e602244f8c334efa655224fbf9`;
its3,174-byte summary SHA256 is
`e9c77d5b883d2a875d8b377d99f8d5534c3db4f4869ca431da033dccb2315328`.
It supplies no message subtype, text, length, packet body or GAME_CMDS witness.
The separate absent original source envelope remains an independent failure.

Original `sendEditMessage` writes a standalone outer Pack1 SERVER_EDITMSG,
two-bit EditorMessageType and NUL-terminated `pktSendString`, then sends.
`bsWriteString` preserves the current bit offset; byte-aligned mode rounds the
two-bit scalar to one byte and starts the string on a byte boundary. There is
no length prefix or alignment step for the string itself. The complete packet
ends after its NUL. Original `commHandleMessage` reads those fields, invokes
error/high-priority dialogs or low/high-priority status text as applicable, and
calls `editNetUpdate` -> `editWaitingForServer(0,1)`. Those effects concern editor
UI waiting/status state; this branch sends no protocol reply or character ACK.
The nonshipping receiver validates the whole body and retains only scalars. It
does not execute the original dispatcher or reproduce interactive editor UI.

`svrTickDoNetSend` can invoke `svrTickSendQueuedErrors` after `entSendUpdate` and
before the later `entFinishUpdate` flush. The former creates type3 messages for
debug-access clients. Other callers include player errors and editor commands.
This source ordering permits an editor message to arrive first; it does not
identify the actual observed message subtype or producer.

Only an actual owned message after one REQALLENTS, while WAIT_ALLENTS with the
same claimed DB/Map/selection owner, schema and a later message generation, can
enter this branch. The parser reads type0..3 and every string byte through NUL,
requires the exact logical packet end, and polls cancellation every256 bytes.
It refuses extra trailing bits/bytes, truncation, missing NUL, invalid aligned
type bits and unsupported commands. The16,384-byte limit including NUL and16
handled-message attempt limit are explicit diagnostic domains, not source limits.
Transport remains16KiB encoded/4MiB decoded. No packet/text allocation or copy
is added. At most262,144 string bytes can be handled per attempt, plus one
bounded refused candidate; the ordinary message budget and timeout also apply.

Internal typed outcomes distinguish a complete EDITMSG from ALLENTS. The
message count and last type/length commit only after successful loan release
and final cancellation polling. A failed candidate leaves these scalars at
their previous successful values. Prior GROUPS evidence survives every later
failure. Handled editor messages keep the original REQALLENTS deadline, do not
call the observer, and do not send another application request. Unknown commands
still terminate without scanning or skipping. Raw ALLENTS retains its existing
separate observer, release and CAPTURED close path. No READY,
RECEIVED_CHARACTER/full-update ACK, actor, world, current-dictionary generation
or complete-character authority follows from either branch.

The exact original whole-file and whole-function LF hashes are in
`editmsg-source-pins.json`. `editmsg_fixtures.py` executes unchanged whole
`sendEditMessage` and original packet/bit writers on trusted bounded inputs.
Explicit adapters supply a bounded estr buffer, packet storage and send record;
the original console printf is counted instead of printing message data. Both
bit profiles, all four types, empty/nonempty/boundary/overlong strings are
fixtures, not observations of the live message. Neither original network nor UI
dispatcher executes. The focused new suite reuses setup helpers without calling
any historical DB/initial-capture suite main or root CLI checker.

```
python native-android/engine/initial-capture/check_initial_editmsg.py \
  --source-root "$PWD" --output /tmp/initial-editmsg.json --sanitize
```

For new root CLI controls, call `editmsg_fixtures.produce_fixtures(root,work)`
and compile `test_initial_editmsg_peer.c` with the existing generated UI fixtures.
Its `--serve --report PATH --mode` accepts `editmsg-captured`, `editmsg-unknown`,
`editmsg-malformed`, `editmsg-limit` and `editmsg-none`. These produce respectively
source-layout EDITMSG then synthetic raw ALLENTS, EDITMSG then GAME_CMDS refusal,
truncated NUL, overlong source string, or valid EDITMSG then silence. Public
stdout remains the existing20-field schema. No new production translation unit
or ordinary source change is needed. This wrapper still has no global aggregate
memory/RSS admission; measured wrapper sizes add to all existing module owners,
caller callback storage and transitive decoder allocations.

The new focused source revision is
`2f8337277b25b10a43b6d9b2001c68e7860b8340`. Release/ASan/UBSan each passed22
transaction scenarios and17,058 direct parser cases. Check totals are25,246 /
25,254 /25,246 respectively; allocator instrumentation contributes checks, so
mode totals can differ. The40 unchanged original sender fixtures cover two
profiles, all four source types and five lengths. Controls include each short
body truncation, aligned reserved type bits, zero/nonzero trailing bits, exact
16KiB boundary, overlong strings,16/17 messages, original deadline, phase/owner
guard refusal, release errors, first-error priority, final cancellation rollback,
same-service EDITMSG then ALLENTS/unknown/decode failure, and budget1 continuation.
The same-service decode failure caught a stale local error cause; the final
source resets both classification and default PROTOCOL cause before every fetch.

All79 source/header/helper hashes equal the qualified Git revision and current
bytes; all ordinary inputs match the prior C baseline. No old public/owner test
main, root CLI checker or capture was executed. The deterministic receipt is
`qualification/initial-editmsg-2f8337277.json.gz`; its binding JSON records exact
compressed/decompressed hashes, per-mode results and unchanged ordinary inputs.
Root's new CLI qualification/build is separate and is not claimed by this proof.

Measured host wrappers are1,088 +1,312 =2,400 bytes,16 more than the classifier
baseline. Diagnostics grew8 bytes to1,032 because new fields also occupy prior
padding; it is embedded in each wrapper and is not an extra allocation.
Ordinary Local1,040 /Map2,536 /loan1,344 bytes are unchanged. The three retained
EDITMSG fields remain scalars; no text buffer, heap allocation or packet copy was
added. These sizes are not a global simultaneous-owner or RSS admission.
