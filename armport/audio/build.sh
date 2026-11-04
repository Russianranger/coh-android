#!/usr/bin/env bash
# Build the guest ALSA playback plugin on an ARM64 host and run its native
# check (real alsa-lib conversion, clock, pause and reconnect against the
# protocol sink). Writes <out>/libasound_module_pcm_trasc.so and
# <out>/audio-bundle.json.
set -euo pipefail
out=${1:?usage: build.sh <output directory>}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out"
docker build --platform linux/arm64 -f "$here/audio.Dockerfile" -t coh-armport-audio:1 "$here"
container=$(docker create coh-armport-audio:1)
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
docker cp "$container:/out/libasound_module_pcm_trasc.so" "$out/"
docker run --rm --network none -v "$here:/audio:ro" coh-armport-audio:1 \
  python3 /audio/check_audio_native.py /out/libasound_module_pcm_trasc.so
image=$(docker image inspect coh-armport-audio:1 --format '{{.Id}}')
python3 - "$out" "$image" <<'PY'
import hashlib, json, pathlib, struct, sys
out, image = pathlib.Path(sys.argv[1]), sys.argv[2]
plugin = out / 'libasound_module_pcm_trasc.so'
data = plugin.read_bytes()
assert data[:5] == b'\x7fELF\x02' and struct.unpack_from('<H', data, 18)[0] == 183, 'not an AArch64 ELF64 object'
(out / 'audio-bundle.json').write_text(json.dumps({
    'protocol': 1, 'architecture': 'arm64-glibc', 'base_image': 'debian:bookworm-slim',
    'image_id': image, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}, indent=2) + '\n')
PY
echo "audio plugin $(sha256sum "$out/libasound_module_pcm_trasc.so" | cut -c1-64)"
