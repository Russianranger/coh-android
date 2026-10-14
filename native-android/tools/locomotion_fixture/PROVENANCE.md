# Gate18 locomotion fixture provenance

Binary inputs are exact members of the existing reference asset pack,
`coh-assets-v1.0.0`, acquired using bounded HTTP/ZIP ranges. `pins.json` records
member path, byte count, compressed size, inner ZIP offset, CRC32 and SHA256.
Whole archive hashes are published provenance and are not claimed verified by
this subset acquisition.

The authored subset binds `V_Arachnos_Wretch` to `player.txt` type `huge`, using
its existing `huge/Skel_ready` base hierarchy. The source definitions and
functions are hash pinned in `source-pins.json`. All source types and files
remain part of the unchanged imported source trees.

`prepare.py` writes one runtime asset, `locomotion.bin`, and metadata
`locomotion-fixture.json`. The three embedded rig headers contain the literal
source animation ranges1–60,1–25,1–23. All animation byte records and encoded
key payloads remain unchanged. The huge/postrun file includes unused source
tracks50/51/52 outside this base hierarchy. Those records must still pass the
raw parser's bounds, format and numeric checks; source sampling only traverses
the selected base skeleton, so those extra tracks are not added to the rig.

`check.py --fixture locomotion.bin --source-directory upstream --morph morph.bin
--output host-proof.json` accepts either the repository's `upstream` directory
or a flat directory of the pinned source files. It compiles and executes six
unchanged original timing/rate/sprint functions and the already-qualified
original compressed-key sampler. The deterministic offline selection wrapper
is identified explicitly. It does not execute the original priority/IRQ search
or claim the complete source sequencer.

The staged `source/`, `corpus/` and `results/` directories are ignored scratch
outputs. Do not publish duplicate imported source trees or the binary corpus as
new repository files; CI reacquires and verifies the exact source inputs.
