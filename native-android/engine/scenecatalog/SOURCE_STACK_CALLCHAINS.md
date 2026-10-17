# Corrected native call-chain stack supplement

The file-maxima sums in source-measure-host.json are historical compiler frame
observations, not a call-chain proof. Multiple frames from one translation unit
can coexist. This supplement supersedes that arithmetic while preserving the
original624-control geometry/ownership evidence and all production source bytes.

The stack-only checker freezes the same64 source hashes before compilation and
revalidates them afterward. It compiles, but never links or runs, the production
translation units with GCC -fstack-usage and -fcallgraph-info=su. Every compiler
call-graph definition's frame bytes/kind must match its .su entry. Static symbols
are qualified by translation-unit path, global native symbols are joined across
units, and all emitted compiler edges are retained, including same-file calls.

For each public sealed create/measure/probe/free/getter entry it computes the
maximum sum along reachable native call chains. Native recursion, unresolved
coh_ or translation-unit-local targets and unbounded dynamic native frames refuse.
Compiler inlining is reflected in the emitted caller frame; tail-call edges may
conservatively retain both caller/callee contributions. The original index find
passes rowcmp to libc bsearch: an explicit pinned source edge includes that native
comparator frame. The O0 external-bsearch callers are checked to be that exact
find function. Optimized inlined bsearch paths expose comparator calls directly.

| Compiler mode | Maximum compiled native chain, bytes |
| --- | ---: |
| O0 |8,528|
| O1 |8,200|
| Release O2 |8,088|
| ASan O1 |11,856|
| UBSan O1 |8,448|

All native-chain totals fit the existing16,384-byte native preparation reserve;
no reserve or production code changes are required. O0 includes the actual
create→measure→source_control chain, plus batch dependencies→safe→known, mesh/body
dependency getters, index owner-source lookup→find→bsearch→rowcmp. All those
same-file and cross-file descendants contribute simultaneously. The largest ASan
path starts at ws_probe→measure and continues through the same dependency chain.

External library, allocator, libc bsearch implementation, cancellation callback,
stack-protector failure and sanitizer runtime frames are explicitly unmeasured
cutpoints, not zero-stack proofs. The native comparator beneath bsearch is counted
while the library's own frame remains in the caller's external allowance. The
existing provider/runtime/callback allowance contract still applies. This is not
a process-stack/RSS bound, Android ABI qualification or a claimed bound on arbitrary
callbacks. The parent working-set report's native frame is included in the graph.

Raw compiler .ci and .su text, reachable edges, frame tables, exact maximum paths,
all entry-point totals, compiler version and external cutpoint lists are retained
in evidence/source-stack-callchains-verified.json.gz. The checker itself is frozen
and hashed. No project Python imports or cached bytecode are used. No geometry,
server, capture, CI or native diagnostic binary was executed for this correction.
