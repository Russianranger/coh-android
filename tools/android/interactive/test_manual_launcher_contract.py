"""Reader/source negatives for helper authority; no Windows execution is claimed."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import manual_launcher_contract as contract


class NativeManualLauncherContractTests(unittest.TestCase):
    def test_original_helper_identity_and_build_source_closure_are_finite(self):
        self.assertEqual(contract.DONOR_HELPER, {'bytes':246319,
            'sha256':'fd8a3724bd009d122fe98e03229e62516b5ee31245db9c093dfaceef73bd11db'})
        self.assertEqual(len(contract.SOURCE_FILES),4)
        self.assertEqual(contract.DLLS,{'kernel32.dll','msvcrt.dll','user32.dll'})
        self.assertEqual(contract.source_pins()[contract.SOURCE],contract.file_pin(contract.ROOT/contract.SOURCE))

    def test_non_pe_truncated_arm64_or_pe64_helpers_are_rejected(self):
        for raw in (b'not a PE',b'MZ'+b'\0'*40,b'MZ'+b'\0'*127):
            with self.subTest(raw=raw[:2]),self.assertRaises(ValueError):contract.pe32(raw)
        # Synthetic headers are negative reader fixtures only, never native proof.
        for machine,magic in ((0xaa64,0x10b),(0x14c,0x20b),(0x8664,0x20b)):
            raw=bytearray(256);raw[:2]=b'MZ';struct.pack_into('<I',raw,0x3c,128)
            raw[128:132]=b'PE\0\0';struct.pack_into('<H',raw,132,machine);struct.pack_into('<H',raw,152,magic)
            with self.subTest(machine=machine),self.assertRaises(ValueError):contract.pe32(bytes(raw))

    def test_missing_build_authority_cannot_authorize_any_native_helper(self):
        with tempfile.TemporaryDirectory()as temporary:
            executable=Path(temporary)/'helper.exe';executable.write_bytes(b'unqualified')
            for value in ({},{'format':1,'status':'built'},{'native_fixture_executed':True}):
                with self.subTest(value=value),self.assertRaises(ValueError):
                    contract.validate_build(value,executable,'1'*40)

    def test_missing_or_inherited_qualification_cannot_authorize_current_helper(self):
        with tempfile.TemporaryDirectory()as temporary:
            executable=Path(temporary)/'helper.exe';executable.write_bytes(b'unqualified')
            with self.assertRaises(ValueError):
                contract.validate_qualification({'status':'passed','tests_executed_in_current_run':False},
                    {},executable,'1'*40)

    def test_windows_native_fixture_refuses_linux_before_build_or_process_access(self):
        import qualify_manual_launcher_windows as fixture
        if fixture.os.name=='nt':
            # This is a reader guard assertion, not the separate real Windows run.
            return
        class Args:pass
        with self.assertRaisesRegex(ValueError,'Genuine Windows'):
            fixture.qualify(Args())

    def test_deadline_fixture_uses_current_production_function_and_separate_simulated_elapsed_claim(self):
        import qualify_manual_launcher_windows as fixture
        raw=(contract.ROOT/contract.SOURCE).read_text()
        selected=fixture.source_block(raw,'lifetime_expired')
        self.assertIn('lifetime_ms',selected)
        self.assertIn(selected,raw)
        self.assertIn('lifetime_expired(lifetime_ms,GetTickCount64(),deadline)',raw)
        self.assertIn('--character-manual',fixture.source_block(raw,'launch_policy'))

    def test_bool_integer_substitution_and_unknown_fields_fail_exact_proof_shape(self):
        expected={'actual_source_function_compiled':True,'simulated_elapsed_hours':48,
            'real_duration_48_hour_run':False,'shipping_helper_binary_modified':False}
        self.assertTrue(contract.exact(copy.deepcopy(expected),expected))
        for key,value in (('actual_source_function_compiled',1),('real_duration_48_hour_run',0),
                ('simulated_elapsed_hours',True)):
            candidate=dict(expected,**{key:value});self.assertFalse(contract.exact(candidate,expected))
        self.assertFalse(contract.exact(dict(expected,physical_validation=True),expected))

    def test_genuine_windows_lifecycle_inventory_retains_old_modes_and_owned_cleanup(self):
        self.assertEqual(len(contract.qualification_cases()),9)
        for name in ('creation_mode_retained','cache_generation_mode_retained','local_login_mode_retained',
                'manual_owned_interruption_cleanup','manual_owned_console_child_exit'):
            self.assertIn(name,contract.qualification_cases())


if __name__=='__main__':unittest.main()
