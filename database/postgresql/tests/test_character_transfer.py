"""Reject false arrivals when Atlas instances share an identical map name."""
from pathlib import Path
import unittest

import character_transfer as transfer

NAME = 'TEST-37762'


def status(map_id):
    return f'{map_id} City_01_01.txt S: 2/3 Ip:127.0.0.1:{transfer.PORTS[map_id]} Mem: 0M Cpu:0\r\n'


def marker(epoch):
    return (f'COH_RESUME_ONLY_TRANSFER_UPDATE epoch={epoch} id=1 base_map=1 instance={2 if epoch == 1 else 1} '
            f'ip=127.0.0.1 port={7002 if epoch == 1 else 7001} name={NAME}\n')


def ownership(map_id):
    return {'loaded': True, 'connected': True, 'in_map_transfer': False,
            'map_id': map_id, 'static_map_id': map_id}


class TransferTests(unittest.TestCase):
    def test_pinned_clone_contract_and_manual_command_have_distinct_owned_port(self):
        proof = transfer.source_contract()
        self.assertEqual(proof['clone_map_id'], 101)
        self.assertEqual(proof['base_map_id'], 1)
        command = transfer.map_command(Path('runtime'))
        self.assertEqual(command[command.index('-map_id') + 1], '101')
        self.assertEqual(command[command.index('-udp') + 1], '7002')
        self.assertEqual(command[command.index('-tcp') + 1], '0')
        self.assertEqual(command[command.index('-idleExitTimeout') + 1], '0')
        self.assertNotIn('-preloadtransient', command)

    def test_ready_requires_exact_numeric_container_and_registered_port(self):
        for map_id in transfer.PORTS:
            self.assertTrue(transfer.ready(transfer.parse_map_status(status(map_id), map_id), map_id))
        clone = status(101)
        for wrong in (status(1), clone.replace('7002', '7001'), clone.replace('127.0.0.1', '192.0.2.1'),
                      clone.replace('City_01_01', 'City_02_01'), clone + clone, clone + status(1),
                      clone + 'SQLERROR: query failed\n', 'Status: Running\n'):
            with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                transfer.parse_map_status(wrong, 101)

    def test_baseline_must_distinguish_not_started_starting_and_absent(self):
        text = '101 maps/City_Zones/City_01_01/City_01_01.txt NotReady 1 (Not started) Info \n'
        self.assertTrue(transfer.parse_map_status(text, 101)['not_started'])
        starting = transfer.parse_map_status(status(101).rstrip() + ' NotReady 1\n', 101)
        self.assertFalse(starting['ready'])
        self.assertFalse(starting['not_started'])
        absent = transfer.parse_map_status('invalid container request\n', 101, allow_missing=True)
        self.assertFalse(absent['not_started'])
        for text in ('invalid container request\n', text.replace('101', '1'), text.replace('NotReady 1', 'NotReady 2')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                transfer.parse_map_status(text, 101)

    def test_roundtrip_epochs_bind_actual_player_and_peer_not_instance_number(self):
        first = transfer.accept_arrival(marker(1), 1, NAME, 1,
                                       transfer.parse_map_status(status(101), 101), ownership(101))
        second = transfer.accept_arrival(marker(1) + marker(2), 1, NAME, 2,
                                        transfer.parse_map_status(status(1), 1), ownership(1))
        self.assertEqual((first['map_id'], first['instance_number']), (101, 2))
        self.assertEqual((second['map_id'], second['instance_number']), (1, 1))
        self.assertFalse(first['instance_number_is_map_container_id'])
        self.assertEqual(transfer.updates('', 1, NAME), [])

    def test_duplicate_stale_foreign_or_wrong_peer_markers_never_establish_arrival(self):
        for text in (marker(1) * 2, marker(2), marker(1) + marker(2) + marker(2),
                     marker(1).replace('id=1 ', 'id=2 '), marker(1).replace('base_map=1', 'base_map=2'),
                     marker(1).replace('name=' + NAME, 'name=OTHER'), marker(1).replace('7002', '7001'),
                     marker(1).replace('127.0.0.1', '127.0.0.2'), marker(1).replace('instance=2', 'instance=-1'),
                     marker(1).replace('epoch=1 ', ''), marker(1) + 'COH_RESUME_ONLY_TRANSFER_UPDATE truncated\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                transfer.updates(text, 1, NAME)
        # The first successful arrival is stale evidence for the return leg.
        with self.assertRaisesRegex(ValueError, 'fresh processed update'):
            transfer.accept_arrival(marker(1), 1, NAME, 2,
                                    transfer.parse_map_status(status(1), 1), ownership(1))

    def test_exact_ownership_and_current_destination_heartbeat_are_required(self):
        map_sample = transfer.parse_map_status(status(101), 101)
        for mutation in ({'connected': False}, {'in_map_transfer': True}, {'map_id': 1},
                         {'static_map_id': 1}, {'loaded': False}):
            changed = dict(ownership(101), **mutation)
            self.assertFalse(transfer.connected(changed, 101))
            with self.assertRaises(ValueError):
                transfer.accept_arrival(marker(1), 1, NAME, 1, map_sample, changed)
        for mutation in ({'network_age_seconds': 21}, {'stats_age_seconds': 21}, {'ready': False},
                         {'map_id': 1}, {'port': 7001}, {'address': '192.0.2.1'}):
            changed = dict(map_sample, **mutation)
            self.assertFalse(transfer.ready(changed, 101))
            with self.assertRaises(ValueError):
                transfer.accept_arrival(marker(1), 1, NAME, 1, changed, ownership(101))


if __name__ == '__main__':
    unittest.main()
