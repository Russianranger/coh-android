"""Explicit NONSHIPPING Map observer. Exact accepted baseline; no upstream writes."""
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
GROUP='MapServer/src/group/groupnetsend.c'
TICK='MapServer/src/svr/svr_tick.c'
ENTS='MapServer/src/entity/entsend.c'
CHAR='MapServer/src/entity/entserver.c'
PROFILE='MapServer/src/group/coh_fresh_source_profile.inc'
PATCHED=(GROUP,TICK,ENTS,CHAR,PROFILE)
BASELINES={GROUP:'960dce22752416c6b6955cb25d01fc870dc7b6daa58ce371f1a2cf8404f486c8',TICK:'790635fec2f21e49981c776815eb8e927e79ef5a277324b0e3601cc3b4bbade0',ENTS:'045a5ecb5b64b956229583143fc61316dd8113d8eacf92183ad4756abad0a054',CHAR:'01da7bf37f633c98a39cd65176810e7b9c4bef4f834b896ed888ec6c52f47806',PROFILE:'65645b3798ac11c19db7be714ae0c4d77f37049b5add89a9ab5ab29c8a01e383'}
PREFIX=b'/* NONSHIPPING bounded original-server initial ledger. */\n'
GROUP_PREFIX=PREFIX+b'#include "coh_server_initial_api.h"\n'
OTHER_PREFIX=PREFIX+b'#include "../group/coh_server_initial_api.h"\n'
TAIL=b'\n/* New role only: caller-owned fixed diagnostic sink. */\n#include "coh_server_initial_adapter.inc"\n'
def need(ok):
 if not ok:raise ValueError('SERVER_INITIAL_SOURCE_REFUSED')
def lf(raw):
 need(type(raw)is bytes and b'\r'not in raw.replace(b'\r\n',b''));return raw.replace(b'\r\n',b'\n')
def restore(raw,original):return raw.replace(b'\n',b'\r\n')if b'\r\n'in original else raw
def once(raw,before,after):need(raw.count(before)==1);return raw.replace(before,after,1)
def hook(event,link,entity,packet='NULL',a='0',b='0',c='0',indent='    '):
 return (indent+'coh_sio_source_event(COH_SIO_'+event+', '+link+', '+entity+', '+packet+', '+a+', '+b+', '+c+'); /* SIO */\n').encode()
