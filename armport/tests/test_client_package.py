#!/usr/bin/env python3
"""Exercise architecture separation and malformed overlay rejection."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import armport_client_package as package


def pe(machine=0xaa64):
    data = bytearray(128)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 64)
    data[64:68] = b'PE\0\0'
    struct.pack_into('<H', data, 68, machine)
    struct.pack_into('<H', data, 88, 0x20b)
    return data


class ClientPackage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client, self.bins, self.shaders = (self.root / name for name in ('client', 'bins', 'shaders'))
        for directory in (self.client, self.bins, self.shaders): directory.mkdir()
        for name in package.BINARIES - {'armport-launcher.exe'}: (self.client / name).write_bytes(pe())
        self.launcher = self.root / 'armport-launcher.exe'
        self.launcher.write_bytes(pe())
        (self.bins / 'BodyParts.bin').write_bytes(b'arm64 bins')
        (self.shaders / 'test.arb').write_bytes(b'!!ARBvp1.0\nEND\n')
        self.archive = self.root / 'armport.zip'

    def build(self):
        return package.package(self.client, self.bins, self.shaders, self.launcher, self.archive, 123, 122)

    def test_data_and_binary_separation(self):
        self.build()
        source = self.root / 'x86' / 'data'
        (source / 'bin').mkdir(parents=True)
        (source / 'bin' / 'BodyParts.bin').write_bytes(b'x86 bins')
        (source / 'bin' / 'obsolete.bin').write_bytes(b'old')
        (source / 'texture_library').mkdir()
        texture = source / 'texture_library' / 'x.texture'
        texture.write_bytes(b'immutable asset')
        destination = self.root / 'arm64'
        report = package.prepare(self.archive, source, destination)
        self.assertEqual((destination / 'data/bin/BodyParts.bin').read_bytes(), b'arm64 bins')
        self.assertFalse((destination / 'data/bin/obsolete.bin').exists())
        self.assertEqual((source / 'bin/BodyParts.bin').read_bytes(), b'x86 bins')
        self.assertEqual(texture.read_bytes(), b'immutable asset')
        self.assertEqual(report['shared_data_files'], 1)
        self.assertFalse(report['x86_bins_reused'])

    def test_reject_x86_binary(self):
        (self.client / 'libc++.dll').write_bytes(pe(0x14c))
        with self.assertRaisesRegex(ValueError, 'ARM64 PE32'):
            self.build()

    def test_linked_server_input_becomes_private_regular_file_without_link_syscall(self):
        self.build()
        source = self.root / 'server-data'
        source.mkdir()
        imported = self.root / 'immutable.texture'
        imported.write_bytes(b'original')
        (source / 'linked.texture').symlink_to(imported)
        destination = self.root / 'arm64'
        # PRoot remaps hard links; the new stage must not rely on link().
        with mock.patch.object(package.os, 'link', side_effect=AssertionError('link2symlink path')):
            report = package.prepare(self.archive, source, destination)
        target = destination / 'data/linked.texture'
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.read_bytes(), b'original')
        target.write_bytes(b'client mutation')
        self.assertEqual(imported.read_bytes(), b'original')
        self.assertEqual(report['data_materialization'], 'private_regular_copies')

    def test_corrupt_payload(self):
        self.build()
        altered = self.root / 'altered.zip'
        with zipfile.ZipFile(self.archive) as source, zipfile.ZipFile(altered, 'w') as output:
            for info in source.infolist():
                data = source.read(info)
                if info.filename == 'data/bin/BodyParts.bin': data = b'altered!!!'
                output.writestr(info, data)
        with self.assertRaisesRegex(ValueError, 'digest differs'):
            package.unpack(altered, self.root / 'output')

    def test_reject_unexpected_member(self):
        self.build()
        with zipfile.ZipFile(self.archive, 'a') as archive: archive.writestr('../escape', b'bad')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            package.unpack(self.archive, self.root / 'output')
        self.assertFalse((self.root / 'escape').exists())


if __name__ == '__main__':
    unittest.main()
