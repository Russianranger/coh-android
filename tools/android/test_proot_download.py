import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import build_proot


class ProotDownloadTests(unittest.TestCase):
    def test_partial_timeout_is_replaced_and_digest_verified(self):
        class Interrupted(io.BytesIO):
            def read(self, count):
                if self.tell():
                    raise TimeoutError('interrupted download')
                return super().read(2)
        good = b'verified archive'
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'source'
            with patch.object(build_proot.urllib.request, 'urlopen', side_effect=[Interrupted(b'partial'), io.BytesIO(good)]), \
                 patch.object(build_proot, 'TALLOC_SHA256', hashlib.sha256(good).hexdigest()), \
                 patch.object(build_proot.time, 'sleep'):
                build_proot.download_talloc(dest)
                self.assertEqual(dest.read_bytes(), good)

    def test_hash_mismatch_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(build_proot.urllib.request, 'urlopen', return_value=io.BytesIO(b'wrong')) as fetch:
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                build_proot.download_talloc(Path(tmp) / 'source')
            self.assertEqual(fetch.call_count, 1)

    def test_retries_are_bounded_and_permanent_http_errors_refused(self):
        for error, attempts in ((TimeoutError('timeout'), 3),
                                (urllib.error.HTTPError('url', 404, 'not found', {}, None), 1)):
            with tempfile.TemporaryDirectory() as tmp, \
                 patch.object(build_proot.urllib.request, 'urlopen', side_effect=error) as fetch, \
                 patch.object(build_proot.time, 'sleep'):
                dest = Path(tmp) / 'source'
                with self.assertRaises(type(error)):
                    build_proot.download_talloc(dest)
                self.assertEqual(fetch.call_count, attempts)
                self.assertFalse(dest.exists())
