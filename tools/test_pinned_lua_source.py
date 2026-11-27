#!/usr/bin/env python3
"""The zone generator's Lua source: job cache first, then verified downloads, never an unpinned copy."""
from __future__ import annotations
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pinned_lua_source as lua

producer = lua.producer
PINNED_SHA256 = producer.LUA_SHA256


def archive():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
        for name, data in (('lua-5.1.5/Makefile', b'all:\n'), ('lua-5.1.5/src/lua.c', b'int main(){return 0;}\n')):
            info = tarfile.TarInfo(name); info.size = len(data); tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class PinnedLuaSourceTests(unittest.TestCase):
    def setUp(self):
        self.raw = archive()
        digest = hashlib.sha256(self.raw).hexdigest()
        patcher = mock.patch.object(producer, 'LUA_SHA256', digest)
        patcher.start(); self.addCleanup(patcher.stop)
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp))
        self.prepared = self.tmp / 'src'
        declaration = self.prepared / producer.LUA_DECLARATION
        declaration.parent.mkdir(parents=True)
        declaration.write_text('CPMAddPackage(\n\tNAME lua51\n\tVERSION 5.1.5\n\tURL "%s"\n\tURL_HASH\n\t\t"SHA256=%s"\n)\n'
                               % (producer.LUA_URL, digest))
        self.cache = self.tmp / 'cache'; self.output = self.tmp / 'lua51'
        self.sleeps = []

    def provide(self, fetcher):
        return lua.provide(self.prepared, self.cache, self.output, fetcher=fetcher, sleep=self.sleeps.append)

    def test_cache_hit_extracts_without_download(self):
        self.cache.mkdir(); (self.cache / producer.LUA_ARCHIVE_NAME).write_bytes(self.raw)
        def refuse(url): raise AssertionError('downloaded despite a verified cache: ' + url)
        record = self.provide(refuse)
        self.assertTrue(record['from_job_cache']); self.assertIsNone(record['downloaded_from'])
        self.assertEqual((self.output / 'src/lua.c').read_bytes(), b'int main(){return 0;}\n')
        self.assertEqual(record['source'], self.output.resolve().as_posix())

    def test_timeout_then_wrong_bytes_then_mirror_fills_the_cache(self):
        replies = {lua.SOURCES[0]: TimeoutError('timed out'), lua.SOURCES[1]: b'not the release archive',
                   lua.SOURCES[2]: self.raw}
        def fetcher(url):
            reply = replies[url]
            if isinstance(reply, Exception): raise reply
            return reply
        record = self.provide(fetcher)
        self.assertFalse(record['from_job_cache']); self.assertEqual(record['downloaded_from'], lua.SOURCES[2])
        self.assertEqual([a['outcome'] for a in record['attempts']], ['TimeoutError', 'sha256_differs', 'verified'])
        self.assertEqual((self.cache / producer.LUA_ARCHIVE_NAME).read_bytes(), self.raw)
        self.assertTrue((self.output / 'Makefile').is_file()); self.assertEqual(self.sleeps, [])

    def test_a_corrupt_cached_copy_is_replaced_only_by_a_verified_download(self):
        self.cache.mkdir(); (self.cache / producer.LUA_ARCHIVE_NAME).write_bytes(b'corrupt')
        record = self.provide(lambda url: self.raw)
        self.assertFalse(record['from_job_cache']); self.assertEqual(record['downloaded_from'], lua.SOURCES[0])
        # The job cache keeps its key; a corrupt entry is not overwritten here (actions/cache never saves a hit).
        self.assertEqual((self.cache / producer.LUA_ARCHIVE_NAME).read_bytes(), b'corrupt')

    def test_every_source_failing_refuses_without_output(self):
        def fetcher(url): raise OSError('unreachable')
        with self.assertRaisesRegex(ValueError, 'Lua 5.1.5 is unavailable'):
            self.provide(fetcher)
        self.assertEqual(self.sleeps, [lua.PAUSE_SECONDS] * (lua.ROUNDS - 1))
        self.assertFalse(self.output.exists()); self.assertFalse((self.cache / producer.LUA_ARCHIVE_NAME).exists())

    def test_oversized_download_is_refused(self):
        big = b'x' * (producer.MAX_LUA_ARCHIVE + 1)
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            self.provide(lambda url: big)

    def test_source_without_the_pinned_declaration_is_refused(self):
        (self.prepared / producer.LUA_DECLARATION).write_text('CPMAddPackage(NAME lua51 URL "https://example.invalid/lua.tar.gz")\n')
        with self.assertRaisesRegex(ValueError, 'does not fetch the pinned Lua archive'):
            self.provide(lambda url: self.raw)

    def test_the_real_generator_source_declares_the_pinned_archive(self):
        with mock.patch.object(producer, 'LUA_SHA256', PINNED_SHA256):
            self.assertTrue(producer.declares_lua(lua.ROOT / 'upstream/ouroboros'))
        self.assertEqual(lua.SOURCES[0], 'https://www.lua.org/ftp/lua-5.1.5.tar.gz')


if __name__ == '__main__':
    unittest.main()
