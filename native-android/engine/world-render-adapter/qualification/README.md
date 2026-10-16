# Worker E independent qualification

Implementation commit: `641424d3e5ad8fdccc799fbe33cb680789453eec`

Implementation tree: `994aa4b21fba9b61686fb72085ea48ebe735c0a6`

`host.json` records clean tracked/native-input state before and after qualification,
exact source hashes, original-source pin and extracted unchanged `mulMat44Inline`.
Release, ASan and UBSan each pass **16,720 checks** with identical native JSON.
The suite includes 512 original matrix comparisons, 5,000 bounded malformed
mutations, 4,096 draw admission, 2,000 generation publications with three reader
threads, exact allocation-budget retirement/rollback and accepted renderer
submission/flush with zero measured render-path allocations/frees.

No NDK is available in this worker environment. Android ARM64/x86_64 builds,
Android emulator execution, physical Thor acceptance and real server-world
rendering are **not claimed**. The standalone check script supports retained
Android binaries/relocatable per-ABI build receipts for coordinator qualification.
LSan cannot inspect /proc tasks in this traced environment; ASan and UBSan ran
successfully and explicit allocation-budget/lifetime assertions remained enabled.

Independent read-only review by Worker F checked mailbox/refcount retirement,
allocation reservation, transactional prepare/bind rollback and Surface ownership.
Its generation-identity finding was corrected before this qualification:
nondecreasing asset generation, exact catalog identity for unchanged scene, exact
manifest for unchanged assets, entity/slot stability for unchanged entity
generation, and nondecreasing pose/appearance. Seven focused rejection cases
exercise the correction. The README preserves its other cautions: full geometry
copy per draw, 4,096-draw cap, borrowed spans through flush and existing renderer
vertex/index scans.

Qualification covers deterministic adapter contracts only. Complete source
catalog/material and full-character/global-tail producers remain unavailable.
No Combined APK rebuild or activation is justified by this isolated milestone.
