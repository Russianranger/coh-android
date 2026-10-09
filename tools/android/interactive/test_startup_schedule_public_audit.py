"""Exercise both valid serialization orders without relaxing manifest guards."""
import copy
import hashlib
import unittest

import audit_startup_schedule_public as audit


class PublicManifestOrderingTests(unittest.TestCase):
    def setUp(self):
        self.frozen = audit.frozen
        self.original = self.frozen.verification_manifests
        self.client = {'files': {name: {'bytes': 1, 'sha256': 'old'} for name in sorted(self.frozen.HELPERS)}}
        self.donor = {'runtime_manifest': {'files': copy.deepcopy(self.client['files'])}}
        self.updates = {name: {'bytes': 2, 'sha256': name} for name in sorted(self.frozen.HELPERS | self.frozen.NATIVE_ASSETS)}

    def test_both_published_native_orders_preserve_exact_client_pin(self):
        native = sorted(self.frozen.NATIVE_ASSETS)
        for order in (native, native[::-1]):
            updates = {name: self.updates[name] for name in sorted(self.frozen.HELPERS) + order}
            actual, runtime = self.original(self.donor, self.client, updates, audit.COMMIT)
            with audit.publication_manifest_order(actual):
                reconstructed, reconstructed_runtime = self.frozen.verification_manifests(
                    self.donor, self.client, dict(reversed(list(updates.items()))), audit.COMMIT)
            self.assertEqual(reconstructed, actual)
            self.assertEqual(reconstructed_runtime, runtime)
            raw = self.frozen.shared.encoded(actual)
            self.assertEqual(runtime['files']['client-manifest.json'],
                {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
            self.assertIs(self.frozen.verification_manifests, self.original)

    def test_extra_or_missing_update_is_rejected_and_function_restored(self):
        actual, _ = self.original(self.donor, self.client, self.updates, audit.COMMIT)
        for invalid in ({**self.updates, 'unexpected.exe': {}},
                        {name: pin for name, pin in self.updates.items() if name != 'startup-dbserver.exe'}):
            with self.assertRaises(ValueError):
                with audit.publication_manifest_order(actual):
                    self.frozen.verification_manifests(self.donor, self.client, invalid, audit.COMMIT)
            self.assertIs(self.frozen.verification_manifests, self.original)

    def test_changed_value_is_rejected(self):
        actual, _ = self.original(self.donor, self.client, self.updates, audit.COMMIT)
        actual = copy.deepcopy(actual)
        actual['files']['startup-dbserver.exe']['sha256'] = 'changed'
        with self.assertRaises(ValueError):
            with audit.publication_manifest_order(actual):
                self.frozen.verification_manifests(self.donor, self.client, self.updates, audit.COMMIT)
        self.assertIs(self.frozen.verification_manifests, self.original)

    def test_missing_native_key_is_rejected_before_adapter_installation(self):
        actual, _ = self.original(self.donor, self.client, self.updates, audit.COMMIT)
        del actual['files']['startup-dbserver.exe']
        with self.assertRaises(ValueError):
            with audit.publication_manifest_order(actual):
                self.fail('Invalid manifest must not enter the context')
        self.assertIs(self.frozen.verification_manifests, self.original)


if __name__ == '__main__':
    unittest.main()
