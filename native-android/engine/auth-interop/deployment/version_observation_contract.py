"""Bounded source-audited ServerMonitor version-body metadata; never a socket.

Caller must independently qualify NetLink/TCP framing, command extraction,
compression/debug mode, actual owned process and observation provenance.
"""
from dataclasses import dataclass
import hashlib
import ipaddress
import re
import subprocess
from source_audit import decoded,extract
from hosted_auth_stage import ORIGINAL_TREE

COMMAND=10
PORT=6996
SOURCE_PINS={
'upstream/ouroboros/DBServer/src/svrmoncomm.c':'ced7f25a46753264c6ee0778b0ec15f12b875dbf621cf3a65a4677cd3bdc0ee1',
'upstream/ouroboros/ServerMonitor/src/serverMonitorNet.c':'e5f35b0e192c3595215e8988527f71b54719534467b37018d05c3f0b53539e31',
'upstream/ouroboros/Common/comm_backend.h':'9af3a17854cc0c9a7e32e545bc563158b6a8538afd9e215f490f55574397f24c',
'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h':'116b3c4a4d4319893ddc0cd75a60722ec58c96a3dc066a74b1b92e12d925aea9',
'upstream/ouroboros/libs/UtilitiesLib/src/network/net_packet.c':'4c970280e323d50e4d2f36882b493a1b640df4b8d9b1192c72598315c8387039',
'upstream/ouroboros/libs/UtilitiesLib/src/components/BitStream.c':'69ebbcb2cba3bc47477b8edba60eea94329c4d56c56e6c11fdbd275c3b8fe0e4'}


def source_audit(root):
    git=lambda *args:subprocess.check_output(['git','-C',str(root),*args],timeout=30)
    if git('rev-parse','HEAD:upstream/ouroboros').decode().strip()!=ORIGINAL_TREE:raise ValueError('version_source_tree')
    values={}
    for name,pin in SOURCE_PINS.items():
        raw=git('show','HEAD:'+name)
        if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('version_source_blob')
        values[name]=decoded(raw)
    handler=extract(values['upstream/ouroboros/DBServer/src/svrmoncomm.c'],'svrMonHandleClientMsg')
    branch=handler.split('    case DBSVRMON_REQUESTVERSION:',1)[1].split('        break;',1)[0]
    enum=values['upstream/ouroboros/Common/comm_backend.h']
    body=enum.split('DBSVRMON_EXEC = COMM_MAX_CMD,',1)[1].split('};',1)[0]
    names=re.findall(r'^\s*(DBSVRMON_[A-Z_]+)\s*,',body,re.M)
    if 3+names.index('DBSVRMON_REQUESTVERSION')!=COMMAND:raise ValueError('version_command_source')
    if not re.search(r'COMM_MAX_CMD\s*=\s*2\s*,',values['upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h']):raise ValueError('version_command_base')
    if not re.search(r'#define DEFAULT_SVRMON_PORT\s+6996\b',enum):raise ValueError('version_port_source')
    functions={}
    for filename,name in [('DBServer/src/svrmoncomm.c','svrMonHandleClientMsg'),('DBServer/src/svrmoncomm.c','svrMonHandleConnect'),
                          ('DBServer/src/svrmoncomm.c','svrMonInit'),('ServerMonitor/src/serverMonitorNet.c','svrMonRequest'),
                          ('libs/UtilitiesLib/src/network/net_packet.c','pktSendString'),('libs/UtilitiesLib/src/components/BitStream.c','bsWriteString')]:
        functions[name]=hashlib.sha256(extract(values['upstream/ouroboros/'+filename],name).encode()).hexdigest()
    return {'schema':'coh-readonly-version-body-source-audit-v1','source_tree':ORIGINAL_TREE,'source_sha256':SOURCE_PINS,
            'function_sha256':functions,'version_branch_sha256':hashlib.sha256(branch.encode()).hexdigest(),
            'request_command':COMMAND,'server_monitor_port':PORT,'application_request_body_bits':0,
            'response_fields':['getCompatibleGameVersion()','getExecutablePatchVersion("CoH Server")'],
            'ordinary_connect_subscribes_full_updates':True,'version_branch_has_svrmon_ready_guard':False,
            'original_functions_executed':False,'transport_qualified':False,'actual_process_version_verified':False}


def generation(value):
    if type(value) is not str or not re.fullmatch('[a-f0-9]{64}',value):raise ValueError('owner_generation_label_required')
    return value


@dataclass(frozen=True)
class VersionRequestMetadata:
    owner_generation: str
    command: int=COMMAND
    port: int=PORT
    application_body_bits: int=0
    sends_monitor_connect: bool=False
    transport_qualified: bool=False
    live_channel_ownership_verified: bool=False


def declare_request(*,owner_generation,peer_ip,port,command=COMMAND):
    if type(peer_ip) is not str:raise ValueError('text_loopback_peer_required')
    try:loopback=ipaddress.IPv4Address(peer_ip).is_loopback
    except Exception:raise ValueError('loopback_ipv4_peer_required') from None
    if not loopback or type(port) is not int or port!=PORT or type(command) is not int or command!=COMMAND:
        raise ValueError('only_owned_loopback_version_request_profile')
    return VersionRequestMetadata(generation(owner_generation))


@dataclass(frozen=True)
class VersionBodyMetadata:
    compatible_version: str
    server_patch_version: str
    owner_generation: str
    source_tree: str=ORIGINAL_TREE
    transport_qualified: bool=False
    actual_process_version_verified: bool=False
    live_channel_ownership_verified: bool=False
    live_deployment_admitted: bool=False


def decode_body(data,*,start_bit,bit_count,command,has_debug_info,owner_generation):
    generation(owner_generation)
    if (type(data) is not bytes or type(start_bit) is not int or not 0<=start_bit<=7
            or type(bit_count) is not int or not 16<=bit_count<=1600 or bit_count%8
            or len(data)!=(start_bit+bit_count+7)//8 or type(command) is not int or command!=COMMAND
            or has_debug_info is not False):raise ValueError('bounded_untyped_version_body_required')
    # bsWriteString preserves the existing bit cursor and emits NUL-terminated
    # octets. NetLink command/framing and decompression are already excluded.
    position=start_bit;end=start_bit+bit_count;strings=[]
    for field in range(2):
        value=[]
        while True:
            if position+8>end:raise ValueError('truncated_version_string')
            byte=sum(((data[(position+i)//8]>>((position+i)%8))&1)<<i for i in range(8));position+=8
            if byte==0:break
            if not 32<=byte<=126 or len(value)>=99:raise ValueError('bounded_printable_version_required')
            value.append(byte)
        if not value:raise ValueError('nonempty_version_required')
        strings.append(bytes(value).decode('ascii'))
    if position!=end:raise ValueError('trailing_version_body')
    return VersionBodyMetadata(*strings,owner_generation)
