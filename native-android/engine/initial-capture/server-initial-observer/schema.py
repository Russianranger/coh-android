"""Fixed public ledger projection; no source object or private binding is read."""
import json
SCHEMA='coh-server-initial-ledger-v1'
MAX_BYTES=4096
REFUSALS=('NONE','OWNER','THREAD','ORDER','LIMIT','VALUE','PACKET','SINK')
STOPS=('ACTIVE','FINAL_RETURN','REFUSED')
BOOLS=('diagnostic_only','valid','groups_owner_bound','owner_retired','dispatch_entered','dispatch_state_written','full_sender_entered','full_update_argument','viewed_entity_matches_owner','allents_header_written','character_entered','character_core_entered','character_core_returned','character_returned','packet_attached','finish_entity_seen','final_packet_same','pkt_send_called','pkt_send_returned','last_sent_self','final_packet_compress','final_packet_ordered','final_packet_reliable')
COUNTERS=('tick_seen','tick_selected','backpressure_entered','backpressure_passed','backpressure_blocked','mapxfer_entered','mapxfer_returned')
FALSE=('packet_queue_acceptance_established','socket_send_established','source_generation_admitted','complete_initial_character','actor_publication','ack_permitted','world_authority')
KEYS=frozenset(('schema','refusal','stop','stage','reached_mask','last_ready','ready_seen_mask','pkt_send_result','final_packet_bits',*BOOLS,*COUNTERS,*FALSE))
def need(ok):
 if not ok:raise ValueError('SERVER_INITIAL_LEDGER_REFUSED')
def pairs(rows):
 result={}
 for key,value in rows:need(key not in result);result[key]=value
 return result
def parse(raw):
 need(type(raw)is bytes and 0<len(raw)<=MAX_BYTES)
 value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False))
 need(type(value)is dict and set(value)==KEYS and value['schema']==SCHEMA)
 for name in (*BOOLS,*FALSE):need(type(value[name])is bool)
 need(value['diagnostic_only']is True and all(value[name]is False for name in FALSE))
 need(type(value['refusal'])is str and value['refusal']in REFUSALS and type(value['stop'])is str and value['stop']in STOPS)
 for name in COUNTERS:need(type(value[name])is int and 0<=value[name]<=1000000)
 for name,limit in [('stage',20),('reached_mask',(1<<21)-1),('last_ready',7),('ready_seen_mask',255),('final_packet_bits',0xffffffff)]:need(type(value[name])is int and 0<=value[name]<=limit)
 need(type(value['pkt_send_result'])is int and value['pkt_send_result']in(-1,0,1))
 need(value['valid']==(value['refusal']=='NONE') and (value['stop']=='REFUSED')==(not value['valid']))
 if not value['groups_owner_bound']:need(not value['owner_retired']and value['stage']==0 and not value['reached_mask']and not any(value[n]for n in (*COUNTERS,*BOOLS[4:])))
 if value['pkt_send_returned']:need(value['pkt_send_called']and value['pkt_send_result']in(0,1)and value['stop']=='FINAL_RETURN'and value['owner_retired'])
 else:need(value['pkt_send_result']==-1 and value['stop']!='FINAL_RETURN')
 if value['pkt_send_called']:need(value['final_packet_same']and value['packet_attached']and value['character_returned']and value['allents_header_written'])
 else:need(not value['final_packet_bits']and not any(value[n]for n in ('final_packet_same','final_packet_compress','final_packet_ordered','final_packet_reliable')))
 if value['character_returned']:need(value['character_entered']and value['character_core_returned'])
 if value['character_core_returned']:need(value['character_core_entered'])
 if value['character_core_entered']:need(value['character_entered'])
 if value['allents_header_written']:need(value['full_sender_entered']and value['full_update_argument']and value['viewed_entity_matches_owner'])
 return {name:value[name]for name in sorted(KEYS)}
