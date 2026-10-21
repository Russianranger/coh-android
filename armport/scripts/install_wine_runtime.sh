#!/bin/bash
# Install the Android app's ARM64 Wine runtime (android/runtime-lock.json,
# sha256-checked) plus Xvfb, Mesa and screen-capture tools on an Ubuntu ARM64
# CI runner, for running the ARM64 client under the same Wine as the app.
set -euo pipefail
url=$(python3 -c "import json;print(json.load(open('android/runtime-lock.json'))['wine']['url'])")
sha=$(python3 -c "import json;print(json.load(open('android/runtime-lock.json'))['wine']['sha256'])")
curl -fsSL --retry 3 -o "$RUNNER_TEMP/wine.tar.gz" "$url"
echo "$sha  $RUNNER_TEMP/wine.tar.gz" | sha256sum -c -
sudo mkdir -p /opt/wine
sudo tar -xzf "$RUNNER_TEMP/wine.tar.gz" -C /opt/wine
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends xvfb x11-utils x11-apps imagemagick tesseract-ocr \
  libfreetype6 libfontconfig1 libx11-6 libxext6 libxrender1 libxrandr2 libxi6 \
  libxfixes3 libxcursor1 libxinerama1 libxxf86vm1 libgnutls30t64 libunwind8 \
  libgl1 libglx-mesa0 libgl1-mesa-dri
echo "WINEPREFIX=$RUNNER_TEMP/wineprefix" >> "$GITHUB_ENV"
/opt/wine/bin/wine --version
