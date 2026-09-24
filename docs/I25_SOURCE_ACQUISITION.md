# Canonical i25 source acquisition

Checked 2026-09-24 from GitHub-hosted Ubuntu runners.

| Item | Finding |
| --- | --- |
| Source project | `https://git.ourodev.com/score/SCoRE.git` |
| Documentation | [OuroDev i25 modding guide](https://wiki.ourodev.com/Modding_your_i25_Server), through search indexing; direct wiki fetch returned 403 |
| Documented branch candidate | `Lexicon-Project(Co)X` |
| Actions secret | `secrets.odtoken`; present/nonempty |
| Credential validity | Untested: TLS fails first |
| Remote refs/commit | Not read; no commit pinned |
| Certificate subject | `CN = git.ourodev.com` |
| Certificate issuer | `C = US, O = Let's Encrypt, CN = YR1` |
| Certificate valid from | 2026-06-25 10:39:55 UTC |
| Certificate expired | 2026-09-23 10:39:54 UTC |
| OpenSSL result | Error 10: certificate has expired |
| Import result | Blocked; no canonical i25 source copied |

The [first Git discovery run](https://github.com/Russianranger/coh-android/actions/runs/35937593556)
failed certificate verification. The [second diagnostic run](https://github.com/Russianranger/coh-android/actions/runs/35937652690)
used an explicit system CA bundle and OpenSSL hostname/chain checks. It identified
the expired leaf certificate. This is not evidence of an invalid token.

The probe uses a temporary askpass helper and environment secret, never a token
in a URL, committed file or public output. TLS verification remains enabled. The
workflow now stops before its credential-bearing step if the public TLS check fails.

After certificate renewal, rerun the manual discovery job and verify branch/commit
before importing. No token change is needed merely because of certificate expiry.
A user-provided canonical archive can also be inspected; record its URL, branch,
commit if available and extracted-file hashes rather than claiming a Git checkout.

The historical Volume 2-derived snapshot does not satisfy this acquisition.
Do not substitute a different lineage or VM image for the requested i25 source.
