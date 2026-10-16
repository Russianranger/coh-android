"""Optional exact public artifact inspection; no binary/service execution."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import inspect_client_reference as reference

ROOT = Path(__file__).resolve().parents[4]
APK = os.environ.get('COH_AUTH_REFERENCE_APK')


@unittest.skipUnless(APK, 'exact public donor artifact not supplied; no reference qualification inferred')
class ClientReferenceTests(unittest.TestCase):
    def test_exact_inspection_never_approves_alias_or_native_profile(self):
        result = reference.inspect(ROOT, Path(APK))
        self.assertTrue(result['inspection_passed'])
        for key in ('deployment_profile_admitted', 'native_reference_compatibility_approved',
                    'alias_created', 'original_alias_present', 'client_version_ini_present',
                    'nondev_compatible_version_observed', 'real_account_login_verified',
                    'original_checksum_functions_executed'):
            self.assertIs(result[key], False)
        self.assertEqual(result['whole_file_md5_hex'], '3102c83178c9bca4385aa9bcc5e003bb')

    def test_pinned_donor_archive_and_executable_identities_enforced(self):
        original = json.loads((reference.HERE / 'client-reference-pins.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            for section in ('donor_apk', 'client_runtime_zip', 'client_executable'):
                pins = json.loads(json.dumps(original))
                pins[section]['sha256'] = '0' * 64
                (config / 'client-reference-pins.json').write_text(json.dumps(pins))
                with self.subTest(section=section), patch.object(reference, 'HERE', config):
                    with self.assertRaisesRegex(ValueError, 'identity_mismatch'):
                        reference.inspect(ROOT, Path(APK))


if __name__ == '__main__':
    unittest.main()
