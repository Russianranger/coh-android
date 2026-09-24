"""Meaningful malformed-input checks for the 32-bit .anim disk inspector."""
import struct
import unittest

from animation_format import animation_header, animation_dependency_report


def sample(name='male/test', base='male/skel_ready', hierarchy_slots=0, flags=18):
    hierarchy_bytes = 4 + hierarchy_slots * 12 if hierarchy_slots else 0
    bone_offset = 596 + hierarchy_bytes
    header_size = bone_offset + 20
    rot_size = 16 if flags & 1 else 5
    pos_size = 12 if flags & 8 else 6
    data = bytearray(header_size + rot_size + pos_size)
    struct.pack_into('<i', data, 0, header_size)
    data[4:4 + len(name)] = name.encode()
    data[260:260 + len(base)] = base.encode()
    struct.pack_into('<ffIiiiI', data, 516, 0, 0, bone_offset, 1, 0, 0,
                     596 if hierarchy_slots else 0)
    struct.pack_into('<IIHHHHbBH', data, bone_offset, header_size,
                     header_size + rot_size, 1, 1, 1, 1, 0, flags, 0)
    if hierarchy_slots:
        struct.pack_into('<iiii', data, 596, 0, -1, -1, 0)
    if flags & 1:
        struct.pack_into('<4f', data, header_size, 0, 0, 0, 1)
    return data


class AnimationFormatTests(unittest.TestCase):
    def assert_bad(self, data, fragment):
        result = animation_header(data)
        self.assertEqual(result['validation_status'], 'structural_checks_failed')
        self.assertTrue(any(fragment in e for e in result['errors']), result)

    def test_32_bit_layout_and_legacy_hierarchy_are_explicit(self):
        full = animation_header(sample())
        self.assertEqual(full['validation_status'], 'structural_checks_passed')
        self.assertEqual(full['bone_tracks_offset'], 596)
        legacy = animation_header(sample(hierarchy_slots=70))
        self.assertEqual(legacy['validation_status'], 'structural_checks_passed')
        self.assertEqual(legacy['hierarchy_capacity'], 70)
        self.assertTrue(legacy['warnings'])
        self.assertEqual(legacy['runtime_compatibility'], 'unverified')

    def test_truncation_and_offsets_fail_before_access(self):
        self.assert_bad(b'\0' * 595, 'truncated')
        data = sample()
        self.assert_bad(data[:-1], 'position key payload')
        struct.pack_into('<I', data, 596, 0xffffffff)
        self.assert_bad(data, 'rotation key payload')
        struct.pack_into('<i', data, 528, 0x7fffffff)
        self.assert_bad(data, 'bone count')

    def test_bad_compression_marker_and_flags(self):
        data = sample()
        data[616] = 64
        self.assert_bad(data, 'top byte')
        data = sample()
        data[596 + 17] = 18 | 1
        self.assert_bad(data, 'ambiguous')

    def test_float_predicates(self):
        data = sample(flags=9)
        struct.pack_into('<f', data, 616, float('nan'))
        self.assert_bad(data, 'quaternion')
        data = sample(flags=9)
        struct.pack_into('<f', data, 632, 2000000)
        self.assert_bad(data, 'position fails')

    def test_hierarchy_cycle_and_link_bounds(self):
        data = sample(hierarchy_slots=70)
        struct.pack_into('<i', data, 600, 0)
        self.assert_bad(data, 'cycle')
        struct.pack_into('<i', data, 600, 70)
        self.assert_bad(data, 'out of bounds')

    def test_name_termination_and_path_validation(self):
        data = sample()
        data[4:260] = b'a' * 256
        self.assert_bad(data, 'NUL-terminated')
        self.assert_bad(sample(name='../outside'), 'safe relative')

    def test_dependency_graph_accepts_self_skeleton_and_rejects_missing_cycles(self):
        root = animation_header(sample('male/skel_ready', 'MALE/SKEL_READY', 100))
        track = animation_header(sample())
        result = animation_dependency_report([root, track])
        self.assertEqual(result['missing_base_names'], [])
        self.assertEqual(result['terminal_base_count'], 1)
        missing = animation_dependency_report([track])
        self.assertEqual(missing['missing_base_names'], ['male/skel_ready'])
        cyclic = animation_dependency_report([
            animation_header(sample('male/a', 'male/b')),
            animation_header(sample('male/b', 'male/a'))])
        self.assertEqual(cyclic['nonterminal_cycles'], [['male/a', 'male/b']])


if __name__ == '__main__':
    unittest.main()
