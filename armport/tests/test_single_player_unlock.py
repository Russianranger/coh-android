"""0.13.85: the account unlock switches (client patch 0136, server patch
patches/mapserver-single-player/0002). Text checks only; both are compiled in CI."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/scripts'), str(ROOT / 'android/guest')]
import armport_server_metrics_contract as contract
import prepare_server_metrics_source as producer

CLIENT = ROOT / 'armport/patches/0136-armport-single-player-unlock.patch'
SERVER = ROOT / producer.UNLOCK_PATCH


def added(text):
    return [line[1:] for line in text.splitlines() if line.startswith('+') and not line.startswith('+++')]


class SinglePlayerUnlock(unittest.TestCase):
    def test_the_client_and_the_server_get_the_same_change_to_one_file(self):
        client, server = CLIENT.read_text(), SERVER.read_text()
        self.assertEqual(client, server)
        self.assertEqual([line[6:] for line in client.splitlines() if line.startswith('+++ b/')],
                         [producer.ACCOUNTDATA])
        self.assertEqual((ROOT / 'armport/patches/series').read_text().split()[-1], CLIENT.name)
        # Nothing is removed: with both switches unset every function runs its original lines.
        self.assertEqual([line for line in client.splitlines()
                          if line.startswith('-') and not line.startswith('---')], [])

    def test_each_switch_is_read_from_the_environment_and_is_off_when_unset(self):
        lines = added(CLIENT.read_text())
        text = '\n'.join(lines)
        self.assertIn('*state = (value && value[0] == \'1\' && value[1] == 0) ? 1 : 0;', text)
        self.assertIn('return armport_switch("ARMPORT_UNLOCK_ALL", &state);', text)
        self.assertIn('return armport_switch("ARMPORT_PRIMALIST", &state);', text)
        self.assertEqual(text.count('getenv('), 1)
        # Every other added statement is behind one of the two switches.
        guards = [line.strip() for line in lines if line.strip().startswith('if (')]
        self.assertEqual(sorted(set(guards) - {'if (*state < 0)'}), sorted([
            'if (node && armport_unlock_all())', 'if (nodeName && armport_unlock_all())',
            'if (tier && armport_unlock_all())', 'if (tierName && armport_unlock_all())',
            'if (level && armport_unlock_all())', 'if (levelName && armport_unlock_all())',
            'if (armport_unlock_all())', 'if (skuIdEquals(sku_id, skuIdFromString("ctatprim")))']))

    def test_the_primalist_product_follows_its_own_switch_only(self):
        text = CLIENT.read_text()
        start = text.index('+    if (skuIdEquals(sku_id, skuIdFromString("ctatprim")))')
        block = text[start:start + 260]
        self.assertLess(block.index('return armport_primalist() != 0;'), block.index('if (armport_unlock_all())'))
        # Counts of consumable products are not touched.
        self.assertNotIn('AccountGetStoreProductCount', '\n'.join(added(text)).replace(
            '(AccountGetStoreProductCount) are not changed', ''))

    def test_the_server_claim_is_the_exact_patch_and_its_file(self):
        self.assertEqual(producer.digest(producer.unlock_patch_bytes()), contract.UNLOCK_PATCH)
        self.assertEqual(tuple(producer.UNLOCK_SOURCES), contract.UNLOCK_SOURCES)
        entry = producer.CONTRACT['account_unlock']
        self.assertEqual(entry['environment_variables'], [contract.UNLOCK_ALL_ENV, contract.PRIMALIST_ENV])
        build = {'build_input': {'patched_sha256': {}, 'contract': {}}}
        self.assertFalse(contract.account_unlock_changed(build))
        build['build_input']['patched_sha256'][contract.UNLOCK_SOURCES[0]] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'outside the reviewed unlock patch'):
            contract.account_unlock_changed(build)
        build['build_input'].update(
            account_unlock_patch={'path': producer.UNLOCK_PATCH, 'sha256': contract.UNLOCK_PATCH},
            contract={'account_unlock': json.loads(json.dumps(entry))})
        self.assertTrue(contract.account_unlock_changed(build))
        for change in (lambda b: b['account_unlock_patch'].update(sha256='1' * 64),
                       lambda b: b['contract']['account_unlock'].update(disabled_by_default=False),
                       lambda b: b['contract']['account_unlock']['unlock_all'].update(
                           consumable_product_counts_changed=True),
                       lambda b: b['contract']['account_unlock']['primalist'].update(part_of_unlock_all=True),
                       lambda b: b['contract']['account_unlock'].update(gameplay_decisions_changed_when_unset=True),
                       lambda b: b['contract'].pop('account_unlock')):
            changed = json.loads(json.dumps(build))
            change(changed['build_input'])
            with self.assertRaisesRegex(ValueError, 'outside the reviewed unlock patch'):
                contract.account_unlock_changed(changed)


if __name__ == '__main__':
    unittest.main()
