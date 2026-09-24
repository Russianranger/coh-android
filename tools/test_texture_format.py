"""Corruption and legacy-layout cases for offline texture inspection."""
import struct
import unittest

from texture_format import texture_header


def dds(width=4, height=4, levels=1, fourcc=b'DXT1', suffix=b''):
    fields = [0] * 31
    fields[0], fields[2], fields[3], fields[6] = 124, height, width, levels
    fields[18], fields[19], fields[20] = 32, 4, int.from_bytes(fourcc, 'little')
    size, w, h = 0, width, height
    for _ in range(max(1, levels)):
        size += ((w + 3) // 4) * ((h + 3) // 4) * (8 if fourcc == b'DXT1' else 16)
        w, h = max(1, w // 2), max(1, h // 2)
    return b'DDS ' + struct.pack('<31I', *fields) + b'\x12' * size + suffix


def texture(payload=None, cache=b'', width=4, height=4, version=b'TX2', name=b'texture_library/test.dds'):
    if payload is None:
        payload = dds()
    header_size = 32 + len(name) + 1 + len(cache)
    return (struct.pack('<iiiiIffB3s', header_size, len(payload), width, height,
                        0, 0.0, 0.0, 0, version) + name + b'\0' + cache + payload)


class TextureTests(unittest.TestCase):
    def assertRejected(self, data, reason):
        result = texture_header(data)
        self.assertEqual(result['validation_status'], 'structural_checks_failed')
        self.assertRegex(result['errors'][0], reason)

    def test_legacy_and_current_containers(self):
        for version in (b'TEX', b'TX2'):
            result = texture_header(texture(version=version))
            self.assertTrue(result['dds_mip_bounds_verified'])
            self.assertTrue(result['baseline_loader_accepts_payload_format'])
            self.assertEqual(result['runtime_compatibility'], 'unverified')
            self.assertFalse(result['image_pixels_decoded'])

    def test_truncated_and_inconsistent_wrapper(self):
        self.assertRejected(texture()[:-1], 'payload size')
        data = bytearray(texture())
        struct.pack_into('<i', data, 0, len(data) + 1)
        self.assertRejected(data, 'header outside')

    def test_name_must_terminate_in_header(self):
        data = bytearray(texture())
        head = struct.unpack_from('<i', data)[0]
        data[32:head] = b'x' * (head - 32)
        self.assertRejected(data, 'terminated texture name')

    def test_mip_truncation_even_with_valid_wrapper_length(self):
        self.assertRejected(texture(payload=dds(levels=3)[:-1]), 'Truncated DDS mip')

    def test_impossible_mip_count(self):
        self.assertRejected(texture(payload=dds(levels=7)), 'mip count')

    def test_legacy_extra_dds_bytes_are_reported(self):
        result = texture_header(texture(payload=dds(suffix=b'padding')))
        self.assertEqual(result['dds_uninterpreted_trailing_bytes'], 7)

    def test_logical_dimensions_can_have_power_of_two_padding(self):
        result = texture_header(texture(width=3, height=2, payload=dds(height=2)))
        self.assertTrue(result['dds_dimensions_match_texture_canvas'])

    def test_cache_is_verified_against_dds_suffix(self):
        payload = dds(levels=3)
        cache = struct.pack('<4i', 16, 2, 2, 0x83f1) + payload[136:]
        self.assertTrue(texture_header(texture(payload=payload, cache=cache))['cached_mip_verified'])
        self.assertRejected(texture(payload=payload, cache=cache[:-1] + b'!'),
                            'differs from DDS mip suffix')
        bad_header = struct.pack('<4i', 16, 2, 2, 0x83f3) + cache[16:]
        self.assertRejected(texture(payload=payload, cache=bad_header), 'format differs')

    def test_unknown_format_does_not_claim_mip_check(self):
        result = texture_header(texture(payload=dds(fourcc=b'DX10')))
        self.assertFalse(result['baseline_loader_accepts_payload_format'])
        self.assertNotIn('dds_mip_bounds_verified', result)

    def test_tga_rejected_by_baseline_loader_and_jpeg_not_decoded(self):
        result = texture_header(texture(payload=b'tga', name=b'texture_library/test.tga'))
        self.assertFalse(result['baseline_loader_accepts_payload_format'])
        result = texture_header(texture(payload=b'\xff\xd8', name=b'texture_library/test.jpg'))
        self.assertEqual(result['structural_validation'], 'wrapper_and_jpeg_signature_only')
        self.assertFalse(result['image_pixels_decoded'])


if __name__ == '__main__':
    unittest.main()
