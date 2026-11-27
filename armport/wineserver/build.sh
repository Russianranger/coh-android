#!/usr/bin/env bash
# Build the wineserver realpath cache on an ARM64 host and run its native
# check (the same answers as glibc for plain files, links, missing files and
# unusual paths; nothing changes in a process of another name). Writes
# <out>/libarmport_realpath.so and <out>/realpath-bundle.json.
set -euo pipefail
out=${1:?usage: build.sh <output directory>}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out"
docker build --platform linux/arm64 -f "$here/realpath.Dockerfile" -t coh-armport-realpath:1 "$here"
container=$(docker create coh-armport-realpath:1)
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
docker cp "$container:/out/libarmport_realpath.so" "$out/"
docker run --rm --network none -v "$here:/wineserver:ro" coh-armport-realpath:1 \
  python3 /wineserver/fuzz_realpath.py /out/libarmport_realpath.so /out/check_realpath 74 60 | tee "$out/fuzz.txt"
grep -qx 'rounds 60 different 0' "$out/fuzz.txt"
docker run --rm --network none -v "$here:/wineserver:ro" coh-armport-realpath:1 \
  python3 /wineserver/check_realpath_native.py /out/libarmport_realpath.so /out/check_realpath | tee "$out/native-check.txt"
image=$(docker image inspect coh-armport-realpath:1 --format '{{.Id}}')
python3 - "$out" "$image" <<'PY'
import hashlib, json, pathlib, struct, sys
out, image = pathlib.Path(sys.argv[1]), sys.argv[2]
library = out / 'libarmport_realpath.so'
data = library.read_bytes()
assert data[:5] == b'\x7fELF\x02' and struct.unpack_from('<H', data, 18)[0] == 183, 'not an AArch64 ELF64 object'
(out / 'realpath-bundle.json').write_text(json.dumps({
    'format': 1, 'architecture': 'arm64-glibc', 'base_image': 'debian:bookworm-slim',
    'image_id': image, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}, indent=2) + '\n')
PY
echo "realpath cache $(sha256sum "$out/libarmport_realpath.so" | cut -c1-64)"
