#!/usr/bin/env python3
"""Hand CMake the pinned Lua 5.1.5 source for a host-only generator compile.

Run 42675871153 (armport-zone-beacons, 2026-11-09): www.lua.org timed out every
connection while CMake fetched Lua 5.1.5 for the zone generator's configure
("Each download failed!"). armport-build's server-metrics job met the same in
build 42488979665 and keeps the verified archive in an Actions cache; CPM's own
override (CPM_lua51_SOURCE) takes a fresh extraction and still applies the
source's lua-cmake.patch (server_metrics_producer.py). This step takes the
archive from that cache, or else downloads it (the official site first, then
mirrors; every copy must match the pinned SHA-256) and leaves it in the cache
directory for the job's cache save, then extracts it for -DCPM_lua51_SOURCE.
It fails when no verified archive is available rather than leave CMake to
retry the same site.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'armport/scripts'))
import server_metrics_producer as producer

# Every source must serve the byte-identical release archive (producer.LUA_SHA256).
SOURCES = (producer.LUA_URL,
           'https://www.tecgraf.puc-rio.br/lua/mirror/ftp/lua-5.1.5.tar.gz',
           'https://distfiles.macports.org/lua/lua-5.1.5.tar.gz',
           'https://deb.debian.org/debian/pool/main/l/lua5.1/lua5.1_5.1.5.orig.tar.gz')
ROUNDS = 3
TIMEOUT_SECONDS = 60
PAUSE_SECONDS = 20


def fetch(url, timeout=TIMEOUT_SECONDS):
    request = urllib.request.Request(url, headers={'User-Agent': 'coh-android-ci'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(producer.MAX_LUA_ARCHIVE + 1)


def download(sources=SOURCES, rounds=ROUNDS, pause=PAUSE_SECONDS, fetcher=fetch, sleep=time.sleep):
    """The first verified copy and every attempt's outcome."""
    attempts = []
    for round_index in range(rounds):
        if round_index:
            sleep(pause)
        for url in sources:
            try:
                raw = fetcher(url)
            except Exception as failure:  # network errors of every kind are only recorded
                attempts.append({'url': url, 'outcome': type(failure).__name__})
                continue
            if len(raw) > producer.MAX_LUA_ARCHIVE:
                attempts.append({'url': url, 'outcome': 'too_large'})
                continue
            if hashlib.sha256(raw).hexdigest() != producer.LUA_SHA256:
                attempts.append({'url': url, 'outcome': 'sha256_differs'})
                continue
            attempts.append({'url': url, 'outcome': 'verified'})
            return raw, url, attempts
    return None, None, attempts


def provide(prepared, cache, output, **download_options):
    producer.require(producer.declares_lua(prepared),
                     'The staged generator source does not fetch the pinned Lua archive')
    cache = Path(cache); cached = cache / producer.LUA_ARCHIVE_NAME
    raw = producer.verified_lua(cached)
    record = {'format': 1, 'archive_sha256': producer.LUA_SHA256, 'from_job_cache': raw is not None,
              'downloaded_from': None, 'attempts': []}
    if raw is None:
        raw, url, attempts = download(**download_options)
        record.update(downloaded_from=url, attempts=attempts)
        producer.require(raw is not None, 'Lua 5.1.5 is unavailable: no cached archive and every download failed')
        cache.mkdir(parents=True, exist_ok=True)
        if not cached.exists():
            cached.write_bytes(raw)
    record['source'] = producer.extract_lua(raw, output).as_posix()
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', required=True, type=Path, help='Staged source that declares the pinned Lua')
    parser.add_argument('--cache', required=True, type=Path, help='Job cache directory for the verified archive')
    parser.add_argument('--output', required=True, type=Path, help='Fresh directory for the extracted source')
    parser.add_argument('--record', required=True, type=Path, help='Where to write the outcome')
    args = parser.parse_args(argv)
    record = provide(args.prepared, args.cache, args.output)
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    print(json.dumps(record, sort_keys=True))


if __name__ == '__main__':
    main()
