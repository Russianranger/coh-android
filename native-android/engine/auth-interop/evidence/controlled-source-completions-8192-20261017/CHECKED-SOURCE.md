The authoritative8192-byte oracle receipt is now checked-qualification.json. The earlier qualification.json/source-seal.json remain preserved historical receipts; their project helper execution provenance was not frozen before imports and they are not the newly admitted proof.

The guarded qualifier begins with standard-library imports only. It requires an explicit expected Git commit and exact working-tree bytes for every flat project Python helper, itself, the fixture, raw source pins and retained runtime-baseline inputs before importing project code. Preimported project helpers are refused. A dedicated import finder/loader compiles the frozen Git-checked bytes directly; it never reads a project PYC, disk source fallback or prior imported helper. After all three native corpus modes and the unchanged-offset negative control, HEAD, helper domain and every frozen source/input are checked again. The new receipt binds all frozen input hashes and every executed project module hash.

The guarded qualification was run once atc86e281a3 after the reviewed helper-source changes. Release, ASan and UBSan again each passed811226 checks with the identical8192 corpus; original-offset failure again reproduced. Eight Python contracts pass, including a malicious disk/PYC sentinel that cannot override frozen source, wrong-commit refusal and post-source mutation refusal. The retained checked-host-controls.txt came from a fresh child interpreter with an absent temporary PYTHONPYCACHEPREFIX, so even the unit-module import could not reuse old bytecode. New checked-source-seal.json binds this evidence separately; old receipts and prototype are unchanged.

Invoke the guarded corpus directly as a script (with the reviewed expected source commit whose Git objects are available):

```sh
python native-android/engine/auth-interop/deployment/qualify_controlled_completions.py --source-root "$PWD" --expected-commit EXACT_REVIEWED_COMMIT --output NEW_RECEIPT.json
```

This repairs qualification provenance only. It adds no live receiver/TCP acceptance, Windows service execution, account-handler coverage, AuthServer/probe rebuild or shipping change.
