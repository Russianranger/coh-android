"""Replay exact unchanged-source helper vectors with an independent wire model."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import unittest
import independent
import group4_oracle
import qualify_outer as q
HERE=Path(__file__).resolve().parent

def retained(name):
 proof=json.loads((HERE/name).read_text());meta=proof['fixtures'];data=(HERE/meta['file']).read_bytes()
 if len(data)!=meta['bytes'] or hashlib.sha256(data).hexdigest()!=meta['sha256']:raise ValueError('fixture archive binding')
 raw=gzip.decompress(data)
 if len(raw)!=meta['expanded_bytes']:raise ValueError('fixture expansion binding')
 cases=json.loads(raw)
 if len(cases)!=meta['cases']:raise ValueError('fixture count binding')
 return proof,cases

class OriginalOuter(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.helper,cls.helpers=retained('host-proof.json');cls.group4,cls.groups=retained('group4-host-proof.json')
 def test_helper_original_vectors(self):
  actual=independent.qualify(self.helpers,self.helper['constants']);self.assertEqual(actual,self.helper['independent_model'])
 def test_group4_original_vectors(self):
  actual=independent.qualify(self.groups,{});self.assertEqual(actual,self.group4['independent_model'])
 def test_group4_tail_truncation(self):
  for c in self.groups:
   data=bytes.fromhex(c['wire_hex'])
   with self.assertRaises(independent.Refused):independent.decode('group4',data,c['end_bit']-1,c['aligned'],c['begin_bit'],{})
 def test_false_original_observation_refused(self):
  c=copy.deepcopy(self.groups[0]);c['observed'][0]^=1
  with self.assertRaises(ValueError):independent.qualify([c],{})
 def test_group4_source_pin_mutation(self):
  texts={p:q.source(p) for p in q.PATHS};texts[q.PATHS[15]]+='\n'
  with self.assertRaisesRegex(ValueError,'source pin'):group4_oracle.generate(texts)
 def test_original_constants(self):
  self.assertEqual(self.group4['counts'],[8,9,10,4,720,128,5,128,6,17]);self.assertEqual(self.helper['constants']['windows'],128)
  self.assertEqual(len(self.helper['constants']['option_widths_in_enum_order']),114)
 def test_scope(self):
  for key in ['whole_character_complete','actor_publication','acknowledgments_enabled','android_executed','physical_thor_accepted']:
   self.assertFalse(self.helper[key])
  self.assertFalse(self.group4['original_oracle_sanitized']);self.assertFalse(self.group4['ui_window_state_applied'])

if __name__=='__main__':unittest.main()
