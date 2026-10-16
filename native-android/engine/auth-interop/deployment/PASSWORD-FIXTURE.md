# Disposable password fixture qualification

`password_fixture.py` executes unchanged original `EncPwdSha512`, the complete
original `cryptLib` SHA512 implementation, and the exact digest conversion
fragment from `CAccount::CheckPassword`. It compares 69 bounded ASCII cases with
the existing native login request builder's captured RSA input and independent
Python SHA512. Every byte of each 64-byte digest is altered in negative controls.
The original password/hash consumer controls pass 4,554 checks in each release
and ASan/UBSan run. All original source inputs and fragments are hash-bound.

This executes the digest conversion fragment, not complete `CheckPassword`, its
ODBC operations, RSA encryption, encrypted framing or a real account exchange.
The existing native request oracle deliberately captures RSA plaintext. Leak
Sanitizer is disabled for the known host restriction; address and undefined
behavior sanitizers execute on the original C++ hashing controls. No source
implementation, accepted APK or server profile changes.

```sh
python3 native-android/engine/auth-interop/deployment/password_fixture.py \
  --source-root . --sanitize --output /tmp/password-qualification.json \
  --private-fixture-dir /private/new-disposable-credential
```

The optional new directory contains a deliberately known disposable credential
and its qualified 128-byte lowercase-hex password field for `hash_type=1`.
Account salt preserves the original CryptoPP Adler digest byte ordering; SQL
stores the same 32 bits using signed `int`. No production/user credential is
accepted. Credentials never appear in the report, argv, environment or console.
POSIX creation uses directory mode 0700 and file mode 0600; Windows ACL isolation
must be provided by the disposable hosted environment. An existing directory,
including a symlink, is refused. The tool never connects to SQL or inserts rows.

The SQL contains only the credential row. A complete isolated service profile
still needs explicitly verified account statistics, UID, region/shard membership,
registered DbServer endpoints and a disposable existing character. The ODBC
byte-pattern fixture from the earlier successful stage is intentionally separate
and is not reused as a login password. No real-authentication acceptance follows
from this fixture qualification.
