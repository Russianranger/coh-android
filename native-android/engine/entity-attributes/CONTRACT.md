# Original monitor-only attribute description

`coh_attrib_monitor_read` consumes the original new-target bit, full-mode bit
and monitor-only body of eleven tagged slots. Ten slots come from source
MAX_COMBAT_STATS and the final defense slot uses the original CharacterAttributes
definition. Each present slot retains its raw32-bit key, finite IEEE32 value and
2-bit buff/debuff word. Keys, including unknown values and duplicates, remain
raw. No dictionary lookup, monitor/UI change, target identity or attribute
application occurs. Absent slot payload stays zeroed, with presence retained.
The outer attribute-present bit is the caller's responsibility.

Full mode returns COH_UNSUPPORTED atomically. It requires the exact ordered
attribute category/dictionary generation and contribution grammar; this module
does not infer those from fixture keys or byte counts. The source oracle's
synthetic description/value lookups do not establish native dictionary authority.
CharacterAttributes has source size460 and fDefense offset184 in the source
fixture; those are admission checks only, not a fabricated native dictionary.

Reader, input, output and workspace spans are pairwise disjoint and overflow
checked. Caller-owned POD storage has no allocation or retained input. Budget
charges input, both PODs,4096-byte conservative stack reserve and caller-retained
bytes once within8MiB. Reader/output commit only after every slot validates;
workspace is scratch. Subsequent dynamic-group and sky/slave bytes stay unread.

The F provider executes the whole original sendAttribDescription and
receiveAttribDescription with explicit winLocsNULL monitor profile, description
lookup/value callbacks and UI shells; full-mode callbacks assert if reached.
Native release/ASan/UBSan compare120 exact field/cursor fixtures and exercise all
fixture truncation bits/single-bit mutations, trailing data, unsupported full
mode, finite-value refusal, budgets, aliasing and atomic rollback. C++ linkage
and emitted conservative reachable stack sum are checked. Original source
oracle itself is unsanitized. There is no full attribute mode, dictionary,
Android app execution, whole initial update, actor, ACK or live qualification.
