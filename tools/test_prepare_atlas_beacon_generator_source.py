"""Finite host-only producer closure; gameplay algorithms remain immutable."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

import prepare_atlas_beacon_generator_source as producer


class AtlasBeaconSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.receipt = producer.expected()

    def test_source_scope_and_active_algorithms_are_exact(self):
        receipt = self.receipt
        self.assertEqual(set(receipt['source_sha256']), set(producer.FILES))
        self.assertEqual(set(receipt['patched_sha256']), set(producer.FILES))
        self.assertEqual(receipt['contract']['map_list_count'], 1)
        self.assertEqual(receipt['contract']['worker_count'], 1)
        self.assertFalse(receipt['contract']['shippable_gameplay_binary'])
        for name, digest in receipt['retained_algorithm_sha256'].items():
            self.assertEqual(producer.progress.sha256(producer.ROOT/'upstream/ouroboros'/name), digest)
        text = (producer.ROOT/'upstream/ouroboros/MapServer/src/beacon/beaconConnection.c').read_text()
        self.assertIn('void beaconProcessCombatBeacons(int doGenerate, int doProcess){\n    #if 0', text)

    def test_patch_contains_no_warning_suppression_and_has_real_readback(self):
        patch = (producer.ROOT/producer.PATCH).read_text()
        additions = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        for call in ('beaconDoesTheBeaconFileMatchTheMap(1)', 'beaconReload()', 'beaconPathFind(search',
                     'assert(paths == 32)'):
            self.assertIn(call, additions)
        self.assertIn('beaconSetPathFindEntity(NULL, 0)', additions)
        self.assertIn('groupLoadMap(freshMapName, 0, 0)', additions)
        self.assertIn('setvbuf(fileGetStdout(), NULL, _IONBF, 0)', additions)
        self.assertIn('fflush(fileGetStdout())', additions)
        self.assertNotIn('fflush(stdout)', additions)
        self.assertNotIn('setvbuf(stdout', additions)
        self.assertIn('COH_ATLAS_BEACON_VERIFY_ONLY', additions)
        self.assertIn('!beacon_server.isMasterServer && !beacon_server.isRequestServer && noNetStart', additions)
        self.assertNotIn('beaconCreatePathCheckEnt()', additions)
        self.assertNotIn('THIS MAP HAS NOT BEEN BEACONIZED', additions)
        self.assertNotIn('beaconProcessCombatBeacons(', additions)
        self.assertNotIn('RegReader', additions)

    def test_containment_patch_applies_without_changing_algorithm_files(self):
        with tempfile.TemporaryDirectory(prefix='coh-beacon-stage-test-') as temporary:
            stage = Path(temporary)
            for name in producer.FILES + producer.RETAINED:
                target = stage/name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((producer.ROOT/'upstream/ouroboros'/name).read_bytes())
            producer.apply_patch(stage, (producer.ROOT/producer.PATCH).read_bytes())
            for name, digest in self.receipt['patched_sha256'].items():
                self.assertEqual(producer.progress.sha256(stage/name), digest)
            for name, digest in self.receipt['retained_algorithm_sha256'].items():
                self.assertEqual(producer.progress.sha256(stage/name), digest)
            client = (stage/'MapServer/src/beacon/beaconClient.c').read_bytes().decode('latin1')
            startup = client[client.index("I'm not the sentry!!!"):]
            self.assertNotIn('checkForCorrectExePath(',startup)
            self.assertNotIn('beaconClientGetCmdLine(',startup)
            self.assertIn('Owned host beacon roles reject executable self-update',client)
            server=(stage/'MapServer/src/beacon/beaconServer.c').read_text()
            self.assertNotIn('checkForCorrectExePath(',server)
            self.assertIn('netInit(&beacon_server.clients, 0, portToTry)', server)
            self.assertNotIn('netInit(&beacon_server.clients, ipFromString(', server)


    def test_network_api_keeps_udp_disabled_and_accepted_loopback_policy(self):
        # The address-looking integer formerly supplied here was really a UDP
        # port: all four roles attempted the same unintended UDP listener.
        header = (producer.ROOT / 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/network/netio.h').read_text()
        self.assertIn('int netInit(NetLinkList *nlist,int udp_port,int tcp_port);', header)
        patch = (producer.ROOT / producer.PATCH).read_text()
        self.assertNotIn('+            if(netInit(', patch)
        contract = self.receipt['base']['game_build_input']['loopback_only']
        self.assertEqual(contract['environment_variable'], 'COH_GAME_LOOPBACK_ONLY')
        self.assertEqual(contract['enabled_value'], '1')
        self.assertEqual(contract['activation'], 'before_common_startup')
        self.assertEqual(contract['endpoint_verification'], 'getsockname_and_SO_TYPE_after_each_successful_bind')
        base = (producer.ROOT / 'patches/game-loopback/0001-game-loopback-bindings.patch').read_text()
        main = base.split('+++ b/MapServer/src/svr/svr_init.c', 1)[1].split('--- a/', 1)[0]
        self.assertLess(main.index('sockGameLoopbackInit()'), main.index('memCheckInit()'))
        for check in ('getsockname', 'getsockopt', 'SO_TYPE', 'htonl(INADDR_LOOPBACK)'):
            self.assertIn(check, base)

    def test_android_load_and_v9_freshness_do_not_depend_on_copied_mtimes(self):
        text = (producer.ROOT/'upstream/ouroboros/MapServer/src/beacon/beaconFile.c').read_text()
        reload = text.split('void beaconReload(void){', 1)[1].split('static S32 isFileTimeNewer', 1)[0]
        self.assertIn('readFile = readBeaconFile(beaconFileName)', reload)
        for forbidden in ('beaconFileIsUpToDate(', 'beaconFileMatchesMapCRC(', 'fileLastChanged(', '.date'):
            self.assertNotIn(forbidden, reload)
        matcher = text.split('static S32 beaconFileMatchesMapCRC(', 1)[1].split('S32 beaconFileIsUpToDate(', 1)[0]
        self.assertIn('if(version >= 9)', matcher)
        self.assertIn('crcMatches = fileCRC == beacon_process.fullMapCRC', matcher)
        freshness = text.split('S32 beaconFileIsUpToDate(', 1)[1].split('S32 beaconDoesTheBeaconFileMatchTheMap(', 1)[0]
        self.assertIn('else if(crcMatches)', freshness)
        self.assertIn('else if(0 && beaconIsFileNewerThanAllUsedFiles(', freshness)


if __name__ == '__main__': unittest.main()
