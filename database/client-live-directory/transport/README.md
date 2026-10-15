# Source-only current-directory transport consumer

This directory implements the bounded byte-stream consumer, not native Game registration or a production optimization. No Game, Wine, FEX, PRoot, Android, AYN Thor, provider ownership, or source namespace qualification is established by these controls.

`coh_live_transport.c` has no socket platform dependency. The native wrapper supplies one already connected and exclusively owned TCPv4 loopback peer through blocking read/write callbacks, plus close and heap allocation callbacks. The wrapper must preserve platform errors in its callback context; close may change the platform's global errno/LastError. No reconnect, request replay, polling loop, or clock exists here. Positive short reads/writes continue the outstanding transfer; zero/negative/over-return terminates it.

## API and custody

1. Admit actual registered Game/process/session/main thread, current bind descriptor, supported constructor directory, runtime/source/ABI pins, and native directory authorization outside this transport.
2. Initialize the caller-owned `CohLiveTransport` once with operation16, protected auth nonce32, and callbacks. Those bytes do not themselves authenticate ownership.
3. Call `cohLiveTransportOpen(t, normalized_guest_path, caller_created_token16, expected_device, expected_native_inode, &handle)`. The native wrapper supplies an ASCII absolute POSIX guest path translated from its admitted Z: directory. Unknown native drives and unsupported directories must decline before opening this transport.
4. OPEN requires exactly 32 ACK bytes: backend held device u64, inode u64, scope recipe version u32=1, flags u32=1 (`CONSTRUCTOR_FIELDS_ONLY`), and eight zero bytes. Device and inode must match the caller's registered device/native-authorized directory inode before a handle is returned or any NEXT is sent. `cohLiveTransportIdentity` exposes the admitted per-handle identity. An old zero-byte OPEN ACK is refused.
5. `cohLiveTransportNext(t, handle, &wfd)` returns 1 for one privately owned 320-byte WFD, 0 for validated final end, -1 for initial decline, or -2 for terminal failure. WFD storage remains valid through consumption of its batch and until the next batch for that same handle or cleanup. Another cursor cannot replace it.
6. `cohLiveTransportClose(t, &handle)` sends one CLOSE ACK exchange when healthy and always releases that cursor locally, including on a failed close. `cohLiveTransportShutdown(t)` finally releases every remaining cursor/shared frame and closes the peer at most once. It preserves the first failure's reason, backend error/status, request/handle identity, and global/per-cursor rows returned.

Any I/O, protocol, allocation, or backend INITIAL_DECLINE after a row has been returned by any cursor is terminal globally. It must not trigger stock fallback, new enumeration, duplicate callbacks, or apparent end of directory. Before the first returned row, an initial decline permits the independently authorized wrapper to select ordinary enumeration. Backend TERMINAL is always terminal, including before any row. Failed OPEN allocation remains owned until shutdown; callers must run finally cleanup on every result. A successful shutdown retains successful diagnostic status; stale calls decline without socket activity.

## Bounds and wire format

The request is exactly 96 little-endian bytes: `COHLDIR1`, version1, OPEN1/NEXT2/CLOSE3, operation16, nonce32, monotonically increasing request sequence starting1, token16, path byte count, total byte count, reserved0. OPEN appends 1–1024 ASCII absolute normalized path bytes without a NUL terminator; NEXT/CLOSE have no path. A 32-byte reply has `COHRSP1\0`, version1, status0/1/2, matching request sequence, bounded payload length, backend error, reserved0. SUCCESS requires error0. Failed replies have no payload; CLOSE SUCCESS has none; NEXT SUCCESS contains one complete COHLIVE1 frame. Sequence wrap, old handles, duplicate active tokens, or more than16 simultaneous cursors fail closed.

Each heap cursor owns one immutable 27,944-byte maximum COHLIVE1 frame through the existing decoder. One additional heap frame is shared receive scratch. There is no 28KB recursive stack object. The fixture checks the total of all16 cursors plus shared scratch stays below480,000 bytes on this host; that is a portable object allocation bound, not Game/Android RSS. Final empty frames,85 rows with valid native8KiB geometry, directory limits, exact token/operation/sequence/row ordinal, and complete-frame validation precede returning any row.

The copied decoder is byte-for-byte identical to `native037-recovery/live-directory-bridge/coh_live_directory_batch.h`: 4,316 bytes, SHA-256 `767077bfefa2f023fbb558a0757d95e0d2021b2b12da7c4c18d25c6591292fc6`. It is not modified by this implementation. Full WFD API parity is not asserted; caller registration authorizes only the frozen constructor-consumed-field recipe.

## Freshly executed controls

```
python3 -W error::ResourceWarning test_coh_live_transport.py
python3 -W error::ResourceWarning qualify_transport_sanitizers.py
```

11 Python tests pass with zero skips;10 C groups perform7,268 checks. Coverage includes one-byte short I/O, partial failed request writes, partial reply header/payload EOF, callback errors/over-return, no replay, immutable private cursor frames, globally terminal late failures, retained backend errors, malformed protocol/batch fields, second-row atomic rejection, invalid native8KiB frame geometry, old/malformed ACKs, device/inode mismatch, active-cursor limits, stale handles, allocation failure, request/handle sequence wrap, normalized-path boundary, and validated empty/final/max frames. A real host TCPv4 random-port loopback test supplies short writes and one-byte reads. Its synthetic metadata is solely a byte-stream control.

The nine controlled C groups also pass AddressSanitizer and UndefinedBehaviorSanitizer. LeakSanitizer is **unqualified**: the first attempt failed because the executor's ptrace/proc visibility prevents inspection. That failure remains in `sanitizer-initial-environment-failure.json`; the passing ASan/UBSan report explicitly disables LeakSanitizer. Every controlled success/failure path separately checks exact allocator balance and one peer close. None of these host results measures device startup savings.
