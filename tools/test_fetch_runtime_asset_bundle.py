import hashlib
import io
import json
from contextlib import redirect_stderr
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from fetch_runtime_asset_bundle import AssetHTTPError, HTTPSRedirect, fetch, main


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

    def failed_cli(self, error, release=True):
        arguments = ['fetch_runtime_asset_bundle.py', '--receipt', str(self.receipt), '--output', str(self.output)]
        environment = {'COH_ASSET_BUNDLE_URL': 'https://private.example.test/a?signature=secret-url',
                       'GITHUB_REPOSITORY': 'owner/repo', 'GH_TOKEN': 'secret-token'}
        if release:
            arguments += ['--release-asset-id', '42']
        stderr = io.StringIO()
        with patch('sys.argv', arguments), patch.dict('os.environ', environment, clear=True), \
                patch('urllib.request.build_opener') as opener, redirect_stderr(stderr):
            opener.return_value.open.side_effect = error
            self.assertEqual(main(), 1)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_suffix('.zip.part').exists())
        return stderr.getvalue()

    def http_error(self, url, code):
        return urllib.error.HTTPError(url, code, 'secret-server-reason',
                                      {'Location': 'https://secret-header.example.test/?token=secret-token'},
                                      io.BytesIO(b'secret-body'))

    def test_api_failure_reports_status_without_server_details(self):
        error = self.http_error('https://api.github.com/repos/owner/repo/releases/assets/42', 404)
        self.assertEqual(self.failed_cli(error),
                         'Asset download failed (HTTP status 404; stage: GitHub API); '
                         'check access, expiry and the pinned receipt.\n')
        self.assertTrue(error.fp.closed)

    def test_redirect_failure_reports_download_stage_without_signed_url(self):
        error = self.http_error('https://private.example.test/a?signature=secret-url', 403)
        self.assertEqual(self.failed_cli(error),
                         'Asset download failed (HTTP status 403; stage: download host); '
                         'check access, expiry and the pinned receipt.\n')

    def test_secret_url_failure_reports_download_stage(self):
        error = self.http_error('https://private.example.test/a?signature=secret-url', 429)
        self.assertEqual(self.failed_cli(error, release=False),
                         'Asset download failed (HTTP status 429; stage: download host); '
                         'check access, expiry and the pinned receipt.\n')

    def test_unexpected_http_status_cannot_inject_diagnostics(self):
        error = self.http_error('https://private.example.test/a?signature=secret-url', 'secret-status')
        self.assertEqual(self.failed_cli(error),
                         'Asset download failed (HTTP status unknown; stage: download host); '
                         'check access, expiry and the pinned receipt.\n')

    def test_other_exceptions_still_do_not_print_private_text(self):
        self.assertEqual(self.failed_cli(urllib.error.URLError('https://private.example.test/?signature=secret-url')),
                         'Asset download failed (URLError); check access, expiry and the pinned receipt.\n')

    def test_http_failure_mid_transfer_removes_partial_file(self):
        response = Response(b'a')
        error = self.http_error('https://private.example.test/a?signature=secret-url', 503)
        with patch.object(response, 'read', side_effect=[b'a', error]):
            with self.assertRaisesRegex(AssetHTTPError, '^HTTP status 503; stage: download host$'):
                fetch(self.receipt, self.output,
                      environment={'COH_ASSET_BUNDLE_URL': 'https://private.example.test/a?signature=secret-url'},
                      opener=Opener(response))
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_suffix('.zip.part').exists())


if __name__ == '__main__':
    unittest.main()
