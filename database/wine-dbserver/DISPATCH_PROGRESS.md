The staged Wine DbServer has an opt-in dispatch observer for the intermittent
Atlas startup stall. It is diagnostic evidence only: a marker does not establish
SQL completion, map readiness, character persistence, or gameplay success.

With `COH_WINE_DB_PROGRESS` absent, initialization creates no file, mapping,
thread, or synchronization object, and every marker returns immediately. An
explicit absolute Windows drive path enables one unnamed, 4096-byte file mapping.
The launcher must provide a private parent directory and a different fresh file
for each launch. `CREATE_NEW` refuses existing evidence. A requested normal launch
exits nonzero if initialization fails. The persistence fixture entry point still
bypasses normal startup; both fixture-enabled and ordinary builds contain the
same observer for normal launches.

The first 128 bytes are a versioned little-endian record. The hash-bound build
receipt publishes its offsets and stage names, parsed from the C enum. It includes
the Windows process and main-thread IDs, a stage, a loop count, and a sequence.
Main is the only writer. Each marker publishes odd sequence, payload, then even
sequence using aligned volatile 32-bit stores and compiler barriers. This relies
on the qualified x86 target's store ordering; compilation rejects other targets.
There are no clocks, OS calls, file writes, logging, allocation, locks, or new
threads in a marker. Sequence saturation sets a flag and stops publication rather
than wrapping; flagged samples are unavailable evidence.

An external observer reads the bounded record twice, requiring identical bytes,
a positive even sequence, zero flags, the expected identity, and the receipt's
format and stage count. Repeated samples with advancing sequence establish main
thread progress between those samples. A stopped stage identifies the operation
about to run, including its nested calls; it does not identify a particular
instruction or prove a deadlock. The record persists after process exit, so
process liveness and launch identity must be checked separately. The reader's
timestamps provide observation times; the record intentionally has no clock.

Markers cover initialization, each broad `msgScan` operation, the foreground SQL
keepalive and queued keepalive work, the main-loop shutdown tick, and console
poll/read/command handling. SQL keepalive check includes the existing clock call;
the foreground and queue markers are written only when the keepalive is due.
The upstream source remains immutable: preparation applies the PostgreSQL patch
first, then the receipted Wine patch and overlay. The marker source, enum, and
patched call sites are bound by the same build-input receipt used for packaging.

The separate [fixed-input mode](FIXED_INPUTS.md) is a scoped candidate response to
a captured stop at `FOLDER_CALLBACKS`. It does not change the observation format
or make a stationary stage proof of deadlock. Its runtime qualification is a
separate gate.
