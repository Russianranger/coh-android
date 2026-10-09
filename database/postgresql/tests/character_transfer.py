"""Source-bound acceptance for an Atlas Park clone round trip.

MapName is identical for both servers. Container IDs, character ownership and
actual client peer endpoints must therefore agree independently. No runtime
configuration or immutable map definitions are rewritten by this helper.
"""
import re
import socket

import run_one_map as one_map
from run_generated_schema import ROOT, require, sha256

HOME_ID, CLONE_ID = 1, 101
PORTS = {HOME_ID: 7001, CLONE_ID: 7002}
MARKER = 'COH_RESUME_ONLY_TRANSFER_UPDATE'
PROOF = {'schema_version': 1, 'marker': MARKER, 'epoch': 'successful_doMapXfer',
         'endpoint': 'connected_peer', 'readiness': 'processed_SERVER_UPDATE',
         'identity': 'initial_received_player_entity'}


def source_contract(root=ROOT):
    maps = root / 'upstream/i24/data/server/db/maps.db'
    text = maps.read_text()
    clones = re.findall(r'^Container 101\s*\n(.*?)^ContainerEnd\s*$', text, re.M | re.S)
    require(len(clones) == 1 and
            re.findall(r'^\s*(\S+)\s+(\S+)\s*$', clones[0], re.M) ==
            [('BaseMapID', '1'), ('DontAutoStart', '1'), ('Transient', '1')],
            'Pinned Atlas clone101 definition changed')
    paths = {
        'DBServer/src/dbinit.c': ('map_con->is_static = 1;', 'map_con->base_map_id',
                                'strcpy(map_con->map_name, base_map->map_name);'),
        'DBServer/src/status.c': ('container->id,getFileName(container->map_name)',
                                'container->map_id,container->static_map_id,'),
        'DBServer/src/mapxfer.c': ('ent_con->static_map_id = dest_map_id;',),
        'MapServer/src/cmdparse/cmdserver.c': ('xcase SCMD_MAPMOVE:',
                                            'dbAsyncMapMove(client->entity,map_id,NULL,XFER_STATIC);'),
        'MapServer/src/dbcomm/dbmapxfer.c': ('svrSendEntListToDb(&e,1);', 'DBCLIENT_MAP_XFER'),
        'MapServer/src/container/containercallbacks.c': ('if (!ci->is_map_xfer && !ci->demand_loaded)',
                                                        'e->login_count++;'),
        'MapServer/src/svr/svr_init.c': ('"-map_id"', '"-udp"', '"-idleExitTimeout"'),
        'MapServer/src/svr/svr_player.c': ('server_state.idle_exit_timeout > 0 || server_state.preload_transient',),
        'MapServer/src/dbcomm/staticMapInfo.c': ('db_state.base_map_id = info->baseMapID;',),
        'MapServer/src/group/groupnetsend.c': ('pktSendBitsPack(pak, 1, db_state.base_map_id);',),
        'Utilities/TestClient/src/externs.c': ('void worldReceiveGroups(Packet *pak)',
                                            'game_state.base_map_id = pktGetBitsPack(pak, 1);'),
    }
    for path, fragments in paths.items():
        source = (root / 'upstream/ouroboros' / path).read_text()
        require(all(fragment in source for fragment in fragments), 'Reviewed transfer source contract changed: ' + path)
    return {'home_map_id': HOME_ID, 'clone_map_id': CLONE_ID, 'base_map_id': 1,
            'map_path': one_map.MAP_PATH, 'udp_ports': {str(k): v for k, v in PORTS.items()},
            'maps_db_sha256': sha256(maps),
            'source_sha256': {path: sha256(root / 'upstream/ouroboros' / path) for path in paths},
            'scope': 'Two manually owned static instances of the same Atlas map; no door or different-zone asset validation',
            'login_count_scope': 'Ordinary resume adds one login; is_map_xfer suppresses further increments',
            'save_scope': 'Transfer sends an ordinary entity update; independent committed SQL is still required'}


def preflight_clone_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind(('0.0.0.0', PORTS[CLONE_ID]))
        except OSError as error:
            raise ValueError('Atlas clone UDP7002 is already occupied') from error
    return {'service': 'atlas_clone_client', 'protocol': 'UDP', 'port': PORTS[CLONE_ID],
            'available_before_start': True}


def map_command(runtime):
    return [str(runtime / 'MapServer.exe'), '-nogui', '-db', '127.0.0.1',
            '-nosharedmemory', '-nostats', '-udp', str(PORTS[CLONE_ID]), '-tcp', '0',
            '-map_id', str(CLONE_ID), '-idleExitTimeout', '0']


