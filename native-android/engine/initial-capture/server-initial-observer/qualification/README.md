# Focused qualification evidence

`host-03/qualification.json` is the final passed proof: three modes each execute
105 portable-ledger and 5030 production-adapter controls, with 206 recipe/schema
controls. Its 15 raw pins include the exact accepted source ZIP and three
original Map TUs. Five files reverse exactly; six executed host ELFs are retained
in the 154927-byte archive (SHA-256
`f7de31f951cead103407087f6824d9873451b18a6a1d98c47cad69629deaf8a2`).
Raw compiler and execution stdout/stderr are retained per mode.

The adapter executes with explicitly synthetic Map objects and Win32 providers.
It does not execute original Map, original packet/character serializers, the
Windows kernel, or a server session. ASan address checking and UBSan passed;
LeakSanitizer is explicitly disabled because the managed host denies its `/proc`
task traversal. The core/adapter allocate no memory. Full compiler/system-header
closure is not claimed. Original Windows compilation and runtime are separate.

`host-01` records the checker's wrong fixed ZIP-prefix failure before host
execution. `host-02` retains the release successes and exact failing ASan output
and ELF: LeakSanitizer could not inspect host tasks. Those attempts are not
relabeled as passing and are not the final qualification.

Receipt interpretation remains narrow. `pkt_send_called` is recorded at the
pre-call checkpoint, so alone establishes reaching that checkpoint. A process
can terminate before the following original invocation. Only
`pkt_send_returned=true` with `stop=FINAL_RETURN` establishes that the original
synchronous invocation returned. Neither raw return zero nor one establishes
whole fragmented-queue acceptance or socket delivery. An ACTIVE receipt is a
last successfully persisted checkpoint; later progress, final counters and sink
health remain unknown. All queue/socket/application/world authority flags remain
false, including after FINAL_RETURN.
