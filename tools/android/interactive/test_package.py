"""Interactive app isolation, guest closure and retained signing identity checks."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent


def load(name, filename):
    spec=importlib.util.spec_from_file_location(name,HERE/filename)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


build=load('interactive_build_test','build_apk.py')
assets=load('interactive_assets_test','prepare_assets.py')


class InteractivePackageTests(unittest.TestCase):
    def test_separate_app_and_version_are_enforced(self):
        manifest=build.ROOT/'android/interactive/src/main/AndroidManifest.xml'
        build.verify_source_manifest(manifest)
        self.assertEqual('COH-Local-Login-0.8.0.apk',build.APK_NAME)
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'AndroidManifest.xml';text=manifest.read_text()
            for changed in (text.replace('cohclientinteractive','cohclienttest'),
                            text.replace('versionName="0.8.0"','versionName="0.7.0"'),
                            text.replace('versionCode="2"','versionCode="1"')):
                path.write_text(changed)
                with self.assertRaisesRegex(ValueError,'identity'):build.verify_source_manifest(path)

    def test_guest_inventory_contains_both_helpers_and_accepted_inputs(self):
        self.assertIn('client_startup_diagnostic.py',assets.PROBE_FILES)
        self.assertIn('client_interactive_diagnostic.py',assets.PROBE_FILES)
        self.assertTrue({'client_login_diagnostic.py','local_login_server.py',
                         'dbserver-package.tar.gz','dbserver-schema.tar.gz',
                         '001-coh-compat.sql','psqlodbc_x86.msi'}<=assets.PROBE_FILES)
        self.assertTrue(assets.bundle_contract()['server_packages_included'])
        self.assertTrue({'client-runtime.zip','client-caches.zip','client-prerequisites.zip','client-launcher.exe'}<=assets.PROBE_FILES)
        self.assertEqual('actual_client_login_guest',assets.bundle_contract()['scope'])
        self.assertEqual('client_login_diagnostic.py',assets.bundle_contract()['guest_script'])
        self.assertEqual('client-manifest.json',assets.PROBE_MANIFEST)
        self.assertEqual('fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203',assets.RUNTIME_MANIFEST_SHA256)

    def test_source_closure_requires_local_interactive_rfb_without_legacy_rfb(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);main=root/'main';java=main/'java';java.mkdir(parents=True)
            generated=root/'generated';generated.mkdir()
            transport=java/'InteractiveRfbClient.java'
            transport.write_text('package '+build.APP_ID+';\nclass InteractiveRfbClient {}\n')
            sources=build.java_sources(main,generated)
            self.assertIn(transport,sources)
            self.assertFalse(any(path.name=='RfbClient.java' for path in sources))
            self.assertEqual(1,sum(path.name=='AtlasAssetImporter.java' for path in sources))
            transport.write_text('package io.github.russianranger.cohpresentation;\nclass InteractiveRfbClient {}\n')
            with self.assertRaisesRegex(ValueError,'package differs'):build.java_sources(main,generated)
            transport.unlink()
            with self.assertRaisesRegex(ValueError,'RFB client source missing'):build.java_sources(main,generated)

    def test_import_donor_stays_original_accepted_atlas(self):
        self.assertEqual(36638344040,build.import_donor()['run_id'])
        self.assertEqual('e30c0b58b0e53534f92e77cdb7b8b93fe3ddc5ce',build.IMPORT_COMMIT)
        self.assertEqual(4,len(build.accepted_import_pins()))


class RetainedSigningTests(unittest.TestCase):
    def test_missing_key_never_generates_a_replacement(self):
        with tempfile.TemporaryDirectory() as temporary,mock.patch.object(build,'run') as invoke:
            path=Path(temporary)/'absent.p12'
            with self.assertRaisesRegex(ValueError,'Existing regular retained'):
                build.verify_signing_identity(path,'coh-client-interactive','a'*64,'env:TEST_PASSWORD')
            invoke.assert_not_called();self.assertFalse(path.exists())

    def test_passwords_use_references_and_signer_pin_rejects_extra_signers(self):
        with mock.patch.dict(os.environ,{'COH_INTERACTIVE_TEST_PASSWORD':'fixture-only'}):
            self.assertEqual('env:COH_INTERACTIVE_TEST_PASSWORD',build.signing_password_spec('COH_INTERACTIVE_TEST_PASSWORD'))
        with self.assertRaises(ValueError):build.signing_password_spec('INVALID:password')
        expected='a'*64;line='Signer #1 certificate SHA-256 digest: '+expected+'\n'
        self.assertEqual(expected,build.verify_signer_output(line,expected))
        for changed in (line.replace(expected,'b'*64),line+'Signer #2 certificate SHA-256 digest: '+expected+'\n'):
            with self.assertRaisesRegex(ValueError,'retained certificate'):build.verify_signer_output(changed,expected)

    @unittest.skipUnless(shutil.which('keytool'),'JDK keytool required for retained certificate preflight')
    def test_real_existing_key_certificate_is_pinned_before_build(self):
        # Fixture creation belongs to this test only; the APK builder has no key-creation path.
        with tempfile.TemporaryDirectory() as temporary,mock.patch.dict(os.environ,{'COH_INTERACTIVE_TEST_PASSWORD':'fixture-only'}):
            root=Path(temporary);keystore=root/'retained.p12';certificate=root/'certificate.der'
            subprocess.run(['keytool','-genkeypair','-keystore',str(keystore),'-storepass:env','COH_INTERACTIVE_TEST_PASSWORD',
                            '-keypass:env','COH_INTERACTIVE_TEST_PASSWORD','-alias','coh-client-interactive','-keyalg','RSA',
                            '-keysize','2048','-validity','1','-dname','CN=Interactive Packaging Test'],
                           check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            subprocess.run(['keytool','-exportcert','-keystore',str(keystore),'-storepass:env','COH_INTERACTIVE_TEST_PASSWORD',
                            '-alias','coh-client-interactive','-file',str(certificate)],
                           check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            expected=hashlib.sha256(certificate.read_bytes()).hexdigest();before=keystore.read_bytes()
            self.assertEqual(expected,build.verify_signing_identity(keystore,'coh-client-interactive',expected,
                                                                   'env:COH_INTERACTIVE_TEST_PASSWORD'))
            password_file=root/'password.txt';password_file.write_text('fixture-only\n')
            self.assertEqual(expected,build.verify_signing_identity(keystore,'coh-client-interactive',expected,
                                                                   build.signing_password_spec(password_file=password_file)))
            with self.assertRaisesRegex(ValueError,'differs from expected'):
                build.verify_signing_identity(keystore,'coh-client-interactive','0'*64,'env:COH_INTERACTIVE_TEST_PASSWORD')
            self.assertEqual(before,keystore.read_bytes())


if __name__=='__main__':unittest.main()
