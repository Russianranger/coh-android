#!/usr/bin/env python3
"""Independent, nonshipping source admission audit. Does not certify packets.

Fail closed if currently unsupported entity-tail authority is enabled, or the
bounded Map controller acquires a completion command. The low-level serializer
is deliberately excluded: ability to encode READY is not permission to send it.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[4]
PATHS = {
    "entity": "engine/entities/coh_entities.c",
    "map": "engine/mapclient/coh_mapclient.c",
    "consumer": "../upstream/ouroboros/Game/src/entity/entrecv.c",
    "dispatch": "../upstream/ouroboros/Game/src/clientcomm/clientcomm.c",
    "producer": "../upstream/ouroboros/MapServer/src/entity/entsend.c",
}


def stripped(text):
    # Preserve strings as opaque tokens so comments cannot spoof audit anchors.
    return re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',
                  lambda m: '""' if m[0].startswith('"') else ' ', text)


def function(text, name):
    text = stripped(text)
    match = re.search(r'\b' + re.escape(name) + r'\s*\([^;{}]*\)\s*\{', text)
    if not match:
        raise ValueError("missing function: " + name)
    start = text.index('{', match.start())
    depth = 1
    end = start + 1
    while depth:
        if end >= len(text):
            raise ValueError("unterminated function: " + name)
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def ordered(text, names):
    cursor = 0
    for name in names:
        at = text.find(name, cursor)
        if at < 0:
            raise ValueError("missing/out-of-order source boundary: " + name)
        cursor = at + len(name)


def audit(sources):
    tail = function(sources['entity'], 'coh_ent_full_update_tail')
    returns = re.findall(r'\breturn\s+([^;]+);', tail)
    if returns != ['COH_INVALID', 'COH_UNSUPPORTED']:
        raise ValueError("unsupported outer tail changed; full transaction review required")
    # Any new command, including a variable expression, requires explicit review.
    sends = re.findall(r'\bsend_command\(m,\s*([^,]+),', stripped(sources['map']))
    if sorted(sends) != sorted(['COH_MAP_REQSHORTCUTS', 'COH_MAP_REQSCENE', 'COH_MAP_CONNECT']):
        raise ValueError("bounded controller command surface changed")
    if re.search(r'\b(?:CLIENTINP_ACK_FULL_UPDATE|CLIENTINP_RECEIVED_CHARACTER)\b',
                 stripped(sources['map'])):
        raise ValueError("application completion command in bounded controller")
    ordered(function(sources['consumer'], 'entReceiveUpdate'), [
        'playerReceiveControlState(pak)', 'entReceiveDeletes(pak)',
        'receiveCharacterFromServer(pak, player)', 'entity_ReceivePowerInfoUpdate(player, pak)',
        'entity_ReceivePowerModeUpdate(player, pak)', 'entity_ReceiveBadgeUpdate(player, pak)',
        'badgeMonitor_ReceiveInfo(player, pak)', 'entity_ReceiveInvUpdate(player, pak)',
        'entity_ReceiveInventionUpdate(player, pak)', 'receiveTeamList(pak, playerPtr())',
        'receiveSuperStats(pak, playerPtr())', 'receiveLeagueList(pak, playerPtr())',
        'receiveAttribDescription(playerPtr(), pak, 1, 0 )', 'groupDynReceive(pak)',
        'receiveSkyFade(pak)'])
    ordered(function(sources['producer'], 'entSendUpdate'), [
        'svrPlayerSendControlState(', 'entSendDeletes(', 'sendCharacterToClient(',
        'entity_SendPowerInfoUpdate(', 'entity_SendPowerModeUpdate(', 'entity_SendBadgeUpdate(',
        'badgeMonitor_SendInfo(', 'entity_SendInvUpdate(', 'entity_SendInventionUpdate(',
        'team_sendList(', 'sgroup_sendList(', 'league_sendList(', 'sendAttribDescription(',
        'groupDynSend(', 'sendSkyFade('])
    dispatch = stripped(sources['dispatch'])
    start = dispatch.index('xcase SERVER_ALLENTS:')
    end = dispatch.index('xcase SERVER_MAP_XFER_WAIT:', start)
    # Original early ACK is a historical hazard, not a native admission oracle.
    ordered(dispatch[start:end], ['CLIENTINP_ACK_FULL_UPDATE', 'entReceiveUpdate(',
                                 'if (!pktEnd(pak))', 'handleGameCmd(pak, gameCmd)'])


def main():
    sources = {key: (ROOT / path).read_text() for key, path in PATHS.items()}
    audit(sources)
    rejected = []
    mutations = [
        ('tail_false_success', 'entity', 'return COH_UNSUPPORTED;', 'return COH_OK;'),
        ('premature_ready', 'map', 'send_command(m,COH_MAP_REQSCENE,now)',
         'send_command(m,COH_MAP_READY,now)'),
        ('premature_allents', 'map', 'send_command(m,COH_MAP_REQSCENE,now)',
         'send_command(m,COH_MAP_REQALLENTS,now)'),
        ('unreviewed_variable_command', 'map', 'send_command(m,COH_MAP_REQSCENE,now)',
         'send_command(m,command,now)'),
        ('missing_power_tail', 'consumer', 'entity_ReceivePowerInfoUpdate(player, pak)',
         'omittedPowerInfo(player, pak)'),
        ('missing_embedded_commands', 'dispatch', 'handleGameCmd(pak, gameCmd)',
         'ignoredGameCmd(pak, gameCmd)'),
    ]
    for name, key, before, after in mutations:
        if before not in sources[key]:
            raise ValueError('mutation target missing: ' + name)
        altered = dict(sources)
        altered[key] = altered[key].replace(before, after)
        try:
            audit(altered)
        except ValueError:
            rejected.append(name)
        else:
            raise ValueError('audit admitted regression: ' + name)
    print(json.dumps({
        'audit_passed': True, 'audit_scope': 'source boundary review only',
        'sha256_lf': {PATHS[k]: hashlib.sha256(v.encode()).hexdigest() for k, v in sources.items()},
        'rejected_mutations': rejected, 'full_update_accepted': False,
        'authoritative_actor_accepted': False, 'live_world_accepted': False,
    }, indent=2))


if __name__ == '__main__':
    main()
