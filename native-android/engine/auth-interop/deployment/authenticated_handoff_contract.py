"""Bounded read-only original Auth/DB handoff grammar, without a live session.

Bodies are already decrypted/deframed by their owning transport. These functions
never generate cookies, send packets, register shards or admit a deployment.
"""
from dataclasses import dataclass, field
import re
import struct

SOURCE_TREE='f634e21e230009fa8edc91d15429cd4da69eee8c'
AUTH_BYTES=128
MAX_ACCOUNT_LEN=14


@dataclass(frozen=True)
class AboutToPlay:
    source_generation: str
    auth_id: int
    account: str = field(repr=False)
    time_remaining: int
    login_flags: int
    warning_flags: int
    auth_data: bytes = field(repr=False)
    pay_stat: int
    loyalty: int
    loyalty_legacy: int


@dataclass(frozen=True)
class GameData:
    source_generation: str
    auth_id: int
    game_data: bytes = field(repr=False)


@dataclass(frozen=True)
class DBPlayOK:
    source_generation: str
    auth_id: int
    cookie: int = field(repr=False)


@dataclass(frozen=True)
class ClientPlayOK:
    source_generation: str
    auth_id: int
    cookie: int = field(repr=False)
    shard_id: int


def generation(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):
        raise ValueError('live_handoff_generation_required')
    return value


def require_original_db_profile(*,user_data,queue_mode,queue_level):
    if user_data is not True or queue_mode is not False or queue_level is not False:
        raise ValueError('db_handoff_requires_full_nonqueue_userdata')
    return {'source_tree':SOURCE_TREE,'auth_data_bytes':AUTH_BYTES,'producer_format':'cdsdddbddd',
            'live_deployment_admitted':False}


def parse_about_to_play(body,source_generation):
    generation(source_generation)
    if not isinstance(body,bytes) or not 159<=len(body)<=172 or body[0]!=0:
        raise ValueError('about_to_play_body_bound')
    auth_id=struct.unpack_from('<I',body,1)[0]
    end=body.find(b'\0',5,5+MAX_ACCOUNT_LEN+1)
    if auth_id==0 or end<6 or len(body)!=end+1+12+AUTH_BYTES+12:
        raise ValueError('about_to_play_identity_or_shape')
    account=body[5:end]
    if any(x<32 or x>126 for x in account) or not account.rstrip(b' '):
        raise ValueError('about_to_play_account_bound')
    remaining,login,warn=struct.unpack_from('<III',body,end+1)
    at=end+13;data=body[at:at+AUTH_BYTES];pay,loyalty,legacy=struct.unpack_from('<III',body,at+AUTH_BYTES)
    return AboutToPlay(source_generation,auth_id,account.decode('ascii').rstrip(' '),remaining,login,warn,data,pay,loyalty,legacy)


def parse_game_data(body,source_generation):
    generation(source_generation)
    if not isinstance(body,bytes) or len(body)!=133 or body[0]!=7:
        raise ValueError('game_data_body_shape')
    uid=struct.unpack_from('<I',body,1)[0]
    if not uid:raise ValueError('game_data_zero_uid')
    return GameData(source_generation,uid,body[5:])


def parse_db_play_ok(body,source_generation):
    generation(source_generation)
    if not isinstance(body,bytes) or len(body)!=9 or body[0]!=0:
        raise ValueError('db_play_ok_body_shape')
    uid,cookie=struct.unpack_from('<II',body,1)
    if not uid:raise ValueError('db_play_ok_zero_uid')
    # Original consumer accepts an exact matching U32 cookie, including zero.
    return DBPlayOK(source_generation,uid,cookie)


def parse_client_play_ok(body,source_generation):
    generation(source_generation)
    if not isinstance(body,bytes) or len(body)!=10 or body[0]!=7:
        raise ValueError('client_play_ok_body_shape')
    cookie,uid,shard=struct.unpack_from('<IIB',body,1)
    if not uid or not shard:raise ValueError('client_play_ok_identity')
    return ClientPlayOK(source_generation,uid,cookie,shard)


def match_handoff(about,game_data,db_reply,client_reply,*,expected_auth_id,expected_shard_id,live_source_generation):
    """Check already-observed immutable records; this is not session admission."""
    generation(live_source_generation)
    if type(expected_auth_id) is not int or not 1<=expected_auth_id<=0xffffffff or type(expected_shard_id) is not int or not 1<=expected_shard_id<=255:
        raise ValueError('expected_live_identity_required')
    if not isinstance(about,AboutToPlay) or not isinstance(game_data,GameData) or not isinstance(db_reply,DBPlayOK) or not isinstance(client_reply,ClientPlayOK):
        raise ValueError('handoff_record_types')
    if any(x.source_generation!=live_source_generation for x in (about,game_data,db_reply,client_reply)):
        raise ValueError('handoff_generation_mismatch')
    if any(x.auth_id!=expected_auth_id for x in (about,game_data,db_reply,client_reply)) or client_reply.shard_id!=expected_shard_id or db_reply.cookie!=client_reply.cookie:
        raise ValueError('handoff_identity_mismatch')
    return {'source_tree':SOURCE_TREE,'matched_observation_records':True,'authenticated_db_login_verified':False,
            'selected_character_dbid':None,'live_deployment_admitted':False,'cookie_minted':False,'auth_bit_ownership_merge_verified':False,'live_message_order_verified':False}
