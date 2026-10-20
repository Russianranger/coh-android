# Bounded shipping report and legacy deep adapter assertions

The 0.1.11 report intentionally omits optional diagnostic objects to preserve the
actual protocol phase, essential counters and cleanup observations within 7,168
bytes. The historical adapter test assumes every optional object is visible and
fails at its first required netfx object even when shipping omission is correct.
Its Java API shape check also predates the ninth `controlState` JNI method.

This additive role preserves both historical source files without modification:
`../interop-adapter-20261018/test_interop_adapter.c` and `check_adapter.py`.
Every assertion in the historical C test executes unchanged. Its report symbol
is redirected only within this host test to an explicitly marked, nested
**TEST-ONLY full-detail view**. Before building that view, the wrapper captures
and independently emits the exact production JNI JSON, validates its cap and
explicit omission metadata, and checks omitted values really are null. Optional
probe details are then serialized from the same actual JNI owner populated by
the production observer, using production probe formatters, solely to retain
all historical deep framing, failure, privacy and lifecycle assertions.

The full-detail view is never returned by shipping JNI and is never used as
proof that the shipping report includes omitted values. Shipping JSON and the
view have separate receipt fields. The deliberate callback-busy test retains
its original assertion and separately checks actual `OWNER_BUSY`, unknown
observation status and an unavailable `controlState` sample. The Python checker
independently parses every shipping sample and verifies every omission bit/name,
null field, authority restriction and report size. It checks all nine current
Java native declarations. The separate `tools/check_report_regression.py`
continues to qualify maximum-width and source-layout report overflow cases.

Run from repository root with a fresh external output directory:

```sh
python native-android/combined-client/diagnostics/interop-report-adapter-20261020/check_bounded_adapter.py --source-root . --output /tmp/coh-bounded-adapter
```

Release, ASan and UBSan run sequentially and pin source/compiler/header/linked
library inputs. JNI, controller, crypto provider and sockets remain explicit
host doubles. This role does not execute Android, Thor or the original server,
change application source, or authorize world/actor publication or ACKs.
