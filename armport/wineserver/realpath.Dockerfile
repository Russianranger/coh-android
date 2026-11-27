# Debian bookworm, the release of the app's guest root filesystem
# (coh-m2-bookworm-arm64-wine10-fex2510), so the library links against the
# glibc that the guest's wineserver loads it into. The first two lines match
# armport/audio/audio.Dockerfile, so its package layer is reused.
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libasound2-dev python3
COPY realpath_cache.c check_realpath.c /src/
RUN mkdir /out && cc -O2 -shared -fPIC -DPIC -Wall -Wextra -Werror /src/realpath_cache.c -o /out/libarmport_realpath.so \
 && strip /out/libarmport_realpath.so \
 && cc -O2 -Wall -Wextra -Werror /src/check_realpath.c -o /out/check_realpath
