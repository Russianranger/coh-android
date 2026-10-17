import dataclasses
import hashlib
from pathlib import Path
import unittest

import checksum_candidate
import db_handoff_profile as p

ROOT=Path(__file__).resolve().parents[4]


class ProfileTests(unittest.TestCase):
    def policy(self,**changes):
        args=dict(fake_auth=False,compatible_version='isolated-normal-1',client_version='ISOLATED-NORMAL-1',
                  client_skip_version=False,reference_md5=b'0123456789abcdef',client_md5=b'0123456789abcdef',
                  reference_file_sha256='a'*64,version_provider_source_sha256='b'*64,
                  checksum_candidate_function_sha256=hashlib.sha256(checksum_candidate.CANDIDATE.encode()).hexdigest())
        args.update(changes);return p.declare_nondevelopment_policy(**args)

    def test_normal_policy_is_metadata_only_and_immutable(self):
        result=self.policy(client_skip_version=True)
        self.assertTrue(result.metadata_matches)
        self.assertFalse(result.actual_version_result_verified)
        self.assertFalse(result.deployed_dbserver_binary_verified)
        self.assertFalse(result.live_deployment_admitted)
        self.assertNotIn('0123456789abcdef',repr(result))
        with self.assertRaises(dataclasses.FrozenInstanceError):result.metadata_matches=False

    def test_refusal_matrix(self):
        for changes in (dict(fake_auth=True),dict(fake_auth=0),dict(compatible_version='dev: isolated'),
                        dict(client_version='wrong',client_skip_version=True),dict(client_md5=bytes(16)),
                        dict(reference_md5=bytes(16),client_md5=bytes(16)),dict(client_md5=b'a'*15),
                        dict(client_md5=bytearray(b'0123456789abcdef')),dict(reference_file_sha256=''),
                        dict(version_provider_source_sha256='G'*64),dict(checksum_candidate_function_sha256='a'*64),
                        dict(compatible_version='a'*100),dict(client_version='a\n'),dict(client_skip_version=1)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.policy(**changes)
        for bit in range(128):
            data=bytearray(b'0123456789abcdef');data[bit//8]^=1<<(bit%8)
            with self.subTest(bit=bit),self.assertRaises(ValueError):self.policy(client_md5=bytes(data))

    def test_source_masks_all_bits_and_forgery(self):
        masks=p.load_source_masks(ROOT)
        self.assertEqual(masks.overlapping_source_bits,31)
        for bit in range(1024):
            a=bytearray(128);a[bit//8]=1<<(bit%8);data=bytes(a)
            self.assertEqual(p.merge_source_auth_data(data,bytes(128),masks),bytes(x&y for x,y in zip(data,masks.auth_mask)))
            self.assertEqual(p.merge_source_auth_data(bytes(128),data,masks),bytes(x&y for x,y in zip(data,masks.db_mask)))
        for field,value in (('auth_mask',bytes(128)),('db_mask',b'x'),('overlapping_source_bits',0),('source_receipt_sha256','a'*64)):
            with self.assertRaises(ValueError):p.merge_source_auth_data(bytes(128),bytes(128),dataclasses.replace(masks,**{field:value}))
        for a,b in ((b'',bytes(128)),(bytes(128),bytes(129)),(bytearray(128),bytes(128))):
            with self.assertRaises(ValueError):p.merge_source_auth_data(a,b,masks)
        self.assertNotIn(masks.auth_mask.hex(),repr(masks))

    def channel(self,rows=None,**changes):
        if rows is None:rows=(p.ShardMetadata(1,'127.0.0.1','127.0.0.1',7002,'c'*64),)
        args=dict(socket_peer_ip='127.0.0.1',observed_shard_id=1,owner_generation='c'*64,
                  allow_unknown_servers=False,game_server_specifies_id=False)
        args.update(changes);return p.declare_shard_channel(rows,**args)

    def test_channel_metadata_only(self):
        result=self.channel()
        self.assertTrue(result.matched_shard_metadata)
        self.assertFalse(result.live_channel_ownership_verified)
        self.assertFalse(result.shard_activation_verified)
        self.assertFalse(result.live_deployment_admitted)
        with self.assertRaises(dataclasses.FrozenInstanceError):result.shard_id=2

    def test_channel_ambiguous_unowned_unknown_refusals(self):
        row=p.ShardMetadata(1,'127.0.0.1','127.0.0.1',7002,'c'*64)
        for changes in (dict(allow_unknown_servers=True),dict(game_server_specifies_id=True),
                        dict(socket_peer_ip='127.0.0.2'),dict(observed_shard_id=2),dict(observed_shard_id=True),
                        dict(owner_generation='d'*64),dict(owner_generation='unowned')):
            with self.assertRaises(ValueError):self.channel(**changes)
        for rows in ((),[row],(row,row),(row,dataclasses.replace(row,shard_id=2)),
                     (dataclasses.replace(row,inner_ip='0.0.0.0'),),(dataclasses.replace(row,outer_ip='10.0.0.1'),),
                     (dataclasses.replace(row,client_port=0),),(dataclasses.replace(row,shard_id=256),),
                     (dataclasses.replace(row,inner_ip='::1'),),(dataclasses.replace(row,inner_ip=2130706433),),tuple([row]*17)):
            with self.assertRaises(ValueError):self.channel(rows)

if __name__=='__main__':unittest.main()
