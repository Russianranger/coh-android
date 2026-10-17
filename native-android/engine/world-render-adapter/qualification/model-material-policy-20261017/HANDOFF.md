# Model material policy handoff

This isolated tranche follows `fd9ea649322aff5dd952878b6a00d9d813a50ba7`
(historical LOD cache/dictionary), which follows `1c8d77028` (automatic LOD
construction). It adds the bounded numerical fresh-initial original CLIENT
model material policy and its source qualifier. No renderer, GLES, JNI, CMake,
Gradle, workflow or protected gameplay/support caller is changed. Removing these
new policy/qualifier/docs/evidence files rolls back this tranche.

Final source review requested an extern-C public guard, an actual C-object/C++
link execution and an explicit readable-name precondition; all are included in
`host.json`. Release, ASan and UBSan each pass 322,641 checks / 79,721 unchanged
source comparisons. All six semantic mutations are refused. The native policy
uses no heap, and existing rigid material admission remains unchanged.

Exact command from the worker-b checkout:

```
python native-android/engine/world-render-adapter/check_model_material.py \
  --actual-cache /workspace/scratch/7ed1da2a7e55/retained-inputs/tricks.bin \
  --actual-states /workspace/scratch/7ed1da2a7e55/retained-inputs/seqstatebits.bin \
  --resources /workspace/scratch/7ed1da2a7e55/retained-inputs/resource-capture/capture/resources.cohres \
  --output /workspace/scratch/7ed1da2a7e55/worker-b-model-policy-final.json
```

`host.json` is that final receipt. Its `source_revision` is the preceding commit;
the new source bytes and original dependencies are bound by `source_sha256`,
before/after readmission, extracted function hashes and compiled-object hashes.
The actual C++ consumer links to the same standalone release C object recorded
in `standalone_public_exports`, then executes successfully.

The 3,083 real root model/name/partition/SERVER scalar controls use derived
TexBind/normal/capability inputs. Eight historical TexOpt and 3,644 historical
Trick controls are independent and have no asserted current model association.
The case count proves fresh-initial source policy, not current CLIENT material
selection, model runtime history, original ABI, Android execution or world
activation. See `CLIENT_MODEL_MATERIAL.md` for exact input preconditions,
unsupported families and the actual composite/Basic namespace dependency.
