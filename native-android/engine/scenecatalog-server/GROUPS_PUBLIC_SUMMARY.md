# Minimal public GROUPS status

`summarize_groups_capture.py` reads only the private supervisor's exact
`capture-receipt.json`. It constructs a new fixed allowlist: pass/runtime/
matching/cleanup/unchanged booleans, three exact source/native pair booleans,
fixed development-authentication/authority scope, fixed internal capture/failure
stage names, and a coarse failure enum
defined in this helper. It never serializes a private dictionary or copies a
failure/exception string. Account, character IDs, dump hashes, native/source
bytes, envelope, run identity, receipt, paths and logs remain private.

The helper checks its actual committed bytes at `GITHUB_SHA`, records only that
public revision and its own source hash, writes an exclusive0600 summary, and
refuses malformed flags, admitted-world assertions, duplicate keys, shared-mode
or linked private inputs. Missing/invalid private receipts yield fixed
`PRIVATE_RECEIPT_ABSENT`/`PRIVATE_RECEIPT_INVALID` summaries. A failed source
capture maps to `SOURCE_CAPTURE_NOT_ACCEPTED`, independent of its private error.
No source-generation, actor, current-scene lifetime, renderer, ACK or world
authority follows from a passing summary.

The workflow must upload only the explicitly named summary and separately
constructed public pre-runtime tooling facts. Never add a whole private
work/output/input directory, raw capture receipt/run identity, account, source
envelope, native packet or log to an artifact path.

Eight offline test methods in `test_groups_public_summary.py` exercise fixed
shape, strict Boolean/schema/authority refusals, private canary fields at every
ignored location, raw exceptions, absent/malformed/duplicate/linked/shared-mode
inputs, successful emission and exclusive output. They execute no server or
capture. They do not admit any actual source/native runtime observation.

`groups_capture_stages.py` owns the explicit stage vocabulary. The supervisor
assigns these labels internally at Wine/ODBC/PG restore/DbServer/MapServer/native/
pair/retention/cleanup boundaries. Its primary failure stage is preserved while
cleanup runs; a cleanup-only refusal uses `CLEANUP`. Preflight with no private
receipt emits `PREFLIGHT`. No stage is copied from an exception, SQL, account,
caller error string or arbitrary private field. This identifies a failed stage
without uploading its raw logs or losing the original failure behind cleanup.
