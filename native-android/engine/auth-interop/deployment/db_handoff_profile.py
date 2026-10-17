"""Source-qualified read-only declarations for a future isolated DB experiment.

None of these metadata functions establishes actual version-file contents,
process/channel provenance, shard activation or live DB login.
"""
from dataclasses import dataclass, field
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import subprocess

import checksum_candidate
from hosted_auth_stage import ORIGINAL_TREE

HERE=Path(__file__).resolve().parent
MASK_PAIR_SHA='3240c3554c8e03d0261af6a44319e213fa8fe72eceb8df7c811efe48d882a195'
MASK_RECEIPT_SHA='3ae6063187ae803cc84caf0e416f9cc9574054964517aeab742588b52a174264'


@dataclass(frozen=True)
class SourceAuthMasks:
    source_tree: str
    auth_mask: bytes = field(repr=False)
    db_mask: bytes = field(repr=False)
    overlapping_source_bits: int
    source_receipt_sha256: str


def load_source_masks(root):
    path=HERE.parent/'evidence/db-handoff-profile-contract-20261017/auth-bit-merge.json'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=MASK_RECEIPT_SHA:
        raise ValueError('auth_mask_receipt_identity')
    value=json.loads(path.read_text())
    if value.get('passed') is not True or value.get('source_tree')!=ORIGINAL_TREE:
        raise ValueError('auth_mask_receipt_scope')
    for name,expected in value['source_sha256'].items():
        data=subprocess.check_output(['git','-C',str(root),'show','HEAD:'+name],timeout=30)
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('auth_mask_original_source_changed')
    auth=bytes.fromhex(value['auth_mask_hex']);db=bytes.fromhex(value['db_mask_hex'])
    if len(auth)!=128 or len(db)!=128:raise ValueError('auth_mask_size')
    overlap=sum((a&b).bit_count() for a,b in zip(auth,db))
    if overlap!=31:raise ValueError('auth_mask_overlap_identity')
    return SourceAuthMasks(ORIGINAL_TREE,auth,db,overlap,MASK_RECEIPT_SHA)


def merge_source_auth_data(auth_data,game_data,masks):
    if not isinstance(masks,SourceAuthMasks) or masks.source_receipt_sha256!=MASK_RECEIPT_SHA or masks.source_tree!=ORIGINAL_TREE:
        raise ValueError('qualified_auth_mask_contract_required')
    if (type(masks.auth_mask) is not bytes or type(masks.db_mask) is not bytes
            or len(masks.auth_mask)!=128 or len(masks.db_mask)!=128 or masks.overlapping_source_bits!=31
            or hashlib.sha256(masks.auth_mask+masks.db_mask).hexdigest()!=MASK_PAIR_SHA):
        raise ValueError('qualified_auth_mask_bytes_required')
    if not isinstance(auth_data,bytes) or not isinstance(game_data,bytes) or len(auth_data)!=128 or len(game_data)!=128:
        raise ValueError('auth_game_data_exact_128_required')
    # Original ownership masks overlap in 31 places. Preserve the original OR;
    # do not invent an exclusive owner or overwrite precedence for those bits.
    return bytes((a&am)|(g&gm) for a,g,am,gm in zip(auth_data,game_data,masks.auth_mask,masks.db_mask))


@dataclass(frozen=True)
class DeclaredNondevelopmentPolicy:
    compatible_version: str
    reference_md5: bytes = field(repr=False)
    reference_file_sha256: str
    version_provider_source_sha256: str
    checksum_candidate_function_sha256: str
    metadata_matches: bool = True
    actual_version_result_verified: bool = False
    deployed_dbserver_binary_verified: bool = False
    live_deployment_admitted: bool = False


def declare_nondevelopment_policy(*,fake_auth,compatible_version,client_version,client_skip_version,
                                 reference_md5,client_md5,reference_file_sha256,version_provider_source_sha256,
                                 checksum_candidate_function_sha256):
    if fake_auth is not False or type(client_skip_version) is not bool:
        raise ValueError('nondevelopment_real_auth_required')
    for version in (compatible_version,client_version):
        if not isinstance(version,str) or not 1<=len(version)<=99 or any(ord(c)<32 or ord(c)>126 for c in version):
            raise ValueError('bounded_normal_version_required')
    if compatible_version.lower().startswith('dev'):
        raise ValueError('development_version_not_nondevelopment_profile')
    if compatible_version.lower()!=client_version.lower():
        raise ValueError('normal_version_mismatch_even_when_client_requests_skip')
    for digest in (reference_file_sha256,version_provider_source_sha256):
        if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):
            raise ValueError('source_bound_reference_and_version_required')
    if checksum_candidate_function_sha256!=hashlib.sha256(checksum_candidate.CANDIDATE.encode()).hexdigest():
        raise ValueError('full_16_byte_failclosed_candidate_required')
    if (not isinstance(reference_md5,bytes) or not isinstance(client_md5,bytes) or len(reference_md5)!=16
            or len(client_md5)!=16 or reference_md5==bytes(16) or client_md5!=reference_md5):
        raise ValueError('full_16_byte_reference_match_required')
    return DeclaredNondevelopmentPolicy(compatible_version,reference_md5,reference_file_sha256,
                                       version_provider_source_sha256,checksum_candidate_function_sha256)


@dataclass(frozen=True)
class ShardMetadata:
    shard_id: int
    inner_ip: str
    outer_ip: str
    client_port: int
    owner_generation: str


@dataclass(frozen=True)
class DeclaredShardChannel:
    shard_id: int
    matched_shard_metadata: bool = True
    live_channel_ownership_verified: bool = False
    shard_activation_verified: bool = False
    live_deployment_admitted: bool = False


def declare_shard_channel(rows,*,socket_peer_ip,observed_shard_id,owner_generation,allow_unknown_servers,
                          game_server_specifies_id):
    if allow_unknown_servers is not False or game_server_specifies_id is not False:
        raise ValueError('explicit_address_matched_shard_profile_required')
    if not isinstance(owner_generation,str) or not re.fullmatch('[0-9a-f]{64}',owner_generation):
        raise ValueError('owned_channel_generation_required')
    if not isinstance(rows,tuple) or not rows or len(rows)>16 or any(not isinstance(row,ShardMetadata) for row in rows):
        raise ValueError('bounded_shard_metadata_required')
    if type(observed_shard_id) is not int or not 1<=observed_shard_id<=255:
        raise ValueError('valid_observed_shard_id_required')
    ids=set();addresses=set()
    for row in rows:
        if type(row.shard_id) is not int or not 1<=row.shard_id<=255 or type(row.client_port) is not int or not 1<=row.client_port<=65535 or row.owner_generation!=owner_generation:
            raise ValueError('shard_metadata_identity_or_generation')
        for address in (row.inner_ip,row.outer_ip):
            if type(address) is not str:raise ValueError('shard_ipv4_text_required')
            try:parsed=ipaddress.IPv4Address(address)
            except Exception:raise ValueError('shard_ipv4_metadata') from None
            if not parsed.is_loopback:raise ValueError('isolated_shard_loopback_required')
        if row.shard_id in ids or row.inner_ip in addresses:raise ValueError('ambiguous_shard_address_or_id')
        ids.add(row.shard_id);addresses.add(row.inner_ip)
    matches=[row for row in rows if row.inner_ip==socket_peer_ip and row.shard_id==observed_shard_id]
    if len(matches)!=1:raise ValueError('shard_socket_metadata_mismatch')
    return DeclaredShardChannel(observed_shard_id)
