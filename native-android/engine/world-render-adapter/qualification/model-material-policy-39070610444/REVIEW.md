# Focused CI material policy review

Run [39070610444](https://github.com/Russianranger/coh-android/actions/runs/39070610444),
attempt 1, completed successfully at published commit
`dd5c3f9a2c30ea20b0a4c714007b1de0b0409546`, reviewed tree
`6e77fe92b2c0c5986b8ec81433bfb4f882466dba`. Job 117507248472 executed
only the new model-material qualifier after reusing the two exact accepted
cache/resource artifacts. No other qualifier was rerun for this review.

The actual uploaded artifact 12114788461 was downloaded, rather than relying only
on step status. `artifact.zip` is 4,694 bytes, SHA256
`ff40f5956afd00cf585301b6fe23e3e50254fc88698b5faa21455cb84efa328f`, matching
GitHub metadata and the upload log. ZIP CRC validation passes, and the sole
regular member is `qualification.json`: 12,220 bytes, SHA256
`036b8bf8c69cba127bf248831c01e12a9766db7edfeacad4ecb283b0a94292a0`.
The exact metadata, final job steps and log are retained beside these bytes.

All 44 receipt source hashes match both the files in published commit dd5c3f9 and
the reviewed worker-b host receipt. Historical input digests, all 10 extracted
original-function hashes, generated original/fixture hashes, 25 compiled numeric
facts and six mutation identities also match the host receipt. The actual C++
executable links the same standalone release C object recorded by the CI receipt,
then executes successfully. This review reads source and evidence; it does not
reexecute the qualifier.

| CI mode | Checks | Original policy comparisons | Result |
| --- | ---: | ---: | --- |
| Release | 322,641 | 79,721 | Pass |
| ASan | 322,641 | 79,721 | Pass |
| UBSan | 322,641 | 79,721 | Pass |

All six semantic mutations were refused. The function's measured host release
stack remains 2,288 bytes, with helpers at most 32 bytes; zero policy heap
allocations and unchanged existing rigid validation remain explicit.

The evidence proves the bounded fresh-initial original CLIENT numerical policy.
The 3,083 root names/partition counts/SERVER Trick scalar observations use derived
TexBind, normal and capability inputs. Eight historical TexOpts and 3,644
historical Tricks are independent controls, with no selected current model
association. The artifact explicitly retains false for current TexBind selection,
current CLIENT generation, effective material/GPU owner, world authority and
Android execution. It does not authorize drawing or prove a full model runtime,
GLES path or physical Thor acceptance. Actual composite/Basic namespace and
texture-owner selection remain the immediate upstream dependency described in
`CLIENT_MODEL_MATERIAL.md`.
