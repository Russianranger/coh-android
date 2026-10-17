import json,unittest
from unittest.mock import patch
import inventory_oracle as item
import invention_oracle as invention
import update_oracle as update
import ledger
import attribute_monitor_oracle as attr
import dynamic_wire_oracle as dw
import sky_oracle as sky
import final_tail_ledger as final
import team_oracle as team
import superstats_oracle as sg
import active_invention_oracle as active
import member_oracle as member
class Oracles(unittest.TestCase):
 def test_original_items(self):
  r=item.qualify();self.assertEqual(r['cases_count'],700);self.assertFalse(r['complete_inventory_update'])
 def test_original_update(self):
  r=update.qualify();self.assertEqual(r['cases_count'],360);self.assertTrue(any(c['expected']['auction_updated']==300 for c in r['cases']));self.assertTrue(any(c['expected']['auction_updated'] and not c['expected']['auction_text'] for c in r['cases']))
 def test_original_invention_divergence(self):
  r=invention.qualify();self.assertEqual(r['cases_count'],20)
  for c in r['cases']:self.assertEqual(c['sender_end_bit']-c['consumer_end_bit'],(32 if c['aligned'] else 1)*c['status'])
 def test_attribute_monitor(self):
  r=attr.qualify();self.assertEqual(r['cases_count'],120);self.assertEqual(r['constants'],{'monitor_slots':10,'defense_offset':184,'character_attributes_bytes':460});self.assertFalse(r['full_mode_qualified'])
 def test_dynamic_source_wire(self):
  r=dw.qualify();self.assertEqual(r['cases_count'],160)
  for c in r['cases']:
   raw=bytes.fromhex(c['wire_hex'])
   with self.assertRaises(ValueError):dw.decode(raw,c['end_bit']-1,c['aligned'],c['begin_bit'],c['expected_world_count'])
   if c['expected']['modified_count']==0xffffffff:
    with self.assertRaises(ValueError):dw.decode(raw,c['end_bit'],c['aligned'],c['begin_bit'],c['expected_world_count']+1)
 def test_sky_source(self):
  r=sky.qualify();self.assertEqual(r['cases_count'],200);self.assertTrue(all(c['expected']['sky2']==1 for c in r['cases'] if not c['expected']['interesting']))
 def test_final_tail_boundaries(self):
  r=final.build();self.assertEqual(r,json.loads((final.HERE/'final-tail-ledger.json').read_text()));self.assertFalse(r['attributes']['full_mode_entry_count_on_wire']);self.assertFalse(r['attributes']['authentic_dictionary_found'])
 def test_whole_team_and_league(self):
  r=team.qualify();self.assertEqual(r['cases_count'],1000);self.assertTrue(any(len(c['expected']['members'])==48 for c in r['cases']))
 def test_superstats_producer(self):
  r=sg.qualify();self.assertEqual(r['cases_count'],180);self.assertFalse(r['original_consumer_executed']);self.assertTrue(any(c['expected']['count']==150 for c in r['cases']))
 def test_active_invention_producer(self):
  r=active.qualify();self.assertEqual(r['cases_count'],420);self.assertTrue(any(c['expected'].get('state')==5 for c in r['cases']));self.assertTrue(any(c['consumer_compatible'] is False for c in r['cases']))
 def test_member_state_profiles(self):
  r=member.qualify();self.assertEqual(r['cases_count'],160);self.assertTrue(any(c['expected']['onmap_wire'] and not c['expected']['applied_onmap'] for c in r['cases']))
 def test_pin_mutation_refused_before_execution(self):
  src=item.texts();src[item.EXTRA[0]]+='\n'
  with patch.object(item,'texts',return_value=src):
   with self.assertRaisesRegex(ValueError,'pin'):item.qualify()
 def test_truncation_model(self):
  r=item.qualify()
  for c in r['cases']:
   reader=item.independent.Reader(bytes.fromhex(c['wire_hex']),c['end_bit']-1,c['aligned'],c['begin_bit'])
   with self.assertRaises(item.independent.Refused):
    vals=[reader.packed(5) for _ in range(4)]
    if vals[0]==1:
     for _ in range(4):reader.scalar(32)
 def test_ledger_pin_and_scope(self):
  r=ledger.build();self.assertEqual(r,json.loads((ledger.HERE/'source-ledger.json').read_text()));self.assertFalse(r['full_initial_update_complete']);self.assertEqual(r['team']['max_members'],8);self.assertEqual(r['league']['max_members'],48)
if __name__=='__main__':unittest.main()
