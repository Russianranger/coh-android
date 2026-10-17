"""Local controls only; never claims MSVC/Windows execution."""
import json,struct,tempfile,unittest
from pathlib import Path
import inventory_oracle as inv
import qualify_dynamic_msvc as m
class MsvcAdmission(unittest.TestCase):
 def test_exact_source_fragments(self):
  texts={n:inv.q.source(n) for n in m.PATHS};self.assertEqual({n:m.sha(s.encode()) for n,s in texts.items()},json.loads((m.HERE/'dynamic-msvc-source-pins.json').read_text()));code,fragments=m.generate(texts);self.assertIn('!defined(_M_IX86)',code);self.assertIn('defined(__clang__)',code);self.assertEqual(len(fragments),3)
 def test_pe_machine_refusals(self):
  raw=bytearray(128);raw[:2]=b'MZ';struct.pack_into('<I',raw,60,64);raw[64:68]=b'PE\0\0';struct.pack_into('<H',raw,68,0x14c);struct.pack_into('<H',raw,88,0x10b);self.assertTrue(m.pe_x86(raw))
  for at,value in [(68,0x8664),(88,0x20b),(0,0)]:
   bad=raw.copy();struct.pack_into('<H',bad,at,value)
   with self.assertRaises(ValueError):m.pe_x86(bad)
  with self.assertRaises(ValueError):m.pe_x86(raw[:70])
 def test_result_refusals(self):
  valid=dict(passed=True,patterns=256,reverse_patterns=256,status_bytes=1,pointer_bytes=4,msc_ver=1930,msc_full_ver=193030705,msc_build=0,m_ix86=600,native_bytes_hex=bytes(range(256)).hex());self.assertTrue(m.validate(valid))
  for field,value in [('passed',False),('patterns',255),('reverse_patterns',0),('status_bytes',4),('pointer_bytes',8),('msc_ver',0),('m_ix86',0),('patterns',True),('native_bytes_hex','00')]:
   with self.assertRaises(ValueError):m.validate({**valid,field:value})
 def test_generated_forward_reverse_guards(self):
  code,_=m.generate({n:inv.q.source(n) for n in m.PATHS})
  with tempfile.TemporaryDirectory(prefix='coh-msvc-helper-test-') as td:
   td=Path(td);(td/'probe.c').write_text(code)
   # Inspect generated guard only; this is not compile or runtime qualification.
   # The actual helper refuses this platform; no fake compiler receipt is minted.
   self.assertIn('require_pointer_size_4',code);self.assertIn('memcpy(&value,&raw,1)',code)
if __name__=='__main__':unittest.main()
