"""Independent source staging checks for the nonshippable map-5 producer."""
from pathlib import Path
import tempfile
import unittest
import prepare_kings_row_beacon_generator_source as producer


class KingsRowBeaconSourceTests(unittest.TestCase):
    def test_native_staging_retains_algorithms_and_rejects_incomplete_world(self):
        receipt=producer.expected()
        self.assertEqual(receipt['contract']['map_id'],5)
        self.assertEqual(receipt['contract']['map'],'maps/city_zones/city_01_02/city_01_02.txt')
        self.assertFalse(receipt['contract']['shippable_gameplay_binary'])
        self.assertFalse(receipt['contract']['native_worker_spawning_allowed'])
        with tempfile.TemporaryDirectory() as td:
            stage=Path(td)
            for name in set(producer.FILES).union(producer.atlas.FILES,producer.RETAINED):
                path=stage/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes((producer.ROOT/'upstream/ouroboros'/name).read_bytes())
            producer.apply_patch(stage,(producer.ROOT/producer.atlas.PATCH).read_bytes())
            producer.apply_patch(stage,(producer.ROOT/producer.PATCH).read_bytes())
            for name,digest in {**receipt['patched_sha256'],**receipt['retained_algorithm_sha256']}.items():
                self.assertEqual(producer.atlas.progress.sha256(stage/name),digest)
            server=(stage/'MapServer/src/beacon/beaconServer.c').read_text()
            self.assertNotIn('city_01_01',server)
            for call in ('groupLoadMap(freshMapName, 0, 0)','beaconDoesTheBeaconFileMatchTheMap(1)',
                         'beaconReload()','beaconPathFind(search','beaconHostRequire(paths == 32'):
                self.assertIn(call,server)
            self.assertLess(server.index('groupLoadMap(freshMapName'),server.index('COH_KINGS_ROW_COLLISION_LOAD_V1'))
            loader=(stage/'Common/group/groupfileload.c').read_text()
            for kind in ('group','root geometry','reference'):
                self.assertIn('Host Kings Row collision missing '+kind,loader)
            self.assertIn('COH_KINGS_ROW_BEACON_VERIFY_ONLY',server)

    def test_original_atlas_source_contract_remains_separate(self):
        base=producer.atlas.expected()
        self.assertEqual(base['contract']['map'],'maps/city_zones/city_01_01/city_01_01.txt')
        self.assertIn('Common/group/groupfileload.c',base['retained_algorithm_sha256'])
        self.assertNotIn('Common/group/groupfileload.c',producer.expected()['retained_algorithm_sha256'])


if __name__=='__main__':unittest.main()
