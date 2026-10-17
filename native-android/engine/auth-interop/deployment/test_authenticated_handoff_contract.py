"""Bounded original packet-body fixtures only; no live auth or deployment."""
from dataclasses import FrozenInstanceError
import struct
import unittest

import authenticated_handoff_contract as stage

GEN='a'*64

def about(account=b'sourcefixture',uid=900001):
    return b'\0'+struct.pack('<I',uid)+account+b'\0'+struct.pack('<III',0,2,3)+bytes(range(128))+struct.pack('<III',1,123,456)


class HandoffContractTests(unittest.TestCase):
    def test_complete_metadata_identity_matches_without_admitting_session(self):
        data=stage.parse_about_to_play(about(),GEN)
        game=stage.parse_game_data(b'\x07'+struct.pack('<I',900001)+bytes(128),GEN)
        db=stage.parse_db_play_ok(b'\0'+struct.pack('<II',900001,0),GEN)
        client=stage.parse_client_play_ok(b'\x07'+struct.pack('<IIB',0,900001,3),GEN)
        proof=stage.match_handoff(data,game,db,client,expected_auth_id=900001,expected_shard_id=3,live_source_generation=GEN)
        self.assertTrue(proof['matched_observation_records']);self.assertFalse(proof['authenticated_db_login_verified'])
        self.assertFalse(proof['auth_bit_ownership_merge_verified']);self.assertFalse(proof['live_message_order_verified'])
        self.assertIsNone(proof['selected_character_dbid']);self.assertFalse(proof['cookie_minted'])
        self.assertNotIn('sourcefixture',repr(data));self.assertNotIn('cookie=',repr(client))
        with self.assertRaises(FrozenInstanceError):db.cookie=123

    def test_current_auth_only_profile_is_not_db_handoff_profile(self):
        with self.assertRaises(ValueError):stage.require_original_db_profile(user_data=False,queue_mode=False,queue_level=False)
        for key in ('queue_mode','queue_level'):
            args={'user_data':True,'queue_mode':False,'queue_level':False};args[key]=True
            with self.assertRaises(ValueError):stage.require_original_db_profile(**args)
        self.assertFalse(stage.require_original_db_profile(user_data=True,queue_mode=False,queue_level=False)['live_deployment_admitted'])

    def test_every_truncated_or_extra_about_to_play_refused(self):
        payload=about()
        for at in range(len(payload)):
            with self.assertRaises(ValueError,msg=str(at)):stage.parse_about_to_play(payload[:at],GEN)
        with self.assertRaises(ValueError):stage.parse_about_to_play(payload+b'x',GEN)
        for name in (b'',b' '*14,b'x'*15,b'\xff',b'x\t'):
            with self.assertRaises(ValueError):stage.parse_about_to_play(about(name),GEN)
        with self.assertRaises(ValueError):stage.parse_about_to_play(about(uid=0),GEN)
        for name in (b'x',b'x'*14):self.assertEqual(stage.parse_about_to_play(about(name),GEN).account,name.decode())
        self.assertEqual(stage.parse_about_to_play(about(b'Name   '),GEN).account,'Name')

    def test_fixed_replies_truncation_opcode_and_zero_identity_refused(self):
        packets=[(stage.parse_game_data,b'\x07'+struct.pack('<I',900001)+bytes(128)),
                 (stage.parse_db_play_ok,b'\0'+struct.pack('<II',900001,123)),
                 (stage.parse_client_play_ok,b'\x07'+struct.pack('<IIB',123,900001,3))]
        for parser,packet in packets:
            for at in range(len(packet)):
                with self.assertRaises(ValueError):parser(packet[:at],GEN)
            with self.assertRaises(ValueError):parser(packet+b'x',GEN)
            with self.assertRaises(ValueError):parser(bytes([99])+packet[1:],GEN)
        with self.assertRaises(ValueError):stage.parse_db_play_ok(b'\0'+bytes(8),GEN)
        with self.assertRaises(ValueError):stage.parse_client_play_ok(b'\x07'+struct.pack('<IIB',1,900001,0),GEN)

    def test_wrong_uid_cookie_shard_and_generation_never_match(self):
        data=stage.parse_about_to_play(about(),GEN)
        game=stage.parse_game_data(b'\x07'+struct.pack('<I',900001)+bytes(128),GEN)
        db=stage.parse_db_play_ok(b'\0'+struct.pack('<II',900001,123),GEN)
        for uid,cookie,shard,generation in ((900002,123,3,GEN),(900001,124,3,GEN),(900001,123,4,GEN),(900001,123,3,'b'*64)):
            client=stage.parse_client_play_ok(b'\x07'+struct.pack('<IIB',cookie,uid,shard),generation)
            with self.assertRaises(ValueError):stage.match_handoff(data,game,db,client,expected_auth_id=900001,expected_shard_id=3,live_source_generation=GEN)
        for generation in ('',None,'historical','A'*64):
            with self.assertRaises(ValueError):stage.parse_about_to_play(about(),generation)


if __name__=='__main__':unittest.main()
