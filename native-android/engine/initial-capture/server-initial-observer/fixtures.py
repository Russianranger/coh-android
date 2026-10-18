"""Explicit synthetic fixed records for new admission controls, never source evidence."""
import json
import schema
def snapshot_fixture(final=False):
 value={name:False for name in (*schema.BOOLS,*schema.FALSE)}
 value.update({name:0 for name in schema.COUNTERS})
 value.update(schema=schema.SCHEMA,refusal='NONE',stop='ACTIVE',stage=20,reached_mask=1<<20,last_ready=0,ready_seen_mask=0,pkt_send_result=-1,final_packet_bits=0,diagnostic_only=True,valid=True,groups_owner_bound=True)
 if final:
  for name in ('owner_retired','dispatch_entered','dispatch_state_written','full_sender_entered','full_update_argument','viewed_entity_matches_owner','allents_header_written','character_entered','character_core_entered','character_core_returned','character_returned','packet_attached','finish_entity_seen','final_packet_same','pkt_send_called','pkt_send_returned','final_packet_compress','final_packet_ordered','final_packet_reliable'):value[name]=True
  value.update(stop='FINAL_RETURN',stage=19,reached_mask=(1<<21)-1,last_ready=1,ready_seen_mask=3,pkt_send_result=0,final_packet_bits=12345,tick_seen=1,tick_selected=1,backpressure_entered=1,backpressure_passed=1,mapxfer_entered=1,mapxfer_returned=1)
 return schema.parse(json.dumps(value).encode())