# Fixed literal replacements are reversed in opposite order; the full baseline
# hash is checked on both paths. No regex matching of arbitrary function bodies.
EDITS={TICK:[
 (b'        xcase CLIENT_REQALLENTS:\n',b'        xcase CLIENT_REQALLENTS:\n'+hook('DISPATCH','client->link','client->entity',indent='            ')),
 (b'            client->ready = CLIENTSTATE_REQALLENTS;\n            SET_ENTINFO(client->entity).sent_self = 0;\n            memset(client->entNetLink, 0, sizeof(EntNetLink));\n',b'            client->ready = CLIENTSTATE_REQALLENTS;\n            SET_ENTINFO(client->entity).sent_self = 0;\n            memset(client->entNetLink, 0, sizeof(EntNetLink));\n'+hook('REQUEST_STATE','client->link','client->entity',a='client->ready',b='!!ENTINFO(client->entity).sent_self',indent='            ')),
 (b'            if (!clientEnt)\n                continue;\n',b'            if (!clientEnt)\n                continue;\n'+hook('TICK','link','clientEnt',a='client->ready',b='!!ENTINFO(clientEnt).sent_self',indent='            ')),
 (b'                if(svrTickCheckDisconnect(link, client, max_buffered_packets))\n',hook('BACKPRESSURE_ENTER','link','clientEnt',indent='                ')+b'                if(svrTickCheckDisconnect(link, client, max_buffered_packets))\n'),
 (b'                {\n                    PERFINFO_AUTO_STOP();\n                    continue;\n                }\n\n                // Needs to stay north',b'                {\n'+hook('BACKPRESSURE_BLOCK','link','clientEnt',indent='                    ')+b'                    PERFINFO_AUTO_STOP();\n                    continue;\n                }\n'+hook('BACKPRESSURE_PASS','link','clientEnt',indent='                ')+b'\n                // Needs to stay north'),
 (b'                dbCheckMapXfer(clientEnt, link);\n',hook('MAPXFER_ENTER','link','clientEnt',indent='                ')+b'                dbCheckMapXfer(clientEnt, link);\n'+hook('MAPXFER_RETURN','link','clientEnt',indent='                ')),
 (b'                    entSendUpdate( link, clientGetViewedEntity(client), client->controls.repredict, client->ready!=CLIENTSTATE_IN_GAME, netSendIterationNumber);\n',hook('SELECTED','link','clientEnt',indent='                    ')+b'                    entSendUpdate( link, clientGetViewedEntity(client), client->controls.repredict, client->ready!=CLIENTSTATE_IN_GAME, netSendIterationNumber);\n')],
 ENTS:[
 (b'    ent_word_count = ((entities_max + sizeof(sent_ents_bits[0]) * 8 - 1)/(sizeof(sent_ents_bits[0])*8));\n',hook('FULL_ENTER','link','player_ent',a='!!full_update',b='player_ent == client->entity',c='!!re_predict')+b'    ent_word_count = ((entities_max + sizeof(sent_ents_bits[0]) * 8 - 1)/(sizeof(sent_ents_bits[0])*8));\n'),
 (b'            pktSendBitsPack(pak,1,SERVER_ALLENTS);\n',b'            pktSendBitsPack(pak,1,SERVER_ALLENTS);\n'+hook('ALLENTS_HEADER','link','player_ent','pak',indent='            ')),
 (b'            sendCharacterToClient(pak, player_ent);\n',b'            sendCharacterToClient(pak, player_ent);\n'+hook('CHARACTER_RETURN','link','player_ent','pak',indent='            ')),
 (b'    player_ent->entityPacket = pak;\n',b'    player_ent->entityPacket = pak;\n'+hook('ATTACHED','link','player_ent','pak')),
 (b'        // Send the packet for this entity (includes the entUpdate packet in the beginning, and all of the SERVER_GAME_CMDS\n',b'        coh_sio_source_finish_entity(e, e->entityPacket); /* SIO */\n        // Send the packet for this entity (includes the entUpdate packet in the beginning, and all of the SERVER_GAME_CMDS\n'),
 (b'                    pktSend(&e->entityPacket,client->link);\n',b'                    { /* SIO: preserve one original invocation and raw result. */\n                        int coh_sio_result;\n                        uintptr_t coh_sio_packet = (uintptr_t)e->entityPacket;\n'+hook('SEND_BEGIN','client->link','e','e->entityPacket',a='e->entityPacket->stream.bitLength',b='(!!e->entityPacket->reliable) | ((!!e->entityPacket->compress) << 1) | ((!!e->entityPacket->ordered) << 2)',indent='                        ')+b'                        coh_sio_result = pktSend(&e->entityPacket,client->link);\n                        coh_sio_source_send_return(coh_sio_packet,coh_sio_result); /* SIO: no post-call packet read. */\n                    }\n')],
 CHAR:[
 (b'void entFreeDbg(Entity *ent, const char* fileName, int fileLine)\n{\n',b'void entFreeDbg(Entity *ent, const char* fileName, int fileLine)\n{\n    coh_sio_source_retire_entity(ent); /* SIO: before original unlink/free. */\n'),
 (b'void sendCharacterToClient( Packet *pak, Entity *e)\n{\n    int i,k;\n',b'void sendCharacterToClient( Packet *pak, Entity *e)\n{\n    int i,k;\n'+b'    coh_sio_source_character(COH_SIO_CHARACTER_ENTER, e, pak); /* SIO: no new owner dereference. */\n'),
 (b'    character_Send(pak, e->pchar);\n',b'    coh_sio_source_character(COH_SIO_CHARACTER_CORE_ENTER, e, pak); /* SIO: no new owner dereference. */\n'+b'    character_Send(pak, e->pchar);\n'+b'    coh_sio_source_character(COH_SIO_CHARACTER_CORE_RETURN, e, pak); /* SIO: no new owner dereference. */\n')],
 PROFILE:[
 (b' int ok;\n if(!coh_fp_owner())return 0;\n ok=coh_fresh_original_hooks.finish(context,id,raw,bits,aligned,compress,report);\n if(ok){coh_fp_committed=1;',b' int ok;const NetLink*coh_sio_committing_link;\n if(!coh_fp_owner())return 0;\n coh_sio_committing_link=coh_groups_boundary.link; /* SIO: borrowed before original finish clears it. */\n ok=coh_fresh_original_hooks.finish(context,id,raw,bits,aligned,compress,report);\n if(ok){coh_sio_source_bind_groups(coh_sio_committing_link);coh_fp_committed=1;')]
}
def transform(originals):
 need(set(originals)==set(PATCHED));out={}
 for name in PATCHED:
  raw=lf(originals[name]);need(hashlib.sha256(raw).hexdigest()==BASELINES[name])
  for before,after in EDITS.get(name,()):raw=once(raw,before,after)
  if name==GROUP:raw=GROUP_PREFIX+raw+TAIL
  elif name!=PROFILE:raw=OTHER_PREFIX+raw
  out[name]=restore(raw,originals[name])
 return out
def reverse(patched):
 need(set(patched)==set(PATCHED));out={}
 for name in PATCHED:
  raw=lf(patched[name])
  if name==GROUP:need(raw.startswith(GROUP_PREFIX)and raw.endswith(TAIL));raw=raw[len(GROUP_PREFIX):-len(TAIL)]
  elif name!=PROFILE:need(raw.startswith(OTHER_PREFIX));raw=raw[len(OTHER_PREFIX):]
  for before,after in reversed(EDITS.get(name,())):raw=once(raw,after,before)
  need(hashlib.sha256(raw).hexdigest()==BASELINES[name]);out[name]=restore(raw,patched[name])
 return out
def overlays(root):
 need(Path(root).resolve()==HERE.parents[3])
 return {'MapServer/src/group/'+name:lf((HERE/local).read_bytes())for name,local in [
 ('coh_server_initial_api.h','coh_server_initial_api.h'),('coh_server_initial_ledger.h','coh_server_initial_ledger.h'),('coh_server_initial_ledger.c','coh_server_initial_ledger.c'),('coh_server_initial_adapter.inc','source_adapter.inc')]}
