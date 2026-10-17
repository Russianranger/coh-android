"""Independent replay of whole original raw group5/6 fixture projections."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import group56_oracle as oracle
import group56_independent as model
from independent import Refused
from test_oracles import retained
HERE=Path(__file__).resolve().parent
class OriginalGroup56(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.proof,cls.cases=retained('group56-host-proof.json')
  cls.widths=json.loads((HERE/'host-proof.json').read_text())['constants']['option_widths_in_enum_order']
 def test_exact_all_fields(self):
  self.assertEqual(model.qualify(self.cases,self.widths),self.proof['independent_model'])
 def test_last_bit_truncation(self):
  for case in self.cases:
   cut=copy.deepcopy(case);cut['end_bit']-=1
   with self.assertRaises(Refused):model.decode(cut,self.widths)
 def test_changed_field_refused(self):
  changed=copy.deepcopy(self.cases[0]);changed['expected']['chat']['tabs'][19]['system1']^=1
  with self.assertRaisesRegex(ValueError,'differs'):model.qualify([changed],self.widths)
 def test_missing_source_pins_refused(self):
  with tempfile.TemporaryDirectory() as d,mock.patch.object(oracle,'HERE',Path(d)):
   with self.assertRaises(FileNotFoundError):oracle.generate({})
 def test_both_option_and_profile_branches(self):
  self.assertEqual({c['expected']['options_saved'] for c in self.cases},{0,1})
  self.assertEqual({c['expected']['wire_key_profile'] for c in self.cases},{'default','Dev'})
  for c in self.cases:
   e=c['expected'];self.assertEqual(len(e['keybinds']),256);self.assertEqual(len(e['chat']['tabs']),20);self.assertEqual(len(e['combat_monitors']),10)
 def test_no_complete_character_claim(self):
  self.assertFalse(self.proof['whole_character_complete']);self.assertFalse(self.proof['original_oracle_sanitized'])
  self.assertTrue(self.proof['dictionary_ui_storage_shells'])
if __name__=='__main__':unittest.main()
