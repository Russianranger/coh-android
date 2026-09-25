import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.request

from fetch_runtime_asset_bundle import HTTPSRedirect, fetch


class Response(io.BytesIO):
    def __init__(self, body, length=None):
        super().__init__(body)
        self.headers = {} if length is None else {'Content-Length': str(length)}


class Opener:
    def __init__(self, response):
        self.response = response
        self.request = None

    def open(self, request, timeout):
        self.request = request
        return self.response


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.receipt = self.root / 'receipt.json'
        self.output = self.root / 'assets.zip'
        self.receipt.write_text(json.dumps({'archive_bytes': 3, 'archive_sha256': hashlib.sha256(b'abc').hexdigest()}))

    def call(self, body, length=None):
        return fetch(self.receipt, self.output, environment={'COH_ASSET_BUNDLE_URL': 'https://example.test/a?signature=private'}, opener=Opener(Response(body, length)))

    def test_matching_download_is_installed(self):
        self.assertEqual(self.call(b'abc')['bytes'], 3)
        self.assertEqual(self.output.read_bytes(), b'abc')

    def test_oversized_stream_stops_without_installing(self):
        with self.assertRaises(ValueError):
            self.call(b'abcd')
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_suffix('.zip.part').exists())

    def test_short_or_wrong_hash_is_not_installed(self):
        for body in (b'ab', b'xyz'):
            with self.assertRaises(ValueError):
                self.call(body)
            self.assertFalse(self.output.exists())

    def test_existing_destination_is_preserved(self):
        self.output.write_bytes(b'keep')
        with self.assertRaises(ValueError):
            self.call(b'abc')
        self.assertEqual(self.output.read_bytes(), b'keep')

    def test_release_token_not_forwarded_to_redirect(self):
        opener = Opener(Response(b'abc'))
        fetch(self.receipt, self.output, '42', {'GITHUB_REPOSITORY': 'owner/repo', 'GH_TOKEN': 'secret'}, opener)
        redirected = HTTPSRedirect().redirect_request(opener.request, None, 302, 'Found', {}, 'https://downloads.example.test/a')
        self.assertEqual(opener.request.get_header('Authorization'), 'Bearer secret')
        self.assertIsNone(redirected.get_header('Authorization'))

    def test_insecure_redirect_rejected(self):
        request = urllib.request.Request('https://example.test/a')
        with self.assertRaises(ValueError):
            HTTPSRedirect().redirect_request(request, None, 302, 'Found', {}, 'http://example.test/a')


if __name__ == '__main__':
    unittest.main()
