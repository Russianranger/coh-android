"""0.13.69: the APK builder admits a second PRoot build only with a receipt of this checkout's recipe.

The donor's libproot.so stays the default and byte-identical; the build with patch 0004 is added
beside it with its receipt, licence files and corresponding source.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/app'))

import build_thor_apk as builder  # noqa: E402

DONOR = {'lib/arm64-v8a/libproot.so': {'bytes': 263648, 'sha256': '54' * 32},
         'lib/arm64-v8a/libproot-loader.so': {'bytes': 17624, 'sha256': '95' * 32}}


class SecondProotBuild(unittest.TestCase):
    def output(self, root, **changes):
        recipe, recipe_path = builder.proot_recipe()
        directory = Path(root) / 'arm64-v8a'
        (directory / 'licenses').mkdir(parents=True)
        (directory / 'libproot.so').write_bytes(b'\x7fELF proot with patch 0004')
        (directory / 'libproot-loader.so').write_bytes(b'\x7fELF loader')
        (directory / builder.PROOT_SOURCES).write_bytes(b'sources')
        (directory / 'licenses/PRoot-COPYING').write_text('GPL-2.0-or-later\n')
        (directory / 'licenses/talloc-talloc.h').write_text('LGPL-3.0-or-later\n')
        receipt = {
            'schema_version': 1, 'target': 'android-arm64', 'status': 'native_built_runtime_unverified',
            'source_commit': recipe.PROOT_COMMIT, 'source_tree': recipe.PROOT_TREE, 'ndk_version': recipe.NDK_VERSION,
            'android_api': 26, 'max_page_size': 16384, 'talloc_linkage': 'static', 'compiler': 'clang 18',
            'ioctl_command_filter_patch': True, 'stop_counts_patch': True, 'accept_untraced_patch': True,
            'patches': {name: builder.pin(recipe.PATCHES / name) for name in recipe.PATCH_NAMES},
            'recipe_sha256': builder.pin(recipe_path)['sha256'],
            'files': {name: dict(builder.pin(directory / name), elf_machine='aarch64')
                      for name in ('libproot.so', 'libproot-loader.so')},
            'corresponding_sources': dict(builder.pin(directory / builder.PROOT_SOURCES), file=builder.PROOT_SOURCES),
            'license_files': {path.name: builder.pin(path) for path in sorted((directory / 'licenses').iterdir())}}
        receipt.update(changes)
        (directory / builder.PROOT_RECEIPT).write_text(json.dumps(receipt))
        return directory

    def test_recipe_holds_the_ioctl_patch(self):
        recipe, _ = builder.proot_recipe()
        self.assertEqual(recipe.PATCH_NAMES[-3:], ('0004-ioctl-command-filter.patch', '0005-stop-counts-getsockopt-filter.patch',
                                                   '0006-accept-untraced-program-counts.patch'))
        for name in recipe.PATCH_NAMES:
            self.assertTrue((recipe.PATCHES / name).is_file(), name)

    def test_members_and_record(self):
        with tempfile.TemporaryDirectory() as root:
            directory = self.output(root)
            members, record = builder.proot_ioctl_members(directory, DONOR)
            self.assertEqual(set(members), {
                'lib/arm64-v8a/libproot-ioctl.so', 'lib/arm64-v8a/libproot-ioctl-loader.so',
                'assets/proot-ioctl/proot-build-receipt.json', 'assets/proot-ioctl/proot-corresponding-sources.tar.gz',
                'assets/proot-ioctl/licenses/PRoot-COPYING', 'assets/proot-ioctl/licenses/talloc-talloc.h'})
            self.assertEqual(members['lib/arm64-v8a/libproot-ioctl.so'], directory / 'libproot.so')
            self.assertEqual(record['donor_libproot_retained'], DONOR['lib/arm64-v8a/libproot.so'])
            self.assertIs(record['default'], True)        # 0.13.70: the second build is the default
            self.assertEqual(record['launch_option'], 'proot-call-filter')
            self.assertIn('PROOT_STOP_COUNTS=<file>', record['switches'])
            self.assertIs(record['device_validated'], False)
            self.assertEqual(set(record['members']), set(members))
            self.assertIn('0004-ioctl-command-filter.patch', record['patches'])

    def test_refusals(self):
        recipe, _ = builder.proot_recipe()
        cases = {
            'linux build': {'target': 'linux-arm64'},
            'prepared only': {'status': 'source_prepared_only'},
            'other commit': {'source_commit': '0' * 40},
            'other ndk': {'ndk_version': '28.2.13676358'},
            'no patch flag': {'ioctl_command_filter_patch': False},
            'no stop counts flag': {'stop_counts_patch': False},
            'no accept flag': {'accept_untraced_patch': False},
            'three patches': {'patches': {name: builder.pin(recipe.PATCHES / name) for name in recipe.PATCH_NAMES[:3]}},
            'other recipe': {'recipe_sha256': '0' * 64},
            'no licence': {'license_files': {}},
        }
        for label, change in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as root:
                with self.assertRaises(ValueError):
                    builder.proot_ioctl_members(self.output(root, **change), DONOR)

    def test_changed_files_are_refused(self):
        for name in ('libproot.so', 'libproot-loader.so', builder.PROOT_SOURCES, 'licenses/PRoot-COPYING'):
            with self.subTest(name), tempfile.TemporaryDirectory() as root:
                directory = self.output(root)
                (directory / name).write_bytes(b'changed after the receipt')
                with self.assertRaises(ValueError):
                    builder.proot_ioctl_members(directory, DONOR)

    def test_a_donor_that_already_holds_the_name_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            donor = dict(DONOR, **{'lib/arm64-v8a/libproot-ioctl.so': {'bytes': 1, 'sha256': '00' * 32}})
            with self.assertRaises(ValueError):
                builder.proot_ioctl_members(self.output(root), donor)

    def test_app_names_match_the_builder(self):
        java = (ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
                'ClientRuntime.java').read_text()
        for member in builder.PROOT_IOCTL_LIBRARIES:
            self.assertIn('"' + member.rsplit('/', 1)[1] + '"', java)
        self.assertIn('builder.environment().put("PROOT_IOCTL_COMMANDS_ONLY", "1")', java)
        self.assertIn('builder.environment().put("PROOT_GETSOCKOPT_PEERCRED_ONLY", "1")', java)
        self.assertIn('builder.environment().put("PROOT_ACCEPT_UNTRACED", "1")', java)
        self.assertIn('builder.environment().put("PROOT_STOP_COUNTS", prootStopCounts.getPath())', java)
        self.assertIn('.getBoolean("proot-call-filter", true)', java)


if __name__ == '__main__':
    unittest.main()
