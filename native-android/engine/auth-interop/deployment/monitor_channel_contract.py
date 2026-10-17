"""Immutable process/channel/handshake metadata matching, never OS evidence.

Constructors and matching labels cannot authenticate a process or make a live
permit. An independently qualified owned-process/socket observer is still needed.
"""
from dataclasses import dataclass
import ipaddress
from version_observation_contract import generation


@dataclass(frozen=True)
class ProcessMetadata:
    owner_generation: str
    pid: int
    start_identity_sha256: str
    binary_sha256: str
    observed_ms: int
    alive: bool


@dataclass(frozen=True)
class ChannelMetadata:
    owner_generation: str
    owner_pid: int
    owner_start_identity_sha256: str
    listener_ip: str
    listener_port: int
    local_ip: str
    local_port: int
    peer_ip: str
    peer_port: int
    transport: str


@dataclass(frozen=True)
class HandshakeMetadata:
    owner_generation: str
    direction: str
    control_command: int
    observed_ms: int


@dataclass(frozen=True)
class MatchedMonitorMetadata:
    owner_generation: str
    pid: int
    process_labels_match: bool=True
    channel_labels_match: bool=True
    handshake_sequence_matches: bool=True
    sends_monitor_connect: bool=False
    actual_process_ownership_verified: bool=False
    actual_socket_ownership_verified: bool=False
    actual_netlink_handshake_verified: bool=False
    live_request_permit: bool=False


def bounded_int(value,lower,upper):
    return type(value) is int and lower<=value<=upper


def match_metadata(before,after,channel,events,*,requested_network_version,negotiated_network_version,
                   required_encryption,server_ack_encryption):
    if not isinstance(before,ProcessMetadata) or not isinstance(after,ProcessMetadata) or not isinstance(channel,ChannelMetadata):
        raise ValueError('typed_owned_channel_metadata_required')
    generation(before.owner_generation)
    for process in (before,after):
        generation(process.start_identity_sha256);generation(process.binary_sha256)
        if not bounded_int(process.pid,1,2**32-1) or not bounded_int(process.observed_ms,0,2**63-1) or process.alive is not True:
            raise ValueError('bounded_live_process_labels_required')
    if ((before.owner_generation,before.pid,before.start_identity_sha256,before.binary_sha256)
            !=(after.owner_generation,after.pid,after.start_identity_sha256,after.binary_sha256)):
        raise ValueError('process_generation_pid_start_or_binary_mismatch')
    if (channel.owner_generation!=before.owner_generation or channel.owner_pid!=before.pid
            or type(channel.owner_pid) is not int or channel.owner_start_identity_sha256!=before.start_identity_sha256
            or channel.transport!='TCP' or type(channel.listener_port) is not int or channel.listener_port!=6996
            or type(channel.local_port) is not int or channel.local_port!=6996 or not bounded_int(channel.peer_port,1,65535)):
        raise ValueError('owned_server_channel_label_mismatch')
    for value in (channel.listener_ip,channel.local_ip,channel.peer_ip):
        if type(value) is not str:raise ValueError('loopback_ipv4_channel_labels_required')
        try:valid=ipaddress.IPv4Address(value).is_loopback
        except Exception:valid=False
        if not valid:raise ValueError('loopback_ipv4_channel_labels_required')
    if channel.listener_ip!=channel.local_ip:raise ValueError('listener_connection_address_mismatch')
    if type(requested_network_version) is not int or requested_network_version!=5 or type(negotiated_network_version) is not int or negotiated_network_version!=5:
        raise ValueError('explicit_network5_no_fallback_profile_required')
    if type(required_encryption) is not bool or type(server_ack_encryption) is not bool or (required_encryption and not server_ack_encryption):
        raise ValueError('declared_encryption_requirement_mismatch')
    if not isinstance(events,tuple) or len(events)!=4:raise ValueError('exact_four_control_observations_required')
    expected=(('outbound',1),('inbound',2),('outbound',3),('inbound',4));last=before.observed_ms
    for event,(direction,command) in zip(events,expected):
        if (not isinstance(event,HandshakeMetadata) or event.owner_generation!=before.owner_generation
                or event.direction!=direction or type(event.control_command) is not int or event.control_command!=command
                or not bounded_int(event.observed_ms,last,2**63-1)):
            raise ValueError('control_handshake_order_generation_or_time_mismatch')
        last=event.observed_ms
    if after.observed_ms<last or after.observed_ms-before.observed_ms>15000:
        raise ValueError('bounded_process_observation_window_required')
    return MatchedMonitorMetadata(before.owner_generation,before.pid)
