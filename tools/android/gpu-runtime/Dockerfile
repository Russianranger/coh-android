FROM debian@sha256:a1b86db52ce3daef089e45aabe36dfec4091f82464c25c1fdcf03de197cbe82a
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates build-essential ninja-build pkg-config python3 python3-pip \
    python3-mako python3-yaml python3-packaging bison flex glslang-tools \
    libexpat1-dev zlib1g-dev libzstd-dev libx11-dev libx11-xcb-dev libxcb1-dev \
    libxcb-dri3-dev libxcb-present-dev libxcb-randr0-dev libxcb-shm0-dev \
    libxcb-sync-dev libxcb-xfixes0-dev libxshmfence-dev libvulkan-dev \
    && pip3 install --break-system-packages meson==1.5.2 cmake==3.31.6
COPY tools/android/gpu-runtime/lock.json /src/lock.json
COPY tools/android/gpu-runtime/build.py /src/build.py
COPY android/native/coh-vulkan-gpu-probe.c /src/coh-vulkan-gpu-probe.c
RUN python3 /src/build.py --output /out
