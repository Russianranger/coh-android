"""NONSHIPPING owned-stream prerequisite; real SDK headers, host fixtures only.

No mesh SDK/cooking or native binary builds occur. ASAN/UBSAN support is required
for this suite to pass; missing tooling fails qualification rather than skipping.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = ROOT / "database/map-startup-physics/qualification"
SDK_INCLUDE = ROOT / "upstream/ouroboros/3rdparty/PhysX/SDKs/Foundation/include"
FIXTURES = (
    "ownership", "parity", "short_reads", "overflow_and_cap", "allocation_failure",
    "modes", "invalid_input", "self_append", "consumer_boundary", "growth",
)
COMPILER = os.environ.get("CXX", "c++")
LEAK_SANITIZER_ENABLED = False


def compile_command(source: Path, binary: Path, sanitized: bool = False) -> list[str]:
    # The unchanged vendor SDK assumes NX32 on Linux. This fixture is explicitly
    # for this host architecture, not a claim that its code/DLL ran as Win32.
    command = [COMPILER, "-std=c++03", "-Wall", "-Wextra", "-Werror",
               "-DNX64" if struct.calcsize("P") == 8 else "-DNX32",
               "-I" + str(QUALIFICATION), "-I" + str(SDK_INCLUDE)]
    if sanitized:
        command += ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
        # Fixed placement avoids intermittent ASAN shadow/PIE mapping conflicts
        # in container hosts. This is a host fixture compiler option only.
        if sys.platform.startswith("linux"):
            command += ["-fno-pie", "-no-pie"]
    command += [str(source), "-o", str(binary)]
    return command


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    # This managed host prevents LSAN's /proc thread inspection. Address and
    # undefined checks remain mandatory. Opt in to LSAN on a compatible host;
    # inability to run requested LSAN is a failure, never an automatic fallback.
    environment["ASAN_OPTIONS"] = (f"detect_leaks={int(LEAK_SANITIZER_ENABLED)}:"
                                    "halt_on_error=1:abort_on_error=1")
    environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    result = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=45)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {command}\n"
                           f"{result.stdout[-12000:]}{result.stderr[-12000:]}")
    return result


class _FixtureMixin:
    sanitized = False

    @classmethod
    def setUpClass(cls):
        if not shutil.which(COMPILER):
            raise RuntimeError(f"C++ compiler required: {COMPILER}")
        cls.temporary = tempfile.TemporaryDirectory(prefix="coh-owned-stream-host-")
        cls.directory = Path(cls.temporary.name)
        cls.binary = cls.directory / "bounded-stream-fixture"
        run(compile_command(QUALIFICATION / "bounded_stream_fixture.cpp", cls.binary, cls.sanitized))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def fixture(self, name):
        result = run([str(self.binary), name])
        self.assertEqual(result.stdout.strip(), f"host bounded stream fixture passed: {name}")
        self.assertEqual(result.stderr, "")

    def test_owned_independent_instances_scoped_release(self): self.fixture("ownership")
    def test_native_byte_primitive_bulk_and_signed_wrapper_parity(self): self.fixture("parity")
    def test_every_primitive_short_read_and_bulk_no_zero_fill(self): self.fixture("short_reads")
    def test_overflow_exact_cap_zero_cap_and_no_failed_transition(self): self.fixture("overflow_and_cap")
    def test_initial_and_growth_allocator_failure_preserve_state(self): self.fixture("allocation_failure")
    def test_write_read_modes_and_sticky_failure(self): self.fixture("modes")
    def test_null_negative_cap_and_bad_allocator_rejection(self): self.fixture("invalid_input")
    def test_self_append_relocation_and_initialized_source_extent(self): self.fixture("self_append")
    def test_mock_consumer_requires_before_after_validity_and_null_rejection(self): self.fixture("consumer_boundary")
    def test_growth_extent_content_cap_and_no_whole_allocation_zeroing(self): self.fixture("growth")


class HostFixtures(_FixtureMixin, unittest.TestCase):
    pass


class AddressUndefinedSanitizerFixtures(_FixtureMixin, unittest.TestCase):
    sanitized = True


class CompileContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="coh-owned-stream-contract-")
        cls.directory = Path(cls.temporary.name)

    @classmethod
    def tearDownClass(cls): cls.temporary.cleanup()

    def rejected(self, statement):
        source = self.directory / "rejected.cpp"
        source.write_text('#include "nx_owned_bounded_stream.h"\nint main() { ' + statement + ' }\n')
        result = run(compile_command(source, self.directory / "rejected"), check=False)
        self.assertNotEqual(result.returncode, 0, "ownership violation unexpectedly compiled")
        return result.stderr

    def test_core_cannot_be_copied(self):
        self.assertIn("private", self.rejected(
            "coh_qualification::OwnedBoundedStream a(4); coh_qualification::OwnedBoundedStream b(a);"))

    def test_core_cannot_be_assigned(self):
        self.assertIn("private", self.rejected(
            "coh_qualification::OwnedBoundedStream a(4), b(4); a = b;"))

    def test_nx_adapter_cannot_be_copied(self):
        self.assertIn("private", self.rejected(
            "coh_qualification::NxOwnedBoundedStream a(4); coh_qualification::NxOwnedBoundedStream b(a);"))

    def test_nx_adapter_cannot_be_assigned(self):
        self.assertIn("private", self.rejected(
            "coh_qualification::NxOwnedBoundedStream a(4), b(4); a = b;"))

    def test_no_unbounded_default_constructor(self):
        self.rejected("coh_qualification::NxOwnedBoundedStream unbounded;")


def evidence(result) -> dict:
    files = [QUALIFICATION / "owned_bounded_stream.h", QUALIFICATION / "nx_owned_bounded_stream.h",
             QUALIFICATION / "bounded_stream_fixture.cpp", Path(__file__).resolve(),
             SDK_INCLUDE / "Nx.h", SDK_INCLUDE / "NxSimpleTypes.h", SDK_INCLUDE / "NxStream.h"]
    return {
        "schema": "coh-owned-bounded-stream-host-prerequisite-v1",
        "status": "passed" if result.wasSuccessful() and not result.skipped else "failed",
        "host_tests": result.testsRun, "skips": len(result.skipped),
        "failures": len(result.failures), "errors": len(result.errors),
        "compiler": run([COMPILER, "--version"]).stdout.splitlines()[0],
        "host_pointer_bits": struct.calcsize("P") * 8,
        "cxx_language": "c++03", "asan": True, "ubsan": True,
        "leak_sanitizer": LEAK_SANITIZER_ENABLED,
        "owned_allocator_allocation_release_accounting": True,
        "real_vendor_headers_compiled": ["Nx.h", "NxSimpleTypes.h", "NxStream.h"],
        "fixtures": list(FIXTURES),
        "files_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in files},
        "shipping_integration": False, "native_binary_built": False,
        "sdk_cooking_executed": False, "sdk_mesh_creation_executed": False,
        "win32_wine_validated": False, "collision_parity_validated": False,
        "thor_validated": False, "startup_seconds": None, "ram_savings_bytes": None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--leak-sanitizer", action="store_true",
                        help="require LSAN as well (needs unrestricted /proc thread inspection)")
    arguments, test_arguments = parser.parse_known_args()
    LEAK_SANITIZER_ENABLED = arguments.leak_sanitizer
    result = unittest.TestProgram(module=__name__, argv=[sys.argv[0], *test_arguments],
                                  exit=False, verbosity=2).result
    if arguments.evidence:
        arguments.evidence.parent.mkdir(parents=True, exist_ok=True)
        arguments.evidence.write_text(json.dumps(evidence(result), indent=2, sort_keys=True) + "\n")
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
