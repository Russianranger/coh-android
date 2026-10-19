# Combined 0.1.9 focused fragment qualification

This source preparation keeps `org.coh.nativecombined`, the accepted public test signer, imports and settings unchanged, and increments only the test version to code 10 / `0.1.9-gates25-27-test`. Root owns workflow execution, publication and the independent original Map transaction. The accepted 0.1.8 APK is preserved.

The new Android driver calls no historical `run_focused()` entrypoint. It reuses bounded install/UI/ADB/SAF and owned peer-cleanup helpers. Its two new explicit handoff transactions send a synthetic 65,536-byte ALLENTS body in original-compatible ordered sibling forms: six fragments sent in reverse order with only part zero's order ID nonzero, then a compressed payload of exactly 1,200 bytes in one sibling. The independent original-function C qualification establishes these envelope forms; this peer does not execute an original character serializer or service.

The driver requires actual Android13 x86_64 JNI mapping and OS UDP reception, one GROUPS/request/raw-initial callback sequence, unchanged refusal of world authority, exact numeric receive schema, successful streaming decode, bounded socket retirement and actual SAF export of the new receive observation. Sampling cannot prove every transient queue maximum. No old framework suite, accepted resource/GLES test or physical Thor test is replayed by this job.

Build after existing exact crypto/scene/runtime reuse:

```sh
python3 native-android/combined-client/gradle.py -PcohCryptoRoot=/tmp/gates-crypto :app:assembleDebug :app:lintDebug
python3 native-android/combined-client/tools/package_check.py --apk <arm64-apk> --abi arm64-v8a --require-clean --require-interop --output <arm64-package.json>
python3 native-android/combined-client/tools/interop_package_audit.py --apk <arm64-apk> --abi arm64-v8a --readelf "$ANDROID_HOME/ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf" --output <arm64-dso.json>
python3 native-android/combined-client/gradle.py -PprobeAbis=x86_64 -PcohCryptoRoot=/tmp/gates-crypto :app:assembleDebug
python3 native-android/combined-client/tools/package_check.py --apk <x86-apk> --abi x86_64 --require-clean --require-interop --output <x86-package.json>
python3 native-android/combined-client/tools/build_interop_peer.py --fragment-compat --ndk "$ANDROID_HOME/ndk/28.2.13676358" --crypto-root /tmp/gates-crypto/x86_64 --output <peer-output>
```

Inside the existing fresh API33 x86_64 emulator runner:

```sh
python3 native-android/combined-client/tools/fragment_interop_emulator_check.py --adb "$ANDROID_HOME/platform-tools/adb" --serial emulator-5554 --apk <x86-apk> --package-receipt <x86-package.json> --peer <peer-output>/coh-initial-interop-peer-x86_64 --peer-receipt <peer-output>/build.json --output <fresh-android-output>
```

Focused local preparation controls:

```sh
python3 -m unittest discover -s native-android/combined-client/tools -p test_fragment_driver.py -v
python3 native-android/combined-client/tools/check_fragment_peer.py --output <fresh-host-output>
```

The new host OS-UDP check already passed both scenarios, including exact decoded synthetic body SHA256, ordered ID one, part-zero-last delivery, the exact 1,200-byte sibling form, and client/peer two-socket cleanup. Its exact binaries and generated fixture header are retained once in `../primary-authority-20261017/worker-e-20261019/fragment-peer-host/`. Host execution does not qualify JNI/Android, a whole original ALLENTS, server-authoritative character/world state, physical Thor, or whole-process/RSS/GPU fit. Actual Android build/execution outcomes remain pending until their separate workflow evidence is retained.
