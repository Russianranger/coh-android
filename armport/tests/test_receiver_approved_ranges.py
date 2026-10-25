import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import stage_approved_ranges as ranges


class ApprovedRanges(unittest.TestCase):
    def test_committed_scope_and_unresolved_names(self):
        document = ranges.read_manifest()
        self.assertEqual(document['file_count'], 9)
        self.assertEqual(len(document['unresolved']), 6)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'manifest.json'
            for change in ('extra', 'substitute', 'range'):
                bad = copy.deepcopy(document)
                first = next(iter(bad['provenance']))
                if change == 'extra':
                    bad['requests'].append('other')
                elif change == 'substitute':
                    bad['provenance'][first]['path'] = 'texture_library/similar.texture'
                else:
                    bad['provenance'][first]['offset'] += 1
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    ranges.read_manifest(path)

    def test_payload_and_header_pins_all_required(self):
        raw = b'header' + b'payload' * 100
        stored = zlib.compress(raw)
        record = dict(bytes=len(raw), stored_bytes=len(stored), compressed=True,
                      sha256=hashlib.sha256(raw).hexdigest(), stored_sha256=hashlib.sha256(stored).hexdigest(),
                      md5_table=hashlib.md5(raw).hexdigest(), cached_header_bytes=6,
                      cached_header_sha256=hashlib.sha256(raw[:6]).hexdigest())
        self.assertEqual(ranges.decode(stored, record), raw)
        for field in ('sha256', 'stored_sha256', 'cached_header_sha256', 'md5_table'):
            with self.assertRaises(ValueError):
                ranges.decode(stored, record | {field: '0' * len(record[field])})
        trailing = stored + b'junk'
        with self.assertRaises(ValueError):
            ranges.decode(trailing, record | dict(stored_bytes=len(trailing), stored_sha256=hashlib.sha256(trailing).hexdigest()))

    def test_whole_archive_and_changed_partial_response_rejected(self):
        record = next(iter(ranges.read_manifest()['provenance'].values()))
        for changed in ('status', 'etag', 'range'):
            response = unittest.mock.MagicMock()
            response.__enter__.return_value = response
            response.status = 200 if changed == 'status' else 206
            response.geturl.return_value = record['source_url']
            response.headers = {'ETag': 'different' if changed == 'etag' else record['source_etag'],
                                'Last-Modified': record['source_last_modified'],
                                'Content-Range': 'wrong' if changed == 'range' else record['source_content_range'],
                                'Content-Length': str(record['stored_bytes'])}
            with patch('stage_approved_ranges.urllib.request.urlopen', return_value=response):
                with self.assertRaises(ValueError):
                    ranges.download(record)
                response.read.assert_not_called()

    def test_extra_missing_corrupt_or_linked_staged_data_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'texture_library/one.texture'
            target.parent.mkdir()
            target.write_bytes(b'one')
            doc = dict(files={'data/texture_library/one.texture': dict(bytes=3, sha256=hashlib.sha256(b'one').hexdigest())})
            ranges.verify(root, doc)
            target.write_bytes(b'two')
            with self.assertRaises(ValueError): ranges.verify(root, doc)
            target.unlink()
            with self.assertRaises(ValueError): ranges.verify(root, doc)
            target.symlink_to('/dev/null')
            with self.assertRaises(ValueError): ranges.verify(root, doc)

    def test_notice_receipt_uses_actual_successful_response(self):
        record = next(iter(ranges.read_manifest()['provenance'].values()))
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 206
        response.geturl.return_value = record['source_url']
        response.headers = {'ETag': record['source_etag'], 'Last-Modified': record['source_last_modified'],
            'Content-Range': record['source_content_range'], 'Content-Length': str(record['stored_bytes'])}
        response.read.return_value = b'payload'
        receipts = []
        with patch('stage_approved_ranges.urllib.request.urlopen', return_value=response):
            self.assertEqual(ranges.download(record, receipts), b'payload')
        self.assertEqual(receipts[0]['content_range'], response.headers['Content-Range'])
        self.assertEqual(receipts[0]['bytes_received'], 7)
