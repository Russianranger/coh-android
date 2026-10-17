import json,unittest
from unittest.mock import patch
import inventory_oracle as item
import invention_oracle as invention
import update_oracle as update
import ledger
class Oracles(unittest.TestCase):
 def test_original_items(self):
  r=item.qualify();self.assertEqual(r['cases_count'],700);self.assertFalse(r['complete_inventory_update'])
 def test_original_update(self):
  r=update.qualify();self.assertEqual(r['cases_count'],360);self.assertTrue(any(c['expected']['auction_updated']==300 for c in r['cases']));self.assertTrue(any(c['expected']['auction_updated'] and not c['expected']['auction_text'] for c in r['cases']))
 def test_original_invention_divergence(self):
  r=invention.qualify();self.assertEqual(r['cases_count'],20)
  for c in r['cases']:self.assertEqual(c['sender_end_bit']-c['consumer_end_bit'],(32 if c['aligned'] else 1)*c['status'])
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
