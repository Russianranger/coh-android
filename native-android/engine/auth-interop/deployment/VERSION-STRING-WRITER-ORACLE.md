# Original string-writer qualification for version payloads

This additive host oracle executes the exact original `BitStream.c::bsWriteString` function against a minimal bounded `BitStream` shell. It writes two synthetic strings at each of eight initial bit offsets, with first-string lengths 1–99. The existing bounded Python version-body decoder consumes every output and checks both values and the declared body size. Release and ASan/UBSan each pass 792 cases and produce identical complete output hashes. The fixture and qualifier, original function/blob and decoder hashes are retained in `../evidence/version-observation-contract-20261017/original-writer.json`. LeakSanitizer is disabled.

This supplements the original four payload-contract suites, which use independently constructed synthetic bits. It qualifies the string writer/decoder association for this bounded untyped body subset. It does not execute a version getter, the packet wrapper, ServerMonitor handler, NetLink transport or Windows process. Values are synthetic, so actual process version verification and live channel ownership remain false. No listener, service, account or accepted runtime is changed.

```sh
python3 native-android/engine/auth-interop/deployment/qualify_version_string_writer.py --source-root . --output /tmp/version-writer.json
```
