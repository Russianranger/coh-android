# Independent GPU lease bridge review

F found no remaining concrete blocker in the six new files at E source
`1312257b7505b78adb85745c8ebcf9d9cabf219a`. The exact 16,616-byte owner
receipt is preserved as `qualification.json`, SHA-256
`655eb3a81a7d31cba656794782ba1a62ab03f675b92e8f444aa76d03be53e026`.
F checked all 27 project-source hashes against the worktree and exact commit,
read production/API/model/EGL/checker code, and did not replay the qualifier.

Requested closures are included: failed registry retain/begin cannot acquire an
unreported pin/gate, every take slot is disjoint from every input path, and the
fixed path-length workspace increases the explicit control reservation to
64 KiB. Conservative host stack sum times four is 36,096 bytes. Metadata still
adds `sizeof(CohWrGpuLease) + texture_count*sizeof(Item)`; all old/new CPU/GPU,
registry/provider/driver and input storage remains external. Drop or numeric
retirement does not reduce the parent reservation.

The new receipt reports 96 model controls and 602 actual private EGL checks for
each release/ASan/UBSan/finite-fixture mode, four actual uploads, 37 readbacks,
four balanced registry pins, three verified deletions and one verified
dead-context disposition. Two contexts and three surfaces are cleaned. Pillow
all nine mips, actual C/C++ linking and five semantic mutation refusals pass.

This closes an explicit lease/GL-maintenance source path: control drops do not
delete; zero leases precede owning-context drain; partial failure retains the
whole-context gate; collection follows complete disposition. Application backend
registry/gate contracts still require a real implementation. No application EGL
adoption, production prepare, current namespace/generation, global parent fit,
Android ABI, process RSS, actor/material/world authority is established. The
system GL driver is unsanitized, and only declared library files are hashed.
