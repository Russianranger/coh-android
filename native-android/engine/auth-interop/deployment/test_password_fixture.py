"""Private disposable fixture storage controls; no account/database operations."""
import json
import os
from pathlib import Path
import tempfile
import unittest

import password_fixture as fixture


class PasswordFixtureTests(unittest.TestCase):
    def test_private_known_fixture_fits_native_contract_and_does_not_replace_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'private'
            fixture.write_private_fixture(directory)
            self.assertLessEqual(len(fixture.ACCOUNT), 14)
            self.assertLessEqual(len(fixture.PASSWORD), 16)
            self.assertEqual(set(x.name for x in directory.iterdir()), {'credential.json', 'credential.sql'})
            credential = json.loads((directory / 'credential.json').read_text())
            self.assertTrue(credential['disposable_known_fixture'])
            self.assertNotIn(fixture.PASSWORD, (directory / 'credential.sql').read_text())
            if os.name == 'posix':
                self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
                self.assertTrue(all(x.stat().st_mode & 0o777 == 0o600 for x in directory.iterdir()))
            original = {x.name: x.read_bytes() for x in directory.iterdir()}
            with self.assertRaises(FileExistsError):
                fixture.write_private_fixture(directory)
            self.assertEqual(original, {x.name: x.read_bytes() for x in directory.iterdir()})

    def test_existing_directory_symlink_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'target'
            target.mkdir()
            link = Path(temporary) / 'link'
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                fixture.write_private_fixture(link)
            self.assertEqual(list(target.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
