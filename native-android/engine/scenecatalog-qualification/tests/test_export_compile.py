"""Compile-only packaging must identify Win32 PE and isolated CMake inputs."""
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from record_export_compile import cmake_identity, pe32_identity, validate_inputs


class CompileArtifactAdmission(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def pe(self, machine=0x14c, optional=0x10b, flags=0x102, optional_size=224):
        image = bytearray(1024)
        image[:2] = b"MZ"
        struct.pack_into("<I", image, 60, 128)
        image[128:132] = b"PE\0\0"
        struct.pack_into("<HH", image, 132, machine, 3)
        struct.pack_into("<HHH", image, 148, optional_size, flags, optional)
        struct.pack_into("<I", image, 168, 0x1000)
        binary = self.root / "MapServer.exe"
        binary.write_bytes(image)
        return binary

    def test_pe32_i386_executable(self):
        pe32_identity(self.pe())

    def test_wrong_pe_architecture_optional_header_and_dll(self):
        for kwargs in ({"machine": 0x8664}, {"optional": 0x20b}, {"flags": 0x2102}, {"flags": 0x100}, {"optional_size": 65535}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                pe32_identity(self.pe(**kwargs))

    def test_corrupt_truncated_and_linked_pe(self):
        binary = self.pe()
        for data in (b"not an executable", b"MZ" + bytes(1022)):
            binary.write_bytes(data)
            with self.assertRaises(ValueError):
                pe32_identity(binary)
        link = self.root / "linked.exe"
        link.symlink_to(self.pe())
        with self.assertRaises(ValueError):
            pe32_identity(link)

    def test_expected_cmake_cache(self):
        cache = self.root / "CMakeCache.txt"
        content = ("CMAKE_GENERATOR:INTERNAL=Visual Studio 18 2026\n"
            "CMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n"
            "CMAKE_CONFIGURATION_TYPES:STRING=Debug;Release;OptDebug\n"
            "CMAKE_HOME_DIRECTORY:INTERNAL=" + str(self.root) + "\n")
        cache.write_text(content)
        cmake_identity(cache, self.root)
        for changed in (content.replace("Win32", "x64"), content.replace("OptDebug", "Other"),
                        content + "CMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n",
                        content.replace(str(self.root), str(self.root / "other"))):
            cache.write_text(changed)
            with self.assertRaises(ValueError):
                cmake_identity(cache, self.root)

    def test_input_receipt_requires_full_pinned_identity_and_exact_types(self):
        helper = SimpleNamespace(DONOR={"bytes": 1, "sha256": "a" * 64}, BASE={"bytes": 2, "sha256": "b" * 64},
            INPUTS={"input.bin": {"bytes": 3, "sha256": "c" * 64}}, fx=SimpleNamespace(BASE={"bytes": 4, "sha256": "d" * 64}))
        receipt = {"format": 1, "status": "exact_published_inputs_staged",
            "donor_commit": "74fe247be85173e618f1af2c8af71b1316de4cd8", "donor_apk": helper.DONOR,
            "asset_release": "coh-assets-v1.0.0", "base_volume": helper.BASE,
            "files": {**helper.INPUTS, "fxinfo-full.bin": helper.fx.BASE},
            "donor_rebuilt": False, "assets_republished": False,
            "native_runtime_execution_validated": False, "physical_execution_validated": False}
        validate_inputs(receipt, helper)
        for key, value in (("donor_commit", "e" * 40), ("files", {}), ("donor_apk", {}), ("donor_rebuilt", 0)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_inputs({**receipt, key: value}, helper)


if __name__ == "__main__":
    unittest.main()
