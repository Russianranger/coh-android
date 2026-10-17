# GPU resource leases and GL retirement

`coh_wr_gpu_lease` connects an actual uploaded GPU owner to presentation's existing
resource lease callbacks. It does not construct a world snapshot, actor,
material, current CLIENT namespace or generation certificate.

Adoption validates sorted nonzero logical IDs against full exact asset path,
generation and whole-body SHA from each existing opaque successful upload owner.
It requires the same GPU operations and common real Surface/context/thread token
and validates every owner through `coh_wr_gpu_view`. Duplicate IDs, pointer slots
and GPU owners refuse. Existing caller pointer slots and output change together
only after all validation and cancellation checks succeed. All failure paths
preserve the caller's upload owners and balance any acquired registry pin.

The backend must supply a real registry pin and a whole-context retirement gate,
in addition to the existing GPU operations. A registry pin keeps actual context
lifetime/destruction records available even after that context is destroyed. It
does not prevent intentional context destruction. The gate quarantines normal GL
work while cleanup is incomplete, including use of another resource set in the
same context. Cleanup operations remain usable. Retain/release callbacks perform
no GL; a failed retain transfers no pin. A failed begin acquires no gate; a failed end preserves the acquired gate.
These are required backend contracts, not facts inferred from a texture name.

One actual control pthread attaches the owner and uses presentation hold/drop.
No hold/drop deletes, allocates or frees. Explicit retirement stops new holds;
existing frame leases can finish their final flush/abandonment before dropping.
GL maintenance drain refuses while any lease remains. It then releases actual
GPU owners on the exact owning GL thread/context, keeping failed or partially
disposed owners and the cleanup gate for retry. An old Surface can retire on its
same surviving context; a destroyed context uses only existing independently
verified destruction retirement. No name is relabeled to a new lifetime.
Control collection frees metadata and releases the registry pin only after every
GPU owner and the gate have been disposed. Callback users must be quiescent.

The parent books all old/new GPU reservations, opaque GPU CPU owners, registry,
provider, input arrays/paths, driver allowances, renderer and other live/peak
storage in `external_bytes`. Explicit opaque-owner and registry reservations
establish minima; they are not new allocator introspection. This owner adds its
actual metadata allocation and 64 KiB control reservation under the same named
96 MiB allowance. It does not create another parent capacity ticket or reduce a
reservation automatically after a numeric reference count changes. GPU heap,
allocator overhead, stacks of external callbacks and process RSS remain outside
any claimed measurement. GPU release may free its existing small CPU object in
the separate GL maintenance call; presentation's render callback does not do so.

The new host callback controls use genuine opaque GPU owners made by the existing
uploader, with explicit model operations. They qualify transactional ownership,
not GL. The new pbuffer harness includes the existing standalone EGL backend
read-only and pins its actual context registry behind a qualification-only gate.
It executes four real uploads, every mip readback, control-worker leases/drop,
wrong-thread refusal, deferred deletion, cleanup errors/retry, Surface recreation
and real context destruction. New-context texture names survive old-context
metadata disposal. CPU texture/loader/provider storage really retires while the
leased GPU data remains readable. It does not adopt a shipping application EGL
display or bypass the existing context/pthread checks.

```sh
python3 native-android/engine/world-render-adapter/check_gpu_lease.py \
  --source-root . --actual-texture /path/to/box-1.texture \
  --host-headers /path/to/pinned-headers \
  --host-egl /lib/x86_64-linux-gnu/libEGL.so.1 \
  --host-gles /lib/x86_64-linux-gnu/libGL.so.1 \
  --sanitize --output /path/to/new-private-evidence
```

The exact 43,990-byte texture and five primary Khronos header pins are reused
from the existing standalone texture qualification. This checker runs only the
new tests, the existing independent Pillow all-mip function, actual C-to-C++
linking, and targeted semantic mutations. It never replays an old qualifier.
Every consumed project dependency, including both new tests and the checker,
must match its current committed blob before and after execution. Actual host
release/ASan/UBSan are separate from the unsanitized system GL driver. Declared
dispatch library files are hashed; loaded mappings and full driver dependencies
are not verified. Root owns later standalone NDK/Android 13 execution; no APK,
production prepare, nine-prerequisite/world/actor admission or current generation
is qualified here. B's final material/default namespace and C's complete actor
transaction remain prerequisites to any production publication.
