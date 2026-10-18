Run `39081284721` stopped in the seven-method Windows host gate: five passed,
one mock-call comparison failed and one temporary Git-fixture ownership check
errored. Auth/Db artifact recovery and service observation were skipped. The
receipt upload found no output, and the run has no artifacts. This is not a
service startup or readiness result.

Both failures used an unresolved Windows temporary path with the public runner
profile's 8.3 alias. Production correctly resolved it to its long path. The
candidate fixture compared the unresolved expected path with that resolved
actual path; the Git fixture compared a resolved patched module path with its
unresolved root. The two-line test-only fix resolves those fixture roots before
comparison. Production identity guards, profiles, deadlines, builder inputs and
the admitted PE are unchanged. All seven methods pass on Linux after the fix;
the corresponding actual Windows followup remains unverified.

`failure.json` preserves fixed job statuses, sanitized public test diagnostics
and zero-artifact metadata without raw temporary paths. `fix-proof.json` binds
the tested bytes to the committed two-line change. No C compiler, Auth account
qualifier, service restart or shipping profile change was performed.
