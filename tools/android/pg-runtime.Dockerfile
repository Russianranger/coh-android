# The caller supplies the locked ARM64 platform manifest, never a moving tag.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG DEBIAN_SNAPSHOT
RUN rm -f /etc/apt/sources.list.d/debian.sources && \
    printf 'deb http://snapshot.debian.org/archive/debian/%s/ bookworm main\ndeb http://snapshot.debian.org/archive/debian/%s/ bookworm-updates main\ndeb http://snapshot.debian.org/archive/debian-security/%s/ bookworm-security main\n' "$DEBIAN_SNAPSHOT" "$DEBIAN_SNAPSHOT" "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list && \
    apt-get -o Acquire::Check-Valid-Until=false update && \
    apt-get -o Acquire::Check-Valid-Until=false install -y --no-install-recommends build-essential bison flex perl python3 ca-certificates pkg-config && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY postgresql-lock.json build_pg_runtime.py provenance.json postgresql.tar.bz2 ./
RUN python3 /build/build_pg_runtime.py --lock /build/postgresql-lock.json --source /build/postgresql.tar.bz2 --provenance /build/provenance.json --output /out