def parse_map_status(text, map_id, allow_missing=False):
    require(map_id in PORTS and type(map_id) is int, 'Unreviewed transfer map ID')
    require(not one_map.diagnostic_failures(text), 'Transfer map query emitted failure diagnostics')
    missing = [line for line in text.splitlines() if line.strip() == 'invalid container request']
    candidates = [match.groups() for line in text.splitlines() if
                  (match := re.fullmatch(r'\s*(\d+)\s+(\S+)\s+((?:NotReady|S:).*)', line))]
    if missing:
        require(allow_missing and len(missing) == 1 and not candidates, 'Unexpected or ambiguous missing transfer map')
        return {'map_id': map_id, 'ready': False, 'not_started': False, 'missing': True}
    require(len(candidates) == 1 and int(candidates[0][0]) == map_id,
            'Transfer map status lacks the exact requested numeric container ID')
    _, name, fields = candidates[0]
    require(name.replace('\\', '/').split('/')[-1].casefold() == one_map.BASE_NAME.casefold(),
            'Transfer map status names a different map asset')
    raw = ' '.join(candidates[0])
    if 'NotReady' in fields:
        require('NotReady 1' in fields, 'Unknown transfer not-ready status')
        return {'map_id': map_id, 'ready': False, 'not_started': '(Not started)' in fields, 'raw': raw}
    match = re.match(r'S:\s*(\d+)\s*/\s*(\d+)\s+Ip:\s*([0-9.]+):(\d+)\s+Mem:', fields)
    require(match is not None, 'Malformed transfer map ready response')
    network_age, stats_age, address, port = match.groups()
    require(address == '127.0.0.1' and int(port) == PORTS[map_id],
            'Transfer map endpoint does not match the owned destination')
    return {'map_id': map_id, 'ready': True, 'network_age_seconds': int(network_age),
            'stats_age_seconds': int(stats_age), 'address': address, 'port': int(port), 'raw': raw}


def ready(sample, map_id):
    return (sample.get('map_id') == map_id and sample.get('ready') is True and
            sample.get('address') == '127.0.0.1' and sample.get('port') == PORTS[map_id] and
            all(type(sample.get(key)) is int and 0 <= sample[key] <= 20
                for key in ('network_age_seconds', 'stats_age_seconds')))


def connected(sample, map_id):
    return (sample.get('loaded') is True and sample.get('connected') is True and
            sample.get('in_map_transfer') is False and sample.get('map_id') == map_id and
            sample.get('static_map_id') == map_id)


def updates(text, identifier, name):
    """Reject duplicate/skipped epochs, foreign identity and invented endpoints."""
    result = []
    for line in text.splitlines():
        if not line.startswith(MARKER):
            continue
        match = re.fullmatch(re.escape(MARKER) +
            r' epoch=(\d+) id=(\d+) base_map=(\d+) instance=(\d+) ip=([0-9.]+) port=(\d+) name=(.+)', line)
        require(match is not None, 'Malformed processed transfer update diagnostic')
        epoch, actual_id, base_map, instance, ip, port, actual_name = match.groups()
        epoch, actual_id, base_map, instance, port = map(int, (epoch, actual_id, base_map, instance, port))
        require(epoch == len(result) + 1 and epoch in (1, 2), 'Duplicate, skipped or extra transfer epoch')
        require(type(identifier) is int and identifier > 0 and actual_id == identifier and actual_name == name,
                'Transfer update returned a different player database ID/name')
        require(base_map == HOME_ID and ip == '127.0.0.1' and port == PORTS[CLONE_ID if epoch == 1 else HOME_ID],
                'Processed transfer update came from the wrong peer endpoint')
        result.append({'epoch': epoch, 'database_id': actual_id, 'name': actual_name,
                       'base_map_id': base_map, 'instance_number': instance, 'address': ip, 'port': port,
                       'database_id_source': 'processed MapServer player entity update',
                       'instance_number_is_map_container_id': False})
    return result


def accept_arrival(text, identifier, name, epoch, map_sample, character_sample):
    require(epoch in (1, 2) and type(epoch) is int, 'Invalid requested transfer epoch')
    observed = updates(text, identifier, name)
    require(len(observed) == epoch, 'Requested transfer lacks exactly its fresh processed update')
    target = CLONE_ID if epoch == 1 else HOME_ID
    require(ready(map_sample, target), 'Transfer destination is not independently ready with a current heartbeat')
    require(connected(character_sample, target), 'Character ownership has not completed transfer to the exact destination')
    return dict(observed[-1], map_id=target, static_map_id=target,
                exact_destination_endpoint_verified=True, in_map_transfer=False)
