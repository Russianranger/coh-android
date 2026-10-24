# Saved logical receiver inputs

These two gzip files contain exactly the recovered logical packets named by
HANDOFF section 5, from the 2026-10-21 Thor session 1a15fad27e9. They are
test fixtures for the original receiver, not network datagrams. The driver
and host both verify the uncompressed file identities before decoding:

| File | Bytes | SHA-256 |
|---|---:|---|
| initial-replay.bin | 37994 | cc949b01f5db6ff108efcf6afcbfe9567c432b4aa15f3a02c8f193e380cc7b39 |
| post-ready-replay.bin | 74416 | f134c3c083e571b679ed6976bec36c672028854f4a48879cc0f2d47423db96a9 |

The enclosing user report, screenshots and other diagnostics are not fixtures.
The INITIAL transport ID was not captured: it remains explicitly synthetic
and is tested as 1 and 31. No payload bytes are rewritten or sanitized;
changing one invalidates the reviewed input identity.
